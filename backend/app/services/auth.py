"""Platform authentication, Argon2id password, JWT, and rotated refresh session service."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from app.core.logging import log_security_event
from app.core.security import (
    create_access_token,
    ensure_utc,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    utc_now,
    verify_dummy_password,
    verify_password,
)
from app.models.enums import RevocationReason, RoleName, RoleScopeType, UserStatus
from app.models.user import User
from app.repositories.auth import RefreshSessionRepository
from app.repositories.rbac import RbacRepository
from app.repositories.user import UserRepository
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    LogoutResponse,
    RefreshSessionSummary,
    RegisterRequest,
    RegisterResponse,
    RevokeSessionResponse,
    SessionListResponse,
)
from app.schemas.user import AuthenticatedUserResponse, UserSummaryResponse
from app.services.rbac import AuthenticatedPrincipal


def build_user_summary(user: User, roles: list[str] | None = None) -> UserSummaryResponse:
    """Map User ORM entity to safe UserSummaryResponse without secret fields."""
    if roles is None:
        resolved_roles = sorted(
            ur.role.name
            for ur in user.user_roles
            if ur.role is not None and ur.role.scope_type == RoleScopeType.PLATFORM.value
        )
    else:
        resolved_roles = sorted(roles)
    return UserSummaryResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        status=user.status,
        is_email_verified=user.is_email_verified,
        email_verified_at=user.email_verified_at,
        roles=resolved_roles,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
    )


def build_authenticated_user(
    user: User,
    *,
    roles: list[str] | tuple[str, ...],
    permissions: frozenset[str] | list[str],
) -> AuthenticatedUserResponse:
    """Build AuthenticatedUserResponse including platform roles and permissions."""
    return AuthenticatedUserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        status=user.status,
        is_email_verified=user.is_email_verified,
        email_verified_at=user.email_verified_at,
        roles=sorted(roles),
        permissions=sorted(permissions),
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
    )


class AuthService:
    """Service orchestrating FastAPI-managed registration, login, rotation, and sessions."""

    def __init__(
        self,
        *,
        settings: Settings,
        db_session: Session,
        user_repository: UserRepository,
        refresh_repository: RefreshSessionRepository,
        rbac_repository: RbacRepository,
    ) -> None:
        self._settings = settings
        self._db = db_session
        self._user_repo = user_repository
        self._refresh_repo = refresh_repository
        self._rbac_repo = rbac_repository

    def register(self, payload: RegisterRequest) -> RegisterResponse:
        """Create a new platform account with Argon2id password hash and default role."""
        if self._user_repo.get_by_email(payload.email) is not None:
            log_security_event(
                event_type="auth.register",
                outcome="denied",
                message="Rejected duplicate account registration attempt.",
            )
            raise ConflictError(
                "An account with this email address already exists.",
                code="ACCOUNT_ALREADY_EXISTS",
            )

        default_role = self._rbac_repo.get_role_by_name(RoleName.STANDARD_USER.value)
        if default_role is None:
            raise ServiceUnavailableError(
                "Platform role catalog is not initialised.",
                code="RBAC_CATALOG_NOT_READY",
            )

        password_digest = hash_password(payload.password)
        try:
            user = self._user_repo.create(
                full_name=payload.full_name,
                email=payload.email,
                password_hash=password_digest,
                status=UserStatus.ACTIVE.value,
            )
            self._rbac_repo.assign_role(
                user_id=user.id,
                role_id=default_role.id,
                assigned_by_id=None,
            )
            self._db.commit()
            self._db.refresh(user)
        except IntegrityError as exc:
            self._db.rollback()
            raise ConflictError(
                "An account with this email address already exists.",
                code="ACCOUNT_ALREADY_EXISTS",
            ) from exc

        log_security_event(
            event_type="auth.register",
            outcome="success",
            actor_user_id=str(user.id),
            message="Registered new platform account with default standard_user role.",
        )
        return RegisterResponse(
            user=build_user_summary(user, roles=[default_role.name]),
            email_verification_required=True,
            email_verification_delivery="not_configured",
            message=(
                "Account registered. Email verification delivery is not yet configured "
                "in this environment."
            ),
        )

    def login(
        self,
        *,
        payload: LoginRequest,
        session_metadata: dict[str, str] | None = None,
    ) -> tuple[AccessTokenResponse, str]:
        """Authenticate credentials cleanly and start a new refresh token family."""
        user = self._user_repo.get_by_email(payload.email)
        if user is None:
            verify_dummy_password(payload.password)
            log_security_event(
                event_type="auth.login",
                outcome="denied",
                message="Rejected login due to invalid credentials.",
            )
            raise UnauthorizedError(
                "Invalid email or password.",
                code="INVALID_CREDENTIALS",
            )

        if not verify_password(payload.password, user.password_hash):
            log_security_event(
                event_type="auth.login",
                outcome="denied",
                actor_user_id=str(user.id),
                message="Rejected login due to invalid credentials.",
            )
            raise UnauthorizedError(
                "Invalid email or password.",
                code="INVALID_CREDENTIALS",
            )

        if user.status != UserStatus.ACTIVE.value:
            log_security_event(
                event_type="auth.login",
                outcome="denied",
                actor_user_id=str(user.id),
                message=f"Rejected login for non-active user status '{user.status}'.",
                level=logging.WARNING,
            )
            raise UnauthorizedError(
                "Invalid email or password.",
                code="INVALID_CREDENTIALS",
            )

        now = utc_now()
        token_family_id = uuid.uuid4()
        raw_refresh_token = generate_refresh_token()
        token_hash = hash_refresh_token(raw_refresh_token)
        expires_at = now + timedelta(days=self._settings.security.jwt_refresh_token_expire_days)

        self._refresh_repo.create(
            user_id=user.id,
            token_family_id=token_family_id,
            token_hash=token_hash,
            expires_at=expires_at,
            session_metadata=session_metadata,
        )
        self._user_repo.update_last_login(user, now)
        roles, permissions = self._rbac_repo.get_user_platform_roles_and_permissions(user.id)
        access_token, expires_in = create_access_token(
            user_id=user.id,
            session_family_id=token_family_id,
            settings=self._settings,
            now=now,
        )
        self._db.commit()
        self._db.refresh(user)

        log_security_event(
            event_type="auth.login",
            outcome="success",
            actor_user_id=str(user.id),
            message="Authenticated platform user and created refresh session family.",
        )
        return (
            AccessTokenResponse(
                access_token=access_token,
                expires_in=expires_in,
                user=build_authenticated_user(
                    user,
                    roles=roles,
                    permissions=permissions,
                ),
            ),
            raw_refresh_token,
        )

    def refresh(self, raw_refresh_token: str | None) -> tuple[AccessTokenResponse, str]:
        """Rotate refresh token securely with reuse detection and family revocation."""
        if not raw_refresh_token:
            raise UnauthorizedError(
                "Refresh session cookie is missing.",
                code="REFRESH_TOKEN_MISSING",
                clear_refresh_cookie=True,
            )

        now = utc_now()
        token_hash = hash_refresh_token(raw_refresh_token)
        existing = self._refresh_repo.get_by_token_hash_for_update(token_hash)
        if existing is None:
            log_security_event(
                event_type="auth.refresh",
                outcome="denied",
                message="Rejected unrecognised refresh token.",
                level=logging.WARNING,
            )
            raise UnauthorizedError(
                "Refresh session is invalid.",
                code="INVALID_REFRESH_TOKEN",
                clear_refresh_cookie=True,
            )

        if existing.revoked_at is not None:
            self._refresh_repo.revoke_family(
                token_family_id=existing.token_family_id,
                reason=RevocationReason.TOKEN_REUSE_DETECTED.value,
                now=now,
            )
            self._db.commit()
            log_security_event(
                event_type="auth.refresh.reuse_detected",
                outcome="denied",
                actor_user_id=str(existing.user_id),
                message=(
                    f"Detected reuse of revoked refresh token; revoked session family "
                    f"'{existing.token_family_id}'."
                ),
                level=logging.WARNING,
            )
            raise UnauthorizedError(
                "Refresh session is no longer valid.",
                code="REFRESH_TOKEN_REUSED",
                clear_refresh_cookie=True,
            )

        if ensure_utc(existing.expires_at) <= now:
            existing.revoked_at = now
            existing.revoked_reason = RevocationReason.EXPIRED.value
            self._db.commit()
            log_security_event(
                event_type="auth.refresh.expired",
                outcome="denied",
                actor_user_id=str(existing.user_id),
                message="Rejected expired refresh session.",
            )
            raise UnauthorizedError(
                "Refresh session has expired.",
                code="REFRESH_TOKEN_EXPIRED",
                clear_refresh_cookie=True,
            )

        user = existing.user or self._user_repo.get_by_id(existing.user_id)
        if user is None or user.status != UserStatus.ACTIVE.value:
            self._refresh_repo.revoke_family(
                token_family_id=existing.token_family_id,
                reason=RevocationReason.USER_DISABLED.value,
                now=now,
            )
            self._db.commit()
            raise UnauthorizedError(
                "Refresh session is no longer valid.",
                code="SESSION_USER_INACTIVE",
                clear_refresh_cookie=True,
            )

        new_raw_token = generate_refresh_token()
        new_token_hash = hash_refresh_token(new_raw_token)
        new_expires_at = now + timedelta(days=self._settings.security.jwt_refresh_token_expire_days)

        new_session = self._refresh_repo.create(
            user_id=user.id,
            token_family_id=existing.token_family_id,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
            session_metadata=existing.session_metadata,
        )
        self._refresh_repo.mark_rotated(
            session_record=existing,
            replaced_by_id=new_session.id,
            reason=RevocationReason.ROTATED.value,
            now=now,
        )

        roles, permissions = self._rbac_repo.get_user_platform_roles_and_permissions(user.id)
        access_token, expires_in = create_access_token(
            user_id=user.id,
            session_family_id=existing.token_family_id,
            settings=self._settings,
            now=now,
        )
        self._db.commit()

        log_security_event(
            event_type="auth.refresh",
            outcome="success",
            actor_user_id=str(user.id),
            message="Rotated refresh session cleanly.",
        )
        return (
            AccessTokenResponse(
                access_token=access_token,
                expires_in=expires_in,
                user=build_authenticated_user(
                    user,
                    roles=roles,
                    permissions=permissions,
                ),
            ),
            new_raw_token,
        )

    def logout(self, raw_refresh_token: str | None) -> LogoutResponse:
        """Revoke the active refresh session family if present."""
        if not raw_refresh_token:
            return LogoutResponse(message="Logged out successfully.", revoked=False)

        now = utc_now()
        token_hash = hash_refresh_token(raw_refresh_token)
        existing = self._refresh_repo.get_by_token_hash_for_update(token_hash)
        if existing is None:
            return LogoutResponse(message="Logged out successfully.", revoked=False)

        revoked_count = self._refresh_repo.revoke_family(
            token_family_id=existing.token_family_id,
            reason=RevocationReason.LOGOUT.value,
            now=now,
        )
        self._db.commit()

        log_security_event(
            event_type="auth.logout",
            outcome="success",
            actor_user_id=str(existing.user_id),
            message="Revoked refresh session family on logout.",
        )
        return LogoutResponse(message="Logged out successfully.", revoked=revoked_count > 0)

    def list_my_sessions(self, principal: AuthenticatedPrincipal) -> SessionListResponse:
        """Return sessions belonging strictly to the authenticated user."""
        now = utc_now()
        sessions = self._refresh_repo.list_for_user(
            user_id=principal.user.id,
            include_revoked=True,
        )
        items = [
            RefreshSessionSummary(
                id=s.id,
                token_family_id=s.token_family_id,
                created_at=s.created_at,
                expires_at=s.expires_at,
                last_used_at=s.last_used_at,
                revoked_at=s.revoked_at,
                revoked_reason=s.revoked_reason,
                is_current_family=(
                    s.token_family_id == principal.session_family_id
                    and s.revoked_at is None
                    and ensure_utc(s.expires_at) > now
                ),
                session_metadata=s.session_metadata,
            )
            for s in sessions
        ]
        return SessionListResponse(items=items)

    def revoke_my_session(
        self,
        *,
        session_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
    ) -> RevokeSessionResponse:
        """Revoke one session family owned strictly by the authenticated user."""
        target = self._refresh_repo.get_by_id_for_user(
            session_id=session_id,
            user_id=principal.user.id,
        )
        if target is None:
            raise NotFoundError("Refresh session was not found.", code="SESSION_NOT_FOUND")

        now = utc_now()
        revoked_count = self._refresh_repo.revoke_family(
            token_family_id=target.token_family_id,
            reason=RevocationReason.REVOKED_BY_USER.value,
            now=now,
        )
        self._db.commit()

        log_security_event(
            event_type="auth.session_revoked",
            outcome="success",
            actor_user_id=str(principal.user.id),
            message=f"User revoked session '{session_id}' (family '{target.token_family_id}').",
        )
        return RevokeSessionResponse(
            session_id=session_id,
            revoked=revoked_count > 0,
            message="Session revoked successfully.",
        )
