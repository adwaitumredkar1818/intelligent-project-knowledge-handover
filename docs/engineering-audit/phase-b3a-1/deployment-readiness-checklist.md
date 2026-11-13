# Production Deployment Readiness Checklist & Runbook

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Topic:** Hardened Production Execution Protocol & Gap Analysis for RLS Hardening Deployment  
**Audit Phase:** **Phase B3A.1 — Migration 0013 Deployment Readiness Audit**  
**Auditor:** Senior Database Architect & PostgreSQL Security Engineer  
**Date:** 2026-11-13  
**Status:** **HARDENED PROTOCOL CODIFIED (AUDIT APPROVED)**

---

## 1. Executive Summary & Gap Analysis of Phase B3 Runbook

A rigorous review of the preliminary Phase B3 checklist identified several critical gaps that could jeopardize a live production deployment:

### Critical Gaps Identified in Prior Checklist:
1. **Target Database Revision Ambiguity:** The prior checklist assumed the live database was at `0012_verification_center`. However, evidence from recent feature branch activity indicates the live Supabase instance has already reached `0015_assistant_workspace`. Attempting to run `upgrade 0013` against a database at revision `0015` would fail.
2. **Missing Active Transaction & Lock Pre-Flight Inspection:** The prior runbook did not inspect `pg_stat_activity` or `pg_locks` before initiating DDL, risking immediate lock contention.
3. **Excessive Lock Timeout:** The prior 5-second `lock_timeout` is long enough to cause connection pool starvation; it has been hardened to **2 seconds**.
4. **Omission of PostgREST Schema Cache Reload:** PostgREST caches table security profiles. Toggling RLS requires issuing `NOTIFY pgrst, 'reload schema';` to guarantee immediate policy re-evaluation.
5. **Worker Shutdown Verification:** The prior runbook suggested pausing workers, but did not provide an authoritative SQL verification query to prove zero workers hold active locks.

This document presents the **hardened, production-grade checklist** addressing all five deficiencies.

---

## 2. Hardened Pre-Execution Prerequisites

- [ ] **1. Formal Business & Technical Authorization:**
  - Written stakeholder sign-off obtained for production maintenance window.
- [ ] **2. Database Revision Identification & Target Reconciliation:**
  - Execute read-only query on target database:
    ```sql
    SELECT version_num FROM public.alembic_version;
    ```
  - **Decision Gate:**
    - If `version_num == '0012_verification_center'`: Target is **Migration 0013** (56 tables).
    - If `version_num == '0015_assistant_workspace'`: Target is **Migration 0016** (61 tables, following git merge finalization).
    - *DO NOT PROCEED IF REVISION DOES NOT MATCH EITHER CANONICAL STATE.*
- [ ] **3. Fresh Database Backup & Point-in-Time Recovery Verification:**
  - Confirm Supabase automated snapshot exists within the last 60 minutes.
  - Or execute explicit manual schema + data dump:
    ```bash
    pg_dump --host=<HOST> --port=5432 --username=postgres --format=custom \
      --file="handover_pre_rls_$(date +%Y%m%d_%H%M%S).dump" postgres
    ```
- [ ] **4. Session Pooler Port Confirmation:**
  - Connect strictly to **Port 5432** (Session Pooler or Direct Connection).
  - *DO NOT USE PORT 6543 (Transaction Pooler)*, as session variables like `lock_timeout` do not persist across pooled transactions.

---

## 3. Pre-Flight Concurrency Clearance (5 Minutes Before Execution)

- [ ] **5. Stop Background Workers:**
  - Terminate all instances of `app.workers.evidence_worker`.
- [ ] **6. Verify Worker Termination via Catalog:**
  - Run query to confirm zero background worker connections remain:
    ```sql
    SELECT pid, application_name, client_addr, state, query 
    FROM pg_stat_activity 
    WHERE application_name ILIKE '%worker%' 
       OR query ILIKE '%background_jobs%';
    ```
  - *Criteria:* 0 rows returned.
- [ ] **7. Inspect Active Long-Running Transactions:**
  - Check for transactions open longer than 10 seconds:
    ```sql
    SELECT pid, now() - xact_start AS duration, query, state 
    FROM pg_stat_activity 
    WHERE state != 'idle' 
      AND (now() - xact_start) > interval '10 seconds';
    ```
  - *Criteria:* Zero long-running transactions on application tables.

---

## 4. Execution Protocol

### Step 1: Pre-Flight Baseline Recording
Record baseline RLS state:
```sql
SELECT 
    COUNT(*) AS total_tables,
    COUNT(*) FILTER (WHERE rowsecurity = true) AS enabled,
    COUNT(*) FILTER (WHERE rowsecurity = false) AS disabled
FROM pg_tables 
WHERE schemaname = 'public';
```
- *Expected:* `disabled` equals 56 (or 61), `enabled` equals 0.

---

### Step 2: Offline Dry-Run DDL Verification
Generate and inspect dry-run SQL:
```powershell
# For revision 0013:
alembic upgrade 0012_verification_center:0013_rls_hardening --sql > dryrun.sql

# OR for revision 0016:
alembic upgrade 0015_assistant_workspace:0016_rls_hardening --sql > dryrun.sql
```
- Verify exact count of `ENABLE ROW LEVEL SECURITY` statements (56 or 61).
- Verify zero `CREATE POLICY` statements.
- Verify zero `FORCE ROW LEVEL SECURITY` statements.

---

### Step 3: Migration Execution with Strict Lock Timeout
Execute with session lock timeout set to 2 seconds:

```sql
-- Inside execution session:
SET lock_timeout = '2000ms';
SET statement_timeout = '30000ms';
```

Execute Alembic upgrade:
```powershell
alembic upgrade <TARGET_REVISION>
```

---

### Step 4: PostgREST Schema Cache Reload
Immediately instruct PostgREST to reload its schema cache:
```sql
NOTIFY pgrst, 'reload schema';
```

---

## 5. Post-Execution Verification Protocol

### Step 5: Catalog Verification
Run verification query:
```sql
SELECT 
    COUNT(*) AS total_tables,
    COUNT(*) FILTER (WHERE rowsecurity = true) AS rls_enabled,
    COUNT(*) FILTER (WHERE rowsecurity = false) AS rls_disabled
FROM pg_tables 
WHERE schemaname = 'public';
```
- **Acceptance Criteria:**
  - `rls_enabled`: 100% of tables (56 or 61).
  - `rls_disabled`: Exactly 0.

Verify Alembic version table:
```sql
SELECT version_num FROM public.alembic_version;
```
- **Acceptance Criteria:** Matches target revision (`0013_rls_hardening` or `0016_rls_hardening`).

---

### Step 6: PostgREST API Denial Probes (External Perimeter Verification)
Verify that PostgREST rejects external anonymous requests:
```bash
curl -i -X GET "https://<PROJECT-REF>.supabase.co/rest/v1/users" \
  -H "apikey: <ANON_KEY>"
```
- **Acceptance Criteria:** HTTP 401 Unauthorized OR HTTP 200 OK with empty array `[]` (0 rows exposed).

---

### Step 7: Application Backend Smoke Verification
Execute automated backend health tests:
```powershell
pytest backend/tests/test_health_endpoints.py backend/tests/test_auth_api.py -v
```
- **Acceptance Criteria:** 100% PASS rate. Proves `postgres` runtime user operates uninhibited.

---

### Step 8: Resume Background Workers
Restart background workers and monitor queue health:
```powershell
python -m app.workers.evidence_worker
```
- Verify worker claims jobs without deadlocks.

---

## 6. Emergency Rollback Runbook

If unresolvable lock contention occurs or the application experiences elevated latency:

### Option A: Clean Rollback via Alembic
```powershell
alembic downgrade <PREVIOUS_REVISION>
```

### Option B: Emergency Direct SQL Rollback Script
Execute directly via `psql` or Supabase SQL Editor:
```sql
BEGIN;
SET lock_timeout = '2000ms';

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'ALTER TABLE public."' || r.tablename || '" DISABLE ROW LEVEL SECURITY;';
    END LOOP;
END $$;

NOTIFY pgrst, 'reload schema';

COMMIT;
```

### Rollback Verification:
```sql
SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public' AND rowsecurity = false;
-- Acceptance Criteria: Equals total table count (56 or 61).
```
