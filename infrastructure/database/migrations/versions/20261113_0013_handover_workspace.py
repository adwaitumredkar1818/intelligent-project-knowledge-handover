"""Add Handover Workspace schema: cases, packages, versions, sections, links, readiness, checklists, signoffs, deliveries, acknowledgements, history, and ownership transfers.

Revision ID: 0013_handover_workspace
Revises: 0012_verification_center
Create Date: 2026-11-13 18:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0013_handover_workspace"
down_revision: Union[str, None] = "0012_verification_center"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    # 1. handover_cases
    op.create_table(
        "handover_cases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("departing_member_id", sa.UUID(), nullable=False),
        sa.Column("successor_id", sa.UUID(), nullable=True),
        sa.Column("target_handover_date", sa.Date(), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("metadata_json", _JSON_TYPE, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["departing_member_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["successor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hc_project_status", "handover_cases", ["project_id", "status"])
    op.create_index("ix_hc_project_departing", "handover_cases", ["project_id", "departing_member_id"])
    op.create_index("ix_hc_project_successor", "handover_cases", ["project_id", "successor_id"])
    op.create_index("ix_hc_org_project", "handover_cases", ["organisation_id", "project_id"])
    op.create_index("ix_handover_cases_status", "handover_cases", ["status"])

    # 2. handover_packages
    op.create_table(
        "handover_packages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["handover_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", name="uq_handover_package_case"),
    )
    op.create_index("ix_hp_project_case", "handover_packages", ["project_id", "case_id"])

    # 3. handover_package_versions
    op.create_table(
        "handover_package_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("package_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("assembly_status", sa.String(length=32), server_default="assembled", nullable=False),
        sa.Column("assembly_snapshot_json", _JSON_TYPE, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("assembled_by_user_id", sa.UUID(), nullable=False),
        sa.Column("assembled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assembled_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["case_id"], ["handover_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["package_id"], ["handover_packages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("package_id", "version_number", name="uq_hpv_package_version"),
    )
    op.create_index("ix_hpv_case_version", "handover_package_versions", ["case_id", "version_number"])
    op.create_index("ix_hpv_package_current", "handover_package_versions", ["package_id", "is_current"])

    # 4. handover_package_sections
    op.create_table(
        "handover_package_sections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=False),
        sa.Column("section_type", sa.String(length=64), nullable=False),
        sa.Column("section_title", sa.String(length=255), nullable=False),
        sa.Column("section_content", sa.Text(), nullable=False),
        sa.Column("content_summary", sa.Text(), nullable=True),
        sa.Column("section_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("knowledge_item_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("relationship_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("metadata_json", _JSON_TYPE, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["handover_package_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", "section_type", name="uq_hps_version_section_type"),
    )
    op.create_index("ix_hps_version_order", "handover_package_sections", ["version_id", "section_order"])

    # 5. handover_content_links
    op.create_table(
        "handover_content_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=False),
        sa.Column("link_type", sa.String(length=32), nullable=False),
        sa.Column("knowledge_item_id", sa.UUID(), nullable=True),
        sa.Column("relationship_id", sa.UUID(), nullable=True),
        sa.Column("evidence_id", sa.UUID(), nullable=True),
        sa.Column("eligibility_status_json", _JSON_TYPE, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["knowledge_item_id"], ["knowledge_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["relationship_id"], ["knowledge_relationships.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["section_id"], ["handover_package_sections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["handover_package_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hcl_section_type", "handover_content_links", ["section_id", "link_type"])
    op.create_index("ix_hcl_version_type", "handover_content_links", ["version_id", "link_type"])
    op.create_index("ix_hcl_knowledge_item", "handover_content_links", ["knowledge_item_id"])
    op.create_index("ix_hcl_relationship", "handover_content_links", ["relationship_id"])
    op.create_index("ix_hcl_evidence", "handover_content_links", ["evidence_id"])

    # 6. handover_readiness_assessments
    op.create_table(
        "handover_readiness_assessments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("blockers_json", _JSON_TYPE, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("warnings_json", _JSON_TYPE, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("details_json", _JSON_TYPE, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("assessed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("assessed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assessed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["case_id"], ["handover_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["handover_package_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hra_version_cat", "handover_readiness_assessments", ["version_id", "category"])
    op.create_index("ix_hra_case_cat", "handover_readiness_assessments", ["case_id", "category"])

    # 7. handover_checklists
    op.create_table(
        "handover_checklists",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=True),
        sa.Column("checklist_type", sa.String(length=32), server_default="pre_handover", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("total_items", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_items", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_completed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["handover_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["handover_package_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hcl_case_type", "handover_checklists", ["case_id", "checklist_type"])
    op.create_index("ix_hcl_project_case", "handover_checklists", ["project_id", "case_id"])

    # 8. handover_checklist_items
    op.create_table(
        "handover_checklist_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("checklist_id", sa.UUID(), nullable=False),
        sa.Column("item_text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=64), server_default="general", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("assigned_to_user_id", sa.UUID(), nullable=True),
        sa.Column("completed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocking", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["checklist_id"], ["handover_checklists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hcli_checklist_status", "handover_checklist_items", ["checklist_id", "status"])
    op.create_index("ix_hcli_checklist_order", "handover_checklist_items", ["checklist_id", "sort_order"])

    # 9. handover_responsibility_transfers
    op.create_table(
        "handover_responsibility_transfers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=True),
        sa.Column("responsibility_description", sa.Text(), nullable=False),
        sa.Column("knowledge_domain", sa.String(length=64), server_default="responsibilities_ownership", nullable=False),
        sa.Column("current_owner_id", sa.UUID(), nullable=False),
        sa.Column("proposed_successor_id", sa.UUID(), nullable=True),
        sa.Column("transfer_status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("transfer_notes", sa.Text(), nullable=True),
        sa.Column("related_entity_id", sa.UUID(), nullable=True),
        sa.Column("transferred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["handover_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposed_successor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_entity_id"], ["knowledge_entities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["version_id"], ["handover_package_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hrt_case_status", "handover_responsibility_transfers", ["case_id", "transfer_status"])
    op.create_index("ix_hrt_owner", "handover_responsibility_transfers", ["current_owner_id"])
    op.create_index("ix_hrt_successor", "handover_responsibility_transfers", ["proposed_successor_id"])

    # 10. handover_signoffs
    op.create_table(
        "handover_signoffs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=False),
        sa.Column("signoff_type", sa.String(length=32), nullable=False),
        sa.Column("signer_user_id", sa.UUID(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("signature_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["handover_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["handover_package_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hs_case_version_type", "handover_signoffs", ["case_id", "version_id", "signoff_type"])
    op.create_index("ix_hs_signer", "handover_signoffs", ["signer_user_id"])

    # 11. handover_deliveries
    op.create_table(
        "handover_deliveries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=False),
        sa.Column("delivered_to_user_id", sa.UUID(), nullable=False),
        sa.Column("delivered_by_user_id", sa.UUID(), nullable=False),
        sa.Column("delivery_method", sa.String(length=32), server_default="internal_download", nullable=False),
        sa.Column("artifact_storage_path", sa.String(length=512), nullable=True),
        sa.Column("artifact_checksum", sa.String(length=64), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["handover_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["delivered_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["delivered_to_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["handover_package_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hd_version_user", "handover_deliveries", ["version_id", "delivered_to_user_id"])
    op.create_index("ix_hd_case_user", "handover_deliveries", ["case_id", "delivered_to_user_id"])

    # 12. handover_acknowledgements
    op.create_table(
        "handover_acknowledgements",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("delivery_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=False),
        sa.Column("acknowledged_by_user_id", sa.UUID(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("acknowledgement_notes", sa.Text(), nullable=True),
        sa.Column("confirmations_json", _JSON_TYPE, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("acknowledgement_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["acknowledged_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["case_id"], ["handover_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["delivery_id"], ["handover_deliveries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["handover_package_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ha_delivery", "handover_acknowledgements", ["delivery_id"])
    op.create_index("ix_ha_case_user", "handover_acknowledgements", ["case_id", "acknowledged_by_user_id"])

    # 13. handover_status_histories
    op.create_table(
        "handover_status_histories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=False),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("changed_by_user_id", sa.UUID(), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata_json", _JSON_TYPE, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["handover_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hsh_case_time", "handover_status_histories", ["case_id", "changed_at"])

    # 14. handover_ownership_transfers
    op.create_table(
        "handover_ownership_transfers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=False),
        sa.Column("transfer_type", sa.String(length=32), server_default="project_ownership", nullable=False),
        sa.Column("from_user_id", sa.UUID(), nullable=False),
        sa.Column("to_user_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=True),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("transfer_notes", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("executed_by_user_id", sa.UUID(), nullable=False),
        sa.Column("rolled_back", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("rollback_reason", sa.Text(), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_by_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["handover_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["executed_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rolled_back_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["handover_package_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hot_case_type", "handover_ownership_transfers", ["case_id", "transfer_type"])
    op.create_index("ix_hot_from_user", "handover_ownership_transfers", ["from_user_id"])
    op.create_index("ix_hot_to_user", "handover_ownership_transfers", ["to_user_id"])


def downgrade() -> None:
    op.drop_table("handover_ownership_transfers")
    op.drop_table("handover_status_histories")
    op.drop_table("handover_acknowledgements")
    op.drop_table("handover_deliveries")
    op.drop_table("handover_signoffs")
    op.drop_table("handover_responsibility_transfers")
    op.drop_table("handover_checklist_items")
    op.drop_table("handover_checklists")
    op.drop_table("handover_readiness_assessments")
    op.drop_table("handover_content_links")
    op.drop_table("handover_package_sections")
    op.drop_table("handover_package_versions")
    op.drop_table("handover_packages")
    op.drop_table("handover_cases")
