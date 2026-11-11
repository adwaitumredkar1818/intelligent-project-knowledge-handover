"""Repository operations for platform user accounts."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import UserStatus
from app.models.rbac import UserRole
from app.models.user import User


class UserRepository:
    """Data-access operations for `users`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        )
        return self._session.scalar(stmt)

    def get_by_email(self, normalised_email: str) -> User | None:
        stmt = (
            select(User)
            .where(User.email == normalised_email)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        )
        return self._session.scalar(stmt)

    def list_users(self, *, limit: int = 50, offset: int = 0) -> list[User]:
        stmt = (
            select(User)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .order_by(User.created_at.desc(), User.id.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())

    def count_users(self) -> int:
        stmt = select(func.count(User.id))
        return int(self._session.scalar(stmt) or 0)

    def create(
        self,
        *,
        full_name: str,
        email: str,
        password_hash: str,
        status: str = UserStatus.ACTIVE.value,
    ) -> User:
        user = User(
            full_name=full_name,
            email=email,
            password_hash=password_hash,
            status=status,
            is_email_verified=False,
        )
        self._session.add(user)
        self._session.flush()
        return user

    def update_last_login(self, user: User, login_at: datetime) -> None:
        user.last_login_at = login_at
        self._session.flush()

    def update_status(self, user: User, status: str) -> None:
        user.status = status
        self._session.flush()
