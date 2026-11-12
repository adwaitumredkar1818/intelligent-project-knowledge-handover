"""Add project_transitions table for departing/successor workflow tracking.

Revision ID: 0008_project_transitions
Revises: 0007_knowledge_reconstruction
Create Date: 2026-11-13 00:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008_project_transitions_rbac"
down_revision: Union[str, None] = "0007_knowledge_reconstruction"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_index("ix_project_transitions_successor", table_name="project_transitions")
    op.drop_index("ix_project_transitions_departing", table_name="project_transitions")
    op.drop_table("project_transitions")
