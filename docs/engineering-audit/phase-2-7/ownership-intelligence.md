# Phase 2.7 Audit: Ownership and Responsibility Intelligence

**Document**: `docs/engineering-audit/phase-2-7/ownership-intelligence.md`  
**Phase**: 2.7 — Complete Knowledge Intelligence Engine  
**Module**: Module E — People and Responsibility Intelligence  
**Status**: APPROVED & VERIFIED  

---

## 1. Executive Summary

This document reviews the ownership and responsibility intelligence capabilities within **The Handover**. 

A frequent cause of handover failure is conflating **historical authorship** with **current maintenance responsibility**. When an engineer leaves a team, systems often assume the original author is still the primary maintainer, obscuring who actually runs or understands the code today. The Ownership Intelligence module solves this through temporal attribution heuristics.

---

## 2. Temporal Attribution Heuristics

The engine computes maintainership by weighing activity recency and contribution density across evidence sources:

```text
Score = (Recency_Weight × Recent_Commits) + 
        (Review_Weight × PR_Approvals) + 
        (Ticket_Weight × Active_Issue_Resolution) + 
        (Decay_Factor × Historical_Authorship)
```

### Distinction Criteria:
1. **Historical Author**: The original creator of a module, component, or decision who may have made zero contributions in the last 6+ months.
2. **Current Active Maintainer**: The person actively reviewing pull requests, answering tickets, and committing bug fixes to the component in the current cycle.
3. **Formal Approver / Owner**: The designated stakeholder with sign-off authority.

---

## 3. Bus Factor & Knowledge Concentration Analysis

The module evaluates knowledge concentration risks across components:

- **Bus Factor 1 Alerts**: Flagging components where >85% of recent commits, reviews, and decisions are attributed to a single person.
- **Orphan Component Detection**: Detecting critical components where all historical contributors have transitioned or departed, leaving zero active maintainers.
- **Departing Member Impact**: When a team member enters handover transition (`transition_participants`), the system immediately identifies all components where their departure reduces the bus factor to zero.

---

## 4. UI & Handover Integration

In the Handover Workspace and Relationship Explorer:
- Ownership cards display both "Primary Maintainer" and "Original Author" with distinct badges.
- Transition alerts highlight which incoming assignees need paired walkthroughs for high-risk single-maintainer modules.
