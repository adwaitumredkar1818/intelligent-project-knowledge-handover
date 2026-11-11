"""Platform authentication, refresh cookie rotation, and self-session endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import (
    get_app_settings,
    get_auth_service,
    require_auth_rate_limit,
    require_permission,
)
from app.core.config import Settings
from app.core.security import (
    clear_refresh_cookie,
    set_refresh_cookie,
    validate_csrf_origin,
)
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    RevokeSessionResponse,
    SessionListResponse,
)
from app.schemas.user import AuthenticatedUserResponse
from app.services.auth import AuthService, build_authenticated_user
from app.services.rbac import AuthenticatedPrincipal

router = APIRouter(prefix="/auth", tags=["authentication"])


def _extract_safe_session_metadata(request: Request) -> dict[str, str] | None:
    """Capture privacy-conscious coarse client classification only (never raw UA/IP/tokens)."""
    user_agent = request.headers.get("user-agent")
    if not user_agent:
        return None
    lowered = user_agent.lower()
    if any(token in lowered for token in ("mozilla/", "chrome/", "safari/", "firefox/", "edg/")):
        return {"client_family": "browser"}
    return {"client_family": "api_client"}


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new platform user account",
    dependencies=[Depends(require_auth_rate_limit("register"))],
)
def register(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> RegisterResponse:
    """Create a platform account with Argon2id password hashing and default user role."""
    return auth_service.register(payload)


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate with email and password",
    dependencies=[Depends(require_auth_rate_limit("login"))],
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_app_settings),  # noqa: B008
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> AccessTokenResponse:
    """Issue a short-lived JWT access token and deliver refresh token via HttpOnly cookie."""
    token_response, raw_refresh_token = auth_service.login(
        payload=payload,
        session_metadata=_extract_safe_session_metadata(request),
    )
    set_refresh_cookie(response, raw_token=raw_refresh_token, settings=settings)
    return token_response


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate HttpOnly refresh cookie and issue a fresh access token",
    dependencies=[Depends(require_auth_rate_limit("refresh"))],
)
def refresh_token(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_app_settings),  # noqa: B008
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> AccessTokenResponse:
    """Validate CSRF origin/referer and rotate refresh session with reuse detection."""
    validate_csrf_origin(request, settings)
    raw_token = request.cookies.get(settings.security.refresh_cookie_name)
    token_response, new_raw_token = auth_service.refresh(raw_token)
    set_refresh_cookie(response, raw_token=new_raw_token, settings=settings)
    return token_response


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke active refresh session and clear cookie",
)
def logout(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_app_settings),  # noqa: B008
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> LogoutResponse:
    """Validate CSRF origin/referer, revoke refresh session family, and delete cookie."""
    validate_csrf_origin(request, settings)
    raw_token = request.cookies.get(settings.security.refresh_cookie_name)
    result = auth_service.logout(raw_token)
    clear_refresh_cookie(response, settings)
    return result


@router.get(
    "/me",
    response_model=AuthenticatedUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Return the currently authenticated user's profile and platform permissions",
)
def read_current_user(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission("account.profile.read")),
    ],
) -> AuthenticatedUserResponse:
    """Return authenticated user details strictly without secret hashes or tokens."""
    return build_authenticated_user(
        principal.user,
        roles=principal.roles,
        permissions=principal.permissions,
    )


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List the current user's active and recent sessions",
)
def list_my_sessions(
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission("account.sessions.read")),
    ],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> SessionListResponse:
    """List refresh session metadata strictly scoped to the authenticated user."""
    return auth_service.list_my_sessions(principal)


@router.delete(
    "/sessions/{session_id}",
    response_model=RevokeSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke one of the current user's sessions",
)
def revoke_my_session(
    session_id: uuid.UUID,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission("account.sessions.revoke")),
    ],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> RevokeSessionResponse:
    """Revoke a session family belonging strictly to the authenticated user."""
    return auth_service.revoke_my_session(session_id=session_id, principal=principal)
