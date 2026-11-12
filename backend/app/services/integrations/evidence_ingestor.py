"""Canonical normalisation and deterministic idempotent upsert of source evidence."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.models.enums import (
    BackgroundJobType,
    EvidenceIndexingStatus,
    EvidenceProcessingStatus,
)
from app.models.evidence import EvidenceItem
from app.repositories.evidence import EvidenceRepository
from app.repositories.job import BackgroundJobRepository
from app.repositories.knowledge import KnowledgeRepository
from app.services.document_extraction import ExtractedPageData


@dataclass(frozen=True, slots=True)
class NormalizedSourceEvidence:
    """Provider-normalised evidence artefact ready for canonical PostgreSQL persistence."""

    source_type: str
    source_provider: str
    category: str
    source_external_id: str
    source_url: str | None
    source_author_identity: str | None
    title: str
    source_created_at: datetime | None
    source_updated_at: datetime | None
    extraction_method: str
    acl_scope: str
    source_access_policy_id: uuid.UUID
    extracted_text: str
    pages: tuple[ExtractedPageData, ...]
    warnings: tuple[str, ...] = ()
    metadata_json: dict[str, Any] = field(default_factory=dict)
    mime_type: str | None = "text/markdown"
    original_filename: str | None = None


@dataclass(frozen=True, slots=True)
class UpsertEvidenceOutcome:
    """Outcome emitted for every normalised external evidence record processed by sync."""

    action: str  # "created" | "updated" | "unchanged"
    evidence_item: EvidenceItem


def compute_source_content_hash(record: NormalizedSourceEvidence) -> str:
    """Compute a deterministic SHA-256 over canonical source identity + normalised content."""
    canonical = {
        "source_type": record.source_type,
        "source_provider": record.source_provider,
        "source_external_id": record.source_external_id,
        "category": record.category,
        "title": record.title,
        "source_url": record.source_url,
        "source_author_identity": record.source_author_identity,
        "acl_scope": record.acl_scope,
        "source_access_policy_id": str(record.source_access_policy_id),
        "extracted_text": record.extracted_text,
        "warnings": list(record.warnings),
        "metadata_json": record.metadata_json,
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class SourceEvidenceIngestor:
    """Idempotently upserts normalised GitHub/Jira evidence into unified PostgreSQL tables."""

    def __init__(
        self,
        *,
        session: Session,
        evidence_repository: EvidenceRepository,
        job_repository: BackgroundJobRepository | None = None,
    ) -> None:
        self._session = session
        self._evidence_repo = evidence_repository
        self._job_repo = job_repository or BackgroundJobRepository(session)

    def _enqueue_indexing_after_upsert(
        self,
        *,
        item: EvidenceItem,
        triggered_by_user_id: uuid.UUID | None,
        extracted_text: str,
        trigger: str,
        now: datetime,
    ) -> None:
        if not extracted_text.strip():
            item.indexing_status = EvidenceIndexingStatus.INDEXED.value
            item.chunk_count = 0
            item.indexed_at = now
            item.index_error_code = None
            item.index_error_message = None
            return
        if not self._job_repo.has_active_job_for_evidence(
            evidence_id=item.id,
            job_type=BackgroundJobType.EVIDENCE_INDEXING.value,
        ):
            self._job_repo.create_job(
                organisation_id=item.organisation_id,
                project_id=item.project_id,
                evidence_id=item.id,
                triggered_by_user_id=triggered_by_user_id,
                job_type=BackgroundJobType.EVIDENCE_INDEXING.value,
                priority=110,
                payload_json={
                    "target": "full",
                    "force_rechunk": True,
                    "trigger": trigger,
                },
            )
        item.indexing_status = EvidenceIndexingStatus.QUEUED.value
        item.index_error_code = None
        item.index_error_message = None

    def upsert_record(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        source_connection_id: uuid.UUID,
        triggered_by_user_id: uuid.UUID | None,
        record: NormalizedSourceEvidence,
        now: datetime | None = None,
    ) -> UpsertEvidenceOutcome:
        """Create or update an external evidence item in place without touching uploads."""
        timestamp = now or utc_now()
        content_hash = compute_source_content_hash(record)
        processing_status = (
            EvidenceProcessingStatus.PARTIALLY_EXTRACTED.value
            if record.warnings
            else EvidenceProcessingStatus.EXTRACTED.value
        )
        error_code = "SOURCE_EXTRACTION_INCOMPLETE" if record.warnings else None
        error_message = (
            "; ".join(record.warnings)[:500] if record.warnings else None
        )
        title = (record.title or record.source_external_id).strip()[:500]
        author_identity = (
            record.source_author_identity.strip()[:255]
            if record.source_author_identity
            else None
        )

        existing = self._evidence_repo.find_active_by_source_external_id(
            project_id=project_id,
            source_type=record.source_type,
            source_external_id=record.source_external_id,
        )
        if existing is None:
            created_item = self._evidence_repo.create_evidence_item(
                organisation_id=organisation_id,
                project_id=project_id,
                uploaded_by_user_id=triggered_by_user_id,
                source_type=record.source_type,
                source_provider=record.source_provider,
                category=record.category,
                source_external_id=record.source_external_id[:255],
                source_url=record.source_url[:1024] if record.source_url else None,
                source_author_identity=author_identity,
                title=title,
                original_filename=(
                    record.original_filename[:255] if record.original_filename else None
                ),
                mime_type=record.mime_type,
                file_size_bytes=len(record.extracted_text.encode("utf-8")),
                content_hash=content_hash,
                storage_provider=None,
                storage_object_key=None,
                encryption_algorithm=None,
                encryption_key_id=None,
                source_connection_id=source_connection_id,
                source_access_policy_id=record.source_access_policy_id,
                acl_scope=record.acl_scope,
                source_created_at=record.source_created_at,
                source_updated_at=record.source_updated_at,
                extracted_at=timestamp,
                last_synced_at=timestamp,
                processing_status=processing_status,
                extraction_method=record.extraction_method,
                page_count=len(record.pages),
                error_code=error_code,
                error_message=error_message,
                metadata_json=dict(record.metadata_json),
            )
            self._evidence_repo.replace_extracted_content(
                evidence_id=created_item.id,
                extracted_text=record.extracted_text,
                warnings=record.warnings,
                pages=record.pages,
            )
            self._enqueue_indexing_after_upsert(
                item=created_item,
                triggered_by_user_id=triggered_by_user_id,
                extracted_text=record.extracted_text,
                trigger="connector_created",
                now=timestamp,
            )
            return UpsertEvidenceOutcome(action="created", evidence_item=created_item)

        if existing.content_hash == content_hash and existing.content is not None:
            existing.last_synced_at = timestamp
            existing.source_connection_id = source_connection_id
            existing.source_access_policy_id = record.source_access_policy_id
            existing.acl_scope = record.acl_scope
            self._session.flush()
            return UpsertEvidenceOutcome(action="unchanged", evidence_item=existing)

        existing.source_provider = record.source_provider
        existing.category = record.category
        existing.source_url = record.source_url[:1024] if record.source_url else None
        existing.source_author_identity = author_identity
        existing.title = title
        existing.original_filename = (
            record.original_filename[:255] if record.original_filename else None
        )
        existing.mime_type = record.mime_type
        existing.file_size_bytes = len(record.extracted_text.encode("utf-8"))
        existing.content_hash = content_hash
        existing.source_connection_id = source_connection_id
        existing.source_access_policy_id = record.source_access_policy_id
        existing.acl_scope = record.acl_scope
        existing.source_created_at = record.source_created_at
        existing.source_updated_at = record.source_updated_at
        existing.extracted_at = timestamp
        existing.last_synced_at = timestamp
        existing.processing_status = processing_status
        existing.extraction_method = record.extraction_method
        existing.page_count = len(record.pages)
        existing.error_code = error_code
        existing.error_message = error_message
        existing.metadata_json = dict(record.metadata_json)
        self._session.flush()

        self._evidence_repo.replace_extracted_content(
            evidence_id=existing.id,
            extracted_text=record.extracted_text,
            warnings=record.warnings,
            pages=record.pages,
        )
        KnowledgeRepository(self._session).mark_stale_for_evidence(
            evidence_id=existing.id,
            reason="source_evidence_updated",
            now=timestamp,
        )
        self._enqueue_indexing_after_upsert(
            item=existing,
            triggered_by_user_id=triggered_by_user_id,
            extracted_text=record.extracted_text,
            trigger="connector_updated",
            now=timestamp,
        )
        return UpsertEvidenceOutcome(action="updated", evidence_item=existing)

    def mark_item_inaccessible(
        self,
        *,
        evidence: EvidenceItem,
        reason: str,
        now: datetime | None = None,
    ) -> None:
        """Flag an item deleted/inaccessible at provider while preserving historical provenance."""
        timestamp = now or utc_now()
        meta = dict(evidence.metadata_json or {})
        meta["source_item_state"] = "inaccessible_or_deleted"
        meta["inaccessible_detected_at"] = timestamp.isoformat()
        meta["inaccessible_reason"] = reason[:300]
        evidence.metadata_json = meta
        evidence.last_synced_at = timestamp
        evidence.processing_status = EvidenceProcessingStatus.PARTIALLY_EXTRACTED.value
        evidence.error_code = "SOURCE_ITEM_INACCESSIBLE"
        evidence.error_message = reason[:500]
        KnowledgeRepository(self._session).mark_stale_for_evidence(
            evidence_id=evidence.id,
            reason="source_item_inaccessible",
            now=timestamp,
        )
        self._session.flush()

    def reconcile_missing_snapshot_items(
        self,
        *,
        project_id: uuid.UUID,
        source_type: str,
        mapping_id: uuid.UUID,
        seen_external_ids: set[str],
        reconciled_categories: set[str],
        now: datetime | None = None,
    ) -> int:
        """Mark previously synced items absent from a complete full scan as inaccessible."""
        existing_items = self._evidence_repo.list_active_external_by_mapping(
            project_id=project_id,
            source_type=source_type,
            mapping_id=mapping_id,
        )
        timestamp = now or utc_now()
        flagged = 0
        for item in existing_items:
            if item.category not in reconciled_categories:
                continue
            if item.source_external_id in seen_external_ids:
                continue
            current_state = (item.metadata_json or {}).get("source_item_state")
            if current_state == "inaccessible_or_deleted":
                continue
            self.mark_item_inaccessible(
                evidence=item,
                reason=(
                    "Item no longer returned in complete source sync snapshot "
                    "(deleted or access revoked)."
                ),
                now=timestamp,
            )
            flagged += 1
        return flagged
