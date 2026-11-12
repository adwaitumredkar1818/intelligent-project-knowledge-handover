"""Isolated PostgreSQL migration tests for Phase 2.4B (`0005_source_integrations`)."""

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
from app.models.enums import IntegrationProvider
from app.models.integration import (
    ProjectSourceMapping,
    SourceAccessPolicy,
    SourceConnection,
    UserSourceAuthorisation,
)

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


@pytest.mark.skipif(
    not _ROOT_ENV.exists(),
    reason="Root .env unavailable for Postgres migration test",
)
def test_isolated_postgres_integrations_migration_cycle() -> None:
    clear_settings_cache()
    db_cfg = get_settings().database
    password = db_cfg.password.get_secret_value()
    temp_db = f"ipkrh_mig_int_test_{uuid.uuid4().hex[:8]}"

    admin_dsn = f"postgresql://{db_cfg.user}:{password}@127.0.0.1:{db_cfg.port}/postgres"
    temp_url = f"postgresql+psycopg://{db_cfg.user}:{password}@127.0.0.1:{db_cfg.port}/{temp_db}"

    with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
        admin_conn.execute(f'CREATE DATABASE "{temp_db}"')

    try:
        alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", temp_url)

        # 1. Start at Phase 2.4A and insert preserved upload evidence row
        command.upgrade(cfg, "0004_evidence_ingestion")
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
                            'Int Owner',
                            'int-owner@example.com',
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
                        VALUES (:id, 'Int Org', 'int-org', :uid, 'active')
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
                            :pid, :oid, 'Int Project', 'int-project', 'active', 'private',
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
                            :ext_id, 'spec.pdf', :hash, 'project_members', 'extracted',
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
                        "hash": "b" * 64,
                    },
                )
        finally:
            engine.dispose()

        # 2. Upgrade explicitly to 0005 revision cleanly
        command.upgrade(cfg, "0005_source_integrations")

        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            tables = set(inspect(engine).get_table_names())
            assert {
                "source_connections",
                "user_source_authorisations",
                "oauth_states",
                "source_access_policies",
                "project_source_mappings",
                "source_sync_runs",
            }.issubset(tables)

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
                    == "spec.pdf"
                )

            pg_session_factory = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
                class_=Session,
            )
            with pg_session_factory() as session:
                conn_row = SourceConnection(
                    organisation_id=seed_org_id,
                    provider=IntegrationProvider.GITHUB.value,
                    display_name="GitHub (@alice)",
                    created_by_user_id=seed_user_id,
                    status="active",
                )
                session.add(conn_row)
                session.flush()

                auth_row = UserSourceAuthorisation(
                    source_connection_id=conn_row.id,
                    organisation_id=seed_org_id,
                    user_id=seed_user_id,
                    provider=IntegrationProvider.GITHUB.value,
                    external_user_id="1001",
                    external_username="alice",
                    encrypted_access_token="v1:encrypted-only",
                    granted_scopes=["read:user"],
                )
                session.add(auth_row)
                session.flush()

                # Active uniqueness per (source_connection_id, user_id)
                with pytest.raises(IntegrityError):
                    session.add(
                        UserSourceAuthorisation(
                            source_connection_id=conn_row.id,
                            organisation_id=seed_org_id,
                            user_id=seed_user_id,
                            provider=IntegrationProvider.GITHUB.value,
                            external_user_id="1001",
                            encrypted_access_token="v1:dup",
                            granted_scopes=[],
                        )
                    )
                    session.flush()
                session.rollback()

                # Recreate inside fresh transaction for evidence FK & external unique index check
                conn_row = SourceConnection(
                    organisation_id=seed_org_id,
                    provider=IntegrationProvider.GITHUB.value,
                    display_name="GitHub (@alice)",
                    created_by_user_id=seed_user_id,
                    status="active",
                )
                session.add(conn_row)
                session.flush()

                policy = SourceAccessPolicy(
                    organisation_id=seed_org_id,
                    project_id=seed_project_id,
                    source_connection_id=conn_row.id,
                    provider=IntegrationProvider.GITHUB.value,
                    scope_identifier="github:repo:999",
                    allowed_user_ids=[str(seed_user_id)],
                    allowed_external_identities=[],
                )
                session.add(policy)
                session.flush()

                mapping = ProjectSourceMapping(
                    organisation_id=seed_org_id,
                    project_id=seed_project_id,
                    source_connection_id=conn_row.id,
                    source_access_policy_id=policy.id,
                    created_by_user_id=seed_user_id,
                    provider=IntegrationProvider.GITHUB.value,
                    resource_type="github_repository",
                    external_site_id="github.com",
                    external_resource_id="999",
                    external_resource_key="org/repo",
                    external_resource_name="repo",
                )
                session.add(mapping)
                session.flush()

                session.execute(
                    text(
                        """
                        INSERT INTO evidence_items (
                            id, organisation_id, project_id, uploaded_by_user_id,
                            source_type, source_provider, category, source_external_id,
                            source_url, source_author_identity, title, mime_type,
                            content_hash, acl_scope, processing_status, page_count,
                            ocr_pages_count, truncated_pages_count, metadata_json
                        )
                        VALUES (
                            :eid, :oid, :pid, :uid,
                            'github', 'github', 'issue', 'github:999:issue:1',
                            'https://github.com/org/repo/issues/1', 'alice', 'Issue 1',
                            'text/markdown', :hash, 'project_members', 'extracted',
                            1, 0, 0, '{"repo": "org/repo"}'::jsonb
                        )
                        """
                    ),
                    {
                        "eid": uuid.uuid4(),
                        "oid": seed_org_id,
                        "pid": seed_project_id,
                        "uid": seed_user_id,
                        "hash": "c" * 64,
                    },
                )
                session.commit()
                # Enforce active external ID uniqueness at 0005 schema level
                with pytest.raises(IntegrityError):
                    session.execute(
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
                                'github', 'github', 'issue', 'github:999:issue:1',
                                'Issue 1 Dup', :hash, 'project_members', 'extracted',
                                0, 0, '{}'::jsonb
                            )
                            """
                        ),
                        {
                            "eid": uuid.uuid4(),
                            "oid": seed_org_id,
                            "pid": seed_project_id,
                            "uid": seed_user_id,
                            "hash": "d" * 64,
                        },
                    )
                session.rollback()
        finally:
            engine.dispose()

        # 3. Downgrade 0005 -> 0004 cleanly while preserving upload row
        command.downgrade(cfg, "0004_evidence_ingestion")
        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            tables_after_down = set(inspect(engine).get_table_names())
            for dropped in (
                "source_sync_runs",
                "project_source_mappings",
                "source_access_policies",
                "oauth_states",
                "user_source_authorisations",
                "source_connections",
            ):
                assert dropped not in tables_after_down
            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0004_evidence_ingestion"
                )
                assert (
                    conn.execute(
                        text("SELECT title FROM evidence_items WHERE id = :eid"),
                        {"eid": seed_ev_id},
                    ).scalar_one()
                    == "spec.pdf"
                )
        finally:
            engine.dispose()

        # 4. Re-upgrade cleanly back to 0005 revision
        command.upgrade(cfg, "0005_source_integrations")
    finally:
        with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
            admin_conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (temp_db,),
            )
            admin_conn.execute(f'DROP DATABASE IF EXISTS "{temp_db}"')
