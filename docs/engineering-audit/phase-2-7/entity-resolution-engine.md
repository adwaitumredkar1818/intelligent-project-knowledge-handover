# Phase 2.7 Audit: Entity Resolution Engine

**Document**: `docs/engineering-audit/phase-2-7/entity-resolution-engine.md`  
**Phase**: 2.7 — Complete Knowledge Intelligence Engine  
**Module**: Module B — Staged Entity Resolution Engine  
**Status**: APPROVED & VERIFIED  

---

## 1. Executive Summary

This document reviews the implementation and validation of the staged identity and entity resolution engine in `backend/app/services/identity_resolution.py`. 

The entity resolution engine reconciles cross-source mentions of the same real-world entity (e.g. GitHub handle `@johndoe`, Jira account `John Doe`, email `john.doe@company.com`, and Slack handle `john_d`) while enforcing multi-tenant isolation and strict human review policies for identity merges.

---

## 2. Multi-Stage Fallback Hierarchy

The resolution engine implements a deterministic 6-tier fallback matching cascade:

```text
Stage 1: Exact Identifier Match (Score: 1.0)
         - Email address exact match
         - External immutable ID (e.g., GitHub User ID, Jira Account ID)
   │
   ▼ (if no match)
Stage 2: Deterministic Handle / Username Normalization (Score: 0.90)
         - Lowercase, punctuation-stripped username matching
         - E.g., "john.doe" == "johndoe"
   │
   ▼ (if no match)
Stage 3: Full Name Similarity Match (Score: 0.70 - 0.85)
         - Jaro-Winkler distance and token set ratio over display names
         - Threshold >= 0.85 required for high-confidence candidate
   │
   ▼ (if no match)
Stage 4: Structural Co-occurrence Heuristics (Score: 0.60 - 0.75)
         - Shared pull requests, authoring identical commits, or co-assigned tickets
   │
   ▼ (if no match)
Stage 5: Aliasing & Transitive Alias Resolution (Score: 0.50 - 0.70)
         - Pre-existing verified aliases in `knowledge_entities.aliases`
   │
   ▼ (if no match)
Stage 6: Fallback / Unresolved (Score: < 0.50)
         - Entity retained as independent record without candidate proposal
```

---

## 3. Strict Boundary & Safety Hardening

In Phase 2.7, two non-negotiable architectural safety rules were implemented in `IdentityResolutionEngine.evaluate_and_record_candidate()`:

### Rule 1: Cross-Tenant Boundary Enforcement
Entities originating from different organisations or projects are strictly prohibited from matching:
```python
if source_entity.project_id != target_entity.project_id:
    logger.warning("Rejected cross-project entity resolution attempt")
    return None
```
Cross-tenant candidate pairs are aborted immediately without persistence or comparison.

### Rule 2: Explicit Person Auto-Merge Prohibition
Because false-positive merges of human identities can conflate intellectual property authorship, security credentials, and handover ownership, `person` entities are **never auto-merged**, regardless of match confidence:
```python
if source_entity.entity_type == EntityType.PERSON or target_entity.entity_type == EntityType.PERSON:
    # Always enforce human review for person entities
    assigned_band = IdentityPolicyBand.MANUAL_REVIEW
```
Auto-merge is restricted to deterministic technical entities (e.g. identical commit hashes or exact repository URLs).

---

## 4. Policy Bands & Human Review Workflow

Candidates are classified into three policy bands:
1. `AUTOMATIC_MERGE` (Score >= 0.95, non-person entities only)
2. `MANUAL_REVIEW` (Score between 0.60 and 0.94, or ANY score for `person` entities)
3. `REJECTED` (Score < 0.60)

The review workflow is exposed via:
- `GET /api/v1/projects/{project_id}/identity-resolution/candidates`
- `POST /api/v1/projects/{project_id}/identity-resolution/review` (Accept or Reject action with reviewer audit trail)
