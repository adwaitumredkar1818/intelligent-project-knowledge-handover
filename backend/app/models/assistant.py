"""SQLAlchemy models for Project Knowledge Assistant (conversations, messages, citations, retrieval runs, feedback)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    AssistantAnswerStatus,
    AssistantConversationStatus,
    AssistantFeedbackType,
    AssistantQueryType,
    AssistantSenderType,
)

if TYPE_CHECKING:
    from app.models.evidence import EvidenceChunk, EvidenceItem
    from app.models.knowledge import KnowledgeItem
    from app.models.organisation import Organisation
    from app.models.project import Project
    from app.models.user import User

_JSON_TYPE = JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")


class AssistantConversation(Base):
    """Project-scoped, private conversation session for an authorized project member."""

    __tablename__ = "assistant_conversations"
    __table_args__ = (
        Index("ix_ac_project_user", "project_id", "created_by_user_id"),
        Index("ix_ac_project_status", "project_id", "status"),
        Index("ix_ac_last_message", "project_id", "last_message_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Conversation")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AssistantConversationStatus.ACTIVE.value,
        server_default=AssistantConversationStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organisation: Mapped[Organisation] = relationship("Organisation")
    project: Mapped[Project] = relationship("Project")
    created_by: Mapped[User] = relationship("User")
    messages: Mapped[list[AssistantMessage]] = relationship(
        "AssistantMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AssistantMessage.created_at",
    )


class AssistantRetrievalRun(Base):
    """Audit and diagnostic log of a hybrid retrieval execution for an assistant query."""

    __tablename__ = "assistant_retrieval_runs"
    __table_args__ = (
        Index("ix_arr_project_time", "project_id", "created_at"),
        Index("ix_arr_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=AssistantQueryType.GENERAL.value,
    )
    retrieval_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="hybrid")
    candidates_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidates_authorized: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    diagnostics_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_TYPE,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AssistantMessage(Base):
    """An individual message turn (User, Assistant, or System) in a project conversation."""

    __tablename__ = "assistant_messages"
    __table_args__ = (
        Index("ix_am_conversation_created", "conversation_id", "created_at"),
        Index("ix_am_project_status", "project_id", "answer_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=AssistantSenderType.USER.value,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    answer_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AssistantAnswerStatus.ANSWERED.value,
        server_default=AssistantAnswerStatus.ANSWERED.value,
    )
    structured_payload_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_TYPE,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    model_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retrieval_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assistant_retrieval_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    conversation: Mapped[AssistantConversation] = relationship(
        "AssistantConversation", back_populates="messages"
    )
    retrieval_run: Mapped[AssistantRetrievalRun | None] = relationship("AssistantRetrievalRun")
    citations: Mapped[list[AssistantCitation]] = relationship(
        "AssistantCitation",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="AssistantCitation.citation_order",
    )
    feedbacks: Mapped[list[AssistantFeedback]] = relationship(
        "AssistantFeedback",
        back_populates="message",
        cascade="all, delete-orphan",
    )


class AssistantCitation(Base):
    """Grounded evidence citation linking an assistant statement to a source record & chunk."""

    __tablename__ = "assistant_citations"
    __table_args__ = (
        Index("ix_acit_message", "message_id"),
        Index("ix_acit_evidence", "evidence_id"),
        Index("ix_acit_chunk", "chunk_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assistant_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    citation_label: Mapped[str] = mapped_column(String(16), nullable=False)  # e.g. "S1"
    citation_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    knowledge_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    section_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        _JSON_TYPE,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    message: Mapped[AssistantMessage] = relationship("AssistantMessage", back_populates="citations")
    evidence: Mapped[EvidenceItem] = relationship("EvidenceItem")
    chunk: Mapped[EvidenceChunk | None] = relationship("EvidenceChunk")


class AssistantFeedback(Base):
    """User quality and accuracy feedback for an assistant response turn."""

    __tablename__ = "assistant_feedback"
    __table_args__ = (
        Index("ix_afb_message", "message_id"),
        Index("ix_afb_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assistant_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    feedback_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AssistantFeedbackType.HELPFUL.value,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    message: Mapped[AssistantMessage] = relationship("AssistantMessage", back_populates="feedbacks")
    user: Mapped[User] = relationship("User")
