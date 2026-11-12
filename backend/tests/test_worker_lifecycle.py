"""Integration tests for worker lifecycle, retries, failure recovery, and stale leases."""

from __future__ import annotations

import io
import uuid
from datetime import timedelta
from pathlib import Path

import docx
import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import utc_now
from app.models.audit import AuditLog
from app.models.enums import BackgroundJobStatus, EvidenceProcessingStatus
from app.models.job import BackgroundJob
from app.services.document_extraction import DocumentExtractionService
from app.services.ingestion_worker import IngestionWorkerService
from app.services.ocr import OCRExecutionError, OCRPageRequest, OCRPageResult
from app.services.storage import LocalPrivateStorageBackend
from tests.conftest import isolated_auth_app, register_and_login_user


class _FlakyOCRService:
    def __init__(self, *, fail_times: int) -> None:
        self.model_name = "flaky-ocr"
        self._remaining_failures = fail_times
        self.attempts = 0

    def extract_page_text(self, request: OCRPageRequest) -> OCRPageResult:
        self.attempts += 1
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise OCRExecutionError(
                code="OCR_TIMEOUT",
                message="Simulated temporary Ollama OCR timeout",
                retryable=True,
            )
        return OCRPageResult(
            page_number=request.page_number,
            text=f"Recovered OCR text for page {request.page_number}",
            model_name=self.model_name,
            truncated=False,
            done_reason="stop",
            prompt_eval_count=512,
            eval_count=48,
            duration_ms=25,
        )


def _scanned_pdf_bytes() -> bytes:
    temp_doc = pymupdf.Document()  # type: ignore[no-untyped-call]
    out_doc = pymupdf.Document()  # type: ignore[no-untyped-call]
    try:
        tp = temp_doc.new_page(width=400, height=200)
        tp.insert_text((36, 80), "Scanned Deployment Checklist")
        pix = tp.get_pixmap(alpha=False)
        img_bytes = bytes(pix.tobytes("png"))  # type: ignore[no-untyped-call]

        page = out_doc.new_page()
        page.insert_image(page.rect, stream=img_bytes)  # type: ignore[no-untyped-call]
        return bytes(out_doc.tobytes())  # type: ignore[no-untyped-call]
    finally:
        temp_doc.close()  # type: ignore[no-untyped-call]
        out_doc.close()  # type: ignore[no-untyped-call]


def _docx_bytes() -> bytes:
    doc = docx.Document()
    doc.add_heading("Database Ownership", level=1)
    doc.add_paragraph("PostgreSQL handles canonical job states without Redis.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_worker_end_to_end_upload_extraction_audit_and_retry_recovery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    upload_dir = tmp_path / "worker_uploads"
    with isolated_auth_app(
        monkeypatch,
        upload_storage_path=upload_dir,
        worker_max_attempts=2,
        worker_retry_base_seconds=5,
    ) as ctx:
        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client,
                email="worker-owner@example.com",
                full_name="Worker Owner",
            )
            org_resp = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "Worker Org"},
            )
            assert org_resp.status_code == 201
            org_id = org_resp.json()["id"]

            proj_resp = client.post(
                f"/api/v1/organisations/{org_id}/projects",
                headers=owner.headers,
                json={"name": "Worker Project", "status": "active", "visibility": "private"},
            )
            assert proj_resp.status_code == 201
            proj_id = proj_resp.json()["id"]

            # Upload 1: DOCX processed smoothly
            up_docx = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={
                    "file": (
                        "db.docx",
                        _docx_bytes(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
            assert up_docx.status_code == 201
            docx_ev_id = up_docx.json()["evidence"]["id"]

            storage = LocalPrivateStorageBackend(
                root_path=upload_dir,
                file_encryption_key=ctx.settings.security.file_encryption_key.get_secret_value(),
            )
            flaky_ocr = _FlakyOCRService(fail_times=2)
            worker = IngestionWorkerService(
                session_factory=ctx.session_factory,
                storage_backend=storage,
                extraction_service=DocumentExtractionService(
                    ocr_service=flaky_ocr,
                    ingestion_settings=ctx.settings.ingestion,
                ),
                ingestion_settings=ctx.settings.ingestion,
                worker_id="test-worker-1",
            )

            assert worker.process_next_job() is True
            assert worker.process_next_job() is False  # Queue empty after docx finishes

            detail_docx = client.get(f"/api/v1/evidence/{docx_ev_id}", headers=owner.headers)
            assert detail_docx.status_code == 200
            docx_data = detail_docx.json()
            assert docx_data["processing_status"] == EvidenceProcessingStatus.EXTRACTED.value
            assert docx_data["extraction_method"] == "python_docx"
            assert (
                "PostgreSQL handles canonical job states"
                in docx_data["extracted_content"]["extracted_text"]
            )
            assert docx_data["latest_job"]["status"] == BackgroundJobStatus.SUCCEEDED.value
            assert docx_data["latest_job"]["duration_ms"] >= 0

            # Upload 2: Scanned PDF fails twice then permanently while keeping original file
            up_pdf = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={"file": ("scanned.pdf", _scanned_pdf_bytes(), "application/pdf")},
            )
            assert up_pdf.status_code == 201
            pdf_ev_id = up_pdf.json()["evidence"]["id"]

            # Attempt 1 fails retryably -> re-queued with next_retry_at
            assert worker.process_next_job() is True
            with ctx.session_factory() as session:
                pdf_job = session.execute(
                    select(BackgroundJob)
                    .where(BackgroundJob.evidence_id == uuid.UUID(pdf_ev_id))
                    .order_by(BackgroundJob.created_at.desc())
                ).scalar_one()
                assert pdf_job.status == BackgroundJobStatus.QUEUED.value
                assert pdf_job.attempt_count == 1
                assert pdf_job.error_code == "OCR_TIMEOUT"
                assert pdf_job.next_retry_at is not None
                # Fast-forward backoff window cleanly
                pdf_job.next_retry_at = utc_now() - timedelta(seconds=1)
                session.commit()

            # Attempt 2 exhausts max_attempts (2/2) -> status='failed', encrypted file intact
            assert worker.process_next_job() is True
            failed_detail = client.get(f"/api/v1/evidence/{pdf_ev_id}", headers=owner.headers)
            assert failed_detail.status_code == 200
            assert (
                failed_detail.json()["processing_status"]
                == EvidenceProcessingStatus.FAILED.value
            )
            assert (
                failed_detail.json()["latest_job"]["status"]
                == BackgroundJobStatus.FAILED.value
            )
            assert len(list(upload_dir.rglob("*.enc"))) == 2

            # Manual reprocess endpoint now succeeds because original file was preserved!
            reprocess_resp = client.post(
                f"/api/v1/evidence/{pdf_ev_id}/reprocess",
                headers=owner.headers,
            )
            assert reprocess_resp.status_code == 202
            assert reprocess_resp.json()["status"] == BackgroundJobStatus.QUEUED.value

            assert worker.process_next_job() is True
            recovered_detail = client.get(f"/api/v1/evidence/{pdf_ev_id}", headers=owner.headers)
            assert recovered_detail.status_code == 200
            assert (
                recovered_detail.json()["processing_status"]
                == EvidenceProcessingStatus.EXTRACTED.value
            )
            assert "Recovered OCR text for page 1" in (
                recovered_detail.json()["extracted_content"]["extracted_text"]
            )

            with ctx.session_factory() as session:
                events = set(
                    session.execute(select(AuditLog.event_type)).scalars().all()
                )
                assert {
                    "evidence.uploaded",
                    "evidence.extraction_started",
                    "evidence.extraction_retry_scheduled",
                    "evidence.extraction_failed",
                    "evidence.reprocess_queued",
                    "evidence.extraction_completed",
                }.issubset(events)


def test_worker_reclaims_expired_stale_lease(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    upload_dir = tmp_path / "lease_uploads"
    with isolated_auth_app(monkeypatch, upload_storage_path=upload_dir) as ctx:
        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client,
                email="lease-owner@example.com",
                full_name="Lease Owner",
            )
            org_id = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "Lease Org"},
            ).json()["id"]
            proj_id = client.post(
                f"/api/v1/organisations/{org_id}/projects",
                headers=owner.headers,
                json={"name": "Lease Project", "status": "active", "visibility": "private"},
            ).json()["id"]
            up_resp = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={
                    "file": (
                        "lease.docx",
                        _docx_bytes(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
            assert up_resp.status_code == 201
            ev_id = up_resp.json()["evidence"]["id"]

            # Simulate crashed worker holding an expired lease on attempt 1
            with ctx.session_factory() as session:
                job = session.execute(select(BackgroundJob)).scalar_one()
                job.status = BackgroundJobStatus.RUNNING.value
                job.attempt_count = 1
                job.locked_by = "crashed-worker"
                job.lease_expires_at = utc_now() - timedelta(minutes=10)
                session.commit()

            storage = LocalPrivateStorageBackend(
                root_path=upload_dir,
                file_encryption_key=ctx.settings.security.file_encryption_key.get_secret_value(),
            )
            worker = IngestionWorkerService(
                session_factory=ctx.session_factory,
                storage_backend=storage,
                extraction_service=DocumentExtractionService(
                    ocr_service=_FlakyOCRService(fail_times=0),
                    ingestion_settings=ctx.settings.ingestion,
                ),
                ingestion_settings=ctx.settings.ingestion,
                worker_id="recovery-worker",
            )
            assert worker.process_next_job() is True

            detail = client.get(f"/api/v1/evidence/{ev_id}", headers=owner.headers)
            assert detail.status_code == 200
            assert detail.json()["processing_status"] == EvidenceProcessingStatus.EXTRACTED.value
            assert detail.json()["latest_job"]["attempt_count"] == 2
