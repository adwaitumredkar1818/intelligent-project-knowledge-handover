"""Graph Projection Service for Relationship Explorer.

Produces frontend-ready React Flow node and edge structures with:
- Bounded depth BFS/DFS traversal
- Source-ACL fail-closed edge and node pruning
- Node side-panel detail aggregation
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import EntityType
from app.models.relationship import KnowledgeTimelineEvent
from app.repositories.relationship import EntityRepository, RelationshipRepository
from app.schemas.relationship import (
    GraphEdgeProjection,
    GraphNodeProjection,
    GraphProjectionResponse,
    KnowledgeEntityResponse,
    KnowledgeRelationshipResponse,
    NodeDetailResponse,
)
from app.services.relationship_taxonomy import get_display_label

logger = logging.getLogger("app.services.graph_projection")


class GraphProjectionService:
    """Projects relational PostgreSQL knowledge graph records into frontend React Flow format."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._entity_repo = EntityRepository(session)
        self._rel_repo = RelationshipRepository(session)

    def project_graph(
        self,
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool,
        center_node_id: uuid.UUID | None = None,
        depth: int = 2,
        entity_type_filter: str | None = None,
        verification_status_filter: str | None = None,
        limit_nodes: int = 250,
        limit_edges: int = 500,
    ) -> GraphProjectionResponse:
        """Generate a React Flow-compatible projection of the accessible project knowledge graph."""
        # Retrieve caller-accessible relationships
        accessible_rels, _ = self._rel_repo.list_accessible_relationships(
            project_id=project_id,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
            verification_status=verification_status_filter,
            limit=limit_edges,
        )

        # Retrieve caller-accessible entities
        accessible_entities, _ = self._entity_repo.list_accessible_entities(
            project_id=project_id,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
            entity_type=entity_type_filter,
            limit=limit_nodes,
        )
        entity_map = {e.id: e for e in accessible_entities}

        # If center_node_id is specified, compute BFS neighborhood up to `depth`
        if center_node_id is not None and center_node_id in entity_map:
            adj: dict[uuid.UUID, set[uuid.UUID]] = {e_id: set() for e_id in entity_map}
            for r in accessible_rels:
                if r.source_entity_id in adj and r.target_entity_id in adj:
                    adj[r.source_entity_id].add(r.target_entity_id)
                    adj[r.target_entity_id].add(r.source_entity_id)

            visited: set[uuid.UUID] = {center_node_id}
            queue: list[tuple[uuid.UUID, int]] = [(center_node_id, 0)]
            while queue:
                curr, d = queue.pop(0)
                if d >= depth:
                    continue
                for neighbor in adj.get(curr, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, d + 1))

            # Restrict entities and relationships to visited set
            entity_map = {e_id: ent for e_id, ent in entity_map.items() if e_id in visited}
            accessible_rels = [
                r
                for r in accessible_rels
                if r.source_entity_id in visited and r.target_entity_id in visited
            ]

        # Build GraphNodeProjections
        nodes: list[GraphNodeProjection] = []
        for ent in entity_map.values():
            nodes.append(
                GraphNodeProjection(
                    id=str(ent.id),
                    entity_id=ent.id,
                    label=ent.canonical_name,
                    description=ent.description,
                    entity_type=ent.entity_type,
                    status=ent.resolution_status,
                    source_provider=ent.source_provider,
                    verification_status=ent.resolution_status,
                    confidence=float(ent.confidence_score),
                    metadata=ent.metadata_json or {},
                )
            )

        # Build GraphEdgeProjections
        edges: list[GraphEdgeProjection] = []
        for r in accessible_rels:
            # Ensure both endpoints exist in projected nodes
            if r.source_entity_id not in entity_map or r.target_entity_id not in entity_map:
                continue

            edges.append(
                GraphEdgeProjection(
                    id=str(r.id),
                    relationship_id=r.id,
                    source=str(r.source_entity_id),
                    target=str(r.target_entity_id),
                    relationship_type=r.relationship_type,
                    label=get_display_label(r.relationship_type),
                    relationship_basis=r.relationship_basis,
                    verification_status=r.verification_status,
                    confidence=float(r.confidence_score),
                    evidence_count=len(r.evidence_links),
                    source_provider=None,
                    supporting_evidence_available=len(r.evidence_links) > 0,
                    is_bidirectional=r.is_bidirectional_display,
                )
            )

        return GraphProjectionResponse(
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges),
            is_truncated=len(nodes) >= limit_nodes or len(edges) >= limit_edges,
            center_node_id=str(center_node_id) if center_node_id else None,
            depth=depth,
        )

    def get_node_details(
        self,
        *,
        project_id: uuid.UUID,
        entity_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool,
    ) -> NodeDetailResponse:
        """Fetch complete detailed metadata, adjacent relationships, and related entities for a node."""
        entity, denied = self._entity_repo.get_accessible_entity(
            entity_id,
            project_id=project_id,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
        )
        if entity is None or denied:
            raise PermissionError("Access denied or entity not found.")

        # Adjacent relationships
        rels, _ = self._rel_repo.list_accessible_relationships(
            project_id=project_id,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
            entity_id=entity_id,
            limit=100,
        )

        incoming: list[KnowledgeRelationshipResponse] = []
        outgoing: list[KnowledgeRelationshipResponse] = []
        decisions: list[str] = []
        work_items: list[str] = []
        components: list[str] = []
        evidence_count = 0

        for r in rels:
            evidence_count += len(r.evidence_links)
            r_schema = KnowledgeRelationshipResponse.model_validate(r)
            if r.target_entity_id == entity_id:
                incoming.append(r_schema)
                other = r.source_entity
            else:
                outgoing.append(r_schema)
                other = r.target_entity

            if other:
                if other.entity_type == EntityType.DECISION.value:
                    decisions.append(other.canonical_name)
                elif other.entity_type == EntityType.WORK_ITEM.value:
                    work_items.append(other.canonical_name)
                elif other.entity_type == EntityType.COMPONENT.value:
                    components.append(other.canonical_name)

        # Timeline event count
        timeline_count = (
            self._session.execute(
                select(KnowledgeTimelineEvent.id).where(
                    KnowledgeTimelineEvent.project_id == project_id,
                    KnowledgeTimelineEvent.entity_id == entity_id,
                )
            )
            .scalars()
            .all()
        )

        return NodeDetailResponse(
            entity=KnowledgeEntityResponse.model_validate(entity),
            incoming_edges=incoming,
            outgoing_edges=outgoing,
            supporting_evidence_count=evidence_count,
            related_decisions=sorted(list(set(decisions))),
            related_work_items=sorted(list(set(work_items))),
            related_components=sorted(list(set(components))),
            timeline_events_count=len(timeline_count),
        )
