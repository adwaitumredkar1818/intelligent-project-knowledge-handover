# THE HANDOVER — VERIFICATION CENTER
## Security Architecture, RBAC & Data Integrity Audit Report

- **Module**: Verification Center (Module 3 / Validation Area)
- **Product**: The Handover (Intelligent Project Knowledge Reconstruction & Handover Platform)
- **Security Standard**: Enterprise Zero-Trust, Epistemic Integrity & Source ACL Isolation
- **Audit Date**: 2026-11-13
- **Security Posture Assessment**: **STRONG** — Zero Critical or High Security Vulnerabilities. Authentication, Multi-Tenant Isolation, Source-Level ACLs, Optimistic Locking, and Audit Immutability verified in live testing.

---

## 1. Executive Summary & Security Baseline

The Verification Center is the authoritative security and quality barrier between untrusted AI-generated extractions and auditable project handover packages.

Because it controls which knowledge is promoted to `HUMAN_VERIFIED` and released in handover deliverables, its security boundaries must prevent:
1. **Unapproved AI Extractions**: AI models or automated scripts bypassing human review.
2. **Cross-Tenant Bleed**: Project members of Organisation A accessing or verifying findings from Organisation B.
3. **Source Privilege Escalation**: Project members viewing private repository or restricted issue data without delegated source permissions (**Project Membership != Source Access**).
4. **Concurrent Edit Overwrites**: Multiple reviewers clobbering each other's decisions.
5. **Reviewer Identity Spoofing**: Actions attributed to arbitrary user IDs without authentication verification.

---

## 2. Security Dimension Evaluation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SECURITY ACCESS PIPELINE                           │
│                                                                             │
│   [ HTTP Request ]                                                          │
│          │                                                                  │
│          ▼                                                                  │
│   1. FastAPI Bearer JWT Token Verification                                  │
│          │   - Signature validated against application secret               │
│          │   - Token family validated against active PostgreSQL             │
│          │     `refresh_sessions` (revocation check)                        │
│          ▼                                                                  │
│   2. Multi-Tenant Organization Membership & Project Isolation               │
│          │   - Caller must be an active member of parent Organisation       │
│          │   - Non-members receive HTTP 404 PROJECT_NOT_FOUND               │
│          │     (security cloaking against resource enumeration)             │
│          ▼                                                                  │
│   3. RBAC Permission Enforcement (fail-closed)                              │
│          │   - `project.read` for queue / case viewing                      │
│          │   - `project.knowledge.review` for approve / reject / edit       │
│          ▼                                                                  │
│   4. Optimistic Concurrency Control (Version Locking)                       │
│          │   - `expected_version` matched against `VerificationCase.version`│
│          │   - Mismatches raise HTTP 409 ConcurrencyConflictError          │
│          ▼                                                                  │
│   5. Source-Level ACL Enforcement (Read-Time Gate)                          │
│          │   - Project Membership != Source Access                          │
│          │   - External permissions checked per evidence citation           │
│          │   - Blocked citations fail closed (excluded from handover)       │
│          ▼                                                                  │
│   6. Immutable PostgreSQL Audit Trail                                       │
│          - Append-only event in `verification_review_events`                │
│          - Security log in `audit_logs` table                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Security Findings by Domain

### 3.1 Platform Authentication
- **Sole Authority**: Platform authentication is managed strictly by FastAPI using short-lived JWT access tokens and SHA-256 `RefreshSession` rotation in PostgreSQL (no Supabase Auth dependency).
- **Session Revocation Verification**: When an access token is presented, `get_current_principal` verifies that the `session_family_id` claims correspond to an active, unrevoked row in `refresh_sessions`. In testing, tokens without an active session were rejected with `HTTP 401 SESSION_REVOKED`.
- **Unauthenticated Protection**: Unauthenticated requests to `/verification/queue` were rejected with `HTTP 401 AUTHENTICATION_REQUIRED` (`SEC-01: PASS`).

### 3.2 Multi-Tenant Organization & Project Isolation
- **Hierarchical Access Verification**: During live testing, when a user who was assigned a project role attempted to access `/api/v1/projects/{id}/verification/queue` without being an active member of the project's parent organisation, the request was immediately blocked:
  ```json
  {
    "event_type": "tenant.project_access_denied",
    "outcome": "denied",
    "message": "Denied project access because caller is not an active parent org member.",
    "status_code": 404,
    "error_code": "PROJECT_NOT_FOUND"
  }
  ```
- **Security Cloaking**: Returning `HTTP 404 PROJECT_NOT_FOUND` rather than `HTTP 403 FORBIDDEN` prevents unauthorized actors from discovering the existence of private projects or tenant IDs.

### 3.3 Role-Based Access Control (RBAC)
- **Granular Permissions**:
  - `project.read`: Required to view review queue, summary metrics, case details, and context requests.
  - `project.knowledge.review`: Required for state-changing operations: `approve()`, `reject()`, `edit_finding()`, `mark_unresolved()`, `assign_reviewer()`, and `request_context()`.
- **Fails Closed**: If a user lacks `project.knowledge.review`, the request is rejected with `HTTP 403 PERMISSION_DENIED` before any database state is updated.

### 3.4 The Critical Source-Level ACL Boundary: `Project Membership != Source Access`
- **Zero Privilege Escalation**: A fundamental tenet of The Handover is that being invited to a project does NOT grant access to private third-party evidence (GitHub repos, Jira issues, Slack private channels) connected by another team member.
- **Handover Gate Enforcement**: In test `GATE-04`, a knowledge item citing private evidence was tested against a user lacking delegated permissions for that source provider.
  - `HandoverEligibilityService` invoked `check_evidence_accessibility()` on each supporting evidence chunk.
  - The item was marked `is_eligible = FALSE` with reason `blocked_by_source_acl = True`.
  - The sensitive evidence was stripped from the eligibility payload, preventing unauthorized data leakage into the handover package.

### 3.5 Epistemic Quality Gate & AI Prohibitions
- **Explicit Prohibition Enforcement**: In test `LIFE-05`, the machine assessment engine was triggered on a candidate finding. Even when deterministic checks and AI scoring gave a `PASSED` rating, the finding's epistemic status remained `EXTRACTED` and review status remained `PENDING_REVIEW`.
- **Strict Human Agency**: Only an authorized human review action (`approve()`) can transition an item to `HUMAN_VERIFIED`. The LLM cannot approve findings, decide task status, or override verification decisions.

### 3.6 Optimistic Concurrency & Data Race Prevention
- **Race Condition Immunity**: In test `REV-02`, concurrent reviewer edits were simulated by passing a stale `expected_version = 1` after another operation had already bumped the case version to `2`.
- **Atomic Abort**: The `HumanReviewService` raised `ConcurrencyConflictError` (HTTP 409), aborting the transaction and preventing silent overwrites.

### 3.7 Audit Trail Immutability & Reviewer Non-Repudiation
- **Dual-Layer Audit Records**:
  1. `verification_review_events`: Dedicated append-only table recording every state change, notes, reviewer user ID, and finding payload JSON diffs. No `UPDATE` or `DELETE` endpoints exist for this table.
  2. `audit_logs`: Platform-wide immutable PostgreSQL audit log capturing `verification.case.approved`, `verification.case.rejected`, `verification.case.marked_unresolved`, and `tenant.project_access_denied` with client IP and user agent.
- **Actor Non-Repudiation**: The reviewer ID is extracted exclusively from the authenticated JWT principal (`principal.user.id`), never accepted as an untrusted request parameter.

---

## 4. Defect & Vulnerability Catalog

| ID | Severity | Category | Description | Impact | Remediation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-MED-01** | **Medium** | Code / Configuration | In `verification_ai.py` line 73, `settings.ollama_model_reconstruction` is referenced instead of `settings.ollama_llm_model`. | Instantiating `AIAssistedVerificationService` without passing an explicit LLM client raises an `AttributeError`. | Update line 73 to reference `settings.ollama_llm_model` (or `settings.ollama.llm_model`). |
| **SEC-MED-02** | **Medium** | Data Model Granularity | Verification cases link entire `KnowledgeItem` records and `EvidenceChunk` references. Individual atomic sub-claims within a multi-sentence finding are not stored in separate normalized rows. | Reviewers must approve or reject an entire finding; they cannot accept 2 claims and reject 1 sub-claim without rewriting the text. | Introduce claim-level decomposition table (`verification_claims`) or structured sub-claims array with per-claim approval status. |
| **SEC-LOW-01** | **Low** | Operational / Performance | `POST /projects/{id}/verification/assess` runs deterministic re-assessment synchronously in the HTTP request thread. | For knowledge items with hundreds of evidence links, the request could take >10 seconds and block Uvicorn worker threads. | Dispatch re-assessment tasks to the PostgreSQL background worker queue (`BackgroundJobRepository`). |
| **SEC-LOW-02** | **Low** | Test Harness | `run_verification_center_audit.py` asserted HTTP 200 for `POST /request-context`, but the endpoint correctly returns HTTP 201 Created. | Caused false failure in API-07 and blocked API-09 during test run. | Update test runner to accept HTTP 201 Created. |

---

## 5. Security Posture Verdict

The Verification Center backend adheres rigorously to enterprise security and epistemic standards:
- **No unauthorized data leakage** across tenants or private source providers.
- **Strict enforcement of human approval gates** before knowledge can become eligible for handover.
- **Tamper-resistant audit trails** and optimistic locking preventing race conditions.
- **Readiness for Production**: Ready for frontend integration upon applying the Priority 1 patch in `verification_ai.py`.
