"""Isolated PostgreSQL migration tests for Phase 2.4A (`0004_evidence_ingestion`)."""

from __future__ import annotations

import uuid
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import clear_settings_cache, get_settings
from app.core.security import utc_now
from app.models.enums import (
    BackgroundJobStatus,
    BackgroundJobType,
)
from app.repositories.job import BackgroundJobRepository

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


@pytest.mark.skipif(
    not _ROOT_ENV.exists(),
    reason="Root .env unavailable for Postgres migration test",
)
def test_isolated_postgres_evidence_migration_upgrade_downgrade_cycle() -> None:
    clear_settings_cache()
    db_cfg = get_settings().database
    password = db_cfg.password.get_secret_value()
    temp_db = f"ipkrh_mig_ev_test_{uuid.uuid4().hex[:8]}"

    admin_dsn = f"postgresql://{db_cfg.user}:{password}@127.0.0.1:{db_cfg.port}/postgres"
    temp_url = f"postgresql+psycopg://{db_cfg.user}:{password}@127.0.0.1:{db_cfg.port}/{temp_db}"

    with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
        admin_conn.execute(f'CREATE DATABASE "{temp_db}"')

    try:
        alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", temp_url)

        # 1. Start at Phase 2.3 and insert realistic user/org/project records for preservation
        command.upgrade(cfg, "0003_org_project_workspaces")
        seed_user_id = uuid.uuid4()
        seed_org_id = uuid.uuid4()
        seed_project_id = uuid.uuid4()
        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO users (id, full_name, email, password_hash, status)
                        VALUES (
                            :id,
                            'Evidence Owner',
                            'ev-owner@example.com',
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
                        VALUES (:id, 'Mig Org', 'mig-org', :uid, 'active')
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
                            :pid, :oid, 'Mig Project', 'mig-project', 'active', 'private',
                            :uid, :uid
                        )
                        """
                    ),
                    {"pid": seed_project_id, "oid": seed_org_id, "uid": seed_user_id},
                )
        finally:
            engine.dispose()

        # 2. Upgrade specifically to 0004 revision cleanly
        command.upgrade(cfg, "0004_evidence_ingestion")

        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            tables = set(inspect(engine).get_table_names())
            assert {
                "evidence_items",
                "evidence_contents",
                "evidence_page_contents",
                "background_jobs",
            }.issubset(tables)

            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0004_evidence_ingestion"
                )
                assert (
                    conn.execute(
                        text("SELECT slug FROM projects WHERE id = :pid"),
                        {"pid": seed_project_id},
                    ).scalar_one()
                    == "mig-project"
                )

            # Verify partial unique index & PostgreSQL FOR UPDATE SKIP LOCKED job claiming
            pg_session_factory = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
                class_=Session,
            )
            test_hash = "a" * 64
            ev_id = uuid.uuid4()
            with pg_session_factory() as pg_session:
                job_repo = BackgroundJobRepository(pg_session)
                pg_session.execute(
                    text(
                        """
                        INSERT INTO evidence_items (
                            id, organisation_id, project_id, uploaded_by_user_id,
                            source_type, source_provider, category, source_external_id,
                            source_author_identity, title, original_filename, mime_type,
                            file_size_bytes, content_hash, storage_provider, storage_object_key,
                            encryption_algorithm, encryption_key_id, acl_scope,
                            processing_status, page_count, ocr_pages_count, truncated_pages_count,
                            metadata_json
                        )
                        VALUES (
                            :eid, :oid, :pid, :uid,
                            'document_upload', 'local_upload', 'pdf_document',
                            'upload:mig-test', 'ev-owner@example.com', 'mig.pdf', 'mig.pdf',
                            'application/pdf', 128, :hash, 'local_encrypted', :skey,
                            'AES-256-GCM', 'local-v1', 'project_members',
                            'queued', 1, 0, 0, '{"document_format": "pdf"}'::jsonb
                        )
                        """
                    ),
                    {
                        "eid": ev_id,
                        "oid": seed_org_id,
                        "pid": seed_project_id,
                        "uid": seed_user_id,
                        "hash": test_hash,
                        "skey": f"{seed_org_id}/{seed_project_id}/{uuid.uuid4()}.enc",
                    },
                )
                job = job_repo.create_job(
                    organisation_id=seed_org_id,
                    project_id=seed_project_id,
                    evidence_id=ev_id,
                    triggered_by_user_id=seed_user_id,
                    job_type=BackgroundJobType.DOCUMENT_INGESTION.value,
                )
                pg_session.commit()

                with pytest.raises(IntegrityError):
                    pg_session.execute(
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
                                'upload:mig-dup', 'dup.pdf', :hash, 'project_members',
                                'queued', 0, 0, '{}'::jsonb
                            )
                            """
                        ),
                        {
                            "eid": uuid.uuid4(),
                            "oid": seed_org_id,
                            "pid": seed_project_id,
                            "uid": seed_user_id,
                            "hash": test_hash,
                        },
                    )
                    pg_session.flush()
                pg_session.rollback()

                claimed = job_repo.claim_next_job(
                    worker_id="pg-mig-worker",
                    lease_seconds=60,
                    now=utc_now(),
                    job_type=BackgroundJobType.DOCUMENT_INGESTION.value,
                )
                assert claimed is not None
                assert claimed.id == job.id
                assert claimed.status == BackgroundJobStatus.RUNNING.value
                assert claimed.attempt_count == 1
                pg_session.commit()
        finally:
            engine.dispose()

        # 3. Downgrade 0004 -> 0003 cleanly while preserving existing 0003 workspace records
        command.downgrade(cfg, "0003_org_project_workspaces")
        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            tables_after_down = set(inspect(engine).get_table_names())
            for dropped in (
                "background_jobs",
                "evidence_page_contents",
                "evidence_contents",
                "evidence_items",
            ):
                assert dropped not in tables_after_down

            assert "projects" in tables_after_down
            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0003_org_project_workspaces"
                )
                assert (
                    conn.execute(
                        text("SELECT slug FROM projects WHERE id = :pid"),
                        {"pid": seed_project_id},
                    ).scalar_one()
                    == "mig-project"
                )
        finally:
            engine.dispose()

        # 4. Re-upgrade back to 0004 cleanly
        command.upgrade(cfg, "0004_evidence_ingestion")
    finally:
        with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
            admin_conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (temp_db,),
            )
            admin_conn.execute(f'DROP DATABASE IF EXISTS "{temp_db}"')
