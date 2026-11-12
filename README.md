# Intelligent Project Knowledge Reconstruction & Handover Platform

An intelligent, evidence-grounded platform that prevents critical organisational knowledge from being lost when employees leave or transition responsibilities. It connects authorised organisational sources and documents, reconstructs fragmented knowledge into structured records with full provenance, surfaces conflicts and gaps, supports human verification, and produces auditable handover packages.

> **Repository Status:** Phase 2.6 (AI Knowledge Reconstruction & Structured Intelligence Extraction Complete) — Docker infrastructure (**PostgreSQL** and **ChromaDB**), native Windows **Ollama** readiness, the Next.js TypeScript runtime (`frontend/`), the FastAPI backend foundation (`backend/app/`, `infrastructure/database/migrations/`), platform authentication & RBAC (`0002_auth_identity_rbac`), multi-tenant organisations & project workspaces (`0003_org_project_workspaces`), encrypted PDF/DOCX document ingestion & GLM OCR (`0004_evidence_ingestion`), delegated per-user GitHub & Jira OAuth 2.0 connectors & sync execution (`0005_source_integrations`), chunking, PG `TSVECTOR`/`GIN` full-text search, `nomic-embed-text` (768-dim) embeddings, ChromaDB HTTP v2 secondary vector indexing, `IndexingWorkerService`, and permission-filtered hybrid search/reindex APIs (`0006_evidence_chunks_and_fts`), and replaceable `StructuredLLMClient` (`OllamaLLMClient` / `qwen3:8b` with `OLLAMA_LLM_THINK=false`), 6-category `NO EVIDENCE -> NO CLAIM` knowledge extraction, conservative corroboration deduplication, staleness invalidation, `ReconstructionWorkerService` (`CompositeWorkerService`), and ACL-enforced `/knowledge/*` endpoints (`0007_knowledge_reconstruction`) are implemented and verified. Knowledge relationships, verification review workflows, handover generation, and assistant synthesis belong to subsequent phases.

---

## Core Workflow

```text
CONNECT  ──▶  RECONSTRUCT  ──▶  VERIFY  ──▶  REVIEW  ──▶  HANDOVER
```

1. **CONNECT**: Authorise and ingest project records from GitHub, Jira, Slack (subject to feasibility and authorised access), and uploaded documents (PDF, DOCX, scanned documents).
2. **RECONSTRUCT**: Persist canonical evidence in PostgreSQL, index chunks in ChromaDB (`nomic-embed-text`), and perform evidence-grounded extraction (Ollama + Qwen3 8B) and relationship mapping.
3. **VERIFY**: Run automated consistency, conflict, attribution, and missing-information checks across sources.
4. **REVIEW**: Enable authorised human reviewers in the **Verification Center** to inspect evidence, resolve discrepancies, and promote findings to **Human-Verified Knowledge**.
5. **HANDOVER**: Assemble, review, and human-approve structured handover packages in the **Handover Workspace**, backed by cited evidence and explicit risk/uncertainty records.

---

## Knowledge Categories

The platform structures reconstructed project knowledge across eight core domains:

- Decisions and their rationale
- Technical and architectural knowledge
- Completed and unfinished work
- Responsibilities and ownership
- Dependencies
- Bugs, blockers and risks
- Operational procedures
- Historical discussions and context

---

## Product Modules

| Module | Purpose |
| :--- | :--- |
| **Project Workspace** | Project lifecycle setup, source connection management, member roles, and handover overview |
| **Evidence Workspace** | Canonical view of ingested source records, uploaded documents, OCR outputs, and source metadata |
| **Knowledge Intelligence** | Evidence-backed extracted knowledge structured across the eight project knowledge domains |
| **Relationship Explorer** | Interactive visualisation (React Flow) of PostgreSQL-stored dependencies, ownership, and links |
| **Verification Center** | Human review queue for conflicts, missing information, uncertainty flags, and evidence verification |
| **Handover Workspace** | Structured handover package compilation, readiness checklists, ownership transfer, and human sign-off |
| **Project Knowledge Assistant** | Permission-filtered hybrid RAG assistant with source citations and explicit uncertainty reporting |

---

## Confirmed Technology Stack

- **Frontend**: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, Lucide Icons, React Flow
- **Backend**: Python 3.11, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, Psycopg 3, HTTPX, lightweight Python worker
- **Data**: PostgreSQL (canonical store, FTS, relationships, job queue), ChromaDB (HTTP server mode), `nomic-embed-text` (embeddings)
- **AI & Document Processing**: Ollama (native host: `qwen3:8b`, `nomic-embed-text`, `glm-ocr:latest`), PyMuPDF, `python-docx`, hybrid RAG
- **Integrations**: GitHub API, Jira API, Slack API (optional MVP gated by workspace auth, scopes & retention)
- **Infrastructure & Security**: Docker Desktop, Docker Compose, Git, GitHub, FastAPI-managed auth (JWT + `HttpOnly` refresh cookies), delegated source OAuth 2.0, RBAC

---

## Repository Structure

```text
.
├── frontend/                   # Next.js / React / TypeScript / Tailwind / shadcn-compatible shell (Phase 1.2 ready)
├── backend/                    # FastAPI backend (`app/`), auth/RBAC, workspaces, uploads, GitHub/Jira integrations, chunking/hybrid retrieval & composite worker (`worker.py`)
├── infrastructure/
│   ├── docker/                 # Docker Compose configuration (PostgreSQL & ChromaDB active)
│   └── database/               # Alembic migrations (`0001` baseline .. `0006` chunks/FTS, `0007` knowledge reconstruction)
├── documentation/
│   ├── architecture/           # System, data flow, database, AI/RAG, and security specs
│   ├── api/                    # API conventions & implemented health, auth, workspace, evidence, integration & retrieval endpoints
│   └── development/            # Environment setup, integration readiness, and phased roadmap
├── scripts/                    # Operational and evaluation scripts (planned Phase 1.3+)
├── .env.example                # Documented environment variable template
├── .gitignore                  # Git exclusion rules for secrets, venvs, caches, and build artefacts
├── AGENTS.md                   # Permanent project rules and engineering instructions
└── README.md                   # Project overview and documentation index
```

---

## Documentation Index

- **Governance**: [`AGENTS.md`](AGENTS.md)
- **Architecture**:
  - [`documentation/architecture/system-architecture.md`](documentation/architecture/system-architecture.md)
  - [`documentation/architecture/data-flow.md`](documentation/architecture/data-flow.md)
  - [`documentation/architecture/database-design.md`](documentation/architecture/database-design.md)
  - [`documentation/architecture/ai-rag-architecture.md`](documentation/architecture/ai-rag-architecture.md)
  - [`documentation/architecture/security-architecture.md`](documentation/architecture/security-architecture.md)
- **API**:
  - [`documentation/api/api-conventions.md`](documentation/api/api-conventions.md)
- **Development**:
  - [`documentation/development/environment-setup.md`](documentation/development/environment-setup.md)
  - [`documentation/development/integration-readiness.md`](documentation/development/integration-readiness.md)
  - [`documentation/development/development-roadmap.md`](documentation/development/development-roadmap.md)

---

## Local Development Quickstart (Phase 2.6)

### 1. Environment Configuration
Copy [`.env.example`](.env.example) to `.env` and populate strong local secrets (`POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`, `FILE_ENCRYPTION_KEY`). Keep optional external integrations disabled (`*_ENABLED=false`) until needed, and **never commit `.env`**.

### 2. Start & Stop Local Infrastructure (PostgreSQL & ChromaDB)
```powershell
# Start PostgreSQL and ChromaDB (Docker Desktop running)
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml up -d

# Inspect health and logs
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml ps
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml logs -f postgres chromadb

# Stop safely without deleting named volumes (never use `down -v` normally)
docker compose --env-file .env -f infrastructure/docker/docker-compose.yml down
```

### 3. Backend FastAPI & Alembic (`backend/`)
```powershell
py -3.11 -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
cd backend
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Frontend Next.js Environment (`frontend/`)
```powershell
cd frontend
npm install
npm run typecheck
npm run lint
npm run build
npm run dev
```

For full details—including native Windows Ollama verification (`qwen3:8b`, `glm-ocr:latest`, `nomic-embed-text`), Docker `host.docker.internal` networking, backup/restore procedures, and optional backend dependency groups—see [`documentation/development/environment-setup.md`](documentation/development/environment-setup.md), [`backend/README.md`](backend/README.md), and [`frontend/README.md`](frontend/README.md).
