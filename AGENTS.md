# AGENTS.md — Permanent Project Governance & Engineering Instructions

This document defines mandatory project rules, architectural boundaries, and engineering standards for all contributors and AI coding agents working on the **Intelligent Project Knowledge Reconstruction & Handover Platform**.

---

## 1. Project Mission & Core Workflow

- **Objective**: Prevent critical organisational knowledge from being lost when employees leave or transition responsibilities by connecting authorised organisational sources and reconstructing fragmented project knowledge into structured, evidence-backed, human-reviewable information.
- **Core Workflow**: `CONNECT → RECONSTRUCT → VERIFY → REVIEW → HANDOVER`
- **Knowledge Categories to Identify**:
  1. Decisions and their rationale
  2. Technical and architectural knowledge
  3. Completed and unfinished work
  4. Responsibilities and ownership
  5. Dependencies
  6. Bugs, blockers and risks
  7. Operational procedures
  8. Historical discussions and context

---

## 2. Canonical Product Terminology

Always use these exact module names across code, UI labels, API contracts, and documentation:

1. **Project Workspace**
2. **Evidence Workspace**
3. **Knowledge Intelligence**
4. **Relationship Explorer**
5. **Verification Center**
6. **Handover Workspace**
7. **Project Knowledge Assistant**

---

## 3. Confirmed Technology Stack & Architectural Baseline

Do **not** silently replace any technology below. Any proposed alternative must be presented separately with technical justification and explicitly approved before implementation.

| Layer | Confirmed Technologies & Baseline Rules |
| :--- | :--- |
| **Frontend** | Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, Lucide Icons, React Flow (relationship visualisation) |
| **Backend** | Python 3.11, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic (migrations), Psycopg 3 (`psycopg`), HTTPX; separate lightweight Python worker process for async jobs (no Redis, Celery, or message broker in initial phase) |
| **Data & Retrieval** | PostgreSQL (canonical store, structured relationship tables, full-text search, and job records), ChromaDB (dedicated HTTP server mode via Docker Compose for semantic vector search), `nomic-embed-text` (embeddings) |
| **AI, OCR & RAG** | Ollama (local inference), Qwen3 8B (initial model to benchmark), `glm-ocr:latest` via local Ollama behind a replaceable backend OCR abstraction (do not introduce vLLM or another OCR runtime at this stage), hybrid RAG (ChromaDB semantic + PostgreSQL full-text search combined by backend retrieval layer) |
| **Document Processing** | PyMuPDF, `python-docx`, GLM OCR (`glm-ocr:latest` on Ollama) |
| **Integrations** | GitHub API and Jira API (initial priority alongside uploaded documents); Slack API kept strictly as an optional MVP integration gated by workspace authorisation, API scope review, and data-retention confirmation |
| **Infrastructure** | Docker Desktop, Docker Compose, Git, GitHub |
| **Auth & Security** | FastAPI-managed platform authentication (secure password hashing, short-lived JWT access tokens, `HttpOnly` refresh cookies never exposed to browser JS), separate OAuth 2.0 integrations for delegated per-user source access, Role-Based Access Control (RBAC) |

---

## 4. Architectural & Storage Rules

1. **PostgreSQL Is Canonical**: PostgreSQL is the single source of truth for all structured application data, source identities, access permissions, evidence metadata, extracted items, relationships, verification decisions, handovers, background job records, and audit logs.
2. **ChromaDB Is Secondary (HTTP Server Mode)**: ChromaDB runs as a dedicated HTTP service via Docker Compose and stores embeddings, searchable vectors, and retrieval metadata only. It must **never** be the sole storage location for evidence or project records and must remain rebuildable from PostgreSQL.
3. **PostgreSQL Relationships (No Graph DB)**: Knowledge relationships must initially be implemented as structured relational records in PostgreSQL. Do **not** introduce a separate graph database (e.g. Neo4j).
4. **Lightweight Worker & PostgreSQL Job Tracking**: Long-running ingestion, OCR, embedding, and AI reconstruction jobs run in a separate lightweight Python worker process backed by PostgreSQL job records (status, retry count, failure reporting). Keep the worker interface replaceable; do **not** introduce Redis, Celery, or another message broker during the initial infrastructure phase.
5. **Hybrid Retrieval Architecture**: Implement retrieval by combining ChromaDB semantic vector search (`nomic-embed-text`) with PostgreSQL full-text search for keyword/identifier matching in a dedicated backend retrieval layer. Benchmark retrieval quality using realistic project evidence before setting numerical performance thresholds.
6. **Mandatory Evidence Retention Metadata**: Every persisted evidence item must retain:
   - Source platform
   - Original source identifier
   - Source URL (where available)
   - Author or owner (where available)
   - Timestamp (original source timestamp)
   - Extraction timestamp
   - Content hash or version information (where appropriate)
7. **Modular Backend Separation**: Maintain strict separation across these 11 backend modules:
   1. API routes
   2. Authentication and authorisation
   3. Source integrations
   4. Document ingestion
   5. Extraction and processing
   6. Embedding and retrieval
   7. Knowledge reconstruction
   8. Relationship management
   9. Verification
   10. Handover
   11. AI assistant

---

## 5. AI, RAG & Data Integrity Rules

1. **LLM Is Not Source of Truth**: All important extracted findings and assistant answers must be traceable to supporting source evidence.
2. **Mandatory AI Safeguards**: Implement evidence-grounded extraction, source attribution, uncertainty handling, conflict detection, missing-information detection, human review, and pre-retrieval permission filtering.
3. **Explicit LLM Prohibitions**: The LLM must **never** independently:
   - Approve handovers
   - Decide official task status
   - Override source permissions
   - Resolve conflicting facts without evidence
   - Invent project decisions or responsibilities
4. **Handover Approval Governance**: A **designated human reviewer** must approve a handover package before final sharing. An incoming assignee may acknowledge receipt, which **cannot** substitute for reviewer approval.
5. **Uncertainty Disclosure**: When supporting evidence is absent, incomplete, or conflicting, the system must explicitly communicate uncertainty rather than guessing.
6. **Embedding Consistency**: Always use the exact same embedding model (`nomic-embed-text`) for both document indexing and query retrieval.
7. **Replaceable OCR Abstraction**: Expose OCR (`glm-ocr:latest` on Ollama) behind a clean backend service abstraction so it can be swapped independently if future benchmarks warrant another runtime.
8. **Four-Tier Epistemic Separation**: Data models, APIs, and UI must explicitly distinguish:
   - **Original source evidence**
   - **Extracted information**
   - **AI-generated interpretation**
   - **Human-verified knowledge**
9. **Zero Fabrication**: Never represent fabricated or synthetic data as real organisational evidence. Any synthetic test fixtures must be clearly labelled as synthetic and isolated from real connected data (never display fabricated GitHub repos, Jira issues, Slack threads, or user evidence as real connected sources).

---

## 6. Security Requirements

- Never hardcode API keys, passwords, tokens, or private secrets anywhere in source files or documentation.
- Keep all secrets strictly in backend environment variables; never commit `.env` files.
- Never expose private credentials, source tokens, or refresh tokens through frontend code, browser JavaScript, or `NEXT_PUBLIC_*` environment variables.
- Keep **platform authentication** (FastAPI-managed credentials, password hashing, short-lived JWT access tokens, `HttpOnly` refresh cookies) strictly separate from **third-party source OAuth 2.0 integrations** (GitHub, Jira, Slack).
- Prefer **delegated, per-user authorisation** for connected sources wherever supported; preserve source identities and access permissions in PostgreSQL; never assume connecting one user's account grants access to every project member.
- Enforce authentication, RBAC, and source-level permissions strictly on the backend **before** evidence enters retrieval context or an LLM prompt.
- Store uploaded files in **private storage outside publicly served frontend directories** with strict access controls, file validation, opaque server-generated filenames, and encryption at rest.
- Maintain immutable audit logs for sensitive and state-changing actions (auth events, connector changes, uploads, verification decisions, handover approvals/acknowledgments, permission denials).

---

## 7. Engineering & Quality Standards

- Write modular, maintainable code following clear naming conventions.
- Require strict type annotations (TypeScript strict mode on frontend; Python type hints + Pydantic models on backend).
- Validate all API requests and responses explicitly via Pydantic schemas.
- Handle errors explicitly—never swallow failures silently, especially in ingestion, OCR, retrieval, worker, or auth paths.
- Write meaningful unit and integration tests for business logic, permission enforcement, and RAG grounding.
- Document every new or modified environment variable in `.env.example` and `documentation/development/environment-setup.md`, distinguishing mandatory, optional integration, and deployment-specific variables.
- Avoid unnecessary dependencies, duplicate implementations, or unrelated modifications outside task scope.
- Design every feature across all four dimensions: **Frontend**, **Backend**, **Database**, and **Security**.
- **Verification Discipline**: Never claim a feature is implemented or working until its tests have been executed and observed passing.
- **Documentation Discipline**: Clearly distinguish **Confirmed Design Decisions** from **Proposed Implementation Details** in all architecture and development documentation.

---

## 8. Repository Structure & Phase Discipline

```text
frontend/                  # Next.js, React, TypeScript, Tailwind, shadcn/ui, React Flow
backend/                   # Python 3.11, FastAPI modular backend & lightweight worker
infrastructure/
  docker/                  # Container definitions and Docker Compose setup
  database/                # PostgreSQL initialisation and Alembic migration scripts
documentation/
  architecture/            # System, data flow, DB, AI/RAG, and security specifications
  api/                     # API contracts and schema specifications
  development/             # Roadmap and environment setup guides
scripts/                   # Utility, indexing, and verification scripts
```

- Follow the phased sequence in [`documentation/development/development-roadmap.md`](documentation/development/development-roadmap.md).
- Do not generate speculative scaffolding, demo data, or unapproved infrastructure beyond the active phase gate.
