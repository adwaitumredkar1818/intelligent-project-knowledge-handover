"""Handover Readiness Assessment Engine.

Platform: The Handover
Module: Handover Workspace (Module 4 / Knowledge Transfer Area)

Enforces:
1. Multi-dimensional evaluation across 9 categories
2. Deterministic scoring (0-100) with clear blocker and warning attribution
3. Human sign-off gating (packages with active blockers cannot be approved)
4. Full audit trail of readiness assessments per package version
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.security import utc_now
from app.models.audit import AuditLog
from app.models.enums import (
    AuditOutcome,
    EpistemicStatus,
    HandoverCaseStatus,
    HandoverReadinessCategory,
    KnowledgeReviewStatus,
    ReadinessLevel,
    RelationshipVerificationStatus,
    VerificationCaseStatus,
    VerificationSeverity,
)
from app.models.handover import (
    HandoverCase,
    HandoverPackageVersion,
    HandoverReadinessAssessment,
    HandoverResponsibilityTransfer,
)
from app.models.knowledge import KnowledgeEvidenceLink, KnowledgeItem
from app.models.relationship import KnowledgeRelationship
from app.models.verification import VerificationCase, VerificationConflict, VerificationIssue
from app.repositories.audit import AuditLogRepository
from app.repositories.handover import (
    HandoverCaseRepository,
    HandoverPackageVersionRepository,
    HandoverReadinessRepository,
    HandoverResponsibilityTransferRepository,
)
from app.schemas.handover import (
    HandoverReadinessAssessmentResponse,
    HandoverReadinessSummaryResponse,
)
from app.services.audit import AuditService
from app.services.handover_case import HandoverCaseService

CATEGORY_WEIGHTS: dict[str, float] = {
    HandoverReadinessCategory.EVIDENCE_COVERAGE.value: 0.15,
    HandoverReadinessCategory.VERIFICATION_COMPLETENESS.value: 0.20,
    HandoverReadinessCategory.CONFLICT_RESOLUTION.value: 0.15,
    HandoverReadinessCategory.KNOWLEDGE_FRESHNESS.value: 0.10,
    HandoverReadinessCategory.RELATIONSHIP_VALIDATION.value: 0.10,
    HandoverReadinessCategory.RESPONSIBILITY_COVERAGE.value: 0.15,
    HandoverReadinessCategory.RISK_ASSESSMENT.value: 0.05,
    HandoverReadinessCategory.DEPENDENCY_MAPPING.value: 0.10,
}


def _score_to_level(score: int, has_blockers: bool) -> str:
    if has_blockers or score < 50:
        return ReadinessLevel.NOT_READY.value
    if score >= 90:
        return ReadinessLevel.READY.value
    if score >= 75:
        return ReadinessLevel.READY_WITH_WARNINGS.value
    return ReadinessLevel.PARTIALLY_READY.value


class HandoverReadinessEngine:
    """Evaluates whether an assembled handover package is ready for human review and sign-off."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.case_repo = HandoverCaseRepository(session)
        self.version_repo = HandoverPackageVersionRepository(session)
        self.readiness_repo = HandoverReadinessRepository(session)
        self.resp_repo = HandoverResponsibilityTransferRepository(session)
        self.case_service = HandoverCaseService(session)
        self.audit_service = AuditService(audit_repository=AuditLogRepository(session))

    def assess_version(
        self,
        version_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        notes: str | None = None,
    ) -> HandoverReadinessSummaryResponse:
        """Run 9-category readiness assessment on an assembled package version."""
        version = self.version_repo.get_by_id(version_id, load_sections=True)
        if not version or version.project_id != project_id:
            raise NotFoundError(f"Package version {version_id} not found in this project.")

        case = self.case_service.get_case(version.case_id, project_id=project_id, load_relationships=False)

        # 1. Evidence Coverage
        stmt_ki = select(KnowledgeItem).where(
            KnowledgeItem.project_id == project_id,
            KnowledgeItem.is_deleted.is_(False),
        )
        all_kis = list(self.session.execute(stmt_ki).scalars().all())
        total_kis = len(all_kis)

        stmt_linked_ki = (
            select(func.count(func.distinct(KnowledgeEvidenceLink.knowledge_item_id)))
            .join(KnowledgeItem, KnowledgeEvidenceLink.knowledge_item_id == KnowledgeItem.id)
            .where(KnowledgeItem.project_id == project_id, KnowledgeItem.is_deleted.is_(False))
        )
        linked_ki_count = self.session.execute(stmt_linked_ki).scalar_one()

        cov_score = int((linked_ki_count / total_kis * 100)) if total_kis > 0 else 100
        cov_blockers: list[str] = []
        cov_warnings: list[str] = []
        if total_kis == 0:
            cov_warnings.append("No active knowledge items found for this project.")
        elif cov_score < 70:
            cov_warnings.append(f"Only {cov_score}% of knowledge items have cited supporting evidence.")

        # 2. Verification Completeness
        verified_kis = [
            k for k in all_kis
            if k.epistemic_status == EpistemicStatus.HUMAN_VERIFIED.value
            and k.review_status == KnowledgeReviewStatus.APPROVED.value
        ]
        ver_score = int((len(verified_kis) / total_kis * 100)) if total_kis > 0 else 100
        ver_blockers: list[str] = []
        ver_warnings: list[str] = []
        unverified_count = total_kis - len(verified_kis)
        if unverified_count > 0:
            if ver_score < 50:
                ver_blockers.append(f"{unverified_count} knowledge items have not been verified by a human reviewer.")
            else:
                ver_warnings.append(f"{unverified_count} knowledge items remain unverified.")

        # 3. Conflict Resolution
        stmt_conflicts = select(VerificationConflict).where(
            VerificationConflict.project_id == project_id,
            VerificationConflict.resolution_state == "unresolved",
        )
        unresolved_conflicts = list(self.session.execute(stmt_conflicts).scalars().all())
        conf_blockers: list[str] = []
        conf_warnings: list[str] = []
        if unresolved_conflicts:
            conf_score = max(0, 100 - len(unresolved_conflicts) * 25)
            conf_blockers.append(f"Found {len(unresolved_conflicts)} unresolved cross-source contradictions.")
        else:
            conf_score = 100

        # 4. Knowledge Freshness
        stale_kis = [k for k in all_kis if getattr(k, "is_stale", False)]
        fresh_score = max(0, 100 - len(stale_kis) * 15)
        fresh_blockers: list[str] = []
        fresh_warnings: list[str] = []
        if stale_kis:
            fresh_warnings.append(f"{len(stale_kis)} knowledge items are marked stale.")

        # 5. Relationship Validation
        stmt_rels = select(KnowledgeRelationship).where(KnowledgeRelationship.project_id == project_id)
        all_rels = list(self.session.execute(stmt_rels).scalars().all())
        total_rels = len(all_rels)
        verified_rels = [
            r for r in all_rels
            if r.verification_status == RelationshipVerificationStatus.VERIFIED.value
        ]
        rel_score = int((len(verified_rels) / total_rels * 100)) if total_rels > 0 else 100
        rel_blockers: list[str] = []
        rel_warnings: list[str] = []
        if total_rels > 0 and rel_score < 60:
            rel_warnings.append(f"Only {rel_score}% of graph relationships have been verified.")

        # 6. Responsibility Coverage
        stmt_transfers = select(HandoverResponsibilityTransfer).where(
            HandoverResponsibilityTransfer.case_id == case.id
        )
        transfers = list(self.session.execute(stmt_transfers).scalars().all())
        resp_blockers: list[str] = []
        resp_warnings: list[str] = []
        if not transfers:
            resp_score = 40
            resp_warnings.append("No explicit responsibility transfers mapped for the departing member.")
        else:
            unassigned = [t for t in transfers if not t.proposed_successor_id]
            if unassigned:
                resp_score = max(50, int((len(transfers) - len(unassigned)) / len(transfers) * 100))
                resp_warnings.append(f"{len(unassigned)} responsibilities have no proposed successor.")
            else:
                resp_score = 100

        # 7. Risk Assessment
        risk_kis = [
            k for k in all_kis
            if k.category in ("bugs_blockers_risks", "risks_blockers_questions")
        ]
        risk_score = 100
        risk_blockers: list[str] = []
        risk_warnings: list[str] = []
        if not risk_kis:
            risk_warnings.append("No active bugs, blockers, or risks documented in this project.")

        # 8. Dependency Mapping
        dep_kis = [
            k for k in all_kis
            if k.category in ("dependencies", "dependencies_relationships")
        ]
        dep_score = 100 if (dep_kis or all_rels) else 60
        dep_blockers: list[str] = []
        dep_warnings: list[str] = []
        if not dep_kis and not all_rels:
            dep_warnings.append("No technical dependencies or architectural links identified.")

        # Aggregate Overall Score
        category_evals: list[dict[str, Any]] = [
            {
                "category": HandoverReadinessCategory.EVIDENCE_COVERAGE.value,
                "score": cov_score,
                "blockers": cov_blockers,
                "warnings": cov_warnings,
            },
            {
                "category": HandoverReadinessCategory.VERIFICATION_COMPLETENESS.value,
                "score": ver_score,
                "blockers": ver_blockers,
                "warnings": ver_warnings,
            },
            {
                "category": HandoverReadinessCategory.CONFLICT_RESOLUTION.value,
                "score": conf_score,
                "blockers": conf_blockers,
                "warnings": conf_warnings,
            },
            {
                "category": HandoverReadinessCategory.KNOWLEDGE_FRESHNESS.value,
                "score": fresh_score,
                "blockers": fresh_blockers,
                "warnings": fresh_warnings,
            },
            {
                "category": HandoverReadinessCategory.RELATIONSHIP_VALIDATION.value,
                "score": rel_score,
                "blockers": rel_blockers,
                "warnings": rel_warnings,
            },
            {
                "category": HandoverReadinessCategory.RESPONSIBILITY_COVERAGE.value,
                "score": resp_score,
                "blockers": resp_blockers,
                "warnings": resp_warnings,
            },
            {
                "category": HandoverReadinessCategory.RISK_ASSESSMENT.value,
                "score": risk_score,
                "blockers": risk_blockers,
                "warnings": risk_warnings,
            },
            {
                "category": HandoverReadinessCategory.DEPENDENCY_MAPPING.value,
                "score": dep_score,
                "blockers": dep_blockers,
                "warnings": dep_warnings,
            },
        ]

        weighted_sum = sum(
            c["score"] * CATEGORY_WEIGHTS[c["category"]] for c in category_evals
        )
        overall_score = int(round(weighted_sum))

        all_blockers = [b for c in category_evals for b in c["blockers"]]
        all_warnings = [w for c in category_evals for w in c["warnings"]]

        overall_eval = {
            "category": HandoverReadinessCategory.OVERALL_QUALITY.value,
            "score": overall_score,
            "blockers": all_blockers,
            "warnings": all_warnings,
        }
        category_evals.append(overall_eval)

        # Persist HandoverReadinessAssessment records
        assessments_to_create: list[HandoverReadinessAssessment] = []
        for eval_data in category_evals:
            has_b = len(eval_data["blockers"]) > 0
            assessments_to_create.append(
                HandoverReadinessAssessment(
                    organisation_id=case.organisation_id,
                    project_id=project_id,
                    case_id=case.id,
                    version_id=version.id,
                    category=eval_data["category"],
                    score=eval_data["score"],
                    level=_score_to_level(eval_data["score"], has_b),
                    blockers_json=eval_data["blockers"],
                    warnings_json=eval_data["warnings"],
                    details_json={"notes": notes} if notes else {},
                    assessed_by_user_id=user_id,
                    assessed_at=utc_now(),
                )
            )

        self.readiness_repo.create_bulk(assessments_to_create)

        # Update case status to READINESS_ASSESSED if applicable
        if case.status in (
            HandoverCaseStatus.ASSEMBLED.value,
            HandoverCaseStatus.READINESS_PENDING.value,
            HandoverCaseStatus.READINESS_ASSESSED.value,
        ):
            self.case_service.transition_status(
                case.id,
                project_id=project_id,
                new_status=HandoverCaseStatus.READINESS_ASSESSED.value,
                user_id=user_id,
                change_reason=f"Readiness assessed: score {overall_score}/100",
            )

        self.audit_service.record_event(
            event_type="handover.readiness.assessed",
            resource_type="handover_package_version",
            resource_id=str(version.id),
            actor_user_id=user_id,
            organisation_id=case.organisation_id,
            project_id=project_id,
            outcome=AuditOutcome.SUCCESS.value,
            metadata={
                "overall_score": overall_score,
                "blocker_count": len(all_blockers),
                "warning_count": len(all_warnings),
            },
        )

        self.session.flush()

        cat_responses = [
            HandoverReadinessAssessmentResponse(
                id=a.id,
                version_id=a.version_id,
                category=a.category,
                score=a.score,
                level=a.level,
                blockers_json=a.blockers_json,
                warnings_json=a.warnings_json,
                assessed_by_user_id=a.assessed_by_user_id,
                assessed_at=a.assessed_at,
                created_at=a.created_at,
            )
            for a in assessments_to_create
        ]

        is_ready = overall_score >= 70 and len(all_blockers) == 0

        return HandoverReadinessSummaryResponse(
            version_id=version.id,
            overall_score=overall_score,
            overall_level=_score_to_level(overall_score, len(all_blockers) > 0),
            categories=cat_responses,
            is_ready_for_signoff=is_ready,
            blocker_count=len(all_blockers),
            warning_count=len(all_warnings),
        )
