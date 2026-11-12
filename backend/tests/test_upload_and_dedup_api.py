"""API integration tests for document upload validation, private storage, and deduplication."""

from __future__ import annotations

import hashlib
import io
import uuid
import zipfile
from pathlib import Path

import docx
import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.evidence import EvidenceItem
from tests.conftest import isolated_auth_app, register_and_login_user


def _build_pdf_bytes(*pages_text: str) -> bytes:
    doc = pymupdf.Document()  # type: ignore[no-untyped-call]
    try:
        for text_line in pages_text:
            page = doc.new_page()
            page.insert_text((72, 72), text_line)
        return bytes(doc.tobytes())  # type: ignore[no-untyped-call]
    finally:
        doc.close()  # type: ignore[no-untyped-call]


def _build_docx_bytes(title_text: str, body_text: str) -> bytes:
    document = docx.Document()
    document.add_heading(title_text, level=1)
    document.add_paragraph(body_text)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def _create_org_and_project(
    client: TestClient,
    *,
    headers: dict[str, str],
    org_name: str,
    project_name: str,
) -> tuple[str, str]:
    org_resp = client.post("/api/v1/organisations", headers=headers, json={"name": org_name})
    assert org_resp.status_code == 201
    org_id = str(org_resp.json()["id"])

    proj_resp = client.post(
        f"/api/v1/organisations/{org_id}/projects",
        headers=headers,
        json={"name": project_name, "status": "active", "visibility": "private"},
    )
    assert proj_resp.status_code == 201
    return org_id, str(proj_resp.json()["id"])


def test_upload_valid_pdf_and_docx_and_hide_storage_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    upload_dir = tmp_path / "private_uploads"
    with isolated_auth_app(monkeypatch, upload_storage_path=upload_dir) as ctx:
        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client,
                email="ev-uploader@example.com",
                full_name="Evidence Uploader",
            )
            org_id, proj_id = _create_org_and_project(
                client,
                headers=owner.headers,
                org_name="Upload Org",
                project_name="Core Migration",
            )

            pdf_bytes = _build_pdf_bytes("Architecture decision record 001.")
            pdf_sha = hashlib.sha256(pdf_bytes).hexdigest()
            pdf_resp = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={"file": ("adr-001.pdf", pdf_bytes, "application/pdf")},
            )
            assert pdf_resp.status_code == 201
            body = pdf_resp.json()
            assert body["duplicate_detected"] is False
            ev = body["evidence"]
            assert ev["organisation_id"] == org_id
            assert ev["project_id"] == proj_id
            assert ev["category"] == "pdf_document"
            assert ev["content_hash"] == pdf_sha
            assert ev["processing_status"] == "queued"
            assert ev["page_count"] == 1
            assert ev["source_type"] == "document_upload"
            assert body["job"]["status"] == "queued"
            # Storage internal location & host paths must never appear in API payload
            assert "storage_object_key" not in ev
            assert "storage_provider" not in ev
            assert "encryption_key_id" not in ev
            assert str(upload_dir) not in pdf_resp.text

            docx_bytes = _build_docx_bytes("Runbook", "Restart worker safely.")
            docx_resp = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={
                    "file": (
                        "runbook.docx",
                        docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
            assert docx_resp.status_code == 201
            assert docx_resp.json()["evidence"]["category"] == "docx_document"

            # Verify stored object on disk is encrypted (no raw PDF header)
            enc_files = list(upload_dir.rglob("*.enc"))
            assert len(enc_files) == 2
            for enc_path in enc_files:
                assert b"%PDF-" not in enc_path.read_bytes()

            with ctx.session_factory() as session:
                audit_events = list(
                    session.execute(
                        select(AuditLog).where(AuditLog.event_type == "evidence.uploaded")
                    )
                    .scalars()
                    .all()
                )
                assert len(audit_events) == 2


def test_upload_validation_rejects_malicious_spoofed_and_oversized_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    upload_dir = tmp_path / "private_uploads"
    with isolated_auth_app(
        monkeypatch,
        upload_storage_path=upload_dir,
        max_upload_size_mb=1,
        max_document_pages=2,
    ) as ctx:
        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client,
                email="sec-uploader@example.com",
                full_name="Security Uploader",
            )
            _, proj_id = _create_org_and_project(
                client,
                headers=owner.headers,
                org_name="Validation Org",
                project_name="Security Checks",
            )

            valid_pdf = _build_pdf_bytes("Valid one page document")

            # 1. Unauthenticated upload rejected
            unauth = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                files={"file": ("doc.pdf", valid_pdf, "application/pdf")},
            )
            assert unauth.status_code == 401

            # 2. Disallowed extension (.exe)
            bad_ext = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={"file": ("payload.exe", b"MZ\x90\x00", "application/octet-stream")},
            )
            assert bad_ext.status_code == 415

            # 3. Spoofed MIME with executable bytes claiming application/pdf
            spoofed_pdf = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={"file": ("fake.pdf", b"MZ\x90\x00not-a-pdf", "application/pdf")},
            )
            assert spoofed_pdf.status_code == 415
            assert spoofed_pdf.json()["error"]["code"] == "INVALID_FILE_SIGNATURE"

            # 4. Wrong MIME type even with PDF magic bytes
            wrong_mime = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={"file": ("notes.pdf", valid_pdf, "text/plain")},
            )
            assert wrong_mime.status_code == 415

            # 5. Plain zip renamed to .docx without word/document.xml
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                zf.writestr("hello.txt", "not a docx")
            fake_docx = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={
                    "file": (
                        "fake.docx",
                        zip_buf.getvalue(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
            assert fake_docx.status_code == 415
            assert fake_docx.json()["error"]["code"] == "INVALID_FILE_SIGNATURE"

            # 6. Empty 0-byte PDF
            empty_pdf = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={"file": ("empty.pdf", b"", "application/pdf")},
            )
            assert empty_pdf.status_code == 400
            assert empty_pdf.json()["error"]["code"] == "EMPTY_FILE"

            # 7. Corrupt PDF payload with %PDF- prefix
            corrupt_pdf = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={
                    "file": (
                        "corrupt.pdf",
                        b"%PDF-1.7\ngarbage-corrupt-body",
                        "application/pdf",
                    )
                },
            )
            assert corrupt_pdf.status_code == 422
            assert corrupt_pdf.json()["error"]["code"] == "MALFORMED_PDF"

            # 8. Exceeding configured page limit (3 pages vs max_document_pages=2)
            three_page_pdf = _build_pdf_bytes("P1", "P2", "P3")
            page_flood = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={"file": ("many.pdf", three_page_pdf, "application/pdf")},
            )
            assert page_flood.status_code == 422
            assert page_flood.json()["error"]["code"] == "PDF_PAGE_LIMIT_EXCEEDED"

            # 9. Exceeding configured size limit (> 1 MB)
            oversized = b"%PDF-1.7\n" + (b"A" * (1024 * 1024 + 128))
            too_big = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={"file": ("huge.pdf", oversized, "application/pdf")},
            )
            assert too_big.status_code == 413
            assert too_big.json()["error"]["code"] == "FILE_TOO_LARGE"

            # Confirm zero invalid uploads were written to disk or DB
            assert list(upload_dir.rglob("*.enc")) == []


def test_project_scoped_deduplication_and_reupload_after_deletion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    upload_dir = tmp_path / "dedup_uploads"
    with isolated_auth_app(monkeypatch, upload_storage_path=upload_dir) as ctx:
        with TestClient(ctx.app) as client:
            owner_a = register_and_login_user(
                client,
                email="dedup-a@example.com",
                full_name="Owner Alpha",
            )
            owner_b = register_and_login_user(
                client,
                email="dedup-b@example.com",
                full_name="Owner Beta",
            )
            org_a, proj_a1 = _create_org_and_project(
                client,
                headers=owner_a.headers,
                org_name="Alpha Org",
                project_name="Alpha One",
            )
            proj_a2_resp = client.post(
                f"/api/v1/organisations/{org_a}/projects",
                headers=owner_a.headers,
                json={"name": "Alpha Two", "status": "active", "visibility": "private"},
            )
            assert proj_a2_resp.status_code == 201
            proj_a2 = str(proj_a2_resp.json()["id"])

            _, proj_b = _create_org_and_project(
                client,
                headers=owner_b.headers,
                org_name="Beta Org",
                project_name="Beta Isolated",
            )

            pdf_bytes = _build_pdf_bytes("Shared compliance specification text.")

            # First upload in proj_a1 -> 201 Created
            first = client.post(
                f"/api/v1/projects/{proj_a1}/evidence/documents",
                headers=owner_a.headers,
                files={"file": ("spec.pdf", pdf_bytes, "application/pdf")},
            )
            assert first.status_code == 201
            first_id = first.json()["evidence"]["id"]
            assert first.json()["duplicate_detected"] is False

            # Duplicate upload in SAME proj_a1 -> 200 OK with duplicate_detected=True
            dup = client.post(
                f"/api/v1/projects/{proj_a1}/evidence/documents",
                headers=owner_a.headers,
                files={"file": ("spec-copy.pdf", pdf_bytes, "application/pdf")},
            )
            assert dup.status_code == 200
            assert dup.json()["duplicate_detected"] is True
            assert dup.json()["evidence"]["id"] == first_id

            # Same file uploaded into SECOND project in same org -> distinct item (201 Created)
            other_proj = client.post(
                f"/api/v1/projects/{proj_a2}/evidence/documents",
                headers=owner_a.headers,
                files={"file": ("spec.pdf", pdf_bytes, "application/pdf")},
            )
            assert other_proj.status_code == 201
            assert other_proj.json()["duplicate_detected"] is False
            assert other_proj.json()["evidence"]["id"] != first_id

            # Same file uploaded into ANOTHER organisation's project -> distinct isolated item
            other_org = client.post(
                f"/api/v1/projects/{proj_b}/evidence/documents",
                headers=owner_b.headers,
                files={"file": ("spec.pdf", pdf_bytes, "application/pdf")},
            )
            assert other_org.status_code == 201
            assert other_org.json()["duplicate_detected"] is False
            assert uuid.UUID(other_org.json()["evidence"]["id"]) != uuid.UUID(first_id)

            # Logically delete proj_a1 item, then re-upload same binary -> new 201 item!
            del_resp = client.delete(
                f"/api/v1/evidence/{first_id}",
                headers=owner_a.headers,
            )
            assert del_resp.status_code == 204

            reupload = client.post(
                f"/api/v1/projects/{proj_a1}/evidence/documents",
                headers=owner_a.headers,
                files={"file": ("spec-reupload.pdf", pdf_bytes, "application/pdf")},
            )
            assert reupload.status_code == 201
            assert reupload.json()["duplicate_detected"] is False
            assert reupload.json()["evidence"]["id"] != first_id

            with ctx.session_factory() as session:
                all_rows = list(session.execute(select(EvidenceItem)).scalars().all())
                assert len(all_rows) == 4
