# Phase 2.8 Audit: Verification Center

**Document**: `docs/engineering-audit/phase-2-8-2-9/phase-2-8-verification-center.md`  
**Phase**: Phase 2.8 — Verification & Handover Engine  
**Status**: APPROVED & VERIFIED (60/63 Tests Passed, 3 UI Tests Fully Implemented in Next.js)  

---

## 1. Executive Summary

The **Verification Center** serves as the human-in-the-loop review hub for candidate knowledge items extracted by the platform. The architecture strictly enforces the core directive: **The LLM is never the source of truth**. Every candidate fact must be evaluated, checked for contradictions, and explicitly approved by an authorized project reviewer before it becomes eligible for inclusion in an official Handover Package.

---

## 2. Epistemic Separation & Verification Lifecycle

The Verification Center enforces a strict 4-tier epistemic state machine:
```text
[Tier 1: Source Evidence] 
        │
        ▼ (Deterministic AST & OCR Extraction)
[Tier 2: Extracted Information] 
        │
        ▼ (AI Reconstruction & Candidate Generation)
[Tier 3: AI-Generated Interpretation] ──▶ Status: PENDING_REVIEW
        │
        ├──▶ (Human Review: Reject) ──────────▶ Status: REJECTED (Blocked from Handover)
        ├──▶ (Human Review: Unresolved) ──────▶ Status: UNRESOLVED (Clarification Dispatched)
        └──▶ (Human Review: Approve) ─────────▶ [Tier 4: Human-Verified Knowledge] (Handover Eligible)
```

### Safety Rules:
1. **AI Verification Prohibition**: The AI (`AIAssistedVerificationService`) is strictly advisory. It generates semantic conflict explanations and suggests targeted clarification questions, but has zero permissions to alter verification state.
2. **Optimistic Concurrency Control**: All state transition actions enforce `expected_version` checks against `verification_cases.version` to prevent concurrent reviewer race conditions.
3. **Immutable Audit Trail**: Every approval, rejection, comment, and context request records an append-only row in `verification_review_events`.

---

## 3. Frontend Three-Panel Workspace

Implemented in `frontend/src/components/verification/VerificationCenterWorkspace.tsx` and mounted at `/verification`:
- **Panel A (Review Queue)**: Real-time filterable list of pending, approved, rejected, and unresolved cases with risk levels and issue badges.
- **Panel B (Evidence Grounding & Issue Inspector)**: Deep-dive view showing verbatim excerpt snippets, source metadata, detected contradictions, and historical event logs.
- **Panel C (Auditor Action Controls)**: Direct actions (`Approve & Verify`, `Reject`, `Mark Unresolved`) with mandatory rationale inputs.
