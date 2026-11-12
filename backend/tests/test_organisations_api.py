"""API and governance tests for organisations, memberships, and org audit trails."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.enums import ProjectMembershipStatus, RoleName
from app.models.project import ProjectMembership
from app.models.rbac import Role, UserRole
from tests.conftest import (
    invite_and_accept_member,
    isolated_auth_app,
    register_and_login_user,
)


def test_unauthenticated_organisation_endpoints_return_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    random_id = str(uuid.uuid4())
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        for method, path in (
            ("POST", "/api/v1/organisations"),
            ("GET", "/api/v1/organisations"),
            ("GET", f"/api/v1/organisations/{random_id}"),
            ("PATCH", f"/api/v1/organisations/{random_id}"),
            ("POST", f"/api/v1/organisations/{random_id}/archive"),
            ("GET", f"/api/v1/organisations/{random_id}/members"),
            ("PATCH", f"/api/v1/organisations/{random_id}/members/{random_id}/role"),
            ("DELETE", f"/api/v1/organisations/{random_id}/members/{random_id}"),
            ("GET", f"/api/v1/organisations/{random_id}/audit-events"),
        ):
            resp = client.request(method, path)
            assert resp.status_code == 401
            assert resp.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_create_list_update_archive_organisation_and_slug_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        owner = register_and_login_user(
            client,
            email="owner@acme.example.com",
            full_name="Owner One",
        )
        member = register_and_login_user(
            client,
            email="member@acme.example.com",
            full_name="Member Two",
        )

        # Create with derived slug & normalised name
        created = client.post(
            "/api/v1/organisations",
            headers=owner.headers,
            json={
                "name": "  Acme   Engineering  Org ",
                "description": "  Platform handover group  ",
            },
        )
        assert created.status_code == 201
        org_data = created.json()
        org_id = org_data["id"]
        assert org_data["name"] == "Acme Engineering Org"
        assert org_data["slug"] == "acme-engineering-org"
        assert org_data["description"] == "Platform handover group"
        assert org_data["status"] == "active"
        assert org_data["my_role"] == "org_owner"
        assert org_data["archived_at"] is None
        assert "organisation.manage" in org_data["my_permissions"]
        assert "organisation.audit.read" in org_data["my_permissions"]

        # Duplicate slug (explicit, normalised uppercase) fails 409
        dup_slug = client.post(
            "/api/v1/organisations",
            headers=owner.headers,
            json={"name": "Another Name", "slug": "  ACME-ENGINEERING-ORG "},
        )
        assert dup_slug.status_code == 409
        assert dup_slug.json()["error"]["code"] == "ORGANISATION_SLUG_ALREADY_EXISTS"

        # Invalid slug rejected at schema validation (422)
        bad_slug = client.post(
            "/api/v1/organisations",
            headers=owner.headers,
            json={"name": "Bad Slug Org", "slug": "-invalid--slug-"},
        )
        assert bad_slug.status_code == 422

        # Add member and verify member list & visibility boundaries
        invite_and_accept_member(
            client,
            organisation_id=org_id,
            inviter_headers=owner.headers,
            invitee=member,
            role_name="org_member",
        )

        owner_list = client.get("/api/v1/organisations?search=acme", headers=owner.headers)
        assert owner_list.status_code == 200
        assert owner_list.json()["total"] == 1
        assert owner_list.json()["items"][0]["my_role"] == "org_owner"

        member_detail = client.get(f"/api/v1/organisations/{org_id}", headers=member.headers)
        assert member_detail.status_code == 200
        assert member_detail.json()["my_role"] == "org_member"
        assert set(member_detail.json()["my_permissions"]) == {
            "organisation.read",
            "organisation.members.read",
        }

        # org_member cannot update or archive
        member_patch = client.patch(
            f"/api/v1/organisations/{org_id}",
            headers=member.headers,
            json={"name": "Hijacked Name"},
        )
        assert member_patch.status_code == 403
        assert member_patch.json()["error"]["code"] == "FORBIDDEN"

        member_archive = client.post(
            f"/api/v1/organisations/{org_id}/archive",
            headers=member.headers,
        )
        assert member_archive.status_code == 403

        # org_owner updates metadata
        patched = client.patch(
            f"/api/v1/organisations/{org_id}",
            headers=owner.headers,
            json={"name": "Acme Updated Org", "slug": "acme-updated"},
        )
        assert patched.status_code == 200
        assert patched.json()["name"] == "Acme Updated Org"
        assert patched.json()["slug"] == "acme-updated"

        # org_owner archives org; duplicate archive & subsequent mutations conflict cleanly
        archived = client.post(f"/api/v1/organisations/{org_id}/archive", headers=owner.headers)
        assert archived.status_code == 200
        assert archived.json()["status"] == "archived"
        assert archived.json()["archived_at"] is not None

        dup_archive = client.post(f"/api/v1/organisations/{org_id}/archive", headers=owner.headers)
        assert dup_archive.status_code == 409
        assert dup_archive.json()["error"]["code"] == "ORGANISATION_ALREADY_ARCHIVED"

        post_archive_patch = client.patch(
            f"/api/v1/organisations/{org_id}",
            headers=owner.headers,
            json={"description": "Should fail"},
        )
        assert post_archive_patch.status_code == 409
        assert post_archive_patch.json()["error"]["code"] == "ORGANISATION_NOT_ACTIVE"

        # Status filter works on listing
        active_list = client.get("/api/v1/organisations?status=active", headers=owner.headers)
        assert active_list.status_code == 200
        assert active_list.json()["total"] == 0
        archived_list = client.get("/api/v1/organisations?status=archived", headers=owner.headers)
        assert archived_list.status_code == 200
        assert archived_list.json()["total"] == 1


def test_user_without_platform_create_permission_is_forbidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        user = register_and_login_user(
            client,
            email="restricted@example.com",
            full_name="Restricted User",
        )
        # Strip platform roles from this user via DB to prove DB-driven enforcement
        with ctx.session_factory() as session:
            session.query(UserRole).filter(UserRole.user_id == user.user_id).delete()
            session.commit()

        resp = client.post(
            "/api/v1/organisations",
            headers=user.headers,
            json={"name": "Blocked Org"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_member_role_governance_escalation_last_owner_and_cascading_removal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        owner = register_and_login_user(
            client,
            email="owner@gov.example.com",
            full_name="Primary Owner",
        )
        admin = register_and_login_user(
            client,
            email="admin@gov.example.com",
            full_name="Tenant Admin",
        )
        worker = register_and_login_user(
            client,
            email="worker@gov.example.com",
            full_name="Project Worker",
        )

        org_id = client.post(
            "/api/v1/organisations",
            headers=owner.headers,
            json={"name": "Governance Corp"},
        ).json()["id"]

        invite_and_accept_member(
            client,
            organisation_id=org_id,
            inviter_headers=owner.headers,
            invitee=admin,
            role_name="org_admin",
        )
        invite_and_accept_member(
            client,
            organisation_id=org_id,
            inviter_headers=owner.headers,
            invitee=worker,
            role_name="org_member",
        )

        # Last org_owner cannot demote or remove themselves
        last_demote = client.patch(
            f"/api/v1/organisations/{org_id}/members/{owner.user_id}/role",
            headers=owner.headers,
            json={"role_name": "org_admin"},
        )
        assert last_demote.status_code == 409
        assert last_demote.json()["error"]["code"] == "LAST_ORG_OWNER_FORBIDDEN"

        last_remove = client.delete(
            f"/api/v1/organisations/{org_id}/members/{owner.user_id}",
            headers=owner.headers,
        )
        assert last_remove.status_code == 409
        assert last_remove.json()["error"]["code"] == "LAST_ORG_OWNER_FORBIDDEN"

        # org_admin lacks organisation.manage
        admin_patch_org = client.patch(
            f"/api/v1/organisations/{org_id}",
            headers=admin.headers,
            json={"description": "Not permitted"},
        )
        assert admin_patch_org.status_code == 403

        # org_admin cannot promote worker to org_owner, nor demote/remove org_owner
        esc_promote = client.patch(
            f"/api/v1/organisations/{org_id}/members/{worker.user_id}/role",
            headers=admin.headers,
            json={"role_name": "org_owner"},
        )
        assert esc_promote.status_code == 403
        assert esc_promote.json()["error"]["code"] == "INSUFFICIENT_ROLE_AUTHORITY"

        esc_demote_owner = client.patch(
            f"/api/v1/organisations/{org_id}/members/{owner.user_id}/role",
            headers=admin.headers,
            json={"role_name": "org_member"},
        )
        assert esc_demote_owner.status_code == 403
        assert esc_demote_owner.json()["error"]["code"] == "INSUFFICIENT_ROLE_AUTHORITY"

        esc_remove_owner = client.delete(
            f"/api/v1/organisations/{org_id}/members/{owner.user_id}",
            headers=admin.headers,
        )
        assert esc_remove_owner.status_code == 403

        # Wrong role scope (platform_admin or project_manager) fails 400 INVALID_ROLE_SCOPE
        wrong_scope = client.patch(
            f"/api/v1/organisations/{org_id}/members/{worker.user_id}/role",
            headers=owner.headers,
            json={"role_name": RoleName.PROJECT_MANAGER.value},
        )
        assert wrong_scope.status_code == 400
        assert wrong_scope.json()["error"]["code"] == "INVALID_ROLE_SCOPE"

        # Verify role promotion to second org_owner allows primary owner demotion afterwards
        make_second_owner = client.patch(
            f"/api/v1/organisations/{org_id}/members/{admin.user_id}/role",
            headers=owner.headers,
            json={"role_name": "org_owner"},
        )
        assert make_second_owner.status_code == 200
        assert make_second_owner.json()["role_name"] == "org_owner"

        demote_first_owner = client.patch(
            f"/api/v1/organisations/{org_id}/members/{owner.user_id}/role",
            headers=admin.headers,
            json={"role_name": "org_admin"},
        )
        assert demote_first_owner.status_code == 200
        # Restore primary owner for cleanup test
        assert (
            client.patch(
                f"/api/v1/organisations/{org_id}/members/{owner.user_id}/role",
                headers=admin.headers,
                json={"role_name": "org_owner"},
            ).status_code
            == 200
        )

        # Create a private project and assign worker, then remove worker from org -> cascade!
        proj_id = client.post(
            f"/api/v1/organisations/{org_id}/projects",
            headers=owner.headers,
            json={"name": "Cascade Project", "visibility": "private"},
        ).json()["id"]
        assert (
            client.post(
                f"/api/v1/projects/{proj_id}/members",
                headers=owner.headers,
                json={"user_id": str(worker.user_id), "role_name": "project_member"},
            ).status_code
            == 201
        )
        assert client.get(f"/api/v1/projects/{proj_id}", headers=worker.headers).status_code == 200

        removed = client.delete(
            f"/api/v1/organisations/{org_id}/members/{worker.user_id}",
            headers=owner.headers,
        )
        assert removed.status_code == 200
        assert removed.json()["revoked_project_memberships"] == 1

        # Verify DB state & immediate loss of access to both org and project
        with ctx.session_factory() as session:
            pm = session.scalar(
                select(ProjectMembership).where(
                    ProjectMembership.project_id == uuid.UUID(proj_id),
                    ProjectMembership.user_id == worker.user_id,
                )
            )
            assert pm is not None
            assert pm.status == ProjectMembershipStatus.REMOVED.value

        org_after = client.get(f"/api/v1/organisations/{org_id}", headers=worker.headers)
        assert org_after.status_code == 404
        assert client.get(f"/api/v1/projects/{proj_id}", headers=worker.headers).status_code == 404

        # Removed members list can be inspected by admin/owner
        removed_list = client.get(
            f"/api/v1/organisations/{org_id}/members?status=removed",
            headers=owner.headers,
        )
        assert removed_list.status_code == 200
        assert removed_list.json()["total"] == 1
        assert removed_list.json()["items"][0]["user_id"] == str(worker.user_id)

        # Audit events: admin/owner can query; org_member cannot
        member2 = register_and_login_user(
            client,
            email="viewer@gov.example.com",
            full_name="Member Viewer",
        )
        invite_and_accept_member(
            client,
            organisation_id=org_id,
            inviter_headers=owner.headers,
            invitee=member2,
            role_name="org_member",
        )
        assert (
            client.get(
                f"/api/v1/organisations/{org_id}/audit-events",
                headers=member2.headers,
            ).status_code
            == 403
        )
        audit_resp = client.get(
            f"/api/v1/organisations/{org_id}/audit-events",
            headers=owner.headers,
        )
        assert audit_resp.status_code == 200
        event_types = {item["event_type"] for item in audit_resp.json()["items"]}
        assert "organisation.created" in event_types
        assert "organisation.member.role_changed" in event_types
        assert "organisation.member.removed" in event_types

        # Unknown role returns 404 ROLE_NOT_FOUND (confirm Role exists in DB check)
        with ctx.session_factory() as session:
            assert session.scalar(select(Role).where(Role.name == "org_owner")) is not None
        unknown_role = client.patch(
            f"/api/v1/organisations/{org_id}/members/{member2.user_id}/role",
            headers=owner.headers,
            json={"role_name": "nonexistent_role"},
        )
        assert unknown_role.status_code == 404
        assert unknown_role.json()["error"]["code"] == "ROLE_NOT_FOUND"
