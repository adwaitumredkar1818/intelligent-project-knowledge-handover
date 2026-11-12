# The Handover — Current Implementation Status

## 1. Truthful Implementation Matrix

| Module & Capability | Code / File Location | Database Tables | Current Status | Notes & Verification Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Platform Authentication** | `app/api/routes/auth.py`, `app/services/auth.py` | `users`, `refresh_sessions` | **Existing and verified** | Password hashing (Argon2id), JWT access tokens, HttpOnly refresh cookies, rotation, session revocation. 36 passing unit tests. |
| **Scope-Separated RBAC** | `app/core/rbac_catalog.py`, `app/models/rbac.py`, `app/services/rbac.py` | `roles`, `permissions`, `role_permissions`, `user_roles` | **Existing and verified** | 15 permissions, 7 system roles, platform/org/project scopes. Seed catalog verified. |
| **Multi-Tenant Organisations** | `app/api/routes/organisations.py`, `app/services/organisation.py` | `organisations`, `organisation_memberships`, `organisation_invitations` | **Existing and verified** | Org creation, member management, invitation lifecycle, role assignment. Verified in unit tests. |
| **Project Workspaces (Core)** | `app/api/routes/projects.py`, `app/services/project.py` | `projects`, `project_memberships` | **Existing and verified** | Create project, list by org, get detail with caller permissions, update, archive. Verified in unit tests. |
| **Project Transition Participants** | Planned: `app/models/project.py`, `app/api/routes/projects.py` | Planned: `project_transitions` | **Currently being implemented** | Needs departing member, successor, handover scope, dates, and validation rules. |
| **Project Overview Aggregation** | Planned: `app/api/routes/projects.py`, `app/services/project.py` | Grouped query across `projects`, `evidence_items`, `audit_logs` | **Currently being implemented** | Grouped metrics for dashboard wireframe (summary, sources, evidence, knowledge, attention, activity). |
| **Project Recent Activity** | Planned: `app/api/routes/projects.py`, `app/services/project.py` | `audit_logs`, `source_sync_jobs` | **Currently being implemented** | Project-scoped event feed. |
| **Connected Sources (GitHub)** | Planned: `app/services/integrations/github.py`, `app/models/source.py` | Planned: `source_connections`, `project_source_mappings` | **Currently being implemented** | OAuth token management, accessible repo discovery, repo mapping to projects, idempotent sync. |
| **Connected Sources (Jira)** | Planned: `app/services/integrations/jira.py`, `app/models/source.py` | Planned: `source_connections`, `project_source_mappings` | **Currently being implemented** | Atlassian 3LO OAuth, cloud_id discovery, Jira project mapping, issue ingestion. |
| **Connected Sources (Slack)** | Config flag `SLACK_ENABLED=false` | None | **Planned** | Strictly optional MVP integration; disabled by default. |
| **Document Upload & Storage** | Planned: `app/services/evidence/upload.py` | Planned: `document_files`, `evidence_items` | **Currently being implemented** | Encrypted local storage (`UPLOAD_STORAGE_PATH`), SHA-256 deduplication, file magic check. |
| **Document Parsing (PDF/DOCX)** | Planned: `app/services/evidence/extractors.py` | Planned: `evidence_contents` | **Currently being implemented** | PyMuPDF text/table extraction with page references, `python-docx` parser. |
| **Scanned Document OCR** | Planned: `app/services/evidence/ocr.py` | Planned: `document_files.ocr_applied` | **Currently being implemented** | Local Ollama `glm-ocr:latest` behind replaceable service abstraction. |
| **Unified Evidence Library** | Planned: `app/api/routes/evidence.py`, `app/services/evidence.py` | Planned: `evidence_items`, `evidence_contents` | **Currently being implemented** | Search, multi-criteria filtering, sorting, bounded pagination. |
| **Evidence Details & Provenance** | Planned: `app/api/routes/evidence.py` | Planned: `evidence_items`, `evidence_contents`, `document_files` | **Currently being implemented** | Detail view, original source URLs, extracted chunks with page numbers, authenticated download. |
| **Source ACL Enforcement** | Planned: `app/api/deps.py`, `app/services/evidence.py` | Planned: `source_connections`, `project_source_mappings` | **Currently being implemented** | Read-time check ensuring project members without source access cannot view restricted evidence. |
| **PostgreSQL Async Worker** | Planned: `app/worker.py` | Planned: `source_sync_jobs`, `document_jobs` | **Currently being implemented** | Lightweight polling worker; job leasing, retries, failure recording. |
| **Knowledge Intelligence (Extraction)**| Models planned | `knowledge_items` | **Planned** | LLM extraction into 8 knowledge categories deferred to subsequent phase. |
| **Relationship Explorer** | Models planned | `knowledge_relationships` | **Planned** | Exact-ID and candidate link storage; graph visualization deferred. |
| **Verification Center (Review)** | Schemas planned | `verification_records` | **Planned** | Human-in-the-loop review queue deferred to subsequent phase. |
| **Handover Workspace (Compilation)**| Schemas planned | `handovers` | **Planned** | Handover package compilation and sign-off deferred to subsequent phase. |
| **Project Knowledge Assistant** | RAG infrastructure ready | None | **Planned** | Hybrid RAG conversational query interface deferred to subsequent phase. |
| **Frontend UI Screens** | `frontend/` shell ready | None | **Deferred** | Implementation strictly deferred until backend completion and verification. |
