# The Handover — Optimization Issue Register
## Consolidated Engineering Findings, Severity Rankings & Remediation Specifications

---

## 1. Issue Register Overview

This register consolidates all verified engineering findings across Architecture, Frontend, Backend, Database, AI Pipeline, Security, Infrastructure, and Testing.

Issues are ranked by:
1. **Security & Data Integrity Risk**
2. **Reliability & Correctness**
3. **Performance Impact**
4. **AI Accuracy & Inference Efficiency**
5. **Scalability & Concurrency**
6. **Maintainability & Developer Experience**

---

## 2. Master Issue Table

| ID | Domain | Severity | Effort | Risk | Finding & Impact | Recommendation |
| :---: | :--- | :---: | :---: | :---: | :--- | :--- |
| **`ISS-01`** | **Database / Reliability** | **Critical** | Small | Low | **Alembic Migration History Desynchronization**: Live DB has `0012_verification_center`, but `main` only has migrations up to `0011`. `alembic current` crashes. | Merge commit `0301ee5ada` (`feature/verification-center-backend`) into `main` to align Alembic versions. |
| **`ISS-02`** | **Security / DB** | **Critical** | Medium | Medium | **Row Level Security (RLS) Disabled on All 42 Tables**: All public tables have `RLS=False` on Supabase, risking direct PostgREST data exposure. | Revoke public schema usage from `anon`/`authenticated` roles and enable RLS on all 42 base tables. |
| **`ISS-03`** | **Testing / Reliability** | **High** | Small | Low | **SyntaxError Blocker in `test_live_postgres.py:49`**: Unmatched `)` breaks `pytest` test collection across the entire test suite. | Delete unmatched `)` on line 49 in `backend/tests/test_live_postgres.py`. |
| **`ISS-04`** | **AI / Security** | **High** | Medium | Medium | **Violation of ADR 0005 (ChromaDB Project Isolation)**: All projects share a single global Chroma collection, creating cross-tenant leakage risks. | Refactor `ChromaV2HttpVectorStore` to create and query dedicated project collections (`th_proj_{hash}`). |
| **`ISS-05`** | **Frontend Performance** | **High** | Small | Low | **Evidence Selection Network Waterfall**: Selecting an evidence item re-fetches Overview, Members, Sources, Evidence, and Metrics simultaneously. | Remove `selectedEvidenceId` from `refreshEvidence` dependencies in `LiveAppContext.tsx`. |
| **`ISS-06`** | **Database Performance** | **High** | Medium | Low | **63 Unindexed Foreign Keys in PostgreSQL**: Missing indexes cause full sequential table scans on cascaded deletes and joins. | Add migration creating b-tree indexes on all 63 unindexed foreign key columns. |
| **`ISS-07`** | **Auth / Frontend** | **High** | Medium | Low | **JWT Stored in `localStorage` Without Automatic Refresh**: XSS vulnerability; missing `credentials: "include"` breaks cookie refresh rotation. | Add `credentials: "include"` to `api.ts`, store access token in memory, and implement 401 refresh interceptor. |
| **`ISS-08`** | **Testing** | **Medium** | Small | Low | **Alembic Test Assertion Failure in `test_db_lifecycle.py`**: Hardcoded assertion asserts `0010_knowledge_domains` instead of `0011`. | Update assertion in `test_db_lifecycle.py:121` to include `0011_relationship_explorer`. |
| **`ISS-09`** | **Frontend Performance** | **Medium** | Small | Low | **Continuous Canvas Animation in `OrganicScene`**: `requestAnimationFrame` loops 60 FPS even when scrolled completely off-screen. | Cancel animation loop when `visible === false` in `IntersectionObserver` callback in `OrganicScene.tsx`. |
| **`ISS-10`** | **Maintainability** | **Medium** | Medium | Low | **5,992 Lines of Redundant Prototype Code**: Parallel mock code in `frontend/src/features/prototype/` bloats repo and causes maintenance confusion. | Remove `frontend/src/features/prototype/` and archive old mockup assets. |
| **`ISS-11`** | **Worker / Concurrency** | **Medium** | Medium | Medium | **Single-Threaded Sequential Worker Starvation**: Long OCR/LLM jobs block quick source sync and chunk indexing tasks. | Split worker loop into concurrent workers or run independent I/O and Compute worker processes. |
| **`ISS-12`** | **AI Efficiency** | **Medium** | Medium | Low | **Absence of Embedding Caching**: Identical chunks re-generate embeddings via Ollama on every re-indexing pass. | Implement a PostgreSQL-backed content-hash embedding cache table (`sha256(chunk) -> vector`). |
| **`ISS-13`** | **Frontend / DX** | **Medium** | Small | Low | **`typescript.ignoreBuildErrors: true` in `next.config.ts`**: Bypasses compiler type validation during `next build`. | Remove `ignoreBuildErrors: true` from `next.config.ts`. |
| **`ISS-14`** | **Backend Performance** | **Medium** | Small | Low | **In-Memory Job Filtering in `has_active_source_sync_job`**: Loads all active jobs into Python to check `mapping_id`. | Replace with native PostgreSQL JSON query: `WHERE payload_json->>'mapping_id' = :id`. |
| **`ISS-15`** | **Backend Performance** | **Medium** | Medium | Low | **Missing Pagination on Evidence & Relationship APIs**: Large projects will return unbounded multi-megabyte payloads. | Add `limit` and `cursor` pagination parameters to evidence and relationship endpoints. |
| **`ISS-16`** | **App Security** | **Low** | Medium | Low | **In-Memory Rate Limiter Not Distributed**: Rate limits reset on process reload and do not protect multi-container deployments. | Back rate limiter with PostgreSQL unlogged table or reverse-proxy gateway. |
| **`ISS-17`** | **Frontend Architecture** | **Low** | Large | Medium | **Monolithic `LiveAppContext` Re-render Overhead**: 30+ states in one context trigger global component re-renders. | Decompose into granular slices: `AuthContext`, `ProjectContext`, `EvidenceContext`, and `UIContext`. |
| **`ISS-18`** | **Testing / DX** | **Low** | Small | Low | **Mixed Fast and Slow Tests Without Pytest Markers**: Running `pytest` triggers 5-minute live LLM runs without markers. | Configure `@pytest.mark.live_ai` and `@pytest.mark.unit` markers in `pyproject.toml`. |

---

## 3. Quick Wins vs. Architectural Changes

### Quick Wins ($< 2\text{ hours each}$, Immediate Impact)
1. **Fix `test_live_postgres.py` Syntax Error (`ISS-03`)**: Delete unmatched `)` on line 49. Restores full test collection immediately.
2. **Fix `test_db_lifecycle.py` Assertion (`ISS-08`)**: Update revision head list. Fixes failing test immediately.
3. **Fix Evidence Selection Waterfall (`ISS-05`)**: Remove `selectedEvidenceId` from `refreshEvidence` deps in `LiveAppContext.tsx`. Eliminates 4 redundant API calls on every item click.
4. **Pause `OrganicScene` Canvas Animation Off-Screen (`ISS-09`)**: Cancel RAF when `visible === false`. Saves 60 FPS CPU wakeups across 4 canvas instances.
5. **Re-enable TypeScript Build Errors (`ISS-13`)**: Remove `ignoreBuildErrors: true` from `next.config.ts`. Prevents silent type regressions.
6. **SQL-Level JSON Filtering for Sync Jobs (`ISS-14`)**: Query `payload_json->>'mapping_id'` directly in SQL instead of looping in Python.

### Architectural Changes (Phased Implementation Required)
1. **Merge Verification Center Branch (`ISS-01`)**: Reconcile Alembic database state with repository code on `main`.
2. **Enable RLS on Supabase Tables (`ISS-02`)**: Secure all 42 tables against unauthorized PostgREST API access.
3. **Enforce Project-Isolated Chroma Collections (`ISS-04`)**: Transition from shared collection to project-isolated collections per ADR 0005.
4. **Index 63 PostgreSQL Foreign Keys (`ISS-06`)**: Create b-tree indexes to optimize relational queries and cascading operations.
5. **Decompose Monolithic Frontend Context (`ISS-17`)**: Refactor `LiveAppContext` into modular state stores.

---

## 4. Success Metrics & Verification Criteria

| Optimization Area | Measuring Methodology | Target Success Threshold |
| :--- | :--- | :--- |
| **Test Collection & Execution** | `pytest backend/tests -m "not live_ai"` | **100% pass rate**, 0 collection errors, $< 15\text{ seconds}$ execution. |
| **Alembic Synchronization** | `alembic current` and `alembic check` | Clean single head output matching live database version. |
| **Evidence Selection Network Calls** | Browser DevTools Network tab on clicking evidence item | Exactly **1 network call** (`GET /evidence/{id}`) instead of 5 calls. |
| **PostgreSQL Foreign Key Scans** | `EXPLAIN ANALYZE` on child table delete/cascade | **Index Scan** utilized; 0 sequential scans on parent deletion. |
| **Database Security (RLS)** | `SELECT relrowsecurity FROM pg_class` | **42 / 42 tables** report `relrowsecurity = True`. |
| **ChromaDB Tenant Isolation** | Query vectors with mismatched project ID | **0 vectors returned** across project boundaries. |
| **Idle Browser CPU Usage** | Chrome Performance Monitor while scrolled away from hero | **0% CPU usage**, 0 active `requestAnimationFrame` ticks. |
