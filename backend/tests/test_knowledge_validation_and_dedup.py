"""Tests for Phase 2.6 NO EVIDENCE -> NO CLAIM validator and conservative deduplication."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.models.enums import (
    EpistemicStatus,
    EvidenceChunkType,
    EvidenceProcessingStatus,
    ExtractionRunScope,
    KnowledgeCategory,
    KnowledgeReviewStatus,
    OrganisationStatus,
    ProjectStatus,
    ProjectVisibility,
    SupportClassification,
    UserStatus,
)
from app.models.evidence import EvidenceChunk, EvidenceItem
from app.models.organisation import Organisation
from app.models.project import Project
from app.models.user import User
from app.repositories.knowledge import KnowledgeRepository
from app.services.extraction_prompts import ChunkPromptInput
from app.services.knowledge_validator import KnowledgeCandidateValidator


def _chunk(
    *,
    chunk_id: uuid.UUID | None = None,
    evidence_id: uuid.UUID | None = None,
    organisation_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    text: str = "",
    author: str | None = "Alex Chen",
    title: str = "adr-001.pdf",
) -> ChunkPromptInput:
    now = datetime(2026, 11, 10, 12, 0, tzinfo=UTC).isoformat()
    return ChunkPromptInput(
        chunk_id=chunk_id or uuid.uuid4(),
        evidence_id=evidence_id or uuid.uuid4(),
        organisation_id=organisation_id or uuid.uuid4(),
        project_id=project_id or uuid.uuid4(),
        chunk_index=0,
        chunk_type="document_section",
        page_number=1,
        section_title="Overview",
        char_start=0,
        char_end=len(text),
        chunk_text=text,
        chunk_content_hash="c" * 64,
        source_type="document_upload",
        source_provider="local_upload",
        source_external_id="upload:doc1",
        source_url=None,
        source_author_identity=author,
        title=title,
        source_created_at_iso=now,
        source_updated_at_iso=now,
        extracted_at_iso=now,
        evidence_content_hash="d" * 64,
    )


def test_validator_enforces_no_evidence_no_claim_and_exact_or_ws_excerpts() -> None:
    validator = KnowledgeCandidateValidator()
    ch = _chunk(
        text=(
            "We chose PostgreSQL 16 as our primary canonical datastore on 2026-10-01.\n"
            "Alternative   considered:   Neo4j   for   relationships."
        )
    )
    other_chunk_id = uuid.uuid4()

    report = validator.validate_batch_response(
        category=KnowledgeCategory.DECISIONS_RATIONALE,
        parsed_json={
            "items": [
                # 1. Valid exact match -> accepted
                {
                    "title": "Use PostgreSQL 16 as canonical datastore",
                    "description": "PostgreSQL 16 selected over Neo4j.",
                    "decision_category": "architectural",
                    "decision_maker": "Alex Chen",
                    "decision_date": "2026-10-01",
                    "rationale": "Relational durability.",
                    "alternatives_considered": ["Neo4j"],
                    "chosen_approach": "PostgreSQL 16",
                    "consequences_or_tradeoffs": [],
                    "affected_components": ["backend"],
                    "decision_status": "accepted",
                    "is_interpretation": False,
                    "is_uncertain": False,
                    "uncertainty_reason": None,
                    "confidence_level": "high",
                    "evidence_refs": [
                        {
                            "chunk_id": str(ch.chunk_id),
                            "supporting_excerpt": (
                                "We chose PostgreSQL 16 as our primary canonical datastore"
                            ),
                            "support_type": "direct",
                        }
                    ],
                },
                # 2. Valid whitespace-normalised match -> accepted
                {
                    "title": "Rejected Neo4j alternative",
                    "description": "Neo4j was evaluated and not chosen.",
                    "decision_category": "architectural",
                    "decision_status": "rejected",
                    "is_interpretation": False,
                    "is_uncertain": False,
                    "confidence_level": "medium",
                    "evidence_refs": [
                        {
                            "chunk_id": str(ch.chunk_id),
                            "supporting_excerpt": (
                                "Alternative considered: Neo4j for relationships."
                            ),
                            "support_type": "direct",
                        }
                    ],
                },
                # 3. Paraphrased / hallucinated quote -> REJECTED
                {
                    "title": "Hallucinated decision",
                    "description": "Team switched to DynamoDB.",
                    "decision_status": "accepted",
                    "confidence_level": "high",
                    "evidence_refs": [
                        {
                            "chunk_id": str(ch.chunk_id),
                            "supporting_excerpt": "Team switched completely to DynamoDB last week.",
                            "support_type": "direct",
                        }
                    ],
                },
                # 4. Out-of-batch chunk_id -> REJECTED
                {
                    "title": "Wrong chunk citation",
                    "description": "PostgreSQL chosen.",
                    "decision_status": "accepted",
                    "confidence_level": "high",
                    "evidence_refs": [
                        {
                            "chunk_id": str(other_chunk_id),
                            "supporting_excerpt": "We chose PostgreSQL 16",
                            "support_type": "direct",
                        }
                    ],
                },
                # 5. Missing evidence_refs -> schema REJECTED
                {
                    "title": "No refs",
                    "description": "No links provided.",
                    "decision_status": "accepted",
                    "evidence_refs": [],
                },
            ]
        },
        supplied_chunks=[ch],
        is_synthetic=False,
    )

    assert report.candidates_received == 5
    assert len(report.accepted_items) == 2
    assert report.rejected_schema_count == 1
    assert report.rejected_ungrounded_count == 2
    assert report.accepted_items[0].evidence_links[0].excerpt_match_mode == "exact"
    assert report.accepted_items[1].evidence_links[0].excerpt_match_mode == "normalized_whitespace"
    for item in report.accepted_items:
        assert item.epistemic_status != EpistemicStatus.HUMAN_VERIFIED.value
        assert item.review_status == KnowledgeReviewStatus.PENDING_REVIEW.value


def test_validator_prevents_severity_hallucination_and_preserves_epistemic_tiers() -> None:
    validator = KnowledgeCandidateValidator()

    risk_chunk_no_sev = _chunk(
        text="Worker retry stalls when Ollama times out during OCR fallback."
    )
    risk_chunk_with_sev = _chunk(
        text="Issue P1 critical blocker: PostgreSQL connection pool exhausted under load."
    )
    risk_report_1 = validator.validate_batch_response(
        category=KnowledgeCategory.BUGS_BLOCKERS_RISKS,
        parsed_json={
            "items": [
                {
                    "title": "Worker retry stalls during OCR timeout",
                    "description": "Worker stalls when Ollama times out.",
                    "risk_category": "operational_risk",
                    "severity": "critical",
                    "risk_status": "open",
                    "confidence_level": "high",
                    "evidence_refs": [
                        {
                            "chunk_id": str(risk_chunk_no_sev.chunk_id),
                            "supporting_excerpt": (
                                "Worker retry stalls when Ollama times out during OCR fallback."
                            ),
                            "support_type": "direct",
                        }
                    ],
                },
            ]
        },
        supplied_chunks=[risk_chunk_no_sev],
        is_synthetic=False,
    )
    risk_report_2 = validator.validate_batch_response(
        category=KnowledgeCategory.BUGS_BLOCKERS_RISKS,
        parsed_json={
            "items": [
                {
                    "title": "PostgreSQL pool exhausted under load",
                    "description": "Pool exhausts under load.",
                    "risk_category": "blocker",
                    "severity": "critical",
                    "risk_status": "blocked",
                    "confidence_level": "high",
                    "evidence_refs": [
                        {
                            "chunk_id": str(risk_chunk_with_sev.chunk_id),
                            "supporting_excerpt": (
                                "Issue P1 critical blocker: PostgreSQL connection pool "
                                "exhausted under load."
                            ),
                            "support_type": "direct",
                        }
                    ],
                },
            ]
        },
        supplied_chunks=[risk_chunk_with_sev],
        is_synthetic=False,
    )
    assert len(risk_report_1.accepted_items) == 1
    assert len(risk_report_2.accepted_items) == 1
    assert risk_report_1.accepted_items[0].structured_payload["severity"] == "unspecified"
    assert "severity" in risk_report_1.accepted_items[0].confidence_metadata["missing_fields"]
    assert risk_report_2.accepted_items[0].structured_payload["severity"] == "critical"

    # Interpretation / inferred_contribution enforces AI_INTERPRETED tier
    resp_chunk = _chunk(
        text=(
            "Commits on backend/auth.py were authored by Alex Chen and reviewed by @achen.\n"
            "Handover note mentions alex.chen@acme.com managed rotating tokens."
        )
    )
    resp_report = validator.validate_batch_response(
        category=KnowledgeCategory.RESPONSIBILITIES_OWNERSHIP,
        parsed_json={
            "items": [
                {
                    "person_identity": "Alex Chen",
                    "person_identifier_type": "display_name",
                    "title": "Auth module contributor",
                    "description": "Authored auth.py commits.",
                    "component_or_workstream": "backend/auth.py",
                    "ownership_role": "maintainer",
                    "ownership_basis": "inferred_contribution",
                    "ownership_status": "active",
                    "is_interpretation": False,
                    "confidence_level": "medium",
                    "evidence_refs": [
                        {
                            "chunk_id": str(resp_chunk.chunk_id),
                            "supporting_excerpt": (
                                "Commits on backend/auth.py were authored by Alex Chen"
                            ),
                            "support_type": "interpretation",
                        }
                    ],
                },
                {
                    "person_identity": "alex.chen@acme.com",
                    "person_identifier_type": "email",
                    "title": "Token rotation owner",
                    "description": "Managed rotating tokens.",
                    "component_or_workstream": "backend/auth.py",
                    "ownership_role": "maintainer",
                    "ownership_basis": "explicitly_assigned",
                    "ownership_status": "active",
                    "is_interpretation": False,
                    "confidence_level": "high",
                    "evidence_refs": [
                        {
                            "chunk_id": str(resp_chunk.chunk_id),
                            "supporting_excerpt": (
                                "alex.chen@acme.com managed rotating tokens."
                            ),
                            "support_type": "direct",
                        }
                    ],
                },
            ]
        },
        supplied_chunks=[resp_chunk],
        is_synthetic=False,
    )
    assert len(resp_report.accepted_items) == 2
    assert (
        resp_report.accepted_items[0].epistemic_status
        == EpistemicStatus.AI_INTERPRETED.value
    )
    assert (
        resp_report.accepted_items[1].epistemic_status
        == EpistemicStatus.EXTRACTED.value
    )
    # Distinct source identities MUST NOT collapse to the same fingerprint
    assert resp_report.accepted_items[0].fingerprint != resp_report.accepted_items[1].fingerprint


def test_validator_supports_remaining_categories_verbatim_identifiers_and_dependencies() -> None:
    validator = KnowledgeCandidateValidator()

    work_ch = _chunk(text="NEX-42 is in progress by Priya Nair to build ChromaDB indexing.")
    work_rep = validator.validate_batch_response(
        category=KnowledgeCategory.WORK_ITEMS,
        parsed_json={
            "items": [
                {
                    "title": "NEX-42: Build ChromaDB indexing",
                    "description": "Implement semantic chunk indexing.",
                    "work_category": "feature",
                    "work_status": "in_progress",
                    "assignee": "Priya Nair",
                    "related_references": ["NEX-42"],
                    "evidence_refs": [
                        {
                            "chunk_id": str(work_ch.chunk_id),
                            "supporting_excerpt": (
                                "NEX-42 is in progress by Priya Nair to build ChromaDB indexing."
                            ),
                            "support_type": "direct",
                        }
                    ],
                }
            ]
        },
        supplied_chunks=[work_ch],
        is_synthetic=False,
    )
    assert len(work_rep.accepted_items) == 1
    assert work_rep.accepted_items[0].normalised_status == "in_progress"

    tech_ch = _chunk(
        text="Route POST /api/v1/projects/{id}/knowledge/extract queues a background job."
    )
    tech_rep = validator.validate_batch_response(
        category=KnowledgeCategory.TECHNICAL_ARCHITECTURE,
        parsed_json={
            "items": [
                {
                    "title": "Knowledge extraction trigger endpoint",
                    "description": "Enqueues extraction job via POST route.",
                    "technical_category": "api_behaviour",
                    "exact_identifiers": [
                        "/api/v1/projects/{id}/knowledge/extract"
                    ],
                    "components": ["knowledge-routes"],
                    "technical_status": "active",
                    "evidence_refs": [
                        {
                            "chunk_id": str(tech_ch.chunk_id),
                            "supporting_excerpt": (
                                "Route POST /api/v1/projects/{id}/knowledge/extract "
                                "queues a background job."
                            ),
                            "support_type": "direct",
                        }
                    ],
                }
            ]
        },
        supplied_chunks=[tech_ch],
        is_synthetic=False,
    )
    assert len(tech_rep.accepted_items) == 1
    assert "/api/v1/projects/{id}/knowledge/extract" in (
        tech_rep.accepted_items[0].structured_payload["exact_identifiers"]
    )

    dep_ch = _chunk(text="RetrievalService depends on Ollama nomic-embed-text and ChromaDB.")
    dep_rep = validator.validate_batch_response(
        category=KnowledgeCategory.DEPENDENCIES,
        parsed_json={
            "items": [
                {
                    "title": "RetrievalService -> nomic-embed-text",
                    "description": "RetrievalService requires nomic-embed-text.",
                    "source_item": "RetrievalService",
                    "target_item": "nomic-embed-text",
                    "dependency_type": "technical_service",
                    "direction": "depends_on",
                    "dependency_status": "active",
                    "evidence_refs": [
                        {
                            "chunk_id": str(dep_ch.chunk_id),
                            "supporting_excerpt": (
                                "RetrievalService depends on Ollama nomic-embed-text"
                            ),
                            "support_type": "direct",
                        }
                    ],
                }
            ]
        },
        supplied_chunks=[dep_ch],
        is_synthetic=False,
    )
    assert len(dep_rep.accepted_items) == 1
    assert dep_rep.accepted_items[0].structured_payload["direction"] == "depends_on"


def _sqlite_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn: Any, _: Any) -> None:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    factory: sessionmaker[Session] = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )
    return factory()


def test_conservative_dedup_corroborates_compatible_facts_and_keeps_conflicts_separate() -> None:
    session = _sqlite_session()
    validator = KnowledgeCandidateValidator()
    repo = KnowledgeRepository(session)

    user = User(
        full_name="Dedup Tester",
        email="dedup@example.com",
        password_hash="hash",
        status=UserStatus.ACTIVE.value,
    )
    session.add(user)
    session.flush()
    org = Organisation(
        name="Org",
        slug="org",
        created_by_id=user.id,
        status=OrganisationStatus.ACTIVE.value,
    )
    session.add(org)
    session.flush()
    proj = Project(
        organisation_id=org.id,
        name="Proj",
        slug="proj",
        status=ProjectStatus.ACTIVE.value,
        visibility=ProjectVisibility.PRIVATE.value,
        created_by_id=user.id,
        owner_id=user.id,
    )
    session.add(proj)
    session.flush()

    ev1 = EvidenceItem(
        organisation_id=org.id,
        project_id=proj.id,
        uploaded_by_user_id=user.id,
        source_type="document_upload",
        source_provider="local_upload",
        category="pdf_document",
        source_external_id="upload:1",
        title="adr.pdf",
        content_hash="1" * 64,
        acl_scope="project_members",
        processing_status=EvidenceProcessingStatus.EXTRACTED.value,
    )
    ev2 = EvidenceItem(
        organisation_id=org.id,
        project_id=proj.id,
        uploaded_by_user_id=user.id,
        source_type="github",
        source_provider="github",
        category="pull_request",
        source_external_id="github:repo#12",
        title="PR #12",
        content_hash="2" * 64,
        acl_scope="project_members",
        processing_status=EvidenceProcessingStatus.EXTRACTED.value,
    )
    ev3 = EvidenceItem(
        organisation_id=org.id,
        project_id=proj.id,
        uploaded_by_user_id=user.id,
        source_type="jira",
        source_provider="jira",
        category="issue",
        source_external_id="jira:NEX-9",
        title="NEX-9",
        content_hash="3" * 64,
        acl_scope="project_members",
        processing_status=EvidenceProcessingStatus.EXTRACTED.value,
    )
    session.add_all([ev1, ev2, ev3])
    session.flush()

    db_c1 = EvidenceChunk(
        organisation_id=org.id,
        project_id=proj.id,
        evidence_id=ev1.id,
        chunk_index=0,
        chunk_type=EvidenceChunkType.DOCUMENT_SECTION.value,
        char_start=0,
        char_end=52,
        char_count=52,
        token_estimate=10,
        chunk_text="ADR: We adopted PostgreSQL for structured relations.",
        chunk_content_hash="c1" * 32,
        search_identifier_text="PostgreSQL",
        source_type="document_upload",
        acl_scope="project_members",
        metadata_json={},
    )
    db_c2 = EvidenceChunk(
        organisation_id=org.id,
        project_id=proj.id,
        evidence_id=ev2.id,
        chunk_index=0,
        chunk_type=EvidenceChunkType.PR_BODY.value,
        char_start=0,
        char_end=69,
        char_count=69,
        token_estimate=12,
        chunk_text="PR discussion confirms we adopted PostgreSQL for structured relations.",
        chunk_content_hash="c2" * 32,
        search_identifier_text="PostgreSQL",
        source_type="github",
        acl_scope="project_members",
        metadata_json={},
    )
    db_c3 = EvidenceChunk(
        organisation_id=org.id,
        project_id=proj.id,
        evidence_id=ev3.id,
        chunk_index=0,
        chunk_type=EvidenceChunkType.ISSUE_BODY.value,
        char_start=0,
        char_end=69,
        char_count=69,
        token_estimate=12,
        chunk_text="Proposal rejected: team rejected PostgreSQL for structured relations.",
        chunk_content_hash="c3" * 32,
        search_identifier_text="PostgreSQL",
        source_type="jira",
        acl_scope="project_members",
        metadata_json={},
    )
    session.add_all([db_c1, db_c2, db_c3])
    session.flush()

    run = repo.create_extraction_run(
        organisation_id=org.id,
        project_id=proj.id,
        background_job_id=None,
        evidence_id=None,
        triggered_by_user_id=user.id,
        scope_type=ExtractionRunScope.PROJECT.value,
        target_categories=[KnowledgeCategory.DECISIONS_RATIONALE.value],
        model_name="qwen3:8b",
        prompt_version="p2.6-v1",
    )

    c1 = _chunk(
        chunk_id=db_c1.id,
        evidence_id=ev1.id,
        organisation_id=org.id,
        project_id=proj.id,
        text=db_c1.chunk_text,
    )
    c2 = _chunk(
        chunk_id=db_c2.id,
        evidence_id=ev2.id,
        organisation_id=org.id,
        project_id=proj.id,
        text=db_c2.chunk_text,
    )
    c3_conflict = _chunk(
        chunk_id=db_c3.id,
        evidence_id=ev3.id,
        organisation_id=org.id,
        project_id=proj.id,
        text=db_c3.chunk_text,
    )

    d1 = validator.validate_batch_response(
        category=KnowledgeCategory.DECISIONS_RATIONALE,
        parsed_json={
            "items": [
                {
                    "title": "Adopt PostgreSQL for structured relations",
                    "description": "Use PostgreSQL.",
                    "decision_status": "accepted",
                    "evidence_refs": [
                        {
                            "chunk_id": str(c1.chunk_id),
                            "supporting_excerpt": (
                                "We adopted PostgreSQL for structured relations."
                            ),
                            "support_type": "direct",
                        }
                    ],
                }
            ]
        },
        supplied_chunks=[c1],
        is_synthetic=False,
    ).accepted_items[0]

    d2 = validator.validate_batch_response(
        category=KnowledgeCategory.DECISIONS_RATIONALE,
        parsed_json={
            "items": [
                {
                    "title": "Adopt PostgreSQL for structured relations",
                    "description": "Confirmed in PR.",
                    "decision_status": "accepted",
                    "evidence_refs": [
                        {
                            "chunk_id": str(c2.chunk_id),
                            "supporting_excerpt": (
                                "we adopted PostgreSQL for structured relations."
                            ),
                            "support_type": "direct",
                        }
                    ],
                }
            ]
        },
        supplied_chunks=[c2],
        is_synthetic=False,
    ).accepted_items[0]

    d3_conflict = validator.validate_batch_response(
        category=KnowledgeCategory.DECISIONS_RATIONALE,
        parsed_json={
            "items": [
                {
                    "title": "Adopt PostgreSQL for structured relations",
                    "description": "Alternative view rejected.",
                    "decision_status": "rejected",
                    "evidence_refs": [
                        {
                            "chunk_id": str(c3_conflict.chunk_id),
                            "supporting_excerpt": (
                                "team rejected PostgreSQL for structured relations."
                            ),
                            "support_type": "direct",
                        }
                    ],
                }
            ]
        },
        supplied_chunks=[c3_conflict],
        is_synthetic=False,
    ).accepted_items[0]

    # Synthetic duplicate with same content must stay isolated from real items
    d4_synthetic = validator.validate_batch_response(
        category=KnowledgeCategory.DECISIONS_RATIONALE,
        parsed_json={
            "items": [
                {
                    "title": "Adopt PostgreSQL for structured relations",
                    "description": "Synthetic copy.",
                    "decision_status": "accepted",
                    "evidence_refs": [
                        {
                            "chunk_id": str(c1.chunk_id),
                            "supporting_excerpt": (
                                "We adopted PostgreSQL for structured relations."
                            ),
                            "support_type": "direct",
                        }
                    ],
                }
            ]
        },
        supplied_chunks=[c1],
        is_synthetic=True,
    ).accepted_items[0]

    item1, merged1 = repo.upsert_validated_draft(
        organisation_id=org.id,
        project_id=proj.id,
        extraction_run_id=run.id,
        model_name="qwen3:8b",
        prompt_version="p2.6-v1",
        draft=d1,
    )
    item2, merged2 = repo.upsert_validated_draft(
        organisation_id=org.id,
        project_id=proj.id,
        extraction_run_id=run.id,
        model_name="qwen3:8b",
        prompt_version="p2.6-v1",
        draft=d2,
    )
    item3, merged3 = repo.upsert_validated_draft(
        organisation_id=org.id,
        project_id=proj.id,
        extraction_run_id=run.id,
        model_name="qwen3:8b",
        prompt_version="p2.6-v1",
        draft=d3_conflict,
    )
    item4, merged4 = repo.upsert_validated_draft(
        organisation_id=org.id,
        project_id=proj.id,
        extraction_run_id=run.id,
        model_name="qwen3:8b",
        prompt_version="p2.6-v1",
        draft=d4_synthetic,
    )
    session.commit()

    assert merged1 is False
    assert merged2 is True
    assert item1.id == item2.id
    assert item1.support_classification == SupportClassification.CORROBORATED.value
    assert len(item1.evidence_links) == 2

    assert merged3 is False
    assert item3.id != item1.id
    assert item3.normalised_status == "rejected"

    assert merged4 is False
    assert item4.id != item1.id
    assert item4.is_synthetic is True
    session.close()
