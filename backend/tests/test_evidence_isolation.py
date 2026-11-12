"""Multi-tenant isolation, RBAC permission, deletion, and audit-logging tests."""

from __future__ import annotations

import uuid
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.evidence import EvidenceItem
from tests.conftest import (
    invite_and_accept_member,
    isolated_auth_app,
    register_and_login_user,
)


def _sample_pdf(text_line: str) -> bytes:
    doc = pymupdf.Document()  # type: ignore[no-untyped-call]
    try:
        page = doc.new_page()
        page.insert_text((72, 72), text_line)
        return bytes(doc.tobytes())  # type: ignore[no-untyped-call]
    finally:
        doc.close()  # type: ignore[no-untyped-call]


def test_cross_org_project_roles_acl_and_deletion_isolation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    upload_dir = tmp_path / "acl_uploads"
    with isolated_auth_app(monkeypatch, upload_storage_path=upload_dir) as ctx:
        with TestClient(ctx.app) as client:
            owner_a = register_and_login_user(
                client,
                email="acl-owner-a@example.com",
                full_name="Owner A",
            )
            member_a1 = register_and_login_user(
                client,
                email="acl-dev1@example.com",
                full_name="Dev One",
            )
            member_a2 = register_and_login_user(
                client,
                email="acl-dev2@example.com",
                full_name="Dev Two",
            )
            reviewer_a = register_and_login_user(
                client,
                email="acl-rev@example.com",
                full_name="Reviewer A",
            )
            non_project_org_member = register_and_login_user(
                client,
                email="acl-orgmem@example.com",
                full_name="Org Member Only",
            )
            outsider_b = register_and_login_user(
                client,
                email="acl-outsider@example.com",
                full_name="Outsider B",
            )

            org_a = client.post(
                "/api/v1/organisations",
                headers=owner_a.headers,
                json={"name": "Tenant Alpha"},
            ).json()["id"]
            _ = client.post(
                "/api/v1/organisations",
                headers=outsider_b.headers,
                json={"name": "Tenant Beta"},
            ).json()["id"]

            for invitee in (member_a1, member_a2, reviewer_a, non_project_org_member):
                invite_and_accept_member(
                    client,
                    organisation_id=org_a,
                    inviter_headers=owner_a.headers,
                    invitee=invitee,
                    role_name="org_member",
                )

            priv_proj_id = client.post(
                f"/api/v1/organisations/{org_a}/projects",
                headers=owner_a.headers,
                json={"name": "Private Handover", "status": "active", "visibility": "private"},
            ).json()["id"]
            org_vis_proj_id = client.post(
                f"/api/v1/organisations/{org_a}/projects",
                headers=owner_a.headers,
                json={"name": "Shared Discovery", "status": "active", "visibility": "organisation"},
            ).json()["id"]

            for target_proj in (priv_proj_id, org_vis_proj_id):
                for usr, role in (
                    (member_a1, "project_member"),
                    (member_a2, "project_member"),
                    (reviewer_a, "reviewer"),
                ):
                    add_resp = client.post(
                        f"/api/v1/projects/{target_proj}/members",
                        headers=owner_a.headers,
                        json={"user_id": str(usr.user_id), "role_name": role},
                    )
                    assert add_resp.status_code == 201

            # Dev 1 uploads a PDF to both projects
            up_priv = client.post(
                f"/api/v1/projects/{priv_proj_id}/evidence/documents",
                headers=member_a1.headers,
                files={"file": ("priv.pdf", _sample_pdf("Private doc content"), "application/pdf")},
            )
            assert up_priv.status_code == 201
            priv_ev_id = up_priv.json()["evidence"]["id"]

            up_shared = client.post(
                f"/api/v1/projects/{org_vis_proj_id}/evidence/documents",
                headers=member_a1.headers,
                files={
                    "file": (
                        "shared.pdf",
                        _sample_pdf("Shared org-proj content"),
                        "application/pdf",
                    )
                },
            )
            assert up_shared.status_code == 201
            shared_ev_id = up_shared.json()["evidence"]["id"]

            # 1. Cross-org outsider sees 404 on every endpoint (no existence leak)
            for method, path in (
                ("GET", f"/api/v1/projects/{priv_proj_id}/evidence"),
                ("GET", f"/api/v1/projects/{org_vis_proj_id}/evidence"),
                ("GET", f"/api/v1/evidence/{priv_ev_id}"),
                ("DELETE", f"/api/v1/evidence/{priv_ev_id}"),
                ("POST", f"/api/v1/evidence/{priv_ev_id}/reprocess"),
            ):
                resp = client.request(method, path, headers=outsider_b.headers)
                assert resp.status_code == 404
            out_up = client.post(
                f"/api/v1/projects/{org_vis_proj_id}/evidence/documents",
                headers=outsider_b.headers,
                files={"file": ("x.pdf", _sample_pdf("X"), "application/pdf")},
            )
            assert out_up.status_code == 404

            # 2. Non-project org member: 404 on private project, 403 on org-visible evidence
            assert (
                client.get(
                    f"/api/v1/projects/{priv_proj_id}/evidence",
                    headers=non_project_org_member.headers,
                ).status_code
                == 404
            )
            assert (
                client.get(
                    f"/api/v1/evidence/{priv_ev_id}",
                    headers=non_project_org_member.headers,
                ).status_code
                == 404
            )
            assert (
                client.get(
                    f"/api/v1/projects/{org_vis_proj_id}/evidence",
                    headers=non_project_org_member.headers,
                ).status_code
                == 403
            )
            assert (
                client.get(
                    f"/api/v1/evidence/{shared_ev_id}",
                    headers=non_project_org_member.headers,
                ).status_code
                == 403
            )
            assert (
                client.post(
                    f"/api/v1/projects/{org_vis_proj_id}/evidence/documents",
                    headers=non_project_org_member.headers,
                    files={"file": ("no.pdf", _sample_pdf("Nope"), "application/pdf")},
                ).status_code
                == 403
            )

            # 3. Reviewer can read evidence list/detail, CANNOT upload or delete
            assert (
                client.get(
                    f"/api/v1/projects/{priv_proj_id}/evidence",
                    headers=reviewer_a.headers,
                ).status_code
                == 200
            )
            assert (
                client.get(
                    f"/api/v1/evidence/{priv_ev_id}",
                    headers=reviewer_a.headers,
                ).status_code
                == 200
            )
            assert (
                client.post(
                    f"/api/v1/projects/{priv_proj_id}/evidence/documents",
                    headers=reviewer_a.headers,
                    files={"file": ("rev.pdf", _sample_pdf("Rev"), "application/pdf")},
                ).status_code
                == 403
            )
            assert (
                client.delete(
                    f"/api/v1/evidence/{priv_ev_id}",
                    headers=reviewer_a.headers,
                ).status_code
                == 403
            )

            # 4. Future source ACL hook (`source_restricted`) denies regular project_member
            with ctx.session_factory() as session:
                shared_row = session.get(EvidenceItem, uuid.UUID(shared_ev_id))
                assert shared_row is not None
                shared_row.acl_scope = "source_restricted"
                session.commit()

            assert (
                client.get(
                    f"/api/v1/evidence/{shared_ev_id}",
                    headers=member_a2.headers,
                ).status_code
                == 403
            )
            assert (
                client.get(f"/api/v1/evidence/{shared_ev_id}", headers=owner_a.headers).status_code
                == 200
            )

            # 5. Other contributor cannot delete member_a1's file; uploader OR manager can
            assert (
                client.delete(
                    f"/api/v1/evidence/{priv_ev_id}",
                    headers=member_a2.headers,
                ).status_code
                == 403
            )
            assert (
                client.delete(
                    f"/api/v1/evidence/{priv_ev_id}",
                    headers=member_a1.headers,
                ).status_code
                == 204
            )
            assert (
                client.delete(
                    f"/api/v1/evidence/{shared_ev_id}",
                    headers=owner_a.headers,
                ).status_code
                == 204
            )

            # Deleted items are hidden from read/list and physical encrypted files are removed
            assert (
                client.get(f"/api/v1/evidence/{priv_ev_id}", headers=owner_a.headers).status_code
                == 404
            )
            assert list(upload_dir.rglob("*.enc")) == []

            # Confirm denied actions & deletion persisted immutable audit logs
            with ctx.session_factory() as session:
                denied_audits = list(
                    session.execute(
                        select(AuditLog).where(AuditLog.outcome == "denied")
                    )
                    .scalars()
                    .all()
                )
                assert any(a.event_type == "evidence.access_denied" for a in denied_audits)
                assert any(a.event_type == "evidence.source_acl_denied" for a in denied_audits)
                assert any(a.event_type == "evidence.delete_denied" for a in denied_audits)
                deleted_audits = list(
                    session.execute(
                        select(AuditLog).where(AuditLog.event_type == "evidence.deleted")
                    )
                    .scalars()
                    .all()
                )
                assert len(deleted_audits) == 2
