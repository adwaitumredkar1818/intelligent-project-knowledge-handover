"""Create platform authentication, refresh session, and RBAC tables (Phase 2.2).

Revision ID: 0002_auth_identity_rbac
Revises: 0001_initial_baseline
Create Date: 2026-11-11 19:05:00
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0002_auth_identity_rbac"
down_revision: str | None = "0001_initial_baseline"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

_RBAC_UUID_NAMESPACE = uuid.UUID("6b7c84d4-2c1b-4c6f-9c2a-9a3e4f502100")


def _rbac_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(_RBAC_UUID_NAMESPACE, f"{kind}:{key}")


def _seed_rbac_catalog() -> None:
    now = datetime(2026, 11, 11, 19, 5, 0, tzinfo=UTC)

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

    permissions = [
        (
            "account.profile.read",
            "Read Own Profile",
            "Read authenticated user's own account profile.",
            "platform",
        ),
        (
            "account.sessions.read",
            "Read Own Sessions",
            "List authenticated user's own refresh sessions.",
            "platform",
        ),
        (
            "account.sessions.revoke",
            "Revoke Own Sessions",
            "Revoke authenticated user's own refresh sessions.",
            "platform",
        ),
        (
            "platform.users.read",
            "Read Platform Users",
            "List and inspect platform user identities.",
            "platform",
        ),
        (
            "platform.users.manage",
            "Manage Platform Users",
            "Activate or disable platform user accounts.",
            "platform",
        ),
        (
            "platform.roles.read",
            "Read Roles & Permissions",
            "View defined RBAC roles and permission mappings.",
            "platform",
        ),
        (
            "platform.roles.manage",
            "Manage Platform Roles",
            "Assign or revoke platform-scoped roles on user accounts.",
            "platform",
        ),
        (
            "platform.sessions.manage",
            "Manage Platform Sessions",
            "Administratively revoke active user refresh sessions.",
            "platform",
        ),
        (
            "organisation.read",
            "Read Organisation",
            "Read organisation metadata within an assigned organisation.",
            "organisation",
        ),
        (
            "organisation.manage",
            "Manage Organisation",
            "Configure organisation settings within an assigned organisation.",
            "organisation",
        ),
        (
            "organisation.members.manage",
            "Manage Organisation Members",
            "Assign organisation-scoped roles within an assigned organisation.",
            "organisation",
        ),
        (
            "project.read",
            "Read Project",
            "Read permitted project resources within an assigned project.",
            "project",
        ),
        (
            "project.manage",
            "Manage Project",
            "Manage project configuration and memberships within an assigned project.",
            "project",
        ),
        (
            "project.evidence.contribute",
            "Contribute Project Evidence",
            "Upload documents and sync authorised sources within an assigned project.",
            "project",
        ),
        (
            "project.knowledge.review",
            "Review Project Knowledge & Handover",
            "Perform human verification reviews and designated handover approvals.",
            "project",
        ),
    ]

    op.bulk_insert(
        permissions_table,
        [
            {
                "id": _rbac_id("permission", code),
                "code": code,
                "name": name,
                "description": desc,
                "scope_type": scope,
                "created_at": now,
            }
            for code, name, desc, scope in permissions
        ],
    )

    roles: list[tuple[str, str, str, str, tuple[str, ...]]] = [
        (
            "standard_user",
            "Standard Platform User",
            "Default authenticated user with self-account and self-session access only.",
            "platform",
            ("account.profile.read", "account.sessions.read", "account.sessions.revoke"),
        ),
        (
            "platform_admin",
            "Platform Administrator",
            "Manages platform accounts, platform roles, and active platform sessions.",
            "platform",
            (
                "account.profile.read",
                "account.sessions.read",
                "account.sessions.revoke",
                "platform.users.read",
                "platform.users.manage",
                "platform.roles.read",
                "platform.roles.manage",
                "platform.sessions.manage",
            ),
        ),
        (
            "org_owner",
            "Organisation Owner",
            "Full governance within an organisation (assigned via Phase 2.3+ memberships).",
            "organisation",
            (
                "organisation.read",
                "organisation.manage",
                "organisation.members.manage",
                "project.read",
                "project.manage",
            ),
        ),
        (
            "org_admin",
            "Organisation Administrator",
            "Administers organisation members and projects (Phase 2.3+ memberships).",
            "organisation",
            (
                "organisation.read",
                "organisation.members.manage",
                "project.read",
                "project.manage",
            ),
        ),
        (
            "project_manager",
            "Project Manager",
            "Manages project workspace, sources, and handovers (Phase 2.3+ memberships).",
            "project",
            ("project.read", "project.manage", "project.evidence.contribute"),
        ),
        (
            "project_member",
            "Project Member",
            "Contributes evidence and curated knowledge inside assigned projects.",
            "project",
            ("project.read", "project.evidence.contribute"),
        ),
        (
            "reviewer",
            "Reviewer",
            "Verifies reconstructed knowledge and issues designated handover approvals.",
            "project",
            ("project.read", "project.knowledge.review"),
        ),
    ]

    op.bulk_insert(
        roles_table,
        [
            {
                "id": _rbac_id("role", name),
                "name": name,
                "display_name": display_name,
                "description": desc,
                "scope_type": scope,
                "is_system": True,
                "created_at": now,
                "updated_at": now,
            }
            for name, display_name, desc, scope, _ in roles
        ],
    )

    op.bulk_insert(
        role_permissions_table,
        [
            {
                "role_id": _rbac_id("role", role_name),
                "permission_id": _rbac_id("permission", perm_code),
                "created_at": now,
            }
            for role_name, _, _, _, perm_codes in roles
            for perm_code in perm_codes
        ],
    )


def upgrade() -> None:
    """Create authentication, refresh session, and RBAC schema tables."""
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column(
            "is_email_verified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'locked', 'pending')",
            name=op.f("ck_users_user_status"),
        ),
        sa.CheckConstraint("email = lower(email)", name=op.f("ck_users_user_email_lowercase")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            "scope_type IN ('platform', 'organisation', 'project')",
            name=op.f("ck_roles_role_scope_type"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
    )
    op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=True)
    op.create_index(op.f("ix_roles_scope_type"), "roles", ["scope_type"], unique=False)

    op.create_table(
        "permissions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "scope_type IN ('platform', 'organisation', 'project')",
            name=op.f("ck_permissions_permission_scope_type"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permissions")),
    )
    op.create_index(op.f("ix_permissions_code"), "permissions", ["code"], unique=True)
    op.create_index(
        op.f("ix_permissions_scope_type"),
        "permissions",
        ["scope_type"],
        unique=False,
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("permission_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name=op.f("fk_role_permissions_permission_id_permissions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_role_permissions_role_id_roles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name=op.f("pk_role_permissions")),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("assigned_by_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by_id"],
            ["users.id"],
            name=op.f("fk_user_roles_assigned_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_user_roles_role_id_roles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_roles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_roles")),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )
    op.create_index(op.f("ix_user_roles_role_id"), "user_roles", ["role_id"], unique=False)
    op.create_index(op.f("ix_user_roles_user_id"), "user_roles", ["user_id"], unique=False)

    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("token_family_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("replaced_by_session_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=64), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_metadata", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "length(token_hash) = 64",
            name=op.f("ck_refresh_sessions_refresh_token_hash_sha256_len"),
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_session_id"],
            ["refresh_sessions.id"],
            name=op.f("fk_refresh_sessions_replaced_by_session_id_refresh_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_refresh_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_sessions")),
    )
    op.create_index(
        op.f("ix_refresh_sessions_expires_at"),
        "refresh_sessions",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_refresh_sessions_family_active",
        "refresh_sessions",
        ["token_family_id", "revoked_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_refresh_sessions_token_family_id"),
        "refresh_sessions",
        ["token_family_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_refresh_sessions_token_hash"),
        "refresh_sessions",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_refresh_sessions_user_active",
        "refresh_sessions",
        ["user_id", "revoked_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_refresh_sessions_user_id"),
        "refresh_sessions",
        ["user_id"],
        unique=False,
    )

    _seed_rbac_catalog()


def downgrade() -> None:
    """Drop Phase 2.2 authentication, refresh session, and RBAC tables cleanly."""
    op.drop_index(op.f("ix_refresh_sessions_user_id"), table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_user_active", table_name="refresh_sessions")
    op.drop_index(op.f("ix_refresh_sessions_token_hash"), table_name="refresh_sessions")
    op.drop_index(op.f("ix_refresh_sessions_token_family_id"), table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_family_active", table_name="refresh_sessions")
    op.drop_index(op.f("ix_refresh_sessions_expires_at"), table_name="refresh_sessions")
    op.drop_table("refresh_sessions")

    op.drop_index(op.f("ix_user_roles_user_id"), table_name="user_roles")
    op.drop_index(op.f("ix_user_roles_role_id"), table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_table("role_permissions")

    op.drop_index(op.f("ix_permissions_scope_type"), table_name="permissions")
    op.drop_index(op.f("ix_permissions_code"), table_name="permissions")
    op.drop_table("permissions")

    op.drop_index(op.f("ix_roles_scope_type"), table_name="roles")
    op.drop_index(op.f("ix_roles_name"), table_name="roles")
    op.drop_table("roles")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
