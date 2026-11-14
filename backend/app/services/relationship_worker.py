"""PostgreSQL-backed background worker executing Relationship Reconstruction runs.

Claims jobs with `job_type == 'relationship_reconstruction'`, coordinates
multi-source discovery, identity resolution, decision traceability, and updates run telemetry.
"""

from __future__ import annotations

import logging
import socket
import uuid

from sqlalchemy.orm import Session, sessionmaker

from app.core.security import utc_now
from app.models.enums import BackgroundJobStatus, BackgroundJobType
from app.repositories.job import BackgroundJobRepository
from app.services.llm import StructuredLLMClient
from app.services.relationship_coordinator import RelationshipCoordinatorService

logger = logging.getLogger("app.services.relationship_worker")


def _default_worker_id() -> str:
    return f"{socket.gethostname()[:48]}-rel-{uuid.uuid4().hex[:8]}"


class RelationshipWorkerService:
    """Processes asynchronous relationship discovery and graph rebuild background jobs."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        llm_client: StructuredLLMClient | None = None,
        worker_id: str | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.llm_client = llm_client
        self.worker_id = worker_id or _default_worker_id()

    def process_next_job(self) -> bool:
        """Claim and process one relationship reconstruction job from the PostgreSQL queue."""
        now = utc_now()
        with self.session_factory() as session:
            job_repo = BackgroundJobRepository(session)
            job = job_repo.claim_next_job(
                worker_id=self.worker_id,
                lease_seconds=60,
                now=now,
                job_types=[BackgroundJobType.RELATIONSHIP_RECONSTRUCTION.value],
            )
            if job is None:
                return False

            logger.info(
                "Claimed relationship reconstruction job %s for project %s", job.id, job.project_id
            )

            payload = job.payload_json or {}
            run_id_str = payload.get("run_id")
            run_id = uuid.UUID(run_id_str) if run_id_str else None
            include_llm = bool(payload.get("include_llm_suggestions", False))

            try:
                coordinator = RelationshipCoordinatorService(session, llm_client=self.llm_client)
                run = coordinator.run_reconstruction(
                    organisation_id=job.organisation_id,
                    project_id=job.project_id,
                    run_id=run_id,
                    include_llm_suggestions=include_llm,
                )

                job.status = BackgroundJobStatus.SUCCEEDED.value
                job.completed_at = utc_now()
                job.result_summary_json = {
                    "run_id": str(run.id),
                    "entities_count": run.entities_discovered_count,
                    "relationships_count": run.relationships_discovered_count,
                    "duration_ms": run.duration_ms,
                }
                session.commit()
                logger.info("Successfully completed relationship reconstruction job %s", job.id)
                return True

            except Exception as exc:
                logger.exception("Failed relationship reconstruction job %s: %s", job.id, exc)
                job.status = BackgroundJobStatus.FAILED.value
                job.completed_at = utc_now()
                job.error_message = str(exc)[:500]
                session.commit()
                return True
