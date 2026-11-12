# ADR 0007: Strict Separation of Project Membership and Source-Level Access

## Status
Accepted

## Context
A critical vulnerability in multi-source knowledge systems is assuming that membership in a project automatically confers permission to read all underlying source materials connected by other team members (e.g. private GitHub repositories or restricted Jira security issues).

## Decision
1. **Critical Axiom**: `Project Membership != Source Access`.
2. **Read-Time ACL Verification**: Before any evidence item, document, or chunk is returned via API or included in a RAG prompt for Qwen3, the backend verifies that the requesting user possesses valid, current external access permissions to that specific source container (repository, Jira project, or private document).
3. **Fail-Closed Policy**: If a user's permissions cannot be established or verified, access is denied (fail closed).
4. **Token Revocation Immediate Effect**: When an external token expires or is revoked, evidence derived from that source connection is immediately filtered out from the user's view, even if previously indexed in ChromaDB.

## Consequences
- Prevents horizontal privilege escalation across project collaborators.
- Ensures evidence citations in handover packages respect organizational confidentiality.
