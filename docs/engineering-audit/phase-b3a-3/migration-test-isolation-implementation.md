# Migration Test Isolation Guard: Technical Implementation Specification

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Component:** Automated Database & Migration Test Safety Guard  
**Implementation File:** `backend/tests/migration_guard.py`  
**Test Suite:** `backend/tests/test_migration_guard.py`  
**Integration Point:** `backend/tests/test_migration_0016_rls_hardening.py`  
**Audit Phase:** **Phase B3A.3 — Migration Test Isolation & Production Runbook Finalization**  
**Date:** 2026-11-13  
**Status:** **IMPLEMENTED, VERIFIED & PASSING 100% OF TESTS**

---

## 1. Executive Summary

In response to the Task 810 live database testing incident, a **permanent, fail-closed test connection guard** has been implemented in `backend/tests/migration_guard.py`.

The guard prevents automated test suites, migration tests, and DDL scripts from targeting hosted remote databases (specifically the Supabase project `rjntmboskzyrsqcetzil` or any non-local PostgreSQL host).

### Core Architectural Guarantees:
1. **Zero Redirection:** The guard **never** silently redirects a remote connection to a local database; it fails closed immediately with an explicit, actionable `DatabaseIsolationError`.
2. **Credential Sanitization:** Error messages **never** print connection strings, passwords, or secret tokens.
3. **Anti-Bypass Protection:** The guard validates both static connection URLs **and** live server catalog identity (`inet_server_addr()`, `current_user`). Changing a hostname string (e.g. DNS spoofing or hosts file aliasing) cannot bypass the guard.
4. **Zero Impact on Existing Unit Tests:** Lightweight tests using SQLite in-memory or mocks continue to run unaffected.

---

## 2. Guard Architecture & Invariant Enforcement

```mermaid
flowchart TD
    Start["Test Invocates Migration / DDL Test"] --> S1["Static URL Isolation Guard<br/>(validate_url_isolation)"]
    
    subgraph Static_Checks ["Static URL Checks"]
        S1 --> C1{"Is URL Empty or Malformed?"}
        C1 -- "Yes" --> Err1["Raise DatabaseIsolationError<br/>('Malformed connection')"]
        C1 -- "No" --> C2{"Contains Supabase Project Ref<br/>('rjntmboskzyrsqcetzil')?"}
        C2 -- "Yes" --> Err2["Raise DatabaseIsolationError<br/>('Production project identifier')"]
        C2 -- "No" --> C3{"Host matches forbidden pattern<br/>('supabase.com', 'aws-', 'pooler')?"}
        C3 -- "Yes" --> Err3["Raise DatabaseIsolationError<br/>('Forbidden hosted pattern')"]
        C3 -- "No" --> C4{"Host in Approved Local Hosts<br/>(localhost, 127.0.0.1, ::1, ipkrh-postgres)?"}
        C4 -- "No" --> Err4["Raise DatabaseIsolationError<br/>('External database forbidden')"]
        C4 -- "Yes" --> S2["Dynamic Server Catalog Guard<br/>(inspect_live_database_identity)"]
    end

    subgraph Dynamic_Checks ["Live Server Identity Catalog Checks"]
        S2 --> Q["Execute SELECT inet_server_addr(),<br/>current_user, current_database()..."]
        Q --> C5{"Query fails or returns NULL?"}
        C5 -- "Yes" --> Err5["Raise DatabaseIsolationError<br/>('Missing database identity')"]
        C5 -- "No" --> C6{"Runtime user matches<br/>production project ref?"}
        C6 -- "Yes" --> Err6["Raise DatabaseIsolationError<br/>('Production runtime user')"]
        C6 -- "No" --> C7{"Server IP is Loopback or<br/>Docker Bridge (172.16.0.0/12)?"}
        C7 -- "No (External IP)" --> Err7["Raise DatabaseIsolationError<br/>('Non-local server address')"]
        C7 -- "Yes" --> Pass["TEST PERMITTED TO EXECUTE<br/>(Isolated Local Container Confirmed)"]
    end
```

---

## 3. Algorithmic Implementation Details

### 3.1 Static URL Validation (`validate_url_isolation`)
* **Approved Local Hostnames:**
  ```python
  _APPROVED_LOCAL_HOSTNAMES = frozenset({
      "localhost",
      "127.0.0.1",
      "::1",
      "ipkrh-postgres",  # Docker compose service name
  })
  ```
* **Forbidden Signatures:**
  - Project references: `rjntmboskzyrsqcetzil`
  - Host patterns: `supabase.com`, `supabase.co`, `pooler.supabase.com`, `aws-1-`, `aws-`, `.rds.amazonaws.com`, `.azure.com`, `.google.com`.
* **Action:** Rejects any match before any network socket is opened.

---

### 3.2 Live Catalog Identity Inspection (`inspect_live_database_identity`)
* **Execution:** Queries PostgreSQL engine metadata:
  ```sql
  SELECT 
    current_database(), 
    current_user, 
    inet_server_addr()::text, 
    inet_server_port(), 
    version();
  ```
* **Fail-Closed Mandate:** If the query fails, times out, or returns `NULL` for `current_database` or `current_user`, it immediately raises `DatabaseIsolationError`.

---

### 3.3 Anti-Bypass Deep IP Verification (`validate_server_identity_isolation`)
* **The Bypass Vector Prevented:** A developer or script might alias `localhost` to `52.65.247.42` in `hosts` or use SSH port forwarding to Supabase.
* **The Defense:** The guard inspects the server's own reported IP address (`inet_server_addr()`):
  ```python
  clean_addr = identity.server_addr.split("/")[0].strip()
  ip = ipaddress.ip_address(clean_addr)

  is_loopback = ip.is_loopback
  is_docker_bridge = ip.version == 4 and ip in _DOCKER_BRIDGE_NETWORK  # 172.16.0.0/12

  if not (is_loopback or is_docker_bridge):
      raise DatabaseIsolationError(...)
  ```
  Even if the client connects to `localhost`, if the server's internal address is remote (e.g. AWS Sydney `52.65.247.42` or IPv6 `2406:da1c:...`), the test is immediately aborted.

---

## 4. Credential Sanitization & Actionable Guidance

In compliance with security directives, error messages **never expose passwords, user tokens, or connection strings**.

Every failure appends the standard guidance block:
```text
[MIGRATION TEST GUARD INSTRUCTION]
Migration and DDL tests are forbidden from targeting remote or production databases.
To configure an approved local test database:
  1. Start the local PostgreSQL container via Docker:
       docker compose up -d postgres
  2. Configure local environment variables in your test settings or .env:
       POSTGRES_HOST=127.0.0.1
       POSTGRES_PORT=5432
       POSTGRES_DB=knowledge_handover
       DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/knowledge_handover
```

---

## 5. Integration into Test Suite

In [test_migration_0016_rls_hardening.py](file:///e:/Projects/Intelligent%20Project%20Knowledge%20Reconstruction%20&%20Handover%20Platform/backend/tests/test_migration_0016_rls_hardening.py), the guard is executed prior to any schema inspection or DDL:

```python
def test_migration_0016_isolated_rls_engine_behavior() -> None:
    settings = get_settings()
    engine = create_db_engine(settings)

    try:
        with engine.connect() as conn:
            # Enforce permanent fail-closed test isolation guard before any inspection or DDL
            verify_migration_target_isolation(settings.database.url.get_secret_value(), conn)
            ...
```
