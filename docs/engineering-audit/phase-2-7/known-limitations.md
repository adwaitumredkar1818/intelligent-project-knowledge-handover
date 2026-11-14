# Phase 2.7 Audit: Known Limitations and Boundary Conditions

**Document**: `docs/engineering-audit/phase-2-7/known-limitations.md`  
**Phase**: 2.7 — Complete Knowledge Intelligence Engine  
**Status**: DOCUMENTED & ACCEPTED  

---

## 1. Intentional Architectural Boundaries

Phase 2.7 establishes a complete Knowledge Intelligence Engine while explicitly respecting project governance constraints:

1. **No External Graph Database**:
   - Relationships are implemented natively in PostgreSQL using relational indexing.
   - Neo4j or external graph databases were deliberately omitted to prevent operational complexity and dual-write inconsistencies.
2. **Deterministic Person Merge Policy**:
   - Because mistaken identity merges in handover packages can incorrectly assign security credentials or ownership, person merges are strictly manual. No automatic merging is permitted for `person` entities.
3. **Graph Explorer Render Limits**:
   - Graph visualization is capped at 100 nodes per view to prevent client-side WebGL/DOM performance degradation in React Flow.
4. **Source ACL Boundary**:
   - Access to an entity requires access to at least one supporting source. If all supporting sources are restricted to a user, the entity is filtered out of that user's view.
5. **No Production DDL Execution**:
   - All migrations remain locked at revision `0016_rls_hardening`. Zero DDL was executed against the live Supabase database during this phase.
