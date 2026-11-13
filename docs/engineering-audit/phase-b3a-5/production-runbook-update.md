# Technical Report: Production Runbook Update (Phase B3A.5)

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Component:** `docs/engineering-audit/phase-b3a-3/production-runbook-final.md`  
**Audit Phase:** **Phase B3A.5 — Alembic Timeout Hardening & Final Deployment Readiness**  
**Date:** 2026-11-13  
**Status:** **SYNCHRONIZED & APPROVED**

---

## 1. Overview of Runbook Revisions

The canonical production runbook (`docs/engineering-audit/phase-b3a-3/production-runbook-final.md`) was updated to eliminate the disconnect between external SQL console session settings and the actual Alembic migration execution connection.

---

## 2. Updated Steps Summary

### Step 4: Built-in In-Migration Timeout Enforcement
The runbook now documents that migration `0016_rls_hardening` enforces timeouts internally within the transaction block:
```python
SET LOCAL lock_timeout = '2000ms';
SET LOCAL statement_timeout = '30000ms';
SHOW lock_timeout;
SHOW statement_timeout;
```
If PostgreSQL does not return `2s` (or `2000ms`) and `30s` (or `30000ms`), the migration aborts with `RuntimeError` before any `ALTER TABLE` statement is executed.

To provide secondary defense-in-depth at the connection pool level, the runbook provides the direct connection string parameter format:
```powershell
$env:DATABASE_URL = "$env:DATABASE_URL`?options=-c%20lock_timeout=2000ms%20-c%20statement_timeout=30000ms"
```

### Step 5: Atomic Alembic Execution Contract
Explicitly specifies the exact pre-flight and execution order:
1. `_verify_schema_integrity` (asserts all 61 tables exist in `public`).
2. `_enforce_connection_timeouts` (asserts timeouts on the active connection).
3. 61 sequential `ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;` statements.
4. Updates `alembic_version` to `0016_rls_hardening`.
5. Atomic transaction commit.
