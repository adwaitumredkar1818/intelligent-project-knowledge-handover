# THE HANDOVER — VERIFICATION CENTER
## Prioritized Remediation & Next-Phase Implementation Plan

- **Module**: Verification Center (Module 3 / Validation Area)
- **Product**: The Handover (Intelligent Project Knowledge Reconstruction & Handover Platform)
- **Creation Date**: 2026-11-13
- **Objective**: Provide an actionable, prioritized roadmap to resolve the findings identified in the comprehensive Verification Center audit, advance epistemic granularity, and prepare for frontend integration.

---

## 1. Remediation Priority Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       REMEDIATION & ADVANCEMENT PHASES                      │
│                                                                             │
│  [ Priority 1: Immediate Patch ]                                            │
│  - Fix `ollama_llm_model` attribute binding in `verification_ai.py`         │
│  - Correct HTTP 201 status assertion in audit runner script                 │
│                                                                             │
│  [ Priority 2: Epistemic Enhancement (Claim-Level Decomposition) ]          │
│  - Introduce atomic sub-claim extraction and tracking                       │
│  - Enable granular per-claim approve / reject states                        │
│                                                                             │
│  [ Priority 3: Frontend UI Implementation (Areas A, B, C) ]                 │
│  - Area A: Review Queue Screen (filtering, pagination, badges)              │
│  - Area B: Split-Pane Evidence Inspection & Conflict Viewer                 │
│  - Area C: Review Action Controls, Edit Drawer & Context Request Modals     │
│                                                                             │
│  [ Priority 4: Performance & Operational Hardening ]                        │
│  - Background worker dispatch for bulk re-assessment jobs                   │
│  - ChromaDB cross-project vector isolation verification                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Priority 1 — Immediate Patch (Zero Risk, Bug Fix)

### Task 1.1: Fix Default Settings Attribute Name in `verification_ai.py`
- **Location**: `backend/app/services/verification_ai.py` (Line 73)
- **Defect**: The method attempts to read `settings.ollama_model_reconstruction`, but the actual configuration setting in `backend/app/core/config.py` is `settings.ollama_llm_model` (or nested `settings.ollama.llm_model`).
- **Proposed Patch**:
  ```python
  # Change:
  model_name = (
      getattr(settings, "ollama_model_reconstruction", None)
      or getattr(getattr(settings, "ollama", None), "llm_model", "qwen3:8b")
  )
  # To:
  model_name = (
      getattr(settings, "ollama_llm_model", None)
      or getattr(getattr(settings, "ollama", None), "llm_model", None)
      or "qwen3:8b"
  )
  ```
- **Verification**: Run `backend/tests/run_verification_center_audit.py` to confirm test `QWEN-00` passes with default constructor instantiation.

### Task 1.2: Correct Test Assertion Status Code for `POST /request-context`
- **Location**: `backend/tests/run_verification_center_audit.py` (Line 1423)
- **Defect**: The test asserts `r7.status_code == 200`, but FastAPI's endpoint is decorated with `status_code=status.HTTP_201_CREATED`.
- **Proposed Patch**:
  ```python
  # Change:
  "PASS" if r7.status_code == 200 and ctx_req_id else "FAIL"
  # To:
  "PASS" if r7.status_code in (200, 201) and ctx_req_id else "FAIL"
  ```
- **Verification**: Ensures `API-07` reports `PASS` and `API-09` unblocks and executes cleanly.

---

## 3. Priority 2 — Claim-Level Assertion Decomposition (High Value)

### Problem Statement
Currently, a `VerificationCase` targets a whole `KnowledgeItem` (e.g. an architectural summary paragraph). If a finding contains three statements:
1. *"The application uses FastAPI on Python 3.11"* (True, backed by evidence).
2. *"PostgreSQL is used as the canonical database"* (True, backed by evidence).
3. *"Redis is used as the message broker"* (False, not supported by evidence).

A reviewer currently must either reject the entire finding or manually use `edit_finding()` to delete statement 3.

### Implementation Architecture
1. **Database Schema Addition**:
   - Create table `verification_claims`:
     - `id`: UUID (Primary Key)
     - `case_id`: UUID (Foreign Key -> `verification_cases.id` ON DELETE CASCADE)
     - `claim_index`: Integer
     - `claim_text`: Text (the atomic factual statement)
     - `claim_status`: String (`unverified`, `verified`, `rejected`, `unsupported`)
     - `supporting_chunk_id`: UUID (Foreign Key -> `evidence_chunks.id` nullable)
     - `confidence_score`: Float
2. **Qwen3 8B Extraction Pipeline**:
   - Instruct Qwen3 8B during knowledge extraction to emit an array of atomic propositions `claims: list[str]`.
3. **Review Actions**:
   - Add endpoint `PATCH /projects/{project_id}/verification/cases/{case_id}/claims/{claim_id}` allowing reviewers to individually toggle claim status without rewriting the entire finding payload.

---

## 4. Priority 3 — Frontend Review Screens Implementation (Area A, B, C)

In accordance with root `AGENTS.md` and the frontend stack (Next.js, React 19, TypeScript strict mode, Tailwind CSS v4, shadcn/ui, Lucide Icons):

### 4.1 Area A: Findings Awaiting Review Screen (`verification/page.tsx`)
- **Key Components**:
  - Summary Metrics Cards: Total cases, pending review, unresolved, verified, handover readiness percentage.
  - Filter Toolbar:
    - Domain dropdown (Decisions, Architecture, Tasks, Ownership, Dependencies, Risks, Procedures, Discussions).
    - Status pills (`All`, `Pending`, `Unresolved`, `Verified`, `Rejected`).
    - Severity chips (`Critical`, `High`, `Medium`, `Low`).
    - Assignee selector (`Unassigned`, `Assigned to me`, specific user).
  - Data Table:
    - Target title, Domain badge, Epistemic status, Machine assessment status, Priority icon, Issues count badge, Conflicts count badge, Last assessed timestamp.
    - Click row to navigate to Case Detail split view.

### 4.2 Area B: Supporting Evidence & Conflict Split-View (`verification/[caseId]/page.tsx`)
- **Left Panel (The Knowledge Finding)**:
  - Finding title, structured summary, domain, author/owner, timestamp.
  - Verbatim highlighted assertions mapped to cited chunks.
- **Center Panel (Side-by-Side Evidence Inspection)**:
  - Source provider badge (GitHub, Jira, Slack, Document).
  - Source URL link, external author, source created date.
  - Verbatim excerpt with matched text highlighting.
- **Right Panel (Conflict & Temporal Precedence Explorer)**:
  - Chronological timeline comparing Source A vs Source B.
  - Temporal badges: `SUPERSEDES`, `CONTRADICTS`, `CONSISTENT`.
  - AI Assistant Panel (Qwen3 8B):
    - "Why is there a conflict?": Displays `likely_cause` and `nuance_explanation`.
    - "Suggested Clarification Questions": Clickable questions to auto-populate context requests.

### 4.3 Area C: Human Review Action Controls & Drawers
- **Action Bar (Top / Bottom Fixed)**:
  - `Approve Finding`: Green button. Checks for open critical issues; triggers optimistic version-checked POST `/approve`.
  - `Reject Finding`: Red button. Opens dialog with mandatory rejection reason text field.
  - `Mark Unresolved`: Amber button. Opens dialog for explanation notes.
  - `Edit Finding`: Ghost button. Opens side drawer allowing inline modification of title, summary, and payload fields.
  - `Request Context`: Outline button. Opens drawer with team member selector, question input (pre-fillable from AI suggestions), and category tag.
- **Concurrency Conflict Handling**:
  - If a 409 `ConcurrencyConflictError` is returned, display an alert toast: *"This case was updated by another reviewer. The view has been refreshed with the latest changes."*

---

## 5. Priority 4 — Operational Hardening & Worker Dispatch

1. **Background Job Dispatch**:
   - Update `POST /projects/{project_id}/verification/assess` to support an `async_mode=true` parameter.
   - For bulk re-assessments (e.g., after syncing a new GitHub repository), queue a `VERIFICATION_ASSESSMENT` background job in PostgreSQL `background_jobs` table.
   - The standalone Python worker process will process the job without blocking API server threads.
2. **Periodic Re-Verification Cron**:
   - Implement scheduled checks to re-evaluate evidence staleness (`STALE_KNOWLEDGE`) every 24 hours for findings whose evidence items have crossed the 90-day threshold.

---

## 6. Action Item Checklist & Verification Gates

| Priority | Task | Target Date | Verification Check |
| :--- | :--- | :--- | :--- |
| **P1** | Fix `settings.ollama_llm_model` binding in `verification_ai.py` | Immediate | `backend/tests/run_verification_center_audit.py` passes `QWEN-00` |
| **P1** | Update audit test assertion for HTTP 201 Created | Immediate | `API-07` & `API-09` pass |
| **P2** | Design and migrate `verification_claims` table | Post-Approval | Alembic migration + claim-level unit tests |
| **P3** | Scaffold Next.js Verification Center route and layout | Frontend Phase | `frontend/src/app/(workspace)/verification/page.tsx` renders |
| **P3** | Implement Area A review queue table & summary cards | Frontend Phase | Queue displays live cases from FastAPI |
| **P3** | Implement Area B split-view evidence & conflict timeline | Frontend Phase | Side-by-side chunks render with diff markers |
| **P3** | Implement Area C review action controls & optimistic locking | Frontend Phase | Approve, reject, edit, and context requests execute cleanly |
| **P4** | Wire background worker dispatch for bulk assessment | Post-Frontend | Large batch assessment runs without HTTP timeout |
