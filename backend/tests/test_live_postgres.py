"""Read-only live PostgreSQL and readiness connectivity test using root `.env`."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import clear_settings_cache, get_settings
from app.db.session import create_db_engine, verify_database_connection
from app.main import create_app

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


@pytest.mark.skipif(not _ROOT_ENV.exists(), reason="Root .env unavailable for live DB check")
def test_live_postgresql_connectivity_and_readiness_readonly() -> None:
    clear_settings_cache()
    settings = get_settings()
    engine = create_db_engine(settings)
    try:
        latency_ms = verify_database_connection(engine)
        assert latency_ms >= 0.0

        with engine.connect() as conn:
            rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            assert rev == "0002_auth_identity_rbac"
            role_count = conn.execute(text("SELECT count(*) FROM roles")).scalar_one()
            assert role_count >= 7
    finally:
        engine.dispose()

    app = create_app(settings)
    with TestClient(app) as client:
        liveness = client.get("/health")
        assert liveness.status_code == 200
        assert liveness.json()["status"] == "ok"

        v1_liveness = client.get("/api/v1/health")
        assert v1_liveness.status_code == 200

        readiness = client.get("/health/ready")
        assert readiness.status_code == 200
        body = readiness.json()
        assert body["database"]["status"] == "ok"
        assert body["status"] in {"ready", "degraded"}
