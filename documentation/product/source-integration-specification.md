# The Handover — Source Integration Specification

## 1. Integration Scope & Architecture

The Handover connects to external source repositories and issue trackers to ingest project records into canonical PostgreSQL evidence items.

```text
┌───────────────────────┐         ┌───────────────────────┐
│     GitHub API        │         │    Atlassian Jira     │
│ (Repos, PRs, Commits) │         │ (Issues, Changelogs)  │
└───────────┬───────────┘         └───────────┬───────────┘
            │ OAuth 2.0                       │ OAuth 2.0 (3LO)
            ▼                                 ▼
┌─────────────────────────────────────────────────────────┐
│               Source Connector Service                  │
│  - Encrypted Token Storage                              │
│  - Resource Discovery (Accessible Repos/Sites)          │
│  - Explicit Project-to-Resource Mapping                 │
│  - Idempotent Sync Workers with Checkpoints             │
│  - Source ACL Policy Preservation                       │
└───────────────────────────┬─────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│           Canonical PostgreSQL Evidence Store           │
│  `source_connections`, `project_source_mappings`,       │
│  `evidence_items`, `evidence_contents`                  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. GitHub Integration

### 2.1 OAuth 2.0 Authorization Flow
- Scopes requested: `repo` (for private and public repository access), `read:user`, `user:email`.
- Authorization URL: `https://github.com/login/oauth/authorize`.
- Token URL: `https://github.com/login/oauth/access_token`.
- User identity endpoint: `https://api.github.com/user`.

### 2.2 Resource Discovery & Mapping
- **Discovery Endpoint**: `GET /user/repos?per_page=100&sort=updated`.
- Returns list of repositories accessible to the connected user (full name, private flag, description, default branch, updated timestamp).
- **Mapping**: User explicitly selects one or more repositories to map to a project workspace via `project_source_mappings`.

### 2.3 Evidence Ingestion Pipeline
When a sync is triggered (initial, manual, or scheduled):
1. **Repository & README**: Ingests repo metadata, languages, and root `README.md` as primary evidence.
2. **Pull Requests**:
   - Ingests closed and open PRs (`/repos/{owner}/{repo}/pulls?state=all`).
   - Captures PR number, title, body, author, merge commit SHA, merged status, timestamps, and reviewers.
3. **Commits**:
   - Ingests recent commit history (`/repos/{owner}/{repo}/commits`).
   - Captures commit SHA, message, author, committer, and committed date.
4. **Issues**:
   - Ingests issues and issue comments (`/repos/{owner}/{repo}/issues`).
   - Captures issue key, title, body, labels, state, and discussion history.
5. **Idempotency**: All records keyed by `provider='github'` and `external_source_id='pr:123'` or `'commit:sha'`. Updates update existing `evidence_items` in place; duplicates are never created.

---

## 3. Jira Integration

### 3.1 OAuth 2.0 (3LO) Flow
- Scopes requested: `read:jira-work`, `read:jira-user`, `offline_access`.
- Authorization URL: `https://auth.atlassian.com/authorize`.
- Token URL: `https://auth.atlassian.com/oauth/token`.
- Accessible Resources (Cloud Sites): `GET https://api.atlassian.com/oauth/token/accessible-resources`.

### 3.2 Resource Discovery & Mapping
- Discover accessible Jira sites and their `cloud_id`.
- Discover accessible Jira projects: `GET https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/project/search`.
- User explicitly maps a Jira project (e.g. `KEY="HANDOVER"`) to a platform project workspace.

### 3.3 Evidence Ingestion Pipeline
1. Ingests Jira project metadata.
2. Ingests issues via JQL search (`/rest/api/3/search?jql=project={project_key}&expand=changelog,names`).
3. Captures issue key, summary, description, issue type, priority, status, assignee, reporter, resolution, fixVersions.
4. Ingests issue comments (`/rest/api/3/issue/{issueIdOrKey}/comment`).
5. Ingests status transitions and changelog entries.

---

## 4. Slack Integration (Optional MVP Boundary)
- In accordance with the governance charter, Slack is **disabled by default** (`SLACK_ENABLED=false`).
- If enabled, requires organization authorization, explicit channel selection, and user confirmation of data retention policies.
- If not enabled, the backend reports `provider='slack'` as `disabled`, and never fabricates fake Slack connections or messages.

---

## 5. Source-Level Access Control (ACL) Enforcement
- External sources retain user-level permissions.
- When an evidence item is requested by user $U$:
  1. Backend checks if $U$ is the user who connected the source, OR
  2. If the repository is public, OR
  3. If $U$ has a verified `source_connection` with read permissions to that same external resource identifier.
- If no permission can be verified, access is denied (HTTP 403 Forbidden).
