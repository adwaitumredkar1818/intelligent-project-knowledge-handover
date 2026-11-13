# The Handover — Backend and API Performance Audit
## API Endpoints, Latency Benchmarks, Concurrency & Execution Architecture

---

## 1. Executive Summary

The backend was audited across its FastAPI route handlers, dependency injection pipelines, SQLAlchemy 2.x database interactions, background worker queues, serialization patterns, and external service connectors.

Empirical latency measurements were executed against the live running backend server. The findings demonstrate that while **FastAPI and core application logic are highly performant (in-memory endpoints respond in 5–10 ms)**, severe performance degradations occur due to **cross-continental database latency (Supabase pooler in Sydney, Australia adding 1.3s–3.3s per round-trip)**, **synchronous execution blocks in background worker loops**, and **unindexed database queries**.

---

## 2. Empirical API Latency Measurements

Measurements were captured using non-invasive probes across 20 iterations per endpoint against the live server at `http://127.0.0.1:8000`.

### Measured Live Latency Table

| Endpoint | HTTP Status | Samples ($N$) | Mean Latency | Median (p50) | p95 Latency | p99 Latency | Performance Classification |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `GET /health` | `200 OK` | 20 | **10.43 ms** | **5.89 ms** | **34.18 ms** | **34.18 ms** | **Optimal** (In-memory liveness) |
| `GET /api/v1/health` | `200 OK` | 20 | **7.76 ms** | **5.76 ms** | **25.72 ms** | **25.72 ms** | **Optimal** (Router liveness) |
| `GET /health/ready` | `200 OK` | 20 | **3,355.91 ms** | **1,810.03 ms** | **8,846.38 ms** | **8,846.38 ms** | **CRITICAL DEGRADATION** (DB probe) |

### Analysis of the 3.35-Second Readiness Latency
- The root liveness check (`/health`) responds in **5.89 ms (median)**.
- The dependency readiness check (`/health/ready`) executes a database connection and runs `SELECT 1`.
- Because `.env` is configured to connect to `aws-1-ap-southeast-2.pooler.supabase.com` (Sydney, Australia) over TLS from a local developer machine in India (+05:30), each connection handshake and query incurs high cross-continental network latency.
- In production, if health check probes (e.g. Kubernetes, AWS ALB) call `/health/ready` with a default 2-second or 5-second timeout, containers will be falsely flagged as unhealthy and restarted in a crash loop.

---

## 3. Async vs. Synchronous Execution Architecture

### Synchronous Endpoint Execution (`def` vs `async def`)
- **Inspection Finding**: Many database-backed endpoints in `backend/app/api/routes/` are declared as standard synchronous functions:
  ```python
  @router.get("/projects/{project_id}/evidence", response_model=EvidenceListResponse)
  def list_evidence(...) -> EvidenceListResponse:
      ...
  ```
- **Execution Mechanism**: FastAPI runs synchronous `def` endpoints inside an `anyio` threadpool (`concurrent.futures.ThreadPoolExecutor`).
- **Database Driver**: SQLAlchemy 2.x is configured with `psycopg` (synchronous binary driver).
- **Concurrency Bottleneck**: Default threadpool size is limited (typically 40 threads). When queries to the remote Supabase database take 1.5–3.0 seconds, a modest spike of 40 concurrent user requests will completely exhaust the FastAPI threadpool, causing all subsequent API requests (including health checks) to queue and time out.

### Single-Threaded Worker Queue Serialisation
- In `backend/app/worker.py`, `CompositeWorkerService` processes jobs across 5 distinct domains:
  ```python
  def process_next_job(self) -> bool:
      if self.ingestion_worker.process_next_job(): return True
      if self.sync_worker.process_next_job(): return True
      if self.indexing_worker.process_next_job(): return True
      if self.reconstruction_worker.process_next_job(): return True
      if self.relationship_worker.process_next_job(): return True
      return False
  ```
- **Impact**: All job execution is strictly sequential within a single process.
- **Resource Starvation**: If a user uploads a 40-page scanned PDF requiring Ollama GLM OCR (taking 60–120 seconds), or triggers an 8-domain Qwen3 LLM reconstruction run (taking 90–180 seconds), **all other background work is completely halted**. Git synchronizations, document uploads, and vector indexing jobs are starved until the heavy job completes.

---

## 4. Query Efficiency, N+1 Risks & Inefficient Data Patterns

### 1. In-Memory Looping in `has_active_source_sync_job`
In `backend/app/repositories/job.py`:
```python
def has_active_source_sync_job(self, *, project_id: uuid.UUID, mapping_id: uuid.UUID) -> bool:
    stmt = select(BackgroundJob).where(
        BackgroundJob.project_id == project_id,
        BackgroundJob.job_type == BackgroundJobType.SOURCE_SYNC.value,
        BackgroundJob.status.in_((BackgroundJobStatus.QUEUED.value, BackgroundJobStatus.RUNNING.value)),
    )
    target_id = str(mapping_id)
    for job in self._session.execute(stmt).scalars().all():
        payload = job.payload_json or {}
        if str(payload.get("mapping_id") or "") == target_id:
            return True
    return False
```
- **Finding**: Instead of querying `payload_json->>'mapping_id' = :mapping_id` directly in SQL, the repository loads **all active source sync jobs into Python memory** and iterates over them with string comparisons.
- **Remediation**: Use PostgreSQL JSON operators:
  `stmt = stmt.where(BackgroundJob.payload_json["mapping_id"].as_string() == target_id)`

### 2. Missing Pagination on High-Volume Endpoints
- `GET /api/v1/projects/{project_id}/evidence`: Returns all evidence items for a project in a single unpaginated list.
- `GET /api/v1/projects/{project_id}/relationships`: Returns all knowledge relationships and entities without cursor-based or limit/offset pagination.
- **Impact**: As projects grow from initial prototypes (50 items) to realistic organizational repositories (10,000+ files, commits, and tickets), these endpoints will suffer severe serialization overhead, excessive memory usage, and multi-megabyte JSON payloads.

### 3. Repeated Access Policy Evaluation
In `backend/app/services/retrieval.py`:
```python
# Re-verify every keyword hit through canonical SourceAccessPolicyService
rank_counter = 0
for kw_hit in raw_kw:
    ...
```
- For every keyword match returned by full-text search, the backend re-evaluates ACL access policies row-by-row in Python. While secure, performing iterative permission checks on hundreds of candidates in application memory adds avoidable CPU latency.

---

## 5. Rate Limiting Architecture

- **Implementation**: `InMemorySlidingWindowRateLimiter` in `backend/app/core/rate_limit.py`.
- **Protected Routes**: `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/refresh`.
- **Limitation**: State is stored purely in Python memory (`dict[str, list[float]]`).
- **Consequence**:
  1. Rate limits reset on every application restart or worker reload.
  2. In a multi-worker or multi-container deployment, attackers can bypass rate limits by round-robining requests across different process instances.

---

## 6. Actionable Backend Optimizations

1. **Colocate Database and Backend (High Priority)**:
   - Deploy the backend in the same region as PostgreSQL (or use the local Docker PostgreSQL container during local development) to reduce database ping times from 200 ms to $< 2\text{ ms}$, dropping `/health/ready` latency from 3.3s to $< 15\text{ ms}$.
2. **Add SQL-Level JSON Filtering in Job Repository**:
   - Replace Python in-memory job payload filtering with native PostgreSQL JSONB indexing and query operators.
3. **Introduce Pagination (`limit`, `cursor`) on Evidence & Relationship APIs**:
   - Enforce a default limit of 50 items with cursor-based pagination on `list_evidence` and `get_graph`.
4. **Decouple Heavy Compute from Lightweight Worker Queues**:
   - Run separate worker instances or concurrent queues: one for I/O tasks (`sync_worker`, `indexing_worker`) and one for heavy inference tasks (`ingestion_worker`, `reconstruction_worker`).
5. **Add Persistent Rate Limiting for Multi-Instance Deployments**:
   - Prepare a Redis or PostgreSQL-backed sliding window rate limiter for production environments.
