# Canonical Entity Taxonomy & Data Model

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Module:** **Module A — Canonical Entity Taxonomy and Data Model**  
**Audit Phase:** **Phase 2.7 — Complete Knowledge Intelligence Engine**  
**Date:** 2026-11-14  

---

## 1. Overview & 19 Canonical Categories

The platform supports 19 canonical project entity categories in `backend/app/models/enums.py` (`EntityType`), mapping directly to real software project artefacts:

1. `project`: Project workspaces and boundary scopes.
2. `person`: Software engineers, architects, managers, volunteers, researchers.
3. `organisation`: Top-level multi-tenant enterprise and team boundaries.
4. `decision`: Architectural Decision Records (ADRs) and recorded choices.
5. `requirement`: Product/functional/security specifications motivating decisions.
6. `task`: Work units, tickets, or epics.
7. `feature`: Customer-facing capability or system function.
8. `technical_component`: Backend service, database, cache, or worker module.
9. `architecture_component`: Structural design patterns, gateways, or layers.
10. `repository`: Git repositories and source code projects.
11. `pull_request`: Merged or open pull requests delivering changes.
12. `commit`: Specific git commit SHAs containing implementation changes.
13. `issue`: Bug reports, incidents, or feature requests.
14. `document`: Architectural specs, meeting transcripts, design documents.
15. `risk`: Identified architectural or operational vulnerabilities.
16. `blocker`: Active impediments preventing work progression.
17. `dependency`: External packages, libraries, or inter-service contracts.
18. `milestone`: Target delivery dates, releases, or sprints.
19. `operational_procedure`: Runbooks, deployment protocols, or maintenance guides.

---

## 2. Model Compatibility & Constraints

- **Storage Table:** `knowledge_entities`
- **Schema Qualification:** Column `entity_type` is stored as `String(32)` with index `ix_entities_project_type_norm`.
- **Zero Alembic Drift:** No database migration was required to expand the enum, preserving existing live Supabase schema alignment.
- **Constraints Enforced:**
  - Non-empty canonical name (`length(trim(canonical_name)) >= 1`).
  - Confidence range assertion (`0.0 <= confidence_score <= 1.0`).
  - Strict organisation and project foreign keys (`ondelete="CASCADE"`).
