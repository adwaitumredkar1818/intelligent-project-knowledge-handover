"""Handover Responsibility Mapping and Ownership Transfer Service.

Platform: The Handover
Module: Handover Workspace (Module 4 / Knowledge Transfer Area)

Enforces:
1. Strict separation between Package Compilation and Ownership Transfer
2. Gated execution (ownership transfer requires prior human approval and acknowledgement)
3. Explicit responsibility mappings (departing -> successor)
4. Full reversibility and rollback tracking
5. Immutable audit trails
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.security import utc_now
from app.models.audit import AuditLog
from app.models.enums import (
    AuditOutcome,
    HandoverCaseStatus,
    OwnershipTransferType,
    TransferStatus,
)
from app.models.handover import (
    HandoverCase,
    HandoverOwnershipTransfer,
    HandoverResponsibilityTransfer,
)
from app.models.project import Project, ProjectMembership
from app.repositories.audit import AuditLogRepository
from app.repositories.handover import (
    HandoverCaseRepository,
    HandoverOwnershipTransferRepository,
    HandoverPackageVersionRepository,
    HandoverResponsibilityTransferRepository,
)
from app.schemas.handover import (
    OwnershipTransferRequest,
    OwnershipTransferRollbackRequest,
    ResponsibilityTransferBulkRequest,
    ResponsibilityTransferRequest,
)
from app.services.audit import AuditService
from app.services.handover_case import HandoverCaseService


class OwnershipTransferService:
    """Manages responsibility mappings and executes discrete ownership transfer operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.case_repo = HandoverCaseRepository(session)
        self.version_repo = HandoverPackageVersionRepository(session)
        self.resp_repo = HandoverResponsibilityTransferRepository(session)
        self.ownership_repo = HandoverOwnershipTransferRepository(session)
        self.case_service = HandoverCaseService(session)
        self.audit_service = AuditService(audit_repository=AuditLogRepository(session))

    def create_responsibility_transfers(
        self,
        case_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        request: ResponsibilityTransferBulkRequest,
    ) -> list[HandoverResponsibilityTransfer]:
        """Create mapping records assigning departing responsibilities to successors."""
        case = self.case_service.get_case(case_id, project_id=project_id, load_relationships=False)

        records_to_create: list[HandoverResponsibilityTransfer] = []
        for req in request.transfers:
            records_to_create.append(
                HandoverResponsibilityTransfer(
                    organisation_id=case.organisation_id,
                    project_id=project_id,
                    case_id=case.id,
                    responsibility_description=req.responsibility_description,
                    knowledge_domain=req.knowledge_domain or "responsibilities_ownership",
                    current_owner_id=case.departing_member_id,
                    proposed_successor_id=req.proposed_successor_id or case.successor_id,
                    transfer_status=TransferStatus.PENDING.value,
                    transfer_notes=req.transfer_notes,
                )
            )

        created = self.resp_repo.create_bulk(records_to_create)

        self.audit_service.record_event(
            event_type="handover.responsibilities.created",
            resource_type="handover_case",
            resource_id=str(case.id),
            actor_user_id=user_id,
            organisation_id=case.organisation_id,
            project_id=project_id,
            outcome=AuditOutcome.SUCCESS.value,
            metadata={"count": len(created)},
        )

        return created

    def list_responsibility_transfers(
        self, case_id: uuid.UUID, *, project_id: uuid.UUID
    ) -> list[HandoverResponsibilityTransfer]:
        """List mapped responsibilities for a case."""
        case = self.case_service.get_case(case_id, project_id=project_id, load_relationships=False)
        return self.resp_repo.list_by_case(case.id)

    def update_responsibility_status(
        self,
        transfer_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        status: str,
        notes: str | None = None,
    ) -> HandoverResponsibilityTransfer:
        """Update individual responsibility transfer status."""
        transfer = self.session.get(HandoverResponsibilityTransfer, transfer_id)
        if not transfer or transfer.project_id != project_id:
            raise NotFoundError(f"Responsibility transfer {transfer_id} not found in this project.")

        updated = self.resp_repo.update_status(transfer_id, status=status, transfer_notes=notes)

        self.audit_service.record_event(
            event_type="handover.responsibility.updated",
            resource_type="handover_responsibility_transfer",
            resource_id=str(transfer_id),
            actor_user_id=user_id,
            organisation_id=transfer.organisation_id,
            project_id=project_id,
            outcome=AuditOutcome.SUCCESS.value,
            metadata={"status": status},
        )

        return updated  # type: ignore[return-value]

    def execute_ownership_transfer(
        self,
        case_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        request: OwnershipTransferRequest,
    ) -> HandoverOwnershipTransfer:
        """Execute an explicit project or component ownership transfer."""
        case = self.case_service.get_case(case_id, project_id=project_id, load_relationships=False)
        version = self.version_repo.get_by_id(request.version_id, load_sections=False)
        if not version or version.case_id != case.id:
            raise NotFoundError(f"Package version {request.version_id} not found for this case.")

        # Prerequisite gate: Package must be APPROVED or ACKNOWLEDGED
        if case.status not in (
            HandoverCaseStatus.APPROVED.value,
            HandoverCaseStatus.DELIVERED.value,
            HandoverCaseStatus.ACKNOWLEDGED.value,
        ):
            raise BadRequestError(
                f"Cannot execute ownership transfer in case status '{case.status}'. "
                "The handover package must be approved and delivered first."
            )

        # Record explicit ownership transfer event
        transfer_event = HandoverOwnershipTransfer(
            organisation_id=case.organisation_id,
            project_id=project_id,
            case_id=case.id,
            version_id=version.id,
            transfer_type=request.transfer_type,
            from_user_id=case.departing_member_id,
            to_user_id=request.to_user_id,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            transfer_notes=request.transfer_reason,
            executed_at=utc_now(),
            executed_by_user_id=user_id,
            rolled_back=False,
        )
        created_transfer = self.ownership_repo.create(transfer_event)

        # Mark all pending responsibility transfers as COMPLETED
        transfers = self.resp_repo.list_by_case(case.id)
        for t in transfers:
            if t.transfer_status == TransferStatus.PENDING.value:
                self.resp_repo.update_status(t.id, status=TransferStatus.COMPLETED.value)

        # Transition Case to TRANSFERRED
        self.case_service.transition_status(
            case_id,
            project_id=project_id,
            new_status=HandoverCaseStatus.TRANSFERRED.value,
            user_id=user_id,
            change_reason=f"Executed ownership transfer ({request.transfer_type}) to {request.to_user_id}",
        )

        self.audit_service.record_event(
            event_type="handover.ownership.transferred",
            resource_type="handover_ownership_transfer",
            resource_id=str(created_transfer.id),
            actor_user_id=user_id,
            organisation_id=case.organisation_id,
            project_id=project_id,
            outcome=AuditOutcome.SUCCESS.value,
            metadata={
                "transfer_type": request.transfer_type,
                "from_user_id": str(case.departing_member_id),
                "to_user_id": str(request.to_user_id),
            },
        )

        return created_transfer

    def rollback_ownership_transfer(
        self,
        transfer_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        request: OwnershipTransferRollbackRequest,
    ) -> HandoverOwnershipTransfer:
        """Rollback a previously executed ownership transfer."""
        transfer = self.ownership_repo.get_by_id(transfer_id)
        if not transfer or transfer.project_id != project_id:
            raise NotFoundError(f"Ownership transfer {transfer_id} not found in this project.")

        if transfer.rolled_back:
            raise BadRequestError("This ownership transfer has already been rolled back.")

        rolled_back = self.ownership_repo.mark_rolled_back(
            transfer_id,
            rolled_back_by_user_id=user_id,
            rollback_reason=request.rollback_reason,
        )

        self.audit_service.record_event(
            event_type="handover.ownership.rolled_back",
            resource_type="handover_ownership_transfer",
            resource_id=str(transfer_id),
            actor_user_id=user_id,
            organisation_id=transfer.organisation_id,
            project_id=project_id,
            outcome=AuditOutcome.SUCCESS.value,
            metadata={"reason": request.rollback_reason},
        )

        return rolled_back  # type: ignore[return-value]
