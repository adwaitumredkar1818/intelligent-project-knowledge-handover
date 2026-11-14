"""Cache package exports."""

from __future__ import annotations

from app.core.cache.cache_keys import CacheKeys
from app.core.cache.cache_metrics import CacheMetricsCollector
from app.core.cache.cache_policies import CachePolicies, CachePolicy
from app.core.cache.cache_service import CacheService
from app.core.cache.redis_client import RedisConnectionManager
from app.core.config import get_settings

_default_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
    """Return the global default CacheService instance, lazily initialized."""
    global _default_cache_service
    if _default_cache_service is None:
        settings = get_settings()
        _default_cache_service = CacheService(settings)
    return _default_cache_service


class _CacheServiceProxy:
    """Thread-safe proxy redirecting attribute access to get_cache_service()."""

    def __getattr__(self, name: str):
        return getattr(get_cache_service(), name)


cache_service = _CacheServiceProxy()

__all__ = [
    "CacheKeys",
    "CacheMetricsCollector",
    "CachePolicies",
    "CachePolicy",
    "CacheService",
    "RedisConnectionManager",
    "cache_service",
    "get_cache_service",
]
