"""Tests for database engine configuration, session lifecycle, and Alembic wiring."""

from __future__ import annotations

import logging
from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.db.base import NAMING_CONVENTION, Base
from app.db.session import build_db_connect_args, create_db_engine, session_scope
from app.models import Base as ModelsBase
from app.repositories.system import SystemRepository
from tests.conftest import build_test_settings


def test_db_engine_and_models_metadata_wiring() -> None:
    assert ModelsBase is Base
    assert "pk" in NAMING_CONVENTION
    assert "fk" in NAMING_CONVENTION

    settings = build_test_settings(postgres_ssl_mode="require")
    assert build_db_connect_args(settings) == {
        "connect_timeout": 5,
        "sslmode": "require",
    }
    assert build_db_connect_args(
        settings,
        "postgresql+psycopg://postgres:secret@localhost:5432/db?sslmode=disable&connect_timeout=9",
    ) == {}
    assert build_db_connect_args(settings, "sqlite:///:memory:") == {}

    engine = create_db_engine(settings)
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
    finally:
        engine.dispose()


def test_get_db_session_closes_and_rolls_back_on_exception() -> None:
    session = MagicMock()
    factory = MagicMock(return_value=session)
    fake_request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(session_factory=factory))
    )

    gen = get_db_session(fake_request)  # type: ignore[arg-type]
    yielded = next(gen)
    assert yielded is session
    with pytest.raises(StopIteration):
        next(gen)
    session.rollback.assert_not_called()
    session.close.assert_called_once()

    err_session = MagicMock()
    err_factory = MagicMock(return_value=err_session)
    err_request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(session_factory=err_factory))
    )
    err_gen = cast(
        Generator[Session, None, None],
        get_db_session(err_request),  # type: ignore[arg-type]
    )
    next(err_gen)
    with pytest.raises(RuntimeError, match="boom"):
        err_gen.throw(RuntimeError("boom"))
    err_session.rollback.assert_called_once()
    err_session.close.assert_called_once()


def test_session_scope_rolls_back_on_error() -> None:
    session = MagicMock()
    factory = MagicMock(return_value=session)

    with session_scope(factory) as s:
        assert s is session
    session.rollback.assert_not_called()
    session.close.assert_called_once()

    err_session = MagicMock()
    err_factory = MagicMock(return_value=err_session)
    with pytest.raises(ValueError, match="fail"), session_scope(err_factory):
        raise ValueError("fail")
    err_session.rollback.assert_called_once()
    err_session.close.assert_called_once()


def test_system_repository_ping_redacts_failure(caplog: pytest.LogCaptureFixture) -> None:
    failing_session = MagicMock()
    failing_session.execute.side_effect = SQLAlchemyError(
        "postgresql+psycopg://postgres:secret@localhost:5432/db failed"
    )
    repo = SystemRepository(failing_session)

    with caplog.at_level(logging.WARNING):
        ok, latency = repo.ping()

    assert ok is False
    assert latency is None
    assert "secret" not in caplog.text


def test_alembic_configuration_and_revisions() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    ini_path = backend_dir / "alembic.ini"
    assert ini_path.exists()

    cfg = Config(str(ini_path))
    script_dir = ScriptDirectory.from_config(cfg)
    heads = script_dir.get_heads()
    assert heads == ["0010_knowledge_domains"]
    revisions = [rev.revision for rev in script_dir.walk_revisions()]
    assert revisions == [
        "0010_knowledge_domains",
        "0009_supabase_and_vector_indexes",
        "0008_project_transitions_rbac",
        "0007_knowledge_reconstruction",
        "0006_evidence_chunks_and_fts",
        "0005_source_integrations",
        "0004_evidence_ingestion",
        "0003_org_project_workspaces",
        "0002_auth_identity_rbac",
        "0001_initial_baseline",
    ]
