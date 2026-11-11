"""Centralised structured logging with request correlation IDs and secret redaction."""

from __future__ import annotations

import json
import logging
import re
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

_correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)

_REDACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Mask userinfo credentials in database or service URLs (e.g. ://user:pass@host)
    (re.compile(r"(://[^:\s/@]+:)([^@\s]+)(@)"), r"\1[REDACTED]\3"),
    # Mask Authorization Bearer tokens
    (re.compile(r"(?i)\b(Bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1[REDACTED]"),
    # Mask Argon2 / bcrypt password hash digests if ever present
    (re.compile(r"\$argon2(?:id|i|d)?\$[^\s,;\"']+"), "[REDACTED]"),
    # Mask common key=value or key: value secret pairs
    (
        re.compile(
            r"(?i)\b(password|passwd|password_hash|secret|jwt_secret_key|token|access_token|"
            r"refresh_token|invitation_token|development_invitation_token|raw_token|"
            r"token_hash|api_key|authorization|cookie|set-cookie)\s*([=:])\s*([^\s,;]+)"
        ),
        r"\1\2[REDACTED]",
    ),
)


def get_correlation_id() -> str:
    """Return the active request correlation ID, or '-' outside request scope."""
    return _correlation_id_ctx.get() or "-"


def set_correlation_id(correlation_id: str | None) -> Token[str | None]:
    """Bind a correlation ID into the current async/thread context."""
    return _correlation_id_ctx.set(correlation_id)


def reset_correlation_id(token: Token[str | None]) -> None:
    """Restore previous correlation ID context."""
    _correlation_id_ctx.reset(token)


def redact_sensitive_text(value: str) -> str:
    """Redact credentials, tokens, and URL passwords from arbitrary log text."""
    redacted = value
    for pattern, replacement in _REDACTION_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


class SensitiveDataFilter(logging.Filter):
    """Attach correlation ID and scrub secret patterns before formatting records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: redact_sensitive_text(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_sensitive_text(v) if isinstance(v, str) else v
                    for v in record.args
                )
        return True


class StructuredJsonFormatter(logging.Formatter):
    """Render single-line structured JSON logs with timestamp and correlation ID."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "correlation_id", get_correlation_id()),
            "message": redact_sensitive_text(record.getMessage()),
        }
        for key in (
            "http_method",
            "http_path",
            "status_code",
            "duration_ms",
            "error_code",
            "event_type",
            "outcome",
            "actor_user_id",
            "organisation_id",
            "project_id",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            payload["exception"] = redact_sensitive_text(exc_text)
        return json.dumps(payload, default=str)


def configure_logging(log_level: str = "INFO") -> None:
    """Configure root and application loggers once without duplicate handlers."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(StructuredJsonFormatter())
    handler.addFilter(SensitiveDataFilter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Normalise Uvicorn/FastAPI loggers onto root handler to prevent double logging.
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "alembic"):
        target = logging.getLogger(logger_name)
        target.handlers.clear()
        target.propagate = True
        target.setLevel(level)

    # Keep transport HTTP client logs at WARNING+ so internal service URLs stay out of INFO logs.
    for client_logger_name in ("httpx", "httpcore"):
        client_logger = logging.getLogger(client_logger_name)
        client_logger.handlers.clear()
        client_logger.propagate = True
        client_logger.setLevel(max(level, logging.WARNING))


_security_audit_logger = logging.getLogger("app.security.audit")


def log_security_event(
    *,
    event_type: str,
    outcome: str,
    message: str,
    actor_user_id: str | None = None,
    organisation_id: str | None = None,
    project_id: str | None = None,
    level: int = logging.INFO,
) -> None:
    """Emit a structured security audit event without exposing tokens, cookies, or secrets."""
    extra: dict[str, Any] = {
        "event_type": event_type,
        "outcome": outcome,
    }
    if actor_user_id is not None:
        extra["actor_user_id"] = actor_user_id
    if organisation_id is not None:
        extra["organisation_id"] = organisation_id
    if project_id is not None:
        extra["project_id"] = project_id
    _security_audit_logger.log(level, message, extra=extra)
