# ADR 0003: PostgreSQL as Canonical Application and Knowledge Store

## Status
Accepted

## Context
A knowledge reconstruction platform deals with multi-tenant organizations, projects, team memberships, fine-grained RBAC, evidence metadata, extraction provenance, structured knowledge items, relationships, verification workflows, and audit logs. There was consideration of using alternative stores or offloading application tables to Supabase.

## Decision
1. **PostgreSQL as Single Source of Truth**: PostgreSQL remains the authoritative, canonical store for all application data, user profiles, RBAC roles/permissions, source connections, project source mappings, evidence items, chunks, knowledge items, verification decisions, and audit events.
2. **No Graph Database in Initial Baseline**: Knowledge relationships (dependencies, decisions, ownership) are stored as structured relational records with foreign key integrity and indexes in PostgreSQL.
3. **Full-Text Search Engine**: PostgreSQL `tsvector` and `tsquery` provide exact keyword, symbol, identifier, and commit hash search across evidence chunks.
4. **Independent from Secondary Stores**: ChromaDB vector indices and Supabase Storage buckets are secondary and always rebuildable from canonical PostgreSQL records.

## Consequences
- ACID transactions guarantee state consistency across permissions, evidence ingestion, and audit trails.
- Simplifies operational footprint and backup recovery.
