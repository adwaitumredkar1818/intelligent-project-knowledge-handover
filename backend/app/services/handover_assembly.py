"""Handover Package Assembly Service.

Platform: The Handover
Module: Handover Workspace (Module 4 / Knowledge Transfer Area)

Enforces:
1. Deterministic 8-domain compilation engine
2. Strict downstream eligibility verification via HandoverEligibilityService
3. Immutable version snapshots with cryptographic content hashes
4. Four-tier epistemic separation (only human_verified knowledge is eligible)
5. Zero synthetic or unverified claims in published handover content
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.security import utc_now
from app.models.audit import AuditLog
from app.models.enums import (
    AuditOutcome,
    HandoverCaseStatus,
    HandoverLinkType,
    HandoverPackageSectionType,
    KnowledgeCategory,
)
from app.models.handover import (
    HandoverCase,
    HandoverContentLink,
    HandoverPackage,
    HandoverPackageSection,
    HandoverPackageVersion,
)
from app.models.knowledge import KnowledgeItem
from app.models.relationship import KnowledgeRelationship
from app.repositories.audit import AuditLogRepository
from app.repositories.handover import (
    HandoverCaseRepository,
    HandoverContentLinkRepository,
    HandoverPackageRepository,
    HandoverPackageVersionRepository,
    HandoverSectionRepository,
)
from app.schemas.handover import PackageAssemblyRequest
from app.services.audit import AuditService
from app.services.handover_case import HandoverCaseService
from app.services.handover_eligibility import HandoverEligibilityService

# Map Knowledge categories to Section types
DOMAIN_CATEGORY_MAP: dict[str, list[str]] = {
    HandoverPackageSectionType.DECISIONS_RATIONALE.value: [
        KnowledgeCategory.DECISIONS_RATIONALE.value,
    ],
    HandoverPackageSectionType.TECHNICAL_ARCHITECTURE.value: [
        KnowledgeCategory.TECHNICAL_ARCHITECTURE.value,
        KnowledgeCategory.ARCHITECTURE_TECHNICAL.value,
    ],
    HandoverPackageSectionType.WORK_PROGRESS.value: [
        KnowledgeCategory.WORK_ITEMS.value,
        KnowledgeCategory.WORK_PROGRESS.value,
    ],
    HandoverPackageSectionType.RESPONSIBILITIES_OWNERSHIP.value: [
        KnowledgeCategory.RESPONSIBILITIES_OWNERSHIP.value,
    ],
    HandoverPackageSectionType.DEPENDENCIES_RELATIONSHIPS.value: [
        KnowledgeCategory.DEPENDENCIES.value,
        KnowledgeCategory.DEPENDENCIES_RELATIONSHIPS.value,
    ],
    HandoverPackageSectionType.BUGS_BLOCKERS_RISKS.value: [
        KnowledgeCategory.BUGS_BLOCKERS_RISKS.value,
        KnowledgeCategory.RISKS_BLOCKERS_QUESTIONS.value,
    ],
    HandoverPackageSectionType.OPERATIONAL_HISTORICAL.value: [
        KnowledgeCategory.OPERATIONAL_HISTORICAL.value,
    ],
    HandoverPackageSectionType.PROJECT_OVERVIEW_CONTEXT.value: [
        KnowledgeCategory.PROJECT_OVERVIEW_CONTEXT.value,
    ],
}

SECTION_TITLES: dict[str, str] = {
    HandoverPackageSectionType.PROJECT_OVERVIEW_CONTEXT.value: "Project Overview & Strategic Context",
    HandoverPackageSectionType.DECISIONS_RATIONALE.value: "Key Architecture & Technical Decisions",
    HandoverPackageSectionType.TECHNICAL_ARCHITECTURE.value: "System Architecture, Services & Schemas",
    HandoverPackageSectionType.WORK_PROGRESS.value: "Active Work, Backlog & In-Flight Tasks",
    HandoverPackageSectionType.RESPONSIBILITIES_OWNERSHIP.value: "Component Ownership & Team Roles",
    HandoverPackageSectionType.DEPENDENCIES_RELATIONSHIPS.value: "Upstream/Downstream Dependencies",
    HandoverPackageSectionType.BUGS_BLOCKERS_RISKS.value: "Known Issues, Blockers & Open Risks",
    HandoverPackageSectionType.OPERATIONAL_HISTORICAL.value: "Operational Procedures & Runbooks",
}

SECTION_ORDER: list[str] = [
    HandoverPackageSectionType.PROJECT_OVERVIEW_CONTEXT.value,
    HandoverPackageSectionType.DECISIONS_RATIONALE.value,
    HandoverPackageSectionType.TECHNICAL_ARCHITECTURE.value,
    HandoverPackageSectionType.WORK_PROGRESS.value,
    HandoverPackageSectionType.RESPONSIBILITIES_OWNERSHIP.value,
    HandoverPackageSectionType.DEPENDENCIES_RELATIONSHIPS.value,
    HandoverPackageSectionType.BUGS_BLOCKERS_RISKS.value,
    HandoverPackageSectionType.OPERATIONAL_HISTORICAL.value,
]


class PackageAssemblyService:
    """Orchestrates deterministic compilation of verified project knowledge into handover packages."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.case_repo = HandoverCaseRepository(session)
        self.package_repo = HandoverPackageRepository(session)
        self.version_repo = HandoverPackageVersionRepository(session)
        self.section_repo = HandoverSectionRepository(session)
        self.link_repo = HandoverContentLinkRepository(session)
        self.eligibility_service = HandoverEligibilityService(session)
        self.case_service = HandoverCaseService(session)
        self.audit_service = AuditService(audit_repository=AuditLogRepository(session))

    def assemble_package_version(
        self,
        case_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        request: PackageAssemblyRequest,
        has_project_manage: bool = True,
    ) -> HandoverPackageVersion:
        """Assemble an immutable handover package version from eligible project knowledge."""
        case = self.case_service.get_case(case_id, project_id=project_id, load_relationships=False)

        # Transition case to ASSEMBLING
        if case.status in (HandoverCaseStatus.DRAFT.value, HandoverCaseStatus.ASSEMBLED.value):
            self.case_service.transition_status(
                case_id,
                project_id=project_id,
                new_status=HandoverCaseStatus.ASSEMBLING.value,
                user_id=user_id,
                change_reason="Starting package compilation",
            )

        # Ensure container package exists
        package = self.package_repo.get_by_case(case.id)
        if not package:
            package = HandoverPackage(
                organisation_id=case.organisation_id,
                project_id=project_id,
                case_id=case.id,
                title=f"Handover Package: {case.title}",
                summary=case.description,
                created_by_user_id=user_id,
            )
            package = self.package_repo.create(package)

        next_version_num = self.version_repo.get_next_version_number(package.id)

        # Query all active knowledge items for the project
        stmt_ki = select(KnowledgeItem).where(
            KnowledgeItem.project_id == project_id,
            KnowledgeItem.is_deleted.is_(False),
        )
        knowledge_items = list(self.session.execute(stmt_ki).scalars().all())

        # Exclusions filter
        exclude_kis = set(request.exclude_knowledge_item_ids or [])
        exclude_rels = set(request.exclude_relationship_ids or [])
        filtered_kis = [ki for ki in knowledge_items if ki.id not in exclude_kis]

        # Query all active relationships for the project
        stmt_rel = select(KnowledgeRelationship).where(
            KnowledgeRelationship.project_id == project_id
        )
        relationships = list(self.session.execute(stmt_rel).scalars().all())
        filtered_rels = [r for r in relationships if r.id not in exclude_rels]

        # Evaluate eligibility for all items
        eligible_items_by_section: dict[str, list[tuple[KnowledgeItem, Any]]] = {
            sec: [] for sec in SECTION_ORDER
        }

        included_ki_ids: list[str] = []
        excluded_ki_ids: list[dict[str, Any]] = []

        for ki in filtered_kis:
            eligibility = self.eligibility_service.check_knowledge_item_eligibility(
                ki.id,
                viewer_user_id=user_id,
                has_project_manage=has_project_manage,
            )
            if eligibility.is_eligible:
                included_ki_ids.append(str(ki.id))
                # Map to target section
                matched_section = HandoverPackageSectionType.PROJECT_OVERVIEW_CONTEXT.value
                for sec_type, categories in DOMAIN_CATEGORY_MAP.items():
                    if ki.category in categories:
                        matched_section = sec_type
                        break
                eligible_items_by_section[matched_section].append((ki, eligibility))
            else:
                excluded_ki_ids.append({
                    "id": str(ki.id),
                    "title": ki.title or str(ki.id),
                    "blockers": eligibility.blockers,
                })

        # Evaluate eligibility for relationships
        eligible_rels_by_section: dict[str, list[tuple[KnowledgeRelationship, Any]]] = {
            sec: [] for sec in SECTION_ORDER
        }
        for rel in filtered_rels:
            eligibility = self.eligibility_service.check_relationship_eligibility(
                rel.id,
                viewer_user_id=user_id,
                has_project_manage=has_project_manage,
            )
            if eligibility.is_eligible:
                # Place in DEPENDENCIES_RELATIONSHIPS by default
                eligible_rels_by_section[
                    HandoverPackageSectionType.DEPENDENCIES_RELATIONSHIPS.value
                ].append((rel, eligibility))

        # Build snapshot data
        snapshot_data: dict[str, Any] = {
            "version_number": next_version_num,
            "assembled_at": utc_now().isoformat(),
            "assembled_by_user_id": str(user_id),
            "project_id": str(project_id),
            "case_id": str(case_id),
            "total_eligible_knowledge_items": len(included_ki_ids),
            "total_excluded_knowledge_items": len(excluded_ki_ids),
            "excluded_items": excluded_ki_ids,
            "domains_included": request.include_domains or SECTION_ORDER,
        }

        # Create Version record
        version = HandoverPackageVersion(
            organisation_id=case.organisation_id,
            project_id=project_id,
            package_id=package.id,
            case_id=case.id,
            version_number=next_version_num,
            is_current=True,
            assembly_status="assembled",
            assembly_snapshot_json=snapshot_data,
            assembled_by_user_id=user_id,
            assembled_at=utc_now(),
            notes=request.assembly_notes,
        )
        created_version = self.version_repo.create(version)
        self.version_repo.set_current(package.id, created_version.id)

        # Generate Sections and Content Links
        section_hashes: list[str] = []

        for order, sec_type in enumerate(SECTION_ORDER, start=1):
            if request.include_domains and sec_type not in request.include_domains:
                continue

            sec_items = eligible_items_by_section.get(sec_type, [])
            sec_rels = eligible_rels_by_section.get(sec_type, [])

            # Generate structured section narrative content
            content_lines: list[str] = [
                f"# {SECTION_TITLES[sec_type]}",
                "",
                f"Compiled {len(sec_items)} verified knowledge items and {len(sec_rels)} verified relationships.",
                "",
            ]

            for ki, _ in sec_items:
                title = ki.title or "Verified Finding"
                details = ki.structured_summary or ""
                content_lines.append(f"### {title}")
                if details:
                    content_lines.append(f"{details}")
                content_lines.append(f"- **Epistemic Status**: {ki.epistemic_status}")
                content_lines.append(f"- **Support**: {ki.support_classification}")
                content_lines.append("")

            for rel, _ in sec_rels:
                content_lines.append(f"- **Relationship**: `{rel.relationship_type}` (from `{rel.source_entity_id}` to `{rel.target_entity_id}`)")

            section_text = "\n".join(content_lines)
            sec_hash = hashlib.sha256(section_text.encode("utf-8")).hexdigest()
            section_hashes.append(sec_hash)

            section = HandoverPackageSection(
                organisation_id=case.organisation_id,
                project_id=project_id,
                version_id=created_version.id,
                section_type=sec_type,
                section_title=SECTION_TITLES[sec_type],
                section_content=section_text,
                content_summary=f"{len(sec_items)} items, {len(sec_rels)} relationships.",
                section_order=order,
                knowledge_item_count=len(sec_items),
                relationship_count=len(sec_rels),
                metadata_json={"sha256": sec_hash},
            )
            created_section = self.section_repo.create(section)

            # Create Content Links for Knowledge Items
            links_to_create: list[HandoverContentLink] = []
            for ki, elig in sec_items:
                links_to_create.append(
                    HandoverContentLink(
                        organisation_id=case.organisation_id,
                        project_id=project_id,
                        section_id=created_section.id,
                        version_id=created_version.id,
                        link_type=HandoverLinkType.KNOWLEDGE_ITEM.value,
                        knowledge_item_id=ki.id,
                        eligibility_status_json={
                            "is_eligible": elig.is_eligible,
                            "case_status": elig.case_status,
                            "epistemic_status": elig.epistemic_status,
                        },
                    )
                )

            # Create Content Links for Relationships
            for rel, elig in sec_rels:
                links_to_create.append(
                    HandoverContentLink(
                        organisation_id=case.organisation_id,
                        project_id=project_id,
                        section_id=created_section.id,
                        version_id=created_version.id,
                        link_type=HandoverLinkType.RELATIONSHIP.value,
                        relationship_id=rel.id,
                        eligibility_status_json={
                            "is_eligible": elig.is_eligible,
                            "case_status": elig.case_status,
                        },
                    )
                )

            if links_to_create:
                self.link_repo.create_bulk(links_to_create)

        # Compute version-level content hash
        version_hash = hashlib.sha256("".join(section_hashes).encode("utf-8")).hexdigest()
        created_version.content_hash = version_hash

        # Transition Case to ASSEMBLED
        self.case_service.transition_status(
            case_id,
            project_id=project_id,
            new_status=HandoverCaseStatus.ASSEMBLED.value,
            user_id=user_id,
            change_reason=f"Assembled package version {created_version.version_number}",
        )

        self.audit_service.record_event(
            event_type="handover.package.assembled",
            resource_type="handover_package_version",
            resource_id=str(created_version.id),
            actor_user_id=user_id,
            organisation_id=case.organisation_id,
            project_id=project_id,
            outcome=AuditOutcome.SUCCESS.value,
            metadata={
                "version_number": next_version_num,
                "content_hash": version_hash,
                "eligible_items_count": len(included_ki_ids),
                "excluded_items_count": len(excluded_ki_ids),
            },
        )

        self.session.flush()
        return created_version
