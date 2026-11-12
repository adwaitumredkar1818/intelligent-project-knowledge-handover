"""Create delegated source integrations, OAuth states, access policies, mappings & sync runs.

Revision ID: 0005_source_integrations
Revises: 0004_evidence_ingestion
Create Date: 2026-11-12 00:50:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_source_integrations"
down_revision: str | None = "0004_evidence_ingestion"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create Phase 2.4B source integration tables and wire evidence FKs/indexes."""
    op.create_table(
        "source_connections",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column(
            "authorisation_mode",
            sa.String(length=32),
            server_default="delegated_per_user",
            nullable=False,
        ),
        sa.Column("external_workspace_id", sa.String(length=255), nullable=True),
        sa.Column("external_workspace_name", sa.String(length=255), nullable=True),
        sa.Column("external_workspace_url", sa.String(length=512), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="pending_auth",
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("last_error_summary", sa.String(length=500), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disconnected_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider IN ('github', 'jira')",
            name="source_connection_provider",
        ),
        sa.CheckConstraint(
            "authorisation_mode IN ('delegated_per_user')",
            name="source_connection_authorisation_mode",
        ),
        sa.CheckConstraint(
            "status IN ('pending_auth', 'active', 'reauth_required', 'disconnected', 'error')",
            name="source_connection_status",
        ),
        sa.CheckConstraint(
            "length(trim(display_name)) >= 1",
            name="source_connection_name_len",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["disconnected_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_source_connections_created_by_user_id"),
        "source_connections",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_connections_organisation_id"),
        "source_connections",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        "ix_source_connections_org_provider_status",
        "source_connections",
        ["organisation_id", "provider", "status"],
        unique=False,
    )

    op.create_table(
        "user_source_authorisations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_connection_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column("external_username", sa.String(length=255), nullable=True),
        sa.Column("external_email", sa.String(length=255), nullable=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column(
            "token_encryption_algorithm",
            sa.String(length=32),
            server_default="AES-256-GCM",
            nullable=False,
        ),
        sa.Column(
            "token_key_id",
            sa.String(length=32),
            server_default="token-local-v1",
            nullable=False,
        ),
        sa.Column("token_type", sa.String(length=32), nullable=True),
        sa.Column(
            "granted_scopes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("last_error_summary", sa.String(length=500), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider IN ('github', 'jira')",
            name="user_source_auth_provider",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'expired', 'revoked', 'error')",
            name="user_source_auth_status",
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_connection_id"],
            ["source_connections.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_source_authorisations_organisation_id"),
        "user_source_authorisations",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_source_authorisations_source_connection_id"),
        "user_source_authorisations",
        ["source_connection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_source_authorisations_user_id"),
        "user_source_authorisations",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_source_auth_org_user_provider",
        "user_source_authorisations",
        ["organisation_id", "user_id", "provider", "status"],
        unique=False,
    )
    op.create_index(
        "uq_user_source_auth_active",
        "user_source_authorisations",
        ["source_connection_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND revoked_at IS NULL"),
    )

    op.create_table(
        "oauth_states",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_connection_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("encrypted_code_verifier", sa.Text(), nullable=True),
        sa.Column("code_verifier_key_id", sa.String(length=32), nullable=True),
        sa.Column("redirect_after", sa.String(length=512), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider IN ('github', 'jira')",
            name="oauth_state_provider",
        ),
        sa.CheckConstraint(
            "length(state_hash) = 64",
            name="oauth_state_hash_sha256_len",
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_connection_id"],
            ["source_connections.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_hash"),
    )
    op.create_index(
        op.f("ix_oauth_states_expires_at"),
        "oauth_states",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_oauth_states_organisation_id"),
        "oauth_states",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_oauth_states_user_id"),
        "oauth_states",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_oauth_states_user_expires",
        "oauth_states",
        ["user_id", "expires_at"],
        unique=False,
    )

    op.create_table(
        "source_access_policies",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_connection_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("scope_identifier", sa.String(length=255), nullable=False),
        sa.Column(
            "visibility_policy",
            sa.String(length=48),
            server_default="verified_source_acl",
            nullable=False,
        ),
        sa.Column(
            "sync_permission_status",
            sa.String(length=32),
            server_default="verified",
            nullable=False,
        ),
        sa.Column("authorised_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "allowed_user_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "allowed_external_identities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("provider_visibility", sa.String(length=64), nullable=True),
        sa.Column("last_acl_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider IN ('github', 'jira')",
            name="source_access_policy_provider",
        ),
        sa.CheckConstraint(
            "visibility_policy IN ("
            "'restricted_fail_closed', 'explicit_user_grants', "
            "'verified_source_acl', 'project_members_verified'"
            ")",
            name="source_access_policy_visibility",
        ),
        sa.CheckConstraint(
            "sync_permission_status IN ('verified', 'unverified', 'revoked', 'failed')",
            name="source_access_policy_sync_status",
        ),
        sa.ForeignKeyConstraint(
            ["authorised_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_connection_id"],
            ["source_connections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "source_connection_id",
            "scope_identifier",
            name="uq_source_access_policy_project_scope",
        ),
    )
    op.create_index(
        op.f("ix_source_access_policies_organisation_id"),
        "source_access_policies",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_access_policies_project_id"),
        "source_access_policies",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_access_policies_source_connection_id"),
        "source_access_policies",
        ["source_connection_id"],
        unique=False,
    )

    op.create_table(
        "project_source_mappings",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_connection_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_access_policy_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("resource_type", sa.String(length=48), nullable=False),
        sa.Column("external_site_id", sa.String(length=255), nullable=False),
        sa.Column("external_resource_id", sa.String(length=255), nullable=False),
        sa.Column("external_resource_key", sa.String(length=255), nullable=False),
        sa.Column("external_resource_name", sa.String(length=255), nullable=False),
        sa.Column("external_resource_url", sa.String(length=512), nullable=True),
        sa.Column("default_branch", sa.String(length=128), nullable=True),
        sa.Column("provider_visibility", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "sync_config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "sync_cursor_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(length=32), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("last_error_summary", sa.String(length=500), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider IN ('github', 'jira')",
            name="project_source_mapping_provider",
        ),
        sa.CheckConstraint(
            "resource_type IN ('github_repository', 'jira_project')",
            name="project_source_mapping_resource_type",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'disconnected', 'error')",
            name="project_source_mapping_status",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_access_policy_id"],
            ["source_access_policies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_connection_id"],
            ["source_connections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_project_source_mappings_organisation_id"),
        "project_source_mappings",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_source_mappings_project_id"),
        "project_source_mappings",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_source_mappings_source_access_policy_id"),
        "project_source_mappings",
        ["source_access_policy_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_source_mappings_source_connection_id"),
        "project_source_mappings",
        ["source_connection_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_source_mappings_project_status",
        "project_source_mappings",
        ["project_id", "status"],
        unique=False,
    )
    op.create_index(
        "uq_project_source_mapping_active",
        "project_source_mappings",
        ["project_id", "provider", "external_site_id", "external_resource_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('active', 'error')"),
    )

    op.create_table(
        "source_sync_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_source_mapping_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_connection_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("background_job_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("triggered_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("sync_mode", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("items_discovered", sa.Integer(), nullable=False),
        sa.Column("items_created", sa.Integer(), nullable=False),
        sa.Column("items_updated", sa.Integer(), nullable=False),
        sa.Column("items_unchanged", sa.Integer(), nullable=False),
        sa.Column("items_inaccessible", sa.Integer(), nullable=False),
        sa.Column("items_failed", sa.Integer(), nullable=False),
        sa.Column(
            "cursor_before_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "cursor_after_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "warnings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider IN ('github', 'jira')",
            name="source_sync_run_provider",
        ),
        sa.CheckConstraint(
            "sync_mode IN ('initial', 'incremental', 'manual')",
            name="source_sync_run_mode",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'partial', 'failed', 'cancelled')",
            name="source_sync_run_status",
        ),
        sa.CheckConstraint(
            "items_discovered >= 0 AND items_created >= 0 AND items_updated >= 0 "
            "AND items_unchanged >= 0 AND items_inaccessible >= 0 AND items_failed >= 0",
            name="source_sync_run_counts_non_negative",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="source_sync_run_duration_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["background_job_id"],
            ["background_jobs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_source_mapping_id"],
            ["project_source_mappings.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_connection_id"],
            ["source_connections.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_source_sync_runs_background_job_id"),
        "source_sync_runs",
        ["background_job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_sync_runs_organisation_id"),
        "source_sync_runs",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_sync_runs_project_id"),
        "source_sync_runs",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_sync_runs_project_source_mapping_id"),
        "source_sync_runs",
        ["project_source_mapping_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_sync_runs_source_connection_id"),
        "source_sync_runs",
        ["source_connection_id"],
        unique=False,
    )
    op.create_index(
        "ix_source_sync_runs_mapping_created",
        "source_sync_runs",
        ["project_source_mapping_id", "created_at"],
        unique=False,
    )

    # Wire real FKs onto Phase 2.4A `evidence_items` placeholder columns and enforce unique
    # external ID per active project + source_type.
    op.create_foreign_key(
        op.f("fk_evidence_items_source_connection_id_source_connections"),
        "evidence_items",
        "source_connections",
        ["source_connection_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_evidence_items_source_access_policy_id_source_access_policies"),
        "evidence_items",
        "source_access_policies",
        ["source_access_policy_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_evidence_active_project_source_external_id",
        "evidence_items",
        ["project_id", "source_type", "source_external_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND processing_status != 'deleted'"),
    )


def downgrade() -> None:
    """Revert Phase 2.4B tables and evidence FK/index additions cleanly."""
    op.drop_index("uq_evidence_active_project_source_external_id", table_name="evidence_items")
    op.drop_constraint(
        op.f("fk_evidence_items_source_access_policy_id_source_access_policies"),
        "evidence_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_evidence_items_source_connection_id_source_connections"),
        "evidence_items",
        type_="foreignkey",
    )

    op.drop_index("ix_source_sync_runs_mapping_created", table_name="source_sync_runs")
    op.drop_index(op.f("ix_source_sync_runs_source_connection_id"), table_name="source_sync_runs")
    op.drop_index(
        op.f("ix_source_sync_runs_project_source_mapping_id"),
        table_name="source_sync_runs",
    )
    op.drop_index(op.f("ix_source_sync_runs_project_id"), table_name="source_sync_runs")
    op.drop_index(op.f("ix_source_sync_runs_organisation_id"), table_name="source_sync_runs")
    op.drop_index(op.f("ix_source_sync_runs_background_job_id"), table_name="source_sync_runs")
    op.drop_table("source_sync_runs")

    op.drop_index("uq_project_source_mapping_active", table_name="project_source_mappings")
    op.drop_index("ix_project_source_mappings_project_status", table_name="project_source_mappings")
    op.drop_index(
        op.f("ix_project_source_mappings_source_connection_id"),
        table_name="project_source_mappings",
    )
    op.drop_index(
        op.f("ix_project_source_mappings_source_access_policy_id"),
        table_name="project_source_mappings",
    )
    op.drop_index(
        op.f("ix_project_source_mappings_project_id"),
        table_name="project_source_mappings",
    )
    op.drop_index(
        op.f("ix_project_source_mappings_organisation_id"),
        table_name="project_source_mappings",
    )
    op.drop_table("project_source_mappings")

    op.drop_index(
        op.f("ix_source_access_policies_source_connection_id"),
        table_name="source_access_policies",
    )
    op.drop_index(op.f("ix_source_access_policies_project_id"), table_name="source_access_policies")
    op.drop_index(
        op.f("ix_source_access_policies_organisation_id"),
        table_name="source_access_policies",
    )
    op.drop_table("source_access_policies")

    op.drop_index("ix_oauth_states_user_expires", table_name="oauth_states")
    op.drop_index(op.f("ix_oauth_states_user_id"), table_name="oauth_states")
    op.drop_index(op.f("ix_oauth_states_organisation_id"), table_name="oauth_states")
    op.drop_index(op.f("ix_oauth_states_expires_at"), table_name="oauth_states")
    op.drop_table("oauth_states")

    op.drop_index("uq_user_source_auth_active", table_name="user_source_authorisations")
    op.drop_index("ix_user_source_auth_org_user_provider", table_name="user_source_authorisations")
    op.drop_index(
        op.f("ix_user_source_authorisations_user_id"),
        table_name="user_source_authorisations",
    )
    op.drop_index(
        op.f("ix_user_source_authorisations_source_connection_id"),
        table_name="user_source_authorisations",
    )
    op.drop_index(
        op.f("ix_user_source_authorisations_organisation_id"),
        table_name="user_source_authorisations",
    )
    op.drop_table("user_source_authorisations")

    op.drop_index("ix_source_connections_org_provider_status", table_name="source_connections")
    op.drop_index(op.f("ix_source_connections_organisation_id"), table_name="source_connections")
    op.drop_index(op.f("ix_source_connections_created_by_user_id"), table_name="source_connections")
    op.drop_table("source_connections")
