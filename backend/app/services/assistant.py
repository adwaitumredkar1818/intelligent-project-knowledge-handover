"""Project Knowledge Assistant Orchestration Service.

Platform: The Handover
Module: Project Knowledge Assistant (Module 5 / AI Assistant Area)
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import (
    ForbiddenError,
    NotFoundError,
)
from app.models.enums import (
    AssistantAnswerStatus,
    AssistantConversationStatus,
    AssistantQueryType,
    AssistantSenderType,
)
from app.repositories.assistant import (
    AssistantCitationRepository,
    AssistantConversationRepository,
    AssistantFeedbackRepository,
    AssistantMessageRepository,
    AssistantRetrievalRunRepository,
)
from app.schemas.assistant import (
    AssistantAnswerResponse,
    AssistantCitationResponse,
    AssistantFeedbackRequest,
    AssistantFeedbackResponse,
    AssistantMessageResponse,
    ConversationDetailResponse,
    ConversationResponse,
    QuestionRequest,
    RetrievalDiagnosticsResponse,
)
from app.services.assistant_llm import AssistantLLMReasoner
from app.services.assistant_query import AssistantQueryClassifier, ClassifiedQuery
from app.services.assistant_retrieval import AssistantRetrievalResult, AssistantRetrievalService
from app.services.assistant_validation import AssistantAnswerValidator, ValidatedAssistantAnswer
from app.services.rbac import ProjectContext

logger = logging.getLogger("app.services.assistant")


class ProjectKnowledgeAssistantService:
    """Coordinates conversations, query classification, hybrid retrieval, LLM reasoning, and validation."""

    def __init__(
        self,
        *,
        session: Session,
        settings: Settings,
        retrieval_service: AssistantRetrievalService | None = None,
        llm_reasoner: AssistantLLMReasoner | None = None,
        validator: AssistantAnswerValidator | None = None,
        query_classifier: AssistantQueryClassifier | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.conversation_repo = AssistantConversationRepository(session)
        self.message_repo = AssistantMessageRepository(session)
        self.citation_repo = AssistantCitationRepository(session)
        self.retrieval_run_repo = AssistantRetrievalRunRepository(session)
        self.feedback_repo = AssistantFeedbackRepository(session)

        self.retrieval_service = retrieval_service or AssistantRetrievalService(
            session=session,
            settings=settings,
        )
        self.llm_reasoner = llm_reasoner or AssistantLLMReasoner(settings=settings)
        self.validator = validator or AssistantAnswerValidator()
        self.classifier = query_classifier or AssistantQueryClassifier()

    # -----------------------------------------------------------------------
    # Conversation Management
    # -----------------------------------------------------------------------

    def create_conversation(
        self,
        *,
        project_ctx: ProjectContext,
        title: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> ConversationResponse:
        """Create a new conversation session for the authenticated project member."""
        user = project_ctx.principal.user
        default_title = title or "New Project Inquiry"

        conversation = self.conversation_repo.create(
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            created_by_user_id=user.id,
            title=default_title,
            metadata_json=metadata_json,
        )
        return ConversationResponse.model_validate(conversation)

    def list_conversations(
        self,
        *,
        project_ctx: ProjectContext,
        status: AssistantConversationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationResponse]:
        """List caller's conversations within the project."""
        user = project_ctx.principal.user
        convs = self.conversation_repo.list_for_user_in_project(
            project_id=project_ctx.project.id,
            user_id=user.id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return [ConversationResponse.model_validate(c) for c in convs]

    def get_conversation_detail(
        self,
        *,
        project_ctx: ProjectContext,
        conversation_id: uuid.UUID,
    ) -> ConversationDetailResponse:
        """Fetch conversation metadata and ordered message turns with their citations."""
        user = project_ctx.principal.user
        conv = self.conversation_repo.get_by_id(
            conversation_id,
            project_id=project_ctx.project.id,
            load_messages=True,
        )
        if not conv:
            raise NotFoundError("Conversation not found.", code="CONVERSATION_NOT_FOUND")

        # Non-managers can only access their own conversations
        if conv.created_by_user_id != user.id and not project_ctx.has_permission("assistant.admin"):
            raise ForbiddenError("You cannot access another user's conversation.", code="FORBIDDEN_CONVERSATION")

        msg_responses: list[AssistantMessageResponse] = []
        for msg in conv.messages:
            cit_responses = [
                AssistantCitationResponse.model_validate(c)
                for c in msg.citations
            ]
            msg_responses.append(
                AssistantMessageResponse(
                    id=msg.id,
                    conversation_id=msg.conversation_id,
                    sender_type=AssistantSenderType(msg.sender_type),
                    content=msg.content,
                    answer_status=AssistantAnswerStatus(msg.answer_status) if msg.answer_status else None,
                    structured_payload_json=msg.structured_payload_json,
                    citations=cit_responses,
                    model_name=msg.model_name,
                    prompt_tokens=msg.prompt_tokens,
                    completion_tokens=msg.completion_tokens,
                    duration_ms=msg.duration_ms,
                    retrieval_run_id=msg.retrieval_run_id,
                    created_at=msg.created_at,
                )
            )

        return ConversationDetailResponse(
            conversation=ConversationResponse.model_validate(conv),
            messages=msg_responses,
        )

    def update_conversation(
        self,
        *,
        project_ctx: ProjectContext,
        conversation_id: uuid.UUID,
        title: str | None = None,
        status: AssistantConversationStatus | None = None,
    ) -> ConversationResponse:
        """Update conversation title or active/archived status."""
        user = project_ctx.principal.user
        conv = self.conversation_repo.get_by_id(
            conversation_id,
            project_id=project_ctx.project.id,
        )
        if not conv:
            raise NotFoundError("Conversation not found.", code="CONVERSATION_NOT_FOUND")

        if conv.created_by_user_id != user.id and not project_ctx.has_permission("assistant.admin"):
            raise ForbiddenError("You cannot modify another user's conversation.", code="FORBIDDEN_CONVERSATION")

        updated = self.conversation_repo.update(
            conversation_id,
            title=title,
            status=status,
        )
        return ConversationResponse.model_validate(updated)

    def delete_conversation(
        self,
        *,
        project_ctx: ProjectContext,
        conversation_id: uuid.UUID,
    ) -> bool:
        """Delete an assistant conversation and all its messages/citations."""
        user = project_ctx.principal.user
        conv = self.conversation_repo.get_by_id(
            conversation_id,
            project_id=project_ctx.project.id,
        )
        if not conv:
            raise NotFoundError("Conversation not found.", code="CONVERSATION_NOT_FOUND")

        if conv.created_by_user_id != user.id and not project_ctx.has_permission("assistant.admin"):
            raise ForbiddenError("You cannot delete another user's conversation.", code="FORBIDDEN_CONVERSATION")

        return self.conversation_repo.delete(conversation_id)

    # -----------------------------------------------------------------------
    # Question Answering & Execution Pipeline
    # -----------------------------------------------------------------------

    def ask_question(
        self,
        *,
        project_ctx: ProjectContext,
        conversation_id: uuid.UUID,
        request: QuestionRequest,
    ) -> AssistantAnswerResponse:
        """Execute end-to-end question answering turn within a conversation."""
        started_at = time.perf_counter()
        user = project_ctx.principal.user

        # 1. Verify conversation exists and user has access
        conv = self.conversation_repo.get_by_id(
            conversation_id,
            project_id=project_ctx.project.id,
        )
        if not conv:
            raise NotFoundError("Conversation not found.", code="CONVERSATION_NOT_FOUND")

        if conv.created_by_user_id != user.id and not project_ctx.has_permission("assistant.admin"):
            raise ForbiddenError("You cannot post in another user's conversation.", code="FORBIDDEN_CONVERSATION")

        # 2. Persist User Message
        user_message = self.message_repo.create(
            conversation_id=conversation_id,
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            sender_type=AssistantSenderType.USER,
            content=request.question,
        )

        # Update conversation title automatically on first turn if it has default title
        if conv.title == "New Conversation" or conv.title == "New Project Inquiry":
            auto_title = request.question.strip()[:60]
            if len(request.question) > 60:
                auto_title += "..."
            self.conversation_repo.update(conversation_id, title=auto_title)

        # 3. Fetch past conversation history
        past_messages = self.message_repo.list_for_conversation(conversation_id, limit=6)
        chat_history: list[dict[str, str]] = []
        for pm in past_messages:
            if pm.id == user_message.id:
                continue
            chat_history.append({"role": pm.sender_type, "content": pm.content})

        # 4. Query Classification & Entity Extraction
        classified: ClassifiedQuery = self.classifier.classify(request.question)

        # 5. Permission-Aware Retrieval
        retrieval_res: AssistantRetrievalResult = self.retrieval_service.retrieve(
            project_ctx=project_ctx,
            classified_query=classified,
            search_mode=request.mode,
            include_domains=request.include_domains,
            max_citations=request.max_citations,
        )

        # 6. Record Retrieval Run Telemetry
        retrieval_run = self.retrieval_run_repo.create(
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            user_id=user.id,
            query_text=request.question,
            query_type=classified.query_type,
            retrieval_mode=request.mode,
            candidates_found=retrieval_res.candidates_found,
            candidates_authorized=retrieval_res.candidates_authorized,
            duration_ms=retrieval_res.duration_ms,
            diagnostics_json=retrieval_res.diagnostics,
        )

        # 7. Qwen3 Structured Reasoner
        available_labels = [c.citation_label for c in retrieval_res.citations_manifest]
        payload, llm_telemetry = self.llm_reasoner.generate_answer(
            question=request.question,
            evidence_prompt=retrieval_res.evidence_prompt,
            conversation_history=chat_history,
            available_citation_labels=available_labels,
        )

        # 8. Citation & Epistemic Validation Engine
        validated: ValidatedAssistantAnswer = self.validator.validate(
            payload=payload,
            citations_manifest=retrieval_res.citations_manifest,
        )

        total_duration_ms = int((time.perf_counter() - started_at) * 1000)

        # 9. Persist Assistant Message Turn
        structured_payload = {
            "query_type": classified.query_type.value,
            "claims": [c.model_dump() for c in validated.claims],
            "uncertainty": validated.uncertainty,
            "conflicts": validated.conflicts,
            "missing_information": validated.missing_information,
            "suggested_followup_questions": validated.suggested_followup_questions,
        }

        assistant_message = self.message_repo.create(
            conversation_id=conversation_id,
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            sender_type=AssistantSenderType.ASSISTANT,
            content=validated.answer,
            answer_status=validated.answer_status,
            structured_payload_json=structured_payload,
            model_name=llm_telemetry.get("model_name"),
            prompt_tokens=llm_telemetry.get("prompt_tokens"),
            completion_tokens=llm_telemetry.get("completion_tokens"),
            duration_ms=total_duration_ms,
            retrieval_run_id=retrieval_run.id,
        )

        # 10. Persist Citations
        citations_to_persist = []
        for order, cit in enumerate(validated.validated_citations, start=1):
            citations_to_persist.append(
                {
                    "message_id": assistant_message.id,
                    "organisation_id": project_ctx.organisation.id,
                    "project_id": project_ctx.project.id,
                    "citation_label": cit.citation_label,
                    "citation_order": order,
                    "evidence_id": cit.evidence_id,
                    "chunk_id": cit.chunk_id,
                    "knowledge_item_id": cit.knowledge_item_id,
                    "source_title": cit.source_title,
                    "source_provider": cit.source_provider,
                    "source_url": cit.source_url,
                    "section_title": cit.section_title,
                    "page_number": cit.page_number,
                    "excerpt": cit.excerpt,
                    "is_verified": cit.is_verified,
                }
            )

        persisted_citations = self.citation_repo.create_batch(citations_to_persist)
        self.conversation_repo.touch_last_message(conversation_id)

        response_citations = [
            AssistantCitationResponse.model_validate(c) for c in persisted_citations
        ]

        return AssistantAnswerResponse(
            message_id=assistant_message.id,
            conversation_id=conversation_id,
            answer=validated.answer,
            answer_status=validated.answer_status,
            query_type=classified.query_type,
            claims=validated.claims,
            citations=response_citations,
            uncertainty=validated.uncertainty,
            conflicts=validated.conflicts,
            missing_information=validated.missing_information,
            suggested_followup_questions=validated.suggested_followup_questions,
            model_name=llm_telemetry.get("model_name", "qwen3:8b"),
            retrieval_run_id=retrieval_run.id,
            duration_ms=total_duration_ms,
            created_at=assistant_message.created_at,
        )

    # -----------------------------------------------------------------------
    # Feedback & Diagnostics
    # -----------------------------------------------------------------------

    def submit_feedback(
        self,
        *,
        project_ctx: ProjectContext,
        message_id: uuid.UUID,
        request: AssistantFeedbackRequest,
    ) -> AssistantFeedbackResponse:
        """Record user feedback rating on an assistant message turn."""
        user = project_ctx.principal.user
        msg = self.message_repo.get_by_id(message_id, load_citations=False)
        if not msg:
            raise NotFoundError("Message not found.", code="MESSAGE_NOT_FOUND")

        if msg.project_id != project_ctx.project.id:
            raise NotFoundError("Message does not belong to this project.", code="MESSAGE_NOT_IN_PROJECT")

        feedback = self.feedback_repo.create(
            message_id=message_id,
            user_id=user.id,
            feedback_type=request.feedback_type,
            comment=request.comment,
        )
        return AssistantFeedbackResponse.model_validate(feedback)

    def get_retrieval_diagnostics(
        self,
        *,
        project_ctx: ProjectContext,
        run_id: uuid.UUID,
    ) -> RetrievalDiagnosticsResponse:
        """Fetch audit diagnostic telemetry for a specific retrieval execution."""
        run = self.retrieval_run_repo.get_by_id(run_id)
        if not run:
            raise NotFoundError("Retrieval run record not found.", code="RUN_NOT_FOUND")

        if run.project_id != project_ctx.project.id:
            raise NotFoundError("Retrieval run does not belong to this project.", code="RUN_NOT_IN_PROJECT")

        return RetrievalDiagnosticsResponse.model_validate(run)
