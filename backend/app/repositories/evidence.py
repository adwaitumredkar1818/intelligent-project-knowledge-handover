"""Repository for Evidence Workspace models (connections, mappings, items, files, jobs)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import (
    EvidenceProcessingStatus,
    EvidenceVerificationStatus,
    JobStatus,
    SourceConnectionStatus,
    SourceProvider,
    SyncStatus,
)
from app.models.evidence import (
    DocumentFile,
    EvidenceContent,
    EvidenceItem,
    ProjectSourceMapping,
    SourceConnection,
    SourceSyncJob,
)


class EvidenceRepository:
    """Encapsulates SQLAlchemy database interactions for Evidence Workspace."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # -------------------------------------------------------------------------
    # Panel A: Source Connections & Mappings
    # -------------------------------------------------------------------------
    def create_source_connection(
        self,
        *,
        organisation_id: uuid.UUID,
        connected_by_id: uuid.UUID,
        provider: SourceProvider,
        account_identifier: str,
        encrypted_access_token: str,
        scopes: list[str] | None = None,
    ) -> SourceConnection:
        """Persist a new source connection with encrypted credentials."""
        now = datetime.now(UTC)
        conn = SourceConnection(
            organisation_id=organisation_id,
            connected_by_id=connected_by_id,
            provider=provider.value if isinstance(provider, SourceProvider) else str(provider),
            account_identifier=account_identifier,
            encrypted_access_token=encrypted_access_token,
            scopes=scopes or [],
            connection_status=SourceConnectionStatus.CONNECTED.value,
            created_at=now,
            updated_at=now,
        )
        self._db.add(conn)
        self._db.flush()
        return conn

    def get_source_connection_by_id(self, connection_id: uuid.UUID) -> SourceConnection | None:
        """Fetch a source connection by primary key."""
        stmt = select(SourceConnection).where(SourceConnection.id == connection_id)
        return self._db.execute(stmt).scalar_one_or_none()

    def list_source_connections_for_org(
        self,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> list[SourceConnection]:
        """List connections for an organisation, optionally filtered by user access."""
        stmt = select(SourceConnection).where(
            SourceConnection.organisation_id == organisation_id,
            SourceConnection.connection_status != SourceConnectionStatus.DISCONNECTED.value,
        )
        if user_id is not None:
            # Accessible if user connected it, or if it is marked as shared in scopes
            stmt = stmt.where(
                or_(
                    SourceConnection.connected_by_id == user_id,
                    SourceConnection.scopes.contains(["shared:organisation"]),
                    SourceConnection.scopes.contains(["shared:project"]),
                )
            )
        stmt = stmt.order_by(SourceConnection.created_at.desc())
        return list(self._db.execute(stmt).scalars().all())

    def update_source_connection(
        self,
        connection: SourceConnection,
        *,
        scopes: list[str] | None = None,
        connection_status: str | None = None,
        last_health_check_at: datetime | None = None,
    ) -> SourceConnection:
        """Update source connection attributes."""
        if scopes is not None:
            connection.scopes = scopes
        if connection_status is not None:
            connection.connection_status = connection_status
        if last_health_check_at is not None:
            connection.last_health_check_at = last_health_check_at

        connection.updated_at = datetime.now(UTC)
        self._db.add(connection)
        self._db.flush()
        return connection

    def create_project_source_mapping(
        self,
        *,
        project_id: uuid.UUID,
        source_connection_id: uuid.UUID,
        external_resource_id: str,
        external_resource_name: str,
        external_metadata: dict[str, Any] | None = None,
    ) -> ProjectSourceMapping:
        """Link an external source container (repo/board) to a project workspace."""
        now = datetime.now(UTC)
        mapping = ProjectSourceMapping(
            project_id=project_id,
            source_connection_id=source_connection_id,
            external_resource_id=external_resource_id,
            external_resource_name=external_resource_name,
            external_metadata=external_metadata or {},
            sync_status=SyncStatus.IDLE.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._db.add(mapping)
        self._db.flush()
        return mapping

    def get_mapping_by_id(self, mapping_id: uuid.UUID) -> ProjectSourceMapping | None:
        """Fetch project source mapping with its connection eagerly loaded."""
        stmt = (
            select(ProjectSourceMapping)
            .options(selectinload(ProjectSourceMapping.source_connection))
            .where(ProjectSourceMapping.id == mapping_id)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def get_mapping_by_resource(
        self,
        project_id: uuid.UUID,
        external_resource_id: str,
    ) -> ProjectSourceMapping | None:
        """Check if an external container is already mapped to this project."""
        stmt = select(ProjectSourceMapping).where(
            ProjectSourceMapping.project_id == project_id,
            ProjectSourceMapping.external_resource_id == external_resource_id,
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def list_mappings_for_project(self, project_id: uuid.UUID) -> list[ProjectSourceMapping]:
        """List all active container mappings for a project workspace."""
        stmt = (
            select(ProjectSourceMapping)
            .options(selectinload(ProjectSourceMapping.source_connection))
            .where(ProjectSourceMapping.project_id == project_id)
            .order_by(ProjectSourceMapping.created_at.desc())
        )
        return list(self._db.execute(stmt).scalars().all())

    def update_mapping(
        self,
        mapping: ProjectSourceMapping,
        *,
        sync_status: str | None = None,
        last_synced_at: datetime | None = None,
        sync_error: str | None = None,
    ) -> ProjectSourceMapping:
        """Update mapping sync outcome and statistics."""
        if sync_status is not None:
            mapping.sync_status = sync_status
        if last_synced_at is not None:
            mapping.last_synced_at = last_synced_at
        mapping.sync_error = sync_error
        mapping.updated_at = datetime.now(UTC)
        self._db.add(mapping)
        self._db.flush()
        return mapping

    # -------------------------------------------------------------------------
    # Panel B & C: Evidence Items & Contents
    # -------------------------------------------------------------------------
    def create_evidence_item(
        self,
        *,
        project_id: uuid.UUID,
        source_mapping_id: uuid.UUID | None = None,
        provider: str,
        record_type: str,
        external_source_id: str,
        source_url: str | None = None,
        title: str,
        author: str | None = None,
        source_created_at: datetime | None = None,
        content_hash: str,
        raw_metadata: dict[str, Any] | None = None,
        processing_status: str = EvidenceProcessingStatus.EXTRACTED.value,
        verification_status: str = EvidenceVerificationStatus.UNVERIFIED.value,
    ) -> EvidenceItem:
        """Persist a new atomic evidence item."""
        now = datetime.now(UTC)
        item = EvidenceItem(
            project_id=project_id,
            source_mapping_id=source_mapping_id,
            provider=provider,
            record_type=record_type,
            external_source_id=external_source_id,
            source_url=source_url,
            title=title,
            author=author,
            source_created_at=source_created_at,
            ingested_at=now,
            content_hash=content_hash,
            raw_metadata=raw_metadata or {},
            processing_status=processing_status,
            verification_status=verification_status,
            created_at=now,
            updated_at=now,
        )
        self._db.add(item)
        self._db.flush()
        return item

    def get_evidence_item_by_id(self, item_id: uuid.UUID) -> EvidenceItem | None:
        """Fetch evidence item by ID with related contents, file, and mapping."""
        stmt = (
            select(EvidenceItem)
            .options(
                selectinload(EvidenceItem.contents),
                selectinload(EvidenceItem.document_file),
                selectinload(EvidenceItem.source_mapping).selectinload(
                    ProjectSourceMapping.source_connection
                ),
            )
            .where(EvidenceItem.id == item_id)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def get_evidence_by_external_id(
        self,
        project_id: uuid.UUID,
        external_source_id: str,
    ) -> EvidenceItem | None:
        """Find an evidence item by its external source key within a project."""
        stmt = select(EvidenceItem).where(
            EvidenceItem.project_id == project_id,
            EvidenceItem.external_source_id == external_source_id,
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def list_evidence_items(
        self,
        *,
        project_id: uuid.UUID,
        search_query: str | None = None,
        provider: str | None = None,
        processing_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[EvidenceItem], int]:
        """Query and paginate evidence items with filtering and search."""
        base_query = select(EvidenceItem).where(EvidenceItem.project_id == project_id)

        if provider is not None:
            base_query = base_query.where(EvidenceItem.provider == provider)
        if processing_status is not None:
            base_query = base_query.where(EvidenceItem.processing_status == processing_status)
        if search_query:
            term = f"%{search_query.strip()}%"
            base_query = base_query.where(
                or_(
                    EvidenceItem.title.ilike(term),
                    EvidenceItem.external_source_id.ilike(term),
                    EvidenceItem.author.ilike(term),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = self._db.execute(count_stmt).scalar_one()

        # Fetch page with eagerly loaded relations
        items_stmt = (
            base_query.options(
                selectinload(EvidenceItem.document_file),
                selectinload(EvidenceItem.contents),
                selectinload(EvidenceItem.source_mapping).selectinload(
                    ProjectSourceMapping.source_connection
                ),
            )
            .order_by(EvidenceItem.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(self._db.execute(items_stmt).scalars().all())

        return items, total

    def get_evidence_metrics(self, project_id: uuid.UUID) -> dict[str, Any]:
        """Aggregate breakdown metrics across evidence records in a project."""
        total = (
            self._db.execute(
                select(func.count(EvidenceItem.id)).where(EvidenceItem.project_id == project_id)
            ).scalar_one()
            or 0
        )

        prov_stmt = (
            select(EvidenceItem.provider, func.count(EvidenceItem.id))
            .where(EvidenceItem.project_id == project_id)
            .group_by(EvidenceItem.provider)
        )
        by_prov = {str(row[0]): int(row[1]) for row in self._db.execute(prov_stmt).all()}

        stat_stmt = (
            select(EvidenceItem.processing_status, func.count(EvidenceItem.id))
            .where(EvidenceItem.project_id == project_id)
            .group_by(EvidenceItem.processing_status)
        )
        by_stat = {str(row[0]): int(row[1]) for row in self._db.execute(stat_stmt).all()}

        # Total bytes from document files
        bytes_stmt = (
            select(func.coalesce(func.sum(DocumentFile.file_size_bytes), 0))
            .select_from(DocumentFile)
            .join(EvidenceItem, DocumentFile.evidence_item_id == EvidenceItem.id)
            .where(EvidenceItem.project_id == project_id)
        )
        total_bytes = int(self._db.execute(bytes_stmt).scalar_one() or 0)

        # Recent sync timestamp
        sync_stmt = (
            select(func.max(ProjectSourceMapping.last_synced_at))
            .where(ProjectSourceMapping.project_id == project_id)
        )
        last_synced = self._db.execute(sync_stmt).scalar_one()

        docs_count = by_prov.get("pdf", 0) + by_prov.get("docx", 0)

        return {
            "total_items": total,
            "total_documents": docs_count,
            "total_code_artifacts": by_prov.get("github", 0),
            "total_tickets": by_prov.get("jira", 0),
            "total_bytes": total_bytes,
            "last_synced_at": last_synced,
            "total_by_provider": by_prov,
            "total_by_status": by_stat,
        }

    # -------------------------------------------------------------------------
    # Document Files & Content
    # -------------------------------------------------------------------------
    def create_document_file(
        self,
        *,
        evidence_item_id: uuid.UUID,
        uploaded_by_id: uuid.UUID,
        original_filename: str,
        file_format: str,
        mime_type: str,
        file_size_bytes: int,
        storage_path: str,
        sha256_hash: str,
        page_count: int | None = None,
        ocr_applied: bool = False,
    ) -> DocumentFile:
        """Record physical document storage metadata."""
        now = datetime.now(UTC)
        doc = DocumentFile(
            evidence_item_id=evidence_item_id,
            uploaded_by_id=uploaded_by_id,
            original_filename=original_filename,
            file_format=file_format,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            storage_path=storage_path,
            sha256_hash=sha256_hash,
            page_count=page_count,
            ocr_applied=ocr_applied,
            created_at=now,
        )
        self._db.add(doc)
        self._db.flush()
        return doc

    def get_document_file_by_id(self, file_id: uuid.UUID) -> DocumentFile | None:
        """Fetch a document file record by ID."""
        stmt = select(DocumentFile).where(DocumentFile.id == file_id)
        return self._db.execute(stmt).scalar_one_or_none()

    def create_evidence_content(
        self,
        *,
        evidence_item_id: uuid.UUID,
        chunk_index: int,
        page_number: int | None = None,
        section_heading: str | None = None,
        content_text: str,
        token_count: int | None = None,
        indexing_status: str = EvidenceProcessingStatus.PENDING.value,
    ) -> EvidenceContent:
        """Persist an extracted text chunk."""
        now = datetime.now(UTC)
        content = EvidenceContent(
            evidence_item_id=evidence_item_id,
            chunk_index=chunk_index,
            page_number=page_number,
            section_heading=section_heading,
            content_text=content_text,
            token_count=token_count,
            indexing_status=indexing_status,
            created_at=now,
        )
        self._db.add(content)
        self._db.flush()
        return content

    # -------------------------------------------------------------------------
    # Background Sync Jobs
    # -------------------------------------------------------------------------
    def create_sync_job(
        self,
        *,
        project_id: uuid.UUID,
        source_mapping_id: uuid.UUID | None = None,
        job_type: str = "full",
    ) -> SourceSyncJob:
        """Create a new queued sync job for the background worker."""
        now = datetime.now(UTC)
        job = SourceSyncJob(
            project_id=project_id,
            source_mapping_id=source_mapping_id,
            job_type=job_type,
            status=JobStatus.QUEUED.value,
            attempt_count=0,
            max_attempts=3,
            progress_percent=0,
            created_at=now,
        )
        self._db.add(job)
        self._db.flush()
        return job

    def get_sync_job_by_id(self, job_id: uuid.UUID) -> SourceSyncJob | None:
        """Fetch a sync job by ID."""
        stmt = select(SourceSyncJob).where(SourceSyncJob.id == job_id)
        return self._db.execute(stmt).scalar_one_or_none()

    def list_sync_jobs_for_mapping(
        self,
        source_mapping_id: uuid.UUID,
        limit: int = 20,
    ) -> list[SourceSyncJob]:
        """List sync jobs for a specific container mapping."""
        stmt = (
            select(SourceSyncJob)
            .where(SourceSyncJob.source_mapping_id == source_mapping_id)
            .order_by(SourceSyncJob.created_at.desc())
            .limit(limit)
        )
        return list(self._db.execute(stmt).scalars().all())

    def update_sync_job(
        self,
        job: SourceSyncJob,
        *,
        status: str,
        error_message: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        increment_attempt: bool = False,
    ) -> SourceSyncJob:
        """Update job lifecycle status and timestamps."""
        job.status = status
        if error_message is not None:
            job.error_message = error_message
        if started_at is not None:
            job.started_at = started_at
        if completed_at is not None:
            job.completed_at = completed_at
        if increment_attempt:
            job.attempt_count += 1
        self._db.add(job)
        self._db.flush()
        return job
