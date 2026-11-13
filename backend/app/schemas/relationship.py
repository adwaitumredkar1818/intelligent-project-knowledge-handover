"""Pydantic schemas for Relationship Explorer API contracts and graph projections."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base schema enforcing attribute extraction from ORM models."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ------------------------------------------------------------------------------
# Entity & Alias Schemas
# ------------------------------------------------------------------------------


class EntityAliasResponse(BaseSchema):
    """Source-specific alias representation."""

    id: uuid.UUID
    entity_id: uuid.UUID
    alias_value: str
    normalized_alias: str
    alias_kind: str
    source_provider: str
    source_external_id: str | None = None
    confidence_score: float
    resolution_status: str
    reviewed_at: datetime | None = None
    created_at: datetime


class KnowledgeEntityResponse(BaseSchema):
    """Canonical knowledge graph entity node response."""

    id: uuid.UUID
    project_id: uuid.UUID
    organisation_id: uuid.UUID
    entity_type: str
    canonical_name: str
    normalized_name: str
    description: str | None = None
    resolution_status: str
    merged_into_entity_id: uuid.UUID | None = None
    primary_knowledge_item_id: uuid.UUID | None = None
    primary_evidence_id: uuid.UUID | None = None
    external_source_id: str | None = None
    source_provider: str | None = None
    confidence_score: float
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    is_synthetic: bool = False
    is_stale: bool = False
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    aliases: list[EntityAliasResponse] = Field(default_factory=list)


class EntityListResponse(BaseSchema):
    """Paginated entity listing."""

    items: list[KnowledgeEntityResponse]
    total: int
    limit: int
    offset: int


class IdentityCandidateResponse(BaseSchema):
    """Candidate identity merge pair with signal score breakdown."""

    id: uuid.UUID
    project_id: uuid.UUID
    left_entity_id: uuid.UUID
    right_entity_id: uuid.UUID
    match_score: float
    signal_breakdown_json: dict[str, Any]
    policy_band: str
    decision_status: str
    decided_by_user_id: uuid.UUID | None = None
    decided_at: datetime | None = None
    decision_rationale: str | None = None
    created_at: datetime
    left_entity: KnowledgeEntityResponse | None = None
    right_entity: KnowledgeEntityResponse | None = None


class IdentityReviewRequest(BaseModel):
    """Review action request for an identity candidate."""

    action: str = Field(description="'accept' to merge right into left, or 'reject'")
    rationale: str | None = Field(default=None, description="Reviewer reasoning")


# ------------------------------------------------------------------------------
# Relationship & Provenance Schemas
# ------------------------------------------------------------------------------


class RelationshipEvidenceLinkResponse(BaseSchema):
    """Verifiable evidence citation backing a relationship."""

    id: uuid.UUID
    relationship_id: uuid.UUID
    evidence_id: uuid.UUID
    evidence_chunk_id: uuid.UUID | None = None
    knowledge_item_id: uuid.UUID | None = None
    evidence_role: str
    supporting_excerpt: str | None = None
    source_location_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class KnowledgeRelationshipResponse(BaseSchema):
    """Typed, directed knowledge graph edge response."""

    id: uuid.UUID
    project_id: uuid.UUID
    organisation_id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: str
    relationship_basis: str
    verification_status: str
    confidence_score: float
    confidence_components_json: dict[str, Any] = Field(default_factory=dict)
    discovery_method: str
    is_bidirectional_display: bool = False
    is_llm_assisted: bool = False
    is_stale: bool = False
    stale_reason: str | None = None
    fingerprint: str
    reviewed_at: datetime | None = None
    review_note: str | None = None
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    evidence_links: list[RelationshipEvidenceLinkResponse] = Field(default_factory=list)
    source_entity: KnowledgeEntityResponse | None = None
    target_entity: KnowledgeEntityResponse | None = None


class RelationshipListResponse(BaseSchema):
    """Paginated relationships listing."""

    items: list[KnowledgeRelationshipResponse]
    total: int
    limit: int
    offset: int


class RelationshipReviewRequest(BaseModel):
    """Review submission request for a candidate relationship."""

    action: str = Field(description="'verify', 'reject', 'dispute', or 'request_evidence'")
    note: str | None = Field(default=None, description="Reviewer justification")


# ------------------------------------------------------------------------------
# Decision Traceability Schemas
# ------------------------------------------------------------------------------


class DecisionTraceabilityResponse(BaseSchema):
    """Decision-to-Implementation chain representation."""

    id: uuid.UUID
    project_id: uuid.UUID
    decision_entity_id: uuid.UUID
    decision_name: str | None = None
    completeness_status: str
    work_item_ids: list[str] = Field(default_factory=list, alias="work_item_ids_json")
    pull_request_ids: list[str] = Field(default_factory=list, alias="pull_request_ids_json")
    commit_ids: list[str] = Field(default_factory=list, alias="commit_ids_json")
    component_ids: list[str] = Field(default_factory=list, alias="component_ids_json")
    relationship_ids: list[str] = Field(default_factory=list, alias="relationship_ids_json")
    missing_links: list[str] = Field(default_factory=list, alias="missing_links_json")
    uncertainty_reasons: list[str] = Field(default_factory=list, alias="uncertainty_reasons_json")
    aggregate_confidence: float
    earliest_event_at: datetime | None = None
    latest_event_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TraceabilityListResponse(BaseSchema):
    """Listing of all decision traceability chains in a project."""

    items: list[DecisionTraceabilityResponse]
    total: int
    complete_count: int
    partially_traced_count: int
    untraced_count: int
    conflicting_count: int


# ------------------------------------------------------------------------------
# Graph Projection Schemas (React Flow Compatible)
# ------------------------------------------------------------------------------


class GraphNodeProjection(BaseModel):
    """Node projection formatted for future React Flow frontend."""

    id: str
    entity_id: uuid.UUID
    label: str
    description: str | None = None
    entity_type: str
    status: str
    source_provider: str | None = None
    verification_status: str
    confidence: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeProjection(BaseModel):
    """Edge projection formatted for future React Flow frontend."""

    id: str
    relationship_id: uuid.UUID
    source: str
    target: str
    relationship_type: str
    label: str
    relationship_basis: str
    verification_status: str
    confidence: float
    evidence_count: int
    source_provider: str | None = None
    supporting_evidence_available: bool = True
    is_bidirectional: bool = False


class GraphProjectionResponse(BaseModel):
    """Complete project graph projection with metadata."""

    nodes: list[GraphNodeProjection]
    edges: list[GraphEdgeProjection]
    total_nodes: int
    total_edges: int
    is_truncated: bool = False
    center_node_id: str | None = None
    depth: int = 1


class NodeDetailResponse(BaseModel):
    """Side panel detailed data for a selected graph node."""

    entity: KnowledgeEntityResponse
    incoming_edges: list[KnowledgeRelationshipResponse] = Field(default_factory=list)
    outgoing_edges: list[KnowledgeRelationshipResponse] = Field(default_factory=list)
    supporting_evidence_count: int = 0
    related_decisions: list[str] = Field(default_factory=list)
    related_work_items: list[str] = Field(default_factory=list)
    related_components: list[str] = Field(default_factory=list)
    timeline_events_count: int = 0


# ------------------------------------------------------------------------------
# Dependency Analysis Schemas
# ------------------------------------------------------------------------------


class DependencyNode(BaseModel):
    """Node within a dependency hierarchy."""

    entity_id: uuid.UUID
    name: str
    entity_type: str
    status: str | None = None


class DependencyEdge(BaseModel):
    """Dependency relationship edge."""

    source_id: uuid.UUID
    target_id: uuid.UUID
    dependency_type: str
    status: str
    confidence: float
    relationship_basis: str


class DependencyGraphResponse(BaseModel):
    """Dependency graph traversal result with cycle detection."""

    nodes: list[DependencyNode]
    edges: list[DependencyEdge]
    detected_cycles: list[list[str]] = Field(default_factory=list)
    has_circular_dependency: bool = False
    root_blockers: list[DependencyNode] = Field(default_factory=list)
    blocked_items: list[DependencyNode] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# Timeline Graph Event Schema
# ------------------------------------------------------------------------------


class TimelineEventGraphResponse(BaseSchema):
    """Chronological event projection bound to graph entities."""

    id: uuid.UUID
    entity_id: uuid.UUID
    secondary_entity_id: uuid.UUID | None = None
    relationship_id: uuid.UUID | None = None
    evidence_id: uuid.UUID
    event_type: str
    title: str
    summary: str | None = None
    occurred_at: datetime | None = None
    timestamp_precision: str
    timestamp_origin: str
    created_at: datetime
    entity_name: str | None = None
    entity_type: str | None = None


class TimelineGraphStreamResponse(BaseSchema):
    """Chronological stream of project graph events."""

    items: list[TimelineEventGraphResponse]
    total: int
    limit: int
    offset: int


# ------------------------------------------------------------------------------
# Reconstruction Run Schemas
# ------------------------------------------------------------------------------


class RelationshipReconstructionRunResponse(BaseSchema):
    """Asynchronous relationship discovery run telemetry."""

    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    entities_discovered_count: int
    relationships_discovered_count: int
    explicit_links_count: int
    inferred_links_count: int
    duration_ms: int | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ReconstructionTriggerRequest(BaseModel):
    """Request to trigger a relationship discovery run."""

    include_llm_suggestions: bool = Field(
        default=False, description="Whether to invoke Qwen3 8B for candidate classification"
    )
    force_rebuild: bool = Field(
        default=False, description="Re-evaluate all existing entities and relationships"
    )
