# The Handover — Verification Center Specification

**Module**: Verification Center (Module 3 / Validation Area)  
**Product**: The Handover — Intelligent Project Knowledge Reconstruction & Handover Platform  
**Mission**: Prevent Critical Knowledge From Leaving With People  

---

## 1. Executive Summary & Purpose

The **Verification Center** is the quality-control and trust engine of **The Handover**. It bridges the gap between automated knowledge extraction (Knowledge Intelligence and Relationship Explorer) and reliable knowledge transfer (Handover Workspace).

Automated extraction pipelines often encounter fragmented, outdated, or conflicting source evidence. The platform operates on a foundational epistemological rule:

> **The AI extracts, analyzes, and recommends. Evidence grounds it. Only an authorized human reviewer approves.**
>
> An AI confidence score is never proof of correctness. An AI-generated finding must never independently become approved knowledge or enter an official handover package without human verification.

```text
┌─────────────────────────┐     ┌─────────────────────────┐
│   Knowledge Extraction  │ ──▶ │   Verification Center   │ ──▶ ┌─────────────────────────┐
│ (KI & Relationship Exp) │     │ (Human Review Gate)     │     │    Handover Workspace   │
└─────────────────────────┘     └─────────────────────────┘     │  (Verified Packages)    │
                                             │                  └─────────────────────────┘
                                             ▼
                                ┌─────────────────────────┐
                                │   Audit Trail & ACLs    │
                                └─────────────────────────┘
```

---

## 2. Four-Tier Epistemic Separation

All knowledge entities in the platform are strictly classified across four distinct epistemic tiers:

1. **Original Source Evidence**: Unaltered primary documents, Jira issues, GitHub commits, pull requests, and authorized Slack communications stored in private encrypted storage or referenced from external providers.
2. **Extracted Information** (`epistemic_status = "extracted"`): Candidate facts, titles, and excerpts parsed directly from source evidence without semantic interpretation.
3. **AI Interpretation** (`epistemic_status = "ai_interpreted"`): Inferred relationships, synthesized summaries, and cross-source connections suggested by language models (e.g., Qwen3 8B).
4. **Human-Verified Knowledge** (`epistemic_status = "human_verified"`): Findings and relationships explicitly inspected, potentially corrected, and approved by an authorized reviewer with platform credentials.

**Only tier 4 (`human_verified`) is eligible for inclusion in official handover packages.**

---

## 3. The 14-Item Verification Issue Taxonomy

The system deterministically evaluates all candidate findings against an extensible 14-item taxonomy of validation issues:

| Issue Type | Category | Default Severity | Blocks Handover? | Description | Recommended Remediation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `missing_evidence` | Provenance | **CRITICAL** | **YES** | Finding has 0 evidence links or cited ID does not exist | Attach verified source document, commit, or issue before approval |
| `invalid_source_reference` | Provenance | **HIGH** | **YES** | Cited chunk does not belong to cited item or is outside workspace | Re-link excerpt to valid chunk within project workspace |
| `unsupported_claim` | Grounding | **HIGH** | **YES** | Supporting excerpt cannot be matched verbatim in source chunk | Review primary text and update excerpt or remove statement |
| `conflicting_sources` | Consistency | **HIGH** | **YES** | Contradictory facts detected between two or more project sources | Inspect claims in conflict view and select canonical source |
| `inconsistent_status` | Consistency | **MEDIUM** | NO | Finding status contradicts observed Jira issue or Git commit state | Synchronize finding status with verified tracking system or document |
| `outdated_information` | Freshness | **MEDIUM** | NO | Supporting evidence was superseded by subsequent activity | Verify against latest document revision or mark superseded |
| `stale_knowledge` | Freshness | **HIGH** | **YES** | Source was revoked or deleted, rendering evidence unverified | Re-authenticate source or link alternative active evidence |
| `duplicate_record` | Uniqueness | **MEDIUM** | NO | Another finding shares identical semantic content or title | Merge duplicate findings into canonical record or dismiss secondary |
| `uncertain_relationship` | Relational | **LOW** | NO | Relationship was inferred without explicit key reference | Human reviewer should confirm or reject graph edge connection |
| `invalid_entity_mapping` | Relational | **HIGH** | **YES** | Target entity does not match required entity type for relationship | Re-map relationship to valid entity node |
| `incorrect_attribution` | Attribution | **MEDIUM** | NO | Attributed owner does not match commit author or assignee | Correct attributed team member in finding payload |
| `missing_source_context` | Completeness | **LOW** | NO | Finding omits expected context (e.g. decision rationale) | Request clarification from departing team member |
| `insufficient_information` | Completeness | **MEDIUM** | NO | Available evidence is insufficient for confident handover sign-off | Request additional context from project lead or departing team member |
| `incomplete_traceability` | Traceability | **LOW** | NO | Decision-to-implementation chain has untraced links across items | Connect intermediate work item or pull request to complete trace |

---

## 4. Conflict Detection & Temporal Supersession Engine

Project knowledge often evolves over time, resulting in contradictory statements across documentation and issue trackers.

### 4.1 Inconsistency Detection
The `ConflictDetectionEngine` analyzes:
- **Status Contradictions**: E.g., Jira issue marked `In Progress` while Git commit history shows merged implementation, or meeting notes claim a feature is deferred while documentation describes it as complete.
- **Decision Divergence**: Two architectural decisions specifying incompatible technologies or standards.

### 4.2 Temporal Ordering
When a conflict is recorded between Claim A and Claim B, the engine assesses timestamps:
- `claim_b_supersedes_a`: Source B has a later timestamp than Source A, suggesting B represents the updated decision.
- `claim_a_supersedes_b`: Source A has a later timestamp than Source B.
- `concurrent_conflict`: Both sources share identical timestamps or occurred within a negligible window.
- `undetermined`: Timestamp metadata is unavailable on one or both sources.

**Crucial Rule**: Even when temporal supersession is detected, the conflict is surfaced to the human reviewer for explicit confirmation.

---

## 5. AI Advisory Role (Qwen3 8B via Ollama)

The local Qwen3 8B model is integrated through `AIAssistedVerificationService` strictly as an **adviser**, never a decision-maker:
- **Conflict Nuance Explanation**: Explains why two sources may appear to diverge (e.g., scoping differences, temporary hotfix vs long-term architecture).
- **Clarification Question Formulation**: Automatically drafts context inquiries for human reviewers to dispatch to departing engineers.
- **Strict Fallback Guarantee**: If local Ollama inference is unavailable or fails, deterministic fallbacks ensure zero disruption to human review workflows.

---

## 6. Human Review Engine & Verification Actions

Authorized reviewers with the `project.knowledge.review` permission interact with cases via atomic review actions:

1. **Approve (`POST /approve`)**:
   - Promotes target finding to `EpistemicStatus.HUMAN_VERIFIED`.
   - Sets review status to `KnowledgeReviewStatus.APPROVED`.
   - **Enforces Precondition Gate**: Rejects approval if any open `CRITICAL` issues (e.g., `missing_evidence`) remain.
2. **Reject (`POST /reject`)**:
   - Marks case and target finding as `REJECTED` with mandatory explanation.
3. **Edit Finding (`POST /finding`)**:
   - Applies direct corrections to title, summary, or structured payloads.
   - Captures complete before/after snapshot diff in review event logs.
4. **Request Context (`POST /request-context`)**:
   - Creates a pending clarification inquiry routed to a departing member or team lead.
5. **Mark Unresolved (`POST /mark-unresolved`)**:
   - Flags finding as unresolved when evidence is ambiguous or contradictory without consensus.
6. **Assign Reviewer (`POST /assign`)**:
   - Delegates case ownership to a team member for specialized subject-matter review.

### 6.1 Optimistic Concurrency Control
Every case maintains an integer `version` incremented on every state modification. Reviewers must provide the `expected_version`. If another reviewer updated the case in the interim, the API rejects the request with `HTTP 409 Conflict`, preventing silent overwrites.

### 6.2 Append-Only Provenance
All review actions append an immutable `VerificationReviewEvent` containing reviewer ID, timestamps, before/after JSON snapshots, and audit trail records.

---

## 7. Downstream Handover Eligibility Gatekeeper

The `HandoverEligibilityService` acts as an impassable gatekeeper between the Verification Center and the Handover Workspace.

To be deemed eligible for handover inclusion, an item must satisfy **all** of the following:
1. **Human Verification**: `item.epistemic_status == EpistemicStatus.HUMAN_VERIFIED`.
2. **Review Approval**: `item.review_status == KnowledgeReviewStatus.APPROVED`.
3. **Active Verification Case**: Case status is `VerificationCaseStatus.VERIFIED`.
4. **Zero Blocking Issues**: No open issues of severity `CRITICAL` or `HIGH`.
5. **Zero Unresolved Conflicts**: All cross-source conflicts resolved by a human.
6. **Source Accessibility (Read-Time ACLs)**: The viewing recipient must have authorized access to all cited external sources. If a user does not have permission to view a restricted GitHub repository or Jira project, the evidence is redacted and eligibility fails closed.
