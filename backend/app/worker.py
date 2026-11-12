"""Lightweight PostgreSQL-backed Python background worker process entrypoint."""

from __future__ import annotations

import argparse
import logging
import signal
import time
from types import FrameType

from sqlalchemy import Engine

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
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
from app.services.storage import LocalPrivateStorageBackend
from app.services.token_encryption import LocalTokenEncryptionService
from app.services.vector_store import ChromaV2HttpVectorStore

logger = logging.getLogger("app.worker")


class CompositeWorkerService:
    """Sequential composite worker polling extraction, sync, indexing & reconstruction queues."""

    def __init__(
        self,
        *,
        ingestion_worker: IngestionWorkerService,
        sync_worker: SourceSyncWorkerService,
        indexing_worker: IndexingWorkerService | None = None,
        reconstruction_worker: ReconstructionWorkerService | None = None,
    ) -> None:
        self.ingestion_worker = ingestion_worker
        self.sync_worker = sync_worker
        self.indexing_worker = indexing_worker
        self.reconstruction_worker = reconstruction_worker

    @property
    def worker_id(self) -> str:
        """Primary worker identifier recorded on claimed leases."""
        return self.ingestion_worker.worker_id

    def process_next_job(self) -> bool:
        """Claim one job across ingestion, sync, indexing, and knowledge extraction queues."""
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
) -> tuple[CompositeWorkerService, Engine]:
    """Assemble isolated engine, storage, encryption, OCR adapter, and composite workers."""
    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)
    storage = LocalPrivateStorageBackend(
        root_path=settings.security.upload_storage_path,
        file_encryption_key=settings.security.file_encryption_key.get_secret_value(),
    )
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
    return (
        CompositeWorkerService(
            ingestion_worker=ingestion_worker,
            sync_worker=sync_worker,
            indexing_worker=indexing_worker,
            reconstruction_worker=reconstruction_worker,
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
