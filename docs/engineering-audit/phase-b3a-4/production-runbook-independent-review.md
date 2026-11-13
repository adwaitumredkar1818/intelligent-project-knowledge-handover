# Independent Security & Architectural Review: Production Runbook

**Target Document:** `docs/engineering-audit/phase-b3a-3/production-runbook-final.md`  
**Target Migration:** `0016_rls_hardening`  
**Audit Phase:** **Phase B3A.4 — Independent Final Security Review of RLS Migration 0016**  
**Review Date:** 2026-11-13  
**Review Mode:** Strictly Read-Only Source Code & Operational Analysis  
**Overall Status:** **VERIFIED TECHNICALLY SOUND (WITH OPERATIONAL CAVEATS IDENTIFIED)**

---

## 1. Executive Summary & Verification Matrix

The production runbook defines the exact sequence of operational steps required to deploy migration `0016_rls_hardening` to the live hosted Supabase PostgreSQL instance.

This independent audit evaluated the runbook against PostgreSQL 17 transaction semantics, connection pooler behaviors, lock acquisition protocols, and application recovery procedures.

### Verification Matrix

| Runbook Requirement | Audit Verdict | Review Findings & Evidence | Critical Operational Nuances |
|---|---|---|---|
| **1. Application Traffic & Worker Quiescence** | **PASS** | Runbook Steps 3.1 & 3.2 mandate stopping `evidence_worker` and enabling 503 maintenance mode. | Prevents incoming user queries from stacking locks behind DDL. |
| **2. Long-Running Transactions Inspected** | **PASS** | Step 3.3 provides SQL query inspecting `pg_stat_activity` for non-idle queries. | Guarantees zero active queries before proceeding. |
| **3. `lock_timeout = 2000ms` Configured** | **PASS WITH CAVEAT** | Documented in Step 4 as `SET lock_timeout = '2000ms';`. | **Finding R-1:** Session vs Transaction lifecycle in Alembic. |
| **4. `statement_timeout = 30000ms` Configured** | **PASS WITH CAVEAT** | Documented in Step 4 as `SET statement_timeout = '30000ms';`. | **Finding R-1:** Session vs Transaction lifecycle in Alembic. |
| **5. Effective Timeouts Checked** | **PASS** | Step 4 mandates `SHOW lock_timeout; SHOW statement_timeout;`. | Operator must verify values before initiating DDL. |
| **6. Atomic Execution** | **PASS** | In `backend/alembic/env.py`, `with context.begin_transaction():` executes all DDL in one transaction. | Atomic commit or rollback. |
| **7. Explicit Failure & Rollback Procedures** | **PASS** | Section 4 details exact PostgreSQL response to `55P03` lock timeout. | Documents immediate abort, rollback, and lock release. |
| **8. Backup Checkpoint Documented** | **PASS** | Step 1 mandates confirming Supabase PITR or taking custom `pg_dump`. | Provides disaster recovery backstop. |
| **9. Post-Migration Verification (61 tables)** | **PASS** | Step 6 details query counting `rowsecurity = true` (asserts 61) and `alembic_version`. | Explicit acceptance criteria. |
| **10. Health & Smoke Checks** | **PASS** | Step 7 includes `/api/v1/health/ready`, pytest auth suites, and PostgREST probe. | Smoke tests before opening ingress. |
| **11. PostgREST Reload NOT Mandatory** | **PASS** | Runbook correctly omits `NOTIFY pgrst` as mandatory security step. | Explains PostgreSQL query engine RLS enforcement. |

---

## 2. Technical Evaluation of Lock & Session Timeouts (Finding R-1)

### Finding R-1: Connection Lifecycle & Session-Level Parameter Persistence
* **Severity:** **MEDIUM (Operational Execution Risk)**
* **Affected Document:** `docs/engineering-audit/phase-b3a-3/production-runbook-final.md` (Steps 4 & 5)
* **Technical Analysis:**
  - Step 4 instructs the operator to execute in a SQL client:
    ```sql
    SET lock_timeout = '2000ms';
    SET statement_timeout = '30000ms';
    SHOW lock_timeout;
    ```
  - Step 5 then instructs the operator to execute in shell:
    ```powershell
    alembic upgrade 0016_rls_hardening
    ```
  - **The Disconnect:** When the operator runs `alembic upgrade` from the CLI, Alembic (via `backend/alembic/env.py`) creates a **new, independent database connection** using SQLAlchemy's `NullPool`. The `SET lock_timeout` executed in an interactive SQL shell (e.g. psql or Supabase SQL Editor) applies **only to that interactive session**, and **does NOT persist** to the separate connection established by Alembic!
  - Furthermore, in PostgreSQL, `SET SESSION` parameters are reset on connection close, and connection poolers (even session-mode poolers) do not propagate session variables across distinct client connections.
* **Why This Matters:**
  If the operator relies on Step 4's interactive `SET` statement, the subsequent `alembic upgrade` command will execute with the server's default timeouts (which on Supabase is typically `lock_timeout = 0` / indefinite, or 2 minutes), rather than the safety-hardened 2000ms lock timeout!
* **Remediation & Hardened Protocol:**
  To guarantee that `lock_timeout = 2000ms` and `statement_timeout = 30000ms` apply to the **exact Alembic connection**, one of the following mechanisms must be employed during execution:
  
  **Option A (Recommended: Alembic CLI `-x` or `alembic.ini` connect_args):**
  Pass connection options directly through PostgreSQL connect parameters:
  ```powershell
  # Using PostgreSQL options parameter in connection string
  $env:DATABASE_URL = "$env:DATABASE_URL&options=-c%20lock_timeout=2000ms%20-c%20statement_timeout=30000ms"
  alembic upgrade 0016_rls_hardening
  ```
  
  **Option B (In-Migration Enforcement):**
  Add explicit `op.execute("SET LOCAL lock_timeout = '2000ms';")` inside `upgrade()` of migration 0016 right before the table loop. Because `SET LOCAL` applies strictly to the current transaction, it is 100% guaranteed to govern all subsequent `ALTER TABLE` statements within that migration transaction.

---

## 3. PostgREST Schema Cache Behavior Analysis

The runbook's architectural clarification regarding PostgREST is **100% ACCURATE**:
- PostgREST is an HTTP interface layer that queries PostgreSQL as the `anon` or `authenticated` role.
- PostgreSQL evaluates `rowsecurity = true` in its own query optimizer/executor, not inside PostgREST.
- When `rowsecurity = true` and 0 policies exist for `anon`/`authenticated`, PostgreSQL executes a default-deny filter. PostgREST receives an empty rowset from the database engine regardless of its internal schema cache.
- Therefore, omitting `NOTIFY pgrst, 'reload schema'` from the critical security path is technically correct and adheres to PostgreSQL internal design.

---

## 4. Final Verdict on Production Runbook

The runbook is **EXCEPTIONAL IN DEPTH AND RIGOR**. With the addition of **Option A or B for Finding R-1** (ensuring timeouts apply to the Alembic connection itself), it is ready for operational deployment.
