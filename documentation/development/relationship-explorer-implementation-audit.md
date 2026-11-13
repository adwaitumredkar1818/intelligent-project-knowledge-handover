# Relationship Explorer Module — Implementation Audit & Gap Analysis

**Product**: The Handover (Intelligent Project Knowledge Reconstruction & Handover Platform)  
**Module**: Relationship Explorer (Module 4)  
**Audit Date**: 2026-11-13  
**Auditor**: Antigravity Assistant  
**Repository State**: Clean working tree on `feature/project-evidence-workspace-and-prototype`, Alembic head `0010_knowledge_domains`

---

## 1. Executive Summary

The **Relationship Explorer** is Module 4 of The Handover platform. Its mission is to reconstruct meaningful, evidence-backed relationships between fragmented project knowledge artefacts across project documents, meeting notes, GitHub repositories, Jira issues, decisions, technical components, and people:
> **"Every relationship must have a traceable basis. The AI must never invent a relationship and present it as established project knowledge."**

This audit systematically evaluates the existing codebase against the 25 capabilities specified in the directive. It establishes what exists, what can be reused, and what must be built to deliver a complete, production-grade, PostgreSQL-backed Relationship Explorer backend.

---

## 2. Capability-by-Capability Audit Matrix

| # | Capability | Existing Models / Services / APIs | Status | Missing Functionality | Required Changes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Knowledge Intelligence** | `KnowledgeItem`, `KnowledgeEvidenceLink`, `KnowledgeExtractionRun`, `KnowledgeIntelligenceService` | **Complete and verified** | None for core extraction | Connect Knowledge Items as graph nodes |
| **2** | **Eight Knowledge Domains** | `KnowledgeDomain` enum, `CANONICAL_DOMAINS`, `build_category_extraction_prompt`, `KnowledgeCandidateValidator` | **Complete and verified** | None | Use domain items as graph node anchors |
| **3** | **Knowledge Items** | `knowledge_items` table in `app/models/knowledge.py` | **Complete and verified** | None | Link entities to `primary_knowledge_item_id` |
| **4** | **Knowledge Evidence Links** | `knowledge_evidence_links` table in `app/models/knowledge.py` | **Complete and verified** | None | Reuse for knowledge item provenance |
| **5** | **Knowledge Extraction Runs** | `knowledge_extraction_runs` table in `app/models/knowledge.py` | **Complete and verified** | None | Parallel run tracking for graph reconstruction |
| **6** | **Entity Resolution** | None in database | **Missing** | No entity table, no resolution candidates, no signal scoring | Create `knowledge_entities`, `identity_resolution_candidates`, and `IdentityResolutionService` |
| **7** | **Entity Aliases** | None in database | **Missing** | No alias table for multi-source handles (`@alexchen`, Jira ID) | Create `entity_aliases` table and alias normalization service |
| **8** | **Relationship Models** | Sketched in `database-design.md`, but no migration exists | **Missing** | No `knowledge_relationships` table in PostgreSQL | Create `knowledge_relationships` table with strict type registry |
| **9** | **Relationship Evidence** | None in database | **Missing** | No provenance linking table for graph edges | Create `relationship_evidence_links` table guaranteeing zero unattributed edges |
| **10** | **Timeline Events** | `ProjectTimelineService` (`app/services/timeline.py`) | **Implemented but incomplete** | Dynamically synthesizes events; no persistent entity-linked event log | Create `knowledge_timeline_events` table and connect graph entities |
| **11** | **Dependency Models** | `KnowledgeItem` (`category="dependencies"`) | **Implemented but incomplete** | No typed dependency edges, no traversal engine, no cycle detection | Build `DependencyIntelligenceService` with DFS cycle detection and transitive walks |
| **12** | **GitHub Connectors** | `GitHubSyncService`, `GitHubClient`, `SourceConnection` | **Complete and verified** | PR-to-issue, commit-to-PR links exist in `metadata_json` but not in graph | Extract graph entities and edges from GitHub metadata |
| **13** | **Jira Connectors** | `JiraSyncService`, `JiraClient`, `SourceConnection` | **Complete and verified** | Issue links, components, worklogs exist in `metadata_json` but not in graph | Extract graph entities and edges from Jira metadata |
| **14** | **Slack Connectors** | None | **Missing** | No Slack integration tables or services | Enforce strict rule: Slack entities must exist only where genuinely authorised |
| **15** | **Evidence Workspace** | `EvidenceItem`, `EvidenceContent`, `EvidenceChunk` | **Complete and verified** | None | Link document nodes to `EvidenceItem` records |
| **16** | **Evidence Chunking** | `EvidenceChunkingService` (`app/services/chunking.py`) | **Complete and verified** | None | Reuse chunks for relationship evidence citation |
| **17** | **Nomic Embeddings** | `OllamaEmbeddingService` (`app/services/embedding.py`) | **Complete and verified** | None | Optional semantic candidate pairing |
| **18** | **ChromaDB Collections** | `ChromaV2HttpVectorStore` (`app/services/vector_store.py`) | **Complete and verified** | None | Reuse for semantic similarity queries |
| **19** | **Hybrid Retrieval** | `HybridRetrievalService` (`app/services/retrieval.py`) | **Complete and verified** | None | Reuse for evidence discovery |
| **20** | **Qwen3 Ollama Client** | `OllamaLLMClient` (`app/services/llm.py`) | **Complete and verified** | No relationship classification prompt | Build `RelationshipPromptBuilder` and JSON output validator |
| **21** | **Ollama Scheduler** | `_OLLAMA_INFERENCE_LOCK` (`OLLAMA_MAX_CONCURRENT_AI_JOBS=1`) | **Complete and verified** | None | Use lock during Qwen relationship suggestions |
| **22** | **PostgreSQL Workers** | `CompositeWorkerService` (`app/worker.py`), `BackgroundJobRepository` | **Implemented but incomplete** | No `relationship_reconstruction` job type | Add `RELATIONSHIP_RECONSTRUCTION` to `BackgroundJobType` |
| **23** | **Review & Audit Services**| `AuditService` (`app/services/audit.py`), `audit_logs` | **Complete and verified** | No review transition handlers for relationships | Connect review actions to `AuditService` |
| **24** | **RBAC & Source ACLs** | `RbacService`, `SourceAccessPolicyService` | **Complete and verified** | Graph-specific read-time filtering missing | Implement `GraphPermissionFilterService` enforcing fail-closed source ACLs |
| **25** | **Existing APIs & Tests** | `app/api/routes/`, test suite (113 passed) | **Complete and verified** | No `/relationships/...` API endpoints | Create `app/api/routes/relationships.py` exposing all 11 required endpoints |

---

## 3. Detailed Gaps & Architectural Assessment

### 3.1 Graph Persistence & Relational Schema (Missing)
- **Current State**: Alembic head is `0010_knowledge_domains`. The database contains unstructured JSON payloads inside `knowledge_items` and `evidence_items.metadata_json`, but has no relational graph tables.
- **Required New Tables (Alembic `0011_relationship_explorer`)**:
  1. `knowledge_entities` — Canonical internal UUID nodes across 13 entity types (`person`, `discussion`, `decision`, `work_item`, `pull_request`, `commit`, `document`, `technical_component`, `dependency`, `risk`, `bug`, `repository`, `organisation`).
  2. `entity_aliases` — Multi-source identity bindings (`@alexchen`, `Alex Chen`, `alex@nexora.com`, Jira account ID).
  3. `identity_resolution_candidates` — Reversible merge candidates with weighted matching scores.
  4. `knowledge_relationships` — Directed, typed graph edges with classification (`explicit`, `inferred`, `human_confirmed`) and verification status (`candidate`, `verified`, `rejected`, `conflicted`, `unresolved`, `stale`).
  5. `relationship_evidence_links` — Mandatory provenance linking edges to `EvidenceItem` and `EvidenceChunk` with support classification.
  6. `decision_traceability_chains` — Traceability ledger connecting `Decision -> Work Item -> Pull Request -> Commit -> Component`.
  7. `knowledge_timeline_events` — Persistent project timeline event log with source timestamp precision.
  8. `relationship_reconstruction_runs` — Async run lifecycle and telemetry.

### 3.2 Discovery & Matching Pipeline (Missing)
- **Current State**: Relationships exist only implicitly inside GitHub PR bodies (`Closes #12`), commit messages, Jira issue links, and Knowledge Items.
- **Required Discovery Engine (`RelationshipDiscoveryService`)**:
  - **Method 1 (Exact Reference Matching)**: Regex parsers for Jira keys (`PROJ-123`), PR numbers (`#42`), commit SHAs, repo URLs.
  - **Method 2 (Structured Source Links)**: Jira `issuelinks` (`blocks`, `depends on`), GitHub PR `head_ref`/`base_ref`, commit author metadata.
  - **Method 3 (Contextual Matching)**: Component path overlap between PR changed files and architecture ADRs.
  - **Method 4 (Semantic Matching)**: ChromaDB embedding similarity for candidate generation (marked `inferred`, `candidate`).
  - **Method 5 (Qwen3-Assisted Suggestions)**: Bounded Ollama LLM prompt for relationship classification citing explicit evidence chunks.

### 3.3 Graph Traversal & Analysis Engine (Missing)
- **Current State**: No graph traversal exists.
- **Required Analysis Services**:
  - `GraphTraversalService`: Bounded BFS/DFS traversal with `max_depth` (default 5, max 10), `max_nodes` (default 100, max 300), cycle detection, and projection to React Flow format.
  - `DependencyIntelligenceService`: Direct and transitive dependency trees, circular dependency detection, root blocker identification.
  - `TraceabilityService`: Full 5-stage decision-to-implementation chain walk with completeness states (`complete`, `partially_traced`, `untraced`, `conflicting`).

### 3.4 Security & Source ACL Enforcement (Critical Security Gap)
- **Governance Mandate**: `Project Membership != Source Access`.
- **Requirement**: Graph nodes, edges, timeline events, and traceability chains must be filtered at read-time against `SourceAccessPolicyService`. If an edge is supported exclusively by restricted evidence that the calling user cannot access, that edge (and any isolated confidential node) must be completely omitted from the graph response without leaking node titles, labels, or edge counts. Direct lookup must fail closed with HTTP 403 `SOURCE_ACCESS_DENIED`.

---

## 4. Audit Conclusion & Next Steps

The existing repository provides a rock-solid foundation:
- Robust multi-tenant PostgreSQL architecture and Alembic migration framework.
- Rich evidence metadata captured by GitHub and Jira sync services.
- Verified local Qwen3 8B and nomic-embed-text Ollama runtime.
- Mature fail-closed source ACL service.

**Next Immediate Step**: Author `documentation/development/relationship-explorer-implementation-plan.md` defining the complete technical specification, schemas, algorithms, and API contracts before writing code.
