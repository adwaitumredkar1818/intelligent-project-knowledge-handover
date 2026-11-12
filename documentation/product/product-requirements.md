# The Handover — Product Requirements Document (PRD)

## 1. Functional Requirements

### 1.1 Project Workspace Requirements
- **FR-PW-01 (Multi-Tenancy & Isolation)**: Every project must belong to exactly one Organisation. Cross-organisation leakage or access must be prevented at the database and API levels.
- **FR-PW-02 (Project Lifecycle)**: Support project creation, slug auto-generation and validation, editing metadata, lifecycle status changes (`planning`, `active`, `on_hold`, `completed`, `archived`), and soft archiving with audit tracking.
- **FR-PW-03 (Project Membership & Scoped Roles)**: Manage project members with assigned project-scoped roles (`project_manager`, `project_member`, `reviewer`). Enforce that all project members belong to the parent organisation.
- **FR-PW-04 (Transition Participant Configuration)**: Designate the departing knowledge owner and the incoming successor within the project workspace. Support capture date windows (start/end dates), context notes, handover scope, and relevant source scopes. Enforce that the departing user and successor cannot be the same user without explicit documented override.
- **FR-PW-05 (Dashboard Aggregation)**: Provide high-performance aggregated metrics for the Project Dashboard:
  - Project summary (dates, owner, status, transition participants, stage)
  - Connected sources summary (provider counts, sync health, latest sync timestamps)
  - Evidence overview (counts by provider, record type, document count, processing status)
  - Knowledge overview (counts by category, candidate vs verified status, availability flags)
  - Attention required (sync failures, processing errors, unresolved conflicts, re-authorisation needs)
  - Recent project activity (chronological event stream of memberships, uploads, syncs, and audit logs)
  - Team knowledge ownership (responsibility allocations per team member)

### 1.2 Evidence Workspace Requirements
- **FR-EW-01 (Three-Panel Architecture)**: Provide backend schemas and APIs corresponding to Panel A (Connected Sources), Panel B (Evidence Library), and Panel C (Evidence Details).
- **FR-EW-02 (External Source Connections)**:
  - **GitHub**: Delegated OAuth 2.0 connection, token encryption at rest, discovery of user-accessible repositories, explicit project-to-repository mapping, manual and incremental sync trigger, and token revocation/disconnection.
  - **Jira**: Delegated Atlassian OAuth 2.0 connection, accessible Cloud ID and site discovery, Jira project discovery and mapping to platform projects, issue/comment sync.
  - **Slack (Optional)**: Disabled by default. Only enabled when specifically authorised with verified scopes and data retention rules.
- **FR-EW-03 (Document Upload & Processing)**:
  - Secure multi-part upload for PDF and DOCX files up to 50 MB.
  - MIME type and file magic number inspection.
  - SHA-256 calculation for project-scoped duplicate detection.
  - Storage in AES/Fernet-encrypted private storage outside public web roots.
  - PyMuPDF text/table extraction with page-level coordinates and references.
  - Automatic fallback to local GLM OCR (`glm-ocr:latest` on Ollama) for scanned, image-only PDF pages.
  - `python-docx` extraction for headings, paragraphs, and tables.
- **FR-EW-04 (Unified Evidence Library)**:
  - Searchable, filterable, paginated index of evidence records across all connected sources and documents.
  - Search across title, filename, source ID, author, commit SHA, Jira key, and extracted text.
  - Filter by source provider (`github`, `jira`, `pdf`, `docx`, `slack`), record type, processing status, and date range.
  - Bounded pagination with total counts and provider breakdown.
- **FR-EW-05 (Evidence Details & Provenance)**:
  - Detailed view returning original source metadata, author, timestamps, source URL, page numbers, extracted text, chunk index references, and associated knowledge items.
  - Authenticated document download/preview URL generation.
  - Clean sanitisation of all backend storage paths and encryption keys.
- **FR-EW-06 (Source ACL Enforcement)**:
  - Re-verify requesting user's source access before returning private repository or Jira issue evidence. Fail closed if the user lacks source credentials.

---

## 2. Non-Functional Requirements

### 2.1 Security & Compliance
- **NFR-SEC-01**: Zero secrets in client-side code, logs, or API responses.
- **NFR-SEC-02**: AES-256 / Fernet symmetric encryption for stored OAuth tokens and uploaded files at rest.
- **NFR-SEC-03**: Short-lived JWT access tokens (15 minutes) and HttpOnly, SameSite=Lax refresh cookies.
- **NFR-SEC-04**: Role-Based Access Control enforced strictly on the backend before data retrieval or LLM execution.
- **NFR-SEC-05**: Immutable audit log of all state-changing and access-denial actions in PostgreSQL.

### 2.2 Performance & Scalability
- **NFR-PERF-01**: Read API response times < 200 ms for 95th percentile under normal local load.
- **NFR-PERF-02**: Ingestion and OCR jobs must run asynchronously in background workers without blocking HTTP request threads.
- **NFR-PERF-03**: Hardware throttling: Never run Qwen3 8B inference and GLM OCR concurrently on single-GPU/CPU local environments.

### 2.3 Reliability & Data Integrity
- **NFR-REL-01**: PostgreSQL 16 is the sole authoritative canonical store. Vector indices in ChromaDB must be secondary and fully rebuildable.
- **NFR-REL-02**: All migration scripts must be strictly additive, safe, and reversible.
- **NFR-REL-03**: Zero data fabrication. Synthetic test fixtures must never be presented as real connected organisational evidence.
