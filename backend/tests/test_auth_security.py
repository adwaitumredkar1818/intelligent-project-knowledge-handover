"""Unit tests for Argon2id hashing, email/password validation, JWT security, and rate limits."""

from __future__ import annotations

import uuid
from datetime import timedelta

import jwt
import pytest
from pydantic import ValidationError

from app.core.exceptions import UnauthorizedError
from app.core.rate_limit import InMemorySlidingWindowRateLimiter
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    utc_now,
    verify_dummy_password,
    verify_password,
)
from app.core.validators import normalize_and_validate_email, validate_password_strength
from tests.conftest import build_test_settings


def test_argon2id_password_hashing_and_verification() -> None:
    plain = "StrongPlatform!Pass2026"
    digest_a = hash_password(plain)
    digest_b = hash_password(plain)

    assert digest_a.startswith("$argon2id$")
    assert digest_b.startswith("$argon2id$")
    assert digest_a != digest_b
    assert plain not in digest_a
    assert verify_password(plain, digest_a) is True
    assert verify_password("WrongPass!1234", digest_a) is False
    assert verify_password("", digest_a) is False
    verify_dummy_password("nonexistent-check-pass")


def test_email_normalisation_and_password_strength_rules() -> None:
    assert normalize_and_validate_email("  Alice.Engineer@Example.COM ") == (
        "alice.engineer@example.com"
    )

    for bad_email in ("", "invalid", "a@b", "user name@example.com", ".dot@example.com"):
        with pytest.raises(ValueError):
            normalize_and_validate_email(bad_email)

    assert (
        validate_password_strength("Complex!AuthPass99", email="alice@example.com")
        == "Complex!AuthPass99"
    )

    for weak_pw in (
        "Short1!",
        "nouppercase123!",
        "NOLOWERCASE123!",
        "NoDigitsHere!@#",
        "NoSpecialChars123",
        "            ",
        "Myalice!Pass12",
        "Test_alice@example.com_1!",
    ):
        with pytest.raises(ValueError):
            validate_password_strength(weak_pw, email="alice@example.com")


def test_refresh_token_generation_and_sha256_hashing() -> None:
    token_a = generate_refresh_token()
    token_b = generate_refresh_token()
    hash_a = hash_refresh_token(token_a)

    assert token_a != token_b
    assert len(token_a) >= 48
    assert len(hash_a) == 64
    assert hash_a == hash_refresh_token(token_a)
    assert hash_a != token_a


def test_jwt_access_token_claims_and_validation() -> None:
    settings = build_test_settings(
        jwt_access_token_expire_minutes=15,
        jwt_issuer="ipkrh-platform",
        jwt_audience="ipkrh-api",
    )
    user_id = uuid.uuid4()
    family_id = uuid.uuid4()

    token, expires_in = create_access_token(
        user_id=user_id,
        session_family_id=family_id,
        settings=settings,
    )
    assert expires_in == 900

    claims = decode_access_token(token, settings)
    assert claims.subject == user_id
    assert claims.session_family_id == family_id
    assert len(claims.jti) > 10

    raw_payload = jwt.decode(
        token,
        settings.security.jwt_secret_key.get_secret_value(),
        algorithms=[settings.security.jwt_algorithm],
        audience="ipkrh-api",
        issuer="ipkrh-platform",
    )
    assert raw_payload["type"] == "access"
    assert "password" not in raw_payload
    assert "refresh_token" not in raw_payload

    # Expired token fails
    expired_token, _ = create_access_token(
        user_id=user_id,
        session_family_id=family_id,
        settings=settings,
        now=utc_now() - timedelta(minutes=20),
    )
    with pytest.raises(UnauthorizedError, match="expired") as exc_info:
        decode_access_token(expired_token, settings)
    assert exc_info.value.code == "ACCESS_TOKEN_EXPIRED"

    # Wrong secret fails
    other_secret_settings = build_test_settings(
        jwt_secret_key="completely-different-secret-key-at-least-32-chars"
    )
    with pytest.raises(UnauthorizedError) as exc_bad_sig:
        decode_access_token(token, other_secret_settings)
    assert exc_bad_sig.value.code == "INVALID_ACCESS_TOKEN"

    # Wrong issuer/audience fails when configured
    wrong_iss_settings = build_test_settings(jwt_issuer="other-issuer")
    with pytest.raises(UnauthorizedError):
        decode_access_token(token, wrong_iss_settings)

    wrong_aud_settings = build_test_settings(jwt_audience="other-audience")
    with pytest.raises(UnauthorizedError):
        decode_access_token(token, wrong_aud_settings)

    # Wrong token type fails even if validly signed
    wrong_type_token = jwt.encode(
        {
            **raw_payload,
            "type": "refresh",
        },
        settings.security.jwt_secret_key.get_secret_value(),
        algorithm=settings.security.jwt_algorithm,
    )
    with pytest.raises(UnauthorizedError) as exc_type:
        decode_access_token(wrong_type_token, settings)
    assert exc_type.value.code == "INVALID_TOKEN_TYPE"


def test_jwt_optional_issuer_audience_and_algorithm_restrictions() -> None:
    no_iss_aud_settings = build_test_settings(jwt_issuer=None, jwt_audience=None)
    user_id = uuid.uuid4()
    family_id = uuid.uuid4()
    token, _ = create_access_token(
        user_id=user_id,
        session_family_id=family_id,
        settings=no_iss_aud_settings,
    )
    claims = decode_access_token(token, no_iss_aud_settings)
    assert claims.subject == user_id

    with pytest.raises(ValidationError):
        build_test_settings(jwt_algorithm="none")


def test_in_memory_sliding_window_rate_limiter() -> None:
    limiter = InMemorySlidingWindowRateLimiter()
    assert limiter.check_rate_limit("login:abc", max_attempts=2, window_seconds=60) is None
    assert limiter.check_rate_limit("login:abc", max_attempts=2, window_seconds=60) is None
    retry_after = limiter.check_rate_limit("login:abc", max_attempts=2, window_seconds=60)
    assert retry_after is not None and retry_after >= 1
    # Separate action/client key remains independent
    assert limiter.check_rate_limit("login:def", max_attempts=2, window_seconds=60) is None
