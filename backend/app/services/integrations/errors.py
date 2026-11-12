"""Typed provider, OAuth, rate-limit, and sync exceptions preventing secret leaks."""

from __future__ import annotations

from app.core.logging import redact_sensitive_text


class IntegrationProviderError(Exception):
    """Raised when an external provider HTTP or OAuth operation fails cleanly."""

    def __init__(
        self,
        *,
        provider: str,
        code: str,
        message: str,
        status_code: int | None = None,
        retryable: bool = False,
        retry_after_seconds: int | None = None,
        requires_reauth: bool = False,
    ) -> None:
        safe_message = redact_sensitive_text(message).strip()[:500]
        super().__init__(safe_message)
        self.provider = provider
        self.code = code[:64]
        self.message = safe_message
        self.status_code = status_code
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds
        self.requires_reauth = requires_reauth


class IntegrationRateLimitError(IntegrationProviderError):
    """Raised when GitHub or Atlassian signals quota exhaustion / HTTP 429 backoff."""

    def __init__(
        self,
        *,
        provider: str,
        message: str,
        retry_after_seconds: int = 60,
        status_code: int | None = 429,
    ) -> None:
        super().__init__(
            provider=provider,
            code=f"{provider.upper()}_RATE_LIMITED",
            message=message,
            status_code=status_code,
            retryable=True,
            retry_after_seconds=max(1, retry_after_seconds),
            requires_reauth=False,
        )


class IntegrationAuthError(IntegrationProviderError):
    """Raised when delegated credentials are invalid, expired without refresh, or revoked."""

    def __init__(
        self,
        *,
        provider: str,
        code: str,
        message: str,
        status_code: int | None = 401,
    ) -> None:
        super().__init__(
            provider=provider,
            code=code,
            message=message,
            status_code=status_code,
            retryable=False,
            retry_after_seconds=None,
            requires_reauth=True,
        )
