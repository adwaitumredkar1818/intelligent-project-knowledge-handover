"""Lightweight system, process, and cache metrics endpoint."""

from __future__ import annotations

import os
import time
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.deps import get_app_settings
from app.core.config import Settings

metrics_router = APIRouter(prefix="/metrics", tags=["observability"])


class SystemMetricsResponse(BaseModel):
    timestamp_utc: float
    process: dict[str, Any]
    cache: dict[str, Any]
    redis: dict[str, Any]


@metrics_router.get("", response_model=SystemMetricsResponse, summary="Lightweight observability metrics")
def get_observability_metrics(
    request: Request,
    settings: Settings = Depends(get_app_settings),
) -> SystemMetricsResponse:
    """Return lightweight process RSS memory, cache hit ratio, and Redis statistics."""
    cache_service = getattr(request.app.state, "cache_service", None)
    redis_mgr = getattr(request.app.state, "redis_manager", None)

    cache_metrics = cache_service.metrics.snapshot() if cache_service else {}
    redis_info = redis_mgr.get_info() if redis_mgr else {"status": "uninitialized"}

    # Process RSS Memory
    rss_mb = 0.0
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        rss_mb = round(proc.memory_info().rss / (1024 * 1024), 2)
    except Exception:
        # Fallback if psutil is unavailable
        try:
            import resource
            rss_mb = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2)
        except Exception:
            rss_mb = -1.0

    process_info = {
        "pid": os.getpid(),
        "rss_memory_mb": rss_mb,
        "app_env": settings.app_env,
    }

    return SystemMetricsResponse(
        timestamp_utc=time.time(),
        process=process_info,
        cache=cache_metrics,
        redis=redis_info,
    )
