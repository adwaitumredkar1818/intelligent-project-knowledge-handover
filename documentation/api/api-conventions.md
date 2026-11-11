# API Conventions & Infrastructure Endpoints

> **Current Stage (Phase 2.2 — Platform Authentication, Identity & RBAC):** This document describes all **actually implemented** HTTP conventions, error envelopes, security headers, health/readiness probes, and Phase 2.2 authentication/identity/RBAC endpoints. Organisations, projects, evidence uploads, external source integrations, verification, handover, and assistant endpoints belong to Phase 2.3+ and are not yet implemented.

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
| `GET /api/v1/roles` | `platform.roles.read` | Returns catalog roles (`standard_user`, `platform_admin`, `org_owner`, `org_admin`, `project_manager`, `project_member`, `reviewer`) with explicit `scope_type` (`platform`, `organisation`, `project`). |
| `POST /api/v1/users/{user_id}/roles` | `platform.roles.manage` | Assigns a strictly `platform`-scoped role via `user_roles`; rejects `organisation` and `project` roles cleanly with `400 INVALID_ROLE_SCOPE`. |

---

## 6. Refresh Cookie & Frontend Browser Integration Contract

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
