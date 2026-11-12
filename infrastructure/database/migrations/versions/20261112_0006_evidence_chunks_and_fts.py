"""Create evidence_chunks table with GIN FTS, indexing columns, and job types (Phase 2.5).

Revision ID: 0006_evidence_chunks_and_fts
Revises: 0005_source_integrations
Create Date: 2026-11-12 03:25:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_evidence_chunks_and_fts"
down_revision: str | None = "0005_source_integrations"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Add evidence indexing tracking columns, expanded job types, and evidence_chunks table."""
    op.add_column(
        "evidence_items",
        sa.Column(
            "indexing_status",
            sa.String(length=32),
            server_default="not_indexed",
            nullable=False,
        ),
    )
    op.add_column(
        "evidence_items",
        sa.Column(
            "chunk_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "evidence_items",
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "evidence_items",
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "evidence_items",
        sa.Column("index_version", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "evidence_items",
        sa.Column("index_error_code", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "evidence_items",
        sa.Column("index_error_message", sa.String(length=500), nullable=True),
    )
    op.create_check_constraint(
        "evidence_indexing_status",
        "evidence_items",
        "indexing_status IN ("
        "'not_indexed', 'queued', 'processing', 'indexed', "
        "'partially_indexed', 'failed', 'deleted'"
        ")",
    )
    op.create_check_constraint(
        "evidence_chunk_count_non_negative",
        "evidence_items",
        "chunk_count >= 0",
    )
    op.create_index(
        "ix_evidence_project_indexing_status",
        "evidence_items",
        ["project_id", "indexing_status"],
        unique=False,
    )

    op.drop_constraint("background_job_type", "background_jobs", type_="check")
    op.create_check_constraint(
        "background_job_type",
        "background_jobs",
        "job_type IN ("
        "'document_ingestion', 'source_sync', "
        "'evidence_chunking', 'evidence_embedding', 'evidence_indexing', "
        "'evidence_reindexing', 'evidence_index_cleanup', "
        "'knowledge_reconstruction'"
        ")",
    )

    op.create_table(
        "evidence_chunks",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("evidence_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_type", sa.String(length=48), nullable=False),
        sa.Column("section_title", sa.String(length=500), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_content_hash", sa.String(length=64), nullable=False),
        sa.Column("search_identifier_text", sa.Text(), nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_author_identity", sa.String(length=255), nullable=True),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "acl_scope",
            sa.String(length=32),
            server_default="project_members",
            nullable=False,
        ),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "indexing_status",
            sa.String(length=32),
            server_default="chunked",
            nullable=False,
        ),
        sa.Column("chroma_collection_name", sa.String(length=160), nullable=True),
        sa.Column("chroma_vector_id", sa.String(length=128), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
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
            "chunk_index >= 0",
            name="evidence_chunk_index_non_negative",
        ),
        sa.CheckConstraint(
            "char_count >= 0 AND token_estimate >= 0",
            name="evidence_chunk_counts_non_negative",
        ),
        sa.CheckConstraint(
            "char_start >= 0 AND char_end >= char_start",
            name="evidence_chunk_offsets_valid",
        ),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number >= 1",
            name="evidence_chunk_page_positive",
        ),
        sa.CheckConstraint(
            "length(chunk_content_hash) = 64",
            name="evidence_chunk_hash_sha256_len",
        ),
        sa.CheckConstraint(
            "indexing_status IN ('chunked', 'embedded', 'indexed', 'partially_indexed', 'failed')",
            name="evidence_chunk_indexing_status",
        ),
        sa.CheckConstraint(
            "embedding_dimensions IS NULL OR embedding_dimensions > 0",
            name="evidence_chunk_embedding_dims_positive",
        ),
        sa.CheckConstraint(
            "acl_scope IN ('project_members', 'source_restricted')",
            name="evidence_chunk_acl_scope",
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_id", "chunk_index", name="uq_evidence_chunk_order"),
    )
    op.create_index(
        op.f("ix_evidence_chunks_evidence_id"),
        "evidence_chunks",
        ["evidence_id"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_chunks_org_project_evidence",
        "evidence_chunks",
        ["organisation_id", "project_id", "evidence_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evidence_chunks_organisation_id"),
        "evidence_chunks",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evidence_chunks_project_id"),
        "evidence_chunks",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_chunks_project_source_type",
        "evidence_chunks",
        ["project_id", "source_type"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_chunks_project_status",
        "evidence_chunks",
        ["project_id", "indexing_status"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_chunks_search_vector",
        "evidence_chunks",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Revert Phase 2.5 evidence_chunks, FTS GIN index, and evidence indexing columns cleanly."""
    op.drop_index("ix_evidence_chunks_search_vector", table_name="evidence_chunks")
    op.drop_index("ix_evidence_chunks_project_status", table_name="evidence_chunks")
    op.drop_index("ix_evidence_chunks_project_source_type", table_name="evidence_chunks")
    op.drop_index(op.f("ix_evidence_chunks_project_id"), table_name="evidence_chunks")
    op.drop_index(op.f("ix_evidence_chunks_organisation_id"), table_name="evidence_chunks")
    op.drop_index("ix_evidence_chunks_org_project_evidence", table_name="evidence_chunks")
    op.drop_index(op.f("ix_evidence_chunks_evidence_id"), table_name="evidence_chunks")
    op.drop_table("evidence_chunks")

    op.drop_constraint("background_job_type", "background_jobs", type_="check")
    op.create_check_constraint(
        "background_job_type",
        "background_jobs",
        "job_type IN ('document_ingestion', 'source_sync', 'knowledge_reconstruction')",
    )

    op.drop_index("ix_evidence_project_indexing_status", table_name="evidence_items")
    op.drop_constraint("evidence_chunk_count_non_negative", "evidence_items", type_="check")
    op.drop_constraint("evidence_indexing_status", "evidence_items", type_="check")
    op.drop_column("evidence_items", "index_error_message")
    op.drop_column("evidence_items", "index_error_code")
    op.drop_column("evidence_items", "index_version")
    op.drop_column("evidence_items", "embedding_model")
    op.drop_column("evidence_items", "indexed_at")
    op.drop_column("evidence_items", "chunk_count")
    op.drop_column("evidence_items", "indexing_status")
