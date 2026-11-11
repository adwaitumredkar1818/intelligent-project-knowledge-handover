"""Platform user identity and RBAC management routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    get_current_principal,
    get_rbac_service,
    get_user_service,
    require_permission,
)
from app.schemas.user import (
    AssignRoleRequest,
    AssignRoleResponse,
    RoleListResponse,
    UpdateUserStatusRequest,
    UserListResponse,
    UserSummaryResponse,
)
from app.services.rbac import AuthenticatedPrincipal, RbacService
from app.services.user import UserService

router = APIRouter(tags=["users-and-rbac"])


@router.get(
    "/users",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List platform users (requires platform.users.read)",
)
def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: AuthenticatedPrincipal = Depends(require_permission("platform.users.read")),  # noqa: B008
    user_service: UserService = Depends(get_user_service),  # noqa: B008
) -> UserListResponse:
    """List platform accounts without exposing password hashes or tokens."""
    return user_service.list_users(limit=limit, offset=offset)


@router.get(
    "/users/{user_id}",
    response_model=UserSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Read a user's profile (self or platform.users.read)",
)
def get_user_profile(
    user_id: uuid.UUID,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),  # noqa: B008
    user_service: UserService = Depends(get_user_service),  # noqa: B008
) -> UserSummaryResponse:
    """Enforce self-account access vs privileged cross-user access."""
    return user_service.get_user_profile(
        target_user_id=user_id,
        acting_principal=principal,
    )


@router.patch(
    "/users/{user_id}/status",
    response_model=UserSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a user's account lifecycle status (requires platform.users.manage)",
)
def update_user_status(
    user_id: uuid.UUID,
    payload: UpdateUserStatusRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission("platform.users.manage")),
    ],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserSummaryResponse:
    """Activate, disable, or lock an account and revoke active refresh sessions when inactive."""
    return user_service.update_user_status(
        target_user_id=user_id,
        payload=payload,
        acting_principal=principal,
    )


@router.get(
    "/roles",
    response_model=RoleListResponse,
    status_code=status.HTTP_200_OK,
    summary="List RBAC roles and permission definitions (requires platform.roles.read)",
)
def list_roles(
    _: Annotated[AuthenticatedPrincipal, Depends(require_permission("platform.roles.read"))],
    rbac_service: Annotated[RbacService, Depends(get_rbac_service)],
) -> RoleListResponse:
    """Return platform, organisation, and project catalog role definitions."""
    return rbac_service.list_roles()


@router.post(
    "/users/{user_id}/roles",
    response_model=AssignRoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a platform-scoped role to a user (requires platform.roles.manage)",
)
def assign_platform_role(
    user_id: uuid.UUID,
    payload: AssignRoleRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission("platform.roles.manage")),
    ],
    rbac_service: Annotated[RbacService, Depends(get_rbac_service)],
) -> AssignRoleResponse:
    """Assign a platform-scoped role; rejects organisation/project roles globally."""
    return rbac_service.assign_platform_role(
        target_user_id=user_id,
        role_name=payload.role_name,
        acting_principal=principal,
    )
