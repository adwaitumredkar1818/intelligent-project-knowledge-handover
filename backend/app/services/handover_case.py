"""Handover Case Management Service.

Platform: The Handover
Module: Handover Workspace (Module 4 / Knowledge Transfer Area)

Enforces:
1. Multi-tenant project boundary validation
2. Optimistic concurrency control (via case.version increments)
3. Strict 14-state lifecycle state machine
4. Immutable HandoverStatusHistory audit trail
5. System audit log generation
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import utc_now
from app.models.audit import AuditLog
from app.models.enums import AuditOutcome, HandoverCaseStatus
from app.models.handover import HandoverCase, HandoverStatusHistory
from app.repositories.audit import AuditLogRepository
from app.repositories.handover import (
    HandoverCaseRepository,
    HandoverStatusHistoryRepository,
)
from app.schemas.handover import (
    HandoverCaseCreateRequest,
    HandoverCaseUpdateRequest,
)
from app.services.audit import AuditService

# Allowed lifecycle state transitions
VALID_TRANSITIONS: dict[str, set[str]] = {
    HandoverCaseStatus.DRAFT.value: {
        HandoverCaseStatus.ASSEMBLING.value,
        HandoverCaseStatus.ARCHIVED.value,
    },
    HandoverCaseStatus.ASSEMBLING.value: {
        HandoverCaseStatus.ASSEMBLED.value,
        HandoverCaseStatus.DRAFT.value,
        HandoverCaseStatus.ARCHIVED.value,
    },
    HandoverCaseStatus.ASSEMBLED.value: {
        HandoverCaseStatus.READINESS_PENDING.value,
        HandoverCaseStatus.READINESS_ASSESSED.value,
        HandoverCaseStatus.ASSEMBLING.value,
        HandoverCaseStatus.DRAFT.value,
        HandoverCaseStatus.ARCHIVED.value,
        HandoverCaseStatus.SUPERSEDED.value,
    },
    HandoverCaseStatus.READINESS_PENDING.value: {
        HandoverCaseStatus.READINESS_ASSESSED.value,
        HandoverCaseStatus.ASSEMBLED.value,
        HandoverCaseStatus.ARCHIVED.value,
    },
    HandoverCaseStatus.READINESS_ASSESSED.value: {
        HandoverCaseStatus.REVIEW_PENDING.value,
        HandoverCaseStatus.READINESS_PENDING.value,
        HandoverCaseStatus.ASSEMBLED.value,
        HandoverCaseStatus.DRAFT.value,
        HandoverCaseStatus.ARCHIVED.value,
    },
    HandoverCaseStatus.REVIEW_PENDING.value: {
        HandoverCaseStatus.UNDER_REVIEW.value,
        HandoverCaseStatus.APPROVED.value,
        HandoverCaseStatus.REJECTED.value,
        HandoverCaseStatus.READINESS_ASSESSED.value,
        HandoverCaseStatus.ARCHIVED.value,
    },
    HandoverCaseStatus.UNDER_REVIEW.value: {
        HandoverCaseStatus.APPROVED.value,
        HandoverCaseStatus.REJECTED.value,
        HandoverCaseStatus.REVIEW_PENDING.value,
        HandoverCaseStatus.READINESS_ASSESSED.value,
        HandoverCaseStatus.ARCHIVED.value,
    },
    HandoverCaseStatus.APPROVED.value: {
        HandoverCaseStatus.DELIVERED.value,
        HandoverCaseStatus.UNDER_REVIEW.value,
        HandoverCaseStatus.ARCHIVED.value,
        HandoverCaseStatus.SUPERSEDED.value,
    },
    HandoverCaseStatus.REJECTED.value: {
        HandoverCaseStatus.DRAFT.value,
        HandoverCaseStatus.ASSEMBLED.value,
        HandoverCaseStatus.REVIEW_PENDING.value,
        HandoverCaseStatus.ARCHIVED.value,
    },
    HandoverCaseStatus.DELIVERED.value: {
        HandoverCaseStatus.ACKNOWLEDGED.value,
        HandoverCaseStatus.ARCHIVED.value,
        HandoverCaseStatus.SUPERSEDED.value,
    },
    HandoverCaseStatus.ACKNOWLEDGED.value: {
        HandoverCaseStatus.TRANSFERRED.value,
        HandoverCaseStatus.ARCHIVED.value,
    },
    HandoverCaseStatus.TRANSFERRED.value: {
        HandoverCaseStatus.ARCHIVED.value,
    },
    HandoverCaseStatus.ARCHIVED.value: {
        HandoverCaseStatus.DRAFT.value,  # unarchive
    },
    HandoverCaseStatus.SUPERSEDED.value: {
        HandoverCaseStatus.ARCHIVED.value,
    },
}


class HandoverCaseService:
    """Domain service managing the HandoverCase lifecycle."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.case_repo = HandoverCaseRepository(session)
        self.history_repo = HandoverStatusHistoryRepository(session)
        self.audit_service = AuditService(
            audit_repository=AuditLogRepository(session)
        )

    def create_case(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        request: HandoverCaseCreateRequest,
    ) -> HandoverCase:
        """Create a new HandoverCase in DRAFT status."""
        case = HandoverCase(
            organisation_id=organisation_id,
            project_id=project_id,
            title=request.title,
            description=request.description,
            status=HandoverCaseStatus.DRAFT.value,
            departing_member_id=request.departing_member_id,
            successor_id=request.successor_id,
            created_by_user_id=user_id,
            metadata_json=request.metadata_json or {},
            version=1,
        )
        created_case = self.case_repo.create(case)

        # Record initial status in history
        self.history_repo.create(
            HandoverStatusHistory(
                organisation_id=organisation_id,
                project_id=project_id,
                case_id=created_case.id,
                previous_status="none",
                new_status=HandoverCaseStatus.DRAFT.value,
                changed_by_user_id=user_id,
                change_reason="Handover case created",
            )
        )

        self.audit_service.record_event(
            event_type="handover.case.created",
            resource_type="handover_case",
            resource_id=str(created_case.id),
            actor_user_id=user_id,
            organisation_id=organisation_id,
            project_id=project_id,
            outcome=AuditOutcome.SUCCESS.value,
            metadata={"title": request.title, "departing_member_id": str(request.departing_member_id)},
        )

        return created_case

    def get_case(
        self,
        case_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        load_relationships: bool = True,
    ) -> HandoverCase:
        """Retrieve a HandoverCase ensuring project boundary isolation."""
        case = self.case_repo.get_by_id(case_id, load_relationships=load_relationships)
        if not case or case.project_id != project_id:
            raise NotFoundError(f"Handover case {case_id} not found in this project.")
        return case

    def list_cases(
        self,
        *,
        project_id: uuid.UUID,
        status: str | None = None,
        departing_member_id: uuid.UUID | None = None,
        successor_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[HandoverCase], int]:
        """List cases with filtering and pagination."""
        return self.case_repo.list_by_project(
            project_id=project_id,
            status=status,
            departing_member_id=departing_member_id,
            successor_id=successor_id,
            offset=offset,
            limit=limit,
        )

    def update_case(
        self,
        case_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        request: HandoverCaseUpdateRequest,
    ) -> HandoverCase:
        """Update mutable fields of a HandoverCase."""
        case = self.get_case(case_id, project_id=project_id, load_relationships=False)
        if case.status in (
            HandoverCaseStatus.APPROVED.value,
            HandoverCaseStatus.DELIVERED.value,
            HandoverCaseStatus.TRANSFERRED.value,
            HandoverCaseStatus.ARCHIVED.value,
        ):
            raise BadRequestError(
                f"Cannot update case in locked status '{case.status}'."
            )

        if request.title is not None:
            case.title = request.title
        if request.description is not None:
            case.description = request.description
        if request.successor_id is not None:
            case.successor_id = request.successor_id
        if request.metadata_json is not None:
            case.metadata_json = request.metadata_json

        case.version += 1
        case.updated_at = utc_now()
        self.session.flush()

        self.audit_service.record_event(
            event_type="handover.case.updated",
            resource_type="handover_case",
            resource_id=str(case.id),
            actor_user_id=user_id,
            organisation_id=case.organisation_id,
            project_id=project_id,
            outcome=AuditOutcome.SUCCESS.value,
        )

        return case

    def transition_status(
        self,
        case_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        new_status: str,
        user_id: uuid.UUID,
        change_reason: str | None = None,
        expected_version: int | None = None,
    ) -> HandoverCase:
        """Execute a state machine transition with audit and concurrency checks."""
        case = self.get_case(case_id, project_id=project_id, load_relationships=False)

        current_status = case.status
        allowed_next = VALID_TRANSITIONS.get(current_status, set())
        if new_status not in allowed_next:
            raise BadRequestError(
                f"Invalid status transition from '{current_status}' to '{new_status}'. "
                f"Allowed transitions: {sorted(allowed_next)}"
            )

        if expected_version is not None and case.version != expected_version:
            raise ConflictError(
                f"Concurrency conflict: Case version is {case.version}, expected {expected_version}."
            )

        case.status = new_status
        case.version += 1
        case.updated_at = utc_now()

        # Record history
        self.history_repo.create(
            HandoverStatusHistory(
                organisation_id=case.organisation_id,
                project_id=project_id,
                case_id=case.id,
                previous_status=current_status,
                new_status=new_status,
                changed_by_user_id=user_id,
                change_reason=change_reason,
            )
        )

        self.audit_service.record_event(
            event_type="handover.case.status_changed",
            resource_type="handover_case",
            resource_id=str(case.id),
            actor_user_id=user_id,
            organisation_id=case.organisation_id,
            project_id=project_id,
            outcome=AuditOutcome.SUCCESS.value,
            metadata={
                "previous_status": current_status,
                "new_status": new_status,
                "reason": change_reason,
            },
        )

        self.session.flush()
        return case
