# ADR 0005: Project-Isolated ChromaDB Vector Collections

## Status
Accepted

## Context
In early implementations, vector search was either stored globally across all projects or proposed per-document. Neither is architecturally sound: global collections mix different organizations and projects, creating multi-tenant data leakage risks, while per-document collections prevent holistic cross-source semantic search within a project.

## Decision
1. **One Collection Per Project**: Every Handover project maintains exactly one dedicated ChromaDB vector collection (e.g. `th_project_{stable_hash}`).
2. **Unified Cross-Source Embedding**: All evidence chunks from that project—whether from PDFs, DOCX files, GitHub commits/PRs/issues, Jira tickets/comments, or Slack threads—are embedded using `nomic-embed-text` and stored in the project's single collection.
3. **Cross-Project Isolation**: Vector queries are strictly scoped to the active project collection. Vectors from Project A can never be returned to Project B.
4. **PostgreSQL Authoritative Revalidation**: ChromaDB collection boundaries do not replace access control. Candidate vectors returned by ChromaDB are joined against PostgreSQL to verify current user source-level ACL permissions before returning content or supplying it to Qwen3 prompts.

## Consequences
- Enables unified semantic search across code, tickets, discussions, and documents within a project.
- Guarantees strict multi-tenant isolation at the vector storage layer.
