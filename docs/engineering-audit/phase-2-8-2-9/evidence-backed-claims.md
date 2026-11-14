# Phase 2.8 Audit: Evidence-Backed Claims & Gatekeeping

**Document**: `docs/engineering-audit/phase-2-8-2-9/evidence-backed-claims.md`  
**Phase**: Phase 2.8 — Verification & Handover Engine  
**Status**: APPROVED & VERIFIED  

---

## 1. Executive Summary

A critical architectural mandate of **The Handover** is that no unsupported claim can enter an official handover package. The **Handover Eligibility Gatekeeper** (`HandoverEligibilityService` in `backend/app/services/handover_eligibility.py`) acts as a strict firewall between reconstructed candidates and compiled packages.

---

## 2. Gatekeeping Rules & Test Evidence

In `backend/tests/run_verification_center_audit.py`, four critical security tests verify this gate:

| Test ID | Scenario | Expected Behavior | Observed Result |
| :--- | :--- | :--- | :--- |
| `GATE-01` | Candidate finding in `PENDING_REVIEW` state | Blocked from handover inclusion | **PASS** (`is_eligible = False`) |
| `GATE-02` | Candidate finding in `REJECTED` state | Blocked from handover inclusion | **PASS** (`is_eligible = False`) |
| `GATE-03` | Candidate finding transitioned to `APPROVED` by human auditor | Approved for handover inclusion | **PASS** (`is_eligible = True`) |
| `GATE-04` | Finding verified, but supporting source revoked or restricted by ACL | Fail-closed exclusion | **PASS** (`is_eligible = False, reason = 'source_acl_denied'`) |

---

## 3. Provenance & Excerpt Integrity

Every claim linked into a handover section preserves:
- The canonical `knowledge_item_id` and supporting `evidence_chunk_ids`.
- The source document/repository identifier and verbatim content snippet.
- The timestamp of original creation and extraction.
- The human reviewer identity and approval timestamp.
