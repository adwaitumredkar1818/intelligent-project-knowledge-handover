"""Handover Eligibility Gatekeeper Service.

Platform: The Handover
Module: Verification Center (Module 3 / Validation Area)

Enforces strict downstream handover eligibility criteria:
1. Knowledge item review_status must be 'approved'
2. Epistemic status must be 'human_verified' (AI-generated knowledge cannot pass autonomously)
3. Record must not be marked stale or deleted
4. Associated VerificationCase must exist and be in 'verified' status
5. No open CRITICAL or HIGH verification issues exist
6. No unresolved verification conflicts exist
7. All supporting evidence must be accessible under viewer's source ACLs (fail-closed)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import (
    EpistemicStatus,
    EvidenceSourceType,
    KnowledgeReviewStatus,
    RelationshipVerificationStatus,
    SourcePermissionVerificationStatus,
    VerificationCaseStatus,
    VerificationSeverity,
    VerificationTargetType,
)
from app.models.evidence import EvidenceItem
from app.models.integration import SourceAccessPolicy
from app.models.knowledge import KnowledgeEvidenceLink, KnowledgeItem
from app.models.relationship import (
    KnowledgeRelationship,
    RelationshipEvidenceLink,
)
from app.repositories.verification import (
    VerificationCaseRepository,
    VerificationConflictRepository,
    VerificationIssueRepository,
)


def _val(x: Any) -> str:
    if hasattr(x, "value"):
        return str(x.value)
    return str(x) if x is not None else ""


@dataclass(frozen=True, slots=True)
class HandoverEligibilityResult:
    """Detailed evaluation outcome for handover package inclusion."""

    is_eligible: bool
    target_type: VerificationTargetType
    target_id: uuid.UUID
    case_status: str
    epistemic_status: str
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def check_evidence_accessibility(
    session: Session,
    evidence_ids: list[uuid.UUID],
    *,
    project_id: uuid.UUID,
    viewer_user_id: uuid.UUID,
    has_project_manage: bool = False,
) -> tuple[bool, list[uuid.UUID]]:
    """Determine if the viewer has delegated permissions to all cited evidence IDs.

    Returns (all_accessible: bool, inaccessible_ids: list[UUID]).
    """
    if not evidence_ids:
        return True, []

    policies = list(
        session.execute(
            select(SourceAccessPolicy).where(SourceAccessPolicy.project_id == project_id)
        )
        .scalars()
        .all()
    )
    viewer_str = str(viewer_user_id)
    allowed_policy_ids: set[uuid.UUID] = set()
    revoked_policy_ids: set[uuid.UUID] = set()
    for policy in policies:
        if policy.sync_permission_status == SourcePermissionVerificationStatus.REVOKED.value:
            revoked_policy_ids.add(policy.id)
            continue
        if viewer_str in (policy.allowed_user_ids or []):
            allowed_policy_ids.add(policy.id)

    stmt = select(EvidenceItem).where(
        EvidenceItem.id.in_(evidence_ids),
        EvidenceItem.project_id == project_id,
        EvidenceItem.deleted_at.is_(None),
    )
    items = list(session.execute(stmt).scalars().all())
    found_ids = {item.id for item in items}

    inaccessible: list[uuid.UUID] = []
    # Any requested ID not found or deleted is inaccessible
    for eid in evidence_ids:
        if eid not in found_ids:
            inaccessible.append(eid)

    for item in items:
        # Check if policy is revoked
        if item.source_access_policy_id and item.source_access_policy_id in revoked_policy_ids:
            inaccessible.append(item.id)
            continue

        if item.acl_scope == "project_members":
            continue
        elif item.acl_scope == "source_restricted":
            if item.source_access_policy_id in allowed_policy_ids:
                continue
            if has_project_manage and item.source_type == EvidenceSourceType.DOCUMENT_UPLOAD.value:
                continue
            inaccessible.append(item.id)

    return len(inaccessible) == 0, inaccessible


class HandoverEligibilityService:
    """Enforces the quality gate between verified knowledge and final handover packages."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.case_repo = VerificationCaseRepository(session)
        self.issue_repo = VerificationIssueRepository(session)
        self.conflict_repo = VerificationConflictRepository(session)

    def check_knowledge_item_eligibility(
        self,
        knowledge_item_id: uuid.UUID,
        *,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool = False,
    ) -> HandoverEligibilityResult:
        """Check whether a KnowledgeItem is eligible for handover export."""
        item = self.session.get(KnowledgeItem, knowledge_item_id)
        if item is None or getattr(item, "is_deleted", False):
            return HandoverEligibilityResult(
                is_eligible=False,
                target_type=VerificationTargetType.KNOWLEDGE_ITEM,
                target_id=knowledge_item_id,
                case_status="not_found",
                epistemic_status="unknown",
                blockers=["Knowledge item does not exist or has been deleted."],
            )

        blockers: list[str] = []
        warnings: list[str] = []

        # 1. Epistemic status gate: Must be human verified
        if item.epistemic_status != EpistemicStatus.HUMAN_VERIFIED.value:
            blockers.append(
                f"Knowledge item has epistemic status '{item.epistemic_status}'. "
                "Only human-verified knowledge is eligible for handover."
            )

        # 2. Review status gate: Must be approved
        if item.review_status != KnowledgeReviewStatus.APPROVED.value:
            blockers.append(
                f"Knowledge item review status is '{item.review_status}'. "
                "It must be reviewed and approved by an authorized reviewer."
            )

        # 3. Staleness gate
        if getattr(item, "is_stale", False):
            blockers.append(
                "Knowledge item is marked stale due to source disconnection or newer updates."
            )

        # 4. Verification Case status
        case = self.case_repo.get_by_target(
            item.project_id,
            VerificationTargetType.KNOWLEDGE_ITEM,
            item.id,
            active_only=True,
            load_relationships=True,
        )
        if case is None:
            blockers.append("No active verification case found for this knowledge item.")
            case_status_str = "missing_case"
        else:
            case_status_str = _val(case.case_status)
            if _val(case.case_status) != _val(VerificationCaseStatus.VERIFIED):
                blockers.append(
                    f"Verification case is in status '{case_status_str}', expected 'verified'."
                )

            # Check open issues
            open_issues = self.issue_repo.list_by_case(case.id, open_only=True)
            blocking_issues = [
                i
                for i in open_issues
                if i.severity in (VerificationSeverity.CRITICAL, VerificationSeverity.HIGH)
            ]
            if blocking_issues:
                issue_types = ", ".join(i.issue_type for i in blocking_issues)
                blockers.append(
                    f"There are {len(blocking_issues)} unresolved blocking issues: {issue_types}."
                )

            # Check unresolved conflicts
            open_conflicts = self.conflict_repo.list_by_case(case.id, unresolved_only=True)
            if open_conflicts:
                blockers.append(
                    f"There are {len(open_conflicts)} unresolved cross-source conflicts."
                )

        # 5. Evidence Source ACL check
        links_stmt = select(KnowledgeEvidenceLink.evidence_id).where(
            KnowledgeEvidenceLink.knowledge_item_id == item.id
        )
        evidence_ids = list(self.session.execute(links_stmt).scalars().all())
        if not evidence_ids:
            blockers.append("Knowledge item has no supporting evidence links attached.")
        else:
            accessible, inaccessible = check_evidence_accessibility(
                self.session,
                evidence_ids,
                project_id=item.project_id,
                viewer_user_id=viewer_user_id,
                has_project_manage=has_project_manage,
            )
            if not accessible:
                blockers.append(
                    f"Viewer lacks access to {len(inaccessible)} supporting evidence source(s)."
                )

        return HandoverEligibilityResult(
            is_eligible=len(blockers) == 0,
            target_type=VerificationTargetType.KNOWLEDGE_ITEM,
            target_id=item.id,
            case_status=case_status_str,
            epistemic_status=str(item.epistemic_status),
            blockers=blockers,
            warnings=warnings,
        )

    def check_relationship_eligibility(
        self,
        relationship_id: uuid.UUID,
        *,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool = False,
    ) -> HandoverEligibilityResult:
        """Check whether a KnowledgeRelationship is eligible for handover graph export."""
        rel = self.session.get(KnowledgeRelationship, relationship_id)
        if rel is None:
            return HandoverEligibilityResult(
                is_eligible=False,
                target_type=VerificationTargetType.RELATIONSHIP,
                target_id=relationship_id,
                case_status="not_found",
                epistemic_status="unknown",
                blockers=["Relationship edge does not exist."],
            )

        blockers: list[str] = []
        warnings: list[str] = []

        if rel.verification_status != RelationshipVerificationStatus.VERIFIED.value:
            blockers.append(
                f"Relationship verification status is '{rel.verification_status}'. "
                "It must be verified by a human reviewer."
            )

        case = self.case_repo.get_by_target(
            rel.project_id,
            VerificationTargetType.RELATIONSHIP,
            rel.id,
            active_only=True,
            load_relationships=True,
        )
        if case is None:
            blockers.append("No active verification case found for this relationship.")
            case_status_str = "missing_case"
        else:
            case_status_str = _val(case.case_status)
            if _val(case.case_status) != _val(VerificationCaseStatus.VERIFIED):
                blockers.append(
                    f"Verification case is in status '{case_status_str}', expected 'verified'."
                )

        links_stmt = select(RelationshipEvidenceLink.evidence_id).where(
            RelationshipEvidenceLink.relationship_id == rel.id
        )
        evidence_ids = list(self.session.execute(links_stmt).scalars().all())
        if not evidence_ids:
            blockers.append("Relationship has no supporting evidence citations.")
        else:
            accessible, inaccessible = check_evidence_accessibility(
                self.session,
                evidence_ids,
                project_id=rel.project_id,
                viewer_user_id=viewer_user_id,
                has_project_manage=has_project_manage,
            )
            if not accessible:
                blockers.append(
                    f"Viewer lacks access to {len(inaccessible)} supporting evidence source(s)."
                )

        return HandoverEligibilityResult(
            is_eligible=len(blockers) == 0,
            target_type=VerificationTargetType.RELATIONSHIP,
            target_id=rel.id,
            case_status=case_status_str,
            epistemic_status=str(rel.verification_status),
            blockers=blockers,
            warnings=warnings,
        )
