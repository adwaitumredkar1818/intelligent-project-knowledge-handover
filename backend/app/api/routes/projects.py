"""Multi-tenant project workspace and project membership routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    get_project_service,
    require_organisation_permission,
    require_project_permission,
    resolve_project_read_context,
)
from app.models.enums import ProjectMembershipStatus, ProjectStatus
from app.schemas.organisation import RemoveMembershipResponse
from app.schemas.project import (
    AddProjectMemberRequest,
    CreateProjectRequest,
    ProjectListResponse,
    ProjectMemberListResponse,
    ProjectMemberResponse,
    ProjectResponse,
    UpdateProjectMemberRoleRequest,
    UpdateProjectRequest,
)
from app.services.project import ProjectService
from app.services.rbac import OrganisationContext, ProjectContext

router = APIRouter(tags=["projects"])


@router.post(
    "/organisations/{organisation_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project workspace inside an organisation (requires project.create)",
)
def create_project(
    payload: CreateProjectRequest,
    org_ctx: Annotated[
        OrganisationContext,
        Depends(require_organisation_permission("project.create")),
    ],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    """Create a project workspace inside an active organisation and assign project managers."""
    return project_service.create_project(org_ctx=org_ctx, payload=payload)


@router.get(
    "/organisations/{organisation_id}/projects",
    response_model=ProjectListResponse,
    status_code=status.HTTP_200_OK,
    summary="List permitted projects in an organisation (requires organisation.read)",
)
def list_organisation_projects(
    org_ctx: Annotated[
        OrganisationContext,
        Depends(require_organisation_permission("organisation.read")),
    ],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    project_status: Annotated[ProjectStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProjectListResponse:
    """List projects visible to the caller within their verified organisation."""
    return project_service.list_projects_in_organisation(
        org_ctx=org_ctx,
        status=project_status.value if project_status is not None else None,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get project workspace details (honors private vs organisation visibility)",
)
def get_project_detail(
    project_ctx: Annotated[ProjectContext, Depends(resolve_project_read_context)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    """Return project metadata and resolved effective permissions for the current user."""
    return project_service.get_project_detail(project_ctx)


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update project workspace metadata, status, or owner (requires project.manage)",
)
def update_project(
    payload: UpdateProjectRequest,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.manage")),
    ],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    """Update a project's metadata, visibility, lifecycle status, or assigned owner."""
    return project_service.update_project(ctx=project_ctx, payload=payload)


@router.post(
    "/projects/{project_id}/archive",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Archive a project workspace (requires project.manage)",
)
def archive_project(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.manage")),
    ],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    """Archive a non-archived project cleanly and record an audit trail entry."""
    return project_service.archive_project(ctx=project_ctx)


@router.get(
    "/projects/{project_id}/members",
    response_model=ProjectMemberListResponse,
    status_code=status.HTTP_200_OK,
    summary="List project members (requires project.members.read)",
)
def list_project_members(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.members.read")),
    ],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    member_status: Annotated[
        ProjectMembershipStatus | None,
        Query(alias="status"),
    ] = ProjectMembershipStatus.ACTIVE,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProjectMemberListResponse:
    """List member assignments and project roles for this project workspace."""
    return project_service.list_project_members(
        ctx=project_ctx,
        status=member_status.value if member_status is not None else None,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/projects/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign an organisation member to a project (requires project.members.manage)",
)
def add_project_member(
    payload: AddProjectMemberRequest,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.members.manage")),
    ],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectMemberResponse:
    """Assign an active parent-organisation member into this project with a project role."""
    return project_service.add_project_member(ctx=project_ctx, payload=payload)


@router.patch(
    "/projects/{project_id}/members/{user_id}/role",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a project member's role (requires project.members.manage)",
)
def update_project_member_role(
    user_id: uuid.UUID,
    payload: UpdateProjectMemberRoleRequest,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.members.manage")),
    ],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectMemberResponse:
    """Update a project member's project-scoped role with owner continuity guards."""
    return project_service.update_project_member_role(
        ctx=project_ctx,
        target_user_id=user_id,
        payload=payload,
    )


@router.delete(
    "/projects/{project_id}/members/{user_id}",
    response_model=RemoveMembershipResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a project member (requires project.members.manage)",
)
def remove_project_member(
    user_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.members.manage")),
    ],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> RemoveMembershipResponse:
    """Revoke a user's active membership in the project workspace."""
    return project_service.remove_project_member(ctx=project_ctx, target_user_id=user_id)
