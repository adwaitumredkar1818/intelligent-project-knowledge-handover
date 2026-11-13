"""Data-access repositories for Handover Workspace (Module 4 / Knowledge Transfer Area).

Provides persistence abstractions for:
- HandoverCaseRepository: Handover cases and lifecycle
- HandoverPackageRepository: Top-level packages
- HandoverPackageVersionRepository: Versioned package snapshots
- HandoverSectionRepository: 8-domain sections
- HandoverContentLinkRepository: Provenance links to knowledge/relationships/evidence
- HandoverReadinessRepository: 9-category readiness scores
- HandoverChecklistRepository: Checklists and checklist items
- HandoverResponsibilityTransferRepository: Responsibility mappings
- HandoverSignoffRepository: Human sign-offs (departing, reviewer, successor)
- HandoverDeliveryRepository: Delivery records
- HandoverAcknowledgementRepository: Successor receipts
- HandoverStatusHistoryRepository: Immutable status audit log
- HandoverOwnershipTransferRepository: Explicit ownership transfers
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.security import utc_now
from app.models.enums import (
    ChecklistItemStatus,
    HandoverCaseStatus,
    HandoverChecklistType,
    HandoverDeliveryMethod,
    HandoverLinkType,
    HandoverPackageSectionType,
    HandoverReadinessCategory,
    OwnershipTransferType,
    ReadinessLevel,
    SignoffDecision,
    SignoffType,
    TransferStatus,
)
from app.models.handover import (
    HandoverAcknowledgement,
    HandoverCase,
    HandoverChecklist,
    HandoverChecklistItem,
    HandoverContentLink,
    HandoverDelivery,
    HandoverOwnershipTransfer,
    HandoverPackage,
    HandoverPackageSection,
    HandoverPackageVersion,
    HandoverReadinessAssessment,
    HandoverResponsibilityTransfer,
    HandoverSignoff,
    HandoverStatusHistory,
)


class HandoverCaseRepository:
    """Repository for managing HandoverCase records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, case: HandoverCase) -> HandoverCase:
        self.session.add(case)
        self.session.flush()
        return case

    def get_by_id(
        self, case_id: uuid.UUID, *, load_relationships: bool = True
    ) -> HandoverCase | None:
        stmt = select(HandoverCase).where(HandoverCase.id == case_id)
        if load_relationships:
            stmt = stmt.options(
                selectinload(HandoverCase.package),
                selectinload(HandoverCase.versions),
                selectinload(HandoverCase.checklists),
                selectinload(HandoverCase.responsibility_transfers),
                selectinload(HandoverCase.signoffs),
                selectinload(HandoverCase.status_history),
                selectinload(HandoverCase.ownership_transfers),
                selectinload(HandoverCase.departing_member),
                selectinload(HandoverCase.successor),
                selectinload(HandoverCase.created_by_user),
            )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_project(
        self,
        project_id: uuid.UUID,
        *,
        status: str | None = None,
        departing_member_id: uuid.UUID | None = None,
        successor_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[HandoverCase], int]:
        stmt = select(HandoverCase).where(HandoverCase.project_id == project_id)
        if status:
            stmt = stmt.where(HandoverCase.status == status)
        if departing_member_id:
            stmt = stmt.where(HandoverCase.departing_member_id == departing_member_id)
        if successor_id:
            stmt = stmt.where(HandoverCase.successor_id == successor_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar_one()

        stmt = (
            stmt.order_by(HandoverCase.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(self.session.execute(stmt).scalars().all())
        return items, total

    def update_status(
        self,
        case_id: uuid.UUID,
        *,
        new_status: str,
        expected_version: int | None = None,
    ) -> HandoverCase | None:
        case = self.session.get(HandoverCase, case_id)
        if not case:
            return None
        if expected_version is not None and case.version != expected_version:
            raise ValueError(
                f"Version mismatch: expected {expected_version}, found {case.version}"
            )
        case.status = new_status
        case.version += 1
        case.updated_at = utc_now()
        self.session.flush()
        return case


class HandoverPackageRepository:
    """Repository for managing HandoverPackage container records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, package: HandoverPackage) -> HandoverPackage:
        self.session.add(package)
        self.session.flush()
        return package

    def get_by_case(self, case_id: uuid.UUID) -> HandoverPackage | None:
        stmt = (
            select(HandoverPackage)
            .where(HandoverPackage.case_id == case_id)
            .options(selectinload(HandoverPackage.versions))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_id(self, package_id: uuid.UUID) -> HandoverPackage | None:
        stmt = (
            select(HandoverPackage)
            .where(HandoverPackage.id == package_id)
            .options(selectinload(HandoverPackage.versions))
        )
        return self.session.execute(stmt).scalar_one_or_none()


class HandoverPackageVersionRepository:
    """Repository for managing HandoverPackageVersion snapshots."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, version: HandoverPackageVersion) -> HandoverPackageVersion:
        self.session.add(version)
        self.session.flush()
        return version

    def get_by_id(
        self, version_id: uuid.UUID, *, load_sections: bool = True
    ) -> HandoverPackageVersion | None:
        stmt = select(HandoverPackageVersion).where(HandoverPackageVersion.id == version_id)
        if load_sections:
            stmt = stmt.options(
                selectinload(HandoverPackageVersion.sections).selectinload(
                    HandoverPackageSection.content_links
                ),
                selectinload(HandoverPackageVersion.readiness_assessments),
                selectinload(HandoverPackageVersion.signoffs),
                selectinload(HandoverPackageVersion.deliveries),
                selectinload(HandoverPackageVersion.package),
                selectinload(HandoverPackageVersion.case),
            )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_current(self, package_id: uuid.UUID) -> HandoverPackageVersion | None:
        stmt = (
            select(HandoverPackageVersion)
            .where(
                HandoverPackageVersion.package_id == package_id,
                HandoverPackageVersion.is_current.is_(True),
            )
            .options(
                selectinload(HandoverPackageVersion.sections),
                selectinload(HandoverPackageVersion.readiness_assessments),
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_latest_by_case(self, case_id: uuid.UUID) -> HandoverPackageVersion | None:
        stmt = (
            select(HandoverPackageVersion)
            .where(HandoverPackageVersion.case_id == case_id)
            .order_by(HandoverPackageVersion.version_number.desc())
            .limit(1)
            .options(
                selectinload(HandoverPackageVersion.sections),
                selectinload(HandoverPackageVersion.readiness_assessments),
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_package(self, package_id: uuid.UUID) -> list[HandoverPackageVersion]:
        stmt = (
            select(HandoverPackageVersion)
            .where(HandoverPackageVersion.package_id == package_id)
            .order_by(HandoverPackageVersion.version_number.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_next_version_number(self, package_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.max(HandoverPackageVersion.version_number), 0)).where(
            HandoverPackageVersion.package_id == package_id
        )
        current_max = self.session.execute(stmt).scalar_one()
        return current_max + 1

    def set_current(self, package_id: uuid.UUID, version_id: uuid.UUID) -> None:
        # unset others
        self.session.execute(
            update(HandoverPackageVersion)
            .where(HandoverPackageVersion.package_id == package_id)
            .values(is_current=False)
        )
        # set target
        self.session.execute(
            update(HandoverPackageVersion)
            .where(HandoverPackageVersion.id == version_id)
            .values(is_current=True)
        )
        self.session.flush()


class HandoverSectionRepository:
    """Repository for managing HandoverPackageSection records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, section: HandoverPackageSection) -> HandoverPackageSection:
        self.session.add(section)
        self.session.flush()
        return section

    def get_by_id(
        self, section_id: uuid.UUID, *, load_links: bool = True
    ) -> HandoverPackageSection | None:
        stmt = select(HandoverPackageSection).where(HandoverPackageSection.id == section_id)
        if load_links:
            stmt = stmt.options(selectinload(HandoverPackageSection.content_links))
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_version(
        self, version_id: uuid.UUID, *, load_links: bool = True
    ) -> list[HandoverPackageSection]:
        stmt = (
            select(HandoverPackageSection)
            .where(HandoverPackageSection.version_id == version_id)
            .order_by(HandoverPackageSection.section_order.asc())
        )
        if load_links:
            stmt = stmt.options(selectinload(HandoverPackageSection.content_links))
        return list(self.session.execute(stmt).scalars().all())

    def update_content(
        self,
        section_id: uuid.UUID,
        *,
        content: str | None = None,
        summary: str | None = None,
    ) -> HandoverPackageSection | None:
        section = self.session.get(HandoverPackageSection, section_id)
        if not section:
            return None
        if content is not None:
            section.section_content = content
        if summary is not None:
            section.content_summary = summary
        self.session.flush()
        return section


class HandoverContentLinkRepository:
    """Repository for managing HandoverContentLink records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, link: HandoverContentLink) -> HandoverContentLink:
        self.session.add(link)
        self.session.flush()
        return link

    def create_bulk(self, links: list[HandoverContentLink]) -> list[HandoverContentLink]:
        for link in links:
            self.session.add(link)
        self.session.flush()
        return links

    def list_by_section(self, section_id: uuid.UUID) -> list[HandoverContentLink]:
        stmt = (
            select(HandoverContentLink)
            .where(HandoverContentLink.section_id == section_id)
            .order_by(HandoverContentLink.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_by_version(self, version_id: uuid.UUID) -> list[HandoverContentLink]:
        stmt = (
            select(HandoverContentLink)
            .where(HandoverContentLink.version_id == version_id)
            .order_by(HandoverContentLink.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars().all())


class HandoverReadinessRepository:
    """Repository for managing HandoverReadinessAssessment records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, assessment: HandoverReadinessAssessment) -> HandoverReadinessAssessment:
        self.session.add(assessment)
        self.session.flush()
        return assessment

    def create_bulk(
        self, assessments: list[HandoverReadinessAssessment]
    ) -> list[HandoverReadinessAssessment]:
        for a in assessments:
            self.session.add(a)
        self.session.flush()
        return assessments

    def list_by_version(self, version_id: uuid.UUID) -> list[HandoverReadinessAssessment]:
        stmt = (
            select(HandoverReadinessAssessment)
            .where(HandoverReadinessAssessment.version_id == version_id)
            .order_by(HandoverReadinessAssessment.category.asc())
        )
        return list(self.session.execute(stmt).scalars().all())


class HandoverChecklistRepository:
    """Repository for managing HandoverChecklist and HandoverChecklistItem records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, checklist: HandoverChecklist) -> HandoverChecklist:
        self.session.add(checklist)
        self.session.flush()
        return checklist

    def get_by_id(
        self, checklist_id: uuid.UUID, *, load_items: bool = True
    ) -> HandoverChecklist | None:
        stmt = select(HandoverChecklist).where(HandoverChecklist.id == checklist_id)
        if load_items:
            stmt = stmt.options(selectinload(HandoverChecklist.items))
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_case(self, case_id: uuid.UUID) -> list[HandoverChecklist]:
        stmt = (
            select(HandoverChecklist)
            .where(HandoverChecklist.case_id == case_id)
            .options(selectinload(HandoverChecklist.items))
            .order_by(HandoverChecklist.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def create_item(self, item: HandoverChecklistItem) -> HandoverChecklistItem:
        self.session.add(item)
        self.session.flush()
        return item

    def create_items_bulk(
        self, items: list[HandoverChecklistItem]
    ) -> list[HandoverChecklistItem]:
        for item in items:
            self.session.add(item)
        self.session.flush()
        return items

    def get_item_by_id(self, item_id: uuid.UUID) -> HandoverChecklistItem | None:
        return self.session.get(HandoverChecklistItem, item_id)

    def update_item_status(
        self,
        item_id: uuid.UUID,
        *,
        status: str,
        completed_by_user_id: uuid.UUID | None = None,
        notes: str | None = None,
    ) -> HandoverChecklistItem | None:
        item = self.session.get(HandoverChecklistItem, item_id)
        if not item:
            return None
        item.status = status
        if status == ChecklistItemStatus.COMPLETED.value:
            item.completed_at = utc_now()
            item.completed_by_user_id = completed_by_user_id
        else:
            item.completed_at = None
            item.completed_by_user_id = None
        if notes is not None:
            item.notes = notes
        item.updated_at = utc_now()

        # Update parent checklist counters
        checklist = self.session.get(HandoverChecklist, item.checklist_id)
        if checklist:
            completed_count = sum(
                1 for i in checklist.items if i.status == ChecklistItemStatus.COMPLETED.value
            )
            checklist.completed_items = completed_count
            checklist.is_completed = (
                checklist.total_items > 0 and completed_count == checklist.total_items
            )
            checklist.updated_at = utc_now()

        self.session.flush()
        return item


class HandoverResponsibilityTransferRepository:
    """Repository for managing HandoverResponsibilityTransfer records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, transfer: HandoverResponsibilityTransfer) -> HandoverResponsibilityTransfer:
        self.session.add(transfer)
        self.session.flush()
        return transfer

    def create_bulk(
        self, transfers: list[HandoverResponsibilityTransfer]
    ) -> list[HandoverResponsibilityTransfer]:
        for t in transfers:
            self.session.add(t)
        self.session.flush()
        return transfers

    def list_by_case(self, case_id: uuid.UUID) -> list[HandoverResponsibilityTransfer]:
        stmt = (
            select(HandoverResponsibilityTransfer)
            .where(HandoverResponsibilityTransfer.case_id == case_id)
            .order_by(HandoverResponsibilityTransfer.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def update_status(
        self,
        transfer_id: uuid.UUID,
        *,
        status: str,
        transfer_notes: str | None = None,
    ) -> HandoverResponsibilityTransfer | None:
        transfer = self.session.get(HandoverResponsibilityTransfer, transfer_id)
        if not transfer:
            return None
        transfer.transfer_status = status
        if status == TransferStatus.COMPLETED.value:
            transfer.transferred_at = utc_now()
        if transfer_notes is not None:
            transfer.transfer_notes = transfer_notes
        transfer.updated_at = utc_now()
        self.session.flush()
        return transfer


class HandoverSignoffRepository:
    """Repository for managing HandoverSignoff records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, signoff: HandoverSignoff) -> HandoverSignoff:
        self.session.add(signoff)
        self.session.flush()
        return signoff

    def get_by_case_and_type(
        self, case_id: uuid.UUID, version_id: uuid.UUID, signoff_type: str
    ) -> HandoverSignoff | None:
        stmt = select(HandoverSignoff).where(
            HandoverSignoff.case_id == case_id,
            HandoverSignoff.version_id == version_id,
            HandoverSignoff.signoff_type == signoff_type,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_case(self, case_id: uuid.UUID) -> list[HandoverSignoff]:
        stmt = (
            select(HandoverSignoff)
            .where(HandoverSignoff.case_id == case_id)
            .order_by(HandoverSignoff.signed_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_by_version(self, version_id: uuid.UUID) -> list[HandoverSignoff]:
        stmt = (
            select(HandoverSignoff)
            .where(HandoverSignoff.version_id == version_id)
            .order_by(HandoverSignoff.signed_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())


class HandoverDeliveryRepository:
    """Repository for managing HandoverDelivery records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, delivery: HandoverDelivery) -> HandoverDelivery:
        self.session.add(delivery)
        self.session.flush()
        return delivery

    def get_by_id(self, delivery_id: uuid.UUID) -> HandoverDelivery | None:
        stmt = (
            select(HandoverDelivery)
            .where(HandoverDelivery.id == delivery_id)
            .options(selectinload(HandoverDelivery.acknowledgements))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_version(self, version_id: uuid.UUID) -> list[HandoverDelivery]:
        stmt = (
            select(HandoverDelivery)
            .where(HandoverDelivery.version_id == version_id)
            .options(selectinload(HandoverDelivery.acknowledgements))
            .order_by(HandoverDelivery.delivered_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())


class HandoverAcknowledgementRepository:
    """Repository for managing HandoverAcknowledgement records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, ack: HandoverAcknowledgement) -> HandoverAcknowledgement:
        self.session.add(ack)
        self.session.flush()
        return ack

    def get_by_delivery(self, delivery_id: uuid.UUID) -> HandoverAcknowledgement | None:
        stmt = select(HandoverAcknowledgement).where(
            HandoverAcknowledgement.delivery_id == delivery_id
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_case(self, case_id: uuid.UUID) -> list[HandoverAcknowledgement]:
        stmt = (
            select(HandoverAcknowledgement)
            .where(HandoverAcknowledgement.case_id == case_id)
            .order_by(HandoverAcknowledgement.acknowledged_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())


class HandoverStatusHistoryRepository:
    """Repository for managing HandoverStatusHistory records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, history: HandoverStatusHistory) -> HandoverStatusHistory:
        self.session.add(history)
        self.session.flush()
        return history

    def list_by_case(self, case_id: uuid.UUID) -> list[HandoverStatusHistory]:
        stmt = (
            select(HandoverStatusHistory)
            .where(HandoverStatusHistory.case_id == case_id)
            .order_by(HandoverStatusHistory.changed_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())


class HandoverOwnershipTransferRepository:
    """Repository for managing HandoverOwnershipTransfer records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, transfer: HandoverOwnershipTransfer) -> HandoverOwnershipTransfer:
        self.session.add(transfer)
        self.session.flush()
        return transfer

    def get_by_id(self, transfer_id: uuid.UUID) -> HandoverOwnershipTransfer | None:
        return self.session.get(HandoverOwnershipTransfer, transfer_id)

    def list_by_case(self, case_id: uuid.UUID) -> list[HandoverOwnershipTransfer]:
        stmt = (
            select(HandoverOwnershipTransfer)
            .where(HandoverOwnershipTransfer.case_id == case_id)
            .order_by(HandoverOwnershipTransfer.executed_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def mark_rolled_back(
        self,
        transfer_id: uuid.UUID,
        *,
        rolled_back_by_user_id: uuid.UUID,
        rollback_reason: str,
    ) -> HandoverOwnershipTransfer | None:
        transfer = self.session.get(HandoverOwnershipTransfer, transfer_id)
        if not transfer:
            return None
        transfer.rolled_back = True
        transfer.rollback_reason = rollback_reason
        transfer.rolled_back_at = utc_now()
        transfer.rolled_back_by_user_id = rolled_back_by_user_id
        self.session.flush()
        return transfer
