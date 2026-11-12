# Backend Application Foundation (`backend/`)

Python 3.11 + FastAPI backend runtime for the **Intelligent Project Knowledge Reconstruction & Handover Platform**.

> **Current Stage (Phase 2.6 — AI Knowledge Reconstruction & Structured Intelligence Extraction):** Core application skeleton, centralised Pydantic Settings (reading root `.env`), structured correlation-ID and secret/OAuth-redacting logging, safe exception handling, SQLAlchemy 2.x + Psycopg 3 PostgreSQL engine/session management, Alembic migrations (`0001_initial_baseline`, `0002_auth_identity_rbac`, `0003_org_project_workspaces`, `0004_evidence_ingestion`, `0005_source_integrations`, `0006_evidence_chunks_and_fts`, `0007_knowledge_reconstruction`), infrastructure health/readiness endpoints, platform authentication, refresh-session rotation, user lifecycle, scope-separated RBAC (8 roles, 23 permissions, 49 role-permission links), multi-tenant organisations, SHA-256 hashed invitations, project workspaces, sanitised PostgreSQL `audit_logs`, AES-256-GCM encrypted private document storage, strict PDF/DOCX validation, PyMuPDF + `python-docx` + replaceable `OCRService` (`glm-ocr:latest`), delegated per-user GitHub & Jira OAuth 2.0 (`TOKEN_ENCRYPTION_KEY`, PKCE `S256`, fail-closed `SourceAccessPolicyService`, idempotent `SourceEvidenceIngestor`), structure-aware `ChunkingService`, PostgreSQL `TSVECTOR` + `GIN` full-text search (`EvidenceChunk`), Ollama `nomic-embed-text` (768-dim) embeddings, ChromaDB HTTP v2 secondary vector indexing (`ChromaV2HttpVectorStore`), `HybridRetrievalService` (RRF fusion, two-phase ACL filtering, `hybrid -> keyword` degraded fallback), replaceable `StructuredLLMClient` (`OllamaLLMClient` / `qwen3:8b` with `think=false`), 6-category `NO EVIDENCE -> NO CLAIM` validator (`KnowledgeCandidateValidator`), conservative corroboration deduplication & staleness invalidation, and the lightweight `CompositeWorkerService` (`python -m app.worker` running `document_ingestion` + `source_sync` + `IndexingWorkerService` + `ReconstructionWorkerService`) under `/api/v1` are implemented and verified. Knowledge relationships, verification review workflows, handover generation, and assistant synthesis belong to subsequent phases.

---

## Application Structure (`backend/app/`)

```text
backend/
├── app/
│   ├── api/
│   │   ├── deps.py                # FastAPI dependencies (settings, DB, HTTPX, storage, JWT, tenant/project RBAC)
│   │   ├── routes/
│   │   │   ├── auth.py            # /api/v1/auth endpoints (register, login, refresh, logout, me, sessions)
│   │   │   ├── evidence.py        # /api/v1/projects/{id}/evidence & /api/v1/evidence/* ingestion endpoints
│   │   │   ├── health.py          # Infrastructure liveness and readiness routes
│   │   │   ├── integrations.py    # /api/v1/.../integrations* delegated OAuth, discovery, mappings & sync routes
│   │   │   ├── knowledge.py       # /api/v1/projects/{id}/.../extract & /knowledge/* reconstruction endpoints
│   │   │   ├── organisations.py   # /api/v1/organisations, memberships, /invitations/{token}/accept & audit events
│   │   │   ├── projects.py        # /api/v1/organisations/{id}/projects & /api/v1/projects endpoints
│   │   │   ├── retrieval.py       # /api/v1/projects/{id}/search, /chunks/{chunk_id} & /indexing/* endpoints
│   │   │   └── users.py           # /api/v1/users & /api/v1/roles admin lifecycle endpoints
│   │   └── v1/router.py           # Versioned /api/v1 router assembly
│   ├── core/
│   │   ├── config.py              # Pydantic Settings (DB, ChromaDB, Chunking, Embedding, Retrieval, Ollama, Extraction, Security & Integrations)
│   │   ├── exceptions.py          # Typed AppError hierarchy (incl. 410/413/415/422) + sanitised error handlers
│   │   ├── logging.py             # Single-line structured JSON logger with correlation ID & secret/OAuth redaction
│   │   ├── middleware.py          # X-Request-ID correlation, request timing log & baseline security headers
│   │   ├── rate_limit.py          # Pluggable rate-limiter protocol & in-memory sliding-window backend
│   │   ├── rbac_catalog.py        # Scope-separated system roles & permissions catalog (23 perms, 8 roles)
│   │   ├── security.py            # Argon2id hashing, JWT creation/decoding, opaque hashes, HttpOnly cookies & CSRF
│   │   └── validators.py          # Shared UTC datetimes, email/name/slug normalisation & password strength checks
│   ├── db/
│   │   ├── base.py                # SQLAlchemy 2.x DeclarativeBase + PostgreSQL naming convention
│   │   └── session.py             # Psycopg 3 engine lifecycle, session factory, connectivity ping
│   ├── models/                    # ORM models (User, Auth, RBAC, Org, Project, AuditLog, Evidence*, BackgroundJob, Integration*)
│   ├── repositories/
│   │   ├── audit.py               # Append-only AuditLog persistence & organisation-scoped queries
│   │   ├── auth.py                # RefreshSession persistence, rotation, family revocation & reuse detection
│   │   ├── chunk.py               # EvidenceChunk persistence, weighted TSVECTOR FTS queries & index status summaries
│   │   ├── evidence.py            # EvidenceItem, EvidenceContent & EvidencePageContent persistence, dedup & ACL filtering
│   │   ├── integration.py         # SourceConnection, UserSourceAuthorisation, OAuthState, Policy, Mapping & SyncRun repos
│   │   ├── job.py                 # BackgroundJob claiming (FOR UPDATE SKIP LOCKED), retries & lease recovery
│   │   ├── knowledge.py           # KnowledgeExtractionRun, KnowledgeItem & KnowledgeEvidenceLink ACL-aware repos
│   │   ├── organisation.py        # Organisation, OrganisationMembership & OrganisationInvitation persistence
│   │   ├── project.py             # Project & ProjectMembership persistence, visibility filter & cascade revoke
│   │   ├── rbac.py                # Role, Permission, RolePermission & UserRole queries/assignments
│   │   ├── system.py              # Database connectivity probe repository
│   │   └── user.py                # User identity persistence & lifecycle queries
│   ├── schemas/
│   │   ├── auth.py                # Auth request/response & session Pydantic v2 schemas
│   │   ├── common.py              # Canonical ErrorResponse / ErrorDetail schemas
│   │   ├── evidence.py            # Evidence summaries, details, separated content, pages, indexing state & job schemas
│   │   ├── health.py              # HealthResponse & ReadinessResponse Pydantic v2 models
│   │   ├── integrations.py        # Connection, OAuth, discovery, mapping, ACL verify & sync run Pydantic schemas
│   │   ├── knowledge.py           # 6-category LLM candidate schemas, extraction run, item & link Pydantic schemas
│   │   ├── organisation.py        # Organisation, membership, invitation & audit log Pydantic v2 schemas
│   │   ├── project.py             # Project workspace & project membership Pydantic v2 schemas
│   │   ├── retrieval.py           # Search filters, RRF score breakdowns, citations, indexing health & reindex schemas
│   │   └── user.py                # User profile, admin user management & RBAC role/permission schemas
│   ├── services/
│   │   ├── integrations/          # Delegated OAuth, PKCE, ACL policy, GitHub/Jira HTTPX clients, syncs & sync worker
│   │   ├── audit.py               # Backend-trusted audit recording with recursive secret sanitisation
│   │   ├── auth.py                # Registration, login, token rotation, logout & self-session management
│   │   ├── chunking.py            # Structure-aware document/GitHub/Jira chunking & FTS identifier extraction
│   │   ├── document_extraction.py # PDF (PyMuPDF + OCR triage) & DOCX structured extraction service
│   │   ├── document_validation.py # Strict MIME, magic-byte, zip-bomb, page limit & filename validation
│   │   ├── embedding.py           # Replaceable EmbeddingService & Ollama nomic-embed-text adapter (768 dims)
│   │   ├── evidence.py            # Upload, project dedup, tenant/ACL enforcement, reprocess & logical delete
│   │   ├── extraction_prompts.py  # Prompt-injection escaping, single-evidence batching & 6-category extraction/repair prompts
│   │   ├── health.py              # Orchestrates DB readiness + optional Ollama/ChromaDB probes
│   │   ├── indexing_worker.py     # Async worker for chunking, PG TSVECTOR, Ollama embeddings, Chroma upsert & cleanup
│   │   ├── ingestion_worker.py    # Worker execution loop for queued document ingestion jobs & retries
│   │   ├── knowledge.py           # KnowledgeReconstructionService (ACL trigger/retry/cancel/list/detail/status)
│   │   ├── knowledge_validator.py # NO EVIDENCE -> NO CLAIM validator, epistemic caps, severity guard & dedup fingerprint
│   │   ├── llm.py                 # Replaceable StructuredLLMClient protocol & OllamaLLMClient (qwen3:8b, think=false)
│   │   ├── ocr.py                 # Replaceable OCRService protocol & OllamaGLMOCRService (glm-ocr:latest)
│   │   ├── organisation.py        # Organisation lifecycle, member role governance & hashed invitation workflows
│   │   ├── project.py             # Project lifecycle transitions, visibility, ownership & membership rules
│   │   ├── rbac.py                # Platform, organisation & project RBAC resolution & escalation checks
│   │   ├── reconstruction_worker.py # Async worker executing Phase 2.6 LLM extraction, JSON repair & ACL re-checks
│   │   ├── retrieval.py           # HybridRetrievalService (RRF fusion, two-phase ACLs, degraded fallback & reindex)
│   │   ├── storage.py             # AES-256-GCM LocalPrivateStorageBackend (HKDF + AAD + opaque keys)
│   │   ├── token_encryption.py    # Dedicated AES-256-GCM LocalTokenEncryptionService (TOKEN_ENCRYPTION_KEY + AAD)
│   │   ├── user.py                # Admin user inspection, status lifecycle & role assignment orchestration
│   │   └── vector_store.py        # Replaceable VectorStoreClient & ChromaDB HTTP v2 adapter
│   ├── main.py                    # FastAPI app factory, lifespan disposal, CORS, middleware & rate limiter
│   └── worker.py                  # Standalone CompositeWorkerService (`document_ingestion` + `source_sync` + `evidence_indexing` + `knowledge_reconstruction`)
├── tests/                         # Unit, security, RBAC, storage, OCR/extraction, OAuth/sync, ACL & migration tests
├── alembic.ini                    # Alembic config pointing to ../infrastructure/database/migrations
├── pyproject.toml                 # Dependencies, optional phase groups, ruff, mypy (strict) & pytest config
└── requirements.txt               # Pinned runtime dependencies compiled with uv
```

---

## Setup & Local Execution

```powershell
# 1. Create and activate Python 3.11 virtual environment (from repository root)
py -3.11 -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1

# 2. Install pinned runtime dependencies (and optional dev tools for lint/type/test)
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
python -m pip install pytest ruff mypy

# 3. Run FastAPI locally against Docker PostgreSQL/ChromaDB & native Windows Ollama
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 4. Run lightweight PostgreSQL-backed ingestion worker (--once drains claimable jobs & exits)
python -m app.worker --once
python -m app.worker
```

---

## Database & Alembic Migrations

Migration scripts live under [`../infrastructure/database/migrations/`](../infrastructure/database/migrations) as specified in [`../AGENTS.md`](../AGENTS.md), configured via [`alembic.ini`](alembic.ini) and reading `DATABASE_URL` dynamically from root `.env` via `Settings`:

```powershell
# Run from backend/ (with PostgreSQL container healthy)
alembic current
alembic history
alembic upgrade head
alembic check

# Or invoke from repository root:
.\backend\.venv\Scripts\alembic.exe -c backend\alembic.ini current
```

---

## Quality Checks & Tests

```powershell
cd backend
..\backend\.venv\Scripts\ruff.exe check app tests ..\infrastructure\database\migrations
..\backend\.venv\Scripts\mypy.exe app tests ..\infrastructure\database\migrations\env.py ..\infrastructure\database\migrations\versions\20261111_0002_auth_identity_rbac.py ..\infrastructure\database\migrations\versions\20261111_0003_org_project_workspaces.py ..\infrastructure\database\migrations\versions\20261111_0004_evidence_ingestion.py ..\infrastructure\database\migrations\versions\20261111_0005_source_integrations.py ..\infrastructure\database\migrations\versions\20261112_0006_evidence_chunks_and_fts.py ..\infrastructure\database\migrations\versions\20261112_0007_knowledge_reconstruction.py
..\backend\.venv\Scripts\pytest.exe -v
```

---

## Dependency Groups (`pyproject.toml`)

- **Core Runtime (`requirements.txt`)**: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `psycopg[binary]`, `alembic`, `httpx`, `python-dotenv`, `pyjwt`, `pwdlib[argon2]`, plus Phase 2.4A document/encryption packages `pymupdf`, `python-docx`, `python-multipart`, and `cryptography`.
- **Separated Optional Groups** *(deferred until subsequent phases)*:
  - `documents`: promoted into core dependencies in Phase 2.4A
  - `embeddings-rag`: `chromadb-client`
  - `integrations-security`: `cryptography` promoted in Phase 2.4A for at-rest upload encryption; reserve for future OAuth connectors
  - `worker`: lightweight PostgreSQL-backed worker utilities *(no Redis or Celery)*
  - `dev`: `pytest`, `ruff`, `mypy`
