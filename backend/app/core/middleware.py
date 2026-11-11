"""HTTP middleware for request correlation IDs, security headers, and safe request logging."""

from __future__ import annotations

import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import reset_correlation_id, set_correlation_id

logger = logging.getLogger(__name__)

_SAFE_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _extract_or_generate_request_id(request: Request) -> str:
    candidate = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
    if candidate:
        trimmed = candidate.strip()
        if _SAFE_REQUEST_ID_RE.fullmatch(trimmed):
            return trimmed
    return str(uuid.uuid4())


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """Bind request correlation IDs, log safe request summaries, and apply security headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _extract_or_generate_request_id(request)
        request.state.request_id = request_id
        ctx_token = set_correlation_id(request_id)
        started_at = time.perf_counter()

        try:
            response = await call_next(request)
        finally:
            reset_correlation_id(ctx_token)

        duration_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        # Log path/method/status/duration only — never query strings, headers, cookies, or bodies.
        log_token = set_correlation_id(request_id)
        try:
            logger.info(
                "HTTP request completed",
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
        finally:
            reset_correlation_id(log_token)

        return response
