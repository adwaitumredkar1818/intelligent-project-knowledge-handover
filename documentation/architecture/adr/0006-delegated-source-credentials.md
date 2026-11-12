# ADR 0006: Delegated Per-User Source Credentials and Secure Token Management

## Status
Accepted

## Context
When connecting external repositories (GitHub), issue trackers (Jira), and communication channels (Slack), naive architectures often use global organization credentials or assume one user's account grants universal access. This violates principle of least privilege and leaks restricted materials.

## Decision
1. **Per-User Delegated Credentials**:
   - **GitHub**: Fine-grained Personal Access Tokens (PATs) with minimal read-only permissions (`Metadata: Read`, `Contents: Read`, `Issues: Read`, `Pull requests: Read`), entered by the user.
   - **Jira**: Primary Atlassian OAuth 2.0 (3LO) with read scopes (`read:jira-work`, `read:jira-user`, `offline_access`), with an optional controlled API token mode for local testing (`JIRA_API_TOKEN_MODE_ENABLED=true`).
   - **Slack**: Slack OAuth v2 read-only scopes (`channels:read`, `channels:history`, `groups:read`, `groups:history`, `users:read`), with an optional development Bot Token mode (`SLACK_MANUAL_BOT_TOKEN_ENABLED=true`).
2. **At-Rest AES-256-GCM Encryption**: All access tokens and credentials are encrypted using `TOKEN_ENCRYPTION_KEY` before persisting to PostgreSQL.
3. **Zero Plaintext Exposure**: Raw credentials are never exposed via API responses, logs, or stored in frontend browser storage. Sensitive form fields are password-masked and cleared after submission.

## Consequences
- Preserves external authorization boundaries.
- Complies with enterprise security requirements.
