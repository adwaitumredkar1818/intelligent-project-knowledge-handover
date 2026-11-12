"""End-to-end API authentication tests against isolated DB instances."""

from __future__ import annotations

import logging
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_refresh_token, utc_now
from app.models.auth import RefreshSession
from app.models.enums import RevocationReason, UserStatus
from app.models.user import User
from tests.conftest import isolated_auth_app

_TRUSTED_ORIGIN = "http://localhost:3000"
_VALID_PASSWORD = "Handover!Auth2026#Secure"


def test_register_normalisation_duplicate_prevention_and_safe_validation(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        with caplog.at_level(logging.INFO):
            reg = client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "  Ada   Lovelace ",
                    "email": "  Ada.Lovelace@Example.COM  ",
                    "password": _VALID_PASSWORD,
                },
            )
            assert reg.status_code == 201
            body = reg.json()
            assert body["user"]["full_name"] == "Ada Lovelace"
            assert body["user"]["email"] == "ada.lovelace@example.com"
            assert body["user"]["status"] == "active"
            assert body["user"]["is_email_verified"] is False
            assert body["user"]["roles"] == ["standard_user"]
            assert body["email_verification_required"] is True
            assert body["email_verification_delivery"] == "not_configured"
            assert "password_hash" not in reg.text
            assert _VALID_PASSWORD not in reg.text

            # Duplicate email with different case must conflict cleanly
            dup = client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Duplicate Ada",
                    "email": "ADA.LOVELACE@example.com",
                    "password": "AnotherStrong!Password2026",
                },
            )
            assert dup.status_code == 409
            assert dup.json()["error"]["code"] == "ACCOUNT_ALREADY_EXISTS"

            # Weak password fails validation without echoing submitted secret
            weak_secret = "weakpass"
            bad_pw = client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Weak Test",
                    "email": "weak@example.com",
                    "password": weak_secret,
                },
            )
            assert bad_pw.status_code == 422
            assert bad_pw.json()["error"]["code"] == "VALIDATION_ERROR"
            assert weak_secret not in bad_pw.text

        assert _VALID_PASSWORD not in caplog.text
        assert weak_secret not in caplog.text

        with ctx.session_factory() as session:
            stored = session.scalar(
                select(User).where(User.email == "ada.lovelace@example.com")
            )
            assert stored is not None
            assert stored.password_hash is not None
            assert stored.password_hash.startswith("$argon2id$")
            assert stored.password_hash != _VALID_PASSWORD


def test_login_cookie_attributes_generic_failures_and_me_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        isolated_auth_app(
            monkeypatch,
            app_env="production",
            cookie_secure=True,
            cookie_samesite="lax",
            postgres_ssl_mode="require",
            cors_allowed_origins=["https://app.example.com"],
        ) as ctx,
        TestClient(ctx.app, base_url="https://app.example.com") as client,
    ):
        client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Grace Hopper",
                "email": "grace@example.com",
                "password": _VALID_PASSWORD,
            },
        )

        with caplog.at_level(logging.INFO):
            login_ok = client.post(
                "/api/v1/auth/login",
                json={"email": "  GRACE@EXAMPLE.COM ", "password": _VALID_PASSWORD},
            )
            assert login_ok.status_code == 200
            payload = login_ok.json()
            access_token = payload["access_token"]
            assert payload["token_type"] == "bearer"
            assert payload["expires_in"] == 900
            assert payload["user"]["email"] == "grace@example.com"
            assert "refresh_token" not in payload
            assert "password_hash" not in login_ok.text

            set_cookie_header = login_ok.headers["set-cookie"]
            assert "ipkrh_refresh_token=" in set_cookie_header
            assert "HttpOnly" in set_cookie_header
            assert "Secure" in set_cookie_header
            assert "Path=/api/v1/auth" in set_cookie_header
            assert "samesite=lax" in set_cookie_header.lower()

            raw_cookie_value = client.cookies.get("ipkrh_refresh_token")
            assert raw_cookie_value is not None

            # Ensure DB persists ONLY SHA-256 hash, never raw token value
            with ctx.session_factory() as session:
                stored_session = session.scalar(select(RefreshSession))
                assert stored_session is not None
                assert stored_session.token_hash == hash_refresh_token(raw_cookie_value)
                assert stored_session.token_hash != raw_cookie_value
                assert len(stored_session.token_hash) == 64

            # GET /api/v1/auth/me works with Bearer token
            me_ok = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert me_ok.status_code == 200
            assert me_ok.json()["email"] == "grace@example.com"
            assert "account.profile.read" in me_ok.json()["permissions"]

            # Login failure oracle check: wrong password and unknown email produce identical errors
            bad_pw = client.post(
                "/api/v1/auth/login",
                json={"email": "grace@example.com", "password": "NotThePassword!123"},
            )
            bad_user = client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@example.com", "password": "NotThePassword!123"},
            )
            assert bad_pw.status_code == 401
            assert bad_user.status_code == 401
            assert bad_pw.json()["error"]["code"] == "INVALID_CREDENTIALS"
            assert bad_user.json()["error"]["code"] == "INVALID_CREDENTIALS"
            assert bad_pw.json()["error"]["message"] == bad_user.json()["error"]["message"]

            # Unauthenticated /me fails 401
            unauth = client.get("/api/v1/auth/me")
            assert unauth.status_code == 401
            assert unauth.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

        assert _VALID_PASSWORD not in caplog.text
        assert raw_cookie_value not in caplog.text
        assert access_token not in caplog.text


def test_refresh_rotation_reuse_detection_and_family_revocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Alan Turing",
                "email": "alan@example.com",
                "password": _VALID_PASSWORD,
            },
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "alan@example.com", "password": _VALID_PASSWORD},
        )
        assert login_resp.status_code == 200
        token_1 = client.cookies.get("ipkrh_refresh_token")
        assert token_1 is not None

        # Rotate token_1 -> token_2
        rot_resp = client.post(
            "/api/v1/auth/refresh",
            headers={"Origin": _TRUSTED_ORIGIN},
        )
        assert rot_resp.status_code == 200
        access_2 = rot_resp.json()["access_token"]
        token_2 = client.cookies.get("ipkrh_refresh_token")
        assert token_2 is not None and token_2 != token_1

        with ctx.session_factory() as session:
            s1 = session.scalar(
                select(RefreshSession).where(
                    RefreshSession.token_hash == hash_refresh_token(token_1)
                )
            )
            s2 = session.scalar(
                select(RefreshSession).where(
                    RefreshSession.token_hash == hash_refresh_token(token_2)
                )
            )
            assert s1 is not None and s2 is not None
            assert s1.revoked_at is not None
            assert s1.revoked_reason == RevocationReason.ROTATED.value
            assert s1.replaced_by_session_id == s2.id
            assert s1.token_family_id == s2.token_family_id
            assert s2.revoked_at is None

        # Replay already-rotated token_1 -> triggers reuse detection & revokes family!
        replay_resp = client.post(
            "/api/v1/auth/refresh",
            headers={
                "Origin": _TRUSTED_ORIGIN,
                "Cookie": f"ipkrh_refresh_token={token_1}",
            },
        )
        assert replay_resp.status_code == 401
        assert replay_resp.json()["error"]["code"] == "REFRESH_TOKEN_REUSED"

        # Now legitimate token_2 AND access_2 (same session family) are revoked!
        post_replay_refresh = client.post(
            "/api/v1/auth/refresh",
            headers={
                "Origin": _TRUSTED_ORIGIN,
                "Cookie": f"ipkrh_refresh_token={token_2}",
            },
        )
        assert post_replay_refresh.status_code == 401
        assert post_replay_refresh.json()["error"]["code"] == "REFRESH_TOKEN_REUSED"

        post_replay_me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_2}"},
        )
        assert post_replay_me.status_code == 401
        assert post_replay_me.json()["error"]["code"] == "SESSION_REVOKED"


def test_expired_refresh_token_and_logout_revocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Katherine Johnson",
                "email": "katherine@example.com",
                "password": _VALID_PASSWORD,
            },
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "katherine@example.com", "password": _VALID_PASSWORD},
        )
        access_token = login_resp.json()["access_token"]
        raw_refresh = client.cookies.get("ipkrh_refresh_token")
        assert raw_refresh is not None

        # Logout revokes active session family and clears cookie
        logout_resp = client.post(
            "/api/v1/auth/logout",
            headers={"Origin": _TRUSTED_ORIGIN},
        )
        assert logout_resp.status_code == 200
        assert logout_resp.json()["revoked"] is True
        assert "Max-Age=0" in logout_resp.headers["set-cookie"]

        # Both /me (access token) and /refresh (old cookie replayed) fail 401 after logout
        assert (
            client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/refresh",
                headers={
                    "Origin": _TRUSTED_ORIGIN,
                    "Cookie": f"ipkrh_refresh_token={raw_refresh}",
                },
            ).status_code
            == 401
        )

        # Fresh login + force DB expiry -> /refresh returns 401 REFRESH_TOKEN_EXPIRED
        login2 = client.post(
            "/api/v1/auth/login",
            json={"email": "katherine@example.com", "password": _VALID_PASSWORD},
        )
        assert login2.status_code == 200
        raw_refresh_2 = client.cookies.get("ipkrh_refresh_token")
        assert raw_refresh_2 is not None
        with ctx.session_factory() as session:
            rec = session.scalar(
                select(RefreshSession).where(
                    RefreshSession.token_hash == hash_refresh_token(raw_refresh_2)
                )
            )
            assert rec is not None
            rec.expires_at = utc_now() - timedelta(minutes=1)
            session.commit()

        exp_resp = client.post(
            "/api/v1/auth/refresh",
            headers={"Origin": _TRUSTED_ORIGIN},
        )
        assert exp_resp.status_code == 401
        assert exp_resp.json()["error"]["code"] == "REFRESH_TOKEN_EXPIRED"


def test_csrf_origin_validation_on_refresh_and_logout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Margaret Hamilton",
                "email": "margaret@example.com",
                "password": _VALID_PASSWORD,
            },
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "margaret@example.com", "password": _VALID_PASSWORD},
        )
        assert login_resp.status_code == 200

        # Missing both Origin and Referer fails closed with 403
        no_origin = client.post("/api/v1/auth/refresh")
        assert no_origin.status_code == 403
        assert no_origin.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"

        # Untrusted Origin or 'null' Origin fails closed with 403
        for bad_headers in (
            {"Origin": "https://evil.example"},
            {"Origin": "null"},
            {"Referer": "https://evil.example/form.html"},
        ):
            r_refresh = client.post("/api/v1/auth/refresh", headers=bad_headers)
            assert r_refresh.status_code == 403
            assert r_refresh.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"

            r_logout = client.post("/api/v1/auth/logout", headers=bad_headers)
            assert r_logout.status_code == 403
            assert r_logout.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"

        # Trusted Referer when Origin absent still succeeds (session stays intact until CSRF pass)
        ref_ok = client.post(
            "/api/v1/auth/refresh",
            headers={"Referer": f"{_TRUSTED_ORIGIN}/settings"},
        )
        assert ref_ok.status_code == 200


def test_auth_rate_limiting_hook_blocks_rapid_login_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(
        monkeypatch,
        auth_rate_limit_enabled=True,
        auth_rate_limit_max_attempts=2,
        auth_rate_limit_window_seconds=60,
    ) as ctx, TestClient(ctx.app) as client:
        for _ in range(2):
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@example.com", "password": "wrong"},
            )
            assert resp.status_code == 401

        limited = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "wrong"},
        )
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert int(limited.headers["retry-after"]) >= 1


def test_disabled_user_login_blocked_generically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Disabled Account",
                "email": "disabled@example.com",
                "password": _VALID_PASSWORD,
            },
        )
        with ctx.session_factory() as session:
            user = session.scalar(
                select(User).where(User.email == "disabled@example.com")
            )
            assert user is not None
            user.status = UserStatus.DISABLED.value
            session.commit()

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "disabled@example.com", "password": _VALID_PASSWORD},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"
