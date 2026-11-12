"""Comprehensive functional and isolation tests for Project Workspace (Phase 2.4 / Gate 3)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import isolated_auth_app

_PASSWORD = "Handover!Project2026#Secure"


def _register_and_login(
    client: TestClient,
    *,
    full_name: str,
    email: str,
) -> tuple[str, str]:
    reg = client.post(
        "/api/v1/auth/register",
        json={"full_name": full_name, "email": email, "password": _PASSWORD},
    )
    assert reg.status_code == 201
    user_id = str(reg.json()["user"]["id"])

    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": _PASSWORD},
    )
    assert login.status_code == 200
    return user_id, str(login.json()["access_token"])


def test_project_workspace_full_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        # 1. Register 3 users: Alice (PM/Owner), Bob (Departing Member), Charlie (Successor)
        alice_id, alice_token = _register_and_login(
            client, full_name="Alice Owner", email="alice.owner@example.com"
        )
        bob_id, bob_token = _register_and_login(
            client, full_name="Bob Departing", email="bob.departing@example.com"
        )
        charlie_id, charlie_token = _register_and_login(
            client, full_name="Charlie Successor", email="charlie.successor@example.com"
        )

        alice_hdr = {"Authorization": f"Bearer {alice_token}"}
        bob_hdr = {"Authorization": f"Bearer {bob_token}"}
        charlie_hdr = {"Authorization": f"Bearer {charlie_token}"}

        # 2. Alice creates Organisation
        org_resp = client.post(
            "/api/v1/organisations",
            headers=alice_hdr,
            json={"name": "Engineering Operations", "slug": "eng-ops"},
        )
        assert org_resp.status_code == 201
        org_id = org_resp.json()["id"]

        # 3. Add Bob and Charlie to Organisation via direct invitations
        invites = [
            (bob_id, "bob.departing@example.com", bob_token),
            (charlie_id, "charlie.successor@example.com", charlie_token),
        ]
        for _uid, uemail, utok in invites:
            inv = client.post(
                f"/api/v1/organisations/{org_id}/invitations",
                headers=alice_hdr,
                json={"email": uemail, "role_name": "org_member"},
            )
            assert inv.status_code == 201
            raw_token = inv.json()["development_invitation_token"]
            assert raw_token is not None

            accept = client.post(
                f"/api/v1/invitations/{raw_token}/accept",
                headers={"Authorization": f"Bearer {utok}"},
            )
            assert accept.status_code == 200

        # 4. Alice creates Project Workspace
        proj_resp = client.post(
            f"/api/v1/organisations/{org_id}/projects",
            headers=alice_hdr,
            json={
                "name": "Core Banking Transition",
                "slug": "core-banking",
                "description": "Handover for legacy banking core",
                "status": "active",
                "visibility": "private",
                "start_date": "2026-01-01",
                "target_completion_date": "2026-06-30",
            },
        )
        assert proj_resp.status_code == 201
        proj_id = proj_resp.json()["id"]

        # 5. Add Bob and Charlie as project members with responsibility descriptions
        bob_resp = "Lead architect for ledger service and settlement"
        charlie_resp = "Incoming tech lead taking over ledger service"
        add_bob = client.post(
            f"/api/v1/projects/{proj_id}/members",
            headers=alice_hdr,
            json={
                "user_id": bob_id,
                "role_name": "project_member",
                "responsibility_description": bob_resp,
            },
        )
        assert add_bob.status_code == 201
        assert add_bob.json()["responsibility_description"] == bob_resp

        add_charlie = client.post(
            f"/api/v1/projects/{proj_id}/members",
            headers=alice_hdr,
            json={
                "user_id": charlie_id,
                "role_name": "project_member",
                "responsibility_description": charlie_resp,
            },
        )
        assert add_charlie.status_code == 201
        assert add_charlie.json()["responsibility_description"] == charlie_resp

        # 6. Verify transition configuration guards
        # Guard A: Departing user == Successor user must fail
        same_user_fail = client.put(
            f"/api/v1/projects/{proj_id}/transition",
            headers=alice_hdr,
            json={
                "departing_user_id": bob_id,
                "successor_user_id": bob_id,
                "workflow_stage": "planning",
            },
        )
        assert same_user_fail.status_code in (400, 422)

        # Guard B: Invalid date ordering must fail
        invalid_dates_fail = client.put(
            f"/api/v1/projects/{proj_id}/transition",
            headers=alice_hdr,
            json={
                "departing_user_id": bob_id,
                "successor_user_id": charlie_id,
                "capture_start_date": "2026-06-30",
                "capture_end_date": "2026-01-01",
            },
        )
        assert invalid_dates_fail.status_code in (400, 422)

        # Guard C: Valid configuration succeeds
        trans_ok = client.put(
            f"/api/v1/projects/{proj_id}/transition",
            headers=alice_hdr,
            json={
                "departing_user_id": bob_id,
                "successor_user_id": charlie_id,
                "workflow_stage": "ingestion",
                "handover_scope": "Full ledger core, payment gateways, and batch scripts.",
                "source_scope": ["github:acme/ledger-core", "jira:LEDGER"],
                "capture_start_date": "2026-01-01",
                "capture_end_date": "2026-06-30",
                "context_notes": "Pay special attention to weekly settlement reconciliation.",
            },
        )
        assert trans_ok.status_code == 200
        trans_data = trans_ok.json()
        assert trans_data["departing_user"]["id"] == bob_id
        assert trans_data["successor_user"]["id"] == charlie_id
        assert trans_data["workflow_stage"] == "ingestion"
        assert len(trans_data["source_scope"]) == 2

        # 7. Query transition configuration
        trans_get = client.get(
            f"/api/v1/projects/{proj_id}/transition",
            headers=bob_hdr,
        )
        assert trans_get.status_code == 200
        assert trans_get.json()["departing_user"]["full_name"] == "Bob Departing"

        # 8. Query Project Overview Dashboard aggregation
        overview = client.get(
            f"/api/v1/projects/{proj_id}/overview",
            headers=charlie_hdr,
        )
        assert overview.status_code == 200
        ov_data = overview.json()

        # Verify Project Summary Card
        assert ov_data["project_summary"]["name"] == "Core Banking Transition"
        assert ov_data["project_summary"]["workflow_stage"] == "ingestion"
        assert ov_data["project_summary"]["departing_member"]["id"] == bob_id
        assert ov_data["project_summary"]["successor"]["id"] == charlie_id

        # Verify Connected Sources Card
        assert ov_data["connected_sources"]["total_sources"] == 0
        assert ov_data["connected_sources"]["health_status"] == "not_configured"

        # Verify Evidence Overview Card
        assert ov_data["evidence_overview"]["total_records"] == 0
        assert ov_data["evidence_overview"]["document_count"] == 0

        # Verify Knowledge Overview Card
        assert ov_data["knowledge_overview"]["availability"] == "available"
        assert ov_data["knowledge_overview"]["decisions_count"] == 0

        # Verify Team Ownership Card
        team_members = ov_data["team_ownership"]
        assert len(team_members) >= 3
        bob_entry = next(m for m in team_members if m["user_id"] == bob_id)
        assert bob_entry["responsibility_description"] == bob_resp

        # 9. Query Project Activity Stream
        activity = client.get(
            f"/api/v1/projects/{proj_id}/activity?limit=10",
            headers=alice_hdr,
        )
        assert activity.status_code == 200
        act_data = activity.json()
        assert act_data["total"] >= 1
        event_types = [item["event_type"] for item in act_data["items"]]
        assert "project.transition.configured" in event_types

        # 10. Cross-project isolation: Non-member cannot access private project overview
        david_id, david_token = _register_and_login(
            client, full_name="David Outsider", email="david.outsider@example.com"
        )
        david_hdr = {"Authorization": f"Bearer {david_token}"}
        # Non-org user receives 404 so project existence is not leaked
        non_org_resp = client.get(
            f"/api/v1/projects/{proj_id}/overview",
            headers=david_hdr,
        )
        assert non_org_resp.status_code == 404

        # Add David to org as standard org_member, but NOT to private project
        inv_d = client.post(
            f"/api/v1/organisations/{org_id}/invitations",
            headers=alice_hdr,
            json={"email": "david.outsider@example.com", "role_name": "org_member"},
        )
        assert inv_d.status_code == 201
        tok_d = inv_d.json()["development_invitation_token"]
        client.post(
            f"/api/v1/invitations/{tok_d}/accept",
            headers=david_hdr,
        )

        # David in org but not on private project receives 404 (opaque existence protection)
        non_proj_resp = client.get(
            f"/api/v1/projects/{proj_id}/overview",
            headers=david_hdr,
        )
        assert non_proj_resp.status_code in (403, 404)
