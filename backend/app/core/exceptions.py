"""Structured application exceptions and safe FastAPI error handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_correlation_id, reset_correlation_id, set_correlation_id
from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base expected application error mapped directly to a safe HTTP JSON response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "APPLICATION_ERROR",
        details: list[dict[str, Any]] | dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        clear_refresh_cookie: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        self.headers = headers
        self.clear_refresh_cookie = clear_refresh_cookie


class BadRequestError(AppError):
    """Expected 400 error for invalid client input or domain state."""

    def __init__(
        self,
        message: str = "Invalid request.",
        *,
        code: str = "BAD_REQUEST",
        details: list[dict[str, Any]] | dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code=code,
            details=details,
        )


class UnauthorizedError(AppError):
    """Expected 401 error when authentication credentials are missing, invalid, or revoked."""

    def __init__(
        self,
        message: str = "Authentication credentials were not provided or are invalid.",
        *,
        code: str = "UNAUTHORIZED",
        details: list[dict[str, Any]] | dict[str, Any] | None = None,
        clear_refresh_cookie: bool = False,
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=code,
            details=details,
            headers={"WWW-Authenticate": "Bearer"},
            clear_refresh_cookie=clear_refresh_cookie,
        )


class ForbiddenError(AppError):
    """Expected 403 error when an authenticated user lacks required permissions or CSRF fails."""

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        *,
        code: str = "FORBIDDEN",
        details: list[dict[str, Any]] | dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_403_FORBIDDEN,
            code=code,
            details=details,
        )


class TooManyRequestsError(AppError):
    """Expected 429 error when rate limits are exceeded."""

    def __init__(
        self,
        message: str = "Too many authentication requests. Please retry later.",
        *,
        code: str = "RATE_LIMIT_EXCEEDED",
        retry_after_seconds: int = 60,
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code=code,
            headers={"Retry-After": str(max(1, retry_after_seconds))},
        )


class NotFoundError(AppError):
    """Expected 404 error when a requested resource does not exist."""

    def __init__(
        self,
        message: str = "Requested resource was not found.",
        *,
        code: str = "NOT_FOUND",
        details: list[dict[str, Any]] | dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_404_NOT_FOUND,
            code=code,
            details=details,
        )


class ConflictError(AppError):
    """Expected 409 error for state or uniqueness conflicts."""

    def __init__(
        self,
        message: str = "Resource conflict.",
        *,
        code: str = "CONFLICT",
        details: list[dict[str, Any]] | dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_409_CONFLICT,
            code=code,
            details=details,
        )


class GoneError(AppError):
    """Expected 410 error when a time-bound token or resource has expired."""

    def __init__(
        self,
        message: str = "Requested resource is no longer available.",
        *,
        code: str = "GONE",
        details: list[dict[str, Any]] | dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_410_GONE,
            code=code,
            details=details,
        )


class PayloadTooLargeError(AppError):
    """Expected 413 error when an uploaded payload exceeds configured size bounds."""

    def __init__(
        self,
        message: str = "Uploaded payload exceeds the maximum permitted size.",
        *,
        code: str = "PAYLOAD_TOO_LARGE",
        details: list[dict[str, Any]] | dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            code=code,
            details=details,
        )


class UnsupportedMediaTypeError(AppError):
    """Expected 415 error when an uploaded file type fails MIME or magic-byte checks."""

    def __init__(
        self,
        message: str = "Unsupported media type.",
        *,
        code: str = "UNSUPPORTED_MEDIA_TYPE",
        details: list[dict[str, Any]] | dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code=code,
            details=details,
        )


class UnprocessableEntityError(AppError):
    """Expected 422 error when document structure is malformed or invalid."""

    def __init__(
        self,
        message: str = "Submitted document could not be processed.",
        *,
        code: str = "UNPROCESSABLE_DOCUMENT",
        details: list[dict[str, Any]] | dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code=code,
            details=details,
        )


class ServiceUnavailableError(AppError):
    """Expected 503 error when a required core dependency is unavailable."""

    def __init__(
        self,
        message: str = "Service temporarily unavailable.",
        *,
        code: str = "SERVICE_UNAVAILABLE",
        details: list[dict[str, Any]] | dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=code,
            details=details,
        )


def _request_id_for(request: Request) -> str:
    state_id = getattr(request.state, "request_id", None)
    return str(state_id) if state_id else get_correlation_id()


def _build_error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | dict[str, Any] | None = None,
    extra_headers: dict[str, str] | None = None,
    clear_refresh_cookie: bool = False,
) -> JSONResponse:
    request_id = _request_id_for(request)
    body = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            request_id=request_id,
            details=details,
        )
    )
    response_headers = {
        "X-Request-ID": request_id,
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }
    if extra_headers:
        response_headers.update(extra_headers)
    response = JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
        headers=response_headers,
    )
    if clear_refresh_cookie:
        settings = getattr(request.app.state, "settings", None)
        if settings is not None:
            sec = settings.security
            response.delete_cookie(
                key=sec.refresh_cookie_name,
                path=sec.refresh_cookie_path,
                domain=sec.cookie_domain,
                secure=sec.cookie_secure,
                httponly=True,
                samesite=sec.cookie_samesite,
            )
    return response


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    """Handle expected domain/application errors cleanly without stack trace noise."""
    log_level = logging.WARNING if exc.status_code >= 500 else logging.INFO
    logger.log(
        log_level,
        "Expected application error: %s",
        exc.message,
        extra={
            "http_method": request.method,
            "http_path": request.url.path,
            "status_code": exc.status_code,
            "error_code": exc.code,
        },
    )
    return _build_error_response(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        extra_headers=exc.headers,
        clear_refresh_cookie=exc.clear_refresh_cookie,
    )


async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Normalise framework HTTP errors (404, 405, etc.) into canonical ErrorResponse JSON."""
    code = f"HTTP_{exc.status_code}"
    message = exc.detail if isinstance(exc.detail, str) else "HTTP request failed."
    logger.info(
        "HTTP exception returned",
        extra={
            "http_method": request.method,
            "http_path": request.url.path,
            "status_code": exc.status_code,
            "error_code": code,
        },
    )
    return _build_error_response(
        request=request,
        status_code=exc.status_code,
        code=code,
        message=message,
    )


async def handle_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return sanitised Pydantic request validation details without echoing raw inputs."""
    sanitised_errors: list[dict[str, Any]] = [
        {
            "loc": list(err.get("loc", ())),
            "msg": str(err.get("msg", "Invalid value.")),
            "type": str(err.get("type", "validation_error")),
        }
        for err in exc.errors()
    ]
    logger.info(
        "Request validation error",
        extra={
            "http_method": request.method,
            "http_path": request.url.path,
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "error_code": "VALIDATION_ERROR",
        },
    )
    return _build_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details=sanitised_errors,
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Catch unexpected server exceptions and return a redacted generic 500 JSON payload."""
    request_id = _request_id_for(request)
    token = set_correlation_id(request_id)
    try:
        logger.exception(
            "Unhandled server exception during request processing",
            exc_info=exc,
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "error_code": "INTERNAL_SERVER_ERROR",
            },
        )
    finally:
        reset_correlation_id(token)
    return _build_error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal server error occurred.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers onto the FastAPI instance."""
    app.add_exception_handler(AppError, handle_app_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, handle_unexpected_error)
