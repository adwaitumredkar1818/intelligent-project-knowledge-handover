# Verification Center — Implementation Plan

**Platform**: The Handover (Intelligent Project Knowledge Reconstruction & Handover Platform)  
**Module**: Verification Center (Module 3 / Validation Area)  
**Author**: Antigravity Platform Agent  
**Date**: November 13, 2026  
**Status**: Ready for Implementation (Stage 2+)

---

## 1. System Architecture & Workflow

The **Verification Center** operates as a continuous evaluation engine and human review queue. It connects upstream reconstructed findings (**Knowledge Intelligence**) and relational edges (**Relationship Explorer**) with downstream consumption (**Handover Workspace**).

```text
┌─────────────────────────┐     ┌────────────────────────┐
│  Knowledge Intelligence │     │  Relationship Explorer │
│  (8 Canonical Domains)  │     │   (Graph Entities/     │
└────────────┬────────────┘     │       Edges)           │
             │                  └───────────┬────────────┘
             ▼                              ▼
  ┌─────────────────────────────────────────────────────┐
  │         VERIFICATION PREFLIGHT & ROUTER             │
  │   - Resolve project/org scope                       │
  │   - Validate source ACLs & evidence availability    │
  │   - Check existing open verification case           │
  └──────────────────────────┬──────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │        DETERMINISTIC VERIFICATION ENGINE            │
  │   - Provenance & Excerpt Verbatim Check             │
  │   - Source Reference & URL Consistency             │
  │   - Freshness & Staleness Rules                     │
  │   - Exact Fingerprint & ID Deduplication            │
  │   - Status Consistency (Jira vs Git Commits)        │
  └──────────────────────────┬──────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │        CONFLICT & UNCERTAINTY DETECTION             │
  │   - Structured Cross-Source Inconsistency Check     │
  │   - Multi-Signal Uncertainty Quantification         │
  │   - Semantic Comparison via Ollama/Qwen3 8B         │
  │   - Side-by-side Contradiction Record Generation    │
  └──────────────────────────┬──────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │             VERIFICATION CASE & QUEUE               │
  │   - Case Status: Candidate | Pending Review |       │
  │                  Conflicted | Unresolved            │
  │   - Prioritization & Reviewer Routing               │
  └──────────────────────────┬──────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │            HUMAN REVIEW ACTIONS (ATOMIC)            │
  │   ┌───────────┐ ┌──────────┐ ┌──────────────────┐   │
  │   │  APPROVE  │ │  REJECT  │ │   EDIT FINDING   │   │
  │   └─────┬─────┘ └────┬─────┘ └────────┬─────────┘   │
  │   ┌─────┴─────┐ ┌────┴─────┐ ┌────────┴─────────┐   │
  │   │  REQUEST  │ │   MARK   │ │    RETURN FOR    │   │
  │   │  CONTEXT  │ │UNRESOLVED│ │    CORRECTION    │   │
  │   └───────────┘ └──────────┘ └──────────────────┘   │
  │   - Optimistic concurrency version check            │
  │   - Append-only review history & audit event        │
  │   - Promote to EpistemicStatus.HUMAN_VERIFIED       │
  └──────────────────────────┬──────────────────────────┘
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │             HANDOVER ELIGIBILITY GATE               │
  │   - HandoverEligibilityService                      │
  │   - Blocks unapproved, stale, or revoked knowledge  │
  └─────────────────────────────────────────────────────┘
```

---

## 2. Verification Issue Taxonomy

All verification assessments evaluate candidate records against a central, extensible taxonomy:

| Identifier | Category | Default Severity | Trigger Condition |
| :--- | :--- | :---: | :--- |
| `MISSING_EVIDENCE` | Provenance | `CRITICAL` | Finding or relationship has 0 cited evidence links or cited evidence ID does not exist in the database. |
| `INVALID_SOURCE_REFERENCE` | Provenance | `HIGH` | Cited chunk ID does not belong to cited evidence item, or evidence is not in project workspace. |
| `UNSUPPORTED_CLAIM` | Grounding | `HIGH` | Cited supporting excerpt cannot be matched verbatim (or normalized whitespace) in chunk text. |
| `CONFLICTING_SOURCES` | Consistency | `HIGH` | Two accessible sources assert mutually incompatible facts (e.g. Jira status `Resolved` vs technical note `Pending`). |
| `INCONSISTENT_STATUS` | Consistency | `MEDIUM` | Finding status contradicts latest observed commit, PR, or Jira issue status. |
| `OUTDATED_INFORMATION` | Freshness | `MEDIUM` | Supporting evidence was modified or superseded by a later document/decision since extraction. |
| `STALE_KNOWLEDGE` | Freshness | `HIGH` | Source connection was revoked or deleted, rendering cited evidence inaccessible. |
| `DUPLICATE_RECORD` | Uniqueness | `MEDIUM` | Multiple findings share identical semantics or normalize to the same entity/decision fingerprint. |
| `UNCERTAIN_RELATIONSHIP` | Relational | `LOW` | Edge basis is purely inferred via semantic similarity without direct ID reference. |
| `INVALID_ENTITY_MAPPING` | Relational | `HIGH` | Relationship target entity does not match the required entity type for the relationship type. |
| `INCORRECT_ATTRIBUTION` | Attribution | `MEDIUM` | Owner/person attributed in finding does not match Jira assignee, git commit author, or meeting attendee. |
| `MISSING_SOURCE_CONTEXT` | Completeness | `LOW` | Finding omits critical domain context (e.g. decision rationale, risk mitigation, or API method). |
| `INSUFFICIENT_INFORMATION`| Completeness | `MEDIUM` | Available evidence is insufficient for human sign-off without additional clarification. |
| `INCOMPLETE_TRACEABILITY` | Traceability | `LOW` | Decision chain has gaps between decision, Jira work item, PR, and commit. |

---

## 3. Database Architecture (Migration `0012_verification_center.py`)

### 3.1 `verification_cases`
- `id`: UUID (Primary Key, default `uuid4`)
- `organisation_id`: UUID (FK `organisations.id`, CASCADE)
- `project_id`: UUID (FK `projects.id`, CASCADE)
- `target_type`: String(32) (`'knowledge_item'`, `'relationship'`)
- `target_id`: UUID (Polymorphic ID matching `knowledge_items.id` or `knowledge_relationships.id`)
- `case_status`: String(32) (`candidate`, `pending_review`, `verified`, `conflicted`, `rejected`, `unresolved`, `archived`)
- `machine_assessment_status`: String(32) (`passed`, `issues_detected`, `conflict_detected`, `uncertain`, `insufficient_evidence`)
- `priority`: String(16) (`critical`, `high`, `medium`, `low`)
- `assigned_reviewer_id`: UUID (FK `users.id`, SET NULL, nullable)
- `machine_assessment_json`: JSONB (Structured metrics, AI recommendations, uncertainty notes)
- `version`: Integer (Default 1, increments on every review action for optimistic locking)
- `last_assessed_at`: DateTime(timezone=True)
- `last_reviewed_at`: DateTime(timezone=True)
- `resolved_at`: DateTime(timezone=True)
- `created_at`: DateTime(timezone=True, default `func.now()`)
- `updated_at`: DateTime(timezone=True, default `func.now()`)
- *Constraints*: Unique active case per target: `UNIQUE (project_id, target_type, target_id) WHERE case_status != 'archived'`.

### 3.2 `verification_issues`
- `id`: UUID (Primary Key, default `uuid4`)
- `organisation_id`: UUID (FK `organisations.id`, CASCADE)
- `project_id`: UUID (FK `projects.id`, CASCADE)
- `case_id`: UUID (FK `verification_cases.id`, CASCADE)
- `issue_type`: String(64) (`MISSING_EVIDENCE`, `CONFLICTING_SOURCES`, etc.)
- `severity`: String(16) (`critical`, `high`, `medium`, `low`, `info`)
- `description`: Text
- `detection_method`: String(32) (`deterministic_rule`, `ai_assisted`, `freshness_check`, `cross_source_matcher`)
- `details_json`: JSONB (Signal breakdown, conflicting claim texts, expected citations)
- `conflicting_evidence_id`: UUID (FK `evidence_items.id`, SET NULL, nullable)
- `conflicting_chunk_id`: UUID (FK `evidence_chunks.id`, SET NULL, nullable)
- `resolution_state`: String(32) (`open`, `resolved`, `dismissed`, `acknowledged`)
- `resolution_reason`: Text (nullable)
- `resolved_by_user_id`: UUID (FK `users.id`, SET NULL, nullable)
- `resolved_at`: DateTime(timezone=True, nullable)
- `created_at`: DateTime(timezone=True, default `func.now()`)
- `updated_at`: DateTime(timezone=True, default `func.now()`)

### 3.3 `verification_conflicts`
- `id`: UUID (Primary Key, default `uuid4`)
- `organisation_id`: UUID (FK `organisations.id`, CASCADE)
- `project_id`: UUID (FK `projects.id`, CASCADE)
- `case_id`: UUID (FK `verification_cases.id`, CASCADE)
- `conflict_type`: String(32) (`status_conflict`, `ownership_conflict`, `decision_conflict`, `technical_conflict`, `temporal_conflict`, `relationship_conflict`)
- `claim_a_text`: Text
- `claim_a_source_evidence_id`: UUID (FK `evidence_items.id`, CASCADE)
- `claim_a_chunk_id`: UUID (FK `evidence_chunks.id`, SET NULL, nullable)
- `claim_a_source_timestamp`: DateTime(timezone=True, nullable)
- `claim_b_text`: Text
- `claim_b_source_evidence_id`: UUID (FK `evidence_items.id`, CASCADE)
- `claim_b_chunk_id`: UUID (FK `evidence_chunks.id`, SET NULL, nullable)
- `claim_b_source_timestamp`: DateTime(timezone=True, nullable)
- `explanation`: Text
- `temporal_comparison`: String(32) (`simultaneous`, `b_supersedes_a`, `a_supersedes_b`, `ambiguous`)
- `resolution_state`: String(32) (`unresolved`, `reconciled`, `superseded`, `dismissed`)
- `resolution_notes`: Text (nullable)
- `resolved_by_user_id`: UUID (FK `users.id`, SET NULL, nullable)
- `resolved_at`: DateTime(timezone=True, nullable)
- `created_at`: DateTime(timezone=True, default `func.now()`)

### 3.4 `verification_review_events`
- `id`: UUID (Primary Key, default `uuid4`)
- `organisation_id`: UUID (FK `organisations.id`, CASCADE)
- `project_id`: UUID (FK `projects.id`, CASCADE)
- `case_id`: UUID (FK `verification_cases.id`, CASCADE)
- `reviewer_user_id`: UUID (FK `users.id`, CASCADE)
- `action`: String(32) (`approve`, `reject`, `edit`, `request_context`, `mark_unresolved`, `return_for_correction`, `assign`)
- `previous_status`: String(32)
- `new_status`: String(32)
- `review_notes`: Text (nullable)
- `finding_patch_json`: JSONB (nullable, record of corrections)
- `previous_snapshot_json`: JSONB (nullable)
- `new_snapshot_json`: JSONB (nullable)
- `correlation_id`: String(64)
- `created_at`: DateTime(timezone=True, default `func.now()`)

### 3.5 `verification_context_requests`
- `id`: UUID (Primary Key, default `uuid4`)
- `organisation_id`: UUID (FK `organisations.id`, CASCADE)
- `project_id`: UUID (FK `projects.id`, CASCADE)
- `case_id`: UUID (FK `verification_cases.id`, CASCADE)
- `requested_by_user_id`: UUID (FK `users.id`, CASCADE)
- `requested_from_user_id`: UUID (FK `users.id`, CASCADE)
- `question`: Text
- `requested_information_type`: String(64) (`decision_rationale`, `ownership_confirmation`, `task_status_clarification`, `technical_context`, `operational_runbook`, `other`)
- `status`: String(32) (`pending`, `responded`, `cancelled`, `expired`)
- `response_text`: Text (nullable)
- `response_evidence_id`: UUID (FK `evidence_items.id`, SET NULL, nullable)
- `responded_at`: DateTime(timezone=True, nullable)
- `created_at`: DateTime(timezone=True, default `func.now()`)
- `updated_at`: DateTime(timezone=True, default `func.now()`)

---

## 4. Verification Engine Architecture & Services

### 4.1 `DeterministicVerificationEngine`
1. **Provenance Validation**:
   - Ensures `evidence_id` exists, belongs to project, has not been deleted (`deleted_at IS NULL`).
   - Ensures `evidence_chunk_id` exists and points to `evidence_id`.
   - Validates that `supporting_excerpt` is present in `chunk_text`.
2. **Freshness & Staleness Detection**:
   - Flags finding as `OUTDATED_INFORMATION` if `evidence.source_updated_at > finding.source_observed_at`.
   - Flags finding as `STALE_KNOWLEDGE` if evidence status is `failed` or deleted.
3. **Duplicate Detection**:
   - Detects exact duplicates via SHA-256 fingerprint.
   - Computes normalized title/owner overlap for near-duplicate candidate generation.
4. **Relational Constraints**:
   - Validates entity endpoints on relationships (`source_entity_id`, `target_entity_id`).
   - Flags inferred edges (`relationship_basis == 'inferred'`) as `UNCERTAIN_RELATIONSHIP`.

### 4.2 `ConflictDetectionEngine`
1. **Status Conflicts**:
   - Compares Jira issue status (e.g. `Closed`/`Done`) with Git commits, PRs, or meeting notes asserting in-progress work.
2. **Ownership Conflicts**:
   - Identifies conflicting owners for the same component or task across different documents.
3. **Decision Conflicts**:
   - Compares conflicting architecture decisions (e.g. JWT rotation vs static tokens) across multiple design documents.
4. **Temporal Reasoning**:
   - Evaluates source timestamps: if document B is strictly newer than document A, annotates `temporal_comparison = 'b_supersedes_a'` rather than an irresolvable deadlock.

### 4.3 `AIAssistedVerificationService`
- Leverages local `qwen3:8b` via existing `OllamaLLMClient`.
- Restricted strictly to:
  - Explaining the nuance of complex semantic contradictions.
  - Suggesting missing context or unanswered technical questions.
  - Generating suggested reconciliation summaries.
- **Strict Prohibition**: The LLM is NEVER called to approve or reject a finding. Its output is persisted into `machine_assessment_json` only.

### 4.4 `HumanReviewService`
Coordinates review actions inside atomic database transactions:
- **`approve(case_id, user_id, review_notes, expected_version)`**:
  - Re-verifies reviewer has `project.knowledge.review` permission.
  - Validates `case.version == expected_version` (prevents lost updates).
  - Verifies that NO unresolved `CRITICAL` issues exist.
  - Updates `verification_cases.case_status = 'verified'`.
  - Updates `knowledge_items.review_status = 'approved'`, `epistemic_status = 'human_verified'`.
  - Writes to `verification_review_events`.
  - Emits immutable PostgreSQL audit log event `knowledge.verified`.
- **`reject(case_id, user_id, reason, review_notes, expected_version)`**:
  - Updates case status to `'rejected'`.
  - Updates `knowledge_items.review_status = 'rejected'`.
  - Writes review event and audit log.
- **`edit_finding(case_id, user_id, patch_data, reason, expected_version)`**:
  - Saves current state into `previous_snapshot_json`.
  - Applies edits to finding title/summary/payload.
  - Increments version; appends review event.
- **`request_context(case_id, reviewer_id, target_user_id, question, info_type)`**:
  - Creates `verification_context_requests` record.
  - Updates case status to `'unresolved'` or maintains `'pending_review'` with context pending indicator.
- **`mark_unresolved(case_id, user_id, explanation, expected_version)`**:
  - Sets case status to `'unresolved'`.

### 4.5 `HandoverEligibilityService`
- Exposes: `check_eligibility(project_id: UUID, knowledge_item_id: UUID, viewer_user_id: UUID) -> HandoverEligibilityResult`
- **Eligibility Criteria (All must hold)**:
  1. `knowledge_item.review_status == 'approved'`
  2. `knowledge_item.epistemic_status == 'human_verified'`
  3. `knowledge_item.is_stale == False`
  4. `knowledge_item.is_deleted == False`
  5. Current viewing user has delegated read access to all cited supporting evidence (via `SourceAccessPolicyService`).
  6. Associated `verification_case` has no unresolved `CRITICAL` or `HIGH` issues.
- Returns detailed boolean outcome and list of active blocker reasons.

---

## 5. API Endpoints (`/api/v1/projects/{project_id}/verification/...`)

1. **Queue & Aggregation**:
   - `GET /queue`: Paginated, filterable review queue with domain, severity, reviewer, and status filters.
   - `GET /summary`: Aggregated verification metrics (counts of candidate, pending, verified, conflicted, rejected, unresolved, and open issues).
2. **Case Detail & Evidence**:
   - `GET /cases/{case_id}`: Full finding details, machine assessments, active issues, review history.
   - `GET /cases/{case_id}/evidence`: Permission-filtered side-by-side supporting and contradictory evidence.
3. **Review Actions**:
   - `POST /cases/{case_id}/approve`: Atomic human approval.
   - `POST /cases/{case_id}/reject`: Human rejection with reason.
   - `PATCH /cases/{case_id}/finding`: Versioned human correction with diff tracking.
   - `POST /cases/{case_id}/request-context`: Issue clarification request.
   - `POST /cases/{case_id}/mark-unresolved`: Mark case unresolved with explanation.
   - `POST /cases/{case_id}/assign`: Reassign review case to specific team member.
4. **Context Requests**:
   - `GET /context-requests`: List open clarification requests.
   - `POST /context-requests/{request_id}/respond`: Provide answer and optional evidence link.
5. **Eligibility Gate**:
   - `GET /cases/{case_id}/eligibility`: Downstream check for handover inclusion.

---

## 6. Implementation Sequence & Gates

1. **Stage 2**: Database migration `0012_verification_center.py` and SQLAlchemy models.
2. **Stage 3**: Deterministic verification engine, issue registry, and provenance checker.
3. **Stage 4**: Conflict detection engine and temporal reconciliation logic.
4. **Stage 5**: Local Qwen3 8B semantic verification worker adapter.
5. **Stage 6**: Human review service with optimistic locking and append-only event logs.
6. **Stage 7**: `HandoverEligibilityService` downstream gate.
7. **Stage 8**: Verification REST API routes and RBAC permissions in `rbac_catalog.py`.
8. **Stage 9**: Comprehensive automated test suite (unit, integration, security, concurrency, and Nexora Assist scenario).
9. **Stage 10**: Documentation updates and final completion report.
