"""HTTP endpoints for Panel A Connected Sources & Project Mappings."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import Field
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_principal,
    get_db_session,
    get_token_encryption_service,
    require_project_permission,
)
from app.core.exceptions import NotFoundError
from app.models.enums import BackgroundJobStatus, BackgroundJobType
from app.models.integration import (
    ProjectSourceMapping,
    SourceAccessPolicy,
    SourceConnection,
    UserSourceAuthorisation,
)
from app.models.job import BackgroundJob
from app.schemas.common import BaseSchema
from app.services.rbac import AuthenticatedPrincipal, ProjectContext
from app.services.token_encryption import TokenEncryptionService

logger = logging.getLogger("app.api.routes.sources")

router = APIRouter(tags=["Connected Sources"])


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------


class CreateSourceConnectionRequest(BaseSchema):
    provider: str
    account_identifier: str
    secret_token: str
    scopes: list[str] = Field(default_factory=list)
    is_shared: bool = False
    display_name: str | None = None


class SourceConnectionItemResponse(BaseSchema):
    id: uuid.UUID
    organisation_id: uuid.UUID
    provider: str
    display_name: str
    status: str
    is_shared: bool
    created_at: datetime


class SourceConnectionListResponse(BaseSchema):
    items: list[SourceConnectionItemResponse]
    total: int


class CreateSourceMappingRequest(BaseSchema):
    source_connection_id: uuid.UUID
    external_resource_id: str
    external_resource_name: str


class SourceMappingItemResponse(BaseSchema):
    id: uuid.UUID
    project_id: uuid.UUID
    source_connection_id: uuid.UUID
    provider: str
    external_resource_id: str
    external_resource_name: str
    status: str
    created_at: datetime


class SourceMappingListResponse(BaseSchema):
    items: list[SourceMappingItemResponse]
    total: int


class PatchSourceConnectionRequest(BaseSchema):
    is_shared: bool


class SourceSyncTriggerResponse(BaseSchema):
    id: uuid.UUID
    status: str
    job_type: str


class SourceSyncJobItem(BaseSchema):
    id: uuid.UUID
    status: str
    created_at: datetime
    completed_at: datetime | None = None


class SourceSyncJobsListResponse(BaseSchema):
    items: list[SourceSyncJobItem]
    total: int


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/organisations/{organisation_id}/sources",
    response_model=SourceConnectionItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a connected source (GitHub PAT or OAuth)",
)
def create_organisation_source(
    organisation_id: uuid.UUID,
    payload: CreateSourceConnectionRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db_session)],
    token_encryption: Annotated[TokenEncryptionService, Depends(get_token_encryption_service)],
) -> SourceConnectionItemResponse:
    encrypted_payload = token_encryption.encrypt_token(
        plaintext=payload.secret_token,
        organisation_id=organisation_id,
        user_id=principal.user.id,
        provider=payload.provider.lower(),
        token_kind="access_token",  # noqa: S106
    )

    display_name = payload.display_name or (
        f"{payload.provider.capitalize()} ({payload.account_identifier})"
    )
    conn = SourceConnection(
        organisation_id=organisation_id,
        provider=payload.provider.lower(),
        display_name=display_name,
        external_workspace_id=payload.account_identifier,
        status="active",
        created_by_user_id=principal.user.id,
        metadata_json={
            "scopes": payload.scopes,
            "is_shared": payload.is_shared,
            "account_identifier": payload.account_identifier,
        },
    )
    session.add(conn)
    session.flush()

    user_auth = UserSourceAuthorisation(
        source_connection_id=conn.id,
        organisation_id=organisation_id,
        user_id=principal.user.id,
        provider=payload.provider.lower(),
        external_user_id=payload.account_identifier,
        external_username=payload.account_identifier,
        encrypted_access_token=encrypted_payload.ciphertext,
        status="active",
        granted_scopes=payload.scopes,
    )
    session.add(user_auth)
    session.commit()
    session.refresh(conn)

    return SourceConnectionItemResponse(
        id=conn.id,
        organisation_id=conn.organisation_id,
        provider=conn.provider,
        display_name=conn.display_name,
        status=conn.status,
        is_shared=payload.is_shared,
        created_at=conn.created_at,
    )


@router.get(
    "/organisations/{organisation_id}/sources",
    response_model=SourceConnectionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List connected sources for an organisation",
)
def list_organisation_sources(
    organisation_id: uuid.UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db_session)],
) -> SourceConnectionListResponse:
    from sqlalchemy import select

    stmt = select(SourceConnection).where(
        SourceConnection.organisation_id == organisation_id,
        SourceConnection.status == "active",
    )
    connections = session.execute(stmt).scalars().all()
    items = [
        SourceConnectionItemResponse(
            id=c.id,
            organisation_id=c.organisation_id,
            provider=c.provider,
            display_name=c.display_name,
            status=c.status,
            is_shared=bool((c.metadata_json or {}).get("is_shared", False)),
            created_at=c.created_at,
        )
        for c in connections
    ]
    return SourceConnectionListResponse(items=items, total=len(items))


@router.patch(
    "/sources/{connection_id}",
    response_model=SourceConnectionItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Update source connection sharing state",
)
def patch_source_connection(
    connection_id: uuid.UUID,
    payload: PatchSourceConnectionRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db_session)],
) -> SourceConnectionItemResponse:
    from sqlalchemy import select

    from app.models.evidence import EvidenceItem

    conn = session.execute(
        select(SourceConnection).where(SourceConnection.id == connection_id)
    ).scalar_one_or_none()
    if conn is None:
        raise NotFoundError("Source connection not found.", code="CONNECTION_NOT_FOUND")

    meta = dict(conn.metadata_json or {})
    meta["is_shared"] = payload.is_shared
    conn.metadata_json = meta

    # Update associated policies and evidence
    policies = session.execute(
        select(SourceAccessPolicy).where(SourceAccessPolicy.source_connection_id == connection_id)
    ).scalars().all()
    for pol in policies:
        if payload.is_shared:
            pol.visibility_policy = "project_members_verified"
        else:
            pol.visibility_policy = "restricted_fail_closed"
            pol.allowed_user_ids = [str(conn.created_by_user_id)]

    # Update evidence acl_scope
    ev_items = session.execute(
        select(EvidenceItem).where(EvidenceItem.source_connection_id == connection_id)
    ).scalars().all()
    for ev in ev_items:
        ev.acl_scope = "project_members" if payload.is_shared else "source_restricted"

    session.commit()
    session.refresh(conn)

    return SourceConnectionItemResponse(
        id=conn.id,
        organisation_id=conn.organisation_id,
        provider=conn.provider,
        display_name=conn.display_name,
        status=conn.status,
        is_shared=payload.is_shared,
        created_at=conn.created_at,
    )


@router.post(
    "/projects/{project_id}/sources/mappings",
    response_model=SourceMappingItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Map external source repository or project to a project workspace",
)
def create_project_source_mapping(
    project_id: uuid.UUID,
    payload: CreateSourceMappingRequest,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> SourceMappingItemResponse:
    from sqlalchemy import select

    conn = session.execute(
        select(SourceConnection).where(SourceConnection.id == payload.source_connection_id)
    ).scalar_one_or_none()
    if conn is None:
        raise NotFoundError("Source connection not found.", code="CONNECTION_NOT_FOUND")

    is_shared = bool((conn.metadata_json or {}).get("is_shared", False))
    visibility = "project_members_verified" if is_shared else "restricted_fail_closed"
    allowed_users = [] if is_shared else [str(project_ctx.principal.user.id)]

    policy = SourceAccessPolicy(
        organisation_id=conn.organisation_id,
        project_id=project_id,
        source_connection_id=conn.id,
        provider=conn.provider,
        scope_identifier=payload.external_resource_id,
        visibility_policy=visibility,
        sync_permission_status="verified",
        allowed_user_ids=allowed_users,
    )
    session.add(policy)
    session.flush()

    resource_type = "github_repository" if conn.provider == "github" else "jira_project"

    mapping = ProjectSourceMapping(
        project_id=project_id,
        organisation_id=conn.organisation_id,
        source_connection_id=conn.id,
        provider=conn.provider,
        resource_type=resource_type,
        external_site_id="github.com" if conn.provider == "github" else "atlassian.net",
        external_resource_id=payload.external_resource_id,
        external_resource_key=payload.external_resource_id,
        external_resource_name=payload.external_resource_name,
        status="active",
        created_by_user_id=project_ctx.principal.user.id,
        source_access_policy_id=policy.id,
    )
    session.add(mapping)
    session.commit()
    session.refresh(mapping)

    return SourceMappingItemResponse(
        id=mapping.id,
        project_id=mapping.project_id,
        source_connection_id=mapping.source_connection_id,
        provider=mapping.provider,
        external_resource_id=mapping.external_resource_id,
        external_resource_name=mapping.external_resource_name,
        status=mapping.status,
        created_at=mapping.created_at,
    )


@router.get(
    "/projects/{project_id}/sources/mappings",
    response_model=SourceMappingListResponse,
    status_code=status.HTTP_200_OK,
    summary="List mapped sources for a project workspace",
)
def list_project_source_mappings(
    project_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> SourceMappingListResponse:
    from sqlalchemy import select

    stmt = select(ProjectSourceMapping).where(
        ProjectSourceMapping.project_id == project_id,
        ProjectSourceMapping.status == "active",
    )
    mappings = session.execute(stmt).scalars().all()
    items = [
        SourceMappingItemResponse(
            id=m.id,
            project_id=m.project_id,
            source_connection_id=m.source_connection_id,
            provider=m.provider,
            external_resource_id=m.external_resource_id,
            external_resource_name=m.external_resource_name,
            status=m.status,
            created_at=m.created_at,
        )
        for m in mappings
    ]
    return SourceMappingListResponse(items=items, total=len(items))


@router.post(
    "/projects/{project_id}/sources/mappings/{mapping_id}/sync",
    response_model=SourceSyncTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a source sync job",
)
def trigger_source_mapping_sync(
    project_id: uuid.UUID,
    mapping_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> SourceSyncTriggerResponse:
    from sqlalchemy import select

    mapping = session.execute(
        select(ProjectSourceMapping).where(
            ProjectSourceMapping.id == mapping_id,
            ProjectSourceMapping.project_id == project_id,
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise NotFoundError("Mapping not found.", code="MAPPING_NOT_FOUND")

    job = BackgroundJob(
        organisation_id=mapping.organisation_id,
        project_id=project_id,
        triggered_by_user_id=project_ctx.principal.user.id,
        job_type=BackgroundJobType.SOURCE_SYNC.value,
        status=BackgroundJobStatus.QUEUED.value,
        payload_json={"mapping_id": str(mapping.id), "provider": mapping.provider},
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    return SourceSyncTriggerResponse(
        id=job.id,
        status=job.status,
        job_type=job.job_type,
    )


@router.get(
    "/projects/{project_id}/sources/mappings/{mapping_id}/jobs",
    response_model=SourceSyncJobsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List background sync jobs for a mapping",
)
def list_source_mapping_jobs(
    project_id: uuid.UUID,
    mapping_id: uuid.UUID,
    project_ctx: Annotated[
        ProjectContext,
        Depends(require_project_permission("project.read")),
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> SourceSyncJobsListResponse:
    from sqlalchemy import select

    jobs = session.execute(
        select(BackgroundJob).where(
            BackgroundJob.project_id == project_id,
            BackgroundJob.job_type == BackgroundJobType.SOURCE_SYNC.value,
        ).order_by(BackgroundJob.created_at.desc())
    ).scalars().all()

    items = [
        SourceSyncJobItem(
            id=j.id,
            status="completed" if j.status == BackgroundJobStatus.SUCCEEDED.value else j.status,
            created_at=j.created_at,
            completed_at=j.completed_at,
        )
        for j in jobs
        if (j.payload_json or {}).get("mapping_id") == str(mapping_id)
    ]
    return SourceSyncJobsListResponse(items=items, total=len(items))
