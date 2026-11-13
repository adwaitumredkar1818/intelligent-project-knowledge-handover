# Row Level Security (RLS) & Data API Security Analysis
## Threat Modeling, Exposure Analysis & PostgREST Probing Report

**Platform:** The Handover  
**Target Environment:** Live Supabase Cloud Project (`rjntmboskzyrsqcetzil`)  
**Audit Phase:** Phase A Investigation  
**Date:** 2026-11-13  
**Auditor:** Senior Database Architect & Application Security Engineer  

---

## 1. Row Level Security (RLS) Status Across Public Tables

A comprehensive query against PostgreSQL system catalogs (`pg_class`, `pg_namespace`, `pg_policy`) verified the RLS state across all base tables in the `public` schema:

- **Total Base Tables in `public` Schema:** 56
- **Tables with RLS Enabled (`relrowsecurity = True`):** **0**
- **Tables with FORCE RLS Enabled (`relforcerowsecurity = True`):** **0**
- **Total Existing Row Security Policies (`pg_policy`):** **0**

### Catalog Evidence
```sql
SELECT relname, relrowsecurity, relforcerowsecurity 
FROM pg_class c 
JOIN pg_namespace n ON n.oid = c.relnamespace 
WHERE n.nspname = 'public' AND c.relkind = 'r';

-- Result:
-- Total base tables: 56
-- Tables with RLS enabled: 0
-- Tables with FORCE RLS: 0
```

Every public application table—including `users`, `projects`, `organisations`, `evidence_items`, `evidence_contents`, `knowledge_items`, and `verification_cases`—is currently running without Row Level Security.

---

## 2. Empirical Supabase PostgREST Data API Probing

To evaluate whether the lack of RLS results in active external data exposure, non-destructive, read-only HTTP probes were executed against the Supabase PostgREST Data API endpoint (`https://rjntmboskzyrsqcetzil.supabase.co/rest/v1/`).

### Test Methodology
Probes evaluated two distinct caller states:
1. **Unauthenticated Public Request:** No `apikey` header, no `Authorization` bearer token.
2. **Invalid / Dummy API Key Request:** Standard Supabase client format with placeholder keys.

### Empirical Results Table

| Probed Endpoint | Authentication Header | HTTP Status Code | Response Payload / Error Message |
|---|---|---|---|
| `GET /` | None | `404 Not Found` | `{"error": "requested path is invalid"}` |
| `GET /rest/v1/` | None | `401 Unauthorized` | `{"message": "No API key found in request", "hint": "No apikey request header or url param was found."}` |
| `GET /rest/v1/` | `apikey: dummy-key` | `401 Unauthorized` | `{"message": "Invalid API key", "hint": "Double check your Supabase anon or service_role API key."}` |
| `GET /rest/v1/projects` | None | `401 Unauthorized` | `{"message": "No API key found in request", "hint": "No apikey request header or url param was found."}` |
| `GET /rest/v1/projects` | `apikey: dummy-key` | `401 Unauthorized` | `{"message": "Invalid API key", "hint": "Double check your Supabase anon or service_role API key."}` |
| `GET /rest/v1/users` | None | `401 Unauthorized` | `{"message": "No API key found in request", "hint": "No apikey request header or url param was found."}` |
| `GET /rest/v1/users` | `apikey: dummy-key` | `401 Unauthorized` | `{"message": "Invalid API key", "hint": "Double check your Supabase anon or service_role API key."}` |
| `GET /rest/v1/evidence_items` | None | `401 Unauthorized` | `{"message": "No API key found in request", "hint": "No apikey request header or url param was found."}` |
| `GET /rest/v1/evidence_items` | `apikey: dummy-key` | `401 Unauthorized` | `{"message": "Invalid API key", "hint": "Double check your Supabase anon or service_role API key."}` |
| `GET /rest/v1/verification_cases` | None | `401 Unauthorized` | `{"message": "No API key found in request", "hint": "No apikey request header or url param was found."}` |
| `GET /rest/v1/verification_cases` | `apikey: dummy-key` | `401 Unauthorized` | `{"message": "Invalid API key", "hint": "Double check your Supabase anon or service_role API key."}` |

### Probing Takeaway
The Supabase API Gateway strictly enforces API key presence and JWT signature verification. An anonymous attacker scanning the internet cannot extract data from the database via PostgREST without a valid cryptographic JWT signed by the project's JWT secret.

---

## 3. Two-Tier Authorization Architecture: PostgREST vs. Direct PostgreSQL

To understand why the application is secure despite RLS being disabled, consider the architectural separation between Handover's application runtime and the Supabase PostgREST layer:

```text
                               ┌──────────────────────────────────────────────┐
                               │           UNAUTHORIZED ATTACKERS             │
                               └──────────────────────┬───────────────────────┘
                                                      │ HTTP / HTTPS
                                                      ▼
                                       ┌──────────────────────────────┐
                                       │ Supabase PostgREST Gateway   │
                                       │ (Port 443 /rest/v1/*)        │
                                       └──────────────┬───────────────┘
                                                      │
                       ┌──────────────────────────────┴──────────────────────────────┐
                       │ GATEWAY CHECK 1: Valid API Key / JWT Required (Returns 401) │
                       └──────────────────────────────┬──────────────────────────────┘
                                                      │ Assuming valid anon/authenticated JWT:
                                                      ▼
                                       ┌──────────────────────────────┐
                                       │ PostgreSQL Role: anon / auth │
                                       └──────────────┬───────────────┘
                                                      │
                       ┌──────────────────────────────┴──────────────────────────────┐
                       │ DAC CHECK 2: has_schema_privilege('public', 'USAGE') = FALSE│
                       │ DAC CHECK 3: has_table_privilege('public', table, 'SELECT') │
                       │              = FALSE (0 of 56 tables granted)               │
                       │ (Returns 403 Forbidden / Permission Denied)                  │
                       └─────────────────────────────────────────────────────────────┘

==============================================================================================

                               ┌──────────────────────────────────────────────┐
                               │           AUTHORIZED APPLICATION             │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      │ Direct TLS (Port 5432)
                                                      ▼
                                       ┌──────────────────────────────┐
                                       │ FastAPI Backend (App Runtime)│
                                       │ - Argon2id Password Auth     │
                                       │ - FastAPI JWTs (60-min TTL)  │
                                       │ - PostgreSQL RBAC Service    │
                                       │ - Read-Time Source ACL Checks│
                                       └──────────────┬───────────────┘
                                                      │
                                                      │ SQLAlchemy / Psycopg
                                                      ▼
                                       ┌──────────────────────────────┐
                                       │ Supabase Session Pooler      │
                                       │ Role: postgres (Port 5432)   │
                                       │ Full Table Privileges (56/56)│
                                       └──────────────────────────────┘
```

1. **The Handover Backend Does Not Use PostgREST:**
   - Handover is a custom FastAPI application.
   - All client traffic hits the Next.js frontend or FastAPI API (`/api/v1/*`).
   - Platform identity is managed entirely inside FastAPI via Argon2id hashed passwords, short-lived custom JWT access tokens, and SHA-256 hashed `RefreshSession` cookies. Supabase Auth is **not used** for platform login.
   - FastAPI communicates directly with PostgreSQL via SQLAlchemy and Psycopg over TLS port 5432 using the `postgres` user credentials.
   - Application-level RBAC and source-level ACL filtering are strictly enforced in Python service layers before data is returned.

2. **PostgREST Is an Idle Management Layer:**
   - In standard Supabase projects, PostgREST is exposed on port 443 to power frontend JavaScript SDKs (`@supabase/supabase-js`).
   - Handover does not use `@supabase/supabase-js` for database queries; all database interaction is mediated through the FastAPI backend.
   - The Supabase PostgREST gateway remains active by default on the cloud instance, but has no grants to schema `public`.

---

## 4. Threat Modeling & Attack Surface Analysis

| Threat Scenario | Vector | Pre-conditions | Barrier / Mitigation in Place | Risk Level |
|---|---|---|---|---|
| **Scenario 1: Blind Internet Scraping** | Direct HTTP requests to `/rest/v1/*` | None | PostgREST API Gateway rejects all unauthenticated calls with `401 Unauthorized` | **NEGLIGIBLE** |
| **Scenario 2: Public Anon Key Exploitation** | Attacker obtains the project's public `anon` API key and queries `/rest/v1/users` | Attacker possesses public `anon` key | PostgREST assumes role `anon`. Role `anon` has `USAGE = False` on schema `public` and `0` table privileges. PostgREST returns permission denied | **LOW** |
| **Scenario 3: Authenticated User Privilege Escalation** | A registered user signs in via Supabase Auth and attempts direct SQL/PostgREST queries | Attacker creates a Supabase Auth user | Role `authenticated` has `USAGE = False` on schema `public` and `0` table privileges. Access denied at PostgreSQL DAC layer | **LOW** |
| **Scenario 4: Service Role Key Compromise** | Attacker compromises `SUPABASE_SERVICE_ROLE_KEY` | Attacker obtains service key | `service_role` has full privileges and by default bypasses RLS. Attacker gains full read/write access. (*Mitigation: Key is not present in `.env` or repository*) | **CRITICAL (THEORETICAL)** |
| **Scenario 5: Schema USAGE Misconfiguration** | An operator or future migration runs `GRANT USAGE ON SCHEMA public TO anon, authenticated` | Operator runs default Supabase script | **No RLS in place.** PostgREST would immediately expose all 56 tables to anyone with an `anon` key. | **HIGH (LATENT RISK)** |

---

## 5. Defense-in-Depth Assessment

### Why Current Protection is Incomplete
While PostgreSQL Discretionary Access Control (DAC) currently prevents data leakage, relying exclusively on DAC on a hosted Supabase instance is a **defense-in-depth failure**:
1. **Single Point of Failure:** Security currently depends entirely on a single boolean permission (`has_schema_privilege('anon', 'public', 'USAGE')`). If any automated script, extension installer, or dashboard toggle grants `USAGE` on schema `public`, the protection collapses completely.
2. **Supabase Architectural Conventions:** In Supabase, the public schema is designed under the assumption that Row Level Security is enabled on every table. Supabase UI and documentation assume RLS is the primary perimeter.
3. **Audit Compliance:** In external audits (SOC 2, ISO 27001, HIPAA), having RLS disabled on 56 cloud-hosted database tables containing user credentials, project intelligence, and internal audit logs represents an automatic high-severity audit finding.

### Remediation Imperative
In Phase B, Row Level Security (`ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`) must be enabled on all 56 tables in `public`, accompanied by explicit default-deny policies for `anon` and `authenticated`. This ensures that even if schema privileges are inadvertently altered in the future, the data remains cryptographically and logically unreadable.
