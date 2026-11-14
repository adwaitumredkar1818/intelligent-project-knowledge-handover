"""Application domain service for GitHub & Jira connections, discovery, mappings, and syncs."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import TypeVar

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.core.security import utc_now
from app.models.enums import (
    AuditOutcome,
    BackgroundJobType,
    IntegrationProvider,
    OrganisationStatus,
    ProjectSourceMappingStatus,
    ProjectStatus,
    SourceConnectionStatus,
    SourcePermissionVerificationStatus,
    SourceSyncRunStatus,
    UserSourceAuthorisationStatus,
)
from app.models.integration import (
    ProjectSourceMapping,
    SourceAccessPolicy,
    SourceConnection,
    SourceSyncRun,
    UserSourceAuthorisation,
)
from app.repositories.integration import IntegrationRepository
from app.repositories.job import BackgroundJobRepository
from app.schemas.integrations import (
    CancelSyncResponse,
    CreateGitHubMappingRequest,
    CreateJiraMappingRequest,
    GitHubRepositoryListResponse,
    JiraDiscoveryResponse,
    JiraProjectCandidate,
    JiraSiteCandidate,
    JiraSiteListResponse,
    OAuthCallbackResponse,
    OAuthStartResponse,
    ProjectSourceMappingListResponse,
    ProjectSourceMappingResponse,
    SourceAccessPolicyResponse,
    SourceConnectionListResponse,
    SourceConnectionResponse,
    SourceSyncHistoryResponse,
    SourceSyncRunResponse,
    TriggerSyncResponse,
    VerifySourceAccessResponse,
)
from app.services.audit import AuditService
from app.services.evidence import to_background_job_response
from app.services.integrations.access_policy import SourceAccessPolicyService
from app.services.integrations.errors import IntegrationAuthError, IntegrationProviderError
from app.services.integrations.github_client import GitHubClient
from app.services.integrations.jira_client import JiraClient
from app.services.integrations.oauth import SourceOAuthService, to_source_connection_response
from app.services.rbac import (
    AuthenticatedPrincipal,
    OrganisationContext,
    ProjectContext,
    RbacService,
)
from app.services.token_encryption import TokenEncryptionService

_T = TypeVar("_T")


def to_access_policy_response(policy: SourceAccessPolicy) -> SourceAccessPolicyResponse:
    """Map SourceAccessPolicy ORM row into public non-secret summary."""
    return SourceAccessPolicyResponse(
        id=policy.id,
        organisation_id=policy.organisation_id,
        project_id=policy.project_id,
        source_connection_id=policy.source_connection_id,
        provider=policy.provider,
        scope_identifier=policy.scope_identifier,
        visibility_policy=policy.visibility_policy,
        sync_permission_status=policy.sync_permission_status,
        authorised_by_user_id=policy.authorised_by_user_id,
        allowed_user_ids=list(policy.allowed_user_ids or []),
        allowed_external_identities=list(policy.allowed_external_identities or []),
        provider_visibility=policy.provider_visibility,
        last_acl_verified_at=policy.last_acl_verified_at,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


def to_mapping_response(mapping: ProjectSourceMapping) -> ProjectSourceMappingResponse:
    """Map ProjectSourceMapping ORM row with attached access policy boundary."""
    return ProjectSourceMappingResponse(
        id=mapping.id,
        organisation_id=mapping.organisation_id,
        project_id=mapping.project_id,
        source_connection_id=mapping.source_connection_id,
        source_access_policy_id=mapping.source_access_policy_id,
        created_by_user_id=mapping.created_by_user_id,
        provider=mapping.provider,
        resource_type=mapping.resource_type,
        external_site_id=mapping.external_site_id,
        external_resource_id=mapping.external_resource_id,
        external_resource_key=mapping.external_resource_key,
        external_resource_name=mapping.external_resource_name,
        external_resource_url=mapping.external_resource_url,
        default_branch=mapping.default_branch,
        provider_visibility=mapping.provider_visibility,
        status=mapping.status,
        sync_config_json=dict(mapping.sync_config_json or {}),
        last_synced_at=mapping.last_synced_at,
        last_sync_status=mapping.last_sync_status,
        last_error_code=mapping.last_error_code,
        last_error_summary=mapping.last_error_summary,
        disabled_at=mapping.disabled_at,
        created_at=mapping.created_at,
        updated_at=mapping.updated_at,
        access_policy=(
            to_access_policy_response(mapping.source_access_policy)
            if mapping.source_access_policy is not None
            else None
        ),
    )


def to_sync_run_response(run: SourceSyncRun) -> SourceSyncRunResponse:
    """Map SourceSyncRun ORM row into non-secret status DTO."""
    return SourceSyncRunResponse(
        id=run.id,
        organisation_id=run.organisation_id,
        project_id=run.project_id,
        project_source_mapping_id=run.project_source_mapping_id,
        source_connection_id=run.source_connection_id,
        background_job_id=run.background_job_id,
        triggered_by_user_id=run.triggered_by_user_id,
        provider=run.provider,
        sync_mode=run.sync_mode,
        status=run.status,
        items_discovered=run.items_discovered,
        items_created=run.items_created,
        items_updated=run.items_updated,
        items_unchanged=run.items_unchanged,
        items_inaccessible=run.items_inaccessible,
        items_failed=run.items_failed,
        warnings_json=list(run.warnings_json or []),
        error_code=run.error_code,
        error_message=run.error_message,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_ms=run.duration_ms,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


class SourceIntegrationService:
    """Coordinates delegated source connections, discovery, mappings, ACL checks, and syncs."""

    def __init__(
        self,
        *,
        session: Session,
        settings: Settings,
        integration_repo: IntegrationRepository,
        job_repository: BackgroundJobRepository,
        token_encryption: TokenEncryptionService,
        rbac_service: RbacService,
        audit_service: AuditService,
        http_transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._repo = integration_repo
        self._job_repo = job_repository
        self._rbac = rbac_service
        self._audit = audit_service
        self._access_policy = SourceAccessPolicyService()
        self._oauth = SourceOAuthService(
            session=session,
            settings=settings,
            integration_repo=integration_repo,
            token_encryption=token_encryption,
            rbac_service=rbac_service,
            audit_service=audit_service,
            http_transport=http_transport,
        )
        self._github = GitHubClient(settings=settings, transport=http_transport)
        self._jira = JiraClient(settings=settings, transport=http_transport)

    def _require_org_active(self, organisation_status: str) -> None:
        if organisation_status != OrganisationStatus.ACTIVE.value:
            raise ConflictError(
                f"Organisation is '{organisation_status}' and cannot modify source integrations.",
                code="ORGANISATION_NOT_ACTIVE",
            )

    def _require_project_mutable(self, project_ctx: ProjectContext) -> None:
        self._require_org_active(project_ctx.organisation.status)
        if project_ctx.project.status == ProjectStatus.ARCHIVED.value:
            raise ConflictError(
                "Project workspace is archived and cannot modify source integrations.",
                code="PROJECT_ARCHIVED",
            )

    def _execute_with_caller_token(
        self,
        *,
        auth: UserSourceAuthorisation,
        fn: Callable[[str, UserSourceAuthorisation], _T],
    ) -> _T:
        """Run an external provider API call strictly under caller's own token with 401 refresh."""
        try:
            access_token, fresh_auth = self._oauth.get_valid_access_token(authorisation_id=auth.id)
        except IntegrationAuthError as exc:
            raise ConflictError(exc.message, code=exc.code) from exc

        try:
            return fn(access_token, fresh_auth)
        except IntegrationAuthError as exc:
            if exc.status_code != 401:
                raise ConflictError(exc.message, code=exc.code) from exc
            try:
                refreshed_token, refreshed_auth = self._oauth.refresh_access_token(
                    authorisation_id=fresh_auth.id,
                    force=True,
                )
            except IntegrationAuthError as refresh_exc:
                raise ConflictError(refresh_exc.message, code=refresh_exc.code) from refresh_exc
            try:
                return fn(refreshed_token, refreshed_auth)
            except IntegrationAuthError as retry_exc:
                raise ConflictError(retry_exc.message, code=retry_exc.code) from retry_exc

    def _resolve_caller_connection_and_auth(
        self,
        *,
        connection_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
        expected_provider: str | None = None,
    ) -> tuple[SourceConnection, OrganisationContext, UserSourceAuthorisation]:
        connection = self._repo.get_connection_by_id(connection_id)
        if connection is None:
            raise NotFoundError(
                "Source connection was not found.",
                code="SOURCE_CONNECTION_NOT_FOUND",
            )
        try:
            org_ctx = self._rbac.resolve_organisation_context(
                organisation_id=connection.organisation_id,
                principal=principal,
            )
        except NotFoundError as exc:
            raise NotFoundError(
                "Source connection was not found.",
                code="SOURCE_CONNECTION_NOT_FOUND",
            ) from exc

        if expected_provider is not None and connection.provider != expected_provider:
            raise BadRequestError(
                f"Source connection provider '{connection.provider}' does not match "
                f"'{expected_provider}'.",
                code="PROVIDER_MISMATCH",
            )
        if connection.status == SourceConnectionStatus.DISCONNECTED.value:
            raise ConflictError(
                "Source connection has been disconnected.",
                code="CONNECTION_DISCONNECTED",
            )
        if connection.provider.strip().lower() == "slack":
            raise ConflictError(
                "Slack integration is disabled pending governance approval.",
                code="SLACK_INTEGRATION_DISABLED",
            )

        active_auth = self._repo.get_active_authorisation(
            source_connection_id=connection.id,
            user_id=principal.user.id,
        )
        if active_auth is None:
            latest = self._repo.get_latest_authorisation_for_connection(
                source_connection_id=connection.id,
                user_id=principal.user.id,
            )
            self._audit.record_event(
                event_type="integration.access_denied",
                resource_type="source_connection",
                actor_user_id=principal.user.id,
                organisation_id=connection.organisation_id,
                resource_id=str(connection.id),
                outcome=AuditOutcome.DENIED.value,
                metadata={
                    "provider": connection.provider,
                    "reason": (
                        f"caller_auth_{latest.status}" if latest else "caller_auth_missing"
                    ),
                },
                message=(
                    "Denied delegated source call because caller lacks active OAuth credentials."
                ),
                level=logging.WARNING,
            )
            self._session.commit()
            if latest is not None and latest.status in {
                UserSourceAuthorisationStatus.REVOKED.value,
                UserSourceAuthorisationStatus.EXPIRED.value,
            }:
                raise ConflictError(
                    "Your delegated source authorisation is revoked or expired; "
                    "please re-authorise.",
                    code="SOURCE_AUTHORISATION_REVOKED",
                )
            raise ForbiddenError(
                "You must connect your own delegated OAuth account for this source first.",
                code="SOURCE_AUTHORISATION_REQUIRED",
            )
        return connection, org_ctx, active_auth

    def list_organisation_connections(
        self,
        *,
        org_ctx: OrganisationContext,
        provider: str | None = None,
    ) -> SourceConnectionListResponse:
        normalized_provider: str | None = None
        if provider is not None:
            normalized_provider = provider.strip().lower()
            if normalized_provider not in {
                IntegrationProvider.GITHUB.value,
                IntegrationProvider.JIRA.value,
            }:
                raise BadRequestError(
                    f"Unsupported provider filter '{provider}'.",
                    code="UNSUPPORTED_PROVIDER",
                )

        connections = self._repo.list_connections_for_organisation(
            organisation_id=org_ctx.organisation.id,
            provider=normalized_provider,
        )
        items = [
            to_source_connection_response(
                conn,
                caller_authorisation=self._repo.get_latest_authorisation_for_connection(
                    source_connection_id=conn.id,
                    user_id=org_ctx.principal.user.id,
                ),
            )
            for conn in connections
        ]
        return SourceConnectionListResponse(items=items, total=len(items))

    def start_oauth(
        self,
        *,
        org_ctx: OrganisationContext,
        provider: str,
        display_name: str | None = None,
        redirect_after: str | None = None,
        source_connection_id: uuid.UUID | None = None,
    ) -> OAuthStartResponse:
        self._require_org_active(org_ctx.organisation.status)
        if source_connection_id is None:
            can_create = (
                org_ctx.has_permission("organisation.manage")
                or org_ctx.has_permission("organisation.projects.create")
                or self._repo.user_has_project_contribution_in_org(
                    organisation_id=org_ctx.organisation.id,
                    user_id=org_ctx.principal.user.id,
                )
            )
            if not can_create:
                raise ForbiddenError(
                    "You do not have permission to create organisation source connections.",
                    code="FORBIDDEN",
                )
        return self._oauth.start_oauth(
            org_ctx=org_ctx,
            provider=provider,
            display_name=display_name,
            redirect_after=redirect_after,
            source_connection_id=source_connection_id,
        )

    def complete_oauth_callback(
        self,
        *,
        provider: str,
        principal: AuthenticatedPrincipal,
        code: str | None = None,
        state: str | None = None,
        oauth_error: str | None = None,
        oauth_error_description: str | None = None,
    ) -> OAuthCallbackResponse:
        return self._oauth.complete_oauth_callback(
            provider=provider,
            principal=principal,
            code=code,
            state=state,
            oauth_error=oauth_error,
            oauth_error_description=oauth_error_description,
        )

    def disconnect_connection(
        self,
        *,
        connection_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
    ) -> SourceConnectionResponse:
        connection = self._repo.get_connection_by_id(connection_id)
        if connection is None:
            raise NotFoundError(
                "Source connection was not found.",
                code="SOURCE_CONNECTION_NOT_FOUND",
            )
        try:
            org_ctx = self._rbac.resolve_organisation_context(
                organisation_id=connection.organisation_id,
                principal=principal,
            )
        except NotFoundError as exc:
            raise NotFoundError(
                "Source connection was not found.",
                code="SOURCE_CONNECTION_NOT_FOUND",
            ) from exc

        can_disconnect = (
            org_ctx.has_permission("organisation.manage")
            or org_ctx.has_permission("organisation.projects.create")
            or connection.created_by_user_id == principal.user.id
        )
        if not can_disconnect:
            raise ForbiddenError(
                "You do not have permission to disconnect this source connection.",
                code="FORBIDDEN",
            )
        if connection.status == SourceConnectionStatus.DISCONNECTED.value:
            raise ConflictError(
                "Source connection is already disconnected.",
                code="CONNECTION_ALREADY_DISCONNECTED",
            )

        now = utc_now()
        connection.status = SourceConnectionStatus.DISCONNECTED.value
        connection.disconnected_at = now
        connection.disconnected_by_user_id = principal.user.id

        revoked_count = self._repo.revoke_all_authorisations_for_connection(
            source_connection_id=connection.id,
            now=now,
            reason_code="CONNECTION_DISCONNECTED",
            reason_summary="Parent source connection was disconnected.",
        )
        disabled_mappings = self._repo.disconnect_mappings_for_connection(
            source_connection_id=connection.id,
            now=now,
        )
        self._audit.record_event(
            event_type="integration.connection_disconnected",
            resource_type="source_connection",
            actor_user_id=principal.user.id,
            organisation_id=connection.organisation_id,
            resource_id=str(connection.id),
            metadata={
                "provider": connection.provider,
                "revoked_authorisations": revoked_count,
                "disconnected_mappings": disabled_mappings,
            },
            message="Disconnected source connection and revoked delegated user tokens.",
        )
        self._session.commit()
        self._session.refresh(connection)
        latest_auth = self._repo.get_latest_authorisation_for_connection(
            source_connection_id=connection.id,
            user_id=principal.user.id,
        )
        return to_source_connection_response(connection, caller_authorisation=latest_auth)

    def revoke_my_authorisation(
        self,
        *,
        connection_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
    ) -> SourceConnectionResponse:
        connection = self._repo.get_connection_by_id(connection_id)
        if connection is None:
            raise NotFoundError(
                "Source connection was not found.",
                code="SOURCE_CONNECTION_NOT_FOUND",
            )
        try:
            self._rbac.resolve_organisation_context(
                organisation_id=connection.organisation_id,
                principal=principal,
            )
        except NotFoundError as exc:
            raise NotFoundError(
                "Source connection was not found.",
                code="SOURCE_CONNECTION_NOT_FOUND",
            ) from exc

        auth = self._repo.get_active_authorisation(
            source_connection_id=connection.id,
            user_id=principal.user.id,
        )
        if auth is None:
            raise NotFoundError(
                "No active delegated source authorisation found for the current user.",
                code="SOURCE_AUTHORISATION_NOT_FOUND",
            )

        now = utc_now()
        auth.status = UserSourceAuthorisationStatus.REVOKED.value
        auth.revoked_at = now
        auth.last_error_code = "REVOKED_BY_USER"
        auth.last_error_summary = "User explicitly revoked delegated source authorisation."
        self._audit.record_event(
            event_type="integration.authorisation_revoked",
            resource_type="user_source_authorisation",
            actor_user_id=principal.user.id,
            organisation_id=connection.organisation_id,
            resource_id=str(auth.id),
            metadata={"connection_id": str(connection.id), "provider": connection.provider},
            message="User revoked their own delegated source OAuth authorisation.",
        )
        self._session.commit()
        self._session.refresh(auth)
        return to_source_connection_response(connection, caller_authorisation=auth)

    def discover_github_repositories(
        self,
        *,
        connection_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
        page: int = 1,
        per_page: int = 30,
    ) -> GitHubRepositoryListResponse:
        connection, _, auth = self._resolve_caller_connection_and_auth(
            connection_id=connection_id,
            principal=principal,
            expected_provider=IntegrationProvider.GITHUB.value,
        )
        try:
            items, has_next = self._execute_with_caller_token(
                auth=auth,
                fn=lambda token, _a: self._github.list_repositories(
                    access_token=token,
                    page=page,
                    per_page=per_page,
                ),
            )
        except IntegrationProviderError as exc:
            raise ServiceUnavailableError(exc.message, code=exc.code) from exc

        self._audit.record_event(
            event_type="integration.discovery_executed",
            resource_type="source_connection",
            actor_user_id=principal.user.id,
            organisation_id=connection.organisation_id,
            resource_id=str(connection.id),
            metadata={"provider": "github", "page": page, "returned_count": len(items)},
            message="Executed delegated GitHub repository discovery.",
        )
        self._session.commit()
        return GitHubRepositoryListResponse(
            connection_id=connection.id,
            items=items,
            page=page,
            per_page=per_page,
            has_next_page=has_next,
        )

    def discover_jira_sites(
        self,
        *,
        connection_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
    ) -> JiraSiteListResponse:
        connection, _, auth = self._resolve_caller_connection_and_auth(
            connection_id=connection_id,
            principal=principal,
            expected_provider=IntegrationProvider.JIRA.value,
        )
        try:
            sites = self._execute_with_caller_token(
                auth=auth,
                fn=lambda token, _a: self._jira.list_accessible_sites(access_token=token),
            )
        except IntegrationProviderError as exc:
            raise ServiceUnavailableError(exc.message, code=exc.code) from exc

        meta = dict(auth.metadata_json or {})
        meta["accessible_sites"] = [s.model_dump(mode="json") for s in sites]
        auth.metadata_json = meta
        self._audit.record_event(
            event_type="integration.discovery_executed",
            resource_type="source_connection",
            actor_user_id=principal.user.id,
            organisation_id=connection.organisation_id,
            resource_id=str(connection.id),
            metadata={"provider": "jira", "target": "sites", "returned_count": len(sites)},
            message="Executed delegated Jira Cloud accessible-sites discovery.",
        )
        self._session.commit()
        return JiraSiteListResponse(connection_id=connection.id, items=sites, total=len(sites))

    def discover_jira_projects(
        self,
        *,
        connection_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
        cloud_id: str | None = None,
        start_at: int = 0,
        max_results: int = 50,
        query: str | None = None,
    ) -> JiraDiscoveryResponse:
        connection, _, auth = self._resolve_caller_connection_and_auth(
            connection_id=connection_id,
            principal=principal,
            expected_provider=IntegrationProvider.JIRA.value,
        )
        try:
            sites: list[JiraSiteCandidate] = self._execute_with_caller_token(
                auth=auth,
                fn=lambda token, _a: self._jira.list_accessible_sites(access_token=token),
            )
        except IntegrationProviderError as exc:
            raise ServiceUnavailableError(exc.message, code=exc.code) from exc

        if not sites:
            return JiraDiscoveryResponse(
                connection_id=connection.id,
                sites=[],
                selected_cloud_id=None,
                projects=[],
                start_at=start_at,
                max_results=max_results,
                total=0,
                is_last=True,
            )

        selected_site: JiraSiteCandidate | None
        if cloud_id:
            selected_site = next((s for s in sites if s.cloud_id == cloud_id), None)
            if selected_site is None:
                raise ForbiddenError(
                    "Requested Jira Cloud site is not authorised for your Atlassian account.",
                    code="JIRA_SITE_NOT_AUTHORISED",
                )
        else:
            selected_site = sites[0]

        try:
            result = self._execute_with_caller_token(
                auth=auth,
                fn=lambda token, _a: self._jira.search_projects(
                    access_token=token,
                    cloud_id=selected_site.cloud_id,
                    start_at=start_at,
                    max_results=max_results,
                    query=query,
                ),
            )
        except IntegrationProviderError as exc:
            raise ServiceUnavailableError(exc.message, code=exc.code) from exc

        self._audit.record_event(
            event_type="integration.discovery_executed",
            resource_type="source_connection",
            actor_user_id=principal.user.id,
            organisation_id=connection.organisation_id,
            resource_id=str(connection.id),
            metadata={
                "provider": "jira",
                "cloud_id": selected_site.cloud_id,
                "returned_count": len(result.projects),
            },
            message="Executed delegated Jira project discovery.",
        )
        self._session.commit()
        return JiraDiscoveryResponse(
            connection_id=connection.id,
            sites=sites,
            selected_cloud_id=selected_site.cloud_id,
            projects=result.projects,
            start_at=result.start_at,
            max_results=result.max_results,
            total=result.total,
            is_last=result.is_last,
        )

    def list_project_mappings(
        self,
        *,
        project_ctx: ProjectContext,
        include_disabled: bool = True,
    ) -> ProjectSourceMappingListResponse:
        mappings = self._repo.list_mappings_for_project(
            project_id=project_ctx.project.id,
            include_disabled=include_disabled,
        )
        return ProjectSourceMappingListResponse(
            items=[to_mapping_response(m) for m in mappings],
            total=len(mappings),
        )

    def create_github_mapping(
        self,
        *,
        project_ctx: ProjectContext,
        request: CreateGitHubMappingRequest,
    ) -> ProjectSourceMappingResponse:
        self._require_project_mutable(project_ctx)
        connection, _, auth = self._resolve_caller_connection_and_auth(
            connection_id=request.source_connection_id,
            principal=project_ctx.principal,
            expected_provider=IntegrationProvider.GITHUB.value,
        )
        if connection.organisation_id != project_ctx.organisation.id:
            raise NotFoundError(
                "Source connection was not found.",
                code="SOURCE_CONNECTION_NOT_FOUND",
            )

        owner = request.owner.strip()
        repo = request.repo.strip()
        try:
            allowed, repo_candidate = self._execute_with_caller_token(
                auth=auth,
                fn=lambda token, _a: self._github.verify_repository_access(
                    access_token=token,
                    owner=owner,
                    repo=repo,
                ),
            )
        except IntegrationProviderError as exc:
            raise ServiceUnavailableError(exc.message, code=exc.code) from exc

        if not allowed or repo_candidate is None:
            self._audit.record_event(
                event_type="integration.access_denied",
                resource_type="source_connection",
                actor_user_id=project_ctx.principal.user.id,
                organisation_id=project_ctx.organisation.id,
                project_id=project_ctx.project.id,
                resource_id=str(connection.id),
                outcome=AuditOutcome.DENIED.value,
                metadata={"provider": "github", "target": f"{owner}/{repo}"},
                message="Denied GitHub mapping because caller lacks repository access.",
                level=logging.WARNING,
            )
            self._session.commit()
            raise ForbiddenError(
                f"Your delegated GitHub account cannot access repository '{owner}/{repo}'.",
                code="SOURCE_RESOURCE_INACCESSIBLE",
            )

        existing = self._repo.find_active_mapping(
            project_id=project_ctx.project.id,
            provider="github",
            external_site_id="github.com",
            external_resource_id=repo_candidate.external_resource_id,
        )
        if existing is not None:
            raise ConflictError(
                f"GitHub repository '{repo_candidate.full_name}' is already mapped "
                "to this project.",
                code="SOURCE_MAPPING_ALREADY_EXISTS",
            )

        now = utc_now()
        classification = self._access_policy.classify_github_repository(
            visibility=repo_candidate.visibility,
            is_private=repo_candidate.is_private,
            restrict_to_verified_users=request.restrict_to_verified_users,
        )
        policy = self._repo.upsert_access_policy(
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            source_connection_id=connection.id,
            provider="github",
            scope_identifier=f"github.com:{repo_candidate.external_resource_id}",
            visibility_policy=classification.visibility_policy,
            sync_permission_status=SourcePermissionVerificationStatus.VERIFIED.value,
            authorised_by_user_id=project_ctx.principal.user.id,
            verified_user_id=project_ctx.principal.user.id,
            external_identity={
                "provider": "github",
                "external_user_id": auth.external_user_id,
                "external_username": auth.external_username,
            },
            provider_visibility=repo_candidate.visibility,
            verified_at=now,
        )

        mapping = self._repo.create_mapping(
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            source_connection_id=connection.id,
            source_access_policy_id=policy.id,
            created_by_user_id=project_ctx.principal.user.id,
            provider="github",
            resource_type="github_repository",
            external_site_id="github.com",
            external_resource_id=repo_candidate.external_resource_id,
            external_resource_key=repo_candidate.full_name,
            external_resource_name=repo_candidate.name,
            external_resource_url=repo_candidate.html_url,
            default_branch=repo_candidate.default_branch,
            provider_visibility=repo_candidate.visibility,
            sync_config_json={
                "include_issues": request.include_issues,
                "include_pull_requests": request.include_pull_requests,
                "include_commits": request.include_commits,
                "include_docs": request.include_docs,
                "include_discussions": request.include_discussions,
                "restrict_to_verified_users": bool(request.restrict_to_verified_users),
            },
        )
        self._audit.record_event(
            event_type="integration.mapping_created",
            resource_type="project_source_mapping",
            actor_user_id=project_ctx.principal.user.id,
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            resource_id=str(mapping.id),
            metadata={
                "provider": "github",
                "repository": repo_candidate.full_name,
                "visibility_policy": policy.visibility_policy,
            },
            message=f"Mapped GitHub repository '{repo_candidate.full_name}' to project.",
        )
        self._session.commit()
        refreshed = self._repo.get_mapping_by_id(mapping.id) or mapping
        return to_mapping_response(refreshed)

    def create_jira_mapping(
        self,
        *,
        project_ctx: ProjectContext,
        request: CreateJiraMappingRequest,
    ) -> ProjectSourceMappingResponse:
        self._require_project_mutable(project_ctx)
        if request.jql_filter:
            lowered = request.jql_filter.lower()
            if ";" in lowered or "\n" in lowered or "\r" in lowered or "order by" in lowered:
                raise BadRequestError(
                    "Custom jql_filter must not contain semicolons, newlines, or ORDER BY.",
                    code="INVALID_JQL_FILTER",
                )

        connection, _, auth = self._resolve_caller_connection_and_auth(
            connection_id=request.source_connection_id,
            principal=project_ctx.principal,
            expected_provider=IntegrationProvider.JIRA.value,
        )
        if connection.organisation_id != project_ctx.organisation.id:
            raise NotFoundError(
                "Source connection was not found.",
                code="SOURCE_CONNECTION_NOT_FOUND",
            )

        cloud_id = request.cloud_id.strip()
        project_key = request.project_key.strip()

        def _verify_jira_site_and_project(
            token: str,
            _a: UserSourceAuthorisation,
        ) -> tuple[JiraSiteCandidate | None, JiraProjectCandidate | None]:
            sites = self._jira.list_accessible_sites(access_token=token)
            site = next((s for s in sites if s.cloud_id == cloud_id), None)
            if site is None:
                return None, None
            ok, cand = self._jira.verify_project_access(
                access_token=token,
                cloud_id=cloud_id,
                project_key_or_id=project_key,
            )
            return site, (cand if ok else None)

        try:
            matched_site, jira_candidate = self._execute_with_caller_token(
                auth=auth,
                fn=_verify_jira_site_and_project,
            )
        except IntegrationProviderError as exc:
            raise ServiceUnavailableError(exc.message, code=exc.code) from exc

        if matched_site is None or jira_candidate is None:
            self._audit.record_event(
                event_type="integration.access_denied",
                resource_type="source_connection",
                actor_user_id=project_ctx.principal.user.id,
                organisation_id=project_ctx.organisation.id,
                project_id=project_ctx.project.id,
                resource_id=str(connection.id),
                outcome=AuditOutcome.DENIED.value,
                metadata={
                    "provider": "jira",
                    "cloud_id": cloud_id,
                    "project_key": project_key,
                },
                message="Denied Jira project mapping because caller lacks site or project access.",
                level=logging.WARNING,
            )
            self._session.commit()
            raise ForbiddenError(
                f"Your delegated Jira account cannot access project '{project_key}' "
                f"on site '{cloud_id}'.",
                code="SOURCE_RESOURCE_INACCESSIBLE",
            )

        existing = self._repo.find_active_mapping(
            project_id=project_ctx.project.id,
            provider="jira",
            external_site_id=cloud_id,
            external_resource_id=jira_candidate.external_resource_id,
        )
        if existing is not None:
            raise ConflictError(
                f"Jira project '{jira_candidate.key}' is already mapped to this project.",
                code="SOURCE_MAPPING_ALREADY_EXISTS",
            )

        now = utc_now()
        classification = self._access_policy.classify_jira_project()
        policy = self._repo.upsert_access_policy(
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            source_connection_id=connection.id,
            provider="jira",
            scope_identifier=f"{cloud_id}:{jira_candidate.key}",
            visibility_policy=classification.visibility_policy,
            sync_permission_status=SourcePermissionVerificationStatus.VERIFIED.value,
            authorised_by_user_id=project_ctx.principal.user.id,
            verified_user_id=project_ctx.principal.user.id,
            external_identity={
                "provider": "jira",
                "external_user_id": auth.external_user_id,
                "external_username": auth.external_username,
                "cloud_id": cloud_id,
            },
            provider_visibility=(
                "private" if jira_candidate.is_private else "jira_project_acl"
            ),
            verified_at=now,
            metadata_json={"site_url": matched_site.url, "site_name": matched_site.name},
        )

        mapping = self._repo.create_mapping(
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            source_connection_id=connection.id,
            source_access_policy_id=policy.id,
            created_by_user_id=project_ctx.principal.user.id,
            provider="jira",
            resource_type="jira_project",
            external_site_id=cloud_id,
            external_resource_id=jira_candidate.external_resource_id,
            external_resource_key=jira_candidate.key,
            external_resource_name=jira_candidate.name,
            external_resource_url=jira_candidate.url or matched_site.url,
            default_branch=None,
            provider_visibility="jira_project_acl",
            sync_config_json={
                "site_url": matched_site.url,
                "site_name": matched_site.name,
                "include_comments": request.include_comments,
                "include_worklogs": request.include_worklogs,
                "include_links": request.include_links,
                "include_changelog": request.include_changelog,
                "jql_filter": request.jql_filter.strip() if request.jql_filter else None,
            },
        )
        self._audit.record_event(
            event_type="integration.mapping_created",
            resource_type="project_source_mapping",
            actor_user_id=project_ctx.principal.user.id,
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            resource_id=str(mapping.id),
            metadata={
                "provider": "jira",
                "cloud_id": cloud_id,
                "project_key": jira_candidate.key,
                "visibility_policy": policy.visibility_policy,
            },
            message=f"Mapped Jira project '{jira_candidate.key}' to platform project.",
        )
        self._session.commit()
        refreshed = self._repo.get_mapping_by_id(mapping.id) or mapping
        return to_mapping_response(refreshed)

    def disable_mapping(
        self,
        *,
        project_ctx: ProjectContext,
        mapping_id: uuid.UUID,
    ) -> ProjectSourceMappingResponse:
        self._require_project_mutable(project_ctx)
        mapping = self._repo.get_mapping_by_id(mapping_id)
        if mapping is None or mapping.project_id != project_ctx.project.id:
            raise NotFoundError(
                "Project source mapping was not found.",
                code="SOURCE_MAPPING_NOT_FOUND",
            )
        if mapping.status == ProjectSourceMappingStatus.DISABLED.value:
            return to_mapping_response(mapping)

        now = utc_now()
        mapping.status = ProjectSourceMappingStatus.DISABLED.value
        mapping.disabled_at = now
        self._audit.record_event(
            event_type="integration.mapping_disabled",
            resource_type="project_source_mapping",
            actor_user_id=project_ctx.principal.user.id,
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            resource_id=str(mapping.id),
            metadata={
                "provider": mapping.provider,
                "resource_key": mapping.external_resource_key,
            },
            message="Disabled project source mapping while retaining historical evidence.",
        )
        self._session.commit()
        refreshed = self._repo.get_mapping_by_id(mapping.id) or mapping
        return to_mapping_response(refreshed)

    def verify_caller_source_access(
        self,
        *,
        project_ctx: ProjectContext,
        mapping_id: uuid.UUID,
        source_connection_id: uuid.UUID | None = None,
    ) -> VerifySourceAccessResponse:
        """Verify caller's own delegated access with the provider and update SourceAccessPolicy."""
        mapping = self._repo.get_mapping_by_id(mapping_id)
        if mapping is None or mapping.project_id != project_ctx.project.id:
            raise NotFoundError(
                "Project source mapping was not found.",
                code="SOURCE_MAPPING_NOT_FOUND",
            )
        target_conn_id = source_connection_id or mapping.source_connection_id
        connection, _, auth = self._resolve_caller_connection_and_auth(
            connection_id=target_conn_id,
            principal=project_ctx.principal,
            expected_provider=mapping.provider,
        )
        policy = mapping.source_access_policy
        if policy is None:
            raise NotFoundError("Source access policy not found.", code="SOURCE_POLICY_NOT_FOUND")

        now = utc_now()
        verified = False
        try:
            if mapping.provider == IntegrationProvider.GITHUB.value:
                owner, repo = mapping.external_resource_key.split("/", 1)
                verified, _ = self._execute_with_caller_token(
                    auth=auth,
                    fn=lambda token, _a: self._github.verify_repository_access(
                        access_token=token,
                        owner=owner,
                        repo=repo,
                    ),
                )
            else:
                cloud_id = mapping.external_site_id
                project_key = mapping.external_resource_key

                def _check_jira(token: str, _a: UserSourceAuthorisation) -> bool:
                    sites = self._jira.list_accessible_sites(access_token=token)
                    if not any(s.cloud_id == cloud_id for s in sites):
                        return False
                    ok, _ = self._jira.verify_project_access(
                        access_token=token,
                        cloud_id=cloud_id,
                        project_key_or_id=project_key,
                    )
                    return ok

                verified = self._execute_with_caller_token(auth=auth, fn=_check_jira)
        except IntegrationProviderError as exc:
            raise ServiceUnavailableError(exc.message, code=exc.code) from exc

        if verified:
            self._repo.add_verified_user_to_policy(
                policy=policy,
                user_id=project_ctx.principal.user.id,
                external_identity={
                    "provider": mapping.provider,
                    "external_user_id": auth.external_user_id,
                    "external_username": auth.external_username,
                },
                verified_at=now,
            )
            # Also evaluate any Jira issue-level security sub-policies individually
            if mapping.provider == IntegrationProvider.JIRA.value:
                sub_prefix = f"{mapping.external_site_id}:{mapping.external_resource_key}:security:"
                sub_policies = self._repo.list_policies_for_project_scope_prefix(
                    project_id=project_ctx.project.id,
                    source_connection_id=connection.id,
                    scope_prefix=sub_prefix,
                )
                for sub_pol in sub_policies:
                    sample_key = (sub_pol.metadata_json or {}).get("sample_issue_key")
                    if isinstance(sample_key, str) and sample_key:
                        target_issue_key = sample_key

                        def _verify_sub_issue(
                            token: str,
                            _a: UserSourceAuthorisation,
                            issue_key: str = target_issue_key,
                        ) -> bool:
                            return self._jira.verify_issue_access(
                                access_token=token,
                                cloud_id=mapping.external_site_id,
                                issue_key=issue_key,
                            )

                        issue_ok = self._execute_with_caller_token(
                            auth=auth,
                            fn=_verify_sub_issue,
                        )
                        if issue_ok:
                            self._repo.add_verified_user_to_policy(
                                policy=sub_pol,
                                user_id=project_ctx.principal.user.id,
                                external_identity={
                                    "provider": "jira",
                                    "external_user_id": auth.external_user_id,
                                    "external_username": auth.external_username,
                                },
                                verified_at=now,
                            )
                        else:
                            self._repo.remove_user_from_policy(
                                policy=sub_pol,
                                user_id=project_ctx.principal.user.id,
                                verified_at=now,
                            )

            self._audit.record_event(
                event_type="integration.access_verified",
                resource_type="source_access_policy",
                actor_user_id=project_ctx.principal.user.id,
                organisation_id=project_ctx.organisation.id,
                project_id=project_ctx.project.id,
                resource_id=str(policy.id),
                metadata={
                    "mapping_id": str(mapping.id),
                    "provider": mapping.provider,
                    "external_user_id": auth.external_user_id,
                },
                message="Verified caller delegated source permissions against external provider.",
            )
        else:
            self._repo.remove_user_from_policy(
                policy=policy,
                user_id=project_ctx.principal.user.id,
                verified_at=now,
            )
            self._audit.record_event(
                event_type="integration.access_denied",
                resource_type="source_access_policy",
                actor_user_id=project_ctx.principal.user.id,
                organisation_id=project_ctx.organisation.id,
                project_id=project_ctx.project.id,
                resource_id=str(policy.id),
                outcome=AuditOutcome.DENIED.value,
                metadata={
                    "mapping_id": str(mapping.id),
                    "provider": mapping.provider,
                    "external_user_id": auth.external_user_id,
                },
                message="Provider denied caller access to mapped source resource.",
                level=logging.WARNING,
            )

        auth.last_verified_at = now
        self._session.commit()
        return VerifySourceAccessResponse(
            mapping_id=mapping.id,
            policy_id=policy.id,
            verified=verified,
            visibility_policy=policy.visibility_policy,
            user_id=project_ctx.principal.user.id,
            external_user_id=auth.external_user_id,
        )

    def trigger_sync(
        self,
        *,
        project_ctx: ProjectContext,
        mapping_id: uuid.UUID,
        sync_mode: str = "incremental",
    ) -> TriggerSyncResponse:
        self._require_project_mutable(project_ctx)
        mapping = self._repo.get_mapping_by_id(mapping_id)
        if mapping is None or mapping.project_id != project_ctx.project.id:
            raise NotFoundError(
                "Project source mapping was not found.",
                code="SOURCE_MAPPING_NOT_FOUND",
            )
        if mapping.status not in {
            ProjectSourceMappingStatus.ACTIVE.value,
            ProjectSourceMappingStatus.ERROR.value,
        }:
            raise ConflictError(
                f"Source mapping is '{mapping.status}' and cannot run new syncs.",
                code="MAPPING_NOT_ACTIVE",
            )

        _, _, auth = self._resolve_caller_connection_and_auth(
            connection_id=mapping.source_connection_id,
            principal=project_ctx.principal,
            expected_provider=mapping.provider,
        )

        if self._repo.has_active_sync_run_for_mapping(
            mapping.id
        ) or self._job_repo.has_active_source_sync_job(
            project_id=project_ctx.project.id,
            mapping_id=mapping.id,
        ):
            raise ConflictError(
                "A sync run is already queued or running for this source mapping.",
                code="SYNC_ALREADY_ACTIVE",
            )

        job = self._job_repo.create_job(
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            evidence_id=None,
            triggered_by_user_id=project_ctx.principal.user.id,
            job_type=BackgroundJobType.SOURCE_SYNC.value,
            max_attempts=self._settings.ingestion.worker_max_attempts,
            payload_json={
                "mapping_id": str(mapping.id),
                "source_connection_id": str(mapping.source_connection_id),
                "authorisation_id": str(auth.id),
                "provider": mapping.provider,
                "sync_mode": sync_mode,
            },
        )
        sync_run = self._repo.create_sync_run(
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            project_source_mapping_id=mapping.id,
            source_connection_id=mapping.source_connection_id,
            background_job_id=job.id,
            triggered_by_user_id=project_ctx.principal.user.id,
            provider=mapping.provider,
            sync_mode=sync_mode,
            cursor_before_json=dict(mapping.sync_cursor_json or {}),
        )
        updated_payload = dict(job.payload_json or {})
        updated_payload["sync_run_id"] = str(sync_run.id)
        job.payload_json = updated_payload

        self._audit.record_event(
            event_type="integration.sync_queued",
            resource_type="source_sync_run",
            actor_user_id=project_ctx.principal.user.id,
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            resource_id=str(sync_run.id),
            metadata={
                "mapping_id": str(mapping.id),
                "provider": mapping.provider,
                "sync_mode": sync_mode,
                "job_id": str(job.id),
            },
            message=f"Queued {mapping.provider} {sync_mode} source sync job.",
        )
        self._session.commit()
        self._session.refresh(sync_run)
        self._session.refresh(job)
        return TriggerSyncResponse(
            sync_run=to_sync_run_response(sync_run),
            job=to_background_job_response(job),
        )

    def list_project_sync_runs(
        self,
        *,
        project_ctx: ProjectContext,
        mapping_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SourceSyncHistoryResponse:
        runs, total = self._repo.list_sync_runs_for_project(
            project_id=project_ctx.project.id,
            mapping_id=mapping_id,
            limit=limit,
            offset=offset,
        )
        return SourceSyncHistoryResponse(
            items=[to_sync_run_response(r) for r in runs],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_sync_run(
        self,
        *,
        sync_run_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
    ) -> SourceSyncRunResponse:
        sync_run = self._repo.get_sync_run_by_id(sync_run_id)
        if sync_run is None:
            raise NotFoundError("Source sync run was not found.", code="SYNC_RUN_NOT_FOUND")
        try:
            project_ctx = self._rbac.resolve_project_context(
                project_id=sync_run.project_id,
                principal=principal,
            )
        except NotFoundError as exc:
            raise NotFoundError(
                "Source sync run was not found.",
                code="SYNC_RUN_NOT_FOUND",
            ) from exc

        if not project_ctx.has_permission("project.read"):
            raise ForbiddenError(
                "You do not have permission to read sync history in this project.",
                code="FORBIDDEN",
            )
        return to_sync_run_response(sync_run)

    def cancel_sync_run(
        self,
        *,
        sync_run_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
    ) -> CancelSyncResponse:
        sync_run = self._repo.get_sync_run_by_id(sync_run_id)
        if sync_run is None:
            raise NotFoundError("Source sync run was not found.", code="SYNC_RUN_NOT_FOUND")
        try:
            project_ctx = self._rbac.resolve_project_context(
                project_id=sync_run.project_id,
                principal=principal,
            )
        except NotFoundError as exc:
            raise NotFoundError(
                "Source sync run was not found.",
                code="SYNC_RUN_NOT_FOUND",
            ) from exc

        if not (
            project_ctx.has_permission("project.manage")
            or project_ctx.has_permission("project.evidence.contribute")
        ):
            raise ForbiddenError(
                "You do not have permission to cancel sync runs in this project.",
                code="FORBIDDEN",
            )

        if sync_run.status not in {
            SourceSyncRunStatus.QUEUED.value,
            SourceSyncRunStatus.RUNNING.value,
        }:
            raise ConflictError(
                f"Sync run in status '{sync_run.status}' cannot be cancelled.",
                code="SYNC_RUN_ALREADY_FINISHED",
            )

        now = utc_now()
        sync_run.status = SourceSyncRunStatus.CANCELLED.value
        sync_run.completed_at = now
        sync_run.error_code = "SYNC_CANCELLED"
        sync_run.error_message = "Source sync run was cancelled by user."

        job = sync_run.background_job
        if job is not None:
            self._job_repo.cancel_job(
                job=job,
                now=now,
                error_code="SYNC_CANCELLED",
                error_message="Source sync run was cancelled by user.",
            )

        self._audit.record_event(
            event_type="integration.sync_cancelled",
            resource_type="source_sync_run",
            actor_user_id=principal.user.id,
            organisation_id=sync_run.organisation_id,
            project_id=sync_run.project_id,
            resource_id=str(sync_run.id),
            metadata={"mapping_id": str(sync_run.project_source_mapping_id)},
            message="Cancelled queued or running source sync run.",
        )
        self._session.commit()
        self._session.refresh(sync_run)
        if job is not None:
            self._session.refresh(job)
        return CancelSyncResponse(
            sync_run=to_sync_run_response(sync_run),
            job=to_background_job_response(job) if job is not None else None,
        )
