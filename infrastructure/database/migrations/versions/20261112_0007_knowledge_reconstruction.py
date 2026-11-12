"""Create knowledge_extraction_runs, knowledge_items, and knowledge_evidence_links (Phase 2.6).

Revision ID: 0007_knowledge_reconstruction
Revises: 0006_evidence_chunks_and_fts
Create Date: 2026-11-12 15:20:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_knowledge_reconstruction"
down_revision: str | None = "0006_evidence_chunks_and_fts"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create canonical knowledge reconstruction tables, constraints, and indexes."""
    op.create_table(
        "knowledge_extraction_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("background_job_id", sa.Uuid(), nullable=True),
        sa.Column("evidence_id", sa.Uuid(), nullable=True),
        sa.Column("triggered_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column(
            "target_categories",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "is_synthetic",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("total_evidence_items", sa.Integer(), server_default="0", nullable=False),
        sa.Column("processed_evidence_items", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_evidence_items", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_evidence_items", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_chunks_evaluated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("batches_executed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("candidates_generated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("claims_persisted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("claims_rejected_ungrounded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duplicates_merged", sa.Integer(), server_default="0", nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completion_tokens", sa.Integer(), server_default="0", nullable=False),
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
            "scope_type IN ('evidence', 'project')",
            name=op.f("ck_knowledge_extraction_runs_knowledge_extraction_scope_type"),
        ),
        sa.CheckConstraint(
            "status IN ("
            "'queued', 'running', 'completed', 'partially_completed', 'failed', 'cancelled'"
            ")",
            name=op.f("ck_knowledge_extraction_runs_knowledge_extraction_run_status"),
        ),
        sa.CheckConstraint(
            "total_evidence_items >= 0 AND processed_evidence_items >= 0 "
            "AND failed_evidence_items >= 0 AND skipped_evidence_items >= 0 "
            "AND total_chunks_evaluated >= 0 AND batches_executed >= 0 "
            "AND candidates_generated >= 0 AND claims_persisted >= 0 "
            "AND claims_rejected_ungrounded >= 0 AND duplicates_merged >= 0 "
            "AND prompt_tokens >= 0 AND completion_tokens >= 0",
            name=op.f("ck_knowledge_extraction_runs_knowledge_extraction_counters_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["background_job_id"],
            ["background_jobs.id"],
            name=op.f("fk_knowledge_extraction_runs_background_job_id_background_jobs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence_items.id"],
            name=op.f("fk_knowledge_extraction_runs_evidence_id_evidence_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name=op.f("fk_knowledge_extraction_runs_organisation_id_organisations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_knowledge_extraction_runs_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by_user_id"],
            ["users.id"],
            name=op.f("fk_knowledge_extraction_runs_triggered_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_extraction_runs")),
    )
    op.create_index(
        "ix_knowledge_extraction_runs_project_created",
        "knowledge_extraction_runs",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_extraction_runs_project_status",
        "knowledge_extraction_runs",
        ["project_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_extraction_runs_evidence_id",
        "knowledge_extraction_runs",
        ["evidence_id"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_extraction_runs_job_id",
        "knowledge_extraction_runs",
        ["background_job_id"],
        unique=False,
    )

    op.create_table(
        "knowledge_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("epistemic_status", sa.String(length=32), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("support_classification", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("structured_summary", sa.Text(), nullable=False),
        sa.Column(
            "structured_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("normalised_status", sa.String(length=64), nullable=True),
        sa.Column("person_or_owner_label", sa.String(length=255), nullable=True),
        sa.Column(
            "source_attribution_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("extraction_model", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "confidence_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("uncertainty_reason", sa.Text(), nullable=True),
        sa.Column(
            "is_stale",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("stale_reason", sa.String(length=255), nullable=True),
        sa.Column("stale_detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by_id", sa.Uuid(), nullable=True),
        sa.Column(
            "is_synthetic",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("source_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
            "category IN ("
            "'decisions_rationale', 'work_items', 'responsibilities_ownership', "
            "'technical_architecture', 'bugs_blockers_risks', 'dependencies'"
            ")",
            name=op.f("ck_knowledge_items_knowledge_item_category"),
        ),
        sa.CheckConstraint(
            "epistemic_status IN ('extracted', 'ai_interpreted', 'human_verified')",
            name=op.f("ck_knowledge_items_knowledge_item_epistemic_status"),
        ),
        sa.CheckConstraint(
            "review_status IN ('pending_review', 'approved', 'rejected', 'needs_clarification')",
            name=op.f("ck_knowledge_items_knowledge_item_review_status"),
        ),
        sa.CheckConstraint(
            "support_classification IN ('direct', 'corroborated', 'interpretation', 'uncertain')",
            name=op.f("ck_knowledge_items_knowledge_item_support_classification"),
        ),
        sa.ForeignKeyConstraint(
            ["extraction_run_id"],
            ["knowledge_extraction_runs.id"],
            name=op.f("fk_knowledge_items_extraction_run_id_knowledge_extraction_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name=op.f("fk_knowledge_items_organisation_id_organisations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_knowledge_items_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"],
            ["knowledge_items.id"],
            name=op.f("fk_knowledge_items_superseded_by_id_knowledge_items"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_items")),
    )
    op.create_index(
        "ix_knowledge_items_project_cat_fp",
        "knowledge_items",
        ["project_id", "category", "fingerprint"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_items_project_filters",
        "knowledge_items",
        ["project_id", "is_deleted", "is_stale", "category", "review_status"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_items_run_id",
        "knowledge_items",
        ["extraction_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_items_org_project",
        "knowledge_items",
        ["organisation_id", "project_id"],
        unique=False,
    )

    op.create_table(
        "knowledge_evidence_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_item_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_chunk_id", sa.Uuid(), nullable=True),
        sa.Column("support_type", sa.String(length=32), nullable=False),
        sa.Column(
            "source_location_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("supporting_excerpt", sa.Text(), nullable=False),
        sa.Column(
            "excerpt_verified",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("excerpt_match_mode", sa.String(length=32), nullable=False),
        sa.Column(
            "source_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "support_type IN ('direct', 'corroborated', 'interpretation', 'uncertain')",
            name=op.f("ck_knowledge_evidence_links_knowledge_evidence_link_support_type"),
        ),
        sa.CheckConstraint(
            "excerpt_match_mode IN ('exact', 'normalized_whitespace')",
            name=op.f("ck_knowledge_evidence_links_knowledge_evidence_link_match_mode"),
        ),
        sa.ForeignKeyConstraint(
            ["evidence_chunk_id"],
            ["evidence_chunks.id"],
            name=op.f("fk_knowledge_evidence_links_evidence_chunk_id_evidence_chunks"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence_items.id"],
            name=op.f("fk_knowledge_evidence_links_evidence_id_evidence_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_item_id"],
            ["knowledge_items.id"],
            name=op.f("fk_knowledge_evidence_links_knowledge_item_id_knowledge_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name=op.f("fk_knowledge_evidence_links_organisation_id_organisations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_knowledge_evidence_links_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_evidence_links")),
    )
    op.create_index(
        "ix_knowledge_evidence_links_item_evidence",
        "knowledge_evidence_links",
        ["knowledge_item_id", "evidence_id"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_evidence_links_evidence_id",
        "knowledge_evidence_links",
        ["evidence_id", "knowledge_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_evidence_links_chunk_id",
        "knowledge_evidence_links",
        ["evidence_chunk_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop Phase 2.6 knowledge reconstruction tables cleanly."""
    op.drop_index("ix_knowledge_evidence_links_chunk_id", table_name="knowledge_evidence_links")
    op.drop_index("ix_knowledge_evidence_links_evidence_id", table_name="knowledge_evidence_links")
    op.drop_index(
        "ix_knowledge_evidence_links_item_evidence",
        table_name="knowledge_evidence_links",
    )
    op.drop_table("knowledge_evidence_links")

    op.drop_index("ix_knowledge_items_org_project", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_run_id", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_project_filters", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_project_cat_fp", table_name="knowledge_items")
    op.drop_table("knowledge_items")

    op.drop_index("ix_knowledge_extraction_runs_job_id", table_name="knowledge_extraction_runs")
    op.drop_index(
        "ix_knowledge_extraction_runs_evidence_id",
        table_name="knowledge_extraction_runs",
    )
    op.drop_index(
        "ix_knowledge_extraction_runs_project_status",
        table_name="knowledge_extraction_runs",
    )
    op.drop_index(
        "ix_knowledge_extraction_runs_project_created",
        table_name="knowledge_extraction_runs",
    )
    op.drop_table("knowledge_extraction_runs")
