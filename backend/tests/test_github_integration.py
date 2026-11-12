"""Integration tests for delegated GitHub discovery, sync, idempotency, and retry logic."""

from __future__ import annotations

import base64
import io
import uuid
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import docx
import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.security import utc_now
from app.models.enums import (
    BackgroundJobStatus,
    EvidenceProcessingStatus,
    SourceSyncRunStatus,
)
from app.models.job import BackgroundJob
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


def _docx_bytes() -> bytes:
    d = docx.Document()
    d.add_paragraph("Uploaded manual architecture handover note.")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def test_github_discovery_mapping_sync_idempotency_retry_and_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    upload_tmp = tmp_path / "gh_sync_uploads"
    state: dict[str, object] = {
        "issue_body": "See #100 for database pool background. Needs failover verification.",
        "issues_etag": '"etag-v1"',
        "return_304": False,
        "return_429_once": False,
        "drop_issue_101": False,
    }
    gh_token = "gho_delegated_sync_token_001"

    def b64(text: str) -> str:
        return base64.b64encode(text.encode("utf-8")).decode("ascii")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/login/oauth/access_token":
            return httpx.Response(
                200,
                json={
                    "access_token": gh_token,
                    "token_type": "bearer",
                    "scope": "repo read:user user:email",
                },
            )
        assert request.headers.get("Authorization") == f"Bearer {gh_token}"
        if path == "/user":
            return httpx.Response(
                200,
                json={"id": 8801, "login": "gh-maintainer", "email": "gh@example.com"},
            )
        if path == "/user/repos":
            page = int(request.url.params.get("page", "1"))
            if page == 1:
                return httpx.Response(
                    200,
                    headers={"Link": '<https://api.github.com/user/repos?page=2>; rel="next"'},
                    json=[
                        {
                            "id": 90001,
                            "name": "core-platform",
                            "full_name": "acme-eng/core-platform",
                            "private": True,
                            "visibility": "private",
                            "default_branch": "main",
                            "description": "Core handover API repository",
                            "html_url": "https://github.com/acme-eng/core-platform",
                            "updated_at": "2026-11-01T10:00:00Z",
                            "owner": {"login": "acme-eng"},
                            "permissions": {"pull": True, "push": True},
                        }
                    ],
                )
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 90002,
                        "name": "public-sdk",
                        "full_name": "acme-eng/public-sdk",
                        "private": False,
                        "visibility": "public",
                        "default_branch": "main",
                        "html_url": "https://github.com/acme-eng/public-sdk",
                        "updated_at": "2026-10-20T09:00:00Z",
                        "owner": {"login": "acme-eng"},
                        "permissions": {"pull": True},
                    }
                ],
            )
        if path == "/repos/acme-eng/core-platform":
            return httpx.Response(
                200,
                json={
                    "id": 90001,
                    "name": "core-platform",
                    "full_name": "acme-eng/core-platform",
                    "private": True,
                    "visibility": "private",
                    "default_branch": "main",
                    "description": "Core handover API repository",
                    "html_url": "https://github.com/acme-eng/core-platform",
                    "updated_at": "2026-11-02T12:00:00Z",
                    "owner": {"login": "acme-eng"},
                    "permissions": {"pull": True, "push": True},
                },
            )
        if path == "/repos/acme-eng/core-platform/issues":
            if state["return_429_once"]:
                state["return_429_once"] = False
                return httpx.Response(
                    429,
                    headers={"Retry-After": "2"},
                    json={"message": "API rate limit exceeded"},
                )
            if state["return_304"] and request.headers.get("If-None-Match") == '"etag-v1"':
                return httpx.Response(304, headers={"ETag": '"etag-v1"'})
            items: list[dict[str, object]] = []
            if not state["drop_issue_101"]:
                items.append(
                    {
                        "number": 101,
                        "title": "PostgreSQL connection pool exhaustion under burst load",
                        "state": "open",
                        "body": state["issue_body"],
                        "html_url": "https://github.com/acme-eng/core-platform/issues/101",
                        "created_at": "2026-10-15T08:00:00Z",
                        "updated_at": "2026-11-01T14:30:00Z",
                        "user": {"login": "dev-jane"},
                        "assignees": [{"login": "gh-maintainer"}],
                        "labels": [{"name": "bug"}, {"name": "database"}],
                        "milestone": {"title": "Handover-M1"},
                    }
                )
            items.append(
                {
                    "number": 102,
                    "title": "Implement OAuth token encryption service",
                    "state": "closed",
                    "body": "Closes #101 after testing HKDF isolation.",
                    "html_url": "https://github.com/acme-eng/core-platform/pull/102",
                    "created_at": "2026-10-20T09:00:00Z",
                    "updated_at": "2026-11-02T11:00:00Z",
                    "user": {"login": "gh-maintainer"},
                    "labels": [{"name": "security"}],
                    "pull_request": {"url": "https://api.github.com/repos/a/b/pulls/102"},
                }
            )
            return httpx.Response(
                200,
                headers={"ETag": str(state["issues_etag"])},
                json=items,
            )
        if path == "/repos/acme-eng/core-platform/issues/101/comments":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 5001,
                        "user": {"login": "ops-bob"},
                        "created_at": "2026-10-16T10:00:00Z",
                        "body": "mitigated via max_overflow=10 references #100",
                    }
                ],
            )
        if path == "/repos/acme-eng/core-platform/issues/102/comments":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 5002,
                        "user": {"login": "reviewer-carol"},
                        "created_at": "2026-11-02T10:15:00Z",
                        "body": "LGTM once tested cleanly.",
                    }
                ],
            )
        if path == "/repos/acme-eng/core-platform/pulls/102":
            return httpx.Response(
                200,
                json={
                    "number": 102,
                    "merged": True,
                    "merged_at": "2026-11-02T11:00:00Z",
                    "head": {"ref": "feat/token-encryption"},
                    "base": {"ref": "main"},
                },
            )
        if path == "/repos/acme-eng/core-platform/pulls/102/reviews":
            return httpx.Response(
                200,
                json=[
                    {
                        "user": {"login": "reviewer-carol"},
                        "state": "APPROVED",
                        "body": "Verified HKDF key separation.",
                    }
                ],
            )
        if path == "/repos/acme-eng/core-platform/pulls/102/comments":
            return httpx.Response(
                200,
                json=[
                    {
                        "user": {"login": "reviewer-carol"},
                        "path": "backend/app/services/token_encryption.py",
                        "body": "Ensure AAD includes token_kind.",
                    }
                ],
            )
        if path == "/repos/acme-eng/core-platform/pulls/102/files":
            return httpx.Response(
                200,
                json=[
                    {
                        "filename": "backend/app/services/token_encryption.py",
                        "status": "added",
                        "additions": 176,
                        "deletions": 0,
                        "changes": 176,
                    }
                ],
            )
        if path == "/repos/acme-eng/core-platform/commits":
            if state["return_304"]:
                return httpx.Response(304, headers={"ETag": '"commits-etag-v1"'})
            return httpx.Response(
                200,
                headers={"ETag": '"commits-etag-v1"'},
                json=[
                    {
                        "sha": "abc123def4567890",
                        "html_url": "https://github.com/acme-eng/core-platform/commit/abc123def4567890",
                        "author": {"login": "gh-maintainer"},
                        "commit": {
                            "author": {
                                "name": "GH Maintainer",
                                "email": "gh@example.com",
                                "date": "2026-11-02T11:00:00Z",
                            },
                            "message": "Add encrypted OAuth token store\n\nFixes #101 cleanly.",
                        },
                    }
                ],
            )
        if path == "/repos/acme-eng/core-platform/readme":
            return httpx.Response(
                200,
                json={
                    "path": "README.md",
                    "sha": "readme-sha-1",
                    "html_url": "https://github.com/acme-eng/core-platform/blob/main/README.md",
                    "encoding": "base64",
                    "size": 45,
                    "content": b64("# Core Platform\n\nPrimary handover service docs."),
                },
            )
        if path == "/repos/acme-eng/core-platform/git/trees/main":
            return httpx.Response(
                200,
                json={
                    "tree": [
                        {"path": "docs/adr-001.md", "type": "blob", "size": 120},
                        {"path": "src/main.py", "type": "blob", "size": 400},
                    ]
                },
            )
        if path == "/repos/acme-eng/core-platform/contents/docs/adr-001.md":
            return httpx.Response(
                200,
                json={
                    "path": "docs/adr-001.md",
                    "sha": "adr-sha-1",
                    "html_url": "https://github.com/acme-eng/core-platform/blob/main/docs/adr-001.md",
                    "encoding": "base64",
                    "size": 68,
                    "content": b64("# ADR-001: PostgreSQL Canonical\nKeep state in PostgreSQL."),
                },
            )
        if path == "/repos/acme-eng/core-platform/discussions":
            return httpx.Response(404, json={"message": "Not Found"})
        return httpx.Response(404, json={"message": f"Unhandled {path}"})

    transport = httpx.MockTransport(handler)
    with isolated_auth_app(
        monkeypatch,
        upload_storage_path=upload_tmp,
        github_enabled=True,
        github_client_id="gh-cid",
        github_client_secret="gh-csec-secret-value",
        worker_max_attempts=2,
        worker_retry_base_seconds=2,
    ) as ctx:
        ctx.app.state.integration_http_transport = transport
        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client,
                email="gh-owner@example.com",
                full_name="GH Owner",
            )
            org_id = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "GitHub Org"},
            ).json()["id"]
            proj_id = client.post(
                f"/api/v1/organisations/{org_id}/projects",
                headers=owner.headers,
                json={"name": "GitHub Project", "status": "active", "visibility": "private"},
            ).json()["id"]

            # Upload existing document in same project (must never be disturbed by GitHub sync)
            doc_up = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={
                    "file": (
                        "handover.docx",
                        _docx_bytes(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
            assert doc_up.status_code == 201
            uploaded_doc_id = doc_up.json()["evidence"]["id"]

            # OAuth flow
            start = client.post(
                f"/api/v1/organisations/{org_id}/integrations/github/oauth/start",
                headers=owner.headers,
                json={"display_name": "Acme GitHub"},
            ).json()
            conn_id = start["source_connection_id"]
            raw_state = parse_qs(urlparse(start["authorisation_url"]).query)["state"][0]
            cb = client.get(
                "/api/v1/integrations/github/callback",
                headers=owner.headers,
                params={"code": "gh_code_ok", "state": raw_state},
            )
            assert cb.status_code == 200

            # Paginated repository discovery
            p1 = client.get(
                f"/api/v1/integrations/connections/{conn_id}/github/repositories",
                headers=owner.headers,
                params={"page": 1, "per_page": 1},
            )
            assert p1.status_code == 200
            assert p1.json()["has_next_page"] is True
            assert p1.json()["items"][0]["full_name"] == "acme-eng/core-platform"

            p2 = client.get(
                f"/api/v1/integrations/connections/{conn_id}/github/repositories",
                headers=owner.headers,
                params={"page": 2, "per_page": 2},
            )
            assert p2.status_code == 200
            assert p2.json()["has_next_page"] is False
            assert p2.json()["items"][0]["full_name"] == "acme-eng/public-sdk"

            # Explicit repo mapping + duplicate prevention
            m_resp = client.post(
                f"/api/v1/projects/{proj_id}/integrations/github/mappings",
                headers=owner.headers,
                json={
                    "source_connection_id": conn_id,
                    "owner": "acme-eng",
                    "repo": "core-platform",
                },
            )
            assert m_resp.status_code == 201
            mapping_id = m_resp.json()["id"]
            assert m_resp.json()["provider_visibility"] == "private"
            assert m_resp.json()["access_policy"]["visibility_policy"] == "verified_source_acl"

            dup_m = client.post(
                f"/api/v1/projects/{proj_id}/integrations/github/mappings",
                headers=owner.headers,
                json={
                    "source_connection_id": conn_id,
                    "owner": "acme-eng",
                    "repo": "core-platform",
                },
            )
            assert dup_m.status_code == 409
            assert dup_m.json()["error"]["code"] == "SOURCE_MAPPING_ALREADY_EXISTS"

            # Queue initial sync + drain composite worker (processes DOCX + GitHub sync)
            sync_1 = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{mapping_id}/sync",
                headers=owner.headers,
                json={"sync_mode": "initial"},
            )
            assert sync_1.status_code == 202
            run_1_id = sync_1.json()["sync_run"]["id"]

            storage = LocalPrivateStorageBackend(
                root_path=upload_tmp,
                file_encryption_key=ctx.settings.security.file_encryption_key.get_secret_value(),
            )
            token_key = ctx.settings.security.token_encryption_key.get_secret_value()
            comp_worker = CompositeWorkerService(
                ingestion_worker=IngestionWorkerService(
                    session_factory=ctx.session_factory,
                    storage_backend=storage,
                    extraction_service=DocumentExtractionService(
                        ocr_service=_NoopOCR(),
                        ingestion_settings=ctx.settings.ingestion,
                    ),
                    ingestion_settings=ctx.settings.ingestion,
                    worker_id="comp-ingest",
                ),
                sync_worker=SourceSyncWorkerService(
                    session_factory=ctx.session_factory,
                    settings=ctx.settings,
                    token_encryption=LocalTokenEncryptionService(token_encryption_key=token_key),
                    http_transport=transport,
                    worker_id="comp-sync",
                ),
            )
            processed = comp_worker.drain_pending_jobs()
            assert processed == 2

            # Check sync metrics: repo overview + issue 101 + pr 102 + commit + README + ADR = 6
            run_1 = client.get(
                f"/api/v1/integrations/sync-runs/{run_1_id}",
                headers=owner.headers,
            ).json()
            assert run_1["status"] == SourceSyncRunStatus.SUCCEEDED.value
            assert run_1["items_discovered"] == 6
            assert run_1["items_created"] == 6
            assert run_1["items_updated"] == 0
            assert run_1["items_failed"] == 0

            # Inspect synced GitHub items + provenance + untouched DOCX upload
            ev_list = client.get(
                f"/api/v1/projects/{proj_id}/evidence",
                headers=owner.headers,
                params={"limit": 50},
            ).json()
            assert ev_list["total"] == 7  # 1 docx + 6 github items
            by_ext = {item["source_external_id"]: item for item in ev_list["items"]}
            issue_item = by_ext["github:90001:issue:101"]
            pr_item = by_ext["github:90001:pr:102"]
            adr_item = by_ext["github:90001:doc:docs/adr-001.md"]

            assert issue_item["source_type"] == "github"
            assert issue_item["source_provider"] == "github"
            assert (
                issue_item["source_url"]
                == "https://github.com/acme-eng/core-platform/issues/101"
            )
            assert issue_item["source_author_identity"] == "dev-jane"
            assert issue_item["source_created_at"] is not None
            assert issue_item["source_updated_at"] is not None
            assert issue_item["extracted_at"] is not None
            assert issue_item["last_synced_at"] is not None
            assert len(issue_item["content_hash"]) == 64
            assert issue_item["metadata_json"]["referenced_issue_numbers"] == [100]

            assert pr_item["metadata_json"]["merged"] is True
            assert pr_item["metadata_json"]["referenced_issue_numbers"] == [101]
            assert pr_item["metadata_json"]["changed_files"][0]["filename"] == (
                "backend/app/services/token_encryption.py"
            )

            pr_detail = client.get(
                f"/api/v1/evidence/{pr_item['id']}",
                headers=owner.headers,
            ).json()
            assert (
                "Verified HKDF key separation."
                in pr_detail["extracted_content"]["extracted_text"]
            )
            assert len(pr_detail["extracted_content"]["pages"]) == 3

            adr_detail = client.get(
                f"/api/v1/evidence/{adr_item['id']}",
                headers=owner.headers,
            ).json()
            assert "Keep state in PostgreSQL." in adr_detail["extracted_content"]["extracted_text"]

            doc_detail = client.get(
                f"/api/v1/evidence/{uploaded_doc_id}",
                headers=owner.headers,
            ).json()
            assert doc_detail["processing_status"] == EvidenceProcessingStatus.EXTRACTED.value
            assert doc_detail["source_type"] == "document_upload"

            # 2. Incremental ETag 304 Not Modified -> unchanged counts & identical UUIDs
            state["return_304"] = True
            sync_2 = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{mapping_id}/sync",
                headers=owner.headers,
                json={"sync_mode": "incremental"},
            ).json()
            assert comp_worker.sync_worker.process_next_job() is True
            run_2 = client.get(
                f"/api/v1/integrations/sync-runs/{sync_2['sync_run']['id']}",
                headers=owner.headers,
            ).json()
            assert run_2["status"] == SourceSyncRunStatus.SUCCEEDED.value
            assert run_2["items_created"] == 0
            assert run_2["items_updated"] == 0
            assert run_2["items_unchanged"] == 3  # repo overview + README + ADR

            # 3. Content modification updates existing UUID in place
            state["return_304"] = False
            state["issues_etag"] = '"etag-v2"'
            state["issue_body"] = "UPDATED body mentioning new PgBouncer fix (#100)."
            sync_3 = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{mapping_id}/sync",
                headers=owner.headers,
                json={"sync_mode": "manual"},
            ).json()
            assert comp_worker.sync_worker.process_next_job() is True
            run_3 = client.get(
                f"/api/v1/integrations/sync-runs/{sync_3['sync_run']['id']}",
                headers=owner.headers,
            ).json()
            assert run_3["items_updated"] == 1
            updated_issue = client.get(
                f"/api/v1/evidence/{issue_item['id']}",
                headers=owner.headers,
            ).json()
            assert updated_issue["id"] == issue_item["id"]
            assert updated_issue["content_hash"] != issue_item["content_hash"]
            assert "PgBouncer fix" in updated_issue["extracted_content"]["extracted_text"]

            # 4. Rate limit (429) retries safely WITHOUT deleting items; next manual snapshot
            #    genuinely missing Issue #101 flags it inaccessible_or_deleted cleanly!
            state["return_429_once"] = True
            state["drop_issue_101"] = True
            sync_4 = client.post(
                f"/api/v1/projects/{proj_id}/integrations/mappings/{mapping_id}/sync",
                headers=owner.headers,
                json={"sync_mode": "manual"},
            ).json()
            run_4_id = sync_4["sync_run"]["id"]
            job_4_id = uuid.UUID(sync_4["job"]["id"])

            # Attempt 1 hits 429 Retry-After=2 -> queued retry, issue #101 untouched
            assert comp_worker.sync_worker.process_next_job() is True
            mid_run = client.get(
                f"/api/v1/integrations/sync-runs/{run_4_id}",
                headers=owner.headers,
            ).json()
            assert mid_run["status"] == SourceSyncRunStatus.QUEUED.value
            assert mid_run["error_code"] == "GITHUB_RATE_LIMITED"

            with ctx.session_factory() as session:
                j4 = session.get(BackgroundJob, job_4_id)
                assert j4 is not None
                assert j4.status == BackgroundJobStatus.QUEUED.value
                assert j4.next_retry_at is not None
                j4.next_retry_at = utc_now() - timedelta(seconds=1)
                session.commit()

            # Attempt 2 succeeds with Issue #101 deleted -> reconciled & marked partial
            assert comp_worker.sync_worker.process_next_job() is True
            final_run = client.get(
                f"/api/v1/integrations/sync-runs/{run_4_id}",
                headers=owner.headers,
            ).json()
            assert final_run["status"] == SourceSyncRunStatus.PARTIAL.value
            assert final_run["items_inaccessible"] == 1

            deleted_issue = client.get(
                f"/api/v1/evidence/{issue_item['id']}",
                headers=owner.headers,
            ).json()
            assert (
                deleted_issue["metadata_json"]["source_item_state"] == "inaccessible_or_deleted"
            )
            assert (
                deleted_issue["processing_status"]
                == EvidenceProcessingStatus.PARTIALLY_EXTRACTED.value
            )
