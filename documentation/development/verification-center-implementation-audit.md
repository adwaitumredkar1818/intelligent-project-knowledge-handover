# Verification Center — Implementation Audit

**Platform**: The Handover (Intelligent Project Knowledge Reconstruction & Handover Platform)  
**Module**: Verification Center (Module 3 / Validation Area)  
**Audit Date**: November 13, 2026  
**Auditor**: Antigravity Platform Agent  
**Status**: Stage 1 Architecture & Capability Audit Completed

---

## 1. Executive Summary

The **Verification Center** is the mandatory, human-controlled quality gate between reconstructed knowledge (from **Knowledge Intelligence** and **Relationship Explorer**) and the downstream **Handover Workspace**.

### Core Governance Directive
> **AI EXTRACTS, ANALYSES AND RECOMMENDS. EVIDENCE GROUNDS IT. AUTHORISED HUMANS VALIDATE IT.**  
> A high confidence score is not proof of correctness. An AI-generated finding must never independently transition into verified knowledge. Handover eligibility requires explicit, auditable human sign-off.

This audit evaluates the current platform codebase against the 6 core responsibilities of the Verification Center:
1. **Evidence Verification**: Validating that every knowledge finding and relationship has valid, accessible, and grounded provenance.
2. **Conflict Detection**: Identifying contradictions across heterogeneous sources (Jira vs GitHub vs Documents vs Meeting Notes).
3. **Missing Information & Uncertainty Detection**: Surfacing unsupported statements, missing context, and ambiguous attributions.
4. **Duplicate & Freshness Detection**: Flagging duplicate records and detecting stale knowledge when source evidence changes.
5. **Human Review Workflow**: Providing an auditable review queue for authorised reviewers to approve, reject, edit, request context, or mark findings unresolved.
6. **Handover Readiness Gate**: Enforcing that only human-verified, accessible, and unblocked knowledge reaches downstream handover packages.

---

## 2. Capability Matrix & Detailed Audit Findings

| Capability | Existing Database Tables / Models | Existing Services / Components | Status | Gaps & Required Extensions |
| :--- | :--- | :--- | :---: | :--- |
| **1. Evidence Grounding & Provenance** | `evidence_items`, `evidence_contents`, `evidence_chunks`, `knowledge_evidence_links`, `relationship_evidence_links` | `KnowledgeCandidateValidator`, `EvidenceChunkRepository`, `ChunkingService` | **Complete and verified** | Verbatim excerpt checks and chunk validation exist. Need claim-level granular verification and dynamic re-verification when evidence is modified or deleted. |
| **2. Epistemic Separation** | `knowledge_items.epistemic_status` (`extracted`, `ai_interpreted`, `human_verified`) | `ReconstructionWorkerService` | **Complete and verified** | Schema strictly prevents LLM from emitting `human_verified`. Need atomic promotion to `human_verified` strictly via human reviewer actions. |
| **3. Verification Case Architecture** | *None* (only raw `review_status` on `knowledge_items` and `verification_status` on `knowledge_relationships`) | *None* | **Missing** | Must implement `verification_cases` to decouple assessment lifecycle, reviewer assignments, and optimistic concurrency from target rows. |
| **4. Verification Issue Registry** | *None* (issues stored as ad-hoc strings in `uncertainty_reason` or logs) | *None* | **Missing** | Must implement `verification_issues` with controlled taxonomy (`MISSING_EVIDENCE`, `CONFLICTING_SOURCES`, etc.), severities, and resolution states. |
| **5. Cross-Source Conflict Detection** | *None* (only status checks on Jira issues) | *None* | **Missing** | Must implement `verification_conflicts` table and `ConflictDetectionEngine` comparing status, ownership, decision, technical, and temporal assertions across sources. |
| **6. Duplicate Detection** | `knowledge_items.fingerprint`, `knowledge_relationships.fingerprint` | `KnowledgeCandidateValidator._compute_fingerprint` | **Implemented but incomplete** | Deterministic SHA-256 fingerprint deduplication works during extraction. Need cross-finding duplicate candidate generation and auditable supersession without destructive deletion. |
| **7. Freshness & Staleness Tracking** | `knowledge_items.is_stale`, `stale_reason`, `stale_detected_at`, `knowledge_relationships.is_stale` | `KnowledgeRepository.mark_stale_for_evidence` | **Implemented but incomplete** | Triggered on chunk replacement. Need proactive staleness checks when source documents are updated, revoked, or superseded by later decisions. |
| **8. Uncertainty Quantification** | `confidence_metadata_json`, `uncertainty_reason`, `match_score`, `confidence_components_json` | `KnowledgeCandidateValidator`, `RelationshipDiscoveryEngine` | **Complete and verified** | Multi-signal breakdown exists. Need structured multi-reason uncertainty taxonomy decoupled from raw confidence floats. |
| **9. Human Review Decision Workflow** | `knowledge_items.review_status` (`pending_review`, `approved`, `rejected`), `relationships.verification_status` | *None* (APIs allow only basic status patch) | **Implemented but incomplete** | Must implement dedicated, atomic review operations: `Approve`, `Reject`, `Edit`, `RequestContext`, `MarkUnresolved`, and `ReturnForCorrection`. |
| **10. Append-Only Review History** | `audit_logs` (general platform audit events) | `AuditService` | **Implemented but not integrated** | While system-wide audit logging exists in PostgreSQL, a dedicated `verification_review_events` table is required to track finding snapshots, diffs, and reviewer notes. |
| **11. Clarification & Context Requests** | *None* | *None* | **Missing** | Must implement `verification_context_requests` to enable reviewers to ask departing team members or technical leads for missing details. |
| **12. Handover Readiness Gate** | *None* | *None* | **Missing** | Must implement `HandoverEligibilityService` as a reusable backend gate that queries verified status, active source ACLs, and lack of unresolved blockers. |
| **13. Verification RBAC** | `roles`, `permissions`, `project_memberships` | `RbacService`, `rbac_catalog.py` (`project.knowledge.review`) | **Implemented but incomplete** | Need granular permissions: `project.verification.read`, `assess`, `review`, `approve`, `reject`, `edit`, `request_context`, `assign`, `admin`. |
| **14. Asynchronous Verification Worker** | `background_jobs`, `IndexingWorkerService`, `ReconstructionWorkerService`, `RelationshipWorkerService` | PostgreSQL job leasing loop | **Implemented but incomplete** | Need dedicated job types: `VERIFICATION_ASSESSMENT`, `CONFLICT_DETECTION`, and `FRESHNESS_CHECK` inside the worker pool. |

---

## 3. Existing Model & Schema Analysis

### 3.1 Knowledge Models (`backend/app/models/knowledge.py`)
- **`KnowledgeItem`**:
  - `epistemic_status`: Enforces `extracted`, `ai_interpreted`, `human_verified`.
  - `review_status`: `pending_review`, `approved`, `rejected`, `needs_clarification`.
  - `support_classification`: `direct`, `corroborated`, `interpretation`, `uncertain`.
  - `is_stale`, `stale_reason`, `stale_detected_at`, `superseded_by_id`.
  - `confidence_metadata_json`, `uncertainty_reason`.
  - *Observation*: Ready for integration. Does not currently reference a `VerificationCase` foreign key or hold version numbers for optimistic concurrency.
- **`KnowledgeEvidenceLink`**:
  - `support_type`: `direct`, `corroborated`, `interpretation`, `uncertain`, `contradiction`.
  - `supporting_excerpt`, `excerpt_verified`, `excerpt_match_mode`.
  - *Observation*: Robust verbatim grounding foundation. Excerpt verification occurs deterministically against `EvidenceChunk.chunk_text`.

### 3.2 Relationship Models (`backend/app/models/relationship.py`)
- **`KnowledgeRelationship`**:
  - `verification_status`: `candidate`, `verified`, `rejected`.
  - `confidence_score`, `confidence_components_json`, `discovery_method`.
  - `relationship_basis`: `explicit`, `inferred`.
  - `reviewed_by_user_id`, `reviewed_at`, `review_note`.
  - *Observation*: Graph edges are stored relationally in PostgreSQL. Relationship verification status is currently modified via simple updates rather than tracked cases.

### 3.3 RBAC Catalog (`backend/app/core/rbac_catalog.py`)
- Has `project.knowledge.review` assigned to `org_owner`, `org_admin`, and `reviewer`.
- Lacks granular verification actions such as `project.verification.approve`, `project.verification.edit`, `project.verification.request_context`.

---

## 4. Key Gaps to Bridge

1. **No First-Class Case Entity**: Findings and relationships are reviewed in place without a case abstraction, preventing multi-issue tracking, assignee routing, priority scoring, and optimistic concurrency versioning.
2. **Missing Conflict Table**: When contradictions occur (e.g., Jira says Closed, meeting notes say Blocked), the system has nowhere to record the conflicting claims, source timestamps, and reconciliation notes side-by-side.
3. **No Append-Only Audit of Human Edits**: Reviewer corrections to finding summaries or technical fields overwrite the existing values without recording the previous snapshot in an immutable review event log.
4. **Context Requests Undefined**: Reviewers have no mechanism to request additional documentation or explanations from the departing owner or project manager within the platform.
5. **Downstream Handover Gate Absent**: There is no barrier preventing a downstream report generator or assistant from querying unverified candidate items directly from `knowledge_items`.

---

## 5. Architectural Remediation & Next Steps

1. Create migration `20261113_0012_verification_center.py` implementing:
   - `verification_cases`
   - `verification_issues`
   - `verification_conflicts`
   - `verification_review_events`
   - `verification_context_requests`
2. Implement `VerificationIssueRegistry` with controlled issue taxonomy and detection rules.
3. Implement `DeterministicVerificationEngine` and `ConflictDetectionEngine`.
4. Integrate local `Qwen3 8B` for semantic contradiction explanation and missing context suggestion.
5. Implement `HumanReviewService` with atomic transactions, optimistic locking, and append-only event recording.
6. Implement `HandoverEligibilityService` as the definitive quality gate.
7. Implement `/api/v1/projects/{project_id}/verification/...` endpoints with RBAC and source ACL filtering.
8. Build comprehensive test suite verifying zero AI self-approval, conflict retention, and source security.
