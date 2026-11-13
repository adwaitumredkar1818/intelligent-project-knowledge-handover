# The Handover — Relationship Graph & Knowledge Topology Architecture

**Module**: Relationship Explorer (Module 4)  
**Status**: Architecture Baseline & Canonical Specification  

---

## 1. Architectural Philosophy: PostgreSQL as Canonical Graph Store

### Strict Constraint: No External Graph Database
Per `AGENTS.md` and confirmed project governance, **The Handover does NOT introduce Neo4j, ArangoDB, Amazon Neptune, or a dedicated graph database**.
- Graph nodes and edges are modeled directly in PostgreSQL using normalized relational schema structures.
- All entities, edges, evidence citations, and traceability chains are subject to ACID transactional consistency.
- Standard B-Tree and compound indexes support sub-millisecond edge traversals up to depth 5 for project workspaces.
- In-memory graph traversal algorithms (bounded BFS/DFS, cycle detection, topological sort) execute in the backend service layer with strict depth (`depth <= 5`) and element caps (`limit_nodes <= 1000`, `limit_edges <= 2000`) to guarantee predictable memory footprint.

---

## 2. Relational Schema Architecture (Migration `0011_relationship_explorer`)

```text
┌────────────────────────────────┐       ┌────────────────────────────────┐
│        knowledge_entities      │       │     knowledge_relationships    │
├────────────────────────────────┤       ├────────────────────────────────┤
│ id (PK, UUID)                  │◀──┐   │ id (PK, UUID)                  │
│ organisation_id (FK)           │   └───│ source_entity_id (FK)          │
│ project_id (FK)                │◀──────│ target_entity_id (FK)          │
│ entity_type (Enum)             │       │ relationship_type (Enum)       │
│ canonical_name (VARCHAR)       │       │ relationship_basis (Enum)      │
│ primary_evidence_id (FK)       │       │ verification_status (Enum)     │
│ resolution_status (Enum)       │       │ confidence_score (NUMERIC)     │
│ merged_into_entity_id (FK)     │       │ relationship_fingerprint (SHA) │
└────────────────────────────────┘       └────────────────────────────────┘
                 │                                        │
                 ▼                                        ▼
┌────────────────────────────────┐       ┌────────────────────────────────┐
│         entity_aliases         │       │   relationship_evidence_links  │
├────────────────────────────────┤       ├────────────────────────────────┤
│ id (PK, UUID)                  │       │ id (PK, UUID)                  │
│ entity_id (FK)                 │       │ relationship_id (FK)           │
│ alias_value (VARCHAR)          │       │ evidence_id (FK)               │
│ source_provider (VARCHAR)      │       │ chunk_id (FK)                  │
│ is_primary (BOOL)              │       │ citation_excerpt (TEXT)        │
└────────────────────────────────┘       └────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────┐       ┌────────────────────────────────┐
│   identity_candidates          │       │ decision_traceability_chains   │
├────────────────────────────────┤       ├────────────────────────────────┤
│ left_entity_id (FK)            │       │ decision_entity_id (FK)        │
│ right_entity_id (FK)           │       │ work_item_ids (JSONB)          │
│ match_score (NUMERIC)          │       │ pull_request_ids (JSONB)       │
│ policy_band (Enum)             │       │ commit_ids (JSONB)             │
│ decision_status (Enum)         │       │ component_ids (JSONB)          │
└────────────────────────────────┘       │ completeness_status (Enum)     │
                                         └────────────────────────────────┘
```

---

## 3. Discovery Pipeline & Tiered Linking

The reconstruction pipeline operates in 5 deterministic tiers:

1. **Exact Identifier Linking**:
   - Regex extraction of Jira keys (`[A-Z][A-Z0-9]+-\d+`).
   - GitHub PR references (`#\d+`, `pull/\d+`).
   - Git SHA hashes (`[0-9a-f]{7,40}`).
   - ADR titles (`ADR-\d+`).
   - Deterministic foreign key resolution -> `relationship_basis = 'explicit'`.

2. **Structured Connector Metadata Linking**:
   - Commits authored by known GitHub user.
   - Jira issues reported by known user identity.
   - PR reviews performed by team members.
   - Direct API links -> `relationship_basis = 'explicit'`.

3. **Contextual File Path & Component Matching**:
   - Inferred module association based on source code directory hierarchy (`backend/app/...`, `frontend/src/...`).
   - `relationship_basis = 'inferred'`.

4. **Semantic Matching**:
   - Vector similarity across chunk embeddings using ChromaDB.
   - Threshold >= 0.75 -> candidate edge.

5. **Qwen3 8B LLM-Assisted Extraction**:
   - Discovers latent causal relationships ("decision X was taken to mitigate risk Y").
   - Strictly validates extracted source and target against authorized project entities.
   - `relationship_basis = 'inferred'`, requiring human review before verified status.

---

## 4. Fail-Closed Security & Read-Time Source ACL Enforcement

### Critical Security Rule: Project Membership != Source Access
A user who belongs to a project does **not** inherit permission to see private evidence from third-party sources (e.g. GitHub repos, Jira boards) connected by other team members unless their source permissions permit it.

### Enforcement Strategy
1. The repository constructs a dynamic subquery identifying accessible evidence items:
   ```sql
   SELECT id FROM evidence_items
   WHERE project_id = :project_id
     AND (acl_scope = 'project_members' OR source_connection_id IN (:user_authorized_connections))
   ```
2. When projecting graph nodes and edges:
   - **Edges**: Any edge whose supporting evidence links are exclusively restricted is **omitted from the caller's graph projection**.
   - **Nodes**: Any node whose primary evidence is restricted has its details and sensitive labels redacted or hidden unless a public project reference exists.
   - Single item lookups (`GET /relationships/{id}`, `GET /relationships/entities/{id}`) **fail closed with `403 FORBIDDEN`** if the caller lacks source access.

---

## 5. React Flow Frontend Projection Contract

The backend transforms the relational graph into standard React Flow compatible JSON format:
```json
{
  "nodes": [
    {
      "id": "uuid",
      "type": "customNode",
      "data": {
        "label": "ADR-002 GraphQL vs REST",
        "entityType": "decision",
        "sourceProvider": "document_upload",
        "verificationStatus": "verified",
        "isRootBlocker": false
      },
      "position": { "x": 0, "y": 0 }
    }
  ],
  "edges": [
    {
      "id": "uuid",
      "source": "uuid-source",
      "target": "uuid-target",
      "label": "AFFECTS_COMPONENT",
      "style": { "strokeDasharray": "0" },
      "data": {
        "relationshipType": "AFFECTS_COMPONENT",
        "basis": "explicit",
        "verificationStatus": "verified",
        "confidence": 1.0
      }
    }
  ],
  "total_nodes": 24,
  "total_edges": 31
}
```
Visual cues conform to product guidelines:
- Solid edges: Explicit / Verified relationships.
- Dashed edges: Inferred / Candidate relationships.
- Red badge: Conflicting / Disputed edges.
