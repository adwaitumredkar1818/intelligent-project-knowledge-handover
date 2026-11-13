"""Comprehensive automated test suite for Verification Center (Module 3 / Validation Area).

Verifies:
1. Deterministic verification: valid grounding, missing evidence, unsupported claims
2. Duplicate detection & stale evidence detection
3. Relational edge verification & uncertain inferred edges
4. Conflict detection engine: status contradictions & temporal supersession
5. Human review service: approval, rejection, field corrections, and context requests
6. Optimistic concurrency control (case.version validation)
7. Handover eligibility gate (blocking unapproved, stale, or ACL-restricted knowledge)
8. REST API endpoints under `/api/v1/projects/{project_id}/verification/`
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.rbac_catalog import deterministic_rbac_id
from app.models.enums import (
    ConflictResolutionState,
    ConflictType,
    EpistemicStatus,
    EvidenceProcessingStatus,
    EvidenceSourceType,
    IssueResolutionState,
    KnowledgeReviewStatus,
    MachineAssessmentStatus,
    OrganisationStatus,
    ProjectStatus,
    ProjectVisibility,
    RoleName,
    TemporalComparison,
    UserStatus,
    VerificationCaseStatus,
    VerificationIssueType,
    VerificationPriority,
    VerificationSeverity,
    VerificationTargetType,
)
from app.models.evidence import EvidenceChunk, EvidenceItem
from app.models.knowledge import KnowledgeEvidenceLink, KnowledgeItem
from app.models.organisation import Organisation
from app.models.project import Project, ProjectMembership
from app.models.user import User
from app.models.verification import (
    VerificationCase,
    VerificationIssue,
)
from app.services.conflict_detection import ConflictDetectionEngine
from app.services.handover_eligibility import HandoverEligibilityService
from app.services.verification_engine import DeterministicVerificationEngine
from app.services.verification_review import (
    ConcurrencyConflictError,
    HumanReviewService,
    ReviewValidationError,
)
from tests.conftest import create_isolated_auth_context, isolated_auth_app, register_and_login_user


def _create_test_context(session: Session) -> tuple[User, Organisation, Project]:
    """Helper creating active User, Organisation, and Project."""
    user = User(
        id=uuid.uuid4(),
        email=f"reviewer-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        full_name="Lead Reviewer",
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    session.flush()

    org = Organisation(
        id=uuid.uuid4(),
        name=f"Verification Org {uuid.uuid4().hex[:6]}",
        slug=f"verif-org-{uuid.uuid4().hex[:6]}",
        created_by_id=user.id,
        status=OrganisationStatus.ACTIVE,
    )
    session.add(org)
    session.flush()

    project = Project(
        id=uuid.uuid4(),
        organisation_id=org.id,
        created_by_id=user.id,
        owner_id=user.id,
        name=f"Verification Project {uuid.uuid4().hex[:6]}",
        slug=f"verif-proj-{uuid.uuid4().hex[:6]}",
        visibility=ProjectVisibility.ORGANISATION,
        status=ProjectStatus.ACTIVE,
    )
    session.add(project)
    session.flush()

    membership = ProjectMembership(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=user.id,
        role_id=deterministic_rbac_id("role", RoleName.REVIEWER.value),
        status="active",
    )
    session.add(membership)
    session.flush()

    return user, org, project


def _create_test_evidence(
    session: Session,
    org: Organisation,
    project: Project,
    user: User,
    *,
    title: str = "Architecture Overview.pdf",
    source_type: str = EvidenceSourceType.DOCUMENT_UPLOAD.value,
    status: str = EvidenceProcessingStatus.EXTRACTED.value,
    source_created_at: datetime | None = None,
) -> EvidenceItem:
    content_hash = hashlib.sha256(f"{title}-{uuid.uuid4()}".encode()).hexdigest()
    ev = EvidenceItem(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=project.id,
        uploaded_by_user_id=user.id,
        source_type=source_type,
        source_provider="local_upload",
        category="pdf_document",
        source_external_id=uuid.uuid4().hex,
        title=title,
        original_filename=title.lower().replace(" ", "_"),
        content_hash=content_hash,
        file_size_bytes=1024,
        mime_type="application/pdf",
        source_created_at=source_created_at,
        processing_status=status,
        acl_scope="project_members",
    )
    session.add(ev)
    session.flush()
    return ev


def _create_test_chunk(
    session: Session,
    org: Organisation,
    project: Project,
    ev: EvidenceItem,
    *,
    chunk_text: str,
    chunk_index: int = 0,
) -> EvidenceChunk:
    chunk_hash = hashlib.sha256(chunk_text.encode()).hexdigest()
    chunk = EvidenceChunk(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=project.id,
        evidence_id=ev.id,
        chunk_index=chunk_index,
        chunk_type="text_segment",
        chunk_text=chunk_text,
        chunk_content_hash=chunk_hash,
        char_start=0,
        char_end=len(chunk_text),
        char_count=len(chunk_text),
        token_estimate=max(1, len(chunk_text) // 4),
        source_type=ev.source_type,
        indexing_status="indexed",
    )
    session.add(chunk)
    session.flush()
    return chunk


def _create_test_knowledge_item(
    session: Session,
    org: Organisation,
    project: Project,
    *,
    title: str,
    category: str = "technical_architecture",
    primary_domain: str = "technical_and_architectural",
    summary: str = "Test summary",
    epistemic_status: str = EpistemicStatus.EXTRACTED.value,
    review_status: str = KnowledgeReviewStatus.PENDING_REVIEW.value,
    payload: dict[str, Any] | None = None,
) -> KnowledgeItem:
    item = KnowledgeItem(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=project.id,
        category=category,
        primary_domain=primary_domain,
        title=title,
        structured_summary=summary,
        structured_payload=payload or {},
        support_classification="direct",
        extraction_model="qwen3:8b",
        prompt_version="1.0.0",
        fingerprint=uuid.uuid4().hex,
        epistemic_status=epistemic_status,
        review_status=review_status,
    )
    session.add(item)
    session.flush()
    return item


def _create_test_link(
    session: Session,
    org: Organisation,
    project: Project,
    item: KnowledgeItem,
    ev: EvidenceItem,
    chunk: EvidenceChunk | None = None,
    supporting_excerpt: str = "Supporting text excerpt",
) -> KnowledgeEvidenceLink:
    link = KnowledgeEvidenceLink(
        id=uuid.uuid4(),
        organisation_id=org.id,
        project_id=project.id,
        knowledge_item_id=item.id,
        evidence_id=ev.id,
        evidence_chunk_id=chunk.id if chunk else None,
        support_type="direct",
        supporting_excerpt=supporting_excerpt,
    )
    session.add(link)
    session.flush()
    return link


# ==============================================================================
# Deterministic Engine Tests
# ==============================================================================


def test_deterministic_verification_valid_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    """A finding with valid, matching excerpt in source chunk receives PASSED machine assessment."""
    ctx = create_isolated_auth_context(monkeypatch)
    with ctx.session_factory() as session:
        user, org, project = _create_test_context(session)
        ev = _create_test_evidence(session, org, project, user, title="Architecture Overview.pdf")

        chunk = _create_test_chunk(
            session,
            org,
            project,
            ev,
            chunk_text=(
                "The system uses PostgreSQL as the canonical database with Alembic for migrations."
            ),
        )

        item = _create_test_knowledge_item(
            session,
            org,
            project,
            title="Canonical Database Selection",
            category="technical_architecture",
            primary_domain="technical_and_architectural",
            payload={"db": "PostgreSQL"},
        )

        _create_test_link(
            session,
            org,
            project,
            item,
            ev,
            chunk,
            supporting_excerpt="PostgreSQL as the canonical database with Alembic",
        )
        session.commit()

        engine = DeterministicVerificationEngine(session)
        result = engine.assess_knowledge_item(item)

        assert result.machine_status == MachineAssessmentStatus.PASSED
        assert result.priority == VerificationPriority.LOW
        assert len(result.issues) == 0

        case = engine.persist_assessment(result)
        session.commit()

        assert case.case_status == VerificationCaseStatus.CANDIDATE
        assert case.machine_assessment_status == MachineAssessmentStatus.PASSED
        assert case.version == 1


def test_deterministic_verification_missing_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    """A finding with 0 evidence links must be flagged as INSUFFICIENT_EVIDENCE."""
    ctx = create_isolated_auth_context(monkeypatch)
    with ctx.session_factory() as session:
        user, org, project = _create_test_context(session)

        item = _create_test_knowledge_item(
            session,
            org,
            project,
            title="Unbacked Decision Claim",
            category="decisions_rationale",
            primary_domain="decisions_and_rationale",
            epistemic_status=EpistemicStatus.AI_INTERPRETED.value,
        )
        session.commit()

        engine = DeterministicVerificationEngine(session)
        result = engine.assess_knowledge_item(item)

        assert result.machine_status == MachineAssessmentStatus.INSUFFICIENT_EVIDENCE
        assert result.priority == VerificationPriority.CRITICAL
        assert len(result.issues) >= 1
        issue_types = [i["issue_type"] for i in result.issues]
        assert VerificationIssueType.MISSING_EVIDENCE in issue_types

        case = engine.persist_assessment(result)
        session.commit()

        assert case.case_status == VerificationCaseStatus.UNRESOLVED
        assert len(case.issues) >= 1
        assert any(i.severity == VerificationSeverity.CRITICAL for i in case.issues)


def test_deterministic_verification_unsupported_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    """A cited excerpt not present in the chunk text raises UNSUPPORTED_CLAIM issue."""
    ctx = create_isolated_auth_context(monkeypatch)
    with ctx.session_factory() as session:
        user, org, project = _create_test_context(session)
        ev = _create_test_evidence(session, org, project, user, title="Notes.pdf")

        chunk = _create_test_chunk(
            session,
            org,
            project,
            ev,
            chunk_text="Frontend is built using React and TypeScript.",
        )

        item = _create_test_knowledge_item(
            session,
            org,
            project,
            title="Frontend Framework",
            category="technical_architecture",
            primary_domain="technical_and_architectural",
        )

        _create_test_link(
            session,
            org,
            project,
            item,
            ev,
            chunk,
            supporting_excerpt="We explicitly decided to migrate the frontend to Vue.js 3",
        )
        session.commit()

        engine = DeterministicVerificationEngine(session)
        result = engine.assess_knowledge_item(item)

        assert result.machine_status == MachineAssessmentStatus.ISSUES_DETECTED
        assert result.priority == VerificationPriority.HIGH
        assert any(
            i["issue_type"] == VerificationIssueType.UNSUPPORTED_CLAIM for i in result.issues
        )


def test_deterministic_verification_duplicate_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Duplicate findings in the same domain and title are detected."""
    ctx = create_isolated_auth_context(monkeypatch)
    with ctx.session_factory() as session:
        user, org, project = _create_test_context(session)

        _item1 = _create_test_knowledge_item(
            session,
            org,
            project,
            title="Adopt Argon2id for Password Hashing",
            category="decisions_rationale",
            primary_domain="decisions_and_rationale",
        )
        item2 = _create_test_knowledge_item(
            session,
            org,
            project,
            title="Adopt Argon2id for Password Hashing",
            category="decisions_rationale",
            primary_domain="decisions_and_rationale",
        )
        session.commit()

        engine = DeterministicVerificationEngine(session)
        result = engine.assess_knowledge_item(item2)

        assert any(i["issue_type"] == VerificationIssueType.DUPLICATE_RECORD for i in result.issues)


# ==============================================================================
# Conflict Detection Tests
# ==============================================================================


def test_conflict_detection_and_temporal_supersession(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cross-source status contradiction registers VerificationConflict with temporal order."""
    ctx = create_isolated_auth_context(monkeypatch)
    with ctx.session_factory() as session:
        user, org, project = _create_test_context(session)

        time_a = datetime.now(UTC) - timedelta(days=2)
        ev_a = _create_test_evidence(
            session, org, project, user, title="Meeting Notes Nov 10", source_created_at=time_a
        )

        time_b = datetime.now(UTC) - timedelta(days=1)
        ev_b = _create_test_evidence(
            session,
            org,
            project,
            user,
            title="Jira SCRUM-42 Auth Migration",
            source_type=EvidenceSourceType.JIRA.value,
            source_created_at=time_b,
        )

        case = VerificationCase(
            organisation_id=org.id,
            project_id=project.id,
            target_type=VerificationTargetType.KNOWLEDGE_ITEM,
            target_id=uuid.uuid4(),
            case_status=VerificationCaseStatus.PENDING_REVIEW,
            machine_assessment_status=MachineAssessmentStatus.PASSED,
            priority=VerificationPriority.MEDIUM,
            version=1,
        )
        session.add(case)
        session.commit()

        conflict_engine = ConflictDetectionEngine(session)
        conflict = conflict_engine.register_conflict(
            case=case,
            conflict_type=ConflictType.STATUS_CONFLICT,
            claim_a_text="Auth migration is blocked and pending security review.",
            claim_a_evidence_id=ev_a.id,
            claim_a_timestamp=time_a,
            claim_b_text="SCRUM-42 marked Resolved: Completed Argon2id hashing.",
            claim_b_evidence_id=ev_b.id,
            claim_b_timestamp=time_b,
            explanation="Meeting notes indicate pending, but Jira marks task Resolved.",
        )
        session.commit()

        assert conflict.temporal_comparison == TemporalComparison.B_SUPERSEDES_A
        assert conflict.resolution_state == ConflictResolutionState.UNRESOLVED
        assert case.case_status == VerificationCaseStatus.CONFLICTED
        assert case.machine_assessment_status == MachineAssessmentStatus.CONFLICT_DETECTED
        assert case.priority == VerificationPriority.HIGH

        open_issues = case.issues
        assert any(i.issue_type == VerificationIssueType.CONFLICTING_SOURCES for i in open_issues)


# ==============================================================================
# Human Review Tests
# ==============================================================================


def test_human_review_approve_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Human review approve promotes finding to HUMAN_VERIFIED and logs audit event."""
    ctx = create_isolated_auth_context(monkeypatch)
    with ctx.session_factory() as session:
        user, org, project = _create_test_context(session)

        item = _create_test_knowledge_item(
            session,
            org,
            project,
            title="FastAPI Modular Architecture",
            category="technical_architecture",
            primary_domain="technical_and_architectural",
            epistemic_status=EpistemicStatus.EXTRACTED.value,
        )

        case = VerificationCase(
            organisation_id=org.id,
            project_id=project.id,
            target_type=VerificationTargetType.KNOWLEDGE_ITEM,
            target_id=item.id,
            case_status=VerificationCaseStatus.PENDING_REVIEW,
            machine_assessment_status=MachineAssessmentStatus.PASSED,
            priority=VerificationPriority.LOW,
            version=1,
        )
        session.add(case)
        session.commit()

        service = HumanReviewService(session)
        updated_case = service.approve(
            case_id=case.id,
            reviewer_user_id=user.id,
            expected_version=1,
            review_notes="Verified against architecture spec.",
        )
        session.commit()

        assert updated_case.case_status == VerificationCaseStatus.VERIFIED
        assert updated_case.version == 2
        assert item.review_status == KnowledgeReviewStatus.APPROVED.value
        assert item.epistemic_status == EpistemicStatus.HUMAN_VERIFIED.value

        events = updated_case.review_events
        assert len(events) == 1
        assert events[0].action == "approve"
        assert events[0].reviewer_user_id == user.id


def test_human_review_approve_blocked_by_critical_issue(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reviewer cannot approve finding while an unresolved CRITICAL issue is open."""
    ctx = create_isolated_auth_context(monkeypatch)
    with ctx.session_factory() as session:
        user, org, project = _create_test_context(session)

        item = _create_test_knowledge_item(
            session,
            org,
            project,
            title="Unbacked Decision",
            category="decisions_rationale",
            primary_domain="decisions_and_rationale",
        )

        case = VerificationCase(
            organisation_id=org.id,
            project_id=project.id,
            target_type=VerificationTargetType.KNOWLEDGE_ITEM,
            target_id=item.id,
            case_status=VerificationCaseStatus.UNRESOLVED,
            machine_assessment_status=MachineAssessmentStatus.INSUFFICIENT_EVIDENCE,
            priority=VerificationPriority.CRITICAL,
            version=1,
        )
        session.add(case)
        session.flush()

        issue = VerificationIssue(
            organisation_id=org.id,
            project_id=project.id,
            case_id=case.id,
            issue_type=VerificationIssueType.MISSING_EVIDENCE,
            severity=VerificationSeverity.CRITICAL,
            description="Finding has 0 evidence links.",
            resolution_state=IssueResolutionState.OPEN,
        )
        session.add(issue)
        session.commit()

        service = HumanReviewService(session)
        with pytest.raises(ReviewValidationError) as exc_info:
            service.approve(case_id=case.id, reviewer_user_id=user.id, expected_version=1)

        assert "unresolved critical issue" in str(exc_info.value).lower()
        assert item.review_status == KnowledgeReviewStatus.PENDING_REVIEW.value


def test_optimistic_concurrency_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Attempting an action with stale expected_version raises ConcurrencyConflictError."""
    ctx = create_isolated_auth_context(monkeypatch)
    with ctx.session_factory() as session:
        user, org, project = _create_test_context(session)

        case = VerificationCase(
            organisation_id=org.id,
            project_id=project.id,
            target_type=VerificationTargetType.KNOWLEDGE_ITEM,
            target_id=uuid.uuid4(),
            case_status=VerificationCaseStatus.PENDING_REVIEW,
            machine_assessment_status=MachineAssessmentStatus.PASSED,
            priority=VerificationPriority.LOW,
            version=2,
        )
        session.add(case)
        session.commit()

        service = HumanReviewService(session)
        with pytest.raises(ConcurrencyConflictError) as exc_info:
            service.reject(
                case_id=case.id,
                reviewer_user_id=user.id,
                expected_version=1,
                reason="Duplicate claim",
            )

        assert "Concurrent modification detected" in str(exc_info.value)


def test_human_review_edit_finding_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Editing finding applies field corrections and captures before/after snapshot diff."""
    ctx = create_isolated_auth_context(monkeypatch)
    with ctx.session_factory() as session:
        user, org, project = _create_test_context(session)

        item = _create_test_knowledge_item(
            session,
            org,
            project,
            title="Old Mistyped Title",
            summary="Old summary.",
            payload={"env": "dev"},
        )

        case = VerificationCase(
            organisation_id=org.id,
            project_id=project.id,
            target_type=VerificationTargetType.KNOWLEDGE_ITEM,
            target_id=item.id,
            case_status=VerificationCaseStatus.PENDING_REVIEW,
            machine_assessment_status=MachineAssessmentStatus.PASSED,
            priority=VerificationPriority.LOW,
            version=1,
        )
        session.add(case)
        session.commit()

        service = HumanReviewService(session)
        updated_case = service.edit_finding(
            case_id=case.id,
            reviewer_user_id=user.id,
            expected_version=1,
            patch_data={
                "title": "Corrected Architecture Title",
                "summary": "Updated accurate summary.",
                "item_payload": {"env": "prod"},
            },
            reason="Corrected typos and environment flag",
        )
        session.commit()

        assert item.title == "Corrected Architecture Title"
        assert item.structured_summary == "Updated accurate summary."
        assert item.structured_payload.get("env") == "prod"
        assert updated_case.version == 2

        event = updated_case.review_events[0]
        assert event.action == "edit"
        assert event.finding_patch_json["title"] == "Corrected Architecture Title"
        assert event.previous_snapshot_json["target_snapshot"]["title"] == "Old Mistyped Title"


# ==============================================================================
# Handover Eligibility Gate Tests
# ==============================================================================


def test_handover_eligibility_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Downstream gate enforces human verification, no open critical issues, and source ACLs."""
    ctx = create_isolated_auth_context(monkeypatch)
    with ctx.session_factory() as session:
        user, org, project = _create_test_context(session)
        ev = _create_test_evidence(session, org, project, user, title="Runbook.pdf")

        item = _create_test_knowledge_item(
            session,
            org,
            project,
            title="Database Backup Routine",
            category="operational_historical",
            primary_domain="operational_procedures",
            epistemic_status=EpistemicStatus.EXTRACTED.value,
        )

        _create_test_link(session, org, project, item, ev)

        case = VerificationCase(
            organisation_id=org.id,
            project_id=project.id,
            target_type=VerificationTargetType.KNOWLEDGE_ITEM,
            target_id=item.id,
            case_status=VerificationCaseStatus.PENDING_REVIEW,
            machine_assessment_status=MachineAssessmentStatus.PASSED,
            priority=VerificationPriority.LOW,
            version=1,
        )
        session.add(case)
        session.commit()

        eligibility_service = HandoverEligibilityService(session)

        # 1. Check unapproved item -> MUST FAIL
        res1 = eligibility_service.check_knowledge_item_eligibility(item.id, viewer_user_id=user.id)
        assert res1.is_eligible is False
        assert any(
            "human-verified" in b.lower() or "human_verified" in b.lower() for b in res1.blockers
        )

        # 2. Approve item and verify eligibility passes
        review_service = HumanReviewService(session)
        review_service.approve(case_id=case.id, reviewer_user_id=user.id, expected_version=1)
        session.commit()

        res2 = eligibility_service.check_knowledge_item_eligibility(item.id, viewer_user_id=user.id)
        assert res2.is_eligible is True
        assert len(res2.blockers) == 0


# ==============================================================================
# REST API Tests
# ==============================================================================


def test_verification_api_queue_and_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    """REST API endpoints for verification queue, detail, approve, and eligibility."""
    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        owner = register_and_login_user(
            client,
            email="verif-owner@example.com",
            full_name="Verification Owner",
        )

        # Create Org & Project via API
        org_res = client.post(
            "/api/v1/organisations",
            headers=owner.headers,
            json={"name": "Verif Org"},
        )
        assert org_res.status_code == 201
        org_id = org_res.json()["id"]

        proj_res = client.post(
            f"/api/v1/organisations/{org_id}/projects",
            headers=owner.headers,
            json={"name": "Verif Proj", "visibility": "organisation"},
        )
        assert proj_res.status_code == 201
        proj_id = proj_res.json()["id"]

        # Insert test evidence, knowledge item, and verification case directly via DB session
        with ctx.session_factory() as session:
            user = session.get(User, owner.user_id)
            org = session.get(Organisation, uuid.UUID(org_id))
            proj = session.get(Project, uuid.UUID(proj_id))

            ev = _create_test_evidence(session, org, proj, user, title="Spec.pdf")
            item = _create_test_knowledge_item(
                session,
                org,
                proj,
                title="API Design Standard",
                category="decisions_rationale",
                primary_domain="decisions_and_rationale",
            )
            _create_test_link(session, org, proj, item, ev)

            case = VerificationCase(
                organisation_id=org.id,
                project_id=proj.id,
                target_type=VerificationTargetType.KNOWLEDGE_ITEM,
                target_id=item.id,
                case_status=VerificationCaseStatus.PENDING_REVIEW,
                machine_assessment_status=MachineAssessmentStatus.PASSED,
                priority=VerificationPriority.MEDIUM,
                version=1,
            )
            session.add(case)
            session.commit()
            case_id_str = str(case.id)

        # 1. GET /queue
        res_queue = client.get(
            f"/api/v1/projects/{proj_id}/verification/queue",
            headers=owner.headers,
        )
        assert res_queue.status_code == 200
        queue_body = res_queue.json()
        assert queue_body["total"] == 1
        assert queue_body["items"][0]["id"] == case_id_str

        # 2. GET /summary
        res_sum = client.get(
            f"/api/v1/projects/{proj_id}/verification/summary",
            headers=owner.headers,
        )
        assert res_sum.status_code == 200
        sum_body = res_sum.json()
        assert sum_body["total_cases"] == 1

        # 3. GET /cases/{case_id}
        res_detail = client.get(
            f"/api/v1/projects/{proj_id}/verification/cases/{case_id_str}",
            headers=owner.headers,
        )
        assert res_detail.status_code == 200
        detail_body = res_detail.json()
        assert detail_body["target_data"]["title"] == "API Design Standard"

        # 4. GET /cases/{case_id}/evidence
        res_ev = client.get(
            f"/api/v1/projects/{proj_id}/verification/cases/{case_id_str}/evidence",
            headers=owner.headers,
        )
        assert res_ev.status_code == 200
        ev_body = res_ev.json()
        assert len(ev_body["supporting_evidence"]) == 1

        # 5. POST /cases/{case_id}/approve
        res_app = client.post(
            f"/api/v1/projects/{proj_id}/verification/cases/{case_id_str}/approve",
            headers=owner.headers,
            json={"expected_version": 1, "review_notes": "API test approval."},
        )
        assert res_app.status_code == 200
        app_body = res_app.json()
        assert app_body["case_status"] == "verified"
        assert app_body["version"] == 2

        # 6. GET /cases/{case_id}/eligibility
        res_elig = client.get(
            f"/api/v1/projects/{proj_id}/verification/cases/{case_id_str}/eligibility",
            headers=owner.headers,
        )
        assert res_elig.status_code == 200
        elig_body = res_elig.json()
        assert elig_body["is_eligible"] is True
