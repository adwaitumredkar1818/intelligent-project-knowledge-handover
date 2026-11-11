"""System-level repository queries for database connectivity verification."""

from __future__ import annotations

import logging
import time

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SystemRepository:
    """Executes lightweight canonical store connectivity probes."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def ping(self) -> tuple[bool, float | None]:
        """Execute SELECT 1 against PostgreSQL and return (healthy, latency_ms)."""
        started_at = time.perf_counter()
        try:
            self._session.execute(text("SELECT 1"))
            latency_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
            return True, latency_ms
        except SQLAlchemyError as exc:
            # Never log raw SQLAlchemy exception arguments containing connection strings.
            logger.warning(
                "PostgreSQL readiness probe failed (%s)",
                type(exc).__name__,
            )
            return False, None
