# Knowledge Intelligence Module Specification

## 1. Executive Summary & Epistemic Foundation

The **Knowledge Intelligence Module** (Canonical Product Module 3) reconstructs unstructured and fragmented project evidence into structured, actionable, and verifiable project records across **eight canonical knowledge domains**.

### The Core Principle
> **AI EXTRACTS KNOWLEDGE. EVIDENCE SUPPORTS IT. AUTHORISED HUMANS VALIDATE IT.**

- **NO EVIDENCE -> NO CLAIM**: No knowledge item can exist in the platform without at least one verified supporting link to an immutable evidence chunk.
- **Project Membership != Source Access**: Evidence and knowledge items derived from restricted external sources (e.g. private GitHub repositories, confidential Jira tickets) are filtered strictly at query time based on external source ACLs. Non-permitted users receive `403 SOURCE_ACCESS_DENIED`.
- **Four-Tier Epistemic Separation**:
  1. **Original Source Evidence**: Immutable raw files and connector payload chunks.
  2. **Extracted Information**: Direct verbatim excerpts anchored to chunk offsets and SHA-256 hashes.
  3. **AI-Generated Interpretation**: Inferred relationships, impact assessments, and categorisations tagged with `is_interpretation=true`.
  4. **Human-Verified Knowledge**: Records formally reviewed, approved, or modified by designated project members.

---

## 2. Eight Canonical Project Knowledge Domains

| Domain # | Canonical Domain Identifier | Scope & Extracted Knowledge |
|---|---|---|
| **Domain 1** | `PROJECT_OVERVIEW_CONTEXT` | High-level project purpose, problem statement, business/operational objectives, historical context, key stakeholders, constraints, and success criteria. |
| **Domain 2** | `DECISIONS_RATIONALE` | Architectural and design decisions, alternatives evaluated, trade-offs considered, rationale, acceptance status, decision-makers, and superseding context. |
| **Domain 3** | `ARCHITECTURE_TECHNICAL` | System architecture, backend/frontend structures, APIs, database schemas, integration patterns, configurations, conventions, workarounds, and technical debt. |
| **Domain 4** | `WORK_STATUS_PROGRESS` | Completed milestones, in-progress tasks, deferred or cancelled items, PR/commit references, test coverage status, and deliverable tracking. |
| **Domain 5** | `OWNERSHIP_RESPONSIBILITIES` | Module and service owners, primary maintainers, subject matter experts (SMEs), key contacts, and transition participant mappings. |
| **Domain 6** | `DEPENDENCIES_INTEGRATIONS` | External systems, internal libraries, third-party APIs, SDKs, data feeds, external blockers, cross-team coupling, and version requirements. |
| **Domain 7** | `RISKS_BLOCKERS_BUGS` | Active impediments, open critical/high bugs, technical debt risks, operational vulnerabilities, security concerns, performance hotspots, and missing documentation. |
| **Domain 8** | `OPERATIONAL_HISTORICAL` | Deployment instructions, runbooks, setup procedures, environment troubleshooting, backup/recovery protocols, historical pivots, and past incidents. |

---

## 3. Architecture & Data Model

### PostgreSQL Database Schema
- **Migration**: `0010_knowledge_domains` (`infrastructure/database/migrations/versions/20261113_0010_knowledge_domains.py`)
- **`knowledge_items`**:
  - `id`: UUID (Primary Key)
  - `organisation_id`: UUID (Foreign Key -> `organisations.id`)
  - `project_id`: UUID (Foreign Key -> `projects.id`)
  - `primary_domain`: String(64) — e.g. `DECISIONS_RATIONALE` (indexed with `project_id`)
  - `secondary_domains`: JSONB Array — additional cross-domain affiliations
  - `category`: String(64) — legacy alias and sub-category
  - `title`: String(255)
  - `structured_summary`: Text
  - `structured_payload`: JSONB — domain-specific typed fields
  - `epistemic_status`: Enum (`extracted`, `interpreted`, `human_verified`, `rejected`)
  - `review_status`: Enum (`pending_review`, `approved`, `rejected`, `flagged_for_clarification`)
  - `support_classification`: Enum (`direct`, `inferred`, `contradicted`, `unsupported`)
- **`knowledge_evidence_links`**:
  - `knowledge_item_id`: UUID
  - `evidence_id`: UUID
  - `evidence_chunk_id`: UUID
  - `supporting_excerpt`: Text — exact verbatim text from chunk
  - `support_type`: Enum (`direct`, `inferred`, `contradicted`, `contextual`)
  - `excerpt_verified`: Boolean

---

## 4. REST API Contract

All endpoints are scoped under `/api/v1/projects/{project_id}/knowledge-intelligence`.

### 4.1 Domain Coverage & Telemetry
- **`GET /domains`**: Returns real-time metrics across all 8 domains (item count, verified count, pending count, high-confidence count, completeness percentage, active domains count).
- **`GET /summary`**: Returns executive handover readiness score (`0-100`), domain breakdown, and latest extraction run metadata.

### 4.2 Findings & Provenance
- **`GET /findings`**: Lists knowledge items filtered by `domain`, `epistemic_status`, `review_status`, `support_classification`, `person`, `source_provider`, `date_from`, `date_to`. Strictly filters items against the caller's external source permissions.
- **`GET /findings/{finding_id}`**: Retrieves finding details and verified supporting excerpts. Returns `403 SOURCE_ACCESS_DENIED` if supporting source access has been revoked.

### 4.3 Chronological Timeline Synthesis
- **`GET /timeline`**: Synthesizes a chronologically unified event stream from decisions, milestones, commits, and incidents with day- and second-precision timestamps. Supports filtering by `domain`, `event_type`, `source_provider`, and sorting (`asc`/`desc`).

### 4.4 Extraction Execution & Telemetry
- **`POST /extract`**: Asynchronously enqueues an extraction run for specified domains or all 8 domains via `ReconstructionWorker`.
- **`GET /runs`**: Lists past extraction job executions, model versions, processed chunk counts, and candidate yield.
- **`GET /runs/{run_id}`**: Inspects execution status, candidate counts, and logs for a specific run.

---

## 5. Security & Fail-Closed Access Control

1. **Authentication**: All routes require valid Supabase JWT bearer token.
2. **Project Authorization**: Caller must hold active membership with `project.read` permission.
3. **Read-Time Source ACL Enforcement**:
   - Every candidate finding is linked to source evidence.
   - For every evidence item originating from a restricted provider (e.g. GitHub repo), the caller's user ID is checked against `source_access_policies.allowed_user_ids`.
   - If the user is not explicitly permitted, the finding is completely omitted from list responses and returns `403 SOURCE_ACCESS_DENIED` on direct detail retrieval.
