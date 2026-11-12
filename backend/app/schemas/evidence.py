"""Pydantic schemas for the Evidence Workspace (Sources, Library, Details, Sync, Upload)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.enums import SourceProvider
from app.schemas.common import BaseSchema


# -----------------------------------------------------------------------------
# Panel A: Connected Sources & Project Source Mappings
# -----------------------------------------------------------------------------
class CreateSourceConnectionRequest(BaseSchema):
    """Register an external source connection (GitHub, Jira, or Slack)."""

    provider: SourceProvider
    account_identifier: str = Field(min_length=1, max_length=255)
    secret_token: str = Field(min_length=1, max_length=4096)
    scopes: list[str] = Field(default_factory=list)
    is_shared: bool = False


class UpdateSourceConnectionRequest(BaseSchema):
    """Modify scopes or sharing setting for an existing source connection."""

    is_shared: bool | None = None
    scopes: list[str] | None = None


class SourceConnectionResponse(BaseSchema):
    """Safe external connection response omitting encrypted credentials."""

    id: uuid.UUID
    organisation_id: uuid.UUID
    connected_by_id: uuid.UUID
    provider: str
    account_identifier: str
    connection_status: str
    scopes: list[str] = Field(default_factory=list)
    is_shared: bool = False
    created_at: datetime
    updated_at: datetime
    last_health_check_at: datetime | None = None


class SourceConnectionListResponse(BaseSchema):
    """List of connected sources accessible to the caller."""

    items: list[SourceConnectionResponse]
    total: int


class CreateProjectSourceMappingRequest(BaseSchema):
    """Link an external container (e.g. repo or Jira project) to a project workspace."""

    source_connection_id: uuid.UUID
    external_resource_id: str = Field(min_length=1, max_length=255)
    external_resource_name: str = Field(min_length=1, max_length=255)
    external_metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectSourceMappingResponse(BaseSchema):
    """Mapping representation linking a project workspace to an external source container."""

    id: uuid.UUID
    project_id: uuid.UUID
    source_connection_id: uuid.UUID
    external_resource_id: str
    external_resource_name: str
    sync_status: str
    last_synced_at: datetime | None = None
    sync_error: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    source_connection: SourceConnectionResponse | None = None


class ProjectSourceMappingListResponse(BaseSchema):
    """List of source mappings bound to a project."""

    items: list[ProjectSourceMappingResponse]
    total: int


# -----------------------------------------------------------------------------
# Panel B: Evidence Library
# -----------------------------------------------------------------------------
class EvidenceItemSummary(BaseSchema):
    """Compact summary of an evidence item for list views in Panel B."""

    id: uuid.UUID
    project_id: uuid.UUID
    provider: str
    record_type: str
    title: str
    external_source_id: str
    source_url: str | None = None
    author: str | None = None
    source_created_at: datetime | None = None
    ingested_at: datetime
    processing_status: str
    verification_status: str
    content_hash: str
    original_filename: str | None = None
    file_size_bytes: int | None = None
    chunk_count: int = 0


class EvidenceListResponse(BaseSchema):
    """Paginated search and filter response for Evidence Library (Panel B)."""

    items: list[EvidenceItemSummary]
    total: int
    offset: int
    limit: int
    total_by_provider: dict[str, int] = Field(default_factory=dict)
    total_by_status: dict[str, int] = Field(default_factory=dict)


class EvidenceLibraryMetricsResponse(BaseSchema):
    """High-level summary metrics across evidence in a project."""

    total_items: int
    total_documents: int
    total_code_artifacts: int
    total_tickets: int
    total_bytes: int
    last_synced_at: datetime | None = None


# -----------------------------------------------------------------------------
# Panel C: Evidence Details
# -----------------------------------------------------------------------------
class EvidenceChunkResponse(BaseSchema):
    """A single extracted chunk belonging to an evidence item."""

    chunk_index: int
    content_text: str
    page_number: int | None = None
    section_heading: str | None = None
    token_count: int | None = None


class DocumentFileResponse(BaseSchema):
    """Physical document metadata associated with an evidence item."""

    id: uuid.UUID
    original_filename: str
    file_format: str
    mime_type: str
    file_size_bytes: int
    page_count: int | None = None
    sha256_hash: str
    created_at: datetime


class EvidenceItemDetail(EvidenceItemSummary):
    """Comprehensive evidence record including full extracted content and chunks."""

    raw_metadata: dict[str, Any] | None = None
    chunks: list[EvidenceChunkResponse] = Field(default_factory=list)
    document_file: DocumentFileResponse | None = None
    source_resource_name: str | None = None
    can_download: bool = False
    download_url: str | None = None


# -----------------------------------------------------------------------------
# Document Upload & Processing
# -----------------------------------------------------------------------------
class DocumentUploadResponse(BaseSchema):
    """Immediate result of document file upload and extraction pipeline."""

    evidence_item_id: uuid.UUID
    document_file_id: uuid.UUID
    original_filename: str
    file_format: str
    mime_type: str
    file_size_bytes: int
    page_count: int | None
    chunk_count: int
    processing_status: str
    message: str


# -----------------------------------------------------------------------------
# Background Sync Jobs
# -----------------------------------------------------------------------------
class TriggerSyncRequest(BaseSchema):
    """Payload to trigger an asynchronous sync for a source mapping."""

    mapping_id: uuid.UUID


class SyncJobResponse(BaseSchema):
    """Status and details of an external source sync background job."""

    id: uuid.UUID
    project_id: uuid.UUID
    source_mapping_id: uuid.UUID | None
    job_type: str
    status: str
    attempt_count: int
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class SyncJobListResponse(BaseSchema):
    """List of sync jobs for a project or mapping."""

    items: list[SyncJobResponse]
    total: int
