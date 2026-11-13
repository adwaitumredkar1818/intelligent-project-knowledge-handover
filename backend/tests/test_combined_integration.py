"""Combined end-to-end integration tests connecting Project Workspace & Evidence/Integrations.

Verifies the full multi-user journey across the reconciled platform:
1. Multi-user setup: Alice (Admin), Bob (Departing PM), Charlie (Successor), Diana (Reviewer).
2. Transition configuration (departing member, successor, workflow stage, capture scope).
3. Document upload (PDF & DOCX) and CompositeWorkerService extraction.
4. Delegated GitHub OAuth connection, repository mapping, and sync via SourceSyncWorkerService.
5. Mandatory Rule: Project Membership != Source Access (fail-closed ACL on evidence & overview).
6. Delegated per-user verification (`/verify-access`) granting Charlie access to synced evidence.
7. Project Overview & Activity timeline consistency.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import docx
import httpx
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.models.enums import SourceSyncRunStatus
from app.services.document_extraction import DocumentExtractionService
from app.services.ingestion_worker import IngestionWorkerService
from app.services.integrations.sync_worker import SourceSyncWorkerService
from app.services.ocr import OCRPageRequest, OCRPageResult
from app.services.storage import LocalPrivateStorageBackend
from app.services.token_encryption import LocalTokenEncryptionService
from app.worker import CompositeWorkerService
from tests.conftest import isolated_auth_app, register_and_login_user


class _NoopOCR:
    model_name = "noop-ocr"

    def extract_page_text(self, request: OCRPageRequest) -> OCRPageResult:
        return OCRPageResult(
            page_number=request.page_number,
            text="",
            model_name=self.model_name,
            truncated=False,
            done_reason="stop",
            prompt_eval_count=0,
            eval_count=0,
            duration_ms=1,
        )


def _create_sample_pdf(title: str, text: str) -> bytes:
    doc = pymupdf.Document()  # type: ignore[no-untyped-call]
    doc.set_metadata({"title": title})
    page = doc.new_page()
    point = pymupdf.Point(50, 72)  # type: ignore[no-untyped-call]
    page.insert_text(point, f"# {title}\n\n{text}", fontsize=12)
    pdf_bytes = doc.tobytes()  # type: ignore[no-untyped-call]
    doc.close()  # type: ignore[no-untyped-call]
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


def test_combined_multi_user_handover_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """End-to-end multi-user integration test validating Project & Evidence Workspaces."""
    upload_tmp = tmp_path / "combined_uploads"
    gh_tokens = {"bob_code": "gho_bob_token_001", "charlie_code": "gho_charlie_token_002"}

    def b64(text: str) -> str:
        return base64.b64encode(text.encode("utf-8")).decode("ascii")

    def gh_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/login/oauth/access_token":
            body_text = request.content.decode("utf-8")
            code = parse_qs(body_text).get("code", ["bob_code"])[0]
            tok = gh_tokens.get(code, "gho_bob_token_001")
            return httpx.Response(
                200,
                json={"access_token": tok, "token_type": "bearer", "scope": "repo read:user"},
            )
        auth = request.headers.get("Authorization", "")
        if path == "/user":
            if auth == "Bearer gho_charlie_token_002":
                return httpx.Response(
                    200,
                    json={"id": 2002, "login": "charlie-dev", "email": "charlie@handover.internal"},
                )
            return httpx.Response(
                200,
                json={"id": 2001, "login": "bob-dev", "email": "bob@handover.internal"},
            )
        if path == "/repos/core-bank/payment-engine":
            return httpx.Response(
                200,
                json={
                    "id": 77001,
                    "name": "payment-engine",
                    "full_name": "core-bank/payment-engine",
                    "private": True,
                    "visibility": "private",
                    "default_branch": "main",
                    "description": "ISO 20022 payment settlement engine",
                    "html_url": "https://github.com/core-bank/payment-engine",
                    "updated_at": "2026-11-01T10:00:00Z",
                    "owner": {"login": "core-bank"},
                    "permissions": {"pull": True, "push": True},
                },
            )
        if path == "/repos/core-bank/payment-engine/issues":
            return httpx.Response(
                200,
                headers={"ETag": '"etag-pe-1"'},
                json=[
                    {
                        "number": 305,
                        "title": "Memory spike during high-volume batch settlement",
                        "state": "open",
                        "body": "Under 10k TPS, GC pauses exceed 400ms.",
                        "html_url": "https://github.com/core-bank/payment-engine/issues/305",
                        "created_at": "2026-10-15T08:00:00Z",
                        "updated_at": "2026-11-01T14:30:00Z",
                        "user": {"login": "bob-dev"},
                        "labels": [{"name": "performance"}],
                    }
                ],
            )
        if path == "/repos/core-bank/payment-engine/issues/305/comments":
            return httpx.Response(200, json=[])
        if path == "/repos/core-bank/payment-engine/commits":
            return httpx.Response(200, json=[])
        if path == "/repos/core-bank/payment-engine/readme":
            return httpx.Response(
                200,
                json={
                    "path": "README.md",
                    "sha": "pe-readme-1",
                    "html_url": "https://github.com/core-bank/payment-engine/blob/main/README.md",
                    "encoding": "base64",
                    "size": 32,
                    "content": b64("# Payment Engine\nSettlement core."),
                },
            )
        if path == "/repos/core-bank/payment-engine/git/trees/main":
            return httpx.Response(200, json={"tree": []})
        if path == "/repos/core-bank/payment-engine/discussions":
            return httpx.Response(404, json={"message": "Not Found"})
        return httpx.Response(404, json={"message": f"Unhandled {path}"})

    transport = httpx.MockTransport(gh_handler)
    with isolated_auth_app(
        monkeypatch,
        upload_storage_path=upload_tmp,
        github_enabled=True,
        github_client_id="gh-cid",
        github_client_secret="gh-csec-secret-value",
    ) as ctx:
        ctx.app.state.integration_http_transport = transport
        with TestClient(ctx.app) as client:
            # 1. Users: Alice (Admin), Bob (Departing), Charlie (Successor), Diana (Reviewer)
            alice = register_and_login_user(
                client, full_name="Alice Admin", email="alice.admin@handover.internal"
            )
            bob = register_and_login_user(
                client, full_name="Bob Departing", email="bob.departing@handover.internal"
            )
            charlie = register_and_login_user(
                client,
                full_name="Charlie Successor",
                email="charlie.successor@handover.internal",
            )
            diana = register_and_login_user(
                client, full_name="Diana Auditor", email="diana.auditor@handover.internal"
            )

            org_resp = client.post(
                "/api/v1/organisations",
                headers=alice.headers,
                json={"name": "Core Banking Division", "slug": "core-banking"},
            )
            assert org_resp.status_code == 201
            org_id = org_resp.json()["id"]

            for u in (bob, charlie, diana):
                inv = client.post(
                    f"/api/v1/organisations/{org_id}/invitations",
                    headers=alice.headers,
                    json={"email": u.email, "role_name": "org_member"},
                )
                assert inv.status_code == 201
                raw_token = inv.json()["development_invitation_token"]
                acc = client.post(f"/api/v1/invitations/{raw_token}/accept", headers=u.headers)
                assert acc.status_code == 200

            proj_resp = client.post(
                f"/api/v1/organisations/{org_id}/projects",
                headers=alice.headers,
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

            assert (
                client.post(
                    f"/api/v1/projects/{proj_id}/members",
                    headers=alice.headers,
                    json={
                        "user_id": str(bob.user_id),
                        "role_name": "project_manager",
                        "responsibility_description": "Lead architect for payment rails.",
                    },
                ).status_code
                == 201
            )
            assert (
                client.post(
                    f"/api/v1/projects/{proj_id}/members",
                    headers=alice.headers,
                    json={
                        "user_id": str(charlie.user_id),
                        "role_name": "project_member",
                        "responsibility_description": "Incoming payments engineer.",
                    },
                ).status_code
                == 201
            )
            assert (
                client.post(
                    f"/api/v1/projects/{proj_id}/members",
                    headers=alice.headers,
                    json={
                        "user_id": str(diana.user_id),
                        "role_name": "reviewer",
                        "responsibility_description": "Compliance and risk auditor.",
                    },
                ).status_code
                == 201
            )

            # 2. Configure Transition Participants (Bob Departing -> Charlie Successor)
            tp_resp = client.put(
                f"/api/v1/projects/{proj_id}/transition",
                headers=alice.headers,
                json={
                    "departing_user_id": str(bob.user_id),
                    "successor_user_id": str(charlie.user_id),
                    "workflow_stage": "planning",
                    "handover_scope": "Handover of reconciliation services and payment engine.",
                    "source_scope": ["github:core-bank/payment-engine"],
                },
            )
            assert tp_resp.status_code == 200
            assert tp_resp.json()["departing_user"]["id"] == str(bob.user_id)
            assert tp_resp.json()["successor_user"]["id"] == str(charlie.user_id)

            # 3. Bob uploads critical documents (PDF + DOCX)
            pdf_bytes = _create_sample_pdf(
                "ADR-042: ISO 20022 Schema Validation",
                "Decision: Implement async validation using streaming parser.",
            )
            upload_pdf = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=bob.headers,
                files={"file": ("adr-042.pdf", pdf_bytes, "application/pdf")},
            )
            assert upload_pdf.status_code == 201
            pdf_item_id = upload_pdf.json()["evidence"]["id"]

            docx_bytes = _create_sample_docx(
                "Disaster Recovery Runbook",
                [
                    "Step 1: Failover active ledger cluster to secondary region.",
                    "Step 2: Verify queue replication lag remains under 50ms.",
                ],
            )
            upload_docx = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=bob.headers,
                files={
                    "file": (
                        "dr-runbook.docx",
                        docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
            assert upload_docx.status_code == 201

            # 4. Bob completes delegated GitHub OAuth, maps private repo, triggers sync
            start = client.post(
                f"/api/v1/organisations/{org_id}/integrations/github/oauth/start",
                headers=bob.headers,
                json={"display_name": "Core Bank GitHub"},
            )
            assert start.status_code == 200
            conn_id = start.json()["source_connection_id"]
            raw_state = parse_qs(urlparse(start.json()["authorisation_url"]).query)["state"][0]
            cb = client.get(
                "/api/v1/integrations/github/callback",
                headers=bob.headers,
                params={"code": "bob_code", "state": raw_state},
            )
            assert cb.status_code == 200

            map_resp = client.post(
                f"/api/v1/projects/{proj_id}/integrations/github/mappings",
                headers=bob.headers,
                json={
                    "source_connection_id": conn_id,
                    "owner": "core-bank",
                    "repo": "payment-engine",
                },
            )
            assert map_resp.status_code == 201
            mapping_id = map_resp.json()["id"]

            sync_resp = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{mapping_id}/sync",
                headers=bob.headers,
                json={"sync_mode": "initial"},
            )
            assert sync_resp.status_code == 202
            run_id = sync_resp.json()["sync_run"]["id"]

            # Drain ingestion + sync jobs via CompositeWorkerService
            storage = LocalPrivateStorageBackend(
                root_path=upload_tmp,
                file_encryption_key=ctx.settings.security.file_encryption_key.get_secret_value(),
            )
            token_key = ctx.settings.security.token_encryption_key.get_secret_value()
            worker = CompositeWorkerService(
                ingestion_worker=IngestionWorkerService(
                    session_factory=ctx.session_factory,
                    storage_backend=storage,
                    extraction_service=DocumentExtractionService(
                        ocr_service=_NoopOCR(),
                        ingestion_settings=ctx.settings.ingestion,
                    ),
                    ingestion_settings=ctx.settings.ingestion,
                    worker_id="comb-ingest",
                ),
                sync_worker=SourceSyncWorkerService(
                    session_factory=ctx.session_factory,
                    settings=ctx.settings,
                    token_encryption=LocalTokenEncryptionService(token_encryption_key=token_key),
                    http_transport=transport,
                    worker_id="comb-sync",
                ),
            )
            processed = worker.drain_pending_jobs()
            assert processed == 3

            run_detail = client.get(
                f"/api/v1/integrations/sync-runs/{run_id}",
                headers=bob.headers,
            )
            assert run_detail.status_code == 200
            assert run_detail.json()["status"] == SourceSyncRunStatus.SUCCEEDED.value

            # 5. Charlie queries Overview & Evidence, checking Project Membership != Source Access
            ov_charlie = client.get(
                f"/api/v1/projects/{proj_id}/overview",
                headers=charlie.headers,
            )
            assert ov_charlie.status_code == 200
            ov_c = ov_charlie.json()
            assert ov_c["project_summary"]["name"] == "Payment Gateway Modernization"
            assert ov_c["project_summary"]["departing_member"]["full_name"] == "Bob Departing"
            assert ov_c["project_summary"]["successor"]["full_name"] == "Charlie Successor"
            assert ov_c["connected_sources"]["total_sources"] == 1
            assert ov_c["connected_sources"]["health_status"] == "healthy"
            assert ov_c["knowledge_overview"]["availability"] == "available"
            assert len(ov_c["team_ownership"]) == 4
            # Charlie cannot see Bob's private GitHub records yet (only 2 uploaded docs)
            assert ov_c["evidence_overview"]["document_count"] == 2
            assert ov_c["evidence_overview"]["total_records"] == 2

            # Charlie CAN read uploaded PDF
            doc_resp = client.get(f"/api/v1/evidence/{pdf_item_id}", headers=charlie.headers)
            assert doc_resp.status_code == 200
            assert "adr-042" in doc_resp.json()["title"].lower()

            # Bob sees GitHub records
            bob_git = client.get(
                f"/api/v1/projects/{proj_id}/evidence?source_type=github",
                headers=bob.headers,
            )
            assert bob_git.status_code == 200
            assert bob_git.json()["total"] >= 1
            git_item_id = bob_git.json()["items"][0]["id"]

            # Charlie & Diana are DENIED access to Bob's private GitHub item!
            assert (
                client.get(f"/api/v1/evidence/{git_item_id}", headers=charlie.headers).status_code
                == 403
            )
            assert (
                client.get(f"/api/v1/evidence/{git_item_id}", headers=diana.headers).status_code
                == 403
            )

            # 6. Charlie authorizes his own delegated GitHub token & verifies repository access
            ch_start = client.post(
                f"/api/v1/organisations/{org_id}/integrations/github/oauth/start",
                headers=charlie.headers,
                json={"source_connection_id": conn_id},
            )
            assert ch_start.status_code == 200
            ch_state = parse_qs(urlparse(ch_start.json()["authorisation_url"]).query)["state"][0]
            ch_cb = client.get(
                "/api/v1/integrations/github/callback",
                headers=charlie.headers,
                params={"code": "charlie_code", "state": ch_state},
            )
            assert ch_cb.status_code == 200

            verify_resp = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{mapping_id}/verify-access",
                headers=charlie.headers,
                json={"source_connection_id": conn_id},
            )
            assert verify_resp.status_code == 200
            assert verify_resp.json()["verified"] is True

            # Now Charlie CAN inspect the GitHub evidence and sees all records in Overview!
            assert (
                client.get(f"/api/v1/evidence/{git_item_id}", headers=charlie.headers).status_code
                == 200
            )
            final_ov = client.get(
                f"/api/v1/projects/{proj_id}/overview",
                headers=charlie.headers,
            )
            assert final_ov.status_code == 200
            assert final_ov.json()["evidence_overview"]["document_count"] == 2
            assert final_ov.json()["evidence_overview"]["total_records"] >= 3

            # 7. Activity timeline includes project & transition events
            act_resp = client.get(
                f"/api/v1/projects/{proj_id}/activity",
                headers=charlie.headers,
            )
            assert act_resp.status_code == 200
            assert act_resp.json()["total"] >= 1
