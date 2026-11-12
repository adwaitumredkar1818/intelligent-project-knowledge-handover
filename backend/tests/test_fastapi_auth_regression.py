"""FastAPI-managed authentication regressions (no Supabase Auth interception/provisioning)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.user import User
from app.repositories.user import UserRepository
from tests.conftest import isolated_auth_app, register_and_login_user


def _forged_external_supabase_jwt(*, email: str = "external@example.com") -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": "sb-external-user-123",
            "email": email,
            "aud": "authenticated",
            "iss": "https://example.supabase.co/auth/v1",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "role": "authenticated",
        },
        "supabase-jwt-secret-that-backend-must-ignore-32",
        algorithm="HS256",
    )


def test_fastapi_auth_rejects_external_supabase_jwt_and_never_autoprovisions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(
        monkeypatch,
        storage_provider="supabase_storage",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role-secret-only-for-storage",
    ) as ctx, TestClient(ctx.app) as client:
        forged = _forged_external_supabase_jwt(email="intruder@example.com")
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {forged}"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_ACCESS_TOKEN"

        with ctx.session_factory() as session:
            users = list(session.execute(select(User)).scalars().all())
            assert users == []


def test_passwordless_user_record_and_repository_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        session_user = register_and_login_user(
            client,
            email="fastapi-owner@example.com",
            full_name="FastAPI Owner",
        )
        me_resp = client.get("/api/v1/auth/me", headers=session_user.headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "fastapi-owner@example.com"

        with ctx.session_factory() as session:
            repo = UserRepository(session)
            with pytest.raises(ValueError, match="password_hash"):
                repo.create(
                    full_name="No Hash",
                    email="nohash@example.com",
                    password_hash="",
                )

            legacy_row = User(
                full_name="Legacy Null Password",
                email="legacy-null@example.com",
                password_hash=None,
            )
            session.add(legacy_row)
            session.commit()

        login_resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "legacy-null@example.com",
                "password": "AnyPassword!2026#Valid",
            },
        )
        assert login_resp.status_code == 401
        assert login_resp.json()["error"]["code"] == "INVALID_CREDENTIALS"
