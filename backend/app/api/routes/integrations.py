"""FastAPI HTTP routes for Phase 2.4B delegated GitHub & Jira integrations."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Response, status

from app.api.deps import (
    get_current_principal,
    get_source_integration_service,
    require_organisation_permission,
    require_project_permission,
    resolve_project_context,
)
from app.core.exceptions import ForbiddenError
from app.schemas.integrations import (
    CancelSyncResponse,
    CreateGitHubMappingRequest,
    CreateJiraMappingRequest,
    GitHubRepositoryListResponse,
    JiraDiscoveryResponse,
    JiraSiteListResponse,
    OAuthCallbackResponse,
    OAuthStartRequest,
    OAuthStartResponse,
    ProjectSourceMappingListResponse,
    ProjectSourceMappingResponse,
    SourceConnectionListResponse,
    SourceConnectionResponse,
    SourceSyncHistoryResponse,
    SourceSyncRunResponse,
    TriggerSyncRequest,
    TriggerSyncResponse,
    VerifySourceAccessRequest,
    VerifySourceAccessResponse,
)
from app.services.integrations.service import SourceIntegrationService
from app.services.rbac import AuthenticatedPrincipal, OrganisationContext, ProjectContext

router = APIRouter(tags=["Source Integrations"])


def _require_project_contributor_or_manager(project_ctx: ProjectContext) -> None:
    allowed = project_ctx.has_permission("project.manage") or (
        project_ctx.project_membership is not None
        and project_ctx.has_permission("project.evidence.contribute")
    )
    if not allowed:
        raise ForbiddenError(
            "You do not have permission to manage or sync source integrations in this project.",
            code="FORBIDDEN",
        )


@router.get(
    "/organisations/{organisation_id}/integrations/connections",
    response_model=SourceConnectionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List source connections inside an authorised organisation",
)
def list_organisation_connections(
    org_ctx: Annotated[
        OrganisationContext,
        Depends(require_organisation_permission("organisation.read")),
    ],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
    provider: Annotated[str | None, Query()] = None,
) -> SourceConnectionListResponse:
    """List organisation-scoped connections with strictly caller's own authorisation status."""
    return service.list_organisation_connections(org_ctx=org_ctx, provider=provider)


@router.post(
    "/organisations/{organisation_id}/integrations/{provider}/oauth/start",
    response_model=OAuthStartResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate delegated OAuth 2.0 authorisation flow for GitHub or Jira",
)
def start_oauth_connection(
    provider: str,
    response: Response,
    org_ctx: Annotated[
        OrganisationContext,
        Depends(require_organisation_permission("organisation.read")),
    ],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
    payload: Annotated[OAuthStartRequest | None, Body()] = None,
) -> OAuthStartResponse:
    """Generate single-use cryptographic state, PKCE challenge, and provider auth URL."""
    response.headers["Cache-Control"] = "no-store"
    req = payload or OAuthStartRequest()
    return service.start_oauth(
        org_ctx=org_ctx,
        provider=provider,
        display_name=req.display_name,
        redirect_after=req.redirect_after,
        source_connection_id=req.source_connection_id,
    )


@router.get(
    "/integrations/{provider}/callback",
    response_model=OAuthCallbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete delegated OAuth 2.0 callback cleanly under authenticated session",
)
def oauth_callback(
    provider: str,
    response: Response,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
    error_description: Annotated[str | None, Query()] = None,
) -> OAuthCallbackResponse:
    """Validate single-use user-bound state, exchange PKCE code, and store encrypted tokens."""
    response.headers["Cache-Control"] = "no-store"
    return service.complete_oauth_callback(
        provider=provider,
        principal=principal,
        code=code,
        state=state,
        oauth_error=error,
        oauth_error_description=error_description,
    )


@router.post(
    "/integrations/connections/{connection_id}/disconnect",
    response_model=SourceConnectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Disconnect a source connection and revoke delegated tokens",
)
def disconnect_connection(
    connection_id: uuid.UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
) -> SourceConnectionResponse:
    """Mark connection disconnected, revoke authorisations, and disable active mappings."""
    return service.disconnect_connection(
        connection_id=connection_id,
        principal=principal,
    )


@router.post(
    "/integrations/connections/{connection_id}/authorisation/revoke",
    response_model=SourceConnectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke the caller's own delegated OAuth credentials for a connection",
)
def revoke_my_authorisation(
    connection_id: uuid.UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
) -> SourceConnectionResponse:
    """Revoke only the calling user's delegated authorisation cleanly."""
    return service.revoke_my_authorisation(
        connection_id=connection_id,
        principal=principal,
    )


@router.get(
    "/integrations/connections/{connection_id}/github/repositories",
    response_model=GitHubRepositoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover GitHub repositories accessible to the calling user",
)
def discover_github_repositories(
    connection_id: uuid.UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
    page: Annotated[int, Query(ge=1, le=200)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 30,
) -> GitHubRepositoryListResponse:
    """List explicit GitHub repositories accessible strictly via the caller's token."""
    return service.discover_github_repositories(
        connection_id=connection_id,
        principal=principal,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/integrations/connections/{connection_id}/jira/sites",
    response_model=JiraSiteListResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover Atlassian Jira Cloud sites accessible to the calling user",
)
def discover_jira_sites(
    connection_id: uuid.UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
) -> JiraSiteListResponse:
    """Resolve accessible Jira Cloud sites (`cloud_id`) via caller's delegated token."""
    return service.discover_jira_sites(
        connection_id=connection_id,
        principal=principal,
    )


@router.get(
    "/integrations/connections/{connection_id}/jira/projects",
    response_model=JiraDiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover Jira Cloud projects inside an authorised Jira site",
)
def discover_jira_projects(
    connection_id: uuid.UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
    cloud_id: Annotated[str | None, Query()] = None,
    start_at: Annotated[int, Query(ge=0, le=5000)] = 0,
    max_results: Annotated[int, Query(ge=1, le=100)] = 50,
    query: Annotated[str | None, Query(max_length=120)] = None,
) -> JiraDiscoveryResponse:
    """List paginated Jira projects strictly inside caller-authorised Jira Cloud sites."""
    return service.discover_jira_projects(
        connection_id=connection_id,
        principal=principal,
        cloud_id=cloud_id,
        start_at=start_at,
        max_results=max_results,
        query=query,
    )


@router.get(
    "/projects/{project_id}/integrations/mappings",
    response_model=ProjectSourceMappingListResponse,
    status_code=status.HTTP_200_OK,
    summary="List configured external source mappings for a project workspace",
)
def list_project_mappings(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
    include_disabled: Annotated[bool, Query()] = True,
) -> ProjectSourceMappingListResponse:
    """List explicit source mappings and ACL policies attached to one project."""
    return service.list_project_mappings(
        project_ctx=project_ctx,
        include_disabled=include_disabled,
    )


@router.post(
    "/projects/{project_id}/integrations/github/mappings",
    response_model=ProjectSourceMappingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Map an explicitly selected GitHub repository into a project workspace",
)
def create_github_mapping(
    request: CreateGitHubMappingRequest,
    project_ctx: Annotated[ProjectContext, Depends(resolve_project_context)],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
) -> ProjectSourceMappingResponse:
    """Verify caller access and bind one GitHub repository to the target project."""
    _require_project_contributor_or_manager(project_ctx)
    return service.create_github_mapping(project_ctx=project_ctx, request=request)


@router.post(
    "/projects/{project_id}/integrations/jira/mappings",
    response_model=ProjectSourceMappingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Map an explicitly selected Jira Cloud project into a project workspace",
)
def create_jira_mapping(
    request: CreateJiraMappingRequest,
    project_ctx: Annotated[ProjectContext, Depends(resolve_project_context)],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
) -> ProjectSourceMappingResponse:
    """Verify caller site & project access and bind one Jira project cleanly."""
    _require_project_contributor_or_manager(project_ctx)
    return service.create_jira_mapping(project_ctx=project_ctx, request=request)


@router.delete(
    "/projects/{project_id}/integrations/mappings/{mapping_id}",
    response_model=ProjectSourceMappingResponse,
    status_code=status.HTTP_200_OK,
    summary="Disable an external source mapping while preserving evidence history",
)
def disable_project_mapping(
    mapping_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(resolve_project_context)],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
) -> ProjectSourceMappingResponse:
    """Disable future syncs on a mapping cleanly without deleting historical evidence."""
    _require_project_contributor_or_manager(project_ctx)
    return service.disable_mapping(project_ctx=project_ctx, mapping_id=mapping_id)


@router.post(
    "/projects/{project_id}/integrations/mappings/{mapping_id}/verify-access",
    response_model=VerifySourceAccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify caller's own delegated source permissions for a mapped resource",
)
def verify_mapping_access(
    mapping_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
    payload: Annotated[VerifySourceAccessRequest | None, Body()] = None,
) -> VerifySourceAccessResponse:
    """Verify caller access via external provider API and update SourceAccessPolicy."""
    return service.verify_caller_source_access(
        project_ctx=project_ctx,
        mapping_id=mapping_id,
        source_connection_id=payload.source_connection_id if payload else None,
    )


@router.post(
    "/projects/{project_id}/integrations/mappings/{mapping_id}/sync",
    response_model=TriggerSyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue an asynchronous delegated source sync job",
)
def trigger_mapping_sync(
    mapping_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(resolve_project_context)],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
    payload: Annotated[TriggerSyncRequest | None, Body()] = None,
) -> TriggerSyncResponse:
    """Queue a PostgreSQL `source_sync` worker job using strictly caller's credentials."""
    _require_project_contributor_or_manager(project_ctx)
    req = payload or TriggerSyncRequest()
    return service.trigger_sync(
        project_ctx=project_ctx,
        mapping_id=mapping_id,
        sync_mode=req.sync_mode,
    )


@router.get(
    "/projects/{project_id}/integrations/sync-runs",
    response_model=SourceSyncHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="List source sync run history for a project workspace",
)
def list_project_sync_runs(
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
    mapping_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SourceSyncHistoryResponse:
    """Return durable sync run history ordered newest-first inside project scope."""
    return service.list_project_sync_runs(
        project_ctx=project_ctx,
        mapping_id=mapping_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/integrations/sync-runs/{sync_run_id}",
    response_model=SourceSyncRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect status and metrics for one source sync run",
)
def get_sync_run(
    sync_run_id: uuid.UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
) -> SourceSyncRunResponse:
    """Fetch sync run metrics after verifying project read access."""
    return service.get_sync_run(sync_run_id=sync_run_id, principal=principal)


@router.post(
    "/integrations/sync-runs/{sync_run_id}/cancel",
    response_model=CancelSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a queued or running source sync run cleanly",
)
def cancel_sync_run(
    sync_run_id: uuid.UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    service: Annotated[SourceIntegrationService, Depends(get_source_integration_service)],
) -> CancelSyncResponse:
    """Cancel an active sync run and its underlying background job."""
    return service.cancel_sync_run(sync_run_id=sync_run_id, principal=principal)
