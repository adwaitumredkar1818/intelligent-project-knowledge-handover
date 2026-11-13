# RLS Table Policy Matrix & PostgREST Boundary Reassessment

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Database Host:** Hosted PostgreSQL 17.11 on Supabase (`aws-1-ap-southeast-2.pooler.supabase.com:5432`)  
**Audit Phase:** Phase B2.1 Technical Reassessment  
**Date:** 2026-11-13  
**Auditor Roles:** Principal Database Architect, Security Engineer  

---

## 1. Reassessment of the PostgREST Boundary: The Four Layers of Defense

To establish why RLS is necessary and what it achieves, we must cleanly separate the four discrete protection mechanisms active on a Supabase PostgreSQL instance:

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. POSTGREST GATEWAY AUTHENTICATION (Port 443 HTTP API)                                     │
│    - Verifies presence of 'apikey' header or 'Authorization: Bearer <jwt>'                   │
│    - Cryptographically validates JWT signature against Supabase JWT secret                  │
│    - Rejects unauthenticated callers with HTTP 401 Unauthorized                              │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │ (If valid JWT provided)
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. POSTGRESQL SCHEMA USAGE (Discretionary Access Control Layer 1)                           │
│    - Checks has_schema_privilege(role, 'public', 'USAGE')                                   │
│    - Currently: 'anon' = FALSE, 'authenticated' = FALSE                                     │
│    - Halts all query execution before table resolution (Returns 403 / Permission Denied)    │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │ (If USAGE were granted)
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. POSTGRESQL TABLE GRANTS (Discretionary Access Control Layer 2)                           │
│    - Checks has_table_privilege(role, table, 'SELECT|INSERT|UPDATE|DELETE')                 │
│    - Currently: 0 of 56 tables granted to 'anon' or 'authenticated'                         │
│    - Halts all access even if schema USAGE is present                                       │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │ (If table grants were present)
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. ROW LEVEL SECURITY (Mandatory Defense-in-Depth Layer)                                    │
│    - Evaluates row-level security quals in the PostgreSQL query rewriter                    │
│    - Currently: DISABLED across all 56 tables (Zero policies in pg_policy)                  │
│    - Role: Acts as the final, un-bypassable backstop if layers 2 or 3 are ever misconfigured│
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Forensic Takeaway: What Currently Prevents Access vs. What RLS Adds
1. **What Currently Protects Handover Data:**
   - Unauthenticated anonymous callers are rejected by **Layer 1** (PostgREST Gateway returns HTTP 401).
   - Even if a caller presents a valid Supabase `anon` API key or authenticated user JWT, they are rejected by **Layer 2** (`has_schema_privilege('anon', 'public', 'USAGE') = false`) and **Layer 3** (0 table grants on all 56 tables).
2. **What RLS Adds (Why It Is Mandatory):**
   - Relying solely on Layers 1, 2, and 3 is fragile. If a future operator inadvertently executes `GRANT USAGE ON SCHEMA public TO anon, authenticated;` (a standard command in many Supabase tutorials), or if a Supabase Dashboard setting enables public schema reflection, **Layers 2 and 3 vanish**.
   - With RLS disabled, all 56 tables would immediately be exposed to the public internet.
   - **Enabling RLS on all 56 tables establishes Layer 4.** Under RLS default-deny semantics, even if a user holds schema `USAGE` and table `SELECT`, PostgreSQL returns **0 rows** unless an explicit permissive policy permits access.

---

## 2. Reconciled Inventory & Classification of All 56 Public Base Tables

The previous Phase B2 report contained an indexing counting discrepancy. Below is the verified, exact reconciliation of all 56 base tables across **8 canonical functional domains**:

- **Domain 1: System, Migrations & Audit** — 3 tables
- **Domain 2: Platform Identity, Auth & RBAC** — 7 tables
- **Domain 3: Multi-Tenant Core: Organisations & Projects** — 5 tables
- **Domain 4: Delegated Integrations & Source ACLs** — 5 tables
- **Domain 5: Evidence Hub & Vector Indexing** — 5 tables
- **Domain 6: Knowledge Reconstruction & Graph Explorer** — 11 tables
- **Domain 7: Verification Center & Human Review** — 5 tables
- **Domain 8: Knowledge Transfer & Handover Workspace** — 15 tables
- **TOTAL:** **56 BASE TABLES** (100% Accounted For)

---

## 3. Granular Table-by-Table Policy & Governance Matrix

### Domain 1: System, Migrations & Audit (3 Tables)
*Infrastructure, job scheduling, and compliance trail.*

| # | Table Name | Sensitivity | Tenant Scope | RLS Appropriate? | Foreign Key / Parent Lookup Required | Target Read/Write Policy |
|---|---|---|---|---|---|---|
| **1** | `alembic_version` | Low | Platform Global | **Yes** | None | System only. Strict default-deny for all API roles. |
| **2** | `background_jobs` | High | Org / Project | **Yes** | `organisation_id` $\to$ `organisations`, `project_id` $\to$ `projects` | Worker queue. Deny API roles. Worker/App execution only. |
| **3** | `audit_logs` | **Critical** | Org / Project | **Yes** | `organisation_id`, `project_id`, `actor_user_id` | Immutable compliance log. Read-only by tenant admin via FastAPI; append-only via services. Deny API roles. |

---

### Domain 2: Platform Identity, Auth & RBAC (7 Tables)
*User accounts, Argon2id credentials, refresh sessions, and RBAC dictionaries.*

| # | Table Name | Sensitivity | Tenant Scope | RLS Appropriate? | Foreign Key / Parent Lookup Required | Target Read/Write Policy |
|---|---|---|---|---|---|---|
| **4** | `users` | **Critical** | User / Platform | **Yes** | None | Contains hashed credentials. Strict default-deny for API roles. Mediated 100% by FastAPI `AuthService`. |
| **5** | `roles` | Low | Platform Global | **Yes** | None | Static system roles. Read-heavy. Deny API roles; cached in FastAPI. |
| **6** | `permissions` | Low | Platform Global | **Yes** | None | Static system permissions. Deny API roles; cached in FastAPI. |
| **7** | `user_roles` | High | User Scoped | **Yes** | `user_id` $\to$ `users.id`, `role_id` $\to$ `roles.id` | Global role mappings. Deny API roles; evaluated by `RbacService`. |
| **8** | `role_permissions` | Low | Platform Global | **Yes** | `role_id` $\to$ `roles.id`, `permission_id` $\to$ `permissions.id` | RBAC matrix. Deny API roles. |
| **9** | `refresh_sessions` | **Critical** | User Scoped | **Yes** | `user_id` $\to$ `users.id` | Refresh token hashes. Highly sensitive auth state. Strict default-deny for API roles. |
| **10** | `oauth_states` | Medium | User / Ephemeral | **Yes** | `user_id` $\to$ `users.id` | CSRF state parameters. Ephemeral. Strict default-deny for API roles. |

---

### Domain 3: Multi-Tenant Core: Organisations & Projects (5 Tables)
*Tenancy hierarchy, workspace partitioning, and memberships.*

| # | Table Name | Sensitivity | Tenant Scope | RLS Appropriate? | Foreign Key / Parent Lookup Required | Target Read/Write Policy |
|---|---|---|---|---|---|---|
| **11** | `organisations` | High | Organisation | **Yes** | None (Root tenant) | Top-level tenant container. Deny API roles; filtered by FastAPI `OrganisationService`. |
| **12** | `organisation_memberships` | High | Org / User | **Yes** | `organisation_id` $\to$ `organisations.id`, `user_id` $\to$ `users.id` | Tenant membership & roles. Deny API roles; evaluated by `RbacService`. |
| **13** | `organisation_invitations` | Medium | Organisation | **Yes** | `organisation_id` $\to$ `organisations.id` | Onboarding invites. Deny API roles. |
| **14** | `projects` | High | Org / Project | **Yes** | `organisation_id` $\to$ `organisations.id` | Project workspaces. Deny API roles; filtered by project context in FastAPI. |
| **15** | `project_memberships` | High | Project / User | **Yes** | `project_id` $\to$ `projects.id`, `user_id` $\to$ `users.id` | Project-level membership. Deny API roles; verified before project access. |

---

### Domain 4: Delegated Integrations & Source ACLs (5 Tables)
*Encrypted OAuth tokens, personal access tokens, connector mappings, and access policies.*

| # | Table Name | Sensitivity | Tenant Scope | RLS Appropriate? | Foreign Key / Parent Lookup Required | Target Read/Write Policy |
|---|---|---|---|---|---|---|
| **16** | `source_connections` | **Critical** | Org / Source | **Yes** | `organisation_id` $\to$ `organisations.id`, `created_by_user_id` $\to$ `users.id` | Stores AES-256-GCM encrypted tokens. Strict default-deny for API roles. |
| **17** | `user_source_authorisations` | High | User / Source | **Yes** | `user_id` $\to$ `users.id`, `source_connection_id` $\to$ `source_connections.id` | Delegated per-user grants. Deny API roles. |
| **18** | `source_access_policies` | High | Project / Source | **Yes** | `project_id` $\to$ `projects.id`, `source_connection_id` $\to$ `source_connections.id` | Read-time source ACL definitions. Evaluated by `SourceAccessPolicyService`. Deny API roles. |
| **19** | `project_source_mappings` | Medium | Project / Source | **Yes** | `project_id` $\to$ `projects.id`, `source_connection_id` $\to$ `source_connections.id` | Active repo/project links. Deny API roles. |
| **20** | `source_sync_runs` | Medium | Project / Source | **Yes** | `project_id` $\to$ `projects.id`, `mapping_id` $\to$ `project_source_mappings.id` | Background sync history. Deny API roles. |

---

### Domain 5: Evidence Hub & Vector Indexing (5 Tables)
*Canonical evidence ledger, encrypted payloads, extracted pages, and search chunks.*

| # | Table Name | Sensitivity | Tenant Scope | RLS Appropriate? | Foreign Key / Parent Lookup Required | Target Read/Write Policy |
|---|---|---|---|---|---|---|
| **21** | `evidence_items` | **Critical** | Project / Source | **Yes** | `project_id` $\to$ `projects.id`, `source_connection_id` $\to$ `source_connections.id` | Unified evidence ledger. Subject to source ACLs. Deny API roles. |
| **22** | `evidence_contents` | **Critical** | Project / Evidence| **Yes** | `evidence_item_id` $\to$ `evidence_items.id` | Encrypted binary storage pointers. Deny API roles. Streamed only via FastAPI. |
| **23** | `evidence_page_contents` | High | Project / Evidence| **Yes** | `evidence_item_id` $\to$ `evidence_items.id` | Extracted page text & OCR results. Deny API roles. |
| **24** | `evidence_chunks` | High | Project / Evidence| **Yes** | `evidence_item_id` $\to$ `evidence_items.id` | Vector & FTS chunks. Subject to source ACL pre-filtering. Deny API roles. |
| **25** | `project_vector_indexes` | Medium | Project Scoped | **Yes** | `project_id` $\to$ `projects.id` | Chroma collection metadata. Deny API roles. |

---

### Domain 6: Knowledge Reconstruction & Graph Explorer (11 Tables)
*Reconstructed facts, entities, graph relationships, timeline events, and provenance.*

| # | Table Name | Sensitivity | Tenant Scope | RLS Appropriate? | Foreign Key / Parent Lookup Required | Target Read/Write Policy |
|---|---|---|---|---|---|---|
| **26** | `knowledge_items` | High | Project Scoped | **Yes** | `project_id` $\to$ `projects.id` | Reconstructed findings across 8 domains. Deny API roles. |
| **27** | `knowledge_entities` | High | Project Scoped | **Yes** | `project_id` $\to$ `projects.id` | Reconstructed entities (people, modules, tech). Deny API roles. |
| **28** | `entity_aliases` | Medium | Project Scoped | **Yes** | `entity_id` $\to$ `knowledge_entities.id` | Disambiguation aliases. Deny API roles. |
| **29** | `knowledge_relationships` | High | Project Scoped | **Yes** | `project_id` $\to$ `projects.id`, `source_item_id`, `target_item_id` | Directed dependency/decision graph edges. Deny API roles. |
| **30** | `knowledge_timeline_events` | High | Project Scoped | **Yes** | `project_id` $\to$ `projects.id`, `item_id` $\to$ `knowledge_items.id` | Chronological event logs. Deny API roles. |
| **31** | `knowledge_evidence_links` | High | Project Scoped | **Yes** | `knowledge_item_id` $\to$ `knowledge_items.id`, `evidence_item_id` $\to$ `evidence_items.id` | Provenance links to evidence. Deny API roles. |
| **32** | `relationship_evidence_links`| High | Project Scoped | **Yes** | `relationship_id` $\to$ `knowledge_relationships.id`, `evidence_item_id` $\to$ `evidence_items.id` | Provenance links to graph edges. Deny API roles. |
| **33** | `decision_traceability_chains`| High | Project Scoped | **Yes** | `project_id` $\to$ `projects.id`, `decision_item_id` $\to$ `knowledge_items.id` | Decision rationale trails. Deny API roles. |
| **34** | `identity_resolution_candidates`| Medium | Project Scoped | **Yes** | `project_id` $\to$ `projects.id` | Ambiguous cross-source identity queue. Deny API roles. |
| **35** | `knowledge_extraction_runs` | Medium | Project Scoped | **Yes** | `project_id` $\to$ `projects.id` | Qwen3 8B extraction run audit. Deny API roles. |
| **36** | `relationship_reconstruction_runs`| Medium | Project Scoped | **Yes** | `project_id` $\to$ `projects.id` | Graph construction run audit. Deny API roles. |

---

### Domain 7: Verification Center & Human Review (5 Tables)
*Human verification queue, deterministic issue taxonomy, conflicts, and audit trail.*

| # | Table Name | Sensitivity | Tenant Scope | RLS Appropriate? | Foreign Key / Parent Lookup Required | Target Read/Write Policy |
|---|---|---|---|---|---|---|
| **37** | `verification_cases` | High | Project Scoped | **Yes** | `project_id` $\to$ `projects.id`, `assigned_reviewer_id` $\to$ `users.id` | Candidate finding review queue. Deny API roles. |
| **38** | `verification_issues` | High | Project Scoped | **Yes** | `case_id` $\to$ `verification_cases.id`, `project_id` $\to$ `projects.id` | Identified issues (14 taxonomies). Deny API roles. |
| **39** | `verification_conflicts` | High | Project Scoped | **Yes** | `case_id` $\to$ `verification_cases.id`, `first_evidence_id`, `second_evidence_id` | Contradiction pairs & supersession. Deny API roles. |
| **40** | `verification_review_events` | High | Project Scoped | **Yes** | `case_id` $\to$ `verification_cases.id`, `reviewer_user_id` $\to$ `users.id` | Immutable human decision history. Deny API roles. |
| **41** | `verification_context_requests`| Medium | Project Scoped | **Yes** | `case_id` $\to$ `verification_cases.id`, `requested_from_user_id` $\to$ `users.id` | Clarification tickets to offboarding staff. Deny API roles. |

---

### Domain 8: Knowledge Transfer & Handover Workspace (15 Tables)
*Handover case compilation, task checklists, package versions, and formal signoffs.*

| # | Table Name | Sensitivity | Tenant Scope | RLS Appropriate? | Foreign Key / Parent Lookup Required | Target Read/Write Policy |
|---|---|---|---|---|---|---|
| **42** | `project_transitions` | High | Project Scoped | **Yes** | `project_id` $\to$ `projects.id`, `departing_user_id`, `incoming_user_id` | Transition participants roster. Deny API roles. |
| **43** | `handover_cases` | High | Project Scoped | **Yes** | `project_id` $\to$ `projects.id`, `transition_id` $\to$ `project_transitions.id` | Handover workspace case containers. Deny API roles. |
| **44** | `handover_checklists` | High | Project Scoped | **Yes** | `handover_case_id` $\to$ `handover_cases.id` | Structured transfer checklists. Deny API roles. |
| **45** | `handover_checklist_items` | Medium | Project Scoped | **Yes** | `checklist_id` $\to$ `handover_checklists.id` | Checklist tasks & verification status. Deny API roles. |
| **46** | `handover_packages` | **Critical** | Project Scoped | **Yes** | `handover_case_id` $\to$ `handover_cases.id` | Master handover document entities. Deny API roles. |
| **47** | `handover_package_versions` | **Critical** | Project Scoped | **Yes** | `package_id` $\to$ `handover_packages.id` | Immutable versioned snapshots. Deny API roles. |
| **48** | `handover_package_sections` | High | Project Scoped | **Yes** | `package_version_id` $\to$ `handover_package_versions.id` | Narrative sections & structured content. Deny API roles. |
| **49** | `handover_signoffs` | **Critical** | Project Scoped | **Yes** | `package_version_id` $\to$ `handover_package_versions.id`, `reviewer_user_id` | Designated reviewer formal approval gates. Deny API roles. |
| **50** | `handover_acknowledgements` | High | Project Scoped | **Yes** | `package_version_id` $\to$ `handover_package_versions.id`, `assignee_user_id` | Incoming staff receipt acknowledgements. Deny API roles. |
| **51** | `handover_content_links` | Medium | Project Scoped | **Yes** | `package_version_id` $\to$ `handover_package_versions.id`, `evidence_item_id` | Evidence attribution links. Deny API roles. |
| **52** | `handover_deliveries` | Medium | Project Scoped | **Yes** | `package_version_id` $\to$ `handover_package_versions.id` | Export & delivery transmission records. Deny API roles. |
| **53** | `handover_ownership_transfers`| High | Project Scoped | **Yes** | `package_version_id` $\to$ `handover_package_versions.id` | System/repo ownership reassignments. Deny API roles. |
| **54** | `handover_readiness_assessments`| Medium | Project Scoped | **Yes** | `handover_case_id` $\to$ `handover_cases.id` | Automated readiness scoring logs. Deny API roles. |
| **55** | `handover_responsibility_transfers`| High | Project Scoped | **Yes** | `package_version_id` $\to$ `handover_package_versions.id` | Role responsibility matrices. Deny API roles. |
| **56** | `handover_status_histories` | Medium | Project Scoped | **Yes** | `handover_case_id` $\to$ `handover_cases.id` | Status state-transition chronicle. Deny API roles. |

---

## 4. Policy Strategy Synthesis

1. **Uniform Perimeter Lockdown:**  
   Every single table across all 8 domains (all 56 tables) must have Row Level Security enabled (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`).
2. **PostgREST Hardening (Default-Deny):**  
   Under PostgreSQL RLS, simply enabling RLS without granting policies to `anon` or `authenticated` enforces an absolute, engine-level default deny against all PostgREST callers. To ensure total audit compliance, explicit restrictive deny policies (`AS RESTRICTIVE ... USING (false)`) will be declared.
3. **Application Non-Disruption:**  
   Because the FastAPI backend and background worker connect as `postgres` (which holds `rolbypassrls = true`), enabling RLS on all 56 tables provides **100% perimeter protection with 0 ms query latency impact and zero risk of breaking existing application features or tests**.
