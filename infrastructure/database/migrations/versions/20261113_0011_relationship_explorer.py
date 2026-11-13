"""Add Relationship Explorer schema: entities, aliases, relationships, provenance, traceability, timeline, and runs.

Revision ID: 0011_relationship_explorer
Revises: 0010_knowledge_domains
Create Date: 2026-11-13 06:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0011_relationship_explorer"
down_revision: Union[str, None] = "0010_knowledge_domains"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")

_ALLOWED_ENTITY_TYPES = (
    "'person'", "'discussion'", "'decision'", "'work_item'", "'pull_request'",
    "'commit'", "'document'", "'technical_component'", "'dependency'", "'risk'",
    "'bug'", "'repository'", "'organisation'"
)

_ALLOWED_RELATIONSHIP_TYPES = (
    "'DECISION_REFERENCED_IN_DISCUSSION'", "'DECISION_RECORDED_IN_DOCUMENT'",
    "'DECISION_IMPLEMENTED_BY'", "'DECISION_AFFECTS_COMPONENT'", "'DECISION_SUPERSEDES'",
    "'DECISION_CONFLICTS_WITH'", "'WORK_ITEM_TRACKED_BY'", "'WORK_ITEM_IMPLEMENTED_BY'",
    "'WORK_ITEM_BLOCKED_BY'", "'WORK_ITEM_DEPENDS_ON'", "'WORK_ITEM_RELATED_TO'",
    "'WORK_ITEM_ADDRESSED_BY_COMMIT'", "'COMMIT_BELONGS_TO_PULL_REQUEST'",
    "'PULL_REQUEST_REFERENCES_ISSUE'", "'PULL_REQUEST_MODIFIES_COMPONENT'",
    "'COMMIT_MODIFIES_COMPONENT'", "'PULL_REQUEST_REVIEWED_BY'", "'PULL_REQUEST_AUTHORED_BY'",
    "'PERSON_AUTHORED'", "'PERSON_REVIEWED'", "'PERSON_ASSIGNED_TO'",
    "'PERSON_RESPONSIBLE_FOR'", "'PERSON_DISCUSSIONS_PARTICIPANT'", "'PERSON_CONTRIBUTED_TO'",
    "'COMPONENT_DEPENDS_ON'", "'COMPONENT_CALLS_COMPONENT'", "'COMPONENT_USES_SERVICE'",
    "'COMPONENT_STORES_DATA_IN'", "'COMPONENT_EXPOSES_API'", "'DOCUMENT_DESCRIBES_COMPONENT'",
    "'DOCUMENT_DESCRIBES_DECISION'", "'RISK_AFFECTS_COMPONENT'", "'BUG_FOUND_IN_COMPONENT'",
    "'RISK_BLOCKS_WORK_ITEM'", "'BUG_RELATED_TO_WORK_ITEM'", "'RISK_DEPENDS_ON_EXTERNAL_FACTOR'",
    "'KNOWLEDGE_SUPPORTED_BY_EVIDENCE'", "'KNOWLEDGE_CORROBORATED_BY'",
    "'DOCUMENT_REFERENCES_EVIDENCE'", "'DISCUSSION_REFERENCES_WORK_ITEM'"
)


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Update background_jobs check constraint
    if is_postgres:
        op.drop_constraint("background_job_type", "background_jobs", type_="check")
        op.create_check_constraint(
            "background_job_type",
            "background_jobs",
            "job_type IN ('document_ingestion', 'source_sync', 'evidence_chunking', "
            "'evidence_embedding', 'evidence_indexing', 'evidence_reindexing', "
            "'evidence_index_cleanup', 'knowledge_reconstruction', 'relationship_reconstruction')"
        )

    # 2. Table: knowledge_entities
    op.create_table(
        "knowledge_entities",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, default=sa.func.gen_random_uuid()),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resolution_status", sa.String(32), nullable=False, server_default="canonical"),
        sa.Column("merged_into_entity_id", sa.Uuid(as_uuid=True), sa.ForeignKey("knowledge_entities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("primary_knowledge_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("knowledge_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("primary_evidence_id", sa.Uuid(as_uuid=True), sa.ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("external_source_id", sa.String(255), nullable=True),
        sa.Column("source_provider", sa.String(64), nullable=True),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=False, server_default="1.000"),
        sa.Column("metadata_json", _JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(f"entity_type IN ({', '.join(_ALLOWED_ENTITY_TYPES)})", name="ck_entity_type_valid"),
        sa.CheckConstraint("length(trim(canonical_name)) >= 1", name="ck_entity_name_non_empty"),
        sa.CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="ck_entity_confidence_range"),
    )
    op.create_index("ix_entities_project_type_norm", "knowledge_entities", ["project_id", "entity_type", "normalized_name"])
    op.create_index("ix_entities_project_resolution", "knowledge_entities", ["project_id", "resolution_status"])
    op.create_index("ix_entities_project_evidence", "knowledge_entities", ["project_id", "primary_evidence_id"])
    op.create_index("ix_entities_project_knowledge_item", "knowledge_entities", ["project_id", "primary_knowledge_item_id"])

    # 3. Table: entity_aliases
    op.create_table(
        "entity_aliases",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, default=sa.func.gen_random_uuid()),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias_value", sa.String(255), nullable=False),
        sa.Column("normalized_alias", sa.String(255), nullable=False),
        sa.Column("alias_kind", sa.String(32), nullable=False, server_default="display_name"),
        sa.Column("source_provider", sa.String(64), nullable=False),
        sa.Column("source_external_id", sa.String(255), nullable=True),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=False, server_default="1.000"),
        sa.Column("resolution_status", sa.String(32), nullable=False, server_default="unresolved"),
        sa.Column("reviewed_by_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="ck_alias_confidence_range"),
        sa.CheckConstraint("resolution_status IN ('unresolved', 'candidate', 'accepted', 'rejected')", name="ck_alias_resolution_status"),
    )
    op.create_index("ix_aliases_project_normalized", "entity_aliases", ["project_id", "normalized_alias"])
    op.create_index("ix_aliases_entity_resolution", "entity_aliases", ["entity_id", "resolution_status"])

    # 4. Table: identity_resolution_candidates
    op.create_table(
        "identity_resolution_candidates",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, default=sa.func.gen_random_uuid()),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("left_entity_id", sa.Uuid(as_uuid=True), sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("right_entity_id", sa.Uuid(as_uuid=True), sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("signal_breakdown_json", _JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("policy_band", sa.String(32), nullable=False, server_default="manual_review"),
        sa.Column("decision_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("decided_by_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_rationale", sa.Text(), nullable=True),
        sa.Column("previous_state_json", _JSON_TYPE, nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("left_entity_id != right_entity_id", name="ck_identity_pair_distinct"),
        sa.CheckConstraint("match_score >= 0.0 AND match_score <= 1.0", name="ck_identity_score_range"),
        sa.CheckConstraint("policy_band IN ('strong_candidate', 'manual_review', 'separate')", name="ck_identity_policy_band"),
        sa.CheckConstraint("decision_status IN ('pending', 'accepted', 'rejected', 'reverted')", name="ck_identity_decision_status"),
        sa.UniqueConstraint("project_id", "left_entity_id", "right_entity_id", name="uq_identity_candidates_pair"),
    )
    op.create_index("ix_identity_candidates_project_status", "identity_resolution_candidates", ["project_id", "decision_status"])

    # 5. Table: knowledge_relationships
    op.create_table(
        "knowledge_relationships",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, default=sa.func.gen_random_uuid()),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_entity_id", sa.Uuid(as_uuid=True), sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_entity_id", sa.Uuid(as_uuid=True), sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(64), nullable=False),
        sa.Column("relationship_basis", sa.String(32), nullable=False, server_default="explicit"),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="candidate"),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=False, server_default="1.000"),
        sa.Column("confidence_components_json", _JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("discovery_method", sa.String(64), nullable=False, server_default="exact_reference"),
        sa.Column("is_bidirectional_display", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_llm_assisted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("stale_reason", sa.Text(), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("source_entity_id != target_entity_id", name="ck_relationship_distinct_nodes"),
        sa.CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="ck_relationship_confidence_range"),
        sa.CheckConstraint(f"relationship_type IN ({', '.join(_ALLOWED_RELATIONSHIP_TYPES)})", name="ck_relationship_type_valid"),
        sa.CheckConstraint("relationship_basis IN ('explicit', 'inferred', 'human_confirmed')", name="ck_relationship_basis"),
        sa.CheckConstraint("verification_status IN ('candidate', 'verified', 'rejected', 'conflicted', 'unresolved', 'stale')", name="ck_relationship_status"),
    )
    op.create_index("ix_relationships_project_source", "knowledge_relationships", ["project_id", "source_entity_id", "relationship_type"])
    op.create_index("ix_relationships_project_target", "knowledge_relationships", ["project_id", "target_entity_id", "relationship_type"])
    op.create_index("ix_relationships_project_status", "knowledge_relationships", ["project_id", "verification_status"])
    op.create_index("ix_relationships_project_fingerprint", "knowledge_relationships", ["project_id", "fingerprint"])

    # 6. Table: relationship_evidence_links
    op.create_table(
        "relationship_evidence_links",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, default=sa.func.gen_random_uuid()),
        sa.Column("relationship_id", sa.Uuid(as_uuid=True), sa.ForeignKey("knowledge_relationships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_id", sa.Uuid(as_uuid=True), sa.ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_chunk_id", sa.Uuid(as_uuid=True), sa.ForeignKey("evidence_chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("knowledge_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("knowledge_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence_role", sa.String(32), nullable=False, server_default="direct_support"),
        sa.Column("supporting_excerpt", sa.Text(), nullable=True),
        sa.Column("source_location_json", _JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("evidence_role IN ('direct_support', 'corroboration', 'context', 'contradiction')", name="ck_rel_evidence_role"),
    )
    op.create_index("ix_rel_evidence_project", "relationship_evidence_links", ["project_id", "relationship_id"])
    op.create_index("ix_rel_evidence_item", "relationship_evidence_links", ["project_id", "evidence_id"])

    # 7. Table: decision_traceability_chains
    op.create_table(
        "decision_traceability_chains",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, default=sa.func.gen_random_uuid()),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision_entity_id", sa.Uuid(as_uuid=True), sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("completeness_status", sa.String(32), nullable=False, server_default="untraced"),
        sa.Column("work_item_ids_json", _JSON_TYPE, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("pull_request_ids_json", _JSON_TYPE, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("commit_ids_json", _JSON_TYPE, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("component_ids_json", _JSON_TYPE, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("relationship_ids_json", _JSON_TYPE, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("missing_links_json", _JSON_TYPE, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("uncertainty_reasons_json", _JSON_TYPE, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("aggregate_confidence", sa.Numeric(4, 3), nullable=False, server_default="1.000"),
        sa.Column("earliest_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("completeness_status IN ('complete', 'partially_traced', 'untraced', 'conflicting')", name="ck_traceability_status"),
        sa.CheckConstraint("aggregate_confidence >= 0.0 AND aggregate_confidence <= 1.0", name="ck_traceability_confidence_range"),
        sa.UniqueConstraint("project_id", "decision_entity_id", name="uq_traceability_project_decision"),
    )
    op.create_index("ix_traceability_project_completeness", "decision_traceability_chains", ["project_id", "completeness_status"])

    # 8. Table: knowledge_timeline_events
    op.create_table(
        "knowledge_timeline_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, default=sa.func.gen_random_uuid()),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("secondary_entity_id", sa.Uuid(as_uuid=True), sa.ForeignKey("knowledge_entities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("relationship_id", sa.Uuid(as_uuid=True), sa.ForeignKey("knowledge_relationships.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence_id", sa.Uuid(as_uuid=True), sa.ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timestamp_precision", sa.String(32), nullable=False, server_default="exact_datetime"),
        sa.Column("timestamp_origin", sa.String(32), nullable=False, server_default="source_api"),
        sa.Column("event_fingerprint", sa.String(64), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("timestamp_precision IN ('exact_datetime', 'date_only', 'month_only', 'unknown')", name="ck_timeline_precision"),
        sa.CheckConstraint("timestamp_origin IN ('source_api', 'source_changelog', 'source_commit', 'document_header', 'text_date_mention', 'unknown')", name="ck_timeline_origin"),
    )
    op.create_index("ix_timeline_project_occurred", "knowledge_timeline_events", ["project_id", "occurred_at"])
    op.create_index("ix_timeline_project_entity", "knowledge_timeline_events", ["project_id", "entity_id", "occurred_at"])
    op.create_index("ix_timeline_project_event_type", "knowledge_timeline_events", ["project_id", "event_type"])

    # 9. Table: relationship_reconstruction_runs
    op.create_table(
        "relationship_reconstruction_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, default=sa.func.gen_random_uuid()),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("entities_discovered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relationships_discovered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("explicit_links_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inferred_links_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('queued', 'running', 'completed', 'failed', 'cancelled')", name="ck_rel_run_status"),
    )
    op.create_index("ix_rel_runs_project_created", "relationship_reconstruction_runs", ["project_id", "created_at"])
    op.create_index("ix_rel_runs_project_status", "relationship_reconstruction_runs", ["project_id", "status"])


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    op.drop_table("relationship_reconstruction_runs")
    op.drop_table("knowledge_timeline_events")
    op.drop_table("decision_traceability_chains")
    op.drop_table("relationship_evidence_links")
    op.drop_table("knowledge_relationships")
    op.drop_table("identity_resolution_candidates")
    op.drop_table("entity_aliases")
    op.drop_table("knowledge_entities")

    if is_postgres:
        op.drop_constraint("background_job_type", "background_jobs", type_="check")
        op.create_check_constraint(
            "background_job_type",
            "background_jobs",
            "job_type IN ('document_ingestion', 'source_sync', 'evidence_chunking', "
            "'evidence_embedding', 'evidence_indexing', 'evidence_reindexing', "
            "'evidence_index_cleanup', 'knowledge_reconstruction')"
        )
