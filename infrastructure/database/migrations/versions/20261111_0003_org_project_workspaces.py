"""Create organisations, memberships, invitations, projects, and audit logs (Phase 2.3).

Revision ID: 0003_org_project_workspaces
Revises: 0002_auth_identity_rbac
Create Date: 2026-11-11 19:40:00
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_org_project_workspaces"
down_revision: str | None = "0002_auth_identity_rbac"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

_RBAC_UUID_NAMESPACE = uuid.UUID("6b7c84d4-2c1b-4c6f-9c2a-9a3e4f502100")

_NEW_PERMISSIONS: tuple[tuple[str, str, str, str], ...] = (
    (
        "platform.organisations.create",
        "Create Organisations",
        "Create new multi-tenant organisations owned by the creator.",
        "platform",
    ),
    (
        "organisation.members.read",
        "Read Organisation Members",
        "View active members and roles within an assigned organisation.",
        "organisation",
    ),
    (
        "organisation.invitations.read",
        "Read Organisation Invitations",
        "List pending and historical invitations within an organisation.",
        "organisation",
    ),
    (
        "organisation.invitations.manage",
        "Manage Organisation Invitations",
        "Issue and revoke invitations for permitted roles within an organisation.",
        "organisation",
    ),
    (
        "organisation.projects.create",
        "Create Organisation Projects",
        "Create project workspaces within an assigned organisation.",
        "organisation",
    ),
    (
        "organisation.audit.read",
        "Read Organisation Audit Events",
        "Inspect sanitised audit events scoped to an assigned organisation.",
        "organisation",
    ),
    (
        "project.members.read",
        "Read Project Members",
        "List active project members and their assigned project roles.",
        "project",
    ),
    (
        "project.members.manage",
        "Manage Project Members",
        "Assign and update project-scoped memberships for organisation members.",
        "project",
    ),
)

_NEW_ROLE = (
    "org_member",
    "Organisation Member",
    "Standard organisation member accessing permitted organisation resources.",
    "organisation",
)

_NEW_ROLE_PERMISSION_PAIRS: tuple[tuple[str, str], ...] = (
    # Existing platform roles gaining organisation creation permission
    ("standard_user", "platform.organisations.create"),
    ("platform_admin", "platform.organisations.create"),
    # Existing org roles gaining Phase 2.3 org & org-governed project permissions
    ("org_owner", "organisation.members.read"),
    ("org_owner", "organisation.invitations.read"),
    ("org_owner", "organisation.invitations.manage"),
    ("org_owner", "organisation.projects.create"),
    ("org_owner", "organisation.audit.read"),
    ("org_owner", "project.members.read"),
    ("org_owner", "project.members.manage"),
    ("org_admin", "organisation.members.read"),
    ("org_admin", "organisation.invitations.read"),
    ("org_admin", "organisation.invitations.manage"),
    ("org_admin", "organisation.projects.create"),
    ("org_admin", "organisation.audit.read"),
    ("org_admin", "project.members.read"),
    ("org_admin", "project.members.manage"),
    # New org_member role permissions
    ("org_member", "organisation.read"),
    ("org_member", "organisation.members.read"),
    # Existing project roles gaining project member permissions
    ("project_manager", "project.members.read"),
    ("project_manager", "project.members.manage"),
    ("project_member", "project.members.read"),
    ("reviewer", "project.members.read"),
)


def _rbac_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(_RBAC_UUID_NAMESPACE, f"{kind}:{key}")


def _seed_phase23_rbac_additions() -> None:
    now = datetime(2026, 11, 11, 19, 40, 0, tzinfo=UTC)

    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("code", sa.String(128)),
        sa.column("name", sa.String(128)),
        sa.column("description", sa.Text()),
        sa.column("scope_type", sa.String(32)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("name", sa.String(64)),
        sa.column("display_name", sa.String(128)),
        sa.column("description", sa.Text()),
        sa.column("scope_type", sa.String(32)),
        sa.column("is_system", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
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

    role_name, role_display, role_desc, role_scope = _NEW_ROLE
    op.execute(
        postgresql.insert(roles_table)
        .values(
            [
                {
                    "id": _rbac_id("role", role_name),
                    "name": role_name,
                    "display_name": role_display,
                    "description": role_desc,
                    "scope_type": role_scope,
                    "is_system": True,
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        )
        .on_conflict_do_nothing(index_elements=["name"])
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


def _remove_phase23_rbac_additions() -> None:
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid(as_uuid=True)),
        sa.column("permission_id", sa.Uuid(as_uuid=True)),
    )
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.Uuid(as_uuid=True)),
    )
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid(as_uuid=True)),
    )

    new_perm_ids = [_rbac_id("permission", code) for code, *_ in _NEW_PERMISSIONS]
    org_member_role_id = _rbac_id("role", _NEW_ROLE[0])

    op.execute(
        role_permissions_table.delete().where(
            sa.or_(
                role_permissions_table.c.role_id == org_member_role_id,
                role_permissions_table.c.permission_id.in_(new_perm_ids),
            )
        )
    )
    op.execute(roles_table.delete().where(roles_table.c.id == org_member_role_id))
    op.execute(permissions_table.delete().where(permissions_table.c.id.in_(new_perm_ids)))


def upgrade() -> None:
    """Create multi-tenant organisation, invitation, project, and audit tables."""
    op.create_table(
        "organisations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("created_by_id", sa.Uuid(as_uuid=True), nullable=False),
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'archived')",
            name=op.f("ck_organisations_organisation_status"),
        ),
        sa.CheckConstraint(
            "slug = lower(slug)",
            name=op.f("ck_organisations_organisation_slug_lowercase"),
        ),
        sa.CheckConstraint(
            "length(trim(name)) >= 2",
            name=op.f("ck_organisations_organisation_name_len"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_organisations_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organisations")),
    )
    op.create_index(
        op.f("ix_organisations_created_by_id"),
        "organisations",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(op.f("ix_organisations_slug"), "organisations", ["slug"], unique=True)
    op.create_index(op.f("ix_organisations_status"), "organisations", ["status"], unique=False)

    op.create_table(
        "organisation_memberships",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("invited_by_id", sa.Uuid(as_uuid=True), nullable=True),
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
            "status IN ('active', 'suspended', 'removed')",
            name=op.f("ck_organisation_memberships_organisation_membership_status"),
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_id"],
            ["users.id"],
            name=op.f("fk_organisation_memberships_invited_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name=op.f("fk_organisation_memberships_organisation_id_organisations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_organisation_memberships_role_id_roles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_organisation_memberships_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organisation_memberships")),
    )
    op.create_index(
        op.f("ix_organisation_memberships_organisation_id"),
        "organisation_memberships",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organisation_memberships_role_id"),
        "organisation_memberships",
        ["role_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organisation_memberships_user_id"),
        "organisation_memberships",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_org_memberships_user_status",
        "organisation_memberships",
        ["user_id", "status"],
        unique=False,
    )
    op.create_index(
        "uq_org_memberships_active_org_user",
        "organisation_memberships",
        ["organisation_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "organisation_invitations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("role_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'revoked', 'expired')",
            name=op.f("ck_organisation_invitations_organisation_invitation_status"),
        ),
        sa.CheckConstraint(
            "email = lower(email)",
            name=op.f("ck_organisation_invitations_organisation_invitation_email_lowercase"),
        ),
        sa.CheckConstraint(
            "length(token_hash) = 64",
            name=op.f("ck_organisation_invitations_organisation_invitation_token_hash_sha256_len"),
        ),
        sa.ForeignKeyConstraint(
            ["accepted_by_user_id"],
            ["users.id"],
            name=op.f("fk_organisation_invitations_accepted_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_id"],
            ["users.id"],
            name=op.f("fk_organisation_invitations_invited_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name=op.f("fk_organisation_invitations_organisation_id_organisations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by_id"],
            ["users.id"],
            name=op.f("fk_organisation_invitations_revoked_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_organisation_invitations_role_id_roles"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organisation_invitations")),
    )
    op.create_index(
        op.f("ix_organisation_invitations_email"),
        "organisation_invitations",
        ["email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organisation_invitations_expires_at"),
        "organisation_invitations",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organisation_invitations_invited_by_id"),
        "organisation_invitations",
        ["invited_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organisation_invitations_organisation_id"),
        "organisation_invitations",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organisation_invitations_role_id"),
        "organisation_invitations",
        ["role_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organisation_invitations_token_hash"),
        "organisation_invitations",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "uq_org_invitations_pending_org_email",
        "organisation_invitations",
        ["organisation_id", "email"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="planning", nullable=False),
        sa.Column("visibility", sa.String(length=32), server_default="private", nullable=False),
        sa.Column("created_by_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("target_completion_date", sa.Date(), nullable=True),
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('planning', 'active', 'on_hold', 'completed', 'archived')",
            name=op.f("ck_projects_project_status"),
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'organisation')",
            name=op.f("ck_projects_project_visibility"),
        ),
        sa.CheckConstraint(
            "slug = lower(slug)",
            name=op.f("ck_projects_project_slug_lowercase"),
        ),
        sa.CheckConstraint(
            "length(trim(name)) >= 2",
            name=op.f("ck_projects_project_name_len"),
        ),
        sa.CheckConstraint(
            "target_completion_date IS NULL OR start_date IS NULL "
            "OR target_completion_date >= start_date",
            name=op.f("ck_projects_project_dates_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_projects_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name=op.f("fk_projects_organisation_id_organisations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_projects_owner_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("organisation_id", "slug", name="uq_projects_organisation_slug"),
    )
    op.create_index(op.f("ix_projects_created_by_id"), "projects", ["created_by_id"], unique=False)
    op.create_index(
        op.f("ix_projects_organisation_id"),
        "projects",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        "ix_projects_organisation_status",
        "projects",
        ["organisation_id", "status"],
        unique=False,
    )
    op.create_index(op.f("ix_projects_owner_id"), "projects", ["owner_id"], unique=False)
    op.create_index(op.f("ix_projects_status"), "projects", ["status"], unique=False)

    op.create_table(
        "project_memberships",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("assigned_by_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
            "status IN ('active', 'removed')",
            name=op.f("ck_project_memberships_project_membership_status"),
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by_id"],
            ["users.id"],
            name=op.f("fk_project_memberships_assigned_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_memberships_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_project_memberships_role_id_roles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_project_memberships_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_memberships")),
    )
    op.create_index(
        op.f("ix_project_memberships_project_id"),
        "project_memberships",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_memberships_role_id"),
        "project_memberships",
        ["role_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_memberships_user_id"),
        "project_memberships",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_memberships_user_status",
        "project_memberships",
        ["user_id", "status"],
        unique=False,
    )
    op.create_index(
        "uq_project_memberships_active_project_user",
        "project_memberships",
        ["project_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("organisation_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=96), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("outcome", sa.String(length=24), server_default="success", nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "outcome IN ('success', 'denied', 'error')",
            name=op.f("ck_audit_logs_audit_log_outcome"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_audit_logs_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name=op.f("fk_audit_logs_organisation_id_organisations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_audit_logs_project_id_projects"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(
        op.f("ix_audit_logs_actor_user_id"),
        "audit_logs",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_event_type"), "audit_logs", ["event_type"], unique=False)
    op.create_index(
        "ix_audit_logs_org_created",
        "audit_logs",
        ["organisation_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_organisation_id"),
        "audit_logs",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_project_created",
        "audit_logs",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(op.f("ix_audit_logs_project_id"), "audit_logs", ["project_id"], unique=False)

    _seed_phase23_rbac_additions()


def downgrade() -> None:
    """Revert Phase 2.3 workspace, project, and audit tables while preserving Phase 2.2."""
    op.drop_index(op.f("ix_audit_logs_project_id"), table_name="audit_logs")
    op.drop_index("ix_audit_logs_project_created", table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_organisation_id"), table_name="audit_logs")
    op.drop_index("ix_audit_logs_org_created", table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_event_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_user_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("uq_project_memberships_active_project_user", table_name="project_memberships")
    op.drop_index("ix_project_memberships_user_status", table_name="project_memberships")
    op.drop_index(op.f("ix_project_memberships_user_id"), table_name="project_memberships")
    op.drop_index(op.f("ix_project_memberships_role_id"), table_name="project_memberships")
    op.drop_index(op.f("ix_project_memberships_project_id"), table_name="project_memberships")
    op.drop_table("project_memberships")

    op.drop_index(op.f("ix_projects_status"), table_name="projects")
    op.drop_index(op.f("ix_projects_owner_id"), table_name="projects")
    op.drop_index("ix_projects_organisation_status", table_name="projects")
    op.drop_index(op.f("ix_projects_organisation_id"), table_name="projects")
    op.drop_index(op.f("ix_projects_created_by_id"), table_name="projects")
    op.drop_table("projects")

    op.drop_index(
        "uq_org_invitations_pending_org_email",
        table_name="organisation_invitations",
    )
    op.drop_index(
        op.f("ix_organisation_invitations_token_hash"),
        table_name="organisation_invitations",
    )
    op.drop_index(
        op.f("ix_organisation_invitations_role_id"),
        table_name="organisation_invitations",
    )
    op.drop_index(
        op.f("ix_organisation_invitations_organisation_id"),
        table_name="organisation_invitations",
    )
    op.drop_index(
        op.f("ix_organisation_invitations_invited_by_id"),
        table_name="organisation_invitations",
    )
    op.drop_index(
        op.f("ix_organisation_invitations_expires_at"),
        table_name="organisation_invitations",
    )
    op.drop_index(
        op.f("ix_organisation_invitations_email"),
        table_name="organisation_invitations",
    )
    op.drop_table("organisation_invitations")

    op.drop_index("uq_org_memberships_active_org_user", table_name="organisation_memberships")
    op.drop_index("ix_org_memberships_user_status", table_name="organisation_memberships")
    op.drop_index(
        op.f("ix_organisation_memberships_user_id"),
        table_name="organisation_memberships",
    )
    op.drop_index(
        op.f("ix_organisation_memberships_role_id"),
        table_name="organisation_memberships",
    )
    op.drop_index(
        op.f("ix_organisation_memberships_organisation_id"),
        table_name="organisation_memberships",
    )
    op.drop_table("organisation_memberships")

    op.drop_index(op.f("ix_organisations_status"), table_name="organisations")
    op.drop_index(op.f("ix_organisations_slug"), table_name="organisations")
    op.drop_index(op.f("ix_organisations_created_by_id"), table_name="organisations")
    op.drop_table("organisations")

    _remove_phase23_rbac_additions()
