"""Read-only PostgreSQL connectivity and SSL verification utility.

Loads root `.env` via backend Settings, connects via SQLAlchemy 2.x + Psycopg 3,
runs a read-only identity/version check, and inspects active TLS/SSL status
without ever logging credentials or full connection strings.
"""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_DIR = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import clear_settings_cache, get_settings  # noqa: E402
from app.db.session import build_db_connect_args, create_db_engine  # noqa: E402


def verify_connection(*, require_ssl: bool = False) -> int:
    """Connect to configured PostgreSQL target and verify read-only SQL + SSL state."""
    clear_settings_cache()
    settings = get_settings()
    raw_url = settings.database.sqlalchemy_url()
    parsed = urlparse(raw_url)
    connect_args = build_db_connect_args(settings, raw_url)

    host = parsed.hostname or ""
    port = parsed.port or 5432
    timeout_s = int(connect_args.get("connect_timeout", settings.database.connect_timeout_seconds))

    print("Target Configuration (redacted):")
    print(f"  scheme   : {parsed.scheme}")
    print(f"  host     : {host}")
    print(f"  port     : {port}")
    print(f"  database : {parsed.path.lstrip('/')}")
    print(f"  user     : {parsed.username}")
    print(f"  ssl_mode : {connect_args.get('sslmode', 'from-url-query')}")
    print(f"  timeout  : {timeout_s}s")

    try:
        addr_infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        resolved_ips = sorted({str(info[4][0]) for info in addr_infos})
        print("\nNetwork Reachability:")
        print(f"  dns_resolution : ok ({', '.join(resolved_ips)})")
    except OSError as exc:
        print(f"\nERROR: DNS resolution failed ({type(exc).__name__}).")
        return 1

    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            print("  tcp_connection : ok")
    except OSError as exc:
        print(f"\nERROR: TCP connection failed ({type(exc).__name__}).")
        return 1

    engine = create_db_engine(settings)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT current_database(), current_user, version(), now();")
            ).one()

            ssl_in_use = False
            raw_conn = conn.connection
            driver_conn = getattr(raw_conn, "driver_connection", None)
            pgconn = getattr(driver_conn, "pgconn", None)
            if pgconn is not None:
                ssl_in_use = bool(pgconn.ssl_in_use)

            pg_stat_ssl_row: tuple[bool, str | None, str | None] | None = None
            try:
                stat_row = conn.execute(
                    text(
                        "SELECT ssl, version, cipher "
                        "FROM pg_stat_ssl WHERE pid = pg_backend_pid();"
                    )
                ).one_or_none()
                if stat_row is not None:
                    pg_stat_ssl_row = (bool(stat_row[0]), stat_row[1], stat_row[2])
            except SQLAlchemyError:
                # Poolers or restricted roles may hide pg_stat_ssl;
                # client pgconn.ssl_in_use remains authoritative.
                pg_stat_ssl_row = None

            alembic_rev: str | None = None
            has_alembic = conn.execute(
                text("SELECT to_regclass('public.alembic_version') IS NOT NULL;")
            ).scalar_one()
            if has_alembic:
                alembic_rev = conn.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1;")
                ).scalar_one_or_none()

        print("\nRead-Only Query Result:")
        print(f"  current_database : {row[0]}")
        print(f"  current_user     : {row[1]}")
        print(f"  server_version   : {row[2]}")
        print(f"  server_time      : {row[3]}")
        print("\nSSL / Migration State:")
        print(f"  client_ssl_in_use : {ssl_in_use}")
        if pg_stat_ssl_row is not None:
            print(
                f"  pg_stat_ssl       : ssl={pg_stat_ssl_row[0]}, "
                f"tls={pg_stat_ssl_row[1]}, cipher={pg_stat_ssl_row[2]}"
            )
        else:
            print("  pg_stat_ssl       : unavailable (pooled or restricted backend view)")
        print(f"  alembic_version_exists : {bool(has_alembic)}")
        print(
            f"  alembic_version        : "
            f"{alembic_rev if alembic_rev is not None else 'not initialized'}"
        )

        if require_ssl and not ssl_in_use:
            print("\nERROR: --require-ssl specified, but active connection is not using SSL.")
            return 2
        return 0
    except SQLAlchemyError as exc:
        # Never print raw SQLAlchemy exception text, which may embed URL details.
        orig = getattr(exc, "orig", None)
        orig_type = type(orig).__name__ if orig is not None else None
        sqlstate = getattr(orig, "sqlstate", None)
        details = [type(exc).__name__]
        if orig_type:
            details.append(orig_type)
        if sqlstate:
            details.append(f"SQLSTATE={sqlstate}")
        print(f"\nERROR: Database connection check failed ({', '.join(details)}).")
        return 1
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify configured PostgreSQL / Supabase connectivity and SSL status."
    )
    parser.add_argument(
        "--require-ssl",
        action="store_true",
        help="Fail with exit code 2 if the active client connection is not TLS/SSL-encrypted.",
    )
    args = parser.parse_args()
    return verify_connection(require_ssl=bool(args.require_ssl))


if __name__ == "__main__":
    raise SystemExit(main())
