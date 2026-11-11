"""Pluggable authentication rate-limiting strategy with an in-process default."""

from __future__ import annotations

import hashlib
import math
import threading
import time
from collections import deque
from typing import Protocol

from fastapi import Request

from app.core.config import Settings
from app.core.exceptions import TooManyRequestsError
from app.core.logging import log_security_event


class RateLimiterProtocol(Protocol):
    """Contract allowing future replacement with a distributed proxy/DB limiter."""

    def check_rate_limit(
        self,
        bucket_key: str,
        *,
        max_attempts: int,
        window_seconds: int,
    ) -> int | None:
        """Record an attempt and return Retry-After seconds if exceeded, else None."""
        ...


class InMemorySlidingWindowRateLimiter:
    """Thread-safe single-process sliding-window rate limiter for local/MVP auth routes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._attempts: dict[str, deque[float]] = {}

    def check_rate_limit(
        self,
        bucket_key: str,
        *,
        max_attempts: int,
        window_seconds: int,
    ) -> int | None:
        now = time.monotonic()
        cutoff = now - float(window_seconds)

        with self._lock:
            timestamps = self._attempts.get(bucket_key)
            if timestamps is None:
                timestamps = deque()
                self._attempts[bucket_key] = timestamps

            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= max_attempts:
                oldest = timestamps[0]
                retry_after = max(1, math.ceil(float(window_seconds) - (now - oldest)))
                return retry_after

            timestamps.append(now)

            # Prune stale keys opportunistically to keep memory bounded.
            if len(self._attempts) > 4096:
                stale_keys = [
                    key
                    for key, queue in self._attempts.items()
                    if not queue or queue[-1] <= cutoff
                ]
                for stale_key in stale_keys:
                    self._attempts.pop(stale_key, None)

        return None


def _anonymised_client_key(request: Request, action: str) -> str:
    client_host = request.client.host if request.client and request.client.host else "unknown"
    host_digest = hashlib.sha256(client_host.encode("utf-8")).hexdigest()[:16]
    return f"{action}:{host_digest}"


def check_auth_rate_limit(
    *,
    request: Request,
    settings: Settings,
    limiter: RateLimiterProtocol | None,
    action: str,
) -> None:
    """Enforce configurable rate limits cleanly without storing raw client IPs."""
    sec = settings.security
    if not sec.auth_rate_limit_enabled or limiter is None:
        return

    bucket_key = _anonymised_client_key(request, action)
    retry_after = limiter.check_rate_limit(
        bucket_key,
        max_attempts=sec.auth_rate_limit_max_attempts,
        window_seconds=sec.auth_rate_limit_window_seconds,
    )
    if retry_after is not None:
        log_security_event(
            event_type=f"auth.rate_limited.{action}",
            outcome="denied",
            message=f"Rate limit exceeded for auth action '{action}'.",
        )
        raise TooManyRequestsError(retry_after_seconds=retry_after)
