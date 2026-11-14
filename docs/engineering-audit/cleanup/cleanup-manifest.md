# The Handover — Pre-Execution Cleanup Manifest

**Document Type:** Formal Cleanup Manifest & Risk Assessment (Stage One Gate)  
**Date:** November 14, 2026  
**Status:** **PENDING EXPLICIT USER APPROVAL — ZERO DELETIONS PERFORMED**  
**Database Target:** Supabase PostgreSQL 17.11 (`aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres`)  
**Project Reference:** `rjntmboskzyrsqcetzil`  
**Current Alembic Revision:** `0016_rls_hardening`  
**Author:** Antigravity Engineering Lead  

---

## CRITICAL SAFETY PROTOCOL & STOP NOTICE

> [!IMPORTANT]
> **NO DELETIONS HAVE BEEN EXECUTED.**  
> In compliance with Critical Safety Requirements (Section 1 and Section 3), this manifest presents a complete, itemized dry-run proposal. No database records, storage objects, vectors, docker volumes, or repository files will be modified or deleted until the user explicitly reviews and approves this document.

---

## A. Supabase Database Proposed Deletions

### A.1 Overview & Deletion Policy
- **Total Tables in Public Schema:** 61 base tables.
- **Tables Targeted for Record Deletion:** 27 tables (all synthetic test records).
- **Tables Strictly Preserved:** 34 tables (including `roles`, `permissions`, `role_permissions`, `alembic_version`, `user_roles`, `audit_logs`, and all empty schemas).
- **Real Users Protected:** 3 accounts (`adwaitumredkar1818@gmail.com`, `shubham392007@gmail.com`, `engineer_live@handover.internal`) — **0% impacted**.
- **Audit Logs Protected:** All 156 records in `audit_logs` are preserved intact. Foreign keys use `ON DELETE SET NULL`, maintaining the immutable audit trail.
- **Estimated Database Storage Reclaimed:** ~2.5 MB (out of 19 MB total).

### A.2 Itemized Table Deletion Schedule (Dependency-Aware Order)

#### Step 1: Assistant Domain Child Records
| Table | Record Count | Primary Identifiers / Filter Criteria | Classification | Cascade / FK Implications | Estimated Reclaimed |
| :--- | ---: | :--- | :--- | :--- | ---: |
| `assistant_feedback` | 2 | `conversation_id IN (SELECT id FROM assistant_conversations WHERE project_id IN (<test_project_ids>))` | `CONFIRMED_TEST_DATA` | Leaf node; no children. | 8 kB |
| `assistant_citations` | 4 | `message_id IN (SELECT id FROM assistant_messages WHERE conversation_id IN (...))` | `CONFIRMED_TEST_DATA` | Leaf node; no children. | 8 kB |
| `assistant_retrieval_runs` | 13 | `conversation_id IN (SELECT id FROM assistant_conversations WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Leaf node; no children. | 16 kB |
| `assistant_messages` | 21 | `conversation_id IN (SELECT id FROM assistant_conversations WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Parent of citations & feedback (cleared first). | 24 kB |
| `assistant_conversations` | 9 | IDs: `fa79d2e4`, `fb5056ea`, `0db673c4`, `b37ce0c4`, `88d0a1f1`, `bc8cddd6`, `4ad05812`, `e91b0481`, `6502cc15` | `CONFIRMED_TEST_DATA` | FK to test projects & test users. | 16 kB |

#### Step 2: Handover Domain Child Records
| Table | Record Count | Primary Identifiers / Filter Criteria | Classification | Cascade / FK Implications | Estimated Reclaimed |
| :--- | ---: | :--- | :--- | :--- | ---: |
| `handover_acknowledgements` | 4 | `package_id IN (SELECT id FROM handover_packages WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Leaf node. | 8 kB |
| `handover_deliveries` | 4 | `package_id IN (SELECT id FROM handover_packages WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Leaf node. | 8 kB |
| `handover_ownership_transfers` | 4 | `package_id IN (SELECT id FROM handover_packages WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Leaf node. | 8 kB |
| `handover_signoffs` | 8 | `package_id IN (SELECT id FROM handover_packages WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Leaf node. | 8 kB |
| `handover_responsibility_transfers` | 8 | `package_id IN (SELECT id FROM handover_packages WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Leaf node. | 8 kB |
| `handover_checklist_items` | 40 | `checklist_id IN (SELECT id FROM handover_checklists WHERE package_id IN (...))` | `CONFIRMED_TEST_DATA` | Child of checklists (cleared first). | 24 kB |
| `handover_checklists` | 12 | `package_id IN (SELECT id FROM handover_packages WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Parent of checklist items. | 16 kB |
| `handover_content_links` | 18 | `package_id IN (SELECT id FROM handover_packages WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Links to knowledge items. | 16 kB |
| `handover_readiness_assessments` | 36 | `package_id IN (SELECT id FROM handover_packages WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Leaf node. | 24 kB |
| `handover_status_histories` | 42 | `package_id IN (SELECT id FROM handover_packages WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Leaf node. | 16 kB |
| `handover_package_sections` | 48 | `package_id IN (SELECT id FROM handover_packages WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Modular dossier content. | 32 kB |
| `handover_package_versions` | 6 | `package_id IN (SELECT id FROM handover_packages WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Version history. | 16 kB |
| `handover_packages` | 6 | IDs: `8113433f`, `b130173c`, `7f8a6ebb`, `2b6347ca`, `9483da90`, `0eb732ba` | `CONFIRMED_TEST_DATA` | Master dossier records. | 16 kB |
| `handover_cases` | 6 | All 6 handover test workflow containers attached to test projects | `CONFIRMED_TEST_DATA` | Parent of packages. | 16 kB |

#### Step 3: Verification & Knowledge Child Records
| Table | Record Count | Primary Identifiers / Filter Criteria | Classification | Cascade / FK Implications | Estimated Reclaimed |
| :--- | ---: | :--- | :--- | :--- | ---: |
| `verification_context_requests` | 1 | `case_id IN (SELECT id FROM verification_cases WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Leaf node. | 8 kB |
| `verification_issues` | 2 | `case_id IN (SELECT id FROM verification_cases WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Leaf node. | 16 kB |
| `verification_review_events` | 6 | `case_id IN (SELECT id FROM verification_cases WHERE project_id IN (...))` | `CONFIRMED_TEST_DATA` | Leaf node. | 40 kB |
| `verification_cases` | 25 | All 25 verification cases attached to test projects | `CONFIRMED_TEST_DATA` | Test cases from `run_verification_center_audit.py`. | 24 kB |
| `knowledge_evidence_links` | 27 | All 27 links joining synthetic knowledge items to test evidence | `CONFIRMED_TEST_DATA` | Bridge table between knowledge & evidence. | 16 kB |
| `knowledge_items` | 34 | All 34 items in test projects (`Item to Reject via API`, etc.) | `CONFIRMED_TEST_DATA` | Category findings from test extractions. | 32 kB |
| `evidence_chunks` | 13 | All 13 chunks belonging to synthetic assistant test documents | `CONFIRMED_TEST_DATA` | Child of `evidence_items`. | 88 kB |
| `evidence_items` | 31 | All 31 test documents (13 assistant mocks + 18 test PDFs) | `CONFIRMED_TEST_DATA` | Master evidence items in test projects. | 120 kB |

#### Step 4: Membership, Project, Organisation & User Records
| Table | Record Count | Primary Identifiers / Filter Criteria | Classification | Cascade / FK Implications | Estimated Reclaimed |
| :--- | ---: | :--- | :--- | :--- | ---: |
| `refresh_sessions` | 31 | `user_id IN (<41_test_user_ids>)` | `CONFIRMED_TEST_DATA` | Auth sessions for synthetic test users. | 32 kB |
| `project_memberships` | 41 | All 41 memberships linking test users to the 20 test projects | `CONFIRMED_TEST_DATA` | Zero real users impacted. | 32 kB |
| `organisation_memberships` | 38 | All 38 memberships linking test users to the 20 test orgs | `CONFIRMED_TEST_DATA` | Zero real users impacted. | 32 kB |
| `projects` | 20 | All 20 projects (`assistant-proj-*`, `handover-proj-*`, `verif-proj-*`) | `CONFIRMED_TEST_DATA` | All child records deleted in Steps 1–3. | 32 kB |
| `organisations` | 20 | All 20 orgs (`assistant-org-*`, `handover-org-*`, `verif-org-*`) | `CONFIRMED_TEST_DATA` | All projects & memberships cleared above. | 24 kB |
| `users` (Synthetic Accounts Only) | 41 | `email LIKE '%@example.com'` (41 users: Alice, Bob, Carol, etc.) | `CONFIRMED_TEST_DATA` | Excludes real users (`adwaitumredkar1818@gmail.com`, `shubham392007@gmail.com`, `engineer_live@handover.internal`). | 32 kB |

---

## B. Supabase Storage Proposed Object Cleanup

- **Target Bucket:** `project-evidence`
- **Current Bucket Count in Database (`storage.buckets`):** **0**
- **Current Object Count in Database (`storage.objects`):** **0**
- **Proposed Object Deletions:** **0 Objects**
- **Estimated Space Reclaimed:** **0 Bytes**
- **Assessment:** No remote storage objects exist. Development upload operations operated in `local_encrypted` filesystem mode.

---

## C. Local Repository Proposed Cleanup

| Category / Target Pattern | Path / Location | File Count | Current Size | Safety Classification | Action Description | Reclaimed Space |
| :--- | :--- | ---: | ---: | :--- | :--- | ---: |
| **Frontend Next.js Build** | `frontend/.next` | 2,261 | 841.06 MB | Safe (Build Artifact) | Delete `.next/` directory. Fully rebuilt on `npm run build`. | **841.06 MB** |
| **Backend Mypy Cache** | `backend/.mypy_cache` | 18 | 29.24 MB | Safe (Cache) | Delete directory. Regenerated automatically by `mypy`. | **29.24 MB** |
| **Root Mypy Cache** | `.mypy_cache` | 19 | 25.82 MB | Safe (Cache) | Delete directory. Regenerated automatically by `mypy`. | **25.82 MB** |
| **Non-Venv Bytecode** | `__pycache__` (in `app`, `tests`, etc.) | 15 dirs | 5.25 MB | Safe (Cache) | Remove `__pycache__` outside `backend/.venv`. | **5.25 MB** |
| **Headless Chrome Profile** | `scratch/chrome-cdp-profile-phase4` | 48 | 1.17 MB | Safe (Temp Test Data) | Delete temporary browser cache generated by Phase 4 CDP. | **1.17 MB** |
| **Orphaned Local Uploads** | `data/uploads/` & `backend/data/uploads/` | 30 files | 0.54 MB | Safe (Unreferenced Files) | Delete 30 `.enc` files unreferenced by any database row. | **0.54 MB** |
| **Pytest Caches** | `backend/.pytest_cache` & `.pytest_cache` | 9 | 0.02 MB | Safe (Cache) | Delete directories. Regenerated on `pytest`. | **0.02 MB** |
| **Ruff Caches** | `backend/.ruff_cache` & `.ruff_cache` | 14 | 0.02 MB | Safe (Cache) | Delete directories. Regenerated on `ruff`. | **0.02 MB** |
| **Local Repository Subtotal** | — | **2,414** | **903.12 MB** | **Safe to Clean** | — | **903.12 MB** |

### Preserved Local Components (DO NOT TOUCH)
- `frontend/node_modules/` (476.73 MB, 28,171 files) — **PRESERVED** (per prompt rules).
- `backend/.venv/` (235.01 MB, 7,822 files) — **PRESERVED** (active Python runtime).
- `graphify-out/` (50.17 MB, 553 files) — **PRESERVED** (codebase knowledge graph).
- `docs/engineering-audit/` (including 55 screenshots, 7.39 MB) — **PRESERVED** (audit history).
- `.git/` (5.27 MB, 1,816 files) — **PRESERVED** (version history).
- `backend/tests/` & test source code — **PRESERVED** (CI and regression test suite).

---

## D. Docker Storage Proposed Cleanup

- **Running Containers:** `ipkrh-postgres` (Postgres 16) & `ipkrh-chromadb` (ChromaDB)
- **Active Images:** `postgres:16-alpine` (420 MB), `chromadb/chroma:latest` (826 MB)
- **Active Volumes:** `ipkrh_postgres_data` (local DB fallback), `ipkrh_chroma_data` (Chroma data)
- **Proposed Docker Pruning:** **NONE (0 B)**
- **Safety Assessment:** Critical Safety Rule 14 mandates never removing active database volumes or Docker infrastructure required by the application. All Docker resources remain active and untouched.

---

## E. ChromaDB Vector Store Proposed Cleanup

- **Target Collection:** `ipkrh_evidence_chunks_nomic-embed-text_v1`
- **Total Vectors in Collection:** 107
- **Target Project:** `c8869ad9-c14b-4886-8617-e691fca6ef5d` (107 / 107 vectors)
- **Database Cross-Reference Status:** Project `c8869ad9...` exists in **neither** Supabase nor local PostgreSQL.
- **Classification:** **`ORPHANED_RECORD` / `CONFIRMED_TEST_DATA`**
- **Proposed Action:** Issue HTTP DELETE request to ChromaDB `/api/v2` to purge the 107 orphaned test vectors while preserving collection schema and dimension metadata:
  ```http
  POST /api/v2/tenants/default_tenant/databases/default_database/collections/23a5f8ad-fb46-46cf-ad33-2ee5bafe068b/delete
  Content-Type: application/json
  {"where": {"project_id": "c8869ad9-c14b-4886-8617-e691fca6ef5d"}}
  ```
- **Estimated Storage Reclaimed:** ~1.5 MB in ChromaDB index.
- **Preservation:** Pinned model (`nomic-embed-text`), 768 dimensions, `index_version=v1`, and collection identity are preserved.

---

## F. Summary & Risk Analysis

### F.1 Reclamation Projection
| Category | Current Storage | Removable | Preserved | Projected Reclaim |
| :--- | ---: | ---: | ---: | ---: |
| **Supabase PostgreSQL** | 19.00 MB | 733 synthetic rows | 61 tables, 3 real users, 156 audit logs | ~2.5 MB |
| **Supabase Storage** | 0.00 B | 0.00 B | 0 buckets, 0 objects | 0.00 B |
| **ChromaDB Vector Store** | ~1.50 MB | 107 orphaned vectors | Collection schema & config | ~1.50 MB |
| **Docker Engine** | 1,360.94 MB | 0.00 B | 2 containers, 2 images, 2 volumes | 0.00 B |
| **Local File System** | 1,643.14 MB | 903.12 MB | Code, node_modules, .venv, audit docs | 903.12 MB |
| **Total Ecosystem** | **~3,024 MB** | **~907.12 MB** | **~2,117 MB** | **~907.12 MB (~30.0%)** |

### F.2 Risks & Mitigation Protocols
1. **Risk:** Accidental deletion of real platform accounts.  
   **Mitigation:** Hardcoded SQL safety filter: `WHERE email NOT IN ('adwaitumredkar1818@gmail.com', 'shubham392007@gmail.com', 'engineer_live@handover.internal')` combined with strict verification that all deleted emails match RFC 2606 `@example.com`.
2. **Risk:** Loss of audit trail continuity.  
   **Mitigation:** Zero rows in `audit_logs` are deleted. All foreign key constraints use `ON DELETE SET NULL`, preserving event records permanently.
3. **Risk:** Schema or Alembic corruption.  
   **Mitigation:** Zero DDL operations. No table drops, alters, or schema resets. Alembic remains at `0016_rls_hardening`.
4. **Risk:** Remote Supabase Pooler transaction timeout during batch deletion.  
   **Mitigation:** Executed inside an explicit single-transaction block with a verified pre-check row count before `COMMIT`.

---

## APPROVAL GATE

**STAGE ONE DRY RUN IS COMPLETE.**

To proceed with **Stage Two (Execution)**:
- Please review and provide explicit approval for the proposed deletions documented above.
- Upon approval, the deletion will execute in strict dependency order, followed by post-cleanup validation and generation of the final cleanup report.
