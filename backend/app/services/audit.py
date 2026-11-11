"""Backend-trusted audit trail service with strict secret sanitisation."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.core.logging import get_correlation_id, log_security_event, redact_sensitive_text
from app.models.audit import AuditLog
from app.models.enums import AuditOutcome
from app.repositories.audit import AuditLogRepository
from app.schemas.organisation import AuditLogEntryResponse, AuditLogListResponse

_SENSITIVE_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "raw_token",
        "token_hash",
        "refresh_token",
        "access_token",
        "invitation_token",
        "development_invitation_token",
        "secret",
        "jwt_secret_key",
        "cookie",
        "set-cookie",
        "authorization",
        "api_key",
    }
)


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, inner in value.items():
            key_str = str(key)
            if key_str.strip().lower() in _SENSITIVE_METADATA_KEYS:
                sanitized[key_str] = "[REDACTED]"
            else:
                sanitized[key_str] = _sanitize_value(inner)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def sanitize_audit_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    """Scrub secret keys and credential patterns before persisting metadata in `audit_logs`."""
    if not metadata:
        return None
    sanitized = _sanitize_value(metadata)
    return sanitized if isinstance(sanitized, dict) and sanitized else None


def to_audit_entry_response(entry: AuditLog) -> AuditLogEntryResponse:
    """Convert an AuditLog ORM entity into a safe API response schema."""
    return AuditLogEntryResponse(
        id=entry.id,
        actor_user_id=entry.actor_user_id,
        organisation_id=entry.organisation_id,
        project_id=entry.project_id,
        event_type=entry.event_type,
        resource_type=entry.resource_type,
        resource_id=entry.resource_id,
        outcome=entry.outcome,
        request_id=entry.request_id,
        event_metadata=entry.event_metadata,
        created_at=entry.created_at,
    )


class AuditService:
    """Persists backend-generated organisational audit events and emits structured logs."""

    def __init__(self, *, audit_repository: AuditLogRepository) -> None:
        self._audit_repo = audit_repository

    def record_event(
        self,
        *,
        event_type: str,
        resource_type: str,
        actor_user_id: uuid.UUID | None,
        organisation_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        resource_id: str | None = None,
        outcome: str = AuditOutcome.SUCCESS.value,
        metadata: dict[str, Any] | None = None,
        message: str | None = None,
        level: int = logging.INFO,
    ) -> AuditLog:
        """Append an immutable audit record in the caller's DB unit of work."""
        correlation_id = get_correlation_id()
        safe_metadata = sanitize_audit_metadata(metadata)
        entry = self._audit_repo.create(
            actor_user_id=actor_user_id,
            organisation_id=organisation_id,
            project_id=project_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            request_id=None if correlation_id == "-" else correlation_id,
            event_metadata=safe_metadata,
        )
        log_security_event(
            event_type=event_type,
            outcome=outcome,
            actor_user_id=str(actor_user_id) if actor_user_id is not None else None,
            organisation_id=str(organisation_id) if organisation_id is not None else None,
            project_id=str(project_id) if project_id is not None else None,
            message=message or f"{event_type} on {resource_type} ({outcome}).",
            level=level,
        )
        return entry

    def list_organisation_events(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AuditLogListResponse:
        """Return paginated audit log entries scoped strictly to one organisation."""
        rows, total = self._audit_repo.list_for_organisation(
            organisation_id=organisation_id,
            project_id=project_id,
            event_type=event_type,
            limit=limit,
            offset=offset,
        )
        return AuditLogListResponse(
            items=[to_audit_entry_response(row) for row in rows],
            total=total,
        )
