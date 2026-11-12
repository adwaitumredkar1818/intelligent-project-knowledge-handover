"""PostgreSQL-backed background worker executing document extraction and OCR jobs."""

from __future__ import annotations

import logging
import socket
import time
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import IngestionSettings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import redact_sensitive_text
from app.core.security import utc_now
from app.models.enums import (
    AuditOutcome,
    BackgroundJobStatus,
    BackgroundJobType,
    EvidenceIndexingStatus,
    EvidenceProcessingStatus,
)
from app.repositories.audit import AuditLogRepository
from app.repositories.evidence import EvidenceRepository
from app.repositories.job import BackgroundJobRepository
from app.repositories.knowledge import KnowledgeRepository
from app.services.audit import AuditService
from app.services.document_extraction import (
    DocumentExtractionError,
    DocumentExtractionService,
)
from app.services.storage import StorageBackend

logger = logging.getLogger("app.services.ingestion_worker")


def _default_worker_id() -> str:
    return f"{socket.gethostname()[:48]}-{uuid.uuid4().hex[:8]}"


def _sanitise_worker_error(message: str) -> str:
    return redact_sensitive_text(message).strip()[:500]


class IngestionWorkerService:
    """Claims queued PostgreSQL jobs and executes PDF/DOCX/OCR extraction sequentially."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        storage_backend: StorageBackend,
        extraction_service: DocumentExtractionService,
        ingestion_settings: IngestionSettings,
        worker_id: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._storage = storage_backend
        self._extraction = extraction_service
        self._settings = ingestion_settings
        self._worker_id = worker_id or _default_worker_id()

    @property
    def worker_id(self) -> str:
        """Identifier recorded on claimed job leases."""
        return self._worker_id

    def process_next_job(self) -> bool:
        """Claim and process one ready document ingestion job; return True if a job was handled."""
        claimed = self._claim_job()
        if claimed is None:
            return False

        (
            job_id,
            evidence_id,
            organisation_id,
            project_id,
            category,
            storage_key,
            key_id,
            title,
            attempt_count,
            max_attempts,
        ) = claimed

        started_perf = time.perf_counter()
        try:
            raw_bytes = self._storage.read_decrypted_bytes(
                storage_object_key=storage_key,
                organisation_id=organisation_id,
                project_id=project_id,
                key_id=key_id,
            )
            extracted = self._extraction.extract_document(
                category=category,
                raw_bytes=raw_bytes,
                document_title=title,
            )
            elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
            self._complete_success(
                job_id=job_id,
                evidence_id=evidence_id,
                duration_ms=elapsed_ms,
                extracted=extracted,
            )
        except DocumentExtractionError as exc:
            elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
            self._complete_failure(
                job_id=job_id,
                evidence_id=evidence_id,
                duration_ms=elapsed_ms,
                error_code=exc.code,
                error_message=exc.message,
                retryable=exc.retryable and attempt_count < max_attempts,
                attempt_count=attempt_count,
            )
        except ServiceUnavailableError as exc:
            elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
            is_missing_obj = exc.code in {
                "STORAGE_OBJECT_MISSING",
                "STORAGE_KEY_INVALID",
                "STORAGE_KEY_UNSUPPORTED",
            }
            self._complete_failure(
                job_id=job_id,
                evidence_id=evidence_id,
                duration_ms=elapsed_ms,
                error_code=exc.code,
                error_message=exc.message,
                retryable=(not is_missing_obj) and attempt_count < max_attempts,
                attempt_count=attempt_count,
            )
        except Exception as exc:  # pragma: no cover - defensive runtime fallback
            elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
            logger.exception("Unhandled error inside document ingestion worker.")
            self._complete_failure(
                job_id=job_id,
                evidence_id=evidence_id,
                duration_ms=elapsed_ms,
                error_code="WORKER_UNEXPECTED_ERROR",
                error_message=f"Unexpected worker failure: {type(exc).__name__}",
                retryable=attempt_count < max_attempts,
                attempt_count=attempt_count,
            )
        return True

    def drain_pending_jobs(self, *, max_jobs: int = 100) -> int:
        """Process currently ready jobs sequentially up to `max_jobs` (useful for CLI/tests)."""
        processed = 0
        while processed < max_jobs:
            did_work = self.process_next_job()
            if not did_work:
                break
            processed += 1
        return processed

    def _claim_job(
        self,
    ) -> tuple[
        uuid.UUID,
        uuid.UUID,
        uuid.UUID,
        uuid.UUID,
        str,
        str,
        str | None,
        str,
        int,
        int,
    ] | None:
        now = utc_now()
        with self._session_factory() as session:
            job_repo = BackgroundJobRepository(session)
            evidence_repo = EvidenceRepository(session)
            audit = AuditService(audit_repository=AuditLogRepository(session))

            job = job_repo.claim_next_job(
                worker_id=self._worker_id,
                lease_seconds=self._settings.worker_lease_seconds,
                now=now,
                job_type=BackgroundJobType.DOCUMENT_INGESTION.value,
            )
            if job is None:
                session.commit()
                return None

            if job.evidence_id is None:
                job.status = BackgroundJobStatus.FAILED.value
                job.completed_at = now
                job.error_code = "MISSING_EVIDENCE_REF"
                job.error_message = "Job is missing an associated evidence item."
                job.locked_by = None
                job.lease_expires_at = None
                session.commit()
                return None

            evidence = evidence_repo.get_by_id(job.evidence_id, include_deleted=False)
            if evidence is None or not evidence.storage_object_key:
                job.status = BackgroundJobStatus.CANCELLED.value
                job.completed_at = now
                job.error_code = "EVIDENCE_UNAVAILABLE"
                job.error_message = "Parent evidence item is unavailable or deleted."
                job.locked_by = None
                job.lease_expires_at = None
                session.commit()
                return None

            evidence.processing_status = EvidenceProcessingStatus.PROCESSING.value
            evidence.error_code = None
            evidence.error_message = None

            audit.record_event(
                event_type="evidence.extraction_started",
                resource_type="evidence_item",
                actor_user_id=None,
                organisation_id=evidence.organisation_id,
                project_id=evidence.project_id,
                resource_id=str(evidence.id),
                metadata={
                    "job_id": str(job.id),
                    "attempt_count": job.attempt_count,
                    "worker_id": self._worker_id,
                },
                message="Background worker claimed document extraction job.",
            )
            session.commit()
            return (
                job.id,
                evidence.id,
                evidence.organisation_id,
                evidence.project_id,
                evidence.category,
                evidence.storage_object_key,
                evidence.encryption_key_id,
                evidence.title,
                int(job.attempt_count),
                int(job.max_attempts),
            )

    def _complete_success(
        self,
        *,
        job_id: uuid.UUID,
        evidence_id: uuid.UUID,
        duration_ms: int,
        extracted: Any,
    ) -> None:
        now = utc_now()
        with self._session_factory() as session:
            job_repo = BackgroundJobRepository(session)
            evidence_repo = EvidenceRepository(session)
            audit = AuditService(audit_repository=AuditLogRepository(session))

            job = job_repo.get_by_id(job_id)
            if job is None:
                return
            evidence = evidence_repo.get_by_id(evidence_id, include_deleted=False)
            if evidence is None:
                job.status = BackgroundJobStatus.CANCELLED.value
                job.completed_at = now
                job.duration_ms = duration_ms
                job.locked_by = None
                job.lease_expires_at = None
                session.commit()
                return

            evidence_repo.replace_extracted_content(
                evidence_id=evidence.id,
                extracted_text=extracted.extracted_text,
                warnings=extracted.warnings,
                pages=extracted.pages,
            )
            KnowledgeRepository(session).mark_stale_for_evidence(
                evidence_id=evidence.id,
                reason="document_content_reextracted",
                now=now,
            )

            merged_meta = dict(evidence.metadata_json or {})
            merged_meta.update(extracted.metadata_json)
            evidence.metadata_json = merged_meta
            evidence.processing_status = extracted.processing_status
            evidence.extraction_method = extracted.extraction_method
            evidence.page_count = extracted.page_count
            evidence.ocr_pages_count = extracted.ocr_pages_count
            evidence.truncated_pages_count = extracted.truncated_pages_count
            evidence.extracted_at = now
            if extracted.source_created_at and evidence.source_created_at is None:
                evidence.source_created_at = extracted.source_created_at
            if extracted.source_updated_at and evidence.source_updated_at is None:
                evidence.source_updated_at = extracted.source_updated_at
            if extracted.source_author_identity:
                evidence.source_author_identity = extracted.source_author_identity

            if extracted.processing_status == EvidenceProcessingStatus.PARTIALLY_EXTRACTED.value:
                evidence.error_code = "EXTRACTION_INCOMPLETE"
                evidence.error_message = (
                    "One or more pages experienced OCR truncation or configured page limits."
                )
            else:
                evidence.error_code = None
                evidence.error_message = None

            job.status = BackgroundJobStatus.SUCCEEDED.value
            job.completed_at = now
            job.duration_ms = duration_ms
            job.locked_by = None
            job.lease_expires_at = None
            job.error_code = None
            job.error_message = None
            job.result_json = {
                "processing_status": extracted.processing_status,
                "extraction_method": extracted.extraction_method,
                "page_count": extracted.page_count,
                "ocr_pages_count": extracted.ocr_pages_count,
                "truncated_pages_count": extracted.truncated_pages_count,
                "char_count": len(extracted.extracted_text),
            }

            if (extracted.extracted_text or "").strip():
                if not job_repo.has_active_job_for_evidence(
                    evidence_id=evidence.id,
                    job_type=BackgroundJobType.EVIDENCE_INDEXING.value,
                ):
                    job_repo.create_job(
                        organisation_id=evidence.organisation_id,
                        project_id=evidence.project_id,
                        evidence_id=evidence.id,
                        triggered_by_user_id=job.triggered_by_user_id,
                        job_type=BackgroundJobType.EVIDENCE_INDEXING.value,
                        max_attempts=self._settings.worker_max_attempts,
                        priority=110,
                        payload_json={
                            "target": "full",
                            "force_rechunk": True,
                            "trigger": "document_extraction_completed",
                        },
                    )
                evidence.indexing_status = EvidenceIndexingStatus.QUEUED.value
                evidence.index_error_code = None
                evidence.index_error_message = None
            else:
                evidence.indexing_status = EvidenceIndexingStatus.INDEXED.value
                evidence.chunk_count = 0
                evidence.indexed_at = now
                evidence.index_error_code = None
                evidence.index_error_message = None

            audit.record_event(
                event_type="evidence.extraction_completed",
                resource_type="evidence_item",
                actor_user_id=None,
                organisation_id=evidence.organisation_id,
                project_id=evidence.project_id,
                resource_id=str(evidence.id),
                metadata={
                    "job_id": str(job.id),
                    "processing_status": extracted.processing_status,
                    "extraction_method": extracted.extraction_method,
                    "page_count": extracted.page_count,
                    "ocr_pages_count": extracted.ocr_pages_count,
                    "truncated_pages_count": extracted.truncated_pages_count,
                    "duration_ms": duration_ms,
                },
                message=(
                    f"Completed document extraction with status '{extracted.processing_status}'."
                ),
            )
            session.commit()

    def _complete_failure(
        self,
        *,
        job_id: uuid.UUID,
        evidence_id: uuid.UUID,
        duration_ms: int,
        error_code: str,
        error_message: str,
        retryable: bool,
        attempt_count: int,
    ) -> None:
        now = utc_now()
        safe_message = _sanitise_worker_error(error_message)
        with self._session_factory() as session:
            job_repo = BackgroundJobRepository(session)
            evidence_repo = EvidenceRepository(session)
            audit = AuditService(audit_repository=AuditLogRepository(session))

            job = job_repo.get_by_id(job_id)
            if job is None:
                return
            evidence = evidence_repo.get_by_id(evidence_id, include_deleted=False)

            if retryable:
                backoff_seconds = min(
                    3600,
                    self._settings.worker_retry_base_seconds * (2 ** max(0, attempt_count - 1)),
                )
                job.status = BackgroundJobStatus.QUEUED.value
                job.next_retry_at = now + timedelta(seconds=backoff_seconds)
                job.locked_by = None
                job.lease_expires_at = None
                job.error_code = error_code[:64]
                job.error_message = safe_message
                if evidence is not None:
                    evidence.processing_status = EvidenceProcessingStatus.QUEUED.value
                    evidence.error_code = error_code[:64]
                    evidence.error_message = safe_message
                    audit.record_event(
                        event_type="evidence.extraction_retry_scheduled",
                        resource_type="evidence_item",
                        actor_user_id=None,
                        organisation_id=evidence.organisation_id,
                        project_id=evidence.project_id,
                        resource_id=str(evidence.id),
                        outcome=AuditOutcome.ERROR.value,
                        metadata={
                            "job_id": str(job.id),
                            "attempt_count": attempt_count,
                            "retry_delay_seconds": backoff_seconds,
                            "error_code": error_code[:64],
                            "duration_ms": duration_ms,
                        },
                        message="Scheduled extraction job retry while preserving original file.",
                        level=logging.WARNING,
                    )
            else:
                job.status = BackgroundJobStatus.FAILED.value
                job.completed_at = now
                job.duration_ms = duration_ms
                job.locked_by = None
                job.lease_expires_at = None
                job.error_code = error_code[:64]
                job.error_message = safe_message
                if evidence is not None:
                    evidence.processing_status = EvidenceProcessingStatus.FAILED.value
                    evidence.error_code = error_code[:64]
                    evidence.error_message = safe_message
                    audit.record_event(
                        event_type="evidence.extraction_failed",
                        resource_type="evidence_item",
                        actor_user_id=None,
                        organisation_id=evidence.organisation_id,
                        project_id=evidence.project_id,
                        resource_id=str(evidence.id),
                        outcome=AuditOutcome.ERROR.value,
                        metadata={
                            "job_id": str(job.id),
                            "attempt_count": attempt_count,
                            "error_code": error_code[:64],
                            "duration_ms": duration_ms,
                        },
                        message=(
                            "Document extraction job failed permanently after retries "
                            "or fatal error."
                        ),
                        level=logging.ERROR,
                    )
            session.commit()
