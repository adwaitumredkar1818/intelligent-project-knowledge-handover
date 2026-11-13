"""Comprehensive Live Functionality, Security & E2E Testing Audit for Handover Workspace.

Module: Handover Workspace (Module 4 / Knowledge Transfer Area)
Platform: The Handover (Intelligent Project Knowledge Reconstruction & Handover Platform)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.rbac_catalog import deterministic_rbac_id
from app.core.security import create_access_token, hash_password
from app.db.session import create_db_engine
from app.main import create_app
from app.models.auth import RefreshSession
from app.models.enums import (
    ChecklistItemStatus,
    ConflictResolutionState,
    ConflictType,
    EpistemicStatus,
    EvidenceProcessingStatus,
    EvidenceSourceType,
    HandoverCaseStatus,
    HandoverChecklistType,
    HandoverDeliveryMethod,
    HandoverPackageSectionType,
    HandoverReadinessCategory,
    KnowledgeCategory,
    KnowledgeReviewStatus,
    OrganisationStatus,
    OwnershipTransferType,
    ProjectStatus,
    ProjectVisibility,
    ReadinessLevel,
    RelationshipBasis,
    RelationshipVerificationStatus,
    RoleName,
    SignoffDecision,
    SignoffType,
    TransferStatus,
    UserStatus,
    VerificationCaseStatus,
    VerificationPriority,
    VerificationSeverity,
    VerificationTargetType,
)
from app.models.evidence import EvidenceChunk, EvidenceItem
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
from app.models.knowledge import KnowledgeEvidenceLink, KnowledgeItem
from app.models.organisation import Organisation, OrganisationMembership
from app.models.project import Project, ProjectMembership
from app.models.relationship import KnowledgeEntity, KnowledgeRelationship
from app.models.user import User
from app.models.verification import VerificationCase
from app.services.handover_assembly import PackageAssemblyService
from app.services.handover_case import HandoverCaseService
from app.services.handover_checklist import ChecklistService
from app.services.handover_eligibility import HandoverEligibilityService
from app.services.handover_narrative import HandoverNarrativeService
from app.services.handover_ownership import OwnershipTransferService
from app.services.handover_readiness import HandoverReadinessEngine
from app.services.handover_signoff import HandoverSignoffService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("handover_audit")


def _setup_test_context(session: Session) -> tuple[User, User, User, Organisation, Project]:
    """Create isolated test organisation, project, departing member, successor, and reviewer."""
    # 1. Departing member
    departing = User(
        id=uuid.uuid4(),
        email=f"departing-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("DepartingSecret123!"),
        full_name="Alice Departing Lead",
        status=UserStatus.ACTIVE,
    )
    # 2. Successor
    successor = User(
        id=uuid.uuid4(),
        email=f"successor-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("SuccessorSecret123!"),
        full_name="Bob Incoming Lead",
        status=UserStatus.ACTIVE,
    )
    # 3. Independent Reviewer
    reviewer = User(
        id=uuid.uuid4(),
        email=f"reviewer-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("ReviewerSecret123!"),
        full_name="Carol Project Reviewer",
        status=UserStatus.ACTIVE,
    )
    session.add_all([departing, successor, reviewer])
    session.flush()

    # Organisation
    org = Organisation(
        id=uuid.uuid4(),
        name=f"Handover Test Org {uuid.uuid4().hex[:6]}",
        slug=f"handover-org-{uuid.uuid4().hex[:6]}",
        created_by_id=reviewer.id,
        status=OrganisationStatus.ACTIVE,
    )
    session.add(org)
    session.flush()

    # Org Memberships (Reviewer is ORG_OWNER, others are ORG_MEMBER)
    session.add(
        OrganisationMembership(
            id=uuid.uuid4(),
            organisation_id=org.id,
            user_id=reviewer.id,
            role_id=deterministic_rbac_id("role", RoleName.ORG_OWNER.value),
            status="active",
            joined_at=datetime.now(UTC),
        )
    )
    session.add(
        OrganisationMembership(
            id=uuid.uuid4(),
            organisation_id=org.id,
            user_id=departing.id,
            role_id=deterministic_rbac_id("role", RoleName.ORG_MEMBER.value),
            status="active",
            joined_at=datetime.now(UTC),
        )
    )
    session.add(
        OrganisationMembership(
            id=uuid.uuid4(),
            organisation_id=org.id,
            user_id=successor.id,
            role_id=deterministic_rbac_id("role", RoleName.ORG_MEMBER.value),
            status="active",
            joined_at=datetime.now(UTC),
        )
    )
    session.flush()

    # Project
    project = Project(
        id=uuid.uuid4(),
        organisation_id=org.id,
        created_by_id=reviewer.id,
        owner_id=departing.id,
        name=f"Handover Test Project {uuid.uuid4().hex[:6]}",
        slug=f"handover-proj-{uuid.uuid4().hex[:6]}",
        visibility=ProjectVisibility.ORGANISATION,
        status=ProjectStatus.ACTIVE,
    )
    session.add(project)
    session.flush()

    # Project Memberships
    session.add(
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=project.id,
            user_id=reviewer.id,
            role_id=deterministic_rbac_id("role", RoleName.REVIEWER.value),
            status="active",
        )
    )
    session.add(
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=project.id,
            user_id=departing.id,
            role_id=deterministic_rbac_id("role", RoleName.PROJECT_MEMBER.value),
            status="active",
        )
    )
    session.add(
        ProjectMembership(
            id=uuid.uuid4(),
            project_id=project.id,
            user_id=successor.id,
            role_id=deterministic_rbac_id("role", RoleName.PROJECT_MEMBER.value),
            status="active",
        )
    )
    session.flush()

    return departing, successor, reviewer, org, project


def _create_verified_finding(
    session: Session,
    org: Organisation,
    project: Project,
    user: User,
    *,
    category: str = "decisions_rationale",
    title: str = "Adopt FastAPI and SQLAlchemy 2.x",
    claim: str = "Use FastAPI and SQLAlchemy 2.x for all backend services",
) -> KnowledgeItem:
    """Create a fully human-verified, approved knowledge item with supporting evidence."""
    # Supporting Evidence Item
    ev = EvidenceItem(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=project.id,
        uploaded_by_user_id=user.id,
        source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
        source_provider="local_upload",
        category="pdf_document",
        source_external_id=uuid.uuid4().hex,
        title=f"Architecture Document {uuid.uuid4().hex[:6]}.pdf",
        original_filename="arch_doc.pdf",
        content_hash=hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
        file_size_bytes=2048,
        mime_type="application/pdf",
        source_created_at=datetime.now(UTC),
        processing_status=EvidenceProcessingStatus.EXTRACTED.value,
        acl_scope="project_members",
    )
    session.add(ev)
    session.flush()

    # Knowledge Item (Epistemic: HUMAN_VERIFIED, Review: APPROVED)
    ki = KnowledgeItem(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=project.id,
        category=category,
        primary_domain=category,
        title=title,
        structured_summary=claim,
        structured_payload={"rfc": 42},
        support_classification="direct",
        extraction_model="qwen3:8b",
        prompt_version="1.0.0",
        fingerprint=uuid.uuid4().hex,
        epistemic_status=EpistemicStatus.HUMAN_VERIFIED.value,
        review_status=KnowledgeReviewStatus.APPROVED.value,
        is_stale=False,
        is_deleted=False,
    )
    session.add(ki)
    session.flush()

    # Link evidence
    link = KnowledgeEvidenceLink(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=project.id,
        knowledge_item_id=ki.id,
        evidence_id=ev.id,
        support_type="direct",
        supporting_excerpt=claim,
    )
    session.add(link)
    session.flush()

    # Active Verification Case in VERIFIED status
    v_case = VerificationCase(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=project.id,
        target_type=VerificationTargetType.KNOWLEDGE_ITEM.value,
        target_id=ki.id,
        case_status=VerificationCaseStatus.VERIFIED.value,
        priority=VerificationPriority.MEDIUM.value,
        machine_assessment_json={"status": "passed"},
        version=1,
    )
    session.add(v_case)
    session.flush()

    return ki


def run_full_handover_audit() -> dict[str, Any]:
    """Execute complete Handover Workspace audit test suite."""
    settings = get_settings()
    engine = create_db_engine(settings)
    session_factory = sessionmaker(bind=engine)

    results: list[dict[str, Any]] = []

    def log_result(test_id: str, name: str, passed: bool, details: str) -> None:
        status_str = "PASS" if passed else "FAIL"
        logger.info(f"[{status_str}] {test_id}: {name} - {details}")
        results.append({
            "test_id": test_id,
            "name": name,
            "passed": passed,
            "details": details,
        })

    # =========================================================================
    # PART 1: Database Schema & Relational Integrity
    # =========================================================================
    logger.info("=== 1. Live Database Models & Schema Integrity ===")
    with session_factory() as session:
        expected_tables = [
            "handover_cases",
            "handover_packages",
            "handover_package_versions",
            "handover_package_sections",
            "handover_content_links",
            "handover_readiness_assessments",
            "handover_checklists",
            "handover_checklist_items",
            "handover_responsibility_transfers",
            "handover_signoffs",
            "handover_deliveries",
            "handover_acknowledgements",
            "handover_status_histories",
            "handover_ownership_transfers",
        ]
        res_tables = list(
            session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'handover%';"
                )
            ).scalars().all()
        )
        tables_found = {t: t in res_tables for t in expected_tables}
        all_tables_present = all(tables_found.values())

        log_result(
            "DB-01",
            "All 14 Handover Tables Exist in PostgreSQL",
            all_tables_present,
            f"Found {sum(tables_found.values())}/{len(expected_tables)} tables.",
        )

    # =========================================================================
    # PART 2: Isolated Test Context Setup
    # =========================================================================
    logger.info("=== 2. Setting Up Test Fixtures ===")
    with session_factory() as session:
        departing, successor, reviewer, org, project = _setup_test_context(session)

        # Create verified findings across domains
        ki_dec = _create_verified_finding(
            session, org, project, reviewer,
            category="decisions_rationale",
            title="Adopt Microservices & FastAPI",
            claim="Standardize on FastAPI for backend APIs and services",
        )
        ki_arch = _create_verified_finding(
            session, org, project, reviewer,
            category="technical_architecture",
            title="PostgreSQL as Canonical Store",
            claim="PostgreSQL is the single source of truth for all structured data",
        )
        ki_work = _create_verified_finding(
            session, org, project, reviewer,
            category="work_items",
            title="Q4 Handover Milestone",
            claim="Complete Module 4 handover workspace implementation",
        )

        session.commit()
        project_id = project.id
        org_id = org.id
        departing_id = departing.id
        successor_id = successor.id
        reviewer_id = reviewer.id
        ki_dec_id = ki_dec.id

    # =========================================================================
    # PART 3: Case Creation & Concurrency Control (TEST-A & TEST-B)
    # =========================================================================
    logger.info("=== 3. Case Creation & Concurrency Control ===")
    with session_factory() as session:
        case_service = HandoverCaseService(session)
        from app.schemas.handover import HandoverCaseCreateRequest

        create_req = HandoverCaseCreateRequest(
            title="Lead Engineer Offboarding Case",
            description="Complete project handover for departing backend lead.",
            departing_member_id=departing_id,
            successor_id=successor_id,
        )
        case = case_service.create_case(
            organisation_id=org_id,
            project_id=project_id,
            user_id=reviewer_id,
            request=create_req,
        )
        case_id = case.id
        session.commit()

        log_result(
            "TEST-A",
            "Create HandoverCase in DRAFT Status",
            case.status == HandoverCaseStatus.DRAFT.value and case.version == 1,
            f"Case {case_id} created in status '{case.status}' with version {case.version}.",
        )

        # Test Concurrency Conflict
        from app.core.exceptions import ConflictError
        conflict_detected = False
        try:
            case_service.transition_status(
                case_id,
                project_id=project_id,
                new_status=HandoverCaseStatus.ASSEMBLING.value,
                user_id=reviewer_id,
                expected_version=99,  # Mismatched version
            )
        except ConflictError:
            conflict_detected = True

        log_result(
            "TEST-B",
            "Optimistic Concurrency Control (Version Mismatch Conflict)",
            conflict_detected,
            "Rejected status transition when expected_version does not match current case version.",
        )

    # =========================================================================
    # PART 4: 8-Domain Deterministic Assembly & Eligibility Gating (TEST-C & TEST-D)
    # =========================================================================
    logger.info("=== 4. Deterministic Assembly & Eligibility Gating ===")
    with session_factory() as session:
        assembly_service = PackageAssemblyService(session)
        from app.schemas.handover import PackageAssemblyRequest

        assembly_req = PackageAssemblyRequest(
            assembly_notes="Initial automated compilation of verified project intelligence."
        )
        version = assembly_service.assemble_package_version(
            case_id=case_id,
            project_id=project_id,
            user_id=reviewer_id,
            request=assembly_req,
            has_project_manage=True,
        )
        version_id = version.id
        session.commit()

        # Check sections created
        sections = version.sections
        section_types = {s.section_type for s in sections}

        log_result(
            "TEST-C",
            "Deterministic 8-Domain Package Assembly",
            len(sections) == 8 and version.version_number == 1 and version.is_current,
            f"Compiled version {version.version_number} with {len(sections)} domain sections and hash {version.content_hash[:12]}...",
        )

        # Check content links created for eligible findings
        total_links = sum(len(s.content_links) for s in sections)
        log_result(
            "TEST-D",
            "Downstream Eligibility Gating & Content Links",
            total_links >= 3,
            f"Linked {total_links} verified findings directly into package sections with provenance.",
        )

    # =========================================================================
    # PART 5: 9-Category Readiness Assessment (TEST-E)
    # =========================================================================
    logger.info("=== 5. 9-Category Readiness Assessment ===")
    with session_factory() as session:
        readiness_engine = HandoverReadinessEngine(session)
        summary = readiness_engine.assess_version(
            version_id=version_id,
            project_id=project_id,
            user_id=reviewer_id,
            notes="Automated pre-review readiness audit",
        )
        session.commit()

        log_result(
            "TEST-E",
            "9-Category Readiness Scoring & Evaluation",
            len(summary.categories) == 9 and 0 <= summary.overall_score <= 100,
            f"Assessed 9 categories: Overall Score={summary.overall_score}/100, Level={summary.overall_level}, Blockers={summary.blocker_count}.",
        )

    # =========================================================================
    # PART 6: Dynamic Checklists (TEST-F)
    # =========================================================================
    logger.info("=== 6. Dynamic Checklists & Task Progression ===")
    with session_factory() as session:
        checklist_service = ChecklistService(session)
        checklists = checklist_service.generate_checklists_for_case(
            case_id=case_id,
            project_id=project_id,
            user_id=reviewer_id,
            version_id=version_id,
        )

        first_chk = checklists[0]
        first_item = first_chk.items[0]

        from app.schemas.handover import ChecklistItemUpdateRequest
        updated_item = checklist_service.update_item_status(
            item_id=first_item.id,
            project_id=project_id,
            user_id=reviewer_id,
            request=ChecklistItemUpdateRequest(status=ChecklistItemStatus.COMPLETED.value),
        )
        session.commit()

        log_result(
            "TEST-F",
            "Dynamic Checklists Generation & Item Completion",
            len(checklists) == 3 and updated_item.status == ChecklistItemStatus.COMPLETED.value,
            f"Generated {len(checklists)} checklists; updated item '{updated_item.item_text[:30]}...' to completed.",
        )

    # =========================================================================
    # PART 7: Responsibility Transfer Mapping (TEST-G)
    # =========================================================================
    logger.info("=== 7. Responsibility Transfer Mapping ===")
    with session_factory() as session:
        ownership_service = OwnershipTransferService(session)
        from app.schemas.handover import ResponsibilityTransferBulkRequest, ResponsibilityTransferRequest

        bulk_req = ResponsibilityTransferBulkRequest(
            transfers=[
                ResponsibilityTransferRequest(
                    responsibility_description="Maintain Authentication & RBAC Service",
                    knowledge_domain="responsibilities_ownership",
                    proposed_successor_id=successor_id,
                ),
                ResponsibilityTransferRequest(
                    responsibility_description="Manage Database Migrations and Alembic Scripts",
                    knowledge_domain="responsibilities_ownership",
                    proposed_successor_id=successor_id,
                ),
            ]
        )
        transfers = ownership_service.create_responsibility_transfers(
            case_id=case_id,
            project_id=project_id,
            user_id=reviewer_id,
            request=bulk_req,
        )
        session.commit()

        log_result(
            "TEST-G",
            "Responsibility Transfer Mapping",
            len(transfers) == 2 and transfers[0].transfer_status == TransferStatus.PENDING.value,
            f"Mapped {len(transfers)} responsibilities from departing member to successor.",
        )

    # =========================================================================
    # PART 8: Three-Phase Human Sign-Off & Separation of Duties (TEST-H & TEST-I)
    # =========================================================================
    logger.info("=== 8. Three-Phase Human Sign-Offs & Separation of Duties ===")
    with session_factory() as session:
        signoff_service = HandoverSignoffService(session)
        from app.schemas.handover import SignoffRequest
        from app.core.exceptions import ForbiddenError

        # Phase 1: Departing member signs
        phase1_req = SignoffRequest(
            version_id=version_id,
            signoff_type=SignoffType.DEPARTING_SIGNOFF.value,
            decision=SignoffDecision.APPROVED.value,
            comments="I certify that all known architectural decisions are documented.",
        )
        sig1 = signoff_service.submit_signoff(
            case_id=case_id,
            project_id=project_id,
            user_id=departing_id,
            request=phase1_req,
        )
        session.commit()

        log_result(
            "TEST-H.1",
            "Phase 1: Departing Member Sign-Off",
            sig1.signoff_type == SignoffType.DEPARTING_SIGNOFF.value and sig1.signature_hash is not None,
            f"Phase 1 signed by departing member with hash {sig1.signature_hash[:12]}...",
        )

        # TEST-I: Separation of Duties Violation Check
        # Departing member attempts to act as Reviewer to approve own package!
        sod_blocked = False
        try:
            illegal_phase2_req = SignoffRequest(
                version_id=version_id,
                signoff_type=SignoffType.REVIEWER_APPROVAL.value,
                decision=SignoffDecision.APPROVED.value,
                comments="Departing member attempting to approve own handover.",
            )
            signoff_service.submit_signoff(
                case_id=case_id,
                project_id=project_id,
                user_id=departing_id,  # VIOLATION: Departing member cannot approve
                request=illegal_phase2_req,
            )
        except ForbiddenError:
            sod_blocked = True

        log_result(
            "TEST-I",
            "Separation of Duties (Departing Member Cannot Approve Own Package)",
            sod_blocked,
            "Successfully blocked departing member from submitting Phase 2 Reviewer Approval.",
        )

        # Phase 2: Independent Reviewer Approves
        phase2_req = SignoffRequest(
            version_id=version_id,
            signoff_type=SignoffType.REVIEWER_APPROVAL.value,
            decision=SignoffDecision.APPROVED.value,
            comments="Approved by project reviewer after inspecting supporting PRs and evidence.",
        )
        sig2 = signoff_service.submit_signoff(
            case_id=case_id,
            project_id=project_id,
            user_id=reviewer_id,
            request=phase2_req,
            is_org_admin=True,  # Org owner can approve
        )
        session.commit()

        case_after_approval = session.get(HandoverCase, case_id)
        log_result(
            "TEST-H.2",
            "Phase 2: Independent Reviewer Approval & Status Transition to APPROVED",
            sig2.decision == SignoffDecision.APPROVED.value and case_after_approval.status == HandoverCaseStatus.APPROVED.value,
            f"Phase 2 approved; Case status transitioned to '{case_after_approval.status}'.",
        )

    # =========================================================================
    # PART 9: Package Delivery & Successor Acknowledgement (TEST-J & TEST-K)
    # =========================================================================
    logger.info("=== 9. Package Delivery & Successor Acknowledgement ===")
    with session_factory() as session:
        signoff_service = HandoverSignoffService(session)
        from app.schemas.handover import DeliveryRequest, AcknowledgementRequest

        # Delivery
        del_req = DeliveryRequest(
            version_id=version_id,
            deliver_to_user_ids=[successor_id],
            delivery_method=HandoverDeliveryMethod.INTERNAL_DOWNLOAD.value,
        )
        deliveries = signoff_service.deliver_package(
            case_id=case_id,
            project_id=project_id,
            user_id=reviewer_id,
            request=del_req,
        )
        session.commit()
        delivery_id = deliveries[0].id

        case_after_del = session.get(HandoverCase, case_id)
        log_result(
            "TEST-J",
            "Package Delivery & Case Transition to DELIVERED",
            len(deliveries) == 1 and case_after_del.status == HandoverCaseStatus.DELIVERED.value,
            f"Delivered version to successor {successor_id}; Case status is '{case_after_del.status}'.",
        )

        # Successor Acknowledgement
        ack_req = AcknowledgementRequest(
            acknowledgement_notes="I confirm receipt and full review of the backend architecture documentation."
        )
        ack = signoff_service.acknowledge_delivery(
            delivery_id=delivery_id,
            project_id=project_id,
            user_id=successor_id,
            request=ack_req,
        )
        session.commit()

        case_after_ack = session.get(HandoverCase, case_id)
        log_result(
            "TEST-K",
            "Successor Receipt Acknowledgement & Case Transition to ACKNOWLEDGED",
            ack.acknowledgement_hash is not None and case_after_ack.status == HandoverCaseStatus.ACKNOWLEDGED.value,
            f"Successor acknowledged delivery with cryptographic hash {ack.acknowledgement_hash[:12]}...; Case status is '{case_after_ack.status}'.",
        )

    # =========================================================================
    # PART 10: Explicit Ownership Transfer & Rollback (TEST-L & TEST-M)
    # =========================================================================
    logger.info("=== 10. Explicit Ownership Transfer & Rollback ===")
    with session_factory() as session:
        ownership_service = OwnershipTransferService(session)
        from app.schemas.handover import OwnershipTransferRequest, OwnershipTransferRollbackRequest

        # Execute Ownership Transfer
        transfer_req = OwnershipTransferRequest(
            version_id=version_id,
            transfer_type=OwnershipTransferType.PROJECT_OWNERSHIP.value,
            to_user_id=successor_id,
            transfer_reason="Lead engineer departed; transfer project leadership to successor.",
        )
        ot = ownership_service.execute_ownership_transfer(
            case_id=case_id,
            project_id=project_id,
            user_id=reviewer_id,
            request=transfer_req,
        )
        session.commit()

        case_after_transfer = session.get(HandoverCase, case_id)
        log_result(
            "TEST-L",
            "Explicit Ownership Transfer (Separate Operation) & Status Transition to TRANSFERRED",
            ot.to_user_id == successor_id and case_after_transfer.status == HandoverCaseStatus.TRANSFERRED.value,
            f"Transferred project ownership to {successor_id}; Case status is '{case_after_transfer.status}'.",
        )

        # Rollback Ownership Transfer
        rollback_req = OwnershipTransferRollbackRequest(
            rollback_reason="Successor transition delayed by 2 weeks due to project reschedule."
        )
        rolled_back_ot = ownership_service.rollback_ownership_transfer(
            transfer_id=ot.id,
            project_id=project_id,
            user_id=reviewer_id,
            request=rollback_req,
        )
        session.commit()

        log_result(
            "TEST-M",
            "Ownership Transfer Rollback with Audit Justification",
            rolled_back_ot.rolled_back and rolled_back_ot.rollback_reason is not None,
            f"Rollback succeeded with logged reason: '{rolled_back_ot.rollback_reason}'.",
        )

    # =========================================================================
    # PART 11: AI Narrative Drafting & Section Editing (TEST-N)
    # =========================================================================
    logger.info("=== 11. AI Narrative Drafting & Section Editing ===")
    with session_factory() as session:
        narrative_service = HandoverNarrativeService(session)
        from app.schemas.handover import NarrativeDraftRequest, SectionEditRequest

        draft_req = NarrativeDraftRequest(
            version_id=version_id,
            section_type=HandoverPackageSectionType.DECISIONS_RATIONALE.value,
            additional_context="Focus on microservice separation and async worker architecture.",
        )
        draft_result = narrative_service.draft_section_narrative(
            project_id=project_id,
            request=draft_req,
        )

        # Edit Section
        edit_req = SectionEditRequest(
            section_content=draft_result["draft_content"] + "\n\n*Reviewed and approved by Tech Lead.*",
            content_summary="Edited section content with technical lead endorsement.",
        )
        edited_section = narrative_service.edit_section_content(
            section_id=draft_result["section_id"],
            project_id=project_id,
            user_id=reviewer_id,
            request=edit_req,
        )
        session.commit()

        log_result(
            "TEST-N",
            "AI Narrative Drafting & Section Content Editing",
            len(draft_result["draft_content"]) > 0 and "Tech Lead" in edited_section.section_content,
            f"Drafted and edited section '{edited_section.section_title}' successfully.",
        )

    # =========================================================================
    # PART 12: Live FastAPI REST HTTP Endpoints
    # =========================================================================
    logger.info("=== 12. Live FastAPI REST API Endpoints Verification ===")
    with session_factory() as session:
        # Create auth token for live HTTP tests
        fam_id = uuid.uuid4()
        session.add(
            RefreshSession(
                id=uuid.uuid4(),
                user_id=reviewer_id,
                token_family_id=fam_id,
                token_hash=hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
        )
        session.commit()

        token, _ = create_access_token(
            user_id=reviewer_id,
            session_family_id=fam_id,
            settings=settings,
        )
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    app = create_app(settings)
    with TestClient(app, headers=headers) as client:
        # 1. GET /api/v1/projects/{project_id}/handover/cases
        r_cases = client.get(f"/api/v1/projects/{project_id}/handover/cases")
        log_result(
            "API-01",
            "GET /projects/{project_id}/handover/cases",
            r_cases.status_code == 200 and r_cases.json()["total"] >= 1,
            f"Status {r_cases.status_code}, total cases={r_cases.json().get('total')}",
        )

        # 2. GET /api/v1/projects/{project_id}/handover/cases/{case_id}
        r_detail = client.get(f"/api/v1/projects/{project_id}/handover/cases/{case_id}")
        log_result(
            "API-02",
            "GET /projects/{project_id}/handover/cases/{case_id}",
            r_detail.status_code == 200 and r_detail.json()["case"]["id"] == str(case_id),
            f"Status {r_detail.status_code}, returned case title='{r_detail.json().get('case', {}).get('title')}'",
        )

        # 3. GET /api/v1/projects/{project_id}/handover/cases/{case_id}/versions
        r_versions = client.get(f"/api/v1/projects/{project_id}/handover/cases/{case_id}/versions")
        log_result(
            "API-03",
            "GET /projects/{project_id}/handover/cases/{case_id}/versions",
            r_versions.status_code == 200 and len(r_versions.json()) >= 1,
            f"Status {r_versions.status_code}, versions count={len(r_versions.json())}",
        )

        # 4. GET /api/v1/projects/{project_id}/handover/cases/{case_id}/readiness/{version_id}
        r_readiness = client.get(f"/api/v1/projects/{project_id}/handover/cases/{case_id}/readiness/{version_id}")
        log_result(
            "API-04",
            "GET /projects/{project_id}/handover/cases/{case_id}/readiness/{version_id}",
            r_readiness.status_code == 200 and len(r_readiness.json()["categories"]) == 9,
            f"Status {r_readiness.status_code}, score={r_readiness.json().get('overall_score')}/100",
        )

        # 5. GET /api/v1/projects/{project_id}/handover/cases/{case_id}/checklists
        r_checklists = client.get(f"/api/v1/projects/{project_id}/handover/cases/{case_id}/checklists")
        log_result(
            "API-05",
            "GET /projects/{project_id}/handover/cases/{case_id}/checklists",
            r_checklists.status_code == 200 and len(r_checklists.json()) >= 1,
            f"Status {r_checklists.status_code}, checklists count={len(r_checklists.json())}",
        )

        # 6. GET /api/v1/projects/{project_id}/handover/cases/{case_id}/responsibilities
        r_resp = client.get(f"/api/v1/projects/{project_id}/handover/cases/{case_id}/responsibilities")
        log_result(
            "API-06",
            "GET /projects/{project_id}/handover/cases/{case_id}/responsibilities",
            r_resp.status_code == 200 and len(r_resp.json()) >= 1,
            f"Status {r_resp.status_code}, responsibilities count={len(r_resp.json())}",
        )

        # 7. GET /api/v1/projects/{project_id}/handover/cases/{case_id}/signoffs
        r_signoffs = client.get(f"/api/v1/projects/{project_id}/handover/cases/{case_id}/signoffs")
        log_result(
            "API-07",
            "GET /projects/{project_id}/handover/cases/{case_id}/signoffs",
            r_signoffs.status_code == 200 and len(r_signoffs.json()) >= 1,
            f"Status {r_signoffs.status_code}, signoffs count={len(r_signoffs.json())}",
        )

        # 8. GET /api/v1/projects/{project_id}/handover/eligibility/knowledge_item/{ki_id}
        r_elig = client.get(f"/api/v1/projects/{project_id}/handover/eligibility/knowledge_item/{ki_dec_id}")
        log_result(
            "API-08",
            "GET /projects/{project_id}/handover/eligibility/knowledge_item/{id}",
            r_elig.status_code == 200 and r_elig.json()["is_eligible"] is True,
            f"Status {r_elig.status_code}, is_eligible={r_elig.json().get('is_eligible')}",
        )

    # =========================================================================
    # SUMMARY REPORT
    # =========================================================================
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["passed"])
    failed_tests = total_tests - passed_tests

    logger.info("=" * 60)
    logger.info(f"HANDOVER WORKSPACE AUDIT RESULTS: {passed_tests}/{total_tests} PASSED ({failed_tests} FAILED)")
    logger.info("=" * 60)

    summary_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "pass_rate_percent": round(passed_tests / total_tests * 100, 1),
        "results": results,
    }

    results_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "handover_audit_results.json")
    )
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    return summary_data


if __name__ == "__main__":
    run_full_handover_audit()
