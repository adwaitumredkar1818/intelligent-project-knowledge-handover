# Handover Workspace — Automated Testing Guide & Test Matrix

**Platform**: The Handover  
**Module**: Handover Workspace (Module 4 / Knowledge Transfer Area)  
**Status**: Implemented  
**Date**: 2026-11-13  

---

## 1. Test Architecture & Methodology

All automated tests for Handover Workspace execute in strict project-isolated contexts:
1. **Zero Contamination**: Test fixtures generate dedicated test organisations, test projects, test users, and distinct memberships.
2. **Ephemeral Contexts**: Clean-up hooks or distinct UUID namespaces prevent data cross-talk.
3. **Multi-Tenant Boundary Testing**: Access attempts by users belonging to different organisations or unassigned projects return `404 Not Found` (fail closed cloaking).
4. **End-to-End State Machine Traversal**: Tests verify every stage of the 14-state lifecycle from DRAFT through ACKNOWLEDGED and TRANSFERRED.

---

## 2. Test Matrix (Tests A through K & Edge Cases)

| Test ID | Test Category | Target Behavior | Expected Outcome |
| :--- | :--- | :--- | :--- |
| **TEST-A** | Case Creation | Create a HandoverCase in DRAFT status | 201 Created, version=1, initial status history record |
| **TEST-B** | Concurrency Control | Concurrent update with stale expected version | 409 Conflict, transaction rolled back |
| **TEST-C** | Assembly Engine | Deterministic compilation of 8 canonical domain sections | 201 Created, version_number=1, is_current=True, content hash calculated |
| **TEST-D** | Downstream Eligibility | Ensure unverified or ungrounded knowledge is excluded | Excluded items tracked in snapshot; eligible items linked via `HandoverContentLink` |
| **TEST-E** | 9-Category Readiness | Evaluate evidence, verification, conflicts, freshness, etc. | 200 OK, score 0-100, readiness level, blockers & warnings populated |
| **TEST-F** | Dynamic Checklists | Generate pre-handover, knowledge-transfer, access revocation lists | 201 Created, checklist items linked, item completion status updates |
| **TEST-G** | Responsibility Mapping | Map departing member duties to successor | 201 Created, items listable and updatable |
| **TEST-H** | Three-Phase Sign-Off | Phase 1 (departing) -> Phase 2 (reviewer approval) -> Phase 3 (successor) | 201 Created, cryptographic signature hash stored, status transitions verified |
| **TEST-I** | Separation of Duties | Departing member attempts to approve package as reviewer | 403 Forbidden, security event logged |
| **TEST-J** | Package Delivery | Release approved package to successor | 201 Created, delivery record active, status -> DELIVERED |
| **TEST-K** | Successor Receipt | Successor confirms delivery receipt | 201 Created, acknowledgement hash stored, status -> ACKNOWLEDGED |
| **TEST-L** | Ownership Transfer | Explicit project ownership transfer post-acknowledgement | 201 Created, status -> TRANSFERRED, responsibilities marked completed |
| **TEST-M** | Transfer Rollback | Rollback an ownership transfer with reason | 200 OK, rolled_back=True, rollback reason logged |
| **TEST-N** | AI Narrative Drafting | Generate draft text for a section based on linked findings | 200 OK, draft text returned, zero ungrounded hallucinations |
