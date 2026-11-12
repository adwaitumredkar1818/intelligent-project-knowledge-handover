"""End-to-end mocked Supabase Storage integration tests across API, worker, and ACLs."""

from __future__ import annotations

import hashlib
import io
import uuid

import docx
import httpx
import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.enums import (
    BackgroundJobStatus,
    EvidenceProcessingStatus,
    StorageProvider,
)
from app.models.evidence import EvidenceItem
from app.services.document_extraction import DocumentExtractionService
from app.services.ingestion_worker import IngestionWorkerService
from app.services.ocr import OCRPageRequest, OCRPageResult
from app.services.storage import (
    ENVELOPE_MAGIC,
    SUPABASE_KEY_ID,
    expected_envelope_size_bytes,
)
from app.services.storage_factory import build_storage_backend
from app.services.supabase_storage import SupabaseStorageBackend
from app.worker import build_worker_service
from tests.conftest import (
    invite_and_accept_member,
    isolated_auth_app,
    register_and_login_user,
)


class _DummyOCR:
    model_name = "dummy-ocr"

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


def _pdf_bytes(text: str) -> bytes:
    doc = pymupdf.Document()  # type: ignore[no-untyped-call]
    try:
        page = doc.new_page()
        page.insert_text((72, 72), text)
        return bytes(doc.tobytes())  # type: ignore[no-untyped-call]
    finally:
        doc.close()  # type: ignore[no-untyped-call]


def _docx_bytes(text: str) -> bytes:
    doc = docx.Document()
    doc.add_heading("Handover Architecture", level=1)
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_mock_supabase_storage_transport(
    store: dict[str, bytes],
    *,
    expected_service_key: str,
    bucket: str = "project-evidence",
) -> httpx.MockTransport:
    obj_prefix = f"/storage/v1/object/{bucket}/"
    info_prefix = f"/storage/v1/object/info/{bucket}/"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") == f"Bearer {expected_service_key}"
        assert request.headers.get("apikey") == expected_service_key
        path = request.url.path
        if request.method == "POST" and path.startswith(obj_prefix):
            key = path[len(obj_prefix) :]
            store[key] = request.content
            return httpx.Response(200, json={"Key": f"{bucket}/{key}"})
        if request.method == "GET" and path.startswith(info_prefix):
            key = path[len(info_prefix) :]
            if key in store:
                return httpx.Response(200, json={"name": key, "size": len(store[key])})
            return httpx.Response(404, json={"statusCode": "404", "error": "not_found"})
        if request.method == "GET" and path.startswith(obj_prefix):
            key = path[len(obj_prefix) :]
            if key in store:
                payload = store[key]
                return httpx.Response(
                    200,
                    content=payload,
                    headers={"Content-Length": str(len(payload))},
                )
            return httpx.Response(404, json={"statusCode": "404", "error": "not_found"})
        if request.method == "DELETE" and path.startswith(obj_prefix):
            key = path[len(obj_prefix) :]
            existed = store.pop(key, None) is not None
            return (
                httpx.Response(200, json={"message": "Deleted"})
                if existed
                else httpx.Response(404, json={"statusCode": "404", "error": "not_found"})
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_supabase_storage_api_worker_acl_and_cleanup_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote_objects: dict[str, bytes] = {}
    service_key = "sb-service-role-key-secret-value"
    transport = _make_mock_supabase_storage_transport(
        remote_objects,
        expected_service_key=service_key,
    )

    with isolated_auth_app(
        monkeypatch,
        storage_provider="supabase_storage",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key=service_key,
        supabase_storage_bucket="project-evidence",
        supabase_storage_retry_backoff_seconds=0.0,
    ) as ctx:
        ctx.app.state.supabase_http_transport = transport

        worker_bundle, worker_engine = build_worker_service(
            ctx.settings,
            worker_id="supabase-worker-check",
            storage_http_transport=transport,
        )
        worker_engine.dispose()
        assert isinstance(worker_bundle.ingestion_worker._storage, SupabaseStorageBackend)

        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client,
                email="sb-owner@example.com",
                full_name="Storage Owner",
            )
            member = register_and_login_user(
                client,
                email="sb-member@example.com",
                full_name="Project Member",
            )
            outsider = register_and_login_user(
                client,
                email="sb-outsider@example.com",
                full_name="Tenant Outsider",
            )

            org_id = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "Supabase Storage Org"},
            ).json()["id"]
            invite_and_accept_member(
                client,
                organisation_id=org_id,
                inviter_headers=owner.headers,
                invitee=member,
                role_name="org_member",
            )
            proj_id = client.post(
                f"/api/v1/organisations/{org_id}/projects",
                headers=owner.headers,
                json={
                    "name": "Supabase Evidence Project",
                    "status": "active",
                    "visibility": "private",
                },
            ).json()["id"]
            add_resp = client.post(
                f"/api/v1/projects/{proj_id}/members",
                headers=owner.headers,
                json={"user_id": str(member.user_id), "role_name": "project_member"},
            )
            assert add_resp.status_code == 201

            pdf_raw = _pdf_bytes("Supabase encrypted evidence text content.")
            up_pdf = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={"file": ("decision.pdf", pdf_raw, "application/pdf")},
            )
            assert up_pdf.status_code == 201
            pdf_body = up_pdf.json()
            pdf_id = pdf_body["evidence"]["id"]
            assert pdf_body["evidence"]["file_size_bytes"] == len(pdf_raw)
            assert pdf_body["evidence"]["content_hash"] == hashlib.sha256(pdf_raw).hexdigest()
            assert "storage_object_key" not in pdf_body["evidence"]
            assert "storage_provider" not in pdf_body["evidence"]
            assert "project-evidence" not in up_pdf.text

            docx_raw = _docx_bytes("Supabase DOCX payload body.")
            up_docx = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={
                    "file": (
                        "notes.docx",
                        docx_raw,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
            assert up_docx.status_code == 201
            docx_id = up_docx.json()["evidence"]["id"]

            assert len(remote_objects) == 2
            with ctx.session_factory() as session:
                ev_row = session.get(EvidenceItem, uuid.UUID(pdf_id))
                assert ev_row is not None
                assert ev_row.storage_provider == StorageProvider.SUPABASE_STORAGE.value
                assert ev_row.encryption_key_id == SUPABASE_KEY_ID
                assert ev_row.storage_object_key is not None
                pdf_storage_key = ev_row.storage_object_key
                assert ev_row.file_size_bytes == len(pdf_raw)

            encrypted_blob = remote_objects[pdf_storage_key]
            assert encrypted_blob.startswith(ENVELOPE_MAGIC)
            assert len(encrypted_blob) == expected_envelope_size_bytes(len(pdf_raw))
            assert b"%PDF-" not in encrypted_blob

            # Background worker decrypts from Supabase Storage and extracts content
            worker = IngestionWorkerService(
                session_factory=ctx.session_factory,
                storage_backend=build_storage_backend(ctx.settings, http_transport=transport),
                extraction_service=DocumentExtractionService(
                    ocr_service=_DummyOCR(),
                    ingestion_settings=ctx.settings.ingestion,
                ),
                ingestion_settings=ctx.settings.ingestion,
                worker_id="supabase-test-worker",
            )
            assert worker.drain_pending_jobs(max_jobs=10) == 2

            detail = client.get(f"/api/v1/evidence/{pdf_id}", headers=owner.headers)
            assert detail.status_code == 200
            detail_json = detail.json()
            assert detail_json["processing_status"] == EvidenceProcessingStatus.EXTRACTED.value
            assert detail_json["download_url"] == f"/api/v1/evidence/{pdf_id}/download"
            assert "signedURL" not in detail.text
            assert detail_json["latest_job"]["status"] == BackgroundJobStatus.SUCCEEDED.value
            assert "Supabase encrypted evidence text content." in (
                detail_json["extracted_content"]["extracted_text"]
            )

            # Backend-mediated download returns exact decrypted bytes
            dl = client.get(f"/api/v1/evidence/{pdf_id}/download", headers=owner.headers)
            assert dl.status_code == 200
            assert dl.headers["content-type"] == "application/pdf"
            assert dl.content == pdf_raw

            # Tenant outsider and ACL-restricted member cannot download
            outsider_dl = client.get(
                f"/api/v1/evidence/{pdf_id}/download",
                headers=outsider.headers,
            )
            assert outsider_dl.status_code == 404

            with ctx.session_factory() as session:
                ev_row = session.get(EvidenceItem, uuid.UUID(pdf_id))
                assert ev_row is not None
                ev_row.acl_scope = "source_restricted"
                session.commit()

            denied_dl = client.get(f"/api/v1/evidence/{pdf_id}/download", headers=member.headers)
            assert denied_dl.status_code == 403
            assert denied_dl.json()["error"]["code"] == "SOURCE_ACCESS_DENIED"

            # Reprocess fails with 422 STORAGE_OBJECT_MISSING if remote object vanished,
            # and succeeds when object exists in Supabase Storage
            with ctx.session_factory() as session:
                docx_row = session.get(EvidenceItem, uuid.UUID(docx_id))
                assert docx_row is not None
                docx_key = docx_row.storage_object_key
                assert docx_key is not None
                docx_blob = remote_objects.pop(docx_key)
                docx_row.processing_status = EvidenceProcessingStatus.FAILED.value
                session.commit()

            missing_reprocess = client.post(
                f"/api/v1/evidence/{docx_id}/reprocess",
                headers=owner.headers,
            )
            assert missing_reprocess.status_code == 422
            assert missing_reprocess.json()["error"]["code"] == "STORAGE_OBJECT_MISSING"

            remote_objects[docx_key] = docx_blob
            ok_reprocess = client.post(
                f"/api/v1/evidence/{docx_id}/reprocess",
                headers=owner.headers,
            )
            assert ok_reprocess.status_code == 202
            assert worker.drain_pending_jobs(max_jobs=10) == 1

            # Deletion removes object from Supabase Storage and blocks future download
            del_resp = client.delete(f"/api/v1/evidence/{pdf_id}", headers=owner.headers)
            assert del_resp.status_code == 204
            assert pdf_storage_key not in remote_objects
            deleted_dl = client.get(
                f"/api/v1/evidence/{pdf_id}/download",
                headers=owner.headers,
            )
            assert deleted_dl.status_code == 404


def test_supabase_storage_upload_rolls_back_remote_object_on_db_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote_objects: dict[str, bytes] = {}
    service_key = "sb-service-role-key-secret-value"
    transport = _make_mock_supabase_storage_transport(
        remote_objects,
        expected_service_key=service_key,
    )

    with isolated_auth_app(
        monkeypatch,
        storage_provider="supabase_storage",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key=service_key,
        supabase_storage_retry_backoff_seconds=0.0,
    ) as ctx:
        ctx.app.state.supabase_http_transport = transport
        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client,
                email="sb-rollback@example.com",
                full_name="Rollback Owner",
            )
            org_id = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "Rollback Org"},
            ).json()["id"]
            proj_id = client.post(
                f"/api/v1/organisations/{org_id}/projects",
                headers=owner.headers,
                json={"name": "Rollback Project", "status": "active", "visibility": "private"},
            ).json()["id"]

            def _boom(*args: object, **kwargs: object) -> object:
                raise RuntimeError("Simulated DB failure after remote upload")

            monkeypatch.setattr("app.repositories.job.BackgroundJobRepository.create_job", _boom)

            with pytest.raises(RuntimeError, match="Simulated DB failure"):
                client.post(
                    f"/api/v1/projects/{proj_id}/evidence/documents",
                    headers=owner.headers,
                    files={"file": ("fail.pdf", _pdf_bytes("Rollback test"), "application/pdf")},
                )

            assert remote_objects == {}
            with ctx.session_factory() as session:
                assert session.execute(select(EvidenceItem)).scalars().all() == []


def test_supabase_storage_upload_rejects_mismatched_key_without_db_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_key = "sb-service-role-key-secret-value"

    def bad_key_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") == f"Bearer {service_key}"
        return httpx.Response(200, json={"Key": "project-evidence/other/mismatch.enc"})

    with isolated_auth_app(
        monkeypatch,
        storage_provider="supabase_storage",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key=service_key,
        supabase_storage_retry_backoff_seconds=0.0,
    ) as ctx:
        ctx.app.state.supabase_http_transport = httpx.MockTransport(bad_key_handler)
        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client,
                email="sb-badkey@example.com",
                full_name="BadKey Owner",
            )
            org_id = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "Integrity Org"},
            ).json()["id"]
            proj_id = client.post(
                f"/api/v1/organisations/{org_id}/projects",
                headers=owner.headers,
                json={"name": "Integrity Project", "status": "active", "visibility": "private"},
            ).json()["id"]

            resp = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={"file": ("badkey.pdf", _pdf_bytes("Integrity fail"), "application/pdf")},
            )
            assert resp.status_code == 503
            assert resp.json()["error"]["code"] == "STORAGE_INTEGRITY_FAILED"

            with ctx.session_factory() as session:
                assert session.execute(select(EvidenceItem)).scalars().all() == []
