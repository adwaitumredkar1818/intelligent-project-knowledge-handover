"""Isolated PostgreSQL migration upgrade, downgrade, and constraint verification."""

from __future__ import annotations

import uuid
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import clear_settings_cache, get_settings
from tests.migration_guard import validate_url_isolation, verify_migration_target_isolation

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


@pytest.mark.skipif(
    not _ROOT_ENV.exists(),
    reason="Root .env unavailable for Postgres migration test",
)
def test_isolated_postgres_auth_migration_upgrade_downgrade_cycle() -> None:
    clear_settings_cache()
    db_cfg = get_settings().database
    password = db_cfg.password.get_secret_value()
    temp_db = f"ipkrh_mig_test_{uuid.uuid4().hex[:8]}"

    admin_dsn = (
        f"postgresql://{db_cfg.user}:{password}@127.0.0.1:{db_cfg.port}/postgres"
    )
    temp_url = (
        f"postgresql+psycopg://{db_cfg.user}:{password}"
        f"@127.0.0.1:{db_cfg.port}/{temp_db}?sslmode=disable"
    )

    # Enforce static URL isolation guard
    validate_url_isolation(admin_dsn)
    validate_url_isolation(temp_url)

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

        # 1. Apply 0001 -> 0002 in clean isolated database
        command.upgrade(cfg, "0002_auth_identity_rbac")

        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            verify_migration_target_isolation(temp_url, conn)
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
            }.issubset(tables)

            with engine.connect() as conn:
                rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                assert rev == "0002_auth_identity_rbac"
                role_rows = conn.execute(
                    text("SELECT name, scope_type FROM roles")
                ).fetchall()
                assert len(role_rows) == 7
                perm_count = conn.execute(text("SELECT count(*) FROM permissions")).scalar_one()
                assert perm_count == 15
        finally:
            engine.dispose()

        # 2. Downgrade cleanly to Phase 2.1 baseline 0001_initial_baseline
        command.downgrade(cfg, "0001_initial_baseline")
        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        try:
            tables_after_down = set(inspect(engine).get_table_names())
            assert "users" not in tables_after_down
            assert "refresh_sessions" not in tables_after_down
            assert "roles" not in tables_after_down
            with engine.connect() as conn:
                rev_down = conn.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                assert rev_down == "0001_initial_baseline"
        finally:
            engine.dispose()

        # 3. Re-upgrade back to 0002 cleanly
        command.upgrade(cfg, "0002_auth_identity_rbac")
    finally:
        with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
            admin_conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (temp_db,),
            )
            admin_conn.execute(f'DROP DATABASE IF EXISTS "{temp_db}"')
