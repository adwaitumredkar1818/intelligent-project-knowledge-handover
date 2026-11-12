# Development Roadmap

> **Classification Key:** **Confirmed Constraints** define fixed sequencing principles, approved architectural decisions, quality gates, and technology baselines. **Proposed Implementation Phases** outline the incremental build order pending explicit approval after Phase 0.

---

## 1. Roadmap Governance & Phase Gates (Confirmed Rules)

1. **Explicit Approval Gate**: Phase 0 covers governance, architecture documentation, and repository structure only. **Do not begin Phase 1 infrastructure setup or application coding until explicit approval is granted.**
2. **Full-Stack Vertical Design**: Every feature implemented from Phase 1 onward must explicitly account for its **Frontend**, **Backend**, **Database**, and **Security** implications.
3. **Testing Gate**: No feature or phase milestone may be marked implemented until automated tests and verification checks pass cleanly.
4. **No Fabrication Rule**: Development and testing must never display synthetic GitHub repositories, Jira issues, Slack threads, or user evidence as real connected organisational data; any test fixtures must be explicitly marked `is_synthetic = true`.
5. **Stack & Infrastructure Discipline**: Adhere strictly to SQLAlchemy 2.x, Alembic, Psycopg 3, ChromaDB HTTP server mode, PostgreSQL-backed lightweight Python worker (no Redis/Celery), local Ollama (`qwen3:8b`, `nomic-embed-text`, `glm-ocr:latest` behind OCR abstraction; no vLLM), and separated FastAPI authentication.

---

## 2. Proposed Phased Implementation Plan

### Phase 0: Project Governance, Architecture & Initial Structure *(Completed)*
- **Scope**:
  - Establish `AGENTS.md`, `README.md`, `.gitignore`, `.env.example`, folder structure, and core architecture/development documentation reflecting all finalised baseline architectural decisions.
  - Ensure complete consistency across documents and clearly separate confirmed decisions from proposed implementation details.
- **Exit Criteria**: Documentation reviewed and explicit user approval received to proceed to Phase 1.

---

### Phase 1: Infrastructure, Database Baseline & Application Skeletons *(Phase 1.1–1.3 Host & Data Infrastructure Completed)*
- **Scope**:
  - Create Docker Compose configuration in `infrastructure/docker/` for PostgreSQL, **ChromaDB (dedicated HTTP server mode)**, backend FastAPI service, **lightweight Python background worker process**, and frontend Next.js app, wired to existing local Ollama (`qwen3:8b`, `nomic-embed-text`, `glm-ocr:latest`).
  - Configure **SQLAlchemy 2.x**, **Alembic**, and **Psycopg 3** (`psycopg`) migrations covering canonical tables including `background_jobs`, `users`, `user_source_authorisations`, `source_access_policies`, and `evidence_chunks` (`tsvector` + `GIN` index).
  - Provision private backend-only encrypted upload storage volume (`UPLOAD_STORAGE_PATH`) completely outside frontend directories.
  - Scaffold Python 3.11 + FastAPI backend preserving the 11-module architecture and worker entrypoint; scaffold Next.js + React + TypeScript + Tailwind + shadcn/ui + Lucide Icons skeleton.
  - Set up automated linting, type-checking, and test runners.
- **Exit Criteria**: Docker Compose services connect reliably; Alembic migrations apply cleanly; worker claims/completes test PostgreSQL job records; health checks and baseline CI checks pass.

---

### Phase 2: FastAPI Authentication, RBAC, Audit Logging & Project Workspace *(Backend 2.1–2.3 Completed; Frontend Workspace UI Pending)*
- **Scope**:
  - **Implemented (Phase 2.1–2.3 Backend)**: Backend **Authentication and authorisation** module (Argon2id registration/login, short-lived JWT access tokens, rotated hashed `HttpOnly` refresh cookies with CSRF origin checks, scope-separated platform/organisation/project RBAC via revisions `0002_auth_identity_rbac` and `0003_org_project_workspaces`), multi-tenant organisations, SHA-256 hashed invitations, project workspaces with visibility/lifecycle governance, and persistent sanitised `audit_logs`.
  - **Remaining in Phase 2 / Frontend Integration**: Build **Project Workspace** and authentication frontend UI flows in `frontend/` (Next.js App Router, Tailwind CSS, shadcn/ui) aligned to `/api/v1` contracts.
- **Exit Criteria**: Unit and integration tests verify password hashing, JWT validation, `HttpOnly` refresh rotation/revocation, multi-tenant isolation, RBAC denial (`403` / `404`) enforcement, and audit log creation.

---

### Phase 3 (Backend Phase 2.4A + Phase 2.5 Completed): Document Ingestion, Evidence Workspace & Hybrid Indexing
- **Scope**:
  - **Implemented (Backend Phase 2.4A — Document Ingestion & Worker Foundation via revision `0004_evidence_ingestion`)**: Unified `evidence_items` ledger with mandatory provenance and future connector/ACL hooks (`source_connection_id`, `source_access_policy_id`, `acl_scope`), separated `evidence_contents` + `evidence_page_contents` tables, PostgreSQL `background_jobs` queue (`SELECT ... FOR UPDATE SKIP LOCKED`, stale-lease recovery, exponential retries), strict PDF/DOCX validation (`PyMuPDF`, `python-docx`), `AES-256-GCM` private storage (`LocalPrivateStorageBackend`), replaceable `OCRService` abstraction (`OllamaGLMOCRService` using `glm-ocr:latest` at `OLLAMA_OCR_NUM_CTX=8192` with truncation detection -> `partially_extracted`), standalone worker CLI (`python -m app.worker`), and `/api/v1/projects/{project_id}/evidence...` + `/api/v1/evidence/...` endpoints with immutable audit logging.
  - **Implemented (Backend Phase 2.5 — Evidence Chunking, Hybrid Search & Permission-Aware Retrieval via revision `0006_evidence_chunks_and_fts`)**: Structure-aware `ChunkingService` (PDF/DOCX headings/tables, GitHub issues/PRs/commits/files, Jira issues/comments/changelog, and identifier token expansion), PostgreSQL `evidence_chunks` with weighted `TSVECTOR` + `GIN` index (`websearch_to_tsquery` + `ts_rank_cd`), replaceable `EmbeddingService` (`OllamaEmbeddingService` using `nomic-embed-text`, 768 dims, `batch_size=8`), ChromaDB HTTP v2 secondary vector indexing (`ChromaV2HttpVectorStore` with allowlisted metadata & model/dimension compatibility checks), `IndexingWorkerService` (`evidence_indexing` / `evidence_reindexing` / `evidence_index_cleanup`, `partially_indexed` resilience on Chroma outage), `HybridRetrievalService` (RRF fusion, two-phase ACL pre-filter + canonical PG post-revalidation, degraded `hybrid -> keyword` fallback vs `semantic -> 503`), and `/api/v1/projects/{id}/search`, `/chunks/{chunk_id}`, `/indexing/*` routes.
  - **Remaining in Frontend Integration**: Build the **Evidence Workspace** and search/citation Next.js UI.
- **Exit Criteria**: Backend tests confirm encryption at rest, private storage isolation, digital/scanned PDF (`glm-ocr:latest`) and `.docx` ingestion, `nomic-embed-text` + ChromaDB v2 + PG FTS hybrid retrieval, ACL enforcement, outage recovery, soft-delete vector cleanup, and `POST /indexing/reindex` ChromaDB rebuild from PostgreSQL.

---

### Phase 4 (Backend Phase 2.4B Completed for GitHub & Jira): Delegated Source Integrations (`CONNECT`)
- **Scope**:
  - **Implemented (Backend Phase 2.4B — `0005_source_integrations`)**: **Source integrations** backend module using `HTTPX` with **delegated, per-user OAuth 2.0 + PKCE (`S256`) authorisation** (`SourceOAuthService`, single-use SHA-256 `oauth_states`, `TOKEN_ENCRYPTION_KEY` AES-256-GCM encryption via `LocalTokenEncryptionService`, atomic `FOR UPDATE` refresh rotation) and PostgreSQL identity/ACL preservation (`source_connections`, `user_source_authorisations`, `source_access_policies`, `project_source_mappings`, `source_sync_runs`):
    1. **GitHub API** connector (`GitHubClient`, `GitHubSyncOrchestrator`): repo discovery, issues/PRs/reviews/comments/commits/README/docs/discussions, `ETag`/`since` cursors, full-snapshot disappearance reconciliation.
    2. **Jira API** connector (`JiraClient`, `JiraSyncOrchestrator`): Atlassian 3LO Cloud site/project discovery, safe project-scoped JQL + `updated >=` cursors, ADF-to-text, comments/worklogs/changelog/links, and fail-closed `fields.security` sub-policies.
    3. **Slack API**: Strictly disabled and gated (`SLACK_ENABLED=false`, returning `409 SLACK_INTEGRATION_DISABLED`) until workspace authorisation, API scope review, and data-retention requirements are confirmed.
  - Execute idempotent sync pipelines (`SourceEvidenceIngestor`) via `CompositeWorkerService` / `SourceSyncWorkerService` (`job_type = "source_sync"`), enforcing fail-closed PostgreSQL item/SQL ACLs (`SourceAccessPolicyService`, `EvidenceRepository`).
  - **Implemented (Backend Phase 2.5 Extension)**: Two-phase ACL enforcement extended onto `evidence_chunks` and ChromaDB metadata filtering (`permission_scope_key`, `is_synthetic`, canonical PG `SourceAccessPolicyService` post-revalidation) prior to retrieval return.
  - **Remaining for Future Hardening / Frontend**: Add periodic background ACL re-sync or webhook triggers if scheduled later, and build the **Project Workspace** / **Evidence Workspace** Next.js integration UI.
- **Exit Criteria**: Contract/integration tests verify delegated per-user token encryption, idempotent sync (`content_hash`), and strict non-sharing of restricted sources when only one member connects an account across both PostgreSQL evidence and hybrid ChromaDB/FTS chunk retrieval.

---

### Phase 5 *(Backend Phase 2.6 Extraction Complete; Relationships & Frontend UI Pending)*: Knowledge Reconstruction & Relationship Explorer (`RECONSTRUCT`)
- **Scope**:
  - **Implemented (Backend Phase 2.6 — Knowledge Reconstruction via revision `0007_knowledge_reconstruction`)**: Replaceable `StructuredLLMClient` (`OllamaLLMClient` using `qwen3:8b` with `think=false` and `format="json"`), category-specific Pydantic candidate extraction across 6 core domains (`decisions_rationale`, `work_items`, `responsibilities_ownership`, `technical_architecture`, `bugs_blockers_risks`, `dependencies`), strict `NO EVIDENCE -> NO CLAIM` validator (`KnowledgeCandidateValidator` enforcing chunk membership, verbatim/normalized-whitespace substring match, epistemic cap `"extracted"`/`"ai_interpreted"`, and ungrounded-severity downgrade to `"unspecified"`), conservative corroboration deduplication, re-chunk/deletion staleness tracking, invalid-JSON repair retries, fail-closed ACL enforcement across trigger/worker/read paths (`ReconstructionWorkerService` in `CompositeWorkerService`), and `/api/v1/projects/{id}/knowledge/*` + `/evidence/{id}/extract` endpoints.
  - **Remaining in Phase 5 / Frontend Integration**: Implement **Relationship management** (`knowledge_relationships` PostgreSQL graph + cross-source identity/entity resolution in Phase 2.7+), remaining domain coverage (operational procedures / historical discussions where needed), and **Knowledge Intelligence** + **Relationship Explorer** Next.js / React Flow UI.
- **Exit Criteria**: Tests validate rejection of ungrounded claims lacking `chunk_id` & verified excerpt attribution, strict separation of `extracted` vs `ai_interpreted` records, zero cross-ACL LLM prompt leakage, and accurate PostgreSQL graph queries (for Phase 2.7+).

---

### Phase 6: Verification Engine & Human Review (`VERIFY` → `REVIEW`)
- **Scope**:
  - Implement **Verification** module: automated conflict detection, missing-information analysis, and uncertainty/staleness checks via worker jobs.
  - Build **Verification Center** UI enabling authorised human reviewers to compare original evidence vs extracted/AI items, resolve disputes, and promote records to **Human-Verified Knowledge**.
- **Exit Criteria**: Tests prove the LLM cannot alter verification status, conflicting evidence surfaces both citations without auto-resolution, and human review actions emit immutable audit logs.

---

### Phase 7: Handover Governance & Hybrid Permission-Filtered Assistant (`HANDOVER` + RAG)
- **Scope**:
  - Implement **Handover** module and **Handover Workspace** UI: structured package assembly, readiness checks, unresolved-risk tracking, **mandatory designated reviewer approval before sharing**, separate **incoming assignee receipt acknowledgment** (non-substituting), and authenticated export.
  - Implement **AI assistant** and **Embedding and retrieval** hybrid query layer (**ChromaDB semantic search + PostgreSQL full-text search** combined and ranked by backend retrieval layer, pre-filtered by user permissions before reaching `qwen3:8b`) and **Project Knowledge Assistant** UI.
- **Exit Criteria**: Security tests confirm cross-project and per-user source isolation before LLM invocation, designated reviewer approval gating vs non-substituting assignee acknowledgment, and explicit abstention when evidence is missing.

---

### Phase 8: Realistic Evidence Benchmarking & Security Hardening
- **Scope**:
  - **Benchmark hybrid retrieval quality, `qwen3:8b` extraction/RAG faithfulness, and `glm-ocr:latest` OCR accuracy/latency using realistic project evidence before fixing numerical retrieval/abstention thresholds.**
  - Document benchmark results and confirm whether existing Ollama runtimes meet requirements or whether any replacement proposal (e.g., separate OCR service or larger model) is warranted.
  - Perform security audit (secrets hygiene, upload fuzzing, `HttpOnly` cookie/CSRF verification, RBAC bypass attempts, prompt-injection tests, synthetic-data isolation checks) and finalise `documentation/api/` specifications.
- **Exit Criteria**: Realistic-evidence benchmark report documented, numerical thresholds justified and configured, full test suite passing, and security checklist verified.

---

## 3. Feature Definition of Done (Confirmed Standard)

Before any feature slice is marked complete:
- [ ] **Backend**: Modular boundary respected; Pydantic validation, worker job error handling, and explicit error propagation implemented.
- [ ] **Database**: Alembic migrations cleanly applied via SQLAlchemy 2.x + Psycopg 3; provenance, source ACLs, and epistemic states preserved.
- [ ] **Frontend**: Typed React/TypeScript components using Tailwind/shadcn/ui/Lucide (and React Flow where applicable); clear epistemic labelling; zero exposed tokens/secrets.
- [ ] **Security**: Backend RBAC, pre-retrieval source permission filtering, private encrypted uploads, audit logging, and non-JS refresh cookies verified.
- [ ] **Tests**: Meaningful unit/integration tests executed and observed passing after final edit.
- [ ] **Docs**: Relevant `documentation/` and `.env.example` entries updated if contracts changed.
