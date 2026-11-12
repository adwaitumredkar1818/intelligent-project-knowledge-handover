"""Add supabase_auth_id to users and project_vector_indexes table.

Revision ID: 0009_supabase_and_vector_indexes
Revises: 0008_project_transitions_rbac
Create Date: 2026-11-13 00:45:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_supabase_and_vector_indexes"
down_revision: str | None = "0008_project_transitions_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update users table for Supabase Auth migration
    op.add_column(
        "users",
        sa.Column("supabase_auth_id", sa.String(128), nullable=True),
    )
    op.create_index(
        "ix_users_supabase_auth_id",
        "users",
        ["supabase_auth_id"],
        unique=True,
    )
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(512),
        nullable=True,
    )

    # 2. Create project_vector_indexes table for project-isolated ChromaDB collections
    op.create_table(
        "project_vector_indexes",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "organisation_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("collection_name", sa.String(128), nullable=False, unique=True),
        sa.Column(
            "embedding_model",
            sa.String(128),
            nullable=False,
            server_default="nomic-embed-text",
        ),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False, server_default="768"),
        sa.Column("collection_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("index_status", sa.String(32), nullable=False, server_default="ready"),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
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
    )
    op.create_index(
        "ix_project_vector_indexes_organisation_id",
        "project_vector_indexes",
        ["organisation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_vector_indexes_organisation_id",
        table_name="project_vector_indexes",
    )
    op.drop_table("project_vector_indexes")
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(512),
        nullable=False,
    )
    op.drop_index("ix_users_supabase_auth_id", table_name="users")
    op.drop_column("users", "supabase_auth_id")
