"""AI-Assisted Narrative Drafting Service for Handover Sections.

Platform: The Handover
Module: Handover Workspace (Module 4 / Knowledge Transfer Area)

Enforces:
1. Optional Qwen3 8B drafting assistance for human editors
2. Grounded narrative generation strictly derived from linked verified knowledge
3. AI cannot independently approve, sign, or alter project facts
4. Fallback deterministic drafting when local LLM inference is offline
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.security import utc_now
from app.models.handover import HandoverPackageSection, HandoverPackageVersion
from app.repositories.handover import (
    HandoverPackageVersionRepository,
    HandoverSectionRepository,
)
from app.schemas.handover import NarrativeDraftRequest, SectionEditRequest
from app.services.llm import LLMChatMessage, StructuredLLMClient

logger = logging.getLogger("app.services.handover_narrative")


class HandoverNarrativeService:
    """Provides grounded narrative generation and section content editing."""

    def __init__(
        self,
        session: Session,
        llm_client: StructuredLLMClient | None = None,
    ) -> None:
        self.session = session
        self.version_repo = HandoverPackageVersionRepository(session)
        self.section_repo = HandoverSectionRepository(session)
        self.llm_client = llm_client

    def draft_section_narrative(
        self,
        *,
        project_id: uuid.UUID,
        request: NarrativeDraftRequest,
    ) -> dict[str, Any]:
        """Generate a structured, evidence-grounded draft narrative for a section."""
        version = self.version_repo.get_by_id(request.version_id, load_sections=True)
        if not version or version.project_id != project_id:
            raise NotFoundError(f"Package version {request.version_id} not found in this project.")

        # Find matching section
        section = next(
            (s for s in version.sections if s.section_type == request.section_type), None
        )
        if not section:
            raise NotFoundError(f"Section type '{request.section_type}' not found in version {request.version_id}.")

        # Collect linked knowledge items
        knowledge_snippets: list[str] = []
        for link in section.content_links:
            if link.knowledge_item:
                ki = link.knowledge_item
                stmt = ki.title or "Verified Finding"
                desc = ki.structured_summary or ""
                knowledge_snippets.append(f"- {stmt}: {desc}")

        context_str = "\n".join(knowledge_snippets) if knowledge_snippets else "No individual items linked."

        draft_content: str
        summary_text: str

        if self.llm_client is not None and knowledge_snippets:
            try:
                system_prompt = (
                    "You are a technical documentation assistant for The Handover platform. "
                    "Synthesize the following verified project knowledge into a clear, professional, "
                    "and well-structured handover section narrative. Do not invent any facts, decisions, "
                    "or claims not present in the provided knowledge findings."
                )
                user_prompt = (
                    f"Section: {section.section_title}\n"
                    f"Additional User Guidance: {request.additional_context or 'None'}\n\n"
                    f"Verified Knowledge Findings:\n{context_str}\n\n"
                    "Provide a clean markdown narrative suitable for an incoming project successor."
                )
                messages = [
                    LLMChatMessage(role="system", content=system_prompt),
                    LLMChatMessage(role="user", content=user_prompt),
                ]
                response_text = self.llm_client.generate_raw(messages=messages, temperature=0.1)
                draft_content = response_text
                summary_text = f"AI-drafted narrative synthesizing {len(knowledge_snippets)} verified findings."
            except Exception as e:
                logger.warning("LLM generation failed, falling back to deterministic draft: %s", e)
                draft_content = self._deterministic_draft(section.section_title, knowledge_snippets)
                summary_text = f"Synthesized {len(knowledge_snippets)} verified findings (deterministic)."
        else:
            draft_content = self._deterministic_draft(section.section_title, knowledge_snippets)
            summary_text = f"Structured compilation of {len(knowledge_snippets)} findings."

        return {
            "section_id": section.id,
            "section_type": section.section_type,
            "draft_content": draft_content,
            "content_summary": summary_text,
            "findings_count": len(knowledge_snippets),
        }

    def edit_section_content(
        self,
        section_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        request: SectionEditRequest,
    ) -> HandoverPackageSection:
        """Human editor updates section text and summary."""
        section = self.section_repo.get_by_id(section_id, load_links=False)
        if not section or section.project_id != project_id:
            raise NotFoundError(f"Section {section_id} not found in this project.")

        updated = self.section_repo.update_content(
            section_id,
            content=request.section_content,
            summary=request.content_summary,
        )
        return updated  # type: ignore[return-value]

    def _deterministic_draft(self, title: str, snippets: list[str]) -> str:
        lines = [
            f"# {title}",
            "",
            "## Summary of Verified Findings",
            "",
        ]
        if snippets:
            lines.extend(snippets)
        else:
            lines.append("No active verified findings recorded for this domain.")
        lines.append("")
        return "\n".join(lines)
