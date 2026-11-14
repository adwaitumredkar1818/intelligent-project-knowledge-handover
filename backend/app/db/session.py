"""SQLAlchemy 2.x + Psycopg 3 engine and session lifecycle management."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import parse_qs, urlparse

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings

logger = logging.getLogger(__name__)


def build_db_connect_args(
    settings: Settings,
    raw_url: str | None = None,
) -> dict[str, Any]:
    """Build Psycopg connect_args matching database timeout and SSL settings."""
    db_cfg = settings.database
    target_url = raw_url or db_cfg.sqlalchemy_url()
    parsed = urlparse(target_url)
    if not parsed.scheme.startswith("postgresql"):
        return {}

    query_params = parse_qs(parsed.query)
    connect_args: dict[str, Any] = {}
    if "connect_timeout" not in query_params:
        connect_args["connect_timeout"] = db_cfg.connect_timeout_seconds
    if "sslmode" not in query_params:
        connect_args["sslmode"] = db_cfg.ssl_mode
    if "prepare_threshold" not in query_params:
        # Supabase transaction pooler (port 6543) requires disabling statement preparation
        if parsed.port == 6543 or "pooler" in (parsed.hostname or ""):
            connect_args["prepare_threshold"] = None
    return connect_args


def create_db_engine(settings: Settings) -> Engine:
    """Create a configured PostgreSQL SQLAlchemy engine using Psycopg 3."""
    raw_url = settings.database.sqlalchemy_url()
    connect_args = build_db_connect_args(settings, raw_url)

    return create_engine(
        raw_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        connect_args=connect_args,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a synchronous SQLAlchemy 2.x session factory bound to an engine."""
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )


def verify_database_connection(engine: Engine) -> float:
    """Verify PostgreSQL connectivity via SELECT 1 and return latency in milliseconds."""
    started_at = time.perf_counter()
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return round((time.perf_counter() - started_at) * 1000.0, 2)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional session scope with automatic rollback on failure."""
    session = session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
