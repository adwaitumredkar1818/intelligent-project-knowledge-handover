"""Tests for TokenEncryptionService isolation, OAuth 2.0 PKCE security, and token rotation."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from app.core.exceptions import ServiceUnavailableError
from app.core.logging import redact_sensitive_text
from app.core.security import utc_now
from app.models.audit import AuditLog
from app.models.enums import (
    ProjectSourceMappingStatus,
    SourceConnectionStatus,
    UserSourceAuthorisationStatus,
)
from app.models.integration import (
    OAuthState,
    ProjectSourceMapping,
    SourceConnection,
    UserSourceAuthorisation,
)
from app.services.integrations.errors import IntegrationProviderError
from app.services.storage import _derive_aes256_key
from app.services.token_encryption import (
    LocalTokenEncryptionService,
    TokenKind,
    _derive_token_aes_key,
)
from tests.conftest import (
    build_test_settings,
    invite_and_accept_member,
    isolated_auth_app,
    register_and_login_user,
)


def _dump_json(resp: httpx.Response) -> str:
    return resp.text


def test_local_token_encryption_hkdf_and_aad_isolation(tmp_path: object) -> None:
    del tmp_path
    svc = LocalTokenEncryptionService(
        token_encryption_key="token-only-master-key-at-least-32-chars!"
    )
    wrong_svc = LocalTokenEncryptionService(
        token_encryption_key="another-token-key-completely-different-32"
    )
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    secret_token = "gho_super_secret_delegated_token_value"

    encrypted = svc.encrypt_token(
        plaintext=secret_token,
        organisation_id=org_id,
        user_id=user_id,
        provider="github",
        token_kind=TokenKind.ACCESS_TOKEN,
    )
    assert encrypted.ciphertext.startswith("v1:")
    assert secret_token not in encrypted.ciphertext
    assert encrypted.encryption_algorithm == "AES-256-GCM"

    assert (
        svc.decrypt_token(
            ciphertext=encrypted.ciphertext,
            organisation_id=org_id,
            user_id=user_id,
            provider="github",
            token_kind=TokenKind.ACCESS_TOKEN,
            key_id=encrypted.key_id,
        )
        == secret_token
    )

    # Swapping key must fail integrity check cleanly
    with pytest.raises(ServiceUnavailableError) as exc_key:
        wrong_svc.decrypt_token(
            ciphertext=encrypted.ciphertext,
            organisation_id=org_id,
            user_id=user_id,
            provider="github",
            token_kind=TokenKind.ACCESS_TOKEN,
        )
    assert exc_key.value.code == "TOKEN_INTEGRITY_FAILED"

    # Swapping organisation_id, user_id, provider, or token_kind must fail AAD check
    for bad_org, bad_user, bad_provider, bad_kind in (
        (uuid.uuid4(), user_id, "github", TokenKind.ACCESS_TOKEN),
        (org_id, uuid.uuid4(), "github", TokenKind.ACCESS_TOKEN),
        (org_id, user_id, "jira", TokenKind.ACCESS_TOKEN),
        (org_id, user_id, "github", TokenKind.REFRESH_TOKEN),
    ):
        with pytest.raises(ServiceUnavailableError) as exc_aad:
            svc.decrypt_token(
                ciphertext=encrypted.ciphertext,
                organisation_id=bad_org,
                user_id=bad_user,
                provider=bad_provider,
                token_kind=bad_kind,
            )
        assert exc_aad.value.code == "TOKEN_INTEGRITY_FAILED"

    # Unsupported key version fails explicitly
    with pytest.raises(ServiceUnavailableError) as exc_ver:
        svc.decrypt_token(
            ciphertext=encrypted.ciphertext,
            organisation_id=org_id,
            user_id=user_id,
            provider="github",
            token_kind=TokenKind.ACCESS_TOKEN,
            key_id="kms-unknown-v9",
        )
    assert exc_ver.value.code == "TOKEN_KEY_UNSUPPORTED"

    # HKDF key separation from FILE_ENCRYPTION_KEY even if raw input strings match
    shared_raw = "identical-seed-material-for-separation-test!"
    assert _derive_aes256_key(shared_raw) != _derive_token_aes_key(shared_raw)


def test_integration_settings_validation_and_secret_redaction() -> None:
    # Disabled providers need no client credentials
    disabled_cfg = build_test_settings(github_enabled=False, jira_enabled=False)
    assert disabled_cfg.integrations.slack_enabled is False

    # Enabled providers require client_id & client_secret
    with pytest.raises(ValidationError):
        build_test_settings(github_enabled=True, github_client_id="gh-id")
    with pytest.raises(ValidationError):
        build_test_settings(jira_enabled=True, jira_client_secret="jira-secret-val")

    raw_leak = (
        "Failed calling https://api.example.com/cb?code=gh_code_99&state=st_abc "
        "with Authorization: Bearer secret_jwt_xyz access_token=tok_111 "
        "refresh_token=ref_222 client_secret=cli_333"
    )
    redacted = redact_sensitive_text(raw_leak)
    for sensitive in ("gh_code_99", "st_abc", "secret_jwt_xyz", "tok_111", "ref_222", "cli_333"):
        assert sensitive not in redacted

    err = IntegrationProviderError(provider="jira", code="ERR", message=raw_leak, status_code=500)
    for sensitive in ("gh_code_99", "st_abc", "secret_jwt_xyz", "tok_111", "ref_222", "cli_333"):
        assert sensitive not in err.message


def test_oauth_start_security_validation_errors_and_slack_gate(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    gh_access = "gho_test_access_secret_token_alpha"
    gh_refresh = "ghr_test_refresh_secret_token_beta"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/login/oauth/access_token":
            return httpx.Response(
                200,
                json={
                    "access_token": gh_access,
                    "refresh_token": gh_refresh,
                    "expires_in": 3600,
                    "token_type": "bearer",
                    "scope": "read:user user:email",
                },
            )
        if request.url.path == "/user":
            assert request.headers.get("Authorization") == f"Bearer {gh_access}"
            return httpx.Response(200, json={"id": 4242, "login": "alice-octo", "email": None})
        if request.url.path == "/user/emails":
            return httpx.Response(
                200,
                json=[
                    {"email": "secondary@example.com", "primary": False, "verified": True},
                    {"email": "alice@octo.example.com", "primary": True, "verified": True},
                ],
            )
        return httpx.Response(404, json={"message": "Not found"})

    with isolated_auth_app(
        monkeypatch,
        github_enabled=True,
        github_client_id="gh-client-123",
        github_client_secret="gh-secret-456-super-confidential",
        github_oauth_mode="github_app",
        github_oauth_scopes="repo read:user user:email",
        jira_enabled=True,
        jira_client_id="jira-client-123",
        jira_client_secret="jira-secret-456-super-confidential",
    ) as ctx:
        ctx.app.state.integration_http_transport = httpx.MockTransport(handler)
        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client,
                email="oauth-owner@example.com",
                full_name="OAuth Owner",
            )
            member = register_and_login_user(
                client,
                email="oauth-member@example.com",
                full_name="OAuth Member",
            )
            org_id = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "OAuth Org"},
            ).json()["id"]
            invite_and_accept_member(
                client,
                organisation_id=org_id,
                inviter_headers=owner.headers,
                invitee=member,
                role_name="org_member",
            )

            # 1. Slack remains strictly disabled until formal governance approval
            slack_resp = client.post(
                f"/api/v1/organisations/{org_id}/integrations/slack/oauth/start",
                headers=owner.headers,
            )
            assert slack_resp.status_code == 409
            assert slack_resp.json()["error"]["code"] == "SLACK_INTEGRATION_DISABLED"

            # 2. Disallowed redirect_after target is rejected (open-redirect defense)
            bad_redir = client.post(
                f"/api/v1/organisations/{org_id}/integrations/github/oauth/start",
                headers=owner.headers,
                json={"redirect_after": "https://evil.attacker.example/steal"},
            )
            assert bad_redir.status_code == 400
            assert bad_redir.json()["error"]["code"] == "REDIRECT_URL_NOT_ALLOWLISTED"

            # 3. Valid start creates single-use hashed state, encrypted PKCE, no-store header
            start_resp = client.post(
                f"/api/v1/organisations/{org_id}/integrations/github/oauth/start",
                headers=owner.headers,
                json={
                    "display_name": "Core GitHub",
                    "redirect_after": "http://localhost:3000/integrations/done",
                },
            )
            assert start_resp.status_code == 200
            assert start_resp.headers.get("cache-control") == "no-store"
            start_data = start_resp.json()
            conn_id = start_data["source_connection_id"]
            state_id = uuid.UUID(start_data["state_id"])

            auth_url = urlparse(start_data["authorisation_url"])
            query = parse_qs(auth_url.query)
            raw_state = query["state"][0]
            assert query["client_id"] == ["gh-client-123"]
            assert query["code_challenge_method"] == ["S256"]
            assert len(query["code_challenge"][0]) >= 32
            # github_app mode strips broad classic `repo` scope cleanly
            assert "scope" not in query

            with ctx.session_factory() as session:
                state_row = session.get(OAuthState, state_id)
                assert state_row is not None
                assert len(state_row.state_hash) == 64
                assert state_row.state_hash != raw_state
                assert state_row.encrypted_code_verifier is not None
                assert state_row.encrypted_code_verifier.startswith("v1:")

            # 4. Cross-user state hijack must fail with 403
            hijack = client.get(
                "/api/v1/integrations/github/callback",
                headers=member.headers,
                params={"code": "gh_auth_code", "state": raw_state},
            )
            assert hijack.status_code == 403
            assert hijack.json()["error"]["code"] == "OAUTH_STATE_USER_MISMATCH"

            # 5. Provider access_denied callback consumes state & audits cleanly
            denied_start = client.post(
                f"/api/v1/organisations/{org_id}/integrations/github/oauth/start",
                headers=owner.headers,
                json={"source_connection_id": conn_id},
            ).json()
            denied_state = parse_qs(urlparse(denied_start["authorisation_url"]).query)["state"][0]
            denied_cb = client.get(
                "/api/v1/integrations/github/callback",
                headers=owner.headers,
                params={
                    "state": denied_state,
                    "error": "access_denied",
                    "error_description": "User cancelled consent",
                },
            )
            assert denied_cb.status_code == 403
            assert denied_cb.json()["error"]["code"] == "OAUTH_ACCESS_DENIED"

            # 6. Expired state returns 410 Gone
            expired_start = client.post(
                f"/api/v1/organisations/{org_id}/integrations/github/oauth/start",
                headers=owner.headers,
                json={"source_connection_id": conn_id},
            ).json()
            exp_state_id = uuid.UUID(expired_start["state_id"])
            exp_state_raw = parse_qs(urlparse(expired_start["authorisation_url"]).query)["state"][0]
            with ctx.session_factory() as session:
                exp_row = session.get(OAuthState, exp_state_id)
                assert exp_row is not None
                exp_row.expires_at = utc_now() - timedelta(minutes=2)
                session.commit()
            exp_cb = client.get(
                "/api/v1/integrations/github/callback",
                headers=owner.headers,
                params={"code": "unused", "state": exp_state_raw},
            )
            assert exp_cb.status_code == 410
            assert exp_cb.json()["error"]["code"] == "OAUTH_STATE_EXPIRED"

            # 7. Valid callback succeeds once, resolves /user/emails primary verified email
            cb_resp = client.get(
                "/api/v1/integrations/github/callback",
                headers=owner.headers,
                params={"code": "valid_gh_code", "state": raw_state},
            )
            assert cb_resp.status_code == 200
            assert cb_resp.headers.get("cache-control") == "no-store"
            cb_data = cb_resp.json()
            assert cb_data["connection"]["status"] == SourceConnectionStatus.ACTIVE.value
            assert cb_data["authorisation"]["external_user_id"] == "4242"
            assert cb_data["authorisation"]["external_username"] == "alice-octo"
            assert cb_data["authorisation"]["external_email"] == "alice@octo.example.com"
            assert cb_data["redirect_after"] == "http://localhost:3000/integrations/done"

            # Raw secret values MUST NEVER appear in HTTP responses, DB columns, or audit logs
            assert gh_access not in cb_resp.text
            assert gh_refresh not in cb_resp.text
            assert "gh-secret-456-super-confidential" not in cb_resp.text

            # 8. Replay of consumed state fails with 409 Conflict
            replay_cb = client.get(
                "/api/v1/integrations/github/callback",
                headers=owner.headers,
                params={"code": "valid_gh_code", "state": raw_state},
            )
            assert replay_cb.status_code == 409
            assert replay_cb.json()["error"]["code"] == "OAUTH_STATE_REPLAYED"

            with ctx.session_factory() as session:
                auth_row = session.execute(
                    select(UserSourceAuthorisation).where(
                        UserSourceAuthorisation.user_id == owner.user_id
                    )
                ).scalar_one()
                assert auth_row.encrypted_access_token.startswith("v1:")
                assert auth_row.encrypted_refresh_token is not None
                assert auth_row.encrypted_refresh_token.startswith("v1:")
                assert gh_access not in auth_row.encrypted_access_token
                assert gh_refresh not in auth_row.encrypted_refresh_token
                audit_events = list(session.execute(select(AuditLog)).scalars().all())
                assert any(a.event_type == "integration.oauth_denied" for a in audit_events)
                assert any(a.event_type == "integration.oauth_connected" for a in audit_events)
                for a in audit_events:
                    serialised = f"{a.event_type} {a.event_metadata}"
                    assert gh_access not in serialised
                    assert gh_refresh not in serialised
                    assert raw_state not in serialised

            for leaked in (gh_access, gh_refresh, raw_state, "gh-secret-456-super-confidential"):
                assert leaked not in caplog.text


def test_jira_3lo_rotating_refresh_token_and_revocation_flows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refresh_calls: list[dict[str, str]] = []
    token_v1 = "jira_access_v1_secret"
    refresh_v1 = "jira_refresh_v1_single_use"
    token_v2 = "jira_access_v2_rotated"
    refresh_v2 = "jira_refresh_v2_single_use"
    token_v3 = "jira_access_v3_after_v2"
    refresh_v3 = "jira_refresh_v3_final"
    fail_next_refresh = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal fail_next_refresh
        path = request.url.path
        if path == "/oauth/token":
            import json as _json

            payload = _json.loads(request.content.decode("utf-8"))
            grant_type = payload.get("grant_type")
            if grant_type == "authorization_code":
                return httpx.Response(
                    200,
                    json={
                        "access_token": token_v1,
                        "refresh_token": refresh_v1,
                        "expires_in": 3600,
                        "token_type": "Bearer",
                        "scope": "read:jira-work read:jira-user offline_access",
                    },
                )
            if grant_type == "refresh_token":
                refresh_calls.append({"refresh_token": str(payload.get("refresh_token"))})
                if fail_next_refresh:
                    return httpx.Response(400, json={"error": "invalid_grant"})
                sent_rt = payload.get("refresh_token")
                if sent_rt == refresh_v1:
                    return httpx.Response(
                        200,
                        json={
                            "access_token": token_v2,
                            "refresh_token": refresh_v2,
                            "expires_in": 3600,
                        },
                    )
                if sent_rt == refresh_v2:
                    return httpx.Response(
                        200,
                        json={
                            "access_token": token_v3,
                            "refresh_token": refresh_v3,
                            "expires_in": 3600,
                        },
                    )
                return httpx.Response(400, json={"error": "reused_refresh_token"})
        if path == "/oauth/token/accessible-resources":
            auth_header = request.headers.get("Authorization", "")
            assert auth_header in {
                f"Bearer {token_v1}",
                f"Bearer {token_v2}",
                f"Bearer {token_v3}",
            }
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "cloud-site-001",
                        "name": "Acme Jira Cloud",
                        "url": "https://acme.atlassian.net",
                        "scopes": ["read:jira-work", "read:jira-user"],
                    }
                ],
            )
        if path == "/ex/jira/cloud-site-001/rest/api/3/myself":
            return httpx.Response(
                200,
                json={
                    "accountId": "jira-acct-900",
                    "displayName": "Alice Jira",
                    "emailAddress": "alice@acme.example.com",
                },
            )
        if path == "/ex/jira/cloud-site-001/rest/api/3/project/search":
            assert request.headers.get("Authorization") == f"Bearer {token_v2}"
            return httpx.Response(
                200,
                json={
                    "startAt": 0,
                    "maxResults": 50,
                    "total": 1,
                    "isLast": True,
                    "values": [
                        {
                            "id": "10010",
                            "key": "CORE",
                            "name": "Core Engineering",
                            "projectTypeKey": "software",
                            "style": "next-gen",
                        }
                    ],
                },
            )
        return httpx.Response(404, json={"message": f"Unhandled {path}"})

    with isolated_auth_app(
        monkeypatch,
        jira_enabled=True,
        jira_client_id="jira-cli-1",
        jira_client_secret="jira-sec-1-super-confidential",
    ) as ctx:
        ctx.app.state.integration_http_transport = httpx.MockTransport(handler)
        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client,
                email="jira-rot@example.com",
                full_name="Jira Rotator",
            )
            org_id = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "Jira Rotation Org"},
            ).json()["id"]

            start = client.post(
                f"/api/v1/organisations/{org_id}/integrations/jira/oauth/start",
                headers=owner.headers,
                json={"display_name": "Acme Jira"},
            ).json()
            conn_id = start["source_connection_id"]
            raw_state = parse_qs(urlparse(start["authorisation_url"]).query)["state"][0]

            cb = client.get(
                "/api/v1/integrations/jira/callback",
                headers=owner.headers,
                params={"code": "jira_code_1", "state": raw_state},
            )
            assert cb.status_code == 200
            assert cb.json()["discovered_sites_count"] == 1
            assert cb.json()["connection"]["external_workspace_id"] == "cloud-site-001"
            auth_id = uuid.UUID(cb.json()["authorisation"]["id"])

            # Expire access token inside DB to verify seamless pre-emptive refresh rotation
            with ctx.session_factory() as session:
                auth_row = session.get(UserSourceAuthorisation, auth_id)
                assert auth_row is not None
                auth_row.token_expires_at = utc_now() + timedelta(seconds=20)
                session.commit()

            # Discovery triggers refresh_v1 -> (token_v2, refresh_v2) and uses token_v2!
            disc = client.get(
                f"/api/v1/integrations/connections/{conn_id}/jira/projects",
                headers=owner.headers,
            )
            assert disc.status_code == 200
            assert disc.json()["projects"][0]["key"] == "CORE"
            assert refresh_calls == [{"refresh_token": refresh_v1}]

            # Force second near-expiry -> must send rotated refresh_v2 (never re-send refresh_v1!)
            with ctx.session_factory() as session:
                auth_row = session.get(UserSourceAuthorisation, auth_id)
                assert auth_row is not None
                auth_row.token_expires_at = utc_now() + timedelta(seconds=10)
                session.commit()
            sites2 = client.get(
                f"/api/v1/integrations/connections/{conn_id}/jira/sites",
                headers=owner.headers,
            )
            assert sites2.status_code == 200
            assert refresh_calls == [
                {"refresh_token": refresh_v1},
                {"refresh_token": refresh_v2},
            ]

            # Revoked / invalid refresh token transitions auth -> expired & conn -> reauth_required
            fail_next_refresh = True
            with ctx.session_factory() as session:
                auth_row = session.get(UserSourceAuthorisation, auth_id)
                assert auth_row is not None
                auth_row.token_expires_at = utc_now() - timedelta(seconds=5)
                session.commit()
            failed_sites = client.get(
                f"/api/v1/integrations/connections/{conn_id}/jira/sites",
                headers=owner.headers,
            )
            assert failed_sites.status_code == 409
            assert failed_sites.json()["error"]["code"] == "TOKEN_REFRESH_REJECTED"

            with ctx.session_factory() as session:
                auth_row = session.get(UserSourceAuthorisation, auth_id)
                conn_row = session.get(SourceConnection, uuid.UUID(conn_id))
                assert auth_row is not None and conn_row is not None
                assert auth_row.status == UserSourceAuthorisationStatus.EXPIRED.value
                assert conn_row.status == SourceConnectionStatus.REAUTH_REQUIRED.value

            # Re-authorise cleanly on the SAME connection & verify self-revoke + disconnect
            reauth_start = client.post(
                f"/api/v1/organisations/{org_id}/integrations/jira/oauth/start",
                headers=owner.headers,
                json={"source_connection_id": conn_id},
            ).json()
            reauth_state = parse_qs(urlparse(reauth_start["authorisation_url"]).query)["state"][0]
            reauth_cb = client.get(
                "/api/v1/integrations/jira/callback",
                headers=owner.headers,
                params={"code": "jira_code_reauth", "state": reauth_state},
            )
            assert reauth_cb.status_code == 200
            assert reauth_cb.json()["connection"]["status"] == SourceConnectionStatus.ACTIVE.value

            revoke_resp = client.post(
                f"/api/v1/integrations/connections/{conn_id}/authorisation/revoke",
                headers=owner.headers,
            )
            assert revoke_resp.status_code == 200
            assert (
                revoke_resp.json()["caller_authorisation"]["status"]
                == UserSourceAuthorisationStatus.REVOKED.value
            )
            post_revoke = client.get(
                f"/api/v1/integrations/connections/{conn_id}/jira/sites",
                headers=owner.headers,
            )
            assert post_revoke.status_code == 409
            assert post_revoke.json()["error"]["code"] == "SOURCE_AUTHORISATION_REVOKED"

            # Disconnect disables connection and any associated mappings cleanly
            disc_conn = client.post(
                f"/api/v1/integrations/connections/{conn_id}/disconnect",
                headers=owner.headers,
            )
            assert disc_conn.status_code == 200
            assert disc_conn.json()["status"] == SourceConnectionStatus.DISCONNECTED.value
            with ctx.session_factory() as session:
                # No remaining active mappings for disconnected connection
                mappings = list(
                    session.execute(
                        select(ProjectSourceMapping).where(
                            ProjectSourceMapping.source_connection_id == uuid.UUID(conn_id)
                        )
                    )
                    .scalars()
                    .all()
                )
                assert all(
                    m.status != ProjectSourceMappingStatus.ACTIVE.value for m in mappings
                )
