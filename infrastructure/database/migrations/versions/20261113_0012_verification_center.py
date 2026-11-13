"""Add Verification Center schema: verification cases, issues, conflicts, review events, and context requests.

Revision ID: 0012_verification_center
Revises: 0011_relationship_explorer
Create Date: 2026-11-13 14:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0012_verification_center"
down_revision: Union[str, None] = "0011_relationship_explorer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    # 1. verification_cases
    op.create_table(
        "verification_cases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("case_status", sa.String(length=32), server_default="candidate", nullable=False),
        sa.Column("machine_assessment_status", sa.String(length=32), server_default="passed", nullable=False),
        sa.Column("priority", sa.String(length=16), server_default="medium", nullable=False),
        sa.Column("assigned_reviewer_id", sa.UUID(), nullable=True),
        sa.Column("machine_assessment_json", _JSON_TYPE, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("last_assessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assigned_reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vc_project_status", "verification_cases", ["project_id", "case_status"])
    op.create_index("ix_vc_project_target", "verification_cases", ["project_id", "target_type", "target_id"])
    op.create_index("ix_vc_project_priority", "verification_cases", ["project_id", "priority"])
    op.create_index("ix_vc_assigned_reviewer", "verification_cases", ["project_id", "assigned_reviewer_id"])
    op.create_index("ix_verification_cases_target_id", "verification_cases", ["target_id"])

    # 2. verification_issues
    op.create_table(
        "verification_issues",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("issue_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), server_default="medium", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("detection_method", sa.String(length=32), server_default="deterministic_rule", nullable=False),
        sa.Column("details_json", _JSON_TYPE, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("conflicting_evidence_id", sa.UUID(), nullable=True),
        sa.Column("conflicting_chunk_id", sa.UUID(), nullable=True),
        sa.Column("resolution_state", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", sa.UUID(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["verification_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conflicting_chunk_id"], ["evidence_chunks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conflicting_evidence_id"], ["evidence_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vi_case_type", "verification_issues", ["case_id", "issue_type"])
    op.create_index("ix_vi_project_state", "verification_issues", ["project_id", "resolution_state"])
    op.create_index("ix_vi_project_severity", "verification_issues", ["project_id", "severity"])

    # 3. verification_conflicts
    op.create_table(
        "verification_conflicts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("conflict_type", sa.String(length=32), nullable=False),
        sa.Column("claim_a_text", sa.Text(), nullable=False),
        sa.Column("claim_a_source_evidence_id", sa.UUID(), nullable=False),
        sa.Column("claim_a_chunk_id", sa.UUID(), nullable=True),
        sa.Column("claim_a_source_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claim_b_text", sa.Text(), nullable=False),
        sa.Column("claim_b_source_evidence_id", sa.UUID(), nullable=False),
        sa.Column("claim_b_chunk_id", sa.UUID(), nullable=True),
        sa.Column("claim_b_source_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("temporal_comparison", sa.String(length=32), server_default="ambiguous", nullable=False),
        sa.Column("resolution_state", sa.String(length=32), server_default="unresolved", nullable=False),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", sa.UUID(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["verification_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["claim_a_chunk_id"], ["evidence_chunks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["claim_a_source_evidence_id"], ["evidence_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["claim_b_chunk_id"], ["evidence_chunks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["claim_b_source_evidence_id"], ["evidence_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vc_conflicts_case", "verification_conflicts", ["case_id", "resolution_state"])
    op.create_index("ix_vc_conflicts_project_type", "verification_conflicts", ["project_id", "conflict_type"])

    # 4. verification_review_events
    op.create_table(
        "verification_review_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("reviewer_user_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=False),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("finding_patch_json", _JSON_TYPE, nullable=True),
        sa.Column("previous_snapshot_json", _JSON_TYPE, nullable=True),
        sa.Column("new_snapshot_json", _JSON_TYPE, nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["verification_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vre_case_time", "verification_review_events", ["case_id", "created_at"])
    op.create_index("ix_vre_project_reviewer", "verification_review_events", ["project_id", "reviewer_user_id"])

    # 5. verification_context_requests
    op.create_table(
        "verification_context_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("requested_by_user_id", sa.UUID(), nullable=False),
        sa.Column("requested_from_user_id", sa.UUID(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("requested_information_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("response_evidence_id", sa.UUID(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["verification_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_from_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["response_evidence_id"], ["evidence_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vcr_case_status", "verification_context_requests", ["case_id", "status"])
    op.create_index("ix_vcr_target_user", "verification_context_requests", ["requested_from_user_id", "status"])
    op.create_index("ix_vcr_project_status", "verification_context_requests", ["project_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_vcr_project_status", table_name="verification_context_requests")
    op.drop_index("ix_vcr_target_user", table_name="verification_context_requests")
    op.drop_index("ix_vcr_case_status", table_name="verification_context_requests")
    op.drop_table("verification_context_requests")

    op.drop_index("ix_vre_project_reviewer", table_name="verification_review_events")
    op.drop_index("ix_vre_case_time", table_name="verification_review_events")
    op.drop_table("verification_review_events")

    op.drop_index("ix_vc_conflicts_project_type", table_name="verification_conflicts")
    op.drop_index("ix_vc_conflicts_case", table_name="verification_conflicts")
    op.drop_table("verification_conflicts")

    op.drop_index("ix_vi_project_severity", table_name="verification_issues")
    op.drop_index("ix_vi_project_state", table_name="verification_issues")
    op.drop_index("ix_vi_case_type", table_name="verification_issues")
    op.drop_table("verification_issues")

    op.drop_index("ix_verification_cases_target_id", table_name="verification_cases")
    op.drop_index("ix_vc_assigned_reviewer", table_name="verification_cases")
    op.drop_index("ix_vc_project_priority", table_name="verification_cases")
    op.drop_index("ix_vc_project_target", table_name="verification_cases")
    op.drop_index("ix_vc_project_status", table_name="verification_cases")
    op.drop_table("verification_cases")
