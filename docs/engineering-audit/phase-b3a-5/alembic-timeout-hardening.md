# Technical Report: Alembic Timeout Hardening (Resolution of Finding R-1)

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Component:** `infrastructure/database/migrations/versions/20261113_0016_rls_hardening.py`  
**Audit Phase:** **Phase B3A.5 — Alembic Timeout Hardening & Final Deployment Readiness**  
**Date:** 2026-11-13  
**Status:** **IMPLEMENTED, TESTED & VERIFIED**

---

## 1. Context & Problem Statement (Finding R-1)

During Phase B3A.4, independent security review identified that setting session parameters interactively via SQL:
```sql
SET lock_timeout = '2000ms';
SET statement_timeout = '30000ms';
```
did **not** reliably survive across connection boundaries to the independent database connection opened by Alembic CLI during `alembic upgrade`. If an operator relied solely on an external SQL console before running Alembic, the migration runner would execute with Supabase default timeouts (typically `lock_timeout = 0`, indefinite), re-introducing the risk of lock accumulation.

---

## 2. Implemented Architecture & Solution

To resolve Finding R-1 with 100% reliability, timeout enforcement was integrated **directly inside the migration transaction itself**:

```python
def _enforce_connection_timeouts(bind: sa.engine.Connection) -> None:
    """Enforce strict lock_timeout and statement_timeout on the active migration connection.

    Requirements:
      - lock_timeout <= 2000ms (2s) to prevent blocking concurrent transactions.
      - statement_timeout <= 30000ms (30s) to abort runaway operations.
    Fails closed if the effective settings cannot be verified.
    """
    if _is_offline():
        return

    # Apply transaction-local timeout configuration
    bind.execute(sa.text("SET LOCAL lock_timeout = '2000ms';"))
    bind.execute(sa.text("SET LOCAL statement_timeout = '30000ms';"))

    # Verify effective values directly from PostgreSQL engine
    lt_str = bind.execute(sa.text("SHOW lock_timeout;")).scalar_one()
    st_str = bind.execute(sa.text("SHOW statement_timeout;")).scalar_one()

    # Parse and assert lock_timeout (e.g. '2s' or '2000ms')
    lt_normalized = str(lt_str).strip().lower()
    if lt_normalized not in {"2s", "2000ms"}:
        raise RuntimeError(
            f"Pre-migration timeout assertion failed: effective lock_timeout is '{lt_str}', "
            "expected '2s' or '2000ms'."
        )

    # Parse and assert statement_timeout (e.g. '30s' or '30000ms')
    st_normalized = str(st_str).strip().lower()
    if st_normalized not in {"30s", "30000ms"}:
        raise RuntimeError(
            f"Pre-migration timeout assertion failed: effective statement_timeout is '{st_str}', "
            "expected '30s' or '30000ms'."
        )
```

### Key Engineering Invariants Satisfied:
1. **Applied on Exact Connection:** Executed through Alembic's active `bind` connection (`op.get_bind()`).
2. **Transaction-Local (`SET LOCAL`):** Scoped strictly to the migration's `BEGIN ... COMMIT` block. Does not alter connection pool defaults or application transactions.
3. **Pre-Flight Assertion:** Querying `SHOW lock_timeout;` and `SHOW statement_timeout;` validates PostgreSQL engine acceptance before a single `ALTER TABLE` DDL statement is dispatched.
4. **Fail-Closed Semantics:** Any mismatch immediately raises `RuntimeError`, aborting the transaction before DDL execution.
5. **Zero Secrets Logging:** Only the parsed configuration string is reported; database URLs and passwords remain completely unformatted.
6. **Offline Safe:** Bypasses live queries when executing `alembic upgrade --sql` (offline generation).
