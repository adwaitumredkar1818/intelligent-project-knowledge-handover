"""Delegated source connection, OAuth state, access policy, mapping, and sync-run models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    ProjectSourceMappingStatus,
    SourceConnectionStatus,
    SourcePermissionVerificationStatus,
    SourceSyncMode,
    SourceSyncRunStatus,
    SourceVisibilityPolicy,
    UserSourceAuthorisationStatus,
)

if TYPE_CHECKING:
    from app.models.job import BackgroundJob
    from app.models.organisation import Organisation
    from app.models.project import Project
    from app.models.user import User

_JSON_VARIANT = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class SourceConnection(Base):
    """Organisation-scoped delegated source integration connection (GitHub or Jira)."""

    __tablename__ = "source_connections"
    __table_args__ = (
        CheckConstraint("provider IN ('github', 'jira')", name="source_connection_provider"),
        CheckConstraint(
            "authorisation_mode IN ('delegated_per_user')",
            name="source_connection_authorisation_mode",
        ),
        CheckConstraint(
            "status IN ('pending_auth', 'active', 'reauth_required', 'disconnected', 'error')",
            name="source_connection_status",
        ),
        CheckConstraint("length(trim(display_name)) >= 1", name="source_connection_name_len"),
        Index(
            "ix_source_connections_org_provider_status",
            "organisation_id",
            "provider",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    authorisation_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="delegated_per_user",
        server_default="delegated_per_user",
    )
    external_workspace_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_workspace_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_workspace_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SourceConnectionStatus.PENDING_AUTH.value,
        server_default=SourceConnectionStatus.PENDING_AUTH.value,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT,
        nullable=False,
        default=dict,
    )
    disconnected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    disconnected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organisation: Mapped[Organisation] = relationship(foreign_keys=[organisation_id])
    created_by_user: Mapped[User] = relationship(foreign_keys=[created_by_user_id])
    disconnected_by_user: Mapped[User | None] = relationship(
        foreign_keys=[disconnected_by_user_id]
    )
    authorisations: Mapped[list[UserSourceAuthorisation]] = relationship(
        back_populates="source_connection",
        cascade="all, delete-orphan",
    )
    access_policies: Mapped[list[SourceAccessPolicy]] = relationship(
        back_populates="source_connection",
        cascade="all, delete-orphan",
    )
    mappings: Mapped[list[ProjectSourceMapping]] = relationship(
        back_populates="source_connection",
        cascade="all, delete-orphan",
    )


class UserSourceAuthorisation(Base):
    """Per-user delegated OAuth 2.0 credentials encrypted strictly via `TOKEN_ENCRYPTION_KEY`."""

    __tablename__ = "user_source_authorisations"
    __table_args__ = (
        CheckConstraint("provider IN ('github', 'jira')", name="user_source_auth_provider"),
        CheckConstraint(
            "status IN ('active', 'expired', 'revoked', 'error')",
            name="user_source_auth_status",
        ),
        Index(
            "uq_user_source_auth_active",
            "source_connection_id",
            "user_id",
            unique=True,
            sqlite_where=text("status = 'active' AND revoked_at IS NULL"),
            postgresql_where=text("status = 'active' AND revoked_at IS NULL"),
        ),
        Index(
            "ix_user_source_auth_org_user_provider",
            "organisation_id",
            "user_id",
            "provider",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_encryption_algorithm: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="AES-256-GCM",
        server_default="AES-256-GCM",
    )
    token_key_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="token-local-v1",
        server_default="token-local-v1",
    )
    token_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    granted_scopes: Mapped[list[str]] = mapped_column(
        _JSON_VARIANT,
        nullable=False,
        default=list,
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=UserSourceAuthorisationStatus.ACTIVE.value,
        server_default=UserSourceAuthorisationStatus.ACTIVE.value,
    )
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    source_connection: Mapped[SourceConnection] = relationship(back_populates="authorisations")
    organisation: Mapped[Organisation] = relationship(foreign_keys=[organisation_id])
    user: Mapped[User] = relationship(foreign_keys=[user_id])


class OAuthState(Base):
    """Single-use, time-bounded cryptographic OAuth state & PKCE verifier store."""

    __tablename__ = "oauth_states"
    __table_args__ = (
        CheckConstraint("provider IN ('github', 'jira')", name="oauth_state_provider"),
        CheckConstraint("length(state_hash) = 64", name="oauth_state_hash_sha256_len"),
        Index("ix_oauth_states_user_expires", "user_id", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_connection_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_connections.id", ondelete="CASCADE"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    encrypted_code_verifier: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_verifier_key_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    redirect_after: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    organisation: Mapped[Organisation] = relationship(foreign_keys=[organisation_id])
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    source_connection: Mapped[SourceConnection | None] = relationship(
        foreign_keys=[source_connection_id]
    )


class SourceAccessPolicy(Base):
    """Explicit fail-closed visibility policy governing synced external evidence access."""

    __tablename__ = "source_access_policies"
    __table_args__ = (
        CheckConstraint("provider IN ('github', 'jira')", name="source_access_policy_provider"),
        CheckConstraint(
            "visibility_policy IN ("
            "'restricted_fail_closed', 'explicit_user_grants', "
            "'verified_source_acl', 'project_members_verified'"
            ")",
            name="source_access_policy_visibility",
        ),
        CheckConstraint(
            "sync_permission_status IN ('verified', 'unverified', 'revoked', 'failed')",
            name="source_access_policy_sync_status",
        ),
        UniqueConstraint(
            "project_id",
            "source_connection_id",
            "scope_identifier",
            name="uq_source_access_policy_project_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    visibility_policy: Mapped[str] = mapped_column(
        String(48),
        nullable=False,
        default=SourceVisibilityPolicy.VERIFIED_SOURCE_ACL.value,
        server_default=SourceVisibilityPolicy.VERIFIED_SOURCE_ACL.value,
    )
    sync_permission_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SourcePermissionVerificationStatus.VERIFIED.value,
        server_default=SourcePermissionVerificationStatus.VERIFIED.value,
    )
    authorised_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    allowed_user_ids: Mapped[list[str]] = mapped_column(
        _JSON_VARIANT,
        nullable=False,
        default=list,
    )
    allowed_external_identities: Mapped[list[dict[str, Any]]] = mapped_column(
        _JSON_VARIANT,
        nullable=False,
        default=list,
    )
    provider_visibility: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_acl_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organisation: Mapped[Organisation] = relationship(foreign_keys=[organisation_id])
    project: Mapped[Project] = relationship(foreign_keys=[project_id])
    source_connection: Mapped[SourceConnection] = relationship(back_populates="access_policies")
    authorised_by_user: Mapped[User | None] = relationship(foreign_keys=[authorised_by_user_id])


class ProjectSourceMapping(Base):
    """Explicit mapping of a selected GitHub repository or Jira project to a project workspace."""

    __tablename__ = "project_source_mappings"
    __table_args__ = (
        CheckConstraint("provider IN ('github', 'jira')", name="project_source_mapping_provider"),
        CheckConstraint(
            "resource_type IN ('github_repository', 'jira_project')",
            name="project_source_mapping_resource_type",
        ),
        CheckConstraint(
            "status IN ('active', 'disabled', 'disconnected', 'error')",
            name="project_source_mapping_status",
        ),
        Index(
            "uq_project_source_mapping_active",
            "project_id",
            "provider",
            "external_site_id",
            "external_resource_id",
            unique=True,
            sqlite_where=text("status IN ('active', 'error')"),
            postgresql_where=text("status IN ('active', 'error')"),
        ),
        Index("ix_project_source_mappings_project_status", "project_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_access_policy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_access_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(48), nullable=False)
    external_site_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="github.com",
    )
    external_resource_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_resource_key: Mapped[str] = mapped_column(String(255), nullable=False)
    external_resource_name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_resource_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    default_branch: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_visibility: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProjectSourceMappingStatus.ACTIVE.value,
        server_default=ProjectSourceMappingStatus.ACTIVE.value,
    )
    sync_config_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT,
        nullable=False,
        default=dict,
    )
    sync_cursor_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT,
        nullable=False,
        default=dict,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organisation: Mapped[Organisation] = relationship(foreign_keys=[organisation_id])
    project: Mapped[Project] = relationship(foreign_keys=[project_id])
    source_connection: Mapped[SourceConnection] = relationship(back_populates="mappings")
    source_access_policy: Mapped[SourceAccessPolicy] = relationship(
        foreign_keys=[source_access_policy_id]
    )
    created_by_user: Mapped[User | None] = relationship(foreign_keys=[created_by_user_id])
    sync_runs: Mapped[list[SourceSyncRun]] = relationship(
        back_populates="mapping",
        cascade="all, delete-orphan",
        order_by="SourceSyncRun.created_at.desc()",
    )


class SourceSyncRun(Base):
    """Durable sync-run history, checkpoint snapshots, and item outcome metrics."""

    __tablename__ = "source_sync_runs"
    __table_args__ = (
        CheckConstraint("provider IN ('github', 'jira')", name="source_sync_run_provider"),
        CheckConstraint(
            "sync_mode IN ('initial', 'incremental', 'manual')",
            name="source_sync_run_mode",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'partial', 'failed', 'cancelled')",
            name="source_sync_run_status",
        ),
        CheckConstraint(
            "items_discovered >= 0 AND items_created >= 0 AND items_updated >= 0 "
            "AND items_unchanged >= 0 AND items_inaccessible >= 0 AND items_failed >= 0",
            name="source_sync_run_counts_non_negative",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="source_sync_run_duration_non_negative",
        ),
        Index(
            "ix_source_sync_runs_mapping_created",
            "project_source_mapping_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_source_mapping_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("project_source_mappings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    background_job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("background_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    sync_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SourceSyncMode.MANUAL.value,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SourceSyncRunStatus.QUEUED.value,
        server_default=SourceSyncRunStatus.QUEUED.value,
    )
    items_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_unchanged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_inaccessible: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cursor_before_json: Mapped[dict[str, Any] | None] = mapped_column(
        _JSON_VARIANT,
        nullable=True,
    )
    cursor_after_json: Mapped[dict[str, Any] | None] = mapped_column(
        _JSON_VARIANT,
        nullable=True,
    )
    warnings_json: Mapped[list[str]] = mapped_column(
        _JSON_VARIANT,
        nullable=False,
        default=list,
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organisation: Mapped[Organisation] = relationship(foreign_keys=[organisation_id])
    project: Mapped[Project] = relationship(foreign_keys=[project_id])
    mapping: Mapped[ProjectSourceMapping] = relationship(back_populates="sync_runs")
    source_connection: Mapped[SourceConnection] = relationship(foreign_keys=[source_connection_id])
    background_job: Mapped[BackgroundJob | None] = relationship(foreign_keys=[background_job_id])
    triggered_by_user: Mapped[User | None] = relationship(foreign_keys=[triggered_by_user_id])
