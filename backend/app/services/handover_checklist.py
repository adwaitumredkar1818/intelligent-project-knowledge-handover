"""Handover Checklist Management Service.

Platform: The Handover
Module: Handover Workspace (Module 4 / Knowledge Transfer Area)

Enforces:
1. Dynamic checklist generation based on readiness gaps and offboarding standards
2. Item-level tracking (pending, in_progress, completed, skipped, blocked)
3. Blocking item enforcement before final approval
4. Full audit logging of checklist progress
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.security import utc_now
from app.models.audit import AuditLog
from app.models.enums import (
    AuditOutcome,
    ChecklistItemStatus,
    HandoverChecklistType,
)
from app.models.handover import HandoverChecklist, HandoverChecklistItem
from app.repositories.audit import AuditLogRepository
from app.repositories.handover import (
    HandoverCaseRepository,
    HandoverChecklistRepository,
)
from app.schemas.handover import ChecklistItemUpdateRequest
from app.services.audit import AuditService


STANDARD_CHECKLIST_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    HandoverChecklistType.PRE_HANDOVER.value: [
        {
            "item_text": "Verify all critical architecture decisions have supporting evidence and rationale",
            "category": "architecture",
            "blocking": True,
            "sort_order": 1,
        },
        {
            "item_text": "Review active bugs, blockers, and open risks with project team",
            "category": "risks",
            "blocking": True,
            "sort_order": 2,
        },
        {
            "item_text": "Ensure departing member responsibilities have designated successors",
            "category": "ownership",
            "blocking": True,
            "sort_order": 3,
        },
        {
            "item_text": "Verify that all connected repositories and Jira boards are up-to-date",
            "category": "evidence",
            "blocking": False,
            "sort_order": 4,
        },
    ],
    HandoverChecklistType.KNOWLEDGE_TRANSFER.value: [
        {
            "item_text": "Conduct deep-dive architecture walkthrough session with successor",
            "category": "knowledge_transfer",
            "blocking": True,
            "sort_order": 1,
        },
        {
            "item_text": "Review deployment pipelines, secrets management, and operational runbooks",
            "category": "operations",
            "blocking": True,
            "sort_order": 2,
        },
        {
            "item_text": "Successor completes dry-run execution of common operational workflows",
            "category": "verification",
            "blocking": False,
            "sort_order": 3,
        },
    ],
    HandoverChecklistType.ACCESS_REVOCATION.value: [
        {
            "item_text": "Audit external source access (GitHub, Jira, Slack) for departing member",
            "category": "security",
            "blocking": True,
            "sort_order": 1,
        },
        {
            "item_text": "Rotate shared API credentials, service accounts, and production secrets",
            "category": "security",
            "blocking": True,
            "sort_order": 2,
        },
        {
            "item_text": "Confirm project membership role transition or account deactivation",
            "category": "governance",
            "blocking": False,
            "sort_order": 3,
        },
    ],
}


class ChecklistService:
    """Domain service for generating and managing handover checklists."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.case_repo = HandoverCaseRepository(session)
        self.checklist_repo = HandoverChecklistRepository(session)
        self.audit_service = AuditService(audit_repository=AuditLogRepository(session))

    def generate_checklists_for_case(
        self,
        case_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        version_id: uuid.UUID | None = None,
        readiness_blockers: list[str] | None = None,
    ) -> list[HandoverChecklist]:
        """Generate standard pre-handover, knowledge-transfer, and access checklists."""
        case = self.case_repo.get_by_id(case_id, load_relationships=False)
        if not case or case.project_id != project_id:
            raise NotFoundError(f"Handover case {case_id} not found in this project.")

        created_checklists: list[HandoverChecklist] = []

        for chk_type, items_meta in STANDARD_CHECKLIST_TEMPLATES.items():
            title = f"{chk_type.replace('_', ' ').title()} Checklist"
            checklist = HandoverChecklist(
                organisation_id=case.organisation_id,
                project_id=project_id,
                case_id=case.id,
                version_id=version_id,
                checklist_type=chk_type,
                title=title,
                total_items=len(items_meta),
                completed_items=0,
                is_completed=False,
            )
            created_chk = self.checklist_repo.create(checklist)

            items_to_add: list[HandoverChecklistItem] = []
            for item in items_meta:
                items_to_add.append(
                    HandoverChecklistItem(
                        organisation_id=case.organisation_id,
                        project_id=project_id,
                        checklist_id=created_chk.id,
                        item_text=item["item_text"],
                        category=item["category"],
                        status=ChecklistItemStatus.PENDING.value,
                        blocking=item["blocking"],
                        sort_order=item["sort_order"],
                        assigned_to_user_id=case.departing_member_id if "departing" in item["item_text"] else case.successor_id,
                    )
                )

            # If this is pre-handover and we have readiness blockers, add specific remediation items
            if chk_type == HandoverChecklistType.PRE_HANDOVER.value and readiness_blockers:
                for idx, blocker in enumerate(readiness_blockers, start=len(items_to_add) + 1):
                    items_to_add.append(
                        HandoverChecklistItem(
                            organisation_id=case.organisation_id,
                            project_id=project_id,
                            checklist_id=created_chk.id,
                            item_text=f"Resolve Blocker: {blocker}",
                            category="remediation",
                            status=ChecklistItemStatus.PENDING.value,
                            blocking=True,
                            sort_order=idx,
                        )
                    )
                created_chk.total_items = len(items_to_add)

            self.checklist_repo.create_items_bulk(items_to_add)
            created_checklists.append(created_chk)

        self.audit_service.record_event(
            event_type="handover.checklists.generated",
            resource_type="handover_case",
            resource_id=str(case.id),
            actor_user_id=user_id,
            organisation_id=case.organisation_id,
            project_id=project_id,
            outcome=AuditOutcome.SUCCESS.value,
            metadata={"checklists_count": len(created_checklists)},
        )

        return created_checklists

    def update_item_status(
        self,
        item_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        request: ChecklistItemUpdateRequest,
    ) -> HandoverChecklistItem:
        """Update checklist item completion status."""
        item = self.checklist_repo.get_item_by_id(item_id)
        if not item or item.project_id != project_id:
            raise NotFoundError(f"Checklist item {item_id} not found in this project.")

        updated = self.checklist_repo.update_item_status(
            item_id,
            status=request.status,
            completed_by_user_id=user_id if request.status == ChecklistItemStatus.COMPLETED.value else None,
            notes=request.notes,
        )

        self.audit_service.record_event(
            event_type="handover.checklist_item.updated",
            resource_type="handover_checklist_item",
            resource_id=str(item.id),
            actor_user_id=user_id,
            organisation_id=item.organisation_id,
            project_id=project_id,
            outcome=AuditOutcome.SUCCESS.value,
            metadata={"status": request.status},
        )

        return updated  # type: ignore[return-value]

    def list_checklists(
        self, case_id: uuid.UUID, *, project_id: uuid.UUID
    ) -> list[HandoverChecklist]:
        """List all checklists and items for a case."""
        case = self.case_repo.get_by_id(case_id, load_relationships=False)
        if not case or case.project_id != project_id:
            raise NotFoundError(f"Handover case {case_id} not found in this project.")
        return self.checklist_repo.list_by_case(case_id)
