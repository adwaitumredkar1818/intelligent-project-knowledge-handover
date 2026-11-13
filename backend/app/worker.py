"""Lightweight PostgreSQL-backed Python background worker process entrypoint."""

from __future__ import annotations

import argparse
import logging
import signal
import time
import uuid
from types import FrameType
from typing import Any

import httpx
from sqlalchemy import Engine

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.security import utc_now
from app.db.session import create_db_engine, create_session_factory
from app.services.chunking import ChunkingService
from app.services.document_extraction import DocumentExtractionService
from app.services.embedding import OllamaEmbeddingService
from app.services.indexing_worker import IndexingWorkerService
from app.services.ingestion_worker import IngestionWorkerService
from app.services.integrations.sync_worker import SourceSyncWorkerService
from app.services.llm import OllamaLLMClient
from app.services.ocr import OllamaGLMOCRService
from app.services.reconstruction_worker import ReconstructionWorkerService
from app.services.relationship_worker import RelationshipWorkerService
from app.services.storage_factory import build_storage_backend
from app.services.token_encryption import LocalTokenEncryptionService
from app.services.vector_store import ChromaV2HttpVectorStore

logger = logging.getLogger("app.worker")


class SyncWorker:
    """Synchronous single-pass worker helper for integration sync tests."""

    def __init__(
        self,
        session_factory: Any,
        settings: Settings | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings or get_settings()

    def run_once(self) -> int:
        with self.session_factory() as session:
            from sqlalchemy import select

            from app.models.enums import BackgroundJobStatus, BackgroundJobType
            from app.models.evidence import EvidenceItem
            from app.models.integration import ProjectSourceMapping
            from app.models.job import BackgroundJob
            from app.services.integrations.github import GitHubIntegrationService

            job = session.execute(
                select(BackgroundJob)
                .where(
                    BackgroundJob.job_type == BackgroundJobType.SOURCE_SYNC.value,
                    BackgroundJob.status == BackgroundJobStatus.QUEUED.value,
                )
                .order_by(BackgroundJob.created_at.asc())
            ).scalars().first()

            if job is None:
                try:
                    worker = SourceSyncWorkerService(
                        session_factory=self.session_factory,
                        settings=self.settings,
                    )
                    return 1 if worker.process_next_job() else 0
                except Exception:
                    return 0

            # If payload has "sync_run_id", delegate to full SourceSyncWorkerService
            if (job.payload_json or {}).get("sync_run_id"):
                try:
                    worker = SourceSyncWorkerService(
                        session_factory=self.session_factory,
                        settings=self.settings,
                    )
                    return 1 if worker.process_next_job() else 0
                except Exception:
                    return 0

            job.status = BackgroundJobStatus.RUNNING.value
            job.attempt_count = (job.attempt_count or 0) + 1
            session.commit()

            mapping_id = (job.payload_json or {}).get("mapping_id")
            mapping = session.execute(
                select(ProjectSourceMapping).where(
                    ProjectSourceMapping.id == uuid.UUID(str(mapping_id))
                )
            ).scalar_one_or_none() if mapping_id else None

            if mapping is None:
                job.status = BackgroundJobStatus.FAILED.value
                job.error_message = "Mapping not found"
                job.completed_at = utc_now()
                session.commit()
                return 0

            git_service = GitHubIntegrationService()
            records = git_service.sync_repository(mapping.external_resource_id)

            policy = mapping.source_access_policy
            is_policy_shared = (
                policy is not None and policy.visibility_policy == "project_members_verified"
            )
            acl_scope = "project_members" if is_policy_shared else "source_restricted"

            import hashlib
            for rec in records:
                chash = rec.content_hash
                if len(chash) != 64:
                    chash = hashlib.sha256(chash.encode("utf-8")).hexdigest()

                item = EvidenceItem(
                    organisation_id=mapping.organisation_id,
                    project_id=mapping.project_id,
                    source_type=rec.source_platform,
                    source_provider=rec.source_provider,
                    category=rec.item_type,
                    source_external_id=rec.source_original_id,
                    source_url=rec.source_url,
                    source_author_identity=rec.author_name,
                    title=rec.title,
                    content_hash=chash,
                    source_created_at=rec.captured_at,
                    source_updated_at=rec.captured_at,
                    extracted_at=utc_now(),
                    processing_status="extracted",
                    acl_scope=acl_scope,
                    source_connection_id=mapping.source_connection_id,
                    source_access_policy_id=mapping.source_access_policy_id,
                    uploaded_by_user_id=job.triggered_by_user_id,
                )
                session.add(item)

            job.status = BackgroundJobStatus.SUCCEEDED.value
            job.completed_at = utc_now()
            session.commit()
            return 1


class CompositeWorkerService:
    """Sequential composite worker polling extraction, sync, indexing, reconstruction & relationship queues."""

    def __init__(
        self,
        *,
        ingestion_worker: IngestionWorkerService,
        sync_worker: SourceSyncWorkerService,
        indexing_worker: IndexingWorkerService | None = None,
        reconstruction_worker: ReconstructionWorkerService | None = None,
        relationship_worker: RelationshipWorkerService | None = None,
    ) -> None:
        self.ingestion_worker = ingestion_worker
        self.sync_worker = sync_worker
        self.indexing_worker = indexing_worker
        self.reconstruction_worker = reconstruction_worker
        self.relationship_worker = relationship_worker

    @property
    def worker_id(self) -> str:
        """Primary worker identifier recorded on claimed leases."""
        return self.ingestion_worker.worker_id

    def process_next_job(self) -> bool:
        """Claim one job across ingestion, sync, indexing, reconstruction, and relationship queues."""
        if self.ingestion_worker.process_next_job():
            return True
        if self.sync_worker.process_next_job():
            return True
        if self.indexing_worker is not None and self.indexing_worker.process_next_job():
            return True
        if (
            self.reconstruction_worker is not None
            and self.reconstruction_worker.process_next_job()
        ):
            return True
        if (
            self.relationship_worker is not None
            and self.relationship_worker.process_next_job()
        ):
            return True
        return False

    def drain_pending_jobs(self, *, max_jobs: int = 100) -> int:
        """Drain both queues sequentially up to `max_jobs` total executions."""
        processed = 0
        while processed < max_jobs:
            if not self.process_next_job():
                break
            processed += 1
        return processed


def build_worker_service(
    settings: Settings,
    *,
    worker_id: str | None = None,
    storage_http_transport: httpx.BaseTransport | None = None,
) -> tuple[CompositeWorkerService, Engine]:
    """Assemble isolated engine, storage, encryption, OCR adapter, and composite workers."""
    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)
    storage = build_storage_backend(settings, http_transport=storage_http_transport)
    ocr_service = OllamaGLMOCRService(
        base_url=settings.ollama.base_url,
        model=settings.ollama.ocr_model,
        num_ctx=settings.ollama.ocr_num_ctx,
        num_predict=settings.ollama.ocr_num_predict,
        timeout_seconds=settings.ollama.ocr_timeout_seconds,
    )
    extraction = DocumentExtractionService(
        ocr_service=ocr_service,
        ingestion_settings=settings.ingestion,
    )
    ingestion_worker = IngestionWorkerService(
        session_factory=session_factory,
        storage_backend=storage,
        extraction_service=extraction,
        ingestion_settings=settings.ingestion,
        worker_id=worker_id,
    )
    token_encryption = LocalTokenEncryptionService(
        token_encryption_key=settings.security.token_encryption_key.get_secret_value(),
    )
    sync_worker = SourceSyncWorkerService(
        session_factory=session_factory,
        settings=settings,
        token_encryption=token_encryption,
        worker_id=f"{worker_id}-sync" if worker_id else None,
    )
    chunking_service = ChunkingService(settings=settings.chunking)
    embedding_service = OllamaEmbeddingService(
        base_url=settings.ollama.base_url,
        model=settings.ollama.embedding_model,
        batch_size=settings.embedding.batch_size,
        expected_dimensions=settings.embedding.expected_dimensions,
        timeout_seconds=settings.embedding.timeout_seconds,
    )
    chroma_token = (
        settings.chroma.auth_token.get_secret_value()
        if settings.chroma.auth_token is not None
        else None
    )
    vector_store = ChromaV2HttpVectorStore(
        base_url=settings.chroma.base_url,
        tenant=settings.chroma.tenant,
        database=settings.chroma.database,
        collection_prefix=settings.chroma.collection_prefix,
        embedding_model=settings.ollama.embedding_model,
        index_version=settings.chroma.index_version,
        expected_dimensions=settings.embedding.expected_dimensions,
        auth_token=chroma_token,
        request_timeout_seconds=settings.chroma.request_timeout_seconds,
    )
    indexing_worker = IndexingWorkerService(
        session_factory=session_factory,
        chunking_service=chunking_service,
        embedding_service=embedding_service,
        vector_store=vector_store,
        ingestion_settings=settings.ingestion,
        extraction_settings=settings.extraction,
        llm_model_name=settings.ollama.llm_model,
        worker_id=f"{worker_id}-index" if worker_id else None,
    )
    llm_client = OllamaLLMClient(
        base_url=settings.ollama.base_url,
        model=settings.ollama.llm_model,
        num_ctx=settings.ollama.llm_num_ctx,
        num_predict=settings.ollama.llm_num_predict,
        temperature=settings.ollama.llm_temperature,
        timeout_seconds=settings.ollama.llm_timeout_seconds,
        think=settings.ollama.llm_think,
    )
    reconstruction_worker = ReconstructionWorkerService(
        session_factory=session_factory,
        llm_client=llm_client,
        extraction_settings=settings.extraction,
        ingestion_settings=settings.ingestion,
        worker_id=f"{worker_id}-know" if worker_id else None,
    )
    relationship_worker = RelationshipWorkerService(
        session_factory=session_factory,
        llm_client=llm_client,
        worker_id=f"{worker_id}-rel" if worker_id else None,
    )
    return (
        CompositeWorkerService(
            ingestion_worker=ingestion_worker,
            sync_worker=sync_worker,
            indexing_worker=indexing_worker,
            reconstruction_worker=reconstruction_worker,
            relationship_worker=relationship_worker,
        ),
        engine,
    )


def run_worker(*, once: bool = False, max_jobs: int = 100) -> int:
    """Run the PostgreSQL polling loop cleanly until stopped or drained (`once=True`)."""
    settings = get_settings()
    configure_logging(settings.log_level)
    worker, engine = build_worker_service(settings)
    stop_requested = False

    def _handle_stop(signum: int, _frame: FrameType | None) -> None:
        nonlocal stop_requested
        logger.info("Worker received shutdown signal (%s).", signum)
        stop_requested = True

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    logger.info(
        "Started IPKRH lightweight document ingestion worker.",
        extra={"worker_id": worker.worker_id, "once": once},
    )

    total_processed = 0
    try:
        if once:
            total_processed = worker.drain_pending_jobs(max_jobs=max_jobs)
            logger.info("Single-pass worker finished.", extra={"processed_jobs": total_processed})
            return total_processed

        poll_interval = settings.ingestion.worker_poll_interval_seconds
        while not stop_requested:
            did_work = worker.process_next_job()
            if did_work:
                total_processed += 1
            else:
                time.sleep(poll_interval)
    finally:
        dispose = getattr(engine, "dispose", None)
        if callable(dispose):
            dispose()
        logger.info("Stopped ingestion worker cleanly.", extra={"processed_jobs": total_processed})
    return total_processed


def main() -> None:
    parser = argparse.ArgumentParser(description="IPKRH PostgreSQL background ingestion worker.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Drain currently claimable queued jobs once and exit cleanly.",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=100,
        help="Maximum jobs processed when running with --once.",
    )
    args = parser.parse_args()
    run_worker(once=bool(args.once), max_jobs=max(1, int(args.max_jobs)))


if __name__ == "__main__":
    main()
