"""Add project transitions, membership responsibility, and workspace RBAC permissions (Phase 2.7).

Revision ID: 0008_project_transitions_rbac
Revises: 0007_knowledge_reconstruction
Create Date: 2026-11-12 23:28:00
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_project_transitions_rbac"
down_revision: str | None = "0007_knowledge_reconstruction"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

_RBAC_UUID_NAMESPACE = uuid.UUID("6b7c84d4-2c1b-4c6f-9c2a-9a3e4f502100")

_NEW_PERMISSIONS: tuple[tuple[str, str, str, str], ...] = (
    (
        "project.evidence.read",
        "Read Project Evidence",
        "Search, filter, and inspect evidence in an assigned project.",
        "project",
    ),
    (
        "project.evidence.upload",
        "Upload Project Evidence",
        "Upload PDF and DOCX documents to an assigned project.",
        "project",
    ),
    (
        "project.evidence.manage",
        "Manage Project Evidence",
        "Delete or trigger reprocessing of evidence items.",
        "project",
    ),
    (
        "project.transition.manage",
        "Manage Project Transition",
        "Configure departing member, successor, and capture scope.",
        "project",
    ),
    (
        "project.sources.manage",
        "Manage Project Sources",
        "Connect and map external sources (GitHub, Jira) within an assigned project.",
        "project",
    ),
)

_NEW_ROLE_PERMISSION_PAIRS: tuple[tuple[str, str], ...] = (
    ("org_owner", "project.transition.manage"),
    ("org_owner", "project.sources.manage"),
    ("org_owner", "project.evidence.read"),
    ("org_owner", "project.evidence.upload"),
    ("org_owner", "project.evidence.manage"),
    ("org_owner", "project.evidence.contribute"),
    ("org_owner", "project.knowledge.review"),
    ("org_admin", "project.transition.manage"),
    ("org_admin", "project.sources.manage"),
    ("org_admin", "project.evidence.read"),
    ("org_admin", "project.evidence.upload"),
    ("org_admin", "project.evidence.manage"),
    ("org_admin", "project.evidence.contribute"),
    ("org_admin", "project.knowledge.review"),
    ("project_manager", "project.transition.manage"),
    ("project_manager", "project.sources.manage"),
    ("project_manager", "project.evidence.read"),
    ("project_manager", "project.evidence.upload"),
    ("project_manager", "project.evidence.manage"),
    ("project_member", "project.evidence.read"),
    ("project_member", "project.evidence.upload"),
    ("reviewer", "project.evidence.read"),
)


def _rbac_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(_RBAC_UUID_NAMESPACE, f"{kind}:{key}")


def _seed_workspace_rbac() -> None:
    now = datetime.now(UTC)
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("code", sa.String(128)),
        sa.column("name", sa.String(128)),
        sa.column("description", sa.Text()),
        sa.column("scope_type", sa.String(32)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid(as_uuid=True)),
        sa.column("permission_id", sa.Uuid(as_uuid=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    perm_rows = [
        {
            "id": _rbac_id("permission", code),
            "code": code,
            "name": name,
            "description": desc,
            "scope_type": scope,
            "created_at": now,
        }
        for code, name, desc, scope in _NEW_PERMISSIONS
    ]
    op.execute(
        postgresql.insert(permissions_table)
        .values(perm_rows)
        .on_conflict_do_nothing(index_elements=["code"])
    )

    link_rows = [
        {
            "role_id": _rbac_id("role", r_name),
            "permission_id": _rbac_id("permission", p_code),
            "created_at": now,
        }
        for r_name, p_code in _NEW_ROLE_PERMISSION_PAIRS
    ]
    op.execute(
        postgresql.insert(role_permissions_table)
        .values(link_rows)
        .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
    )


def _remove_workspace_rbac() -> None:
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid(as_uuid=True)),
        sa.column("permission_id", sa.Uuid(as_uuid=True)),
    )
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid(as_uuid=True)),
    )
    new_perm_ids = [_rbac_id("permission", code) for code, *_ in _NEW_PERMISSIONS]

    op.execute(
        role_permissions_table.delete().where(
            role_permissions_table.c.permission_id.in_(new_perm_ids)
        )
    )
    extra_pairs = (
        ("org_owner", "project.evidence.contribute"),
        ("org_owner", "project.knowledge.review"),
        ("org_admin", "project.evidence.contribute"),
        ("org_admin", "project.knowledge.review"),
    )
    for role_name, perm_code in extra_pairs:
        op.execute(
            role_permissions_table.delete().where(
                sa.and_(
                    role_permissions_table.c.role_id == _rbac_id("role", role_name),
                    role_permissions_table.c.permission_id == _rbac_id("permission", perm_code),
                )
            )
        )
    op.execute(permissions_table.delete().where(permissions_table.c.id.in_(new_perm_ids)))


def upgrade() -> None:
    """Add responsibility_description, project_transitions table, and workspace RBAC."""
    op.add_column(
        "project_memberships",
        sa.Column("responsibility_description", sa.Text(), nullable=True),
    )

    op.create_table(
        "project_transitions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("departing_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("successor_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "workflow_stage",
            sa.String(length=64),
            server_default="planning",
            nullable=False,
        ),
        sa.Column("handover_scope", sa.Text(), nullable=True),
        sa.Column(
            "source_scope",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("capture_start_date", sa.Date(), nullable=True),
        sa.Column("capture_end_date", sa.Date(), nullable=True),
        sa.Column("context_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "departing_user_id != successor_user_id",
            name="ck_project_transitions_uq_project_transitions_distinct_participants",
        ),
        sa.ForeignKeyConstraint(
            ["departing_user_id"],
            ["users.id"],
            name="fk_project_transitions_departing_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_project_transitions_project_id_projects",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["successor_user_id"],
            ["users.id"],
            name="fk_project_transitions_successor_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_project_transitions"),
    )
    op.create_index(
        op.f("ix_project_transitions_departing_user_id"),
        "project_transitions",
        ["departing_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_transitions_project_id"),
        "project_transitions",
        ["project_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_project_transitions_successor_user_id"),
        "project_transitions",
        ["successor_user_id"],
        unique=False,
    )

    _seed_workspace_rbac()


def downgrade() -> None:
    """Remove workspace RBAC additions, project_transitions, and responsibility_description."""
    _remove_workspace_rbac()
    op.drop_index(
        op.f("ix_project_transitions_successor_user_id"),
        table_name="project_transitions",
    )
    op.drop_index(
        op.f("ix_project_transitions_project_id"),
        table_name="project_transitions",
    )
    op.drop_index(
        op.f("ix_project_transitions_departing_user_id"),
        table_name="project_transitions",
    )
    op.drop_table("project_transitions")
    op.drop_column("project_memberships", "responsibility_description")
