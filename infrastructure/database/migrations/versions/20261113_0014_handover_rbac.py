"""Seed Handover Workspace RBAC permissions and role mappings.

Revision ID: 0014_handover_rbac
Revises: 0013_handover_workspace
Create Date: 2026-11-13 18:15:00.000000
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0014_handover_rbac"
down_revision: Union[str, None] = "0013_handover_workspace"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RBAC_UUID_NAMESPACE = uuid.UUID("6b7c84d4-2c1b-4c6f-9c2a-9a3e4f502100")


def _rbac_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(_RBAC_UUID_NAMESPACE, f"{kind}:{key}")


_NEW_PERMISSIONS: tuple[tuple[str, str, str, str], ...] = (
    (
        "handover.read",
        "Read Handover Packages",
        "View handover cases, assembled packages, and readiness assessments.",
        "project",
    ),
    (
        "handover.create",
        "Create Handover Cases",
        "Create and configure handover cases.",
        "project",
    ),
    (
        "handover.edit",
        "Edit Handover Cases",
        "Update handover cases, checklist items, and section narrative notes.",
        "project",
    ),
    (
        "handover.compile",
        "Compile Handover Packages",
        "Trigger deterministic 8-domain assembly of package versions.",
        "project",
    ),
    (
        "handover.readiness.assess",
        "Assess Handover Readiness",
        "Run 9-category readiness evaluation across verified knowledge.",
        "project",
    ),
    (
        "handover.review",
        "Review Handover Packages",
        "Conduct human review and checklist item tracking.",
        "project",
    ),
    (
        "handover.approve",
        "Approve Handover Packages",
        "Issue official reviewer approval sign-off on package versions.",
        "project",
    ),
    (
        "handover.deliver",
        "Deliver Handover Packages",
        "Release and deliver approved package versions to successors.",
        "project",
    ),
    (
        "handover.acknowledge",
        "Acknowledge Handover Packages",
        "Successor receipt and acknowledgement sign-off.",
        "project",
    ),
    (
        "handover.transfer",
        "Execute Ownership Transfer",
        "Perform internal project ownership and responsibility transfers.",
        "project",
    ),
    (
        "handover.admin",
        "Administrate Handover",
        "Full administrative control over handover lifecycle and rollbacks.",
        "project",
    ),
)

_NEW_ROLE_PERMISSION_PAIRS: tuple[tuple[str, str], ...] = (
    # ORG_OWNER
    ("org_owner", "handover.read"),
    ("org_owner", "handover.create"),
    ("org_owner", "handover.edit"),
    ("org_owner", "handover.compile"),
    ("org_owner", "handover.readiness.assess"),
    ("org_owner", "handover.review"),
    ("org_owner", "handover.approve"),
    ("org_owner", "handover.deliver"),
    ("org_owner", "handover.acknowledge"),
    ("org_owner", "handover.transfer"),
    ("org_owner", "handover.admin"),
    # ORG_ADMIN
    ("org_admin", "handover.read"),
    ("org_admin", "handover.create"),
    ("org_admin", "handover.edit"),
    ("org_admin", "handover.compile"),
    ("org_admin", "handover.readiness.assess"),
    ("org_admin", "handover.review"),
    ("org_admin", "handover.approve"),
    ("org_admin", "handover.deliver"),
    ("org_admin", "handover.acknowledge"),
    ("org_admin", "handover.transfer"),
    ("org_admin", "handover.admin"),
    # PROJECT_MANAGER
    ("project_manager", "handover.read"),
    ("project_manager", "handover.create"),
    ("project_manager", "handover.edit"),
    ("project_manager", "handover.compile"),
    ("project_manager", "handover.readiness.assess"),
    ("project_manager", "handover.review"),
    ("project_manager", "handover.deliver"),
    ("project_manager", "handover.transfer"),
    ("project_manager", "handover.admin"),
    # REVIEWER
    ("reviewer", "handover.read"),
    ("reviewer", "handover.review"),
    ("reviewer", "handover.approve"),
    ("reviewer", "handover.readiness.assess"),
    # PROJECT_MEMBER
    ("project_member", "handover.read"),
    ("project_member", "handover.edit"),
    ("project_member", "handover.acknowledge"),
)


def upgrade() -> None:
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


def downgrade() -> None:
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid(as_uuid=True)),
        sa.column("permission_id", sa.Uuid(as_uuid=True)),
    )
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("code", sa.String(128)),
    )

    new_perm_ids = [_rbac_id("permission", code) for code, *_ in _NEW_PERMISSIONS]
    op.execute(
        role_permissions_table.delete().where(
            role_permissions_table.c.permission_id.in_(new_perm_ids)
        )
    )
    op.execute(
        permissions_table.delete().where(
            permissions_table.c.id.in_(new_perm_ids)
        )
    )
