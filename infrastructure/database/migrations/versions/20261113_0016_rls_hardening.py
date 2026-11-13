"""Enable Row Level Security (RLS) on all 61 public base tables.

Revision ID: 0016_rls_hardening
Revises: 0015_assistant_workspace
Create Date: 2026-11-13 19:30:00.000000

Approved Architecture:
- RLS enabled across all 61 public base tables as defense-in-depth backstop.
- Relies on PostgreSQL default-deny semantics for non-BYPASSRLS roles (e.g. PostgREST anon/authenticated).
- Zero permissive policies created for anon/authenticated (ensuring 0 rows accessible via PostgREST).
- Zero policies created for postgres or service_role (both retain native BYPASSRLS=true runtime access).
- FORCE ROW LEVEL SECURITY is NOT enabled (preserving unconstrained backend/worker operation).
- Preserves all existing records, constraints, indexes, triggers, and foreign keys.
- Fully reversible via downgrade().
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "0016_rls_hardening"
down_revision: str | None = "0015_assistant_workspace"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# Verified canonical list of all 61 public base tables in the Handover platform schema.
_ALL_PUBLIC_BASE_TABLES: tuple[str, ...] = (
    "alembic_version",
    "assistant_citations",
    "assistant_conversations",
    "assistant_feedback",
    "assistant_messages",
    "assistant_retrieval_runs",
    "audit_logs",
    "background_jobs",
    "decision_traceability_chains",
    "entity_aliases",
    "evidence_chunks",
    "evidence_contents",
    "evidence_items",
    "evidence_page_contents",
    "handover_acknowledgements",
    "handover_cases",
    "handover_checklist_items",
    "handover_checklists",
    "handover_content_links",
    "handover_deliveries",
    "handover_ownership_transfers",
    "handover_package_sections",
    "handover_package_versions",
    "handover_packages",
    "handover_readiness_assessments",
    "handover_responsibility_transfers",
    "handover_signoffs",
    "handover_status_histories",
    "identity_resolution_candidates",
    "knowledge_entities",
    "knowledge_evidence_links",
    "knowledge_extraction_runs",
    "knowledge_items",
    "knowledge_relationships",
    "knowledge_timeline_events",
    "oauth_states",
    "organisation_invitations",
    "organisation_memberships",
    "organisations",
    "permissions",
    "project_memberships",
    "project_source_mappings",
    "project_transitions",
    "project_vector_indexes",
    "projects",
    "refresh_sessions",
    "relationship_evidence_links",
    "relationship_reconstruction_runs",
    "role_permissions",
    "roles",
    "source_access_policies",
    "source_connections",
    "source_sync_runs",
    "user_roles",
    "user_source_authorisations",
    "users",
    "verification_cases",
    "verification_conflicts",
    "verification_context_requests",
    "verification_issues",
    "verification_review_events",
)


def _is_offline() -> bool:
    """Safely check if Alembic is running in offline mode."""
    try:
        return bool(context.is_offline_mode())
    except (AttributeError, NameError, RuntimeError):
        return False


def _verify_schema_integrity(bind: sa.engine.Connection) -> None:
    """Pre-flight check verifying all 61 tables exist in public schema before applying DDL."""
    if _is_offline():
        return

    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names(schema="public"))
    missing_tables = [t for t in _ALL_PUBLIC_BASE_TABLES if t not in existing_tables]
    if missing_tables:
        raise RuntimeError(
            f"Pre-migration schema assertion failed: {len(missing_tables)} expected "
            f"table(s) missing from schema 'public': {missing_tables}"
        )


def _enforce_connection_timeouts(bind: sa.engine.Connection) -> None:
    """Enforce strict lock_timeout and statement_timeout on the active migration connection.

    Requirements:
      - lock_timeout <= 2000ms (2s) to prevent blocking concurrent transactions.
      - statement_timeout <= 30000ms (30s) to abort runaway operations.
    Fails closed if the effective settings cannot be verified.
    """
    if _is_offline():
        return

    # Apply transaction-local timeout configuration
    bind.execute(sa.text("SET LOCAL lock_timeout = '2000ms';"))
    bind.execute(sa.text("SET LOCAL statement_timeout = '30000ms';"))

    # Verify effective values directly from PostgreSQL engine
    lt_str = bind.execute(sa.text("SHOW lock_timeout;")).scalar_one()
    st_str = bind.execute(sa.text("SHOW statement_timeout;")).scalar_one()

    # Parse and assert lock_timeout (e.g. '2s' or '2000ms')
    lt_normalized = str(lt_str).strip().lower()
    if lt_normalized not in {"2s", "2000ms"}:
        raise RuntimeError(
            f"Pre-migration timeout assertion failed: effective lock_timeout is '{lt_str}', "
            "expected '2s' or '2000ms'."
        )

    # Parse and assert statement_timeout (e.g. '30s' or '30000ms')
    st_normalized = str(st_str).strip().lower()
    if st_normalized not in {"30s", "30000ms"}:
        raise RuntimeError(
            f"Pre-migration timeout assertion failed: effective statement_timeout is '{st_str}', "
            "expected '30s' or '30000ms'."
        )


def upgrade() -> None:
    """Enable Row Level Security on all 61 public base tables."""
    bind = op.get_bind()
    _verify_schema_integrity(bind)
    _enforce_connection_timeouts(bind)

    for table in _ALL_PUBLIC_BASE_TABLES:
        # PostgreSQL 17 standard DDL enabling RLS.
        # Tables with RLS enabled and zero permissive policies enforce absolute default-deny
        # for non-BYPASSRLS roles (PostgREST anon / authenticated).
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;')


def downgrade() -> None:
    """Disable Row Level Security on all 61 public base tables."""
    bind = op.get_bind()
    _verify_schema_integrity(bind)
    _enforce_connection_timeouts(bind)

    for table in _ALL_PUBLIC_BASE_TABLES:
        op.execute(f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY;')
