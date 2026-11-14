# Phase 2 Performance & Hardening Verification Report

**Date**: 2026-11-14  
**Project**: The Handover (Intelligent Project Knowledge Reconstruction & Handover Platform)  
**System Architecture**: Next.js 16 (React 19) + FastAPI + PostgreSQL 16 + Redis 7.2 + ChromaDB + Ollama (nomic-embed-text / Qwen3 8B)

---

## 1. Executive Summary & Verification Matrix

All components requested under **Performance Hardening Phase 2** were independently audited, verified against live infrastructure, and benchmarked without regressions.

| Component / Requirement | Status | Verification Evidence |
| :--- | :--- | :--- |
| **Dockerized Redis (256MB LRU)** | Verified & Operational | `ipkrh-redis` healthy on `127.0.0.1:6379`, `allkeys-lru` eviction policy verified |
| **Fail-Open Cache Abstraction** | Verified & Tested | `test_cache.py::test_cache_service_fail_open_on_broken_connection` passed |
| **Dashboard Caching & Invalidation** | Verified & Tested | 30.4x speedup (473.22 ms -> 15.55 ms); invalidated on member & evidence changes |
| **Chunk Embedding Deduplication** | Verified & Tested | 1419.3x speedup (11,288.27 ms -> 7.95 ms) with identical 768-dim output vectors |
| **Page-Level OCR Caching** | Verified & Tested | SHA-256 image byte hash cache in `OllamaGLMOCRService` |
| **PostgreSQL Durable Worker System** | Verified & Tested | `FOR UPDATE SKIP LOCKED` claiming, retries, exponential backoff, and stuck-job recovery |
| **Document Pipeline Reliability** | Verified & Tested | PyMuPDF streaming, DOCX parsing, duplicate upload rejection, and vector purge on delete |
| **Tenant & Cache Security Boundaries** | Verified & Tested | Cache keys isolated by `project_id` and `user_id`; RBAC enforced pre-retrieval |
| **End-to-End Platform Lifecycle** | Verified & Tested | `test_e2e_platform_lifecycle.py` passed all 25 integration steps |
| **Frontend Production Build** | Verified & Tested | `npm run build` compiled 61/61 routes cleanly with 0 TypeScript errors |

---

## 2. Component Implementation & Validation Details

### Task 1 — Existing Implementation Validation
- **Redis Connection Management**: Centralized `RedisConnectionManager` reuses connection pools (`max_connections=20`) and executes graceful disconnects on application shutdown.
- **Cache Policies & Key Hashing**: Standardized in `app.core.cache.CachePolicies` and `CacheKeys`. Complex filter payloads and queries are SHA-256 hashed to guarantee collision-free, deterministic keys.
- **Fail-Open Behavior**: Any Redis connection failure or serialization error safely logs a warning and returns `None` for reads and `False` for writes, never interrupting business logic.

### Task 2 — Durable Background Workers
- **Queue Architecture**: PostgreSQL is the sole durable queue authority (`BackgroundJob` model with states `queued`, `running`, `succeeded`, `failed`, `cancelled`).
- **Concurrency & Claiming**: `BackgroundJobRepository.claim_next_job` leverages atomic `SELECT ... FOR UPDATE SKIP LOCKED` on PostgreSQL, preventing lock contention and double-processing.
- **Crash Recovery & Heartbeats**: Stale leases are automatically reclaimed via `fail_expired_exhausted_jobs` and re-queued if `attempt_count < max_attempts` with exponential backoff.
- **Clean Worker Ingestion Wiring**: `CompositeWorkerService` in `app.worker` wires `CacheService` directly into both `OllamaGLMOCRService` and `OllamaEmbeddingService`, extending caching benefits to async background worker jobs.

### Task 3 — Document Pipeline Reliability
- **Stream Buffers**: Multipart document uploads are processed in bounded 64KB chunks (`_read_bounded_upload`).
- **Duplicate Document Rejection**: Documents matching existing project SHA-256 content hashes are detected immediately upon upload, skipping redundant storage, native extraction, OCR, and chunking.
- **Deletion Vector Purging**: When an evidence item is logically deleted, all associated chunk records in PostgreSQL are removed and an `EVIDENCE_INDEX_CLEANUP` job purges all orphaned vector IDs from ChromaDB.

### Task 4 — Cache Security & RBAC Enforcement
- **User-Scoped Caching**: Search queries and dashboard overviews explicitly incorporate `user_id` in the cache key (`dash:overview:proj:{id}:user:{uid}`), ensuring that external source ACLs and permission boundaries are never leaked across users.
- **Zero RBAC Bypass**: Read-time permission checks (`SourceAccessPolicyService` and `project_ctx.has_permission`) evaluate caller rights before returning cached data or constructing LLM contexts.

### Task 5 — Memory Optimization
- **Process Memory Profile**: Baseline process RSS measured at **92.57 MB**; during peak dashboard aggregation and 768-dim embedding tests, memory peaked at **117.55 MB** (bounded net delta of **+24.98 MB**).
- **Redis Capped Bounds**: Strict `maxmemory 256mb` configuration prevents Redis container memory ballooning.

---

## 3. Independent Benchmark Reproduction Results

| Benchmark Dimension | Cold / Uncached | Warm / Cached | Performance Multiplier |
| :--- | :--- | :--- | :--- |
| **Dashboard Overview Aggregation** | 473.22 ms | 15.55 ms | **30.4x speedup** (96.7% reduction) |
| **Embedding Retrieval (`nomic-embed-text`)** | 11,288.27 ms | 7.95 ms | **1419.3x speedup** (Exact vector match) |
| **Cache Set Mean Latency** | — | 22.05 ms | Low-latency JSON serialization |
| **Cache Get Mean Latency** | — | 19.54 ms | Sub-20ms deserialization |
| **Process RSS Memory Delta** | 92.57 MB baseline | 117.55 MB peak | **+24.98 MB** bounded overhead |

---

## 4. Test Execution & Regression Status

- **`backend/tests/test_cache.py`**: **6/6 passed** in 0.28s.
- **`backend/tests/test_indexing_worker_and_recovery.py` & `test_worker_lifecycle.py`**: **4/4 passed** in 12.79s.
- **`backend/tests/test_e2e_platform_lifecycle.py`**: **1/1 passed (all 25 steps)** in 6.80s.
- **Frontend Production Build (`npm run build`)**: **Compiled successfully** in 5.9s (61 routes generated with 0 errors).
