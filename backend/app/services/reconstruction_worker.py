"""PostgreSQL-backed background worker executing Phase 2.6 knowledge extraction runs."""

from __future__ import annotations

import logging
import socket
import time
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import ExtractionSettings, IngestionSettings
from app.core.exceptions import AppError
from app.core.logging import redact_sensitive_text
from app.core.security import utc_now
from app.models.enums import (
    AuditOutcome,
    BackgroundJobStatus,
    BackgroundJobType,
    EvidenceProcessingStatus,
    ExtractionRunStatus,
    KnowledgeCategory,
    OrganisationStatus,
    ProjectStatus,
    UserStatus,
)
from app.repositories.audit import AuditLogRepository
from app.repositories.chunk import EvidenceChunkRepository
from app.repositories.evidence import EvidenceRepository
from app.repositories.job import BackgroundJobRepository
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.organisation import OrganisationRepository
from app.repositories.project import ProjectRepository
from app.repositories.rbac import RbacRepository
from app.repositories.user import UserRepository
from app.services.audit import AuditService
from app.services.extraction_prompts import (
    ChunkPromptInput,
    build_category_extraction_prompt,
    build_chunk_prompt_input,
    build_json_repair_prompt,
    partition_chunks_into_batches,
)
from app.services.integrations.access_policy import SourceAccessPolicyService
from app.services.knowledge_validator import KnowledgeCandidateValidator
from app.services.llm import (
    LLMExecutionError,
    LLMGenerationRequest,
    LLMGenerationResult,
    StructuredLLMClient,
)
from app.services.rbac import RbacService

logger = logging.getLogger("app.services.reconstruction_worker")

_ELIGIBLE_EVIDENCE_STATUSES: frozenset[str] = frozenset(
    {
        EvidenceProcessingStatus.EXTRACTED.value,
        EvidenceProcessingStatus.PARTIALLY_EXTRACTED.value,
    }
)


def _default_worker_id() -> str:
    return f"{socket.gethostname()[:48]}-know-{uuid.uuid4().hex[:8]}"


def _sanitise_error(message: str) -> str:
    return redact_sensitive_text(message).strip()[:500]


@dataclass(frozen=True, slots=True)
class _ClaimedExtractionJob:
    job_id: uuid.UUID
    run_id: uuid.UUID
    organisation_id: uuid.UUID
    project_id: uuid.UUID
    triggered_by_user_id: uuid.UUID | None
    attempt_count: int
    max_attempts: int
    evidence_ids: tuple[uuid.UUID, ...]
    categories: tuple[KnowledgeCategory, ...]
    force_rerun: bool
    include_synthetic: bool


@dataclass(slots=True)
class _RunAccumulator:
    processed_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    chunks_evaluated: int = 0
    batches_executed: int = 0
    candidates_generated: int = 0
    claims_persisted: int = 0
    claims_rejected_ungrounded: int = 0
    duplicates_merged: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    warnings: list[str] = None  # type: ignore[assignment]
    last_retryable_error: LLMExecutionError | None = None
    last_fatal_error: LLMExecutionError | None = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


class ReconstructionWorkerService:
    """Claims queued `knowledge_reconstruction` jobs and runs verified structured extraction."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        llm_client: StructuredLLMClient,
        extraction_settings: ExtractionSettings,
        ingestion_settings: IngestionSettings,
        validator: KnowledgeCandidateValidator | None = None,
        access_policy_service: SourceAccessPolicyService | None = None,
        worker_id: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._llm = llm_client
        self._extraction_settings = extraction_settings
        self._ingestion_settings = ingestion_settings
        self._validator = validator or KnowledgeCandidateValidator()
        self._access_policy = access_policy_service or SourceAccessPolicyService()
        self._worker_id = worker_id or _default_worker_id()

    @property
    def worker_id(self) -> str:
        """Identifier recorded on claimed job leases."""
        return self._worker_id

    def drain_pending_jobs(self, *, max_jobs: int = 50) -> int:
        """Claim and execute ready knowledge extraction jobs up to `max_jobs`."""
        processed = 0
        while processed < max_jobs:
            if not self.process_next_job():
                break
            processed += 1
        return processed

    def process_next_job(self) -> bool:
        """Claim and execute one ready knowledge reconstruction job; return True if handled."""
        claimed = self._claim_job()
        if claimed is None:
            return False

        started_perf = time.perf_counter()
        try:
            self._execute_claimed_run(claimed=claimed, started_perf=started_perf)
        except Exception as exc:  # pragma: no cover - defensive runtime safeguard
            elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
            logger.exception("Unhandled error inside knowledge reconstruction worker.")
            self._fail_run_unexpected(
                claimed=claimed,
                duration_ms=elapsed_ms,
                error_code="RECONSTRUCTION_WORKER_UNEXPECTED",
                error_message=f"Unexpected extraction error: {type(exc).__name__}",
                retryable=claimed.attempt_count < claimed.max_attempts,
            )
        return True

    def _claim_job(self) -> _ClaimedExtractionJob | None:
        now = utc_now()
        with self._session_factory() as session:
            job_repo = BackgroundJobRepository(session)
            knowledge_repo = KnowledgeRepository(session)

            job = job_repo.claim_next_job(
                worker_id=self._worker_id,
                lease_seconds=self._ingestion_settings.worker_lease_seconds,
                now=now,
                job_types=(BackgroundJobType.KNOWLEDGE_RECONSTRUCTION.value,),
            )
            if job is None:
                session.commit()
                return None

            payload = dict(job.payload_json or {})
            run = None
            raw_run_id = payload.get("run_id")
            if raw_run_id:
                try:
                    run = knowledge_repo.get_run_by_id(uuid.UUID(str(raw_run_id)))
                except ValueError:
                    run = None

            if run is None or run.status == ExtractionRunStatus.CANCELLED.value:
                job.status = BackgroundJobStatus.CANCELLED.value
                job.completed_at = now
                job.error_code = "EXTRACTION_RUN_UNAVAILABLE"
                job.error_message = "Associated knowledge extraction run is missing or cancelled."
                job.locked_by = None
                job.lease_expires_at = None
                session.commit()
                return None

            ev_ids: list[uuid.UUID] = []
            for raw_ev_id in payload.get("evidence_ids") or []:
                try:
                    ev_ids.append(uuid.UUID(str(raw_ev_id)))
                except ValueError:
                    continue
            if not ev_ids and run.evidence_id is not None:
                ev_ids.append(run.evidence_id)

            categories: list[KnowledgeCategory] = []
            for raw_cat in payload.get("categories") or run.target_categories or []:
                try:
                    categories.append(KnowledgeCategory(str(raw_cat)))
                except ValueError:
                    continue
            if not categories:
                categories = list(KnowledgeCategory)

            run.status = ExtractionRunStatus.RUNNING.value
            run.started_at = run.started_at or now
            run.model_name = self._llm.model_name
            run.error_code = None
            run.error_message = None

            claimed = _ClaimedExtractionJob(
                job_id=job.id,
                run_id=run.id,
                organisation_id=run.organisation_id,
                project_id=run.project_id,
                triggered_by_user_id=run.triggered_by_user_id or job.triggered_by_user_id,
                attempt_count=int(job.attempt_count),
                max_attempts=int(job.max_attempts),
                evidence_ids=tuple(ev_ids),
                categories=tuple(categories),
                force_rerun=bool(payload.get("force_rerun", False)),
                include_synthetic=bool(payload.get("include_synthetic", run.is_synthetic)),
            )
            session.commit()
            return claimed

    def _verify_triggering_actor_access(
        self,
        session: Session,
        *,
        claimed: _ClaimedExtractionJob,
    ) -> tuple[bool, bool, str | None]:
        """Re-verify user/org/project permissions immediately prior to LLM execution.

        Returns `(allowed, has_project_manage, denial_reason)`.
        """
        org_repo = OrganisationRepository(session)
        proj_repo = ProjectRepository(session)
        org = org_repo.get_by_id(claimed.organisation_id)
        proj = proj_repo.get_by_id(claimed.project_id)
        if org is None or org.status != OrganisationStatus.ACTIVE.value:
            return False, False, "Organisation is inactive or missing."
        if proj is None or proj.status == ProjectStatus.ARCHIVED.value:
            return False, False, "Project is archived or missing."

        if claimed.triggered_by_user_id is None:
            return True, True, None

        user_repo = UserRepository(session)
        user = user_repo.get_by_id(claimed.triggered_by_user_id)
        if user is None or user.status != UserStatus.ACTIVE.value:
            return False, False, "Triggering user account is no longer active."

        rbac = RbacService(
            db_session=session,
            rbac_repository=RbacRepository(session),
            user_repository=user_repo,
            organisation_repository=org_repo,
            project_repository=proj_repo,
        )
        principal = rbac.resolve_principal(user=user, session_family_id=uuid.uuid4())
        try:
            proj_ctx = rbac.resolve_project_context(
                project_id=claimed.project_id,
                principal=principal,
            )
        except AppError as exc:
            return False, False, exc.message

        has_manage = proj_ctx.has_permission("project.manage")
        can_trigger = has_manage or (
            proj_ctx.project_membership is not None
            and proj_ctx.has_permission("project.evidence.contribute")
        )
        if not can_trigger:
            return (
                False,
                False,
                "Triggering user no longer holds project extraction permissions.",
            )
        return True, has_manage, None

    def _call_llm_with_json_retry(
        self,
        *,
        category: KnowledgeCategory,
        batch: list[ChunkPromptInput],
        acc: _RunAccumulator,
    ) -> LLMGenerationResult:
        prompt = build_category_extraction_prompt(
            category=category,
            chunks=batch,
            prompt_version=self._extraction_settings.prompt_version,
        )
        req = LLMGenerationRequest(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
        )
        max_attempts = 1 + max(0, int(self._extraction_settings.max_retries))
        last_exc: LLMExecutionError | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                res = self._llm.generate_json(req)
                acc.batches_executed += 1
                acc.prompt_tokens += res.prompt_tokens
                acc.completion_tokens += res.completion_tokens
                return res
            except LLMExecutionError as exc:
                acc.batches_executed += 1
                acc.prompt_tokens += exc.prompt_tokens
                acc.completion_tokens += exc.completion_tokens
                last_exc = exc
                is_json_repairable = exc.code in {
                    "LLM_INVALID_JSON",
                    "LLM_EMPTY_RESPONSE",
                    "LLM_TRUNCATED",
                }
                if is_json_repairable and attempt < max_attempts:
                    repair = build_json_repair_prompt(
                        category=category,
                        chunks=batch,
                        prior_error=exc.code,
                        prompt_version=self._extraction_settings.prompt_version,
                    )
                    req = LLMGenerationRequest(
                        system_prompt=repair.system_prompt,
                        user_prompt=repair.user_prompt,
                    )
                    continue
                raise

        if last_exc is None:  # pragma: no cover - loop always raises or returns
            raise RuntimeError("Unreachable LLM retry state.")
        raise last_exc

    def _execute_claimed_run(
        self,
        *,
        claimed: _ClaimedExtractionJob,
        started_perf: float,
    ) -> None:
        with self._session_factory() as session:
            allowed, has_project_manage, denial_reason = self._verify_triggering_actor_access(
                session,
                claimed=claimed,
            )
        if not allowed:
            elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
            self._finalize_denied_run(
                claimed=claimed,
                duration_ms=elapsed_ms,
                reason=denial_reason or "Permission check failed prior to extraction.",
            )
            return

        acc = _RunAccumulator()
        for evidence_id in claimed.evidence_ids:
            # 1. Load authorised snapshot strictly for ONE evidence item at a time.
            with self._session_factory() as session:
                ev = EvidenceRepository(session).get_by_id(evidence_id, include_deleted=False)
                if ev is None or ev.project_id != claimed.project_id:
                    acc.skipped_items += 1
                    continue
                if ev.processing_status not in _ELIGIBLE_EVIDENCE_STATUSES:
                    acc.skipped_items += 1
                    continue
                if claimed.triggered_by_user_id is not None and not (
                    self._access_policy.can_user_access_evidence(
                        evidence=ev,
                        user_id=claimed.triggered_by_user_id,
                        has_project_manage=has_project_manage,
                    )
                ):
                    acc.skipped_items += 1
                    if "skipped_revoked_or_restricted_evidence" not in acc.warnings:
                        acc.warnings.append("skipped_revoked_or_restricted_evidence")
                    continue

                is_synthetic = EvidenceChunkRepository.is_item_synthetic(ev)
                if is_synthetic and not claimed.include_synthetic:
                    acc.skipped_items += 1
                    continue

                chunks = EvidenceChunkRepository(session).list_chunks_for_evidence(ev.id)
                if not chunks:
                    acc.skipped_items += 1
                    continue

                chunk_inputs = [
                    build_chunk_prompt_input(chunk=chunk, evidence=ev) for chunk in chunks
                ]

            acc.chunks_evaluated += len(chunk_inputs)
            batches = partition_chunks_into_batches(
                chunk_inputs,
                max_chunks_per_batch=self._extraction_settings.max_chunks_per_batch,
                max_chars_per_batch=self._extraction_settings.max_chars_per_batch,
            )

            accepted_drafts: list[Any] = []
            evidence_had_error = False
            for batch in batches:
                for category in claimed.categories:
                    try:
                        llm_res = self._call_llm_with_json_retry(
                            category=category,
                            batch=batch,
                            acc=acc,
                        )
                    except LLMExecutionError as exc:
                        evidence_had_error = True
                        if exc.retryable:
                            acc.last_retryable_error = exc
                        else:
                            acc.last_fatal_error = exc
                        warn_tag = f"{category.value}:{exc.code}"
                        if warn_tag not in acc.warnings and len(acc.warnings) < 25:
                            acc.warnings.append(warn_tag)
                        continue

                    val_report = self._validator.validate_batch_response(
                        category=category,
                        parsed_json=llm_res.parsed_json,
                        supplied_chunks=batch,
                        is_synthetic=is_synthetic,
                    )
                    acc.candidates_generated += val_report.candidates_received
                    acc.claims_rejected_ungrounded += (
                        val_report.rejected_schema_count + val_report.rejected_ungrounded_count
                    )
                    for reason in val_report.rejection_reasons:
                        if reason not in acc.warnings and len(acc.warnings) < 25:
                            acc.warnings.append(reason)
                    accepted_drafts.extend(val_report.accepted_items)

            # 2. Persist validated drafts atomically for this evidence item
            with self._session_factory() as session:
                knowledge_repo = KnowledgeRepository(session)
                if claimed.force_rerun and not evidence_had_error:
                    knowledge_repo.mark_stale_for_evidence(
                        evidence_id=evidence_id,
                        reason="superseded_by_reextraction",
                        exclude_run_id=claimed.run_id,
                    )
                for draft in accepted_drafts:
                    _item, merged = knowledge_repo.upsert_validated_draft(
                        organisation_id=claimed.organisation_id,
                        project_id=claimed.project_id,
                        extraction_run_id=claimed.run_id,
                        model_name=self._llm.model_name,
                        prompt_version=self._extraction_settings.prompt_version,
                        draft=draft,
                    )
                    if merged:
                        acc.duplicates_merged += 1
                    else:
                        acc.claims_persisted += 1
                session.commit()

            if evidence_had_error:
                acc.failed_items += 1
            else:
                acc.processed_items += 1

        elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
        self._finalize_run(claimed=claimed, acc=acc, duration_ms=elapsed_ms)

    def _finalize_denied_run(
        self,
        *,
        claimed: _ClaimedExtractionJob,
        duration_ms: int,
        reason: str,
    ) -> None:
        now = utc_now()
        safe_reason = _sanitise_error(reason)
        with self._session_factory() as session:
            run = KnowledgeRepository(session).get_run_by_id(claimed.run_id)
            job = BackgroundJobRepository(session).get_by_id(claimed.job_id)
            audit = AuditService(audit_repository=AuditLogRepository(session))
            if run is not None:
                run.status = ExtractionRunStatus.FAILED.value
                run.error_code = "EXTRACTION_PERMISSION_REVOKED"
                run.error_message = safe_reason
                run.completed_at = now
                run.duration_ms = duration_ms
            if job is not None:
                job.status = BackgroundJobStatus.FAILED.value
                job.error_code = "EXTRACTION_PERMISSION_REVOKED"
                job.error_message = safe_reason
                job.completed_at = now
                job.duration_ms = duration_ms
                job.locked_by = None
                job.lease_expires_at = None
            audit.record_event(
                event_type="knowledge.extraction_denied_at_execution",
                resource_type="knowledge_extraction_run",
                actor_user_id=claimed.triggered_by_user_id,
                organisation_id=claimed.organisation_id,
                project_id=claimed.project_id,
                resource_id=str(claimed.run_id),
                outcome=AuditOutcome.DENIED.value,
                message=safe_reason,
                level=logging.WARNING,
            )
            session.commit()

    def _finalize_run(
        self,
        *,
        claimed: _ClaimedExtractionJob,
        acc: _RunAccumulator,
        duration_ms: int,
    ) -> None:
        now = utc_now()
        should_retry_job = (
            acc.processed_items == 0
            and acc.failed_items > 0
            and acc.last_retryable_error is not None
            and claimed.attempt_count < claimed.max_attempts
        )

        with self._session_factory() as session:
            run = KnowledgeRepository(session).get_run_by_id(claimed.run_id)
            job = BackgroundJobRepository(session).get_by_id(claimed.job_id)
            audit = AuditService(audit_repository=AuditLogRepository(session))

            summary_meta = {
                "run_id": str(claimed.run_id),
                "processed_evidence_items": acc.processed_items,
                "failed_evidence_items": acc.failed_items,
                "skipped_evidence_items": acc.skipped_items,
                "total_chunks_evaluated": acc.chunks_evaluated,
                "batches_executed": acc.batches_executed,
                "candidates_generated": acc.candidates_generated,
                "claims_persisted": acc.claims_persisted,
                "claims_rejected_ungrounded": acc.claims_rejected_ungrounded,
                "duplicates_merged": acc.duplicates_merged,
                "prompt_tokens": acc.prompt_tokens,
                "completion_tokens": acc.completion_tokens,
                "duration_ms": duration_ms,
            }

            if run is not None:
                run.processed_evidence_items += acc.processed_items
                run.failed_evidence_items = acc.failed_items
                run.skipped_evidence_items = acc.skipped_items
                run.total_chunks_evaluated += acc.chunks_evaluated
                run.batches_executed += acc.batches_executed
                run.candidates_generated += acc.candidates_generated
                run.claims_persisted += acc.claims_persisted
                run.claims_rejected_ungrounded += acc.claims_rejected_ungrounded
                run.duplicates_merged += acc.duplicates_merged
                run.prompt_tokens += acc.prompt_tokens
                run.completion_tokens += acc.completion_tokens
                merged_warnings = list(dict.fromkeys([*(run.warnings_json or []), *acc.warnings]))
                run.warnings_json = merged_warnings[:30]

            if should_retry_job:
                err = acc.last_retryable_error
                backoff = min(
                    3600,
                    self._ingestion_settings.worker_retry_base_seconds
                    * (2 ** max(0, claimed.attempt_count - 1)),
                )
                retry_code = (err.code if err else "LLM_RETRYABLE_ERROR")[:64]
                retry_msg = _sanitise_error(
                    err.message if err else "Transient LLM failure scheduled for retry."
                )
                if run is not None:
                    run.status = ExtractionRunStatus.QUEUED.value
                    run.error_code = retry_code
                    run.error_message = retry_msg
                if job is not None:
                    job.status = BackgroundJobStatus.QUEUED.value
                    job.next_retry_at = now + timedelta(seconds=backoff)
                    job.locked_by = None
                    job.lease_expires_at = None
                    job.error_code = retry_code
                    job.error_message = retry_msg
                    job.result_json = summary_meta
                audit.record_event(
                    event_type="knowledge.extraction_retry_scheduled",
                    resource_type="knowledge_extraction_run",
                    actor_user_id=claimed.triggered_by_user_id,
                    organisation_id=claimed.organisation_id,
                    project_id=claimed.project_id,
                    resource_id=str(claimed.run_id),
                    outcome=AuditOutcome.ERROR.value,
                    metadata={
                        **summary_meta,
                        "retry_delay_seconds": backoff,
                        "error_code": retry_code,
                    },
                    message="Scheduled retry for knowledge extraction due to transient LLM error.",
                    level=logging.WARNING,
                )
                session.commit()
                return

            total_failed = acc.failed_items
            safe_code: str | None = None
            safe_msg: str | None = None
            if total_failed > 0 and acc.processed_items == 0 and acc.claims_persisted == 0:
                final_run_status = ExtractionRunStatus.FAILED.value
                final_job_status = BackgroundJobStatus.FAILED.value
                err_obj = acc.last_retryable_error or acc.last_fatal_error
                safe_code = (err_obj.code if err_obj else "EXTRACTION_FAILED")[:64]
                safe_msg = _sanitise_error(
                    err_obj.message if err_obj else "Knowledge extraction failed across all items."
                )
            elif total_failed > 0:
                final_run_status = ExtractionRunStatus.PARTIALLY_COMPLETED.value
                final_job_status = BackgroundJobStatus.SUCCEEDED.value
                err_obj = acc.last_retryable_error or acc.last_fatal_error
                safe_code = (err_obj.code if err_obj else "EXTRACTION_PARTIAL")[:64]
                safe_msg = _sanitise_error(
                    err_obj.message if err_obj else "One or more batches failed during extraction."
                )
            else:
                final_run_status = ExtractionRunStatus.COMPLETED.value
                final_job_status = BackgroundJobStatus.SUCCEEDED.value
                safe_code = None
                safe_msg = None

            if run is not None:
                run.status = final_run_status
                run.completed_at = now
                run.duration_ms = duration_ms
                run.error_code = safe_code
                run.error_message = safe_msg
            if job is not None:
                job.status = final_job_status
                job.completed_at = now
                job.duration_ms = duration_ms
                job.locked_by = None
                job.lease_expires_at = None
                job.error_code = safe_code
                job.error_message = safe_msg
                job.result_json = summary_meta

            audit.record_event(
                event_type=(
                    "knowledge.extraction_failed"
                    if final_run_status == ExtractionRunStatus.FAILED.value
                    else "knowledge.extraction_completed"
                ),
                resource_type="knowledge_extraction_run",
                actor_user_id=claimed.triggered_by_user_id,
                organisation_id=claimed.organisation_id,
                project_id=claimed.project_id,
                resource_id=str(claimed.run_id),
                outcome=(
                    AuditOutcome.ERROR.value
                    if final_run_status == ExtractionRunStatus.FAILED.value
                    else AuditOutcome.SUCCESS.value
                ),
                metadata={**summary_meta, "run_status": final_run_status},
                message=(
                    safe_msg
                    or f"Completed knowledge extraction ({acc.claims_persisted} persisted, "
                    f"{acc.claims_rejected_ungrounded} rejected)."
                ),
                level=(
                    logging.ERROR
                    if final_run_status == ExtractionRunStatus.FAILED.value
                    else logging.INFO
                ),
            )
            session.commit()

    def _fail_run_unexpected(
        self,
        *,
        claimed: _ClaimedExtractionJob,
        duration_ms: int,
        error_code: str,
        error_message: str,
        retryable: bool,
    ) -> None:
        now = utc_now()
        safe_msg = _sanitise_error(error_message)
        with self._session_factory() as session:
            run = KnowledgeRepository(session).get_run_by_id(claimed.run_id)
            job = BackgroundJobRepository(session).get_by_id(claimed.job_id)
            if retryable:
                backoff = min(
                    3600,
                    self._ingestion_settings.worker_retry_base_seconds
                    * (2 ** max(0, claimed.attempt_count - 1)),
                )
                if run is not None:
                    run.status = ExtractionRunStatus.QUEUED.value
                    run.error_code = error_code[:64]
                    run.error_message = safe_msg
                if job is not None:
                    job.status = BackgroundJobStatus.QUEUED.value
                    job.next_retry_at = now + timedelta(seconds=backoff)
                    job.locked_by = None
                    job.lease_expires_at = None
                    job.error_code = error_code[:64]
                    job.error_message = safe_msg
            else:
                if run is not None:
                    run.status = ExtractionRunStatus.FAILED.value
                    run.completed_at = now
                    run.duration_ms = duration_ms
                    run.error_code = error_code[:64]
                    run.error_message = safe_msg
                if job is not None:
                    job.status = BackgroundJobStatus.FAILED.value
                    job.completed_at = now
                    job.duration_ms = duration_ms
                    job.locked_by = None
                    job.lease_expires_at = None
                    job.error_code = error_code[:64]
                    job.error_message = safe_msg
            session.commit()
