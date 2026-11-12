# Phase 2.7 — Cross-Source Knowledge Intelligence: Detailed Implementation Plan

> **Classification Key:** **Confirmed Architectural Baseline** reflects repository constraints from [`AGENTS.md`](../../AGENTS.md) and Phases 2.1–2.6. **Proposed Phase 2.7 Design** specifies the concrete relational schema, deterministic + LLM-assisted pipelines, identity/relationship rules, API contracts, and test plan awaiting user review before implementation begins.

> **Directive Completeness Notice:** The Phase 2.7 prompt truncated at `# 10. RELATIONSHIP CONFIDENCE AND PROVENANCE` (`- Name`). Sections 1–9 and the beginning of Section 10 are grounded directly in the prompt; completion of Section 10 (`confidence_components`), RBAC/security guarantees, background execution, API surface, evaluation thresholds, and rollback details follows the existing Phase 2.1–2.6 architecture and is flagged for explicit confirmation before code edits begin.

---

## 1. Existing Architecture Findings (Verified Against Repository)

Inspection of Phases 2.1–2.6 confirms the following authoritative baseline conventions that Phase 2.7 must preserve without rewriting:

1. **PostgreSQL Canonical Store & Portability (`backend/app/db/session.py`, `backend/app/models/`)**:
   - SQLAlchemy 2.x synchronous ORM (`psycopg` v3 driver) + Alembic migrations in `infrastructure/database/migrations/versions/` (currently at `0007_knowledge_reconstruction`).
   - All primary keys use `Uuid(as_uuid=True)` (`default=uuid.uuid4`). Never use external IDs as primary keys.
   - JSON columns use `_JSON_VARIANT = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")` so fast isolated SQLite in-memory tests and live PostgreSQL 16 tests execute identical ORM code.
   - Partial indexes declare both `sqlite_where=text(...)` and `postgresql_where=text(...)`.
   - Alembic constraints follow SQLAlchemy naming conventions (`ck_<table>_<name>`, `fk_<table>_<col>_<ref>`, `pk_<table>`, `uq_...`).
2. **Existing Rich Cross-Source Signals Already Captured (`Phase 2.4B` & `Phase 2.6`)**:
   - **GitHub Evidence (`app/services/integrations/github_sync.py`)**: Stores structured `metadata_json` per synced record: `repository`, `number`, `state`, `merged`, `merged_at`, `base_ref`, `head_ref`, `labels`, `assignees`, `milestone`, `changed_files`, `referenced_issue_numbers`, commit `sha`, doc `path`, and `source_author_identity` / `source_created_at` / `source_updated_at`. Chunking also tags `pr_body`, `pr_review`, `pr_comment`, `pr_changed_files`, `commit_message`, `issue_body`, `issue_comment`.
   - **Jira Evidence (`app/services/integrations/jira_sync.py`)**: Stores `cloud_id`, `project_key`, `jira_issue_key`, `issue_type`, `status`, `priority`, `resolution`, `assignee`, `reporter`, `labels`, `components`, `issue_links` (`parent`, `relates to`, `blocks`, etc.), `security_level`, comments, worklogs, and changelog status/assignee history (`source_created_at`, `source_updated_at`).
   - **Phase 2.6 Knowledge (`knowledge_items`, `knowledge_evidence_links`)**: Extracts `decisions_rationale`, `work_items`, `responsibilities_ownership`, `technical_architecture`, `bugs_blockers_risks`, and `dependencies` with verified `evidence_id` + `evidence_chunk_id` (`ON DELETE SET NULL`), `supporting_excerpt`, `fingerprint`, unmerged `person_or_owner_label`, `source_observed_at`, `is_stale`, `epistemic_status`, and `is_synthetic`.
3. **Authentication, RBAC & Fail-Closed Source ACLs (`app/core/rbac_catalog.py`, `app/services/integrations/access_policy.py`)**:
   - Currently seeded catalog: **8 roles**, **23 permissions**, **49 role-permission mappings** (validated by `tests/test_live_postgres.py`). Existing project permissions already cover `project.read`, `project.manage`, `project.evidence.contribute`, and `project.knowledge.review`.
   - Read routes use `require_project_permission("project.read")` (`ProjectContext`); state-changing extraction/ingestion triggers use `resolve_project_context` + explicit project membership + `project.evidence.contribute` (or `project.manage`).
   - `SourceAccessPolicyService` + SQL clauses enforce fail-closed source permissions (`project_members` vs `source_restricted` + revoked policies + legacy restricted uploads) before any retrieval, LLM prompt assembly, or API response, and emit `audit_logs` on denials (`403 SOURCE_ACCESS_DENIED`).
4. **Lightweight Worker & LLM Execution (`app/worker.py`, `app/services/llm.py`, `app/repositories/job.py`)**:
   - Single `CompositeWorkerService` polls PostgreSQL `background_jobs` (`SELECT ... FOR UPDATE SKIP LOCKED`, lease recovery, exponential retries) sequentially across `document_ingestion`, `source_sync`, `evidence_indexing`/`reindexing`/`cleanup`, and `knowledge_reconstruction`.
   - `StructuredLLMClient` (`OllamaLLMClient` -> `qwen3:8b`, `think=false`, `format="json"`, shared `_OLLAMA_INFERENCE_LOCK`) handles optional bounded LLM JSON inference cleanly behind a mockable protocol. Observed local GPU latency (~47–69 s/call on 6 GB VRAM) reinforces keeping relationship inference strictly optional/bounded in background jobs and relying primarily on deterministic cross-source linking.
5. **Existing Roadmap Placeholder (`documentation/architecture/database-design.md`)**:
   - Section 2.2E previously outlined a minimal placeholder `knowledge_relationships` table (`source_node_type`, `target_node_type`, `evidence_id`) that has **not** yet been migrated (`0007` is current head). Phase 2.7 replaces that sketch with the complete, normalised entity, alias, relationship, provenance, traceability, timeline, and dependency schema below.

---

## 2. Architecture & Design Boundaries

1. **PostgreSQL Remains Canonical**: Zero Neo4j, Memgraph, Redis, or Celery additions. Graph traversal (multi-hop dependency paths, cycle detection, traceability chains) runs deterministically over indexed PostgreSQL relational adjacency tables with explicit depth/node/timeout bounds in Python services.
2. **Preserve Phase 2.6 Intact**: Do not alter existing Phase 2.6 extraction schemas, validators, or endpoints (`knowledge_items` stays canonical for extracted category payloads). Phase 2.7 consumes `evidence_items`, `evidence_contents`, `evidence_chunks`, `knowledge_items`, and `knowledge_evidence_links` via existing repositories/ACL services without creating a duplicate knowledge store.
3. **Deterministic First, Optional Bounded LLM Second**:
   - Deterministic algorithms handle structural extraction (GitHub PR `Closes #N` / `NEX-123` refs, commits linked to PRs/issues, Jira `issuelinks` / `parent` / changelog transitions, Phase 2.6 `DependencyCandidate` / `ResponsibilityCandidate` / `DecisionCandidate.affected_components`), exact ID matching, normalised text matching, graph cycle detection, and timeline reconstruction.
   - Optional `StructuredLLMClient` assistance operates **only** on explicitly scoped, ACL-compatible ambiguous candidate pairs (`is_llm_assisted = true`), always emits `classification = "inferred"` (never `human_confirmed`), must pass `RelationshipCandidateValidator` citing valid `evidence_id` / `chunk_id` + excerpt provenance, and degrades gracefully to deterministic-only mode when LLM inference is disabled or skipped.
4. **Hard AI Prohibitions**: LLMs never authorise access, bypass ACLs, auto-merge identities, auto-confirm relationships, invent timestamps, mark work items completed without evidence, or silently drop cycles/conflicts.

---

## 3. Proposed Database Changes (Alembic Revision `0008_cross_source_intelligence`)

Create one clean additive migration `infrastructure/database/migrations/versions/20261112_0008_cross_source_intelligence.py` (`down_revision = "0007_knowledge_reconstruction"`):

### 3.1 Extend Existing `background_jobs` Check Constraint
- Update `BackgroundJobType` enum and `background_jobs` `ck_background_jobs_background_job_type` constraint cleanly (`drop_constraint` + `create_check_constraint`, reversed cleanly in `downgrade()`) to allow `'knowledge_intelligence'`.

### 3.2 New Relational Tables

| Table | Purpose | Key Constraints & Indexes |
| :--- | :--- | :--- |
| `intelligence_runs` | Tracks async Phase 2.7 reconstruction runs (status, scope, deterministic vs LLM metrics, token usage, warnings, `background_job_id`). | CHECK counters `>= 0`, `status IN ('queued','running','completed','partially_completed','failed','cancelled')`; indexes `(project_id, created_at)`, `(project_id, status)`. |
| `knowledge_entities` | Canonical project-scoped internal UUID entities across all 13+ required entity types (`person`, `project`, `organisation`, `work_item`, `decision`, `technical_component`, `repository`, `pull_request`, `commit`, `document`, `risk`, `dependency`, `bug`). | Optional FKs `primary_knowledge_item_id -> knowledge_items(id) SET NULL` and `primary_evidence_id -> evidence_items(id) SET NULL` (no duplicate payload copy). `is_synthetic` isolation, `is_deleted`, `is_stale`, `confidence_score` `0..1`, `resolution_status` (`unresolved` \| `canonical` \| `merged` \| `disputed`), `merged_into_entity_id -> knowledge_entities(id) SET NULL` (non-destructive merge history). Unique active key `(project_id, entity_type, normalized_name, is_synthetic)` where `is_deleted = false AND merged_into_entity_id IS NULL`. |
| `entity_aliases` | Source-specific identifiers and name variants bound to `knowledge_entities` without destructive merging. | FK `entity_id -> knowledge_entities(id) CASCADE`, optional `evidence_id -> evidence_items(id) SET NULL`, optional `knowledge_item_id -> knowledge_items(id) SET NULL`, `reviewed_by_user_id -> users(id) SET NULL`, `reviewed_at`, `review_note`. Fields: `alias_value`, `normalized_alias`, `alias_kind`, `source_type`, `source_provider`, `source_external_id`, `source_account_id`, `confidence_score` (`0..1`), `resolution_status` (`unresolved` \| `candidate` \| `accepted` \| `rejected`), `is_synthetic`. Index `(project_id, normalized_alias)`, `(entity_id, resolution_status)`. |
| `identity_resolution_candidates` | Audit-ready candidate merge pairs produced by the Identity Resolution Engine with weighted signal breakdown & reversal support. | `left_entity_id`, `right_entity_id` (`CHECK left != right`), weighted `match_score` (`0..1`), `signal_breakdown_json` (JSONB: `exact_external_id`, `exact_normalised_name`, `matching_source_identity`, `contextual_evidence_overlap`, `semantic_similarity`), `policy_band` (`strong_candidate` \| `manual_review` \| `separate`), `decision_status` (`pending` \| `accepted` \| `rejected` \| `reverted`), `decided_by_user_id`, `decided_at`, `decision_rationale`, `previous_left_state_json`, `is_synthetic`. Unique `(project_id, left_entity_id, right_entity_id, is_synthetic)`. |
| `knowledge_relationships` | Canonical typed, directed project knowledge graph edges stored in PostgreSQL. | `source_entity_id`, `target_entity_id` (`FK -> knowledge_entities(id) CASCADE`), `relationship_type` (controlled 16+ enum), `dependency_type` (nullable, set for dependency edges), `dependency_status` (`active` \| `resolved` \| `blocked` \| `uncertain` \| `stale` NULL), `classification` (`explicit` \| `inferred` \| `human_confirmed`), `confidence_score` (`0..1`), `confidence_components_json`, `is_bidirectional_display` (BOOLEAN), `is_llm_assisted` (BOOLEAN), `is_stale` (BOOLEAN), `stale_reason`, `review_status` (`pending_review` \| `confirmed` \| `rejected` \| `disputed`), `reviewed_by_user_id`, `reviewed_at`, `review_note`, `fingerprint` (SHA-256 dedup key), `is_synthetic`, `first_observed_at`, `last_observed_at`. Indexes: `(project_id, source_entity_id, relationship_type)`, `(project_id, target_entity_id, relationship_type)`, `(project_id, is_deleted, is_synthetic, classification)`. |
| `relationship_evidence_links` | Mandatory verifiable provenance linking every persisted relationship back to supporting evidence/knowledge records. | FK `relationship_id -> knowledge_relationships(id) CASCADE`, `evidence_id -> evidence_items(id) CASCADE`, nullable `evidence_chunk_id -> evidence_chunks(id) SET NULL`, nullable `knowledge_item_id -> knowledge_items(id) SET NULL`, `support_classification` (`explicit` \| `inferred` \| `corroborated`), `supporting_excerpt`, `source_location_json`, `signal_type`, `source_metadata_json`. Guarantees no relationship exists without traceable evidence. |
| `decision_traceability_chains` | Persistent summary index connecting `Decision -> Work item -> PR -> Commit -> Technical component` with completeness status & uncertainty notes. | `decision_entity_id -> knowledge_entities(id) CASCADE`, `completeness_status` (`complete` \| `partially_traced` \| `untraced` \| `conflicting`), `work_item_ids_json`, `pull_request_ids_json`, `commit_ids_json`, `component_ids_json`, `relationship_ids_json`, `missing_links_json`, `uncertainty_reasons_json`, `aggregate_confidence` (`0..1`), `classification` (`explicit` \| `inferred` \| `human_confirmed`), `earliest_event_at`, `latest_event_at`, `is_synthetic`. Unique `(project_id, decision_entity_id)`. |
| `knowledge_timeline_events` | Chronological project event log derived strictly from source timestamps & extracted provenance. | `entity_id -> knowledge_entities(id) CASCADE NULL`, `secondary_entity_id -> knowledge_entities(id) SET NULL`, `relationship_id -> knowledge_relationships(id) SET NULL`, `evidence_id -> evidence_items(id) CASCADE`, `knowledge_item_id -> knowledge_items(id) SET NULL`, `event_type` (controlled enum: `decision_proposed`, `decision_approved`, `work_item_created`, `work_assigned`, `work_started`, `pr_opened`, `review_submitted`, `commit_created`, `pr_merged`, `issue_updated`, `issue_completed`, `blocker_identified`, `risk_identified`, `documentation_updated`), `title`, `summary`, `occurred_at`, `recorded_at`, `source_timestamp`, `source_timezone`, `timestamp_precision` (`exact_datetime` \| `date_only` \| `month_only` \| `unknown`), `timestamp_origin` (`source_api` \| `source_changelog` \| `source_commit` \| `document_header` \| `text_date_mention` \| `unknown`), `actor_entity_id -> knowledge_entities(id) SET NULL`, `event_fingerprint`, `is_synthetic`. Indexes: `(project_id, occurred_at)`, `(project_id, entity_id, occurred_at)`, `(project_id, event_type)`. |

---

## 4. Entity Model & Alias Governance

### 4.1 Entity Types (`EntityType` Enum)
`person`, `project`, `organisation`, `work_item`, `decision`, `technical_component`, `repository`, `pull_request`, `commit`, `document`, `risk`, `dependency`, `bug`.

### 4.2 Typed Entity Metadata (`EntityMetadata` Pydantic Schema)
Rather than unrestricted dicts, `metadata_json` is validated via discriminated/typed Pydantic models before persistence:
- Common fields: `source_providers: list[str]`, `external_keys: list[str]`, `tags: list[str]`.
- Type-specific structured attributes (e.g., `repository`: `owner_repo`, `default_branch`; `pull_request`: `number`, `head_ref`, `base_ref`, `merged`; `commit`: `sha`, `repository`; `work_item`/`bug`: `issue_key`, `issue_type`, `priority`; `technical_component`: `paths_or_modules`, `layer`; `person`: `provider_accounts` list of `{provider, account_id, username}`).

### 4.3 Non-Destructive Entity Discovery & Alias Rules
- Discovery inspects:
  1. Existing `Project` and `Organisation` workspaces (for `project` and `organisation` anchor entities).
  2. Accessible `EvidenceItem` records (`github` repo/issue/PR/commit/doc, `jira` issue, uploaded `pdf`/`docx` documents) -> instantiates deterministic `repository`, `pull_request`, `commit`, `work_item`/`bug`, `document`, `person` (author/assignee/reporter/reviewer), and Jira `component` -> `technical_component` entities with `source_external_id` recorded on `EntityAlias`.
  3. Accessible `KnowledgeItem` records (`decisions_rationale` -> `decision`, `work_items` -> `work_item`, `bugs_blockers_risks` -> `bug`/`risk`, `technical_architecture` -> `technical_component`, `dependencies` -> `dependency` + component anchors, `responsibilities_ownership` -> `person` + `technical_component` / workstream) -> attaches `primary_knowledge_item_id` without copying full `structured_payload`.
- Aliases record `source_type`, `source_external_id`, `confidence_score`, `evidence_id`, and `resolution_status` (`unresolved` | `candidate` | `accepted` | `rejected`). Similar names like `@achen`, `Alex Chen`, and `Alex` are created/kept as separate entities or `candidate` aliases until identity resolution policy permits linking or human approval occurs.

---

## 5. Identity Resolution Engine

### 5.1 Weighted Deterministic + Optional Semantic Pipeline (`IdentityResolutionService`)
Configurable via `Settings.intelligence` (`INTELLIGENCE_WEIGHT_*` & `INTELLIGENCE_THRESHOLD_*`):

| Signal | Default Weight | Computation Rule |
| :--- | ---: | :--- |
| `exact_external_id` | `0.40` | Exact `(provider, external_workspace_or_site_id, account_id_or_resource_id)` match inside the same identity provider/namespace. Cross-provider matching strings do **not** score `exact_external_id`. |
| `exact_normalised_name` | `0.25` | Normalized Unicode NFKC lowercase punctuation-stripped string equality (e.g., `Auth Service` == `auth-service`). |
| `matching_source_identity` | `0.15` | Explicit email/handle correlation within verified connector profiles (e.g., `user_source_authorisations` or commit email + GitHub handle recorded in the same commit record), **never** inferred across tenants. |
| `contextual_evidence_overlap` | `0.10` | Jaccard/overlap ratio over co-referenced artefacts (ticket keys, repos, component paths) in accessible evidence. |
| `semantic_similarity` | `0.10` | Optional embedding cosine similarity (`nomic-embed-text` when available, else normalized token trigram similarity) restricted to non-person entities or tie-breaking ambiguous aliases. |

### 5.2 Resolution Policy & Hard Safety Guardrails
- **Thresholds**: `>= 0.95` -> `strong_candidate`; `0.75–0.949` -> `manual_review`; `< 0.75` -> `separate`.
- **Person Entity Safety Override**: For `entity_type == "person"`, a display-name or semantic score **never** merges or accepts an alias automatically—even if total score `>= 0.95`. Automatic person linking occurs **only** when a strong stable same-provider account ID or explicitly verified platform/source link (`user_source_authorisations` / reviewer-approved mapping) exists; otherwise `@achen` vs `Alex Chen` stays `manual_review` (`candidate`) for human review!
- **Non-Destructive & Reversible**: Merging sets `merged_into_entity_id` on the secondary entity, repoints active query views via canonical resolution while keeping original `EntityAlias` + `IdentityResolutionCandidate` rows + `previous_left_state_json`, logs an audit entry, and supports `POST .../identities/{candidate_id}/revert` (by `project.knowledge.review` / `project.manage`) to undo a merge cleanly.
- **No Permission Escalation**: Identity resolution **never** alters `SourceAccessPolicy.allowed_user_ids`, `ProjectMembership`, or `OrganisationMembership`.

---

## 6. Cross-Source Relationship & Dependency Intelligence

### 6.1 Controlled Relationship Registry (`RelationshipType` Enum & Validator Matrix)
Implement exact metadata registry defining `(allowed_source_types, allowed_target_types, bidirectional_display, requires_explicit_evidence, allows_inference)` for all 16 required types:
- `DECISION_IMPLEMENTED_BY`, `WORK_ITEM_TRACKED_BY`, `WORK_ITEM_IMPLEMENTED_BY`, `COMMIT_BELONGS_TO_PR`, `PR_REFERENCES_ISSUE`, `PERSON_RESPONSIBLE_FOR`, `PERSON_AUTHORED`, `PERSON_REVIEWED`, `COMPONENT_DEPENDS_ON`, `WORK_ITEM_DEPENDS_ON`, `DECISION_AFFECTS`, `RISK_AFFECTS`, `BUG_FOUND_IN`, `DOCUMENT_DESCRIBES`, `WORK_ITEM_BLOCKED_BY`, `KNOWLEDGE_CORROBORATED_BY`.
- Reject any candidate whose source/target entity types violate the registry or whose entities merely co-occur in the same document without explicit or structural evidence.

### 6.2 Ordered Relationship Discovery Priority
1. **Explicit Source References**:
   - GitHub PR body/title/comments/commits (`Closes #12`, `Fixes PROJ-123`) -> `PR_REFERENCES_ISSUE`, `WORK_ITEM_IMPLEMENTED_BY`, `COMMIT_BELONGS_TO_PR` (matching commit SHA in PR/repo).
   - Jira `issuelinks` (`blocks` -> `WORK_ITEM_BLOCKED_BY`, `depends on` -> `WORK_ITEM_DEPENDS_ON`, `parent`/subtask -> `WORK_ITEM_TRACKED_BY`), Jira `components` -> `COMPONENT`/`WORK_ITEM` links.
   - Author/Assignee/Reviewer fields on GitHub PRs/reviews/commits and Jira issues -> `PERSON_AUTHORED`, `PERSON_REVIEWED`, `PERSON_RESPONSIBLE_FOR`.
2. **Stable Source Identifiers**: Same ticket key (`NEX-201`) across Jira issue, GitHub PR title/branch (`feat/nex-201-refresh`), commit message, and uploaded design PDF -> `WORK_ITEM_TRACKED_BY` (`explicit`).
3. **Phase 2.6 Knowledge Evidence Links**:
   - `decisions_rationale.affected_components` -> `DECISION_AFFECTS` (`explicit` if verbatim component name in excerpt).
   - `dependencies` (`source_item`, `target_item`, `direction`, `dependency_type`) -> `COMPONENT_DEPENDS_ON` / `WORK_ITEM_DEPENDS_ON` / `WORK_ITEM_BLOCKED_BY`.
   - `responsibilities_ownership` -> `PERSON_RESPONSIBLE_FOR`.
   - `bugs_blockers_risks` -> `RISK_AFFECTS` / `BUG_FOUND_IN`.
   - Same-fingerprint multi-source `KnowledgeItem` -> `KNOWLEDGE_CORROBORATED_BY`.
4. **Deterministic Matching**: Branch/file path overlap (`backend/app/services/auth.py` modified in PR matching component path in ADR/Technical item) -> `inferred` (`DECISION_IMPLEMENTED_BY` / `WORK_ITEM_IMPLEMENTED_BY`).
5. **Semantic Similarity (pg chunks / Nomic optional) & Bounded LLM Classification (`StructuredLLMClient`)**:
   - Only invoked when enabled (`allow_llm_inference=true`) on bounded shortlists of topically related Decisions <-> PRs/Work Items lacking explicit links.
   - Prompt escapes evidence chunks identically to Phase 2.6, forces citation of **both** sides' `evidence_id` + `chunk_id` + verbatim excerpt, and validator marks `classification="inferred"`, `is_llm_assisted=true`, never `human_confirmed`.

### 6.3 Dependency Graph Analysis Engine (`DependencyIntelligenceService`)
- Deterministic DFS/BFS over PostgreSQL `knowledge_relationships` filtered to dependency/blocking types (`COMPONENT_DEPENDS_ON`, `WORK_ITEM_DEPENDS_ON`, `WORK_ITEM_BLOCKED_BY`, `RISK_AFFECTS`) within one `project_id` and caller-accessible provenance.
- Enforces configurable bounds: `INTELLIGENCE_GRAPH_MAX_DEPTH` (default `8`, max `15`), `INTELLIGENCE_GRAPH_MAX_NODES` (default `250`, max `500`), query statement timeout guard.
- Outputs: direct/transitive dependency trees, blocked work items + root blockers, **explicit cycle detection** (SCC / DFS back-edge paths reported intact as `detected_cycles`—never silently pruned), and uncertainty flags when dependency `status` is unconfirmed (`resolved` requires explicit resolving evidence, never inferred from task closure alone). Critical dependency chains are annotated only when explicit duration/milestone metadata supports them; otherwise flagged `scheduling_metadata_absent`.

---

## 7. Decision-to-Implementation Traceability & Temporal Intelligence

### 7.1 Decision Traceability Chains (`TraceabilityService`)
- Anchors on every active `decision` entity in a project and walks verified outbound/inbound relationships across `Decision -> Work item -> Pull request -> Commit -> Technical component`.
- Completeness classification rules:
  - `untraced`: Zero linked work items, PRs, or commits.
  - `partially_traced`: Has work item OR PR OR commit/component link, but missing intermediate/downstream stages (missing stages recorded explicitly in `missing_links_json`).
  - `complete`: Continuous traced path Decision -> Work item -> PR (or direct Decision -> PR/Commit) -> Commit -> Component with non-rejected provenance.
  - `conflicting`: Competing statuses/targets or disputed/rejected links exist on the chain (both citations preserved).

### 7.2 Temporal Knowledge Intelligence (`TemporalIntelligenceService`)
- Extracts timeline events conservatively from canonical timestamps:
  - Connector API timestamps (`source_created_at`, `merged_at`, `changelog.histories[].created`, commit `author.date`) -> `timestamp_precision="exact_datetime"`, `timestamp_origin="source_api"`/`"source_changelog"`/`"source_commit"`.
  - Document header dates (e.g. `ADR-002 (2026-10-12)` in text) -> `timestamp_precision="date_only"`, `timestamp_origin="document_header"`, `occurred_at` set to explicit `None` or midnight UTC strictly paired with `timestamp_precision="date_only"` (API explicitly surfaces `timestamp_precision` and distinguishes `occurred_at` from `evidence.created_at` ingestion time!).
  - Missing dates -> `occurred_at=NULL`, `timestamp_precision="unknown"`, `timestamp_origin="unknown"`, `recorded_at=evidence.extracted_at`. Upload `created_at` is **never** falsely assigned as `occurred_at` for historical events inside an uploaded file.
- Pairwise/sequence comparison computes: `before`, `after`, `overlapping`, `same_period` (for matching `date_only`/`month_only` granularity), or `unknown` when either side lacks comparable precision.

---

## 8. Relationship Confidence, Provenance & Permissions *(Section 10+ Alignment)*

1. **Relationship Confidence Score & Component Breakdown (Completing Section 10)**:
   - Store bounded `confidence_score` (`0.0 <= score <= 1.0`) alongside explicit metadata clarifying `confidence_is_calibrated_probability = false` (heuristic evidence strength score, not calibrated probability).
   - Store structured `confidence_components_json`:
     - `exact_identifier_match` (`0..1`)
     - `name_or_title_similarity` (`0..1`)
     - `source_metadata_corroboration` (`0..1`, e.g., PR/Jira native link vs single mention)
     - `cross_source_evidence_overlap` (`0..1`, distinct source count & independent evidence items)
     - `temporal_alignment_score` (`0..1`)
     - `semantic_or_llm_score` (`0..1`, `null` when deterministic-only)
2. **Fail-Closed Permission Enforcement (`PermissionFilterService`)**:
   - Every query (`entities`, `relationships`, `traceability`, `timeline`, `dependencies`, `identities`) resolves the caller's live allowed evidence IDs via `SourceAccessPolicyService` + `EvidenceRepository` in PostgreSQL **before** returning nodes, edges, timeline events, or traceability chains.
   - An entity/relationship/event backed solely by inaccessible or soft-deleted evidence is hidden in project lists (`403 SOURCE_ACCESS_DENIED` + `intelligence.*_denied` audit event on direct item lookup); corroborated items strip inaccessible provenance links while keeping accessible ones.
   - `include_synthetic=false` is enforced by default on every endpoint and run.
   - Updating or deleting an underlying `EvidenceItem` or `KnowledgeItem` propagates `is_stale=true` cleanly to linked `knowledge_entities`, `knowledge_relationships`, and `decision_traceability_chains`.

---

## 9. Background Processing, API Contracts & RBAC

1. **Background Worker (`IntelligenceWorkerService` in `CompositeWorkerService`)**:
   - Claim job type `knowledge_intelligence` from `background_jobs` via `SELECT ... FOR UPDATE SKIP LOCKED`, re-verify actor org/project membership & `SourceAccessPolicyService` ACLs per scope (never mixing restricted & open items inside an LLM batch), build deterministic entities/aliases/relationships/timeline/chains/dependency index first, run optional bounded LLM disambiguation if configured, and update `intelligence_runs` telemetry.
2. **REST API Endpoints (`/api/v1/projects/{project_id}/intelligence/...` in `app/api/routes/intelligence.py`)**:
   - **Orchestration** (Explicit Member + `project.evidence.contribute` or `project.manage`):
     - `POST /projects/{project_id}/intelligence/reconstruct` (`202 Accepted` — `include_llm_inference: bool = False`, `include_synthetic: bool = False`, `force_rerun: bool = False`, idempotent active run guard)
     - `GET /projects/{project_id}/intelligence/runs` & `GET .../runs/{run_id}` (`project.read`)
     - `POST /projects/{project_id}/intelligence/runs/{run_id}/cancel` (`project.evidence.contribute` | `project.manage`)
     - `POST /projects/{project_id}/intelligence/runs/{run_id}/retry` (`project.evidence.contribute` | `project.manage`)
   - **Entity & Identity Resolution**:
     - `GET /projects/{project_id}/intelligence/entities` & `GET .../entities/{entity_id}` (`project.read` + live ACL filtering; returns aliases, relationships count, linked timeline count)
     - `GET /projects/{project_id}/intelligence/identities/candidates` (`project.read` + live ACL filtering)
     - `POST /projects/{project_id}/intelligence/identities/candidates/{candidate_id}/review` (`project.knowledge.review` or `project.manage` -> `accept` | `reject`, records reviewer & audit log)
     - `POST /projects/{project_id}/intelligence/identities/candidates/{candidate_id}/revert` (`project.knowledge.review` or `project.manage` -> restores unmerged entities & audit log)
   - **Relationships & Provenance**:
     - `GET /projects/{project_id}/intelligence/relationships` (filter by `relationship_type`, `classification`, `entity_id`, `min_confidence`, `include_stale`, `include_synthetic`) & `GET .../relationships/{relationship_id}` (`project.read` + live ACL)
     - `POST /projects/{project_id}/intelligence/relationships/{relationship_id}/review` (`project.knowledge.review` or `project.manage` -> transitions `confirm` (`human_confirmed`) | `reject` | `dispute`, never callable by worker/LLM)
   - **Decision Traceability, Timeline & Dependency Analysis**:
     - `GET /projects/{project_id}/intelligence/traceability` & `GET .../traceability/decisions/{decision_entity_id}` (`project.read` + live ACL)
     - `GET /projects/{project_id}/intelligence/timeline` (`project.read` + filters: `entity_id`, `event_type`, `source_type`, `date_from`, `date_to`, `include_synthetic`)
     - `GET /projects/{project_id}/intelligence/dependencies/graph` & `GET .../dependencies/entities/{entity_id}` (`project.read` + `max_depth`, `include_inferred`, `include_cycles`, live ACL)
3. **Configuration Additions (`app/core/config.py`, `.env.example`, `environment-setup.md`)**:
   - `IntelligenceSettings`: identity weights (`0.40, 0.25, 0.15, 0.10, 0.10`), thresholds (`0.95`, `0.75`), `allow_llm_relationship_inference=false` (opt-in or configurable default with bounded max pairs `INTELLIGENCE_LLM_MAX_CANDIDATE_PAIRS=25`), `graph_max_depth=8`, `graph_max_nodes=250`.

---

## 10. Testing, Evaluation & Rollback Plan

1. **Automated Test Matrix (SQLite Isolated + Live PostgreSQL 16 + Optional Live `qwen3:8b`)**:
   - `test_migrations_intelligence.py`: Upgrade `base -> 0008_cross_source_intelligence -> downgrade 0007 -> upgrade head` on live PostgreSQL verifying all tables, CHECK constraints, partial indexes, and `background_jobs` constraint rollback.
   - `test_identity_resolution.py`: Tests weighted matching (`exact_external_id`, cross-provider collision guard, `@achen` vs `Alex Chen` staying `manual_review`, display-name-only never auto-merging persons, reviewer accept & revert restoring original entities cleanly).
   - `test_cross_source_relationships_and_traceability.py`: End-to-end ADR PDF + Jira `NEX-101` (`issuelinks` + changelog) + GitHub PR (`Closes #12`, `NEX-101`, changed files) + Commit -> verifies Decision -> Work Item -> PR -> Commit -> Component chain (`complete` vs `partially_traced` vs `untraced`), dependency cycle detection (preserving cyclic edges cleanly), ungrounded relationship rejection, and conservative `confidence_components`.
   - `test_temporal_intelligence.py`: Verifies `date_only` vs `exact_datetime` vs `unknown` precision, upload timestamps never impersonating event dates, and sequence comparisons (`before`, `after`, `same_period`, `unknown`).
   - `test_intelligence_security_and_acl.py`: Verifies cross-tenant `404`, source-restricted Jira/GitHub hiding across entities, relationships, traceability chains, timeline events, and dependency graphs, non-promotion of AI links to `human_confirmed`, RBAC rejection (`403`) when non-reviewer attempts confirm/revert, `include_synthetic=false` isolation, staleness propagation on evidence update/delete, and `audit_logs` emission.
   - `test_live_qwen3_intelligence_evaluation.py`: Optional/live PG + Ollama `qwen3:8b` synthetic multi-source evaluation measuring deterministic + LLM-assisted precision/grounding cleanly inside synthetic isolation.
2. **Rollback Safety**:
   - All new schema resides in additive tables (`0008`) except the single reversible `background_jobs` `ck_background_jobs_background_job_type` CHECK expansion. Running `alembic downgrade 0007_knowledge_reconstruction` cleanly restores Phase 2.6 schema state.

---

## 11. Confirmation Checklist Before Implementation Begins

1. **Truncated Section 10+ Check**: Please share Sections 10 (rest of Confidence & Provenance) onward from your Phase 2.7 directive if there were additional mandatory requirements (e.g., specific endpoint paths, confidence breakdown fields, evaluation benchmarks, or worker auto-chaining triggers after Phase 2.6).
2. **Review Endpoints Scope**: Confirm whether human alias merge approval/reversal and relationship confirmation endpoints (`POST .../review` / `revert` gated on existing `project.knowledge.review` / `project.manage`) belong directly in Phase 2.7 APIs or should emit candidates only until Verification Center (Phase 6).
3. **LLM Inference Default**: Confirm `INTELLIGENCE_ALLOW_LLM_INFERENCE` default (we recommend `false` by default or opt-in `include_llm_inference` per run given measured ~47–69s/call local 6 GB VRAM `qwen3:8b` latency, keeping deterministic matching fast and always-on).
