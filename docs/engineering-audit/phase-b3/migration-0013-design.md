# Migration 0013 Design Specification: Row Level Security Hardening

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Migration Target:** `infrastructure/database/migrations/versions/20261113_0013_rls_hardening.py`  
**Revision ID:** `0013_rls_hardening`  
**Parent Revision:** `0012_verification_center`  
**Date:** 2026-11-13  
**Status:** **AUTHORED & VERIFIED LOCALLY (PENDING PRODUCTION APPROVAL)**  

---

## 1. Executive Summary & Design Scope

Migration `0013_rls_hardening` codifies the approved Phase B2.1 Alternative A architectural recommendation for The Handover platform.

The migration enables PostgreSQL Row Level Security (RLS) across all **56 verified public base tables** in the platform database. It introduces an un-bypassable engine-level perimeter defense against unauthorized external API calls (e.g. Supabase PostgREST) while preserving the platform's existing authentication, worker concurrency, and source-level access control architectures.

---

## 2. Approved Architectural Principles

1. **Defense-in-Depth Perimeter (Not Application-Level Isolation):**
   RLS is introduced strictly as a defense-in-depth backstop for ordinary PostgREST roles (`anon`, `authenticated`), **not** as application-level tenant isolation.
2. **FastAPI Sole Identity Authority:**
   Platform authentication remains 100% managed by FastAPI (Argon2id password hashing, 60-minute JWT access tokens, SHA-256 hashed refresh session rotation). Supabase Auth is not used.
3. **Preservation of `postgres` Runtime Role:**
   The FastAPI application backend and background worker continue to connect using the configured role `postgres` over TLS via the Supabase session pooler (`aws-1-ap-southeast-2.pooler.supabase.com:5432`).
4. **PostgreSQL Default-Deny Semantics:**
   When RLS is enabled on a table and **no permissive policies are defined**, PostgreSQL enforces an absolute, engine-level default-deny for all roles that do not hold the `BYPASSRLS` attribute.
5. **No Permissive Policies for API Roles:**
   Zero permissive policies are created for `anon` or `authenticated`. Any request originating from PostgREST will evaluate to an empty policy set and be denied all rows.
6. **No Redundant or Inert Policies:**
   - Zero policies are created for `postgres` or `service_role`. Both hold `rolbypassrls = true`, meaning PostgreSQL query rewriters skip policy evaluation entirely.
   - Misleading permissive `USING (false)` policies are omitted.
7. **No `FORCE ROW LEVEL SECURITY`:**
   `FORCE ROW LEVEL SECURITY` is **not** enabled. Enabling it would alter table-owner semantics without affecting `BYPASSRLS` roles, introducing unnecessary catalog clutter without security benefit.
8. **Preservation of AGENTS.md Rule #2 (Source-Level ACLs):**
   Fine-grained permissions for external connected sources (GitHub private repositories, Jira issue security levels) continue to be evaluated at read time in the FastAPI Python service layer (`SourceAccessPolicyService`).

---

## 3. Explicit Protection Boundary: What RLS Protects vs. What It Does Not

| Security Dimension | Protected by Migration 0013? | Protection Mechanism & Engineering Reality |
|---|---|---|
| **External PostgREST API Exploitation** | **YES (100% Protected)** | Even if an operator accidentally runs `GRANT USAGE ON SCHEMA public TO anon, authenticated;`, RLS default-deny prevents `anon` and `authenticated` from reading or writing a single row across all 56 tables. |
| **Supabase Data API Discovery** | **YES (100% Protected)** | OpenAPI schema introspection via `/rest/v1/` will reflect tables as RLS-locked, returning empty arrays (`[]`) for any query. |
| **Public Internet Scraping** | **YES (100% Protected)** | Direct HTTP calls to `/rest/v1/*` are rejected by both PostgREST gateway authentication (HTTP 401) and PostgreSQL RLS (0 rows). |
| **Internal Application SQL Injection** | **NO (Not Protected by RLS)** | Because the backend connects as `postgres` (which holds `rolbypassrls = true`), any SQL executed on this connection bypasses RLS. Protection relies on SQLAlchemy query parameterization and input validation. |
| **Cross-Tenant Application Logic Bugs** | **NO (Not Protected by RLS)** | If application code omits a `.where(project_id == ...)` filter, the database will not block the query because `postgres` bypasses RLS. Protection is enforced by FastAPI `RbacService` dependencies. |
| **Source-Level Access Control (Rule #2)**| **NO (Enforced in Python Layer)** | Database RLS cannot evaluate external delegated OAuth scopes. The FastAPI `SourceAccessPolicyService` remains the sole authority for source evidence authorization. |

---

## 4. Reconciled 56-Table Inventory Covered by Migration 0013

All 56 base tables in schema `public` are explicitly defined in the migration's static tuple `_ALL_PUBLIC_BASE_TABLES`:

1. `alembic_version`
2. `audit_logs`
3. `background_jobs`
4. `decision_traceability_chains`
5. `entity_aliases`
6. `evidence_chunks`
7. `evidence_contents`
8. `evidence_items`
9. `evidence_page_contents`
10. `handover_acknowledgements`
11. `handover_cases`
12. `handover_checklist_items`
13. `handover_checklists`
14. `handover_content_links`
15. `handover_deliveries`
16. `handover_ownership_transfers`
17. `handover_package_sections`
18. `handover_package_versions`
19. `handover_packages`
20. `handover_readiness_assessments`
21. `handover_responsibility_transfers`
22. `handover_signoffs`
23. `handover_status_histories`
24. `identity_resolution_candidates`
25. `knowledge_entities`
26. `knowledge_evidence_links`
27. `knowledge_extraction_runs`
28. `knowledge_items`
29. `knowledge_relationships`
30. `knowledge_timeline_events`
31. `oauth_states`
32. `organisation_invitations`
33. `organisation_memberships`
34. `organisations`
35. `permissions`
36. `project_memberships`
37. `project_source_mappings`
38. `project_transitions`
39. `project_vector_indexes`
40. `projects`
41. `refresh_sessions`
42. `relationship_evidence_links`
43. `relationship_reconstruction_runs`
44. `role_permissions`
45. `roles`
46. `source_access_policies`
47. `source_connections`
48. `source_sync_runs`
49. `user_roles`
50. `user_source_authorisations`
51. `users`
52. `verification_cases`
53. `verification_conflicts`
54. `verification_context_requests`
55. `verification_issues`
56. `verification_review_events`

---

## 5. DDL Implementation: Upgrade and Downgrade

### 5.1 Pre-Flight Schema Verification Function
Before executing DDL, the migration verifies that all 56 expected tables physically exist in schema `public`:
```python
def _verify_schema_integrity(bind: sa.engine.Connection) -> None:
  if context.is_offline_mode():
    return
  inspector = sa.inspect(bind)
  existing_tables = set(inspector.get_table_names(schema="public"))
  missing = [t for t in _ALL_PUBLIC_BASE_TABLES if t not in existing_tables]
  if missing:
    raise RuntimeError(
        f"Pre-migration schema assertion failed: {len(missing)} expected "
        f"table(s) missing from schema 'public': {missing}"
    )
```

### 5.2 `upgrade()` Implementation
```python
def upgrade() -> None:
  bind = op.get_bind()
  _verify_schema_integrity(bind)
  for table in _ALL_PUBLIC_BASE_TABLES:
    op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;')
```

### 5.3 `downgrade()` Implementation
```python
def downgrade() -> None:
  bind = op.get_bind()
  _verify_schema_integrity(bind)
  for table in _ALL_PUBLIC_BASE_TABLES:
    op.execute(f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY;')
```

---

## 6. Migration Safety & Invariants

- **Zero Data Modification:** No rows are inserted, updated, or deleted.
- **Zero Constraint Modification:** Primary keys, foreign keys, unique constraints, and check constraints remain untouched.
- **Zero Index Modification:** All 100+ B-Tree and GIN indexes remain intact.
- **100% Reversible:** Downgrade restores the database to its exact pre-0013 RLS-disabled state.
