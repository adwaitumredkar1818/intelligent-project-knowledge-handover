# Relationship Explorer Module — Complete Implementation Plan

**Product**: The Handover (Intelligent Project Knowledge Reconstruction & Handover Platform)  
**Module**: Relationship Explorer (Module 4)  
**Plan Date**: 2026-11-13  
**Target Milestone**: Complete Backend Implementation (Cross-Source Knowledge Graph, Traceability & APIs)  
**Prerequisites**: Alembic Head `0010_knowledge_domains`, Ollama Qwen3 8B, nomic-embed-text, Evidence Workspace, Source ACLs

---

## 1. Architectural Baseline & Principles

1. **PostgreSQL as Sole Canonical Graph Store**:
   - Zero graph databases (no Neo4j, ArangoDB, or Memgraph).
   - Zero external message brokers (no Redis, Celery, or Kafka).
   - Graph nodes and edges are stored in PostgreSQL relational tables using indexed foreign keys, compound uniqueness constraints, and bounded recursive/iterative traversals in Python.
2. **Core Governance Principle**:
   > **"Every relationship must have a traceable basis. The AI must never invent a relationship and present it as established project knowledge."**
3. **Dual-Classification System**:
   - Every relationship must carry:
     1. **Basis**: `explicit` (direct source link), `inferred` (heuristic/semantic/LLM suggestion), or `human_confirmed` (approved by authorized reviewer).
     2. **Verification Status**: `candidate`, `verified`, `rejected`, `conflicted`, `unresolved`, `stale`.
4. **Security Boundary**:
   - `Project Membership != Source Access`. Every graph query strictly filters nodes, edges, timeline events, and traceability chains against caller-accessible evidence IDs via `SourceAccessPolicyService`.

---

## 2. Graph Entity Taxonomy & Persistence Model

### 2.1 Entity Types (`EntityType` Enum)
13 canonical project entity types:
1. `person` — Project members, authors, assignees, reporters, reviewers.
2. `discussion` — Meeting notes, Jira comments, PR reviews/comments, authorised Slack threads.
3. `decision` — Architectural and process decisions extracted from Knowledge Intelligence.
4. `work_item` — Jira issues, GitHub issues, tasks extracted from documents.
5. `pull_request` — GitHub pull requests with state, branch, and review metadata.
6. `commit` — Git commits with SHA, message, author, and timestamp.
7. `document` — Uploaded technical specs, ADRs, PDFs, DOCXs.
8. `technical_component` — Services, architectural modules, layers, databases, APIs.
9. `dependency` — Inter-system, inter-task, or external dependency records.
10. `risk` — Blockers, technical risks, operational risks.
11. `bug` — Known defects, issues flagged in evidence.
12. `repository` — GitHub repositories.
13. `organisation` — Tenant organisation anchor.

### 2.2 Relational Tables (Alembic `0011_relationship_explorer`)

```
                          ┌──────────────────────────┐
                          │    knowledge_entities    │
                          └─────────────┬────────────┘
                                        │ 1
                                        │
                         ┌──────────────┴──────────────┐
                       * │                           * │
            ┌────────────▼───────────┐    ┌────────────▼───────────┐
            │     entity_aliases     │    │ knowledge_relationships│
            └────────────────────────┘    └─────────────┬──────────┘
                                                        │ 1
                                                        │ *
                                          ┌─────────────▼──────────┐
                                          │relationship_evidence_  │
                                          │        links           │
                                          └────────────────────────┘
```

#### Table 1: `knowledge_entities`
- `id` (UUID, PK)
- `organisation_id` (UUID, FK -> `organisations.id`, CASCADE)
- `project_id` (UUID, FK -> `projects.id`, CASCADE)
- `entity_type` (VARCHAR(32), NOT NULL, check constraint on 13 types)
- `canonical_name` (VARCHAR(255), NOT NULL)
- `normalized_name` (VARCHAR(255), NOT NULL, lowercase stripped)
- `description` (TEXT, NULL)
- `resolution_status` (VARCHAR(32), default `'canonical'`, check: `unresolved`, `canonical`, `merged`, `disputed`)
- `merged_into_entity_id` (UUID, FK -> `knowledge_entities.id` SET NULL, for non-destructive merges)
- `primary_knowledge_item_id` (UUID, FK -> `knowledge_items.id` SET NULL)
- `primary_evidence_id` (UUID, FK -> `evidence_items.id` SET NULL)
- `external_source_id` (VARCHAR(255), NULL)
- `source_provider` (VARCHAR(64), NULL)
- `confidence_score` (NUMERIC(4, 3), default 1.000)
- `metadata_json` (JSONB / JSON Variant)
- `is_synthetic` (BOOLEAN, default False)
- `is_stale` (BOOLEAN, default False)
- `is_deleted` (BOOLEAN, default False)
- `first_observed_at` (TIMESTAMPTZ, NULL)
- `last_observed_at` (TIMESTAMPTZ, NULL)
- `created_at`, `updated_at` (TIMESTAMPTZ)
- *Indexes*: `(project_id, entity_type, normalized_name)`, `(project_id, resolution_status)`, `(project_id, primary_evidence_id)`

#### Table 2: `entity_aliases`
- `id` (UUID, PK)
- `entity_id` (UUID, FK -> `knowledge_entities.id`, CASCADE)
- `organisation_id`, `project_id` (UUID, FKs)
- `alias_value` (VARCHAR(255), NOT NULL)
- `normalized_alias` (VARCHAR(255), NOT NULL)
- `alias_kind` (VARCHAR(32), NOT NULL: `username`, `display_name`, `email`, `account_id`, `shorthand`)
- `source_provider` (VARCHAR(64), NOT NULL)
- `source_external_id` (VARCHAR(255), NULL)
- `confidence_score` (NUMERIC(4, 3), default 1.000)
- `resolution_status` (VARCHAR(32), default `'unresolved'`, check: `unresolved`, `candidate`, `accepted`, `rejected`)
- `reviewed_by_user_id` (UUID, FK -> `users.id` SET NULL)
- `reviewed_at` (TIMESTAMPTZ, NULL)
- `created_at` (TIMESTAMPTZ)
- *Index*: `(project_id, normalized_alias)`

#### Table 3: `identity_resolution_candidates`
- `id` (UUID, PK)
- `organisation_id`, `project_id` (UUID, FKs)
- `left_entity_id`, `right_entity_id` (UUID, FKs -> `knowledge_entities.id`, CASCADE)
- `match_score` (NUMERIC(4, 3), NOT NULL)
- `signal_breakdown_json` (JSONB, NOT NULL)
- `policy_band` (VARCHAR(32), check: `strong_candidate`, `manual_review`, `separate`)
- `decision_status` (VARCHAR(32), default `'pending'`, check: `pending`, `accepted`, `rejected`, `reverted`)
- `decided_by_user_id` (UUID, FK -> `users.id` SET NULL)
- `decided_at` (TIMESTAMPTZ, NULL)
- `decision_rationale` (TEXT, NULL)
- `previous_state_json` (JSONB, NULL)
- *Unique Constraint*: `(project_id, left_entity_id, right_entity_id)`

#### Table 4: `knowledge_relationships`
- `id` (UUID, PK)
- `organisation_id`, `project_id` (UUID, FKs)
- `source_entity_id`, `target_entity_id` (UUID, FKs -> `knowledge_entities.id`, CASCADE)
- `relationship_type` (VARCHAR(64), NOT NULL, check constraint on controlled types)
- `relationship_basis` (VARCHAR(32), NOT NULL, check: `explicit`, `inferred`, `human_confirmed`)
- `verification_status` (VARCHAR(32), NOT NULL, check: `candidate`, `verified`, `rejected`, `conflicted`, `unresolved`, `stale`)
- `confidence_score` (NUMERIC(4, 3), NOT NULL)
- `confidence_components_json` (JSONB, NOT NULL)
- `discovery_method` (VARCHAR(64), NOT NULL: `exact_reference`, `structured_link`, `contextual_overlap`, `semantic_similarity`, `llm_suggestion`, `human_manual`)
- `is_bidirectional_display` (BOOLEAN, default False)
- `is_llm_assisted` (BOOLEAN, default False)
- `is_stale` (BOOLEAN, default False)
- `stale_reason` (TEXT, NULL)
- `fingerprint` (VARCHAR(64), NOT NULL)
- `reviewed_by_user_id` (UUID, FK -> `users.id` SET NULL)
- `reviewed_at` (TIMESTAMPTZ, NULL)
- `review_note` (TEXT, NULL)
- `first_observed_at`, `last_observed_at` (TIMESTAMPTZ, NULL)
- `created_at`, `updated_at` (TIMESTAMPTZ)
- *Indexes*: `(project_id, source_entity_id, relationship_type)`, `(project_id, target_entity_id, relationship_type)`, `(project_id, verification_status)`

#### Table 5: `relationship_evidence_links`
- `id` (UUID, PK)
- `relationship_id` (UUID, FK -> `knowledge_relationships.id`, CASCADE)
- `organisation_id`, `project_id` (UUID, FKs)
- `evidence_id` (UUID, FK -> `evidence_items.id`, CASCADE)
- `evidence_chunk_id` (UUID, FK -> `evidence_chunks.id` SET NULL)
- `knowledge_item_id` (UUID, FK -> `knowledge_items.id` SET NULL)
- `evidence_role` (VARCHAR(32), NOT NULL, check: `direct_support`, `corroboration`, `context`, `contradiction`)
- `supporting_excerpt` (TEXT, NULL)
- `source_location_json` (JSONB, NULL)
- `created_at` (TIMESTAMPTZ)

#### Table 6: `decision_traceability_chains`
- `id` (UUID, PK)
- `organisation_id`, `project_id` (UUID, FKs)
- `decision_entity_id` (UUID, FK -> `knowledge_entities.id`, CASCADE)
- `completeness_status` (VARCHAR(32), check: `complete`, `partially_traced`, `untraced`, `conflicting`)
- `work_item_ids_json` (JSONB, list of UUIDs)
- `pull_request_ids_json` (JSONB, list of UUIDs)
- `commit_ids_json` (JSONB, list of UUIDs)
- `component_ids_json` (JSONB, list of UUIDs)
- `relationship_ids_json` (JSONB, list of UUIDs)
- `missing_links_json` (JSONB, list of missing stages)
- `uncertainty_reasons_json` (JSONB, list of explanations)
- `aggregate_confidence` (NUMERIC(4, 3), NOT NULL)
- `earliest_event_at`, `latest_event_at` (TIMESTAMPTZ, NULL)
- `created_at`, `updated_at` (TIMESTAMPTZ)

#### Table 7: `knowledge_timeline_events`
- `id` (UUID, PK)
- `organisation_id`, `project_id` (UUID, FKs)
- `entity_id` (UUID, FK -> `knowledge_entities.id`, CASCADE)
- `secondary_entity_id` (UUID, FK -> `knowledge_entities.id` SET NULL)
- `relationship_id` (UUID, FK -> `knowledge_relationships.id` SET NULL)
- `evidence_id` (UUID, FK -> `evidence_items.id`, CASCADE)
- `event_type` (VARCHAR(64), NOT NULL)
- `title` (VARCHAR(255), NOT NULL)
- `summary` (TEXT, NULL)
- `occurred_at` (TIMESTAMPTZ, NULL)
- `timestamp_precision` (VARCHAR(32), check: `exact_datetime`, `date_only`, `month_only`, `unknown`)
- `timestamp_origin` (VARCHAR(32), check: `source_api`, `source_changelog`, `source_commit`, `document_header`, `text_date_mention`, `unknown`)
- `event_fingerprint` (VARCHAR(64), NOT NULL)
- `created_at` (TIMESTAMPTZ)

#### Table 8: `relationship_reconstruction_runs`
- `id` (UUID, PK)
- `organisation_id`, `project_id` (UUID, FKs)
- `status` (VARCHAR(32), check: `queued`, `running`, `completed`, `failed`, `cancelled`)
- `entities_discovered_count` (INTEGER, default 0)
- `relationships_discovered_count` (INTEGER, default 0)
- `explicit_links_count` (INTEGER, default 0)
- `inferred_links_count` (INTEGER, default 0)
- `duration_ms` (INTEGER, NULL)
- `created_at`, `completed_at` (TIMESTAMPTZ)

---

## 3. Relationship Taxonomy & Validation Registry

Strict registry mapping `(allowed_source_types, allowed_target_types, direction, bidirectional_display)`:

```python
RELATIONSHIP_TAXONOMY = {
    # Decision relationships
    "DECISION_REFERENCED_IN_DISCUSSION": ({"decision"}, {"discussion"}, False),
    "DECISION_RECORDED_IN_DOCUMENT": ({"decision"}, {"document"}, False),
    "DECISION_IMPLEMENTED_BY": ({"decision"}, {"work_item", "pull_request", "commit"}, False),
    "DECISION_AFFECTS_COMPONENT": ({"decision"}, {"technical_component"}, False),
    "DECISION_SUPERSEDES": ({"decision"}, {"decision"}, False),
    "DECISION_CONFLICTS_WITH": ({"decision"}, {"decision"}, True),

    # Work relationships
    "WORK_ITEM_TRACKED_BY": ({"work_item"}, {"work_item", "document"}, False),
    "WORK_ITEM_IMPLEMENTED_BY": ({"work_item"}, {"pull_request", "commit"}, False),
    "WORK_ITEM_BLOCKED_BY": ({"work_item"}, {"work_item", "risk", "bug"}, False),
    "WORK_ITEM_DEPENDS_ON": ({"work_item"}, {"work_item", "dependency"}, False),
    "WORK_ITEM_RELATED_TO": ({"work_item"}, {"work_item"}, True),
    "WORK_ITEM_ADDRESSED_BY_COMMIT": ({"work_item"}, {"commit"}, False),

    # GitHub relationships
    "COMMIT_BELONGS_TO_PULL_REQUEST": ({"commit"}, {"pull_request"}, False),
    "PULL_REQUEST_REFERENCES_ISSUE": ({"pull_request"}, {"work_item"}, False),
    "PULL_REQUEST_MODIFIES_COMPONENT": ({"pull_request"}, {"technical_component"}, False),
    "COMMIT_MODIFIES_COMPONENT": ({"commit"}, {"technical_component"}, False),
    "PULL_REQUEST_REVIEWED_BY": ({"pull_request"}, {"person"}, False),
    "PULL_REQUEST_AUTHORED_BY": ({"pull_request"}, {"person"}, False),

    # Person relationships
    "PERSON_AUTHORED": ({"person"}, {"document", "pull_request", "commit", "decision"}, False),
    "PERSON_REVIEWED": ({"person"}, {"pull_request", "document", "decision"}, False),
    "PERSON_ASSIGNED_TO": ({"person"}, {"work_item"}, False),
    "PERSON_RESPONSIBLE_FOR": ({"person"}, {"technical_component", "project", "work_item"}, False),
    "PERSON_DISCUSSIONS_PARTICIPANT": ({"person"}, {"discussion"}, False),
    "PERSON_CONTRIBUTED_TO": ({"person"}, {"repository", "technical_component"}, False),

    # Technical relationships
    "COMPONENT_DEPENDS_ON": ({"technical_component"}, {"technical_component", "dependency"}, False),
    "COMPONENT_CALLS_COMPONENT": ({"technical_component"}, {"technical_component"}, False),
    "COMPONENT_USES_SERVICE": ({"technical_component"}, {"technical_component"}, False),
    "COMPONENT_STORES_DATA_IN": ({"technical_component"}, {"technical_component"}, False),
    "COMPONENT_EXPOSES_API": ({"technical_component"}, {"technical_component"}, False),
    "DOCUMENT_DESCRIBES_COMPONENT": ({"document"}, {"technical_component"}, False),
    "DOCUMENT_DESCRIBES_DECISION": ({"document"}, {"decision"}, False),

    # Risk and bug relationships
    "RISK_AFFECTS_COMPONENT": ({"risk"}, {"technical_component"}, False),
    "BUG_FOUND_IN_COMPONENT": ({"bug"}, {"technical_component"}, False),
    "RISK_BLOCKS_WORK_ITEM": ({"risk"}, {"work_item"}, False),
    "BUG_RELATED_TO_WORK_ITEM": ({"bug"}, {"work_item"}, True),
    "RISK_DEPENDS_ON_EXTERNAL_FACTOR": ({"risk"}, {"dependency"}, False),

    # Evidence relationships
    "KNOWLEDGE_SUPPORTED_BY_EVIDENCE": ({"decision", "work_item", "risk", "bug", "technical_component"}, {"document", "pull_request", "commit", "discussion"}, False),
    "KNOWLEDGE_CORROBORATED_BY": ({"decision", "work_item", "technical_component"}, {"document", "pull_request", "commit"}, False),
}
```

---

## 4. Multi-Tier Relationship Discovery Pipeline

```
Evidence & Knowledge Sources (GitHub, Jira, Docs, Knowledge Items)
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Method 1: Exact Reference Matching                          │
│ Regex Jira keys (PROJ-123), PR #s (#42), Commit SHAs        │ ──▶ Basis: explicit
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Method 2: Structured Connector Relationships                │
│ Jira issuelinks, GitHub PR base/head, commit associations   │ ──▶ Basis: explicit
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Method 3: Deterministic Contextual Matching                 │
│ Component path overlap (PR changed files vs ADR paths)      │ ──▶ Basis: inferred
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Method 4: Semantic Embedding Matching                       │
│ ChromaDB vector similarity between Decisions and Work Items │ ──▶ Basis: inferred
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Method 5: Bounded Qwen3 8B Relationship Classification       │
│ Evidence-grounded JSON reasoning with verbatim citations    │ ──▶ Basis: inferred
└─────────────────────────────────────────────────────────────┘
```

### Safety Rules:
1. **Never Invent Relationships**: If a candidate link does not cite valid `evidence_id` and `evidence_chunk_id`, it is rejected.
2. **Never Auto-Confirm**: Inferred links remain `candidate` with dashed lines in the graph visualization until reviewed by a designated human.
3. **No Unbounded Extraction**: Candidate pairs for Qwen3 8B are strictly bounded (top 25 pairs per run) and executed under `_OLLAMA_INFERENCE_LOCK`.

---

## 5. Decision-to-Implementation Traceability

The Traceability Engine walks the 5-stage chain:
$$\text{Discussion} \longrightarrow \text{Decision} \longrightarrow \text{Work Item} \longrightarrow \text{Pull Request} \longrightarrow \text{Commit} \longrightarrow \text{Technical Component}$$

### Traceability States:
- `complete`: Continuous uninterrupted path from Decision to Component through Work Item, PR, and Commit.
- `partially_traced`: Partial chain (e.g. Decision has Work Item and PR, but no linked Commits or Component).
- `untraced`: Decision exists in documentation, but zero linked implementation records exist in Jira or GitHub.
- `conflicting`: Opposing evidence or rejected/disputed links present along the chain.

---

## 6. Graph Projection & Traversal (React Flow Ready)

The graph projection API returns nodes and edges structured for consumption by future React Flow interfaces:

### Node Payload:
```json
{
  "id": "urn:entity:uuid",
  "type": "customNode",
  "label": "ADR-004: PostgreSQL Storage",
  "description": "Decision to use PostgreSQL as canonical store",
  "entity_type": "decision",
  "status": "accepted",
  "source_provider": "manual_upload",
  "verification_status": "verified",
  "metadata": {
    "decision_status": "accepted",
    "decision_date": "2026-10-15"
  }
}
```

### Edge Payload:
```json
{
  "id": "urn:rel:uuid",
  "source": "urn:entity:source_uuid",
  "target": "urn:entity:target_uuid",
  "relationship_type": "DECISION_IMPLEMENTED_BY",
  "label": "implemented by",
  "relationship_basis": "explicit",
  "verification_status": "verified",
  "confidence": 0.95,
  "evidence_count": 2,
  "source_provider": "github",
  "supporting_evidence_available": true
}
```

### Traversal Bounds:
- `max_depth`: Default 3, Maximum 8.
- `max_nodes`: Default 100, Maximum 300.
- `detected_cycles`: Explicitly reported via Tarjan's / DFS back-edge detection.

---

## 7. Security Architecture & Read-Time Source ACL Filtering

1. **Authentication & Project RBAC**:
   - `require_project_permission("project.read")` on all query endpoints.
   - `require_project_permission("project.knowledge.review")` on review endpoints.
2. **Read-Time Evidence Permitted Set Resolution**:
   - Query `SourceAccessPolicyService` for caller's permitted source IDs in the target project.
   - Any graph edge supported *solely* by evidence outside this permitted set is omitted from the response.
   - Any graph node originating *solely* from inaccessible evidence is omitted from the response.
   - Direct lookup on a restricted entity or relationship raises HTTP 403 `SOURCE_ACCESS_DENIED` and logs an audit event.

---

## 8. REST API Suite

All endpoints under `/api/v1/projects/{project_id}/relationships/`:
1. `GET /graph` — Bounded, filtered graph projection for React Flow.
2. `GET /entities` — Filterable entity search with pagination.
3. `GET /entities/{entity_id}` — Detailed node view with incoming/outgoing edges.
4. `GET /` — Flat relationship listing with filters.
5. `GET /{relationship_id}` — Edge detail with confidence components and review history.
6. `GET /{relationship_id}/evidence` — Accessible supporting excerpts and chunk citations.
7. `GET /traceability` — List of project decision traceability chains.
8. `GET /traceability/{entity_id}` — Deep traceability inspection for a specific decision or work item.
9. `GET /dependencies` — Dependency items and blockers.
10. `GET /dependencies/graph` — Dependency tree and cycle detection.
11. `GET /timeline` — Entity-linked chronological timeline stream.
12. `POST /{relationship_id}/submit-for-review` — Submit candidate relationship to Verification Center.
13. `POST /reconstruct` — Dispatch asynchronous graph discovery run to worker.

---

## 9. Phased Implementation Roadmap

- **Phase 1: Database Foundation & Models**:
  - Alembic migration `0011_relationship_explorer.py`
  - SQLAlchemy models in `app/models/relationship.py`
- **Phase 2: Repositories & ACL Filtering**:
  - `EntityRepository`, `RelationshipRepository`, `TimelineEventRepository`
- **Phase 3: Relationship Discovery Engine**:
  - Regex extractors for Jira/GitHub, structured connector linkers, component path matchers
- **Phase 4: Traversal, Traceability & Dependencies**:
  - `GraphTraversalService`, `TraceabilityService`, `DependencyIntelligenceService`
- **Phase 5: REST API & Schemas**:
  - Pydantic schemas in `app/schemas/relationship.py`
  - Route handlers in `app/api/routes/relationships.py`
- **Phase 6: Worker Job & Review Integration**:
  - Worker task in `CompositeWorkerService`
- **Phase 7: Testing & Verification**:
  - Automated unit and integration tests (exact linking, cycle detection, ACL filtering, live Qwen test)
- **Phase 8: Documentation**:
  - Architecture and API specifications
