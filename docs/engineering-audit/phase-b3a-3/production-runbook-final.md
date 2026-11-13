# Production Deployment Runbook: Migration 0016 (Final Standard)

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Target Migration:** `infrastructure/database/migrations/versions/20261113_0016_rls_hardening.py`  
**Target Revision:** `0016_rls_hardening` (Parent: `0015_assistant_workspace`)  
**Scope:** Enable Row Level Security (RLS) across all 61 public base tables  
**Audit Phase:** **Phase B3A.3 — Migration Test Isolation & Production Runbook Finalization**  
**Date:** 2026-11-13  
**Status:** **FINAL APPROVED RUNBOOK (PENDING PRODUCTION EXECUTION AUTHORIZATION)**

---

## 1. Executive Summary & Engineering Precepts

This document defines the final, hardened production deployment runbook for enabling Row Level Security across the Handover platform's 61 public database tables.

### Key Corrections from Prior Drafts:
1. **Engine-Level RLS Enforcement (PostgREST Reload Omitted as Mandatory):**
   Prior drafts listed `NOTIFY pgrst, 'reload schema'` as a mandatory security step. This has been corrected. In PostgreSQL, Row Level Security is enforced directly inside the database query planner and executor (`relrowsecurity = true`). When an unprivileged role (`anon` or `authenticated`) queries PostgreSQL, the database engine returns 0 rows (default-deny) immediately. PostgREST's schema cache only caches OpenAPI table structures, not row filtering. Therefore, PostgreSQL itself guarantees RLS enforcement without requiring a PostgREST notification.
2. **Exact Connection Timeout Enforcement:**
   `lock_timeout = 2000ms` and `statement_timeout = 30000ms` must be set and verified on the exact connection that executes the Alembic migration before the first DDL statement.
3. **Application Traffic Quiescence:**
   The procedure includes full application ingress quiescence (maintenance window / HTTP 503) alongside worker suspension to guarantee zero lock contention on core tables (`users`, `projects`).

---

## 2. Complete Deployment Timeline & Protocol

```mermaid
sequenceDiagram
    autonumber
    participant Op as Release Operator
    participant LB as Ingress / Application Gateway
    participant Worker as Background Worker Service
    participant PG as PostgreSQL 17 (Supabase Port 5432)
    participant Alembic as Alembic Migration Runner

    Note over Op, PG: Phase 1: Pre-Flight Safety & Checkpoint
    Op->>PG: Confirm automated PITR snapshot or execute pg_dump
    Op->>PG: Query SELECT version_num FROM alembic_version (Must be '0015_assistant_workspace')

    Note over Op, LB: Phase 2: Traffic Quiescence & Isolation
    Op->>Worker: Terminate all worker processes (stop evidence_worker)
    Op->>PG: Assert zero active workers via pg_stat_activity
    Op->>LB: Enable Maintenance Mode (Return HTTP 503 Service Unavailable)
    Op->>PG: Inspect active transactions & locks (Must be idle)

    Note over Op, Alembic: Phase 3: Atomic Execution with Timeout Guard
    Op->>Alembic: Launch migration runner on Session Pooler (Port 5432)
    Alembic->>PG: SET lock_timeout = '2000ms'; SET statement_timeout = '30000ms';
    Alembic->>PG: SHOW lock_timeout; SHOW statement_timeout; (Assert effective values)
    Alembic->>PG: BEGIN TRANSACTION;
    Alembic->>PG: ALTER TABLE public."..." ENABLE RLS; (Executed across 61 tables)
    Alembic->>PG: UPDATE alembic_version SET version_num = '0016_rls_hardening';
    Alembic->>PG: COMMIT;

    Note over Op, PG: Phase 4: Verification & Service Restoration
    Op->>PG: Verify COUNT(*) FILTER (WHERE rowsecurity = true) == 61
    Op->>LB: Run health checks & auth smoke tests (/api/v1/health/ready)
    Op->>LB: Disable Maintenance Mode (Restore traffic)
    Op->>Worker: Restart background workers
```

---

## 3. Step-by-Step Production Execution Runbook

### Step 1: Pre-Flight Backup Checkpoint
* Confirm that Supabase Point-in-Time Recovery (PITR) is active and a snapshot exists within the last 30 minutes.
* Alternatively, run manual custom-format schema + data dump:
  ```bash
  pg_dump --host=aws-1-ap-southeast-2.pooler.supabase.com --port=5432 --username=postgres \
    --format=custom --file="handover_pre_0016_$(date +%Y%m%d_%H%M%S).dump" postgres
  ```

---

### Step 2: Database Revision Pre-Flight Verification
Execute read-only query on target database:
```sql
SELECT version_num FROM public.alembic_version;
```
* **Acceptance Criteria:** Exactly one row containing `'0015_assistant_workspace'`.
* *DO NOT PROCEED IF REVISION DOES NOT MATCH.*

---

### Step 3: Application Traffic Quiescence & Worker Suspension
1. **Stop Background Workers:**
   Terminate all running instances of `app.workers.evidence_worker`.
2. **Quiesce Application Web Traffic:**
   - Place the FastAPI backend into maintenance mode or route ingress traffic to a static 503 Maintenance Page.
   - Allow active user HTTP requests to drain for 30 seconds.
   - *Why?* Prevents incoming user sessions from acquiring `AccessShareLock` on `users` or `projects`, eliminating connection pool queueing.
3. **Verify Zero Active Queries on Public Schema:**
   ```sql
   SELECT pid, now() - xact_start AS duration, query, state 
   FROM pg_stat_activity 
   WHERE state != 'idle' 
     AND query NOT ILIKE '%pg_stat_activity%';
   ```
   - **Acceptance Criteria:** Exactly 0 active application queries.

---

### Step 4: Built-in In-Migration Lock Timeout & Statement Timeout Verification
Migration `0016_rls_hardening` incorporates internal pre-flight timeout enforcement directly inside its database transaction (`_enforce_connection_timeouts`):
- `SET LOCAL lock_timeout = '2000ms';`
- `SET LOCAL statement_timeout = '30000ms';`
- `SHOW lock_timeout;` and `SHOW statement_timeout;` asserting effective values before executing any `ALTER TABLE` statement.

To provide defense-in-depth on the connection string itself, set the connection parameters before invoking Alembic:
```powershell
$env:DATABASE_URL = "$env:DATABASE_URL`?options=-c%20lock_timeout=2000ms%20-c%20statement_timeout=30000ms"
```
* **Acceptance Criteria:**
  - `lock_timeout`: `2s` or `2000ms` verified by migration pre-flight.
  - `statement_timeout`: `30s` or `30000ms` verified by migration pre-flight.
  - If either parameter cannot be asserted by PostgreSQL, the migration aborts with `RuntimeError` before any DDL is applied.

---

### Step 5: Execute Atomic Alembic Migration
Execute the upgrade against the target database via Port 5432:
```powershell
alembic upgrade 0016_rls_hardening
```
* **Execution Contract:**
  - Alembic executes inside a single `BEGIN ... COMMIT` block.
  - Executes `_verify_schema_integrity` (validating all 61 public tables exist).
  - Executes `_enforce_connection_timeouts` (guaranteeing 2000ms lock timeout on this exact connection).
  - Sequentially applies `ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;` on all 61 tables.
  - Updates `alembic_version` to `0016_rls_hardening`.
  - Commits transaction atomically.

---

### Step 6: Post-Migration Catalog Verification
Run verification query:
```sql
SELECT 
    COUNT(*) AS total_tables,
    COUNT(*) FILTER (WHERE rowsecurity = true) AS rls_enabled,
    COUNT(*) FILTER (WHERE rowsecurity = false) AS rls_disabled
FROM pg_tables 
WHERE schemaname = 'public';
```
* **Acceptance Criteria:**
  - `total_tables`: 61
  - `rls_enabled`: 61
  - `rls_disabled`: 0

Verify `public.alembic_version`:
```sql
SELECT version_num FROM public.alembic_version;
```
* **Acceptance Criteria:** `0016_rls_hardening`

---

### Step 7: Application Smoke Verification Before Restoring Traffic
Before opening ingress to public users, execute smoke tests:
1. **Backend Health Check:**
   ```bash
   curl -i http://localhost:8000/api/v1/health/ready
   ```
   - *Expected:* HTTP 200 OK.
2. **FastAPI Auth & Database Smoke Test:**
   ```powershell
   pytest backend/tests/test_health_endpoints.py backend/tests/test_auth_api.py -v
   ```
   - *Expected:* 100% PASS rate.
3. **PostgREST External Denial Probe:**
   ```bash
   curl -i -X GET "https://rjntmboskzyrsqcetzil.supabase.co/rest/v1/users" -H "apikey: <ANON_KEY>"
   ```
   - *Expected:* HTTP 401 Unauthorized OR HTTP 200 OK with `[]` (0 rows).

---

### Step 8: Restore Application Traffic & Resume Workers
1. Disable maintenance mode on the ingress load balancer / gateway.
2. Restart background workers:
   ```powershell
   python -m app.workers.evidence_worker
   ```
3. Monitor application logs and pooler latency for 15 minutes.

---

## 4. Failure Midway & Rollback Mechanics

* **Scenario:** At table #50 (`users`), an unexpected lock contention exceeds 2000ms.
* **Engine Response:** PostgreSQL triggers `55P03: lock_not_available`.
* **Atomicity Guarantee:**
  - The PostgreSQL transaction immediately enters the `ABORTED` state.
  - Alembic catches the exception and issues `ROLLBACK;`.
  - All preceding 49 `ENABLE ROW LEVEL SECURITY` statements are rolled back.
  - The database catalog returns 100% to revision `0015_assistant_workspace` with `rowsecurity = false` on all 61 tables.
* **Zero Orphaned Locks:** All locks are released immediately upon rollback.
