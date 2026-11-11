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

### Phase 0: Project Governance, Architecture & Initial Structure *(Current Phase)*
- **Scope**:
  - Establish `AGENTS.md`, `README.md`, `.gitignore`, `.env.example`, folder structure, and core architecture/development documentation reflecting all finalised baseline architectural decisions.
  - Ensure complete consistency across documents and clearly separate confirmed decisions from proposed implementation details.
- **Exit Criteria**: Documentation reviewed and explicit user approval received to proceed to Phase 1.

---

### Phase 1: Infrastructure, Database Baseline & Application Skeletons *(Next Upon Approval)*
- **Scope**:
  - Create Docker Compose configuration in `infrastructure/docker/` for PostgreSQL, **ChromaDB (dedicated HTTP server mode)**, backend FastAPI service, **lightweight Python background worker process**, and frontend Next.js app, wired to existing local Ollama (`qwen3:8b`, `nomic-embed-text`, `glm-ocr:latest`).
  - Configure **SQLAlchemy 2.x**, **Alembic**, and **Psycopg 3** (`psycopg`) migrations covering canonical tables including `background_jobs`, `users`, `user_source_authorisations`, `source_access_policies`, and `evidence_chunks` (`tsvector` + `GIN` index).
  - Provision private backend-only encrypted upload storage volume (`UPLOAD_STORAGE_PATH`) completely outside frontend directories.
  - Scaffold Python 3.11 + FastAPI backend preserving the 11-module architecture and worker entrypoint; scaffold Next.js + React + TypeScript + Tailwind + shadcn/ui + Lucide Icons skeleton.
  - Set up automated linting, type-checking, and test runners.
- **Exit Criteria**: Docker Compose services connect reliably; Alembic migrations apply cleanly; worker claims/completes test PostgreSQL job records; health checks and baseline CI checks pass.

---

### Phase 2: FastAPI Authentication, RBAC, Audit Logging & Project Workspace
- **Scope**:
  - Implement Backend **Authentication and authorisation** module: FastAPI-managed registration/login with secure password hashing, short-lived JWT access tokens, rotated hashed refresh tokens delivered strictly in `HttpOnly` cookies (never exposed to browser JavaScript), RBAC dependencies, and audit log writer.
  - Build **Project Workspace** APIs and UI (create/manage projects, assign project roles including designated reviewers and incoming assignees, view audit history).
- **Exit Criteria**: Unit and integration tests verify password hashing, JWT validation, `HttpOnly` refresh rotation/revocation, RBAC denial (403) enforcement, and audit log creation.

---

### Phase 3: Document Ingestion, Evidence Workspace & Hybrid Indexing
- **Scope**:
  - Implement **Document ingestion** module: file validation (MIME, magic bytes, size), opaque UUID filenames, encryption at rest inside private backend storage, `PyMuPDF` + `python-docx` parsers, and the **replaceable backend OCR abstraction** using local Ollama `glm-ocr:latest` executed via Python worker jobs.
  - Persist canonical `evidence_items` with all 7 mandatory metadata fields in PostgreSQL.
  - Implement **Embedding and retrieval** indexing baseline: PostgreSQL `tsvector` FTS maintenance + `nomic-embed-text` embeddings written to ChromaDB HTTP server + rebuild script from PostgreSQL.
  - Build **Evidence Workspace** UI to upload, inspect original text/OCR output, track worker job status, and verify provenance metadata.
- **Exit Criteria**: Tests confirm encryption at rest, private storage isolation, digital/scanned PDF and `.docx` ingestion via worker jobs, full provenance retention, and deterministic ChromaDB rebuild from PostgreSQL.

---

### Phase 4: Delegated Source Integrations (`CONNECT`)
- **Scope**:
  - Implement **Source integrations** module using `HTTPX` with **delegated, per-user OAuth 2.0 authorisation** (kept separate from platform login) and PostgreSQL identity/ACL preservation (`user_source_authorisations`, `source_access_policies`):
    1. **GitHub API** connector (initial priority)
    2. **Jira API** connector (initial priority)
    3. **Slack API** optional MVP evaluation — proceed **only** after workspace authorisation, API scope review, and data-retention requirements are confirmed
  - Execute sync pipelines via Python worker jobs.
- **Exit Criteria**: Contract/integration tests verify delegated per-user token encryption, idempotent sync (`content_hash`), and strict non-sharing of restricted sources when only one member connects an account.

---

### Phase 5: Knowledge Reconstruction & Relationship Explorer (`RECONSTRUCT`)
- **Scope**:
  - Implement **Extraction and processing** and **Knowledge reconstruction** modules via worker jobs using Ollama (`qwen3:8b`) + Pydantic structured extraction across all 8 knowledge categories.
  - Implement **Relationship management** module storing typed edges in PostgreSQL (`knowledge_relationships`).
  - Build **Knowledge Intelligence** UI (epistemic state badges, source citations) and **Relationship Explorer** UI (interactive graph via React Flow).
- **Exit Criteria**: Tests validate rejection of ungrounded claims lacking `chunk_id` attribution, strict separation of `extracted` vs `ai_interpreted` records, and accurate PostgreSQL graph queries.

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
