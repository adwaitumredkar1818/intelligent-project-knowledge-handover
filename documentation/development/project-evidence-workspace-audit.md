# Project Workspace & Evidence Workspace Implementation Audit

## 1. Executive Summary & Audit Context
In accordance with Part 5 of the Master Implementation Directive for **The Handover** (**Intelligent Project Knowledge Reconstruction & Handover Platform**), this audit evaluates every capability proposed for **Module 1 (Project Workspace)** and **Module 2 (Evidence Workspace)** against the actual codebase as of Phase 2.3.

The inspection verified:
- **FastAPI Core & Auth/RBAC**: Fully implemented and tested (36 passing unit tests, 0 Ruff errors, 0 strict Mypy issues across 68 source files).
- **Multi-Tenant Organisations & Core Projects**: Implemented and tested in migration `0003_org_project_workspaces`.
- **Project Transition Configuration & Dashboard Aggregation**: Missing from current models and routes; requires additive schema and service methods.
- **Evidence Workspace**: Completely missing from existing codebase. No source connection models, no evidence library, no upload endpoints, no extraction worker.
- **Frontend**: Baseline shell exists; frontend code is explicitly deferred until backend completion and verification.

---

## 2. Capability Audit Matrix

| Capability | Existing Implementation Location | Existing Database Tables | Existing Service | Existing API | Existing Tests | Known Defects / Gaps | Missing Behaviour | Required Changes | Audit State |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Organisation Management** | `app/api/routes/organisations.py`, `app/models/organisation.py` | `organisations`, `organisation_memberships`, `organisation_invitations` | `OrganisationService` | `POST /organisations`, `GET /organisations`, `POST /invitations` | `tests/test_rbac_and_constraints.py` | None | None | None (Reuse as-is) | **Fully implemented and tested** |
| **Project Workspace Foundation** | `app/api/routes/projects.py`, `app/models/project.py` | `projects`, `project_memberships` | `ProjectService` | `POST /organisations/{org_id}/projects`, `GET /organisations/{org_id}/projects`, `GET /projects/{id}`, `PATCH /projects/{id}`, `POST /projects/{id}/archive` | `tests/test_rbac_and_constraints.py` | None | No transition participant fields or responsibilities | Add transition config model and responsibility field | **Implemented but incomplete** |
| **Project Team Members** | `app/api/routes/projects.py` | `project_memberships` | `ProjectService` | `GET /projects/{id}/members`, `POST /projects/{id}/members`, `PATCH /projects/{id}/members/{uid}/role`, `DELETE /projects/{id}/members/{uid}` | `tests/test_rbac_and_constraints.py` | None | Responsibility description not persisted on membership | Add `responsibility_description` to `project_memberships` | **Implemented but incomplete** |
| **Project Transition Configuration** | None | None | None | None | None | Completely missing | Cannot define departing member, successor, handover scope, capture dates, or workflow stage | Create `project_transitions` model, repo, service, schemas, and `GET/PUT /projects/{id}/transition` API | **Missing** |
| **Project Overview Aggregation** | None | None | None | None | None | Completely missing | No endpoint aggregating summary, sources, evidence, knowledge, attention, activity, and team ownership | Build `GET /projects/{id}/overview` aggregating real DB records efficiently in grouped queries | **Missing** |
| **Project Activity Stream** | Partial (`audit_logs`) | `audit_logs` | `AuditService` | None (internal only) | `tests/test_db_lifecycle.py` | Audit events recorded but not queryable by project members | No project-scoped activity feed API | Implement `GET /projects/{id}/activity` reading project audit records | **Implemented but not integrated** |
| **Connected Sources (GitHub)** | None | None | None | None | None | Completely missing | No OAuth token storage, repo discovery, repo mapping, or sync worker | Create `source_connections`, `project_source_mappings`, GitHub OAuth client, and sync pipeline | **Missing** |
| **Connected Sources (Jira)** | None | None | None | None | None | Completely missing | No Atlassian OAuth, site discovery, project mapping, or issue sync | Create Jira OAuth client, project mapping, and issue sync pipeline | **Missing** |
| **Document Upload & Encryption** | Config exists (`UPLOAD_STORAGE_PATH`, `FILE_ENCRYPTION_KEY`) | None | None | None | `tests/test_config.py` (settings test only) | Upload directory defined in config but no upload route or encrypted file handling | File validation, SHA-256 deduplication, AES encryption at rest, private storage | Create `document_files` model, file service, and `POST /projects/{id}/evidence/upload` | **Missing** |
| **Document Extraction (PDF/DOCX)** | Dependencies installed (`pymupdf`, `python-docx`) | None | None | None | None | Library available in venv but no extraction service wired | PyMuPDF text/table extraction with page numbers, `python-docx` headings/tables | Implement document extraction service and chunking logic | **Missing** |
| **Scanned Document OCR (GLM OCR)** | Ollama running with `glm-ocr:latest` | None | None | None | None | Model running locally on port 11434 but no backend abstraction | Replaceable OCR abstraction invoking local Ollama OCR endpoint for scanned pages | Implement OCR service abstraction with hardware throttling | **Missing** |
| **Unified Evidence Library** | None | None | None | None | None | Completely missing | No evidence catalog, search, provider filters, record type filters, or pagination | Create `evidence_items`, `evidence_contents` models, repository, service, and `GET /projects/{id}/evidence` API | **Missing** |
| **Evidence Details & Provenance** | None | None | None | None | None | Completely missing | No detail endpoint returning extracted text, page references, source URL, or authenticated download | Create `GET /evidence/{id}` and `GET /evidence/{id}/download` with source ACL enforcement | **Missing** |
| **Source Access Control (ACLs)** | None | None | None | None | None | Completely missing | No check verifying whether project member has credentials for private external source | Enforce source-level permissions in dependency / service layer before returning evidence | **Requires security review** |
| **PostgreSQL Async Worker** | Job polling configuration exists in settings | None | None | None | None | Worker settings present in `.env` (`WORKER_POLL_INTERVAL_SECONDS`) but worker script missing | No background job claiming, leasing, execution, or retry mechanism | Implement `app/worker.py` and job records table (`source_sync_jobs`) | **Missing** |

---

## 3. Detailed Gap Analysis & Defect Inventory

### 3.1 Project Workspace Gaps
1. **Transition Participants**: The `Project` model does not store departing member or successor pointers, nor capture scopes. A dedicated `project_transitions` table is needed to link departing member and successor to the project, validate that they are distinct active users, and record workflow stages.
2. **Member Responsibility Description**: `ProjectMembership` records role assignments but lacks a `responsibility_description` field to record why a member is involved or what components they own.
3. **Overview Dashboard Aggregation**: The future UI dashboard (Proposal page 9, Fig. 4) expects a unified `GET /projects/{project_id}/overview` response. Calling individual endpoints creates severe frontend overhead. The backend must provide a single consolidated aggregation service that queries real database counts.
4. **Project Activity Endpoint**: Audit events are recorded in `audit_logs` during project and member operations, but no API exposes them to authorised project members.

### 3.2 Evidence Workspace Gaps
1. **Source Connection Persistence**: OAuth tokens and credentials must be stored securely. A `source_connections` table with encrypted token columns (`encrypted_access_token`, `encrypted_refresh_token`) is required.
2. **Project-to-Resource Mapping**: A `project_source_mappings` table is needed to associate an external repository (e.g., `octocat/Hello-World`) or Jira project (e.g., `PROJ`) with a specific project workspace.
3. **Evidence Entity Model**: Canonical `evidence_items` table is required to store all ingested items (commits, PRs, issues, document pages) with provider, record type, author, external ID, source URL, content hash, and processing status.
4. **Uploaded File Entity Model**: `document_files` table is required to store uploaded file metadata, SHA-256 hash, storage path, encryption status, page count, and OCR status.
5. **Extracted Content / Chunks**: `evidence_contents` table is required to store extracted text, chunk index, page number, section heading, and token count.
6. **Source ACL Policy**: Crucial security rule: `Project membership != Source access`. The backend must enforce that a user requesting private repository evidence either owns the connection or has verified external access to that repository.
7. **Document Extraction & OCR**: Must integrate PyMuPDF for native PDF text and tables, `python-docx` for Word files, and local Ollama `glm-ocr:latest` for image/scanned PDF pages.
8. **Asynchronous Background Processing**: Ingestion and OCR jobs must run asynchronously via a PostgreSQL-backed job runner (`source_sync_jobs`), preserving hardware safety (no concurrent Qwen3 8B and GLM OCR execution).
