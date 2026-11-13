"""Human Review Service for Atomic Verification Approvals, Corrections, and Context Requests.

Platform: The Handover
Module: Verification Center (Module 3 / Validation Area)

Enforces:
1. Optimistic Concurrency Control (via case.version increments)
2. Append-Only Audit Logging & Review History Tracking
3. Promotion of Approved Findings to EpistemicStatus.HUMAN_VERIFIED
4. Gatekeeper Rules (blocking approval when critical provenance issues are open)
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_correlation_id
from app.core.security import utc_now
from app.models.enums import (
    ContextRequestStatus,
    EpistemicStatus,
    KnowledgeReviewStatus,
    RelationshipVerificationStatus,
    ReviewActionType,
    VerificationCaseStatus,
    VerificationSeverity,
    VerificationTargetType,
)
from app.models.knowledge import KnowledgeItem
from app.models.relationship import KnowledgeRelationship
from app.models.verification import (
    VerificationCase,
    VerificationContextRequest,
    VerificationReviewEvent,
)
from app.repositories.audit import AuditLogRepository
from app.repositories.verification import (
    VerificationCaseRepository,
    VerificationContextRequestRepository,
    VerificationIssueRepository,
    VerificationReviewEventRepository,
)
from app.services.audit import AuditService


class VerificationReviewError(Exception):
    """Base error for verification review operations."""


class CaseNotFoundError(VerificationReviewError):
    """Raised when the specified verification case does not exist."""


class ConcurrencyConflictError(VerificationReviewError):
    """Raised when the target case has been modified concurrently."""


class ReviewValidationError(VerificationReviewError):
    """Raised when an approval precondition fails (e.g. unresolved critical issues)."""


def _val(x: Any) -> str:
    if hasattr(x, "value"):
        return str(x.value)
    return str(x) if x is not None else ""


class HumanReviewService:
    """Orchestrates human review actions with optimistic locking and full provenance."""

    def __init__(self, session: Session, audit_service: AuditService | None = None) -> None:
        self.session = session
        self.case_repo = VerificationCaseRepository(session)
        self.issue_repo = VerificationIssueRepository(session)
        self.event_repo = VerificationReviewEventRepository(session)
        self.context_repo = VerificationContextRequestRepository(session)
        if audit_service is not None:
            self.audit = audit_service
        else:
            self.audit = AuditService(audit_repository=AuditLogRepository(session))

    def _get_case_or_raise(self, case_id: uuid.UUID) -> VerificationCase:
        case = self.case_repo.get_by_id(case_id, load_relationships=True)
        if case is None:
            raise CaseNotFoundError(f"Verification case {case_id} not found.")
        return case

    def _check_version(self, case: VerificationCase, expected_version: int) -> None:
        if case.version != expected_version:
            raise ConcurrencyConflictError(
                f"Concurrent modification detected. Current version is {case.version}, "
                f"expected {expected_version}. Please refresh and review latest changes."
            )

    def _make_snapshot(self, case: VerificationCase) -> dict[str, Any]:
        """Create a JSON snapshot of the case and its target for audit traceability."""
        snapshot: dict[str, Any] = {
            "case_id": str(case.id),
            "target_type": _val(case.target_type),
            "target_id": str(case.target_id),
            "case_status": _val(case.case_status),
            "machine_assessment_status": _val(case.machine_assessment_status),
            "priority": _val(case.priority),
            "version": case.version,
        }
        if _val(case.target_type) == _val(VerificationTargetType.KNOWLEDGE_ITEM):
            item = self.session.get(KnowledgeItem, case.target_id)
            if item:
                snapshot["target_snapshot"] = {
                    "title": item.title,
                    "summary": getattr(item, "structured_summary", None)
                    or getattr(item, "summary", ""),
                    "domain": getattr(item, "primary_domain", None)
                    or getattr(item, "category", ""),
                    "epistemic_status": item.epistemic_status,
                    "review_status": item.review_status,
                    "item_payload": getattr(item, "structured_payload", None)
                    or getattr(item, "item_payload", {}),
                }
        elif _val(case.target_type) == _val(VerificationTargetType.RELATIONSHIP):
            rel = self.session.get(KnowledgeRelationship, case.target_id)
            if rel:
                snapshot["target_snapshot"] = {
                    "relationship_type": rel.relationship_type,
                    "source_entity_id": str(rel.source_entity_id),
                    "target_entity_id": str(rel.target_entity_id),
                    "verification_status": rel.verification_status,
                }
        return snapshot

    def approve(
        self,
        *,
        case_id: uuid.UUID,
        reviewer_user_id: uuid.UUID,
        expected_version: int,
        review_notes: str | None = None,
    ) -> VerificationCase:
        """Approve a finding or relationship as human-verified knowledge."""
        case = self._get_case_or_raise(case_id)
        self._check_version(case, expected_version)

        # Precondition: No open CRITICAL issues (e.g. missing evidence)
        open_issues = self.issue_repo.list_by_case(case.id, open_only=True)
        critical_issues = [i for i in open_issues if i.severity == VerificationSeverity.CRITICAL]
        if critical_issues:
            types = ", ".join(i.issue_type for i in critical_issues)
            raise ReviewValidationError(
                f"Cannot approve finding with {len(critical_issues)} "
                f"unresolved critical issue(s): {types}. Resolve or attach valid evidence first."
            )

        now = utc_now()
        previous_status = _val(case.case_status)
        prev_snapshot = self._make_snapshot(case)

        # 1. Update Case
        case.case_status = VerificationCaseStatus.VERIFIED
        case.resolved_at = now
        case.last_reviewed_at = now
        case.version += 1

        # 2. Update Target
        if _val(case.target_type) == _val(VerificationTargetType.KNOWLEDGE_ITEM):
            item = self.session.get(KnowledgeItem, case.target_id)
            if item:
                item.review_status = KnowledgeReviewStatus.APPROVED
                item.epistemic_status = EpistemicStatus.HUMAN_VERIFIED
                item.reviewed_by_user_id = reviewer_user_id
                item.review_note = review_notes
                item.reviewed_at = now
                item.updated_at = now
        elif _val(case.target_type) == _val(VerificationTargetType.RELATIONSHIP):
            rel = self.session.get(KnowledgeRelationship, case.target_id)
            if rel:
                rel.verification_status = RelationshipVerificationStatus.VERIFIED
                rel.reviewed_by_user_id = reviewer_user_id
                rel.review_note = review_notes
                rel.reviewed_at = now
                rel.updated_at = now

        new_snapshot = self._make_snapshot(case)

        # 3. Append Review Event
        correlation_id = get_correlation_id()
        event = VerificationReviewEvent(
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            case=case,
            case_id=case.id,
            reviewer_user_id=reviewer_user_id,
            action=ReviewActionType.APPROVE,
            previous_status=previous_status,
            new_status=_val(VerificationCaseStatus.VERIFIED),
            review_notes=review_notes,
            previous_snapshot_json=prev_snapshot,
            new_snapshot_json=new_snapshot,
            correlation_id=correlation_id if correlation_id != "-" else str(uuid.uuid4()),
        )
        self.event_repo.create(event)

        # 4. Audit Log
        self.audit.record_event(
            actor_user_id=reviewer_user_id,
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            event_type="verification.case.approved",
            resource_type="verification_case",
            resource_id=str(case.id),
            metadata={
                "target_type": _val(case.target_type),
                "target_id": str(case.target_id),
                "version": case.version,
                "review_notes": review_notes,
            },
        )

        self.session.flush()
        self.session.refresh(case)
        return case

    def reject(
        self,
        *,
        case_id: uuid.UUID,
        reviewer_user_id: uuid.UUID,
        expected_version: int,
        reason: str,
        review_notes: str | None = None,
    ) -> VerificationCase:
        """Reject a candidate finding or relationship."""
        case = self._get_case_or_raise(case_id)
        self._check_version(case, expected_version)

        now = utc_now()
        previous_status = _val(case.case_status)
        prev_snapshot = self._make_snapshot(case)

        case.case_status = VerificationCaseStatus.REJECTED
        case.resolved_at = now
        case.last_reviewed_at = now
        case.version += 1

        if _val(case.target_type) == _val(VerificationTargetType.KNOWLEDGE_ITEM):
            item = self.session.get(KnowledgeItem, case.target_id)
            if item:
                item.review_status = KnowledgeReviewStatus.REJECTED
                item.reviewed_by_user_id = reviewer_user_id
                item.review_note = f"Rejected: {reason}. {review_notes or ''}".strip()
                item.reviewed_at = now
                item.updated_at = now
        elif _val(case.target_type) == _val(VerificationTargetType.RELATIONSHIP):
            rel = self.session.get(KnowledgeRelationship, case.target_id)
            if rel:
                rel.verification_status = RelationshipVerificationStatus.REJECTED
                rel.reviewed_by_user_id = reviewer_user_id
                rel.review_note = f"Rejected: {reason}. {review_notes or ''}".strip()
                rel.reviewed_at = now
                rel.updated_at = now

        new_snapshot = self._make_snapshot(case)

        correlation_id = get_correlation_id()
        event = VerificationReviewEvent(
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            case=case,
            case_id=case.id,
            reviewer_user_id=reviewer_user_id,
            action=ReviewActionType.REJECT,
            previous_status=previous_status,
            new_status=_val(VerificationCaseStatus.REJECTED),
            review_notes=f"Reason: {reason}\nNotes: {review_notes or 'None'}",
            previous_snapshot_json=prev_snapshot,
            new_snapshot_json=new_snapshot,
            correlation_id=correlation_id if correlation_id != "-" else str(uuid.uuid4()),
        )
        self.event_repo.create(event)

        self.audit.record_event(
            actor_user_id=reviewer_user_id,
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            event_type="verification.case.rejected",
            resource_type="verification_case",
            resource_id=str(case.id),
            metadata={
                "target_type": _val(case.target_type),
                "target_id": str(case.target_id),
                "reason": reason,
                "version": case.version,
            },
        )

        self.session.flush()
        self.session.refresh(case)
        return case

    def edit_finding(
        self,
        *,
        case_id: uuid.UUID,
        reviewer_user_id: uuid.UUID,
        expected_version: int,
        patch_data: dict[str, Any],
        reason: str,
    ) -> VerificationCase:
        """Apply human corrections directly to a finding while preserving full audit diff."""
        case = self._get_case_or_raise(case_id)
        self._check_version(case, expected_version)

        if _val(case.target_type) != _val(VerificationTargetType.KNOWLEDGE_ITEM):
            raise ReviewValidationError("Finding edits can only be applied to knowledge items.")

        item = self.session.get(KnowledgeItem, case.target_id)
        if not item:
            raise ReviewValidationError(f"Target knowledge item {case.target_id} not found.")

        now = utc_now()
        previous_status = _val(case.case_status)
        prev_snapshot = self._make_snapshot(case)

        # Apply allowed patch fields
        if "title" in patch_data and patch_data["title"]:
            item.title = str(patch_data["title"]).strip()
        if "summary" in patch_data and patch_data["summary"]:
            val = str(patch_data["summary"]).strip()
            if hasattr(item, "structured_summary"):
                item.structured_summary = val
            if hasattr(item, "summary"):
                item.summary = val
        if "item_payload" in patch_data and isinstance(patch_data["item_payload"], dict):
            current_payload = dict(
                getattr(item, "structured_payload", None) or getattr(item, "item_payload", {}) or {}
            )
            current_payload.update(patch_data["item_payload"])
            if hasattr(item, "structured_payload"):
                item.structured_payload = current_payload
            if hasattr(item, "item_payload"):
                item.item_payload = current_payload

        item.updated_at = now
        case.last_reviewed_at = now
        case.version += 1

        new_snapshot = self._make_snapshot(case)

        correlation_id = get_correlation_id()
        event = VerificationReviewEvent(
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            case=case,
            case_id=case.id,
            reviewer_user_id=reviewer_user_id,
            action=ReviewActionType.EDIT,
            previous_status=previous_status,
            new_status=_val(case.case_status),
            review_notes=f"Correction: {reason}",
            finding_patch_json=patch_data,
            previous_snapshot_json=prev_snapshot,
            new_snapshot_json=new_snapshot,
            correlation_id=correlation_id if correlation_id != "-" else str(uuid.uuid4()),
        )
        self.event_repo.create(event)

        self.audit.record_event(
            actor_user_id=reviewer_user_id,
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            event_type="verification.case.edited",
            resource_type="verification_case",
            resource_id=str(case.id),
            metadata={"patch": patch_data, "reason": reason, "version": case.version},
        )

        self.session.flush()
        self.session.refresh(case)
        return case

    def request_context(
        self,
        *,
        case_id: uuid.UUID,
        reviewer_user_id: uuid.UUID,
        requested_from_user_id: uuid.UUID,
        question: str,
        requested_information_type: str,
        expected_version: int | None = None,
    ) -> VerificationContextRequest:
        """Dispatch a clarification question to a departing member or project lead."""
        case = self._get_case_or_raise(case_id)
        if expected_version is not None:
            self._check_version(case, expected_version)

        now = utc_now()
        req = VerificationContextRequest(
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            case_id=case.id,
            requested_by_user_id=reviewer_user_id,
            requested_from_user_id=requested_from_user_id,
            question=question,
            requested_information_type=requested_information_type,
            status=ContextRequestStatus.PENDING,
        )
        req = self.context_repo.create(req)

        # Set case to pending review with context pending indicator
        case.case_status = VerificationCaseStatus.PENDING_REVIEW
        case.last_reviewed_at = now
        case.version += 1

        correlation_id = get_correlation_id()
        event = VerificationReviewEvent(
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            case=case,
            case_id=case.id,
            reviewer_user_id=reviewer_user_id,
            action=ReviewActionType.REQUEST_CONTEXT,
            previous_status=_val(case.case_status),
            new_status=_val(VerificationCaseStatus.PENDING_REVIEW),
            review_notes=f"Context requested: {question}",
            correlation_id=correlation_id if correlation_id != "-" else str(uuid.uuid4()),
        )
        self.event_repo.create(event)

        self.audit.record_event(
            actor_user_id=reviewer_user_id,
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            event_type="verification.context_requested",
            resource_type="verification_context_request",
            resource_id=str(req.id),
            metadata={
                "case_id": str(case.id),
                "requested_from": str(requested_from_user_id),
                "info_type": requested_information_type,
            },
        )

        self.session.flush()
        self.session.refresh(case)
        return req

    def mark_unresolved(
        self,
        *,
        case_id: uuid.UUID,
        reviewer_user_id: uuid.UUID,
        expected_version: int,
        explanation: str,
    ) -> VerificationCase:
        """Mark a case as unresolved when consensus or evidence cannot be established."""
        case = self._get_case_or_raise(case_id)
        self._check_version(case, expected_version)

        now = utc_now()
        previous_status = _val(case.case_status)
        case.case_status = VerificationCaseStatus.UNRESOLVED
        case.last_reviewed_at = now
        case.version += 1

        correlation_id = get_correlation_id()
        event = VerificationReviewEvent(
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            case=case,
            case_id=case.id,
            reviewer_user_id=reviewer_user_id,
            action=ReviewActionType.MARK_UNRESOLVED,
            previous_status=previous_status,
            new_status=_val(VerificationCaseStatus.UNRESOLVED),
            review_notes=f"Marked unresolved: {explanation}",
            correlation_id=correlation_id if correlation_id != "-" else str(uuid.uuid4()),
        )
        self.event_repo.create(event)

        self.audit.record_event(
            actor_user_id=reviewer_user_id,
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            event_type="verification.case.marked_unresolved",
            resource_type="verification_case",
            resource_id=str(case.id),
            metadata={"explanation": explanation, "version": case.version},
        )

        self.session.flush()
        self.session.refresh(case)
        return case

    def assign_reviewer(
        self,
        *,
        case_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        assignee_user_id: uuid.UUID | None,
        expected_version: int,
    ) -> VerificationCase:
        """Assign or reassign a verification case to a specific reviewer."""
        case = self._get_case_or_raise(case_id)
        self._check_version(case, expected_version)

        case.assigned_reviewer_id = assignee_user_id
        case.version += 1

        correlation_id = get_correlation_id()
        event = VerificationReviewEvent(
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            case=case,
            case_id=case.id,
            reviewer_user_id=actor_user_id,
            action=ReviewActionType.ASSIGN,
            previous_status=_val(case.case_status),
            new_status=_val(case.case_status),
            review_notes=f"Assigned reviewer to: {assignee_user_id or 'Unassigned'}",
            correlation_id=correlation_id if correlation_id != "-" else str(uuid.uuid4()),
        )
        self.event_repo.create(event)

        self.audit.record_event(
            actor_user_id=actor_user_id,
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            event_type="verification.case.assigned",
            resource_type="verification_case",
            resource_id=str(case.id),
            metadata={
                "assigned_reviewer_id": str(assignee_user_id) if assignee_user_id else None,
                "version": case.version,
            },
        )

        self.session.flush()
        self.session.refresh(case)
        return case
