"""Repository operations for PostgreSQL-backed refresh sessions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, selectinload

from app.models.auth import RefreshSession


class RefreshSessionRepository:
    """Data-access operations for `refresh_sessions`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        user_id: uuid.UUID,
        token_family_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        session_metadata: dict[str, str] | None = None,
    ) -> RefreshSession:
        record = RefreshSession(
            user_id=user_id,
            token_family_id=token_family_id,
            token_hash=token_hash,
            expires_at=expires_at,
            session_metadata=session_metadata,
        )
        self._session.add(record)
        self._session.flush()
        return record

    def get_by_token_hash_for_update(self, token_hash: str) -> RefreshSession | None:
        stmt = (
            select(RefreshSession)
            .where(RefreshSession.token_hash == token_hash)
            .options(selectinload(RefreshSession.user))
            .with_for_update()
        )
        return self._session.scalar(stmt)

    def get_by_id_for_user(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> RefreshSession | None:
        stmt = select(RefreshSession).where(
            RefreshSession.id == session_id,
            RefreshSession.user_id == user_id,
        )
        return self._session.scalar(stmt)

    def is_family_active(
        self,
        *,
        token_family_id: uuid.UUID,
        user_id: uuid.UUID,
        now: datetime,
    ) -> bool:
        stmt = (
            select(RefreshSession.id)
            .where(
                RefreshSession.token_family_id == token_family_id,
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
                RefreshSession.expires_at > now,
            )
            .limit(1)
        )
        return self._session.scalar(stmt) is not None

    def mark_rotated(
        self,
        *,
        session_record: RefreshSession,
        replaced_by_id: uuid.UUID,
        reason: str,
        now: datetime,
    ) -> None:
        session_record.revoked_at = now
        session_record.last_used_at = now
        session_record.revoked_reason = reason
        session_record.replaced_by_session_id = replaced_by_id
        self._session.flush()

    def revoke_family(
        self,
        *,
        token_family_id: uuid.UUID,
        reason: str,
        now: datetime,
    ) -> int:
        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.token_family_id == token_family_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=now, revoked_reason=reason)
        )
        result = cast(CursorResult[Any], self._session.execute(stmt))
        self._session.flush()
        return int(result.rowcount or 0)

    def revoke_all_for_user(
        self,
        *,
        user_id: uuid.UUID,
        reason: str,
        now: datetime,
    ) -> int:
        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=now, revoked_reason=reason)
        )
        result = cast(CursorResult[Any], self._session.execute(stmt))
        self._session.flush()
        return int(result.rowcount or 0)

    def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        include_revoked: bool = False,
        limit: int = 50,
    ) -> list[RefreshSession]:
        stmt = select(RefreshSession).where(RefreshSession.user_id == user_id)
        if not include_revoked:
            stmt = stmt.where(RefreshSession.revoked_at.is_(None))
        stmt = stmt.order_by(RefreshSession.created_at.desc()).limit(limit)
        return list(self._session.scalars(stmt).all())
