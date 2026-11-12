"""PostgreSQL-backed background worker executing delegated GitHub & Jira sync jobs."""

from __future__ import annotations

import logging
import socket
import time
import uuid
from datetime import timedelta

import httpx
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import redact_sensitive_text
from app.core.security import utc_now
from app.models.enums import (
    AuditOutcome,
    BackgroundJobStatus,
    BackgroundJobType,
    IntegrationProvider,
    ProjectSourceMappingStatus,
    SourceConnectionStatus,
    SourceSyncRunStatus,
    UserSourceAuthorisationStatus,
)
from app.models.integration import ProjectSourceMapping
from app.repositories.audit import AuditLogRepository
from app.repositories.evidence import EvidenceRepository
from app.repositories.integration import IntegrationRepository
from app.repositories.job import BackgroundJobRepository
from app.repositories.organisation import OrganisationRepository
from app.repositories.project import ProjectRepository
from app.repositories.rbac import RbacRepository
from app.repositories.user import UserRepository
from app.services.audit import AuditService
from app.services.integrations.access_policy import SourceAccessPolicyService
from app.services.integrations.errors import (
    IntegrationAuthError,
    IntegrationProviderError,
    IntegrationRateLimitError,
)
from app.services.integrations.evidence_ingestor import SourceEvidenceIngestor
from app.services.integrations.github_client import GitHubClient
from app.services.integrations.github_sync import GitHubSyncOrchestrator, SyncExecutionReport
from app.services.integrations.jira_client import JiraClient
from app.services.integrations.jira_sync import JiraSyncOrchestrator
from app.services.integrations.oauth import SourceOAuthService
from app.services.rbac import RbacService
from app.services.token_encryption import LocalTokenEncryptionService, TokenEncryptionService

logger = logging.getLogger("app.services.integrations.sync_worker")


def _default_worker_id() -> str:
    return f"{socket.gethostname()[:48]}-sync-{uuid.uuid4().hex[:8]}"


class SourceSyncWorkerService:
    """Claims `source_sync` background jobs sequentially with rate-limit backoff & rotation."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        settings: Settings,
        token_encryption: TokenEncryptionService | None = None,
        http_transport: httpx.BaseTransport | None = None,
        worker_id: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._encryption = token_encryption or LocalTokenEncryptionService(
            token_encryption_key=settings.security.token_encryption_key.get_secret_value()
        )
        self._transport = http_transport
        self._worker_id = worker_id or _default_worker_id()

    @property
    def worker_id(self) -> str:
        """Identifier recorded on claimed background job leases."""
        return self._worker_id

    def drain_pending_jobs(self, *, max_jobs: int = 100) -> int:
        """Process currently ready `source_sync` jobs up to `max_jobs`."""
        processed = 0
        while processed < max_jobs:
            if not self.process_next_job():
                break
            processed += 1
        return processed

    def process_next_job(self) -> bool:
        """Claim and execute one ready `source_sync` job; return True if handled."""
        claimed = self._claim_job()
        if claimed is None:
            return False

        (
            job_id,
            sync_run_id,
            mapping_id,
            authorisation_id,
            sync_mode,
            attempt_count,
            max_attempts,
        ) = claimed

        started_perf = time.perf_counter()
        try:
            report = self._execute_claimed_sync(
                job_id=job_id,
                sync_run_id=sync_run_id,
                mapping_id=mapping_id,
                authorisation_id=authorisation_id,
                sync_mode=sync_mode,
            )
            elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
            if report is not None:
                self._complete_success(
                    job_id=job_id,
                    sync_run_id=sync_run_id,
                    mapping_id=mapping_id,
                    duration_ms=elapsed_ms,
                    report=report,
                )
        except IntegrationRateLimitError as exc:
            elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
            self._complete_failure(
                job_id=job_id,
                sync_run_id=sync_run_id,
                mapping_id=mapping_id,
                duration_ms=elapsed_ms,
                error_code=exc.code,
                error_message=exc.message,
                retryable=attempt_count < max_attempts,
                retry_delay_seconds=exc.retry_after_seconds,
                attempt_count=attempt_count,
                requires_reauth=False,
            )
        except IntegrationAuthError as exc:
            elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
            self._complete_failure(
                job_id=job_id,
                sync_run_id=sync_run_id,
                mapping_id=mapping_id,
                duration_ms=elapsed_ms,
                error_code=exc.code,
                error_message=exc.message,
                retryable=False,
                retry_delay_seconds=None,
                attempt_count=attempt_count,
                requires_reauth=True,
            )
        except IntegrationProviderError as exc:
            elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
            self._complete_failure(
                job_id=job_id,
                sync_run_id=sync_run_id,
                mapping_id=mapping_id,
                duration_ms=elapsed_ms,
                error_code=exc.code,
                error_message=exc.message,
                retryable=exc.retryable and attempt_count < max_attempts,
                retry_delay_seconds=exc.retry_after_seconds,
                attempt_count=attempt_count,
                requires_reauth=exc.requires_reauth,
            )
        except ServiceUnavailableError as exc:
            elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
            self._complete_failure(
                job_id=job_id,
                sync_run_id=sync_run_id,
                mapping_id=mapping_id,
                duration_ms=elapsed_ms,
                error_code=exc.code,
                error_message=exc.message,
                retryable=False,
                retry_delay_seconds=None,
                attempt_count=attempt_count,
                requires_reauth=False,
            )
        except Exception as exc:  # pragma: no cover
            elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
            logger.exception("Unhandled error inside source sync worker.")
            self._complete_failure(
                job_id=job_id,
                sync_run_id=sync_run_id,
                mapping_id=mapping_id,
                duration_ms=elapsed_ms,
                error_code="SYNC_WORKER_UNEXPECTED_ERROR",
                error_message=f"Unexpected sync failure: {type(exc).__name__}",
                retryable=attempt_count < max_attempts,
                retry_delay_seconds=None,
                attempt_count=attempt_count,
                requires_reauth=False,
            )
        return True

    def _claim_job(
        self,
    ) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, str, int, int] | None:
        now = utc_now()
        with self._session_factory() as session:
            job_repo = BackgroundJobRepository(session)
            int_repo = IntegrationRepository(session)
            audit = AuditService(audit_repository=AuditLogRepository(session))

            job = job_repo.claim_next_job(
                worker_id=self._worker_id,
                lease_seconds=self._settings.ingestion.worker_lease_seconds,
                now=now,
                job_type=BackgroundJobType.SOURCE_SYNC.value,
            )
            if job is None:
                session.commit()
                return None

            payload = job.payload_json or {}
            try:
                sync_run_id = uuid.UUID(str(payload.get("sync_run_id")))
                mapping_id = uuid.UUID(str(payload.get("mapping_id")))
                auth_id = uuid.UUID(str(payload.get("authorisation_id")))
                sync_mode = str(payload.get("sync_mode") or "incremental")
            except (ValueError, TypeError):
                job.status = BackgroundJobStatus.FAILED.value
                job.completed_at = now
                job.error_code = "INVALID_SYNC_JOB_PAYLOAD"
                job.error_message = "Source sync job payload is malformed."
                job.locked_by = None
                job.lease_expires_at = None
                session.commit()
                return None

            sync_run = int_repo.get_sync_run_by_id(sync_run_id)
            mapping = int_repo.get_mapping_by_id(mapping_id)
            auth = int_repo.get_authorisation_by_id(auth_id)

            if (
                sync_run is None
                or sync_run.status == SourceSyncRunStatus.CANCELLED.value
                or mapping is None
                or mapping.status
                in {
                    ProjectSourceMappingStatus.DISABLED.value,
                    ProjectSourceMappingStatus.DISCONNECTED.value,
                }
                or mapping.source_connection is None
                or mapping.source_connection.status == SourceConnectionStatus.DISCONNECTED.value
            ):
                job.status = BackgroundJobStatus.CANCELLED.value
                job.completed_at = now
                job.error_code = "SYNC_CANCELLED_OR_DISCONNECTED"
                job.error_message = "Sync cancelled because mapping or connection is inactive."
                job.locked_by = None
                job.lease_expires_at = None
                if sync_run is not None and sync_run.status in {
                    SourceSyncRunStatus.QUEUED.value,
                    SourceSyncRunStatus.RUNNING.value,
                }:
                    sync_run.status = SourceSyncRunStatus.CANCELLED.value
                    sync_run.completed_at = now
                    sync_run.error_code = "SYNC_CANCELLED"
                    sync_run.error_message = job.error_message
                session.commit()
                return None

            if auth is None or auth.status != UserSourceAuthorisationStatus.ACTIVE.value:
                job.status = BackgroundJobStatus.FAILED.value
                job.completed_at = now
                job.error_code = "SOURCE_AUTHORISATION_REVOKED"
                job.error_message = "Triggering user's source authorisation is inactive or revoked."
                job.locked_by = None
                job.lease_expires_at = None
                sync_run.status = SourceSyncRunStatus.FAILED.value
                sync_run.completed_at = now
                sync_run.error_code = job.error_code
                sync_run.error_message = job.error_message
                session.commit()
                return None

            sync_run.status = SourceSyncRunStatus.RUNNING.value
            if sync_run.started_at is None:
                sync_run.started_at = now
            sync_run.error_code = None
            sync_run.error_message = None

            audit.record_event(
                event_type="integration.sync_started",
                resource_type="source_sync_run",
                actor_user_id=None,
                organisation_id=sync_run.organisation_id,
                project_id=sync_run.project_id,
                resource_id=str(sync_run.id),
                metadata={
                    "job_id": str(job.id),
                    "mapping_id": str(mapping.id),
                    "provider": mapping.provider,
                    "attempt_count": job.attempt_count,
                    "worker_id": self._worker_id,
                },
                message=f"Worker started {mapping.provider} source sync run.",
            )
            session.commit()
            return (
                job.id,
                sync_run.id,
                mapping.id,
                auth.id,
                sync_mode,
                int(job.attempt_count),
                int(job.max_attempts),
            )

    def _execute_claimed_sync(
        self,
        *,
        job_id: uuid.UUID,
        sync_run_id: uuid.UUID,
        mapping_id: uuid.UUID,
        authorisation_id: uuid.UUID,
        sync_mode: str,
    ) -> SyncExecutionReport | None:
        with self._session_factory() as session:
            job_repo = BackgroundJobRepository(session)
            int_repo = IntegrationRepository(session)
            evidence_repo = EvidenceRepository(session)
            audit = AuditService(audit_repository=AuditLogRepository(session))
            rbac = RbacService(
                db_session=session,
                rbac_repository=RbacRepository(session),
                user_repository=UserRepository(session),
                organisation_repository=OrganisationRepository(session),
                project_repository=ProjectRepository(session),
            )
            oauth = SourceOAuthService(
                session=session,
                settings=self._settings,
                integration_repo=int_repo,
                token_encryption=self._encryption,
                rbac_service=rbac,
                audit_service=audit,
                http_transport=self._transport,
            )

            job = job_repo.get_by_id(job_id)
            sync_run = int_repo.get_sync_run_by_id(sync_run_id)
            mapping = int_repo.get_mapping_by_id(mapping_id)
            if (
                job is None
                or job.status == BackgroundJobStatus.CANCELLED.value
                or sync_run is None
                or sync_run.status == SourceSyncRunStatus.CANCELLED.value
                or mapping is None
                or mapping.source_access_policy is None
            ):
                return None

            policy = mapping.source_access_policy
            ingestor = SourceEvidenceIngestor(
                session=session,
                evidence_repository=evidence_repo,
            )
            policy_svc = SourceAccessPolicyService()

            def _run_with_token(
                access_token: str,
                auth_obj: object,
                active_mapping: ProjectSourceMapping,
            ) -> SyncExecutionReport:
                del auth_obj
                loaded_auth = int_repo.get_authorisation_by_id(authorisation_id)
                if loaded_auth is None:
                    raise IntegrationAuthError(
                        provider=active_mapping.provider,
                        code="AUTHORISATION_INACTIVE",
                        message="Delegated source authorisation was removed before sync.",
                    )
                if active_mapping.provider == IntegrationProvider.GITHUB.value:
                    gh = GitHubSyncOrchestrator(
                        settings=self._settings,
                        github_client=GitHubClient(
                            settings=self._settings,
                            transport=self._transport,
                        ),
                        integration_repo=int_repo,
                        ingestor=ingestor,
                        access_policy_service=policy_svc,
                    )
                    return gh.execute_sync(
                        mapping=active_mapping,
                        policy=policy,
                        access_token=access_token,
                        actor_user_id=loaded_auth.user_id,
                        external_user_id=loaded_auth.external_user_id,
                        external_username=loaded_auth.external_username,
                        sync_mode=sync_mode,
                    )

                site_url = (
                    str(active_mapping.sync_config_json.get("site_url"))
                    if isinstance(active_mapping.sync_config_json, dict)
                    and active_mapping.sync_config_json.get("site_url")
                    else None
                )
                jira = JiraSyncOrchestrator(
                    settings=self._settings,
                    jira_client=JiraClient(
                        settings=self._settings,
                        transport=self._transport,
                    ),
                    integration_repo=int_repo,
                    ingestor=ingestor,
                    access_policy_service=policy_svc,
                )
                return jira.execute_sync(
                    mapping=active_mapping,
                    policy=policy,
                    access_token=access_token,
                    actor_user_id=loaded_auth.user_id,
                    external_user_id=loaded_auth.external_user_id,
                    external_username=loaded_auth.external_username,
                    sync_mode=sync_mode,
                    site_base_url=site_url,
                )

            token, auth_row = oauth.get_valid_access_token(authorisation_id=authorisation_id)
            try:
                report = _run_with_token(token, auth_row, mapping)
            except IntegrationAuthError as exc:
                if exc.status_code != 401:
                    raise
                session.rollback()
                # Re-fetch cleanly before refresh rotation and retry once
                reloaded_mapping = int_repo.get_mapping_by_id(mapping_id)
                if reloaded_mapping is not None:
                    mapping = reloaded_mapping
                policy = mapping.source_access_policy or policy
                new_token, refreshed_auth = oauth.refresh_access_token(
                    authorisation_id=authorisation_id,
                    force=True,
                )
                report = _run_with_token(new_token, refreshed_auth, mapping)

            # Check if cancellation raced during HTTP execution before committing results
            session.refresh(job)
            session.refresh(sync_run)
            if (
                job.status == BackgroundJobStatus.CANCELLED.value
                or sync_run.status == SourceSyncRunStatus.CANCELLED.value
            ):
                session.rollback()
                return None

            session.commit()
            return report

    def _complete_success(
        self,
        *,
        job_id: uuid.UUID,
        sync_run_id: uuid.UUID,
        mapping_id: uuid.UUID,
        duration_ms: int,
        report: SyncExecutionReport,
    ) -> None:
        now = utc_now()
        with self._session_factory() as session:
            job_repo = BackgroundJobRepository(session)
            int_repo = IntegrationRepository(session)
            audit = AuditService(audit_repository=AuditLogRepository(session))

            job = job_repo.get_by_id(job_id)
            sync_run = int_repo.get_sync_run_by_id(sync_run_id)
            mapping = int_repo.get_mapping_by_id(mapping_id)
            if job is None or sync_run is None or mapping is None:
                return
            if (
                job.status == BackgroundJobStatus.CANCELLED.value
                or sync_run.status == SourceSyncRunStatus.CANCELLED.value
            ):
                return

            final_status = (
                SourceSyncRunStatus.PARTIAL.value
                if report.partial or report.items_failed > 0 or report.items_inaccessible > 0
                else SourceSyncRunStatus.SUCCEEDED.value
            )
            sync_run.status = final_status
            sync_run.items_discovered = report.items_discovered
            sync_run.items_created = report.items_created
            sync_run.items_updated = report.items_updated
            sync_run.items_unchanged = report.items_unchanged
            sync_run.items_inaccessible = report.items_inaccessible
            sync_run.items_failed = report.items_failed
            sync_run.warnings_json = list(report.warnings)[:50]
            sync_run.cursor_after_json = dict(report.new_cursor)
            sync_run.completed_at = now
            sync_run.duration_ms = duration_ms
            sync_run.error_code = None
            sync_run.error_message = None

            mapping.sync_cursor_json = dict(report.new_cursor)
            mapping.last_synced_at = now
            mapping.last_sync_status = final_status
            mapping.last_error_code = None
            mapping.last_error_summary = None
            if mapping.status == ProjectSourceMappingStatus.ERROR.value:
                mapping.status = ProjectSourceMappingStatus.ACTIVE.value
            if mapping.source_connection is not None:
                mapping.source_connection.last_synced_at = now
                mapping.source_connection.last_error_code = None
                mapping.source_connection.last_error_summary = None

            job.status = BackgroundJobStatus.SUCCEEDED.value
            job.completed_at = now
            job.duration_ms = duration_ms
            job.locked_by = None
            job.lease_expires_at = None
            job.error_code = None
            job.error_message = None
            job.result_json = {
                "sync_run_id": str(sync_run.id),
                "status": final_status,
                "items_discovered": report.items_discovered,
                "items_created": report.items_created,
                "items_updated": report.items_updated,
                "items_unchanged": report.items_unchanged,
                "items_inaccessible": report.items_inaccessible,
                "items_failed": report.items_failed,
            }

            audit.record_event(
                event_type="integration.sync_completed",
                resource_type="source_sync_run",
                actor_user_id=None,
                organisation_id=sync_run.organisation_id,
                project_id=sync_run.project_id,
                resource_id=str(sync_run.id),
                metadata=job.result_json,
                message=(
                    f"Completed {mapping.provider} source sync run with status '{final_status}'."
                ),
            )
            session.commit()

    def _complete_failure(
        self,
        *,
        job_id: uuid.UUID,
        sync_run_id: uuid.UUID,
        mapping_id: uuid.UUID,
        duration_ms: int,
        error_code: str,
        error_message: str,
        retryable: bool,
        retry_delay_seconds: int | None,
        attempt_count: int,
        requires_reauth: bool,
    ) -> None:
        now = utc_now()
        safe_message = redact_sensitive_text(error_message).strip()[:500]
        with self._session_factory() as session:
            job_repo = BackgroundJobRepository(session)
            int_repo = IntegrationRepository(session)
            audit = AuditService(audit_repository=AuditLogRepository(session))

            job = job_repo.get_by_id(job_id)
            sync_run = int_repo.get_sync_run_by_id(sync_run_id)
            mapping = int_repo.get_mapping_by_id(mapping_id)
            if job is None:
                return

            if retryable:
                backoff = (
                    retry_delay_seconds
                    if retry_delay_seconds is not None
                    else min(
                        1800,
                        self._settings.ingestion.worker_retry_base_seconds
                        * (2 ** max(0, attempt_count - 1)),
                    )
                )
                job.status = BackgroundJobStatus.QUEUED.value
                job.next_retry_at = now + timedelta(seconds=backoff)
                job.locked_by = None
                job.lease_expires_at = None
                job.error_code = error_code[:64]
                job.error_message = safe_message
                if sync_run is not None and sync_run.status != SourceSyncRunStatus.CANCELLED.value:
                    sync_run.status = SourceSyncRunStatus.QUEUED.value
                    sync_run.error_code = error_code[:64]
                    sync_run.error_message = safe_message
                    audit.record_event(
                        event_type="integration.sync_retry_scheduled",
                        resource_type="source_sync_run",
                        actor_user_id=None,
                        organisation_id=sync_run.organisation_id,
                        project_id=sync_run.project_id,
                        resource_id=str(sync_run.id),
                        outcome=AuditOutcome.ERROR.value,
                        metadata={
                            "job_id": str(job.id),
                            "attempt_count": attempt_count,
                            "retry_delay_seconds": backoff,
                            "error_code": error_code[:64],
                        },
                        message="Scheduled source sync retry after transient or rate-limit error.",
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
                if sync_run is not None and sync_run.status != SourceSyncRunStatus.CANCELLED.value:
                    sync_run.status = SourceSyncRunStatus.FAILED.value
                    sync_run.completed_at = now
                    sync_run.duration_ms = duration_ms
                    sync_run.error_code = error_code[:64]
                    sync_run.error_message = safe_message
                if mapping is not None:
                    mapping.status = ProjectSourceMappingStatus.ERROR.value
                    mapping.last_sync_status = SourceSyncRunStatus.FAILED.value
                    mapping.last_error_code = error_code[:64]
                    mapping.last_error_summary = safe_message
                    if (
                        requires_reauth
                        and mapping.source_connection is not None
                        and mapping.source_connection.status
                        != SourceConnectionStatus.DISCONNECTED.value
                    ):
                        mapping.source_connection.status = (
                            SourceConnectionStatus.REAUTH_REQUIRED.value
                        )
                        mapping.source_connection.last_error_code = error_code[:64]
                        mapping.source_connection.last_error_summary = safe_message
                if sync_run is not None:
                    audit.record_event(
                        event_type="integration.sync_failed",
                        resource_type="source_sync_run",
                        actor_user_id=None,
                        organisation_id=sync_run.organisation_id,
                        project_id=sync_run.project_id,
                        resource_id=str(sync_run.id),
                        outcome=AuditOutcome.ERROR.value,
                        metadata={
                            "job_id": str(job.id),
                            "attempt_count": attempt_count,
                            "error_code": error_code[:64],
                            "requires_reauth": requires_reauth,
                        },
                        message="Source sync run failed permanently.",
                        level=logging.ERROR,
                    )
            session.commit()
