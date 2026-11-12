"""Isolated PostgreSQL migration tests for Phase 2.5 (`0006_evidence_chunks_and_fts`)."""

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
from app.models.enums import BackgroundJobType, EvidenceChunkType
from app.models.evidence import EvidenceChunk, EvidenceItem
from app.models.job import BackgroundJob

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


@pytest.mark.skipif(
    not _ROOT_ENV.exists(),
    reason="Root .env unavailable for Postgres migration test",
)
def test_isolated_postgres_chunks_and_fts_migration_cycle() -> None:
    clear_settings_cache()
    db_cfg = get_settings().database
    password = db_cfg.password.get_secret_value()
    temp_db = f"ipkrh_mig_chunks_test_{uuid.uuid4().hex[:8]}"

    admin_dsn = f"postgresql://{db_cfg.user}:{password}@127.0.0.1:{db_cfg.port}/postgres"
    temp_url = (
        f"postgresql+psycopg://{db_cfg.user}:{password}"
        f"@127.0.0.1:{db_cfg.port}/{temp_db}?sslmode=disable"
    )

    with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
        admin_conn.execute(f'CREATE DATABASE "{temp_db}"')

    try:
        alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", temp_url)

        # 1. Start at Phase 2.4B (0005) and seed existing evidence row to verify preservation
        command.upgrade(cfg, "0005_source_integrations")
        seed_user_id = uuid.uuid4()
        seed_org_id = uuid.uuid4()
        seed_project_id = uuid.uuid4()
        seed_ev_id = uuid.uuid4()

        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO users (id, full_name, email, password_hash, status)
                        VALUES (
                            :id,
                            'Chunk Owner',
                            'chunk-owner@example.com',
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
                        VALUES (:id, 'Chunk Org', 'chunk-org', :uid, 'active')
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
                            :pid, :oid, 'Chunk Project', 'chunk-project', 'active', 'private',
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
                            :ext_id, 'architecture.pdf', :hash, 'project_members', 'extracted',
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
                        "hash": "d" * 64,
                    },
                )
        finally:
            engine.dispose()

        # 2. Upgrade to Phase 2.5 revision (0006)
        command.upgrade(cfg, "0006_evidence_chunks_and_fts")

        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())
            assert "evidence_chunks" in tables

            ev_cols = {col["name"] for col in inspector.get_columns("evidence_items")}
            assert {
                "indexing_status",
                "chunk_count",
                "indexed_at",
                "embedding_model",
                "index_version",
                "index_error_code",
                "index_error_message",
            }.issubset(ev_cols)

            chunk_indexes = {idx["name"] for idx in inspector.get_indexes("evidence_chunks")}
            assert "ix_evidence_chunks_search_vector" in chunk_indexes

            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0006_evidence_chunks_and_fts"
                )
                row = conn.execute(
                    text(
                        "SELECT title, indexing_status, chunk_count "
                        "FROM evidence_items WHERE id = :eid"
                    ),
                    {"eid": seed_ev_id},
                ).one()
                assert row[0] == "architecture.pdf"
                assert row[1] == "not_indexed"
                assert row[2] == 0

            pg_session_factory = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
                class_=Session,
            )
            with pg_session_factory() as session:
                ev = session.get(EvidenceItem, seed_ev_id)
                assert ev is not None
                job = BackgroundJob(
                    organisation_id=seed_org_id,
                    project_id=seed_project_id,
                    evidence_id=seed_ev_id,
                    triggered_by_user_id=seed_user_id,
                    job_type=BackgroundJobType.EVIDENCE_INDEXING.value,
                )
                chunk = EvidenceChunk(
                    organisation_id=seed_org_id,
                    project_id=seed_project_id,
                    evidence_id=seed_ev_id,
                    chunk_index=0,
                    chunk_type=EvidenceChunkType.DOCUMENT_SECTION.value,
                    section_title="Database Ownership",
                    page_number=1,
                    char_start=0,
                    char_end=48,
                    char_count=48,
                    token_estimate=15,
                    chunk_text="PostgreSQL stores canonical structured knowledge.",
                    chunk_content_hash="e" * 64,
                    search_identifier_text="NEX-142 PostgreSQL",
                    search_vector=func.to_tsvector(
                        "english",
                        "NEX-142 PostgreSQL stores canonical structured knowledge.",
                    ),
                    source_type="document_upload",
                    acl_scope="project_members",
                    metadata_json={"section_title": "Database Ownership"},
                )
                session.add_all([job, chunk])
                session.flush()

                # Unique constraint (evidence_id, chunk_index) prevents duplicates
                with pytest.raises(IntegrityError):
                    session.add(
                        EvidenceChunk(
                            organisation_id=seed_org_id,
                            project_id=seed_project_id,
                            evidence_id=seed_ev_id,
                            chunk_index=0,
                            chunk_type=EvidenceChunkType.DOCUMENT_SECTION.value,
                            char_start=0,
                            char_end=10,
                            char_count=10,
                            token_estimate=3,
                            chunk_text="Duplicate.",
                            chunk_content_hash="f" * 64,
                            search_identifier_text="",
                            source_type="document_upload",
                            acl_scope="project_members",
                            metadata_json={},
                        )
                    )
                    session.flush()
                session.rollback()
        finally:
            engine.dispose()

        # 3. Downgrade 0006 -> 0005 cleanly while preserving Phase 2.4A/2.4B evidence rows
        command.downgrade(cfg, "0005_source_integrations")
        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            inspector = inspect(engine)
            assert "evidence_chunks" not in set(inspector.get_table_names())
            ev_cols_after_down = {col["name"] for col in inspector.get_columns("evidence_items")}
            assert "indexing_status" not in ev_cols_after_down
            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0005_source_integrations"
                )
                assert (
                    conn.execute(
                        text("SELECT title FROM evidence_items WHERE id = :eid"),
                        {"eid": seed_ev_id},
                    ).scalar_one()
                    == "architecture.pdf"
                )
        finally:
            engine.dispose()

        # 4. Re-upgrade cleanly back to head and re-run alembic check
        command.upgrade(cfg, "head")
        command.check(cfg)
    finally:
        with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
            admin_conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (temp_db,),
            )
            admin_conn.execute(f'DROP DATABASE IF EXISTS "{temp_db}"')
