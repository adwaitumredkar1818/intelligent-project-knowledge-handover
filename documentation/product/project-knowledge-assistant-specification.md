# Project Knowledge Assistant — Product Specification

**Platform**: The Handover  
**Formal Description**: Intelligent Project Knowledge Reconstruction & Handover Platform  
**Product Tagline**: Prevent Critical Knowledge From Leaving With People.  
**Module**: Project Knowledge Assistant (Module 5 / AI Assistant Area)  
**Status**: Implemented & Audited (Backend Verified)  
**Date**: 2026-11-13  

---

## 1. Product Mission & Purpose

When employees, volunteers, researchers, or developers depart a project, successors encounter a fragmented landscape of code repositories, task trackers, documents, and chat threads. Generic AI chatbots fail in this scenario: they hallucinate plausible-sounding explanations, disregard access permissions, and provide answers devoid of verifiable audit trails.

The **Project Knowledge Assistant** is the permission-aware, conversational truth engine of **The Handover**. It serves as an interactive project expert that answers successor questions grounded strictly in:
1. Original source evidence (documents, commits, pull requests, issues, discussions).
2. Reconstructed structured knowledge across the 8 canonical domains.
3. The relationship graph (decisions, components, dependencies, responsibilities).
4. Project chronological timelines and milestone histories.

---

## 2. Core Epistemic Guarantees

The Project Knowledge Assistant adheres to strict epistemic boundaries:
- **Zero Fabrication**: The assistant never invents facts, reasons, or team roles. If project evidence does not document a rationale, it explicitly abstains.
- **Strict Evidence Grounding**: Every substantial claim in an answer is mapped to one or more verified source citations (`[S1]`, `[S2]`). Hallucinated citation tags are stripped by the validation engine.
- **Fail-Closed Access Control**: Project membership does not equal source access. Inaccessible sources (e.g., restricted Jira boards or private repositories) are strictly filtered out before prompt construction.
- **Explicit Uncertainty Disclosure**: Rather than guessing when information is contradictory, outdated, or absent, the assistant signals its exact epistemic status to the user.

---

## 3. The 8 Epistemic States

Every generated answer is tagged with one of eight definitive epistemic statuses:

| Status | Definition | User Experience |
| :--- | :--- | :--- |
| `ANSWERED` | The question is fully substantiated by authorized project evidence. | Complete answer with inline citations `[S1]` and expandable evidence drawers. |
| `PARTIALLY_ANSWERED` | Some aspects are documented, but key gaps or unrecorded rationales exist. | Partial answer clearly demarcating known evidence from undocumented areas. |
| `INSUFFICIENT_EVIDENCE` | No supporting evidence exists within the authorized project corpus. | Explicit abstention explaining what could not be found, without guessing. |
| `CONFLICTED_EVIDENCE` | Authoritative sources contradict each other on this topic. | Balanced presentation of contradictory facts with citations to opposing records. |
| `OUTDATED_EVIDENCE` | The only available evidence is flagged as obsolete or superseded. | Answer accompanied by high-visibility warning highlighting record obsolescence. |
| `ACCESS_RESTRICTED` | Relevant evidence exists in the project but the user lacks source ACL credentials. | Neutral notice that information exists in restricted sources without leaking contents. |
| `UNSUPPORTED_QUERY` | The query falls outside project knowledge (e.g., general trivia or unrelated prompts). | Friendly redirect prompting questions relevant to the project's knowledge base. |
| `PROCESSING_ERROR` | An internal retrieval, reasoning, or parsing failure occurred. | Safe graceful fallback error message with correlation tracking ID. |

---

## 4. Query Routing & 12 Supported Query Types

The assistant uses deterministic pattern classification combined with intent extraction to route user prompts across 12 distinct query categories:

1. **`GENERAL_QA`**: Broad conceptual inquiries regarding project goals, features, or architecture.
2. **`ARCHITECTURE`**: Structural design, component boundaries, frameworks, and deployment patterns.
3. **`DECISION_RATIONALE`**: Why a particular decision was made, alternatives rejected, and historical trade-offs.
4. **`RISK_BLOCKER`**: Known technical debts, security vulnerabilities, unresolved bugs, or blockers.
5. **`OWNER_RESPONSIBILITY`**: Who owns a service, module, or task, and their transition counterparts.
6. **`DEPENDENCY_CHAIN`**: Upstream/downstream dependencies, third-party libraries, and internal service links.
7. **`CODE_PROVENANCE`**: How a specific commit, PR, or file came to be and who authored it.
8. **`HISTORICAL_EVOLUTION`**: Chronological milestone progression, release history, and phase transitions.
9. **`WORK_IN_PROGRESS`**: Open PRs, active Jira tasks, and unfinished deliverables.
10. **`OUTDATED_CHECK`**: Inquiries specifically testing whether a document or procedure is current.
11. **`CONFLICT_INSPECTION`**: Clarifying conflicting records identified during verification or review.
12. **`SYSTEM_HELP`**: Inquiries regarding platform usage, capabilities, and navigation.

---

## 5. Entity Extraction & Precision Provenance

The assistant automatically detects and extracts domain entities from user prompts:
- **Jira Issue Keys**: `PROJ-1234`, `ENG-402`, etc.
- **Commit SHAs**: 7- to 40-character hexadecimal git hashes.
- **Pull Request Numbers**: `#128`, `PR-45`.
- **File Paths**: `backend/app/main.py`, `src/components/ui/button.tsx`.
- **User Mentions**: `@alice`, `@shubham`.

Extracted entities are leveraged by the retrieval service to perform targeted exact-match database queries, boosting precision alongside semantic vector search.

---

## 6. Read-Only Governance & Anti-Prompt Injection

1. **Strictly Read-Only Execution**: The assistant is strictly a knowledge query interface. It is architecturally prevented from approving handovers, verifying findings, mutating Jira tickets, pushing git commits, or altering access control policies.
2. **Untrusted Data Boundary**: All retrieved evidence chunks, commit messages, and PR descriptions are enclosed within XML-delimited `<project_evidence>` tags. The reasoning engine treats this content strictly as passive reference data, neutralizing prompt injection attacks attempting to override system instructions.

---

## 7. Next.js Frontend Integration Contract

The backend exposes an idiomatic REST API under `/api/v1/projects/{project_id}/assistant/...` designed for the future Next.js chat interface:

### Key Endpoints
- `GET /conversations`: List all user conversations in the project.
- `POST /conversations`: Create a new conversation thread.
- `GET /conversations/{id}`: Retrieve conversation metadata and history.
- `DELETE /conversations/{id}`: Soft-delete/archive a conversation.
- `POST /conversations/{id}/messages`: Submit a question and receive a structured answer.
- `POST /messages/{id}/feedback`: Submit user feedback (`helpful`, `unhelpful`, `inaccurate`, `missing_context`).
- `GET /diagnostics/retrieval/{run_id}`: Inspect retrieval runs, RRF scores, and filtered sources.
- `GET /suggestions`: Retrieve contextual question prompts tailored to current project risks.
