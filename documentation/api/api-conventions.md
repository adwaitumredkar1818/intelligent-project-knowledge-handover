# API Conventions & Infrastructure Endpoints

> **Current Stage (Phase 2.6 — AI Knowledge Reconstruction & Structured Intelligence Extraction):** This document describes all **actually implemented** HTTP conventions, error envelopes, security headers, health/readiness probes, Phase 2.2 authentication/identity/RBAC endpoints, Phase 2.3 multi-tenant organisation/invitation/project/audit endpoints, Phase 2.4A project document upload, evidence listing/detail, reprocessing, and logical deletion endpoints, Phase 2.4B delegated GitHub & Jira OAuth connection, discovery, project mapping, ACL verification, and asynchronous sync endpoints, Phase 2.5 permission-aware hybrid search, chunk inspection, indexing status, reindex, and Chroma/FTS health endpoints, and Phase 2.6 evidence-grounded AI knowledge extraction triggers, run monitoring/cancel/retry, and ACL-filtered knowledge query endpoints. Verification review decisions, relationship graph management, handover generation, and assistant synthesis endpoints belong to subsequent phases.

---

## 1. Base URL, Versioning & OpenAPI Visibility

- **Local Development Origin**: `http://127.0.0.1:8000` (frontend public reference: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`).
- **Versioning**: Domain API routes live under `/api/v1` (`app/api/v1/router.py`). Infrastructure process probes (`/health`, `/health/ready`) live at root for orchestrator/load-balancer compatibility alongside `/api/v1/health`.
- **OpenAPI / Interactive Docs**:
  - Enabled in `development` and `test` (`/docs`, `/redoc`, `/openapi.json`).
  - Automatically disabled (`404`) when `APP_ENV=production`.

---

## 2. Correlation IDs, Security Headers & CORS

- **Request Correlation IDs**:
  - Incoming `X-Request-ID` (or fallback `X-Correlation-ID`) is accepted only when it matches `^[A-Za-z0-9._-]{1,64}$` (preventing log injection). Otherwise, a server-generated UUID4 is assigned.
  - Every response (including `4xx` / `5xx` error envelopes) echoes `X-Request-ID` and carries the matching `request_id` field.
- **CORS Defaults**:
  - Origins are restricted explicitly to `CORS_ALLOWED_ORIGINS` (comma-separated or JSON array; wildcard `*` is rejected in all environments since `allow_credentials=true` is configured).
- **Security Headers Applied**:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`

---

## 3. Canonical Error Response Structure

All expected `AppError` exceptions, HTTP errors (`404`, `405`), request validation errors (`422`), and unexpected `500` server errors return the shared `ErrorResponse` JSON schema:

```json
{
  "error": {
    "code": "HTTP_404",
    "message": "Not Found",
    "request_id": "phase21-doc-404",
    "details": null
  }
}
```

### Error Handling Guarantees
- **Expected Application Errors (`AppError`)**: Return their typed HTTP status code and safe domain code/message.
- **Validation Errors (`422`)**: Return `code: "VALIDATION_ERROR"` with `details` containing sanitised `{loc, msg, type}` entries only — raw submitted `input` values are stripped so malformed payloads containing sensitive fields never echo back.
- **Unexpected Server Errors (`500`)**: Logged server-side with `request_id` and secret redaction; clients receive only `code: "INTERNAL_SERVER_ERROR"` and `"An unexpected internal server error occurred."` with zero stack traces, connection strings, or internal host/port details.

---

## 4. Implemented Phase 2.1 Endpoints

### 4.1 `GET /health` — Application Process Liveness
- **Purpose**: Confirms the FastAPI process is running and handling HTTP requests without acquiring a PostgreSQL connection or probing external services.
- **Status Code**: `200 OK`
- **Observed Response Example**:
```json
{
  "status": "ok",
  "service": "Intelligent Project Knowledge Reconstruction & Handover Platform",
  "environment": "development",
  "api_version": "v1",
  "request_id": "phase21-doc-sample"
}
```

### 4.2 `GET /api/v1/health` — Versioned API Liveness
- **Purpose**: Confirms the `/api/v1` versioned router, request correlation middleware, and Pydantic serialization stack are active.
- **Status Code**: `200 OK`
- **Observed Response Example**:
```json
{
  "status": "ok",
  "service": "Intelligent Project Knowledge Reconstruction & Handover Platform",
  "environment": "development",
  "api_version": "v1",
  "request_id": "phase21-doc-sample"
}
```

### 4.3 `GET /health/ready` — Dependency-Aware Readiness
- **Purpose**: Independently evaluates:
  1. `application`: FastAPI process status (`"ok"`).
  2. `database` (**required core store**): Live PostgreSQL `SELECT 1` check via SQLAlchemy 2.x + Psycopg 3.
  3. `external_services.ollama` (**optional AI service**, non-fatal): Async `HTTPX` check against `/api/version`.
  4. `external_services.chromadb` (**optional vector store**, non-fatal): Async `HTTPX` check against `/api/v2/heartbeat`.
- **Status Code Semantics**:
  - **`200 OK` (`status: "ready"`)**: PostgreSQL, Ollama, and ChromaDB are reachable.
  - **`200 OK` (`status: "degraded"`)**: PostgreSQL is reachable, while one or both optional services (`ollama`, `chromadb`) are unavailable. An unavailable optional AI service never marks the core backend application unavailable.
  - **`503 Service Unavailable` (`status: "unavailable"`)**: PostgreSQL is unreachable (`database.status: "unavailable"`).
- **Security Guarantee**: Responses never disclose database connection strings, credentials, internal URLs, ports, or stack traces.
- **Observed Response Example (`200 OK` when all dependencies are up)**:
```json
{
  "status": "ready",
  "request_id": "phase21-doc-sample",
  "application": {
    "status": "ok"
  },
  "database": {
    "status": "ok",
    "required": true,
    "latency_ms": 6.65,
    "message": "Reachable"
  },
  "external_services": {
    "ollama": {
      "status": "ok",
      "required": false,
      "latency_ms": 26.07,
      "message": "Reachable"
    },
    "chromadb": {
      "status": "ok",
      "required": false,
      "latency_ms": 266.28,
      "message": "Reachable"
    }
  }
}
```

---

## 5. Implemented Phase 2.2 Authentication, Identity & RBAC Endpoints

### 5.1 Authentication & Self-Service Session Endpoints (`/api/v1/auth`)

| Method & Path | Auth / Permission | Purpose & Security Guarantees |
| :--- | :--- | :--- |
| `POST /api/v1/auth/register` | Public (rate-limited) | Normalises email (`.strip().lower()`), enforces strong password rules (`>= 12` chars, upper/lower/digit/special, excludes email), hashes with **Argon2id**, creates user with `standard_user` platform role, prevents duplicates (`409 ACCOUNT_ALREADY_EXISTS`), and reports `email_verification_delivery: "not_configured"` honestly. |
| `POST /api/v1/auth/login` | Public (rate-limited) | Constant-cost Argon2id verification (with dummy hash on unknown email), uniform `401 INVALID_CREDENTIALS` across invalid/disabled cases, updates `last_login_at`, creates hashed `refresh_sessions` row, sets `HttpOnly` refresh cookie, and returns short-lived JWT `access_token`. |
| `POST /api/v1/auth/refresh` | Refresh cookie + CSRF Origin/Referer + rate limit | Validates `Origin`/`Referer` against allowed origins (`403 CSRF_VALIDATION_FAILED`), hashes cookie token with SHA-256 (`FOR UPDATE`), rotates within `token_family_id`, and **revokes the entire session family + clears cookie** (`401 REFRESH_TOKEN_REUSED`) if an already-revoked/rotated token is replayed. |
| `POST /api/v1/auth/logout` | Optional refresh cookie + CSRF Origin/Referer | Validates `Origin`/`Referer`, revokes the active `token_family_id` (`revoked_reason="logout"`), and deletes the `HttpOnly` refresh cookie (`Max-Age=0`). Active access tokens carrying the revoked `sid` fail closed immediately. |
| `GET /api/v1/auth/me` | Bearer JWT + `account.profile.read` | Validates JWT signature, `exp`, `iat`, `iss`/`aud` (when configured), `type="access"`, active `User.status`, and active session family `sid`; returns profile, platform roles, and permissions without secrets. |
| `GET /api/v1/auth/sessions` | Bearer JWT + `account.sessions.read` | Lists session metadata (`id`, `token_family_id`, timestamps, revocation state, coarse non-PII `session_metadata`) strictly for `current_user.id`; never returns token values or hashes. |
| `DELETE /api/v1/auth/sessions/{session_id}` | Bearer JWT + `account.sessions.revoke` | Revokes the session family only if owned by `current_user.id` (`404 SESSION_NOT_FOUND` otherwise, preserving user isolation). |

### 5.2 Platform User Identity & RBAC Endpoints (`/api/v1/users`, `/api/v1/roles`)

| Method & Path | Permission Required | Purpose & Scope Boundary |
| :--- | :--- | :--- |
| `GET /api/v1/users` | `platform.users.read` | Paginated listing of platform accounts (`UserListResponse`, never returns `password_hash`). |
| `GET /api/v1/users/{user_id}` | `account.profile.read` (self) OR `platform.users.read` (cross-user) | Enforces per-user isolation; standard users receive `403 FORBIDDEN` for other user IDs. |
| `PATCH /api/v1/users/{user_id}/status` | `platform.users.manage` | Transitions user account status (`active`, `disabled`, `locked`); non-active transitions immediately revoke all active refresh sessions for that user. |
| `GET /api/v1/roles` | `platform.roles.read` | Returns catalog roles (`standard_user`, `platform_admin`, `org_owner`, `org_admin`, `org_member`, `project_manager`, `project_member`, `reviewer`) with explicit `scope_type` (`platform`, `organisation`, `project`). |
| `POST /api/v1/users/{user_id}/roles` | `platform.roles.manage` | Assigns a strictly `platform`-scoped role via `user_roles`; rejects `organisation` and `project` roles cleanly with `400 INVALID_ROLE_SCOPE`. |

---

## 6. Implemented Phase 2.3 Organisation, Invitation, Project & Audit Endpoints

### 6.1 Multi-Tenant Organisations, Memberships & Audit (`/api/v1/organisations`)

| Method & Path | Scope / Permission Required | Purpose & Multi-Tenant Guarantees |
| :--- | :--- | :--- |
| `POST /api/v1/organisations` | Platform: `platform.organisations.create` | Creates an organisation with normalised unique lowercase `slug` (derived from `name` if omitted) and binds creator as initial active `org_owner` (`201 Created`). |
| `GET /api/v1/organisations` | Authenticated user | Lists organisations where the caller holds active membership, supporting `status`, `search`, `limit`, and `offset`. |
| `GET /api/v1/organisations/{organisation_id}` | Active Org Member + `organisation.read` | Returns organisation metadata plus caller's resolved role & permissions (`404 ORGANISATION_NOT_FOUND` for non-members). |
| `PATCH /api/v1/organisations/{organisation_id}` | Active Org Member + `organisation.manage` | Updates active organisation `name`, `slug`, or `description` (`409 ORGANISATION_NOT_ACTIVE` when archived). |
| `POST /api/v1/organisations/{organisation_id}/archive` | Active Org Member + `organisation.manage` | Archives the organisation (`archived_at` stamped) and rejects duplicate archival (`409 ORGANISATION_ALREADY_ARCHIVED`). |
| `GET /api/v1/organisations/{organisation_id}/members` | Active Org Member + `organisation.members.read` | Lists member profiles & roles strictly within that organisation, filterable by `status` (`active` default, `removed`, `suspended`). |
| `PATCH /api/v1/organisations/{organisation_id}/members/{user_id}/role` | Active Org Member + `organisation.members.manage` | Updates an active member's `organisation`-scoped role with rank check (`org_admin` cannot promote/demote `org_owner`) and last-owner protection (`409 LAST_ORG_OWNER_FORBIDDEN`). |
| `DELETE /api/v1/organisations/{organisation_id}/members/{user_id}` | Active Org Member + `organisation.members.manage` | Marks org membership `removed` AND revokes all active `project_memberships` for that user in the same transaction; blocks removing the last active `org_owner`. |
| `GET /api/v1/organisations/{organisation_id}/audit-events` | Active Org Member + `organisation.audit.read` | Lists sanitised immutable `audit_logs` strictly scoped to the organisation (`project_id`, `event_type`, `limit`, `offset`). |

### 6.2 Hashed Single-Use Organisation Invitations

| Method & Path | Scope / Permission Required | Purpose & Token Security Rules |
| :--- | :--- | :--- |
| `POST /api/v1/organisations/{organisation_id}/invitations` | Active Org Member + `organisation.invitations.manage` | Creates a SHA-256 hashed (`token_hash`) single-use invitation matching inviter rank (`org_admin` cannot invite `org_owner`), reports `invitation_delivery: "not_configured"` honestly, and sets `development_invitation_token: null` when `APP_ENV=production`. |
| `GET /api/v1/organisations/{organisation_id}/invitations` | Active Org Member + `organisation.invitations.read` | Lists non-secret invitation metadata scoped to the organisation (`status`, `limit`, `offset`). Never returns raw tokens or `token_hash`. |
| `DELETE /api/v1/organisations/{organisation_id}/invitations/{invitation_id}` | Active Org Member + `organisation.invitations.manage` | Revokes a `pending` invitation so subsequent acceptance attempts fail cleanly (`409 INVITATION_REVOKED`). |
| `POST /api/v1/invitations/{token}/accept` | Authenticated user | Validates SHA-256 hash, case-normalised email match (`403 INVITATION_EMAIL_MISMATCH` without consuming token), expiry (`410 INVITATION_EXPIRED`), active org state, live inviter authority (`403 INVITER_NO_LONGER_AUTHORISED`), and single-use transition (`409 INVITATION_ALREADY_ACCEPTED`). |

### 6.3 Project Workspaces & Memberships (`/api/v1/organisations/{id}/projects`, `/api/v1/projects`)

Every `/api/v1/projects/{project_id}...` endpoint dynamically re-verifies active membership in the parent organisation before evaluating project visibility or permissions (`404 PROJECT_NOT_FOUND` on non-org-member or non-member `private` project).

| Method & Path | Scope / Permission Required | Purpose & Lifecycle Guarantees |
| :--- | :--- | :--- |
| `POST /api/v1/organisations/{organisation_id}/projects` | Active Org Member + `organisation.projects.create` | Creates a project with per-organisation unique `(organisation_id, slug)`, date check (`target_completion_date >= start_date`), and initial `project_manager` assignment(s) for creator/owner (`owner_id` must be active org member: `400 USER_NOT_ORG_MEMBER`). |
| `GET /api/v1/organisations/{organisation_id}/projects` | Active Org Member + `organisation.read` | Lists permitted projects in the organisation: org roles holding `project.read` (`org_owner`, `org_admin`) see all projects; `org_member` sees `organisation`-visibility projects plus `private` projects where explicitly assigned. |
| `GET /api/v1/projects/{project_id}` | Parent Org Member + (`project.read` OR `organisation` visibility) | Returns project details and resolved `effective_permissions` (`resolve_project_read_context`). |
| `PATCH /api/v1/projects/{project_id}` | Parent Org Member + `project.manage` | Updates metadata, `visibility`, validated lifecycle status transitions (`planning -> active/on_hold/archived`, `active -> on_hold/completed/archived`, etc.; `409 INVALID_PROJECT_STATUS_TRANSITION`), or `owner_id` transfer (automatically grants `project_manager`). Blocked when `archived`. |
| `POST /api/v1/projects/{project_id}/archive` | Parent Org Member + `project.manage` | Archives the project (`status="archived"`, `archived_at` populated; `409 PROJECT_ALREADY_ARCHIVED` on retry). |
| `GET /api/v1/projects/{project_id}/members` | Parent Org Member + `project.members.read` | Lists assigned project members and project-scoped roles (`status` defaults to `active`). |
| `POST /api/v1/projects/{project_id}/members` | Parent Org Member + `project.members.manage` | Assigns an existing parent-organisation member with a strictly `project`-scoped role (`project_manager`, `project_member`, `reviewer`). Non-org members fail uniformly with `400 USER_NOT_ORG_MEMBER`. |
| `PATCH /api/v1/projects/{project_id}/members/{user_id}/role` | Parent Org Member + `project.members.manage` | Changes a member's project role; blocks demoting current `project.owner_id` (`409 PROJECT_OWNER_ROLE_LOCKED`). |
| `DELETE /api/v1/projects/{project_id}/members/{user_id}` | Parent Org Member + `project.members.manage` | Revokes active project membership; blocks removing current `project.owner_id` (`409 PROJECT_OWNER_REMOVAL_FORBIDDEN`) until ownership transfers. |

---

## 7. Implemented Phase 2.4A Evidence & Document Ingestion Endpoints

Every evidence endpoint re-verifies active parent-organisation membership, project isolation (returning `404 EVIDENCE_NOT_FOUND` or `404 PROJECT_NOT_FOUND` across tenant boundaries), RBAC permissions, and fail-closed `acl_scope` (`project_members` vs `source_restricted`) checks on the backend, and commits denial events (`evidence.access_denied`, `evidence.delete_denied`, `evidence.reprocess_denied`, `evidence.source_acl_denied`) to `audit_logs` before returning `403`. Public schemas (`EvidenceSummaryResponse`, `EvidenceDetailResponse`) intentionally withhold internal `storage_object_key`, `storage_provider`, `encryption_key_id`, and host filesystem paths.

| Method & Path | Scope / Permission Required | Status & Guarantees |
| :--- | :--- | :--- |
| `POST /api/v1/projects/{project_id}/evidence/documents` | Explicit Project Member + `project.evidence.contribute` | Streams multipart upload (`file`) up to `MAX_UPLOAD_SIZE_MB`, validates filename/extension (`.pdf`/`.docx`), MIME header, magic bytes (`%PDF-`, DOCX zip entries & expansion bounds), unencrypted PDF + `MAX_DOCUMENT_PAGES`, computes SHA-256 digest, encrypts via AES-256-GCM inside `UPLOAD_STORAGE_PATH`, and queues a PostgreSQL `background_jobs` (`document_ingestion`) record (`201 Created`, `duplicate_detected: false`). Matching an active SHA-256 digest in the **same** project returns `200 OK` (`duplicate_detected: true`) without duplicating the blob (other projects remain independent). |
| `GET /api/v1/projects/{project_id}/evidence` | Parent Org Member + (`project.read` OR `organisation` visibility read) | Paginated (`limit` 1..100, `offset`) listing of non-deleted evidence summaries filterable by `processing_status`, `source_type`, and `category` (`400 INVALID_FILTER` on unsupported filter or `deleted`). |
| `GET /api/v1/evidence/{evidence_id}` | Parent Org Member + `project.read` (+ fail-closed `acl_scope` hook) | Returns full provenance (`source_type`, `source_provider`, `source_external_id`, `content_hash`, timestamps), separated `extracted_content` (`extracted_text`, `char_count`, `word_count`, `extraction_warnings`, ordered `pages`), and `jobs` telemetry. |
| `DELETE /api/v1/evidence/{evidence_id}` | Parent Org Member + (`project.manage` OR uploading owner with `project.evidence.contribute`) | Logically deletes the item (`processing_status = "deleted"`, `deleted_at` stamped), cancels queued/running jobs, deletes the encrypted object from private storage, emits `evidence.deleted`, and returns `204 No Content`. |
| `POST /api/v1/evidence/{evidence_id}/reprocess` | Parent Org Member + `project.read` + (`project.manage` OR explicit member with `project.evidence.contribute`) | Enqueues a clean `document_ingestion` retry job (`202 Accepted`) using the preserved encrypted upload when `processing_status` is `failed` or `partially_extracted` and no job is active (`409 INVALID_EVIDENCE_STATE` / `JOB_ALREADY_ACTIVE`, `422 STORAGE_OBJECT_MISSING`). |

### Validation & Rejection Status Codes (Phase 2.4A)
- **`413 Payload Too Large`**: `FILE_TOO_LARGE` when streaming upload bytes exceed `MAX_UPLOAD_SIZE_MB`.
- **`415 Unsupported Media Type`**: `UNSUPPORTED_FILE_EXTENSION`, `UNSUPPORTED_MEDIA_TYPE`, or `INVALID_FILE_SIGNATURE` on MIME/extension/magic-byte spoofing.
- **`422 Unprocessable Entity`**: `ENCRYPTED_DOCUMENT_UNSUPPORTED`, `MALFORMED_PDF`, `PDF_PAGE_LIMIT_EXCEEDED`, `MALFORMED_DOCX`, `ARCHIVE_EXPANSION_LIMIT_EXCEEDED`, or `STORAGE_OBJECT_MISSING`.

---

## 8. Implemented Phase 2.4B Delegated Source Integration Endpoints

All Phase 2.4B endpoints live in `app/api/routes/integrations.py` under `/api/v1`, enforce active platform Bearer authentication and tenant/project isolation, keep external tokens encrypted on the backend (`TOKEN_ENCRYPTION_KEY`), and return strictly non-secret metadata DTOs. Slack requests reject cleanly with `409 SLACK_INTEGRATION_DISABLED` (`SLACK_ENABLED=false`).

### 8.1 Organisation Source Connections & Delegated OAuth (`/api/v1/.../integrations`)

| Method & Path | Scope / Permission Required | Purpose & Security Guarantees |
| :--- | :--- | :--- |
| `GET /api/v1/organisations/{organisation_id}/integrations/connections` | Active Org Member + `organisation.read` | Lists organisation-scoped connections (`provider` optional: `github` \| `jira`) with **only the caller's own** `caller_authorisation` summary (never other users' identities or tokens). |
| `POST /api/v1/organisations/{organisation_id}/integrations/{provider}/oauth/start` | Active Org Member + `organisation.read` *(plus `organisation.manage`, `organisation.projects.create`, or org project contributor role when creating a new connection)* | Generates SHA-256 single-use `oauth_states`, PKCE `S256` challenge (AES-256-GCM encrypted `code_verifier`), allowlist-validated `redirect_after`, and provider consent URL (`Cache-Control: no-store`). |
| `GET /api/v1/integrations/{provider}/callback` | Authenticated User (`get_current_principal`) + Active Target Org Member | Validates `oauth_state.user_id == principal.user.id` (`403 OAUTH_STATE_USER_MISMATCH`), provider match, expiry (`410 OAUTH_STATE_EXPIRED`), and single-use consumption (`409 OAUTH_STATE_REPLAYED`); exchanges PKCE code and encrypts tokens (`Cache-Control: no-store`). |
| `POST /api/v1/integrations/connections/{connection_id}/disconnect` | Active Org Member + (`organisation.manage` \| `organisation.projects.create` \| `created_by_user_id`) | Marks `SourceConnection` `disconnected`, revokes all active delegated `UserSourceAuthorisation` rows, and disables linked mappings. |
| `POST /api/v1/integrations/connections/{connection_id}/authorisation/revoke` | Active Org Member (Self-Service) | Revokes strictly the caller's own active delegated `UserSourceAuthorisation` (`REVOKED_BY_USER`) cleanly (`404 SOURCE_AUTHORISATION_NOT_FOUND` if none active). |

### 8.2 Delegated External Source Discovery (`/api/v1/integrations/connections/{connection_id}`)

Every discovery call executes exclusively with the caller's own active delegated OAuth token (`403 SOURCE_AUTHORISATION_REQUIRED` or `409 SOURCE_AUTHORISATION_REVOKED` if missing/revoked; automatic single-use `401` refresh rotation when applicable):

| Method & Path | Scope / Permission Required | Purpose |
| :--- | :--- | :--- |
| `GET /api/v1/integrations/connections/{connection_id}/github/repositories` | Active Org Member + Caller Active GitHub Auth | Lists paginated repositories (`page`, `per_page`) accessible to the caller's delegated GitHub token. |
| `GET /api/v1/integrations/connections/{connection_id}/jira/sites` | Active Org Member + Caller Active Jira Auth | Lists Atlassian Cloud sites (`cloud_id`, URLs, scopes) authorised via `/oauth/token/accessible-resources`. |
| `GET /api/v1/integrations/connections/{connection_id}/jira/projects` | Active Org Member + Caller Active Jira Auth | Lists paginated Jira projects (`cloud_id`, `start_at`, `max_results`, `query`) inside an authorised Cloud site (`403 JIRA_SITE_NOT_AUTHORISED` if `cloud_id` not accessible). |

### 8.3 Project Source Mappings, ACL Verification & Sync Execution

| Method & Path | Scope / Permission Required | Status & Guarantees |
| :--- | :--- | :--- |
| `GET /api/v1/projects/{project_id}/integrations/mappings` | Parent Org Member + `project.read` | Lists configured GitHub/Jira mappings and attached `SourceAccessPolicy` summaries (`include_disabled` filter). |
| `POST /api/v1/projects/{project_id}/integrations/github/mappings` | Parent Org Member + (`project.manage` \| explicit member with `project.evidence.contribute`) + Caller Active GitHub Auth | Verifies caller repository access live (`403 SOURCE_RESOURCE_INACCESSIBLE` on failure), classifies `SourceAccessPolicy` (`project_members_verified` for public unless `restrict_to_verified_users=true`, else `verified_source_acl`), prevents duplicate active mapping (`409 SOURCE_MAPPING_ALREADY_EXISTS`), returns `201 Created`. |
| `POST /api/v1/projects/{project_id}/integrations/jira/mappings` | Parent Org Member + (`project.manage` \| explicit member with `project.evidence.contribute`) + Caller Active Jira Auth | Validates safe optional `jql_filter` (rejecting `;`, newlines, `ORDER BY` with `400 INVALID_JQL_FILTER`), verifies Cloud site & project live, creates fail-closed `verified_source_acl` policy, returns `201 Created`. |
| `DELETE /api/v1/projects/{project_id}/integrations/mappings/{mapping_id}` | Parent Org Member + (`project.manage` \| explicit member with `project.evidence.contribute`) | Transitions mapping to `disabled` cleanly while preserving historical synced `evidence_items` (`200 OK`). |
| `POST /api/v1/projects/{project_id}/integrations/mappings/{mapping_id}/verify-access` | Parent Org Member + `project.read` + Caller Active Provider Auth | Re-verifies caller's delegated access against GitHub repo or Jira site + project + per-security-level Jira sub-policies (`{cloud_id}:{project_key}:security:{sec_id}`), updating `SourceAccessPolicy.allowed_user_ids` and logging audit result (`200 OK`). |
| `POST /api/v1/projects/{project_id}/integrations/mappings/{mapping_id}/sync` | Parent Org Member + (`project.manage` \| explicit member with `project.evidence.contribute`) + Caller Active Provider Auth | Enqueues PostgreSQL `background_jobs` (`job_type="source_sync"`) + `source_sync_runs` (`initial` \| `incremental` \| `manual`) executed by `SourceSyncWorkerService` (`202 Accepted`; `409 SYNC_ALREADY_ACTIVE` if queued/running). |
| `GET /api/v1/projects/{project_id}/integrations/sync-runs` | Parent Org Member + `project.read` | Lists paginated (`limit`, `offset`, optional `mapping_id`) sync history ordered newest-first inside project scope. |
| `GET /api/v1/integrations/sync-runs/{sync_run_id}` | Parent Org Member + `project.read` | Returns counters (`items_discovered`, `items_created`, `items_updated`, `items_unchanged`, `items_inaccessible`, `items_failed`), warnings, and timing for one sync run. |
| `POST /api/v1/integrations/sync-runs/{sync_run_id}/cancel` | Parent Org Member + (`project.manage` \| `project.evidence.contribute`) | Cancels a `queued` or `running` sync run and linked `background_jobs` record (`200 OK`; `409 SYNC_RUN_ALREADY_FINISHED` if completed). |

### Integration Rejection & Governance Status Codes (Phase 2.4B)
- **`400 Bad Request`**: `UNSUPPORTED_PROVIDER`, `PROVIDER_MISMATCH`, `INVALID_REDIRECT_URL`, `REDIRECT_URL_NOT_ALLOWLISTED`, `INVALID_JQL_FILTER`, `OAUTH_STATE_MISSING`, `OAUTH_STATE_INVALID`, `OAUTH_STATE_MISMATCH`, `OAUTH_CODE_MISSING`.
- **`403 Forbidden`**: `OAUTH_STATE_USER_MISMATCH`, `OAUTH_ACCESS_DENIED`, `SOURCE_AUTHORISATION_REQUIRED`, `JIRA_SITE_NOT_AUTHORISED`, `SOURCE_RESOURCE_INACCESSIBLE`, `SOURCE_ACCESS_DENIED`.
- **`409 Conflict`**: `SLACK_INTEGRATION_DISABLED`, `OAUTH_STATE_REPLAYED`, `SOURCE_AUTHORISATION_REVOKED`, `CONNECTION_DISCONNECTED`, `CONNECTION_ALREADY_DISCONNECTED`, `SOURCE_MAPPING_ALREADY_EXISTS`, `MAPPING_NOT_ACTIVE`, `SYNC_ALREADY_ACTIVE`, `SYNC_RUN_ALREADY_FINISHED`.
- **`410 Gone`**: `OAUTH_STATE_EXPIRED`.
- **`503 Service Unavailable`**: `INTEGRATION_DISABLED` (when `GITHUB_ENABLED=false` or `JIRA_ENABLED=false`).

---

## 9. Implemented Phase 2.5 Retrieval, Chunk Inspection & Indexing Endpoints

All Phase 2.5 endpoints live in `app/api/routes/retrieval.py` under `/api/v1/projects/{project_id}`, re-verify active parent-organisation membership, enforce project RBAC and two-phase fail-closed `SourceAccessPolicyService` permissions (`project_members` vs `source_restricted`), withhold all internal encryption/storage paths, and exclude `is_synthetic=true` evidence by default unless `filters.include_synthetic=true` is explicitly requested.

| Method & Path | Scope / Permission Required | Purpose & Behavioural Guarantees |
| :--- | :--- | :--- |
| `POST /api/v1/projects/{project_id}/search` | Parent Org Member + `project.read` + Fail-Closed Source ACL Filtering | Executes `mode`: `"hybrid"` (default, weighted RRF fusion of PG FTS + ChromaDB `nomic-embed-text`), `"keyword"` (PostgreSQL `TSVECTOR` + `GIN`), or `"semantic"` (ChromaDB v2 cosine similarity). Supports filters (`source_types`, `categories`, `chunk_types`, `author`, `evidence_ids`, UTC `date_from`/`date_to`, `include_synthetic`) and `top_k` (`1..RETRIEVAL_MAX_TOP_K`, rejecting excess with `400 TOP_K_EXCEEDED`). If ChromaDB or Ollama embeddings are unavailable, `"hybrid"` degrades cleanly to `mode_executed: "keyword"` (`degraded: true`, structured `degraded_reason` + warning), whereas `"semantic"` fails with `503 Service Unavailable`. Emits `evidence.search_executed` audit log (`200 OK`). |
| `GET /api/v1/projects/{project_id}/chunks/{chunk_id}` | Parent Org Member + `project.read` + `SourceAccessPolicyService.enforce_evidence_access` | Returns canonical `chunk_text`, byte offsets (`char_start`, `char_end`), page/section location, indexing status, and full `SearchCitation` after verifying project isolation (`404 CHUNK_NOT_FOUND` across tenants) and source ACL (`403 SOURCE_ACCESS_DENIED` + `evidence.source_acl_denied` audit log). |
| `GET /api/v1/projects/{project_id}/indexing/status` | Parent Org Member + `project.read` | Returns canonical PostgreSQL counts (`total_eligible_evidence`, `status_counts`, `total_chunks`, `indexed_chunks`, `pending_vector_chunks`, `failed_chunks`, `active_indexing_jobs`, `fts_ready_items`, `vector_synced_items`, observed embedding models & index versions, excluding synthetic items by default). |
| `POST /api/v1/projects/{project_id}/indexing/reindex` | Parent Org Member + (`project.manage` \| explicit member with `project.evidence.contribute`) | Enqueues asynchronous `evidence_reindexing` job in `background_jobs` (`202 Accepted`; idempotent `already_running: true` if one is already active). Supports `target`: `"full"` (re-chunk + PG FTS + embeddings + Chroma), `"fts_only"` (rebuild PG chunks & `TSVECTOR`), or `"vectors_only"` (recover missing/stale Chroma vectors from PG chunks), plus optional `evidence_ids` targeting and `force_rechunk`. Emits `evidence.reindex_queued` (`evidence.reindex_denied` -> `403` if unauthorised; `409 PROJECT_ARCHIVED` / `ORGANISATION_NOT_ACTIVE`). |
| `GET /api/v1/projects/{project_id}/indexing/health` | Parent Org Member + `project.read` | Reports `postgresql_fts_ready`, `chroma_reachable`, resolved `chroma_collection_name`, `chroma_collection_exists`, `chroma_vector_count`, `chroma_space`, `expected_embedding_model`, `expected_index_version`, `expected_dimensions`, `collection_compatible` / `compatibility_error`, and nested `indexing_summary`. |
| `GET /api/v1/projects/{project_id}/indexing/jobs/{job_id}` | Parent Org Member + `project.read` | Returns `BackgroundJobResponse` status, retry attempts, and sanitised error details for project-scoped indexing/cleanup/reindex jobs (`404 JOB_NOT_FOUND` across projects or non-indexing job types). |

---

## 10. Implemented Phase 2.6 Knowledge Reconstruction Endpoints

All Phase 2.6 endpoints live in `app/api/routes/knowledge.py` under `/api/v1/projects/{project_id}`, enforce active parent-organisation membership, project RBAC, live fail-closed `SourceAccessPolicyService` checks across trigger, worker, and read paths, strict epistemic caps (worker outputs are restricted to `"extracted"` or `"ai_interpreted"`, never `"human_verified"`), `NO EVIDENCE -> NO CLAIM` excerpt attribution verification, and `include_synthetic=false` by default.

| Method & Path | Scope / Permission Required | Purpose & Behavioural Guarantees |
| :--- | :--- | :--- |
| `POST /api/v1/projects/{project_id}/evidence/{evidence_id}/extract` | Explicit Project Member + `project.evidence.contribute` (or `project.manage`) + Fail-Closed Source ACL | Validates single evidence item is non-deleted, chunked (`evidence_chunks`), and accessible to caller (`403 SOURCE_ACCESS_DENIED` otherwise). Enqueues `KnowledgeExtractionRun` (`scope_type="evidence"`) and `background_jobs` (`knowledge_reconstruction`) (`202 Accepted`; returns existing run with `already_active=true` if already queued/running unless superseded after completion with `force_rerun=true`). Optional body `categories` (subset of `decisions_rationale`, `work_items`, `responsibilities_ownership`, `technical_architecture`, `bugs_blockers_risks`, `dependencies`), `force_rerun`. |
| `POST /api/v1/projects/{project_id}/knowledge/extract` | Explicit Project Member + `project.evidence.contribute` (or `project.manage`) + Fail-Closed Source ACL | Queues project-wide or `evidence_ids`-targeted asynchronous extraction (`scope_type="project"`, `202 Accepted`). Excludes restricted items caller cannot access (`skipped_inaccessible_count`), excludes synthetic items unless `include_synthetic=true`, supports `categories` and `force_rerun`, and enforces single active project run idempotency (`already_active=true`). |
| `GET /api/v1/projects/{project_id}/knowledge/status` | Parent Org Member + `project.read` + Live Source ACL | Returns `ProjectKnowledgeStatusResponse`: `total_accessible_items`, `stale_items_count`, `counts_by_category`, `counts_by_epistemic_status`, `counts_by_support_classification`, `active_runs_count`, and `latest_run` (`include_synthetic` defaults to `false`). |
| `GET /api/v1/projects/{project_id}/knowledge/runs` | Parent Org Member + `project.read` | Lists paginated `KnowledgeExtractionRunResponse` history (`status` filter, `limit` 1..100, `offset`) with model/prompt versions, token telemetry, grounded vs rejected claim counts, and nested `job` state. |
| `GET /api/v1/projects/{project_id}/knowledge/runs/{run_id}` | Parent Org Member + `project.read` | Returns detailed status, counters, warnings, sanitised errors, and job link for one extraction run (`404 EXTRACTION_RUN_NOT_FOUND` across projects). |
| `POST /api/v1/projects/{project_id}/knowledge/runs/{run_id}/retry` | Explicit Project Member + `project.evidence.contribute` (or `project.manage`) | Enqueues a new clean retry run from a `failed`, `partially_completed`, or `cancelled` extraction run (`202 Accepted`; `409 INVALID_EXTRACTION_RUN_STATE` otherwise). |
| `POST /api/v1/projects/{project_id}/knowledge/runs/{run_id}/cancel` | Explicit Project Member + `project.evidence.contribute` (or `project.manage`) | Cancels a `queued` extraction run and linked PostgreSQL `background_jobs` record cleanly (`200 OK`; `409 INVALID_EXTRACTION_RUN_STATE` if already running/finished). |
| `GET /api/v1/projects/{project_id}/knowledge/items` | Parent Org Member + `project.read` + Live Source ACL | Paginated (`limit` 1..100, `offset`) list of accessible `KnowledgeItemSummaryResponse` items backed by at least one active, ACL-permitted `evidence_item`. Filterable by `category`, `epistemic_status`, `review_status`, `support_classification`, `normalised_status`, `person` (unmerged owner substring), `source_provider`, `evidence_id`, `date_from`/`date_to` (returns `400 INVALID_FILTER` if `date_from > date_to`), `include_stale`, `stale_only`, and `include_synthetic` (default `false`). |
| `GET /api/v1/projects/{project_id}/knowledge/items/{item_id}` | Parent Org Member + `project.read` + Live Source ACL | Returns `KnowledgeItemDetailResponse` containing full `structured_payload`, `source_attribution`, `confidence_metadata`, `uncertainty_reason`, `is_stale`/`stale_reason`, and **only caller-accessible** active `evidence_links` (each carrying `supporting_excerpt`, `excerpt_verified`, `excerpt_match_mode`, `source_location`, `evidence_chunk_id`). Fails closed with `403 SOURCE_ACCESS_DENIED` + `knowledge.source_acl_denied` audit log if caller lacks access to every supporting evidence item. |

---

## 11. Refresh Cookie & Frontend Browser Integration Contract

The frontend (Next.js App Router) must follow this browser authentication contract when auth UI screens are built in later phases:

1. **HttpOnly Refresh Cookie (`ipkrh_refresh_token`)**:
   - Issued strictly via `Set-Cookie` on `POST /api/v1/auth/login` and `POST /api/v1/auth/refresh` with:
     - `HttpOnly=true` (unreadable via `document.cookie` / browser JS)
     - `Path=/api/v1/auth` (never transmitted on non-auth API calls)
     - `SameSite=lax` *(configurable via `COOKIE_SAMESITE`)*
     - `Secure=true` in HTTPS staging/production (`COOKIE_SECURE=true`), `false` only for local HTTP `localhost` dev.
2. **Short-Lived JWT Access Token (Memory Only)**:
   - Returned in the JSON response body (`access_token`, `expires_in`, `token_type="bearer"`).
   - Held **only in client memory** (React state/context) or server-side BFF memory—**never** persisted to `localStorage`, `sessionStorage`, or non-HttpOnly cookies.
   - Attached as `Authorization: Bearer <access_token>` on authenticated API requests.
3. **CORS Credentials & CSRF Origin Interaction**:
   - FastAPI enables `allow_credentials=True` strictly for explicit `CORS_ALLOWED_ORIGINS` (default `http://localhost:3000`; wildcard `*` is rejected).
   - Frontend must include `credentials: "include"` on `POST /api/v1/auth/login`, `/refresh`, and `/logout`.
   - Browsers automatically include the `Origin` header on these `POST` calls; `POST /api/v1/auth/refresh` and `POST /api/v1/auth/logout` reject missing, `"null"`, or untrusted `Origin`/`Referer` headers with `403 CSRF_VALIDATION_FAILED`.
   - On page load or when a protected call fails with `401 ACCESS_TOKEN_EXPIRED`, the client calls `POST /api/v1/auth/refresh` (with `credentials: "include"`) once to obtain a fresh in-memory `access_token` while rotating the `HttpOnly` cookie.
   - Auth endpoints may return `429 RATE_LIMIT_EXCEEDED` with `Retry-After` when configurable attempt thresholds are exceeded.
