"""Create unified evidence ledger, separated document content, and background jobs (Phase 2.4A).

Revision ID: 0004_evidence_ingestion
Revises: 0003_org_project_workspaces
Create Date: 2026-11-11 23:52:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_evidence_ingestion"
down_revision: str | None = "0003_org_project_workspaces"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create Phase 2.4A evidence, page/content separation, and job queue tables."""
    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "source_type",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "source_provider",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("source_external_id", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("source_author_identity", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_provider", sa.String(length=32), nullable=True),
        sa.Column("storage_object_key", sa.String(length=255), nullable=True),
        sa.Column("encryption_algorithm", sa.String(length=32), nullable=True),
        sa.Column("encryption_key_id", sa.String(length=64), nullable=True),
        sa.Column("source_connection_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("source_access_policy_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "acl_scope",
            sa.String(length=32),
            server_default="project_members",
            nullable=False,
        ),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "processing_status",
            sa.String(length=32),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("extraction_method", sa.String(length=32), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "ocr_pages_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "truncated_pages_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
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
            "source_type IN ('document_upload', 'github', 'jira', 'slack', 'manual_note')",
            name="evidence_source_type",
        ),
        sa.CheckConstraint(
            "category IN ("
            "'pdf_document', 'docx_document', 'issue', 'pull_request', "
            "'commit', 'discussion_thread', 'design_document', 'other'"
            ")",
            name="evidence_category",
        ),
        sa.CheckConstraint(
            "processing_status IN ("
            "'pending', 'queued', 'processing', 'extracted', "
            "'partially_extracted', 'failed', 'deleted'"
            ")",
            name="evidence_processing_status",
        ),
        sa.CheckConstraint(
            "acl_scope IN ('project_members', 'source_restricted')",
            name="evidence_acl_scope",
        ),
        sa.CheckConstraint(
            "length(content_hash) = 64",
            name="evidence_content_hash_sha256_len",
        ),
        sa.CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0",
            name="evidence_file_size_non_negative",
        ),
        sa.CheckConstraint(
            "page_count IS NULL OR page_count >= 0",
            name="evidence_page_count_non_negative",
        ),
        sa.CheckConstraint(
            "ocr_pages_count >= 0 AND truncated_pages_count >= 0",
            name="evidence_ocr_counts_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by_user_id"],
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
            ["uploaded_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evidence_items_organisation_id"),
        "evidence_items",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evidence_items_processing_status"),
        "evidence_items",
        ["processing_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evidence_items_project_id"),
        "evidence_items",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evidence_items_source_access_policy_id"),
        "evidence_items",
        ["source_access_policy_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evidence_items_source_connection_id"),
        "evidence_items",
        ["source_connection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evidence_items_uploaded_by_user_id"),
        "evidence_items",
        ["uploaded_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_org_project_status",
        "evidence_items",
        ["organisation_id", "project_id", "processing_status"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_project_created_at",
        "evidence_items",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_project_source_type",
        "evidence_items",
        ["project_id", "source_type"],
        unique=False,
    )
    op.create_index(
        "uq_evidence_active_project_hash",
        "evidence_items",
        ["project_id", "content_hash"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND processing_status != 'deleted'"),
    )

    op.create_table(
        "evidence_contents",
        sa.Column("evidence_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column(
            "extraction_warnings",
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
            "char_count >= 0 AND word_count >= 0",
            name="evidence_content_counts_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence_items.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("evidence_id"),
    )

    op.create_table(
        "evidence_page_contents",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("evidence_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("extraction_outcome", sa.String(length=32), nullable=False),
        sa.Column(
            "ocr_applied",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "ocr_truncated",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column(
            "structured_metadata",
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
            "page_number >= 1",
            name="evidence_page_number_positive",
        ),
        sa.CheckConstraint(
            "char_count >= 0",
            name="evidence_page_char_count_non_negative",
        ),
        sa.CheckConstraint(
            "extraction_outcome IN ("
            "'digital_text', 'ocr_succeeded', 'ocr_truncated', "
            "'ocr_failed', 'empty', 'skipped_limit'"
            ")",
            name="evidence_page_extraction_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence_items.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_id", "page_number", name="uq_evidence_page_number"),
    )
    op.create_index(
        "ix_evidence_pages_evidence_page",
        "evidence_page_contents",
        ["evidence_id", "page_number"],
        unique=False,
    )

    op.create_table(
        "background_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("evidence_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("triggered_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("job_type", sa.String(length=48), nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("priority", sa.Integer(), server_default="100", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "result_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("locked_by", sa.String(length=128), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
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
            "job_type IN ('document_ingestion', 'source_sync', 'knowledge_reconstruction')",
            name="background_job_type",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="background_job_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0 AND max_attempts >= 1 AND attempt_count <= max_attempts",
            name="background_job_attempts_valid",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="background_job_duration_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence_items.id"],
            ondelete="CASCADE",
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
            ["triggered_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_background_jobs_claimable",
        "background_jobs",
        ["priority", "next_retry_at", "created_at"],
        unique=False,
        postgresql_where=sa.text("status = 'queued'"),
    )
    op.create_index(
        op.f("ix_background_jobs_evidence_id"),
        "background_jobs",
        ["evidence_id"],
        unique=False,
    )
    op.create_index(
        "ix_background_jobs_evidence_created",
        "background_jobs",
        ["evidence_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_background_jobs_org_project_status",
        "background_jobs",
        ["organisation_id", "project_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_background_jobs_organisation_id"),
        "background_jobs",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_background_jobs_project_id"),
        "background_jobs",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_background_jobs_status"),
        "background_jobs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Revert Phase 2.4A evidence and background job schema cleanly."""
    op.drop_index(op.f("ix_background_jobs_status"), table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_project_id"), table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_organisation_id"), table_name="background_jobs")
    op.drop_index("ix_background_jobs_org_project_status", table_name="background_jobs")
    op.drop_index("ix_background_jobs_evidence_created", table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_evidence_id"), table_name="background_jobs")
    op.drop_index("ix_background_jobs_claimable", table_name="background_jobs")
    op.drop_table("background_jobs")

    op.drop_index("ix_evidence_pages_evidence_page", table_name="evidence_page_contents")
    op.drop_table("evidence_page_contents")
    op.drop_table("evidence_contents")

    op.drop_index("uq_evidence_active_project_hash", table_name="evidence_items")
    op.drop_index("ix_evidence_project_source_type", table_name="evidence_items")
    op.drop_index("ix_evidence_project_created_at", table_name="evidence_items")
    op.drop_index("ix_evidence_org_project_status", table_name="evidence_items")
    op.drop_index(op.f("ix_evidence_items_uploaded_by_user_id"), table_name="evidence_items")
    op.drop_index(op.f("ix_evidence_items_source_connection_id"), table_name="evidence_items")
    op.drop_index(op.f("ix_evidence_items_source_access_policy_id"), table_name="evidence_items")
    op.drop_index(op.f("ix_evidence_items_project_id"), table_name="evidence_items")
    op.drop_index(op.f("ix_evidence_items_processing_status"), table_name="evidence_items")
    op.drop_index(op.f("ix_evidence_items_organisation_id"), table_name="evidence_items")
    op.drop_table("evidence_items")
