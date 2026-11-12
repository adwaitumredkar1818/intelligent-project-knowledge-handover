"""Evidence Workspace service managing sources, mappings, extraction, and library access."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.crypto import decrypt_token, encrypt_token
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.models.enums import (
    EvidenceProcessingStatus,
    EvidenceVerificationStatus,
    JobStatus,
    SourceProvider,
    SyncStatus,
)
from app.models.evidence import EvidenceItem, ProjectSourceMapping, SourceConnection
from app.repositories.evidence import EvidenceRepository
from app.schemas.evidence import (
    CreateProjectSourceMappingRequest,
    CreateSourceConnectionRequest,
    DocumentFileResponse,
    DocumentUploadResponse,
    EvidenceChunkResponse,
    EvidenceItemDetail,
    EvidenceItemSummary,
    EvidenceLibraryMetricsResponse,
    EvidenceListResponse,
    ProjectSourceMappingListResponse,
    ProjectSourceMappingResponse,
    SourceConnectionListResponse,
    SourceConnectionResponse,
    SyncJobListResponse,
    SyncJobResponse,
    UpdateSourceConnectionRequest,
)
from app.services.evidence.access import SourceAclService
from app.services.evidence.extractors import (
    DocxExtractor,
    PdfExtractor,
    TextChunker,
)
from app.services.evidence.storage import SecureStorageService
from app.services.integrations.github import GitHubIntegrationService
from app.services.integrations.jira import JiraIntegrationService

logger = logging.getLogger("app.evidence.service")


class EvidenceService:
    """Orchestrates Evidence Workspace operations across Panels A, B, and C."""

    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._repo = EvidenceRepository(db)
        self._storage = SecureStorageService(settings)
        self._acl = SourceAclService()
        self._pdf_extractor = PdfExtractor()
        self._docx_extractor = DocxExtractor()
        self._chunker = TextChunker()

    # -------------------------------------------------------------------------
    # Panel A: Source Connections & Mappings
    # -------------------------------------------------------------------------
    def create_source_connection(
        self,
        *,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: CreateSourceConnectionRequest,
    ) -> SourceConnectionResponse:
        """Register and persist a new external source connection with encrypted credentials."""
        encrypted_token = encrypt_token(
            payload.secret_token,
            self._settings.security.token_encryption_key,
        )

        scopes = list(payload.scopes)
        if payload.is_shared and "shared:organisation" not in scopes:
            scopes.append("shared:organisation")

        conn = self._repo.create_source_connection(
            organisation_id=organisation_id,
            connected_by_id=user_id,
            provider=payload.provider,
            account_identifier=payload.account_identifier,
            encrypted_access_token=encrypted_token,
            scopes=scopes,
        )
        self._db.commit()
        return self._to_source_connection_response(conn)

    def list_source_connections(
        self,
        *,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SourceConnectionListResponse:
        """List active connections accessible to this user within the organisation."""
        connections = self._repo.list_source_connections_for_org(
            organisation_id=organisation_id,
            user_id=user_id,
        )
        items = [self._to_source_connection_response(c) for c in connections]
        return SourceConnectionListResponse(items=items, total=len(items))

    def update_source_connection(
        self,
        *,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: UpdateSourceConnectionRequest,
    ) -> SourceConnectionResponse:
        """Update connection settings (only creator can modify)."""
        conn = self._repo.get_source_connection_by_id(connection_id)
        if conn is None:
            raise NotFoundError("Source connection not found.", code="SOURCE_NOT_FOUND")

        if conn.connected_by_id != user_id:
            raise ForbiddenError(
                "Only the user who connected this source can modify its settings.",
                code="SOURCE_OWNER_REQUIRED",
            )

        scopes = list(conn.scopes or [])
        if payload.scopes is not None:
            scopes = list(payload.scopes)

        if payload.is_shared is True and "shared:organisation" not in scopes:
            scopes.append("shared:organisation")
        elif payload.is_shared is False and "shared:organisation" in scopes:
            scopes.remove("shared:organisation")

        updated = self._repo.update_source_connection(
            conn,
            scopes=scopes,
        )
        self._db.commit()
        return self._to_source_connection_response(updated)

    def create_project_source_mapping(
        self,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: CreateProjectSourceMappingRequest,
    ) -> ProjectSourceMappingResponse:
        """Bind an external container (e.g. repo/board) to a project workspace."""
        conn = self._repo.get_source_connection_by_id(payload.source_connection_id)
        if conn is None:
            raise NotFoundError("Source connection not found.", code="SOURCE_NOT_FOUND")

        # Verify caller has source access
        if not self._acl.can_access_connection(user_id=user_id, connection=conn):
            raise ForbiddenError(
                "You do not have access to bind this private external source.",
                code="SOURCE_ACCESS_DENIED",
            )

        # Check existing mapping
        existing = self._repo.get_mapping_by_resource(
            project_id=project_id,
            external_resource_id=payload.external_resource_id,
        )
        if existing is not None:
            raise ConflictError(
                f"Resource '{payload.external_resource_id}' is already mapped to this project.",
                code="CONTAINER_ALREADY_MAPPED",
            )

        mapping = self._repo.create_project_source_mapping(
            project_id=project_id,
            source_connection_id=payload.source_connection_id,
            external_resource_id=payload.external_resource_id,
            external_resource_name=payload.external_resource_name,
            external_metadata=payload.external_metadata,
        )
        self._db.commit()

        reloaded = self._repo.get_mapping_by_id(mapping.id)
        if reloaded is None:
            raise NotFoundError("Failed to reload source mapping.", code="MAPPING_NOT_FOUND")
        return self._to_project_source_mapping_response(reloaded)

    def list_project_source_mappings(
        self,
        project_id: uuid.UUID,
    ) -> ProjectSourceMappingListResponse:
        """List all active container mappings configured for this project."""
        mappings = self._repo.list_mappings_for_project(project_id)
        items = [self._to_project_source_mapping_response(m) for m in mappings]
        return ProjectSourceMappingListResponse(items=items, total=len(items))

    def trigger_sync(
        self,
        *,
        mapping_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SyncJobResponse:
        """Queue a background sync job for a mapped external container."""
        mapping = self._repo.get_mapping_by_id(mapping_id)
        if mapping is None:
            raise NotFoundError("Project source mapping not found.", code="MAPPING_NOT_FOUND")

        has_access = self._acl.can_access_connection(
            user_id=user_id,
            connection=mapping.source_connection,
        )
        if not has_access:
            raise ForbiddenError(
                "You are not authorised to trigger sync on this private source.",
                code="SOURCE_ACCESS_DENIED",
            )

        job = self._repo.create_sync_job(
            project_id=mapping.project_id,
            source_mapping_id=mapping.id,
            job_type="full",
        )
        self._repo.update_mapping(mapping, sync_status=SyncStatus.SYNCING.value)
        self._db.commit()

        return SyncJobResponse(
            id=job.id,
            project_id=mapping.project_id,
            source_mapping_id=mapping.id,
            job_type=job.job_type,
            status=job.status,
            attempt_count=job.attempt_count,
            created_at=job.created_at,
        )

    def list_sync_jobs(self, mapping_id: uuid.UUID) -> SyncJobListResponse:
        """List sync job history for a container mapping."""
        jobs = self._repo.list_sync_jobs_for_mapping(mapping_id)
        items = [
            SyncJobResponse(
                id=j.id,
                project_id=j.project_id,
                source_mapping_id=j.source_mapping_id,
                job_type=j.job_type,
                status=j.status,
                attempt_count=j.attempt_count,
                error_message=j.error_message,
                started_at=j.started_at,
                completed_at=j.completed_at,
                created_at=j.created_at,
            )
            for j in jobs
        ]
        return SyncJobListResponse(items=items, total=len(items))

    # -------------------------------------------------------------------------
    # Document Upload & Processing Pipeline
    # -------------------------------------------------------------------------
    def upload_document(
        self,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        filename: str,
        content: bytes,
    ) -> DocumentUploadResponse:
        """Upload, encrypt, extract, and ingest a PDF or DOCX document."""
        # 1. Encrypt and persist file to disk
        storage_path, sha256_hash, byte_size, mime_type = self._storage.save_file(
            filename=filename,
            content=content,
        )

        # 2. Extract structured content based on extension
        ext = filename.lower()
        if ext.endswith(".pdf"):
            extraction = self._pdf_extractor.extract(content, filename=filename)
            provider_str = SourceProvider.PDF.value
            file_format = "pdf"
        elif ext.endswith(".docx"):
            extraction = self._docx_extractor.extract(content, filename=filename)
            provider_str = SourceProvider.DOCX.value
            file_format = "docx"
        else:
            raise BadRequestError(
                "Only PDF and DOCX documents are supported.",
                code="UNSUPPORTED_TYPE",
            )

        # 3. Create atomic EvidenceItem
        now = datetime.now(UTC)
        doc_uuid = uuid.uuid4()
        evidence_item = self._repo.create_evidence_item(
            project_id=project_id,
            source_mapping_id=None,
            provider=provider_str,
            record_type="uploaded_document",
            external_source_id=f"doc:{doc_uuid.hex}",
            title=extraction.detected_metadata.get("title") or filename,
            author=extraction.detected_metadata.get("author") or "Unknown",
            source_created_at=now,
            content_hash=sha256_hash,
            raw_metadata=extraction.detected_metadata,
            processing_status=EvidenceProcessingStatus.EXTRACTED.value,
            verification_status=EvidenceVerificationStatus.UNVERIFIED.value,
        )

        # 4. Create DocumentFile record
        doc_file = self._repo.create_document_file(
            evidence_item_id=evidence_item.id,
            uploaded_by_id=user_id,
            original_filename=filename,
            file_format=file_format,
            mime_type=mime_type,
            file_size_bytes=byte_size,
            storage_path=storage_path,
            sha256_hash=sha256_hash,
            page_count=extraction.page_count,
            ocr_applied=extraction.ocr_applied,
        )

        # 5. Persist extracted chunks in EvidenceContent
        for c in extraction.chunks:
            self._repo.create_evidence_content(
                evidence_item_id=evidence_item.id,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                section_heading=c.heading_path,
                content_text=c.content,
                token_count=c.word_count,
                indexing_status=EvidenceProcessingStatus.EXTRACTED.value,
            )

        self._db.commit()

        return DocumentUploadResponse(
            evidence_item_id=evidence_item.id,
            document_file_id=doc_file.id,
            original_filename=filename,
            file_format=file_format,
            mime_type=mime_type,
            file_size_bytes=byte_size,
            page_count=extraction.page_count,
            chunk_count=len(extraction.chunks),
            processing_status=evidence_item.processing_status,
            message="Document successfully uploaded, encrypted, and extracted.",
        )

    # -------------------------------------------------------------------------
    # Panel B: Evidence Library
    # -------------------------------------------------------------------------
    def list_evidence(
        self,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        search_query: str | None = None,
        provider: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> EvidenceListResponse:
        """Query evidence items honoring strict source-level ACL pre-filtering."""
        raw_items, total = self._repo.list_evidence_items(
            project_id=project_id,
            search_query=search_query,
            provider=provider,
            processing_status=status,
            limit=limit,
            offset=offset,
        )

        # Filter items where caller is authorised
        permitted_items: list[EvidenceItemSummary] = []
        for item in raw_items:
            if self._acl.can_access_evidence_item(user_id=user_id, item=item):
                permitted_items.append(self._to_evidence_item_summary(item))

        metrics = self._repo.get_evidence_metrics(project_id)

        return EvidenceListResponse(
            items=permitted_items,
            total=len(permitted_items),
            offset=offset,
            limit=limit,
            total_by_provider=metrics["total_by_provider"],
            total_by_status=metrics["total_by_status"],
        )

    def get_evidence_metrics(self, project_id: uuid.UUID) -> EvidenceLibraryMetricsResponse:
        """Return aggregated evidence metrics for the project."""
        metrics = self._repo.get_evidence_metrics(project_id)
        return EvidenceLibraryMetricsResponse(
            total_items=metrics["total_items"],
            total_documents=metrics["total_documents"],
            total_code_artifacts=metrics["total_code_artifacts"],
            total_tickets=metrics["total_tickets"],
            total_bytes=metrics["total_bytes"],
            last_synced_at=metrics["last_synced_at"],
        )

    # -------------------------------------------------------------------------
    # Panel C: Evidence Details & Download
    # -------------------------------------------------------------------------
    def get_evidence_detail(
        self,
        *,
        evidence_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> EvidenceItemDetail:
        """Fetch complete evidence details, enforcing strict source ACL verification."""
        item = self._repo.get_evidence_item_by_id(evidence_id)
        if item is None:
            raise NotFoundError("Evidence record not found.", code="EVIDENCE_NOT_FOUND")

        # Enforce Source ACL
        self._acl.enforce_evidence_item_access(user_id=user_id, item=item)

        chunks: list[EvidenceChunkResponse] = []
        for c in item.contents:
            chunks.append(
                EvidenceChunkResponse(
                    chunk_index=c.chunk_index,
                    content_text=c.content_text,
                    page_number=c.page_number,
                    section_heading=c.section_heading,
                    token_count=c.token_count,
                )
            )

        doc_summary: DocumentFileResponse | None = None
        if item.document_file:
            df = item.document_file
            doc_summary = DocumentFileResponse(
                id=df.id,
                original_filename=df.original_filename,
                file_format=df.file_format,
                mime_type=df.mime_type,
                file_size_bytes=df.file_size_bytes,
                page_count=df.page_count,
                sha256_hash=df.sha256_hash,
                created_at=df.created_at,
            )

        summary = self._to_evidence_item_summary(item)
        resource_name = (
            item.source_mapping.external_resource_name if item.source_mapping else None
        )

        return EvidenceItemDetail(
            **summary.model_dump(),
            raw_metadata=item.raw_metadata,
            chunks=chunks,
            document_file=doc_summary,
            source_resource_name=resource_name,
            can_download=item.document_file is not None,
            download_url=(
                f"/api/v1/evidence/{item.id}/download" if item.document_file is not None else None
            ),
        )

    def download_document_file(
        self,
        *,
        evidence_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> tuple[bytes, str, str]:
        """Verify access and decrypt file bytes for downloading."""
        item = self._repo.get_evidence_item_by_id(evidence_id)
        if item is None:
            raise NotFoundError("Evidence record not found.", code="EVIDENCE_NOT_FOUND")

        # Enforce ACL
        self._acl.enforce_evidence_item_access(user_id=user_id, item=item)

        if not item.document_file:
            raise NotFoundError(
                "This evidence record does not have an attached physical file.",
                code="NO_FILE",
            )

        raw_bytes = self._storage.read_file(item.document_file.storage_path)
        return raw_bytes, item.document_file.original_filename, item.document_file.mime_type

    # -------------------------------------------------------------------------
    # Sync Execution Pipeline
    # -------------------------------------------------------------------------
    def execute_mapping_sync(
        self,
        mapping_id: uuid.UUID,
        job_id: uuid.UUID | None = None,
    ) -> int:
        """Run the end-to-end sync pipeline for a mapped external container."""
        mapping = self._repo.get_mapping_by_id(mapping_id)
        if mapping is None:
            raise NotFoundError("Mapping not found.", code="MAPPING_NOT_FOUND")

        conn = mapping.source_connection
        if conn is None or not conn.encrypted_access_token:
            raise BadRequestError(
                "Connected source credentials missing.",
                code="CREDENTIALS_MISSING",
            )

        # Decrypt access token
        raw_token = decrypt_token(
            conn.encrypted_access_token,
            self._settings.security.token_encryption_key,
        )

        job = self._repo.get_sync_job_by_id(job_id) if job_id else None
        now = datetime.now(UTC)
        if job:
            self._repo.update_sync_job(job, status=JobStatus.RUNNING.value, started_at=now)

        try:
            records = []
            if conn.provider == SourceProvider.GITHUB.value:
                gh = GitHubIntegrationService(token=raw_token)
                records = gh.sync_repository(mapping.external_resource_id)
            elif conn.provider == SourceProvider.JIRA.value:
                meta = mapping.external_metadata or {}
                jira_url = meta.get("base_url") or "https://jira.atlassian.com"
                jira = JiraIntegrationService(base_url=jira_url, bearer_token=raw_token)
                records = jira.sync_project_issues(mapping.external_resource_id)
            else:
                raise BadRequestError(f"Sync not implemented for provider '{conn.provider}'.")

            # Persist discovered records
            ingested_count = 0
            for rec in records:
                existing = self._repo.get_evidence_by_external_id(
                    project_id=mapping.project_id,
                    external_source_id=rec.source_original_id,
                )
                if existing:
                    continue

                item = self._repo.create_evidence_item(
                    project_id=mapping.project_id,
                    source_mapping_id=mapping.id,
                    provider=conn.provider,
                    record_type=rec.item_type,
                    external_source_id=rec.source_original_id,
                    source_url=rec.source_url,
                    title=rec.title,
                    author=rec.author_name,
                    source_created_at=rec.captured_at,
                    content_hash=rec.content_hash,
                    raw_metadata=rec.attributes,
                    processing_status=EvidenceProcessingStatus.EXTRACTED.value,
                    verification_status=EvidenceVerificationStatus.UNVERIFIED.value,
                )

                chunks = self._chunker.chunk_document_pages([(1, rec.raw_content, rec.title)])
                for c in chunks:
                    self._repo.create_evidence_content(
                        evidence_item_id=item.id,
                        chunk_index=c.chunk_index,
                        page_number=c.page_number,
                        section_heading=c.heading_path,
                        content_text=c.content,
                        token_count=c.word_count,
                        indexing_status=EvidenceProcessingStatus.EXTRACTED.value,
                    )

                ingested_count += 1

            completed_now = datetime.now(UTC)
            self._repo.update_mapping(
                mapping,
                sync_status=SyncStatus.COMPLETED.value,
                last_synced_at=completed_now,
                sync_error=None,
            )
            self._repo.update_source_connection(
                conn,
                last_health_check_at=completed_now,
            )

            if job:
                self._repo.update_sync_job(
                    job,
                    status=JobStatus.COMPLETED.value,
                    completed_at=completed_now,
                )

            self._db.commit()
            return ingested_count

        except Exception as exc:
            logger.error("Failed sync execution on mapping %s: %s", mapping_id, exc)
            self._repo.update_mapping(
                mapping,
                sync_status=SyncStatus.FAILED.value,
                sync_error=str(exc)[:500],
            )
            if job:
                self._repo.update_sync_job(
                    job,
                    status=JobStatus.FAILED.value,
                    error_message=str(exc)[:500],
                    increment_attempt=True,
                )
            self._db.commit()
            raise

    # -------------------------------------------------------------------------
    # Response Transformers
    # -------------------------------------------------------------------------
    @staticmethod
    def _to_source_connection_response(conn: SourceConnection) -> SourceConnectionResponse:
        scopes = conn.scopes or []
        is_shared = "shared:organisation" in scopes or "shared:project" in scopes
        return SourceConnectionResponse(
            id=conn.id,
            organisation_id=conn.organisation_id,
            connected_by_id=conn.connected_by_id,
            provider=conn.provider,
            account_identifier=conn.account_identifier,
            connection_status=conn.connection_status,
            scopes=scopes,
            is_shared=is_shared,
            created_at=conn.created_at,
            updated_at=conn.updated_at,
            last_health_check_at=conn.last_health_check_at,
        )

    def _to_project_source_mapping_response(
        self, mapping: ProjectSourceMapping
    ) -> ProjectSourceMappingResponse:
        conn_resp = (
            self._to_source_connection_response(mapping.source_connection)
            if mapping.source_connection
            else None
        )
        return ProjectSourceMappingResponse(
            id=mapping.id,
            project_id=mapping.project_id,
            source_connection_id=mapping.source_connection_id,
            external_resource_id=mapping.external_resource_id,
            external_resource_name=mapping.external_resource_name,
            sync_status=mapping.sync_status,
            last_synced_at=mapping.last_synced_at,
            sync_error=mapping.sync_error,
            is_active=mapping.is_active,
            created_at=mapping.created_at,
            updated_at=mapping.updated_at,
            source_connection=conn_resp,
        )

    @staticmethod
    def _to_evidence_item_summary(item: EvidenceItem) -> EvidenceItemSummary:
        filename = item.document_file.original_filename if item.document_file else None
        fsize = item.document_file.file_size_bytes if item.document_file else None
        chunk_count = len(item.contents) if item.contents else 0

        return EvidenceItemSummary(
            id=item.id,
            project_id=item.project_id,
            provider=item.provider,
            record_type=item.record_type,
            title=item.title,
            external_source_id=item.external_source_id,
            source_url=item.source_url,
            author=item.author,
            source_created_at=item.source_created_at,
            ingested_at=item.ingested_at,
            processing_status=item.processing_status,
            verification_status=item.verification_status,
            content_hash=item.content_hash,
            original_filename=filename,
            file_size_bytes=fsize,
            chunk_count=chunk_count,
        )
