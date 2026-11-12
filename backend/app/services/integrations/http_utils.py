"""Shared HTTP client, datetime normalisation, and provider error-mapping helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from app.services.integrations.errors import (
    IntegrationAuthError,
    IntegrationProviderError,
    IntegrationRateLimitError,
)


def create_integration_http_client(
    *,
    timeout_seconds: float,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    """Create a bounded synchronous HTTPX client with optional mock transport injection."""
    kwargs: dict[str, object] = {
        "timeout": timeout_seconds,
        "follow_redirects": False,
    }
    if transport is not None:
        kwargs["transport"] = transport
    return httpx.Client(**kwargs)  # type: ignore[arg-type]


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Normalise naive SQLite datetimes to UTC so comparisons are always timezone-safe."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def parse_provider_datetime(value: str | None) -> datetime | None:
    """Parse ISO-8601 provider timestamps cleanly to UTC datetime."""
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
        return ensure_utc(parsed)
    except ValueError:
        return None


def parse_retry_after_seconds(
    headers: httpx.Headers,
    *,
    now: datetime | None = None,
    default: int = 60,
    max_seconds: int = 900,
) -> int:
    """Derive bounded retry delay from Retry-After or X-RateLimit-Reset headers."""
    reference_now = ensure_utc(now) or datetime.now(UTC)
    retry_after = headers.get("retry-after")
    if retry_after:
        cleaned = retry_after.strip()
        if cleaned.isdigit():
            return max(1, min(max_seconds, int(cleaned)))
        try:
            retry_dt = parsedate_to_datetime(cleaned)
            retry_utc = ensure_utc(retry_dt)
            if retry_utc is not None:
                delta = int((retry_utc - reference_now).total_seconds())
                return max(1, min(max_seconds, delta))
        except (TypeError, ValueError):
            pass

    reset_header = headers.get("x-ratelimit-reset")
    if reset_header and reset_header.strip().isdigit():
        reset_epoch = int(reset_header.strip())
        now_epoch = int(reference_now.timestamp())
        if reset_epoch > now_epoch:
            return max(1, min(max_seconds, reset_epoch - now_epoch))

    return max(1, min(max_seconds, default))


def is_rate_limit_response(response: httpx.Response) -> bool:
    """Detect primary and secondary rate-limit responses from GitHub and Atlassian."""
    if response.status_code == 429:
        return True
    if response.status_code == 403:
        if response.headers.get("retry-after"):
            return True
        if response.headers.get("x-ratelimit-remaining") == "0":
            return True
        lowered = response.text.lower()
        if "rate limit" in lowered or "secondary rate limit" in lowered:
            return True
    return False


def raise_for_provider_error(
    response: httpx.Response,
    *,
    provider: str,
    endpoint_label: str,
) -> None:
    """Map HTTP failures onto typed IntegrationProviderError subclasses without leaking secrets."""
    status = response.status_code
    if status < 400:
        return

    if is_rate_limit_response(response):
        retry_after = parse_retry_after_seconds(response.headers)
        raise IntegrationRateLimitError(
            provider=provider,
            message=f"{provider.title()} API rate limit encountered at {endpoint_label}.",
            retry_after_seconds=retry_after,
            status_code=status,
        )

    if status == 401:
        raise IntegrationAuthError(
            provider=provider,
            code=f"{provider.upper()}_UNAUTHORISED",
            message=(
                f"{provider.title()} rejected delegated access credentials at {endpoint_label}."
            ),
            status_code=401,
        )

    retryable = status >= 500 or status == 408
    raise IntegrationProviderError(
        provider=provider,
        code=f"{provider.upper()}_HTTP_{status}",
        message=f"{provider.title()} API returned HTTP {status} during {endpoint_label}.",
        status_code=status,
        retryable=retryable,
    )
