"""Relational knowledge graph models for Relationship Explorer.

Provides canonical storage for:
- Knowledge entities (nodes across 13 types)
- Entity aliases (multi-source handles and identity mappings)
- Identity resolution candidates (reversible merge pairs with signal breakdown)
- Knowledge relationships (typed, directed graph edges with dual classification)
- Relationship evidence links (mandatory provenance citations)
- Decision traceability chains (5-stage Decision -> Work item -> PR -> Commit -> Component)
- Knowledge timeline events (chronological project event log with timestamp precision)
- Relationship reconstruction runs (async worker execution lifecycle)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base
from app.models.enums import (
    AliasResolutionStatus,
    EntityResolutionStatus,
    IdentityCandidateStatus,
    IdentityPolicyBand,
    RelationshipBasis,
    RelationshipEvidenceRole,
    RelationshipRunStatus,
    RelationshipVerificationStatus,
    TimelineOrigin,
    TimelinePrecision,
    TraceabilityCompletenessStatus,
)

_JSON_VARIANT = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class KnowledgeEntity(Base):
    """Canonical project-scoped entity node in the knowledge graph."""

    __tablename__ = "knowledge_entities"
    __table_args__ = (
        CheckConstraint("length(trim(canonical_name)) >= 1", name="ck_entity_name_non_empty"),
        CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 1.0", name="ck_entity_confidence_range"
        ),
        Index("ix_entities_project_type_norm", "project_id", "entity_type", "normalized_name"),
        Index("ix_entities_project_resolution", "project_id", "resolution_status"),
        Index("ix_entities_project_evidence", "project_id", "primary_evidence_id"),
        Index("ix_entities_project_knowledge_item", "project_id", "primary_knowledge_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    resolution_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EntityResolutionStatus.CANONICAL.value,
        server_default=EntityResolutionStatus.CANONICAL.value,
    )
    merged_into_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_entities.id", ondelete="SET NULL"),
        nullable=True,
    )

    primary_knowledge_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    primary_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="SET NULL"),
        nullable=True,
    )

    external_source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=1.0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=dict
    )

    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    first_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    aliases: Mapped[list[EntityAlias]] = relationship(
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    outbound_relationships: Mapped[list[KnowledgeRelationship]] = relationship(
        foreign_keys="[KnowledgeRelationship.source_entity_id]",
        back_populates="source_entity",
        cascade="all, delete-orphan",
    )
    inbound_relationships: Mapped[list[KnowledgeRelationship]] = relationship(
        foreign_keys="[KnowledgeRelationship.target_entity_id]",
        back_populates="target_entity",
        cascade="all, delete-orphan",
    )


class EntityAlias(Base):
    """Source-specific alias or identity handle bound to a KnowledgeEntity."""

    __tablename__ = "entity_aliases"
    __table_args__ = (
        CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 1.0", name="ck_alias_confidence_range"
        ),
        Index("ix_aliases_project_normalized", "project_id", "normalized_alias"),
        Index("ix_aliases_entity_resolution", "entity_id", "resolution_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    alias_value: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alias_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="display_name")
    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    source_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=1.0)
    resolution_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AliasResolutionStatus.UNRESOLVED.value,
        server_default=AliasResolutionStatus.UNRESOLVED.value,
    )

    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    entity: Mapped[KnowledgeEntity] = relationship(back_populates="aliases")


class IdentityResolutionCandidate(Base):
    """Audit-ready candidate identity merge pair with weighted signal breakdown."""

    __tablename__ = "identity_resolution_candidates"
    __table_args__ = (
        CheckConstraint("left_entity_id != right_entity_id", name="ck_identity_pair_distinct"),
        CheckConstraint(
            "match_score >= 0.0 AND match_score <= 1.0", name="ck_identity_score_range"
        ),
        UniqueConstraint(
            "project_id", "left_entity_id", "right_entity_id", name="uq_identity_candidates_pair"
        ),
        Index("ix_identity_candidates_project_status", "project_id", "decision_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    left_entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    right_entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )

    match_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    signal_breakdown_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=dict
    )

    policy_band: Mapped[str] = mapped_column(
        String(32), nullable=False, default=IdentityPolicyBand.MANUAL_REVIEW.value
    )
    decision_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=IdentityCandidateStatus.PENDING.value,
        server_default=IdentityCandidateStatus.PENDING.value,
    )

    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_state_json: Mapped[dict[str, Any] | None] = mapped_column(_JSON_VARIANT, nullable=True)

    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class KnowledgeRelationship(Base):
    """Canonical typed, directed edge in the knowledge graph."""

    __tablename__ = "knowledge_relationships"
    __table_args__ = (
        CheckConstraint(
            "source_entity_id != target_entity_id", name="ck_relationship_distinct_nodes"
        ),
        CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 1.0",
            name="ck_relationship_confidence_range",
        ),
        Index(
            "ix_relationships_project_source", "project_id", "source_entity_id", "relationship_type"
        ),
        Index(
            "ix_relationships_project_target", "project_id", "target_entity_id", "relationship_type"
        ),
        Index("ix_relationships_project_status", "project_id", "verification_status"),
        Index("ix_relationships_project_fingerprint", "project_id", "fingerprint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )

    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    relationship_basis: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RelationshipBasis.EXPLICIT.value,
        server_default=RelationshipBasis.EXPLICIT.value,
    )
    verification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RelationshipVerificationStatus.CANDIDATE.value,
        server_default=RelationshipVerificationStatus.CANDIDATE.value,
    )

    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=1.0)
    confidence_components_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=dict
    )
    discovery_method: Mapped[str] = mapped_column(
        String(64), nullable=False, default="exact_reference"
    )

    is_bidirectional_display: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_llm_assisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stale_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    source_entity: Mapped[KnowledgeEntity] = relationship(
        foreign_keys=[source_entity_id], back_populates="outbound_relationships"
    )
    target_entity: Mapped[KnowledgeEntity] = relationship(
        foreign_keys=[target_entity_id], back_populates="inbound_relationships"
    )
    evidence_links: Mapped[list[RelationshipEvidenceLink]] = relationship(
        back_populates="relationship", cascade="all, delete-orphan"
    )


class RelationshipEvidenceLink(Base):
    """Mandatory verifiable provenance connecting a KnowledgeRelationship to evidence."""

    __tablename__ = "relationship_evidence_links"
    __table_args__ = (
        Index("ix_rel_evidence_project", "project_id", "relationship_id"),
        Index("ix_rel_evidence_item", "project_id", "evidence_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    relationship_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_relationships.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence_chunks.id", ondelete="SET NULL"), nullable=True
    )
    knowledge_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="SET NULL"), nullable=True
    )

    evidence_role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RelationshipEvidenceRole.DIRECT_SUPPORT.value,
        server_default=RelationshipEvidenceRole.DIRECT_SUPPORT.value,
    )
    supporting_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_location_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=dict
    )
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    relationship: Mapped[KnowledgeRelationship] = relationship(back_populates="evidence_links")


class DecisionTraceabilityChain(Base):
    """Persistent index recording Decision -> Work Item -> PR -> Commit -> Component chains."""

    __tablename__ = "decision_traceability_chains"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "decision_entity_id", name="uq_traceability_project_decision"
        ),
        Index("ix_traceability_project_completeness", "project_id", "completeness_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    decision_entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    completeness_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TraceabilityCompletenessStatus.UNTRACED.value,
        server_default=TraceabilityCompletenessStatus.UNTRACED.value,
    )

    work_item_ids_json: Mapped[list[str]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=list
    )
    pull_request_ids_json: Mapped[list[str]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=list
    )
    commit_ids_json: Mapped[list[str]] = mapped_column(_JSON_VARIANT, nullable=False, default=list)
    component_ids_json: Mapped[list[str]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=list
    )
    relationship_ids_json: Mapped[list[str]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=list
    )
    missing_links_json: Mapped[list[str]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=list
    )
    uncertainty_reasons_json: Mapped[list[str]] = mapped_column(
        _JSON_VARIANT, nullable=False, default=list
    )

    aggregate_confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=1.0)
    earliest_event_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    latest_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class KnowledgeTimelineEvent(Base):
    """Chronological project event log bound to graph entities and verifiable source timestamps."""

    __tablename__ = "knowledge_timeline_events"
    __table_args__ = (
        Index("ix_timeline_project_occurred", "project_id", "occurred_at"),
        Index("ix_timeline_project_entity", "project_id", "entity_id", "occurred_at"),
        Index("ix_timeline_project_event_type", "project_id", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    secondary_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_entities.id", ondelete="SET NULL"), nullable=True
    )
    relationship_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_relationships.id", ondelete="SET NULL"), nullable=True
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False, index=True
    )

    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    timestamp_precision: Mapped[str] = mapped_column(
        String(32), nullable=False, default=TimelinePrecision.EXACT_DATETIME.value
    )
    timestamp_origin: Mapped[str] = mapped_column(
        String(32), nullable=False, default=TimelineOrigin.SOURCE_API.value
    )

    event_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RelationshipReconstructionRun(Base):
    """Lifecycle tracking for asynchronous relationship discovery and graph rebuild runs."""

    __tablename__ = "relationship_reconstruction_runs"
    __table_args__ = (
        Index("ix_rel_runs_project_created", "project_id", "created_at"),
        Index("ix_rel_runs_project_status", "project_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RelationshipRunStatus.QUEUED.value,
        server_default=RelationshipRunStatus.QUEUED.value,
    )

    entities_discovered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    relationships_discovered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    explicit_links_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inferred_links_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
