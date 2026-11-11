"""Repository operations for immutable backend audit logs."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditOutcome


class AuditLogRepository:
    """Append-only data-access operations for `audit_logs`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        actor_user_id: uuid.UUID | None,
        organisation_id: uuid.UUID | None,
        project_id: uuid.UUID | None,
        event_type: str,
        resource_type: str,
        resource_id: str | None,
        outcome: str = AuditOutcome.SUCCESS.value,
        request_id: str | None = None,
        event_metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_user_id=actor_user_id,
            organisation_id=organisation_id,
            project_id=project_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            request_id=request_id,
            event_metadata=event_metadata,
        )
        self._session.add(entry)
        self._session.flush()
        return entry

    def list_for_organisation(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        base = select(AuditLog).where(AuditLog.organisation_id == organisation_id)
        if project_id is not None:
            base = base.where(AuditLog.project_id == project_id)
        if event_type is not None:
            base = base.where(AuditLog.event_type == event_type)

        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        stmt = (
            base.order_by(AuditLog.created_at.desc(), AuditLog.id.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all()), total
