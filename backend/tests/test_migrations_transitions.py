"""Isolated PostgreSQL migration tests for `0008_project_transitions_rbac`."""

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
from app.models.project import ProjectTransition

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


@pytest.mark.skipif(
    not _ROOT_ENV.exists(),
    reason="Root .env unavailable for Postgres migration test",
)
def test_isolated_postgres_transitions_migration_cycle() -> None:
    clear_settings_cache()
    db_cfg = get_settings().database
    password = db_cfg.password.get_secret_value()
    temp_db = f"ipkrh_mig_trans_test_{uuid.uuid4().hex[:8]}"

    admin_dsn = f"postgresql://{db_cfg.user}:{password}@127.0.0.1:{db_cfg.port}/postgres"
    temp_url = (
        f"postgresql+psycopg://{db_cfg.user}:{password}"
        f"@127.0.0.1:{db_cfg.port}/{temp_db}?sslmode=disable"
    )

    try:
        admin_conn = psycopg.connect(admin_dsn, autocommit=True, connect_timeout=2)
    except (psycopg.OperationalError, psycopg.errors.ConnectionTimeout):
        pytest.skip("PostgreSQL offline; skipping isolated live database migration test")

    with admin_conn:
        admin_conn.execute(f'CREATE DATABASE "{temp_db}"')

    try:
        alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", temp_url)

        # 1. Start at 0007 and seed realistic users, org, project, and membership
        command.upgrade(cfg, "0007_knowledge_reconstruction")
        seed_owner_id = uuid.uuid4()
        seed_successor_id = uuid.uuid4()
        seed_org_id = uuid.uuid4()
        seed_project_id = uuid.uuid4()
        seed_membership_id = uuid.uuid4()

        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            with engine.begin() as conn:
                for uid, name, email in (
                    (seed_owner_id, "Owner User", "owner@example.com"),
                    (seed_successor_id, "Successor User", "successor@example.com"),
                ):
                    conn.execute(
                        text(
                            """
                            INSERT INTO users (id, full_name, email, password_hash, status)
                            VALUES (
                                :id, :name, :email,
                                '$argon2id$v=19$m=65536,t=3,p=4$test$test', 'active'
                            )
                            """
                        ),
                        {"id": uid, "name": name, "email": email},
                    )
                conn.execute(
                    text(
                        """
                        INSERT INTO organisations (id, name, slug, created_by_id, status)
                        VALUES (:oid, 'Mig Org', 'mig-org', :uid, 'active')
                        """
                    ),
                    {"oid": seed_org_id, "uid": seed_owner_id},
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO projects (
                            id, organisation_id, name, slug, status, visibility,
                            created_by_id, owner_id
                        )
                        VALUES (
                            :pid, :oid, 'Mig Project', 'mig-proj',
                            'active', 'private', :uid, :uid
                        )
                        """
                    ),
                    {"pid": seed_project_id, "oid": seed_org_id, "uid": seed_owner_id},
                )
                pm_role_id = conn.execute(
                    text("SELECT id FROM roles WHERE name = 'project_manager'")
                ).scalar_one()
                conn.execute(
                    text(
                        """
                        INSERT INTO project_memberships (
                            id, project_id, user_id, role_id, status
                        )
                        VALUES (:mid, :pid, :uid, :rid, 'active')
                        """
                    ),
                    {
                        "mid": seed_membership_id,
                        "pid": seed_project_id,
                        "uid": seed_owner_id,
                        "rid": pm_role_id,
                    },
                )
                perm_count_0007 = conn.execute(
                    text("SELECT count(*) FROM permissions")
                ).scalar_one()
        finally:
            engine.dispose()

        # 2. Upgrade to head (0008) and verify zero Alembic schema drift
        command.upgrade(cfg, "head")
        command.check(cfg)

        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            inspector = inspect(engine)
            assert "project_transitions" in set(inspector.get_table_names())
            pm_cols = {c["name"] for c in inspector.get_columns("project_memberships")}
            assert "responsibility_description" in pm_cols

            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0008_project_transitions_rbac"
                )
                perm_count_0008 = conn.execute(
                    text("SELECT count(*) FROM permissions")
                ).scalar_one()
                assert int(perm_count_0008) == int(perm_count_0007) + 5

            pg_session_factory = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
                class_=Session,
            )
            with pg_session_factory() as session:
                transition = ProjectTransition(
                    project_id=seed_project_id,
                    departing_user_id=seed_owner_id,
                    successor_user_id=seed_successor_id,
                    workflow_stage="planning",
                    handover_scope="Transfer core service ownership.",
                    source_scope={"providers": ["github", "pdf"]},
                )
                session.add(transition)
                session.commit()

                # Self-transition must violate CHECK constraint
                with pytest.raises(IntegrityError):
                    session.add(
                        ProjectTransition(
                            project_id=seed_project_id,
                            departing_user_id=seed_owner_id,
                            successor_user_id=seed_owner_id,
                            workflow_stage="planning",
                        )
                    )
                    session.flush()
                session.rollback()
        finally:
            engine.dispose()

        # 3. Downgrade 0008 -> 0007 cleanly while preserving pre-existing data
        command.downgrade(cfg, "0007_knowledge_reconstruction")
        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            inspector = inspect(engine)
            assert "project_transitions" not in set(inspector.get_table_names())
            pm_cols_down = {c["name"] for c in inspector.get_columns("project_memberships")}
            assert "responsibility_description" not in pm_cols_down
            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0007_knowledge_reconstruction"
                )
                perm_count_down = conn.execute(
                    text("SELECT count(*) FROM permissions")
                ).scalar_one()
                assert int(perm_count_down) == int(perm_count_0007)
                proj_name = conn.execute(
                    text("SELECT name FROM projects WHERE id = :pid"),
                    {"pid": seed_project_id},
                ).scalar_one()
                assert proj_name == "Mig Project"
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

