# Phase 2.7 Audit: Entity Model Review

**Document**: `docs/engineering-audit/phase-2-7/entity-model-review.md`  
**Phase**: 2.7 — Complete Knowledge Intelligence Engine  
**Module**: Module A — Canonical Entity Taxonomy and Data Model  
**Status**: APPROVED & VERIFIED  

---

## 1. Executive Summary

This document reviews the data model implementation for Knowledge Entities within **The Handover** platform. Prior to Phase 2.7, the entity enum (`EntityType`) defined 12 coarse-grained categories with several critical semantic gaps (e.g., lacking explicit `risk`, `blocker`, `dependency`, `milestone`, `commit`, and `operational_procedure` representations). 

In Phase 2.7, `EntityType` was expanded to full 19-entity taxonomy alignment while preserving complete backward compatibility with existing legacy entities in PostgreSQL.

---

## 2. Canonical Entity Taxonomy Review

The 19 canonical entity types are organized into 5 functional clusters:

| Cluster | Entity Type | Enum Value | Description |
| :--- | :--- | :--- | :--- |
| **Project & Org** | Project | `project` | High-level workspace and container for all assets |
| | Person | `person` | Project contributors, reviewers, authors, assignees |
| | Organisation | `organisation` | Multi-tenant organization boundaries |
| **Requirements & Decisions** | Decision | `decision` | Architectural and technical choices with rationale |
| | Requirement | `requirement` | Functional/non-functional specifications |
| | Milestone | `milestone` | Target deadlines, release phases, delivery gates |
| **Work Management** | Task | `task` | Actionable work units across Jira, GitHub, docs |
| | Feature | `feature` | High-level capabilities or epic deliverables |
| | Issue | `issue` | Problem tickets, defects, Jira issues, GitHub issues |
| | Blocker | `blocker` | Critical impediments halting work progress |
| | Dependency | `dependency` | Prerequisite constraints linking entities |
| **Technical & Code** | Technical Component | `technical_component` | Libraries, services, modules, APIs |
| | Architecture Component | `architecture_component`| High-level subsystems, boundary gateways |
| | Repository | `repository` | Code repositories (e.g., GitHub repos) |
| | Pull Request | `pull_request` | Code review and integration proposals |
| | Commit | `commit` | Atomic VCS change sets with sha |
| **Documentation & Procedures**| Document | `document` | Uploaded PDFs, DOCX, specs, architecture docs |
| | Operational Procedure | `operational_procedure`| Runbooks, deployment instructions, SOPs |
| | Risk | `risk` | Documented project threats, liabilities, technical debt |

### Backward Compatibility Mapping
Legacy aliases are preserved in `backend/app/models/enums.py`:
- `team` -> Aliased / mapped to `organisation`
- `work_item` -> Mapped to `task`
- `component` -> Mapped to `technical_component`
- `finding` -> Reconstructed finding item

---

## 3. Database Schema Verification

### Table Definition (`knowledge_entities`)
Located in PostgreSQL public schema:
- `id` (`UUID`, PK)
- `project_id` (`UUID`, FK `projects.id`, ON DELETE CASCADE)
- `entity_type` (`VARCHAR(32)`, NOT NULL, indexed)
- `name` (`VARCHAR(255)`, NOT NULL)
- `normalized_name` (`VARCHAR(255)`, NOT NULL, indexed)
- `canonical_entity_id` (`UUID`, FK `knowledge_entities.id`, nullable)
- `description` (`TEXT`, nullable)
- `aliases` (`JSONB`, NOT NULL, default `'[]'`)
- `status` (`VARCHAR(32)`, default `'active'`)
- `metadata` (`JSONB`, NOT NULL, default `'{}'`)
- `source_evidence_ids` (`JSONB`, NOT NULL, default `'[]'`)
- `confidence_score` (`FLOAT`, NOT NULL, default 1.0)
- `created_at` / `updated_at` (`TIMESTAMPTZ`)

### Migration Impact Analysis
Because `entity_type` is defined as `VARCHAR(32)` without a native PostgreSQL enum type constraint or static check constraint:
- Python enum expansion does **not** alter the database schema.
- Zero Alembic migration is required.
- Zero risk of table locking or migration regression on live Supabase (`0016_rls_hardening`).

---

## 4. Multi-Tenant Isolation Guarantees

Every entity record is bound to a strict `project_id`. All queries executed via `RelationshipExplorerService` enforce:
1. `WHERE knowledge_entities.project_id = :project_id`
2. Cross-project entity references are strictly rejected at the service validation boundary.
3. Pre-retrieval ACL filtering ensures users cannot inspect entities derived exclusively from sources they lack permissions to access.
