"""Tests for the fail-closed migration test isolation guard."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.migration_guard import (
    DatabaseIdentity,
    DatabaseIsolationError,
    inspect_live_database_identity,
    validate_server_identity_isolation,
    validate_url_isolation,
    verify_migration_target_isolation,
)


def test_guard_accepts_approved_local_hostnames() -> None:
    """Verify that all approved local host configurations pass static validation."""
    approved_urls = [
        "postgresql+psycopg://postgres:secret@localhost:5432/knowledge_handover",
        "postgresql+psycopg://postgres:secret@127.0.0.1:5432/test_db",
        "postgresql+psycopg://postgres:secret@[::1]:5432/test_db",
        "postgresql+psycopg://postgres:secret@ipkrh-postgres:5432/knowledge_handover",
    ]
    for url in approved_urls:
        validate_url_isolation(url)


def test_guard_rejects_production_supabase_project() -> None:
    """Verify that any connection referencing the production Supabase project is rejected."""
    poisoned_urls = [
        "postgresql+psycopg://postgres.rjntmboskzyrsqcetzil:secret@localhost:5432/postgres",
        "postgresql+psycopg://postgres:secret@rjntmboskzyrsqcetzil.supabase.co:5432/postgres",
        "postgresql+psycopg://admin:secret@127.0.0.1:5432/rjntmboskzyrsqcetzil",
    ]
    for url in poisoned_urls:
        with pytest.raises(DatabaseIsolationError) as exc_info:
            validate_url_isolation(url)
        assert "production project identifier" in str(exc_info.value).lower()
        # Verify credentials/passwords are NOT printed
        assert "secret" not in str(exc_info.value)


def test_guard_rejects_supabase_session_pooler() -> None:
    """Verify that connections to Supabase Pooler hosts are rejected."""
    pooler_urls = [
        "postgresql+psycopg://postgres.rjntmboskzyrsqcetzil:pass@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres",
        "postgresql+psycopg://postgres:pass@pooler.supabase.com:5432/postgres",
        "postgresql+psycopg://postgres:pass@db.rjntmboskzyrsqcetzil.supabase.co:5432/postgres",
    ]
    for url in pooler_urls:
        with pytest.raises(DatabaseIsolationError) as exc_info:
            validate_url_isolation(url)
        assert "forbidden" in str(exc_info.value).lower()
        assert "pass" not in str(exc_info.value)


def test_guard_rejects_unknown_external_hosts() -> None:
    """Verify that arbitrary external database endpoints are rejected."""
    external_urls = [
        "postgresql+psycopg://postgres:pass@db.example.com:5432/test",
        "postgresql+psycopg://postgres:pass@198.51.100.25:5432/test",
        "postgresql+psycopg://postgres:pass@production-database.internal:5432/test",
        "postgresql+psycopg://postgres:pass@postgres.rds.amazonaws.com:5432/test",
    ]
    for url in external_urls:
        with pytest.raises(DatabaseIsolationError) as exc_info:
            validate_url_isolation(url)
        err_msg = str(exc_info.value).lower()
        assert "not in approved local test hosts" in err_msg or "matches forbidden" in err_msg
        assert "pass" not in str(exc_info.value)


def test_guard_rejects_missing_database_identity() -> None:
    """Verify that missing host or incomplete server identity fails closed."""
    # 1. Missing host in URL
    with pytest.raises(DatabaseIsolationError) as exc_info:
        validate_url_isolation("postgresql+psycopg:///missing_host_db")
    assert "hostname is empty or undefined" in str(exc_info.value)

    # 2. Database catalog returns None or empty
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = None

    with pytest.raises(DatabaseIsolationError) as exc_info:
        inspect_live_database_identity(mock_conn)
    assert "incomplete identity metadata" in str(exc_info.value)

    # 3. Database catalog returns NULL for essential fields
    mock_conn.execute.return_value.fetchone.return_value = (
        None, None, "127.0.0.1", 5432, "PostgreSQL 17"
    )
    with pytest.raises(DatabaseIsolationError) as exc_info:
        inspect_live_database_identity(mock_conn)
    assert "incomplete identity metadata" in str(exc_info.value)


def test_guard_rejects_malformed_connection_configuration() -> None:
    """Verify that malformed or non-string URLs are rejected safely."""
    for malformed in ["", None, "   ", 12345, "not_a_valid_url:::"]:
        with pytest.raises(DatabaseIsolationError) as exc_info:
            validate_url_isolation(malformed)  # type: ignore[arg-type]
        assert "malformed" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()


def test_guard_anti_bypass_server_identity_verification() -> None:
    """Verify that DNS spoofing or localhost aliasing cannot bypass IP inspection."""
    # Scenario: Hostname is set to "localhost", but the server identity resolves to an external IP
    spoofed_identity = DatabaseIdentity(
        current_database="postgres",
        current_user="postgres",
        server_addr="52.65.247.42",  # AWS Sydney IP
        server_port=5432,
        version="PostgreSQL 17.11",
    )

    with pytest.raises(DatabaseIsolationError) as exc_info:
        validate_server_identity_isolation(spoofed_identity)
    assert "non-local address '52.65.247.42'" in str(exc_info.value)

    # Scenario: Server reports username with production project ref
    project_identity = DatabaseIdentity(
        current_database="knowledge_handover",
        current_user="postgres.rjntmboskzyrsqcetzil",
        server_addr="127.0.0.1",
        server_port=5432,
        version="PostgreSQL 16.15",
    )
    with pytest.raises(DatabaseIsolationError) as exc_info:
        validate_server_identity_isolation(project_identity)
    assert "production project identifier" in str(exc_info.value).lower()


def test_guard_accepts_valid_docker_and_loopback_identities() -> None:
    """Verify that legitimate loopback and Docker bridge identities are accepted."""
    # Loopback IP
    local_identity = DatabaseIdentity(
        current_database="knowledge_handover",
        current_user="postgres",
        server_addr="127.0.0.1",
        server_port=5432,
        version="PostgreSQL 16.15",
    )
    validate_server_identity_isolation(local_identity)

    # Docker bridge network IP (172.18.0.3)
    docker_identity = DatabaseIdentity(
        current_database="knowledge_handover",
        current_user="postgres",
        server_addr="172.18.0.3",
        server_port=5432,
        version="PostgreSQL 16.15",
    )
    validate_server_identity_isolation(docker_identity)

    # Unix domain socket (server_addr is None)
    unix_socket_identity = DatabaseIdentity(
        current_database="knowledge_handover",
        current_user="postgres",
        server_addr=None,
        server_port=5432,
        version="PostgreSQL 16.15",
    )
    validate_server_identity_isolation(unix_socket_identity)


def test_verify_migration_target_isolation_end_to_end_mock() -> None:
    """Verify end-to-end function with safe URL and mock connection."""
    safe_url = "postgresql+psycopg://postgres:secret@127.0.0.1:5432/knowledge_handover"
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = (
        "knowledge_handover",
        "postgres",
        "127.0.0.1",
        5432,
        "PostgreSQL 16.15",
    )

    identity = verify_migration_target_isolation(safe_url, mock_conn)
    assert identity is not None
    assert identity.current_database == "knowledge_handover"
    assert identity.current_user == "postgres"
    assert identity.server_addr == "127.0.0.1"


def test_guard_rejects_unsafe_target_on_live_inspection() -> None:
    """Verify that an unsafe server identity causes isolation check to fail closed."""
    safe_url = "postgresql+psycopg://postgres:secret@127.0.0.1:5432/knowledge_handover"
    mock_conn = MagicMock()
    # Mocking server_addr resolving to public IP despite localhost in URL
    mock_conn.execute.return_value.fetchone.return_value = (
        "knowledge_handover",
        "postgres",
        "54.252.123.45",  # Remote AWS IP
        5432,
        "PostgreSQL 17.11",
    )
    with pytest.raises(DatabaseIsolationError) as exc_info:
        verify_migration_target_isolation(safe_url, mock_conn)
    assert "non-local address" in str(exc_info.value).lower()
