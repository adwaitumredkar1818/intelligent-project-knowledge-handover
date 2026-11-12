"""Pydantic v2 request and response schemas for Phase 2.4B GitHub & Jira integrations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.evidence import BackgroundJobResponse


class UserSourceAuthorisationSummary(BaseSchema):
    """Non-secret summary of a user's delegated OAuth authorisation for a source connection."""

    id: uuid.UUID
    user_id: uuid.UUID
    provider: str
    external_user_id: str
    external_username: str | None
    external_email: str | None
    granted_scopes: list[str]
    status: str
    token_expires_at: datetime | None
    last_refreshed_at: datetime | None
    last_verified_at: datetime | None
    revoked_at: datetime | None
    last_error_code: str | None
    last_error_summary: str | None
    created_at: datetime
    updated_at: datetime


class SourceConnectionResponse(BaseSchema):
    """Public metadata for an organisation-scoped source connection without credentials."""

    id: uuid.UUID
    organisation_id: uuid.UUID
    provider: str
    display_name: str
    authorisation_mode: str
    external_workspace_id: str | None
    external_workspace_name: str | None
    external_workspace_url: str | None
    status: str
    created_by_user_id: uuid.UUID
    last_synced_at: datetime | None
    last_error_code: str | None
    last_error_summary: str | None
    metadata_json: dict[str, Any]
    disconnected_at: datetime | None
    created_at: datetime
    updated_at: datetime
    caller_authorisation: UserSourceAuthorisationSummary | None = None


class SourceConnectionListResponse(BaseSchema):
    """List of source connections visible inside one authorised organisation."""

    items: list[SourceConnectionResponse]
    total: int


class OAuthStartRequest(BaseSchema):
    """Optional parameters when starting a delegated OAuth 2.0 connection flow."""

    source_connection_id: uuid.UUID | None = None
    display_name: str | None = Field(default=None, max_length=200)
    redirect_after: str | None = Field(default=None, max_length=512)


class OAuthStartResponse(BaseSchema):
    """Server-generated OAuth authorisation URL bound to single-use state."""

    provider: str
    organisation_id: uuid.UUID
    source_connection_id: uuid.UUID | None
    authorisation_url: str
    expires_at: datetime
    state_id: uuid.UUID


class OAuthCallbackResponse(BaseSchema):
    """Completed delegated OAuth callback payload without raw tokens."""

    connection: SourceConnectionResponse
    authorisation: UserSourceAuthorisationSummary
    redirect_after: str | None = None
    discovered_sites_count: int | None = None


class GitHubRepositoryCandidate(BaseSchema):
    """Accessible GitHub repository discovered through the caller's delegated authorisation."""

    external_resource_id: str
    full_name: str
    name: str
    owner_login: str
    description: str | None = None
    default_branch: str | None = None
    visibility: str
    is_private: bool
    html_url: str | None = None
    updated_at: datetime | None = None
    permissions: dict[str, bool] = Field(default_factory=dict)


class GitHubRepositoryListResponse(BaseSchema):
    """Paginated list of GitHub repositories accessible to the calling user."""

    connection_id: uuid.UUID
    items: list[GitHubRepositoryCandidate]
    page: int
    per_page: int
    has_next_page: bool


class JiraSiteCandidate(BaseSchema):
    """Authorised Atlassian Cloud Jira site resolved via `/oauth/token/accessible-resources`."""

    cloud_id: str
    name: str
    url: str | None = None
    scopes: list[str] = Field(default_factory=list)
    avatar_url: str | None = None


class JiraSiteListResponse(BaseSchema):
    """Authorised Jira Cloud sites accessible to the calling user."""

    connection_id: uuid.UUID
    items: list[JiraSiteCandidate]
    total: int


class JiraProjectCandidate(BaseSchema):
    """Accessible Jira project inside a verified Jira Cloud site."""

    cloud_id: str
    external_resource_id: str
    key: str
    name: str
    project_type_key: str | None = None
    url: str | None = None
    is_private: bool | None = None
    style: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class JiraDiscoveryResponse(BaseSchema):
    """Accessible Jira Cloud sites and paginated projects for the calling user."""

    connection_id: uuid.UUID
    sites: list[JiraSiteCandidate]
    selected_cloud_id: str | None
    projects: list[JiraProjectCandidate]
    start_at: int
    max_results: int
    total: int
    is_last: bool


class SourceAccessPolicyResponse(BaseSchema):
    """Explicit visibility boundary governing access to mapped external evidence."""

    id: uuid.UUID
    organisation_id: uuid.UUID
    project_id: uuid.UUID
    source_connection_id: uuid.UUID
    provider: str
    scope_identifier: str
    visibility_policy: str
    sync_permission_status: str
    authorised_by_user_id: uuid.UUID | None
    allowed_user_ids: list[str]
    allowed_external_identities: list[dict[str, Any]]
    provider_visibility: str | None
    last_acl_verified_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CreateGitHubMappingRequest(BaseSchema):
    """Request to map one explicitly selected GitHub repository into a project workspace."""

    source_connection_id: uuid.UUID
    owner: str = Field(min_length=1, max_length=120)
    repo: str = Field(min_length=1, max_length=120)
    include_issues: bool = True
    include_pull_requests: bool = True
    include_commits: bool = True
    include_docs: bool = True
    include_discussions: bool = True
    restrict_to_verified_users: bool | None = None


class CreateJiraMappingRequest(BaseSchema):
    """Request to map one explicitly selected Jira Cloud project into a project workspace."""

    source_connection_id: uuid.UUID
    cloud_id: str = Field(min_length=1, max_length=255)
    project_key: str = Field(min_length=1, max_length=64)
    include_comments: bool = True
    include_worklogs: bool = True
    include_links: bool = True
    include_changelog: bool = True
    jql_filter: str | None = Field(default=None, max_length=500)


class ProjectSourceMappingResponse(BaseSchema):
    """Configured external source mapping bound to one platform project."""

    id: uuid.UUID
    organisation_id: uuid.UUID
    project_id: uuid.UUID
    source_connection_id: uuid.UUID
    source_access_policy_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    provider: str
    resource_type: str
    external_site_id: str
    external_resource_id: str
    external_resource_key: str
    external_resource_name: str
    external_resource_url: str | None
    default_branch: str | None
    provider_visibility: str | None
    status: str
    sync_config_json: dict[str, Any]
    last_synced_at: datetime | None
    last_sync_status: str | None
    last_error_code: str | None
    last_error_summary: str | None
    disabled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    access_policy: SourceAccessPolicyResponse | None = None


class ProjectSourceMappingListResponse(BaseSchema):
    """List of configured source mappings for a project."""

    items: list[ProjectSourceMappingResponse]
    total: int


class VerifySourceAccessRequest(BaseSchema):
    """Optional connection selection when verifying the caller's own external source access."""

    source_connection_id: uuid.UUID | None = None


class VerifySourceAccessResponse(BaseSchema):
    """Outcome of verifying the calling user's delegated access to a mapped source resource."""

    mapping_id: uuid.UUID
    policy_id: uuid.UUID
    verified: bool
    visibility_policy: str
    user_id: uuid.UUID
    external_user_id: str | None


class TriggerSyncRequest(BaseSchema):
    """Parameters for manually enqueueing a delegated source sync job."""

    sync_mode: Literal["initial", "incremental", "manual"] = "incremental"


class SourceSyncRunResponse(BaseSchema):
    """Durable execution summary of a single source sync run."""

    id: uuid.UUID
    organisation_id: uuid.UUID
    project_id: uuid.UUID
    project_source_mapping_id: uuid.UUID
    source_connection_id: uuid.UUID
    background_job_id: uuid.UUID | None
    triggered_by_user_id: uuid.UUID | None
    provider: str
    sync_mode: str
    status: str
    items_discovered: int
    items_created: int
    items_updated: int
    items_unchanged: int
    items_inaccessible: int
    items_failed: int
    warnings_json: list[str]
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    created_at: datetime
    updated_at: datetime


class TriggerSyncResponse(BaseSchema):
    """Created sync run and queued PostgreSQL background job."""

    sync_run: SourceSyncRunResponse
    job: BackgroundJobResponse


class SourceSyncHistoryResponse(BaseSchema):
    """Paginated sync run history for a project or mapping."""

    items: list[SourceSyncRunResponse]
    total: int
    limit: int
    offset: int


class CancelSyncResponse(BaseSchema):
    """Updated sync run and background job after explicit sync cancellation."""

    sync_run: SourceSyncRunResponse
    job: BackgroundJobResponse | None = None
