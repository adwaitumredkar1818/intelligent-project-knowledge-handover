# The Handover — Full-Platform Architecture Audit
## Architecture, Code Quality & Module Dependency Analysis

---

## 1. System Architecture Overview

The Handover is designed as a modular knowledge reconstruction platform that ingests unstructured project artifacts (PDFs, DOCX, GitHub repositories, Jira issues, Slack discussions), extracts and normalizes textual content, indexes dense semantic vectors alongside full-text keyword indices, reconstructs structured knowledge records via local LLM reasoning, identifies cross-source relationships and dependencies, and prepares auditable handover packages.

```mermaid
flowchart TD
    subgraph ClientLayer ["Client Layer (Next.js 16.4.6 / React 19)"]
        UI_Landing["Landing & Marketing Views"]
        UI_Auth["Authentication Views"]
        UI_Workspace["Project Workspace (Overview, Team, Settings)"]
        UI_Evidence["Evidence Center (Sources, Library, Details)"]
        UI_Knowledge["Knowledge Intelligence (8 Domains)"]
        UI_Rel["Relationship Explorer (Graph & Timeline)"]
        UI_Context["LiveAppContext (Monolithic Client State)"]
        API_Client["API Client (Fetch Wrapper / LocalStorage Token)"]
    end

    subgraph APILayer ["Backend API Layer (FastAPI / Uvicorn)"]
        CORS["CORS & Request Correlation Middleware"]
        RateLimit["In-Memory Sliding Window Rate Limiter"]
        RouterAuth["/api/v1/auth (JWT, Argon2id, Refresh Cookie)"]
        RouterProjects["/api/v1/projects & /organisations"]
        RouterEvidence["/api/v1/projects/{id}/evidence"]
        RouterSources["/api/v1/integrations & /sources"]
        RouterRetrieval["/api/v1/projects/{id}/retrieval"]
        RouterKnowledge["/api/v1/projects/{id}/knowledge"]
        RouterRelationships["/api/v1/projects/{id}/relationships"]
    end

    subgraph ServiceLayer ["Domain Services & Business Logic"]
        AuthSvc["AuthService & RBAC Policy Engine"]
        StorageSvc["StorageService (Local Encrypted / Supabase Storage AES-256)"]
        ExtractSvc["DocumentExtractionService (PyMuPDF / OCR)"]
        EmbedSvc["EmbeddingService (nomic-embed-text)"]
        HybridRetSvc["HybridRetrievalService (PG FTS + Chroma RRF)"]
        ReconSvc["KnowledgeReconstructionService (Prompting & Grounding)"]
        RelCoord["RelationshipCoordinator (Entities, Relationships, Timeline)"]
        TokenCrypt["LocalTokenEncryptionService (AES-256-GCM / HKDF)"]
    end

    subgraph WorkerLayer ["Asynchronous Job Execution (worker.py)"]
        CompWorker["CompositeWorkerService (Sequential Polling)"]
        IngestWorker["IngestionWorkerService (Doc Extraction & OCR)"]
        SyncWorker["SourceSyncWorkerService (GitHub/Jira Sync)"]
        IndexWorker["IndexingWorkerService (Chunking & Vector Indexing)"]
        ReconWorker["ReconstructionWorkerService (Qwen3 8B Extraction)"]
        RelWorker["RelationshipWorkerService (Graph & Entity Linking)"]
    end

    subgraph PersistenceLayer ["Canonical Persistence & External Services"]
        PG[("PostgreSQL 17.11 (Canonical Store)
        42 Tables, RBAC, Jobs, Audit, FTS")]
        Chroma[("ChromaDB v2 HTTP Server
        Vector Embeddings")]
        Ollama["Local Ollama Runtime
        Qwen3 8B / GLM OCR / nomic-embed-text"]
        StorageBackend[("Object Storage
        Local AES Encrypted / Supabase Bucket")]
        ExternalSources["External APIs
        GitHub REST API / Jira OAuth 3LO / Slack")]
    end

    %% Wiring
    ClientLayer -->|HTTP / JSON| APILayer
    APILayer --> ServiceLayer
    CompWorker --> IngestWorker & SyncWorker & IndexWorker & ReconWorker & RelWorker
    WorkerLayer <-->|Claim Jobs FOR UPDATE SKIP LOCKED| PG
    ServiceLayer <--> PG
    ServiceLayer <--> Chroma
    ServiceLayer <--> Ollama
    ServiceLayer <--> StorageBackend
    SyncWorker <--> ExternalSources
```

---

## 2. Module Inventory & Responsibilities

### Backend Modules (`backend/app/`)

| Module | Core Files | Responsibility |
| :--- | :--- | :--- |
| **API Routers** | `app/api/routes/*.py` | 12 REST routers handling authentication, organizations, projects, evidence, sources, integrations, retrieval, knowledge, relationships, and health. |
| **Core & Security** | `app/core/` | Configuration (`pydantic-settings`), Argon2id hashing, JWT access token issuing/decoding, refresh token hashing, AES-256-GCM encryption primitives, rate limiting, and exception handlers. |
| **Database & Models** | `app/db/`, `app/models/` | SQLAlchemy 2.x declarative models for 42 tables; connection pool configuration via `psycopg` (binary); Alembic migration scripts. |
| **Repositories** | `app/repositories/` | Clean data access layer isolating SQL queries and transactions for users, roles, organizations, projects, evidence, chunks, jobs, knowledge items, relationships, and audit logs. |
| **Services** | `app/services/` | Domain logic orchestration: document extraction, OCR adapters, chunking, embedding generation, hybrid RRF search, LLM structured extraction, excerpt verification, entity resolution, and graph projection. |
| **Integrations** | `app/services/integrations/` | Connectors for GitHub (OAuth App/Fine-grained PAT), Jira (OAuth 2.0 3LO), and Slack; source access policy enforcement and token refresh. |
| **Background Worker** | `app/worker.py`, `app/services/*_worker.py` | Single lightweight Python process sequentially polling PostgreSQL-backed jobs using `SELECT ... FOR UPDATE SKIP LOCKED`. |

### Frontend Modules (`frontend/src/`)

| Module | Core Files | Responsibility |
| :--- | :--- | :--- |
| **App Router Pages** | `app/` | 27 static and dynamic route entrypoints including `/overview`, `/projects`, `/team`, `/evidence`, `/knowledge`, `/relationships`, `/verification`, `/handover`, `/login`, and `/signup`. |
| **State Management** | `context/LiveAppContext.tsx` | Monolithic React Context holding authentication, organization, project, team, source, evidence, modal, and toast states. |
| **Layout & Shell** | `components/layout/` | Persistent application shell containing `Sidebar`, `TopNav`, `AppLayout`, mobile drawer, and modal containers. |
| **Core Views** | `components/views/` | Main feature views: `OverviewView`, `ProjectsView`, `TeamMembersView`, `EvidenceCenterView`, `ConnectedSourcesView`, and `Phase2ModuleView`. |
| **Landing & Brand** | `components/landing/`, `components/brand/` | 15 marketing sections, SVG logos, brand design tokens, and the 2,136-line `OrganicScene` Canvas 3D particle visualization. |
| **UI Primitives** | `components/ui/` | Shared UI components (Button, Card, Badge, Modal, Tabs, Input, Toast). |
| **Duplicate Prototype** | `features/prototype/` | **5,992 lines** of parallel prototype code containing duplicate layouts, components, views, and hardcoded demo data. |
| **API Client** | `lib/api.ts` | Fetch wrapper with authorization headers, error unpacking, and unwrap utilities. |

---

## 3. Critical Request & Data Flows

### A. Document Upload, Extraction & Chunking Flow
1. User uploads a PDF/DOCX file via `POST /api/v1/projects/{id}/evidence/upload`.
2. `UploadService` validates MIME type, magic bytes, and file size constraints ($< 50\text{ MB}$, $< 200\text{ pages}$).
3. File is encrypted via AES-256-GCM envelope encryption and saved to `data/uploads` or private Supabase bucket.
4. An `EvidenceItem` is created in PostgreSQL with `processing_status = 'pending'`, and an `evidence_extraction` job is enqueued in `background_jobs`.
5. Background worker claims the job:
   - For PDFs: PyMuPDF extracts digital text page-by-page; pages with $< 40$ chars and images trigger Ollama GLM OCR.
   - For DOCXs: `python-docx` extracts structured headings, paragraphs, and tables.
6. Extracted text and page records are committed, and an `evidence_indexing` job is enqueued.
7. `IndexingWorkerService` chunks text into $1,100$-char overlapping chunks, generates 768-dim embeddings via `nomic-embed-text`, and stores vectors in ChromaDB.

### B. Knowledge Reconstruction Flow
1. User or worker triggers `POST /api/v1/projects/{id}/knowledge/reconstruct`.
2. `ReconstructionWorkerService` claims the job and partitions project chunks into bounded batches ($\le 6$ chunks, $\le 5,500$ chars).
3. Batches are dispatched to local Ollama running `qwen3:8b` with domain-specific structured JSON extraction prompts.
4. `KnowledgeCandidateValidator` validates all returned candidates against strict epistemic rules:
   - **`NO EVIDENCE -> NO CLAIM`**: Verbatim excerpt matching verifies that supporting text exists in the supplied chunk.
   - Rejection of ungrounded or speculative claims.
   - Deduplication via conservative SHA-256 fingerprinting.
5. Accepted items are persisted to `knowledge_items` with `epistemic_status = 'extracted_finding'` and verified provenance links in `knowledge_evidence_links`.

### C. Relationship Explorer Flow
1. `RelationshipCoordinator` reads extracted knowledge items and source evidence.
2. `IdentityResolutionService` resolves entity aliases and generates entity candidate matches.
3. `RelationshipDiscoveryService` projects structured relationships across 13 entity types.
4. `TimelineService` synthesizes a chronological timeline of project events with source timestamp precision.
5. `DependencyIntelligenceService` calculates direct and transitive dependency trees, identifying root blockers and circular dependency cycles without silent pruning.

---

## 4. Architectural Strengths

1. **Strict 3-Tier Layering & Separation of Concerns (Backend)**:
   - Routers only handle request parsing, authentication dependencies, and HTTP response serialization.
   - Business rules live exclusively in service classes (`AuthService`, `EvidenceService`, `HybridRetrievalService`).
   - SQL operations and transaction scopes are encapsulated in repositories (`UserRepository`, `EvidenceChunkRepository`).

2. **Epistemic Integrity & Grounding Guarantees**:
   - The platform strictly enforces a 4-tier separation: (1) Original source evidence, (2) Extracted findings, (3) AI-generated interpretations, and (4) Human-verified knowledge.
   - LLMs are never permitted to approve handovers, alter task status, or invent decisions without supporting excerpts.

3. **Fine-Grained Read-Time ACL Verification**:
   - External source permissions are preserved at ingestion.
   - Even after vector search in ChromaDB, the backend re-validates every candidate chunk against PostgreSQL source access policies before returning it to the client or supplying it to prompt context.

4. **Cryptographic Rigor**:
   - Platform authentication uses Argon2id with dummy verification against user-enumeration timing leaks.
   - Refresh tokens are hashed with SHA-256 and rotated with reuse detection.
   - External OAuth tokens are encrypted at rest with HKDF-derived keys and AES-256-GCM.

---

## 5. Architectural Weaknesses & Anti-Patterns

### 1. Desynchronization of Migration Branches
- The database schema on Supabase was upgraded to `0012_verification_center` from branch `feature/verification-center-backend`.
- The `main` branch was never merged with this migration, leaving `alembic_version` pointing to a missing revision file.
- **Consequence**: `alembic current` fails, breaking CI/CD schema verification and preventing any future migrations from being cleanly applied.

### 2. Massive Code Duplication in Frontend (`src/features/prototype/`)
- A complete parallel prototype application exists in `frontend/src/features/prototype/` containing 5,992 lines of redundant code, duplicate layouts, mock data stores (`demo-evidence.ts`, `demo-projects.ts`), and duplicate components.
- In addition, an untracked directory `figma-make-reference/` contains 11,623 lines of Vite/React code.
- **Consequence**: High maintenance overhead, developer confusion over canonical components, and bloated repository size.

### 3. Monolithic React Context (`LiveAppContext.tsx`)
- All application states (Auth, Orgs, Projects, Members, Sources, Evidence, Modals, Toasts) are combined into a single 698-line React context.
- Any update to a minor state (e.g. typing in search filter, modal toggle, toast timer) causes the entire context value to be recreated, triggering re-renders across all subscribed components (`Sidebar`, `TopNav`, `AppLayout`, and views).

### 4. Violation of ChromaDB Isolation Architecture (ADR 0005)
- ADR 0005 specifies that each project must have its own isolated ChromaDB collection (`th_project_{hash}`).
- Instead, the vector store implementation uses a single shared collection (`ipkrh_evidence_chunks_nomic_embed_text_v1`) and relies entirely on ChromaDB metadata filters.
- **Consequence**: High multi-tenant leakage risk if a filter clause is omitted or malformed, and index scalability bottlenecks as all projects share one index.

### 5. Single Threaded Sequential Background Worker Loop
- The worker executes 5 queues sequentially: `ingestion -> sync -> indexing -> reconstruction -> relationships`.
- Long-running OCR or LLM reconstruction jobs (which can take 1–3 minutes per document) completely block fast jobs like source syncing or chunk indexing.

---

## 6. Recommended Architectural Improvements

1. **Merge Verification Center Backend**: Merge `feature/verification-center-backend` into `main` to align Alembic revisions and make Verification Center models and routes canonical.
2. **Remove Dead Prototype Code**: Delete or archive `frontend/src/features/prototype/` and remove untracked `figma-make-reference/` from the active repository.
3. **Decompose Frontend Context**: Split `LiveAppContext` into 4 focused contexts or Zustand stores:
   - `AuthContext`: user, token, login, logout.
   - `WorkspaceContext`: active org, active project, org list, project list.
   - `EvidenceContext`: evidence list, metrics, selection, upload.
   - `UIContext`: modals, sidebar, toasts.
4. **Enforce Project-Isolated Chroma Collections**: Refactor `ChromaV2HttpVectorStore` to dynamically create and query project-specific collections matching ADR 0005.
5. **Decouple Worker Execution Queues**: Allow I/O-bound workers (sync, document fetch) and compute-bound workers (OCR, LLM) to poll concurrently or in separate process invocations.
