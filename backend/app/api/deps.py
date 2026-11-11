"""Reusable request-scoped FastAPI dependencies."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from typing import cast

import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.core.logging import get_correlation_id
from app.core.rate_limit import RateLimiterProtocol, check_auth_rate_limit
from app.core.security import decode_access_token, utc_now
from app.models.enums import UserStatus
from app.repositories.audit import AuditLogRepository
from app.repositories.auth import RefreshSessionRepository
from app.repositories.organisation import OrganisationRepository
from app.repositories.project import ProjectRepository
from app.repositories.rbac import RbacRepository
from app.repositories.system import SystemRepository
from app.repositories.user import UserRepository
from app.services.audit import AuditService
from app.services.auth import AuthService
from app.services.health import HealthService
from app.services.organisation import OrganisationService
from app.services.project import ProjectService
from app.services.rbac import (
    AuthenticatedPrincipal,
    OrganisationContext,
    ProjectContext,
    RbacService,
)
from app.services.user import UserService

_bearer_scheme = HTTPBearer(auto_error=False)


def get_app_settings(request: Request) -> Settings:
    """Return validated application settings attached to app state."""
    return cast(Settings, request.app.state.settings)


def get_db_session(request: Request) -> Iterator[Session]:
    """Yield a request-scoped SQLAlchemy Session with guaranteed cleanup."""
    session_factory = cast(sessionmaker[Session], request.app.state.session_factory)
    session = session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Return shared application HTTPX client initialized during app lifespan."""
    return cast(httpx.AsyncClient, request.app.state.http_client)


def get_request_id(request: Request) -> str:
    """Return active correlation ID bound to the current request."""
    state_id = getattr(request.state, "request_id", None)
    return str(state_id) if state_id else get_correlation_id()


def get_auth_rate_limiter(request: Request) -> RateLimiterProtocol | None:
    """Return configured auth rate limiter from app state when available."""
    return cast(
        RateLimiterProtocol | None,
        getattr(request.app.state, "auth_rate_limiter", None),
    )


def require_auth_rate_limit(
    action: str,
) -> Callable[[Request, Settings, RateLimiterProtocol | None], None]:
    """Dependency enforcing per-action authentication rate limits."""

    def _dependency(
        request: Request,
        settings: Settings = Depends(get_app_settings),  # noqa: B008
        limiter: RateLimiterProtocol | None = Depends(get_auth_rate_limiter),  # noqa: B008
    ) -> None:
        check_auth_rate_limit(
            request=request,
            settings=settings,
            limiter=limiter,
            action=action,
        )

    return _dependency


def get_health_service(
    settings: Settings = Depends(get_app_settings),  # noqa: B008
    db_session: Session = Depends(get_db_session),  # noqa: B008
    http_client: httpx.AsyncClient = Depends(get_http_client),  # noqa: B008
) -> HealthService:
    """Construct HealthService for the current request scope."""
    return HealthService(
        settings=settings,
        system_repository=SystemRepository(db_session),
        http_client=http_client,
    )


def get_rbac_service(
    db_session: Session = Depends(get_db_session),  # noqa: B008
) -> RbacService:
    """Construct RbacService for the current request scope."""
    return RbacService(
        db_session=db_session,
        rbac_repository=RbacRepository(db_session),
        user_repository=UserRepository(db_session),
        organisation_repository=OrganisationRepository(db_session),
        project_repository=ProjectRepository(db_session),
    )


def get_audit_service(
    db_session: Session = Depends(get_db_session),  # noqa: B008
) -> AuditService:
    """Construct AuditService for the current request scope."""
    return AuditService(audit_repository=AuditLogRepository(db_session))


def get_auth_service(
    settings: Settings = Depends(get_app_settings),  # noqa: B008
    db_session: Session = Depends(get_db_session),  # noqa: B008
) -> AuthService:
    """Construct AuthService for the current request scope."""
    return AuthService(
        settings=settings,
        db_session=db_session,
        user_repository=UserRepository(db_session),
        refresh_repository=RefreshSessionRepository(db_session),
        rbac_repository=RbacRepository(db_session),
    )


def get_user_service(
    db_session: Session = Depends(get_db_session),  # noqa: B008
    rbac_service: RbacService = Depends(get_rbac_service),  # noqa: B008
) -> UserService:
    """Construct UserService for the current request scope."""
    return UserService(
        db_session=db_session,
        user_repository=UserRepository(db_session),
        refresh_repository=RefreshSessionRepository(db_session),
        rbac_service=rbac_service,
    )


def get_organisation_service(
    settings: Settings = Depends(get_app_settings),  # noqa: B008
    db_session: Session = Depends(get_db_session),  # noqa: B008
    rbac_service: RbacService = Depends(get_rbac_service),  # noqa: B008
    audit_service: AuditService = Depends(get_audit_service),  # noqa: B008
) -> OrganisationService:
    """Construct OrganisationService for the current request scope."""
    return OrganisationService(
        settings=settings,
        db_session=db_session,
        org_repository=OrganisationRepository(db_session),
        project_repository=ProjectRepository(db_session),
        rbac_repository=RbacRepository(db_session),
        user_repository=UserRepository(db_session),
        rbac_service=rbac_service,
        audit_service=audit_service,
    )


def get_project_service(
    db_session: Session = Depends(get_db_session),  # noqa: B008
    rbac_service: RbacService = Depends(get_rbac_service),  # noqa: B008
    audit_service: AuditService = Depends(get_audit_service),  # noqa: B008
) -> ProjectService:
    """Construct ProjectService for the current request scope."""
    return ProjectService(
        db_session=db_session,
        org_repository=OrganisationRepository(db_session),
        project_repository=ProjectRepository(db_session),
        rbac_repository=RbacRepository(db_session),
        rbac_service=rbac_service,
        audit_service=audit_service,
    )


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),  # noqa: B008
    settings: Settings = Depends(get_app_settings),  # noqa: B008
    db_session: Session = Depends(get_db_session),  # noqa: B008
    rbac_service: RbacService = Depends(get_rbac_service),  # noqa: B008
) -> AuthenticatedPrincipal:
    """Validate Bearer JWT, verify user status & active session family, and resolve RBAC."""
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not credentials.credentials
    ):
        raise UnauthorizedError(
            "Authentication credentials were not provided.",
            code="AUTHENTICATION_REQUIRED",
        )

    claims = decode_access_token(credentials.credentials, settings)
    user = UserRepository(db_session).get_by_id(claims.subject)
    if user is None or user.status != UserStatus.ACTIVE.value:
        raise UnauthorizedError(
            "Authentication credentials are invalid.",
            code="AUTHENTICATION_INVALID",
        )

    is_active_family = RefreshSessionRepository(db_session).is_family_active(
        token_family_id=claims.session_family_id,
        user_id=user.id,
        now=utc_now(),
    )
    if not is_active_family:
        raise UnauthorizedError(
            "Authentication session has been revoked or expired.",
            code="SESSION_REVOKED",
        )

    return rbac_service.resolve_principal(
        user=user,
        session_family_id=claims.session_family_id,
    )


def require_permissions(
    *permission_codes: str,
) -> Callable[[AuthenticatedPrincipal, RbacService], AuthenticatedPrincipal]:
    """Dependency factory enforcing one or more platform permissions (fails closed)."""

    def _dependency(
        principal: AuthenticatedPrincipal = Depends(get_current_principal),  # noqa: B008
        rbac_service: RbacService = Depends(get_rbac_service),  # noqa: B008
    ) -> AuthenticatedPrincipal:
        rbac_service.require_permissions(principal, permission_codes)
        return principal

    return _dependency


def require_permission(
    permission_code: str,
) -> Callable[[AuthenticatedPrincipal, RbacService], AuthenticatedPrincipal]:
    """Dependency factory enforcing a single named permission (fails closed)."""
    return require_permissions(permission_code)


def resolve_organisation_context(
    organisation_id: uuid.UUID,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),  # noqa: B008
    rbac_service: RbacService = Depends(get_rbac_service),  # noqa: B008
) -> OrganisationContext:
    """Resolve verified active membership context for `{organisation_id}` (404 otherwise)."""
    return rbac_service.resolve_organisation_context(
        organisation_id=organisation_id,
        principal=principal,
    )


def require_organisation_membership(
    organisation_id: uuid.UUID,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),  # noqa: B008
    rbac_service: RbacService = Depends(get_rbac_service),  # noqa: B008
) -> OrganisationContext:
    """Verify active organisation membership before accessing tenant-scoped resources."""
    return rbac_service.resolve_organisation_context(
        organisation_id=organisation_id,
        principal=principal,
    )


def require_organisation_permissions(
    *permission_codes: str,
) -> Callable[[OrganisationContext, RbacService], OrganisationContext]:
    """Dependency factory enforcing organisation-scoped permissions (fails closed)."""

    def _dependency(
        org_ctx: OrganisationContext = Depends(resolve_organisation_context),  # noqa: B008
        rbac_service: RbacService = Depends(get_rbac_service),  # noqa: B008
    ) -> OrganisationContext:
        rbac_service.require_organisation_permissions(org_ctx, permission_codes)
        return org_ctx

    return _dependency


def require_organisation_permission(
    permission_code: str,
) -> Callable[[OrganisationContext, RbacService], OrganisationContext]:
    """Dependency factory enforcing a single organisation-scoped permission."""
    return require_organisation_permissions(permission_code)


def resolve_project_context(
    project_id: uuid.UUID,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),  # noqa: B008
    rbac_service: RbacService = Depends(get_rbac_service),  # noqa: B008
) -> ProjectContext:
    """Resolve verified project context with dynamic parent-organisation membership check."""
    return rbac_service.resolve_project_context(
        project_id=project_id,
        principal=principal,
    )


def resolve_project_read_context(
    project_id: uuid.UUID,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),  # noqa: B008
    rbac_service: RbacService = Depends(get_rbac_service),  # noqa: B008
) -> ProjectContext:
    """Resolve verified project read context honoring `private` vs `organisation` visibility."""
    return rbac_service.resolve_project_read_context(
        project_id=project_id,
        principal=principal,
    )


def require_project_membership(
    project_id: uuid.UUID,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),  # noqa: B008
    rbac_service: RbacService = Depends(get_rbac_service),  # noqa: B008
) -> ProjectContext:
    """Require both active parent-organisation membership and explicit active project membership."""
    return rbac_service.resolve_project_context(
        project_id=project_id,
        principal=principal,
        require_explicit_membership=True,
    )


def require_project_permissions(
    *permission_codes: str,
    require_explicit_membership: bool = False,
) -> Callable[[ProjectContext, RbacService], ProjectContext]:
    """Dependency factory enforcing project-scoped permissions (with parent org verification)."""

    def _dependency(
        project_ctx: ProjectContext = Depends(resolve_project_context),  # noqa: B008
        rbac_service: RbacService = Depends(get_rbac_service),  # noqa: B008
    ) -> ProjectContext:
        rbac_service.require_project_permissions(
            project_ctx,
            permission_codes,
            require_explicit_membership=require_explicit_membership,
        )
        return project_ctx

    return _dependency


def require_project_permission(
    permission_code: str,
    *,
    require_explicit_membership: bool = False,
) -> Callable[[ProjectContext, RbacService], ProjectContext]:
    """Dependency factory enforcing a single project-scoped permission."""
    return require_project_permissions(
        permission_code,
        require_explicit_membership=require_explicit_membership,
    )
