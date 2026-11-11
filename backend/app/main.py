"""FastAPI application entrypoint and lifecycle wiring."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes.health import root_health_router
from app.api.v1.router import api_v1_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestCorrelationMiddleware
from app.core.rate_limit import InMemorySlidingWindowRateLimiter
from app.db.session import create_db_engine, create_session_factory, verify_database_connection

logger = logging.getLogger(__name__)


def _build_lifespan(
    settings: Settings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        engine = create_db_engine(settings)
        session_factory = create_session_factory(engine)
        http_client = httpx.AsyncClient()

        app.state.settings = settings
        app.state.db_engine = engine
        app.state.session_factory = session_factory
        app.state.http_client = http_client
        if getattr(app.state, "auth_rate_limiter", None) is None:
            app.state.auth_rate_limiter = InMemorySlidingWindowRateLimiter()

        try:
            latency_ms = verify_database_connection(engine)
            logger.info("PostgreSQL startup check succeeded (%.2f ms)", latency_ms)
        except Exception as exc:
            # Allow process boot cleanly in dev/health checks while /health/ready reports 503.
            logger.warning(
                "PostgreSQL unavailable during startup check (%s)",
                type(exc).__name__,
            )

        try:
            yield
        finally:
            await http_client.aclose()
            engine.dispose()
            logger.info("Backend application resources disposed cleanly")

    return lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)

    docs_url = None if active_settings.is_production else "/docs"
    redoc_url = None if active_settings.is_production else "/redoc"
    openapi_url = None if active_settings.is_production else "/openapi.json"

    application = FastAPI(
        title=active_settings.app_name,
        version=__version__,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=_build_lifespan(active_settings),
    )

    # Set attributes upfront so routes inspectable before/without lifespan triggers still see them,
    # while lifespan manages connection pool & client lifecycle cleanly.
    application.state.settings = active_settings
    application.state.auth_rate_limiter = InMemorySlidingWindowRateLimiter()

    register_exception_handlers(application)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID"],
        expose_headers=["X-Request-ID"],
    )
    application.add_middleware(RequestCorrelationMiddleware)

    application.include_router(root_health_router)
    application.include_router(api_v1_router, prefix="/api/v1")

    return application


app = create_app()
