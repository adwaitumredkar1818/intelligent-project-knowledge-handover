"""Cache TTL policies and invalidation scopes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CachePolicy:
    """TTL and invalidation characteristics for cached entities."""

    ttl_seconds: int
    namespace: str
    description: str


class CachePolicies:
    """Standardized TTL policies across application domains."""

    # Dashboard aggregations: short TTL (30s) to balance freshness and DB query overhead
    DASHBOARD_STATS = CachePolicy(
        ttl_seconds=30,
        namespace="dash",
        description="Aggregated project dashboard overview statistics",
    )

    # Project metadata: moderate TTL (120s)
    PROJECT_METADATA = CachePolicy(
        ttl_seconds=120,
        namespace="proj_meta",
        description="Project properties, settings, and workspace summary",
    )

    # RBAC & effective permissions: short TTL (60s) with explicit immediate invalidation
    RBAC_PERMISSIONS = CachePolicy(
        ttl_seconds=60,
        namespace="rbac_perm",
        description="User project/organization effective permissions and role set",
    )

    # Search & hybrid retrieval: short TTL (45s)
    SEARCH_RESULTS = CachePolicy(
        ttl_seconds=45,
        namespace="search",
        description="Deterministic search and hybrid query candidate cache",
    )

    # OCR text results: long TTL (30 days / 2592000s) keyed by content hash + engine + version
    OCR_RESULT = CachePolicy(
        ttl_seconds=2592000,
        namespace="ocr",
        description="Extracted OCR text page-by-page keyed by SHA-256 fingerprint",
    )

    # Chunk embeddings: long TTL (30 days / 2592000s) keyed by chunk hash + model
    CHUNK_EMBEDDING = CachePolicy(
        ttl_seconds=2592000,
        namespace="emb",
        description="Dense vector embedding keyed by chunk text hash and model signature",
    )

    # AI assistant grounded responses: moderate TTL (300s) for identical queries & citations
    AI_RESPONSE = CachePolicy(
        ttl_seconds=300,
        namespace="ai_resp",
        description="Grounded AI response keyed by query, context fingerprint, and prompt",
    )
