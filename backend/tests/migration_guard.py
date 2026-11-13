"""Fail-closed migration test connection guard.

Permanently enforces that migration, DDL, and database lifecycle tests
execute exclusively against local containerized PostgreSQL or an approved
disposable test database, and NEVER against remote production databases.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlparse

import sqlalchemy as sa
from sqlalchemy.engine import Connection

# Known forbidden production project identifiers and host signatures
_FORBIDDEN_PROJECT_REFS = frozenset({"rjntmboskzyrsqcetzil"})
_FORBIDDEN_HOST_SUBSTRINGS = (
    "supabase.com",
    "supabase.co",
    "pooler.supabase.com",
    "aws-1-",
    "aws-",
    ".rds.amazonaws.com",
    ".azure.com",
    ".google.com",
)

# Approved local hostnames
_APPROVED_LOCAL_HOSTNAMES = frozenset({
    "localhost",
    "127.0.0.1",
    "::1",
    "ipkrh-postgres",  # Docker compose service name
})

# Approved local network ranges (loopback and Docker bridge networks)
_DOCKER_BRIDGE_NETWORK = ipaddress.ip_network("172.16.0.0/12")

# Sanitized configuration instruction message (no credentials exposed)
LOCAL_DB_CONFIG_HELP = (
    "\n[MIGRATION TEST GUARD INSTRUCTION]\n"
    "Migration and DDL tests are forbidden from targeting remote or production databases.\n"
    "To configure an approved local test database:\n"
    "  1. Start the local PostgreSQL container via Docker:\n"
    "       docker compose up -d postgres\n"
    "  2. Configure local environment variables in your test settings or .env:\n"
    "       POSTGRES_HOST=127.0.0.1\n"
    "       POSTGRES_PORT=5432\n"
    "       POSTGRES_DB=knowledge_handover\n"
    "       DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/knowledge_handover\n"
)


class DatabaseIsolationError(RuntimeError):
    """Raised when a database connection violates test isolation invariants."""

    pass


@dataclass(frozen=True, slots=True)
class DatabaseIdentity:
    """Verified database identity from server catalog."""

    current_database: str
    current_user: str
    server_addr: str | None
    server_port: int | None
    version: str


def validate_url_isolation(raw_url: str) -> None:
    """Statically validate database URL before attempting any connection.

    Fails closed without printing secrets.
    """
    if not raw_url or not isinstance(raw_url, str):
        raise DatabaseIsolationError(
            "Malformed connection configuration: database URL is empty or undefined."
            + LOCAL_DB_CONFIG_HELP
        )

    try:
        parsed = urlparse(raw_url)
    except Exception as exc:
        raise DatabaseIsolationError(
            f"Malformed connection configuration: unable to parse URL ({type(exc).__name__})."
            + LOCAL_DB_CONFIG_HELP
        ) from exc

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise DatabaseIsolationError(
            "Missing database identity: connection hostname is empty or undefined."
            + LOCAL_DB_CONFIG_HELP
        )

    username = (parsed.username or "").strip().lower()

    # Rule 1: Check forbidden project references in username or URL
    for ref in _FORBIDDEN_PROJECT_REFS:
        if ref in username or ref in raw_url.lower():
            raise DatabaseIsolationError(
                "CRITICAL ISOLATION VIOLATION: Target configuration matches production "
                "project identifier. Execution rejected to protect hosted database."
                + LOCAL_DB_CONFIG_HELP
            )

    # Rule 2: Check forbidden host substrings
    for forbidden in _FORBIDDEN_HOST_SUBSTRINGS:
        if forbidden in hostname:
            raise DatabaseIsolationError(
                f"CRITICAL ISOLATION VIOLATION: Target host '{hostname}' matches forbidden "
                f"hosted/cloud pattern '{forbidden}'. Execution rejected."
                + LOCAL_DB_CONFIG_HELP
            )

    # Rule 3: Check approved local hostnames
    if hostname not in _APPROVED_LOCAL_HOSTNAMES:
        raise DatabaseIsolationError(
            f"CRITICAL ISOLATION VIOLATION: Target host '{hostname}' is not in approved "
            f"local test hosts. External databases are strictly forbidden."
            + LOCAL_DB_CONFIG_HELP
        )


def inspect_live_database_identity(conn: Connection) -> DatabaseIdentity:
    """Inspect active PostgreSQL server identity catalog via read-only query.

    Fails closed if the identity query fails or returns incomplete data.
    """
    try:
        row = conn.execute(
            sa.text(
                "SELECT "
                "  current_database(), "
                "  current_user, "
                "  inet_server_addr()::text, "
                "  inet_server_port(), "
                "  version();"
            )
        ).fetchone()
    except Exception as exc:
        raise DatabaseIsolationError(
            f"Missing database identity: failed to query server catalog ({type(exc).__name__})."
            + LOCAL_DB_CONFIG_HELP
        ) from exc

    if not row or row[0] is None or row[1] is None:
        raise DatabaseIsolationError(
            "Missing database identity: server returned incomplete identity metadata."
            + LOCAL_DB_CONFIG_HELP
        )

    return DatabaseIdentity(
        current_database=str(row[0]),
        current_user=str(row[1]),
        server_addr=str(row[2]) if row[2] is not None else None,
        server_port=int(row[3]) if row[3] is not None else None,
        version=str(row[4]) if row[4] is not None else "",
    )


def validate_server_identity_isolation(identity: DatabaseIdentity) -> None:
    """Deep verification of live PostgreSQL server identity.

    Prevents bypass via DNS spoofing, hosts file poisoning, or proxy tunnelling.
    """
    # Rule 1: Username identity check
    user_lower = identity.current_user.lower()
    for ref in _FORBIDDEN_PROJECT_REFS:
        if ref in user_lower:
            raise DatabaseIsolationError(
                "CRITICAL ISOLATION VIOLATION: Server reports runtime user associated with "
                "production project identifier. Execution rejected."
                + LOCAL_DB_CONFIG_HELP
            )

    # Rule 2: IP address boundary check
    if identity.server_addr is not None:
        clean_addr = identity.server_addr.split("/")[0].strip()
        try:
            ip = ipaddress.ip_address(clean_addr)
        except ValueError as exc:
            raise DatabaseIsolationError(
                f"Malformed server address: '{identity.server_addr}' is not a valid IP."
                + LOCAL_DB_CONFIG_HELP
            ) from exc

        # Allow loopback (127.0.0.1, ::1)
        is_loopback = ip.is_loopback
        # Allow Docker bridge network
        is_docker_bridge = ip.version == 4 and ip in _DOCKER_BRIDGE_NETWORK

        if not (is_loopback or is_docker_bridge):
            raise DatabaseIsolationError(
                f"CRITICAL ISOLATION VIOLATION: Database server resolved to non-local address "
                f"'{identity.server_addr}'. Only local container/loopback addresses are allowed."
                + LOCAL_DB_CONFIG_HELP
            )


def verify_migration_target_isolation(
    raw_url: str,
    conn: Connection | None = None,
) -> DatabaseIdentity | None:
    """Comprehensive fail-closed test isolation verification.

    1. Statically validates URL configuration.
    2. If connection is provided, dynamically inspects live server identity.
    3. Fails closed with sanitized diagnostics on any invariant violation.
    """
    validate_url_isolation(raw_url)

    if conn is not None:
        identity = inspect_live_database_identity(conn)
        validate_server_identity_isolation(identity)
        return identity

    return None
