"""Comprehensive integration tests for Evidence Workspace (Panel A, B, C, Upload, Sync, ACLs)."""

from __future__ import annotations

import io
from datetime import UTC, datetime

import docx
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.services.integrations.github import DiscoveredEvidenceRecord
from tests.conftest import isolated_auth_app

_PASSWORD = "Handover!Evidence2026#Secure"


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


def _create_sample_pdf_bytes(title: str = "Architecture Decision Record") -> bytes:
    """Generate minimal valid PDF bytes in-memory using PyMuPDF."""
    doc = pymupdf.open()
    doc.set_metadata({"title": title})
    page = doc.new_page()
    page.insert_text(
        pymupdf.Point(50, 72),
        f"# {title}\n\nDecision: Migrate monolithic core to event-driven services.\n"
        "Rationale: Unblock parallel team development and isolated deployments.",
        fontsize=12,
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return bytes(pdf_bytes)


def _create_sample_docx_bytes(title: str = "Operational Runbook") -> bytes:
    """Generate minimal valid DOCX bytes in-memory using python-docx."""
    doc = docx.Document()
    doc.core_properties.title = title
    doc.add_heading(title, level=1)
    doc.add_paragraph("Step 1: Check health endpoints across all microservices.")
    doc.add_paragraph("Step 2: Verify database connection pooling latency.")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Service"
    table.cell(0, 1).text = "Threshold"
    table.cell(1, 0).text = "Payment Gateway"
    table.cell(1, 1).text = "200ms"
    stream = io.BytesIO()
    doc.save(stream)
    return stream.getvalue()


def test_evidence_workspace_complete_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test full Evidence Workspace lifecycle across Panels A, B, and C."""
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        # 1. Setup Organisation and Project with Alice (owner) and Bob (member)
        alice_id, alice_token = _register_and_login(
            client, full_name="Alice Owner", email="alice.owner@example.com"
        )
        bob_id, bob_token = _register_and_login(
            client, full_name="Bob Member", email="bob.member@example.com"
        )

        alice_hdr = {"Authorization": f"Bearer {alice_token}"}
        bob_hdr = {"Authorization": f"Bearer {bob_token}"}

        # Create Org
        org_resp = client.post(
            "/api/v1/organisations",
            headers=alice_hdr,
            json={"name": "Platform Engineering", "slug": "plat-eng"},
        )
        assert org_resp.status_code == 201
        org_id = org_resp.json()["id"]

        # Invite and accept Bob to Org
        inv = client.post(
            f"/api/v1/organisations/{org_id}/invitations",
            headers=alice_hdr,
            json={"email": "bob.member@example.com", "role_name": "org_member"},
        )
        assert inv.status_code == 201
        raw_token = inv.json()["development_invitation_token"]
        assert raw_token is not None
        acc = client.post(
            f"/api/v1/invitations/{raw_token}/accept",
            headers=bob_hdr,
        )
        assert acc.status_code == 200

        # Alice creates Project
        proj_resp = client.post(
            f"/api/v1/organisations/{org_id}/projects",
            headers=alice_hdr,
            json={
                "name": "Knowledge Extraction Project",
                "slug": "knowledge-extraction",
                "status": "active",
                "visibility": "private",
            },
        )
        assert proj_resp.status_code == 201
        proj_id = proj_resp.json()["id"]

        # Add Bob as project member with project.evidence.read / project.evidence.upload
        add_bob = client.post(
            f"/api/v1/projects/{proj_id}/members",
            headers=alice_hdr,
            json={
                "user_id": bob_id,
                "role_name": "project_member",
                "responsibility_description": "Data pipelines and ingestion",
            },
        )
        assert add_bob.status_code == 201

        # ---------------------------------------------------------------------
        # Stage A: Document Upload (PDF & DOCX)
        # ---------------------------------------------------------------------
        pdf_bytes = _create_sample_pdf_bytes("Core Banking ADR 001")
        pdf_upload = client.post(
            f"/api/v1/projects/{proj_id}/evidence/upload",
            headers=bob_hdr,
            files={"file": ("adr-001.pdf", pdf_bytes, "application/pdf")},
        )
        assert pdf_upload.status_code == 201
        pdf_data = pdf_upload.json()
        pdf_ev = pdf_data.get("evidence", pdf_data)
        assert pdf_ev.get("original_filename") == "adr-001.pdf"
        assert pdf_ev.get("category") == "pdf_document"
        pdf_evidence_id = pdf_ev["id"]

        docx_bytes = _create_sample_docx_bytes("Production Runbook")
        docx_upload = client.post(
            f"/api/v1/projects/{proj_id}/evidence/upload",
            headers=bob_hdr,
            files={
                "file": (
                    "runbook.docx",
                    docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert docx_upload.status_code == 201
        docx_data = docx_upload.json()
        docx_ev = docx_data.get("evidence", docx_data)
        assert docx_ev.get("category") == "docx_document"
        docx_evidence_id = docx_ev["id"]

        # ---------------------------------------------------------------------
        # Stage B: Evidence Library (Panel B) Search & Metrics
        # ---------------------------------------------------------------------
        lib_resp = client.get(
            f"/api/v1/projects/{proj_id}/evidence",
            headers=bob_hdr,
        )
        assert lib_resp.status_code == 200
        lib_data = lib_resp.json()
        assert lib_data["total"] == 2
        titles = [item["title"] for item in lib_data["items"]]
        assert any("Core Banking ADR 001" in t for t in titles)

        # Keyword Search
        search_resp = client.get(
            f"/api/v1/projects/{proj_id}/evidence?q=Runbook",
            headers=bob_hdr,
        )
        assert search_resp.status_code == 200
        assert search_resp.json()["total"] == 1
        assert "Production Runbook" in search_resp.json()["items"][0]["title"]

        # Filter by provider
        filter_resp = client.get(
            f"/api/v1/projects/{proj_id}/evidence?provider=pdf",
            headers=bob_hdr,
        )
        assert filter_resp.status_code == 200
        assert filter_resp.json()["total"] == 1
        assert filter_resp.json()["items"][0]["provider"] == "pdf"

        # Evidence Metrics
        metrics_resp = client.get(
            f"/api/v1/projects/{proj_id}/evidence/metrics",
            headers=bob_hdr,
        )
        assert metrics_resp.status_code == 200
        m_data = metrics_resp.json()
        assert m_data["total_items"] == 2
        assert m_data["total_documents"] == 2
        assert m_data["total_bytes"] > 0

        # ---------------------------------------------------------------------
        # Stage C: Evidence Details (Panel C) & Secure Download
        # ---------------------------------------------------------------------
        detail_resp = client.get(
            f"/api/v1/evidence/{pdf_evidence_id}",
            headers=bob_hdr,
        )
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["can_download"] is True
        assert detail_data["download_url"] is not None
        assert len(detail_data["chunks"]) >= 1
        assert "Decision: Migrate" in detail_data["chunks"][0]["content_text"]

        # Download decrypted PDF content
        dl_resp = client.get(
            f"/api/v1/evidence/{pdf_evidence_id}/download",
            headers=bob_hdr,
        )
        assert dl_resp.status_code == 200
        assert dl_resp.headers["content-type"] == "application/pdf"
        assert dl_resp.content == pdf_bytes  # Byte-for-byte exact fidelity!

        # Download decrypted DOCX content
        dl_docx = client.get(
            f"/api/v1/evidence/{docx_evidence_id}/download",
            headers=alice_hdr,
        )
        assert dl_docx.status_code == 200
        assert dl_docx.content == docx_bytes  # Byte-for-byte exact fidelity!

        # ---------------------------------------------------------------------
        # Stage D: Panel A - Connected Sources & Project Mappings
        # ---------------------------------------------------------------------
        # Alice registers a private GitHub source connection
        conn_resp = client.post(
            f"/api/v1/organisations/{org_id}/sources",
            headers=alice_hdr,
            json={
                "provider": "github",
                "account_identifier": "alice-github",
                "secret_token": "ghp_MockSecretToken2026ForTestingPurposes",
                "scopes": ["repo", "read:org"],
                "is_shared": False,
            },
        )
        assert conn_resp.status_code == 201
        conn_id = conn_resp.json()["id"]

        # Map GitHub repository to project
        map_resp = client.post(
            f"/api/v1/projects/{proj_id}/sources/mappings",
            headers=alice_hdr,
            json={
                "source_connection_id": conn_id,
                "external_resource_id": "org/ledger-service",
                "external_resource_name": "Ledger Service Core",
            },
        )
        assert map_resp.status_code == 201
        mapping_id = map_resp.json()["id"]

        # List project source mappings
        maps_get = client.get(
            f"/api/v1/projects/{proj_id}/sources/mappings",
            headers=bob_hdr,
        )
        assert maps_get.status_code == 200
        assert maps_get.json()["total"] == 1

        # ---------------------------------------------------------------------
        # Stage E: Mock Sync Pipeline & Source ACL Enforcement
        # ---------------------------------------------------------------------
        # Mock GitHub sync extraction to return realistic external records
        now = datetime.now(UTC)
        mock_records = [
            DiscoveredEvidenceRecord(
                source_platform="github",
                source_provider="github",
                source_original_id="pr:101",
                source_url="https://github.com/org/ledger-service/pull/101",
                title="PR #101: Add dual-ledger idempotency key",
                author_name="alice.dev",
                captured_at=now,
                content_hash="abc123mockhash",
                item_type="pull_request",
                raw_content="PR #101: Add dual-ledger idempotency key\nAuthor: alice.dev",
                markdown_content="## PR #101\nAdded idempotency key to prevent double posting.",
                attributes={"pr_number": 101, "state": "merged"},
            )
        ]

        def _mock_sync(
            self: object,
            full_name: str,
            limit: int = 50,
        ) -> list[DiscoveredEvidenceRecord]:
            return mock_records

        monkeypatch.setattr(
            "app.services.integrations.github.GitHubIntegrationService.sync_repository",
            _mock_sync,
        )

        # Trigger sync
        sync_trigger = client.post(
            f"/api/v1/projects/{proj_id}/sources/mappings/{mapping_id}/sync",
            headers=alice_hdr,
        )
        assert sync_trigger.status_code == 202
        assert "id" in sync_trigger.json()

        # Run background worker pass
        from app.worker import SyncWorker

        worker = SyncWorker(
            session_factory=ctx.app.state.session_factory,
            settings=ctx.app.state.settings,
        )
        processed = worker.run_once()
        assert processed == 1

        # Verify sync job completed
        jobs_resp = client.get(
            f"/api/v1/projects/{proj_id}/sources/mappings/{mapping_id}/jobs",
            headers=alice_hdr,
        )
        assert jobs_resp.status_code == 200
        assert jobs_resp.json()["items"][0]["status"] == "completed"

        # ---------------------------------------------------------------------
        # CRITICAL RULE VERIFICATION: Project Membership != Source Access!
        # ---------------------------------------------------------------------
        # Query newly ingested GitHub PR item ID
        lib_alice = client.get(
            f"/api/v1/projects/{proj_id}/evidence?provider=github",
            headers=alice_hdr,
        )
        assert lib_alice.status_code == 200
        assert lib_alice.json()["total"] == 1
        github_item_id = lib_alice.json()["items"][0]["id"]

        # Alice (owner of GitHub source) CAN read the private evidence item
        alice_view = client.get(
            f"/api/v1/evidence/{github_item_id}",
            headers=alice_hdr,
        )
        assert alice_view.status_code == 200

        # Bob is an active Project Member, BUT does NOT own Alice's GitHub source!
        # Rule: Fail closed! Bob is DENIED access to this private external evidence!
        bob_denied = client.get(
            f"/api/v1/evidence/{github_item_id}",
            headers=bob_hdr,
        )
        assert bob_denied.status_code == 403
        assert bob_denied.json()["error"]["code"] == "SOURCE_ACCESS_DENIED"

        # In Evidence Library, Bob's view pre-filters out items he has no source access to:
        bob_lib = client.get(
            f"/api/v1/projects/{proj_id}/evidence?provider=github",
            headers=bob_hdr,
        )
        assert bob_lib.status_code == 200
        assert bob_lib.json()["total"] == 0  # Pre-filtered, Bob sees 0 private GitHub items!

        # Now Alice shares the connection with organisation/project
        alice_share = client.patch(
            f"/api/v1/sources/{conn_id}",
            headers=alice_hdr,
            json={"is_shared": True},
        )
        assert alice_share.status_code == 200

        # Now Bob CAN access the evidence item!
        bob_allowed = client.get(
            f"/api/v1/evidence/{github_item_id}",
            headers=bob_hdr,
        )
        assert bob_allowed.status_code == 200
        assert "Add dual-ledger idempotency key" in bob_allowed.json()["title"]

        # ---------------------------------------------------------------------
        # Stage F: Combined Project Workspace Overview Dashboard Update
        # ---------------------------------------------------------------------
        overview_resp = client.get(
            f"/api/v1/projects/{proj_id}/overview",
            headers=bob_hdr,
        )
        assert overview_resp.status_code == 200
        ov = overview_resp.json()
        assert ov["connected_sources"]["total_sources"] == 1
        assert ov["connected_sources"]["health_status"] == "healthy"
        assert ov["evidence_overview"]["total_records"] >= 2
        assert ov["evidence_overview"]["document_count"] == 2
