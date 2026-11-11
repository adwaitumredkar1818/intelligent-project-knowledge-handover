"""Initial empty Alembic baseline revision (Phase 2.1 backend foundation).

Revision ID: 0001_initial_baseline
Revises:
Create Date: 2026-11-11 18:15:00
"""

from __future__ import annotations

revision: str = "0001_initial_baseline"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Establish baseline Alembic revision before application tables are introduced."""


def downgrade() -> None:
    """Revert baseline Alembic revision."""
