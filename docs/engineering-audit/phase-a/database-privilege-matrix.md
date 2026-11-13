# Database Privilege Matrix
## Comprehensive PostgreSQL Catalog Privilege & Role Inspection

**Platform:** The Handover  
**Database Host:** `aws-1-ap-southeast-2.pooler.supabase.com:5432`  
**Database Engine:** PostgreSQL 17.11 on x86_64-pc-linux-gnu  
**Audit Phase:** Phase A Investigation  
**Date:** 2026-11-13  
**Auditor:** Senior Database Architect & PostgreSQL Security Engineer  

---

## 1. Role Inventory & Membership Hierarchy

PostgreSQL role attributes and inheritance structures were extracted directly from `pg_roles` and `pg_auth_members`.

| Role Name | Superuser? | Can Login? | Inherits Privileges? | Direct Role Memberships | Purpose & Execution Context |
|---|---|---|---|---|---|
| `postgres` | No | **Yes** | Yes | `pg_monitor`, `pg_signal_backend`, `pg_read_all_data`, `pg_create_subscription`, `anon`, `authenticated`, `service_role`, `authenticator`, `supabase_privileged_role` | Primary tenant admin role used by FastAPI backend & Alembic |
| `supabase_admin` | **Yes** | **Yes** | Yes | None | Supabase platform infrastructure administrator |
| `authenticator` | No | **Yes** | **No** (`NOINHERIT`) | `anon`, `authenticated`, `service_role` | PostgREST HTTP gateway role; switches to child roles based on JWT |
| `anon` | No | No | Yes | None | Unauthenticated public API caller role |
| `authenticated` | No | No | Yes | None | Authenticated Supabase Auth user role |
| `service_role` | No | No | Yes | None | Supabase backend administrative role (bypasses RLS) |
| `dashboard_user` | No | No | Yes | None | Supabase web console operator role |

> [!NOTE]
> The `authenticator` role has `INHERIT = False`. When PostgREST receives an HTTP request, it issues `SET LOCAL ROLE anon` or `SET LOCAL ROLE authenticated`. It possesses **no privileges of its own**, operating strictly with the permissions of the assumed role.

---

## 2. Schema-Level Privileges on Schema `public`

Permissions on the `public` schema were queried via `has_schema_privilege()`:

| Role | `USAGE` Privilege | `CREATE` Privilege | Effective API Capability |
|---|---|---|---|
| `public` (pseudo-role) | **False** | **False** | No access to objects in `public` schema |
| `anon` | **False** | **False** | **CANNOT access `public` schema via PostgREST** |
| `authenticated` | **False** | **False** | **CANNOT access `public` schema via PostgREST** |
| `authenticator` | **False** | **False** | **CANNOT access `public` schema without assuming permitted role** |
| `service_role` | **True** | **False** | Can access objects in `public` schema |
| `postgres` | **True** | **True** | Full schema administrative control (FastAPI backend) |
| `supabase_admin` | **True** | **True** | Full platform administrative control |

> [!IMPORTANT]
> Because `has_schema_privilege('anon', 'public', 'USAGE')` is **False**, PostgreSQL Discretionary Access Control (DAC) halts all object resolution for unauthenticated PostgREST callers before any table permissions or RLS policies are even evaluated.

---

## 3. Table-Level Privilege Matrix (Across All 56 Base Tables)

Every base table in the `public` schema was evaluated across core DML actions (`SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`) using `has_table_privilege()`:

| Role | Base Table Count | `SELECT` Permitted | `INSERT` Permitted | `UPDATE` Permitted | `DELETE` Permitted | `TRUNCATE` Permitted |
|---|---|---|---|---|---|---|
| `public` | 56 | **0** | **0** | **0** | **0** | **0** |
| `anon` | 56 | **0** | **0** | **0** | **0** | **0** |
| `authenticated` | 56 | **0** | **0** | **0** | **0** | **0** |
| `authenticator` | 56 | **0** | **0** | **0** | **0** | **0** |
| `service_role` | 56 | **56** | **56** | **56** | **56** | **56** |
| `postgres` | 56 | **56** | **56** | **56** | **56** | **56** |

### Verified Base Table Catalog (All 56 Tables)
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

## 4. Default Privileges (`pg_default_acl`)

PostgreSQL default privileges determine what permissions are automatically granted when a specific role creates new database objects.

Querying `pg_default_acl` across all grantors revealed 24 default ACL definitions. The critical entries for schema `public` are:

```sql
-- Objects created by 'postgres' in schema 'public':
Grantor: postgres | Schema: public | Obj: r (tables)    | ACL: ['postgres=arwdDxtm/postgres', 'service_role=arwdDxtm/postgres']
Grantor: postgres | Schema: public | Obj: S (sequences) | ACL: ['postgres=rwU/postgres', 'service_role=rwU/postgres']
Grantor: postgres | Schema: public | Obj: f (functions) | ACL: ['postgres=X/postgres', 'service_role=X/postgres']
```

### Forensic Takeaway:
When Alembic runs migrations connecting as role `postgres`, PostgreSQL automatically applies `pg_default_acl` for grantor `postgres`. Under these rules, **ONLY `postgres` and `service_role`** are granted table permissions.
Neither `anon` nor `authenticated` are granted permissions on any tables created by `postgres`.

---

## 5. Internal Schemas Privilege & Exposure Analysis

Supabase manages several internal schemas. The privileges for `anon`, `authenticated`, and `service_role` on these schemas were verified:

| Schema Name | Role `anon` USAGE | Role `authenticated` USAGE | Role `service_role` USAGE | Contents / Functionality | Security Exposure |
|---|---|---|---|---|---|
| `auth` | **True** | **True** | **True** | Supabase Auth internal tables (`users`, `identities`, etc.) | **Protected by internal RLS**; Handover does not use Supabase Auth for platform identity |
| `storage` | **True** | **True** | **True** | Supabase Storage metadata (`objects`, `buckets`) | Private bucket `project-evidence` configured; direct downloads blocked |
| `realtime` | **True** | **True** | **True** | Realtime subscription metadata | Handover does not publish sensitive streams |
| `extensions`| **True** | **True** | **True** | Installed extensions (`uuid-ossp`, `pgcrypto`) | Read-only extension functions |
| `graphql_public` | **True** | **True** | **True** | Public GraphQL schema reflection | Limited to reflected schemas; `public` schema tables have 0 grants |

---

## 6. Privilege Verdict

1. **DAC Is Fully Restrictive:** Discretionary Access Control on PostgreSQL is completely locked down against the Supabase PostgREST API roles `anon` and `authenticated`.
2. **Backend Unimpeded:** The FastAPI backend connects as `postgres` over TLS via the Supabase connection pooler (`aws-1-ap-southeast-2.pooler.supabase.com:5432`), possessing full table access (`56/56`).
3. **Defense-in-Depth Required:** The lack of Row Level Security (RLS) is mitigated solely by DAC schema `USAGE` and table `GRANT` restrictions. RLS must be enabled as an active secondary security layer.
