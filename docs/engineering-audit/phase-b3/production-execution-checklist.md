# Production Execution Checklist & Runbook: Migration 0013

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Migration Target:** `infrastructure/database/migrations/versions/20261113_0013_rls_hardening.py`  
**Revision:** `0013_rls_hardening` (Revises: `0012_verification_center`)  
**Scope:** Enable Row Level Security (RLS) on all 56 public base tables  
**Status:** **READY FOR EXECUTION UPON SEPARATE AUTHORIZATION**

---

## 1. Pre-Execution Prerequisites & Approvals

Before executing migration 0013 against the live production or staging database, the operator must verify each item below:

- [ ] **Formal Authorization:** Explicit stakeholder approval has been granted to apply migration 0013.
- [ ] **Codebase Branch State:** The executing branch is `main` (or the approved release branch) containing commit history through `0013_rls_hardening`.
- [ ] **Database Backup:** 
  - A fresh backup or Point-in-Time Recovery (PITR) snapshot exists in the Supabase Dashboard.
  - Alternatively, execute manual schema + data backup:
    ```bash
    # Verify backup availability before proceeding
    pg_dump --host=aws-1-ap-southeast-2.pooler.supabase.com --port=5432 --username=postgres --format=custom --file="handover_pre_0013_$(date +%Y%m%d_%H%M%S).dump" postgres
    ```
- [ ] **Target Database Revision Reconciliation:**
  - Check the live `alembic_version` on the target database:
    ```sql
    SELECT version_num FROM public.alembic_version;
    ```
  - *Note on Multi-Branch State:* If the database reflects migrations from another feature branch (such as `0013_handover_workspace` or `0015_assistant_workspace`), the migration order must be reconciled or deployed to a freshly branched database before running this command.
- [ ] **Network & Pooler Stability:**
  - Confirm stable latency to `aws-1-ap-southeast-2.pooler.supabase.com:5432`.

---

## 2. Maintenance Window & Concurrency Precautions

`ALTER TABLE ... ENABLE ROW LEVEL SECURITY` acquires an `AccessExclusiveLock` on each table. To prevent lock contention and avoid deadlocks with concurrent transactions:

- [ ] **Schedule Maintenance Window:** Execute during an off-peak maintenance window or period of minimal user traffic.
- [ ] **Pause Background Workers:** Stop all running background worker processes prior to execution:
  ```powershell
  # Stop evidence processing and OCR workers
  # (Terminate background worker terminals or systemd/daemon services)
  ```
- [ ] **Set Session Lock Timeout:** Ensure the migration session uses a short `lock_timeout` (e.g. 5 seconds) so that it fails fast rather than queueing and causing connection pool exhaustion:
  ```sql
  SET lock_timeout = '5s';
  ```

---

## 3. Step-by-Step Execution Protocol

### Step 1: Pre-Flight Baseline Verification (Read-Only)
Run the following SQL query on the target database to record the baseline RLS status across all 56 public base tables:

```sql
SELECT 
    schemaname, 
    tablename, 
    rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;
```
- **Expected Baseline:** All 56 tables must report `rowsecurity = false`.

---

### Step 2: Dry-Run Offline SQL Generation
Generate and inspect the exact SQL payload before execution:

```powershell
backend/.venv/Scripts/alembic.exe -c backend/alembic.ini upgrade 0012_verification_center:0013_rls_hardening --sql > migration_0013_dryrun.sql
```
- Verify `migration_0013_dryrun.sql` contains exactly 56 `ALTER TABLE public."..." ENABLE ROW LEVEL SECURITY;` statements.
- Verify zero `CREATE POLICY` statements exist.
- Verify zero `FORCE ROW LEVEL SECURITY` statements exist.

---

### Step 3: Online Migration Execution
Execute the migration using Alembic:

```powershell
backend/.venv/Scripts/alembic.exe -c backend/alembic.ini upgrade 0013_rls_hardening
```
- **Expected Output:**
  ```text
  INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
  INFO  [alembic.runtime.migration] Will assume transactional DDL.
  INFO  [alembic.runtime.migration] Running upgrade 0012_verification_center -> 0013_rls_hardening, Enable Row Level Security (RLS) on all 56 public base tables.
  ```

---

### Step 4: Post-Migration Catalog Verification
Execute the verification query on the target database:

```sql
SELECT 
    COUNT(*) AS total_tables,
    COUNT(*) FILTER (WHERE rowsecurity = true) AS rls_enabled_tables,
    COUNT(*) FILTER (WHERE rowsecurity = false) AS rls_disabled_tables
FROM pg_tables 
WHERE schemaname = 'public';
```
- **Acceptance Criteria:**
  - `total_tables`: 56
  - `rls_enabled_tables`: 56
  - `rls_disabled_tables`: 0

Verify Alembic version table:
```sql
SELECT version_num FROM public.alembic_version;
```
- **Expected Result:** `0013_rls_hardening`

---

### Step 5: PostgREST External API Denial Verification
Verify that external unauthenticated and authenticated requests to PostgREST cannot access data:

```bash
# 1. Unauthenticated request to users table
curl -i -X GET "https://<PROJECT-REF>.supabase.co/rest/v1/users" \
  -H "apikey: <ANON_KEY>"

# Expected Response: HTTP 401 Unauthorized OR HTTP 200 OK with empty array []
```

---

### Step 6: Backend Application Health & Smoke Verification
Run backend automated health tests to verify the FastAPI backend (connecting as `postgres`) continues to operate unhindered:

```powershell
backend/.venv/Scripts/pytest.exe backend/tests/test_health_endpoints.py backend/tests/test_auth_api.py -v
```
- **Acceptance Criteria:** 100% test pass rate.

---

### Step 7: Resume Background Workers
Restart background workers and verify job queue processing:
```powershell
python -m app.workers.evidence_worker
```

---

## 4. Rollback Runbook (Contingency Procedure)

If an unexpected lock contention, deadlock, or application degradation occurs, execute the following rollback procedure immediately.

### Immediate Rollback via Alembic
```powershell
backend/.venv/Scripts/alembic.exe -c backend/alembic.ini downgrade 0012_verification_center
```

### Emergency Direct SQL Rollback Script
If Alembic cannot connect or is hung, execute the following emergency DDL directly via `psql` or the Supabase SQL Editor:

```sql
BEGIN;

ALTER TABLE public."alembic_version" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."audit_logs" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."background_jobs" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."decision_traceability_chains" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."entity_aliases" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."evidence_chunks" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."evidence_contents" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."evidence_items" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."evidence_page_contents" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."handover_acknowledgements" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."handover_cases" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."handover_checklist_items" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."handover_checklists" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."handover_content_links" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."handover_deliveries" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."handover_ownership_transfers" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."handover_package_sections" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."handover_package_versions" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."handover_packages" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."handover_readiness_assessments" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."handover_responsibility_transfers" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."handover_signoffs" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."handover_status_histories" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."identity_resolution_candidates" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."knowledge_entities" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."knowledge_evidence_links" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."knowledge_extraction_runs" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."knowledge_items" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."knowledge_relationships" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."knowledge_timeline_events" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."oauth_states" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."organisation_invitations" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."organisation_memberships" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."organisations" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."permissions" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."project_memberships" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."project_source_mappings" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."project_transitions" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."project_vector_indexes" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."projects" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."refresh_sessions" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."relationship_evidence_links" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."relationship_reconstruction_runs" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."role_permissions" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."roles" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."source_access_policies" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."source_connections" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."source_sync_runs" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."user_roles" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."user_source_authorisations" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."users" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."verification_cases" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."verification_conflicts" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."verification_context_requests" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."verification_issues" DISABLE ROW LEVEL SECURITY;
ALTER TABLE public."verification_review_events" DISABLE ROW LEVEL SECURITY;

UPDATE public.alembic_version SET version_num = '0012_verification_center';

COMMIT;
```

### Rollback Verification
Confirm that all 56 tables have reverted to `rowsecurity = false`:
```sql
SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public' AND rowsecurity = false;
-- Expected output: 56
```

---

## 5. Execution Sign-Off Log

| Role | Name / Identifier | Signature / Decision | Date & Time |
|---|---|---|---|
| **Author / Lead Engineer** | Database Architect | Pre-flight Verified & Tested Locally | 2026-11-13 |
| **Security Reviewer** | Security Engineer | Code Review & Architecture Approved | 2026-11-13 |
| **Production Approver** | Project Lead / User | **PENDING AUTHORIZATION** | — |
| **Executing Operator** | Operator | PENDING | — |
