"""Create project transition and evidence workspace tables (Phase 2.4).

Revision ID: 0004_project_evidence_workspace
Revises: 0003_org_project_workspaces
Create Date: 2026-11-12 20:10:00
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_project_evidence_workspace"
down_revision: str | None = "0003_org_project_workspaces"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

_RBAC_UUID_NAMESPACE = uuid.UUID("6b7c84d4-2c1b-4c6f-9c2a-9a3e4f502100")

_NEW_PERMISSIONS: tuple[tuple[str, str, str, str], ...] = (
    (
        "project.transition.manage",
        "Manage Project Transition",
        "Configure departing member, successor, and capture scope within an assigned project.",
        "project",
    ),
    (
        "project.sources.manage",
        "Manage Project Sources",
        "Connect and map external sources (GitHub, Jira) within an assigned project.",
        "project",
    ),
    (
        "project.evidence.read",
        "Read Project Evidence",
        "Search, filter, and inspect permitted project evidence within an assigned project.",
        "project",
    ),
    (
        "project.evidence.upload",
        "Upload Project Evidence",
        "Upload PDF and DOCX documents to an assigned project.",
        "project",
    ),
    (
        "project.evidence.manage",
        "Manage Project Evidence",
        "Delete or trigger reprocessing of evidence items within an assigned project.",
        "project",
    ),
)

_NEW_ROLE_PERMISSION_PAIRS: tuple[tuple[str, str], ...] = (
    ("org_owner", "project.transition.manage"),
    ("org_owner", "project.sources.manage"),
    ("org_owner", "project.evidence.read"),
    ("org_owner", "project.evidence.upload"),
    ("org_owner", "project.evidence.manage"),
    ("org_admin", "project.transition.manage"),
    ("org_admin", "project.sources.manage"),
    ("org_admin", "project.evidence.read"),
    ("org_admin", "project.evidence.upload"),
    ("org_admin", "project.evidence.manage"),
    ("project_manager", "project.transition.manage"),
    ("project_manager", "project.sources.manage"),
    ("project_manager", "project.evidence.read"),
    ("project_manager", "project.evidence.upload"),
    ("project_manager", "project.evidence.manage"),
    ("project_member", "project.evidence.read"),
    ("project_member", "project.evidence.upload"),
    ("reviewer", "project.evidence.read"),
)


def _rbac_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(_RBAC_UUID_NAMESPACE, f"{kind}:{key}")


def _seed_phase24_rbac() -> None:
    now = datetime.now(UTC)
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("code", sa.String(128)),
        sa.column("name", sa.String(128)),
        sa.column("description", sa.Text()),
        sa.column("scope_type", sa.String(32)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid(as_uuid=True)),
        sa.column("permission_id", sa.Uuid(as_uuid=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    perm_rows = [
        {
            "id": _rbac_id("permission", code),
            "code": code,
            "name": name,
            "description": desc,
            "scope_type": scope,
            "created_at": now,
        }
        for code, name, desc, scope in _NEW_PERMISSIONS
    ]
    op.execute(
        postgresql.insert(permissions_table)
        .values(perm_rows)
        .on_conflict_do_nothing(index_elements=["code"])
    )

    link_rows = [
        {
            "role_id": _rbac_id("role", r_name),
            "permission_id": _rbac_id("permission", p_code),
            "created_at": now,
        }
        for r_name, p_code in _NEW_ROLE_PERMISSION_PAIRS
    ]
    op.execute(
        postgresql.insert(role_permissions_table)
        .values(link_rows)
        .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
    )


def _remove_phase24_rbac() -> None:
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid(as_uuid=True)),
        sa.column("permission_id", sa.Uuid(as_uuid=True)),
    )
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid(as_uuid=True)),
    )
    new_perm_ids = [_rbac_id("permission", code) for code, *_ in _NEW_PERMISSIONS]

    op.execute(
        role_permissions_table.delete().where(
            role_permissions_table.c.permission_id.in_(new_perm_ids)
        )
    )
    op.execute(permissions_table.delete().where(permissions_table.c.id.in_(new_perm_ids)))


def upgrade() -> None:
    """Create project transitions and evidence workspace tables."""
    # 1. Add responsibility_description to project_memberships
    op.add_column(
        "project_memberships",
        sa.Column("responsibility_description", sa.Text(), nullable=True),
    )

    # 2. project_transitions
    op.create_table(
        "project_transitions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "departing_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "successor_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "workflow_stage",
            sa.String(64),
            nullable=False,
            server_default="planning",
        ),
        sa.Column("handover_scope", sa.Text(), nullable=True),
        sa.Column("source_scope", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("capture_start_date", sa.Date(), nullable=True),
        sa.Column("capture_end_date", sa.Date(), nullable=True),
        sa.Column("context_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "departing_user_id != successor_user_id",
            name="uq_project_transitions_distinct_participants",
        ),
    )
    op.create_index(
        "ix_project_transitions_departing",
        "project_transitions",
        ["departing_user_id"],
    )
    op.create_index(
        "ix_project_transitions_successor",
        "project_transitions",
        ["successor_user_id"],
    )

    # 3. source_connections
    op.create_table(
        "source_connections",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "organisation_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "connected_by_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("account_identifier", sa.String(255), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "scopes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "connection_status",
            sa.String(32),
            nullable=False,
            server_default="connected",
        ),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "provider IN ('github', 'jira', 'slack')",
            name="source_connection_provider",
        ),
        sa.CheckConstraint(
            "connection_status IN ('connected', 'needs_reauth', 'disconnected', 'error')",
            name="source_connection_status_valid",
        ),
    )
    op.create_index(
        "ix_source_connections_org_provider",
        "source_connections",
        ["organisation_id", "provider"],
    )
    op.create_index(
        "ix_source_connections_connected_by",
        "source_connections",
        ["connected_by_id"],
    )

    # 4. project_source_mappings
    op.create_table(
        "project_source_mappings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_connection_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("source_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_resource_id", sa.String(255), nullable=False),
        sa.Column("external_resource_name", sa.String(255), nullable=False),
        sa.Column(
            "external_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "sync_status",
            sa.String(32),
            nullable=False,
            server_default="idle",
        ),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "project_id",
            "external_resource_id",
            name="uq_project_source_mappings_project_resource",
        ),
        sa.CheckConstraint(
            "sync_status IN ('idle', 'syncing', 'completed', 'failed')",
            name="project_source_mapping_sync_status",
        ),
    )
    op.create_index(
        "ix_project_source_mappings_project_status",
        "project_source_mappings",
        ["project_id", "sync_status"],
    )

    # 5. evidence_items
    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_mapping_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("project_source_mappings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("record_type", sa.String(64), nullable=False),
        sa.Column("external_source_id", sa.String(500), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "processing_status",
            sa.String(32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "verification_status",
            sa.String(32),
            nullable=False,
            server_default="unverified",
        ),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "raw_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "provider IN ('github', 'jira', 'pdf', 'docx', 'slack')",
            name="evidence_item_provider",
        ),
        sa.CheckConstraint(
            "processing_status IN ('pending', 'processing', 'extracted', 'indexed', 'failed')",
            name="evidence_item_processing_status",
        ),
        sa.CheckConstraint(
            "verification_status IN ("
            "'unverified', 'candidate', 'verified', 'conflicted', 'rejected')",
            name="evidence_item_verification_status",
        ),
    )
    op.create_index(
        "ix_evidence_items_proj_provider",
        "evidence_items",
        ["project_id", "provider"],
    )
    op.create_index(
        "ix_evidence_items_proj_status",
        "evidence_items",
        ["project_id", "processing_status"],
    )
    op.create_index(
        "ix_evidence_items_proj_created",
        "evidence_items",
        ["project_id", "created_at"],
    )

    # 6. document_files
    op.create_table(
        "document_files",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "evidence_item_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("evidence_items.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "uploaded_by_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_format", sa.String(16), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("is_encrypted", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("ocr_applied", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "file_format IN ('pdf', 'docx')",
            name="document_file_format_valid",
        ),
    )
    op.create_index(
        "ix_document_files_sha256",
        "document_files",
        ["sha256_hash"],
    )

    # 7. evidence_contents
    op.create_table(
        "evidence_contents",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "evidence_item_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("evidence_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_heading", sa.String(255), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("chroma_point_id", sa.String(128), nullable=True),
        sa.Column(
            "indexing_status",
            sa.String(32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_evidence_contents_item_chunk",
        "evidence_contents",
        ["evidence_item_id", "chunk_index"],
    )

    # 8. source_sync_jobs
    op.create_table(
        "source_sync_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_mapping_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("project_source_mappings.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("job_type", sa.String(64), nullable=False),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="source_sync_job_status_valid",
        ),
    )
    op.create_index(
        "ix_source_sync_jobs_status_created",
        "source_sync_jobs",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_source_sync_jobs_project",
        "source_sync_jobs",
        ["project_id"],
    )

    # 9. Seed RBAC additions for Phase 2.4
    _seed_phase24_rbac()


def downgrade() -> None:
    """Drop Phase 2.4 tables and RBAC additions in reverse order."""
    _remove_phase24_rbac()
    op.drop_table("source_sync_jobs")
    op.drop_table("evidence_contents")
    op.drop_table("document_files")
    op.drop_table("evidence_items")
    op.drop_table("project_source_mappings")
    op.drop_table("source_connections")
    op.drop_table("project_transitions")
    op.drop_column("project_memberships", "responsibility_description")
