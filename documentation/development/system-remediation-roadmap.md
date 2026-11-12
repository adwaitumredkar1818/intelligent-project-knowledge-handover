# System Remediation Roadmap — The Handover Platform

**Product**: The Handover — Intelligent Project Knowledge Reconstruction & Handover Platform  
**Date**: November 13, 2026  
**Auditor**: Antigravity System Audit Agent  
**Goal**: Prioritized technical remediation plan to transition all components from Audit status to full Production Readiness.

---

## 1. Prioritization Framework

Remediations are organized into four sequential tiers based on architectural criticality:

```text
TIER 1 (Immediate Stability & Code Hygiene)
     │
     ▼
TIER 2 (Schema Integrity & Type Safety)
     │
     ▼
TIER 3 (Phase 2.7 Cross-Source Intelligence Implementation)
     │
     ▼
TIER 4 (External Source OAuth & Cloud Storage Provisioning)
```

---

## 2. Remediation Work Items

### Tier 1: Immediate Stability & Code Hygiene (Effort: 0.5 Days)
- [x] **Unwrap API Response Envelopes**: Added `unwrapList` helper in `frontend/src/lib/api.ts` to cleanly handle `{ items: [...] }` backend responses. *(Completed)*
- [x] **Add Missing Source Connection API Route**: Implemented `GET /api/v1/organisations/{organisation_id}/sources` in `backend/app/api/routes/sources.py`. *(Completed)*
- [x] **Inline Organization Creation in Project Modal**: Enabled organization creation from within the project creation flow when 0 organizations exist. *(Completed)*
- [ ] **Fix Missing `typing.Any` Import in Background Worker**: Add `from typing import Any` to `backend/app/worker.py:39`.
- [ ] **Enhance GLM OCR Repetition Pruning**: Augment `backend/app/services/ocr.py` post-processor to automatically trim runaway repetitive punctuation sequences (e.g. `---`, `===`) from OCR text output.
- [ ] **Clean Up Frontend Lint Warnings**: Replace `(err: any)` in catch blocks with typed `unknown` error handlers across `frontend/src/lib/api.ts` and modal components.

### Tier 2: Schema Integrity & Type Safety (Effort: 1 Day)
- [ ] **Resolve Alembic Schema Drift**:
  - Update `backend/app/models/workspace.py` to declare `source_scope = Column(postgresql.JSONB)` to match the canonical PostgreSQL column type.
  - Update `backend/app/models/vector_index.py` index name to match `ix_project_vector_indexes_org`.
  - Re-run `alembic check` to verify zero drift.
- [ ] **Address Mypy Typing Discrepancies**:
  - Annotate untyped parameters in `backend/app/api/routes/sources.py`.
  - Ensure `verify_password` input handling in `backend/app/services/auth.py` handles `str | None` defensively.
  - Ensure `app/api/deps.py` principal resolution strictly passes UUIDs.

### Tier 3: Phase 2.7 Cross-Source Intelligence (Effort: 2 Days)
- [ ] **Build Cross-Source Deduplication & Synthesis Service**:
  - Implement `CrossSourceIntelligenceService` in `backend/app/services/cross_source.py`.
  - Ingest entities, commits, PRs, Jira issues, and document findings to correlate common identifiers (e.g. Jira issue keys in Git commit messages).
  - Implement conflict detection heuristics across sources (e.g. conflicting task statuses or decision outcomes).
- [ ] **Integrate Cross-Source Synthesis into Background Worker**:
  - Register `CrossSourceWorkerService` in `backend/app/worker.py` to periodically evaluate correlated project evidence.

### Tier 4: External OAuth & Cloud Integrations (Effort: Ongoing / User-Gated)
- [ ] **GitHub OAuth Application Setup**:
  - When user provides `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`, activate full 3-legged OAuth flow alongside the currently working Personal Access Token (PAT) mode.
- [ ] **Jira Cloud OAuth 2.0 (3LO) Setup**:
  - Configure Atlassian Developer Console app credentials in `.env` to enable team-wide delegated Jira authorization.
- [ ] **Slack App OAuth Setup**:
  - Configure Slack App Bot Token (`xoxb-`) or OAuth v2 credentials to enable real-time channel sync.
- [ ] **Supabase Auth & Storage Cloud Activation**:
  - When user sets `SUPABASE_ENABLED=true` with valid Supabase URL, service role key, and JWT secret, switch platform authentication from local FastAPI JWT to Supabase Auth and object storage to `project-evidence` bucket.

---

## 3. Verification & Acceptance Criteria

Each remediation step must satisfy:
1. `pytest -q` passes 100% of unit, integration, and security tests.
2. `ruff check .` reports 0 errors.
3. `mypy app` passes in strict mode.
4. `npm run typecheck` and `npm run build` pass with 0 errors.
5. All 27 components classified as `PASS` or cleanly `NOT CONFIGURED` with explicit user guidance.
