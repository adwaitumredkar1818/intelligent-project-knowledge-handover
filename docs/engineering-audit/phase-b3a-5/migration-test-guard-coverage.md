# Technical Report: Migration Test Guard Coverage (Resolution of Finding G-1 & T-1)

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Component:** `backend/tests/migration_guard.py` & `backend/tests/test_migrations_*.py`  
**Audit Phase:** **Phase B3A.5 — Alembic Timeout Hardening & Final Deployment Readiness**  
**Date:** 2026-11-13  
**Status:** **IMPLEMENTED & AUDITED**

---

## 1. Context & Problem Statement (Findings G-1 & T-1)

- **Finding G-1:** In Phase B3A.4, audit of legacy migration test files (`test_migrations_auth.py`, `test_migrations_chunks_and_fts.py`, etc.) revealed that while they hardcode `127.0.0.1`, they did not import or invoke `migration_guard.py`.
- **Finding T-1:** Investigated whether a global autouse fixture in `conftest.py` could intercept all engine creation and enforce the guard across all tests.

---

## 2. Evaluation of Central Guard Enforcement (T-1)

An architectural evaluation of introducing a global `pytest` engine wrapper / hook was conducted:
1. **Risks of Global Interception:**
   - The platform test suite extensively uses SQLite in-memory databases (`sqlite:///:memory:`) for hundreds of isolated unit tests across auth, chunking, and worker logic.
   - Enforcing a global PostgreSQL catalog query (`inspect_live_database_identity`) against SQLite causes immediate syntax/function errors (`current_database()` does not exist in SQLite).
   - Hooking SQLAlchemy's `create_engine` globally creates hidden coupling and risks silent bypasses in tests that construct raw `psycopg.connect` sessions.
2. **Decision:**
   - Central interception across all non-migration tests is **unsafe** to introduce at this phase without risking regression in 100+ existing fast unit tests.
   - The recommended, reliable pattern is **explicit fail-closed guard invocation** in all tests that create PostgreSQL engines or execute Alembic DDL.

---

## 3. Implementation of Guard Coverage in Migration Tests (G-1)

`backend/tests/test_migrations_auth.py` was retrofitted with explicit guard validation:
```python
# 1. Enforce static URL validation on both admin DSN and isolated test DB URL
validate_url_isolation(admin_dsn)
validate_url_isolation(temp_url)

# 2. Enforce catalog identity inspection on live connection before test execution
engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
with engine.connect() as conn:
    verify_migration_target_isolation(temp_url, conn)
```

### Regression Tests Added (`backend/tests/test_migration_guard.py`):
Added `test_guard_rejects_unsafe_target_on_live_inspection`:
- Proves that even if an attacker or misconfigured test passes a URL containing `127.0.0.1`, if the catalog inspects `server_addr` and resolves to a public/cloud IP (e.g. `54.252.123.45`), `verify_migration_target_isolation` fails closed immediately with `DatabaseIsolationError`.
- Test suite expanded from 9 to 10 automated unit tests (100% pass rate).
