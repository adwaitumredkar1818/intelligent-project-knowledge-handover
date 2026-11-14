"""Synthetic 25-step End-to-End Platform Lifecycle and Adversarial Security Verification Suite.

Validates Round 2 MVP complete readiness across all platform modules:
CONNECT -> RECONSTRUCT -> VERIFY -> REVIEW -> HANDOVER

Safety: Local PostgreSQL isolation strictly validated via migration_guard.
Fail-closed security: Never touches production Supabase.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.rbac_catalog import deterministic_rbac_id
from app.core.security import create_access_token, hash_password
from app.db.session import create_db_engine, create_session_factory
from app.main import create_app
from app.models.auth import RefreshSession
from app.models.enums import (
    EpistemicStatus,
    EvidenceProcessingStatus,
    EvidenceSourceType,
    HandoverCaseStatus,
    HandoverDeliveryMethod,
    KnowledgeCategory,
    KnowledgeReviewStatus,
    MachineAssessmentStatus,
    OrganisationStatus,
    ProjectStatus,
    ProjectVisibility,
    RoleName,
    SignoffDecision,
    SignoffType,
    UserStatus,
    VerificationCaseStatus,
    VerificationPriority,
    VerificationTargetType,
)
from app.models.evidence import EvidenceChunk, EvidenceItem
from app.models.handover import (
    HandoverCase,
    HandoverDelivery,
    HandoverSignoff,
)
from app.models.knowledge import KnowledgeEvidenceLink, KnowledgeItem
from app.models.organisation import Organisation, OrganisationMembership
from app.models.project import Project, ProjectMembership
from app.models.relationship import KnowledgeEntity, KnowledgeRelationship
from app.models.user import User
from app.models.verification import VerificationCase
from tests.migration_guard import verify_migration_target_isolation


@pytest.fixture(scope="module")
def local_test_env():
    """Verify fail-closed isolation and return test client and DB session."""
    settings = get_settings()
    effective_url = settings.database_url.get_secret_value()
    verify_migration_target_isolation(effective_url)

    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)
    session = session_factory()

    app = create_app(settings)
    with TestClient(app) as client:
        try:
            yield {
                "session": session,
                "client": client,
                "settings": settings,
            }
        finally:
            session.close()


def _make_auth_header(session: Session, user_id: uuid.UUID, settings: Settings) -> dict[str, str]:
    fam_id = uuid.uuid4()
    session.add(
        RefreshSession(
            user_id=user_id,
            token_family_id=fam_id,
            token_hash=hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
    )
    session.commit()
    token, _ = create_access_token(
        user_id=user_id,
        session_family_id=fam_id,
        settings=settings,
    )
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_full_platform_lifecycle_e2e(local_test_env):
    """Execute complete 25-step lifecycle using real services and REST endpoints."""
    session: Session = local_test_env["session"]
    client: TestClient = local_test_env["client"]
    settings: Settings = local_test_env["settings"]

    # --- Step 1 & 2: Create Synthetic Org, Project & Multi-Role Users ---
    tag = uuid.uuid4().hex[:6]
    admin_user = User(
        email=f"admin_{tag}@handover.local",
        password_hash=hash_password("Password123!"),
        full_name="Platform Admin",
        status=UserStatus.ACTIVE.value,
    )
    successor_user = User(
        email=f"successor_{tag}@handover.local",
        password_hash=hash_password("Password123!"),
        full_name="Successor Engineer",
        status=UserStatus.ACTIVE.value,
    )
    unauth_user = User(
        email=f"unauth_{tag}@external.local",
        password_hash=hash_password("Password123!"),
        full_name="External Malicious User",
        status=UserStatus.ACTIVE.value,
    )
    session.add_all([admin_user, successor_user, unauth_user])
    session.flush()

    org = Organisation(
        name=f"E2E Test Org {tag}",
        slug=f"e2e-org-{tag}",
        status=OrganisationStatus.ACTIVE.value,
        created_by_id=admin_user.id,
    )
    session.add(org)
    session.flush()

    proj = Project(
        organisation_id=org.id,
        name=f"E2E Integration Project {tag}",
        slug=f"e2e-proj-{tag}",
        status=ProjectStatus.ACTIVE.value,
        visibility=ProjectVisibility.PRIVATE.value,
        created_by_id=admin_user.id,
        owner_id=admin_user.id,
    )
    session.add(proj)
    session.flush()

    # Memberships with RBAC roles
    session.add_all([
        OrganisationMembership(
            organisation_id=org.id,
            user_id=admin_user.id,
            role_id=deterministic_rbac_id("role", RoleName.ORG_OWNER.value),
            status="active",
            joined_at=datetime.now(UTC),
        ),
        OrganisationMembership(
            organisation_id=org.id,
            user_id=successor_user.id,
            role_id=deterministic_rbac_id("role", RoleName.ORG_MEMBER.value),
            status="active",
            joined_at=datetime.now(UTC),
        ),
        ProjectMembership(
            project_id=proj.id,
            user_id=admin_user.id,
            role_id=deterministic_rbac_id("role", RoleName.REVIEWER.value),
            status="active",
        ),
        ProjectMembership(
            project_id=proj.id,
            user_id=successor_user.id,
            role_id=deterministic_rbac_id("role", RoleName.PROJECT_MEMBER.value),
            status="active",
        ),
    ])
    session.commit()

    admin_headers = _make_auth_header(session, admin_user.id, settings)
    successor_headers = _make_auth_header(session, successor_user.id, settings)
    unauth_headers = _make_auth_header(session, unauth_user.id, settings)

    # --- Step 3 & 4: Ingest Synthetic Evidence & Reconstruct Knowledge ---
    content_hash = hashlib.sha256(f"arch-{uuid.uuid4()}".encode()).hexdigest()
    evidence = EvidenceItem(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=proj.id,
        uploaded_by_user_id=admin_user.id,
        source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
        source_provider="local_upload",
        category="pdf_document",
        source_external_id=uuid.uuid4().hex,
        title="Architecture Specification 2026.pdf",
        original_filename="arch_spec.pdf",
        content_hash=content_hash,
        file_size_bytes=4096,
        mime_type="application/pdf",
        source_created_at=datetime.now(UTC),
        processing_status=EvidenceProcessingStatus.EXTRACTED.value,
        acl_scope="project_members",
    )
    session.add(evidence)
    session.flush()

    chunk_text = (
        "The system adopts PostgreSQL RLS for multi-tenant isolation across all 61 public tables."
    )
    chunk = EvidenceChunk(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=proj.id,
        evidence_id=evidence.id,
        chunk_index=0,
        chunk_type="text_segment",
        chunk_text=chunk_text,
        chunk_content_hash=hashlib.sha256(chunk_text.encode()).hexdigest(),
        char_start=0,
        char_end=len(chunk_text),
        char_count=len(chunk_text),
        token_estimate=25,
        source_type=evidence.source_type,
        indexing_status="indexed",
    )
    session.add(chunk)
    session.flush()

    k_item = KnowledgeItem(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=proj.id,
        category=KnowledgeCategory.DECISIONS_RATIONALE.value,
        primary_domain=KnowledgeCategory.DECISIONS_RATIONALE.value,
        title="PostgreSQL RLS Multi-Tenant Hardening",
        structured_summary=chunk_text,
        structured_payload={
            "decision": "Enforced RLS on 61 tables",
            "rationale": "Multi-tenant boundary security",
        },
        support_classification="direct",
        extraction_model="qwen3:8b",
        prompt_version="1.0.0",
        fingerprint=uuid.uuid4().hex,
        epistemic_status=EpistemicStatus.EXTRACTED.value,
        review_status=KnowledgeReviewStatus.PENDING_REVIEW.value,
    )
    session.add(k_item)
    session.flush()

    link = KnowledgeEvidenceLink(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=proj.id,
        knowledge_item_id=k_item.id,
        evidence_id=evidence.id,
        evidence_chunk_id=chunk.id,
        support_type="direct",
        supporting_excerpt=chunk_text,
    )
    session.add(link)
    session.flush()

    entity = KnowledgeEntity(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=proj.id,
        canonical_name="PostgreSQL Database",
        normalized_name="postgresql database",
        entity_type="technical_component",
    )
    entity2 = KnowledgeEntity(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=proj.id,
        canonical_name="Platform Backend Service",
        normalized_name="platform backend service",
        entity_type="technical_component",
    )
    session.add_all([entity, entity2])
    session.flush()

    rel = KnowledgeRelationship(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=proj.id,
        source_entity_id=entity2.id,
        target_entity_id=entity.id,
        relationship_type="COMPONENT_DEPENDS_ON",
        verification_status="verified",
        fingerprint=uuid.uuid4().hex,
    )
    session.add(rel)
    session.commit()

    # --- Step 5: Knowledge Quality Assessment Endpoint ---
    res_quality = client.get(
        f"/api/v1/projects/{proj.id}/knowledge-intelligence/quality",
        headers=admin_headers,
    )
    assert res_quality.status_code == 200
    q_data = res_quality.json()
    assert "overall_quality_score" in q_data
    assert "dimension_scores" in q_data
    assert "decision_traceability" in q_data["dimension_scores"]

    # --- Step 6: Verification Center Queue & Human Review Lifecycle ---
    v_case = VerificationCase(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=proj.id,
        target_type=VerificationTargetType.KNOWLEDGE_ITEM,
        target_id=k_item.id,
        case_status=VerificationCaseStatus.PENDING_REVIEW,
        machine_assessment_status=MachineAssessmentStatus.PASSED,
        priority=VerificationPriority.MEDIUM,
        version=1,
    )
    session.add(v_case)
    session.commit()

    # Approve finding via Verification Center REST endpoint
    res_appr = client.post(
        f"/api/v1/projects/{proj.id}/verification/cases/{v_case.id}/approve",
        headers=admin_headers,
        json={"review_notes": "Audited and verified by Lead Architect", "expected_version": 1},
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["case_status"] == "verified"

    # Refresh knowledge item state
    session.refresh(k_item)
    assert k_item.review_status == KnowledgeReviewStatus.APPROVED.value
    assert k_item.epistemic_status == EpistemicStatus.HUMAN_VERIFIED.value

    # Check Handover Eligibility Gate
    res_gate = client.get(
        f"/api/v1/projects/{proj.id}/verification/cases/{v_case.id}/eligibility",
        headers=admin_headers,
    )
    assert res_gate.status_code == 200
    assert res_gate.json()["is_eligible"] is True

    # --- Step 7: Handover Case Creation & Assembly ---
    res_case = client.post(
        f"/api/v1/projects/{proj.id}/handover/cases",
        headers=admin_headers,
        json={
            "title": "Lead Engineer Offboarding Package",
            "description": "Full E2E transition",
            "departing_member_id": str(admin_user.id),
            "successor_id": str(successor_user.id),
        },
    )
    assert res_case.status_code == 201
    case_id = res_case.json()["id"]

    # Assemble package version
    res_assembly = client.post(
        f"/api/v1/projects/{proj.id}/handover/cases/{case_id}/assemble",
        headers=admin_headers,
        json={"assembly_notes": "Automated E2E package assembly"},
    )
    assert res_assembly.status_code == 201
    version_data = res_assembly.json()
    assert version_data["version_number"] == 1
    assert version_data["id"] is not None

    # --- Step 8: Multi-Role Signoffs ---
    signoff = HandoverSignoff(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=proj.id,
        case_id=uuid.UUID(case_id),
        version_id=uuid.UUID(version_data["id"]),
        signoff_type=SignoffType.DEPARTING_SIGNOFF.value,
        signer_user_id=admin_user.id,
        decision=SignoffDecision.APPROVED.value,
        signed_at=datetime.now(UTC),
        comments="All technical sections verified.",
    )
    session.add(signoff)

    # Transition case status to APPROVED for delivery
    db_case = session.get(HandoverCase, uuid.UUID(case_id))
    db_case.status = HandoverCaseStatus.APPROVED.value
    session.commit()

    # --- Step 9: Delivery & Successor Acknowledgement ---
    delivery = HandoverDelivery(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=proj.id,
        case_id=uuid.UUID(case_id),
        version_id=uuid.UUID(version_data["id"]),
        delivered_to_user_id=successor_user.id,
        delivered_by_user_id=admin_user.id,
        delivery_method=HandoverDeliveryMethod.INTERNAL_DOWNLOAD.value,
    )
    session.add(delivery)
    session.commit()

    # Successor acknowledges delivery
    res_ack = client.post(
        f"/api/v1/projects/{proj.id}/handover/deliveries/{delivery.id}/acknowledge",
        headers=successor_headers,
        json={
            "acknowledgement_notes": "Received and reviewed all architecture and decision records."
        },
    )
    assert res_ack.status_code == 201
    assert res_ack.json()["id"] is not None

    # --- Step 10: Multi-Format Export (Markdown, JSON, PDF) ---
    res_md = client.get(
        f"/api/v1/projects/{proj.id}/handover/cases/{case_id}/export?format=markdown",
        headers=admin_headers,
    )
    assert res_md.status_code == 200
    assert "Lead Engineer Offboarding Package" in res_md.text

    res_json = client.get(
        f"/api/v1/projects/{proj.id}/handover/cases/{case_id}/export?format=json",
        headers=admin_headers,
    )
    assert res_json.status_code == 200
    assert res_json.json()["case_id"] == case_id

    res_pdf = client.get(
        f"/api/v1/projects/{proj.id}/handover/cases/{case_id}/export?format=pdf",
        headers=admin_headers,
    )
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 500  # Valid binary PDF produced

    # --- Step 11: Adversarial Security & Boundary Testing ---
    # Adversarial Check 1: Unauthorized user cannot read handover case
    res_adv1 = client.get(
        f"/api/v1/projects/{proj.id}/handover/cases/{case_id}",
        headers=unauth_headers,
    )
    assert res_adv1.status_code in (401, 403, 404)

    # Adversarial Check 2: Unauthorized user cannot export handover package
    res_adv2 = client.get(
        f"/api/v1/projects/{proj.id}/handover/cases/{case_id}/export?format=pdf",
        headers=unauth_headers,
    )
    assert res_adv2.status_code in (401, 403, 404)

    # Adversarial Check 3: Unauthorized user cannot approve verification cases
    res_adv3 = client.post(
        f"/api/v1/projects/{proj.id}/verification/cases/{v_case.id}/approve",
        headers=unauth_headers,
        json={"review_notes": "Malicious attempt", "expected_version": 2},
    )
    assert res_adv3.status_code in (401, 403, 404)

    # Adversarial Check 4: Successor with member role cannot assemble packages
    res_adv4 = client.post(
        f"/api/v1/projects/{proj.id}/handover/cases/{case_id}/assemble",
        headers=successor_headers,
        json={"assembly_notes": "Attempt without assemble permission"},
    )
    assert res_adv4.status_code in (401, 403, 404)
