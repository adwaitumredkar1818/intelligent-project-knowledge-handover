# Independent Security & Architectural Review: Migration 0016 (RLS Hardening)

**Target File:** `infrastructure/database/migrations/versions/20261113_0016_rls_hardening.py`  
**Revision:** `0016_rls_hardening`  
**Parent Revision (`down_revision`):** `0015_assistant_workspace`  
**Audit Phase:** **Phase B3A.4 — Independent Final Security Review of RLS Migration 0016**  
**Review Date:** 2026-11-13  
**Review Mode:** Strictly Read-Only Source Code Analysis  
**Overall Status:** **VERIFIED TECHNICALLY SOUND (WITH DOCUMENTATION DEFECT IDENTIFIED)**

---

## 1. Executive Summary & Verification Matrix

Migration `0016_rls_hardening` was authored to enable Row Level Security on all 61 public base tables in the Handover platform database. This review independently inspected the source code, SQL generation, atomicity, and schema integrity assertions.

### Verification Matrix

| Check | Verdict | Independent Inspection Evidence |
|---|---|---|
| **Revision ID** | **PASS** | `revision: str = "0016_rls_hardening"` |
| **Parent Revision (`down_revision`)** | **PASS** | `down_revision: str \| None = "0015_assistant_workspace"` |
| **Alembic Graph Head** | **PASS** | `poetry run alembic heads` / `python -m alembic heads` returns exactly `0016_rls_hardening (head)`. |
| **Exact 61 Public Tables** | **PASS** | `_ALL_PUBLIC_BASE_TABLES` contains exactly 61 strings. `len(set(...)) == 61`. |
| **Identifier Validation** | **PASS** | All 61 strings match `^[a-z_][a-z0-9_]*$`. No SQL injection or untrusted characters. |
| **Schema Qualification** | **PASS** | Statements use explicit schema: `ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;`. |
| **Zero Permissive Policies** | **PASS** | No `CREATE POLICY` statements exist. Default-deny semantics for PostgREST non-bypass roles. |
| **Zero FORCE RLS** | **PASS** | `FORCE ROW LEVEL SECURITY` is **not** enabled, preserving backend `postgres` operation without bypass disruption. |
| **Unrelated Schemas** | **PASS** | Only `public` tables are referenced. Zero modification to `extensions`, `auth`, `storage`, or `realtime`. |
| **Symmetric Downgrade** | **PASS** | `downgrade()` runs `ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY;` across all 61 tables. |
| **Transaction Atomicity** | **PASS** | In `env.py`, `context.begin_transaction()` wraps `context.run_migrations()`. The migration runs in a single transactional block. |
| **Docstring / Comment Accuracy** | **DOC DEFECT (LOW)** | Docstring states "56 public base tables" in 3 places (inherited from revision 0013 draft), while code correctly has 61. |

---

## 2. Table-by-Table Alignment Against Live Database Catalog

The table tuple `_ALL_PUBLIC_BASE_TABLES` was compared against the documented live catalog snapshot of Supabase PostgreSQL at revision `0015_assistant_workspace` (`docs/engineering-audit/phase-b3a-2/live-database-state.md`):

| # | Migration 0016 Table Identifier | Documented Live Catalog Status | Domain / Subsystem |
|---|---|---|---|
| 1 | `alembic_version` | Present | Schema Version Tracking |
| 2 | `assistant_citations` | Present | Module 5: Project Assistant |
| 3 | `assistant_conversations` | Present | Module 5: Project Assistant |
| 4 | `assistant_feedback` | Present | Module 5: Project Assistant |
| 5 | `assistant_messages` | Present | Module 5: Project Assistant |
| 6 | `assistant_retrieval_runs` | Present | Module 5: Project Assistant |
| 7 | `audit_logs` | Present | Core Audit Trail |
| 8 | `background_jobs` | Present | Worker Infrastructure |
| 9 | `decision_traceability_chains` | Present | Module 2: Relationships |
| 10 | `entity_aliases` | Present | Module 2: Relationships |
| 11 | `evidence_chunks` | Present | Module 2: Evidence Center |
| 12 | `evidence_contents` | Present | Module 2: Evidence Center |
| 13 | `evidence_items` | Present | Module 2: Evidence Center |
| 14 | `evidence_page_contents` | Present | Module 2: Evidence Center |
| 15 | `handover_acknowledgements` | Present | Module 4: Handover Transfer |
| 16 | `handover_cases` | Present | Module 4: Handover Transfer |
| 17 | `handover_checklist_items` | Present | Module 4: Handover Transfer |
| 18 | `handover_checklists` | Present | Module 4: Handover Transfer |
| 19 | `handover_content_links` | Present | Module 4: Handover Transfer |
| 20 | `handover_deliveries` | Present | Module 4: Handover Transfer |
| 21 | `handover_ownership_transfers` | Present | Module 4: Handover Transfer |
| 22 | `handover_package_sections` | Present | Module 4: Handover Transfer |
| 23 | `handover_package_versions` | Present | Module 4: Handover Transfer |
| 24 | `handover_packages` | Present | Module 4: Handover Transfer |
| 25 | `handover_readiness_assessments` | Present | Module 4: Handover Transfer |
| 26 | `handover_responsibility_transfers` | Present | Module 4: Handover Transfer |
| 27 | `handover_signoffs` | Present | Module 4: Handover Transfer |
| 28 | `handover_status_histories` | Present | Module 4: Handover Transfer |
| 29 | `identity_resolution_candidates` | Present | Module 2: Relationships |
| 30 | `knowledge_entities` | Present | Module 2: Knowledge Reconstruct |
| 31 | `knowledge_evidence_links` | Present | Module 2: Knowledge Reconstruct |
| 32 | `knowledge_extraction_runs` | Present | Module 2: Knowledge Reconstruct |
| 33 | `knowledge_items` | Present | Module 2: Knowledge Reconstruct |
| 34 | `knowledge_relationships` | Present | Module 2: Relationships |
| 35 | `knowledge_timeline_events` | Present | Module 2: Knowledge Reconstruct |
| 36 | `oauth_states` | Present | Integrations & Auth |
| 37 | `organisation_invitations` | Present | Module 1: Workspace Core |
| 38 | `organisation_memberships` | Present | Module 1: Workspace Core |
| 39 | `organisations` | Present | Module 1: Workspace Core |
| 40 | `permissions` | Present | Security & RBAC |
| 41 | `project_memberships` | Present | Module 1: Workspace Core |
| 42 | `project_source_mappings` | Present | Integrations & Sources |
| 43 | `project_transitions` | Present | Module 1: Transitions |
| 44 | `project_vector_indexes` | Present | RAG Vector Storage |
| 45 | `projects` | Present | Module 1: Workspace Core |
| 46 | `refresh_sessions` | Present | Security & Auth |
| 47 | `relationship_evidence_links` | Present | Module 2: Relationships |
| 48 | `relationship_reconstruction_runs` | Present | Module 2: Relationships |
| 49 | `role_permissions` | Present | Security & RBAC |
| 50 | `roles` | Present | Security & RBAC |
| 51 | `source_access_policies` | Present | Integrations & Source ACLs |
| 52 | `source_connections` | Present | Integrations & Sources |
| 53 | `source_sync_runs` | Present | Integrations & Sync Runs |
| 54 | `user_roles` | Present | Security & RBAC |
| 55 | `user_source_authorisations` | Present | Integrations & Per-User Auth |
| 56 | `users` | Present | Core User Records |
| 57 | `verification_cases` | Present | Module 3: Verification Center |
| 58 | `verification_conflicts` | Present | Module 3: Verification Center |
| 59 | `verification_context_requests` | Present | Module 3: Verification Center |
| 60 | `verification_issues` | Present | Module 3: Verification Center |
| 61 | `verification_review_events` | Present | Module 3: Verification Center |

**Conclusion on Coverage:** There is **100% exact alignment** between the 61 tables declared in migration 0016 and the 61 tables in the verified live database catalog.

---

## 3. Discovered Vulnerabilities & Discrepancies

### Finding M-1: Stale Table Count in Migration Docstrings and Function Comments
* **Severity:** **LOW (Documentation Quality / Cosmetic)**
* **Affected File:** `infrastructure/database/migrations/versions/20261113_0016_rls_hardening.py`
* **Evidence:**
  - Line 97: `def _verify_schema_integrity(bind: sa.engine.Connection) -> None: """Pre-flight check verifying all 56 tables exist..."""`
  - Line 112: `def upgrade() -> None: """Enable Row Level Security on all 56 public base tables."""`
  - Line 124: `def downgrade() -> None: """Disable Row Level Security on all 56 public base tables."""`
* **Analysis:**
  The literal tuple `_ALL_PUBLIC_BASE_TABLES` correctly defines all **61** tables, and the file header on line 1 and line 8 states 61 tables. However, the docstrings on lines 97, 112, and 124 still read "56 tables" (a copy-paste remnant from revision 0013 before the merge of Handover and Assistant workspaces).
* **Operational Impact:** None during runtime. The code iterates over `_ALL_PUBLIC_BASE_TABLES` which contains 61 elements.
* **Remediation Recommendation:** Update docstring numbers to 61 in a subsequent minor documentation cleanup.

---

## 4. Final Verdict on Migration 0016

Migration `20261113_0016_rls_hardening.py` is **STRUCTURALLY CORRECT, ATOMIC, REVERSIBLE, AND READY FOR EXECUTION**.
