"""Dependency intelligence, cycle detection, and root blocker analysis.

Traverses dependency graphs formed by:
- BLOCKS
- BLOCKED_BY
- DEPENDS_ON
- ARCHITECTURAL_DEPENDENCY

Detects circular dependencies via DFS back-edge detection, identifies root blockers,
and computes transitive dependency impact trees.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import RelationshipType
from app.models.relationship import KnowledgeEntity, KnowledgeRelationship
from app.schemas.relationship import DependencyEdge, DependencyGraphResponse, DependencyNode

logger = logging.getLogger("app.services.dependency_intelligence")

_DEPENDENCY_TYPES: frozenset[str] = frozenset(
    [
        RelationshipType.BLOCKS.value,
        RelationshipType.BLOCKED_BY.value,
        RelationshipType.DEPENDS_ON.value,
        RelationshipType.ARCHITECTURAL_DEPENDENCY.value,
    ]
)


class DependencyIntelligenceService:
    """Analyzes directed dependency chains, circularities, and root blockers."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def analyze_dependencies(
        self,
        *,
        project_id: uuid.UUID,
        root_entity_id: uuid.UUID | None = None,
        max_depth: int = 10,
    ) -> DependencyGraphResponse:
        """Build dependency graph, run cycle detection, and identify blockers."""
        # Query all active dependency edges in the project
        query = select(KnowledgeRelationship).where(
            KnowledgeRelationship.project_id == project_id,
            KnowledgeRelationship.relationship_type.in_(_DEPENDENCY_TYPES),
        )
        relationships = list(self._session.execute(query).scalars().all())

        # Normalize directed dependency edges:
        # We define: Source depends on Target (Target is prerequisite / blocker of Source)
        # If rel is BLOCKS: A blocks B -> B depends on A (B -> A)
        # If rel is BLOCKED_BY: A is blocked by B -> A depends on B (A -> B)
        # If rel is DEPENDS_ON: A depends on B -> A depends on B (A -> B)
        # If rel is ARCHITECTURAL_DEPENDENCY: A depends on B -> A depends on B (A -> B)
        adj_list: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
        edge_metadata: dict[tuple[uuid.UUID, uuid.UUID], KnowledgeRelationship] = {}
        all_node_ids: set[uuid.UUID] = set()

        for rel in relationships:
            s_id = rel.source_entity_id
            t_id = rel.target_entity_id

            if rel.relationship_type == RelationshipType.BLOCKS.value:
                # Target depends on Source
                dep_source = t_id
                dep_target = s_id
            else:
                dep_source = s_id
                dep_target = t_id

            adj_list[dep_source].append(dep_target)
            edge_metadata[(dep_source, dep_target)] = rel
            all_node_ids.add(dep_source)
            all_node_ids.add(dep_target)

        # Preload entities
        entities_stmt = select(KnowledgeEntity).where(
            KnowledgeEntity.id.in_(list(all_node_ids)),
            KnowledgeEntity.is_deleted.is_(False),
        )
        entities = {e.id: e for e in self._session.execute(entities_stmt).scalars().all()}

        # Filter nodes if root_entity_id is specified (reachable subgraph)
        if root_entity_id is not None and root_entity_id in entities:
            reachable: set[uuid.UUID] = set()
            queue = [(root_entity_id, 0)]
            while queue:
                curr, depth = queue.pop(0)
                if curr in reachable or depth > max_depth:
                    continue
                reachable.add(curr)
                for neighbor in adj_list.get(curr, []):
                    if neighbor not in reachable:
                        queue.append((neighbor, depth + 1))
            all_node_ids = reachable

        # Detect Cycles via DFS (finding back-edges in directed graph)
        visited: dict[uuid.UUID, int] = {}  # 0: unvisited, 1: visiting, 2: visited
        cycles: list[list[str]] = []

        def dfs_detect_cycle(u: uuid.UUID, path: list[uuid.UUID]) -> None:
            visited[u] = 1
            path.append(u)
            for v in adj_list.get(u, []):
                if v not in entities or v not in all_node_ids:
                    continue
                if visited.get(v, 0) == 1:
                    # Cycle detected: back-edge to an ancestor in recursion stack
                    cycle_start = path.index(v)
                    cycle_nodes = path[cycle_start:] + [v]
                    cycle_names = [entities[n].canonical_name for n in cycle_nodes if n in entities]
                    cycles.append(cycle_names)
                elif visited.get(v, 0) == 0:
                    dfs_detect_cycle(v, path)
            path.pop()
            visited[u] = 2

        for node in list(all_node_ids):
            if visited.get(node, 0) == 0:
                dfs_detect_cycle(node, [])

        # Identify Root Blockers vs Blocked Items
        # A root blocker is a node that blocks others (has incoming dependency edges)
        # but does NOT depend on any other node (out-degree in dependency graph == 0).
        in_degree: dict[uuid.UUID, int] = defaultdict(int)
        out_degree: dict[uuid.UUID, int] = defaultdict(int)
        for u in all_node_ids:
            for v in adj_list.get(u, []):
                if v in all_node_ids:
                    out_degree[u] += 1
                    in_degree[v] += 1

        root_blocker_nodes: list[DependencyNode] = []
        blocked_item_nodes: list[DependencyNode] = []

        for nid in all_node_ids:
            ent = entities.get(nid)
            if not ent:
                continue
            dnode = DependencyNode(
                entity_id=ent.id,
                name=ent.canonical_name,
                entity_type=ent.entity_type,
                status=ent.resolution_status,
            )
            # Root blocker: blocks others (in_degree > 0) but not blocked by anything (out_degree == 0)
            if in_degree[nid] > 0 and out_degree[nid] == 0:
                root_blocker_nodes.append(dnode)
            # Blocked item: depends on something (out_degree > 0)
            if out_degree[nid] > 0:
                blocked_item_nodes.append(dnode)

        # Build response nodes and edges
        response_nodes = [
            DependencyNode(
                entity_id=e.id,
                name=e.canonical_name,
                entity_type=e.entity_type,
                status=e.resolution_status,
            )
            for e in entities.values()
            if e.id in all_node_ids
        ]

        response_edges: list[DependencyEdge] = []
        for (u, v), rel in edge_metadata.items():
            if u in all_node_ids and v in all_node_ids:
                response_edges.append(
                    DependencyEdge(
                        source_id=u,
                        target_id=v,
                        dependency_type=rel.relationship_type,
                        status=rel.verification_status,
                        confidence=float(rel.confidence_score),
                        relationship_basis=rel.relationship_basis,
                    )
                )

        return DependencyGraphResponse(
            nodes=response_nodes,
            edges=response_edges,
            detected_cycles=cycles,
            has_circular_dependency=len(cycles) > 0,
            root_blockers=root_blocker_nodes,
            blocked_items=blocked_item_nodes,
        )
