# Phase A Remediation Plan (Phase B Execution Specification)
## Staged Implementation Plan for Migration Reconciliation & Security Hardening

**Platform:** The Handover  
**Scope:** Remediation of Migration Desynchronization and PostgreSQL Defense-in-Depth Hardening  
**Target Environment:** Local Repository & Supabase Hosted PostgreSQL (`aws-1-ap-southeast-2.pooler.supabase.com:5432`)  
**Status:** **AWAITING USER APPROVAL (READ-ONLY AUDIT COMPLETE)**  

---

## 1. Overview & Phased Governance

This remediation plan translates the empirical findings of the Phase A audit into an executable, zero-downtime, zero-data-loss engineering roadmap.

Remediation is partitioned into three sequential, atomic workstreams:
- **Workstream 1:** Reconcile Repository & Alembic Migrations (Execution of Option A).
- **Workstream 2:** Database Security Hardening (RLS & Grant Lockdown via Migration `0013`).
- **Workstream 3:** Verification & End-to-End Regression Testing.

> [!IMPORTANT]
> **GATE CHECK — ZERO PRODUCTION STATE CHANGES IN PHASE A:**  
> In accordance with audit safety directives, no steps below have been executed. Execution will commence only after the user reviews Phase A findings and issues explicit written authorization.

---

## 2. Workstream 1: Migration Synchronization (Option A)

### Objective
Synchronize the local `main` branch with the live database schema at revision `0012_verification_center` by integrating `origin/feature/verification-center-backend`.

### Execution Steps
1. **Pre-Flight Verification:**
   - Confirm working tree is clean: `git status --short`.
   - Verify local branch is `main`: `git rev-parse --abbrev-ref HEAD`.
   - Confirm remote tracking branch is up to date: `git fetch origin`.
2. **Merge Feature Branch:**
   - Execute merge:
     ```bash
     git merge origin/feature/verification-center-backend --no-ff -m "chore(migrations): reconcile migration 0012 and integrate Verification Center backend"
     ```
   - *Note:* Because commit `0301ee5ada` is a direct child of `main` (`2903bf2d0369`), this merge is conflict-free.
3. **Verify Alembic State:**
   - Inspect local heads:
     ```bash
     alembic -c backend/alembic.ini heads
     # Expected output: 0012_verification_center (head)
     ```
   - Verify alignment with live database:
     ```bash
     alembic -c backend/alembic.ini current
     # Expected output: 0012_verification_center (head)
     ```
4. **Execute Verification Backend Unit Tests:**
   - Run automated test suite:
     ```bash
     pytest backend/tests/test_verification_center.py -v
     # Expected output: 11 passed in < 2.0s
     ```

### Workstream 1 Rollback Plan
If unexpected issues arise during merge:
```bash
git merge --abort
```
The repository returns instantly to `main` at `2903bf2d0369` with zero database side-effects.

---

## 3. Workstream 2: Database Security Hardening (RLS & Grant Lockdown)

### Objective
Implement defense-in-depth on the live Supabase PostgreSQL database by enabling Row Level Security across all 56 base tables in the `public` schema and enforcing explicit default-deny policies for Supabase API roles.

### Architecture of Hardening Migration (`0013_rls_hardening.py`)
To ensure total database consistency, security hardening will be authored as a standard, tracked Alembic migration:
- **Revision ID:** `0013_rls_hardening`
- **Down Revision:** `0012_verification_center`
- **Target Schema:** `public` (all 56 base tables)

### Core DDL Specifications in Migration `0013`
For every table in the public schema (`users`, `projects`, `organisations`, `evidence_items`, `verification_cases`, etc.):

1. **Enable Row Level Security:**
   ```sql
   ALTER TABLE public.<table_name> ENABLE ROW LEVEL SECURITY;
   ```
2. **Define Explicit Application Policy for Backend Operational Roles:**
   Because the FastAPI backend connects as role `postgres` (or `service_role` in administrative contexts), explicit permissive policies ensure backend queries are never throttled:
   ```sql
   CREATE POLICY "allow_backend_postgres" ON public.<table_name>
       FOR ALL
       TO postgres, service_role
       USING (true)
       WITH CHECK (true);
   ```
3. **Define Explicit Deny Policies for Supabase Data API Roles:**
   Explicitly deny all operations for `anon` and `authenticated`:
   ```sql
   CREATE POLICY "deny_anon_access" ON public.<table_name>
       FOR ALL
       TO anon
       USING (false)
       WITH CHECK (false);

   CREATE POLICY "deny_authenticated_access" ON public.<table_name>
       FOR ALL
       TO authenticated
       USING (false)
       WITH CHECK (false);
   ```
4. **Revoke Residual Schema Privileges:**
   Reinforce Discretionary Access Control (DAC):
   ```sql
   REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
   REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
   REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;
   REVOKE USAGE, CREATE ON SCHEMA public FROM anon, authenticated;
   ```

### Execution Command
```bash
alembic -c backend/alembic.ini upgrade head
```

### Workstream 2 Rollback Plan
The migration `downgrade()` block will cleanly revert the security policies and disable RLS if any unforeseen backend permission issue is detected:
```sql
-- Inside downgrade():
ALTER TABLE public.<table_name> DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "allow_backend_postgres" ON public.<table_name>;
DROP POLICY IF EXISTS "deny_anon_access" ON public.<table_name>;
DROP POLICY IF EXISTS "deny_authenticated_access" ON public.<table_name>;
```
Executing `alembic downgrade 0012_verification_center` will restore the database to its exact pre-hardening state in seconds.

---

## 4. Workstream 3: Verification & End-to-End Regression Testing

### Objective
Empirically verify that:
1. Application backend operations remain 100% functional without permission errors.
2. Supabase PostgREST Data API endpoints remain completely inaccessible to unauthenticated and authenticated external callers.
3. Database performance and connection pooling are unaffected.

### Verification Checklist
- [ ] **Run Full Backend Test Suite:**
  ```bash
  pytest backend/tests/ -v
  ```
- [ ] **Run Live PostgreSQL Integration Tests:**
  ```bash
  pytest backend/tests/test_live_postgres.py -v
  pytest backend/tests/test_verification_center.py -v
  ```
- [ ] **Probe Supabase Data API (PostgREST):**
  Execute `probe_supabase_api.py` against `https://rjntmboskzyrsqcetzil.supabase.co/rest/v1/`:
  - Verify `/rest/v1/projects` returns `401 Unauthorized`.
  - Verify calls with placeholder or anonymous tokens return `401` or `403 Forbidden`.
- [ ] **Inspect PostgreSQL Catalog Post-Migration:**
  - Verify `relrowsecurity = True` for all 56 base tables.
  - Verify policy count $\ge 168$ (3 policies $\times$ 56 tables).
- [ ] **Inspect Backend Application Logs:**
  Verify clean startup and connection pool checkout via `uvicorn backend.app.main:app`.

---

## 5. Phase B User Approval Gate

To proceed with the execution of this remediation plan, the user must explicitly approve:
1. Merging `origin/feature/verification-center-backend` into `main` (Option A).
2. Creating and executing migration `0013_rls_hardening.py` on the live Supabase PostgreSQL database.

```text
[ ] APPROVED: Proceed with Phase B Workstreams 1, 2, and 3.
[ ] HOLD: Request modifications to the remediation specification.
```
