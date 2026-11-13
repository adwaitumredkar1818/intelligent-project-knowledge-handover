# Runtime Role Architecture Assessment
## In-Depth Evaluation of PostgreSQL Roles, Connection Pooling & Context Isolation

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Database Host:** `aws-1-ap-southeast-2.pooler.supabase.com:5432` (Supabase Cloud)  
**Pooler Engine:** Supavisor (Session Mode on Port 5432)  
**Audit Phase:** Phase B2.1 Technical Reassessment  
**Date:** 2026-11-13  
**Auditor Roles:** Principal Database Architect, Cloud Infrastructure Engineer  

---

## 1. Executive Summary

A core question in hardening The Handover's database is whether the application backend should continue connecting as role `postgres` or transition to a dedicated, unprivileged PostgreSQL runtime role (e.g. `handover_app`, `handover_worker`).

Because `postgres` holds `rolbypassrls = true` in Supabase, any connection authenticated as `postgres` bypasses Row Level Security entirely. However, altering the application connection role in a hosted Supabase environment introduces critical infrastructure constraints with the Supavisor connection pooler, credential management, Alembic migrations, and background worker concurrency.

This document evaluates four distinct runtime-role architectural models across seven operational and security dimensions.

---

## 2. Comparative Evaluation of Runtime-Role Architectural Alternatives

### Alternative A: Keep Current `postgres` Runtime Role (With Perimeter RLS)

- **Mechanics:**
  - The FastAPI application, background worker, and Alembic migrations continue connecting over port 5432 using `postgres.rjntmboskzyrsqcetzil`.
  - Row Level Security (RLS) is enabled across all 56 public tables.
  - Zero RLS policies are created for `postgres` (since `postgres` bypasses RLS).
  - Explicit restrictive policies or default-deny rules are enforced against external PostgREST roles (`anon`, `authenticated`).
- **Supabase Pooler Compatibility:**
  - **100% Native & Proven.** Fully compatible with existing `DATABASE_URL` and Supavisor session mode. Zero risk of pooler rejection.
- **Required Privileges & Ownership:**
  - `postgres` owns all 56 tables, holds `CREATEROLE`, `CREATEDB`, and full schema/table privileges.
- **Alembic Migration Compatibility:**
  - **Flawless.** Alembic runs DDL seamlessly as the table owner.
- **Connection-Pool Safety:**
  - Standard SQLAlchemy connection pooling (`pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`) operates with zero state leakage.
- **Background Worker Compatibility:**
  - **Flawless.** The background composite worker executes bulk ingestion, OCR, chunking, and reconstruction across multiple projects without role switching or context contention.
- **Security Limitations:**
  - RLS provides **defense-in-depth against external API exposure (PostgREST)**, but provides **zero internal protection** against SQL injection or application-level logic flaws. Application multi-tenancy relies 100% on FastAPI RBAC and SQLAlchemy query filters.
- **Operational Complexity:**
  - **Lowest.** No new database credentials, no new users to manage, zero code changes required.

---

### Alternative B: Dedicated Restricted Application Runtime Role (`handover_app`)

- **Mechanics:**
  - Create a new PostgreSQL role:
    ```sql
    CREATE ROLE handover_app WITH LOGIN PASSWORD '<secure_password>' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
    GRANT USAGE ON SCHEMA public TO handover_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO handover_app;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO handover_app;
    ```
  - FastAPI connects using `handover_app`.
  - Because `handover_app` has `NOBYPASSRLS` and does *not* own the tables, all queries executed by `handover_app` are strictly subjected to Row Level Security policies.
- **Supabase Pooler Compatibility (CRITICAL UNCERTAINTY):**
  - **HIGH RISK / UNVERIFIED PROVIDER CONSTRAINT:** In hosted Supabase, the Supavisor pooler authenticates connections formatted as `<username>.<project_ref>`.
  - Supavisor maintains its own user credential cache. In standard Supabase plans, Supavisor is pre-configured to pool connections *only* for user `postgres`. Creating a new role via SQL does **not** automatically configure Supavisor to accept connections for `handover_app.rjntmboskzyrsqcetzil`.
  - If Supavisor rejects custom role authentication, the application would be forced to connect directly to port 5432 (bypassing the pooler) or port 6543, introducing connection starvation under load.
  - **Mandatory Precondition:** A provider-side check in the Supabase Dashboard / Support is required to verify whether custom pooled users are supported on this project tier.
- **Required Privileges & Ownership:**
  - Tables must remain owned by `postgres` so Alembic can manage DDL. `handover_app` is granted DML privileges only.
  - New tables created by future migrations must automatically grant DML to `handover_app` via `ALTER DEFAULT PRIVILEGES`.
- **Alembic Migration Compatibility:**
  - Dual-role split required: Alembic must continue connecting as `postgres` (for schema changes), while FastAPI connects as `handover_app`.
- **Security Scope:**
  - Provides genuine database-level multi-tenant isolation *inside* the application, provided session context (Alternative D) is also implemented.
- **Operational Complexity:**
  - **High.** Requires provisioning new secrets, updating deployment environments, managing default privileges across migrations, and verifying Supavisor compatibility.

---

### Alternative C: Separate API (`handover_api`) and Worker (`handover_worker`) Runtime Roles

- **Mechanics:**
  - Splits runtime privileges into two distinct non-privileged roles:
    1. `handover_api`: Granted DML on application tables; subject to tenant RLS policies.
    2. `handover_worker`: Granted read access across all evidence/chunks, write access to jobs, knowledge items, and extraction tables.
- **Supabase Pooler Compatibility:**
  - **Extreme Risk.** Requires Supavisor to support *two* distinct custom pooled roles simultaneously.
- **Required Privileges & Ownership:**
  - Highly complex grant matrix. The worker needs broad cross-tenant read privileges to process documents and chunks, while the API needs strict tenant isolation.
- **Background Worker Contradiction:**
  - Handover's background worker is a unified composite process (`CompositeWorkerService`) that performs multi-tenant processing (e.g. ingesting Jira issues for Project A while indexing document chunks for Project B). Restricting the worker via RLS creates severe operational friction or requires the worker to hold `BYPASSRLS`, which defeats the purpose of the split.
- **Operational Complexity:**
  - **Extreme.** Managing dual credentials, disparate pooler configurations, and granular table-level grants across 56 tables is unjustifiably complex for the current stage.

---

### Alternative D: Transaction-Local Application Context (`SET LOCAL` / `set_config`)

- **Mechanics:**
  - Can be paired with either Alternative A (using `SET LOCAL ROLE`) or Alternative B (using session variables).
  - When FastAPI opens a database session, it executes:
    ```sql
    SELECT set_config('app.current_user_id', :user_id, true);
    SELECT set_config('app.current_org_id', :org_id, true);
    SELECT set_config('app.current_project_id', :project_id, true);
    ```
  - The third argument (`is_local = true`) ensures these variables are scoped strictly to the current transaction and are automatically purged on `COMMIT` or `ROLLBACK`.
  - RLS policies on tables evaluate `current_setting('app.current_project_id', true)`.
- **Supabase Pooler Compatibility:**
  - **Compatible with Session Pooler (Port 5432), Fragile with Transaction Pooler (Port 6543):**
    - In Supavisor *Session Mode* (Port 5432), connection state is pinned to the client socket for the lifetime of the session. `set_config(..., true)` is safely discarded at transaction boundaries.
    - In Supavisor *Transaction Mode* (Port 6543), if a developer accidentally runs `set_config(..., false)` (session-scoped), the variable bleeds into subsequent transactions executed by different users on that pooled socket, causing **catastrophic cross-tenant data leakage**.
- **Latency & Performance Overhead:**
  - Setting context requires an extra SQL round-trip at the beginning of every request. Over a remote cloud pooler with 20–50ms latency, this adds a non-trivial latency tax to every API interaction.
- **The Source-Level ACL Disqualification (AGENTS.md Rule #2):**
  - Project-level context (`app.current_project_id`) **cannot enforce source-level permissions**. In The Handover, evidence items are restricted based on delegated per-user OAuth tokens (GitHub private repos, Jira issue security levels).
  - Even with `app.current_project_id` set, an RLS policy cannot determine whether User X has access to Evidence Y without querying `user_source_authorisations`, `source_access_policies`, and checking token status. Doing this inside SQL RLS policies on high-volume chunk queries would severely degrade retrieval throughput.
- **Operational Complexity:**
  - **High.** Requires rewriting FastAPI session dependencies (`deps.py`), wrapping all background worker loops in synthetic transaction contexts, and instrumenting strict session cleanup guards.

---

## 3. Detailed Architectural Comparison Matrix

| Evaluation Criteria | Alternative A: Current `postgres` (Perimeter RLS) | Alternative B: Dedicated `handover_app` Role | Alternative C: Split API / Worker Roles | Alternative D: Transaction-Local Context (`SET LOCAL`) |
|---|---|---|---|---|
| **Supabase Pooler Safety** | **Verified 100% Compatible** | **Unverified Provider Constraint** (Supavisor user mapping) | **Unverified Provider Constraint** (Multiple custom users) | Compatible on Port 5432; High Leakage Risk on Port 6543 |
| **Alembic DDL Execution** | **Zero Friction** (Runs as table owner) | Requires dual-role setup (Migrations as `postgres`) | Requires dual-role setup | Zero Friction (Alembic skips context) |
| **Query Latency Overhead** | **0 ms** (Engine skips RLS quals) | Low (SQL evaluation of quals) | Low | **+20ms to +50ms per request** (Extra SQL round-trip) |
| **PostgREST Neutralization** | **100% Secure** (Blocks `anon` & `authenticated`) | **100% Secure** | **100% Secure** | **100% Secure** |
| **Internal SQLi Protection** | Low (Relies on SQLAlchemy parameterization) | High (Database enforces policy) | Maximum | High (Database enforces policy) |
| **Source ACL Integrity** | **100% Preserved** (Enforced in Python service layer) | **High Leakage Risk** if SQL policy is project-scoped | High Leakage Risk | **High Leakage Risk** if SQL policy is project-scoped |
| **Worker Concurrency Safety** | **100% Safe** (Processes batch jobs unimpeded) | Complex worker policy exceptions | High operational overhead | High friction (Must spoof context per job) |
| **Operational Feasibility** | **Immediate** (Single tracked migration) | Requires provider dashboard coordination | Disproportionate overhead | Requires extensive application refactor |

---

## 4. Definitive Role Architecture Conclusion

1. **Alternative A (Perimeter RLS under `postgres`) is the Only Immediately Feasible Architecture:**
   Because Handover runs on hosted Supabase, introducing custom runtime roles (Alternative B or C) requires provider-side confirmation that Supavisor supports custom pooled user accounts. Without this verification, switching roles risks breaking backend database connectivity entirely.
2. **Alternative D is Fundamentally at Odds with AGENTS.md Rule #2:**
   Because source-level access control requires dynamic evaluation of external delegated credentials and token scopes, database-level project context cannot safely govern evidence access.
3. **The Recommended Phased Approach:**
   - **Phase B (Immediate):** Implement Alternative A (Perimeter RLS). Enable RLS across all 56 tables to permanently eliminate the PostgREST exposure risk while keeping the backend running seamlessly as `postgres`.
   - **Phase C (Future Hardening Gate):** Verify Supabase Supavisor support for custom roles. If confirmed, evaluate transitioning the API runtime to a dedicated role with explicit service grants.
