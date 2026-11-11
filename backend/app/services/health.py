"""Health and readiness orchestration across application, PostgreSQL, ChromaDB, and Ollama."""

from __future__ import annotations

import asyncio
import logging
import time

import httpx
from fastapi.concurrency import run_in_threadpool

from app.core.config import Settings
from app.repositories.system import SystemRepository
from app.schemas.health import (
    ApplicationProcessStatus,
    DependencyHealth,
    ExternalServicesHealth,
    HealthResponse,
    OverallReadinessStatus,
    ReadinessResponse,
)

logger = logging.getLogger(__name__)


async def _probe_http_service(
    client: httpx.AsyncClient,
    *,
    url: str,
    timeout_seconds: float,
    service_label: str,
    required: bool = False,
    headers: dict[str, str] | None = None,
) -> DependencyHealth:
    """Probe an external HTTP service safely without leaking internal URLs or exceptions."""
    started_at = time.perf_counter()
    try:
        response = await client.get(url, headers=headers, timeout=timeout_seconds)
        latency_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
        if response.is_success:
            return DependencyHealth(
                status="ok",
                required=required,
                latency_ms=latency_ms,
                message="Reachable",
            )
        logger.warning(
            "Optional external service %s returned non-2xx status %s",
            service_label,
            response.status_code,
        )
        return DependencyHealth(
            status="unavailable",
            required=required,
            latency_ms=latency_ms,
            message=f"{service_label} service returned an unexpected status.",
        )
    except httpx.HTTPError as exc:
        logger.warning(
            "Optional external service %s health check failed (%s)",
            service_label,
            type(exc).__name__,
        )
        return DependencyHealth(
            status="unavailable",
            required=required,
            latency_ms=None,
            message=f"{service_label} service unreachable.",
        )


class HealthService:
    """Coordinates lightweight liveness and dependency-aware readiness checks."""

    def __init__(
        self,
        *,
        settings: Settings,
        system_repository: SystemRepository,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._settings = settings
        self._system_repository = system_repository
        self._http_client = http_client

    @staticmethod
    def build_liveness(*, settings: Settings, request_id: str) -> HealthResponse:
        """Return process liveness metadata without opening database or HTTP connections."""
        return HealthResponse(
            status="ok",
            service=settings.app_name,
            environment=settings.app_env,
            api_version="v1",
            request_id=request_id,
        )

    def get_liveness(self, *, request_id: str) -> HealthResponse:
        """Return process liveness metadata without hitting external dependencies."""
        return self.build_liveness(settings=self._settings, request_id=request_id)

    async def check_readiness(self, *, request_id: str) -> ReadinessResponse:
        """Check required PostgreSQL connectivity alongside optional Ollama & ChromaDB status."""
        ollama_cfg = self._settings.ollama
        chroma_cfg = self._settings.chroma

        chroma_headers: dict[str, str] | None = None
        if chroma_cfg.auth_token is not None:
            chroma_headers = {"Authorization": f"Bearer {chroma_cfg.auth_token.get_secret_value()}"}

        db_task = run_in_threadpool(self._system_repository.ping)
        ollama_task = _probe_http_service(
            self._http_client,
            url=f"{ollama_cfg.base_url}/api/version",
            timeout_seconds=ollama_cfg.health_timeout_seconds,
            service_label="Ollama AI",
            required=False,
        )
        chroma_task = _probe_http_service(
            self._http_client,
            url=f"{chroma_cfg.base_url}/api/v2/heartbeat",
            timeout_seconds=chroma_cfg.health_timeout_seconds,
            service_label="ChromaDB",
            required=False,
            headers=chroma_headers,
        )

        (db_ok, db_latency_ms), ollama_health, chroma_health = await asyncio.gather(
            db_task,
            ollama_task,
            chroma_task,
        )

        database_health = DependencyHealth(
            status="ok" if db_ok else "unavailable",
            required=True,
            latency_ms=db_latency_ms,
            message="Reachable" if db_ok else "Database connectivity check failed.",
        )

        overall_status: OverallReadinessStatus
        if not db_ok:
            overall_status = "unavailable"
        elif ollama_health.status != "ok" or chroma_health.status != "ok":
            overall_status = "degraded"
        else:
            overall_status = "ready"

        return ReadinessResponse(
            status=overall_status,
            request_id=request_id,
            application=ApplicationProcessStatus(status="ok"),
            database=database_health,
            external_services=ExternalServicesHealth(
                ollama=ollama_health,
                chromadb=chroma_health,
            ),
        )
