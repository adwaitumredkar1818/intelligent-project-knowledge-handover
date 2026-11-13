"""Deterministic Verification Engine for Knowledge Items and Relationships.

Platform: The Handover
Module: Verification Center (Module 3 / Validation Area)

Enforces:
1. Provenance & Excerpt Verbatim Grounding
2. Source Reference & Chunk Consistency
3. Freshness & Staleness Rules
4. Exact Fingerprint & ID Deduplication
5. Status & Attribution Consistency
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import utc_now
from app.models.enums import (
    IssueResolutionState,
    MachineAssessmentStatus,
    RelationshipBasis,
    VerificationCaseStatus,
    VerificationIssueType,
    VerificationPriority,
    VerificationSeverity,
    VerificationTargetType,
)
from app.models.knowledge import KnowledgeEvidenceLink, KnowledgeItem
from app.models.relationship import (
    KnowledgeEntity,
    KnowledgeRelationship,
    RelationshipEvidenceLink,
)
from app.models.verification import (
    VerificationCase,
    VerificationIssue,
)
from app.repositories.verification import (
    VerificationCaseRepository,
    VerificationIssueRepository,
)
from app.services.verification_taxonomy import get_taxonomy_entry


def _normalize_text(text: str) -> str:
    """Normalize whitespace and lowercase for forgiving excerpt matching."""
    return re.sub(r"\s+", " ", text).strip().lower()


@dataclass
class AssessmentResult:
    """In-memory assessment outcome from deterministic rules."""

    target_type: VerificationTargetType
    target_id: uuid.UUID
    project_id: uuid.UUID
    organisation_id: uuid.UUID
    machine_status: MachineAssessmentStatus
    priority: VerificationPriority
    issues: list[dict[str, Any]] = field(default_factory=list)
    assessment_metadata: dict[str, Any] = field(default_factory=dict)


class DeterministicVerificationEngine:
    """Performs deterministic verification and provenance checks on project knowledge."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.case_repo = VerificationCaseRepository(session)
        self.issue_repo = VerificationIssueRepository(session)

    def assess_knowledge_item(self, item: KnowledgeItem) -> AssessmentResult:
        """Run deterministic verification on a reconstructed KnowledgeItem."""
        issues: list[dict[str, Any]] = []

        # 1. Fetch evidence links
        links_stmt = (
            select(KnowledgeEvidenceLink)
            .where(KnowledgeEvidenceLink.knowledge_item_id == item.id)
            .options(
                selectinload(KnowledgeEvidenceLink.evidence_item),
                selectinload(KnowledgeEvidenceLink.evidence_chunk),
            )
        )
        links = list(self.session.execute(links_stmt).scalars().all())

        if not links:
            entry = get_taxonomy_entry(VerificationIssueType.MISSING_EVIDENCE)
            issues.append(
                {
                    "issue_type": VerificationIssueType.MISSING_EVIDENCE,
                    "severity": entry.default_severity,
                    "description": "Finding has no supporting evidence links.",
                    "details_json": {"reason": "zero_links_found"},
                    "conflicting_evidence_id": None,
                    "conflicting_chunk_id": None,
                }
            )
        else:
            valid_links_count = 0
            for link in links:
                ev = link.evidence_item
                chunk = link.evidence_chunk

                # Validate evidence existence & project scope
                if not ev or ev.project_id != item.project_id:
                    entry = get_taxonomy_entry(VerificationIssueType.INVALID_SOURCE_REFERENCE)
                    issues.append(
                        {
                            "issue_type": VerificationIssueType.INVALID_SOURCE_REFERENCE,
                            "severity": entry.default_severity,
                            "description": (
                                "Cited evidence item is invalid or not in workspace."
                            ),
                            "details_json": {"cited_evidence_id": str(link.evidence_id)},
                            "conflicting_evidence_id": link.evidence_id,
                            "conflicting_chunk_id": link.evidence_chunk_id,
                        }
                    )
                    continue

                # Check chunk containment
                if link.evidence_chunk_id and (
                    not chunk or getattr(chunk, "evidence_id", None) != ev.id
                ):
                    entry = get_taxonomy_entry(VerificationIssueType.INVALID_SOURCE_REFERENCE)
                    issues.append(
                        {
                            "issue_type": VerificationIssueType.INVALID_SOURCE_REFERENCE,
                            "severity": entry.default_severity,
                            "description": "Cited chunk does not belong to cited evidence item.",
                            "details_json": {
                                "chunk_id": str(link.evidence_chunk_id),
                                "evidence_id": str(ev.id),
                            },
                            "conflicting_evidence_id": ev.id,
                            "conflicting_chunk_id": link.evidence_chunk_id,
                        }
                    )
                    continue

                # Check excerpt verbatim presence if excerpt is specified
                if link.supporting_excerpt:
                    excerpt_clean = _normalize_text(link.supporting_excerpt)
                    if chunk and chunk.chunk_text:
                        chunk_clean = _normalize_text(chunk.chunk_text)
                        if excerpt_clean not in chunk_clean:
                            entry = get_taxonomy_entry(VerificationIssueType.UNSUPPORTED_CLAIM)
                            issues.append(
                                {
                                    "issue_type": VerificationIssueType.UNSUPPORTED_CLAIM,
                                    "severity": entry.default_severity,
                                    "description": (
                                        "Supporting excerpt could not be matched in source chunk."
                                    ),
                                    "details_json": {
                                        "excerpt_preview": link.supporting_excerpt[:200],
                                        "chunk_id": str(chunk.id),
                                    },
                                    "conflicting_evidence_id": ev.id,
                                    "conflicting_chunk_id": chunk.id,
                                }
                            )
                    else:
                        entry = get_taxonomy_entry(VerificationIssueType.UNSUPPORTED_CLAIM)
                        issues.append(
                            {
                                "issue_type": VerificationIssueType.UNSUPPORTED_CLAIM,
                                "severity": entry.default_severity,
                                "description": (
                                    "Supporting excerpt provided but chunk has no readable text."
                                ),
                                "details_json": {"excerpt": link.supporting_excerpt[:200]},
                                "conflicting_evidence_id": ev.id,
                                "conflicting_chunk_id": link.evidence_chunk_id,
                            }
                        )

                # Check staleness
                if getattr(ev, "processing_status", None) == "failed" or getattr(
                    ev, "is_stale", False
                ):
                    entry = get_taxonomy_entry(VerificationIssueType.STALE_KNOWLEDGE)
                    issues.append(
                        {
                            "issue_type": VerificationIssueType.STALE_KNOWLEDGE,
                            "severity": entry.default_severity,
                            "description": (
                                "Cited evidence item is marked stale or failed processing."
                            ),
                            "details_json": {"evidence_id": str(ev.id)},
                            "conflicting_evidence_id": ev.id,
                            "conflicting_chunk_id": None,
                        }
                    )

                valid_links_count += 1

            if valid_links_count == 0 and not any(
                i["issue_type"] == VerificationIssueType.MISSING_EVIDENCE for i in issues
            ):
                entry = get_taxonomy_entry(VerificationIssueType.MISSING_EVIDENCE)
                issues.append(
                    {
                        "issue_type": VerificationIssueType.MISSING_EVIDENCE,
                        "severity": entry.default_severity,
                        "description": "No valid accessible evidence links exist for this finding.",
                        "details_json": {"reason": "all_links_invalid"},
                        "conflicting_evidence_id": None,
                        "conflicting_chunk_id": None,
                    }
                )

        # 2. Duplicate Detection
        domain = getattr(item, "primary_domain", None) or getattr(item, "category", "") or ""
        dup_stmt = select(KnowledgeItem).where(
            KnowledgeItem.project_id == item.project_id,
            KnowledgeItem.id != item.id,
            or_(
                KnowledgeItem.primary_domain == item.primary_domain,
                KnowledgeItem.category == item.category,
            ),
            func.lower(func.trim(KnowledgeItem.title)) == func.lower(func.trim(item.title)),
        )
        duplicates = list(self.session.execute(dup_stmt).scalars().all())
        if duplicates:
            entry = get_taxonomy_entry(VerificationIssueType.DUPLICATE_RECORD)
            issues.append(
                {
                    "issue_type": VerificationIssueType.DUPLICATE_RECORD,
                    "severity": entry.default_severity,
                    "description": (
                        f"Found {len(duplicates)} other finding(s) with identical title."
                    ),
                    "details_json": {"duplicate_item_ids": [str(d.id) for d in duplicates]},
                    "conflicting_evidence_id": None,
                    "conflicting_chunk_id": None,
                }
            )

        # 3. Completeness check
        payload = (
            getattr(item, "structured_payload", None) or getattr(item, "item_payload", None) or {}
        )
        if isinstance(payload, dict) and "decision" in domain.lower():
            rationale = payload.get("rationale") or payload.get("decision_rationale")
            if not rationale or len(str(rationale).strip()) < 5:
                entry = get_taxonomy_entry(VerificationIssueType.MISSING_SOURCE_CONTEXT)
                issues.append(
                    {
                        "issue_type": VerificationIssueType.MISSING_SOURCE_CONTEXT,
                        "severity": entry.default_severity,
                        "description": "Architectural decision is missing documented rationale.",
                        "details_json": {"missing_field": "rationale"},
                        "conflicting_evidence_id": None,
                        "conflicting_chunk_id": None,
                    }
                )

        # Calculate severity and machine status
        priority, machine_status = self._compute_priority_and_status(issues)

        return AssessmentResult(
            target_type=VerificationTargetType.KNOWLEDGE_ITEM,
            target_id=item.id,
            project_id=item.project_id,
            organisation_id=item.organisation_id,
            machine_status=machine_status,
            priority=priority,
            issues=issues,
            assessment_metadata={
                "assessed_at": utc_now().isoformat(),
                "knowledge_domain": domain,
                "links_checked": len(links),
                "issues_count": len(issues),
            },
        )

    def assess_relationship(self, rel: KnowledgeRelationship) -> AssessmentResult:
        """Run deterministic verification on a KnowledgeRelationship graph edge."""
        issues: list[dict[str, Any]] = []

        # 1. Fetch relationship evidence links
        links_stmt = (
            select(RelationshipEvidenceLink)
            .where(RelationshipEvidenceLink.relationship_id == rel.id)
            .options(
                selectinload(RelationshipEvidenceLink.evidence_item),
                selectinload(RelationshipEvidenceLink.evidence_chunk),
            )
        )
        links = list(self.session.execute(links_stmt).scalars().all())

        if not links:
            entry = get_taxonomy_entry(VerificationIssueType.MISSING_EVIDENCE)
            issues.append(
                {
                    "issue_type": VerificationIssueType.MISSING_EVIDENCE,
                    "severity": entry.default_severity,
                    "description": "Relationship edge has no cited supporting evidence links.",
                    "details_json": {"relationship_type": rel.relationship_type},
                    "conflicting_evidence_id": None,
                    "conflicting_chunk_id": None,
                }
            )
        else:
            for link in links:
                if link.supporting_excerpt and link.evidence_chunk:
                    excerpt_clean = _normalize_text(link.supporting_excerpt)
                    chunk_text = getattr(link.evidence_chunk, "chunk_text", "")
                    if chunk_text and excerpt_clean not in _normalize_text(chunk_text):
                        entry = get_taxonomy_entry(VerificationIssueType.UNSUPPORTED_CLAIM)
                        issues.append(
                            {
                                "issue_type": VerificationIssueType.UNSUPPORTED_CLAIM,
                                "severity": entry.default_severity,
                                "description": (
                                    "Relationship excerpt does not appear in cited chunk text."
                                ),
                                "details_json": {"excerpt": link.supporting_excerpt[:200]},
                                "conflicting_evidence_id": link.evidence_id,
                                "conflicting_chunk_id": link.evidence_chunk_id,
                            }
                        )

        # 2. Check inferred uncertainty
        if rel.relationship_basis == RelationshipBasis.INFERRED:
            entry = get_taxonomy_entry(VerificationIssueType.UNCERTAIN_RELATIONSHIP)
            issues.append(
                {
                    "issue_type": VerificationIssueType.UNCERTAIN_RELATIONSHIP,
                    "severity": entry.default_severity,
                    "description": (
                        "Relationship was inferred without explicit key reference."
                    ),
                    "details_json": {
                        "confidence_score": float(rel.confidence_score)
                        if rel.confidence_score is not None
                        else None,
                        "inference_reason": rel.inference_reason,
                    },
                    "conflicting_evidence_id": None,
                    "conflicting_chunk_id": None,
                }
            )

        # 3. Check entity endpoints
        source_ent = self.session.get(KnowledgeEntity, rel.source_entity_id)
        target_ent = self.session.get(KnowledgeEntity, rel.target_entity_id)
        if not source_ent or not target_ent:
            entry = get_taxonomy_entry(VerificationIssueType.INVALID_ENTITY_MAPPING)
            issues.append(
                {
                    "issue_type": VerificationIssueType.INVALID_ENTITY_MAPPING,
                    "severity": entry.default_severity,
                    "description": "One or both linked entity nodes do not exist.",
                    "details_json": {
                        "source_exists": bool(source_ent),
                        "target_exists": bool(target_ent),
                    },
                    "conflicting_evidence_id": None,
                    "conflicting_chunk_id": None,
                }
            )

        priority, machine_status = self._compute_priority_and_status(issues)

        return AssessmentResult(
            target_type=VerificationTargetType.RELATIONSHIP,
            target_id=rel.id,
            project_id=rel.project_id,
            organisation_id=rel.organisation_id,
            machine_status=machine_status,
            priority=priority,
            issues=issues,
            assessment_metadata={
                "assessed_at": utc_now().isoformat(),
                "relationship_type": rel.relationship_type,
                "basis": rel.relationship_basis,
                "issues_count": len(issues),
            },
        )

    def persist_assessment(self, result: AssessmentResult) -> VerificationCase:
        """Create or update canonical VerificationCase and its issues in PostgreSQL."""
        case = self.case_repo.get_by_target(
            result.project_id,
            result.target_type,
            result.target_id,
            active_only=True,
            load_relationships=True,
        )

        now = utc_now()
        if case is None:
            # Determine initial case status
            initial_case_status = VerificationCaseStatus.PENDING_REVIEW
            if result.machine_status == MachineAssessmentStatus.PASSED:
                initial_case_status = VerificationCaseStatus.CANDIDATE
            elif any(i["severity"] == VerificationSeverity.CRITICAL for i in result.issues):
                initial_case_status = VerificationCaseStatus.UNRESOLVED

            case = VerificationCase(
                organisation_id=result.organisation_id,
                project_id=result.project_id,
                target_type=result.target_type,
                target_id=result.target_id,
                case_status=initial_case_status,
                machine_assessment_status=result.machine_status,
                priority=result.priority,
                machine_assessment_json=result.assessment_metadata,
                last_assessed_at=now,
                version=1,
            )
            case = self.case_repo.create(case)
        else:
            case.machine_assessment_status = result.machine_status
            case.priority = result.priority
            case.machine_assessment_json = result.assessment_metadata
            case.last_assessed_at = now
            self.session.flush()

        # Reconcile issues: mark existing open issues that no longer appear as resolved, add new
        existing_issues = self.issue_repo.list_by_case(case.id, open_only=True)
        existing_types = {i.issue_type: i for i in existing_issues}
        new_types = {i["issue_type"] for i in result.issues}

        # Resolve disappearing issues
        for itype, ex_issue in existing_types.items():
            if itype not in new_types:
                ex_issue.resolution_state = IssueResolutionState.RESOLVED
                ex_issue.resolution_reason = (
                    "Auto-resolved by re-assessment: issue condition no longer met."
                )
                ex_issue.resolved_at = now

        # Add newly detected issues
        for issue_dict in result.issues:
            if issue_dict["issue_type"] not in existing_types:
                new_issue = VerificationIssue(
                    organisation_id=result.organisation_id,
                    project_id=result.project_id,
                    case_id=case.id,
                    issue_type=issue_dict["issue_type"],
                    severity=issue_dict["severity"],
                    description=issue_dict["description"],
                    detection_method="deterministic_rule",
                    details_json=issue_dict.get("details_json", {}),
                    conflicting_evidence_id=issue_dict.get("conflicting_evidence_id"),
                    conflicting_chunk_id=issue_dict.get("conflicting_chunk_id"),
                    resolution_state=IssueResolutionState.OPEN,
                )
                self.issue_repo.create(new_issue)

        self.session.flush()
        return case

    def _compute_priority_and_status(
        self, issues: list[dict[str, Any]]
    ) -> tuple[VerificationPriority, MachineAssessmentStatus]:
        if not issues:
            return VerificationPriority.LOW, MachineAssessmentStatus.PASSED

        severities = {i["severity"] for i in issues}
        types = {i["issue_type"] for i in issues}

        if VerificationIssueType.CONFLICTING_SOURCES in types:
            return VerificationPriority.HIGH, MachineAssessmentStatus.CONFLICT_DETECTED

        if VerificationIssueType.MISSING_EVIDENCE in types:
            return VerificationPriority.CRITICAL, MachineAssessmentStatus.INSUFFICIENT_EVIDENCE

        if VerificationSeverity.CRITICAL in severities:
            return VerificationPriority.CRITICAL, MachineAssessmentStatus.ISSUES_DETECTED

        if VerificationSeverity.HIGH in severities:
            return VerificationPriority.HIGH, MachineAssessmentStatus.ISSUES_DETECTED

        if VerificationSeverity.MEDIUM in severities:
            return VerificationPriority.MEDIUM, MachineAssessmentStatus.ISSUES_DETECTED

        return VerificationPriority.LOW, MachineAssessmentStatus.UNCERTAIN
