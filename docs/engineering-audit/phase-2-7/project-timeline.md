# Phase 2.7 Audit: Project Knowledge Timeline

**Document**: `docs/engineering-audit/phase-2-7/project-timeline.md`  
**Phase**: 2.7 — Complete Knowledge Intelligence Engine  
**Module**: Module G — Project Knowledge Timeline Engine  
**Status**: APPROVED & VERIFIED  

---

## 1. Executive Summary

This document reviews the **Project Knowledge Timeline Engine** (`TimelineEngine` in `backend/app/services/timeline_engine.py`).

Traditional knowledge bases order events by when the document or record was indexed into the database. In a handover context, this creates catastrophic temporal inversions (e.g. an architecture decision record written in 2023 but uploaded in 2026 appears newer than yesterday's Jira ticket). The Timeline Engine resolves this by separating real-world event occurrence from ingestion timestamps.

---

## 2. Temporal Precision & Timestamp Disambiguation

The engine enforces a strict timestamp hierarchy across all reconstructed events:

```text
Priority 1: Real-World Occurrence Timestamp (`event_timestamp`)
            - Git commit author/commit timestamp
            - Jira status transition timestamp
            - Document explicit publication / signature date
   │
   ▼ (if absent)
Priority 2: Source Record Creation Timestamp (`source_created_at`)
            - File creation time in external storage / repository
   │
   ▼ (if absent)
Priority 3: Ingestion Timestamp (`created_at`)
            - Fallback marked explicitly with low temporal precision flag
```

### Event Precision Levels:
- `EXACT`: Sub-second or minute-level timestamp from authoritative source metadata.
- `DAY`: Date known without specific hour/minute.
- `APPROXIMATE`: Inferred from context or fallback ingestion timestamp.

---

## 3. Timeline Streams & Filter Facets

The Timeline API allows filtering across multiple dimensions:
- **Decision Stream**: Evolution of architectural choices and superseded standards.
- **Delivery Stream**: Merged pull requests, completed milestones, and deployed features.
- **Risk & Incident Stream**: Surfaced blockers, identified vulnerabilities, and post-mortems.
- **Team Transition Stream**: Onboarding, role handoffs, and departure events.

Exposed endpoint:
`GET /api/v1/projects/{project_id}/relationships/timeline`
