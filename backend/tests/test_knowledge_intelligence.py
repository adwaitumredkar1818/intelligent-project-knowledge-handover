"""Comprehensive unit and integration tests for Module 3: Knowledge Intelligence."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models.enums import (
    EpistemicStatus,
    EvidenceSourceType,
    IntegrationProvider,
    KnowledgeCategory,
    KnowledgeReviewStatus,
    SourcePermissionVerificationStatus,
    SourceVisibilityPolicy,
    SupportClassification,
)
from app.models.evidence import EvidenceChunk, EvidenceItem
from app.models.integration import (
    SourceAccessPolicy,
    SourceConnection,
)
from app.models.knowledge import KnowledgeEvidenceLink, KnowledgeItem
from app.services.extraction_prompts import ChunkPromptInput
from app.services.knowledge_domains import (
    KnowledgeDomain,
    canonical_domain_to_legacy_category,
    list_all_domain_definitions,
    resolve_canonical_domain,
)
from app.services.knowledge_validator import KnowledgeCandidateValidator
from app.services.timeline import (
    _derive_event_type,
    _parse_flexible_timestamp,
)
from tests.conftest import (
    invite_and_accept_member,
    isolated_auth_app,
    register_and_login_user,
)


def test_canonical_domains_registry_and_mappings():
    """Verify all 8 canonical domains are registered, ordered, and bi-directionally mapped."""
    all_defs = list_all_domain_definitions()
    assert len(all_defs) == 8

    expected_domains = [
        KnowledgeDomain.PROJECT_OVERVIEW_CONTEXT,
        KnowledgeDomain.DECISIONS_RATIONALE,
        KnowledgeDomain.ARCHITECTURE_TECHNICAL,
        KnowledgeDomain.WORK_PROGRESS,
        KnowledgeDomain.RESPONSIBILITIES_OWNERSHIP,
        KnowledgeDomain.DEPENDENCIES_RELATIONSHIPS,
        KnowledgeDomain.RISKS_BLOCKERS_QUESTIONS,
        KnowledgeDomain.OPERATIONAL_HISTORICAL,
    ]

    for idx, expected in enumerate(expected_domains, start=1):
        defn = all_defs[idx - 1]
        assert defn.domain == expected
        assert defn.code == idx
        assert defn.display_name
        assert defn.description
        assert defn.prompt_template_id

    # Test resolution from various formats
    assert (
        resolve_canonical_domain("project_overview_context")
        == KnowledgeDomain.PROJECT_OVERVIEW_CONTEXT
    )
    assert (
        resolve_canonical_domain("PROJECT_OVERVIEW_CONTEXT")
        == KnowledgeDomain.PROJECT_OVERVIEW_CONTEXT
    )
    assert resolve_canonical_domain("decisions_rationale") == KnowledgeDomain.DECISIONS_RATIONALE
    assert resolve_canonical_domain("work_items") == KnowledgeDomain.WORK_PROGRESS
    assert (
        resolve_canonical_domain("technical_architecture") == KnowledgeDomain.ARCHITECTURE_TECHNICAL
    )
    assert (
        resolve_canonical_domain("bugs_blockers_risks") == KnowledgeDomain.RISKS_BLOCKERS_QUESTIONS
    )
    assert resolve_canonical_domain("dependencies") == KnowledgeDomain.DEPENDENCIES_RELATIONSHIPS
    assert (
        resolve_canonical_domain("operational_historical") == KnowledgeDomain.OPERATIONAL_HISTORICAL
    )

    # Test reverse mapping to storage category
    assert (
        canonical_domain_to_legacy_category(KnowledgeDomain.PROJECT_OVERVIEW_CONTEXT)
        == "project_overview_context"
    )
    assert canonical_domain_to_legacy_category(KnowledgeDomain.WORK_PROGRESS) == "work_items"
    assert (
        canonical_domain_to_legacy_category(KnowledgeDomain.OPERATIONAL_HISTORICAL)
        == "operational_historical"
    )


def test_candidate_validation_project_overview_and_operational():
    """Verify validation for Domain 1 (Overview) and Domain 8 (Operational) candidates."""
    chunk_id = uuid.uuid4()
    chunk_text = (
        "Project Handover Mission: Prevent critical knowledge from leaving with people. "
        "Core objectives: reconstruct fragmented project knowledge into structured records. "
        "Standard deployment runbook: Run 'alembic upgrade head' followed by starting uvicorn."
    )
    chunk_input = ChunkPromptInput(
        chunk_id=chunk_id,
        evidence_id=uuid.uuid4(),
        organisation_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        chunk_index=0,
        chunk_type="section",
        page_number=1,
        section_title="Introduction",
        char_start=0,
        char_end=len(chunk_text),
        chunk_text=chunk_text,
        chunk_content_hash="hash123",
        source_type="document_upload",
        source_provider="manual_upload",
        source_external_id="doc-1",
        source_url=None,
        source_author_identity="System Architect",
        title="Project Overview Document",
        source_created_at_iso=datetime.now(UTC).isoformat(),
        source_updated_at_iso=None,
        extracted_at_iso=None,
        evidence_content_hash="evhash123",
    )

    validator = KnowledgeCandidateValidator()

    # 1. Valid Overview Candidate
    overview_json = {
        "items": [
            {
                "title": "Project Handover Core Mission",
                "description": "Prevent critical knowledge from leaving with people.",
                "overview_category": "purpose_mission",
                "problem_statement": "Knowledge loss when key team members transition.",
                "objectives": ["Reconstruct fragmented project knowledge into structured records."],
                "is_interpretation": False,
                "is_uncertain": False,
                "confidence_level": "high",
                "evidence_refs": [
                    {
                        "chunk_id": str(chunk_id),
                        "supporting_excerpt": (
                            "Prevent critical knowledge from leaving with people."
                        ),
                        "support_type": "direct",
                    }
                ],
            }
        ]
    }

    rep1 = validator.validate_batch_response(
        category=KnowledgeCategory.PROJECT_OVERVIEW_CONTEXT,
        parsed_json=overview_json,
        supplied_chunks=[chunk_input],
        is_synthetic=False,
    )
    assert len(rep1.accepted_items) == 1
    item1 = rep1.accepted_items[0]
    assert item1.primary_domain == "PROJECT_OVERVIEW_CONTEXT"
    assert item1.title == "Project Handover Core Mission"
    assert item1.epistemic_status == EpistemicStatus.EXTRACTED.value
    assert item1.support_classification == SupportClassification.DIRECT.value

    # 2. Valid Operational Candidate
    operational_json = {
        "items": [
            {
                "title": "Database Migration and Startup Runbook",
                "description": "Standard deployment procedure for applying migrations.",
                "knowledge_type": "deployment_runbook",
                "target_environment": "production",
                "execution_steps": ["Run 'alembic upgrade head' followed by starting uvicorn."],
                "is_interpretation": False,
                "is_uncertain": False,
                "confidence_level": "high",
                "evidence_refs": [
                    {
                        "chunk_id": str(chunk_id),
                        "supporting_excerpt": (
                            "Run 'alembic upgrade head' followed by starting uvicorn."
                        ),
                        "support_type": "direct",
                    }
                ],
            }
        ]
    }

    rep2 = validator.validate_batch_response(
        category=KnowledgeCategory.OPERATIONAL_HISTORICAL,
        parsed_json=operational_json,
        supplied_chunks=[chunk_input],
        is_synthetic=False,
    )
    assert len(rep2.accepted_items) == 1
    item2 = rep2.accepted_items[0]
    assert item2.primary_domain == "OPERATIONAL_HISTORICAL"
    assert item2.structured_payload["knowledge_type"] == "deployment_runbook"

    # 3. Grounding check: Rejection if excerpt not in chunk
    ungrounded_json = {
        "items": [
            {
                "title": "Fabricated Claim",
                "description": "This claim does not appear in any chunk.",
                "knowledge_type": "historical_context",
                "evidence_refs": [
                    {
                        "chunk_id": str(chunk_id),
                        "supporting_excerpt": "Completely non-existent sentence in chunk.",
                        "support_type": "direct",
                    }
                ],
            }
        ]
    }
    rep3 = validator.validate_batch_response(
        category=KnowledgeCategory.OPERATIONAL_HISTORICAL,
        parsed_json=ungrounded_json,
        supplied_chunks=[chunk_input],
        is_synthetic=False,
    )
    assert len(rep3.accepted_items) == 0
    assert rep3.rejected_ungrounded_count == 1


def test_timeline_event_derivation_and_parsing():
    """Verify timeline date parsing and event type mapping."""
    now = datetime(2026, 11, 13, 10, 0, 0, tzinfo=UTC)

    # Second precision
    dt, prec = _parse_flexible_timestamp("2026-11-13T10:00:00Z", fallback=now)
    assert prec == "second"
    assert dt.year == 2026 and dt.month == 11 and dt.day == 13

    # Day precision
    dt_day, prec_day = _parse_flexible_timestamp("2026-11-13", fallback=now)
    assert prec_day == "day"
    assert dt_day.year == 2026 and dt_day.month == 11 and dt_day.day == 13

    # Event type mapping
    assert _derive_event_type("decisions_rationale", {}, "accepted") == "decision_accepted"
    assert _derive_event_type("work_items", {}, "completed") == "work_completed"
    assert _derive_event_type("bugs_blockers_risks", {}, "open") == "risk_reported"
    assert (
        _derive_event_type(
            "operational_historical", {"knowledge_type": "incident_response"}, "active"
        )
        == "incident"
    )
    assert _derive_event_type("project_overview_context", {}, "current") == "project_charter"


def test_knowledge_intelligence_api_endpoints(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """End-to-end integration test of Knowledge Intelligence endpoints via isolated test app."""
    with isolated_auth_app(
        monkeypatch,
        upload_storage_path=tmp_path / "ki_uploads",
        embedding_expected_dimensions=64,
    ) as ctx:
        with TestClient(ctx.app) as client:
            user = register_and_login_user(
                client, email="intel-owner@example.com", full_name="Intel Owner"
            )

            # Create an organisation
            org_res = client.post(
                "/api/v1/organisations",
                headers=user.headers,
                json={"name": "Intelligence Test Org", "slug": "intel-org-test"},
            )
            assert org_res.status_code == 201
            org_id = org_res.json()["id"]

            # Create a project
            proj_res = client.post(
                f"/api/v1/organisations/{org_id}/projects",
                headers=user.headers,
                json={"name": "Intelligence Project", "slug": "intel-proj-test"},
            )
            assert proj_res.status_code == 201
            proj_id = proj_res.json()["id"]

            # Seed a knowledge item directly in database
            with ctx.session_factory() as session:
                content_hash = hashlib.sha256(b"seed-evidence-doc").hexdigest()
                chunk_hash = hashlib.sha256(b"seed-chunk-text").hexdigest()

                ev = EvidenceItem(
                    organisation_id=uuid.UUID(org_id),
                    project_id=uuid.UUID(proj_id),
                    source_type="document_upload",
                    source_provider="manual_upload",
                    category="pdf_document",
                    source_external_id="seed-doc-1",
                    title="Architecture Decision Record",
                    content_hash=content_hash,
                    mime_type="application/pdf",
                    chunk_count=1,
                )
                session.add(ev)
                session.flush()

                chunk = EvidenceChunk(
                    organisation_id=uuid.UUID(org_id),
                    project_id=uuid.UUID(proj_id),
                    evidence_id=ev.id,
                    source_type="document_upload",
                    chunk_index=0,
                    chunk_type="section",
                    char_start=0,
                    char_end=100,
                    chunk_text=(
                        "We decided to use PostgreSQL as the canonical data store "
                        "for all project records."
                    ),
                    chunk_content_hash=chunk_hash,
                )
                session.add(chunk)
                session.flush()

                k_item = KnowledgeItem(
                    organisation_id=uuid.UUID(org_id),
                    project_id=uuid.UUID(proj_id),
                    category="decisions_rationale",
                    primary_domain="DECISIONS_RATIONALE",
                    title="Adopt PostgreSQL for Canonical Store",
                    structured_summary=(
                        "Decided to use PostgreSQL for all structured knowledge items."
                    ),
                    structured_payload={
                        "decision_status": "accepted",
                        "decision_maker": "Chief Architect",
                    },
                    normalised_status="accepted",
                    extraction_model="qwen3:8b",
                    prompt_version="p2.6-v1",
                    fingerprint="fp123456",
                    epistemic_status=EpistemicStatus.EXTRACTED.value,
                    review_status=KnowledgeReviewStatus.PENDING_REVIEW.value,
                    support_classification=SupportClassification.DIRECT.value,
                    confidence_metadata_json={"extraction_confidence": "high"},
                )
                session.add(k_item)
                session.flush()

                link = KnowledgeEvidenceLink(
                    organisation_id=uuid.UUID(org_id),
                    project_id=uuid.UUID(proj_id),
                    knowledge_item_id=k_item.id,
                    evidence_id=ev.id,
                    evidence_chunk_id=chunk.id,
                    support_type=SupportClassification.DIRECT.value,
                    source_location_json={"chunk_index": 0},
                    supporting_excerpt=(
                        "We decided to use PostgreSQL as the canonical data store "
                        "for all project records."
                    ),
                    excerpt_verified=True,
                    source_metadata_json={"source_provider": "manual_upload"},
                )
                session.add(link)
                session.commit()
                k_item_id = str(k_item.id)

            # 1. GET /domains
            res = client.get(
                f"/api/v1/projects/{proj_id}/knowledge-intelligence/domains",
                headers=user.headers,
            )
            assert res.status_code == 200
            dom_data = res.json()
            assert dom_data["total_domains"] == 8
            assert dom_data["active_domains_count"] >= 1
            dec_dom = next(
                d for d in dom_data["domains"] if d["domain_id"] == "DECISIONS_RATIONALE"
            )
            assert dec_dom["item_count"] == 1
            assert dec_dom["high_confidence_count"] == 1

            # 2. GET /summary
            res = client.get(
                f"/api/v1/projects/{proj_id}/knowledge-intelligence/summary",
                headers=user.headers,
            )
            assert res.status_code == 200
            sum_data = res.json()
            assert sum_data["total_findings"] >= 1
            assert sum_data["overall_confidence_score"] > 0
            assert "overall_readiness_pct" in sum_data

            # 3. GET /findings
            res = client.get(
                f"/api/v1/projects/{proj_id}/knowledge-intelligence/findings?domain=DECISIONS_RATIONALE",
                headers=user.headers,
            )
            assert res.status_code == 200
            f_data = res.json()
            assert f_data["total"] >= 1
            assert f_data["items"][0]["title"] == "Adopt PostgreSQL for Canonical Store"

            # 4. GET /findings/{id}
            res = client.get(
                f"/api/v1/projects/{proj_id}/knowledge-intelligence/findings/{k_item_id}",
                headers=user.headers,
            )
            assert res.status_code == 200
            detail = res.json()
            assert detail["id"] == k_item_id
            assert len(detail["evidence_links"]) == 1

            # 5. GET /timeline
            res = client.get(
                f"/api/v1/projects/{proj_id}/knowledge-intelligence/timeline",
                headers=user.headers,
            )
            assert res.status_code == 200
            tl_data = res.json()
            assert tl_data["total_events"] >= 1
            assert tl_data["items"][0]["event_type"] == "decision_accepted"


def test_knowledge_intelligence_source_acl_enforcement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Verify that Project Membership != Source Access and Knowledge Intelligence fails closed."""
    with isolated_auth_app(
        monkeypatch,
        upload_storage_path=tmp_path / "acl_uploads",
        embedding_expected_dimensions=64,
    ) as ctx:
        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client, email="proj-owner@example.com", full_name="Project Owner"
            )
            contributor = register_and_login_user(
                client, email="proj-contrib@example.com", full_name="Project Contributor"
            )

            # Create organisation and project as owner
            org_res = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "ACL Org", "slug": "acl-org"},
            )
            assert org_res.status_code == 201
            org_id = org_res.json()["id"]

            proj_res = client.post(
                f"/api/v1/organisations/{org_id}/projects",
                headers=owner.headers,
                json={"name": "ACL Project", "slug": "acl-project"},
            )
            assert proj_res.status_code == 201
            proj_id = proj_res.json()["id"]

            # Add contributor as a project member via invitation and project member assignment
            invite_and_accept_member(
                client,
                organisation_id=org_id,
                inviter_headers=owner.headers,
                invitee=contributor,
                role_name="org_member",
            )
            add_proj_m = client.post(
                f"/api/v1/projects/{proj_id}/members",
                headers=owner.headers,
                json={"user_id": str(contributor.user_id), "role_name": "project_member"},
            )
            assert add_proj_m.status_code == 201

            with ctx.session_factory() as session:
                # 1. Public evidence item (accessible to all project members)
                pub_hash = hashlib.sha256(b"public-doc").hexdigest()
                pub_chunk_hash = hashlib.sha256(b"public-chunk").hexdigest()
                pub_ev = EvidenceItem(
                    organisation_id=uuid.UUID(org_id),
                    project_id=uuid.UUID(proj_id),
                    source_type="document_upload",
                    source_provider="manual_upload",
                    category="pdf_document",
                    source_external_id="public-doc-1",
                    title="Public Architecture Document",
                    content_hash=pub_hash,
                    mime_type="application/pdf",
                    acl_scope="project_members",
                    chunk_count=1,
                )
                session.add(pub_ev)
                session.flush()

                pub_chunk = EvidenceChunk(
                    organisation_id=uuid.UUID(org_id),
                    project_id=uuid.UUID(proj_id),
                    evidence_id=pub_ev.id,
                    source_type="document_upload",
                    chunk_index=0,
                    chunk_type="section",
                    char_start=0,
                    char_end=60,
                    chunk_text="Public decision: FastAPI backend with modular architecture.",
                    chunk_content_hash=pub_chunk_hash,
                )
                session.add(pub_chunk)
                session.flush()

                pub_k = KnowledgeItem(
                    organisation_id=uuid.UUID(org_id),
                    project_id=uuid.UUID(proj_id),
                    category="technical_architecture",
                    primary_domain="ARCHITECTURE_TECHNICAL",
                    title="Adopt FastAPI Architecture",
                    structured_summary="Public architecture decision for FastAPI.",
                    structured_payload={"technical_category": "architecture"},
                    normalised_status="active",
                    extraction_model="qwen3:8b",
                    prompt_version="p2.6-v1",
                    fingerprint="fp-public-1",
                    epistemic_status=EpistemicStatus.EXTRACTED.value,
                    review_status=KnowledgeReviewStatus.PENDING_REVIEW.value,
                    support_classification=SupportClassification.DIRECT.value,
                    confidence_metadata_json={"extraction_confidence": "high"},
                )
                session.add(pub_k)
                session.flush()

                session.add(
                    KnowledgeEvidenceLink(
                        organisation_id=uuid.UUID(org_id),
                        project_id=uuid.UUID(proj_id),
                        knowledge_item_id=pub_k.id,
                        evidence_id=pub_ev.id,
                        evidence_chunk_id=pub_chunk.id,
                        support_type=SupportClassification.DIRECT.value,
                        source_location_json={"chunk_index": 0},
                        supporting_excerpt=(
                            "Public decision: FastAPI backend with modular architecture."
                        ),
                        excerpt_verified=True,
                        source_metadata_json={"source_provider": "manual_upload"},
                    )
                )

                # 2. Restricted GitHub source connection and policy (accessible ONLY to owner)
                gh_conn = SourceConnection(
                    organisation_id=uuid.UUID(org_id),
                    provider=IntegrationProvider.GITHUB.value,
                    display_name="Private Infra GitHub",
                    created_by_user_id=owner.user_id,
                    status="active",
                )
                session.add(gh_conn)
                session.flush()

                restricted_policy = SourceAccessPolicy(
                    organisation_id=uuid.UUID(org_id),
                    project_id=uuid.UUID(proj_id),
                    source_connection_id=gh_conn.id,
                    provider=IntegrationProvider.GITHUB.value,
                    scope_identifier="acme/secret-infra",
                    visibility_policy=SourceVisibilityPolicy.RESTRICTED_FAIL_CLOSED.value,
                    sync_permission_status=SourcePermissionVerificationStatus.VERIFIED.value,
                    allowed_user_ids=[str(owner.user_id)],
                )
                session.add(restricted_policy)
                session.flush()

                priv_hash = hashlib.sha256(b"restricted-issue").hexdigest()
                priv_chunk_hash = hashlib.sha256(b"restricted-chunk").hexdigest()
                priv_ev = EvidenceItem(
                    organisation_id=uuid.UUID(org_id),
                    project_id=uuid.UUID(proj_id),
                    source_type=EvidenceSourceType.GITHUB.value,
                    source_provider="github",
                    category="issue",
                    source_external_id="acme/secret-infra#42",
                    title="Confidential Vault Credential Migration",
                    content_hash=priv_hash,
                    acl_scope="source_restricted",
                    source_access_policy_id=restricted_policy.id,
                    chunk_count=1,
                )
                session.add(priv_ev)
                session.flush()

                priv_chunk = EvidenceChunk(
                    organisation_id=uuid.UUID(org_id),
                    project_id=uuid.UUID(proj_id),
                    evidence_id=priv_ev.id,
                    source_type="github",
                    chunk_index=0,
                    chunk_type="issue_body",
                    char_start=0,
                    char_end=70,
                    chunk_text="Confidential: Rotate production database secrets via Vault agent.",
                    chunk_content_hash=priv_chunk_hash,
                )
                session.add(priv_chunk)
                session.flush()

                priv_k = KnowledgeItem(
                    organisation_id=uuid.UUID(org_id),
                    project_id=uuid.UUID(proj_id),
                    category="operational_historical",
                    primary_domain="OPERATIONAL_HISTORICAL",
                    title="Production Secret Rotation Runbook",
                    structured_summary=(
                        "Confidential procedure for rotating production database secrets."
                    ),
                    structured_payload={"knowledge_type": "deployment_runbook"},
                    normalised_status="active",
                    extraction_model="qwen3:8b",
                    prompt_version="p2.6-v1",
                    fingerprint="fp-private-1",
                    epistemic_status=EpistemicStatus.EXTRACTED.value,
                    review_status=KnowledgeReviewStatus.PENDING_REVIEW.value,
                    support_classification=SupportClassification.DIRECT.value,
                    confidence_metadata_json={"extraction_confidence": "high"},
                )
                session.add(priv_k)
                session.flush()

                session.add(
                    KnowledgeEvidenceLink(
                        organisation_id=uuid.UUID(org_id),
                        project_id=uuid.UUID(proj_id),
                        knowledge_item_id=priv_k.id,
                        evidence_id=priv_ev.id,
                        evidence_chunk_id=priv_chunk.id,
                        support_type=SupportClassification.DIRECT.value,
                        source_location_json={"chunk_index": 0},
                        supporting_excerpt=(
                            "Confidential: Rotate production database secrets via Vault agent."
                        ),
                        excerpt_verified=True,
                        source_metadata_json={"source_provider": "github"},
                    )
                )
                session.commit()
                priv_k_id = str(priv_k.id)
                pub_k_id = str(pub_k.id)

            # Owner sees BOTH public and restricted items
            res_owner = client.get(
                f"/api/v1/projects/{proj_id}/knowledge-intelligence/findings",
                headers=owner.headers,
            )
            assert res_owner.status_code == 200
            owner_items = res_owner.json()["items"]
            assert len(owner_items) == 2

            # Contributor (project member, but NOT on restricted policy) sees ONLY public item
            res_contrib = client.get(
                f"/api/v1/projects/{proj_id}/knowledge-intelligence/findings",
                headers=contributor.headers,
            )
            assert res_contrib.status_code == 200
            contrib_items = res_contrib.json()["items"]
            assert len(contrib_items) == 1
            assert contrib_items[0]["id"] == pub_k_id

            # Contributor requesting the restricted item directly FAILS CLOSED with 403 Forbidden
            res_direct = client.get(
                f"/api/v1/projects/{proj_id}/knowledge-intelligence/findings/{priv_k_id}",
                headers=contributor.headers,
            )
            assert res_direct.status_code == 403
            assert res_direct.json()["error"]["code"] == "SOURCE_ACCESS_DENIED"

            # Contributor summary counts only the 1 accessible item
            sum_contrib = client.get(
                f"/api/v1/projects/{proj_id}/knowledge-intelligence/summary",
                headers=contributor.headers,
            )
            assert sum_contrib.status_code == 200
            assert sum_contrib.json()["total_findings"] == 1
