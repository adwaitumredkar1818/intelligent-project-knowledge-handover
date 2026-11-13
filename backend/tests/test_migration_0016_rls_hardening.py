"""Automated unit and controlled rollback-only tests for migration 0016 (RLS Hardening)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.core.config import get_settings
from app.db.session import create_db_engine

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_INI = _PROJECT_ROOT / "backend" / "alembic.ini"
_MIGRATION_PATH = (
    _PROJECT_ROOT
    / "infrastructure"
    / "database"
    / "migrations"
    / "versions"
    / "20261113_0016_rls_hardening.py"
)


def _load_migration_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0016", _MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load migration module from {_MIGRATION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_0016_metadata_and_revision_chain() -> None:
    """Verify revision chain, down_revision, and 61-table coverage."""
    mod = _load_migration_module()
    assert mod.revision == "0016_rls_hardening"
    assert mod.down_revision == "0015_assistant_workspace"
    tables = mod._ALL_PUBLIC_BASE_TABLES
    assert len(tables) == 61
    assert len(set(tables)) == 61

    # Verify key canonical tables are explicitly present
    assert "users" in tables
    assert "organisations" in tables
    assert "projects" in tables
    assert "evidence_items" in tables
    assert "knowledge_items" in tables
    assert "verification_cases" in tables
    assert "handover_packages" in tables
    assert "assistant_conversations" in tables
    assert "audit_logs" in tables
    assert "alembic_version" in tables


def test_migration_0016_offline_sql_generation_contract(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify offline SQL generation generates exactly 61 ENABLE and 61 DISABLE statements."""
    mod = _load_migration_module()
    tables = mod._ALL_PUBLIC_BASE_TABLES
    alembic_cfg = Config(str(_ALEMBIC_INI))

    # Capture upgrade --sql output via capsys
    command.upgrade(alembic_cfg, "0015_assistant_workspace:0016_rls_hardening", sql=True)
    captured_upgrade = capsys.readouterr()
    upgrade_sql = captured_upgrade.out

    for table in tables:
        assert f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;' in upgrade_sql

    # Assert no permissive policies or FORCE RLS in upgrade SQL
    assert "CREATE POLICY" not in upgrade_sql
    assert "FORCE ROW LEVEL SECURITY" not in upgrade_sql

    # Capture downgrade --sql output via capsys
    command.downgrade(alembic_cfg, "0016_rls_hardening:0015_assistant_workspace", sql=True)
    captured_downgrade = capsys.readouterr()
    downgrade_sql = captured_downgrade.out

    for table in tables:
        assert f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY;' in downgrade_sql


def test_migration_0016_isolated_rls_engine_behavior() -> None:
    """Verify PostgreSQL RLS engine semantics on an isolated test table in live database session."""
    settings = get_settings()
    engine = create_db_engine(settings)

    try:
        with engine.connect() as conn:
            # 1. Verify connection and inspect that all 56 expected tables exist in schema
            inspector = inspect(conn)
            public_tables = set(inspector.get_table_names(schema="public"))
            mod = _load_migration_module()
            for t in mod._ALL_PUBLIC_BASE_TABLES:
                assert t in public_tables, f"Expected table {t} missing from public schema"

            # Rollback any autobegun transaction from inspection
            conn.rollback()

            # 2. Test RLS semantics on an isolated temp table (avoids locking shared tables)
            with conn.begin() as trans:
                try:
                    conn.execute(text(
                        "CREATE TEMPORARY TABLE _test_rls_semantics (id int, val text);"
                    ))
                    conn.execute(text("INSERT INTO _test_rls_semantics VALUES (1, 'secret');"))

                    # Enable RLS
                    conn.execute(text("ALTER TABLE _test_rls_semantics ENABLE ROW LEVEL SECURITY;"))

                    # Check relrowsecurity is True
                    res = conn.execute(text("""
                        SELECT c.relrowsecurity 
                        FROM pg_class c 
                        WHERE c.relname = '_test_rls_semantics';
                    """)).scalar_one()
                    assert res is True

                    # Verify postgres user (holding BYPASSRLS) can still read
                    stmt = text("SELECT val FROM _test_rls_semantics WHERE id = 1")
                    val = conn.execute(stmt).scalar_one()
                    assert val == "secret"

                    # Disable RLS (downgrade verification)
                    conn.execute(text(
                        "ALTER TABLE _test_rls_semantics DISABLE ROW LEVEL SECURITY;"
                    ))
                    res_disabled = conn.execute(text("""
                        SELECT c.relrowsecurity 
                        FROM pg_class c 
                        WHERE c.relname = '_test_rls_semantics';
                    """)).scalar_one()
                    assert res_disabled is False

                finally:
                    trans.rollback()
    finally:
        engine.dispose()
