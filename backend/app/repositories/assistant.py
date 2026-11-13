"""Data-access repositories for Project Knowledge Assistant (Module 5 / AI Assistant Area).

Provides persistence abstractions for:
- AssistantConversationRepository: Conversation lifecycle & project isolation
- AssistantMessageRepository: User & Assistant message turns
- AssistantCitationRepository: Grounded citations and claim attribution
- AssistantRetrievalRunRepository: Retrieval telemetry and diagnostic records
- AssistantFeedbackRepository: User feedback and ratings
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.security import utc_now
from app.models.assistant import (
    AssistantCitation,
    AssistantConversation,
    AssistantFeedback,
    AssistantMessage,
    AssistantRetrievalRun,
)
from app.models.enums import (
    AssistantAnswerStatus,
    AssistantConversationStatus,
    AssistantFeedbackType,
    AssistantQueryType,
    AssistantSenderType,
)


class AssistantConversationRepository:
    """Manages persistence for project assistant conversations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        title: str = "New Conversation",
        metadata_json: dict[str, Any] | None = None,
    ) -> AssistantConversation:
        conversation = AssistantConversation(
            organisation_id=organisation_id,
            project_id=project_id,
            created_by_user_id=created_by_user_id,
            title=title,
            status=AssistantConversationStatus.ACTIVE.value,
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_by_id(
        self,
        conversation_id: uuid.UUID,
        *,
        project_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        load_messages: bool = False,
    ) -> AssistantConversation | None:
        stmt = select(AssistantConversation).where(AssistantConversation.id == conversation_id)
        if project_id:
            stmt = stmt.where(AssistantConversation.project_id == project_id)
        if user_id:
            stmt = stmt.where(AssistantConversation.created_by_user_id == user_id)

        if load_messages:
            stmt = stmt.options(
                selectinload(AssistantConversation.messages).selectinload(AssistantMessage.citations)
            )

        return self.db.scalars(stmt).first()

    def list_for_user_in_project(
        self,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        status: AssistantConversationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AssistantConversation]:
        stmt = (
            select(AssistantConversation)
            .where(
                AssistantConversation.project_id == project_id,
                AssistantConversation.created_by_user_id == user_id,
            )
            .order_by(
                AssistantConversation.last_message_at.desc().nullslast(),
                AssistantConversation.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        if status:
            stmt = stmt.where(AssistantConversation.status == status.value)

        return list(self.db.scalars(stmt).all())

    def update(
        self,
        conversation_id: uuid.UUID,
        *,
        title: str | None = None,
        status: AssistantConversationStatus | None = None,
    ) -> AssistantConversation | None:
        conversation = self.get_by_id(conversation_id)
        if not conversation:
            return None

        if title is not None:
            conversation.title = title
        if status is not None:
            conversation.status = status.value
        conversation.updated_at = utc_now()

        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def touch_last_message(self, conversation_id: uuid.UUID, when: datetime | None = None) -> None:
        now = when or utc_now()
        stmt = (
            update(AssistantConversation)
            .where(AssistantConversation.id == conversation_id)
            .values(last_message_at=now, updated_at=now)
        )
        self.db.execute(stmt)
        self.db.commit()

    def delete(self, conversation_id: uuid.UUID) -> bool:
        conversation = self.get_by_id(conversation_id)
        if not conversation:
            return False
        self.db.delete(conversation)
        self.db.commit()
        return True


class AssistantMessageRepository:
    """Manages user & assistant message turns with structured payloads."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        conversation_id: uuid.UUID,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        sender_type: AssistantSenderType,
        content: str,
        answer_status: AssistantAnswerStatus = AssistantAnswerStatus.ANSWERED,
        structured_payload_json: dict[str, Any] | None = None,
        model_name: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        duration_ms: int | None = None,
        retrieval_run_id: uuid.UUID | None = None,
    ) -> AssistantMessage:
        message = AssistantMessage(
            conversation_id=conversation_id,
            organisation_id=organisation_id,
            project_id=project_id,
            sender_type=sender_type.value,
            content=content,
            answer_status=answer_status.value,
            structured_payload_json=structured_payload_json or {},
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_ms=duration_ms,
            retrieval_run_id=retrieval_run_id,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_by_id(
        self,
        message_id: uuid.UUID,
        *,
        load_citations: bool = True,
    ) -> AssistantMessage | None:
        stmt = select(AssistantMessage).where(AssistantMessage.id == message_id)
        if load_citations:
            stmt = stmt.options(selectinload(AssistantMessage.citations))
        return self.db.scalars(stmt).first()

    def list_for_conversation(
        self,
        conversation_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AssistantMessage]:
        stmt = (
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == conversation_id)
            .options(selectinload(AssistantMessage.citations))
            .order_by(AssistantMessage.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt).all())

    def count_for_conversation(self, conversation_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(AssistantMessage)
            .where(AssistantMessage.conversation_id == conversation_id)
        )
        return self.db.scalar(stmt) or 0


class AssistantCitationRepository:
    """Manages evidence citations linked to assistant message claims."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_batch(
        self,
        citations_data: list[dict[str, Any]],
    ) -> list[AssistantCitation]:
        if not citations_data:
            return []

        created: list[AssistantCitation] = []
        for item in citations_data:
            citation = AssistantCitation(
                message_id=item["message_id"],
                organisation_id=item["organisation_id"],
                project_id=item["project_id"],
                citation_label=item["citation_label"],
                citation_order=item.get("citation_order", 1),
                evidence_id=item["evidence_id"],
                chunk_id=item.get("chunk_id"),
                knowledge_item_id=item.get("knowledge_item_id"),
                source_title=item["source_title"],
                source_provider=item["source_provider"],
                source_url=item.get("source_url"),
                section_title=item.get("section_title"),
                page_number=item.get("page_number"),
                excerpt=item["excerpt"],
                is_verified=item.get("is_verified", True),
                metadata_json=item.get("metadata_json", {}),
            )
            self.db.add(citation)
            created.append(citation)

        self.db.commit()
        for c in created:
            self.db.refresh(c)
        return created

    def list_for_message(self, message_id: uuid.UUID) -> list[AssistantCitation]:
        stmt = (
            select(AssistantCitation)
            .where(AssistantCitation.message_id == message_id)
            .order_by(AssistantCitation.citation_order.asc())
        )
        return list(self.db.scalars(stmt).all())


class AssistantRetrievalRunRepository:
    """Manages audit and diagnostic logs for assistant retrieval runs."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        organisation_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        query_text: str,
        query_type: AssistantQueryType,
        retrieval_mode: str = "hybrid",
        candidates_found: int = 0,
        candidates_authorized: int = 0,
        duration_ms: int = 0,
        diagnostics_json: dict[str, Any] | None = None,
    ) -> AssistantRetrievalRun:
        run = AssistantRetrievalRun(
            organisation_id=organisation_id,
            project_id=project_id,
            user_id=user_id,
            query_text=query_text,
            query_type=query_type.value,
            retrieval_mode=retrieval_mode,
            candidates_found=candidates_found,
            candidates_authorized=candidates_authorized,
            duration_ms=duration_ms,
            diagnostics_json=diagnostics_json or {},
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_by_id(self, run_id: uuid.UUID) -> AssistantRetrievalRun | None:
        stmt = select(AssistantRetrievalRun).where(AssistantRetrievalRun.id == run_id)
        return self.db.scalars(stmt).first()


class AssistantFeedbackRepository:
    """Manages user feedback records for assistant message answers."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        feedback_type: AssistantFeedbackType,
        comment: str | None = None,
    ) -> AssistantFeedback:
        feedback = AssistantFeedback(
            message_id=message_id,
            user_id=user_id,
            feedback_type=feedback_type.value,
            comment=comment,
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def list_for_message(self, message_id: uuid.UUID) -> list[AssistantFeedback]:
        stmt = (
            select(AssistantFeedback)
            .where(AssistantFeedback.message_id == message_id)
            .order_by(AssistantFeedback.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())
