"""Source connection and project container mapping routes for Panel A (Connected Sources)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    get_current_principal,
    get_evidence_service,
    require_organisation_membership,
    require_project_permission,
)
from app.schemas.evidence import (
    CreateProjectSourceMappingRequest,
    CreateSourceConnectionRequest,
    ProjectSourceMappingListResponse,
    ProjectSourceMappingResponse,
    SourceConnectionListResponse,
    SourceConnectionResponse,
    SyncJobListResponse,
    SyncJobResponse,
    UpdateSourceConnectionRequest,
)
from app.services.evidence import EvidenceService
from app.services.rbac import AuthenticatedPrincipal, OrganisationContext, ProjectContext

router = APIRouter(tags=["sources"])


# -----------------------------------------------------------------------------
# Organisation Connected Sources (Global / Per-User OAuth & Tokens)
# -----------------------------------------------------------------------------
@router.post(
    "/organisations/{organisation_id}/sources",
    response_model=SourceConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new external source connection (GitHub, Jira, or Upload)",
)
def create_source_connection(
    organisation_id: uuid.UUID,
    payload: CreateSourceConnectionRequest,
    org_ctx: Annotated[OrganisationContext, Depends(require_organisation_membership)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> SourceConnectionResponse:
    """Connect an external source with encrypted credentials linked to the caller."""
    return evidence_service.create_source_connection(
        organisation_id=organisation_id,
        user_id=principal.user_id,
        payload=payload,
    )


@router.get(
    "/organisations/{organisation_id}/sources",
    response_model=SourceConnectionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List active source connections accessible to the caller",
)
def list_source_connections(
    organisation_id: uuid.UUID,
    org_ctx: Annotated[OrganisationContext, Depends(require_organisation_membership)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> SourceConnectionListResponse:
    """List source connections owned by the caller or marked as shared."""
    return evidence_service.list_source_connections(
        organisation_id=organisation_id,
        user_id=principal.user_id,
    )


@router.patch(
    "/sources/{connection_id}",
    response_model=SourceConnectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update source connection display name, sharing settings, or metadata",
)
def update_source_connection(
    connection_id: uuid.UUID,
    payload: UpdateSourceConnectionRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> SourceConnectionResponse:
    """Update connection settings (requires owner)."""
    return evidence_service.update_source_connection(
        connection_id=connection_id,
        user_id=principal.user_id,
        payload=payload,
    )


# -----------------------------------------------------------------------------
# Project Source Mappings (Panel A Container Links)
# -----------------------------------------------------------------------------
@router.post(
    "/projects/{project_id}/sources/mappings",
    response_model=ProjectSourceMappingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Map an external repo or Jira board to this project (requires project.sources.manage)",
)
def create_project_source_mapping(
    project_id: uuid.UUID,
    payload: CreateProjectSourceMappingRequest,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.sources.manage")),
    ],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> ProjectSourceMappingResponse:
    """Bind a specific external repository or project board into a project workspace."""
    return evidence_service.create_project_source_mapping(
        project_id=project_id,
        user_id=principal.user_id,
        payload=payload,
    )


@router.get(
    "/projects/{project_id}/sources/mappings",
    response_model=ProjectSourceMappingListResponse,
    status_code=status.HTTP_200_OK,
    summary="List source container mappings bound to this project (requires project.read)",
)
def list_project_source_mappings(
    project_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> ProjectSourceMappingListResponse:
    """List active source mappings configured in Panel A."""
    return evidence_service.list_project_source_mappings(project_id=project_id)


@router.post(
    "/projects/{project_id}/sources/mappings/{mapping_id}/sync",
    response_model=SyncJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger asynchronous sync for a source mapping (requires project.sources.manage)",
)
def trigger_source_mapping_sync(
    project_id: uuid.UUID,
    mapping_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.sources.manage")),
    ],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> SyncJobResponse:
    """Enqueue background synchronization for an external source container."""
    return evidence_service.trigger_sync(
        mapping_id=mapping_id,
        user_id=principal.user_id,
    )


@router.get(
    "/projects/{project_id}/sources/mappings/{mapping_id}/jobs",
    response_model=SyncJobListResponse,
    status_code=status.HTTP_200_OK,
    summary="List background sync job history for a container mapping (requires project.read)",
)
def list_source_mapping_jobs(
    project_id: uuid.UUID,
    mapping_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    evidence_service: Annotated[EvidenceService, Depends(get_evidence_service)],
) -> SyncJobListResponse:
    """Retrieve execution log history for container sync operations."""
    return evidence_service.list_sync_jobs(mapping_id=mapping_id)
