# Phase 2.7 Audit: Evidence Provenance and Confidence Engine

**Document**: `docs/engineering-audit/phase-2-7/evidence-provenance.md`  
**Phase**: 2.7 — Complete Knowledge Intelligence Engine  
**Module**: Module H — Evidence Provenance and Confidence Engine  
**Status**: APPROVED & VERIFIED  

---

## 1. Executive Summary

This document reviews the implementation of **Evidence Provenance and Four-Tier Epistemic Separation** in The Handover platform.

A foundational directive of the platform architecture is that the LLM is never the source of truth. Every reconstructed entity, relationship, and finding must trace back to concrete source evidence, and data models must distinguish between raw facts, machine extractions, AI syntheses, and human sign-offs.

---

## 2. Four-Tier Epistemic Separation

All knowledge representations are explicitly classified into four distinct epistemic tiers:

```text
┌─────────────────────────────────────────────────────────┐
│ Tier 1: Original Source Evidence                        │
│ - Raw document chunks, commit diffs, Jira issue payloads│
│ - Immutable content hashes and source URLs              │
└────────────────────────────┬────────────────────────────┘
                             │ (Parsed / Extracted)
                             ▼
┌─────────────────────────────────────────────────────────┐
│ Tier 2: Extracted Information                           │
│ - Entities, tokens, direct mentions, dates, authors     │
│ - Deterministically extracted via AST/rules             │
└────────────────────────────┬────────────────────────────┘
                             │ (Inferred / Reconstructed)
                             ▼
┌─────────────────────────────────────────────────────────┐
│ Tier 3: AI-Generated Interpretation                     │
│ - Rationale summaries, candidate identity resolutions   │
│ - Draft findings, suggested dependencies, confidence < 1│
└────────────────────────────┬────────────────────────────┘
                             │ (Human Reviewed / Approved)
                             ▼
┌─────────────────────────────────────────────────────────┐
│ Tier 4: Human-Verified Knowledge                        │
│ - Approved decisions, verified relationships            │
│ - Signed-off handovers, immutable audit stamp           │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Pre-Retrieval Source ACL Filtering

A critical security requirement is that **Project Membership != Source Access**:
- Being a member of a project does NOT automatically allow viewing evidence from a private source (e.g., an internal GitHub repo) if that user does not have explicit source access.
- In `backend/app/services/relationship_explorer.py` and `backend/app/services/hybrid_retrieval.py`:
  1. The requesting user's accessible source IDs are retrieved before running graph or vector searches.
  2. Findings, entities, and evidence items whose supporting evidence belongs exclusively to restricted sources are pruned from the result set.
  3. Pre-retrieval filtering guarantees that restricted text is never exposed in API responses or injected into LLM context prompts.

---

## 4. Confidence Score Degradation & Provenance Attribution

Confidence scores are computed deterministically based on:
1. **Source Corroboration**: Multiple independent sources supporting the same entity increases confidence towards 1.0.
2. **Single Uncorroborated Mention**: Scored between 0.60 and 0.75.
3. **Temporal Stale Decay**: Findings without recent corroboration undergo slight confidence degradation.
4. **Direct Human Verification**: Automatically promotes confidence to 1.0 with `verification_status = 'verified'`.
