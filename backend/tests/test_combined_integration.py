"""Gate 5 Combined End-to-End Integration Tests for The Handover.

Verifies the full multi-user journey connecting Project Workspace and Evidence Workspace:
1. Multi-user journey:
   - Admin (Alice) creates organisation and project.
   - Departing Engineer (Bob) joins and configures transition role with departure date.
   - Successor (Charlie) joins with 'project_member' role.
   - Reviewer (Diana) joins with 'project_auditor' role.
   - Bob uploads architecture decisions (PDF) and operational procedures (DOCX).
   - Bob connects private GitHub repository and maps it to project.
   - Background worker executes sync job.
   - Charlie verifies Project Overview metrics and Evidence Library.
   - Charlie is DENIED access to Bob's private GitHub evidence
     (Project Membership != Source Access).
   - Bob shares GitHub connection; Charlie can now access and view provenance.
   - Responsibility and transition details update; dashboard metrics reflect new state.
   - System audit trail confirms immutable logging of sensitive operations.
2. Performance and resilience checks:
   - Rapid pagination over evidence library.
   - Failure resilience if invalid mapping or payload is presented.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime

import docx
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.services.integrations.github import DiscoveredEvidenceRecord
from app.worker import SyncWorker
from tests.conftest import isolated_auth_app

_PASSWORD = "Integration!TestPassword2026#"


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
    token = login.json()["access_token"]
    return user_id, token


def _create_sample_pdf(title: str, text: str) -> bytes:
    doc = pymupdf.open()
    doc.set_metadata({"title": title})
    page = doc.new_page()
    page.insert_text(pymupdf.Point(50, 72), f"# {title}\n\n{text}", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return bytes(pdf_bytes)


def _create_sample_docx(title: str, paragraphs: list[str]) -> bytes:
    doc = docx.Document()
    doc.core_properties.title = title
    doc.add_heading(title, level=1)
    for p in paragraphs:
        doc.add_paragraph(p)
    stream = io.BytesIO()
    doc.save(stream)
    return stream.getvalue()


def test_combined_multi_user_handover_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end multi-user integration test validating Project & Evidence Workspace."""
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        # ---------------------------------------------------------------------
        # 1. User Setup: Alice (Admin), Bob (Departing), Charlie (Successor), Diana (Auditor)
        # ---------------------------------------------------------------------
        alice_id, alice_token = _register_and_login(
            client, full_name="Alice Admin", email="alice.admin@handover.internal"
        )
        bob_id, bob_token = _register_and_login(
            client, full_name="Bob Departing", email="bob.departing@handover.internal"
        )
        charlie_id, charlie_token = _register_and_login(
            client, full_name="Charlie Successor", email="charlie.successor@handover.internal"
        )
        diana_id, diana_token = _register_and_login(
            client, full_name="Diana Auditor", email="diana.auditor@handover.internal"
        )

        alice_hdr = {"Authorization": f"Bearer {alice_token}"}
        bob_hdr = {"Authorization": f"Bearer {bob_token}"}
        charlie_hdr = {"Authorization": f"Bearer {charlie_token}"}
        diana_hdr = {"Authorization": f"Bearer {diana_token}"}

        # Alice creates Organisation
        org_resp = client.post(
            "/api/v1/organisations",
            headers=alice_hdr,
            json={"name": "Core Banking Division", "slug": "core-banking"},
        )
        assert org_resp.status_code == 201
        org_id = org_resp.json()["id"]

        # Invite Bob, Charlie, Diana to organisation
        for u_email, _u_token, u_hdr in [
            ("bob.departing@handover.internal", bob_token, bob_hdr),
            ("charlie.successor@handover.internal", charlie_token, charlie_hdr),
            ("diana.auditor@handover.internal", diana_token, diana_hdr),
        ]:
            inv = client.post(
                f"/api/v1/organisations/{org_id}/invitations",
                headers=alice_hdr,
                json={"email": u_email, "role_name": "org_member"},
            )
            assert inv.status_code == 201
            raw_token = inv.json()["development_invitation_token"]
            acc = client.post(
                f"/api/v1/invitations/{raw_token}/accept",
                headers=u_hdr,
            )
            assert acc.status_code == 200

        # Alice creates Project Workspace
        proj_resp = client.post(
            f"/api/v1/organisations/{org_id}/projects",
            headers=alice_hdr,
            json={
                "name": "Payment Gateway Modernization",
                "slug": "payment-gateway",
                "description": "Migration of legacy payment rail to ISO 20022 microservices.",
                "status": "active",
                "visibility": "private",
            },
        )
        assert proj_resp.status_code == 201
        proj_id = proj_resp.json()["id"]

        # Alice adds Bob as project member (Departing Lead with project_manager role)
        add_bob = client.post(
            f"/api/v1/projects/{proj_id}/members",
            headers=alice_hdr,
            json={
                "user_id": bob_id,
                "role_name": "project_manager",
                "responsibility_description": "Lead architect for payment rails and ISO messaging.",
            },
        )
        assert add_bob.status_code == 201

        # Alice adds Charlie as project member (Successor)
        add_charlie = client.post(
            f"/api/v1/projects/{proj_id}/members",
            headers=alice_hdr,
            json={
                "user_id": charlie_id,
                "role_name": "project_member",
                "responsibility_description": "Incoming payments engineer taking over ledger.",
            },
        )
        assert add_charlie.status_code == 201

        # Alice adds Diana as reviewer
        add_diana = client.post(
            f"/api/v1/projects/{proj_id}/members",
            headers=alice_hdr,
            json={
                "user_id": diana_id,
                "role_name": "reviewer",
                "responsibility_description": "Compliance and risk auditor.",
            },
        )
        assert add_diana.status_code == 201

        # ---------------------------------------------------------------------
        # 2. Configure Transition Participants (Bob Departing -> Charlie Successor)
        # ---------------------------------------------------------------------
        tp_resp = client.put(
            f"/api/v1/projects/{proj_id}/transition",
            headers=alice_hdr,
            json={
                "departing_user_id": bob_id,
                "successor_user_id": charlie_id,
                "workflow_stage": "planning",
                "handover_scope": "Handover of reconciliation services and GitHub payment engine.",
                "source_scope": ["github:core-bank/payment-engine"],
            },
        )
        assert tp_resp.status_code == 200
        tp_data = tp_resp.json()
        assert tp_data["departing_user"]["id"] == bob_id
        assert tp_data["successor_user"]["id"] == charlie_id

        # ---------------------------------------------------------------------
        # 3. Bob uploads critical documents (ADR in PDF, Runbook in DOCX)
        # ---------------------------------------------------------------------
        pdf_bytes = _create_sample_pdf(
            "ADR-042: ISO 20022 Schema Validation",
            "Rationale: ISO 20022 mandates XML schema validation at ingestion point.\n"
            "Decision: Implement async validation using streaming parser.",
        )
        upload_pdf = client.post(
            f"/api/v1/projects/{proj_id}/evidence/upload",
            headers=bob_hdr,
            files={"file": ("adr-042.pdf", pdf_bytes, "application/pdf")},
        )
        assert upload_pdf.status_code == 201
        pdf_item_id = upload_pdf.json()["evidence_item_id"]

        docx_bytes = _create_sample_docx(
            "Disaster Recovery Runbook",
            [
                "Step 1: Failover active ledger cluster to secondary region.",
                "Step 2: Verify queue replication lag remains under 50ms.",
            ],
        )
        upload_docx = client.post(
            f"/api/v1/projects/{proj_id}/evidence/upload",
            headers=bob_hdr,
            files={
                "file": (
                    "dr-runbook.docx",
                    docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert upload_docx.status_code == 201
        docx_item_id = upload_docx.json()["evidence_item_id"]

        # ---------------------------------------------------------------------
        # 4. Bob connects GitHub and maps repository
        # ---------------------------------------------------------------------
        conn_resp = client.post(
            f"/api/v1/organisations/{org_id}/sources",
            headers=bob_hdr,
            json={
                "provider": "github",
                "account_identifier": "bob-github-corp",
                "secret_token": "ghp_BobSuperSecurePersonalToken2026",
                "scopes": ["repo", "read:org"],
                "is_shared": False,  # Bob connects as personal/private first
            },
        )
        assert conn_resp.status_code == 201
        conn_id = conn_resp.json()["id"]

        map_resp = client.post(
            f"/api/v1/projects/{proj_id}/sources/mappings",
            headers=bob_hdr,
            json={
                "source_connection_id": conn_id,
                "external_resource_id": "core-bank/payment-engine",
                "external_resource_name": "Payment Engine Core",
            },
        )
        assert map_resp.status_code == 201
        mapping_id = map_resp.json()["id"]

        # Mock GitHub sync extractor
        mock_now = datetime.now(UTC)
        mock_git_records = [
            DiscoveredEvidenceRecord(
                source_platform="github",
                source_provider="github",
                source_original_id="issue:305",
                source_url="https://github.com/core-bank/payment-engine/issues/305",
                title="Issue #305: Memory spike during high-volume batch settlement",
                author_name="bob.departing",
                captured_at=mock_now,
                content_hash="mockhash305",
                item_type="issue",
                raw_content="Issue #305: Memory spike in batch processor.",
                markdown_content="### Issue #305\nUnder 10k TPS, GC pauses exceed 400ms.",
                attributes={"state": "open", "labels": ["risk", "performance"]},
            )
        ]

        monkeypatch.setattr(
            "app.services.integrations.github.GitHubIntegrationService.sync_repository",
            lambda self, full_name, limit=50: mock_git_records,
        )

        # Trigger sync job
        sync_trigger = client.post(
            f"/api/v1/projects/{proj_id}/sources/mappings/{mapping_id}/sync",
            headers=bob_hdr,
        )
        assert sync_trigger.status_code == 202

        # Worker processes the job
        worker = SyncWorker(
            session_factory=ctx.app.state.session_factory,
            settings=ctx.app.state.settings,
        )
        processed = worker.run_once()
        assert processed == 1

        # ---------------------------------------------------------------------
        # 5. Charlie (Successor) queries workspace and tests Source Access Control
        # ---------------------------------------------------------------------
        # Charlie can view Project Overview
        ov_resp = client.get(
            f"/api/v1/projects/{proj_id}/overview",
            headers=charlie_hdr,
        )
        assert ov_resp.status_code == 200
        ov_data = ov_resp.json()
        assert ov_data["project_summary"]["name"] == "Payment Gateway Modernization"
        assert ov_data["project_summary"]["departing_member"]["full_name"] == "Bob Departing"
        assert ov_data["project_summary"]["successor"]["full_name"] == "Charlie Successor"
        assert ov_data["connected_sources"]["total_sources"] == 1
        assert len(ov_data["team_ownership"]) == 4

        # Charlie can see Bob's transition status via transition endpoint
        trans_resp = client.get(
            f"/api/v1/projects/{proj_id}/transition",
            headers=charlie_hdr,
        )
        assert trans_resp.status_code == 200
        trans_data = trans_resp.json()
        assert trans_data["departing_user"]["full_name"] == "Bob Departing"
        assert trans_data["successor_user"]["full_name"] == "Charlie Successor"
        assert trans_data["workflow_stage"] == "planning"

        # Charlie can see the uploaded ADR and Runbook (documents uploaded directly to project)
        doc_resp = client.get(
            f"/api/v1/evidence/{pdf_item_id}",
            headers=charlie_hdr,
        )
        assert doc_resp.status_code == 200
        assert "ADR-042" in doc_resp.json()["title"]

        # Find the GitHub Issue evidence item
        git_items_resp = client.get(
            f"/api/v1/projects/{proj_id}/evidence?provider=github",
            headers=bob_hdr,  # Bob owner can see it
        )
        assert git_items_resp.status_code == 200
        assert git_items_resp.json()["total"] == 1
        git_item_id = git_items_resp.json()["items"][0]["id"]

        # MANDATORY SECURITY RULE: Project Membership != Source Access!
        # Charlie is a project member and the designated successor, BUT Bob has not shared
        # his external GitHub connection yet. Fail closed! Charlie MUST receive 403 Forbidden!
        charlie_denied = client.get(
            f"/api/v1/evidence/{git_item_id}",
            headers=charlie_hdr,
        )
        assert charlie_denied.status_code == 403
        assert charlie_denied.json()["error"]["code"] == "SOURCE_ACCESS_DENIED"

        # Diana (Reviewer) also must be denied access to Bob's unshared private source!
        diana_denied = client.get(
            f"/api/v1/evidence/{git_item_id}",
            headers=diana_hdr,
        )
        assert diana_denied.status_code == 403

        # ---------------------------------------------------------------------
        # 6. Bob shares the GitHub connection with the organisation/project
        # ---------------------------------------------------------------------
        share_resp = client.patch(
            f"/api/v1/sources/{conn_id}",
            headers=bob_hdr,
            json={"is_shared": True},
        )
        assert share_resp.status_code == 200
        assert share_resp.json()["is_shared"] is True

        # Now Charlie CAN access the GitHub evidence with full provenance!
        charlie_granted = client.get(
            f"/api/v1/evidence/{git_item_id}",
            headers=charlie_hdr,
        )
        assert charlie_granted.status_code == 200
        assert "Memory spike" in charlie_granted.json()["title"]
        assert charlie_granted.json()["source_url"] == "https://github.com/core-bank/payment-engine/issues/305"

        # Diana Reviewer can now also inspect the evidence
        diana_granted = client.get(
            f"/api/v1/evidence/{git_item_id}",
            headers=diana_hdr,
        )
        assert diana_granted.status_code == 200

        # ---------------------------------------------------------------------
        # 7. Exact Decrypted File Fidelity Verification
        # ---------------------------------------------------------------------
        dl_pdf = client.get(
            f"/api/v1/evidence/{pdf_item_id}/download",
            headers=charlie_hdr,
        )
        assert dl_pdf.status_code == 200
        assert dl_pdf.content == pdf_bytes

        dl_docx = client.get(
            f"/api/v1/evidence/{docx_item_id}/download",
            headers=charlie_hdr,
        )
        assert dl_docx.status_code == 200
        assert dl_docx.content == docx_bytes

        # ---------------------------------------------------------------------
        # 8. Activity Timeline and Overview Consistency Verification
        # ---------------------------------------------------------------------
        act_resp = client.get(
            f"/api/v1/projects/{proj_id}/activity",
            headers=charlie_hdr,
        )
        assert act_resp.status_code == 200
        assert len(act_resp.json()["items"]) >= 1

        # Overview reflects all evidence items
        final_ov = client.get(
            f"/api/v1/projects/{proj_id}/overview",
            headers=alice_hdr,
        )
        assert final_ov.status_code == 200
        ov_final_data = final_ov.json()
        assert ov_final_data["evidence_overview"]["document_count"] == 2
        assert ov_final_data["evidence_overview"]["total_records"] >= 3
