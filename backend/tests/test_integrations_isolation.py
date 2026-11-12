"""Cross-tenant isolation, RBAC role enforcement, and fail-closed delegated source ACL tests."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.audit import AuditLog
from app.services.integrations.sync_worker import SourceSyncWorkerService
from app.services.token_encryption import LocalTokenEncryptionService
from tests.conftest import (
    invite_and_accept_member,
    isolated_auth_app,
    register_and_login_user,
)


def test_cross_tenant_rbac_and_delegated_source_acl_enforcement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gh_tok_a = "gh_token_user_a_secret"
    gh_tok_b = "gh_token_user_b_secret"
    jira_tok_a = "jira_token_user_a_secret"
    jira_tok_b = "jira_token_user_b_secret"
    oauth_user_cursor: dict[str, str] = {"gh_next": gh_tok_a, "jira_next": jira_tok_a}
    acl_state: dict[str, bool] = {
        "b_has_gh_repo": False,
        "b_has_jira_proj": False,
        "b_has_jira_sec2": False,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        auth_header = request.headers.get("Authorization", "")

        # GitHub OAuth
        if path == "/login/oauth/access_token":
            tok = oauth_user_cursor["gh_next"]
            return httpx.Response(200, json={"access_token": tok, "token_type": "bearer"})
        if path == "/user":
            if auth_header == f"Bearer {gh_tok_a}":
                return httpx.Response(
                    200,
                    json={"id": 101, "login": "user-a-gh", "email": "a@gh.test"},
                )
            return httpx.Response(200, json={"id": 202, "login": "user-b-gh", "email": "b@gh.test"})

        # Jira OAuth
        if path == "/oauth/token":
            tok = oauth_user_cursor["jira_next"]
            return httpx.Response(
                200,
                json={"access_token": tok, "expires_in": 3600, "token_type": "Bearer"},
            )
        if path == "/oauth/token/accessible-resources":
            if auth_header == f"Bearer {jira_tok_b}" and not acl_state["b_has_jira_proj"]:
                return httpx.Response(
                    200,
                    json=[{"id": "site-1", "name": "Site 1", "url": "https://site1.atlassian.net"}],
                )
            return httpx.Response(
                200,
                json=[{"id": "site-1", "name": "Site 1", "url": "https://site1.atlassian.net"}],
            )
        if path == "/ex/jira/site-1/rest/api/3/myself":
            if auth_header == f"Bearer {jira_tok_a}":
                return httpx.Response(200, json={"accountId": "jira-a", "displayName": "User A"})
            return httpx.Response(200, json={"accountId": "jira-b", "displayName": "User B"})

        # GitHub resource access + sync data
        if path == "/repos/org-x/secret-repo":
            if auth_header == f"Bearer {gh_tok_b}" and not acl_state["b_has_gh_repo"]:
                return httpx.Response(404, json={"message": "Not Found"})
            return httpx.Response(
                200,
                json={
                    "id": 7001,
                    "name": "secret-repo",
                    "full_name": "org-x/secret-repo",
                    "private": True,
                    "visibility": "private",
                    "default_branch": "main",
                    "html_url": "https://github.com/org-x/secret-repo",
                    "owner": {"login": "org-x"},
                },
            )
        if path == "/repos/org-x/secret-repo/issues":
            return httpx.Response(
                200,
                json=[
                    {
                        "number": 1,
                        "title": "Internal production database credentials design",
                        "state": "open",
                        "body": "Private architectural secret detail.",
                        "html_url": "https://github.com/org-x/secret-repo/issues/1",
                        "created_at": "2026-11-01T10:00:00Z",
                        "updated_at": "2026-11-01T10:00:00Z",
                        "user": {"login": "user-a-gh"},
                    }
                ],
            )
        if path == "/repos/org-x/secret-repo/issues/1/comments":
            return httpx.Response(200, json=[])
        if path == "/repos/org-x/secret-repo/commits":
            return httpx.Response(409, json={"message": "Git Repository is empty."})
        if path == "/repos/org-x/secret-repo/readme":
            return httpx.Response(404, json={})
        if path == "/repos/org-x/secret-repo/git/trees/main":
            return httpx.Response(404, json={})
        if path == "/repos/org-x/secret-repo/discussions":
            return httpx.Response(404, json={})

        # Jira project & issue ACL + sync data
        if path == "/ex/jira/site-1/rest/api/3/project/SEC":
            if auth_header == f"Bearer {jira_tok_b}" and not acl_state["b_has_jira_proj"]:
                return httpx.Response(403, json={"message": "Forbidden"})
            return httpx.Response(
                200,
                json={"id": "3001", "key": "SEC", "name": "Security Handover", "isPrivate": True},
            )
        if path == "/ex/jira/site-1/rest/api/3/search":
            return httpx.Response(
                200,
                json={
                    "total": 2,
                    "isLast": True,
                    "issues": [
                        {
                            "id": "4001",
                            "key": "SEC-1",
                            "fields": {
                                "summary": "Standard security checklist item",
                                "issuetype": {"name": "Task"},
                                "status": {"name": "Open"},
                                "created": "2026-11-01T10:00:00.000+0000",
                                "updated": "2026-11-01T10:00:00.000+0000",
                            },
                        },
                        {
                            "id": "4002",
                            "key": "SEC-2",
                            "fields": {
                                "summary": "Restricted incident root cause",
                                "issuetype": {"name": "Bug"},
                                "status": {"name": "Open"},
                                "security": {"id": "sec-level-1", "name": "Restricted"},
                                "created": "2026-11-01T11:00:00.000+0000",
                                "updated": "2026-11-01T11:00:00.000+0000",
                            },
                        },
                    ],
                },
            )
        if path == "/ex/jira/site-1/rest/api/3/issue/SEC-2":
            if auth_header == f"Bearer {jira_tok_b}" and not acl_state["b_has_jira_sec2"]:
                return httpx.Response(403, json={"message": "Issue restricted"})
            return httpx.Response(200, json={"key": "SEC-2"})
        if path.endswith("/comment"):
            return httpx.Response(200, json={"comments": []})
        if path.endswith("/worklog"):
            return httpx.Response(200, json={"worklogs": []})

        return httpx.Response(404, json={"message": f"Unhandled {path}"})

    transport = httpx.MockTransport(handler)
    with isolated_auth_app(
        monkeypatch,
        github_enabled=True,
        github_client_id="gh-acl-id",
        github_client_secret="gh-acl-secret-val",
        jira_enabled=True,
        jira_client_id="jira-acl-id",
        jira_client_secret="jira-acl-secret-val",
    ) as ctx:
        ctx.app.state.integration_http_transport = transport
        with TestClient(ctx.app) as client:
            owner_a = register_and_login_user(
                client,
                email="iso-owner-a@example.com",
                full_name="Owner A",
            )
            manager_b = register_and_login_user(
                client,
                email="iso-mgr-b@example.com",
                full_name="Manager B",
            )
            reviewer_a = register_and_login_user(
                client,
                email="iso-rev-a@example.com",
                full_name="Reviewer A",
            )
            outsider = register_and_login_user(
                client,
                email="iso-outsider@example.com",
                full_name="Outsider",
            )

            org_a = client.post(
                "/api/v1/organisations",
                headers=owner_a.headers,
                json={"name": "Tenant Alpha"},
            ).json()["id"]
            _ = client.post(
                "/api/v1/organisations",
                headers=outsider.headers,
                json={"name": "Tenant Outsider"},
            )

            invite_and_accept_member(
                client,
                organisation_id=org_a,
                inviter_headers=owner_a.headers,
                invitee=manager_b,
                role_name="org_admin",
            )
            invite_and_accept_member(
                client,
                organisation_id=org_a,
                inviter_headers=owner_a.headers,
                invitee=reviewer_a,
                role_name="org_member",
            )

            proj_id = client.post(
                f"/api/v1/organisations/{org_a}/projects",
                headers=owner_a.headers,
                json={"name": "ACL Handover", "status": "active", "visibility": "private"},
            ).json()["id"]
            assert (
                client.post(
                    f"/api/v1/projects/{proj_id}/members",
                    headers=owner_a.headers,
                    json={"user_id": str(manager_b.user_id), "role_name": "project_manager"},
                ).status_code
                == 201
            )
            assert (
                client.post(
                    f"/api/v1/projects/{proj_id}/members",
                    headers=owner_a.headers,
                    json={"user_id": str(reviewer_a.user_id), "role_name": "reviewer"},
                ).status_code
                == 201
            )

            # User A connects GitHub & Jira, creates mappings, and syncs both
            gh_start_a = client.post(
                f"/api/v1/organisations/{org_a}/integrations/github/oauth/start",
                headers=owner_a.headers,
            ).json()
            gh_conn_id = gh_start_a["source_connection_id"]
            gh_state_a = parse_qs(urlparse(gh_start_a["authorisation_url"]).query)["state"][0]
            assert (
                client.get(
                    "/api/v1/integrations/github/callback",
                    headers=owner_a.headers,
                    params={"code": "gh-a", "state": gh_state_a},
                ).status_code
                == 200
            )

            jira_start_a = client.post(
                f"/api/v1/organisations/{org_a}/integrations/jira/oauth/start",
                headers=owner_a.headers,
            ).json()
            jira_conn_id = jira_start_a["source_connection_id"]
            jira_state_a = parse_qs(urlparse(jira_start_a["authorisation_url"]).query)["state"][0]
            assert (
                client.get(
                    "/api/v1/integrations/jira/callback",
                    headers=owner_a.headers,
                    params={"code": "jira-a", "state": jira_state_a},
                ).status_code
                == 200
            )

            gh_map_id = client.post(
                f"/api/v1/projects/{proj_id}/integrations/github/mappings",
                headers=owner_a.headers,
                json={"source_connection_id": gh_conn_id, "owner": "org-x", "repo": "secret-repo"},
            ).json()["id"]
            jira_map_id = client.post(
                f"/api/v1/projects/{proj_id}/integrations/jira/mappings",
                headers=owner_a.headers,
                json={
                    "source_connection_id": jira_conn_id,
                    "cloud_id": "site-1",
                    "project_key": "SEC",
                },
            ).json()["id"]

            run_gh = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{gh_map_id}/sync",
                headers=owner_a.headers,
                json={"sync_mode": "initial"},
            ).json()["sync_run"]["id"]
            run_jira = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{jira_map_id}/sync",
                headers=owner_a.headers,
                json={"sync_mode": "initial"},
            ).json()["sync_run"]["id"]

            sync_worker = SourceSyncWorkerService(
                session_factory=ctx.session_factory,
                settings=ctx.settings,
                token_encryption=LocalTokenEncryptionService(
                    token_encryption_key=ctx.settings.security.token_encryption_key.get_secret_value()
                ),
                http_transport=transport,
                worker_id="acl-sync-worker",
            )
            assert sync_worker.drain_pending_jobs() == 2

            # Verify Owner A sees all 5 items (GH repo + GH issue #1 + Jira proj + SEC-1 + SEC-2)
            a_ev = client.get(
                f"/api/v1/projects/{proj_id}/evidence",
                headers=owner_a.headers,
                params={"limit": 50},
            ).json()
            assert a_ev["total"] == 5
            ext_map = {item["source_external_id"]: item["id"] for item in a_ev["items"]}
            gh_issue_id = ext_map["github:7001:issue:1"]
            sec1_id = ext_map["jira:site-1:issue:SEC-1"]
            sec2_id = ext_map["jira:site-1:issue:SEC-2"]

            # 1. Cross-org outsider receives 404 across all integration endpoints
            for method, path in (
                ("GET", f"/api/v1/organisations/{org_a}/integrations/connections"),
                ("GET", f"/api/v1/integrations/connections/{gh_conn_id}/github/repositories"),
                ("GET", f"/api/v1/integrations/connections/{jira_conn_id}/jira/sites"),
                ("POST", f"/api/v1/integrations/connections/{gh_conn_id}/disconnect"),
                ("GET", f"/api/v1/projects/{proj_id}/integrations/mappings"),
                ("DELETE", f"/api/v1/projects/{proj_id}/integrations/mappings/{gh_map_id}"),
                ("GET", f"/api/v1/projects/{proj_id}/integrations/sync-runs"),
                ("GET", f"/api/v1/integrations/sync-runs/{run_gh}"),
                ("POST", f"/api/v1/integrations/sync-runs/{run_gh}/cancel"),
            ):
                assert client.request(method, path, headers=outsider.headers).status_code == 404

            # 2. Reviewer can inspect mappings/sync history, CANNOT create mappings or trigger sync
            assert (
                client.get(
                    f"/api/v1/projects/{proj_id}/integrations/mappings",
                    headers=reviewer_a.headers,
                ).status_code
                == 200
            )
            assert (
                client.get(
                    f"/api/v1/projects/{proj_id}/integrations/sync-runs",
                    headers=reviewer_a.headers,
                ).status_code
                == 200
            )
            assert (
                client.post(
                    f"/api/v1/projects/{proj_id}/integrations/github/mappings",
                    headers=reviewer_a.headers,
                    json={"source_connection_id": gh_conn_id, "owner": "org-x", "repo": "other"},
                ).status_code
                == 403
            )
            assert (
                client.post(
                    f"/api/v1/projects/{proj_id}/integrations/mappings/{gh_map_id}/sync",
                    headers=reviewer_a.headers,
                    json={"sync_mode": "manual"},
                ).status_code
                == 403
            )
            assert (
                client.post(
                    f"/api/v1/integrations/sync-runs/{run_jira}/cancel",
                    headers=reviewer_a.headers,
                ).status_code
                == 403
            )

            # 3. Manager B (even as project_manager!) CANNOT borrow Owner A's tokens or bypass ACL!
            conns_b = client.get(
                f"/api/v1/organisations/{org_a}/integrations/connections",
                headers=manager_b.headers,
            ).json()
            assert all(c["caller_authorisation"] is None for c in conns_b["items"])

            need_oauth = client.get(
                f"/api/v1/integrations/connections/{gh_conn_id}/github/repositories",
                headers=manager_b.headers,
            )
            assert need_oauth.status_code == 403
            assert need_oauth.json()["error"]["code"] == "SOURCE_AUTHORISATION_REQUIRED"

            b_list_0 = client.get(
                f"/api/v1/projects/{proj_id}/evidence",
                headers=manager_b.headers,
            ).json()
            assert b_list_0["total"] == 0

            for blocked_id in (gh_issue_id, sec1_id, sec2_id):
                resp = client.get(f"/api/v1/evidence/{blocked_id}", headers=manager_b.headers)
                assert resp.status_code == 403
                assert resp.json()["error"]["code"] == "SOURCE_ACCESS_DENIED"

            # 4. Manager B connects their own delegated GitHub & Jira tokens on SAME connections
            oauth_user_cursor["gh_next"] = gh_tok_b
            oauth_user_cursor["jira_next"] = jira_tok_b

            gh_start_b = client.post(
                f"/api/v1/organisations/{org_a}/integrations/github/oauth/start",
                headers=manager_b.headers,
                json={"source_connection_id": gh_conn_id},
            ).json()
            gh_state_b = parse_qs(urlparse(gh_start_b["authorisation_url"]).query)["state"][0]
            assert (
                client.get(
                    "/api/v1/integrations/github/callback",
                    headers=manager_b.headers,
                    params={"code": "gh-b", "state": gh_state_b},
                ).status_code
                == 200
            )

            jira_start_b = client.post(
                f"/api/v1/organisations/{org_a}/integrations/jira/oauth/start",
                headers=manager_b.headers,
                json={"source_connection_id": jira_conn_id},
            ).json()
            jira_state_b = parse_qs(urlparse(jira_start_b["authorisation_url"]).query)["state"][0]
            assert (
                client.get(
                    "/api/v1/integrations/jira/callback",
                    headers=manager_b.headers,
                    params={"code": "jira-b", "state": jira_state_b},
                ).status_code
                == 200
            )

            # While provider denies Manager B -> verify-access returns False & evidence stays 403
            v_gh_deny = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{gh_map_id}/verify-access",
                headers=manager_b.headers,
            )
            assert v_gh_deny.status_code == 200
            assert v_gh_deny.json()["verified"] is False
            assert (
                client.get(f"/api/v1/evidence/{gh_issue_id}", headers=manager_b.headers).status_code
                == 403
            )

            # 5. Grant Manager B access to GitHub repo & Jira SEC project EXCEPT restricted SEC-2!
            acl_state["b_has_gh_repo"] = True
            acl_state["b_has_jira_proj"] = True
            acl_state["b_has_jira_sec2"] = False

            v_gh_ok = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{gh_map_id}/verify-access",
                headers=manager_b.headers,
            )
            assert v_gh_ok.status_code == 200
            assert v_gh_ok.json()["verified"] is True

            v_jira_ok = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{jira_map_id}/verify-access",
                headers=manager_b.headers,
            )
            assert v_jira_ok.status_code == 200
            assert v_jira_ok.json()["verified"] is True

            # Manager B can now read GitHub issue & SEC-1, yet SEC-2 STILL fails closed (403)!
            assert (
                client.get(f"/api/v1/evidence/{gh_issue_id}", headers=manager_b.headers).status_code
                == 200
            )
            assert (
                client.get(f"/api/v1/evidence/{sec1_id}", headers=manager_b.headers).status_code
                == 200
            )
            assert (
                client.get(f"/api/v1/evidence/{sec2_id}", headers=manager_b.headers).status_code
                == 403
            )
            b_list_partial = client.get(
                f"/api/v1/projects/{proj_id}/evidence",
                headers=manager_b.headers,
                params={"limit": 50},
            ).json()
            visible_ids = {item["id"] for item in b_list_partial["items"]}
            assert b_list_partial["total"] == 4
            assert sec2_id not in visible_ids

            # Verify immutable audits recorded cleanly without exposing any secret tokens
            with ctx.session_factory() as session:
                logs = list(session.execute(select(AuditLog)).scalars().all())
                event_types = {log.event_type for log in logs}
                assert {
                    "integration.oauth_started",
                    "integration.oauth_connected",
                    "integration.mapping_created",
                    "integration.sync_queued",
                    "integration.sync_started",
                    "integration.sync_completed",
                    "integration.access_verified",
                    "integration.access_denied",
                    "evidence.source_acl_denied",
                }.issubset(event_types)
                for log in logs:
                    blob = f"{log.event_type} {log.event_metadata}"
                    for secret in (gh_tok_a, gh_tok_b, jira_tok_a, jira_tok_b):
                        assert secret not in blob
