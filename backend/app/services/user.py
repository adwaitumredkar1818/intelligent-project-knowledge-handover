"""Platform user identity management service enforcing RBAC and user isolation."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.logging import log_security_event
from app.core.security import utc_now
from app.models.enums import RevocationReason, UserStatus
from app.repositories.auth import RefreshSessionRepository
from app.repositories.user import UserRepository
from app.schemas.user import UpdateUserStatusRequest, UserListResponse, UserSummaryResponse
from app.services.auth import build_user_summary
from app.services.rbac import AuthenticatedPrincipal, RbacService


class UserService:
    """Identity management operations with strict permission and isolation boundaries."""

    def __init__(
        self,
        *,
        db_session: Session,
        user_repository: UserRepository,
        refresh_repository: RefreshSessionRepository,
        rbac_service: RbacService,
    ) -> None:
        self._db = db_session
        self._user_repo = user_repository
        self._refresh_repo = refresh_repository
        self._rbac_service = rbac_service

    def get_user_profile(
        self,
        *,
        target_user_id: uuid.UUID,
        acting_principal: AuthenticatedPrincipal,
    ) -> UserSummaryResponse:
        """Enforce self-read (`account.profile.read`) vs cross-user read (`platform.users.read`)."""
        if target_user_id == acting_principal.user.id:
            self._rbac_service.require_permissions(
                acting_principal,
                ("account.profile.read",),
            )
        else:
            self._rbac_service.require_permissions(
                acting_principal,
                ("platform.users.read",),
            )

        user = self._user_repo.get_by_id(target_user_id)
        if user is None:
            raise NotFoundError("User account was not found.", code="USER_NOT_FOUND")
        return build_user_summary(user)

    def list_users(self, *, limit: int = 50, offset: int = 0) -> UserListResponse:
        """List platform user accounts cleanly."""
        users = self._user_repo.list_users(limit=limit, offset=offset)
        total = self._user_repo.count_users()
        return UserListResponse(
            items=[build_user_summary(u) for u in users],
            total=total,
        )

    def update_user_status(
        self,
        *,
        target_user_id: uuid.UUID,
        payload: UpdateUserStatusRequest,
        acting_principal: AuthenticatedPrincipal,
    ) -> UserSummaryResponse:
        """Update user lifecycle status and revoke active sessions if deactivated."""
        if (
            target_user_id == acting_principal.user.id
            and payload.status != UserStatus.ACTIVE.value
        ):
            raise BadRequestError(
                "You cannot deactivate or lock your own account.",
                code="SELF_STATUS_CHANGE_FORBIDDEN",
            )

        user = self._user_repo.get_by_id(target_user_id)
        if user is None:
            raise NotFoundError("User account was not found.", code="USER_NOT_FOUND")

        self._user_repo.update_status(user, payload.status)
        if payload.status != UserStatus.ACTIVE.value:
            self._refresh_repo.revoke_all_for_user(
                user_id=user.id,
                reason=RevocationReason.USER_DISABLED.value,
                now=utc_now(),
            )

        self._db.commit()
        refreshed = self._user_repo.get_by_id(user.id) or user

        log_security_event(
            event_type="user.status_updated",
            outcome="success",
            actor_user_id=str(acting_principal.user.id),
            message=f"Updated account '{refreshed.id}' status to '{refreshed.status}'.",
        )
        return build_user_summary(refreshed)
