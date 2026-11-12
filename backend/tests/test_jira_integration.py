"""Integration tests for delegated Jira Cloud 3LO discovery, ADF extraction, and syncs."""

from __future__ import annotations

import json
import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import utc_now
from app.models.enums import (
    BackgroundJobStatus,
    SourceSyncRunStatus,
    SourceVisibilityPolicy,
)
from app.models.integration import SourceAccessPolicy
from app.models.job import BackgroundJob
from app.services.integrations.sync_worker import SourceSyncWorkerService
from app.services.token_encryption import LocalTokenEncryptionService
from tests.conftest import isolated_auth_app, register_and_login_user


def test_jira_discovery_adf_sync_security_policy_refresh_429_and_cancel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_jql: list[str] = []
    state: dict[str, object] = {
        "current_access": "jira_tok_1",
        "current_refresh": "jira_rt_1",
        "force_401_once": False,
        "force_429_once": False,
    }

    adf_description = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Failover Architecture"}],
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Primary database requires read replica promotion. "},
                    {"type": "mention", "attrs": {"text": "@oncall-dba"}},
                ],
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": "Verify WAL archive lag < 5s"}
                                ],
                            }
                        ],
                    }
                ],
            },
            {
                "type": "codeBlock",
                "attrs": {"language": "sql"},
                "content": [{"type": "text", "text": "SELECT pg_is_in_recovery();"}],
            },
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/oauth/token":
            body = json.loads(request.content.decode("utf-8"))
            if body.get("grant_type") == "authorization_code":
                return httpx.Response(
                    200,
                    json={
                        "access_token": "jira_tok_1",
                        "refresh_token": "jira_rt_1",
                        "expires_in": 3600,
                        "token_type": "Bearer",
                        "scope": "read:jira-work read:jira-user offline_access",
                    },
                )
            if body.get("grant_type") == "refresh_token":
                assert body.get("refresh_token") == state["current_refresh"]
                state["current_access"] = "jira_tok_2_refreshed"
                state["current_refresh"] = "jira_rt_2_rotated"
                return httpx.Response(
                    200,
                    json={
                        "access_token": "jira_tok_2_refreshed",
                        "refresh_token": "jira_rt_2_rotated",
                        "expires_in": 3600,
                        "token_type": "Bearer",
                    },
                )

        if request.headers.get("Authorization") != f"Bearer {state['current_access']}":
            return httpx.Response(401, json={"message": "Unauthorized token"})

        if path == "/oauth/token/accessible-resources":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "site-cloud-77",
                        "name": "Engineering Cloud",
                        "url": "https://eng-demo.atlassian.net",
                        "scopes": ["read:jira-work", "read:jira-user"],
                    }
                ],
            )
        if path == "/ex/jira/site-cloud-77/rest/api/3/myself":
            return httpx.Response(
                200,
                json={
                    "accountId": "acct-jira-1",
                    "displayName": "Maya Lead",
                    "emailAddress": "maya@example.com",
                },
            )
        if path == "/ex/jira/site-cloud-77/rest/api/3/project/search":
            return httpx.Response(
                200,
                json={
                    "startAt": 0,
                    "maxResults": 50,
                    "total": 1,
                    "isLast": True,
                    "values": [
                        {
                            "id": "10500",
                            "key": "PLAT",
                            "name": "Platform Reliability",
                            "projectTypeKey": "software",
                            "style": "classic",
                            "isPrivate": True,
                        }
                    ],
                },
            )
        if path == "/ex/jira/site-cloud-77/rest/api/3/project/PLAT":
            return httpx.Response(
                200,
                json={
                    "id": "10500",
                    "key": "PLAT",
                    "name": "Platform Reliability",
                    "projectTypeKey": "software",
                    "style": "classic",
                    "isPrivate": True,
                },
            )
        if path == "/ex/jira/site-cloud-77/rest/api/3/search":
            if state["force_401_once"]:
                state["force_401_once"] = False
                return httpx.Response(401, json={"message": "Expired mid-request"})
            if state["force_429_once"]:
                state["force_429_once"] = False
                return httpx.Response(
                    429,
                    headers={"Retry-After": "3"},
                    json={"message": "Rate limit hit"},
                )
            jql = request.url.params.get("jql", "")
            observed_jql.append(jql)
            if "updated >=" in jql:
                return httpx.Response(200, json={"total": 0, "isLast": True, "issues": []})
            return httpx.Response(
                200,
                json={
                    "total": 2,
                    "isLast": True,
                    "issues": [
                        {
                            "id": "20001",
                            "key": "PLAT-10",
                            "fields": {
                                "summary": "Zero-downtime Postgres migration playbook",
                                "issuetype": {"name": "Story"},
                                "status": {"name": "In Progress"},
                                "priority": {"name": "High"},
                                "assignee": {"displayName": "Sam DBA"},
                                "reporter": {"displayName": "Maya Lead"},
                                "labels": ["database", "handover"],
                                "components": [{"name": "storage"}],
                                "description": adf_description,
                                "parent": {
                                    "key": "PLAT-1",
                                    "fields": {"summary": "Q4 Resilience Epic"},
                                },
                                "issuelinks": [
                                    {
                                        "type": {"name": "Blocks", "outward": "blocks"},
                                        "outwardIssue": {
                                            "key": "PLAT-12",
                                            "fields": {
                                                "summary": "Cutover traffic",
                                                "status": {"name": "To Do"},
                                            },
                                        },
                                    }
                                ],
                                "created": "2026-10-10T09:00:00.000+0000",
                                "updated": "2026-11-01T16:30:00.000+0000",
                            },
                            "changelog": {
                                "histories": [
                                    {
                                        "author": {"displayName": "Maya Lead"},
                                        "created": "2026-10-12T10:00:00.000+0000",
                                        "items": [
                                            {
                                                "field": "status",
                                                "fromString": "To Do",
                                                "toString": "In Progress",
                                            }
                                        ],
                                    }
                                ]
                            },
                        },
                        {
                            "id": "20002",
                            "key": "PLAT-99",
                            "fields": {
                                "summary": "Executive KMS master rotation window",
                                "issuetype": {"name": "Task"},
                                "status": {"name": "Open"},
                                "security": {"id": "sec-99", "name": "Leadership Only"},
                                "reporter": {"displayName": "Maya Lead"},
                                "description": {
                                    "type": "doc",
                                    "version": 1,
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Confidential rotation dates.",
                                                }
                                            ],
                                        }
                                    ],
                                },
                                "created": "2026-10-18T12:00:00.000+0000",
                                "updated": "2026-11-02T08:00:00.000+0000",
                            },
                        },
                    ],
                },
            )
        if path == "/ex/jira/site-cloud-77/rest/api/3/issue/PLAT-10/comment":
            return httpx.Response(
                200,
                json={
                    "comments": [
                        {
                            "author": {"displayName": "Sam DBA"},
                            "created": "2026-10-19T11:00:00.000+0000",
                            "body": {
                                "type": "doc",
                                "version": 1,
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": (
                                                    "Dry-run completed without lock contention."
                                                ),
                                            }
                                        ],
                                    }
                                ],
                            },
                        }
                    ]
                },
            )
        if path == "/ex/jira/site-cloud-77/rest/api/3/issue/PLAT-10/worklog":
            return httpx.Response(
                200,
                json={
                    "worklogs": [
                        {
                            "author": {"displayName": "Sam DBA"},
                            "timeSpent": "2h",
                            "comment": {
                                "type": "doc",
                                "version": 1,
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {"type": "text", "text": "Benchmarked pg_repack."}
                                        ],
                                    }
                                ],
                            },
                        }
                    ]
                },
            )
        if path.endswith("/comment"):
            return httpx.Response(200, json={"comments": []})
        if path.endswith("/worklog"):
            return httpx.Response(200, json={"worklogs": []})
        return httpx.Response(404, json={"message": f"Unhandled {path}"})

    transport = httpx.MockTransport(handler)
    with isolated_auth_app(
        monkeypatch,
        jira_enabled=True,
        jira_client_id="jira-cid",
        jira_client_secret="jira-csec-secret-value",
        worker_max_attempts=2,
        worker_retry_base_seconds=2,
    ) as ctx:
        ctx.app.state.integration_http_transport = transport
        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client,
                email="jira-owner@example.com",
                full_name="Jira Owner",
            )
            org_id = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "Jira Org"},
            ).json()["id"]
            proj_id = client.post(
                f"/api/v1/organisations/{org_id}/projects",
                headers=owner.headers,
                json={"name": "Jira Workspace", "status": "active", "visibility": "private"},
            ).json()["id"]

            # OAuth connect
            start = client.post(
                f"/api/v1/organisations/{org_id}/integrations/jira/oauth/start",
                headers=owner.headers,
            ).json()
            conn_id = start["source_connection_id"]
            raw_state = parse_qs(urlparse(start["authorisation_url"]).query)["state"][0]
            assert (
                client.get(
                    "/api/v1/integrations/jira/callback",
                    headers=owner.headers,
                    params={"code": "jira_code", "state": raw_state},
                ).status_code
                == 200
            )

            # Site & project discovery
            sites = client.get(
                f"/api/v1/integrations/connections/{conn_id}/jira/sites",
                headers=owner.headers,
            )
            assert sites.status_code == 200
            assert sites.json()["items"][0]["cloud_id"] == "site-cloud-77"

            projects = client.get(
                f"/api/v1/integrations/connections/{conn_id}/jira/projects",
                headers=owner.headers,
                params={"cloud_id": "site-cloud-77", "query": "PLAT"},
            )
            assert projects.status_code == 200
            assert projects.json()["projects"][0]["key"] == "PLAT"

            # Reject unsafe JQL filter inputs cleanly
            for bad_jql in (
                "status != Done; DROP",
                "status = Open\nORDER BY id",
                "assignee = a order by id",
            ):
                bad_map = client.post(
                    f"/api/v1/projects/{proj_id}/integrations/jira/mappings",
                    headers=owner.headers,
                    json={
                        "source_connection_id": conn_id,
                        "cloud_id": "site-cloud-77",
                        "project_key": "PLAT",
                        "jql_filter": bad_jql,
                    },
                )
                assert bad_map.status_code == 400
                assert bad_map.json()["error"]["code"] == "INVALID_JQL_FILTER"

            # Create valid Jira project mapping
            m_resp = client.post(
                f"/api/v1/projects/{proj_id}/integrations/jira/mappings",
                headers=owner.headers,
                json={
                    "source_connection_id": conn_id,
                    "cloud_id": "site-cloud-77",
                    "project_key": "PLAT",
                    "jql_filter": 'status != "Archived"',
                },
            )
            assert m_resp.status_code == 201
            mapping_id = m_resp.json()["id"]

            sync_worker = SourceSyncWorkerService(
                session_factory=ctx.session_factory,
                settings=ctx.settings,
                token_encryption=LocalTokenEncryptionService(
                    token_encryption_key=ctx.settings.security.token_encryption_key.get_secret_value()
                ),
                http_transport=transport,
                worker_id="jira-sync-worker",
            )

            # 1. Queue initial sync + simulate reactive HTTP 401 triggering refresh rotation!
            state["force_401_once"] = True
            s1 = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{mapping_id}/sync",
                headers=owner.headers,
                json={"sync_mode": "initial"},
            )
            assert s1.status_code == 202
            run_1_id = s1.json()["sync_run"]["id"]

            # Duplicate active sync rejected with 409
            dup_s = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{mapping_id}/sync",
                headers=owner.headers,
                json={"sync_mode": "initial"},
            )
            assert dup_s.status_code == 409
            assert dup_s.json()["error"]["code"] == "SYNC_ALREADY_ACTIVE"

            assert sync_worker.process_next_job() is True
            assert state["current_access"] == "jira_tok_2_refreshed"

            run_1 = client.get(
                f"/api/v1/integrations/sync-runs/{run_1_id}",
                headers=owner.headers,
            ).json()
            assert run_1["status"] == SourceSyncRunStatus.SUCCEEDED.value
            assert run_1["items_discovered"] == 3  # project metadata + PLAT-10 + PLAT-99
            assert run_1["items_created"] == 3

            ev_list = client.get(
                f"/api/v1/projects/{proj_id}/evidence",
                headers=owner.headers,
                params={"limit": 50},
            ).json()
            by_ext = {item["source_external_id"]: item for item in ev_list["items"]}
            plat10 = by_ext["jira:site-cloud-77:issue:PLAT-10"]
            plat99 = by_ext["jira:site-cloud-77:issue:PLAT-99"]

            plat10_detail = client.get(
                f"/api/v1/evidence/{plat10['id']}",
                headers=owner.headers,
            ).json()
            text10 = plat10_detail["extracted_content"]["extracted_text"]
            assert "## Failover Architecture" in text10
            assert "@oncall-dba" in text10
            assert "- Verify WAL archive lag < 5s" in text10
            assert "SELECT pg_is_in_recovery();" in text10
            assert "Dry-run completed without lock contention." in text10
            assert "Benchmarked pg_repack." in text10
            assert "changed `status`: `To Do` -> `In Progress`" in text10
            assert len(plat10_detail["metadata_json"]["issue_links"]) == 2
            assert len(plat10_detail["extracted_content"]["pages"]) == 3

            # PLAT-99 created dedicated fail-closed security-level sub-policy
            with ctx.session_factory() as session:
                sec_policy = session.execute(
                    select(SourceAccessPolicy).where(
                        SourceAccessPolicy.scope_identifier == "site-cloud-77:PLAT:security:sec-99"
                    )
                ).scalar_one()
                assert (
                    sec_policy.visibility_policy
                    == SourceVisibilityPolicy.RESTRICTED_FAIL_CLOSED.value
                )
            assert plat99["acl_scope"] == "source_restricted"

            # 2. Incremental sync uses `updated >=` cursor + 429 retry scheduling
            state["force_429_once"] = True
            s2 = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{mapping_id}/sync",
                headers=owner.headers,
                json={"sync_mode": "incremental"},
            ).json()
            run_2_id = s2["sync_run"]["id"]
            job_2_id = uuid.UUID(s2["job"]["id"])

            assert sync_worker.process_next_job() is True
            r2_mid = client.get(
                f"/api/v1/integrations/sync-runs/{run_2_id}",
                headers=owner.headers,
            ).json()
            assert r2_mid["status"] == SourceSyncRunStatus.QUEUED.value
            assert r2_mid["error_code"] == "JIRA_RATE_LIMITED"

            with ctx.session_factory() as session:
                j2 = session.get(BackgroundJob, job_2_id)
                assert j2 is not None
                j2.next_retry_at = utc_now() - timedelta(seconds=1)
                session.commit()

            assert sync_worker.process_next_job() is True
            r2_done = client.get(
                f"/api/v1/integrations/sync-runs/{run_2_id}",
                headers=owner.headers,
            ).json()
            assert r2_done["status"] == SourceSyncRunStatus.SUCCEEDED.value
            assert any("updated >=" in q for q in observed_jql)

            # 3. Queued cancellation cancels run + job and worker skips cancelled job
            s3 = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{mapping_id}/sync",
                headers=owner.headers,
                json={"sync_mode": "manual"},
            ).json()
            run_3_id = s3["sync_run"]["id"]
            cancel_resp = client.post(
                f"/api/v1/integrations/sync-runs/{run_3_id}/cancel",
                headers=owner.headers,
            )
            assert cancel_resp.status_code == 200
            assert cancel_resp.json()["sync_run"]["status"] == SourceSyncRunStatus.CANCELLED.value
            assert cancel_resp.json()["job"]["status"] == BackgroundJobStatus.CANCELLED.value
            assert sync_worker.process_next_job() is False
