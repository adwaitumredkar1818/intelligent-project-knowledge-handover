"""Data-access repository for Verification Center (Module 3 / Validation Area).

Manages:
- Verification cases (polymorphic tracking of knowledge items and relationships)
- Verification issues (provenance, grounding, freshness, and consistency flaws)
- Verification conflicts (side-by-side contradiction records)
- Verification review events (immutable human review actions)
- Verification context requests (in-platform clarification requests)
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import utc_now
from app.models.enums import (
    ConflictResolutionState,
    ContextRequestStatus,
    IssueResolutionState,
    VerificationCaseStatus,
    VerificationPriority,
    VerificationTargetType,
)
from app.models.verification import (
    VerificationCase,
    VerificationConflict,
    VerificationContextRequest,
    VerificationIssue,
    VerificationReviewEvent,
)


class VerificationCaseRepository:
    """Repository for managing VerificationCase records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, case: VerificationCase) -> VerificationCase:
        self.session.add(case)
        self.session.flush()
        return case

    def get_by_id(
        self, case_id: uuid.UUID, *, load_relationships: bool = True
    ) -> VerificationCase | None:
        stmt = select(VerificationCase).where(VerificationCase.id == case_id)
        if load_relationships:
            stmt = stmt.options(
                selectinload(VerificationCase.issues),
                selectinload(VerificationCase.conflicts),
                selectinload(VerificationCase.review_events),
                selectinload(VerificationCase.context_requests),
                selectinload(VerificationCase.assigned_reviewer),
            )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_target(
        self,
        project_id: uuid.UUID,
        target_type: VerificationTargetType,
        target_id: uuid.UUID,
        *,
        active_only: bool = True,
        load_relationships: bool = True,
    ) -> VerificationCase | None:
        stmt = select(VerificationCase).where(
            VerificationCase.project_id == project_id,
            VerificationCase.target_type == target_type,
            VerificationCase.target_id == target_id,
        )
        if active_only:
            stmt = stmt.where(VerificationCase.case_status != VerificationCaseStatus.ARCHIVED)
        if load_relationships:
            stmt = stmt.options(
                selectinload(VerificationCase.issues),
                selectinload(VerificationCase.conflicts),
                selectinload(VerificationCase.review_events),
                selectinload(VerificationCase.context_requests),
                selectinload(VerificationCase.assigned_reviewer),
            )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_queue(
        self,
        project_id: uuid.UUID,
        *,
        case_status: VerificationCaseStatus | None = None,
        priority: VerificationPriority | None = None,
        target_type: VerificationTargetType | None = None,
        assigned_reviewer_id: uuid.UUID | None = None,
        unassigned_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VerificationCase]:
        stmt = (
            select(VerificationCase)
            .where(VerificationCase.project_id == project_id)
            .options(
                selectinload(VerificationCase.issues),
                selectinload(VerificationCase.conflicts),
                selectinload(VerificationCase.assigned_reviewer),
            )
        )
        if case_status is not None:
            stmt = stmt.where(VerificationCase.case_status == case_status)
        else:
            stmt = stmt.where(VerificationCase.case_status != VerificationCaseStatus.ARCHIVED)

        if priority is not None:
            stmt = stmt.where(VerificationCase.priority == priority)
        if target_type is not None:
            stmt = stmt.where(VerificationCase.target_type == target_type)
        if unassigned_only:
            stmt = stmt.where(VerificationCase.assigned_reviewer_id.is_(None))
        elif assigned_reviewer_id is not None:
            stmt = stmt.where(VerificationCase.assigned_reviewer_id == assigned_reviewer_id)

        # Order by: priority (critical > high > medium > low), then updated_at desc
        stmt = stmt.order_by(VerificationCase.created_at.desc()).limit(limit).offset(offset)

        return list(self.session.execute(stmt).scalars().all())

    def count_queue(
        self,
        project_id: uuid.UUID,
        *,
        case_status: VerificationCaseStatus | None = None,
        priority: VerificationPriority | None = None,
        target_type: VerificationTargetType | None = None,
        assigned_reviewer_id: uuid.UUID | None = None,
        unassigned_only: bool = False,
    ) -> int:
        stmt = select(func.count(VerificationCase.id)).where(
            VerificationCase.project_id == project_id
        )
        if case_status is not None:
            stmt = stmt.where(VerificationCase.case_status == case_status)
        else:
            stmt = stmt.where(VerificationCase.case_status != VerificationCaseStatus.ARCHIVED)

        if priority is not None:
            stmt = stmt.where(VerificationCase.priority == priority)
        if target_type is not None:
            stmt = stmt.where(VerificationCase.target_type == target_type)
        if unassigned_only:
            stmt = stmt.where(VerificationCase.assigned_reviewer_id.is_(None))
        elif assigned_reviewer_id is not None:
            stmt = stmt.where(VerificationCase.assigned_reviewer_id == assigned_reviewer_id)

        return self.session.execute(stmt).scalar_one() or 0

    def get_summary(self, project_id: uuid.UUID) -> dict[str, Any]:
        """Aggregate summary metrics for project verification status."""
        # 1. Counts by case status
        status_stmt = (
            select(VerificationCase.case_status, func.count(VerificationCase.id))
            .where(VerificationCase.project_id == project_id)
            .group_by(VerificationCase.case_status)
        )
        status_rows = self.session.execute(status_stmt).all()
        by_status = {str(row[0]): row[1] for row in status_rows}

        # 2. Counts by priority
        priority_stmt = (
            select(VerificationCase.priority, func.count(VerificationCase.id))
            .where(
                VerificationCase.project_id == project_id,
                VerificationCase.case_status != VerificationCaseStatus.ARCHIVED,
            )
            .group_by(VerificationCase.priority)
        )
        priority_rows = self.session.execute(priority_stmt).all()
        by_priority = {str(row[0]): row[1] for row in priority_rows}

        # 3. Active open issues count
        issues_stmt = select(func.count(VerificationIssue.id)).where(
            VerificationIssue.project_id == project_id,
            VerificationIssue.resolution_state == IssueResolutionState.OPEN,
        )
        open_issues_count = self.session.execute(issues_stmt).scalar_one() or 0

        # 4. Open conflicts count
        conflicts_stmt = select(func.count(VerificationConflict.id)).where(
            VerificationConflict.project_id == project_id,
            VerificationConflict.resolution_state == ConflictResolutionState.UNRESOLVED,
        )
        open_conflicts_count = self.session.execute(conflicts_stmt).scalar_one() or 0

        # 5. Pending context requests count
        context_stmt = select(func.count(VerificationContextRequest.id)).where(
            VerificationContextRequest.project_id == project_id,
            VerificationContextRequest.status == ContextRequestStatus.PENDING,
        )
        pending_context_requests_count = self.session.execute(context_stmt).scalar_one() or 0

        return {
            "total_cases": sum(by_status.values()),
            "by_status": by_status,
            "by_priority": by_priority,
            "open_issues_count": open_issues_count,
            "open_conflicts_count": open_conflicts_count,
            "pending_context_requests_count": pending_context_requests_count,
        }

    def update(self, case: VerificationCase) -> VerificationCase:
        case.updated_at = utc_now()
        self.session.flush()
        return case


class VerificationIssueRepository:
    """Repository for managing VerificationIssue records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, issue: VerificationIssue) -> VerificationIssue:
        self.session.add(issue)
        self.session.flush()
        return issue

    def get_by_id(self, issue_id: uuid.UUID) -> VerificationIssue | None:
        stmt = (
            select(VerificationIssue)
            .where(VerificationIssue.id == issue_id)
            .options(
                selectinload(VerificationIssue.conflicting_evidence),
                selectinload(VerificationIssue.conflicting_chunk),
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_case(
        self, case_id: uuid.UUID, *, open_only: bool = False
    ) -> list[VerificationIssue]:
        stmt = select(VerificationIssue).where(VerificationIssue.case_id == case_id)
        if open_only:
            stmt = stmt.where(VerificationIssue.resolution_state == IssueResolutionState.OPEN)
        stmt = stmt.options(
            selectinload(VerificationIssue.conflicting_evidence),
            selectinload(VerificationIssue.conflicting_chunk),
        ).order_by(VerificationIssue.created_at.asc())
        return list(self.session.execute(stmt).scalars().all())

    def update_resolution(
        self,
        issue_id: uuid.UUID,
        resolution_state: IssueResolutionState,
        *,
        reason: str | None = None,
        resolved_by_user_id: uuid.UUID | None = None,
    ) -> VerificationIssue | None:
        issue = self.get_by_id(issue_id)
        if not issue:
            return None
        issue.resolution_state = resolution_state
        issue.resolution_reason = reason
        issue.resolved_by_user_id = resolved_by_user_id
        issue.resolved_at = utc_now() if resolution_state != IssueResolutionState.OPEN else None
        issue.updated_at = utc_now()
        self.session.flush()
        return issue


class VerificationConflictRepository:
    """Repository for managing VerificationConflict records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, conflict: VerificationConflict) -> VerificationConflict:
        self.session.add(conflict)
        self.session.flush()
        return conflict

    def get_by_id(self, conflict_id: uuid.UUID) -> VerificationConflict | None:
        stmt = (
            select(VerificationConflict)
            .where(VerificationConflict.id == conflict_id)
            .options(
                selectinload(VerificationConflict.claim_a_evidence),
                selectinload(VerificationConflict.claim_b_evidence),
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_case(
        self, case_id: uuid.UUID, *, unresolved_only: bool = False
    ) -> list[VerificationConflict]:
        stmt = select(VerificationConflict).where(VerificationConflict.case_id == case_id)
        if unresolved_only:
            stmt = stmt.where(
                VerificationConflict.resolution_state == ConflictResolutionState.UNRESOLVED
            )
        stmt = stmt.options(
            selectinload(VerificationConflict.claim_a_evidence),
            selectinload(VerificationConflict.claim_b_evidence),
        ).order_by(VerificationConflict.created_at.asc())
        return list(self.session.execute(stmt).scalars().all())

    def update_resolution(
        self,
        conflict_id: uuid.UUID,
        resolution_state: ConflictResolutionState,
        *,
        notes: str | None = None,
        resolved_by_user_id: uuid.UUID | None = None,
    ) -> VerificationConflict | None:
        conflict = self.get_by_id(conflict_id)
        if not conflict:
            return None
        conflict.resolution_state = resolution_state
        conflict.resolution_notes = notes
        conflict.resolved_by_user_id = resolved_by_user_id
        conflict.resolved_at = (
            utc_now() if resolution_state != ConflictResolutionState.UNRESOLVED else None
        )
        self.session.flush()
        return conflict


class VerificationReviewEventRepository:
    """Repository for appending and reading VerificationReviewEvent records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, event: VerificationReviewEvent) -> VerificationReviewEvent:
        self.session.add(event)
        self.session.flush()
        return event

    def list_by_case(self, case_id: uuid.UUID) -> list[VerificationReviewEvent]:
        stmt = (
            select(VerificationReviewEvent)
            .where(VerificationReviewEvent.case_id == case_id)
            .options(selectinload(VerificationReviewEvent.reviewer))
            .order_by(VerificationReviewEvent.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())


class VerificationContextRequestRepository:
    """Repository for managing VerificationContextRequest records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, req: VerificationContextRequest) -> VerificationContextRequest:
        self.session.add(req)
        self.session.flush()
        return req

    def get_by_id(self, req_id: uuid.UUID) -> VerificationContextRequest | None:
        stmt = (
            select(VerificationContextRequest)
            .where(VerificationContextRequest.id == req_id)
            .options(
                selectinload(VerificationContextRequest.requested_by),
                selectinload(VerificationContextRequest.requested_from),
                selectinload(VerificationContextRequest.response_evidence),
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_case(self, case_id: uuid.UUID) -> list[VerificationContextRequest]:
        stmt = (
            select(VerificationContextRequest)
            .where(VerificationContextRequest.case_id == case_id)
            .options(
                selectinload(VerificationContextRequest.requested_by),
                selectinload(VerificationContextRequest.requested_from),
                selectinload(VerificationContextRequest.response_evidence),
            )
            .order_by(VerificationContextRequest.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_by_user(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        status: ContextRequestStatus | None = None,
    ) -> list[VerificationContextRequest]:
        stmt = (
            select(VerificationContextRequest)
            .where(
                VerificationContextRequest.project_id == project_id,
                VerificationContextRequest.requested_from_user_id == user_id,
            )
            .options(
                selectinload(VerificationContextRequest.requested_by),
                selectinload(VerificationContextRequest.response_evidence),
            )
        )
        if status is not None:
            stmt = stmt.where(VerificationContextRequest.status == status)
        stmt = stmt.order_by(VerificationContextRequest.created_at.desc())
        return list(self.session.execute(stmt).scalars().all())

    def respond(
        self,
        req_id: uuid.UUID,
        response_text: str,
        *,
        evidence_id: uuid.UUID | None = None,
    ) -> VerificationContextRequest | None:
        req = self.get_by_id(req_id)
        if not req:
            return None
        req.response_text = response_text
        req.response_evidence_id = evidence_id
        req.status = ContextRequestStatus.RESPONDED
        req.responded_at = utc_now()
        req.updated_at = utc_now()
        self.session.flush()
        return req
