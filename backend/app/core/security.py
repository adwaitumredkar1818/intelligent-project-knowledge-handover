"""Core authentication security primitives: Argon2id, JWT, refresh tokens, cookies, and CSRF."""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import jwt
from fastapi import Request, Response
from jwt.types import Options
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import Settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.logging import log_security_event
from app.core.validators import (
    derive_slug_from_name,
    ensure_utc,
    normalize_and_validate_email,
    normalize_and_validate_slug,
    normalize_display_name,
    utc_now,
    validate_password_strength,
)

__all__ = [
    "AccessTokenClaims",
    "clear_refresh_cookie",
    "create_access_token",
    "decode_access_token",
    "derive_slug_from_name",
    "ensure_utc",
    "generate_opaque_token",
    "generate_refresh_token",
    "hash_opaque_token",
    "hash_password",
    "hash_refresh_token",
    "normalize_and_validate_email",
    "normalize_and_validate_slug",
    "normalize_display_name",
    "set_refresh_cookie",
    "utc_now",
    "validate_csrf_origin",
    "validate_password_strength",
    "verify_dummy_password",
    "verify_password",
]

_PASSWORD_HASHER = PasswordHash((Argon2Hasher(),))
_DUMMY_PASSWORD_HASH: str = _PASSWORD_HASHER.hash(secrets.token_urlsafe(24))


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _PASSWORD_HASHER.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against its stored Argon2id digest."""
    if not plain_password or not password_hash:
        return False
    try:
        return bool(_PASSWORD_HASHER.verify(plain_password, password_hash))
    except Exception:
        return False


def verify_dummy_password(plain_password: str) -> None:
    """Execute constant-cost Argon2id verification to reduce user-enumeration timing leaks."""
    verify_password(plain_password, _DUMMY_PASSWORD_HASH)


def generate_opaque_token(nbytes: int = 48) -> str:
    """Generate a high-entropy cryptographically random URL-safe opaque secret."""
    return secrets.token_urlsafe(nbytes)


def hash_opaque_token(raw_token: str) -> str:
    """Return the deterministic 64-character SHA-256 hex digest stored in PostgreSQL."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_refresh_token() -> str:
    """Generate a high-entropy cryptographically random opaque refresh token."""
    return generate_opaque_token(48)


def hash_refresh_token(raw_token: str) -> str:
    """Return the deterministic SHA-256 hex digest stored in PostgreSQL."""
    return hash_opaque_token(raw_token)


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Validated claims extracted from a FastAPI-issued JWT access token."""

    subject: uuid.UUID
    session_family_id: uuid.UUID
    jti: str
    issued_at: datetime
    expires_at: datetime


def create_access_token(
    *,
    user_id: uuid.UUID,
    session_family_id: uuid.UUID,
    settings: Settings,
    now: datetime | None = None,
) -> tuple[str, int]:
    """Sign a short-lived JWT access token containing minimum identity and session claims."""
    sec = settings.security
    issued_at = ensure_utc(now) if now is not None else utc_now()
    expires_in_seconds = sec.jwt_access_token_expire_minutes * 60
    expires_at = issued_at + timedelta(seconds=expires_in_seconds)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "sid": str(session_family_id),
        "jti": str(uuid.uuid4()),
        "type": "access",
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if sec.jwt_issuer:
        payload["iss"] = sec.jwt_issuer
    if sec.jwt_audience:
        payload["aud"] = sec.jwt_audience

    token = jwt.encode(
        payload,
        sec.jwt_secret_key.get_secret_value(),
        algorithm=sec.jwt_algorithm,
    )
    return token, expires_in_seconds


def decode_access_token(token: str, settings: Settings) -> AccessTokenClaims:
    """Validate JWT signature, lifetime, issuer, audience, token type, and UUID claims."""
    sec = settings.security
    decode_options: Options = {
        "require": ["exp", "iat", "sub", "sid", "jti", "type"],
        "verify_signature": True,
        "verify_exp": True,
        "verify_iat": True,
        "verify_iss": bool(sec.jwt_issuer),
        "verify_aud": bool(sec.jwt_audience),
    }

    try:
        payload = jwt.decode(
            token,
            sec.jwt_secret_key.get_secret_value(),
            algorithms=[sec.jwt_algorithm],
            issuer=sec.jwt_issuer,
            audience=sec.jwt_audience,
            options=decode_options,
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError(
            "Authentication session has expired.",
            code="ACCESS_TOKEN_EXPIRED",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError(
            "Invalid authentication credentials.",
            code="INVALID_ACCESS_TOKEN",
        ) from exc

    if payload.get("type") != "access":
        raise UnauthorizedError(
            "Invalid authentication credentials.",
            code="INVALID_TOKEN_TYPE",
        )

    try:
        subject = uuid.UUID(str(payload["sub"]))
        session_family_id = uuid.UUID(str(payload["sid"]))
        jti = str(payload["jti"])
        issued_at = datetime.fromtimestamp(int(payload["iat"]), tz=UTC)
        expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
    except (KeyError, TypeError, ValueError) as exc:
        raise UnauthorizedError(
            "Invalid authentication credentials.",
            code="INVALID_ACCESS_TOKEN",
        ) from exc

    if not jti:
        raise UnauthorizedError(
            "Invalid authentication credentials.",
            code="INVALID_ACCESS_TOKEN",
        )

    return AccessTokenClaims(
        subject=subject,
        session_family_id=session_family_id,
        jti=jti,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def set_refresh_cookie(
    response: Response,
    *,
    raw_token: str,
    settings: Settings,
) -> None:
    """Attach the opaque refresh token inside a hardened HttpOnly cookie."""
    sec = settings.security
    response.set_cookie(
        key=sec.refresh_cookie_name,
        value=raw_token,
        max_age=sec.jwt_refresh_token_expire_days * 86400,
        path=sec.refresh_cookie_path,
        domain=sec.cookie_domain,
        secure=sec.cookie_secure,
        httponly=True,
        samesite=sec.cookie_samesite,
    )


def clear_refresh_cookie(response: Response, settings: Settings) -> None:
    """Expire and remove the HttpOnly refresh cookie using matching attributes."""
    sec = settings.security
    response.delete_cookie(
        key=sec.refresh_cookie_name,
        path=sec.refresh_cookie_path,
        domain=sec.cookie_domain,
        secure=sec.cookie_secure,
        httponly=True,
        samesite=sec.cookie_samesite,
    )


def _normalize_origin(raw_url: str) -> str | None:
    cleaned = raw_url.strip()
    if not cleaned or cleaned.lower() == "null":
        return None
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _allowed_csrf_origins(settings: Settings) -> set[str]:
    allowed_origins: set[str] = {
        origin
        for raw in settings.cors_allowed_origins
        if (origin := _normalize_origin(raw)) is not None
    }
    if not settings.is_production:
        for local_host in ("localhost", "127.0.0.1"):
            allowed_origins.add(f"http://{local_host}:{settings.backend_port}")
    return allowed_origins


def validate_csrf_origin(request: Request, settings: Settings) -> None:
    """Verify Origin/Referer against trusted origins for cookie-authenticated endpoints."""
    allowed_origins = _allowed_csrf_origins(settings)

    raw_origin = request.headers.get("origin")
    raw_referer = request.headers.get("referer")

    candidate_origin: str | None = None
    if raw_origin is not None:
        candidate_origin = _normalize_origin(raw_origin)
    elif raw_referer is not None:
        candidate_origin = _normalize_origin(raw_referer)

    if candidate_origin is None or candidate_origin not in allowed_origins:
        log_security_event(
            event_type="auth.csrf_rejected",
            outcome="denied",
            message=f"Rejected request on {request.url.path} due to origin validation failure.",
            level=logging.WARNING,
        )
        raise ForbiddenError(
            "Request origin is not authorised for cookie-based authentication.",
            code="CSRF_VALIDATION_FAILED",
        )
