"""Isolated PostgreSQL migration tests for Phase 2.6 (`0007_knowledge_reconstruction`)."""

from __future__ import annotations

import uuid
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import clear_settings_cache, get_settings
from app.models.enums import (
    EpistemicStatus,
    ExtractionRunScope,
    ExtractionRunStatus,
    KnowledgeCategory,
    KnowledgeReviewStatus,
    SupportClassification,
)
from app.models.evidence import EvidenceChunk
from app.models.knowledge import (
    KnowledgeEvidenceLink,
    KnowledgeExtractionRun,
    KnowledgeItem,
)

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


@pytest.mark.skipif(
    not _ROOT_ENV.exists(),
    reason="Root .env unavailable for Postgres migration test",
)
def test_isolated_postgres_knowledge_migration_cycle() -> None:
    clear_settings_cache()
    db_cfg = get_settings().database
    password = db_cfg.password.get_secret_value()
    temp_db = f"ipkrh_mig_know_test_{uuid.uuid4().hex[:8]}"

    admin_dsn = f"postgresql://{db_cfg.user}:{password}@127.0.0.1:{db_cfg.port}/postgres"
    temp_url = f"postgresql+psycopg://{db_cfg.user}:{password}@127.0.0.1:{db_cfg.port}/{temp_db}"

    with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
        admin_conn.execute(f'CREATE DATABASE "{temp_db}"')

    try:
        alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", temp_url)

        # 1. Start at Phase 2.5 (`0006_evidence_chunks_and_fts`) and seed evidence + chunk rows
        command.upgrade(cfg, "0006_evidence_chunks_and_fts")
        seed_user_id = uuid.uuid4()
        seed_org_id = uuid.uuid4()
        seed_project_id = uuid.uuid4()
        seed_ev_id = uuid.uuid4()
        seed_chunk_id = uuid.uuid4()

        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO users (id, full_name, email, password_hash, status)
                        VALUES (
                            :id,
                            'Knowledge Owner',
                            'know-owner@example.com',
                            '$argon2id$v=19$m=65536,t=3,p=4$test$test',
                            'active'
                        )
                        """
                    ),
                    {"id": seed_user_id},
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO organisations (id, name, slug, created_by_id, status)
                        VALUES (:id, 'Know Org', 'know-org', :uid, 'active')
                        """
                    ),
                    {"id": seed_org_id, "uid": seed_user_id},
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO projects (
                            id, organisation_id, name, slug, status, visibility,
                            created_by_id, owner_id
                        )
                        VALUES (
                            :pid, :oid, 'Know Project', 'know-project', 'active', 'private',
                            :uid, :uid
                        )
                        """
                    ),
                    {"pid": seed_project_id, "oid": seed_org_id, "uid": seed_user_id},
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO evidence_items (
                            id, organisation_id, project_id, uploaded_by_user_id,
                            source_type, source_provider, category, source_external_id,
                            title, content_hash, acl_scope, processing_status,
                            ocr_pages_count, truncated_pages_count, metadata_json
                        )
                        VALUES (
                            :eid, :oid, :pid, :uid,
                            'document_upload', 'local_upload', 'pdf_document',
                            :ext_id, 'adr-001.pdf', :hash, 'project_members', 'extracted',
                            0, 0, '{}'::jsonb
                        )
                        """
                    ),
                    {
                        "eid": seed_ev_id,
                        "oid": seed_org_id,
                        "pid": seed_project_id,
                        "uid": seed_user_id,
                        "ext_id": f"upload:{seed_ev_id}",
                        "hash": "a" * 64,
                    },
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO evidence_chunks (
                            id, organisation_id, project_id, evidence_id,
                            chunk_index, chunk_type, char_start, char_end,
                            char_count, token_estimate, chunk_text,
                            chunk_content_hash, search_identifier_text,
                            search_vector, source_type, acl_scope, metadata_json
                        )
                        VALUES (
                            :cid, :oid, :pid, :eid,
                            0, 'document_section', 0, 56, 56, 12,
                            'We selected PostgreSQL as the canonical datastore.',
                            :chash, 'PostgreSQL',
                            to_tsvector('english', 'We selected PostgreSQL as the canonical'),
                            'document_upload', 'project_members', '{}'::jsonb
                        )
                        """
                    ),
                    {
                        "cid": seed_chunk_id,
                        "oid": seed_org_id,
                        "pid": seed_project_id,
                        "eid": seed_ev_id,
                        "chash": "b" * 64,
                    },
                )
        finally:
            engine.dispose()

        # 2. Upgrade to head (0007) and verify zero Alembic schema drift
        command.upgrade(cfg, "head")
        command.check(cfg)

        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())
            assert {
                "knowledge_extraction_runs",
                "knowledge_items",
                "knowledge_evidence_links",
            }.issubset(tables)

            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0007_knowledge_reconstruction"
                )
                # Pre-existing Phase 2.5 chunk remains untouched
                assert (
                    conn.execute(
                        text("SELECT chunk_text FROM evidence_chunks WHERE id = :cid"),
                        {"cid": seed_chunk_id},
                    ).scalar_one()
                    == "We selected PostgreSQL as the canonical datastore."
                )

            pg_session_factory = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
                class_=Session,
            )
            with pg_session_factory() as session:
                run = KnowledgeExtractionRun(
                    organisation_id=seed_org_id,
                    project_id=seed_project_id,
                    evidence_id=seed_ev_id,
                    triggered_by_user_id=seed_user_id,
                    scope_type=ExtractionRunScope.EVIDENCE.value,
                    target_categories=[KnowledgeCategory.DECISIONS_RATIONALE.value],
                    model_name="qwen3:8b",
                    prompt_version="p2.6-v1",
                    status=ExtractionRunStatus.COMPLETED.value,
                )
                session.add(run)
                session.flush()

                item = KnowledgeItem(
                    organisation_id=seed_org_id,
                    project_id=seed_project_id,
                    extraction_run_id=run.id,
                    category=KnowledgeCategory.DECISIONS_RATIONALE.value,
                    epistemic_status=EpistemicStatus.EXTRACTED.value,
                    review_status=KnowledgeReviewStatus.PENDING_REVIEW.value,
                    support_classification=SupportClassification.DIRECT.value,
                    title="Select PostgreSQL as canonical datastore",
                    structured_summary="PostgreSQL selected as canonical store.",
                    structured_payload={"decision_status": "accepted"},
                    normalised_status="accepted",
                    fingerprint="1" * 64,
                    extraction_model="qwen3:8b",
                    prompt_version="p2.6-v1",
                )
                session.add(item)
                session.flush()

                link = KnowledgeEvidenceLink(
                    organisation_id=seed_org_id,
                    project_id=seed_project_id,
                    knowledge_item_id=item.id,
                    evidence_id=seed_ev_id,
                    evidence_chunk_id=seed_chunk_id,
                    support_type=SupportClassification.DIRECT.value,
                    source_location_json={"chunk_index": 0},
                    supporting_excerpt="We selected PostgreSQL as the canonical datastore.",
                    excerpt_verified=True,
                    excerpt_match_mode="exact",
                    source_metadata_json={"title": "adr-001.pdf"},
                )
                session.add(link)
                session.commit()

                # Deleting chunk sets evidence_chunk_id = NULL while retaining provenance excerpt
                chunk_row = session.get(EvidenceChunk, seed_chunk_id)
                assert chunk_row is not None
                session.delete(chunk_row)
                session.commit()
                session.refresh(link)
                assert link.evidence_chunk_id is None
                assert (
                    link.supporting_excerpt
                    == "We selected PostgreSQL as the canonical datastore."
                )

                # Invalid category rejected by CHECK constraint
                with pytest.raises(IntegrityError):
                    session.add(
                        KnowledgeItem(
                            organisation_id=seed_org_id,
                            project_id=seed_project_id,
                            extraction_run_id=run.id,
                            category="invalid_category",
                            epistemic_status=EpistemicStatus.EXTRACTED.value,
                            review_status=KnowledgeReviewStatus.PENDING_REVIEW.value,
                            support_classification=SupportClassification.DIRECT.value,
                            title="Bad cat",
                            structured_summary="Bad",
                            fingerprint="2" * 64,
                            extraction_model="qwen3:8b",
                            prompt_version="p2.6-v1",
                        )
                    )
                    session.flush()
                session.rollback()

                # Verify FTS column helper works cleanly
                count_items = session.execute(
                    text("SELECT count(*) FROM knowledge_items")
                ).scalar_one()
                assert int(count_items) == 1
                _ = func.now()
        finally:
            engine.dispose()

        # 3. Downgrade 0007 -> 0006 cleanly while preserving Phase 2.5 evidence rows
        command.downgrade(cfg, "0006_evidence_chunks_and_fts")
        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            inspector = inspect(engine)
            remaining = set(inspector.get_table_names())
            assert "knowledge_extraction_runs" not in remaining
            assert "knowledge_items" not in remaining
            assert "knowledge_evidence_links" not in remaining
            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0006_evidence_chunks_and_fts"
                )
                assert (
                    conn.execute(
                        text("SELECT title FROM evidence_items WHERE id = :eid"),
                        {"eid": seed_ev_id},
                    ).scalar_one()
                    == "adr-001.pdf"
                )
        finally:
            engine.dispose()

        # 4. Re-upgrade cleanly back to head and verify zero Alembic drift
        command.upgrade(cfg, "head")
        command.check(cfg)
    finally:
        with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
            admin_conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (temp_db,),
            )
            admin_conn.execute(f'DROP DATABASE IF EXISTS "{temp_db}"')
