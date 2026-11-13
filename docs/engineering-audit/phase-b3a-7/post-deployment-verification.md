# Post-Deployment Database Catalog & RLS Verification Report

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Database:** Hosted Supabase PostgreSQL 17.11 (`rjntmboskzyrsqcetzil`)  
**Audit Phase:** **Phase B3A.7 — Controlled Production Deployment of RLS Migration 0016**  
**Inspection Date:** 2026-11-13 23:17:00 UTC+5:30  
**Status:** **100% VERIFIED & COMPLIANT**

---

## 1. Alembic Version Table Inspection

```sql
SELECT version_num FROM public.alembic_version;
```
* **Inspected Result:** Exactly 1 row storing **`'0016_rls_hardening'`**.
* **Integrity:** `0015_assistant_workspace` successfully upgraded to `0016_rls_hardening`. Zero orphaned heads.

---

## 2. Row Level Security (RLS) Status Matrix

```sql
SELECT 
    COUNT(*) AS total_tables,
    COUNT(*) FILTER (WHERE rowsecurity = true) AS rls_enabled,
    COUNT(*) FILTER (WHERE rowsecurity = false) AS rls_disabled
FROM pg_tables 
WHERE schemaname = 'public';
```

| Metric | Pre-Deployment State | Post-Deployment State | Compliance Invariant |
|---|:---:|:---:|:---:|
| **Total Public Tables** | 61 | 61 | Exact Match |
| **RLS Enabled (`rowsecurity = true`)** | **0 (0%)** | **61 (100%)** | **PASS (100% SECURED)** |
| **RLS Disabled (`rowsecurity = false`)** | **61 (100%)** | **0 (0%)** | **PASS (ZERO UNPROTECTED)** |

### Verified Table-by-Table Scope:
Every single one of the 61 public tables has `rowsecurity = true`:
`alembic_version`, `assistant_citations`, `assistant_conversations`, `assistant_feedback`, `assistant_messages`, `assistant_retrieval_runs`, `audit_logs`, `background_jobs`, `decision_traceability_chains`, `entity_aliases`, `evidence_chunks`, `evidence_contents`, `evidence_items`, `evidence_page_contents`, `handover_acknowledgements`, `handover_cases`, `handover_checklist_items`, `handover_checklists`, `handover_content_links`, `handover_deliveries`, `handover_ownership_transfers`, `handover_package_sections`, `handover_package_versions`, `handover_packages`, `handover_readiness_assessments`, `handover_responsibility_transfers`, `handover_signoffs`, `handover_status_histories`, `identity_resolution_candidates`, `knowledge_entities`, `knowledge_evidence_links`, `knowledge_extraction_runs`, `knowledge_items`, `knowledge_relationships`, `knowledge_timeline_events`, `oauth_states`, `organisation_invitations`, `organisation_memberships`, `organisations`, `permissions`, `project_memberships`, `project_source_mappings`, `project_transitions`, `project_vector_indexes`, `projects`, `refresh_sessions`, `relationship_evidence_links`, `relationship_reconstruction_runs`, `role_permissions`, `roles`, `source_access_policies`, `source_connections`, `source_sync_runs`, `user_roles`, `user_source_authorisations`, `users`, `verification_cases`, `verification_conflicts`, `verification_context_requests`, `verification_issues`, `verification_review_events`.

---

## 3. Policy & Privilege State Checks

1. **Permissive Policy Count:**
   - Query: `SELECT COUNT(*) FROM pg_policy pol JOIN pg_class c ON pol.polrelid = c.oid WHERE ...`
   - **Result: 0 policies in `public` schema.**
   - **Semantic Result:** Non-BYPASSRLS roles (`anon`, `authenticated`) receive **0 rows** (absolute default-deny).
2. **FORCE ROW LEVEL SECURITY:**
   - Query: `SELECT c.relname FROM pg_class c WHERE c.relforcerowsecurity = true;`
   - **Result: None.** (Table owners and `postgres` runtime retain native access).
3. **Unrelated Schemas:**
   - `auth` schema: 27 tables (unchanged).
   - `storage` schema: 10 tables (unchanged).
   - Zero modification to extensions or system catalogs.
