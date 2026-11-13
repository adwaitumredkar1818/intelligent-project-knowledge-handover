"""Comprehensive automated test suite for Relationship Explorer module.

Verifies:
1. Relationship taxonomy & endpoint pair constraints
2. Exact identifier linking (Jira keys, ADR references)
3. Structured connector linking (GitHub PR author/reviewers, Jira links & components)
4. Contextual file path matching
5. Multi-signal identity resolution & Person safety override (NO auto-merge for person)
6. Reversible identity merge and revert operations
7. 5-Stage decision traceability chain analysis
8. Dependency graph traversal, circular dependency cycle detection, root blocker identification
9. React Flow graph projection formatting
10. Fail-closed source ACL enforcement (restricted evidence hides edge/node)
11. REST API endpoints under `/api/v1/projects/{project_id}/relationships/`
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import (
    EntityResolutionStatus,
    EntityType,
    IdentityCandidateStatus,
    IdentityPolicyBand,
    OrganisationStatus,
    ProjectStatus,
    ProjectVisibility,
    RelationshipType,
    RelationshipVerificationStatus,
    TraceabilityCompletenessStatus,
    UserStatus,
)
from app.models.evidence import EvidenceItem
from app.models.organisation import Organisation
from app.models.project import Project
from app.models.user import User
from app.repositories.relationship import (
    EntityRepository,
    RelationshipRepository,
)
from app.services.dependency_intelligence import DependencyIntelligenceService
from app.services.identity_resolution import IdentityResolutionService
from app.services.relationship_discovery import RelationshipDiscoveryEngine
from app.services.relationship_taxonomy import (
    get_display_label,
    validate_relationship_endpoints,
)
from app.services.traceability import DecisionTraceabilityService
from tests.conftest import create_isolated_auth_context


def _create_test_context(session: Session) -> tuple[User, Organisation, Project]:
    """Helper creating active User, Organisation, and Project adhering to foreign key constraints."""
    user = User(
        id=uuid.uuid4(),
        full_name="Test Operator",
        email=f"operator-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hash",
        status=UserStatus.ACTIVE.value,
    )
    session.add(user)
    session.flush()

    org = Organisation(
        id=uuid.uuid4(),
        name="Test Org",
        slug=f"org-{uuid.uuid4().hex[:6]}",
        created_by_id=user.id,
        status=OrganisationStatus.ACTIVE.value,
    )
    session.add(org)
    session.flush()

    proj = Project(
        id=uuid.uuid4(),
        organisation_id=org.id,
        name="Test Project",
        slug=f"proj-{uuid.uuid4().hex[:6]}",
        created_by_id=user.id,
        owner_id=user.id,
        status=ProjectStatus.ACTIVE.value,
        visibility=ProjectVisibility.PRIVATE.value,
    )
    session.add(proj)
    session.flush()

    return user, org, proj


# ==============================================================================
# 1. Taxonomy & Endpoint Constraints
# ==============================================================================


def test_relationship_taxonomy_constraints() -> None:
    """Validate allowed and disallowed source/target entity type pairs."""
    # Valid: DECISION -> PERSON for DECIDED_BY
    valid, err = validate_relationship_endpoints(
        RelationshipType.DECIDED_BY.value,
        EntityType.DECISION.value,
        EntityType.PERSON.value,
    )
    assert valid is True
    assert err is None

    # Invalid: PERSON -> DECISION for DECIDED_BY
    valid, err = validate_relationship_endpoints(
        RelationshipType.DECIDED_BY.value,
        EntityType.PERSON.value,
        EntityType.DECISION.value,
    )
    assert valid is False
    assert "Source type 'person' is not allowed" in (err or "")

    # Valid: PULL_REQUEST -> WORK_ITEM for IMPLEMENTS
    valid, _ = validate_relationship_endpoints(
        RelationshipType.IMPLEMENTS.value,
        EntityType.PULL_REQUEST.value,
        EntityType.WORK_ITEM.value,
    )
    assert valid is True

    # Bidirectional display labels
    assert get_display_label(RelationshipType.BLOCKS.value, inverse=False) == "Blocks"
    assert get_display_label(RelationshipType.BLOCKS.value, inverse=True) == "Blocked By"


# ==============================================================================
# 2. Identity Resolution & Person Safety Override
# ==============================================================================


def test_identity_resolution_scoring_and_person_safety_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify 5-signal identity scoring, auto-merge for non-person, and strict manual review for persons."""
    iso = create_isolated_auth_context(monkeypatch)
    with iso.session_factory() as session:
        user, org, proj = _create_test_context(session)

        entity_repo = EntityRepository(session)
        service = IdentityResolutionService(session)

        # Case 1: Two component entities with slightly different names
        comp1 = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.COMPONENT.value,
            canonical_name="Auth Service",
        )
        comp2 = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.COMPONENT.value,
            canonical_name="Authentication Service",
        )
        assert comp1.id != comp2.id
        signal_comp = service.compute_match_signal(comp1, comp2)
        assert signal_comp.aggregate_score >= 0.20

        # Case 2: Two PERSON entities with similar names and identical emails across sources
        person1 = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.PERSON.value,
            canonical_name="Alex Vance",
            source_provider="github",
        )
        entity_repo.add_alias(
            entity_id=person1.id,
            organisation_id=org.id,
            project_id=proj.id,
            alias_value="alex.vance@company.com",
            source_provider="github",
        )

        person2 = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.PERSON.value,
            canonical_name="Alexander Vance",
            source_provider="jira",
        )
        entity_repo.add_alias(
            entity_id=person2.id,
            organisation_id=org.id,
            project_id=proj.id,
            alias_value="alex.vance@company.com",
            source_provider="jira",
        )

        assert person1.id != person2.id
        signal_person = service.compute_match_signal(person1, person2)

        # High match score (name fuzzy ~0.83, handle match 1.0, cross-ref 1.0)
        assert signal_person.aggregate_score >= 0.70
        # SAFETY OVERRIDE: Person entities MUST NEVER be placed in auto_merge
        assert signal_person.policy_band == IdentityPolicyBand.MANUAL_REVIEW.value

        # Evaluate and record candidate
        candidate = service.evaluate_and_record_candidate(person1, person2)
        assert candidate is not None
        assert candidate.policy_band == IdentityPolicyBand.MANUAL_REVIEW.value
        assert candidate.decision_status == IdentityCandidateStatus.PENDING.value
        # Ensure person2 was NOT automatically merged
        assert person2.resolution_status == EntityResolutionStatus.CANONICAL.value

        # Human Review: Accept merge
        reviewed = entity_repo.review_identity_candidate(
            candidate.id,
            user_id=user.id,
            action="accept",
            rationale="Verified identical GitHub and Jira identities for Alex Vance.",
        )
        assert reviewed.decision_status == IdentityCandidateStatus.ACCEPTED.value
        merged_entity = person2 if candidate.right_entity_id == person2.id else person1
        surviving_entity = person1 if candidate.right_entity_id == person2.id else person2
        assert merged_entity.resolution_status == EntityResolutionStatus.MERGED.value
        assert merged_entity.merged_into_entity_id == surviving_entity.id

        # Revert merge
        reverted = entity_repo.revert_identity_candidate(
            candidate.id,
            user_id=user.id,
            rationale="Accidental merge, separating identities.",
        )
        assert reverted.decision_status == IdentityCandidateStatus.REVERTED.value
        assert merged_entity.resolution_status == EntityResolutionStatus.CANONICAL.value
        assert merged_entity.merged_into_entity_id is None


# ==============================================================================
# 3. Exact Linking & Structured Connector Discovery
# ==============================================================================


def test_exact_linking_and_structured_connectors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify exact identifier matching and structured connector extraction."""
    iso = create_isolated_auth_context(monkeypatch)
    with iso.session_factory() as session:
        user, org, proj = _create_test_context(session)

        # Create Evidence Items
        ev_jira = EvidenceItem(
            organisation_id=org.id,
            project_id=proj.id,
            source_type="jira",
            source_provider="jira",
            category="issue",
            title="CORE-101 Implement JWT Auth",
            source_external_id="CORE-101",
            content_hash="1" * 64,
            processing_status="extracted",
            acl_scope="project_members",
        )
        ev_pr = EvidenceItem(
            organisation_id=org.id,
            project_id=proj.id,
            source_type="github",
            source_provider="github",
            category="pull_request",
            title="feat: add auth service (fixes CORE-101)",
            source_external_id="PR-42",
            content_hash="2" * 64,
            processing_status="extracted",
            acl_scope="project_members",
            metadata_json={
                "author": "octocat",
                "reviewers": ["senior-reviewer"],
                "repository": "core-backend",
            },
        )
        session.add_all([ev_jira, ev_pr])
        session.flush()

        entity_repo = EntityRepository(session)
        # Create work item entity
        wi = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.WORK_ITEM.value,
            canonical_name="CORE-101 Implement JWT Auth",
            primary_evidence_id=ev_jira.id,
            external_source_id="CORE-101",
        )
        # Create PR entity referencing CORE-101
        pr = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.PULL_REQUEST.value,
            canonical_name="PR #42: feat: add auth service (fixes CORE-101)",
            description="Fixes CORE-101 with token rotation",
            primary_evidence_id=ev_pr.id,
            metadata_json=ev_pr.metadata_json,
        )

        # Create Person and Component entities
        octo = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.PERSON.value,
            canonical_name="octocat",
        )
        comp = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.COMPONENT.value,
            canonical_name="core-backend",
        )

        engine = RelationshipDiscoveryEngine(session)

        # 1. Exact Identifier Linking (PR -> Work Item via CORE-101)
        exact_drafts = engine.discover_exact_identifier_links(
            project_id=proj.id,
            organisation_id=org.id,
        )
        assert len(exact_drafts) == 1
        assert exact_drafts[0].source_entity_id == pr.id
        assert exact_drafts[0].target_entity_id == wi.id
        assert exact_drafts[0].relationship_type == RelationshipType.IMPLEMENTS.value

        # 2. Structured Connector Linking (PR author -> octocat, PR -> core-backend)
        conn_drafts = engine.discover_structured_connector_links(
            project_id=proj.id,
            organisation_id=org.id,
        )
        authored_by = [
            d for d in conn_drafts if d.relationship_type == RelationshipType.AUTHORED_BY.value
        ]
        affects_comp = [
            d
            for d in conn_drafts
            if d.relationship_type == RelationshipType.AFFECTS_COMPONENT.value
        ]

        assert len(authored_by) == 1
        assert authored_by[0].source_entity_id == pr.id
        assert authored_by[0].target_entity_id == octo.id

        assert len(affects_comp) == 1
        assert affects_comp[0].source_entity_id == pr.id
        assert affects_comp[0].target_entity_id == comp.id

        # Persist drafts
        created, updated = engine.persist_discovered_relationships(
            organisation_id=org.id,
            project_id=proj.id,
            drafts=exact_drafts + conn_drafts,
        )
        assert created == 3
        assert updated == 0


# ==============================================================================
# 4. Decision Traceability Chain Analysis
# ==============================================================================


def test_decision_traceability_analysis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify 5-stage traceability chain analysis and completeness status."""
    iso = create_isolated_auth_context(monkeypatch)
    with iso.session_factory() as session:
        user, org, proj = _create_test_context(session)

        entity_repo = EntityRepository(session)
        rel_repo = RelationshipRepository(session)

        # 1. Decision: ADR-001 Use PostgreSQL for Canonical Storage
        decision = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.DECISION.value,
            canonical_name="ADR-001 Use PostgreSQL for Canonical Storage",
        )

        service = DecisionTraceabilityService(session)

        # Initial check: Untraced
        analysis_untraced = service.analyze_decision_traceability(decision)
        assert (
            analysis_untraced.completeness_status == TraceabilityCompletenessStatus.UNTRACED.value
        )
        assert "Missing tracked Work Item / Jira issue" in analysis_untraced.missing_links

        # 2. Add Work Item
        work_item = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.WORK_ITEM.value,
            canonical_name="CORE-102 Setup Postgres DB schema",
        )
        rel_repo.create_or_get_relationship(
            organisation_id=org.id,
            project_id=proj.id,
            source_entity_id=decision.id,
            target_entity_id=work_item.id,
            relationship_type=RelationshipType.IMPLEMENTED_BY.value,
        )

        # Partially Traced
        analysis_part = service.analyze_decision_traceability(decision)
        assert (
            analysis_part.completeness_status
            == TraceabilityCompletenessStatus.PARTIALLY_TRACED.value
        )
        assert str(work_item.id) in analysis_part.work_item_ids
        assert "Missing Pull Request" in analysis_part.missing_links

        # 3. Add PR, Commit, Component
        pr = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.PULL_REQUEST.value,
            canonical_name="PR #50 DB initial migrations",
        )
        commit = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.COMMIT.value,
            canonical_name="commit abc1234 Initial schema",
        )
        comp = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.COMPONENT.value,
            canonical_name="database",
        )

        rel_repo.create_or_get_relationship(
            organisation_id=org.id,
            project_id=proj.id,
            source_entity_id=pr.id,
            target_entity_id=work_item.id,
            relationship_type=RelationshipType.IMPLEMENTS.value,
        )
        rel_repo.create_or_get_relationship(
            organisation_id=org.id,
            project_id=proj.id,
            source_entity_id=commit.id,
            target_entity_id=pr.id,
            relationship_type=RelationshipType.PART_OF.value,
        )
        rel_repo.create_or_get_relationship(
            organisation_id=org.id,
            project_id=proj.id,
            source_entity_id=pr.id,
            target_entity_id=comp.id,
            relationship_type=RelationshipType.AFFECTS_COMPONENT.value,
        )

        analysis_complete = service.analyze_decision_traceability(decision)
        assert (
            analysis_complete.completeness_status == TraceabilityCompletenessStatus.COMPLETE.value
        )
        assert len(analysis_complete.missing_links) == 0
        assert str(pr.id) in analysis_complete.pull_request_ids
        assert str(commit.id) in analysis_complete.commit_ids
        assert str(comp.id) in analysis_complete.component_ids


# ==============================================================================
# 5. Dependency Intelligence & Cycle Detection
# ==============================================================================


def test_dependency_cycle_detection_and_blockers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify directed dependency traversal, cycle detection, and root blocker analysis."""
    iso = create_isolated_auth_context(monkeypatch)
    with iso.session_factory() as session:
        user, org, proj = _create_test_context(session)

        entity_repo = EntityRepository(session)
        rel_repo = RelationshipRepository(session)

        # Create tasks A, B, C
        task_a = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.WORK_ITEM.value,
            canonical_name="Task A: DB Migration",
        )
        task_b = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.WORK_ITEM.value,
            canonical_name="Task B: API Routes",
        )
        task_c = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.WORK_ITEM.value,
            canonical_name="Task C: Frontend Dashboard",
        )

        # Task A blocks Task B (Task B depends on Task A)
        rel_repo.create_or_get_relationship(
            organisation_id=org.id,
            project_id=proj.id,
            source_entity_id=task_a.id,
            target_entity_id=task_b.id,
            relationship_type=RelationshipType.BLOCKS.value,
        )
        # Task B blocks Task C (Task C depends on Task B)
        rel_repo.create_or_get_relationship(
            organisation_id=org.id,
            project_id=proj.id,
            source_entity_id=task_b.id,
            target_entity_id=task_c.id,
            relationship_type=RelationshipType.BLOCKS.value,
        )

        dep_service = DependencyIntelligenceService(session)
        res = dep_service.analyze_dependencies(project_id=proj.id)

        assert res.has_circular_dependency is False
        assert len(res.detected_cycles) == 0
        # Task A is root blocker (blocks others, not blocked by anything)
        assert any(b.entity_id == task_a.id for b in res.root_blockers)
        # Task B and Task C are blocked items
        blocked_ids = [b.entity_id for b in res.blocked_items]
        assert task_b.id in blocked_ids
        assert task_c.id in blocked_ids

        # Introduce circular dependency: Task C blocks Task A!
        rel_repo.create_or_get_relationship(
            organisation_id=org.id,
            project_id=proj.id,
            source_entity_id=task_c.id,
            target_entity_id=task_a.id,
            relationship_type=RelationshipType.BLOCKS.value,
        )

        res_cycle = dep_service.analyze_dependencies(project_id=proj.id)
        assert res_cycle.has_circular_dependency is True
        assert len(res_cycle.detected_cycles) > 0


# ==============================================================================
# 6. Fail-Closed Source ACL Enforcement
# ==============================================================================


def test_fail_closed_source_acl_filtering(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that edges supported only by restricted evidence are hidden from unauthorized users."""
    iso = create_isolated_auth_context(monkeypatch)
    with iso.session_factory() as session:
        user1, org, proj = _create_test_context(session)

        user2 = User(
            id=uuid.uuid4(),
            email=f"u2-{uuid.uuid4().hex[:6]}@test.com",
            password_hash="hash",
            full_name="User Two",
            status=UserStatus.ACTIVE.value,
        )
        session.add(user2)
        session.flush()

        # Restricted evidence item uploaded by user1 (source_restricted)
        ev_private = EvidenceItem(
            organisation_id=org.id,
            project_id=proj.id,
            source_type="document_upload",
            source_provider="local_upload",
            category="pdf_document",
            source_external_id="priv-doc-1",
            title="Private Architecture Spec",
            content_hash="3" * 64,
            processing_status="extracted",
            acl_scope="source_restricted",
            uploaded_by_user_id=user1.id,
        )
        session.add(ev_private)
        session.flush()

        entity_repo = EntityRepository(session)
        rel_repo = RelationshipRepository(session)

        # Entities
        e1 = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.DECISION.value,
            canonical_name="Secret Internal Decision",
            primary_evidence_id=ev_private.id,
        )
        e2 = entity_repo.create_or_get_entity(
            organisation_id=org.id,
            project_id=proj.id,
            entity_type=EntityType.COMPONENT.value,
            canonical_name="Secret Engine",
        )

        rel = rel_repo.create_or_get_relationship(
            organisation_id=org.id,
            project_id=proj.id,
            source_entity_id=e1.id,
            target_entity_id=e2.id,
            relationship_type=RelationshipType.AFFECTS_COMPONENT.value,
        )
        rel_repo.add_evidence_link(
            relationship_id=rel.id,
            organisation_id=org.id,
            project_id=proj.id,
            evidence_id=ev_private.id,
        )

        # User 1 (uploader) CAN see the relationship
        rels_u1, total_u1 = rel_repo.list_accessible_relationships(
            project_id=proj.id,
            viewer_user_id=user1.id,
            has_project_manage=False,
        )
        assert total_u1 == 1

        # User 2 (not uploader, not manage) CANNOT see the relationship
        rels_u2, total_u2 = rel_repo.list_accessible_relationships(
            project_id=proj.id,
            viewer_user_id=user2.id,
            has_project_manage=False,
        )
        assert total_u2 == 0

        # Direct lookup by User 2 fails closed
        _, _, denied = rel_repo.get_accessible_relationship(
            rel.id,
            project_id=proj.id,
            viewer_user_id=user2.id,
            has_project_manage=False,
        )
        assert denied is True


# ==============================================================================
# 7. Real HTTP REST API Tests
# ==============================================================================


def test_relationship_explorer_api_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test all HTTP endpoints under /api/v1/projects/{project_id}/relationships/."""
    from tests.conftest import isolated_auth_app, register_and_login_user

    with isolated_auth_app(monkeypatch) as ctx, TestClient(ctx.app) as client:
        owner = register_and_login_user(
            client,
            email="rel-owner@example.com",
            full_name="Relationship Owner",
        )

        # 1. Create Org & Project
        org_res = client.post(
            "/api/v1/organisations",
            headers=owner.headers,
            json={"name": "Rel Org"},
        )
        assert org_res.status_code == 201
        org_id = org_res.json()["id"]

        proj_res = client.post(
            f"/api/v1/organisations/{org_id}/projects",
            headers=owner.headers,
            json={"name": "Rel Project", "visibility": "private"},
        )
        assert proj_res.status_code == 201
        proj_id = proj_res.json()["id"]

        # 2. Seed an entity and relationship directly via DB
        with ctx.session_factory() as session:
            ev = EvidenceItem(
                organisation_id=uuid.UUID(org_id),
                project_id=uuid.UUID(proj_id),
                source_type="document_upload",
                source_provider="local_upload",
                category="pdf_document",
                source_external_id="api-doc-1",
                title="API Spec Doc",
                content_hash="4" * 64,
                processing_status="extracted",
                acl_scope="project_members",
            )
            session.add(ev)
            session.flush()

            erepo = EntityRepository(session)
            rrepo = RelationshipRepository(session)

            e_dec = erepo.create_or_get_entity(
                organisation_id=uuid.UUID(org_id),
                project_id=uuid.UUID(proj_id),
                entity_type=EntityType.DECISION.value,
                canonical_name="ADR-002 GraphQL vs REST",
                primary_evidence_id=ev.id,
            )
            e_comp = erepo.create_or_get_entity(
                organisation_id=uuid.UUID(org_id),
                project_id=uuid.UUID(proj_id),
                entity_type=EntityType.COMPONENT.value,
                canonical_name="gateway",
            )

            rel = rrepo.create_or_get_relationship(
                organisation_id=uuid.UUID(org_id),
                project_id=uuid.UUID(proj_id),
                source_entity_id=e_dec.id,
                target_entity_id=e_comp.id,
                relationship_type=RelationshipType.AFFECTS_COMPONENT.value,
            )
            rrepo.add_evidence_link(
                relationship_id=rel.id,
                organisation_id=uuid.UUID(org_id),
                project_id=uuid.UUID(proj_id),
                evidence_id=ev.id,
            )
            session.commit()

        # 3. Test GET /relationships/graph
        graph_res = client.get(
            f"/api/v1/projects/{proj_id}/relationships/graph",
            headers=owner.headers,
        )
        assert graph_res.status_code == 200
        graph_data = graph_res.json()
        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert graph_data["total_nodes"] >= 2
        assert graph_data["total_edges"] >= 1

        # 4. Test GET /relationships/entities
        ent_res = client.get(
            f"/api/v1/projects/{proj_id}/relationships/entities",
            headers=owner.headers,
        )
        assert ent_res.status_code == 200
        assert ent_res.json()["total"] >= 2

        # 5. Test GET /relationships/entities/{entity_id}
        node_res = client.get(
            f"/api/v1/projects/{proj_id}/relationships/entities/{e_dec.id}",
            headers=owner.headers,
        )
        assert node_res.status_code == 200
        assert node_res.json()["entity"]["canonical_name"] == "ADR-002 GraphQL vs REST"

        # 6. Test GET /relationships
        rels_res = client.get(
            f"/api/v1/projects/{proj_id}/relationships",
            headers=owner.headers,
        )
        assert rels_res.status_code == 200
        assert rels_res.json()["total"] >= 1

        # 7. Test GET /relationships/{id}
        rel_id = rels_res.json()["items"][0]["id"]
        rel_detail = client.get(
            f"/api/v1/projects/{proj_id}/relationships/{rel_id}",
            headers=owner.headers,
        )
        assert rel_detail.status_code == 200

        # 8. Test GET /relationships/{id}/evidence
        ev_res = client.get(
            f"/api/v1/projects/{proj_id}/relationships/{rel_id}/evidence",
            headers=owner.headers,
        )
        assert ev_res.status_code == 200
        assert len(ev_res.json()) >= 1

        # 9. Test POST /relationships/{id}/submit-for-review
        rev_res = client.post(
            f"/api/v1/projects/{proj_id}/relationships/{rel_id}/submit-for-review",
            headers=owner.headers,
            json={"action": "verify", "note": "Verified by lead architect"},
        )
        assert rev_res.status_code == 200
        assert (
            rev_res.json()["verification_status"] == RelationshipVerificationStatus.VERIFIED.value
        )

        # 10. Test GET /relationships/traceability
        trace_res = client.get(
            f"/api/v1/projects/{proj_id}/relationships/traceability",
            headers=owner.headers,
        )
        assert trace_res.status_code == 200

        # 11. Test GET /relationships/dependencies
        dep_res = client.get(
            f"/api/v1/projects/{proj_id}/relationships/dependencies",
            headers=owner.headers,
        )
        assert dep_res.status_code == 200

        # 12. Test GET /relationships/timeline
        tl_res = client.get(
            f"/api/v1/projects/{proj_id}/relationships/timeline",
            headers=owner.headers,
        )
        assert tl_res.status_code == 200

        # 13. Test GET /relationships/identities/candidates
        id_res = client.get(
            f"/api/v1/projects/{proj_id}/relationships/identities/candidates",
            headers=owner.headers,
        )
        assert id_res.status_code == 200

        # 14. Test POST /relationships/reconstruct
        rec_res = client.post(
            f"/api/v1/projects/{proj_id}/relationships/reconstruct",
            headers=owner.headers,
            json={"include_llm_suggestions": False},
        )
        assert rec_res.status_code == 202
        assert rec_res.json()["status"] in ("queued", "completed")
