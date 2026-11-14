# Phase 2.8 Audit: Handover Workspace & Generation Engine

**Document**: `docs/engineering-audit/phase-2-8-2-9/handover-workspace.md`  
**Phase**: Phase 2.8 — Verification & Handover Engine  
**Status**: APPROVED & VERIFIED (24/24 Audit Tests Passed, Frontend Workspace Integrated)  

---

## 1. Executive Summary

The **Handover Workspace** transforms verified project knowledge into structured, role-specific, auditable handover packages. It provides transition case tracking, deterministic 8-domain assembly, multi-party role sign-offs (Outgoing Owner, Incoming Successor, Reviewer), and markdown/JSON export capabilities.

---

## 2. Handover Case Lifecycle & Concurrency Control

Handover cases transition through a deterministic lifecycle:
```text
DRAFT ──▶ ASSEMBLED ──▶ IN_REVIEW ──▶ SIGNED_OFF ──▶ PUBLISHED ──▶ COMPLETED
```
- **Optimistic Concurrency**: Tested in `TEST-B`, updates fail with HTTP 409 Conflict if `expected_version` does not match the active `version` in PostgreSQL.
- **Rollback Safeguards**: Ownership transfers can be rolled back to historical maintainers with required audit justifications (`TEST-M`).

---

## 3. Deterministic 8-Domain Assembly & Cryptographic Integrity

When `POST /projects/{id}/handover/cases/{id}/assemble` is invoked, the `HandoverAssemblyService`:
1. Gathers all human-verified knowledge items linked to the project.
2. Filters out any item whose underlying evidence is restricted by source-level ACL for the assembly actor.
3. Groups items into the 8 canonical domains: Overview & Context, Decisions & Rationale, Technical Architecture, Work Progress, Ownership & Maintainers, Dependencies & Blockers, Risks & Issues, and Operational Runbooks.
4. Generates a SHA-256 package content hash (`package_hash`) sealing the assembled package version.

---

## 4. Multi-Party Sign-Off & Successor Acknowledgement

- Handover cases require designated sign-off roles:
  - `OUTBOUND_LEAD`
  - `INBOUND_SUCCESSOR`
  - `AUDIT_REVIEWER`
- Successors review project context, inspect supporting evidence, raise clarification questions, and explicitly record sign-off.
- The system distinguishes between **Factual Verification** (conducted by reviewers in Verification Center) and **Receipt Acknowledgement** (conducted by successors in Handover Workspace).
