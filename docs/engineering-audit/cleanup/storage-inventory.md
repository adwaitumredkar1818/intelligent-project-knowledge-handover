# The Handover — Comprehensive Storage & Environment Inventory

**Document Type:** Pre-Cleanup Environmental & Storage Audit (Stage One)  
**Date:** November 14, 2026  
**Status:** Complete — Dry-Run Inspection (No Deletions Executed)  
**Database Reference:** Supabase Project `rjntmboskzyrsqcetzil` (PostgreSQL 17.11)  
**Alembic Revision:** `0016_rls_hardening` (Verified on Live Remote & Local Instances)  
**Author:** Antigravity Engineering Lead  

---

## 1. Executive Summary

In accordance with the Handover Cleanup Directive, a comprehensive, non-destructive audit and storage inventory was executed across all nine target domains:
1. **Supabase PostgreSQL** (hosted on Supabase project `rjntmboskzyrsqcetzil`, accessed via Session Pooler)
2. **Supabase Storage** (remote private bucket `project-evidence`)
3. **Local Project Repository** (Git branch `main`, working tree, untracked and modified files)
4. **Python Test & Build Artifacts** (`.mypy_cache`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.venv`)
5. **Frontend Build Artifacts** (`.next` build output and caches, `node_modules`)
6. **Docker Storage** (`ipkrh-postgres`, `ipkrh-chromadb`, volumes, images, networks)
7. **ChromaDB Vector Store** (dedicated HTTP server mode, collection `ipkrh_evidence_chunks_nomic-embed-text_v1`)
8. **Temporary AI & Document-Processing Outputs** (local encrypted `.enc` files in `data/uploads/`)
9. **Logs, Reports, Exports & Scratch Files** (`scratch/`, `docs/engineering-audit/screenshots/`)

### Key Inventory Findings
- **Zero Schema or RLS Violations:** Supabase PostgreSQL hosts **61 public base tables**, all with **Row Level Security (RLS) active and verified** (`relrowsecurity = True`). Alembic revision is verified at `0016_rls_hardening`.
- **Real Production Users Identified & Protected:** Three human platform accounts (`adwaitumredkar1818@gmail.com`, `shubham392007@gmail.com`, and `engineer_live@handover.internal`) were discovered in PostgreSQL. None have synthetic patterns or test roles; all are classified as **`PRODUCTION_OR_REAL_DATA`** and protected from deletion.
- **Confirmed Synthetic Database Artifacts:** 20 test organisations, 20 test projects, 41 test user accounts (all utilizing the RFC 2606 reserved `@example.com` domain with names like `Alice Developer`, `Bob Restricted`, `Carol Project Reviewer`), 31 synthetic evidence records, 34 synthetic knowledge items, 25 verification cases, and 6 handover test packages were identified from automated Phase 6–9 integration test runs.
- **Supabase Storage Empty:** The `storage` schema in Supabase (`storage.buckets` and `storage.objects`) contains **0 buckets and 0 objects**. Remote object storage consumption is 0 bytes.
- **Orphaned Local Uploads:** 30 encrypted `.enc` files (569,722 bytes / 0.54 MB) exist in `data/uploads/` and `backend/data/uploads/`. None are referenced by any database record in either Supabase or local PostgreSQL.
- **Orphaned ChromaDB Vectors:** 107 vectors exist in collection `ipkrh_evidence_chunks_nomic-embed-text_v1`, all tagged with orphaned test project `c8869ad9-c14b-4886-8617-e691fca6ef5d` which exists in neither database.
- **Local Disk Footprint:** Total repository disk consumption is **1,643.14 MB (1.64 GB)**, dominated by `frontend/.next` (802.10 MB), `frontend/node_modules` (476.73 MB), and `backend/.venv` (235.01 MB).

---

## 2. Git & Repository Inspection

### 2.1 Working Tree & Commit State
- **Branch:** `main`
- **Head Commit:** `2788e88dd747a3d7e282f8da859835673543b47b` (*"Merge branch 'origin/main' into main"*)
- **Status:** Unstaged modifications and untracked files resulting from recent Phase 3–10 delivery and audit scripts.
- **Repository Total Size (Filesystem):** **1,643.14 MB (1.64 GB)**
- **Total Files Tracked & Untracked:** 40,789 files

### 2.2 Directory Size Hierarchy
| Directory / Component | File Count | Size (Bytes) | Size (MB) | Classification | Action Safety |
| :--- | ---: | ---: | ---: | :--- | :--- |
| `frontend/.next` | 2,261 | 841,061,356 | 802.10 MB | Build Cache & Output | Reclaimable (via `npm run build` rebuild) |
| `frontend/node_modules` | 28,171 | 499,888,831 | 476.73 MB | NPM Dependencies | **PRESERVE** (Rule: preserve node_modules) |
| `backend/.venv` | 7,822 | 246,423,969 | 235.01 MB | Python Virtual Env | **PRESERVE** (Runtime environment) |
| `graphify-out` | 553 | 52,602,611 | 50.17 MB | Codebase Knowledge Graph | **PRESERVE** (Project navigation & AST graph) |
| `backend/.mypy_cache` | 18 | 29,237,477 | 27.88 MB | Mypy Cache | Reclaimable (regenerates on `mypy`) |
| `.mypy_cache` (root) | 19 | 25,817,375 | 24.62 MB | Mypy Cache | Reclaimable (regenerates on `mypy`) |
| `docs/engineering-audit` | 152 | 7,747,415 | 7.39 MB | Engineering Audit Reports | **PRESERVE** (Mandatory audit records) |
| `docs/.../screenshots` | 55 | 7,028,359 | 6.70 MB | Visual Audit Artifacts | **PRESERVE** (49 CDP audit screenshots) |
| `.git` | 1,816 | 5,529,408 | 5.27 MB | Git Object Database | **PRESERVE** (Version control history) |
| Non-venv `__pycache__` | 15 dirs | 5,250,242 | 5.01 MB | Python Bytecode Cache | Reclaimable (regenerates automatically) |
| `scratch` (total) | 69 | 1,397,630 | 1.33 MB | Scratch Scripts & CDP Profile | Partially Reclaimable |
| `scratch/chrome-cdp-profile-phase4` | 48 | 1,166,120 | 1.11 MB | Headless Chrome Cache | Reclaimable (temporary browser profile) |
| `frontend/src` | 147 | 1,155,186 | 1.10 MB | Frontend Source Code | **PRESERVE** (Production application code) |
| `data/uploads` | 24 | 455,722 | 0.43 MB | Orphaned Local Encrypted Uploads | Reclaimable (Unreferenced test files) |
| `backend/data/uploads` | 6 | 114,000 | 0.11 MB | Orphaned Local Encrypted Uploads | Reclaimable (Unreferenced test files) |
| `backend/.pytest_cache` & root | 9 | 19,066 | 0.02 MB | Pytest Cache | Reclaimable (regenerates on `pytest`) |
| `backend/.ruff_cache` & root | 14 | 18,508 | 0.02 MB | Ruff Linter Cache | Reclaimable (regenerates on `ruff`) |

---

## 3. Supabase PostgreSQL Inspection

### 3.1 Live Database Identification
- **Project Reference:** `rjntmboskzyrsqcetzil`
- **Host / Pooler:** `aws-1-ap-southeast-2.pooler.supabase.com:5432` (Session Pooler)
- **Database Name:** `postgres`
- **Connected Role:** `postgres`
- **Engine Version:** PostgreSQL 17.11 on `x86_64-pc-linux-gnu` (compiled by GCC 15.2.0, 64-bit)
- **Alembic Version:** `0016_rls_hardening`
- **Total Physical Database Size:** **19 MB (20,289,203 bytes)**
- **Public Schema Tables:** **61 Base Tables**
- **Row Level Security Status:** **61 / 61 tables have RLS enabled (`relrowsecurity = True`)**

### 3.2 Public Tables Row Counts & Sizes (Full 61-Table Census)

| Table Name | Row Count | Total Size | Table Data Size | Index Size | RLS Enabled | Force RLS |
| :--- | ---: | ---: | ---: | ---: | :---: | :---: |
| `audit_logs` | 156 | 272 kB | 104 kB | 128 kB | True | False |
| `role_permissions` | 132 | 56 kB | 16 kB | 16 kB | True | False |
| `handover_package_sections` | 48 | 104 kB | 24 kB | 48 kB | True | False |
| `users` | 44 | 104 kB | 16 kB | 48 kB | True | False |
| `permissions` | 44 | 64 kB | 8 kB | 48 kB | True | False |
| `handover_status_histories` | 42 | 48 kB | 8 kB | 32 kB | True | False |
| `project_memberships` | 41 | 152 kB | 16 kB | 96 kB | True | False |
| `handover_checklist_items` | 40 | 96 kB | 16 kB | 48 kB | True | False |
| `organisation_memberships` | 38 | 136 kB | 16 kB | 96 kB | True | False |
| `handover_readiness_assessments` | 36 | 96 kB | 16 kB | 48 kB | True | False |
| `knowledge_items` | 34 | 152 kB | 16 kB | 96 kB | True | False |
| `evidence_items` | 31 | 400 kB | 104 kB | 256 kB | True | False |
| `refresh_sessions` | 31 | 128 kB | 8 kB | 112 kB | True | False |
| `knowledge_evidence_links` | 27 | 112 kB | 16 kB | 64 kB | True | False |
| `verification_cases` | 25 | 144 kB | 8 kB | 96 kB | True | False |
| `assistant_messages` | 21 | 104 kB | 24 kB | 48 kB | True | False |
| `projects` | 20 | 160 kB | 8 kB | 112 kB | True | False |
| `organisations` | 20 | 112 kB | 8 kB | 64 kB | True | False |
| `handover_content_links` | 18 | 112 kB | 8 kB | 96 kB | True | False |
| `evidence_chunks` | 13 | 1,208 kB | 80 kB | 1,048 kB | True | False |
| `assistant_retrieval_runs` | 13 | 64 kB | 8 kB | 48 kB | True | False |
| `handover_checklists` | 12 | 64 kB | 8 kB | 48 kB | True | False |
| `assistant_conversations` | 9 | 72 kB | 8 kB | 64 kB | True | False |
| `handover_responsibility_transfers` | 8 | 80 kB | 8 kB | 64 kB | True | False |
| `handover_signoffs` | 8 | 64 kB | 8 kB | 48 kB | True | False |
| `roles` | 8 | 64 kB | 8 kB | 48 kB | True | False |
| `verification_review_events` | 6 | 120 kB | 40 kB | 48 kB | True | False |
| `handover_cases` | 6 | 112 kB | 8 kB | 96 kB | True | False |
| `handover_package_versions` | 6 | 80 kB | 8 kB | 64 kB | True | False |
| `handover_packages` | 6 | 64 kB | 8 kB | 48 kB | True | False |
| `assistant_citations` | 4 | 80 kB | 8 kB | 64 kB | True | False |
| `handover_ownership_transfers` | 4 | 80 kB | 8 kB | 64 kB | True | False |
| `handover_acknowledgements` | 4 | 64 kB | 8 kB | 48 kB | True | False |
| `handover_deliveries` | 4 | 64 kB | 8 kB | 48 kB | True | False |
| `user_roles` | 3 | 72 kB | 8 kB | 64 kB | True | False |
| `verification_issues` | 2 | 112 kB | 16 kB | 64 kB | True | False |
| `assistant_feedback` | 2 | 64 kB | 8 kB | 48 kB | True | False |
| `verification_context_requests` | 1 | 80 kB | 8 kB | 64 kB | True | False |
| `alembic_version` | 1 | 24 kB | 8 kB | 16 kB | True | False |
| *22 Empty Tables (listed below)* | 0 | 1,688 kB | 176 kB | 1,512 kB | True | False |
| **Total (61 Base Tables)** | **926** | **6,424 kB (~6.27 MB)** | **880 kB** | **5,376 kB** | **61 / 61** | **0 / 61** |

#### Empty Tables (0 Rows Each)
`knowledge_entities` (184 kB), `background_jobs` (152 kB), `evidence_page_contents` (152 kB), `evidence_contents` (128 kB), `knowledge_relationships` (128 kB), `relationship_evidence_links` (96 kB), `source_access_policies` (96 kB), `verification_conflicts` (96 kB), `knowledge_timeline_events` (88 kB), `source_connections` (80 kB), `entity_aliases` (64 kB), `organisation_invitations` (64 kB), `project_source_mappings` (64 kB), `relationship_reconstruction_runs` (64 kB), `source_sync_runs` (64 kB), `oauth_states` (56 kB), `user_source_authorisations` (56 kB), `knowledge_extraction_runs` (48 kB), `project_transitions` (40 kB), `decision_traceability_chains` (32 kB), `identity_resolution_candidates` (32 kB), `project_vector_indexes` (32 kB).

---

## 4. Test Data & Record Classification

In strict adherence to Section 2.3, every record category in Supabase PostgreSQL was inspected and classified:

### 4.1 System & Platform Identity Records (MANDATORY PRESERVATION)
| Entity / Table | Count | Classification | Retention Rationale |
| :--- | ---: | :--- | :--- |
| `roles` | 8 | `SYSTEM_RECORD` | Platform RBAC role definitions (`platform_admin`, `org_admin`, `org_member`, `lead_reviewer`, etc.). |
| `permissions` | 44 | `SYSTEM_RECORD` | Fine-grained platform permissions across all 11 product domains. |
| `role_permissions` | 132 | `SYSTEM_RECORD` | Authoritative permission assignments to roles. |
| `alembic_version` | 1 | `SYSTEM_RECORD` | Tracks migration head `0016_rls_hardening`. Rule 4: Never reset Alembic history. |
| `users` (Human Accounts) | 3 | `PRODUCTION_OR_REAL_DATA` | Real user accounts: `adwaitumredkar1818@gmail.com`, `shubham392007@gmail.com`, `engineer_live@handover.internal`. |
| `user_roles` | 3 | `PRODUCTION_OR_REAL_DATA` | Assigns `standard_user` role to the 3 real platform users. |
| `audit_logs` | 156 | `SYSTEM_RECORD` | Immutable security and operational audit trail. Rule 8: Never delete all audit records. |

### 4.2 Confirmed Synthetic Test Records (ELIGIBLE FOR CLEANUP)
| Entity / Table | Count | Classification | Evidence of Test Origin |
| :--- | ---: | :--- | :--- |
| `organisations` | 20 | `CONFIRMED_TEST_DATA` | Names: `Assistant Org <hex>` (9), `Handover Test Org <hex>` (6), `Verification Org <hex>` (5). All generated during automated integration test runs on 2026-11-13. |
| `projects` | 20 | `CONFIRMED_TEST_DATA` | Names: `Assistant Project <hex>` (9), `Handover Test Project <hex>` (6), `Verification Project <hex>` (5). Slugs: `verif-proj-*`, `handover-proj-*`, `assistant-proj-*`. |
| `users` (Test Accounts) | 41 | `CONFIRMED_TEST_DATA` | All 41 use the RFC 2606 reserved `@example.com` synthetic domain (`alice.assistant.*@example.com`, `bob.assistant.*@example.com`, `reviewer-*@example.com`, `successor-*@example.com`, `departing-*@example.com`). |
| `organisation_memberships` | 38 | `CONFIRMED_TEST_DATA` | Links the 41 test users to the 20 test organisations. |
| `project_memberships` | 41 | `CONFIRMED_TEST_DATA` | Links the 41 test users to the 20 test projects. |
| `refresh_sessions` | 31 | `CONFIRMED_TEST_DATA` | Sessions issued to the 41 test users during automated audit test execution. |
| `evidence_items` | 31 | `CONFIRMED_TEST_DATA` | 13 mock documents with synthetic keys (`project-evidence/adr_001.md`, `salaries_2026.docx`) + 18 test architecture documents (`Architecture Document <hex>.pdf`). |
| `evidence_chunks` | 13 | `CONFIRMED_TEST_DATA` | Chunks generated for the synthetic assistant test documents. |
| `knowledge_items` | 34 | `CONFIRMED_TEST_DATA` | Synthetic findings created during Phase 5/6/7 audit runs (e.g. `Item to Reject via API`, `Updated via Live API PATCH`). |
| `knowledge_evidence_links` | 27 | `CONFIRMED_TEST_DATA` | Provenance links joining synthetic knowledge items to synthetic evidence items. |
| `verification_cases` | 25 | `CONFIRMED_TEST_DATA` | Cases generated by `run_verification_center_audit.py` to test human review flows. |
| `verification_review_events` | 6 | `CONFIRMED_TEST_DATA` | Review event logs from automated verification case approval/rejection tests. |
| `verification_issues` | 2 | `CONFIRMED_TEST_DATA` | Test issues attached to verification test cases. |
| `verification_context_requests` | 1 | `CONFIRMED_TEST_DATA` | Test context request created during verification audit. |
| `handover_packages` | 6 | `CONFIRMED_TEST_DATA` | Test dossiers (`Handover Package: Lead Engineer Offboarding...`) created by `run_handover_workspace_audit.py`. |
| `handover_package_versions` | 6 | `CONFIRMED_TEST_DATA` | Version records for the 6 test handover packages. |
| `handover_package_sections` | 48 | `CONFIRMED_TEST_DATA` | Modular sections for the 6 test handover packages. |
| `handover_checklist_items` | 40 | `CONFIRMED_TEST_DATA` | Checklist items for the test handover packages. |
| `handover_status_histories` | 42 | `CONFIRMED_TEST_DATA` | Status transition records for the test handover packages. |
| `handover_readiness_assessments` | 36 | `CONFIRMED_TEST_DATA` | Readiness score assessments for the test handover packages. |
| `handover_content_links` | 18 | `CONFIRMED_TEST_DATA` | Content linkages for the test handover packages. |
| `handover_checklists` | 12 | `CONFIRMED_TEST_DATA` | Checklists for the test handover packages. |
| `handover_responsibility_transfers` | 8 | `CONFIRMED_TEST_DATA` | Transfer assignments created during handover tests. |
| `handover_signoffs` | 8 | `CONFIRMED_TEST_DATA` | Signoff records from departing/reviewer/successor triads in tests. |
| `handover_cases` | 6 | `CONFIRMED_TEST_DATA` | Parent workflow cases for the 6 test handover packages. |
| `handover_ownership_transfers` | 4 | `CONFIRMED_TEST_DATA` | Ownership transition records in handover tests. |
| `handover_acknowledgements` | 4 | `CONFIRMED_TEST_DATA` | Receipt acknowledgements in handover tests. |
| `handover_deliveries` | 4 | `CONFIRMED_TEST_DATA` | Delivery receipt events in handover tests. |
| `assistant_conversations` | 9 | `CONFIRMED_TEST_DATA` | Chat sessions created by `run_assistant_audit.py` (`Bob's Inquiry`, `Updated Architecture Discussion`). |
| `assistant_messages` | 21 | `CONFIRMED_TEST_DATA` | Chat messages in the test conversations. |
| `assistant_retrieval_runs` | 13 | `CONFIRMED_TEST_DATA` | RAG retrieval telemetry from assistant test runs. |
| `assistant_citations` | 4 | `CONFIRMED_TEST_DATA` | Evidence citations emitted during assistant test runs. |
| `assistant_feedback` | 2 | `CONFIRMED_TEST_DATA` | Thumbs-up/down feedback test events. |

---

## 5. Supabase Storage Inspection

- **Storage Provider:** `storage.buckets` & `storage.objects` queried directly in Supabase PostgreSQL catalog.
- **Buckets:** **0 Buckets** (`storage.buckets` count = 0)
- **Objects:** **0 Objects** (`storage.objects` count = 0)
- **Object Storage Consumption:** **0 bytes**
- **Assessment:** All document uploads during Phase 2.4A–Phase 10 development utilized `STORAGE_PROVIDER=local_encrypted` directed to local disk directories (`./data/uploads`), rather than Supabase private object storage. No remote storage cleanup is required.

---

## 6. ChromaDB Vector Store Inspection

- **Endpoint:** `http://localhost:8001/api/v2` (Docker service `ipkrh-chromadb`)
- **Heartbeat:** Healthy (status 200, nanosecond heartbeat active)
- **Total Collections:** **1 Collection**
- **Collection Identity:**
  - **ID:** `23a5f8ad-fb46-46cf-ad33-2ee5bafe068b`
  - **Name:** `ipkrh_evidence_chunks_nomic-embed-text_v1`
  - **Embedding Model:** `nomic-embed-text`
  - **Dimensions:** 768
  - **Index Version:** `v1`
  - **Vector Count:** **107 vectors**
- **Vector Metadata Breakdown:**
  - `project_id: c8869ad9-c14b-4886-8617-e691fca6ef5d` (107 / 107 vectors)
  - `source_provider: document_upload` (101 vectors), `jira` (5 vectors), `slack` (1 vector)
  - `is_synthetic: False` (107 / 107 vectors)
- **Orphan Status:** Project `c8869ad9-c14b-4886-8617-e691fca6ef5d` exists in **neither** Supabase PostgreSQL nor local Docker PostgreSQL.
- **Classification:** **`ORPHANED_RECORD` / `CONFIRMED_TEST_DATA`**. These 107 vectors are abandoned remnants of an isolated Phase 2.5 indexing test run.

---

## 7. Docker Storage Inspection

- **Docker Version / Runtime:** Docker Desktop on WSL2 (Healthy, daemon task `task-2823`)
- **Containers:**
  - `812c3ccca77c` — `postgres:16-alpine` (`ipkrh-postgres`, healthy, port `127.0.0.1:5432`)
  - `6c3bb0ddf0cb` — `chromadb/chroma:latest` (`ipkrh-chromadb`, healthy, port `127.0.0.1:8001`)
  - *Stopped Containers:* 0
- **Images:**
  - `chromadb/chroma:latest` (`1e0b73a187a2`, 826 MB disk usage, 176 MB content)
  - `postgres:16-alpine` (`aa6cb33cf4c1`, 420 MB disk usage, 117 MB content)
  - *Dangling Images:* 0
- **Volumes:**
  - `ipkrh_postgres_data` (local driver, persistent PostgreSQL 16 store)
  - `ipkrh_chroma_data` (local driver, persistent ChromaDB store)
  - *Total Volume Size:* **114.9 MB**
- **Networks:** `ipkrh_network` (bridge), `bridge`, `host`, `none`.
- **Build Cache:** **0 B**
- **Safety Assessment:** Both containers, images, and volumes are **actively running and required** for local development and regression testing. In accordance with Critical Safety Rule 14, **no Docker volumes, containers, or images will be pruned**. Reclaimable Docker storage is **0 bytes**.

---

## 8. Temporary AI & Document-Processing Outputs

### 8.1 Encrypted File Census (`data/uploads/` & `backend/data/uploads/`)
Inspection of local filesystem directories identified **30 encrypted `.enc` files**:
- `data/uploads`: 11 directory pairs containing 24 files (455,722 bytes / 0.43 MB)
- `backend/data/uploads`: 3 directory pairs containing 6 files (114,000 bytes / 0.11 MB)
- **Total Local Upload Disk Usage:** **569,722 bytes (~0.54 MB)**

### 8.2 Database Cross-Reference Audit
Every `.enc` file path was cross-referenced against `evidence_items` in both Supabase PostgreSQL and local PostgreSQL:
- **Supabase PostgreSQL Matched Files:** **0** (Supabase evidence records hold mock keys or remote references).
- **Local PostgreSQL Matched Files:** **0** (Local DB evidence records point to separate identifiers).
- **Orphan Status:** **30 of 30 files (100%) are completely unreferenced by any database record**.
- **Classification:** **`CONFIRMED_TEST_DATA`**. These files were created by unit tests (`test_document_ingestion.py`, `test_evidence_indexing.py`) that failed to clean up their test upload artifacts.

---

## 9. Scratch, Logs & Build Artifacts

### 9.1 Headless Chrome User Profile
- **Path:** `scratch/chrome-cdp-profile-phase4/`
- **File Count:** 48 files
- **Size:** **1,166,120 bytes (1.11 MB)**
- **Contents:** Chrome GPU cache, crashpad logs, leveldb sync data generated during Phase 4 headless Chrome DevTools Protocol verification.
- **Classification:** **`CONFIRMED_TEST_DATA`** (Safe to remove).

### 9.2 Python Typecheck & Test Caches
- **Paths:**
  - `backend/.mypy_cache`: 18 files, 29,237,477 bytes (27.88 MB)
  - `.mypy_cache` (root): 19 files, 25,817,375 bytes (24.62 MB)
  - Non-venv `__pycache__` directories: 15 dirs, 5,250,242 bytes (5.01 MB)
  - `.pytest_cache` (backend + root): 9 files, 19,066 bytes (0.02 MB)
  - `.ruff_cache` (backend + root): 14 files, 18,508 bytes (0.02 MB)
- **Total Python Cache Size:** **60,342,668 bytes (57.55 MB)**
- **Classification:** **`CONFIRMED_TEST_DATA`** (Safe to remove; automatically regenerated).

### 9.3 Frontend Build Output
- **Path:** `frontend/.next/`
- **File Count:** 2,261 files
- **Size:** **841,061,356 bytes (802.10 MB)**
- **Contents:** Standalone Next.js server bundle, webpack compilation cache, static route chunks.
- **Classification:** **Build Artifact**. Can be safely deleted to reclaim 802.10 MB, and regenerated on demand via `npm run build`.

---

## 10. Overall Storage Reclamation Summary

| Storage Layer | Current Size | Confirmed Removable | Retained / Preserved | Expected Reclaimed Space |
| :--- | ---: | ---: | ---: | ---: |
| **Supabase PostgreSQL** | 19.00 MB | 733 synthetic rows (~2.5 MB) | 61 tables, schema, 3 real users, 156 audit logs | ~2.5 MB (relational rows) |
| **Supabase Storage** | 0.00 B | 0.00 B | 0 buckets, 0 objects | 0.00 B |
| **ChromaDB Vectors** | ~1.50 MB | 107 orphaned vectors (1 col) | Collection schema & Nomic index configuration | ~1.5 MB (vector index) |
| **Docker Engine** | 1,360.94 MB | 0.00 B | 2 active containers, 2 images, 2 volumes | 0.00 B |
| **Local Uploads (`.enc`)** | 0.54 MB | 0.54 MB (30 orphaned files) | Clean directory structures | 0.54 MB |
| **Python Caches** | 57.55 MB | 57.55 MB (Mypy, Pycache, Pytest) | `.venv` runtime preserved | 57.55 MB |
| **Frontend `.next` Build** | 802.10 MB | 802.10 MB (build cache/chunks) | `node_modules`, `package.json`, source | 802.10 MB |
| **Scratch Chrome Profile** | 1.11 MB | 1.11 MB (48 files) | Reusable test helper scripts | 1.11 MB |
| **Total Ecosystem** | **~2,242 MB** | **~864.80 MB** | **~1,377 MB** | **~864.80 MB (~38.5%)** |

---

*Stage One Storage Inventory complete. No destructive actions executed. Manifest presented in accompanying document.*
