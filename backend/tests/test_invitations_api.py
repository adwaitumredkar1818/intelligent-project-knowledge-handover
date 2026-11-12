"""API and security tests for SHA-256 hashed single-use organisation invitations."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_opaque_token, utc_now
from app.models.audit import AuditLog
from app.models.enums import InvitationStatus, RoleName
from app.models.organisation import OrganisationInvitation
from tests.conftest import (
    DEFAULT_TEST_PASSWORD,
    invite_and_accept_member,
    isolated_auth_app,
    register_and_login_user,
)


def test_invitation_hash_storage_delivery_status_and_production_redaction(
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
        owner = register_and_login_user(
            client,
            email="prod-owner@example.com",
            full_name="Prod Owner",
        )
        org_id = client.post(
            "/api/v1/organisations",
            headers=owner.headers,
            json={"name": "Prod Tenant"},
        ).json()["id"]

        with caplog.at_level(logging.INFO):
            resp = client.post(
                f"/api/v1/organisations/{org_id}/invitations",
                headers=owner.headers,
                json={"email": "  New.Member@Example.COM ", "role_name": "org_member"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["invitation_delivery"] == "not_configured"
            assert data["development_invitation_token"] is None
            assert data["invitation"]["email"] == "new.member@example.com"
            assert data["invitation"]["status"] == "pending"
            assert data["invitation"]["role_name"] == "org_member"
            assert "token_hash" not in resp.text

            with ctx.session_factory() as session:
                inv = session.scalar(select(OrganisationInvitation))
                assert inv is not None
                assert inv.email == "new.member@example.com"
                assert len(inv.token_hash) == 64
                assert inv.token_hash not in resp.text
                assert inv.token_hash not in caplog.text


def test_invitation_accept_email_match_replay_expiry_revocation_and_reinvite(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        owner = register_and_login_user(
            client,
            email="owner@inv.example.com",
            full_name="Invite Owner",
        )
        target = register_and_login_user(
            client,
            email="target@inv.example.com",
            full_name="Target User",
        )
        wrong_user = register_and_login_user(
            client,
            email="other@inv.example.com",
            full_name="Wrong User",
        )

        org_id = client.post(
            "/api/v1/organisations",
            headers=owner.headers,
            json={"name": "Invite Corp"},
        ).json()["id"]

        with caplog.at_level(logging.INFO):
            invite_resp = client.post(
                f"/api/v1/organisations/{org_id}/invitations",
                headers=owner.headers,
                json={"email": "TARGET@INV.EXAMPLE.COM", "role_name": "org_admin"},
            )
            assert invite_resp.status_code == 201
            payload = invite_resp.json()
            assert payload["invitation_delivery"] == "not_configured"
            raw_token = payload["development_invitation_token"]
            assert isinstance(raw_token, str) and len(raw_token) > 20
            invitation_id = payload["invitation"]["id"]

            # Raw token never appears in DB, logs, or audit metadata
            with ctx.session_factory() as session:
                stored = session.get(OrganisationInvitation, uuid.UUID(invitation_id))
                assert stored is not None
                assert stored.token_hash == hash_opaque_token(raw_token)
                assert stored.token_hash != raw_token
                audits = session.scalars(select(AuditLog)).all()
                assert all(raw_token not in str(a.event_metadata or {}) for a in audits)
            assert raw_token not in caplog.text

            # Duplicate active pending invitation rejected cleanly
            dup_invite = client.post(
                f"/api/v1/organisations/{org_id}/invitations",
                headers=owner.headers,
                json={"email": "target@inv.example.com", "role_name": "org_member"},
            )
            assert dup_invite.status_code == 409
            assert dup_invite.json()["error"]["code"] == "INVITATION_ALREADY_EXISTS"

            # Wrong user cannot accept another user's invitation AND does not consume it
            wrong_accept = client.post(
                f"/api/v1/invitations/{raw_token}/accept",
                headers=wrong_user.headers,
            )
            assert wrong_accept.status_code == 403
            assert wrong_accept.json()["error"]["code"] == "INVITATION_EMAIL_MISMATCH"

            # Unknown token returns 404
            unknown_accept = client.post(
                "/api/v1/invitations/completely-unknown-token-value/accept",
                headers=target.headers,
            )
            assert unknown_accept.status_code == 404
            assert unknown_accept.json()["error"]["code"] == "INVITATION_NOT_FOUND"

            # Matching authenticated target accepts successfully
            ok_accept = client.post(
                f"/api/v1/invitations/{raw_token}/accept",
                headers=target.headers,
            )
            assert ok_accept.status_code == 200
            accepted = ok_accept.json()
            assert accepted["organisation_id"] == org_id
            assert accepted["role_name"] == "org_admin"
            assert accepted["membership_status"] == "active"

            # Single-use: second attempt fails 409 INVITATION_ALREADY_ACCEPTED
            replay = client.post(
                f"/api/v1/invitations/{raw_token}/accept",
                headers=target.headers,
            )
            assert replay.status_code == 409
            assert replay.json()["error"]["code"] == "INVITATION_ALREADY_ACCEPTED"

            # Already-active member cannot be invited again
            already_member = client.post(
                f"/api/v1/organisations/{org_id}/invitations",
                headers=owner.headers,
                json={"email": target.email, "role_name": "org_member"},
            )
            assert already_member.status_code == 409
            assert already_member.json()["error"]["code"] == "MEMBERSHIP_ALREADY_EXISTS"

            assert raw_token not in caplog.text

        # Test revocation and re-invitation for wrong_user
        rev_invite = client.post(
            f"/api/v1/organisations/{org_id}/invitations",
            headers=owner.headers,
            json={"email": wrong_user.email, "role_name": "org_member"},
        )
        assert rev_invite.status_code == 201
        rev_token = rev_invite.json()["development_invitation_token"]
        rev_id = rev_invite.json()["invitation"]["id"]

        listed = client.get(
            f"/api/v1/organisations/{org_id}/invitations?status=pending",
            headers=owner.headers,
        )
        assert listed.status_code == 200
        assert listed.json()["total"] == 1
        assert listed.json()["items"][0]["id"] == rev_id

        revoked = client.delete(
            f"/api/v1/organisations/{org_id}/invitations/{rev_id}",
            headers=owner.headers,
        )
        assert revoked.status_code == 200
        assert revoked.json()["status"] == "revoked"

        revoked_accept = client.post(
            f"/api/v1/invitations/{rev_token}/accept",
            headers=wrong_user.headers,
        )
        assert revoked_accept.status_code == 409
        assert revoked_accept.json()["error"]["code"] == "INVITATION_REVOKED"

        # Re-inviting after revocation succeeds cleanly, then test expiration -> 410 Gone
        exp_invite = client.post(
            f"/api/v1/organisations/{org_id}/invitations",
            headers=owner.headers,
            json={"email": wrong_user.email, "role_name": "org_member"},
        )
        assert exp_invite.status_code == 201
        exp_token = exp_invite.json()["development_invitation_token"]
        exp_id = exp_invite.json()["invitation"]["id"]

        with ctx.session_factory() as session:
            inv_row = session.get(OrganisationInvitation, uuid.UUID(exp_id))
            assert inv_row is not None
            inv_row.expires_at = utc_now() - timedelta(minutes=5)
            session.commit()

        expired_accept = client.post(
            f"/api/v1/invitations/{exp_token}/accept",
            headers=wrong_user.headers,
        )
        assert expired_accept.status_code == 410
        assert expired_accept.json()["error"]["code"] == "INVITATION_EXPIRED"

        with ctx.session_factory() as session:
            inv_row = session.get(OrganisationInvitation, uuid.UUID(exp_id))
            assert inv_row is not None
            assert inv_row.status == InvitationStatus.EXPIRED.value

        # Re-inviting after expiration also works and lets wrong_user join!
        reinvited = client.post(
            f"/api/v1/organisations/{org_id}/invitations",
            headers=owner.headers,
            json={"email": wrong_user.email, "role_name": "org_member"},
        )
        assert reinvited.status_code == 201
        final_token = reinvited.json()["development_invitation_token"]
        assert (
            client.post(
                f"/api/v1/invitations/{final_token}/accept",
                headers=wrong_user.headers,
            ).status_code
            == 200
        )


def test_invitation_blocks_escalation_and_stale_inviter_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        owner = register_and_login_user(
            client,
            email="owner@esc.example.com",
            full_name="Owner Esc",
        )
        admin = register_and_login_user(
            client,
            email="admin@esc.example.com",
            full_name="Admin Esc",
        )
        candidate = register_and_login_user(
            client,
            email="candidate@esc.example.com",
            full_name="Candidate Esc",
        )

        org_id = client.post(
            "/api/v1/organisations",
            headers=owner.headers,
            json={"name": "Esc Guard Org"},
        ).json()["id"]

        invite_and_accept_member(
            client,
            organisation_id=org_id,
            inviter_headers=owner.headers,
            invitee=admin,
            role_name="org_admin",
        )

        # org_admin CANNOT invite someone as org_owner
        esc_invite = client.post(
            f"/api/v1/organisations/{org_id}/invitations",
            headers=admin.headers,
            json={"email": candidate.email, "role_name": RoleName.ORG_OWNER.value},
        )
        assert esc_invite.status_code == 403
        assert esc_invite.json()["error"]["code"] == "INSUFFICIENT_ROLE_AUTHORITY"

        # org_member cannot list or issue invitations
        member = register_and_login_user(
            client,
            email="plain@esc.example.com",
            full_name="Plain Member",
        )
        invite_and_accept_member(
            client,
            organisation_id=org_id,
            inviter_headers=owner.headers,
            invitee=member,
            role_name="org_member",
        )
        assert (
            client.get(
                f"/api/v1/organisations/{org_id}/invitations",
                headers=member.headers,
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/organisations/{org_id}/invitations",
                headers=member.headers,
                json={"email": candidate.email, "role_name": "org_member"},
            ).status_code
            == 403
        )

        # Admin invites candidate as org_admin; Owner demotes Admin -> org_member BEFORE accept!
        admin_invite = client.post(
            f"/api/v1/organisations/{org_id}/invitations",
            headers=admin.headers,
            json={"email": candidate.email, "role_name": "org_admin"},
        )
        assert admin_invite.status_code == 201
        stale_token = admin_invite.json()["development_invitation_token"]

        assert (
            client.patch(
                f"/api/v1/organisations/{org_id}/members/{admin.user_id}/role",
                headers=owner.headers,
                json={"role_name": "org_member"},
            ).status_code
            == 200
        )

        stale_accept = client.post(
            f"/api/v1/invitations/{stale_token}/accept",
            headers=candidate.headers,
        )
        assert stale_accept.status_code == 403
        assert stale_accept.json()["error"]["code"] == "INVITER_NO_LONGER_AUTHORISED"

        # Unused dummy ref to keep password constant clearly referenced in test suite if needed
        assert len(DEFAULT_TEST_PASSWORD) >= 12
