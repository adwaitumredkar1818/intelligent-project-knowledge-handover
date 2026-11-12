"""Domain service for evidence upload, provenance retention, access control, and deletion."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnprocessableEntityError,
)
from app.core.security import utc_now
from app.models.enums import (
    AuditOutcome,
    BackgroundJobType,
    EvidenceCategory,
    EvidenceIndexingStatus,
    EvidenceProcessingStatus,
    EvidenceSourceType,
    OrganisationStatus,
    ProjectStatus,
)
from app.models.evidence import EvidenceItem
from app.models.job import BackgroundJob
from app.repositories.chunk import EvidenceChunkRepository
from app.repositories.evidence import EvidenceRepository
from app.repositories.job import BackgroundJobRepository
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.evidence import (
    BackgroundJobResponse,
    DocumentUploadResponse,
    EvidenceChunkDetailResponse,
    EvidenceDetailResponse,
    EvidenceExtractedContentResponse,
    EvidenceListResponse,
    EvidenceMetricsResponse,
    EvidencePageContentResponse,
    EvidenceSummaryResponse,
)
from app.services.audit import AuditService
from app.services.document_validation import validate_uploaded_document
from app.services.integrations.access_policy import SourceAccessPolicyService
from app.services.rbac import AuthenticatedPrincipal, ProjectContext, RbacService
from app.services.storage import StorageBackend

logger = logging.getLogger("app.services.evidence")

_VALID_STATUSES = frozenset(item.value for item in EvidenceProcessingStatus)
_VALID_SOURCE_TYPES = frozenset(item.value for item in EvidenceSourceType)
_VALID_CATEGORIES = frozenset(item.value for item in EvidenceCategory)
_INDEXING_JOB_TYPES = frozenset(
    {
        BackgroundJobType.EVIDENCE_CHUNKING.value,
        BackgroundJobType.EVIDENCE_EMBEDDING.value,
        BackgroundJobType.EVIDENCE_INDEXING.value,
        BackgroundJobType.EVIDENCE_REINDEXING.value,
        BackgroundJobType.EVIDENCE_INDEX_CLEANUP.value,
    }
)


def _pick_latest_jobs(
    jobs: list[BackgroundJob],
) -> tuple[BackgroundJob | None, BackgroundJob | None]:
    """Return `(latest_primary_job, latest_indexing_job)` preserving ingestion focus."""
    if not jobs:
        return None, None
    latest_indexing: BackgroundJob | None = None
    latest_primary: BackgroundJob | None = None
    for job in jobs:
        if job.job_type in _INDEXING_JOB_TYPES:
            if latest_indexing is None:
                latest_indexing = job
        elif latest_primary is None:
            latest_primary = job
        if latest_primary is not None and latest_indexing is not None:
            break
    if latest_primary is None:
        latest_primary = jobs[0]
    return latest_primary, latest_indexing


def to_background_job_response(job: BackgroundJob) -> BackgroundJobResponse:
    """Map BackgroundJob ORM row into a sanitised public schema."""
    return BackgroundJobResponse(
        id=job.id,
        organisation_id=job.organisation_id,
        project_id=job.project_id,
        evidence_id=job.evidence_id,
        job_type=job.job_type,
        status=job.status,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        error_code=job.error_code,
        error_message=job.error_message,
        result_json=job.result_json,
        next_retry_at=job.next_retry_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        duration_ms=job.duration_ms,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def to_evidence_summary_response(item: EvidenceItem) -> EvidenceSummaryResponse:
    """Map EvidenceItem ORM row while strictly withholding private storage details."""
    primary_job, indexing_job = _pick_latest_jobs(list(item.jobs or []))
    latest_job = to_background_job_response(primary_job) if primary_job is not None else None
    latest_indexing_job = (
        to_background_job_response(indexing_job) if indexing_job is not None else None
    )
    return EvidenceSummaryResponse(
        id=item.id,
        organisation_id=item.organisation_id,
        project_id=item.project_id,
        uploaded_by_user_id=item.uploaded_by_user_id,
        source_type=item.source_type,
        source_provider=item.source_provider,
        category=item.category,
        source_external_id=item.source_external_id,
        source_url=item.source_url,
        source_author_identity=item.source_author_identity,
        title=item.title,
        original_filename=item.original_filename,
        mime_type=item.mime_type,
        file_size_bytes=item.file_size_bytes,
        content_hash=item.content_hash,
        acl_scope=item.acl_scope,
        source_created_at=item.source_created_at,
        source_updated_at=item.source_updated_at,
        extracted_at=item.extracted_at,
        last_synced_at=item.last_synced_at,
        processing_status=item.processing_status,
        extraction_method=item.extraction_method,
        page_count=item.page_count,
        ocr_pages_count=item.ocr_pages_count,
        truncated_pages_count=item.truncated_pages_count,
        error_code=item.error_code,
        error_message=item.error_message,
        indexing_status=item.indexing_status,
        chunk_count=item.chunk_count,
        indexed_at=item.indexed_at,
        embedding_model=item.embedding_model,
        index_version=item.index_version,
        index_error_code=item.index_error_code,
        index_error_message=item.index_error_message,
        metadata_json=dict(item.metadata_json or {}),
        latest_job=latest_job,
        latest_indexing_job=latest_indexing_job,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def to_evidence_detail_response(item: EvidenceItem) -> EvidenceDetailResponse:
    """Map detailed EvidenceItem with separated extracted text & pages."""
    summary = to_evidence_summary_response(item)
    extracted_content: EvidenceExtractedContentResponse | None = None
    if item.content is not None:
        extracted_content = EvidenceExtractedContentResponse(
            char_count=item.content.char_count,
            word_count=item.content.word_count,
            extraction_warnings=list(item.content.extraction_warnings or []),
            extracted_text=item.content.extracted_text,
            pages=[
                EvidencePageContentResponse(
                    page_number=page.page_number,
                    extraction_outcome=page.extraction_outcome,
                    ocr_applied=page.ocr_applied,
                    ocr_truncated=page.ocr_truncated,
                    text_content=page.text_content,
                    char_count=page.char_count,
                    structured_metadata=dict(page.structured_metadata or {}),
                )
                for page in item.pages
            ],
        )

    can_download = bool(item.storage_object_key and item.deleted_at is None)
    download_url = f"/api/v1/evidence/{item.id}/download" if can_download else None

    chunks_list = [
        EvidenceChunkDetailResponse(
            id=c.id,
            chunk_index=c.chunk_index,
            content_text=c.chunk_text,
            chunk_type=c.chunk_type,
            section_title=c.section_title,
            page_number=c.page_number,
            char_length=c.char_count,
            word_count=c.token_estimate,
        )
        for c in (item.chunks or [])
    ]

    return EvidenceDetailResponse(
        **summary.model_dump(),
        extracted_content=extracted_content,
        jobs=[to_background_job_response(job) for job in item.jobs],
        can_download=can_download,
        download_url=download_url,
        chunks=chunks_list,
    )


@dataclass(frozen=True, slots=True)
class UploadDocumentResult:
    """Carrier containing response payload plus created vs duplicate status."""

    payload: DocumentUploadResponse
    created: bool


class EvidenceService:
    """Orchestrates validated document ingestion, tenant isolation, ACL checks, and deletion."""

    def __init__(
        self,
        *,
        session: Session,
        settings: Settings,
        evidence_repository: EvidenceRepository,
        job_repository: BackgroundJobRepository,
        storage_backend: StorageBackend,
        rbac_service: RbacService,
        audit_service: AuditService,
    ) -> None:
        self._session = session
        self._settings = settings
        self._evidence_repo = evidence_repository
        self._job_repo = job_repository
        self._storage = storage_backend
        self._rbac = rbac_service
        self._audit = audit_service
        self._source_acl = SourceAccessPolicyService()

    def _require_project_mutable(self, project_ctx: ProjectContext) -> None:
        if project_ctx.organisation.status != OrganisationStatus.ACTIVE.value:
            raise ConflictError(
                f"Organisation is '{project_ctx.organisation.status}' and cannot modify evidence.",
                code="ORGANISATION_NOT_ACTIVE",
            )
        if project_ctx.project.status == ProjectStatus.ARCHIVED.value:
            raise ConflictError(
                "Project workspace is archived and cannot modify evidence.",
                code="PROJECT_ARCHIVED",
            )

    def _record_denied_and_commit(
        self,
        *,
        event_type: str,
        actor_user_id: uuid.UUID,
        organisation_id: uuid.UUID | None,
        project_id: uuid.UUID | None,
        evidence_id: uuid.UUID,
        message: str,
    ) -> None:
        self._audit.record_event(
            event_type=event_type,
            resource_type="evidence_item",
            actor_user_id=actor_user_id,
            organisation_id=organisation_id,
            project_id=project_id,
            resource_id=str(evidence_id),
            outcome=AuditOutcome.DENIED.value,
            message=message,
            level=logging.WARNING,
        )
        self._session.commit()

    def _enforce_future_source_acl(
        self,
        *,
        evidence: EvidenceItem,
        project_ctx: ProjectContext,
    ) -> None:
        """Fail-closed delegated source ACL check before evidence access."""
        self._source_acl.enforce_evidence_access(
            evidence=evidence,
            project_ctx=project_ctx,
            session=self._session,
            audit_service=self._audit,
        )

    def _resolve_accessible_evidence(
        self,
        *,
        evidence_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
        detailed: bool = False,
        require_read_permission: bool = True,
    ) -> tuple[EvidenceItem, ProjectContext]:
        evidence = (
            self._evidence_repo.get_by_id_detail(evidence_id)
            if detailed
            else self._evidence_repo.get_by_id(evidence_id)
        )
        if evidence is None:
            raise NotFoundError("Evidence item was not found.", code="EVIDENCE_NOT_FOUND")

        try:
            project_ctx = self._rbac.resolve_project_context(
                project_id=evidence.project_id,
                principal=principal,
            )
        except NotFoundError as exc:
            raise NotFoundError("Evidence item was not found.", code="EVIDENCE_NOT_FOUND") from exc

        if require_read_permission and not project_ctx.has_permission("project.read"):
            self._record_denied_and_commit(
                event_type="evidence.access_denied",
                actor_user_id=principal.user.id,
                organisation_id=evidence.organisation_id,
                project_id=evidence.project_id,
                evidence_id=evidence.id,
                message="Denied evidence read due to missing project.read permission.",
            )
            raise ForbiddenError(
                "You do not have permission to read evidence in this project.",
                code="FORBIDDEN",
            )

        self._enforce_future_source_acl(evidence=evidence, project_ctx=project_ctx)
        return evidence, project_ctx

    def upload_document(
        self,
        *,
        project_ctx: ProjectContext,
        filename: str | None,
        declared_mime_type: str | None,
        raw_bytes: bytes,
    ) -> UploadDocumentResult:
        """Validate, deduplicate within project scope, encrypt at rest, and queue extraction."""
        self._require_project_mutable(project_ctx)

        validated = validate_uploaded_document(
            filename=filename,
            declared_mime_type=declared_mime_type,
            raw_bytes=raw_bytes,
            max_upload_size_bytes=self._settings.ingestion.max_upload_size_bytes,
            max_document_pages=self._settings.ingestion.max_document_pages,
        )

        # Deduplication is strictly scoped to active items inside THIS project only.
        existing = self._evidence_repo.find_active_duplicate(
            project_id=project_ctx.project.id,
            content_hash=validated.content_hash,
        )
        if existing is not None:
            self._audit.record_event(
                event_type="evidence.duplicate_upload_detected",
                resource_type="evidence_item",
                actor_user_id=project_ctx.principal.user.id,
                organisation_id=project_ctx.organisation.id,
                project_id=project_ctx.project.id,
                resource_id=str(existing.id),
                metadata={
                    "content_hash": validated.content_hash,
                    "original_filename": validated.original_filename,
                },
                message="Matched active project duplicate document via SHA-256 checksum.",
            )
            self._session.commit()
            detailed_existing = self._evidence_repo.get_by_id_detail(existing.id) or existing
            dup_primary, _ = _pick_latest_jobs(list(detailed_existing.jobs or []))
            latest_job = (
                to_background_job_response(dup_primary) if dup_primary is not None else None
            )
            return UploadDocumentResult(
                payload=DocumentUploadResponse(
                    evidence=to_evidence_summary_response(detailed_existing),
                    job=latest_job,
                    duplicate_detected=True,
                ),
                created=False,
            )

        evidence_id = uuid.uuid4()
        stored = self._storage.store_encrypted_bytes(
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            data=validated.raw_bytes,
        )

        try:
            item = self._evidence_repo.create_evidence_item(
                evidence_id=evidence_id,
                organisation_id=project_ctx.organisation.id,
                project_id=project_ctx.project.id,
                uploaded_by_user_id=project_ctx.principal.user.id,
                source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
                source_provider="local_upload",
                category=validated.category,
                source_external_id=f"upload:{evidence_id}",
                source_url=None,
                source_author_identity=(
                    validated.source_author_identity or project_ctx.principal.user.email
                ),
                title=(
                    validated.initial_metadata.get("embedded_title")
                    or validated.original_filename
                ),
                original_filename=validated.original_filename,
                mime_type=validated.mime_type,
                file_size_bytes=validated.file_size_bytes,
                content_hash=validated.content_hash,
                storage_provider=stored.storage_provider,
                storage_object_key=stored.storage_object_key,
                encryption_algorithm=stored.encryption_algorithm,
                encryption_key_id=stored.encryption_key_id,
                source_created_at=validated.source_created_at,
                source_updated_at=validated.source_updated_at,
                processing_status=EvidenceProcessingStatus.QUEUED.value,
                page_count=validated.page_count,
                metadata_json=validated.initial_metadata,
            )
            job = self._job_repo.create_job(
                organisation_id=project_ctx.organisation.id,
                project_id=project_ctx.project.id,
                evidence_id=item.id,
                triggered_by_user_id=project_ctx.principal.user.id,
                job_type=BackgroundJobType.DOCUMENT_INGESTION.value,
                max_attempts=self._settings.ingestion.worker_max_attempts,
                payload_json={
                    "category": validated.category,
                    "mime_type": validated.mime_type,
                },
            )
            self._audit.record_event(
                event_type="evidence.uploaded",
                resource_type="evidence_item",
                actor_user_id=project_ctx.principal.user.id,
                organisation_id=project_ctx.organisation.id,
                project_id=project_ctx.project.id,
                resource_id=str(item.id),
                metadata={
                    "category": validated.category,
                    "mime_type": validated.mime_type,
                    "file_size_bytes": validated.file_size_bytes,
                    "content_hash": validated.content_hash,
                    "job_id": str(job.id),
                },
                message="Uploaded and encrypted document into private project storage.",
            )
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            self._storage.delete_object(storage_object_key=stored.storage_object_key)
            concurrent_existing = self._evidence_repo.find_active_duplicate(
                project_id=project_ctx.project.id,
                content_hash=validated.content_hash,
            )
            if concurrent_existing is not None:
                detailed_concurrent = (
                    self._evidence_repo.get_by_id_detail(concurrent_existing.id)
                    or concurrent_existing
                )
                dup_primary, _ = _pick_latest_jobs(list(detailed_concurrent.jobs or []))
                latest_job = (
                    to_background_job_response(dup_primary) if dup_primary is not None else None
                )
                return UploadDocumentResult(
                    payload=DocumentUploadResponse(
                        evidence=to_evidence_summary_response(detailed_concurrent),
                        job=latest_job,
                        duplicate_detected=True,
                    ),
                    created=False,
                )
            raise
        except Exception:
            self._session.rollback()
            self._storage.delete_object(storage_object_key=stored.storage_object_key)
            raise

        self._session.refresh(item)
        self._session.refresh(job)
        refreshed = self._evidence_repo.get_by_id_detail(item.id) or item
        return UploadDocumentResult(
            payload=DocumentUploadResponse(
                evidence=to_evidence_summary_response(refreshed),
                job=to_background_job_response(job),
                duplicate_detected=False,
            ),
            created=True,
        )

    def list_project_evidence(
        self,
        *,
        project_ctx: ProjectContext,
        processing_status: str | None = None,
        source_type: str | None = None,
        category: str | None = None,
        q: str | None = None,
        provider: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> EvidenceListResponse:
        """List active evidence items inside one authorised project workspace."""
        if processing_status is not None and (
            processing_status not in _VALID_STATUSES
            or processing_status == EvidenceProcessingStatus.DELETED.value
        ):
            raise BadRequestError(
                "Unsupported processing_status filter value.",
                code="INVALID_FILTER",
            )
        if source_type is not None and source_type not in _VALID_SOURCE_TYPES:
            raise BadRequestError("Unsupported source_type filter value.", code="INVALID_FILTER")
        if category is not None and category not in _VALID_CATEGORIES:
            raise BadRequestError("Unsupported category filter value.", code="INVALID_FILTER")

        items, total = self._evidence_repo.list_for_project(
            project_id=project_ctx.project.id,
            processing_status=processing_status,
            source_type=source_type,
            category=category,
            q=q,
            provider=provider,
            viewer_user_id=project_ctx.principal.user.id,
            has_project_manage=project_ctx.has_permission("project.manage"),
            enforce_source_acl=True,
            limit=limit,
            offset=offset,
        )
        return EvidenceListResponse(
            items=[to_evidence_summary_response(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    def download_evidence_content(
        self,
        *,
        evidence_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
    ) -> tuple[bytes, str, str]:
        """Verify project & source ACL permissions, decrypt at rest, and return raw file bytes."""
        evidence, _ = self._resolve_accessible_evidence(
            evidence_id=evidence_id,
            principal=principal,
            detailed=False,
            require_read_permission=True,
        )
        if not evidence.storage_object_key:
            raise NotFoundError(
                "Evidence item has no stored document object.",
                code="NO_STORAGE_OBJECT",
            )

        raw_bytes = self._storage.read_decrypted_bytes(
            storage_object_key=evidence.storage_object_key,
            organisation_id=evidence.organisation_id,
            project_id=evidence.project_id,
        )
        filename = evidence.original_filename or f"evidence-{evidence.id}"
        mime_type = evidence.mime_type or "application/octet-stream"
        return raw_bytes, filename, mime_type

    def get_project_evidence_metrics(
        self,
        *,
        project_ctx: ProjectContext,
    ) -> EvidenceMetricsResponse:
        """Aggregate evidence item counts, categories, and bytes for Panel B header."""
        if not project_ctx.has_permission("project.read"):
            raise ForbiddenError(
                "You do not have permission to read evidence in this project.",
                code="FORBIDDEN",
            )
        data = self._evidence_repo.get_project_evidence_metrics(project_ctx.project.id)
        return EvidenceMetricsResponse(
            total_items=data["total_items"],
            total_documents=data["total_documents"],
            total_bytes=data["total_bytes"],
            by_provider=data["by_provider"],
            by_status=data["by_status"],
        )

    def get_evidence_detail(
        self,
        *,
        evidence_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
    ) -> EvidenceDetailResponse:
        """Retrieve one evidence item and separated extracted content after permission checks."""
        evidence, _ = self._resolve_accessible_evidence(
            evidence_id=evidence_id,
            principal=principal,
            detailed=True,
            require_read_permission=True,
        )

        if (not evidence.chunks or len(evidence.chunks) == 0) and evidence.storage_object_key:
            try:
                raw_bytes = self._storage.read_decrypted_bytes(
                    storage_object_key=evidence.storage_object_key,
                    organisation_id=evidence.organisation_id,
                    project_id=evidence.project_id,
                )
                text = ""
                if evidence.category == EvidenceCategory.PDF_DOCUMENT.value or (evidence.mime_type or "").endswith("pdf"):
                    import pymupdf
                    with pymupdf.Document(stream=raw_bytes, filetype="pdf") as doc:
                        text = "\n".join(page.get_text() for page in doc).strip()
                elif evidence.category == EvidenceCategory.DOCX_DOCUMENT.value or "wordprocessing" in (evidence.mime_type or ""):
                    import io
                    import docx
                    parsed = docx.Document(io.BytesIO(raw_bytes))
                    text = "\n".join(p.text for p in parsed.paragraphs if p.text).strip()

                if text:
                    import hashlib
                    from app.models.evidence import EvidenceChunk

                    chunk = EvidenceChunk(
                        organisation_id=evidence.organisation_id,
                        project_id=evidence.project_id,
                        evidence_id=evidence.id,
                        chunk_index=0,
                        chunk_type="text_segment",
                        chunk_text=text,
                        chunk_content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                        char_count=len(text),
                        token_estimate=len(text.split()),
                        page_number=1,
                        source_type=evidence.source_type,
                        acl_scope=evidence.acl_scope,
                    )
                    self._session.add(chunk)
                    self._session.commit()
                    self._session.refresh(evidence)
            except Exception as exc:
                logger.warning("On-demand chunk extraction skipped: %s", exc)

        return to_evidence_detail_response(evidence)

    def delete_evidence(
        self,
        *,
        evidence_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
    ) -> None:
        """Logically delete an evidence item, cancel pending jobs, and purge encrypted object."""
        evidence, project_ctx = self._resolve_accessible_evidence(
            evidence_id=evidence_id,
            principal=principal,
            detailed=False,
            require_read_permission=False,
        )
        self._require_project_mutable(project_ctx)

        is_manager = project_ctx.has_permission("project.manage")
        is_owner_contributor = (
            evidence.uploaded_by_user_id == principal.user.id
            and project_ctx.has_permission("project.evidence.contribute")
        )
        if not (is_manager or is_owner_contributor):
            self._record_denied_and_commit(
                event_type="evidence.delete_denied",
                actor_user_id=principal.user.id,
                organisation_id=evidence.organisation_id,
                project_id=evidence.project_id,
                evidence_id=evidence.id,
                message=(
                    "Denied evidence deletion without project.manage or owner contributor rights."
                ),
            )
            raise ForbiddenError(
                "You do not have permission to delete this evidence item.",
                code="FORBIDDEN",
            )

        now = utc_now()
        storage_key = evidence.storage_object_key
        cancelled_jobs = self._job_repo.cancel_pending_jobs_for_evidence(
            evidence_id=evidence.id,
            now=now,
        )
        deleted_vector_ids = EvidenceChunkRepository(self._session).delete_chunks_for_evidence(
            evidence.id
        )
        KnowledgeRepository(self._session).mark_stale_for_evidence(
            evidence_id=evidence.id,
            reason="supporting_evidence_deleted",
            now=now,
        )
        evidence.processing_status = EvidenceProcessingStatus.DELETED.value
        evidence.indexing_status = EvidenceIndexingStatus.DELETED.value
        evidence.chunk_count = 0
        evidence.index_error_code = None
        evidence.index_error_message = None
        evidence.deleted_at = now
        evidence.deleted_by_user_id = principal.user.id

        cleanup_job = self._job_repo.create_job(
            organisation_id=evidence.organisation_id,
            project_id=evidence.project_id,
            evidence_id=evidence.id,
            triggered_by_user_id=principal.user.id,
            job_type=BackgroundJobType.EVIDENCE_INDEX_CLEANUP.value,
            max_attempts=self._settings.ingestion.worker_max_attempts,
            priority=50,
            payload_json={
                "evidence_id": str(evidence.id),
                "vector_ids": deleted_vector_ids,
            },
        )

        self._audit.record_event(
            event_type="evidence.deleted",
            resource_type="evidence_item",
            actor_user_id=principal.user.id,
            organisation_id=evidence.organisation_id,
            project_id=evidence.project_id,
            resource_id=str(evidence.id),
            metadata={
                "category": evidence.category,
                "content_hash": evidence.content_hash,
                "cancelled_jobs_count": cancelled_jobs,
                "cleanup_job_id": str(cleanup_job.id),
            },
            message="Logically deleted evidence item, purged chunks, and queued vector cleanup.",
        )
        self._session.commit()

        if storage_key:
            self._storage.delete_object(storage_object_key=storage_key)

    def reprocess_evidence(
        self,
        *,
        evidence_id: uuid.UUID,
        principal: AuthenticatedPrincipal,
    ) -> BackgroundJobResponse:
        """Enqueue a safe re-extraction job for failed or partially extracted documents."""
        evidence, project_ctx = self._resolve_accessible_evidence(
            evidence_id=evidence_id,
            principal=principal,
            detailed=False,
            require_read_permission=True,
        )
        self._require_project_mutable(project_ctx)

        can_reprocess = project_ctx.has_permission("project.manage") or (
            project_ctx.project_membership is not None
            and project_ctx.has_permission("project.evidence.contribute")
        )
        if not can_reprocess:
            self._record_denied_and_commit(
                event_type="evidence.reprocess_denied",
                actor_user_id=principal.user.id,
                organisation_id=evidence.organisation_id,
                project_id=evidence.project_id,
                evidence_id=evidence.id,
                message="Denied evidence reprocess due to insufficient project permissions.",
            )
            raise ForbiddenError(
                "You do not have permission to reprocess this evidence item.",
                code="FORBIDDEN",
            )

        if evidence.source_type != EvidenceSourceType.DOCUMENT_UPLOAD.value:
            raise BadRequestError(
                "Only uploaded document evidence supports extraction reprocessing.",
                code="UNSUPPORTED_REPROCESS_SOURCE",
            )

        if evidence.processing_status not in {
            EvidenceProcessingStatus.FAILED.value,
            EvidenceProcessingStatus.PARTIALLY_EXTRACTED.value,
        }:
            raise ConflictError(
                f"Evidence item in status '{evidence.processing_status}' cannot be reprocessed.",
                code="INVALID_EVIDENCE_STATE",
            )

        if self._job_repo.has_active_job_for_evidence(
            evidence_id=evidence.id,
            job_type=BackgroundJobType.DOCUMENT_INGESTION.value,
        ):
            raise ConflictError(
                "An active extraction job is already queued or running for this item.",
                code="JOB_ALREADY_ACTIVE",
            )

        if not evidence.storage_object_key or not self._storage.exists(
            storage_object_key=evidence.storage_object_key
        ):
            raise UnprocessableEntityError(
                "Original encrypted upload object is missing and cannot be reprocessed.",
                code="STORAGE_OBJECT_MISSING",
            )

        evidence.processing_status = EvidenceProcessingStatus.QUEUED.value
        evidence.error_code = None
        evidence.error_message = None
        evidence.indexing_status = EvidenceIndexingStatus.NOT_INDEXED.value
        evidence.index_error_code = None
        evidence.index_error_message = None

        job = self._job_repo.create_job(
            organisation_id=evidence.organisation_id,
            project_id=evidence.project_id,
            evidence_id=evidence.id,
            triggered_by_user_id=principal.user.id,
            job_type=BackgroundJobType.DOCUMENT_INGESTION.value,
            max_attempts=self._settings.ingestion.worker_max_attempts,
            payload_json={
                "category": evidence.category,
                "mime_type": evidence.mime_type,
                "reprocess": True,
            },
        )
        self._audit.record_event(
            event_type="evidence.reprocess_queued",
            resource_type="evidence_item",
            actor_user_id=principal.user.id,
            organisation_id=evidence.organisation_id,
            project_id=evidence.project_id,
            resource_id=str(evidence.id),
            metadata={"job_id": str(job.id)},
            message="Queued manual reprocessing job using preserved original upload.",
        )
        self._session.commit()
        self._session.refresh(job)
        return to_background_job_response(job)
