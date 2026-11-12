# The Handover — Evidence Workspace Specification

## 1. Module Overview & Responsibilities
The **Evidence Workspace** (presented in UI navigation as **Evidence Center**) is the central evidence ingestion, processing, and inspection hub. It is responsible for:
- Connecting external platforms (GitHub, Jira, and optional future Slack).
- Ingesting, parsing, and storing native PDF, DOCX, and scanned documents.
- Preserving strict cryptographic hashes, page coordinates, and source provenance.
- Enforcing source access control (Project membership != Source access).
- Providing unified search, filtering, and pagination over all evidence items.
- Rendering comprehensive Evidence Details for individual items with source URLs and download links.
- Orchestrating asynchronous sync and extraction jobs backed by PostgreSQL.

---

## 2. Three-Panel Architecture & Layout

```text
┌──────────────────────────┬─────────────────────────────┬───────────────────────────┐
│ PANEL A: CONNECTED       │ PANEL B: EVIDENCE LIBRARY   │ PANEL C: EVIDENCE DETAILS │
│ SOURCES                  │ (Search, Filter, Paginated) │ (Provenance, Text, Chunks)│
├──────────────────────────┼─────────────────────────────┼───────────────────────────┤
│ • GitHub Account & Repos │ • Search bar (title, text)  │ • Original Source Info    │
│ • Jira Site & Projects   │ • Filters: Provider, Type,  │ • Author & Timestamps     │
│ • PDF Uploads & Status   │   Status, Date Range        │ • Extracted Content & Page│
│ • DOCX Uploads & Status  │ • Sort: Date, Name, Status  │ • Source Reference / URL  │
│ • Slack (if authorized)  │ • Columns: Name, Provider,  │ • Related Evidence Items  │
│ • Trigger Sync button    │   Type, Author, Time, Status│ • Download / Preview URL  │
└──────────────────────────┴─────────────────────────────┴───────────────────────────┘
```

---

## 3. Data Models & Entity Schema

### 3.1 Source Connections (`source_connections`)
- `id` (UUID, Primary Key)
- `organisation_id` (UUID, Foreign Key -> `organisations.id`, CASCADE)
- `connected_by_id` (UUID, Foreign Key -> `users.id`, RESTRICT)
- `provider` (VARCHAR(32), Enum: `github`, `jira`, `slack`)
- `account_identifier` (VARCHAR(255), e.g., GitHub username or Atlassian account email)
- `encrypted_access_token` (TEXT, Non-Null — Fernet/AES encrypted)
- `encrypted_refresh_token` (TEXT, Nullable — Fernet/AES encrypted)
- `token_expires_at` (TIMESTAMPTZ, Nullable)
- `scopes` (JSONB, Array of granted OAuth scopes)
- `connection_status` (VARCHAR(32), Enum: `connected`, `needs_reauth`, `disconnected`, `error`)
- `last_health_check_at` (TIMESTAMPTZ, Nullable)
- `error_message` (TEXT, Nullable)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

### 3.2 Project Source Mappings (`project_source_mappings`)
- `id` (UUID, Primary Key)
- `project_id` (UUID, Foreign Key -> `projects.id`, CASCADE)
- `source_connection_id` (UUID, Foreign Key -> `source_connections.id`, CASCADE)
- `external_resource_id` (VARCHAR(255), e.g., GitHub repo full name `org/repo` or Jira project key `PROJ`)
- `external_resource_name` (VARCHAR(255))
- `external_metadata` (JSONB, e.g., cloud_id for Jira, visibility for GitHub)
- `sync_status` (VARCHAR(32), Enum: `idle`, `syncing`, `completed`, `failed`)
- `last_synced_at` (TIMESTAMPTZ, Nullable)
- `sync_error` (TEXT, Nullable)
- `is_active` (BOOLEAN, Default True)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

### 3.3 Evidence Items (`evidence_items`)
- `id` (UUID, Primary Key)
- `project_id` (UUID, Foreign Key -> `projects.id`, CASCADE)
- `source_mapping_id` (UUID, Foreign Key -> `project_source_mappings.id`, SET NULL, Nullable)
- `provider` (VARCHAR(32), Enum: `github`, `jira`, `pdf`, `docx`, `slack`)
- `record_type` (VARCHAR(64), e.g., `repository`, `pull_request`, `commit`, `issue`, `comment`, `document_page`, `document_section`)
- `external_source_id` (VARCHAR(500), stable upstream ID or relative file section)
- `source_url` (VARCHAR(2048), Nullable — canonical link to upstream GitHub/Jira record)
- `title` (VARCHAR(500), Non-Null)
- `author` (VARCHAR(255), Nullable — original author name/email/handle)
- `source_created_at` (TIMESTAMPTZ, Nullable)
- `source_updated_at` (TIMESTAMPTZ, Nullable)
- `ingested_at` (TIMESTAMPTZ, Default now())
- `processing_status` (VARCHAR(32), Enum: `pending`, `processing`, `extracted`, `indexed`, `failed`)
- `verification_status` (VARCHAR(32), Enum: `unverified`, `candidate`, `verified`, `conflicted`, `rejected`)
- `content_hash` (VARCHAR(64), SHA-256 of extracted text content)
- `raw_metadata` (JSONB — upstream attributes, labels, tags, PR stats)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

### 3.4 Uploaded Document Files (`document_files`)
- `id` (UUID, Primary Key)
- `evidence_item_id` (UUID, Foreign Key -> `evidence_items.id`, CASCADE, Unique)
- `uploaded_by_id` (UUID, Foreign Key -> `users.id`)
- `original_filename` (VARCHAR(255))
- `file_format` (VARCHAR(16), `pdf` or `docx`)
- `mime_type` (VARCHAR(128))
- `file_size_bytes` (BIGINT)
- `storage_path` (VARCHAR(1024) — opaque server-generated UUID path)
- `sha256_hash` (VARCHAR(64))
- `is_encrypted` (BOOLEAN, Default True)
- `page_count` (INTEGER, Nullable)
- `ocr_applied` (BOOLEAN, Default False)
- `extraction_error` (TEXT, Nullable)
- `created_at` (TIMESTAMPTZ)

### 3.5 Evidence Contents & Chunks (`evidence_contents`)
- `id` (UUID, Primary Key)
- `evidence_item_id` (UUID, Foreign Key -> `evidence_items.id`, CASCADE)
- `chunk_index` (INTEGER, Default 0)
- `page_number` (INTEGER, Nullable)
- `section_heading` (VARCHAR(255), Nullable)
- `content_text` (TEXT, Non-Null)
- `token_count` (INTEGER, Nullable)
- `chroma_point_id` (VARCHAR(128), Nullable)
- `indexing_status` (VARCHAR(32), Enum: `pending`, `indexed`, `failed`)
- `created_at` (TIMESTAMPTZ)

---

## 4. API Endpoints Specification

### 4.1 Connected Sources Management (Panel A)
- `GET /api/v1/projects/{project_id}/sources`: List connected sources for the project with sync status and health.
- `POST /api/v1/projects/{project_id}/sources/{provider}/connect`: Initialize OAuth or map an existing connection.
- `GET /api/v1/projects/{project_id}/sources/{provider}/discover`: Discover accessible repositories or Jira projects using authenticated tokens.
- `POST /api/v1/projects/{project_id}/sources/map`: Map an external repository or Jira project to this platform project.
- `DELETE /api/v1/projects/{project_id}/sources/{mapping_id}`: Unmap source and archive its evidence.
- `POST /api/v1/projects/{project_id}/sources/{mapping_id}/sync`: Trigger manual synchronization job.

### 4.2 Document Upload & Extraction
- `POST /api/v1/projects/{project_id}/evidence/upload`: Multi-part upload (PDF/DOCX). Validates MIME type, calculates SHA-256, encrypts and stores in private folder, creates `evidence_items` record, queues background extraction.
- `GET /api/v1/evidence/{evidence_id}/download`: Generate temporary, authenticated download/preview link.

### 4.3 Evidence Library (Panel B)
- `GET /api/v1/projects/{project_id}/evidence`: Searchable, filterable, paginated evidence list:
  - Query params: `search` (text), `provider` (github, jira, pdf, docx), `record_type`, `processing_status`, `verification_status`, `author`, `date_from`, `date_to`, `limit`, `offset`, `sort_by`, `sort_dir`.
  - Response: list of evidence summaries, total count, facets by provider and status.

### 4.4 Evidence Details (Panel C)
- `GET /api/v1/evidence/{evidence_id}`: Comprehensive details of a selected evidence record:
  - Validates project membership AND external source ACL for the calling user.
  - Returns metadata, author, timestamps, source URL, document file info, extracted content chunks with page numbers, and related evidence references.
