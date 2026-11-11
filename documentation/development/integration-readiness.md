# Integration Readiness & Permission Prerequisites

This document specifies the required permissions, OAuth 2.0 setup procedures, security boundaries, and pre-enablement gates for external source connectors before application integration development begins in Phase 4.

> [!IMPORTANT]
> **Phase 1.3 Scope Boundary**: No live OAuth applications, webhooks, API connectors, or credentials are created in this phase. All integrations remain disabled by default (`GITHUB_ENABLED=false`, `JIRA_ENABLED=false`, `SLACK_ENABLED=false` in [`.env.example`](../../.env.example)).

---

## 1. Confirmed Governance & Security Baseline

All source integrations must satisfy the architectural decisions in [`security-architecture.md`](../architecture/security-architecture.md) and [`development-roadmap.md`](./development-roadmap.md):

1. **Strict Separation from Platform Authentication**:
   - Platform login uses FastAPI-managed credentials, short-lived JWT access tokens, and `HttpOnly` refresh cookies.
   - GitHub, Jira, and optional Slack OAuth 2.0 tokens are used **solely** for delegated source ingestion and permission checks. They never authenticate a user to the platform and never replace platform RBAC.
2. **Delegated Per-User Authorisation & ACL Preservation**:
   - Prefer delegated per-user OAuth 2.0 authorisation (`user_source_authorisations`) over shared tenant-wide service tokens wherever supported.
   - Connecting one project member's account **never** implies every project member can read those repositories, Jira projects, or Slack channels.
   - Preserve external user identities (`external_user_id`), granted OAuth scopes, and source-level ACL metadata (`source_access_policies`) in PostgreSQL and enforce permission filtering **before** evidence enters ChromaDB/FTS retrieval or LLM prompts.
3. **Backend-Only Secrets & Encrypted Storage**:
   - Store client secrets, signing secrets, and delegated OAuth access/refresh tokens exclusively on the backend. Never expose them in browser JavaScript, API responses, logs, or `NEXT_PUBLIC_*` environment variables.
   - Encrypt stored OAuth tokens at rest in PostgreSQL using `TOKEN_ENCRYPTION_KEY`.
4. **Mandatory Provenance Retention**:
   - Every ingested external item must retain: source platform, original source identifier, source URL (where available), author or owner (where available), original source timestamp, extraction timestamp, and content hash or version/ETag metadata.
5. **Immutable Audit Trail**:
   - Log all OAuth connection attempts, completions, token refreshes/revocations, connector sync runs, and `403` source-permission denials in PostgreSQL `audit_logs`.

---

## 2. GitHub OAuth & API Readiness

**Status**: Initial priority source integration (`GITHUB_ENABLED=false` until enabled in Phase 4).

### 2.1 Environment Variables (Canonical Reference)

Defined in [`.env.example`](../../.env.example) and [`environment-setup.md`](./environment-setup.md):

| Variable | Visibility | Default / Placeholder | Purpose |
| :--- | :--- | :--- | :--- |
| `GITHUB_ENABLED` | Backend / Worker | `false` | Feature gate for GitHub connector |
| `GITHUB_API_BASE_URL` | Backend / Worker | `https://api.github.com` | GitHub REST API base URL (supports GitHub Enterprise override) |
| `GITHUB_CLIENT_ID` | Backend only | *(empty)* | GitHub App or OAuth App Client ID |
| `GITHUB_CLIENT_SECRET` | Backend secret | *(empty)* | GitHub App or OAuth App Client Secret |
| `GITHUB_REDIRECT_URI` | Backend only | `http://localhost:8000/api/v1/integrations/github/callback` | Backend-handled delegated OAuth callback URI |

### 2.2 Required Permissions & App Choice

- **Confirmed Design Decision**: Read-only delegated access with no repository write/admin scopes.
- **Proposed Implementation Detail (Preferred App Model)**:
  - Prefer a **GitHub App with user-to-server OAuth tokens** over a classic OAuth App because classic OAuth's `repo` scope grants read **and write** access to private repositories, whereas a GitHub App permits granular **read-only** repository permissions:
    - **Account / Identity**: User email addresses (Read-only) to map `external_user_id` cleanly.
    - **Repository Permissions (Read-only)**: `Metadata` (mandatory baseline), `Contents` (READMEs, architecture docs, ADRs), `Issues`, and `Pull requests` (PR descriptions, review threads, merge commits).
  - **Fallback (Classic OAuth App — Public Repos or Restricted Org Policy)**:
    - Use `read:user`, `user:email`, and `public_repo` when only public repositories are needed. Only request `repo` if private repositories cannot use a GitHub App and explicit security sign-off is recorded.

### 2.3 Setup & Operational Prerequisites

1. Register the GitHub App / OAuth App under the target organisation's developer settings (or a dedicated test organisation for sandbox verification).
2. Configure the Authorization Callback URL to match `GITHUB_REDIRECT_URI` (`http://localhost:8000/api/v1/integrations/github/callback` locally; HTTPS origin in deployment).
3. Enforce cryptographic `state` parameter verification (and PKCE where supported) stored short-lived server-side during the OAuth handshake to prevent CSRF and account-linking attacks.
4. **Organisation Approval**: If accessing private organisation repositories, obtain GitHub Organisation Owner / Admin approval so the OAuth/GitHub App is authorised against org SAML/IP rules.
5. **Rate Limits & Conditional Requests**: Use `X-RateLimit-Remaining` / `X-RateLimit-Reset` backoff headers and store HTTP `ETag` / `If-None-Match` headers on incremental syncs to minimise quota consumption.

---

## 3. Jira API (Atlassian OAuth 2.0 3LO) Readiness

**Status**: Initial priority source integration (`JIRA_ENABLED=false` until enabled in Phase 4).

### 3.1 Environment Variables (Canonical Reference)

| Variable | Visibility | Default / Placeholder | Purpose |
| :--- | :--- | :--- | :--- |
| `JIRA_ENABLED` | Backend / Worker | `false` | Feature gate for Jira connector |
| `JIRA_AUTH_BASE_URL` | Backend only | `https://auth.atlassian.com` | Atlassian OAuth 2.0 (3LO) authorisation & token exchange base URL |
| `JIRA_API_BASE_URL` | Backend / Worker | `https://api.atlassian.com` | Atlassian Cloud REST API gateway base URL |
| `JIRA_CLIENT_ID` | Backend only | *(empty)* | Atlassian Developer Console App Client ID |
| `JIRA_CLIENT_SECRET` | Backend secret | *(empty)* | Atlassian Developer Console App Client Secret |
| `JIRA_REDIRECT_URI` | Backend only | `http://localhost:8000/api/v1/integrations/jira/callback` | Backend-handled delegated OAuth 2.0 (3LO) callback URI |

### 3.2 Required Permissions & Scopes

- **Confirmed Design Decision**: Read-only delegated access using Atlassian OAuth 2.0 (3LO), respecting Jira project/issue visibility per user.
- **Proposed Implementation Detail (Minimum Read-Only Scopes)**:
  - **Classic Jira Platform REST API Scopes** (simplest Cloud 3LO read-only bundle):
    - `read:jira-work` — read projects, epics, stories, tasks, bugs, comments, attachments metadata, transitions, and linked issues.
    - `read:jira-user` — resolve assignee/reporter identities (`accountId`, display name) for responsibility tracking.
    - `offline_access` — obtain rotating refresh tokens for authorised background sync jobs.
  - **Granular Scopes Alternative** (if the Atlassian app opts into granular permissions):
    - `read:issue:jira`, `read:issue-meta:jira`, `read:issue.changelog:jira`, `read:comment:jira`, `read:project:jira`, `read:user:jira`, plus `offline_access`.
  - Explicitly **exclude** `write:jira-work` and admin/delete scopes—the platform reconstructs knowledge read-only from Jira and never mutates Jira tickets.

### 3.3 Setup & Operational Prerequisites

1. Create an OAuth 2.0 (3LO) app in the Atlassian Developer Console and enable **Jira API** permissions with only the read scopes above.
2. Register `JIRA_REDIRECT_URI` (`http://localhost:8000/api/v1/integrations/jira/callback`) as the allowed callback URL.
3. Implement **Cloud ID Tenant Discovery**: After token exchange at `${JIRA_AUTH_BASE_URL}/oauth/token`, query `${JIRA_API_BASE_URL}/oauth/token/accessible-resources` to resolve authorised Jira Cloud `id`s and scope REST v3 requests to `${JIRA_API_BASE_URL}/ex/jira/{cloud_id}/rest/api/3/...`.
4. **Refresh Token Rotation**: Atlassian 3LO refresh tokens are single-use/rotating; worker/backend token refresh must execute atomically inside a PostgreSQL transaction before persisting the rotated encrypted refresh token.
5. **Jira Site Admin / Security Controls**: Confirm whether target Jira Cloud sites enforce Atlassian Guard / IP allowlists or app-access restrictions before staging rollout.

---

## 4. Optional Slack OAuth & API Readiness (Gated MVP)

**Status**: Strictly optional MVP integration (`SLACK_ENABLED=false` by default). Must **not** be implemented or enabled until all three governance gates below are signed off.

### 4.1 Environment Variables (Canonical Reference)

| Variable | Visibility | Default / Placeholder | Purpose |
| :--- | :--- | :--- | :--- |
| `SLACK_ENABLED` | Backend / Worker | `false` | Optional MVP gate; keep `false` until all 3 gates pass |
| `SLACK_API_BASE_URL` | Backend / Worker | `https://slack.com/api` | Slack Web API base URL |
| `SLACK_CLIENT_ID` | Backend only | *(empty)* | Slack App Client ID |
| `SLACK_CLIENT_SECRET` | Backend secret | *(empty)* | Slack App Client Secret |
| `SLACK_SIGNING_SECRET` | Backend secret | *(empty)* | HMAC-SHA256 request verification secret (if event callbacks are added later) |
| `SLACK_REDIRECT_URI` | Backend only | `http://localhost:8000/api/v1/integrations/slack/callback` | Backend-handled Slack OAuth v2 callback URI |

### 4.2 Mandatory Three-Part Enablement Gate

Do not flip `SLACK_ENABLED=true` or ingest Slack conversations until written confirmation exists for:

1. **Workspace Authorisation**: Explicit approval from the Slack Workspace Owner / Org Admin (including Slack App Directory/workspace installation policies).
2. **API Scope Review**: Formal sign-off on exact read-only OAuth v2 scopes:
   - Candidate read-only scopes: `channels:read`, `channels:history` (and `groups:read`, `groups:history` **only** if explicitly authorised private channels are opted in per channel membership ACL), `users:read`, `team:read`.
   - **Prohibited by default**: Direct messages (`im:read`, `im:history`, `mpim:read`, `mpim:history`), file/user write scopes (`chat:write`, `files:write`), and workspace admin scopes unless a formal privacy amendment specifies otherwise.
3. **Data-Retention & Privacy Confirmation**:
   - Defined channel allowlist (ingest only designated project channels, never blanket workspace scraping).
   - Retention period, redaction policy for personal data/credentials accidentally posted in threads, and deletion workflow guaranteeing synced PostgreSQL evidence and corresponding ChromaDB vectors can be purged on retention expiry or channel opt-out.

### 4.3 Technical Prerequisites (Once Gated Requirements Are Met)

- Use Slack OAuth v2 (`oauth.v2.access`) with cryptographic `state` validation and delegated user tokens (`user_scope`) or explicitly ACL-mapped channel memberships stored in `source_access_policies`.
- Respect Slack Web API tier rate limits (`HTTP 429` with `Retry-After` backoff; particularly Tier 2/3 limits on `conversations.history` and `conversations.replies`).
- Verify `X-Slack-Signature` using `SLACK_SIGNING_SECRET` with constant-time comparison if Slack Events API webhooks are ever introduced later.

---

## 5. Pre-Implementation Verification Checklist (Before Phase 4)

- [ ] Platform authentication (login, JWT access tokens, `HttpOnly` refresh cookies, RBAC) is operational before enabling any source connector callback route.
- [ ] `TOKEN_ENCRYPTION_KEY` encryption/decryption helper and `audit_logs` writer are tested before persisting any third-party OAuth token.
- [ ] Per-user ACL filtering (`source_access_policies`) is verified in unit/integration tests before external evidence is chunked into ChromaDB.
- [ ] Synthetic test fixtures (`is_synthetic = true`) remain completely isolated from real OAuth connection states—never present mock repos, Jira tickets, or Slack messages as connected organisational data.
