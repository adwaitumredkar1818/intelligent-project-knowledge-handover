# The Handover — Verification Center REST API Reference

**Base Path**: `/api/v1/projects/{project_id}/verification`  
**Authentication**: Platform Bearer JWT Access Token  
**Authorization**: RBAC Scope Check + Read-Time Source ACL Verification  

---

## 1. Endpoints Summary

| Method | Endpoint | Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/queue` | `project.read` | Paginated listing of verification cases with multi-criteria filtering |
| `GET` | `/summary` | `project.read` | Aggregated case counts by status, machine assessment, and priority |
| `GET` | `/cases/{case_id}` | `project.read` | Detailed verification case inspection including target, issues, conflicts, and events |
| `GET` | `/cases/{case_id}/evidence` | `project.read` | Supporting evidence citations with ACL-aware redaction and conflict comparisons |
| `POST` | `/cases/{case_id}/approve` | `project.knowledge.review` | Human approval promoting finding to `HUMAN_VERIFIED` (optimistic locking enforced) |
| `POST` | `/cases/{case_id}/reject` | `project.knowledge.review` | Reject candidate finding or suggested relationship with reason |
| `POST` | `/cases/{case_id}/finding` | `project.knowledge.review` | Apply human corrections to finding with before/after audit snapshot diff |
| `POST` | `/cases/{case_id}/request-context` | `project.knowledge.review` | Dispatch clarification inquiry to departing contributor or project lead |
| `POST` | `/cases/{case_id}/mark-unresolved` | `project.knowledge.review` | Mark case unresolved when evidence or consensus cannot be established |
| `POST` | `/cases/{case_id}/assign` | `project.knowledge.review` | Assign or reassign verification case to an authorized reviewer |
| `GET` | `/context-requests` | `project.read` | List pending clarification requests addressed to current user or project |
| `POST` | `/context-requests/{request_id}/respond` | `project.read` | Submit answer or supplemental context for an active inquiry |
| `GET` | `/cases/{case_id}/eligibility` | `project.read` | Evaluate downstream Handover Workspace export eligibility gate |
| `POST` | `/assess` | `project.knowledge.review` | Trigger on-demand deterministic assessment of a finding or relationship |

---

## 2. Request & Response Specifications

### 2.1 `GET /queue`
List verification queue cases ordered by priority and update timestamp.

**Query Parameters**:
- `status` (optional `VerificationCaseStatus`: `candidate`, `in_review`, `pending_review`, `verified`, `rejected`, `unresolved`)
- `machine_status` (optional `MachineAssessmentStatus`: `passed`, `issues_detected`, `insufficient_evidence`, `conflicts_detected`)
- `priority` (optional `VerificationPriority`: `critical`, `high`, `medium`, `low`)
- `target_type` (optional `VerificationTargetType`: `knowledge_item`, `relationship`)
- `assigned_to_me` (optional boolean, filter to cases assigned to caller)
- `page` (integer, default `1`)
- `page_size` (integer, default `50`, max `200`)

**Response (`200 OK`)**:
```json
{
  "total": 1,
  "page": 1,
  "page_size": 50,
  "items": [
    {
      "id": "7b0b6cf6-0045-4202-b258-3f8d22765d75",
      "organisation_id": "90eb5bc5-857e-40dc-bc54-20a2d59ceb55",
      "project_id": "5fc4e5ce-a13f-42e1-8cb5-e41da80bb8b3",
      "target_type": "knowledge_item",
      "target_id": "7769a9b0-97b7-4c4c-9f89-8d76a382d5be",
      "case_status": "pending_review",
      "machine_assessment_status": "passed",
      "priority": "medium",
      "assigned_reviewer_id": null,
      "machine_assessment_json": {
        "assessment_mode": "deterministic",
        "evidence_links_count": 1
      },
      "version": 1,
      "open_issues_count": 0,
      "open_conflicts_count": 0,
      "last_assessed_at": "2026-11-13T10:00:00Z",
      "last_reviewed_at": null,
      "resolved_at": null,
      "created_at": "2026-11-13T10:00:00Z",
      "updated_at": "2026-11-13T10:00:00Z"
    }
  ]
}
```

---

### 2.2 `GET /summary`
Aggregated overview of verification health and queue backlog.

**Response (`200 OK`)**:
```json
{
  "total_cases": 42,
  "pending_review_count": 18,
  "verified_count": 20,
  "rejected_count": 2,
  "unresolved_count": 2,
  "critical_priority_count": 3,
  "high_priority_count": 8,
  "open_issues_count": 14,
  "unresolved_conflicts_count": 2
}
```

---

### 2.3 `POST /cases/{case_id}/approve`
Approves a finding as human-verified knowledge. Fails with `409 Conflict` if concurrent modifications occurred, or `422 Unprocessable Entity` if open critical issues exist.

**Request Body**:
```json
{
  "expected_version": 1,
  "review_notes": "Cross-referenced with RFC-104 and verified with architecture team."
}
```

**Response (`200 OK`)**:
```json
{
  "id": "7b0b6cf6-0045-4202-b258-3f8d22765d75",
  "organisation_id": "90eb5bc5-857e-40dc-bc54-20a2d59ceb55",
  "project_id": "5fc4e5ce-a13f-42e1-8cb5-e41da80bb8b3",
  "target_type": "knowledge_item",
  "target_id": "7769a9b0-97b7-4c4c-9f89-8d76a382d5be",
  "case_status": "verified",
  "machine_assessment_status": "passed",
  "priority": "low",
  "assigned_reviewer_id": "3e02b8d2-7d3b-405d-9d1a-bf5528bd3d5d",
  "version": 2,
  "target_data": {
    "id": "7769a9b0-97b7-4c4c-9f89-8d76a382d5be",
    "title": "Adopt Argon2id for Password Hashing",
    "epistemic_status": "human_verified",
    "review_status": "approved",
    "confidence_score": 1.0
  },
  "issues": [],
  "conflicts": [],
  "review_events": [
    {
      "id": "42921cb9-8e43-4dc9-a9a3-cbb84883f3a8",
      "action": "approve",
      "previous_status": "pending_review",
      "new_status": "verified",
      "review_notes": "Cross-referenced with RFC-104 and verified with architecture team.",
      "created_at": "2026-11-13T10:15:00Z"
    }
  ]
}
```

---

### 2.4 `POST /cases/{case_id}/finding`
Applies human edits directly to a finding while capturing before/after state diff.

**Request Body**:
```json
{
  "expected_version": 1,
  "patch_data": {
    "title": "Use Argon2id v1.3 with 64MB memory cost",
    "summary": "Updated memory cost parameters to comply with OWASP 2026 baseline."
  },
  "reason": "Corrected parameter specifications according to security review."
}
```

---

### 2.5 `POST /cases/{case_id}/request-context`
Dispatches a clarification inquiry to a departing contributor or project lead.

**Request Body**:
```json
{
  "expected_version": 1,
  "requested_from_user_id": "19b5b248-933e-436f-870d-f01878d6b063",
  "question": "Can you confirm whether the PostgreSQL failover configuration was tested in staging?",
  "requested_information_type": "operational_verification"
}
```

---

### 2.6 `GET /cases/{case_id}/eligibility`
Downstream gatekeeper evaluation for Handover Workspace packaging.

**Response (`200 OK`)**:
```json
{
  "is_eligible": true,
  "target_type": "knowledge_item",
  "target_id": "7769a9b0-97b7-4c4c-9f89-8d76a382d5be",
  "case_status": "verified",
  "epistemic_status": "human_verified",
  "blockers": [],
  "warnings": []
}
```
*If unverified or restricted by ACLs, `is_eligible` returns `false` with explicit blocking explanations.*

---

## 3. Optimistic Concurrency Control
All state-modifying endpoints (`approve`, `reject`, `finding`, `request-context`, `mark-unresolved`, `assign`) require `expected_version: integer`. If the record was modified by another reviewer in the interim:
- Returns `HTTP 409 Conflict`
- Payload: `{"detail": "Concurrent modification detected. Current version is X, expected Y. Please refresh and review latest changes."}`

## 4. Audit Trail Integration
Every human review action records an immutable row in `audit_logs` with event types:
- `verification.case.approved`
- `verification.case.rejected`
- `verification.case.edited`
- `verification.context_requested`
- `verification.case.marked_unresolved`
- `verification.case.assigned`
