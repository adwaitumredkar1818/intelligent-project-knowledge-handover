"""Data-access repository for unified evidence items and separated extracted content."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.enums import (
    EvidenceProcessingStatus,
    EvidenceSourceType,
    SourcePermissionVerificationStatus,
)
from app.models.evidence import EvidenceContent, EvidenceItem, EvidencePageContent
from app.models.integration import SourceAccessPolicy
from app.services.document_extraction import ExtractedPageData


class EvidenceRepository:
    """Repository encapsulating tenant-scoped evidence ledger persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(
        self,
        evidence_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> EvidenceItem | None:
        stmt = (
            select(EvidenceItem)
            .options(
                joinedload(EvidenceItem.project),
                joinedload(EvidenceItem.organisation),
                joinedload(EvidenceItem.source_access_policy),
            )
            .where(EvidenceItem.id == evidence_id)
        )
        if not include_deleted:
            stmt = stmt.where(
                EvidenceItem.deleted_at.is_(None),
                EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
            )
        return self._session.execute(stmt).unique().scalar_one_or_none()

    def get_by_id_detail(
        self,
        evidence_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> EvidenceItem | None:
        stmt = (
            select(EvidenceItem)
            .options(
                joinedload(EvidenceItem.project),
                joinedload(EvidenceItem.organisation),
                joinedload(EvidenceItem.source_access_policy),
                joinedload(EvidenceItem.content),
                selectinload(EvidenceItem.pages),
                selectinload(EvidenceItem.jobs),
            )
            .where(EvidenceItem.id == evidence_id)
        )
        if not include_deleted:
            stmt = stmt.where(
                EvidenceItem.deleted_at.is_(None),
                EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
            )
        return self._session.execute(stmt).unique().scalar_one_or_none()

    def find_active_duplicate(
        self,
        *,
        project_id: uuid.UUID,
        content_hash: str,
    ) -> EvidenceItem | None:
        """Look up an active duplicate inside ONE project boundary only."""
        stmt = (
            select(EvidenceItem)
            .where(
                EvidenceItem.project_id == project_id,
                EvidenceItem.content_hash == content_hash,
                EvidenceItem.deleted_at.is_(None),
                EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
            )
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def find_active_by_source_external_id(
        self,
        *,
        project_id: uuid.UUID,
        source_type: str,
        source_external_id: str,
    ) -> EvidenceItem | None:
        """Look up an active external-source evidence record inside one project scope."""
        stmt = (
            select(EvidenceItem)
            .options(
                joinedload(EvidenceItem.content),
                selectinload(EvidenceItem.pages),
                joinedload(EvidenceItem.source_access_policy),
            )
            .where(
                EvidenceItem.project_id == project_id,
                EvidenceItem.source_type == source_type,
                EvidenceItem.source_external_id == source_external_id,
                EvidenceItem.deleted_at.is_(None),
                EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
            )
            .limit(1)
        )
        return self._session.execute(stmt).unique().scalar_one_or_none()

    def list_active_external_by_mapping(
        self,
        *,
        project_id: uuid.UUID,
        source_type: str,
        mapping_id: uuid.UUID,
    ) -> list[EvidenceItem]:
        """Return active external evidence items previously ingested for one source mapping."""
        stmt = select(EvidenceItem).where(
            EvidenceItem.project_id == project_id,
            EvidenceItem.source_type == source_type,
            EvidenceItem.deleted_at.is_(None),
            EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
        )
        mapping_str = str(mapping_id)
        return [
            item
            for item in self._session.execute(stmt).scalars().all()
            if str((item.metadata_json or {}).get("mapping_id") or "") == mapping_str
        ]

    def _allowed_policy_ids_for_viewer(
        self,
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID | None,
    ) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
        if viewer_user_id is None:
            return [], []
        policies = list(
            self._session.execute(
                select(SourceAccessPolicy).where(SourceAccessPolicy.project_id == project_id)
            )
            .scalars()
            .all()
        )
        viewer_str = str(viewer_user_id)
        allowed_ids: list[uuid.UUID] = []
        revoked_ids: list[uuid.UUID] = []
        for policy in policies:
            if policy.sync_permission_status == SourcePermissionVerificationStatus.REVOKED.value:
                revoked_ids.append(policy.id)
                continue
            if viewer_str in (policy.allowed_user_ids or []):
                allowed_ids.append(policy.id)
        return allowed_ids, revoked_ids

    def list_for_project(
        self,
        *,
        project_id: uuid.UUID,
        processing_status: str | None = None,
        source_type: str | None = None,
        category: str | None = None,
        viewer_user_id: uuid.UUID | None = None,
        has_project_manage: bool = False,
        enforce_source_acl: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[EvidenceItem], int]:
        filters: list[Any] = [
            EvidenceItem.project_id == project_id,
            EvidenceItem.deleted_at.is_(None),
            EvidenceItem.processing_status != EvidenceProcessingStatus.DELETED.value,
        ]
        if processing_status is not None:
            filters.append(EvidenceItem.processing_status == processing_status)
        if source_type is not None:
            filters.append(EvidenceItem.source_type == source_type)
        if category is not None:
            filters.append(EvidenceItem.category == category)

        if enforce_source_acl:
            allowed_policy_ids, revoked_policy_ids = self._allowed_policy_ids_for_viewer(
                project_id=project_id,
                viewer_user_id=viewer_user_id,
            )
            public_clause = (
                and_(
                    EvidenceItem.acl_scope == "project_members",
                    or_(
                        EvidenceItem.source_access_policy_id.is_(None),
                        EvidenceItem.source_access_policy_id.notin_(revoked_policy_ids),
                    ),
                )
                if revoked_policy_ids
                else EvidenceItem.acl_scope == "project_members"
            )
            acl_clauses: list[Any] = [public_clause]
            if allowed_policy_ids:
                acl_clauses.append(
                    and_(
                        EvidenceItem.acl_scope == "source_restricted",
                        EvidenceItem.source_access_policy_id.in_(allowed_policy_ids),
                    )
                )
            if has_project_manage:
                acl_clauses.append(
                    and_(
                        EvidenceItem.acl_scope == "source_restricted",
                        EvidenceItem.source_type == EvidenceSourceType.DOCUMENT_UPLOAD.value,
                        EvidenceItem.source_access_policy_id.is_(None),
                        EvidenceItem.source_connection_id.is_(None),
                    )
                )
            elif viewer_user_id is not None:
                acl_clauses.append(
                    and_(
                        EvidenceItem.acl_scope == "source_restricted",
                        EvidenceItem.source_type == EvidenceSourceType.DOCUMENT_UPLOAD.value,
                        EvidenceItem.source_access_policy_id.is_(None),
                        EvidenceItem.source_connection_id.is_(None),
                        EvidenceItem.uploaded_by_user_id == viewer_user_id,
                    )
                )
            filters.append(or_(*acl_clauses))

        total = int(
            self._session.execute(
                select(func.count()).select_from(EvidenceItem).where(*filters)
            ).scalar_one()
        )
        items = list(
            self._session.execute(
                select(EvidenceItem)
                .options(selectinload(EvidenceItem.jobs))
                .where(*filters)
                .order_by(EvidenceItem.created_at.desc(), EvidenceItem.id.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total

    def create_evidence_item(
        self,
        *,
        evidence_id: uuid.UUID | None = None,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        uploaded_by_user_id: uuid.UUID | None,
        source_type: str,
        source_provider: str,
        category: str,
        source_external_id: str,
        source_url: str | None,
        source_author_identity: str | None,
        title: str,
        original_filename: str | None,
        mime_type: str | None,
        file_size_bytes: int | None,
        content_hash: str,
        storage_provider: str | None,
        storage_object_key: str | None,
        encryption_algorithm: str | None,
        encryption_key_id: str | None,
        source_connection_id: uuid.UUID | None = None,
        source_access_policy_id: uuid.UUID | None = None,
        acl_scope: str = "project_members",
        source_created_at: datetime | None,
        source_updated_at: datetime | None,
        extracted_at: datetime | None = None,
        last_synced_at: datetime | None = None,
        processing_status: str,
        extraction_method: str | None = None,
        page_count: int | None,
        error_code: str | None = None,
        error_message: str | None = None,
        metadata_json: dict[str, Any],
    ) -> EvidenceItem:
        item = EvidenceItem(
            id=evidence_id or uuid.uuid4(),
            organisation_id=organisation_id,
            project_id=project_id,
            uploaded_by_user_id=uploaded_by_user_id,
            source_type=source_type,
            source_provider=source_provider,
            category=category,
            source_external_id=source_external_id,
            source_url=source_url,
            source_author_identity=source_author_identity,
            title=title,
            original_filename=original_filename,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            content_hash=content_hash,
            storage_provider=storage_provider,
            storage_object_key=storage_object_key,
            encryption_algorithm=encryption_algorithm,
            encryption_key_id=encryption_key_id,
            source_connection_id=source_connection_id,
            source_access_policy_id=source_access_policy_id,
            acl_scope=acl_scope,
            source_created_at=source_created_at,
            source_updated_at=source_updated_at,
            extracted_at=extracted_at,
            last_synced_at=last_synced_at,
            processing_status=processing_status,
            extraction_method=extraction_method,
            page_count=page_count,
            error_code=error_code,
            error_message=error_message,
            metadata_json=metadata_json,
        )
        self._session.add(item)
        self._session.flush()
        return item

    def replace_extracted_content(
        self,
        *,
        evidence_id: uuid.UUID,
        extracted_text: str,
        warnings: tuple[str, ...],
        pages: tuple[ExtractedPageData, ...],
    ) -> None:
        """Persist separated canonical text and ordered page segments cleanly."""
        char_count = len(extracted_text)
        word_count = len(extracted_text.split()) if extracted_text.strip() else 0

        existing_content = self._session.get(EvidenceContent, evidence_id)
        if existing_content is None:
            self._session.add(
                EvidenceContent(
                    evidence_id=evidence_id,
                    extracted_text=extracted_text,
                    char_count=char_count,
                    word_count=word_count,
                    extraction_warnings=list(warnings),
                )
            )
        else:
            existing_content.extracted_text = extracted_text
            existing_content.char_count = char_count
            existing_content.word_count = word_count
            existing_content.extraction_warnings = list(warnings)

        self._session.execute(
            delete(EvidencePageContent).where(EvidencePageContent.evidence_id == evidence_id)
        )
        self._session.flush()
        for page in pages:
            self._session.add(
                EvidencePageContent(
                    evidence_id=evidence_id,
                    page_number=page.page_number,
                    extraction_outcome=page.extraction_outcome,
                    ocr_applied=page.ocr_applied,
                    ocr_truncated=page.ocr_truncated,
                    text_content=page.text_content,
                    char_count=len(page.text_content),
                    structured_metadata=dict(page.structured_metadata),
                )
            )
        self._session.flush()
