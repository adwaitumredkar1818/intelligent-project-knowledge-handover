# The Handover — Product Modules Architecture

## 1. Complete Product Modules Overview

The Handover is structured into seven primary functional modules accessed via six persistent sidebar navigation groups:

```text
┌────────────────────────────────────────────────────────┐
│                      THE HANDOVER                      │
├──────────────────────────┬─────────────────────────────┤
│ SIDEBAR NAVIGATION GROUP │ CANONICAL PRODUCT MODULE   │
├──────────────────────────┼─────────────────────────────┤
│ 1. WORKSPACE             │ Module 1: Project Workspace │
│ 2. PROJECT INTELLIGENCE  │ Module 2: Evidence Workspace│
│                          │ Module 3: Knowledge Intel   │
│                          │ Module 4: Rel Explorer      │
│ 3. VALIDATION            │ Module 5: Verification Ctr  │
│ 4. KNOWLEDGE TRANSFER    │ Module 6: Handover Workspace│
│ 5. AI ASSISTANT          │ Module 7: AI Assistant      │
│ 6. ADMINISTRATION        │ Cross-Cutting Governance    │
└──────────────────────────┴─────────────────────────────┘
```

---

## 2. Module Specifications

### Module 1: Project Workspace (Active Implementation)
- **Purpose**: Provides the organizational container, project lifecycle, team membership, transition configuration, and high-level aggregated dashboard for handover initiatives.
- **Sidebar Locations**: `WORKSPACE > Overview`, `WORKSPACE > Projects`, `WORKSPACE > Team Members`.
- **Inputs**: Organization ID, project metadata, team member assignments, project roles, departing member designation, successor designation, capture windows.
- **Processing**: Tenant scoping, RBAC permission verification, transition participant validation, grouped metric aggregation across evidence, sources, and audit logs.
- **Outputs**: Project records, membership lists, transition configuration records, dashboard aggregation payload, activity feeds.
- **Interactions**: Establishes tenant and project context for all other modules. Passes project ID scope to Evidence Workspace and downstream modules.

### Module 2: Evidence Workspace (Active Implementation)
- **Purpose**: Manages connected external sources, document uploads, document extraction and OCR, evidence lifecycle, and the project-scoped Evidence Library and Details.
- **Sidebar Locations**: `PROJECT INTELLIGENCE > Evidence Center`, `ADMINISTRATION > Connected Sources`.
- **Three-Panel Architecture**:
  - **Panel A (Connected Sources)**: Provider connection cards (GitHub, Jira, PDF, DOCX, Slack), account identity, sync status, sync triggers.
  - **Panel B (Evidence Library)**: Filterable, searchable, paginated table of ingested records with metadata, timestamps, author, and status.
  - **Panel C (Evidence Details)**: Inspection view showing original source metadata, author, timestamps, extracted text, page/chunk references, source URLs, and provenance.
- **Inputs**: OAuth tokens, repository IDs, Jira cloud IDs, uploaded PDF/DOCX files, search/filter queries.
- **Processing**: Delegated OAuth handshake, token encryption, file signature validation, PyMuPDF parsing, GLM OCR on scanned pages, SHA-256 deduplication, chunking, PostgreSQL-backed async sync jobs.
- **Outputs**: Canonical `evidence_items`, `document_files`, `evidence_contents`, `source_connections`, `source_sync_jobs`.
- **Interactions**: Supplies raw evidence and chunk references to Knowledge Intelligence and the retrieval index. Serves as the immutable proof backing all findings.

### Module 3: Knowledge Intelligence (Architecturally Supported)
- **Purpose**: Extracts structured knowledge findings across the eight project knowledge domains from evidence chunks using local LLM inference.
- **Sidebar Location**: `PROJECT INTELLIGENCE > Knowledge Intelligence`.
- **Inputs**: Permission-filtered evidence text chunks from Evidence Workspace.
- **Processing**: Ollama (`qwen3:8b`) prompt execution, Pydantic schema validation, confidence calculation, missing-information detection.
- **Outputs**: Candidate knowledge records (decisions, tasks, risks, responsibilities, dependencies).
- **Current Scope**: Data models and enum contracts defined. Automated LLM extraction pipeline is deferred to subsequent phases.

### Module 4: Relationship Explorer (Architecturally Supported)
- **Purpose**: Reconstructs and visualizes relationships between fragmented items (e.g. decision to commit, PR to Jira task, owner to component).
- **Sidebar Location**: `PROJECT INTELLIGENCE > Relationship Explorer`.
- **Inputs**: Candidate knowledge entities, commit SHAs, issue keys, source IDs.
- **Processing**: Exact-ID matching (solid edges), semantic co-occurrence and LLM suggestions (dashed candidate edges). Relational storage in PostgreSQL (no graph DB).
- **Outputs**: Relationship edge records with link types and evidence basis.
- **Current Scope**: Relational schema supported. Graph visualization deferred.

### Module 5: Verification Center (Architecturally Supported)
- **Purpose**: Provides a dedicated human-in-the-loop review queue for technical leads and reviewers to verify candidate findings, resolve contradictions, and certify knowledge.
- **Sidebar Locations**: `VALIDATION > Verification Center`, `VALIDATION > Conflicts`.
- **Inputs**: Candidate findings, conflict flags, missing information requests.
- **Processing**: Status transitions (`candidate` -> `verified` / `rejected` / `modified`), resolution logs, immutable audit trail.
- **Outputs**: Human-Verified Knowledge records.
- **Current Scope**: Schema status fields and audit events prepared. Full interactive review queue deferred.

### Module 6: Handover Workspace (Architecturally Supported)
- **Purpose**: Assembles verified findings, readiness checklists, and operational notes into a cohesive, role-tailored handover package.
- **Sidebar Locations**: `KNOWLEDGE TRANSFER > Handover Workspace`, `KNOWLEDGE TRANSFER > Generated Handovers`.
- **Inputs**: Verified knowledge records, transition configuration, reviewer sign-off.
- **Processing**: Handover document assembly, readiness scoring, human reviewer approval gate, versioned publishing.
- **Outputs**: Versioned handover packages, successor receipt acknowledgement records.
- **Current Scope**: Transition participant models implemented. Handover compilation engine deferred.

### Module 7: Project Knowledge Assistant (Architecturally Supported)
- **Purpose**: Evidence-grounded conversational assistant allowing incoming successors to query project knowledge with strict source citations and uncertainty disclosure.
- **Sidebar Location**: `AI ASSISTANT > Project Knowledge Assistant`.
- **Inputs**: Natural language questions, user project context, user source permissions.
- **Processing**: Hybrid RAG (PostgreSQL full-text search + ChromaDB vector search), permission pre-filtering, grounded synthesis via `qwen3:8b`.
- **Outputs**: Grounded answers with clickable evidence links and explicit uncertainty warnings.
- **Current Scope**: ChromaDB and Ollama infrastructure active. Conversational orchestration deferred.

---

## 3. Administration & Cross-Cutting Governance
- **Connected Sources**: Global management of organization and user source authorizations.
- **Audit Logs**: Immutable PostgreSQL audit trail of all security, project, source, and verification events.
- **Settings**: System configuration, rate limiting, and project-level parameters.
