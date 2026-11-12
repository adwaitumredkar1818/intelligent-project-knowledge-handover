"""Unit and integration tests for Supabase Auth JWT verification and user provisioning."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.models.enums import UserStatus
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.supabase_auth import SupabaseAuthService, SupabaseUserClaims
from tests.conftest import build_test_settings, isolated_auth_app

_MOCK_JWT_SECRET = "supabase-test-jwt-secret-at-least-32-chars-long"


def _create_mock_supabase_token(
    *,
    sub: str,
    email: str,
    full_name: str = "Alice Handover",
    secret: str = _MOCK_JWT_SECRET,
    algorithm: str = "HS256",
    expires_in_seconds: int = 3600,
    audience: str = "authenticated",
    issuer: str = "https://example.supabase.co/auth/v1",
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "email": email,
        "aud": audience,
        "iss": issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
        "user_metadata": {
            "full_name": full_name,
            "email_verified": True,
        },
        "role": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def test_supabase_auth_verify_valid_token_hs256() -> None:
    settings = build_test_settings(
        supabase_enabled=True,
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret=_MOCK_JWT_SECRET,
        supabase_jwt_audience="authenticated",
    )
    service = SupabaseAuthService(settings)
    assert service.is_configured

    token = _create_mock_supabase_token(
        sub="usr_supabase_001",
        email="alice@company.org",
        full_name="Alice Architect",
    )

    claims = service.verify_token(token)
    assert claims.sub == "usr_supabase_001"
    assert claims.email == "alice@company.org"
    assert claims.full_name == "Alice Architect"
    assert claims.is_email_verified is True


def test_supabase_auth_rejects_expired_token() -> None:
    settings = build_test_settings(
        supabase_enabled=True,
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret=_MOCK_JWT_SECRET,
    )
    service = SupabaseAuthService(settings)

    token = _create_mock_supabase_token(
        sub="usr_expired_001",
        email="bob@company.org",
        expires_in_seconds=-60,
    )

    with pytest.raises(UnauthorizedError) as exc_info:
        service.verify_token(token)
    assert exc_info.value.code == "SESSION_EXPIRED"


def test_supabase_auth_rejects_invalid_signature() -> None:
    settings = build_test_settings(
        supabase_enabled=True,
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret=_MOCK_JWT_SECRET,
    )
    service = SupabaseAuthService(settings)

    token = _create_mock_supabase_token(
        sub="usr_tampered_001",
        email="eve@company.org",
        secret="different-secret-that-does-not-match-at-all",
    )

    with pytest.raises(UnauthorizedError) as exc_info:
        service.verify_token(token)
    assert exc_info.value.code == "AUTHENTICATION_INVALID"


def test_supabase_user_provisioning_and_linking(monkeypatch: pytest.MonkeyPatch) -> None:
    with isolated_auth_app(
        monkeypatch,
        supabase_enabled=True,
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret=_MOCK_JWT_SECRET,
    ) as ctx:
        settings = ctx.settings
        service = SupabaseAuthService(settings)

        claims_new = SupabaseUserClaims(
            sub="sb_uuid_999",
            email="carol@enterprise.com",
            full_name="Carol Engineer",
            is_email_verified=True,
        )

        # 1. Provision new user
        with ctx.session_factory() as session:
            user = service.provision_or_sync_user(session, claims_new)
            session.commit()
            assert user.id is not None
            assert user.supabase_auth_id == "sb_uuid_999"
            assert user.email == "carol@enterprise.com"
            assert user.full_name == "Carol Engineer"
            assert user.password_hash is None
            assert user.is_email_verified is True
            assert user.last_login_at is not None

        # 2. Existing user links on second login
        with ctx.session_factory() as session:
            claims_updated = SupabaseUserClaims(
                sub="sb_uuid_999",
                email="carol@enterprise.com",
                full_name="Carol Senior Engineer",
                is_email_verified=True,
            )
            user_relogin = service.provision_or_sync_user(session, claims_updated)
            session.commit()
            assert user_relogin.id == user.id
            assert user_relogin.supabase_auth_id == "sb_uuid_999"


def test_supabase_auth_end_to_end_api(monkeypatch: pytest.MonkeyPatch) -> None:
    with isolated_auth_app(
        monkeypatch,
        supabase_enabled=True,
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret=_MOCK_JWT_SECRET,
        supabase_jwt_audience="authenticated",
    ) as ctx, TestClient(ctx.app) as client:
        token = _create_mock_supabase_token(
            sub="sb_user_api_123",
            email="dan@platform.test",
            full_name="Dan Tech Lead",
        )

        # Access user me endpoint with Bearer Supabase JWT
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "dan@platform.test"
        assert data["full_name"] == "Dan Tech Lead"
