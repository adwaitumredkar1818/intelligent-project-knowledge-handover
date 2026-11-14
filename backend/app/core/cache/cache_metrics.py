"""Thread-safe in-memory metrics collector for cache operations."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheMetricsData:
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    fallbacks: int = 0
    latency_ms_total: float = 0.0
    ops_count: int = 0

    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return round(self.hits / total, 4)

    @property
    def avg_latency_ms(self) -> float:
        if self.ops_count == 0:
            return 0.0
        return round(self.latency_ms_total / self.ops_count, 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "fallbacks": self.fallbacks,
            "hit_ratio": self.hit_ratio,
            "avg_latency_ms": self.avg_latency_ms,
            "total_operations": self.ops_count,
        }


class CacheMetricsCollector:
    """Thread-safe metrics tracker for cache performance and latency."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = CacheMetricsData()

    def record_hit(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._data.hits += 1
            self._data.ops_count += 1
            self._data.latency_ms_total += duration_ms

    def record_miss(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._data.misses += 1
            self._data.ops_count += 1
            self._data.latency_ms_total += duration_ms

    def record_set(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._data.sets += 1
            self._data.ops_count += 1
            self._data.latency_ms_total += duration_ms

    def record_delete(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._data.deletes += 1
            self._data.ops_count += 1
            self._data.latency_ms_total += duration_ms

    def record_error(self) -> None:
        with self._lock:
            self._data.errors += 1
            self._data.fallbacks += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._data.to_dict()

    def reset(self) -> None:
        with self._lock:
            self._data = CacheMetricsData()
