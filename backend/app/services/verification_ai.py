"""AI-Assisted Verification Service using local Qwen3 8B.

Platform: The Handover
Module: Verification Center (Module 3 / Validation Area)

MANDATORY SAFEGUARD:
The AI is strictly advisory. It generates semantic explanations of contradictions
and formulates targeted clarification questions.
The AI NEVER approves, rejects, or independently marks any finding as verified.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.services.llm import LLMGenerationRequest, OllamaLLMClient, StructuredLLMClient

logger = logging.getLogger("app.services.verification_ai")

_EXPLAIN_CONFLICT_PROMPT = """You are an expert project knowledge auditor.
Two pieces of project evidence appear contradictory.
Analyze them objectively and explain the nuance.

Claim A:
"{claim_a}"

Claim B:
"{claim_b}"

Additional Context:
"{context}"

Return a JSON object matching this schema:
{{
  "likely_cause": "<one sentence explaining why these sources diverge>",
  "nuance_explanation": "<concise analytical explanation of the differences>",
  "reconciliation_recommendation": "<suggested action for the human reviewer>",
  "clarification_questions": ["<question 1 to ask the author or team lead>", "<question 2>"]
}}
"""

_SUGGEST_CLARIFICATIONS_PROMPT = """You are an expert handover auditor.
A candidate project knowledge finding has incomplete context or missing rationale.

Finding Title: "{title}"
Finding Domain: "{domain}"
Current Summary: "{summary}"
Missing Context Area: "{missing_context}"

Formulate 2-3 precise, professional clarification questions to ask the departing team member.
Return a JSON object:
{{
  "questions": [
    {{
      "question": "<specific question to clarify rationale, scope, or operational procedure>",
      "purpose": "<why this knowledge is critical for the incoming successor>"
    }}
  ]
}}
"""


class AIAssistedVerificationService:
    """Provides local LLM-assisted nuance analysis and question suggestion for human reviewers."""

    def __init__(self, llm_client: StructuredLLMClient | None = None) -> None:
        if llm_client is None:
            settings = get_settings()
            self._client: StructuredLLMClient = OllamaLLMClient(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model_reconstruction,
            )
        else:
            self._client = llm_client

    def explain_conflict(
        self,
        *,
        claim_a: str,
        claim_b: str,
        context: str = "",
    ) -> dict[str, Any]:
        """Explain the nuance of contradictory claims between two sources."""
        user_prompt = _EXPLAIN_CONFLICT_PROMPT.format(
            claim_a=claim_a[:1000],
            claim_b=claim_b[:1000],
            context=context[:1000],
        )
        request = LLMGenerationRequest(
            system_prompt=(
                "You are a strict, objective project knowledge verification auditor. "
                "Produce valid JSON only."
            ),
            user_prompt=user_prompt,
            temperature=0.1,
        )

        try:
            result = self._client.generate_json(request)
            return result.parsed_json
        except Exception as exc:
            logger.warning(
                "AI conflict explanation failed, returning deterministic fallback: %s",
                exc,
            )
            return {
                "likely_cause": "Semantic or temporal discrepancy between sources.",
                "nuance_explanation": (
                    "Automated AI explanation unavailable. Inspect raw source excerpts directly."
                ),
                "reconciliation_recommendation": (
                    "Review latest source timestamps and confirm with project lead."
                ),
                "clarification_questions": [
                    "Which source represents the final accepted direction?",
                    "Was the older decision explicitly superseded?",
                ],
            }

    def suggest_clarifications(
        self,
        *,
        title: str,
        domain: str,
        summary: str,
        missing_context: str,
    ) -> list[dict[str, str]]:
        """Formulate targeted clarification questions for incomplete findings."""
        user_prompt = _SUGGEST_CLARIFICATIONS_PROMPT.format(
            title=title[:200],
            domain=domain,
            summary=summary[:1000],
            missing_context=missing_context,
        )
        request = LLMGenerationRequest(
            system_prompt=(
                "You are a strict, objective project knowledge verification auditor. "
                "Produce valid JSON only."
            ),
            user_prompt=user_prompt,
            temperature=0.1,
        )

        try:
            result = self._client.generate_json(request)
            parsed = result.parsed_json
            questions = parsed.get("questions", [])
            if isinstance(questions, list):
                return questions
            return []
        except Exception as exc:
            logger.warning(
                "AI clarification question generation failed: %s",
                exc,
            )
            return [
                {
                    "question": f"Please clarify the background and rationale for '{title}'.",
                    "purpose": "Ensure complete context is captured for the handover.",
                }
            ]
