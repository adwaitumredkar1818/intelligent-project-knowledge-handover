"""Strict multi-tenant isolation, parent-org enforcement, and permission-guard tests."""

from __future__ import annotations

import uuid
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.api.deps import require_organisation_membership, require_project_membership
from app.models.enums import OrganisationMembershipStatus
from app.models.organisation import OrganisationMembership
from app.services.rbac import OrganisationContext, ProjectContext
from tests.conftest import (
    invite_and_accept_member,
    isolated_auth_app,
    register_and_login_user,
)


def test_cross_organisation_and_cross_project_isolation_returns_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        owner_a = register_and_login_user(
            client,
            email="owner-a@tenant-a.example.com",
            full_name="Owner A",
        )
        owner_b = register_and_login_user(
            client,
            email="owner-b@tenant-b.example.com",
            full_name="Owner B",
        )

        org_a_id = client.post(
            "/api/v1/organisations",
            headers=owner_a.headers,
            json={"name": "Tenant A"},
        ).json()["id"]
        proj_a_id = client.post(
            f"/api/v1/organisations/{org_a_id}/projects",
            headers=owner_a.headers,
            json={"name": "Secret Alpha", "visibility": "organisation"},
        ).json()["id"]
        inv_a = client.post(
            f"/api/v1/organisations/{org_a_id}/invitations",
            headers=owner_a.headers,
            json={"email": "outsider@tenant-a.example.com", "role_name": "org_member"},
        ).json()["invitation"]["id"]

        org_b_id = client.post(
            "/api/v1/organisations",
            headers=owner_b.headers,
            json={"name": "Tenant B"},
        ).json()["id"]
        assert org_a_id != org_b_id

        # Owner B gets 404 (not 403/200) for every Tenant A organisation & project route
        for method, path, body in (
            ("GET", f"/api/v1/organisations/{org_a_id}", None),
            ("PATCH", f"/api/v1/organisations/{org_a_id}", {"name": "Tamper"}),
            ("POST", f"/api/v1/organisations/{org_a_id}/archive", None),
            ("GET", f"/api/v1/organisations/{org_a_id}/members", None),
            (
                "PATCH",
                f"/api/v1/organisations/{org_a_id}/members/{owner_a.user_id}/role",
                {"role_name": "org_member"},
            ),
            ("DELETE", f"/api/v1/organisations/{org_a_id}/members/{owner_a.user_id}", None),
            (
                "POST",
                f"/api/v1/organisations/{org_a_id}/invitations",
                {"email": "x@example.com", "role_name": "org_member"},
            ),
            ("GET", f"/api/v1/organisations/{org_a_id}/invitations", None),
            ("DELETE", f"/api/v1/organisations/{org_a_id}/invitations/{inv_a}", None),
            ("GET", f"/api/v1/organisations/{org_a_id}/audit-events", None),
            ("GET", f"/api/v1/organisations/{org_a_id}/projects", None),
            (
                "POST",
                f"/api/v1/organisations/{org_a_id}/projects",
                {"name": "Injected Project"},
            ),
        ):
            resp = client.request(method, path, headers=owner_b.headers, json=body)
            assert resp.status_code == 404, (
                f"Expected 404 on {method} {path}, got {resp.status_code}"
            )
            assert resp.json()["error"]["code"] == "ORGANISATION_NOT_FOUND"

        for method, path, body in (
            ("GET", f"/api/v1/projects/{proj_a_id}", None),
            ("PATCH", f"/api/v1/projects/{proj_a_id}", {"name": "Tamper"}),
            ("POST", f"/api/v1/projects/{proj_a_id}/archive", None),
            ("GET", f"/api/v1/projects/{proj_a_id}/members", None),
            (
                "POST",
                f"/api/v1/projects/{proj_a_id}/members",
                {"user_id": str(owner_b.user_id), "role_name": "project_member"},
            ),
            (
                "PATCH",
                f"/api/v1/projects/{proj_a_id}/members/{owner_a.user_id}/role",
                {"role_name": "project_member"},
            ),
            ("DELETE", f"/api/v1/projects/{proj_a_id}/members/{owner_a.user_id}", None),
        ):
            resp = client.request(method, path, headers=owner_b.headers, json=body)
            assert resp.status_code == 404, (
                f"Expected 404 on {method} {path}, got {resp.status_code}"
            )
            assert resp.json()["error"]["code"] == "PROJECT_NOT_FOUND"

        # Cannot add external Tenant B user to Tenant A project or assign them as project owner
        add_external = client.post(
            f"/api/v1/projects/{proj_a_id}/members",
            headers=owner_a.headers,
            json={"user_id": str(owner_b.user_id), "role_name": "project_member"},
        )
        assert add_external.status_code == 400
        assert add_external.json()["error"]["code"] == "USER_NOT_ORG_MEMBER"

        owner_external = client.patch(
            f"/api/v1/projects/{proj_a_id}",
            headers=owner_a.headers,
            json={"owner_id": str(owner_b.user_id)},
        )
        assert owner_external.status_code == 400
        assert owner_external.json()["error"]["code"] == "USER_NOT_ORG_MEMBER"


def test_dynamic_parent_org_membership_blocks_stale_project_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even if a stale active ProjectMembership exists in DB, revoking parent org denies access."""
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        owner = register_and_login_user(
            client,
            email="owner@stale.example.com",
            full_name="Stale Guard Owner",
        )
        worker = register_and_login_user(
            client,
            email="worker@stale.example.com",
            full_name="Stale Guard Worker",
        )

        org_id = client.post(
            "/api/v1/organisations",
            headers=owner.headers,
            json={"name": "Parent Guard Org"},
        ).json()["id"]
        invite_and_accept_member(
            client,
            organisation_id=org_id,
            inviter_headers=owner.headers,
            invitee=worker,
            role_name="org_member",
        )
        proj_id = client.post(
            f"/api/v1/organisations/{org_id}/projects",
            headers=owner.headers,
            json={"name": "Guarded Workspace", "visibility": "organisation"},
        ).json()["id"]
        assert (
            client.post(
                f"/api/v1/projects/{proj_id}/members",
                headers=owner.headers,
                json={"user_id": str(worker.user_id), "role_name": "project_manager"},
            ).status_code
            == 201
        )
        assert client.get(f"/api/v1/projects/{proj_id}", headers=worker.headers).status_code == 200

        # Simulate out-of-band org suspension WITHOUT touching project_memberships
        with ctx.session_factory() as session:
            org_mem = (
                session.query(OrganisationMembership)
                .filter(
                    OrganisationMembership.organisation_id == uuid.UUID(org_id),
                    OrganisationMembership.user_id == worker.user_id,
                )
                .one()
            )
            org_mem.status = OrganisationMembershipStatus.SUSPENDED.value
            session.commit()

        # Worker is immediately denied 404 despite still having active ProjectMembership!
        assert client.get(f"/api/v1/projects/{proj_id}", headers=worker.headers).status_code == 404
        assert (
            client.patch(
                f"/api/v1/projects/{proj_id}",
                headers=worker.headers,
                json={"name": "Bypass"},
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/api/v1/projects/{proj_id}/members",
                headers=worker.headers,
            ).status_code
            == 404
        )


def test_membership_dependencies_enforce_explicit_organisation_and_project_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify reusable `require_organisation_membership` and `require_project_membership` guards."""
    with isolated_auth_app(monkeypatch) as ctx:

        @ctx.app.get("/api/v1/_test/orgs/{organisation_id}/member-check")
        def _org_member_probe(
            org_ctx: Annotated[OrganisationContext, Depends(require_organisation_membership)],
        ) -> dict[str, str]:
            return {"organisation_id": str(org_ctx.organisation.id), "role": org_ctx.role.name}

        @ctx.app.get("/api/v1/_test/projects/{project_id}/member-check")
        def _project_member_probe(
            proj_ctx: Annotated[ProjectContext, Depends(require_project_membership)],
        ) -> dict[str, str]:
            assert proj_ctx.project_role is not None
            return {"project_id": str(proj_ctx.project.id), "role": proj_ctx.project_role.name}

        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client,
                email="owner@deps.example.com",
                full_name="Deps Owner",
            )
            non_proj_admin = register_and_login_user(
                client,
                email="admin@deps.example.com",
                full_name="Org Admin NonProjectMember",
            )
            outsider = register_and_login_user(
                client,
                email="outsider@deps.example.com",
                full_name="Outsider User",
            )

            org_id = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "Deps Verification Org"},
            ).json()["id"]
            invite_and_accept_member(
                client,
                organisation_id=org_id,
                inviter_headers=owner.headers,
                invitee=non_proj_admin,
                role_name="org_admin",
            )
            proj_id = client.post(
                f"/api/v1/organisations/{org_id}/projects",
                headers=owner.headers,
                json={"name": "Org Visible Project", "visibility": "organisation"},
            ).json()["id"]

            # Outsider -> 404 on org membership guard & 404 on project membership guard
            assert (
                client.get(
                    f"/api/v1/_test/orgs/{org_id}/member-check",
                    headers=outsider.headers,
                ).status_code
                == 404
            )
            assert (
                client.get(
                    f"/api/v1/_test/projects/{proj_id}/member-check",
                    headers=outsider.headers,
                ).status_code
                == 404
            )

            # org_admin without explicit project membership passes org guard,
            # but is blocked (403) on explicit project membership guard
            assert (
                client.get(
                    f"/api/v1/_test/orgs/{org_id}/member-check",
                    headers=non_proj_admin.headers,
                ).status_code
                == 200
            )
            assert (
                client.get(
                    f"/api/v1/_test/projects/{proj_id}/member-check",
                    headers=non_proj_admin.headers,
                ).status_code
                == 403
            )

            # Owner has explicit project_manager membership -> 200
            ok_proj = client.get(
                f"/api/v1/_test/projects/{proj_id}/member-check",
                headers=owner.headers,
            )
            assert ok_proj.status_code == 200
            assert ok_proj.json()["role"] == "project_manager"
