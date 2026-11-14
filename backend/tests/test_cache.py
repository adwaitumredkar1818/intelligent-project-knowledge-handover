"""Comprehensive unit and integration tests for Redis and multi-layer caching."""

from __future__ import annotations

import time
import uuid
from typing import Any

import pytest
from app.core.cache import (
    CacheKeys,
    CachePolicies,
    CachePolicy,
    CacheService,
    RedisConnectionManager,
)
from app.core.config import Settings, get_settings


@pytest.fixture
def test_settings() -> Settings:
    return get_settings()


@pytest.fixture
def cache_service_fixture(test_settings: Settings) -> CacheService:
    redis_mgr = RedisConnectionManager(test_settings)
    redis_mgr.initialize()
    return CacheService(test_settings, redis_mgr=redis_mgr)


def test_redis_connection_manager_healthy(test_settings: Settings) -> None:
    mgr = RedisConnectionManager(test_settings)
    is_healthy = mgr.ping()
    assert is_healthy is True

    info = mgr.get_info()
    assert info["status"] == "connected"


def test_cache_keys_deterministic() -> None:
    p_id = uuid.uuid4()
    u_id = uuid.uuid4()

    key1 = CacheKeys.dashboard_overview(p_id, u_id)
    key2 = CacheKeys.dashboard_overview(p_id, u_id)
    assert key1 == key2
    assert str(p_id) in key1
    assert str(u_id) in key1

    # Search query key hashing
    skey1 = CacheKeys.search_query(p_id, u_id, "PostgreSQL", 10, 0, {"cat": "db"})
    skey2 = CacheKeys.search_query(p_id, u_id, "postgresql ", 10, 0, {"cat": "db"})
    assert skey1 == skey2  # Query is case and whitespace normalized


def test_cache_service_set_get_delete(cache_service_fixture: CacheService) -> None:
    svc = cache_service_fixture
    test_key = f"test:item:{uuid.uuid4()}"
    data = {"status": "ok", "count": 42, "items": ["a", "b"]}

    # Set
    success = svc.set(test_key, data, ttl=10)
    assert success is True

    # Get
    cached = svc.get(test_key)
    assert cached == data

    # Delete
    deleted = svc.delete(test_key)
    assert deleted is True

    # Verify deleted
    assert svc.get(test_key) is None


def test_cache_service_invalidate_prefix(cache_service_fixture: CacheService) -> None:
    svc = cache_service_fixture
    prefix = f"test:bulk:{uuid.uuid4()}"
    k1 = f"{prefix}:1"
    k2 = f"{prefix}:2"
    k3 = f"{prefix}:3"

    svc.set(k1, {"val": 1}, ttl=30)
    svc.set(k2, {"val": 2}, ttl=30)
    svc.set(k3, {"val": 3}, ttl=30)

    assert svc.get(k1) is not None
    assert svc.get(k2) is not None

    deleted_count = svc.invalidate_prefix(prefix)
    assert deleted_count >= 3

    assert svc.get(k1) is None
    assert svc.get(k2) is None
    assert svc.get(k3) is None


def test_cache_service_fail_open_on_broken_connection(test_settings: Settings) -> None:
    # Build settings with redis.enabled = False using model_copy
    disabled_settings = test_settings.model_copy(
        update={"redis": test_settings.redis.model_copy(update={"enabled": False})}
    )
    disabled_mgr = RedisConnectionManager(disabled_settings)
    failing_svc = CacheService(disabled_settings, redis_mgr=disabled_mgr)

    # When disabled, fail-open returns None
    val = failing_svc.get("any_key")
    assert val is None

    # Set should return False without raising
    saved = failing_svc.set("any_key", {"a": 1})
    assert saved is False


def test_cache_metrics_tracking(cache_service_fixture: CacheService) -> None:
    svc = cache_service_fixture
    key = f"test:metrics:{uuid.uuid4()}"

    # Miss
    svc.get(key)
    # Hit
    svc.set(key, {"sample": "data"}, ttl=10)
    svc.get(key)

    metrics = svc.metrics.snapshot()
    assert metrics["hits"] >= 1
    assert metrics["misses"] >= 1
    assert metrics["hit_ratio"] > 0
    assert metrics["sets"] >= 1
