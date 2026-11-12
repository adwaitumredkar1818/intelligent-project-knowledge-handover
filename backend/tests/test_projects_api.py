"""API and business-rule tests for project workspaces, visibility, lifecycle, and members."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.models.enums import RoleName
from tests.conftest import (
    invite_and_accept_member,
    isolated_auth_app,
    register_and_login_user,
)


def test_project_creation_per_org_slug_uniqueness_and_visibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        owner = register_and_login_user(
            client,
            email="owner@proj.example.com",
            full_name="Org Owner",
        )
        org_member = register_and_login_user(
            client,
            email="member@proj.example.com",
            full_name="Plain Org Member",
        )

        org_a = client.post(
            "/api/v1/organisations",
            headers=owner.headers,
            json={"name": "Tenant Alpha"},
        ).json()["id"]
        org_b = client.post(
            "/api/v1/organisations",
            headers=owner.headers,
            json={"name": "Tenant Beta"},
        ).json()["id"]

        invite_and_accept_member(
            client,
            organisation_id=org_a,
            inviter_headers=owner.headers,
            invitee=org_member,
            role_name="org_member",
        )

        # Create private and organisation-visible projects in Tenant Alpha
        priv = client.post(
            f"/api/v1/organisations/{org_a}/projects",
            headers=owner.headers,
            json={
                "name": "Core Migration",
                "visibility": "private",
                "status": "planning",
                "start_date": "2026-11-01",
                "target_completion_date": "2026-12-31",
            },
        )
        assert priv.status_code == 201
        priv_data = priv.json()
        priv_id = priv_data["id"]
        assert priv_data["slug"] == "core-migration"
        assert priv_data["visibility"] == "private"
        assert priv_data["status"] == "planning"
        assert priv_data["my_project_role"] == "project_manager"
        assert "project.manage" in priv_data["effective_permissions"]

        # Duplicate slug in same org conflicts cleanly
        dup_same_org = client.post(
            f"/api/v1/organisations/{org_a}/projects",
            headers=owner.headers,
            json={"name": "Another Core", "slug": "core-migration"},
        )
        assert dup_same_org.status_code == 409
        assert dup_same_org.json()["error"]["code"] == "PROJECT_SLUG_ALREADY_EXISTS"

        # Same slug in a DIFFERENT organisation succeeds!
        same_slug_other_org = client.post(
            f"/api/v1/organisations/{org_b}/projects",
            headers=owner.headers,
            json={"name": "Beta Copy", "slug": "core-migration"},
        )
        assert same_slug_other_org.status_code == 201

        # Create organisation-visible project in Tenant Alpha
        shared = client.post(
            f"/api/v1/organisations/{org_a}/projects",
            headers=owner.headers,
            json={"name": "Shared Handover", "visibility": "organisation", "status": "active"},
        )
        assert shared.status_code == 201
        shared_id = shared.json()["id"]

        # Invalid completion date before start date -> 422
        bad_dates = client.post(
            f"/api/v1/organisations/{org_a}/projects",
            headers=owner.headers,
            json={
                "name": "Bad Dates",
                "start_date": "2026-12-10",
                "target_completion_date": "2026-11-01",
            },
        )
        assert bad_dates.status_code == 422

        # org_member cannot create projects
        member_create = client.post(
            f"/api/v1/organisations/{org_a}/projects",
            headers=org_member.headers,
            json={"name": "Forbidden Project"},
        )
        assert member_create.status_code == 403

        # Visibility check: org_member sees ONLY shared project, NOT private project
        member_list = client.get(
            f"/api/v1/organisations/{org_a}/projects",
            headers=org_member.headers,
        )
        assert member_list.status_code == 200
        assert member_list.json()["total"] == 1
        assert member_list.json()["items"][0]["id"] == shared_id

        # Private project returns 404 to non-member org_member
        priv_read = client.get(f"/api/v1/projects/{priv_id}", headers=org_member.headers)
        assert priv_read.status_code == 404

        # Organisation-visible project is readable by org_member, NOT manageable
        shared_read = client.get(f"/api/v1/projects/{shared_id}", headers=org_member.headers)
        assert shared_read.status_code == 200
        assert shared_read.json()["my_project_role"] is None
        assert (
            client.patch(
                f"/api/v1/projects/{shared_id}",
                headers=org_member.headers,
                json={"name": "Hijack"},
            ).status_code
            == 403
        )
        assert (
            client.get(
                f"/api/v1/projects/{shared_id}/members",
                headers=org_member.headers,
            ).status_code
            == 403
        )


def test_project_lifecycle_ownership_and_member_role_management(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        owner = register_and_login_user(
            client,
            email="owner@life.example.com",
            full_name="Owner Life",
        )
        dev = register_and_login_user(
            client,
            email="dev@life.example.com",
            full_name="Dev Member",
        )
        reviewer = register_and_login_user(
            client,
            email="reviewer@life.example.com",
            full_name="Reviewer User",
        )

        org_id = client.post(
            "/api/v1/organisations",
            headers=owner.headers,
            json={"name": "Lifecycle Org"},
        ).json()["id"]

        for u in (dev, reviewer):
            invite_and_accept_member(
                client,
                organisation_id=org_id,
                inviter_headers=owner.headers,
                invitee=u,
                role_name="org_member",
            )

        proj_id = client.post(
            f"/api/v1/organisations/{org_id}/projects",
            headers=owner.headers,
            json={"name": "Handover Alpha", "visibility": "private"},
        ).json()["id"]

        # Invalid status transition (planning -> completed) blocked
        bad_transition = client.patch(
            f"/api/v1/projects/{proj_id}",
            headers=owner.headers,
            json={"status": "completed"},
        )
        assert bad_transition.status_code == 409
        assert bad_transition.json()["error"]["code"] == "INVALID_PROJECT_STATUS_TRANSITION"

        # Valid lifecycle path: planning -> active -> on_hold -> active -> completed
        for next_status in ("active", "on_hold", "active", "completed"):
            step = client.patch(
                f"/api/v1/projects/{proj_id}",
                headers=owner.headers,
                json={"status": next_status},
            )
            assert step.status_code == 200
            assert step.json()["status"] == next_status

        # Add dev (project_member) and reviewer (reviewer)
        added_dev = client.post(
            f"/api/v1/projects/{proj_id}/members",
            headers=owner.headers,
            json={"user_id": str(dev.user_id), "role_name": "project_member"},
        )
        assert added_dev.status_code == 201
        assert added_dev.json()["role_name"] == "project_member"

        added_rev = client.post(
            f"/api/v1/projects/{proj_id}/members",
            headers=owner.headers,
            json={"user_id": str(reviewer.user_id), "role_name": "reviewer"},
        )
        assert added_rev.status_code == 201
        assert added_rev.json()["role_name"] == "reviewer"

        # Verify project_member permissions (can read & list members, cannot manage or review)
        dev_detail = client.get(f"/api/v1/projects/{proj_id}", headers=dev.headers)
        assert dev_detail.status_code == 200
        assert dev_detail.json()["my_project_role"] == "project_member"
        assert "project.evidence.contribute" in dev_detail.json()["effective_permissions"]
        assert "project.knowledge.review" not in dev_detail.json()["effective_permissions"]

        rev_detail = client.get(f"/api/v1/projects/{proj_id}", headers=reviewer.headers)
        assert rev_detail.status_code == 200
        assert "project.knowledge.review" in rev_detail.json()["effective_permissions"]
        assert "project.evidence.contribute" not in rev_detail.json()["effective_permissions"]

        # Reject assigning org/platform role at project scope
        bad_scope = client.post(
            f"/api/v1/projects/{proj_id}/members",
            headers=owner.headers,
            json={"user_id": str(dev.user_id), "role_name": RoleName.ORG_ADMIN.value},
        )
        assert bad_scope.status_code == 400
        assert bad_scope.json()["error"]["code"] == "INVALID_ROLE_SCOPE"

        # Current project owner cannot be demoted or removed while owner
        demote_owner = client.patch(
            f"/api/v1/projects/{proj_id}/members/{owner.user_id}/role",
            headers=owner.headers,
            json={"role_name": "project_member"},
        )
        assert demote_owner.status_code == 409
        assert demote_owner.json()["error"]["code"] == "PROJECT_OWNER_ROLE_LOCKED"

        remove_owner = client.delete(
            f"/api/v1/projects/{proj_id}/members/{owner.user_id}",
            headers=owner.headers,
        )
        assert remove_owner.status_code == 409
        assert remove_owner.json()["error"]["code"] == "PROJECT_OWNER_REMOVAL_FORBIDDEN"

        # Transfer ownership to dev -> dev becomes project_manager automatically
        transfer = client.patch(
            f"/api/v1/projects/{proj_id}",
            headers=owner.headers,
            json={"owner_id": str(dev.user_id)},
        )
        assert transfer.status_code == 200
        assert transfer.json()["owner_id"] == str(dev.user_id)

        dev_after = client.get(f"/api/v1/projects/{proj_id}", headers=dev.headers)
        assert dev_after.status_code == 200
        assert dev_after.json()["my_project_role"] == "project_manager"
        assert "project.manage" in dev_after.json()["effective_permissions"]

        # Now original owner can be demoted or removed by new owner (dev)
        demote_prev_owner = client.patch(
            f"/api/v1/projects/{proj_id}/members/{owner.user_id}/role",
            headers=dev.headers,
            json={"role_name": "reviewer"},
        )
        assert demote_prev_owner.status_code == 200
        assert demote_prev_owner.json()["role_name"] == "reviewer"

        # New owner removes reviewer -> reviewer loses access to private project immediately
        rm_rev = client.delete(
            f"/api/v1/projects/{proj_id}/members/{reviewer.user_id}",
            headers=dev.headers,
        )
        assert rm_rev.status_code == 200
        assert rm_rev.json()["revoked_project_memberships"] == 1
        rev_after = client.get(f"/api/v1/projects/{proj_id}", headers=reviewer.headers)
        assert rev_after.status_code == 404

        # Archive project -> immutable afterwards
        archived = client.post(f"/api/v1/projects/{proj_id}/archive", headers=dev.headers)
        assert archived.status_code == 200
        assert archived.json()["status"] == "archived"
        assert archived.json()["archived_at"] is not None

        assert (
            client.patch(
                f"/api/v1/projects/{proj_id}",
                headers=dev.headers,
                json={"description": "Blocked"},
            ).status_code
            == 409
        )
        dup_arch = client.post(f"/api/v1/projects/{proj_id}/archive", headers=dev.headers)
        assert dup_arch.status_code == 409

        # Verify project audit events filter cleanly by project_id
        audit = client.get(
            f"/api/v1/organisations/{org_id}/audit-events?project_id={proj_id}",
            headers=owner.headers,
        )
        assert audit.status_code == 200
        types = {row["event_type"] for row in audit.json()["items"]}
        assert "project.created" in types
        assert "project.updated" in types
        assert "project.archived" in types
        assert "project.member.added" in types
        assert "project.member.removed" in types
