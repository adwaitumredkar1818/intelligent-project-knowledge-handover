"""Pydantic schemas for application liveness and dependency readiness endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import BaseSchema

ServiceStatus = Literal["ok", "unavailable"]
OverallReadinessStatus = Literal["ready", "degraded", "unavailable"]


class HealthResponse(BaseSchema):
    """Response payload for lightweight application liveness endpoints."""

    status: Literal["ok"] = "ok"
    service: str
    environment: str
    api_version: str = "v1"
    request_id: str


class ApplicationProcessStatus(BaseSchema):
    """Status of the running FastAPI application process."""

    status: Literal["ok"] = "ok"


class DependencyHealth(BaseSchema):
    """Sanitised connectivity state for a required or optional external dependency."""

    status: ServiceStatus
    required: bool
    latency_ms: float | None = Field(default=None, ge=0.0)
    message: str


class ExternalServicesHealth(BaseSchema):
    """Grouped readiness state for non-core / AI infrastructure services."""

    ollama: DependencyHealth
    chromadb: DependencyHealth


class ReadinessResponse(BaseSchema):
    """Response payload for dependency-aware readiness checks."""

    status: OverallReadinessStatus
    request_id: str
    application: ApplicationProcessStatus
    database: DependencyHealth
    external_services: ExternalServicesHealth
