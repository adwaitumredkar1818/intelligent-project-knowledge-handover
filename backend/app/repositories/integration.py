"""Data-access repository for delegated source connections, policies, mappings, and sync runs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.models.enums import (
    ProjectMembershipStatus,
    ProjectSourceMappingStatus,
    SourceSyncRunStatus,
    UserSourceAuthorisationStatus,
)
from app.models.integration import (
    OAuthState,
    ProjectSourceMapping,
    SourceAccessPolicy,
    SourceConnection,
    SourceSyncRun,
    UserSourceAuthorisation,
)
from app.models.project import Project, ProjectMembership
from app.models.rbac import Permission, Role, RolePermission


class IntegrationRepository:
    """Repository encapsulating tenant-scoped source integrations and OAuth state."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_connection_by_id(self, connection_id: uuid.UUID) -> SourceConnection | None:
        stmt = (
            select(SourceConnection)
            .options(joinedload(SourceConnection.organisation))
            .where(SourceConnection.id == connection_id)
        )
        return self._session.execute(stmt).unique().scalar_one_or_none()

    def list_connections_for_organisation(
        self,
        *,
        organisation_id: uuid.UUID,
        provider: str | None = None,
    ) -> list[SourceConnection]:
        stmt = select(SourceConnection).where(
            SourceConnection.organisation_id == organisation_id
        )
        if provider is not None:
            stmt = stmt.where(SourceConnection.provider == provider)
        stmt = stmt.order_by(SourceConnection.created_at.desc(), SourceConnection.id.desc())
        return list(self._session.execute(stmt).scalars().all())

    def create_connection(
        self,
        *,
        organisation_id: uuid.UUID,
        provider: str,
        display_name: str,
        created_by_user_id: uuid.UUID,
        status: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> SourceConnection:
        connection = SourceConnection(
            organisation_id=organisation_id,
            provider=provider,
            display_name=display_name,
            authorisation_mode="delegated_per_user",
            status=status,
            created_by_user_id=created_by_user_id,
            metadata_json=dict(metadata_json or {}),
        )
        self._session.add(connection)
        self._session.flush()
        return connection

    def user_has_project_contribution_in_org(
        self,
        *,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Check whether user holds project manage/contribute rights inside an org project."""
        stmt = (
            select(ProjectMembership.id)
            .join(Project, ProjectMembership.project_id == Project.id)
            .join(Role, ProjectMembership.role_id == Role.id)
            .join(RolePermission, Role.id == RolePermission.role_id)
            .join(Permission, RolePermission.permission_id == Permission.id)
            .where(
                Project.organisation_id == organisation_id,
                ProjectMembership.user_id == user_id,
                ProjectMembership.status == ProjectMembershipStatus.ACTIVE.value,
                Permission.code.in_(("project.manage", "project.evidence.contribute")),
            )
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none() is not None

    def get_active_authorisation(
        self,
        *,
        source_connection_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> UserSourceAuthorisation | None:
        stmt = (
            select(UserSourceAuthorisation)
            .where(
                UserSourceAuthorisation.source_connection_id == source_connection_id,
                UserSourceAuthorisation.user_id == user_id,
                UserSourceAuthorisation.status == UserSourceAuthorisationStatus.ACTIVE.value,
                UserSourceAuthorisation.revoked_at.is_(None),
            )
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def get_latest_authorisation_for_connection(
        self,
        *,
        source_connection_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> UserSourceAuthorisation | None:
        stmt = (
            select(UserSourceAuthorisation)
            .where(
                UserSourceAuthorisation.source_connection_id == source_connection_id,
                UserSourceAuthorisation.user_id == user_id,
            )
            .order_by(
                UserSourceAuthorisation.updated_at.desc(),
                UserSourceAuthorisation.created_at.desc(),
            )
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def get_authorisation_by_id(
        self,
        authorisation_id: uuid.UUID,
    ) -> UserSourceAuthorisation | None:
        stmt = select(UserSourceAuthorisation).where(
            UserSourceAuthorisation.id == authorisation_id
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def get_authorisation_for_update(
        self,
        authorisation_id: uuid.UUID,
    ) -> UserSourceAuthorisation | None:
        stmt = select(UserSourceAuthorisation).where(
            UserSourceAuthorisation.id == authorisation_id
        )
        bind = self._session.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update()
        return self._session.execute(stmt).scalar_one_or_none()

    def replace_active_authorisation(
        self,
        *,
        source_connection_id: uuid.UUID,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str,
        external_user_id: str,
        external_username: str | None,
        external_email: str | None,
        encrypted_access_token: str,
        encrypted_refresh_token: str | None,
        token_encryption_algorithm: str,
        token_key_id: str,
        token_type: str | None,
        granted_scopes: list[str],
        token_expires_at: datetime | None,
        metadata_json: dict[str, Any] | None,
        now: datetime,
    ) -> UserSourceAuthorisation:
        """Atomically supersede any prior active authorisation for `(connection, user)`."""
        self._session.execute(
            update(UserSourceAuthorisation)
            .where(
                UserSourceAuthorisation.source_connection_id == source_connection_id,
                UserSourceAuthorisation.user_id == user_id,
                UserSourceAuthorisation.status == UserSourceAuthorisationStatus.ACTIVE.value,
                UserSourceAuthorisation.revoked_at.is_(None),
            )
            .values(
                status=UserSourceAuthorisationStatus.REVOKED.value,
                revoked_at=now,
                last_error_code="SUPERSEDED_BY_REAUTH",
                last_error_summary="Superseded by a newer OAuth authorisation.",
            )
        )
        self._session.flush()

        auth = UserSourceAuthorisation(
            source_connection_id=source_connection_id,
            organisation_id=organisation_id,
            user_id=user_id,
            provider=provider,
            external_user_id=external_user_id,
            external_username=external_username,
            external_email=external_email,
            encrypted_access_token=encrypted_access_token,
            encrypted_refresh_token=encrypted_refresh_token,
            token_encryption_algorithm=token_encryption_algorithm,
            token_key_id=token_key_id,
            token_type=token_type,
            granted_scopes=list(granted_scopes),
            token_expires_at=token_expires_at,
            status=UserSourceAuthorisationStatus.ACTIVE.value,
            last_verified_at=now,
            metadata_json=dict(metadata_json or {}),
        )
        self._session.add(auth)
        self._session.flush()
        return auth

    def revoke_all_authorisations_for_connection(
        self,
        *,
        source_connection_id: uuid.UUID,
        now: datetime,
        reason_code: str,
        reason_summary: str,
    ) -> int:
        result = self._session.execute(
            update(UserSourceAuthorisation)
            .where(
                UserSourceAuthorisation.source_connection_id == source_connection_id,
                UserSourceAuthorisation.status.in_(
                    (
                        UserSourceAuthorisationStatus.ACTIVE.value,
                        UserSourceAuthorisationStatus.EXPIRED.value,
                        UserSourceAuthorisationStatus.ERROR.value,
                    )
                ),
            )
            .values(
                status=UserSourceAuthorisationStatus.REVOKED.value,
                revoked_at=now,
                last_error_code=reason_code[:64],
                last_error_summary=reason_summary[:500],
            )
        )
        self._session.flush()
        return int(getattr(result, "rowcount", 0) or 0)

    def create_oauth_state(
        self,
        *,
        state_hash: str,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
        source_connection_id: uuid.UUID | None,
        provider: str,
        encrypted_code_verifier: str | None,
        code_verifier_key_id: str | None,
        redirect_after: str | None,
        expires_at: datetime,
    ) -> OAuthState:
        row = OAuthState(
            state_hash=state_hash,
            organisation_id=organisation_id,
            user_id=user_id,
            source_connection_id=source_connection_id,
            provider=provider,
            encrypted_code_verifier=encrypted_code_verifier,
            code_verifier_key_id=code_verifier_key_id,
            redirect_after=redirect_after,
            expires_at=expires_at,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def get_oauth_state_by_hash(
        self,
        state_hash: str,
        *,
        for_update: bool = False,
    ) -> OAuthState | None:
        stmt = select(OAuthState).where(OAuthState.state_hash == state_hash)
        if for_update:
            bind = self._session.get_bind()
            if bind is not None and bind.dialect.name == "postgresql":
                stmt = stmt.with_for_update()
        return self._session.execute(stmt).scalar_one_or_none()

    def get_access_policy_by_id(self, policy_id: uuid.UUID) -> SourceAccessPolicy | None:
        return self._session.get(SourceAccessPolicy, policy_id)

    def get_access_policy_by_scope(
        self,
        *,
        project_id: uuid.UUID,
        source_connection_id: uuid.UUID,
        scope_identifier: str,
    ) -> SourceAccessPolicy | None:
        stmt = select(SourceAccessPolicy).where(
            SourceAccessPolicy.project_id == project_id,
            SourceAccessPolicy.source_connection_id == source_connection_id,
            SourceAccessPolicy.scope_identifier == scope_identifier,
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def upsert_access_policy(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        source_connection_id: uuid.UUID,
        provider: str,
        scope_identifier: str,
        visibility_policy: str,
        sync_permission_status: str,
        authorised_by_user_id: uuid.UUID | None,
        verified_user_id: uuid.UUID | None,
        external_identity: dict[str, Any] | None,
        provider_visibility: str | None,
        verified_at: datetime,
        metadata_json: dict[str, Any] | None = None,
    ) -> SourceAccessPolicy:
        policy = self.get_access_policy_by_scope(
            project_id=project_id,
            source_connection_id=source_connection_id,
            scope_identifier=scope_identifier,
        )
        if policy is None:
            allowed_users = [str(verified_user_id)] if verified_user_id is not None else []
            allowed_ext = [external_identity] if external_identity else []
            policy = SourceAccessPolicy(
                organisation_id=organisation_id,
                project_id=project_id,
                source_connection_id=source_connection_id,
                provider=provider,
                scope_identifier=scope_identifier,
                visibility_policy=visibility_policy,
                sync_permission_status=sync_permission_status,
                authorised_by_user_id=authorised_by_user_id,
                allowed_user_ids=allowed_users,
                allowed_external_identities=allowed_ext,
                provider_visibility=provider_visibility,
                last_acl_verified_at=verified_at,
                metadata_json=dict(metadata_json or {}),
            )
            self._session.add(policy)
            self._session.flush()
            return policy

        policy.visibility_policy = visibility_policy
        policy.sync_permission_status = sync_permission_status
        policy.provider_visibility = provider_visibility
        policy.last_acl_verified_at = verified_at
        if authorised_by_user_id is not None:
            policy.authorised_by_user_id = authorised_by_user_id
        if metadata_json:
            merged_meta = dict(policy.metadata_json or {})
            merged_meta.update(metadata_json)
            policy.metadata_json = merged_meta

        if verified_user_id is not None:
            self.add_verified_user_to_policy(
                policy=policy,
                user_id=verified_user_id,
                external_identity=external_identity,
                verified_at=verified_at,
            )
        self._session.flush()
        return policy

    def add_verified_user_to_policy(
        self,
        *,
        policy: SourceAccessPolicy,
        user_id: uuid.UUID,
        external_identity: dict[str, Any] | None,
        verified_at: datetime,
    ) -> SourceAccessPolicy:
        user_str = str(user_id)
        allowed_users = list(policy.allowed_user_ids or [])
        if user_str not in allowed_users:
            allowed_users.append(user_str)
            policy.allowed_user_ids = allowed_users

        if external_identity:
            existing_ext = list(policy.allowed_external_identities or [])
            ext_uid = str(external_identity.get("external_user_id") or "")
            filtered = [
                entry
                for entry in existing_ext
                if str(entry.get("user_id") or "") != user_str
                and (not ext_uid or str(entry.get("external_user_id") or "") != ext_uid)
            ]
            filtered.append({**external_identity, "user_id": user_str})
            policy.allowed_external_identities = filtered

        policy.last_acl_verified_at = verified_at
        self._session.flush()
        return policy

    def remove_user_from_policy(
        self,
        *,
        policy: SourceAccessPolicy,
        user_id: uuid.UUID,
        verified_at: datetime,
    ) -> SourceAccessPolicy:
        user_str = str(user_id)
        policy.allowed_user_ids = [
            uid for uid in (policy.allowed_user_ids or []) if uid != user_str
        ]
        policy.allowed_external_identities = [
            entry
            for entry in (policy.allowed_external_identities or [])
            if str(entry.get("user_id") or "") != user_str
        ]
        policy.last_acl_verified_at = verified_at
        self._session.flush()
        return policy

    def list_policies_for_project_scope_prefix(
        self,
        *,
        project_id: uuid.UUID,
        source_connection_id: uuid.UUID,
        scope_prefix: str,
    ) -> list[SourceAccessPolicy]:
        stmt = select(SourceAccessPolicy).where(
            SourceAccessPolicy.project_id == project_id,
            SourceAccessPolicy.source_connection_id == source_connection_id,
            SourceAccessPolicy.scope_identifier.like(f"{scope_prefix}%"),
        )
        return list(self._session.execute(stmt).scalars().all())

    def get_mapping_by_id(self, mapping_id: uuid.UUID) -> ProjectSourceMapping | None:
        stmt = (
            select(ProjectSourceMapping)
            .options(
                joinedload(ProjectSourceMapping.source_connection),
                joinedload(ProjectSourceMapping.source_access_policy),
                joinedload(ProjectSourceMapping.project),
                joinedload(ProjectSourceMapping.organisation),
            )
            .where(ProjectSourceMapping.id == mapping_id)
        )
        return self._session.execute(stmt).unique().scalar_one_or_none()

    def find_active_mapping(
        self,
        *,
        project_id: uuid.UUID,
        provider: str,
        external_site_id: str,
        external_resource_id: str,
    ) -> ProjectSourceMapping | None:
        stmt = (
            select(ProjectSourceMapping)
            .where(
                ProjectSourceMapping.project_id == project_id,
                ProjectSourceMapping.provider == provider,
                ProjectSourceMapping.external_site_id == external_site_id,
                ProjectSourceMapping.external_resource_id == external_resource_id,
                ProjectSourceMapping.status.in_(
                    (
                        ProjectSourceMappingStatus.ACTIVE.value,
                        ProjectSourceMappingStatus.ERROR.value,
                    )
                ),
            )
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def list_mappings_for_project(
        self,
        *,
        project_id: uuid.UUID,
        include_disabled: bool = True,
    ) -> list[ProjectSourceMapping]:
        stmt = (
            select(ProjectSourceMapping)
            .options(joinedload(ProjectSourceMapping.source_access_policy))
            .where(ProjectSourceMapping.project_id == project_id)
        )
        if not include_disabled:
            stmt = stmt.where(
                ProjectSourceMapping.status.in_(
                    (
                        ProjectSourceMappingStatus.ACTIVE.value,
                        ProjectSourceMappingStatus.ERROR.value,
                    )
                )
            )
        stmt = stmt.order_by(ProjectSourceMapping.created_at.desc(), ProjectSourceMapping.id.desc())
        return list(self._session.execute(stmt).unique().scalars().all())

    def create_mapping(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        source_connection_id: uuid.UUID,
        source_access_policy_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        provider: str,
        resource_type: str,
        external_site_id: str,
        external_resource_id: str,
        external_resource_key: str,
        external_resource_name: str,
        external_resource_url: str | None,
        default_branch: str | None,
        provider_visibility: str | None,
        sync_config_json: dict[str, Any],
    ) -> ProjectSourceMapping:
        mapping = ProjectSourceMapping(
            organisation_id=organisation_id,
            project_id=project_id,
            source_connection_id=source_connection_id,
            source_access_policy_id=source_access_policy_id,
            created_by_user_id=created_by_user_id,
            provider=provider,
            resource_type=resource_type,
            external_site_id=external_site_id,
            external_resource_id=external_resource_id,
            external_resource_key=external_resource_key,
            external_resource_name=external_resource_name,
            external_resource_url=external_resource_url,
            default_branch=default_branch,
            provider_visibility=provider_visibility,
            status=ProjectSourceMappingStatus.ACTIVE.value,
            sync_config_json=dict(sync_config_json),
            sync_cursor_json={},
        )
        self._session.add(mapping)
        self._session.flush()
        return mapping

    def disconnect_mappings_for_connection(
        self,
        *,
        source_connection_id: uuid.UUID,
        now: datetime,
    ) -> int:
        result = self._session.execute(
            update(ProjectSourceMapping)
            .where(
                ProjectSourceMapping.source_connection_id == source_connection_id,
                ProjectSourceMapping.status.in_(
                    (
                        ProjectSourceMappingStatus.ACTIVE.value,
                        ProjectSourceMappingStatus.ERROR.value,
                    )
                ),
            )
            .values(
                status=ProjectSourceMappingStatus.DISCONNECTED.value,
                disabled_at=now,
                last_error_code="CONNECTION_DISCONNECTED",
                last_error_summary="Parent organisation source connection was disconnected.",
            )
        )
        self._session.flush()
        return int(getattr(result, "rowcount", 0) or 0)

    def create_sync_run(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        project_source_mapping_id: uuid.UUID,
        source_connection_id: uuid.UUID,
        background_job_id: uuid.UUID | None,
        triggered_by_user_id: uuid.UUID | None,
        provider: str,
        sync_mode: str,
        cursor_before_json: dict[str, Any] | None,
    ) -> SourceSyncRun:
        run = SourceSyncRun(
            organisation_id=organisation_id,
            project_id=project_id,
            project_source_mapping_id=project_source_mapping_id,
            source_connection_id=source_connection_id,
            background_job_id=background_job_id,
            triggered_by_user_id=triggered_by_user_id,
            provider=provider,
            sync_mode=sync_mode,
            status=SourceSyncRunStatus.QUEUED.value,
            cursor_before_json=dict(cursor_before_json) if cursor_before_json else None,
        )
        self._session.add(run)
        self._session.flush()
        return run

    def get_sync_run_by_id(self, sync_run_id: uuid.UUID) -> SourceSyncRun | None:
        stmt = (
            select(SourceSyncRun)
            .options(
                joinedload(SourceSyncRun.mapping),
                joinedload(SourceSyncRun.source_connection),
                joinedload(SourceSyncRun.background_job),
            )
            .where(SourceSyncRun.id == sync_run_id)
        )
        return self._session.execute(stmt).unique().scalar_one_or_none()

    def has_active_sync_run_for_mapping(self, mapping_id: uuid.UUID) -> bool:
        stmt = (
            select(SourceSyncRun.id)
            .where(
                SourceSyncRun.project_source_mapping_id == mapping_id,
                SourceSyncRun.status.in_(
                    (
                        SourceSyncRunStatus.QUEUED.value,
                        SourceSyncRunStatus.RUNNING.value,
                    )
                ),
            )
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none() is not None

    def list_sync_runs_for_project(
        self,
        *,
        project_id: uuid.UUID,
        mapping_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[SourceSyncRun], int]:
        filters: list[Any] = [SourceSyncRun.project_id == project_id]
        if mapping_id is not None:
            filters.append(SourceSyncRun.project_source_mapping_id == mapping_id)

        total = int(
            self._session.execute(
                select(func.count()).select_from(SourceSyncRun).where(*filters)
            ).scalar_one()
        )
        items = list(
            self._session.execute(
                select(SourceSyncRun)
                .where(*filters)
                .order_by(SourceSyncRun.created_at.desc(), SourceSyncRun.id.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total
