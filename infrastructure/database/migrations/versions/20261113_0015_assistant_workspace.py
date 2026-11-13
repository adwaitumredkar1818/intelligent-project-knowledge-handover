"""Add Project Knowledge Assistant schema: conversations, messages, citations, retrieval runs, feedback, and RBAC seed.

Revision ID: 0015_assistant_workspace
Revises: 0014_handover_rbac
Create Date: 2026-11-13 18:50:00.000000
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0015_assistant_workspace"
down_revision: Union[str, None] = "0014_handover_rbac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
_RBAC_UUID_NAMESPACE = uuid.UUID("6b7c84d4-2c1b-4c6f-9c2a-9a3e4f502100")


def _rbac_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(_RBAC_UUID_NAMESPACE, f"{kind}:{key}")


_NEW_PERMISSIONS: tuple[tuple[str, str, str, str], ...] = (
    (
        "assistant.read",
        "Read Assistant Conversations",
        "View conversations, message turns, citations, and answers.",
        "project",
    ),
    (
        "assistant.chat",
        "Ask Assistant Questions",
        "Create conversations and ask project questions with hybrid RAG.",
        "project",
    ),
    (
        "assistant.manage",
        "Manage Assistant Conversations",
        "Rename, archive, or delete user's own project conversations.",
        "project",
    ),
    (
        "assistant.feedback",
        "Submit Assistant Feedback",
        "Rate answers and report incorrect citations or information.",
        "project",
    ),
    (
        "assistant.admin",
        "Administrate Assistant",
        "View all retrieval diagnostics and manage assistant configuration.",
        "project",
    ),
)

_NEW_ROLE_PERMISSION_PAIRS: tuple[tuple[str, str], ...] = (
    # ORG_OWNER
    ("org_owner", "assistant.read"),
    ("org_owner", "assistant.chat"),
    ("org_owner", "assistant.manage"),
    ("org_owner", "assistant.feedback"),
    ("org_owner", "assistant.admin"),
    # ORG_ADMIN
    ("org_admin", "assistant.read"),
    ("org_admin", "assistant.chat"),
    ("org_admin", "assistant.manage"),
    ("org_admin", "assistant.feedback"),
    ("org_admin", "assistant.admin"),
    # PROJECT_MANAGER
    ("project_manager", "assistant.read"),
    ("project_manager", "assistant.chat"),
    ("project_manager", "assistant.manage"),
    ("project_manager", "assistant.feedback"),
    ("project_manager", "assistant.admin"),
    # PROJECT_MEMBER
    ("project_member", "assistant.read"),
    ("project_member", "assistant.chat"),
    ("project_member", "assistant.manage"),
    ("project_member", "assistant.feedback"),
    # REVIEWER
    ("reviewer", "assistant.read"),
    ("reviewer", "assistant.chat"),
    ("reviewer", "assistant.manage"),
    ("reviewer", "assistant.feedback"),
)


def upgrade() -> None:
    # 1. assistant_conversations
    op.create_table(
        "assistant_conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ac_project_user", "assistant_conversations", ["project_id", "created_by_user_id"])
    op.create_index("ix_ac_project_status", "assistant_conversations", ["project_id", "status"])
    op.create_index("ix_ac_last_message", "assistant_conversations", ["project_id", "last_message_at"])

    # 2. assistant_retrieval_runs
    op.create_table(
        "assistant_retrieval_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("query_type", sa.String(length=64), server_default="general", nullable=False),
        sa.Column("retrieval_mode", sa.String(length=32), server_default="hybrid", nullable=False),
        sa.Column("candidates_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("candidates_authorized", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duration_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("diagnostics_json", _JSON_TYPE, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_arr_project_time", "assistant_retrieval_runs", ["project_id", "created_at"])
    op.create_index("ix_arr_user", "assistant_retrieval_runs", ["user_id"])

    # 3. assistant_messages
    op.create_table(
        "assistant_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("sender_type", sa.String(length=16), server_default="user", nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("answer_status", sa.String(length=32), server_default="answered", nullable=False),
        sa.Column("structured_payload_json", _JSON_TYPE, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("retrieval_run_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["assistant_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["retrieval_run_id"], ["assistant_retrieval_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_am_conversation_created", "assistant_messages", ["conversation_id", "created_at"])
    op.create_index("ix_am_project_status", "assistant_messages", ["project_id", "answer_status"])

    # 4. assistant_citations
    op.create_table(
        "assistant_citations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("organisation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("citation_label", sa.String(length=16), nullable=False),
        sa.Column("citation_order", sa.Integer(), server_default="1", nullable=False),
        sa.Column("evidence_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=True),
        sa.Column("knowledge_item_id", sa.UUID(), nullable=True),
        sa.Column("source_title", sa.String(length=512), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("section_title", sa.Text(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("metadata_json", _JSON_TYPE, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["evidence_chunks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_item_id"], ["knowledge_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["message_id"], ["assistant_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_acit_message", "assistant_citations", ["message_id"])
    op.create_index("ix_acit_evidence", "assistant_citations", ["evidence_id"])
    op.create_index("ix_acit_chunk", "assistant_citations", ["chunk_id"])

    # 5. assistant_feedback
    op.create_table(
        "assistant_feedback",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("feedback_type", sa.String(length=32), server_default="helpful", nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["assistant_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_afb_message", "assistant_feedback", ["message_id"])
    op.create_index("ix_afb_user", "assistant_feedback", ["user_id"])

    # 6. Seed RBAC permissions & role mappings
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

    op.drop_table("assistant_feedback")
    op.drop_table("assistant_citations")
    op.drop_table("assistant_messages")
    op.drop_table("assistant_retrieval_runs")
    op.drop_table("assistant_conversations")
