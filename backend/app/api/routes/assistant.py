"""FastAPI HTTP endpoints for Project Knowledge Assistant (Module 5 / AI Assistant Area).

Provides:
- Project conversation management (creation, history, update, deletion)
- Evidence-grounded natural language question answering
- Multi-domain query classification and entity extraction
- Permission-aware hybrid RAG execution and attribution
- Source citation manifest validation and hallucination checks
- Epistemic uncertainty, conflict detection, and abstention handling
- Response quality feedback and retrieval diagnostic telemetry
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_app_settings,
    get_db_session,
    get_hybrid_retrieval_service,
    get_llm_client,
    require_project_permission,
)
from app.core.config import Settings
from app.models.enums import AssistantConversationStatus
from app.schemas.assistant import (
    AssistantAnswerResponse,
    AssistantFeedbackRequest,
    AssistantFeedbackResponse,
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationResponse,
    ConversationUpdateRequest,
    QuestionRequest,
    RetrievalDiagnosticsResponse,
)
from app.services.assistant import ProjectKnowledgeAssistantService
from app.services.assistant_llm import AssistantLLMReasoner
from app.services.assistant_retrieval import AssistantRetrievalService
from app.services.llm import StructuredLLMClient
from app.services.rbac import ProjectContext
from app.services.retrieval import HybridRetrievalService

router = APIRouter(prefix="/projects/{project_id}/assistant", tags=["Project Knowledge Assistant"])


def _get_assistant_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    hybrid_service: HybridRetrievalService = Depends(get_hybrid_retrieval_service),
    llm_client: StructuredLLMClient = Depends(get_llm_client),
) -> ProjectKnowledgeAssistantService:
    """Dependency provider assembling the full Project Knowledge Assistant stack."""
    retrieval_svc = AssistantRetrievalService(
        session=session,
        settings=settings,
        hybrid_retrieval_service=hybrid_service,
    )
    llm_reasoner = AssistantLLMReasoner(
        settings=settings,
        llm_client=llm_client,
    )
    return ProjectKnowledgeAssistantService(
        session=session,
        settings=settings,
        retrieval_service=retrieval_svc,
        llm_reasoner=llm_reasoner,
    )


# ---------------------------------------------------------------------------
# Conversation Management Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new assistant conversation",
)
def create_conversation(
    project_id: uuid.UUID,
    payload: ConversationCreateRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("assistant.chat"))],
    assistant_service: Annotated[ProjectKnowledgeAssistantService, Depends(_get_assistant_service)],
) -> ConversationResponse:
    """Create a new private conversation session for the authenticated user."""
    return assistant_service.create_conversation(
        project_ctx=project_ctx,
        title=payload.title,
        metadata_json=payload.metadata_json,
    )


@router.get(
    "/conversations",
    response_model=list[ConversationResponse],
    summary="List caller's conversations in the project",
)
def list_conversations(
    project_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("assistant.read"))],
    assistant_service: Annotated[ProjectKnowledgeAssistantService, Depends(_get_assistant_service)],
    status: AssistantConversationStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ConversationResponse]:
    """Retrieve all conversations created by the caller in this project."""
    return assistant_service.list_conversations(
        project_ctx=project_ctx,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation detail with message turns and citations",
)
def get_conversation_detail(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("assistant.read"))],
    assistant_service: Annotated[ProjectKnowledgeAssistantService, Depends(_get_assistant_service)],
) -> ConversationDetailResponse:
    """Retrieve complete message thread, structured payloads, and cited sources."""
    return assistant_service.get_conversation_detail(
        project_ctx=project_ctx,
        conversation_id=conversation_id,
    )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Update conversation title or status",
)
def update_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    payload: ConversationUpdateRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("assistant.chat"))],
    assistant_service: Annotated[ProjectKnowledgeAssistantService, Depends(_get_assistant_service)],
) -> ConversationResponse:
    """Update title or archive/activate a conversation."""
    return assistant_service.update_conversation(
        project_ctx=project_ctx,
        conversation_id=conversation_id,
        title=payload.title,
        status=payload.status,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an assistant conversation",
)
def delete_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("assistant.chat"))],
    assistant_service: Annotated[ProjectKnowledgeAssistantService, Depends(_get_assistant_service)],
) -> None:
    """Delete a conversation, associated message history, and citations."""
    assistant_service.delete_conversation(
        project_ctx=project_ctx,
        conversation_id=conversation_id,
    )


# ---------------------------------------------------------------------------
# Question Answering Turn Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=AssistantAnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question and receive an evidence-grounded answer",
)
def ask_question(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    payload: QuestionRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("assistant.chat"))],
    assistant_service: Annotated[ProjectKnowledgeAssistantService, Depends(_get_assistant_service)],
) -> AssistantAnswerResponse:
    """Submit a user prompt, execute permission-aware hybrid RAG, and return cited answer."""
    return assistant_service.ask_question(
        project_ctx=project_ctx,
        conversation_id=conversation_id,
        request=payload,
    )


# ---------------------------------------------------------------------------
# Feedback & Diagnostics Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/messages/{message_id}/feedback",
    response_model=AssistantFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit user feedback for an assistant response turn",
)
def submit_feedback(
    project_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: AssistantFeedbackRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("assistant.feedback"))],
    assistant_service: Annotated[ProjectKnowledgeAssistantService, Depends(_get_assistant_service)],
) -> AssistantFeedbackResponse:
    """Record helpfulness or accuracy feedback on an assistant message."""
    return assistant_service.submit_feedback(
        project_ctx=project_ctx,
        message_id=message_id,
        request=payload,
    )


@router.get(
    "/diagnostics/retrieval/{run_id}",
    response_model=RetrievalDiagnosticsResponse,
    summary="Get audit retrieval telemetry diagnostics",
)
def get_retrieval_diagnostics(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("assistant.read"))],
    assistant_service: Annotated[ProjectKnowledgeAssistantService, Depends(_get_assistant_service)],
) -> RetrievalDiagnosticsResponse:
    """Inspect detailed retrieval telemetry, candidate counts, and query classification."""
    return assistant_service.get_retrieval_diagnostics(
        project_ctx=project_ctx,
        run_id=run_id,
    )
