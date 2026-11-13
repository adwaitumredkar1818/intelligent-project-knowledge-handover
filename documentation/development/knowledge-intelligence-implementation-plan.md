# Knowledge Intelligence Implementation Plan

**Product**: The Handover — Intelligent Project Knowledge Reconstruction & Handover Platform  
**Module**: Module 3 — Knowledge Intelligence Backend  
**Date**: November 13, 2026  
**Auditor & Architect**: Antigravity Software Engineering Agent  
**Status**: APPROVED ARCHITECTURAL PLAN (Ready for Execution)

---

## 1. Overview & Architectural Goals

The Knowledge Intelligence module transforms permission-filtered evidence from the Evidence Workspace into structured, traceable project knowledge records across **eight canonical project knowledge domains**.

### Core Tenet
> **AI EXTRACTS KNOWLEDGE. EVIDENCE SUPPORTS IT. AUTHORISED HUMANS VALIDATE IT.**

The system is not a conversational bot and not a generic summarizer. It is a deterministic, evidence-grounded reconstruction engine that preserves source citations, character-accurate excerpts, epistemic boundaries, confidence indicators, and human review states.

---

## 2. Eight Canonical Project Knowledge Domains

### Domain Taxonomy & Canonical Registry

The central domain registry is established in `backend/app/services/knowledge_domains.py` as an immutable singleton registry:

| Canonical Domain Identifier | Display Name | Supported Finding Types | Description | Legacy Category Mapped |
| :--- | :--- | :--- | :--- | :--- |
| `PROJECT_OVERVIEW_CONTEXT` | **Project Overview & Context** | `project_purpose`, `objective`, `scope_boundary`, `stakeholder`, `business_context`, `constraint`, `assumption`, `terminology` | High-level project charter, purpose, objectives, business context, in/out of scope boundaries, stakeholders, and terminology required for project transition. | *New Capability* |
| `DECISIONS_RATIONALE` | **Decisions & Rationale** | `architectural_decision`, `product_decision`, `process_decision`, `infra_choice`, `security_choice` | Architectural, technical, process, and product choices made, proposed, rejected, or superseded, with explicit rationale and trade-offs. | `decisions_rationale` |
| `ARCHITECTURE_TECHNICAL` | **Architecture & Technical Knowledge** | `system_architecture`, `api_endpoint`, `database_design`, `data_model`, `configuration`, `convention`, `technical_debt` | Reconstructed technical blueprints, service interactions, API schemas, DB structures, technical conventions, and known limitations. | `technical_architecture` |
| `WORK_PROGRESS` | **Work & Progress** | `completed_work`, `work_in_progress`, `pending_work`, `blocked_work`, `cancelled_work` | Comprehensive ledger of completed milestones, active tasks, Jira issues, GitHub PRs, and outstanding work items. | `work_items` |
| `RESPONSIBILITIES_OWNERSHIP`| **Responsibilities & Ownership** | `component_ownership`, `duty_assignment`, `reviewer_role`, `escalation_contact`, `historical_owner` | Human accountability mapping for components, services, deployment on-call, and transitional handoff participants. | `responsibilities_ownership` |
| `DEPENDENCIES_RELATIONSHIPS`| **Dependencies & Relationships** | `service_dependency`, `api_dependency`, `task_sequence`, `team_approval`, `external_system` | Concrete, explicitly documented dependencies and blocking relationships connecting systems, tasks, and teams. | `dependencies` |
| `RISKS_BLOCKERS_QUESTIONS` | **Risks, Blockers & Open Questions** | `technical_risk`, `operational_risk`, `security_risk`, `bug`, `blocker`, `unanswered_question` | Critical obstacles, defects, vulnerabilities, recurring issues, and unanswered technical questions that threaten project continuity. | `bugs_blockers_risks` |
| `OPERATIONAL_HISTORICAL` | **Operational & Historical Knowledge** | `deployment_runbook`, `setup_procedure`, `env_configuration`, `troubleshooting_guide`, `historical_event`, `superseded_approach` | Practical operational procedures, runbooks, configuration rules, alongside historical context, past pivots, and resolved incidents. | *New Capability* |

### Cross-Domain Perspectives
1. **Overview**: An aggregated dashboard summary of findings, review readiness, and source distribution across all 8 domains (not a domain).
2. **Project Timeline**: A chronological cross-domain event perspective derived from timestamped knowledge items, evidence events, and audit logs (not a domain).

---

## 3. Database Schema Upgrades & Compatibility Layer

To seamlessly support the 8 canonical domains while preserving existing Phase 2.6 records and zero downtime:

### 3.1 Alembic Migration `20261113_0010_knowledge_domains_and_timeline.py`
1. **Check Constraint Expansion on `knowledge_items.category`**:
   Update `ck_knowledge_items_knowledge_item_category` to permit:
   - Canonical 8 domains (e.g. `PROJECT_OVERVIEW_CONTEXT`, `DECISIONS_RATIONALE`, `ARCHITECTURE_TECHNICAL`, `WORK_PROGRESS`, `RESPONSIBILITIES_OWNERSHIP`, `DEPENDENCIES_RELATIONSHIPS`, `RISKS_BLOCKERS_QUESTIONS`, `OPERATIONAL_HISTORICAL`).
   - Lowercase canonical domains (`project_overview_context`, `operational_historical`, etc.).
   - Legacy 6 categories (`decisions_rationale`, `work_items`, `responsibilities_ownership`, `technical_architecture`, `bugs_blockers_risks`, `dependencies`).
2. **Add Explicit Domain Columns on `knowledge_items`**:
   - `primary_domain`: `sa.Column(sa.String(length=64), nullable=True)` (indexed).
   - `secondary_domains`: `sa.Column(postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))`.
3. **Backfill Existing Items**:
   Execute SQL update in migration backfilling `primary_domain = category_to_canonical_domain(category)` for all existing records.
4. **Expand `knowledge_evidence_links.support_type` Check Constraint**:
   Update `ck_knowledge_evidence_links_knowledge_evidence_link_support_type` to permit canonical evidence roles:
   `'direct', 'direct_support', 'corroborated', 'corroboration', 'interpretation', 'context', 'uncertain', 'contradiction'`.

---

## 4. Extraction Prompts & Candidate Validation Schemas

### 4.1 Two New Candidate Schemas in `backend/app/schemas/knowledge.py`
1. **`ProjectOverviewCandidate`**:
   - `project_purpose`: String
   - `objectives`: List of strings
   - `problem_statement`: String or None
   - `in_scope`: List of strings
   - `out_of_scope`: List of strings
   - `stakeholders`: List of strings
   - `business_context`: String or None
   - `target_users`: List of strings
   - `key_milestones`: List of strings
   - `constraints`: List of strings
   - `assumptions`: List of strings
   - `terminology`: Dict[str, str]
2. **`OperationalHistoricalCandidate`**:
   - `knowledge_type`: `Literal["operational_procedure", "deployment_instruction", "troubleshooting_guide", "configuration_rule", "historical_event", "superseded_approach", "historical_incident"]`
   - `procedure_or_event_title`: String
   - `steps_or_narrative`: List of strings or string
   - `prerequisites`: List of strings
   - `environment_or_target`: String or None
   - `historical_context`: String or None
   - `superseded_reason`: String or None
   - `is_potentially_outdated`: Boolean
   - `verification_recommendation`: String or None

### 4.2 Two New Extraction Prompts in `backend/app/services/extraction_prompts.py`
1. **`overview_context_v1`**:
   Extracts formal purpose, objectives, stakeholders, scope constraints, and terminology.
   Enforces: Do NOT guess objectives from repository names; do NOT derive status from an isolated outdated note.
2. **`operational_historical_v1`**:
   Extracts step-by-step procedures, runbooks, and historical pivots/incidents.
   Enforces: Preserve timestamps; flag potentially outdated operational instructions.

---

## 5. Candidate Validation & Grounding Engine

In `backend/app/services/knowledge_validator.py`:
1. Register `ProjectOverviewCandidate` and `OperationalHistoricalCandidate` in `_CANDIDATE_MODEL_BY_DOMAIN`.
2. Implement domain-specific fingerprint algorithms ensuring idempotent deduplication:
   - For Overview items: hash of normalized purpose, objective, or terminology term.
   - For Operational items: hash of procedure title + environment target.
3. Validate verbatim excerpt presence in chunk text (min 12 characters).
4. Verify chunk IDs belong to the current project and active extraction run.
5. Filter out ungrounded claims with rejection reasons recorded in `BatchValidationReport`.

---

## 6. Cross-Domain Project Timeline Synthesis

Create `ProjectTimelineService` in `backend/app/services/timeline.py`:
1. Queries timestamped `KnowledgeItem` records and their supporting `KnowledgeEvidenceLink` records.
2. Reconstructs chronological event sequence:
   - Decision proposed/accepted dates
   - Work item created, updated, and completed dates
   - Pull request and commit dates
   - Risk and incident reported dates
   - Operational procedure updates
3. Retains exact precision (`day`, `hour`, `second`).
4. Avoids confusing source creation date with event occurrence date or ingestion date.
5. Returns typed `ProjectTimelineResponse` with filters for domain, provider, and date range.

---

## 7. Knowledge Intelligence API Endpoints

Add dedicated router `backend/app/api/routes/knowledge_intelligence.py` mounted at `/api/v1`:

1. `GET /api/v1/projects/{project_id}/knowledge-intelligence/domains`:
   - Returns metadata, display info, finding types, and real counts for all 8 domains.
2. `GET /api/v1/projects/{project_id}/knowledge-intelligence/summary`:
   - High-level overview metrics across the 8 domains, review statuses, and source coverage.
3. `GET /api/v1/projects/{project_id}/knowledge-intelligence/findings`:
   - Paginated, searchable, multi-filtered findings queryable by domain, finding type, review status, person, source provider, and date range.
4. `GET /api/v1/projects/{project_id}/knowledge-intelligence/findings/{finding_id}`:
   - Complete finding details including structured payload, supporting evidence excerpts, contradiction links, confidence indicators, and review state.
5. `GET /api/v1/projects/{project_id}/knowledge-intelligence/timeline`:
   - Chronological cross-domain timeline events with precision indicators and evidence links.
6. `POST /api/v1/projects/{project_id}/knowledge-intelligence/extract`:
   - Enqueue asynchronous extraction targeting specific domains or all eligible evidence chunks.
7. `GET /api/v1/projects/{project_id}/knowledge-intelligence/runs`:
   - List extraction run history, duration, token telemetry, and grounding metrics.

---

## 8. Phased Implementation Roadmap

```text
STEP 1: Domain Registry & Taxonomy Definition
  ├── Create backend/app/services/knowledge_domains.py
  └── Map 6 legacy categories to 8 canonical domains

STEP 2: Alembic Database Migration
  ├── Create migration 0010_knowledge_domains_and_timeline.py
  ├── Expand check constraints for category and evidence link support_type
  └── Add primary_domain and secondary_domains to knowledge_items

STEP 3: Extraction Prompts & Candidate Schemas
  ├── Add ProjectOverviewCandidate & OperationalHistoricalCandidate to schemas/knowledge.py
  └── Add overview_context_v1 & operational_historical_v1 to services/extraction_prompts.py

STEP 4: Candidate Validation & Deduplication
  ├── Update KnowledgeCandidateValidator in services/knowledge_validator.py
  └── Implement domain-specific fingerprinting & excerpt validation

STEP 5: Repository & Worker Upgrades
  ├── Update KnowledgeRepository to query by canonical domain and legacy categories
  └── Update ReconstructionWorkerService to handle 8-domain extraction loops

STEP 6: Project Timeline Engine
  └── Implement ProjectTimelineService in services/timeline.py

STEP 7: Knowledge Intelligence API Endpoints
  └── Implement api/routes/knowledge_intelligence.py and register in app/main.py

STEP 8: Test Suite & Live Qwen3 Evaluation
  ├── Add comprehensive domain, evidence, security, and lifecycle tests
  └── Execute Pytest, Ruff, Mypy, and Alembic checks
```

---

## 9. Verification & Acceptance Criteria

- [ ] All 8 canonical domains registered in central registry.
- [ ] Alembic migration applied and verified via `alembic check`.
- [ ] Qwen3 structured extraction operational for all 8 domains.
- [ ] Verbatim excerpt matching enforced (`NO EVIDENCE -> NO CLAIM`).
- [ ] Cross-domain Project Timeline endpoint verified with source timestamps.
- [ ] Source ACL enforcement strictly prevents unauthorized evidence access.
- [ ] 100% of Pytest tests pass with zero regressions.
- [ ] Ruff and strict Mypy pass with zero errors.
- [ ] Zero fake data inserted into production database.
