"""Infrastructure liveness and dependency readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.deps import get_app_settings, get_health_service, get_request_id
from app.core.config import Settings
from app.schemas.health import HealthResponse, ReadinessResponse
from app.services.health import HealthService

root_health_router = APIRouter(tags=["health"])
v1_health_router = APIRouter(tags=["health"])


@root_health_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application process liveness check",
)
def get_root_health(
    settings: Settings = Depends(get_app_settings),  # noqa: B008
    request_id: str = Depends(get_request_id),
) -> HealthResponse:
    """Confirm the FastAPI process is up and accepting requests."""
    return HealthService.build_liveness(settings=settings, request_id=request_id)


@root_health_router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadinessResponse,
            "description": "Required PostgreSQL dependency is unavailable.",
        }
    },
    summary="Dependency-aware readiness check",
)
async def get_readiness(
    health_service: HealthService = Depends(get_health_service),  # noqa: B008
    request_id: str = Depends(get_request_id),
) -> JSONResponse:
    """Verify PostgreSQL readiness and report optional external AI/vector service state."""
    report = await health_service.check_readiness(request_id=request_id)
    http_status = (
        status.HTTP_503_SERVICE_UNAVAILABLE
        if report.status == "unavailable"
        else status.HTTP_200_OK
    )
    return JSONResponse(status_code=http_status, content=report.model_dump(mode="json"))


@v1_health_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Versioned API v1 liveness check",
)
def get_v1_health(
    settings: Settings = Depends(get_app_settings),  # noqa: B008
    request_id: str = Depends(get_request_id),
) -> HealthResponse:
    """Confirm the versioned `/api/v1` router is active."""
    return HealthService.build_liveness(settings=settings, request_id=request_id)
