"""Isolated PostgreSQL migration upgrade, downgrade, check, and data-preservation tests."""

from __future__ import annotations

import uuid
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import clear_settings_cache, get_settings

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


@pytest.mark.skipif(
    not _ROOT_ENV.exists(),
    reason="Root .env unavailable for Postgres migration test",
)
def test_isolated_postgres_workspace_migration_upgrade_downgrade_cycle() -> None:
    clear_settings_cache()
    db_cfg = get_settings().database
    password = db_cfg.password.get_secret_value()
    temp_db = f"ipkrh_mig_ws_test_{uuid.uuid4().hex[:8]}"

    admin_dsn = f"postgresql://{db_cfg.user}:{password}@127.0.0.1:{db_cfg.port}/postgres"
    temp_url = f"postgresql+psycopg://{db_cfg.user}:{password}@127.0.0.1:{db_cfg.port}/{temp_db}"

    with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
        admin_conn.execute(f'CREATE DATABASE "{temp_db}"')

    try:
        alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", temp_url)

        # 1. Start at Phase 2.2 revision and insert a realistic user row to verify preservation
        command.upgrade(cfg, "0002_auth_identity_rbac")
        seed_user_id = uuid.uuid4()
        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO users (id, full_name, email, password_hash, status)
                        VALUES (
                            :id,
                            'Preserved User',
                            'preserved@example.com',
                            '$argon2id$v=19$m=65536,t=3,p=4$test$test',
                            'active'
                        )
                        """
                    ),
                    {"id": seed_user_id},
                )
        finally:
            engine.dispose()

        # 2. Upgrade to 0003 head and verify Alembic model-to-DB parity (`alembic check`)
        command.upgrade(cfg, "head")
        command.check(cfg)

        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            tables = set(inspect(engine).get_table_names())
            assert {
                "alembic_version",
                "users",
                "roles",
                "permissions",
                "role_permissions",
                "user_roles",
                "refresh_sessions",
                "organisations",
                "organisation_memberships",
                "organisation_invitations",
                "projects",
                "project_memberships",
                "audit_logs",
            }.issubset(tables)

            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0003_org_project_workspaces"
                )
                assert conn.execute(text("SELECT count(*) FROM roles")).scalar_one() == 8
                assert conn.execute(text("SELECT count(*) FROM permissions")).scalar_one() == 23
                assert (
                    conn.execute(text("SELECT count(*) FROM role_permissions")).scalar_one()
                    == 49
                )
                preserved = conn.execute(
                    text("SELECT email FROM users WHERE id = :id"),
                    {"id": seed_user_id},
                ).scalar_one()
                assert preserved == "preserved@example.com"
        finally:
            engine.dispose()

        # 3. Downgrade 0003 -> 0002 cleanly while preserving existing 0002 auth & RBAC records
        command.downgrade(cfg, "0002_auth_identity_rbac")
        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            tables_after_down = set(inspect(engine).get_table_names())
            for dropped in (
                "organisations",
                "organisation_memberships",
                "organisation_invitations",
                "projects",
                "project_memberships",
                "audit_logs",
            ):
                assert dropped not in tables_after_down
            assert "users" in tables_after_down
            assert "roles" in tables_after_down
            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0002_auth_identity_rbac"
                )
                assert conn.execute(text("SELECT count(*) FROM roles")).scalar_one() == 7
                assert conn.execute(text("SELECT count(*) FROM permissions")).scalar_one() == 15
                assert (
                    conn.execute(
                        text("SELECT email FROM users WHERE id = :id"),
                        {"id": seed_user_id},
                    ).scalar_one()
                    == "preserved@example.com"
                )
        finally:
            engine.dispose()

        # 4. Re-upgrade back to 0003 head cleanly
        command.upgrade(cfg, "head")
        command.check(cfg)
    finally:
        with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
            admin_conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (temp_db,),
            )
            admin_conn.execute(f'DROP DATABASE IF EXISTS "{temp_db}"')
