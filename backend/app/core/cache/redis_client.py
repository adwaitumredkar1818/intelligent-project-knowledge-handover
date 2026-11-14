"""Centralized Redis connection manager and health check."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import redis

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger("app.core.cache.redis_client")


class RedisConnectionManager:
    """Manages thread-safe bounded connection pooling and graceful degradation for Redis."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cfg = settings.redis
        self._pool: redis.ConnectionPool | None = None
        self._client: redis.Redis | None = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the shared bounded connection pool."""
        if not self._cfg.enabled:
            logger.info("Redis cache layer is disabled via REDIS_ENABLED=false.")
            return

        try:
            if self._cfg.url:
                raw_url = self._cfg.url.get_secret_value().strip()
                self._pool = redis.ConnectionPool.from_url(
                    raw_url,
                    max_connections=self._cfg.max_connections,
                    socket_timeout=self._cfg.socket_timeout,
                    socket_connect_timeout=self._cfg.connect_timeout,
                    decode_responses=False,
                )
            else:
                password = (
                    self._cfg.password.get_secret_value()
                    if self._cfg.password
                    else None
                )
                self._pool = redis.ConnectionPool(
                    host=self._cfg.host,
                    port=self._cfg.port,
                    db=self._cfg.db,
                    password=password,
                    max_connections=self._cfg.max_connections,
                    socket_timeout=self._cfg.socket_timeout,
                    socket_connect_timeout=self._cfg.connect_timeout,
                    decode_responses=False,
                )
            self._client = redis.Redis(connection_pool=self._pool)
            # Lightweight ping on startup to verify connectivity
            self._client.ping()
            self._initialized = True
            logger.info(
                "Redis client initialized successfully (%s:%d db=%d pool_size=%d).",
                self._cfg.host,
                self._cfg.port,
                self._cfg.db,
                self._cfg.max_connections,
            )
        except Exception as exc:
            logger.warning(
                "Failed to connect to Redis during startup (%s:%d): %s. "
                "Operating in degraded fail-open mode.",
                self._cfg.host,
                self._cfg.port,
                exc,
            )
            self._initialized = False

    def get_client(self) -> redis.Redis | None:
        """Return the active Redis client or None if unavailable/disabled."""
        if not self._cfg.enabled:
            return None
        if not self._initialized or self._client is None:
            # Attempt lazy reconnection if previous attempt failed
            try:
                self.initialize()
            except Exception:
                return None
        return self._client

    def ping(self) -> bool:
        """Return True if Redis responds to PING."""
        if not self._cfg.enabled:
            return False
        client = self.get_client()
        if client is None:
            return False
        try:
            return bool(client.ping())
        except Exception as exc:
            logger.debug("Redis ping check failed: %s", exc)
            return False

    def get_info(self) -> dict[str, Any]:
        """Fetch Redis server and memory info safely."""
        client = self.get_client()
        if client is None:
            return {"status": "disabled_or_unavailable"}
        try:
            info = client.info(section="memory")
            return {
                "status": "connected",
                "used_memory_human": info.get("used_memory_human"),
                "used_memory_peak_human": info.get("used_memory_peak_human"),
                "maxmemory_human": info.get("maxmemory_human"),
                "maxmemory_policy": info.get("maxmemory_policy"),
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def close(self) -> None:
        """Gracefully release connection pool resources."""
        if self._pool is not None:
            try:
                self._pool.disconnect()
                logger.info("Redis connection pool disconnected gracefully.")
            except Exception as exc:
                logger.debug("Error disconnecting Redis pool: %s", exc)
            finally:
                self._pool = None
                self._client = None
                self._initialized = False
