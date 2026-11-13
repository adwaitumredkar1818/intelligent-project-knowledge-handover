# Knowledge Intelligence Module — Remediation & Integration Plan

**Product**: The Handover  
**Module**: Knowledge Intelligence (Module 3)  
**Target Milestone**: Integration Readiness (Connecting Verified Backend to Next.js Frontend)  
**Audit Baseline Status**: **FUNCTIONALLY COMPLETE** (Backend Core Verified, UI Pending)

---

## 1. Prioritized Remediation Roadmap

Based on the findings from `knowledge-intelligence-audit.md` and `knowledge-intelligence-test-results.md`, the remaining tasks are structured into three distinct priority tiers:

```
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│  P0: Infrastructure    │ ──▶  │  P1: Frontend UI       │ ──▶  │  P2: Performance & UX  │
│  ChromaDB Container    │      │  Domain Hub & Timeline │      │  GPU Batch Scheduling  │
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘
```

---

## 2. Priority 0 (P0) — Infrastructure: ChromaDB Container Verification

### Problem Description
ChromaDB HTTP vector store on port 8001 returned a connection timeout because the Docker Desktop daemon was not running during the test run. While the backend's `HybridRetrievalService` gracefully falls back to PostgreSQL full-text search (`tsvector`), optimal hybrid semantic retrieval requires the ChromaDB container to be active.

### Proposed Action Items
1. Verify Docker Compose configuration in `infrastructure/docker/docker-compose.yml`:
   ```bash
   docker compose up -d chroma
   ```
2. Validate HTTP heartbeat endpoint:
   ```bash
   curl http://localhost:8001/api/v2/heartbeat
   ```
3. Run verification test ensuring `HybridRetrievalService` operates in full `hybrid` mode without setting `degraded=True`.

---

## 3. Priority 1 (P1) — Frontend UI Implementation for Knowledge Intelligence

### Problem Description
Currently, `frontend/src/app/knowledge/page.tsx` renders the `Phase2ModuleView` placeholder component. The backend provides 7 fully functional endpoints under `/api/v1/projects/{project_id}/knowledge-intelligence/` that must be connected to an interactive UI.

### Proposed Architecture & Component Structure
```
frontend/src/
  ├── app/
  │   └── knowledge/
  │       └── page.tsx                     # Main Knowledge Intelligence hub
  ├── components/knowledge/
  │   ├── KnowledgeHeader.tsx              # Executive summary cards & readiness score
  │   ├── DomainTabs.tsx                   # 8 Canonical domain selector tabs
  │   ├── DomainCoverageGrid.tsx           # Coverage % and confidence meters per domain
  │   ├── FindingsTable.tsx                # Filterable list of reconstructed findings
  │   ├── FindingDetailDrawer.tsx          # Full finding payload, verbatim excerpts & citations
  │   ├── TimelineView.tsx                 # Chronological project events with precision badges
  │   └── ExtractionTriggerModal.tsx       # Trigger new extraction run across evidence
  └── lib/
      └── api/
          └── knowledge.ts                 # Typed API client bindings for the 7 endpoints
```

### Key UI Features to Implement:
1. **Executive Telemetry Banner**: Displays Total Findings, Verified %, Pending Verification, and Overall Readiness Score from `GET /summary`.
2. **Eight Domain Tabs**: Clean navigation tabs with item count pills for each of the 8 canonical domains.
3. **Filterable Findings Table**:
   - Status filters (`accepted`, `proposed`, `in_progress`, etc.)
   - Epistemic status badges (`extracted` in blue, `ai_interpreted` in purple, `human_verified` in green)
   - Search by keyword/person.
4. **Three-Panel Evidence Drawer**:
   - Clicking a finding opens a slide-over drawer showing the structured JSON payload, uncertainty notes, and exact highlighted verbatim excerpt from original chunk evidence.
5. **Interactive Project Timeline**:
   - Visual vertical stream with event icons (`decision_accepted`, `work_completed`, `risk_reported`, `deployment`), source provider tags (GitHub, Jira, Document), and timestamp precision indicators (`second` vs `day`).

---

## 4. Priority 2 (P2) — Performance Tuning & Inference Scheduling

### Problem Description
Qwen3 8B inference on the RTX 4050 Laptop GPU (6GB VRAM) requires between 22s and 75s per domain chunk. While this is expected for an 8B model on consumer hardware, user experience requires proactive optimizations.

### Proposed Action Items
1. **Background Job Progress Polling**:
   - Expose granular step reporting (`extracting_domain_1_of_8`, `validating_candidates`) in `KnowledgeExtractionRun` so the frontend displays an animated step-by-step progress bar rather than a static spinner.
2. **Selective Domain Extraction**:
   - Allow users to trigger extraction for a specific domain (e.g., extracting only `DECISIONS_RATIONALE` or `RISKS_BLOCKERS_QUESTIONS`) rather than requiring an all-domain sweep.
3. **Ollama Context Window Optimization**:
   - Benchmark Qwen3 8B with `num_ctx=4096` instead of `8192` for short chunks to reduce prompt evaluation latency by ~20%.

---

## 5. Implementation Gate & Approval

In strict accordance with the **Audit-First Directive** and `AGENTS.md`:
- **NO application code or frontend modifications will be executed until the user reviews this audit report and explicitly approves the implementation plan.**
- Upon user authorization, implementation will proceed systematically through P0 and P1.
