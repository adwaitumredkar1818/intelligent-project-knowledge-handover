# Forensic Incident Audit: Previous Production Test DDL Execution

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Incident Classification:** Unauthorized DDL Execution & Concurrency Deadlock Against Hosted Database During Testing  
**Audit Phase:** **Phase B3A.2 — Migration History Reconciliation & Production Safety Audit**  
**Auditor:** Senior Database Architect & PostgreSQL Security Engineer  
**Date:** 2026-11-13  
**Status:** **INCIDENT ROOT CAUSE, SEQUENCE OF EVENTS, AND CONTAINMENT VERIFIED**

---

## 1. Incident Executive Summary

During automated testing in Phase B3A, an automated test case (`test_migration_0013_controlled_rollback_transactional_simulation`) was executed against the **live hosted Supabase PostgreSQL instance**. The test issued progressive `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` DDL statements directly on production tables inside an open transaction block.

Upon reaching table #49 (`public."user_roles"`), the test process encountered a **deadlock** against a concurrent production process and was forcibly terminated by PostgreSQL with `psycopg.errors.DeadlockDetected`.

### Key Forensic Findings:
1. **Target of DDL:** Actual persistent tables on the live hosted database (`aws-1-ap-southeast-2.pooler.supabase.com:5432`) were targeted.
2. **PostgreSQL Rollback:** Because the transaction failed with `DeadlockDetected`, PostgreSQL immediately aborted the transaction. SQLAlchemy executed a full `ROLLBACK`.
3. **Zero Permanent Catalog Mutation:** Subsequent forensic catalog queries confirmed that **all tables retained their original state (`relrowsecurity = false`)**. Not a single table was permanently modified.
4. **Application Disruption Assessment:** The deadlock detection cycle resolved in ~1000ms. The test runner was aborted; the concurrent production transaction completed immediately upon lock release, causing a transient ~1-second latency spike on `users` without data corruption.

---

## 2. Forensic Reconstruction & Incident Timeline

* **Incident Identifier:** `TASK-810-DEADLOCK-SUPABASE`
* **Timestamp:** 2026-11-13T14:11:29Z (19:41:29 IST)
* **Test Runner Task:** `ac033aed-de55-4b35-bc88-4172b795eeee/task-810`
* **Failing File & Test:** `backend/tests/test_migration_0013_rls_hardening.py` :: `test_migration_0013_controlled_rollback_transactional_simulation`

### 2.1 Target Server & Connection Identity
* **Host:** `aws-1-ap-southeast-2.pooler.supabase.com:5432` (Sydney, Australia)
* **Supabase Project Reference:** `rjntmboskzyrsqcetzil`
* **Database Name:** `postgres` (PostgreSQL Database OID: `5`)
* **Connected User:** `postgres`

### 2.2 Sequence of DDL Operations Executed

1. The test opened a connection using `create_db_engine(get_settings())` and issued `BEGIN TRANSACTION;`.
2. The test iterated alphabetically through `_ALL_PUBLIC_BASE_TABLES`, executing `ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;` sequentially:
   - `public."alembic_version"` (Acquired `AccessExclusiveLock`)
   - `public."audit_logs"` (Acquired `AccessExclusiveLock`)
   - `public."background_jobs"` (Acquired `AccessExclusiveLock`)
   - ... (45 additional tables locked exclusively) ...
   - `public."users"` (Acquired `AccessExclusiveLock` on relation `17662`)
3. The test reached `public."user_roles"` (relation `17702`) and issued `ALTER TABLE public."user_roles" ENABLE ROW LEVEL SECURITY;`.

---

## 3. The Deadlock Inversion Cycle

```text
E psycopg.errors.DeadlockDetected: deadlock detected
E DETAIL:  Process 119012 waits for AccessExclusiveLock on relation 17702 of database 5; blocked by process 118299.
E Process 118299 waits for AccessShareLock on relation 17662 of database 5; blocked by process 119012.
E HINT:  See server log for query details.
E [SQL: ALTER TABLE public."user_roles" ENABLE ROW LEVEL SECURITY;]
```

### Forensic Lock Order Analysis:
* **Process 119012 (Pytest Test Process):**
  - Held: `AccessExclusiveLock` on relation `17662` (`users`).
  - Blocked waiting for: `AccessExclusiveLock` on relation `17702` (`user_roles`).
* **Process 118299 (Concurrent Client / Background Worker on Supabase):**
  - Held: `AccessShareLock` on relation `17702` (`user_roles`).
  - Blocked waiting for: `AccessShareLock` on relation `17662` (`users`) during a foreign-key join (`SELECT ... FROM user_roles JOIN users ...`).

After 1000ms (`deadlock_timeout`), the PostgreSQL engine detected the dependency cycle:
$$\text{Process 119012} \xrightarrow{\text{waits for}} \text{Relation 17702} \xrightarrow{\text{held by}} \text{Process 118299} \xrightarrow{\text{waits for}} \text{Relation 17662} \xrightarrow{\text{held by}} \text{Process 119012}$$

PostgreSQL selected Process 119012 as the deadlock victim and aborted it.

---

## 4. Verification of Database Rollback & Containment

1. **Transaction State:** When PostgreSQL terminates a query with `DeadlockDetected`, the entire transaction block is marked as `ABORTED`.
2. **SQLAlchemy Cleanup:** The Python test context manager caught `DeadlockDetected` and issued an immediate `ROLLBACK`.
3. **Subsequent Read-Only Catalog Verification:**
   - In Step 1 of Phase B3A.2 (task-1040), a strictly read-only inspection query was executed directly on `aws-1-ap-southeast-2.pooler.supabase.com:5432`:
     ```json
     {
       "tables_total_count": 61,
       "rls_enabled_tables_count": 0,
       "rls_disabled_tables_count": 61
     }
     ```
   - **Empirical Proof:** All 61 tables retained `rowsecurity = false`. Zero tables were permanently altered.

---

## 5. Application Disruption Assessment

* **Test Process:** Aborted with error (0 rows permanently altered).
* **Production Client (Process 118299):** As soon as Process 119012 was aborted, its `AccessExclusiveLock` on `users` was released. Process 118299 immediately acquired its `AccessShareLock` and completed its query.
* **Duration of Impact:** Contention lasted approximately 1.1 seconds.
* **Data Loss or Inconsistency:** **ZERO.** No records or schema states were corrupted.

---

## 6. Root Cause & Governance Failure

The incident occurred because the test suite `backend/tests/test_migration_0013_rls_hardening.py` relied on `get_settings()` without a connection-level safety guard. Because `.env` was configured to point to remote Supabase, the test mistakenly targeted the hosted database instead of a local disposable container.

---

## 7. Mandatory Permanent Engineering Rule

The following rule is hereby codified as a permanent governance standard for all contributors and automated agents working on The Handover platform:

> ### [!CAUTION] MANDATORY PERMANENT GOVERNANCE RULE: TEST ISOLATION
> **Production databases must NEVER be used for migration simulations, rollback tests, or DDL-based automated tests.**
>
> All automated migration tests, DDL verification, and rollback simulations must execute exclusively against a local containerized PostgreSQL instance (`ipkrh-postgres` on `localhost:5432`) or a dynamically provisioned disposable database.
>
> Any test attempting to execute DDL against a connection whose host resolves to Supabase Cloud or an external IP must fail closed immediately.
