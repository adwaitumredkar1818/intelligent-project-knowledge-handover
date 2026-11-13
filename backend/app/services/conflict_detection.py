"""Conflict Detection Engine for Cross-Source Contradictions and Inconsistencies.

Platform: The Handover
Module: Verification Center (Module 3 / Validation Area)

Identifies:
1. Status Conflicts (e.g. Jira Done vs Notes In-Progress)
2. Ownership Conflicts (e.g. conflicting assignees/architects)
3. Decision Conflicts (e.g. competing architectural directions)
4. Temporal Comparison & Supersession Analysis
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.enums import (
    ConflictResolutionState,
    ConflictType,
    IssueResolutionState,
    MachineAssessmentStatus,
    TemporalComparison,
    VerificationCaseStatus,
    VerificationIssueType,
    VerificationPriority,
)
from app.models.evidence import EvidenceItem
from app.models.verification import (
    VerificationCase,
    VerificationConflict,
    VerificationIssue,
)
from app.repositories.verification import (
    VerificationCaseRepository,
    VerificationConflictRepository,
    VerificationIssueRepository,
)
from app.services.verification_taxonomy import get_taxonomy_entry


def evaluate_temporal_precedence(
    ts_a: datetime | None, ts_b: datetime | None, *, threshold_seconds: float = 3600.0
) -> TemporalComparison:
    """Analyze timestamps to determine if one claim temporally supersedes another."""
    if ts_a is None or ts_b is None:
        return TemporalComparison.AMBIGUOUS

    # Ensure tz-aware
    if ts_a.tzinfo is None:
        ts_a = ts_a.replace(tzinfo=UTC)
    if ts_b.tzinfo is None:
        ts_b = ts_b.replace(tzinfo=UTC)

    diff = (ts_b - ts_a).total_seconds()
    if diff > threshold_seconds:
        return TemporalComparison.B_SUPERSEDES_A
    elif diff < -threshold_seconds:
        return TemporalComparison.A_SUPERSEDES_B
    return TemporalComparison.SIMULTANEOUS


class ConflictDetectionEngine:
    """Detects, explains, and records cross-source contradictions."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.case_repo = VerificationCaseRepository(session)
        self.conflict_repo = VerificationConflictRepository(session)
        self.issue_repo = VerificationIssueRepository(session)

    def register_conflict(
        self,
        *,
        case: VerificationCase,
        conflict_type: ConflictType,
        claim_a_text: str,
        claim_a_evidence_id: uuid.UUID,
        claim_b_text: str,
        claim_b_evidence_id: uuid.UUID,
        explanation: str,
        claim_a_chunk_id: uuid.UUID | None = None,
        claim_a_timestamp: datetime | None = None,
        claim_b_chunk_id: uuid.UUID | None = None,
        claim_b_timestamp: datetime | None = None,
    ) -> VerificationConflict:
        """Record a structured conflict between two sources on the verification case."""
        # 1. Deduce temporal comparison
        if claim_a_timestamp is None:
            ev_a = self.session.get(EvidenceItem, claim_a_evidence_id)
            if ev_a:
                claim_a_timestamp = ev_a.source_created_at or ev_a.source_updated_at
        if claim_b_timestamp is None:
            ev_b = self.session.get(EvidenceItem, claim_b_evidence_id)
            if ev_b:
                claim_b_timestamp = ev_b.source_created_at or ev_b.source_updated_at

        temporal_comp = evaluate_temporal_precedence(claim_a_timestamp, claim_b_timestamp)

        # 2. Persist VerificationConflict
        conflict = VerificationConflict(
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            case_id=case.id,
            conflict_type=conflict_type,
            claim_a_text=claim_a_text,
            claim_a_source_evidence_id=claim_a_evidence_id,
            claim_a_chunk_id=claim_a_chunk_id,
            claim_a_source_timestamp=claim_a_timestamp,
            claim_b_text=claim_b_text,
            claim_b_source_evidence_id=claim_b_evidence_id,
            claim_b_chunk_id=claim_b_chunk_id,
            claim_b_source_timestamp=claim_b_timestamp,
            explanation=explanation,
            temporal_comparison=temporal_comp,
            resolution_state=ConflictResolutionState.UNRESOLVED,
        )
        self.conflict_repo.create(conflict)

        # 3. Add CONFLICTING_SOURCES VerificationIssue if not already present
        existing_issues = self.issue_repo.list_by_case(case.id, open_only=True)
        has_conflict_issue = any(
            i.issue_type == VerificationIssueType.CONFLICTING_SOURCES for i in existing_issues
        )
        if not has_conflict_issue:
            entry = get_taxonomy_entry(VerificationIssueType.CONFLICTING_SOURCES)
            issue = VerificationIssue(
                organisation_id=case.organisation_id,
                project_id=case.project_id,
                case_id=case.id,
                issue_type=VerificationIssueType.CONFLICTING_SOURCES,
                severity=entry.default_severity,
                description=f"Contradiction detected ({conflict_type.value}): {explanation}",
                detection_method="cross_source_matcher",
                details_json={
                    "conflict_id": str(conflict.id),
                    "conflict_type": conflict_type.value,
                    "temporal_comparison": temporal_comp.value,
                },
                conflicting_evidence_id=claim_b_evidence_id,
                conflicting_chunk_id=claim_b_chunk_id,
                resolution_state=IssueResolutionState.OPEN,
            )
            self.issue_repo.create(issue)

        # 4. Escalate case status & machine assessment
        case.case_status = VerificationCaseStatus.CONFLICTED
        case.machine_assessment_status = MachineAssessmentStatus.CONFLICT_DETECTED
        if case.priority in (VerificationPriority.LOW, VerificationPriority.MEDIUM):
            case.priority = VerificationPriority.HIGH
        self.session.flush()

        return conflict

    def detect_status_conflicts(
        self,
        *,
        case: VerificationCase,
        finding_status: str,
        finding_text: str,
        primary_evidence_id: uuid.UUID,
        observed_items: list[dict[str, Any]],
    ) -> list[VerificationConflict]:
        """Scan observed external source items (Jira, commits) for contradictory status.

        observed_items format:
        [{"status": "in_progress", "text": "Issue", "evidence_id": UUID, "timestamp": datetime}]
        """
        conflicts: list[VerificationConflict] = []
        norm_status = finding_status.lower().strip()
        is_finding_completed = norm_status in ("completed", "done", "resolved", "closed")

        for item in observed_items:
            item_status = item.get("status", "").lower().strip()
            item_is_pending = item_status in ("in_progress", "to_do", "open", "blocked", "pending")
            item_evidence_id = item.get("evidence_id")

            if is_finding_completed and item_is_pending and item_evidence_id:
                expl = (
                    f"Finding asserts status '{finding_status}', but external source "
                    f"reports status '{item.get('status')}'."
                )
                conf = self.register_conflict(
                    case=case,
                    conflict_type=ConflictType.STATUS_CONFLICT,
                    claim_a_text=finding_text,
                    claim_a_evidence_id=primary_evidence_id,
                    claim_b_text=item.get("text", f"External status: {item_status}"),
                    claim_b_evidence_id=item_evidence_id,
                    explanation=expl,
                    claim_b_timestamp=item.get("timestamp"),
                )
                conflicts.append(conf)

        return conflicts
