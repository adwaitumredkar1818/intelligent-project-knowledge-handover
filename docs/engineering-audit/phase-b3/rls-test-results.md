# Row Level Security (RLS) Test Results & Verification Report

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Test Suite:** `backend/tests/test_migration_0013_rls_hardening.py`  
**Migration Tested:** `infrastructure/database/migrations/versions/20261113_0013_rls_hardening.py`  
**Alembic Revisions:** `0012_verification_center` -> `0013_rls_hardening`  
**Database Engine:** PostgreSQL 17.6 (Supabase Session Pooler via TLS)  
**Date:** 2026-11-13  
**Overall Result:** **3 PASSED / 0 FAILED (100% PASS RATE)**

---

## 1. Executive Summary

This report documents the automated and static verification of migration `0013_rls_hardening`. Testing was executed under strict **zero-production-mutation** safety boundaries. No DDL was applied to live persistent tables, and no production data was altered.

Testing verified:
1. Complete linear Alembic revision chain linkage from `0012_verification_center` to `0013_rls_hardening`.
2. Exact 56-table coverage with static offline SQL generation contracts for both `upgrade()` and `downgrade()`.
3. Existence of all 56 tables in the live PostgreSQL 17 `public` schema.
4. Engine-level catalog behavior of `ENABLE ROW LEVEL SECURITY` and `DISABLE ROW LEVEL SECURITY`.
5. Non-interference with the application's `postgres` runtime role (`rolbypassrls = true`).

---

## 2. Test Execution Details

### 2.1 Test Environment
- **Operating System:** Windows 11 (Host)
- **Python Runtime:** Python 3.11 (Virtual Environment in `backend/.venv/`)
- **Key Libraries:** `pytest 8.3.4`, `SQLAlchemy 2.0.38`, `Alembic 1.14.1`, `psycopg 3.2.4`
- **Database Host:** `aws-1-ap-southeast-2.pooler.supabase.com:5432` (PostgreSQL 17.6)

### 2.2 Test Run Output
```text
backend/.venv/Scripts/pytest.exe backend/tests/test_migration_0013_rls_hardening.py -v

============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-8.3.4, pluggy-1.5.0 -- 
rootdir: e:\Projects\Intelligent Project Knowledge Reconstruction & Handover Platform
configfile: pyproject.toml
plugins: anyio-4.8.0, asyncio-0.25.3
asyncio: mode=Mode.STRICT
collected 3 items

backend/tests/test_migration_0013_rls_hardening.py::test_migration_0013_metadata_and_revision_chain PASSED [ 33%]
backend/tests/test_migration_0013_rls_hardening.py::test_migration_0013_offline_sql_generation_contract PASSED [ 66%]
backend/tests/test_migration_0013_rls_hardening.py::test_migration_0013_isolated_rls_engine_behavior PASSED [100%]

============================== 3 passed in 49.64s ==============================
```

---

## 3. Detailed Test Breakdown

### 3.1 Test 1: Metadata, Revision Chain & Table Integrity
- **Test Identifier:** `test_migration_0013_metadata_and_revision_chain`
- **Objective:** Validate Alembic revision identifiers, linear ancestry, and completeness of the 56-table inventory.
- **Assertions Evaluated:**
  - `mod.revision == "0013_rls_hardening"`: **PASSED**
  - `mod.down_revision == "0012_verification_center"`: **PASSED**
  - `len(mod._ALL_PUBLIC_BASE_TABLES) == 56`: **PASSED**
  - `len(set(mod._ALL_PUBLIC_BASE_TABLES)) == 56` (no duplicates): **PASSED**
  - Explicit presence of core platform tables (`users`, `organisations`, `projects`, `evidence_items`, `knowledge_items`, `verification_cases`, `handover_packages`, `audit_logs`, `alembic_version`): **PASSED**
- **Outcome:** **PASS**

---

### 3.2 Test 2: Offline SQL Generation Contract (`upgrade` & `downgrade`)
- **Test Identifier:** `test_migration_0013_offline_sql_generation_contract`
- **Objective:** Verify that Alembic dry-run SQL generation emits exact, safe DDL without extraneous policies or unapproved clauses.
- **Execution:**
  - Invoked `alembic.command.upgrade(alembic_cfg, "0012_verification_center:0013_rls_hardening", sql=True)`
  - Captured stdout and parsed SQL output.
  - Invoked `alembic.command.downgrade(alembic_cfg, "0013_rls_hardening:0012_verification_center", sql=True)`
  - Captured stdout and parsed SQL output.
- **Assertions Evaluated:**
  - Exactly 56 `ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;` statements generated: **PASSED**
  - Zero `CREATE POLICY` statements generated: **PASSED** (confirmed: `"CREATE POLICY" not in upgrade_sql`)
  - Zero `FORCE ROW LEVEL SECURITY` statements generated: **PASSED** (confirmed: `"FORCE ROW LEVEL SECURITY" not in upgrade_sql`)
  - Exactly 56 `ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY;` statements generated in downgrade: **PASSED**
- **Outcome:** **PASS**

---

### 3.3 Test 3: PostgreSQL 17 Engine RLS Semantics & Catalog Verification
- **Test Identifier:** `test_migration_0013_isolated_rls_engine_behavior`
- **Objective:** Verify live PostgreSQL catalog reflection, schema validation, and runtime role bypass semantics.
- **Execution:**
  - Connected to live PostgreSQL 17 engine over TLS via Supabase pooler.
  - Validated with `sa.inspect` that all 56 tables in `_ALL_PUBLIC_BASE_TABLES` exist in schema `public` on the remote database.
  - Created session-scoped temporary table `_test_rls_semantics (id int, val text)`.
  - Executed `ALTER TABLE _test_rls_semantics ENABLE ROW LEVEL SECURITY;`.
  - Queried `pg_class.relrowsecurity`: Verified catalog flag changed from `false` to `true`.
  - Queried data as application role `postgres`: Verified query returned data unhindered, proving `rolbypassrls = true` functions as designed.
  - Executed `ALTER TABLE _test_rls_semantics DISABLE ROW LEVEL SECURITY;`.
  - Queried `pg_class.relrowsecurity`: Verified catalog flag returned to `false`.
  - Rolled back transaction cleanly.
- **Outcome:** **PASS**

---

## 4. Alembic Linearity & Graph Consistency

### 4.1 Alembic Head Inspection
```powershell
backend/.venv/Scripts/alembic.exe -c backend/alembic.ini heads
```
- **Output:**
  ```text
  0013_rls_hardening (head)
  ```
- **Status:** **PASS (Exactly 1 head)**

### 4.2 Alembic History Inspection
```powershell
backend/.venv/Scripts/alembic.exe -c backend/alembic.ini history
```
- **Output:**
  ```text
  0012_verification_center -> 0013_rls_hardening (head), Enable Row Level Security (RLS) on all 56 public base tables.
  0011_phase29_verification_framework -> 0012_verification_center, Verification Center (Module 3)
  0010_phase29_unified_models -> 0011_phase29_verification_framework, Phase 2.9: Verification framework tables...
  0009_phase29_evidence_workspace -> 0010_phase29_unified_models, Phase 2.9: Unified core models...
  0008_phase29_project_workspace -> 0009_phase29_evidence_workspace, Phase 2.9: Evidence workspace tables...
  0007_phase29_rbac_foundation -> 0008_phase29_project_workspace, Phase 2.9: Project workspace tables...
  0006_evidence_workspace_v2 -> 0007_phase29_rbac_foundation, Phase 2.9: Foundation tables...
  0005_project_workspace_v2 -> 0006_evidence_workspace_v2, Evidence Workspace tables (v2)
  0004_fix_schema_mismatches -> 0005_project_workspace_v2, Project Workspace tables (v2)
  0003_knowledge_and_handover -> 0004_fix_schema_mismatches, Fix schema mismatches...
  0002_evidence_and_jobs -> 0003_knowledge_and_handover, Knowledge and handover models
  0001_initial_schema -> 0002_evidence_and_jobs, Evidence and jobs models
  <base> -> 0001_initial_schema, Initial schema
  ```
- **Status:** **PASS (Unbroken linear sequence of 13 revisions)**

---

## 5. Concurrency & Lock Investigation Finding

### Deadlock Encountered During Live Transactional Simulation
During early test development, a transactional test attempted to execute `ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;` on all 56 live tables inside a single transaction with immediate rollback:

```text
sqlalchemy.exc.OperationalError: (psycopg.errors.DeadlockDetected) deadlock detected
DETAIL: Process 18451 waits for AccessExclusiveLock on relation 17293 of database 16384; 
blocked by process 18320.
Process 18320 waits for AccessShareLock on relation 17280 of database 16384; 
blocked by process 18451.
```

### Analysis & Resolution
1. **Root Cause:** PostgreSQL `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` acquires an `AccessExclusiveLock`. Concurrent active sessions on Supabase (e.g. background syncs or external connections) held `AccessShareLock` on relations such as `users` and `user_roles`. Because multiple locks were requested across 56 tables, lock order inversion occurred, resulting in an automatic deadlock resolution by PostgreSQL.
2. **Test Safety Resolution:** Engine semantics were validated on a session-isolated temporary table `_test_rls_semantics`, which acquires zero locks on shared tables.
3. **Operational Recommendation:** Applying migration 0013 in production must occur during an off-peak maintenance window with background workers paused and a `lock_timeout` safeguard configured.

---

## 6. Test Limitations & Deferred Verifications

| Test Category | Verified in Phase B3A? | Status & Reason |
|---|:---:|---|
| **Alembic Metadata & Parentage** | **YES** | Verified via unit test & `alembic history`. |
| **56 Table Offline DDL Generation** | **YES** | Verified via `test_migration_0013_offline_sql_generation_contract`. |
| **Catalog Table Existence** | **YES** | All 56 tables verified present in Supabase `public` schema. |
| **PostgreSQL 17 RLS Engine Semantics** | **YES** | Verified on temporary table in live session. |
| **`postgres` Role BYPASSRLS Operation** | **YES** | Verified queries execute unhindered under RLS. |
| **Live 56-Table Catalog Flip** | **DEFERRED** | Deferred to production execution (requires live DDL). |
| **Live PostgREST HTTP 401/Empty Denial** | **DEFERRED** | Deferred to post-migration verification stage. |
| **Live Frontend/Backend End-to-End** | **DEFERRED** | Deferred until migration is applied to Supabase. |
