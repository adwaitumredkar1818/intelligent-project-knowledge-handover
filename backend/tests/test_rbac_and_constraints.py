"""Tests for RBAC permission checks, fail-closed guards, user isolation, and DB constraints."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Annotated

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import require_permission
from app.core.security import hash_password, utc_now
from app.models.auth import RefreshSession
from app.models.enums import RoleName
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.repositories.rbac import RbacRepository
from app.services.rbac import AuthenticatedPrincipal
from tests.conftest import isolated_auth_app

_PASSWORD = "Handover!Rbac2026#Secure"


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


def test_rbac_fail_closed_and_user_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    with isolated_auth_app(monkeypatch) as ctx:
        test_router = APIRouter()

        @test_router.get("/__test/unknown-perm")
        def unknown_perm_route(
            _: Annotated[
                AuthenticatedPrincipal,
                Depends(require_permission("unknown.made_up.perm")),
            ],
        ) -> dict[str, bool]:
            return {"ok": True}

        @test_router.get("/__test/project-perm")
        def project_perm_route(
            _: Annotated[
                AuthenticatedPrincipal,
                Depends(require_permission("project.read")),
            ],
        ) -> dict[str, bool]:
            return {"ok": True}

        ctx.app.include_router(test_router)

        with TestClient(ctx.app) as client:
            alice_id, alice_token = _register_and_login(
                client, full_name="Alice User", email="alice@example.com"
            )
            alice_headers = {"Authorization": f"Bearer {alice_token}"}
            alice_sessions = client.get(
                "/api/v1/auth/sessions", headers=alice_headers
            ).json()["items"]
            assert len(alice_sessions) == 1
            alice_session_id = alice_sessions[0]["id"]

            bob_id, bob_token = _register_and_login(
                client, full_name="Bob User", email="bob@example.com"
            )
            bob_headers = {"Authorization": f"Bearer {bob_token}"}

            # User isolation: Bob can read his own profile but NOT Alice's profile
            assert client.get(f"/api/v1/users/{bob_id}", headers=bob_headers).status_code == 200
            cross_read = client.get(f"/api/v1/users/{alice_id}", headers=bob_headers)
            assert cross_read.status_code == 403
            assert cross_read.json()["error"]["code"] == "FORBIDDEN"

            # User isolation: Bob cannot revoke Alice's session
            cross_revoke = client.delete(
                f"/api/v1/auth/sessions/{alice_session_id}",
                headers=bob_headers,
            )
            assert cross_revoke.status_code == 404

            # Alice's session remains active
            assert client.get("/api/v1/auth/me", headers=alice_headers).status_code == 200

            # Standard user lacks privileged admin, project, and unknown permissions (fail closed)
            for path in (
                "/api/v1/users",
                "/api/v1/roles",
                "/__test/unknown-perm",
                "/__test/project-perm",
            ):
                denied = client.get(path, headers=bob_headers)
                assert denied.status_code == 403
                assert denied.json()["error"]["code"] == "FORBIDDEN"


def test_platform_admin_permissions_scope_separation_and_disable_revocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        alice_id, alice_token = _register_and_login(
            client, full_name="Alice Standard", email="alice.std@example.com"
        )
        admin_id, _ = _register_and_login(
            client, full_name="Platform Admin", email="admin@example.com"
        )

        # Grant platform_admin role to admin user in DB and re-login cleanly
        with ctx.session_factory() as session:
            rbac_repo = RbacRepository(session)
            admin_role = rbac_repo.get_role_by_name(RoleName.PLATFORM_ADMIN.value)
            assert admin_role is not None
            rbac_repo.assign_role(user_id=uuid.UUID(admin_id), role_id=admin_role.id)
            session.commit()

        admin_login = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": _PASSWORD},
        )
        assert admin_login.status_code == 200
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

        # Admin can list users and roles
        users_resp = client.get("/api/v1/users", headers=admin_headers)
        assert users_resp.status_code == 200
        assert users_resp.json()["total"] == 2

        roles_resp = client.get("/api/v1/roles", headers=admin_headers)
        assert roles_resp.status_code == 200
        role_names = {r["name"] for r in roles_resp.json()["items"]}
        assert {
            "standard_user",
            "platform_admin",
            "org_owner",
            "org_admin",
            "project_manager",
            "project_member",
            "reviewer",
        }.issubset(role_names)

        # Scope separation: org/project roles cannot be assigned via platform user_roles
        for non_platform_role in ("org_owner", "project_member", "reviewer"):
            bad_assign = client.post(
                f"/api/v1/users/{alice_id}/roles",
                headers=admin_headers,
                json={"role_name": non_platform_role},
            )
            assert bad_assign.status_code == 400
            assert bad_assign.json()["error"]["code"] == "INVALID_ROLE_SCOPE"

        # Platform-scoped role assignment succeeds
        ok_assign = client.post(
            f"/api/v1/users/{alice_id}/roles",
            headers=admin_headers,
            json={"role_name": "platform_admin"},
        )
        assert ok_assign.status_code == 201
        assert ok_assign.json()["scope_type"] == "platform"

        # Disabling Alice revokes her active session family immediately
        disable_resp = client.patch(
            f"/api/v1/users/{alice_id}/status",
            headers=admin_headers,
            json={"status": "disabled"},
        )
        assert disable_resp.status_code == 200
        assert disable_resp.json()["status"] == "disabled"

        alice_me_after = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        assert alice_me_after.status_code == 401


def test_database_constraints_and_cascades(monkeypatch: pytest.MonkeyPatch) -> None:
    with isolated_auth_app(monkeypatch) as ctx:
        pw_hash = hash_password(_PASSWORD)

        # 1. Lowercase email check constraint
        with ctx.session_factory() as session:
            session.add(
                User(
                    full_name="Bad Case",
                    email="MixedCase@Example.com",
                    password_hash=pw_hash,
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

        # 2. Status CHECK constraint
        with ctx.session_factory() as session:
            session.add(
                User(
                    full_name="Bad Status",
                    email="badstatus@example.com",
                    password_hash=pw_hash,
                    status="super_admin",
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

        # 3. Valid user + unique user_roles + token_hash length check + cascade delete
        with ctx.session_factory() as session:
            user = User(
                full_name="Constraint User",
                email="constraint@example.com",
                password_hash=pw_hash,
            )
            session.add(user)
            session.flush()

            role = session.scalar(select(Role).where(Role.name == RoleName.STANDARD_USER.value))
            assert role is not None
            session.add(UserRole(user_id=user.id, role_id=role.id))
            session.commit()

            # Duplicate (user_id, role_id) violates uq_user_roles_user_role
            session.add(UserRole(user_id=user.id, role_id=role.id))
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            # Invalid non-SHA256 token_hash length violates check constraint
            session.add(
                RefreshSession(
                    user_id=user.id,
                    token_family_id=uuid.uuid4(),
                    token_hash="too-short",
                    expires_at=utc_now() + timedelta(days=7),
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            # Deleting user cascades to refresh_sessions and user_roles
            session.add(
                RefreshSession(
                    user_id=user.id,
                    token_family_id=uuid.uuid4(),
                    token_hash="a" * 64,
                    expires_at=utc_now() + timedelta(days=7),
                )
            )
            session.commit()
            user_id = user.id

        with ctx.session_factory() as session:
            target = session.get(User, user_id)
            assert target is not None
            session.delete(target)
            session.commit()

            assert (
                session.scalar(
                    select(RefreshSession).where(RefreshSession.user_id == user_id)
                )
                is None
            )
            assert (
                session.scalar(select(UserRole).where(UserRole.user_id == user_id))
                is None
            )
