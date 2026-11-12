"""Lightweight PostgreSQL background worker process for asynchronous sync and extraction jobs."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
import time
from datetime import UTC, datetime
from types import FrameType

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.db.session import create_db_engine, create_session_factory
from app.models.enums import JobStatus
from app.models.evidence import SourceSyncJob
from app.services.evidence import EvidenceService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("app.worker")


class SyncWorker:
    """PostgreSQL-backed worker leasing and processing queued sync and extraction jobs."""

    def __init__(
        self,
        poll_interval_seconds: float = 2.0,
        session_factory: sessionmaker[Session] | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._engine = create_db_engine(self._settings) if session_factory is None else None
        self._session_factory = session_factory or create_session_factory(self._engine)  # type: ignore[arg-type]
        self._poll_interval = poll_interval_seconds
        self._running = True

        # Signal handling (only on main thread)
        if threading.current_thread() is threading.main_thread():
            try:
                signal.signal(signal.SIGINT, self._handle_signal)
                signal.signal(signal.SIGTERM, self._handle_signal)
            except (ValueError, AttributeError):
                pass

    def _handle_signal(self, signum: int, frame: FrameType | None) -> None:
        logger.info("Worker received termination signal %d. Shutting down gracefully...", signum)
        self._running = False

    def lease_next_job(self, db: Session) -> SourceSyncJob | None:
        """Atomically select and lease a single queued job using SKIP LOCKED on PostgreSQL."""
        stmt = (
            select(SourceSyncJob)
            .where(SourceSyncJob.status == JobStatus.QUEUED.value)
            .order_by(SourceSyncJob.created_at.asc())
            .limit(1)
        )
        # Using with_for_update(skip_locked=True) prevents race conditions
        # across worker processes on PostgreSQL
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)

        job = db.execute(stmt).scalar_one_or_none()
        if job is not None and job.source_mapping_id is not None:
            now = datetime.now(UTC)
            job.status = JobStatus.RUNNING.value
            job.started_at = now
            db.commit()
            logger.info("Leased sync job %s for mapping %s", job.id, job.source_mapping_id)
        return job

    def process_job(self, db: Session, job: SourceSyncJob) -> bool:
        """Execute the sync workflow for the leased job."""
        if job.source_mapping_id is None:
            return False
        service = EvidenceService(db=db, settings=self._settings)
        logger.info("Processing sync job %s (type: %s)", job.id, job.job_type)

        try:
            records_count = service.execute_mapping_sync(
                mapping_id=job.source_mapping_id,
                job_id=job.id,
            )
            logger.info("Completed job %s: ingested %d records", job.id, records_count)
            return True
        except Exception as exc:
            logger.error("Job %s execution failed: %s", job.id, exc, exc_info=True)
            return False

    def run_once(self) -> int:
        """Execute one polling pass; returns number of processed jobs."""
        with self._session_factory() as db:
            job = self.lease_next_job(db)
            if job is not None:
                self.process_job(db, job)
                return 1
            return 0

    def run(self) -> None:
        """Start the continuous worker polling loop."""
        logger.info("The Handover Lightweight Background Worker started.")
        while self._running:
            try:
                processed = self.run_once()
                if processed == 0:
                    time.sleep(self._poll_interval)
            except Exception as exc:
                logger.error("Unexpected worker loop error: %s", exc, exc_info=True)
                time.sleep(self._poll_interval)

        if self._engine is not None:
            self._engine.dispose()
        logger.info("Worker process stopped cleanly.")


def main() -> None:
    """CLI entrypoint for running the worker."""
    parser = argparse.ArgumentParser(description="The Handover Background Worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single job lease cycle and exit",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Polling interval in seconds (default 2.0)",
    )
    args = parser.parse_args()

    worker = SyncWorker(poll_interval_seconds=args.interval)
    if args.once:
        count = worker.run_once()
        logger.info("One-shot worker completed %d job(s)", count)
        sys.exit(0)
    else:
        worker.run()


if __name__ == "__main__":
    main()
