"""High-level caching service providing fail-open semantics, serialization, and invalidation."""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from app.core.cache.cache_metrics import CacheMetricsCollector
from app.core.cache.cache_policies import CachePolicy
from app.core.cache.redis_client import RedisConnectionManager

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger("app.core.cache.cache_service")
T = TypeVar("T")


class CacheService:
    """Application-level cache abstraction decoupling business logic from direct Redis calls."""

    def __init__(
        self,
        settings: Settings,
        redis_mgr: RedisConnectionManager | None = None,
        metrics: CacheMetricsCollector | None = None,
    ) -> None:
        self._settings = settings
        self._redis_mgr = redis_mgr or RedisConnectionManager(settings)
        self._metrics = metrics or CacheMetricsCollector()
        self._prefix = settings.redis.cache_prefix

    @property
    def metrics(self) -> CacheMetricsCollector:
        return self._metrics

    def _qualify_key(self, raw_key: str) -> str:
        return f"{self._prefix}{raw_key}"

    def get(self, key: str) -> Any | None:
        """Fetch and deserialize JSON value from cache with fail-open error handling."""
        client = self._redis_mgr.get_client()
        if client is None:
            self._metrics.record_error()
            return None

        t0 = time.perf_counter()
        qkey = self._qualify_key(key)
        try:
            raw_bytes = client.get(qkey)
            duration_ms = (time.perf_counter() - t0) * 1000.0
            if raw_bytes is None:
                self._metrics.record_miss(duration_ms)
                return None
            data = json.loads(raw_bytes.decode("utf-8"))
            self._metrics.record_hit(duration_ms)
            return data
        except Exception as exc:
            logger.warning("Cache GET failed for key '%s': %s (failing open)", key, exc)
            self._metrics.record_error()
            return None

    def set(
        self,
        key: str,
        value: Any,
        policy: CachePolicy | None = None,
        ttl_seconds: int | None = None,
        ttl: int | None = None,
    ) -> bool:
        """Serialize and persist value to cache with fail-open behavior."""
        client = self._redis_mgr.get_client()
        if client is None:
            self._metrics.record_error()
            return False

        effective_ttl = ttl if ttl is not None else ttl_seconds
        if effective_ttl is None:
            effective_ttl = policy.ttl_seconds if policy else self._settings.redis.default_ttl
        elif isinstance(effective_ttl, CachePolicy):
            effective_ttl = effective_ttl.ttl_seconds

        t0 = time.perf_counter()
        qkey = self._qualify_key(key)
        try:
            payload = json.dumps(value, default=str).encode("utf-8")
            client.set(qkey, payload, ex=effective_ttl)
            duration_ms = (time.perf_counter() - t0) * 1000.0
            self._metrics.record_set(duration_ms)
            return True
        except Exception as exc:
            logger.warning("Cache SET failed for key '%s': %s", key, exc)
            self._metrics.record_error()
            return False

    def delete(self, key: str) -> bool:
        """Delete specific key from cache."""
        client = self._redis_mgr.get_client()
        if client is None:
            return False

        t0 = time.perf_counter()
        qkey = self._qualify_key(key)
        try:
            client.delete(qkey)
            duration_ms = (time.perf_counter() - t0) * 1000.0
            self._metrics.record_delete(duration_ms)
            return True
        except Exception as exc:
            logger.warning("Cache DELETE failed for key '%s': %s", key, exc)
            self._metrics.record_error()
            return False

    def invalidate_prefix(self, pattern_suffix: str) -> int:
        """Scan and delete all keys matching a specific pattern prefix."""
        client = self._redis_mgr.get_client()
        if client is None:
            return 0

        pattern = f"{self._prefix}{pattern_suffix}*"
        deleted_count = 0
        try:
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    deleted = client.delete(*keys)
                    deleted_count += deleted
                if cursor == 0:
                    break
            if deleted_count > 0:
                logger.debug("Invalidated %d cache keys for pattern '%s'", deleted_count, pattern)
            return deleted_count
        except Exception as exc:
            logger.warning("Cache prefix invalidation failed for '%s': %s", pattern, exc)
            return 0

    def get_or_set(
        self,
        key: str,
        producer: Callable[[], T],
        policy: CachePolicy | None = None,
        ttl_seconds: int | None = None,
    ) -> T:
        """Transparent read-through caching pattern."""
        cached = self.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        result = producer()
        if result is not None:
            self.set(key, result, policy=policy, ttl_seconds=ttl_seconds)
        return result
