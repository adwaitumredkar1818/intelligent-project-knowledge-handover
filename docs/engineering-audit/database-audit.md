# The Handover — Database and Data Architecture Audit
## PostgreSQL Schema, Foreign Key Indexes, RLS Security & ChromaDB Vector Store Audit

---

## 1. Executive Summary

A comprehensive, non-invasive audit of the persistence layer was performed across **PostgreSQL 17.11** (hosted on Supabase) and **ChromaDB v2** (HTTP dedicated mode).

The audit revealed three critical architectural and operational findings:
1. **Migration State Desynchronization**: The live database is stamped with revision `0012_verification_center`, but the migration file is missing from the active `main` branch.
2. **Zero Row Level Security (RLS)**: **0 out of 42 tables** in the public schema have RLS enabled, creating a severe data exposure vulnerability if Supabase PostgREST is reachable.
3. **63 Unindexed Foreign Keys**: Widespread missing indexes on foreign keys causing sequential table scans during cascading operations and relational joins.
4. **ChromaDB Architecture Drift**: A single shared collection is used across all projects, directly violating the isolation architecture defined in **ADR 0005**.

---

## 2. PostgreSQL Schema & Alembic Migration State

### Live Database Configuration
- **Host**: `aws-1-ap-southeast-2.pooler.supabase.com:5432` (Supabase Session Pooler)
- **Engine**: PostgreSQL 17.11 (x86_64-pc-linux-gnu, compiled by GCC 15.2.0)
- **SSL Connection**: Active (`sslmode=require`, client TLS in use)
- **Total Public Tables**: **42 Base Tables**

### Critical Finding: Migration Desynchronization
Inspection of `alembic_version` in the live database returned:
```sql
SELECT version_num FROM alembic_version;
-- Result: [('0012_verification_center',)]
```
However, inspecting `infrastructure/database/migrations/versions/` on the current branch (`main`) showed:
```text
20261111_0001_initial_baseline.py
20261111_0002_auth_identity_rbac.py
20261111_0003_org_project_workspaces.py
20261111_0004_evidence_ingestion.py
20261111_0005_source_integrations.py
20261112_0006_evidence_chunks_and_fts.py
20261112_0007_knowledge_reconstruction.py
20261112_0008_project_transitions_and_workspace_rbac.py
20261113_0009_supabase_auth_and_vector_indexes.py
20261113_0010_knowledge_domains.py
20261113_0011_relationship_explorer.py
```
- **Finding**: The highest revision file on `main` is `0011_relationship_explorer`.
- **Root Cause**: Commit `0301ee5ada` (*"feat(verification): implement Verification Center backend and human review engine"*) executed migration `0012_verification_center` on the live database from remote branch `feature/verification-center-backend`. This branch was never merged into `main`.
- **Consequence**:
  - Running `alembic current` on `main` fails: `FAILED: Can't locate revision identified by '0012_verification_center'`.
  - The live database already contains tables `verification_cases`, `verification_issues`, `verification_conflicts`, `verification_context_requests`, and `verification_review_events`, but the code models on `main` have no knowledge of these tables.

---

## 3. Security Vulnerability: Row Level Security (RLS) Disabled

Inspection of `pg_class.relrowsecurity` across all 42 public base tables revealed:

```text
Row Level Security (RLS) Status:
42 / 42 tables have RLS=False and ForceRLS=False.
```

### Risk Assessment: Critical
- **Context**: The database is hosted on **Supabase**. In standard Supabase architectures, the PostgREST engine automatically exposes all tables in the `public` schema over HTTP REST endpoints (`/rest/v1/*`).
- **Exposure**: Because RLS is disabled across all 42 tables, if the PostgREST API is not explicitly blocked or disabled at the project gateway, any client with the project's anonymous API key (`anon` key) can execute arbitrary `SELECT`, `INSERT`, `UPDATE`, and `DELETE` queries directly against the database, bypassing FastAPI authentication, RBAC, and source ACLs entirely.
- **Immediate Requirement**:
  1. Revoke API schema access for `anon` and `authenticated` roles in PostgreSQL:
     ```sql
     REVOKE USAGE ON SCHEMA public FROM anon, authenticated;
     ```
  2. Enable RLS on all public tables:
     ```sql
     ALTER TABLE users ENABLE ROW LEVEL SECURITY;
     ALTER TABLE evidence_items ENABLE ROW LEVEL SECURITY;
     ... (for all 42 tables)
     ```

---

## 4. Performance Bottleneck: 63 Unindexed Foreign Keys

PostgreSQL does **not** automatically create indexes on foreign key columns. If a foreign key is unindexed, any `DELETE` or `UPDATE` on the parent table requires a **full sequential table scan** of the child table to enforce referential integrity. Furthermore, joins between child and parent tables cannot use index scans.

Catalog analysis identified **63 foreign keys lacking an index**:

### Unindexed Foreign Keys by Domain

| Table Name | Foreign Key Name | Column(s) | Impact / Risk |
| :--- | :--- | :--- | :--- |
| `role_permissions` | `fk_role_permissions_permission_id` | `permission_id` | Sequential scan on permission lookup |
| `refresh_sessions` | `fk_refresh_sessions_replaced_by` | `replaced_by_session_id` | Slow token family rotation checks |
| `knowledge_entities` | `fk_knowledge_entities_primary_evidence` | `primary_evidence_id` | Table scan when deleting evidence |
| `knowledge_entities` | `fk_knowledge_entities_primary_item` | `primary_knowledge_item_id` | Table scan when updating knowledge item |
| `knowledge_relationships` | `fk_knowledge_relationships_source_entity` | `source_entity_id` | High latency on relationship traversal |
| `knowledge_relationships` | `fk_knowledge_relationships_target_entity` | `target_entity_id` | High latency on incoming edge traversal |
| `knowledge_relationships` | `fk_knowledge_relationships_org` | `organisation_id` | Slow organization-wide relationship queries |
| `knowledge_relationships` | `fk_knowledge_relationships_reviewer` | `reviewed_by_user_id` | Unindexed user reference |
| `relationship_evidence_links` | `fk_rel_evidence_links_evidence_id` | `evidence_id` | Table scan on evidence deletion |
| `relationship_evidence_links` | `fk_rel_evidence_links_chunk_id` | `evidence_chunk_id` | Table scan on chunk re-indexing |
| `relationship_evidence_links` | `fk_rel_evidence_links_rel_id` | `relationship_id` | Slow link lookup for relationships |
| `relationship_evidence_links` | `fk_rel_evidence_links_item_id` | `knowledge_item_id` | Table scan when items updated |
| `knowledge_timeline_events` | `fk_timeline_events_entity_id` | `entity_id` | Slow entity timeline queries |
| `knowledge_timeline_events` | `fk_timeline_events_secondary_entity` | `secondary_entity_id` | Slow secondary entity timeline joins |
| `knowledge_timeline_events` | `fk_timeline_events_evidence_id` | `evidence_id` | Table scan on evidence cleanup |
| `knowledge_timeline_events` | `fk_timeline_events_relationship_id` | `relationship_id` | Unindexed relationship link |
| `decision_traceability_chains` | `fk_decision_chains_entity_id` | `decision_entity_id` | Slow traceability tree queries |
| `identity_resolution_candidates`| `fk_identity_candidates_left` | `left_entity_id` | Slow alias matching joins |
| `identity_resolution_candidates`| `fk_identity_candidates_right` | `right_entity_id` | Slow alias matching joins |
| `verification_cases` | `fk_verification_cases_reviewer` | `assigned_reviewer_id` | Unindexed reviewer queue filter |
| `verification_issues` | `fk_verification_issues_chunk` | `conflicting_chunk_id` | Table scan on chunk update |
| `verification_issues` | `fk_verification_issues_evidence` | `conflicting_evidence_id` | Table scan on evidence delete |
| `verification_conflicts` | `fk_verification_conflicts_chunk_a` | `claim_a_chunk_id` | Table scan on chunk update |
| `verification_conflicts` | `fk_verification_conflicts_chunk_b` | `claim_b_chunk_id` | Table scan on chunk update |
| `verification_review_events` | `fk_review_events_reviewer` | `reviewer_user_id` | Unindexed audit query |
| `verification_context_requests`| `fk_context_requests_requested_by`| `requested_by_user_id` | Unindexed user reference |

---

## 5. ChromaDB Vector Store Audit & ADR 0005 Compliance

### ChromaDB Architecture Violation
In **ADR 0005** (*"Project-Isolated ChromaDB Vector Collections"*), the architecture explicitly mandates:
> *"1. One Collection Per Project: Every Handover project maintains exactly one dedicated ChromaDB vector collection (e.g. `th_project_{stable_hash}`)."*
> *"3. Cross-Project Isolation: Vector queries are strictly scoped to the active project collection. Vectors from Project A can never be returned to Project B."*

### Observed Implementation in `vector_store.py`
```python
# Lines 235-243 of vector_store.py
self._collection_name = (
    collection_name_override.strip()
    if collection_name_override and collection_name_override.strip()
    else build_chroma_collection_name(
        prefix=collection_prefix,
        embedding_model=self._embedding_model,
        index_version=self._index_version,
    )
)
```
- **Finding**: All evidence chunks across all organizations and projects are stored in **a single global collection**: `ipkrh_evidence_chunks_nomic_embed_text_v1`.
- **Dormant Schema**: The PostgreSQL table `project_vector_indexes` (intended to track per-project vector collections, models, versions, and chunk counts) contains **0 rows**.
- **Security & Multi-Tenancy Risk**: Isolation between projects relies entirely on passing `where: {"project_id": ...}` in ChromaDB query metadata. If a developer accidentally omits this metadata clause in a new endpoint or query, semantic search will leak document chunks across unrelated projects.

---

## 6. Prioritized Database Remediation Plan

| Priority | Action | Target Table(s) | Benefit |
| :---: | :--- | :--- | :--- |
| **P0** | **Reconcile Alembic Revisions** | `alembic_version`, migrations | Merge `0012_verification_center` so schema migration tooling operates cleanly. |
| **P0** | **Enable RLS & Revoke PostgREST Access** | All 42 public tables | Prevent unauthorized API data access via Supabase data APIs. |
| **P1** | **Index 63 Foreign Keys** | `knowledge_*`, `verification_*`, `relationship_*` | Eliminate sequential table scans during cascading deletes and relational queries. |
| **P1** | **Enforce ADR 0005 Project Collections** | ChromaDB, `vector_store.py` | Create dedicated Chroma collections per project to eliminate cross-project vector leakage risks. |
| **P2** | **Add JSONB Functional Indexes** | `background_jobs.payload_json` | Enable direct SQL-level filtering for `mapping_id` in sync jobs. |
