# The Handover — Database Gaps & Backend Implementation Plan (Gate 2)

## 1. Identified Database Schema Gaps

To fully support both **Module 1 (Project Workspace)** and **Module 2 (Evidence Workspace)** without disrupting existing tables (`organisations`, `projects`, `users`, `roles`, `audit_logs`), the following additive schema changes are required in a new Alembic migration (`0004_project_evidence_workspace`):

### 1.1 Project Workspace Additions
1. **`project_memberships.responsibility_description`**:
   - `TEXT, nullable=True`
   - Stores the member's primary domain of ownership or handover responsibility.
2. **`project_transitions` Table**:
   - `id`: UUID (PK)
   - `project_id`: UUID (FK -> `projects.id`, ondelete="CASCADE", unique=True)
   - `departing_user_id`: UUID (FK -> `users.id`, ondelete="RESTRICT")
   - `successor_user_id`: UUID (FK -> `users.id`, ondelete="RESTRICT")
   - `workflow_stage`: VARCHAR(64) default `'planning'`
   - `handover_scope`: TEXT nullable=True
   - `source_scope`: JSONB nullable=True (array of mapped source resource IDs)
   - `capture_start_date`: DATE nullable=True
   - `capture_end_date`: DATE nullable=True
   - `context_notes`: TEXT nullable=True
   - `created_at`: TIMESTAMPTZ default `now()`
   - `updated_at`: TIMESTAMPTZ default `now()`
   - Constraint: `CHECK (departing_user_id != successor_user_id)`

### 1.2 Evidence Workspace Additions
1. **`source_connections` Table**:
   - `id`: UUID (PK)
   - `organisation_id`: UUID (FK -> `organisations.id`, ondelete="CASCADE")
   - `connected_by_id`: UUID (FK -> `users.id`, ondelete="RESTRICT")
   - `provider`: VARCHAR(32) (Enum: `'github'`, `'jira'`, `'slack'`)
   - `account_identifier`: VARCHAR(255) (e.g. GitHub username or Jira email)
   - `encrypted_access_token`: TEXT (Fernet encrypted)
   - `encrypted_refresh_token`: TEXT nullable=True (Fernet encrypted)
   - `token_expires_at`: TIMESTAMPTZ nullable=True
   - `scopes`: JSONB default `'[]'`
   - `connection_status`: VARCHAR(32) default `'connected'`
   - `last_health_check_at`: TIMESTAMPTZ nullable=True
   - `error_message`: TEXT nullable=True
   - `created_at`: TIMESTAMPTZ default `now()`
   - `updated_at`: TIMESTAMPTZ default `now()`
   - Index: `("organisation_id", "provider")`
2. **`project_source_mappings` Table**:
   - `id`: UUID (PK)
   - `project_id`: UUID (FK -> `projects.id`, ondelete="CASCADE")
   - `source_connection_id`: UUID (FK -> `source_connections.id`, ondelete="CASCADE")
   - `external_resource_id`: VARCHAR(255) (e.g. `'org/repo'` or Jira project key `'PMOD'`)
   - `external_resource_name`: VARCHAR(255)
   - `external_metadata`: JSONB default `'{}'` (e.g. cloud_id, default branch, visibility)
   - `sync_status`: VARCHAR(32) default `'idle'` (`'idle'`, `'syncing'`, `'completed'`, `'failed'`)
   - `last_synced_at`: TIMESTAMPTZ nullable=True
   - `sync_error`: TEXT nullable=True
   - `is_active`: BOOLEAN default `True`
   - `created_at`: TIMESTAMPTZ default `now()`
   - `updated_at`: TIMESTAMPTZ default `now()`
   - Unique: `("project_id", "external_resource_id")`
3. **`evidence_items` Table**:
   - `id`: UUID (PK)
   - `project_id`: UUID (FK -> `projects.id`, ondelete="CASCADE")
   - `source_mapping_id`: UUID (FK -> `project_source_mappings.id`, ondelete="SET NULL", nullable=True)
   - `provider`: VARCHAR(32) (Enum: `'github'`, `'jira'`, `'pdf'`, `'docx'`, `'slack'`)
   - `record_type`: VARCHAR(64) (`'repository'`, `'pull_request'`, `'commit'`, `'issue'`, `'comment'`, `'document'`)
   - `external_source_id`: VARCHAR(500)
   - `source_url`: VARCHAR(2048) nullable=True
   - `title`: VARCHAR(500)
   - `author`: VARCHAR(255) nullable=True
   - `source_created_at`: TIMESTAMPTZ nullable=True
   - `source_updated_at`: TIMESTAMPTZ nullable=True
   - `ingested_at`: TIMESTAMPTZ default `now()`
   - `processing_status`: VARCHAR(32) default `'pending'` (`'pending'`, `'processing'`, `'extracted'`, `'indexed'`, `'failed'`)
   - `verification_status`: VARCHAR(32) default `'unverified'` (`'unverified'`, `'candidate'`, `'verified'`, `'conflicted'`, `'rejected'`)
   - `content_hash`: VARCHAR(64) (SHA-256)
   - `raw_metadata`: JSONB default `'{}'`
   - `created_at`: TIMESTAMPTZ default `now()`
   - `updated_at`: TIMESTAMPTZ default `now()`
   - Index: `("project_id", "provider", "record_type")`
   - Index: `("project_id", "processing_status")`
4. **`document_files` Table**:
   - `id`: UUID (PK)
   - `evidence_item_id`: UUID (FK -> `evidence_items.id`, ondelete="CASCADE", unique=True)
   - `uploaded_by_id`: UUID (FK -> `users.id`, ondelete="RESTRICT")
   - `original_filename`: VARCHAR(255)
   - `file_format`: VARCHAR(16) (`'pdf'`, `'docx'`)
   - `mime_type`: VARCHAR(128)
   - `file_size_bytes`: BIGINT
   - `storage_path`: VARCHAR(1024) (server-generated opaque path)
   - `sha256_hash`: VARCHAR(64)
   - `is_encrypted`: BOOLEAN default `True`
   - `page_count`: INTEGER nullable=True
   - `ocr_applied`: BOOLEAN default `False`
   - `extraction_error`: TEXT nullable=True
   - `created_at`: TIMESTAMPTZ default `now()`
   - Index: `("evidence_item_id", "sha256_hash")`
5. **`evidence_contents` Table**:
   - `id`: UUID (PK)
   - `evidence_item_id`: UUID (FK -> `evidence_items.id`, ondelete="CASCADE")
   - `chunk_index`: INTEGER default 0
   - `page_number`: INTEGER nullable=True
   - `section_heading`: VARCHAR(255) nullable=True
   - `content_text`: TEXT
   - `token_count`: INTEGER nullable=True
   - `chroma_point_id`: VARCHAR(128) nullable=True
   - `indexing_status`: VARCHAR(32) default `'pending'`
   - `created_at`: TIMESTAMPTZ default `now()`
   - Index: `("evidence_item_id", "chunk_index")`
6. **`source_sync_jobs` Table**:
   - `id`: UUID (PK)
   - `project_id`: UUID (FK -> `projects.id`, ondelete="CASCADE")
   - `source_mapping_id`: UUID (FK -> `project_source_mappings.id`, ondelete="CASCADE", nullable=True)
   - `job_type`: VARCHAR(64) (`'github_sync'`, `'jira_sync'`, `'document_extraction'`, `'ocr_processing'`)
   - `status`: VARCHAR(32) default `'queued'` (`'queued'`, `'running'`, `'completed'`, `'failed'`)
   - `attempt_count`: INTEGER default 0
   - `max_attempts`: INTEGER default 3
   - `locked_at`: TIMESTAMPTZ nullable=True
   - `locked_by`: VARCHAR(128) nullable=True
   - `error_message`: TEXT nullable=True
   - `progress_percent`: INTEGER default 0
   - `started_at`: TIMESTAMPTZ nullable=True
   - `completed_at`: TIMESTAMPTZ nullable=True
   - `created_at`: TIMESTAMPTZ default `now()`

---

## 2. Step-by-Step Implementation Roadmap

```text
┌────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: SHARED DOMAIN FOUNDATION & MIGRATION                          │
│ 1. Define models (`project_transitions`, `source_connections`, etc.)   │
│ 2. Create and verify Alembic migration 0004                            │
│ 3. Add RBAC permissions (`project.transition.manage`, `evidence.*`)    │
├────────────────────────────────────────────────────────────────────────┤
│ STAGE 2: PROJECT WORKSPACE BACKEND                                     │
│ 1. Project Transition repository, service, and schemas                 │
│ 2. Project Overview aggregation service & endpoint                     │
│ 3. Project Activity feed endpoint & repo query                         │
│ 4. Transition & Overview unit tests                                    │
├────────────────────────────────────────────────────────────────────────┤
│ STAGE 3: EVIDENCE WORKSPACE BACKEND                                    │
│ 1. Token Encryption helper (Fernet/AES)                                │
│ 2. Document Upload & Storage Service (AES encryption, SHA-256)         │
│ 3. Document Extraction Service (PyMuPDF native + python-docx)          │
│ 4. Replaceable GLM OCR Service (local Ollama integration)              │
│ 5. GitHub Connector (OAuth, discovery, repo mapping, sync)            │
│ 6. Jira Connector (OAuth, cloud_id discovery, project mapping, sync)   │
│ 7. Unified Evidence Library & Details Service                          │
│ 8. Source ACL Enforcement Policy                                       │
│ 9. Background Job Runner (`app/worker.py` polling `source_sync_jobs`) │
│ 10. Evidence APIs (`GET /sources`, `POST /upload`, `GET /evidence`)    │
├────────────────────────────────────────────────────────────────────────┤
│ STAGE 4: CROSS-MODULE INTEGRATION & E2E TESTING                        │
│ 1. Wire Project Overview to live Evidence and Source counts            │
│ 2. Unit and integration tests for all workflows (A through F)          │
│ 3. Regression test suite execution (39 existing + new tests)           │
│ 4. Ruff and strict Mypy verification                                   │
│ 5. Live Uvicorn HTTP smoke tests with real JSON payloads               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Strict Safety & Governance Commitments
- **Zero data loss**: No existing tables or migration histories dropped or modified destructively.
- **Strict typing**: Python 3.11 type hints throughout, strict Mypy compliance.
- **Zero fabrication**: All tests and services strictly handle authentic or cleanly isolated synthetic test fixtures; no fake production records.
- **Backend first**: No frontend screens or React components generated during this phase.
