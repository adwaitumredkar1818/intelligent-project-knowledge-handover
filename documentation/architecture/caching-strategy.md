# Caching Strategy — The Handover Platform

## 1. Objectives

The caching strategy eliminates redundant database calculations, expensive LLM inferences, and duplicate vector embedding operations while guaranteeing strict tenant isolation, security boundaries, and authorization adherence.

## 2. Cache Key Namespacing & Security Rules

All cache keys adhere to deterministic, collision-resistant namespacing defined in `app.core.cache.CacheKeys`:

```python
# Dashboard Overview
dash:overview:proj:{project_id}:user:{user_id}

# Project Metadata
proj_meta:id:{project_id}

# RBAC Permissions
rbac:perm:proj:{project_id}:user:{user_id}
rbac:perm:org:{organisation_id}:user:{user_id}

# Search Results
search:proj:{project_id}:user:{user_id}:q:{query_hash}:lim:{limit}:off:{offset}:f:{filter_hash}

# Chunk Embeddings (Deduplicated across all documents)
emb:chash:{chunk_content_hash}:m:{model_name}:d:{dimensions}

# OCR Pages (Deduplicated across identical page renders)
ocr:chash:{image_content_hash}:p:{page_number}:eng:{engine}:v:{version}
```

### Security Safeguards:
1. **Zero Secret Leakage**: Raw JWTs, credentials, and API keys are never embedded in cache keys or values.
2. **Permission Boundary**: Cached search results and dashboard overviews are strictly user-scoped to enforce read-time source ACLs.
3. **Fail-Open Fallback**: Any Redis connection failure or serialization error safely logs a warning and falls back to canonical database retrieval without raising uncaught exceptions to callers.

---

## 3. Invalidation Rules

- **Project Member Mutation (`add_project_member`, `update_project_member_role`, `remove_project_member`)**:
  - Invalidates `dash:overview:proj:{project_id}*`
  - Deletes `rbac:perm:proj:{project_id}:user:{target_user_id}`
- **Evidence Ingestion**:
  - Invalidates `dash:overview:proj:{project_id}*`
  - Clears `search:proj:{project_id}*`
- **Handover Assembly & Verification**:
  - Emits real-time database transactions ensuring no stale cache state affects human sign-offs.
