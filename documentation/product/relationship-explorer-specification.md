# The Handover — Relationship Explorer Specification

**Module**: Relationship Explorer (Module 4)  
**Status**: Fully Implemented Backend (API, Database, Services, Worker Pipeline, Test Suite Verified)  
**Parent System**: The Handover — Intelligent Project Knowledge Reconstruction & Handover Platform  

---

## 1. Executive Summary & Product Mission

When team members leave a project, the most fragile knowledge is not isolated code files or documents, but the **interconnections between artifacts**:
- Which architectural decision led to which PR and commits?
- Which Jira ticket explains why a component was redesigned?
- Who was the true author and domain expert responsible for a critical service?
- Which unresolved dependencies and blockers will stall the incoming engineer?
- In what chronological order did related project events transpire?

The **Relationship Explorer** reconstructs these connections across heterogeneous organizational sources (GitHub, Jira, Slack, technical documents, ADRs, meeting notes, and knowledge items).

### Core Principle
> **EVERY RELATIONSHIP MUST HAVE A TRACEABLE BASIS.**  
> The system distinguishes:
> 1. **Explicit relationships** (deterministic cross-source links, foreign keys, PR/issue mentions).
> 2. **Inferred relationships** (contextual path matches, semantic links, LLM suggestions).
> 3. **Human-confirmed relationships** (explicit human review promoting candidate links to verified knowledge).
> 4. **Uncertain relationships** (confidence < 0.70 requiring human review).
> 5. **Conflicting relationships** (detected contradictions across sources).
>
> **The AI must never invent a relationship and present it as established project knowledge.**

---

## 2. Canonical Entity Taxonomy

The Relationship Explorer models 13 first-class knowledge entity types:

| Entity Type | Description | Canonical Sources |
| :--- | :--- | :--- |
| `person` | Individual team member, developer, reviewer, assignee, author | GitHub, Jira, Slack, commits |
| `team` | Organizational team, squad, or working group | Jira, GitHub org teams |
| `decision` | Architectural or technical decision (ADR, design doc outcome) | Docs, PR descriptions, ADRs |
| `work_item` | Task, issue, bug, user story | Jira, GitHub Issues |
| `pull_request` | Code review and pull request | GitHub PRs |
| `commit` | Individual Git commit hash | Git repository history |
| `component` | Software service, library, package, microservice | Code paths, system architecture docs |
| `document` | Project specification, guide, README, architecture document | Local uploads, repo docs |
| `discussion_thread` | Communication thread, channel conversation | Slack, Jira comments, PR reviews |
| `meeting_note` | Transcribed or recorded meeting notes | Uploaded meeting documents |
| `blocker` | Critical impediment or technical roadblock | Jira blockers, bug reports |
| `risk` | Architectural or delivery risk | Knowledge findings, risk registers |
| `procedure` | Operational runbook, deployment procedure, SOP | Ops documentation, READMEs |

---

## 3. Canonical Relationship Taxonomy

Over 40 validated relationship types organized into functional categories:

### Decision & Governance
- `DECIDED_BY` (`decision -> person | team`)
- `INFLUENCED_BY` (`decision | work_item -> meeting_note | discussion_thread | person`)
- `SUPERSEDES` (`decision -> decision`)
- `AFFECTS_COMPONENT` (`decision | work_item | pull_request | commit -> component`)
- `MITIGATES_RISK` (`decision | work_item -> risk`)

### Implementation & Traceability
- `IMPLEMENTS` (`work_item | pull_request | commit -> decision`)
- `RESOLVES` (`pull_request | commit -> work_item`)
- `AUTHORED_BY` (`pull_request | commit | document -> person`)
- `REVIEWED_BY` (`pull_request | document -> person`)
- `MODIFIES` (`commit | pull_request -> component | document`)
- `CONTAINS` (`component -> component | document`)

### Dependency & Blocking Hierarchy
- `BLOCKS` (`work_item | blocker | risk -> work_item | component`)
- `DEPENDS_ON` (`work_item | component -> work_item | component`)
- `ARCHITECTURAL_DEPENDENCY` (`component -> component`)

### Ownership & Responsibility
- `OWNS` (`person | team -> component | document | procedure`)
- `ASSIGNED_TO` (`work_item -> person | team`)
- `ESCALATED_TO` (`risk | blocker -> person | team`)

### Context & Provenance
- `DISCUSSED_IN` (`decision | work_item | component -> discussion_thread | meeting_note`)
- `DOCUMENTED_IN` (`component | decision | procedure -> document`)
- `REFERENCES` (`any -> any`)

---

## 4. Multi-Signal Identity Resolution & Person Safety Override

Engineers and stakeholders appear under disparate handles across sources (e.g. `alexv` on GitHub, `alex.vance@company.com` on Jira, `@alex` on Slack).

The system implements a **5-signal weighted identity matching engine**:
1. **Exact string match** (weight: 0.40)
2. **Normalized handle / username match** (weight: 0.25)
3. **Email domain & local-part match** (weight: 0.15)
4. **Cross-source evidence co-occurrence** (weight: 0.10)
5. **Organizational proximity & team overlap** (weight: 0.10)

### Policy Bands
- `aggregate_score >= 0.85`: `AUTO_MERGE` (non-person entities only)
- `0.60 <= aggregate_score < 0.85`: `MANUAL_REVIEW`
- `aggregate_score < 0.60`: `DISMISSED`

### Person Safety Override (Mandatory)
> **CRITICAL RULE**: To prevent erroneous conflation of human identities and permissions, **person entities are strictly barred from automatic merging**. Any candidate match involving a `person` entity is unconditionally capped at `MANUAL_REVIEW`, requiring human confirmation.
>
> All merges are **fully reversible** without data loss.

---

## 5. End-to-End Decision Traceability

The Relationship Explorer constructs a complete 5-stage traceability chain for architectural decisions:
```text
DECISION ──▶ WORK ITEM (Jira) ──▶ PULL REQUEST (GitHub) ──▶ COMMIT ──▶ COMPONENT
```

### Traceability States
- **COMPLETE**: All 5 stages exist and are verified.
- **PARTIALLY_TRACED**: At least one stage is missing (e.g. decision recorded without PR link).
- **UNTRACED**: Decision has no linked implementation artifacts.
- **CONFLICTING**: Contradictory links or competing implementations detected.

---

## 6. Dependency Intelligence & Cycle Detection

- Implements Tarjan's / DFS cycle detection algorithm to identify circular dependencies.
- Identifies **root blockers**: items that block other tasks/components but are not themselves blocked.
- Calculates blast radius and dependency depth for safe handover planning.

---

## 7. Knowledge Timeline Stream

Reconstructs chronological project evolution with precision metadata:
- Precision: `exact_datetime`, `date_only`, `inferred_range`, `relative_sequence`.
- Origin: `source_api`, `git_commit_timestamp`, `document_metadata`, `inferred`.
