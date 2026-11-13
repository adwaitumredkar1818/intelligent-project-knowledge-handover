# The Handover — Master Engineering Audit
## Executive Summary & Full-Platform Assessment

- **Product Name**: The Handover (Intelligent Project Knowledge Reconstruction & Handover Platform)
- **Repository Root**: `E:\Projects\Intelligent Project Knowledge Reconstruction & Handover Platform`
- **Audit Date**: 2026-11-13
- **Git Branch**: `main`
- **Current Baseline Commit**: `2903bf2` ("fix(frontend): import useEffect in CreateProjectModal")
- **Audit Scope**: Full-Platform (Frontend, Backend, Database, AI Pipeline, Security, Infrastructure, Testing, DX)
- **Execution Mode**: **AUDIT ONLY** (No code modified, no schemas altered, no migrations executed)

---

## 1. Executive Summary

This master engineering audit was conducted across all subsystems of **The Handover** platform, inspecting source code, configuration manifests, database schemas, background worker pipelines, AI orchestration services, and test suites. Live, non-invasive performance measurements and schema inspections were executed against the running backend, database, and build tooling.

### Current Engineering Condition

The Handover possesses an exceptionally strong architectural foundation in its backend services, domain models, and data integrity safeguards:
- **Strict Epistemic Integrity**: The knowledge reconstruction engine strictly enforces `NO EVIDENCE -> NO CLAIM`, requiring verbatim excerpt validation and rejecting ungrounded LLM claims.
- **Robust RBAC & ACLs**: Project membership does not equal source access; read-time source ACL policy enforcement prevents unauthorized retrieval.
- **Enterprise-Grade Cryptography**: External OAuth credentials and uploaded documents are encrypted with AES-256-GCM envelope encryption and HKDF key derivation.
- **Clean 3-Tier Layering**: Backend modules strictly adhere to Router $\to$ Service $\to$ Repository/Model patterns with full Pydantic v2 validation.

However, the audit revealed **critical operational blockers, database desynchronizations, frontend performance traps, and architectural drift** that jeopardize production stability, latency, and multi-tenant security if left unaddressed.

---

## 2. Platform Health Scorecard

| Domain | Rating | Condition Summary |
| :--- | :---: | :--- |
| **1. Architecture & Code Structure** | **B+** | Clean 3-tier backend and well-separated services. Compromised by 5,992 lines of duplicate prototype code in `frontend/src/features/prototype/` and desynchronized branch migrations. |
| **2. Frontend Performance** | **C** | Monolithic `LiveAppContext` causes global cascading re-renders; selecting any evidence item triggers 4 simultaneous API re-fetches. `OrganicScene` animation loops run continuously even off-screen. |
| **3. Backend & API Performance** | **B** | Pure in-memory API routes respond in 5–10 ms. However, remote Supabase cross-region queries introduce a 1.3s–3.3s latency penalty. Sequential worker loop starves jobs during long OCR/LLM tasks. |
| **4. Database & Data Architecture** | **C-** | **Critical**: Live database is on Alembic revision `0012_verification_center`, but revision file is missing on `main` (branch desync). All 42 public tables lack Row Level Security (RLS). 63 unindexed foreign keys exist. |
| **5. AI & Knowledge Pipeline** | **B+** | High-precision extraction with conservative deduplication and excerpt verification. Weakness: All projects share a single ChromaDB collection, violating ADR 0005. Single inference lock limits throughput. |
| **6. Security & Authorization** | **B** | Solid Argon2id, JWT, and encrypted storage. Vulnerabilities: Frontend stores access token in `localStorage` without automatic refresh rotation; lack of RLS on Supabase exposes tables if PostgREST is enabled. |
| **7. Infrastructure & Scalability** | **B-** | Clean Docker Compose setup for local development. Scalability bottleneck: Sequential worker processes one job at a time; cross-continental Supabase pooler connection handshakes take 5–8 seconds. |
| **8. Testing & Reliability** | **D+** | Over 140 comprehensive tests exist, but `test_live_postgres.py` has a Python `SyntaxError: unmatched ')'` breaking full test collection; `test_db_lifecycle.py` fails due to stale Alembic head assertion. 0 frontend tests. |
| **9. Observability & Developer Experience** | **B-** | Excellent structured logging and request correlation IDs. Lacks automated CI test sharding, separating live LLM tests from fast unit tests. |

---

## 3. Most Serious Risks (Critical & High)

1. **Alembic Migration Desynchronization (CRITICAL — Reliability/DB)**:
   - The live database `alembic_version` table is set to `0012_verification_center`.
   - On the `main` branch, migration files stop at `0011_relationship_explorer`.
   - Commit `0301ee5ada` containing `0012_verification_center` was committed to `feature/verification-center-backend` but never merged to `main`.
   - Running `alembic current` or `alembic upgrade head` on `main` immediately fails with `Can't locate revision identified by '0012_verification_center'`.

2. **Row Level Security (RLS) Disabled on All 42 Tables (CRITICAL — Security/DB)**:
   - On the managed Supabase PostgreSQL instance, **0 out of 42 public tables have RLS enabled** (`RLS=False, ForceRLS=False`).
   - If the Supabase PostgREST Data API is active or publicly exposed, any client with an anon key could bypass backend access controls and query or mutate platform data.

3. **ChromaDB Multi-Tenant Isolation Violation (HIGH — Security/AI)**:
   - ADR 0005 strictly mandates *"strictly one project-isolated collection per Handover project"*.
   - The implementation in `ChromaV2HttpVectorStore` routes all evidence chunks across all organisations and projects into a single shared collection (`ipkrh_evidence_chunks_nomic_embed_text_v1`), relying solely on metadata query filters.

4. **Frontend Cascading API Fetch Waterfall on Item Select (HIGH — Performance)**:
   - In `LiveAppContext.tsx`, `refreshEvidence` includes `selectedEvidenceId` in its dependency array.
   - When a user clicks any evidence item, `refreshEvidence` is recreated, triggering a global `useEffect` that re-fetches Project Overview, Team Members, Source Mappings, Evidence List, and Evidence Metrics simultaneously.

5. **Test Suite Collection Blocker (HIGH — Reliability/Testing)**:
   - `backend/tests/test_live_postgres.py` contains a fatal syntax error on line 49 (`unmatched ')'`), preventing `pytest` from collecting or running the test suite when executing `pytest backend/tests`.
   - In addition, `test_alembic_configuration_and_revisions` fails because it asserts heads is `["0010_knowledge_domains"]` while `0011_relationship_explorer` is now present.

6. **Frontend Authentication Token in `localStorage` Without Refresh Loop (MEDIUM/HIGH — Security)**:
   - The frontend stores JWT access tokens in `localStorage`.
   - Frontend `fetch` does not set `credentials: "include"`, preventing `HttpOnly` refresh cookies from being sent across origins.
   - The client has no automatic token refresh interceptor; after the 15-minute access token expires, user requests fail with 401 errors.

7. **63 Unindexed Foreign Keys in PostgreSQL Schema (MEDIUM/HIGH — Performance/DB)**:
   - PostgreSQL schema analysis revealed 63 unindexed foreign keys across 20 tables. This causes sequential table scans during foreign key joins and `ON DELETE CASCADE` / `ON DELETE SET NULL` operations.

8. **4 Concurrent Continuous Canvas Animation Loops in `OrganicScene` (MEDIUM — Performance)**:
   - The landing page mounts 4 instances of `OrganicScene`.
   - `OrganicScene.tsx` reschedules `requestAnimationFrame` continuously on every tick, even when `visible === false` (off-screen), consuming unnecessary CPU/GPU cycles.

---

## 4. Top 10 Prioritized Recommended Optimizations

| Priority | ID | Domain | Recommendation | Severity | Effort | Risk |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: |
| **1** | `ISSUE-01` | **Database** | Reconcile Alembic migration history by merging `0012_verification_center` from `feature/verification-center-backend` into `main`. | **Critical** | Small | Low |
| **2** | `ISSUE-02` | **Security** | Enable Row Level Security (RLS) on all 42 public tables in Supabase and revoke public PostgREST API access to ensure backend-only data access. | **Critical** | Medium | Medium |
| **3** | `ISSUE-03` | **Testing** | Fix `SyntaxError: unmatched ')'` on line 49 in `test_live_postgres.py` and update `test_alembic_configuration_and_revisions` head assertion to `0011`/`0012`. | **High** | Small | Low |
| **4** | `ISSUE-04` | **AI/Vector** | Refactor `ChromaV2HttpVectorStore` to enforce dedicated project collections per ADR 0005 (`th_proj_{hash}`), guaranteeing true multi-tenant vector isolation. | **High** | Medium | Medium |
| **5** | `ISSUE-05` | **Frontend** | Decouple `selectedEvidenceId` from `refreshEvidence` deps in `LiveAppContext.tsx` to eliminate the 5-endpoint cascading fetch waterfall on click. | **High** | Small | Low |
| **6** | `ISSUE-06` | **Database** | Create indexes on all 63 unindexed foreign keys in PostgreSQL to prevent table-scan locks during cascaded updates and joins. | **High** | Medium | Low |
| **7** | `ISSUE-07` | **Auth/Sec** | Update frontend API client (`api.ts`) to include `credentials: "include"` and implement an automatic 401 token refresh interceptor using `/api/v1/auth/refresh`. | **High** | Medium | Low |
| **8** | `ISSUE-08` | **Frontend** | Update `brand/OrganicScene.tsx` to pause `requestAnimationFrame` entirely when the canvas is off-screen via `IntersectionObserver`. | **Medium** | Small | Low |
| **9** | `ISSUE-09` | **Worker/Scale** | Split sequential worker queues into distinct task workers (or introduce async concurrency) so document ingestion/sync is not blocked by multi-minute LLM runs. | **Medium** | Medium | Medium |
| **10** | `ISSUE-10` | **Testing/DX** | Add pytest markers (`@pytest.mark.live_llm`, `@pytest.mark.unit`) to separate sub-second unit tests from multi-minute Ollama inference benchmarks. | **Medium** | Small | Low |

---

## 5. Audit Methodology & Evidence Summary

### Verified Findings (Observed & Measured)
- **Database Migration Desync**: Confirmed via live database query `SELECT version_num FROM alembic_version` returning `('0012_verification_center',)` and Git branch inspection showing commit `0301ee5ada` on `origin/feature/verification-center-backend`.
- **Database RLS State**: Verified via `pg_class` query showing `RLS=False` across all 42 tables.
- **Unindexed Foreign Keys**: Cataloged 63 foreign keys lacking leading index columns via `pg_constraint` catalog join.
- **Syntax Error in Test**: Reproduced via `pytest backend/tests --collect-only` raising `SyntaxError: unmatched ')'` in `test_live_postgres.py:49`.
- **Alembic Test Failure**: Reproduced in `test_db_lifecycle.py::test_alembic_configuration_and_revisions` asserting `0010_knowledge_domains` instead of `0011_relationship_explorer`.
- **Live Endpoint Latency**: Measured 20 iterations per endpoint against the live server:
  - `GET /health` (in-memory): avg 10.43 ms, p50 5.89 ms, p95 34.18 ms.
  - `GET /health/ready` (Supabase cross-region check): avg 3,355.91 ms, p50 1,810.03 ms, p95 8,846.38 ms.
- **Frontend Build & Bundle**: Measured via `next build` generating 27 static pages, 56 static assets totaling 1.83 MB, with the primary JS chunk measuring 471.2 KB.
- **Code Duplication**: Measured 5,992 lines of duplicate code in `frontend/src/features/prototype/` and 11,623 lines in untracked `figma-make-reference/`.

### Potential Risks Requiring Further Validation
- **Supabase PostgREST Exposure**: Whether the PostgREST API schema is enabled for `public` in the Supabase management console (safe read-only SQL inspection showed RLS is false, but dashboard settings were not directly queryable via SQL).
- **GPU VRAM Contention under High Concurrency**: While `_OLLAMA_INFERENCE_LOCK` prevents intra-process collision, multi-worker processes on the same machine could contend for Ollama VRAM.

### Architectural Recommendations
- Migrate from monolithic `LiveAppContext` to domain-specific contexts or Zustand stores (Auth, Project, Evidence, UI).
- Separate the worker into an I/O worker (sync, ingestion, indexing) and a compute worker (OCR, LLM reconstruction).
- Deploy Supabase database and backend in the same cloud region to eliminate the 1.5s–3.0s cross-continental network latency.

---

## 6. Audit Deliverables Directory Structure

All 11 comprehensive audit documents have been generated in `docs/engineering-audit/`:

1. [`engineering-audit-summary.md`](./engineering-audit-summary.md) — Master summary, health scorecard, and executive assessment.
2. [`architecture-audit.md`](./architecture-audit.md) — Full platform architecture, module dependency map, diagrams, and structural evaluation.
3. [`frontend-performance-audit.md`](./frontend-performance-audit.md) — Next.js bundle sizes, re-render waterfalls, canvas overhead, and Core Web Vitals.
4. [`backend-performance-audit.md`](./backend-performance-audit.md) — API latency benchmarks (p50/p95/p99), async execution, N+1 queries, and serialization.
5. [`database-audit.md`](./database-audit.md) — PostgreSQL schema, 63 unindexed foreign keys, RLS security, Alembic migration desync, and ChromaDB audit.
6. [`ai-pipeline-audit.md`](./ai-pipeline-audit.md) — OCR, embeddings, LLM orchestration, grounding verification (`NO EVIDENCE -> NO CLAIM`), and benchmarks.
7. [`security-audit.md`](./security-audit.md) — Auth, RBAC, token encryption, CSRF/CORS, SSRF, prompt injection, and threat modeling.
8. [`infrastructure-scalability-audit.md`](./infrastructure-scalability-audit.md) — Docker, worker queue architecture, VRAM bounds, and scaling limitations.
9. [`testing-reliability-audit.md`](./testing-reliability-audit.md) — Automated test coverage, syntax error blocker, failure analysis, and testing strategy.
10. [`optimization-issue-register.md`](./optimization-issue-register.md) — Comprehensive, prioritized issue register across all domains.
11. [`optimization-roadmap.md`](./optimization-roadmap.md) — Phased, step-by-step engineering remediation plan.
