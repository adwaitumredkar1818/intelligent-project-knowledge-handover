"""Citation Validation and Uncertainty Engine for Project Knowledge Assistant.

Platform: The Handover
Module: Project Knowledge Assistant (Module 5 / AI Assistant Area)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from app.models.enums import AssistantAnswerStatus
from app.schemas.assistant import (
    AssistantAnswerPayload,
    AssistantCitationResponse,
    FactualClaim,
)

logger = logging.getLogger("app.services.assistant_validation")

_CITATION_LABEL_RE = re.compile(r"\[(S\d+)\]")


@dataclass
class ValidatedAssistantAnswer:
    """Consolidated answer payload after citation verification, grounding checks, and abstention."""

    answer: str
    answer_status: AssistantAnswerStatus
    claims: list[FactualClaim]
    validated_citations: list[AssistantCitationResponse]
    uncertainty: str | None
    conflicts: list[str]
    missing_information: list[str]
    suggested_followup_questions: list[str]


class AssistantAnswerValidator:
    """Validates citations against prompt manifest, enforces grounding, and detects hallucinations."""

    def validate(
        self,
        *,
        payload: AssistantAnswerPayload,
        citations_manifest: list[AssistantCitationResponse],
        is_access_restricted: bool = False,
    ) -> ValidatedAssistantAnswer:
        """Validate LLM output against candidate evidence manifest and fail-closed rules."""
        manifest_map: dict[str, AssistantCitationResponse] = {
            c.citation_label: c for c in citations_manifest
        }
        valid_labels = set(manifest_map.keys())

        # If user access to the requested scope was blocked/restricted
        if is_access_restricted:
            return ValidatedAssistantAnswer(
                answer=(
                    "Access restricted: You do not possess the required delegated source permissions "
                    "or project access level to retrieve information from the requested repository or source."
                ),
                answer_status=AssistantAnswerStatus.ACCESS_RESTRICTED,
                claims=[],
                validated_citations=[],
                uncertainty="Caller lacks authorized credentials for the target evidence source.",
                conflicts=[],
                missing_information=["Delegated source authorization."],
                suggested_followup_questions=[
                    "Please verify your source connection in Settings -> Connected Sources.",
                ],
            )

        # If no evidence was available
        if not citations_manifest:
            return ValidatedAssistantAnswer(
                answer=payload.answer,
                answer_status=AssistantAnswerStatus.INSUFFICIENT_EVIDENCE,
                claims=[],
                validated_citations=[],
                uncertainty=payload.uncertainty or "No matching evidence found in current project context.",
                conflicts=payload.conflicts,
                missing_information=payload.missing_information or ["Supporting documentation or source records."],
                suggested_followup_questions=payload.suggested_followup_questions,
            )

        # 1. Extract all citation labels mentioned in answer text
        mentioned_in_text = set(_CITATION_LABEL_RE.findall(payload.answer))

        # 2. Validate claims and their citation labels
        validated_claims: list[FactualClaim] = []
        cited_labels: set[str] = set(mentioned_in_text)

        for claim in payload.claims:
            clean_labels = [lbl for lbl in claim.citation_labels if lbl in valid_labels]
            cited_labels.update(clean_labels)
            # Only keep claim if it has at least one valid supporting citation or status is partial
            if clean_labels or payload.answer_status != AssistantAnswerStatus.ANSWERED:
                validated_claims.append(
                    FactualClaim(
                        claim_text=claim.claim_text,
                        citation_labels=clean_labels,
                        confidence=claim.confidence if clean_labels else 0.5,
                    )
                )

        # 3. Clean up hallucinated citation tags from answer text
        cleaned_answer = payload.answer
        for label in mentioned_in_text:
            if label not in valid_labels:
                # Remove hallucinated citation tag [S99]
                cleaned_answer = cleaned_answer.replace(f"[{label}]", "")

        # 4. Resolve final validated citations
        # Include all citations that were directly cited, plus any top evidence if none were explicitly tagged
        final_citations: list[AssistantCitationResponse] = []
        if cited_labels.intersection(valid_labels):
            for label in sorted(cited_labels.intersection(valid_labels)):
                final_citations.append(manifest_map[label])
        else:
            # If model didn't cite in text but provided an answer, attach top 2 manifest citations
            final_citations = citations_manifest[:2]

        # 5. Determine resolved epistemic status
        resolved_status = payload.answer_status

        # If model claimed answered, but 0 citations could be validated
        if resolved_status == AssistantAnswerStatus.ANSWERED and not final_citations:
            resolved_status = AssistantAnswerStatus.INSUFFICIENT_EVIDENCE

        # If conflicts are reported
        if payload.conflicts and resolved_status == AssistantAnswerStatus.ANSWERED:
            resolved_status = AssistantAnswerStatus.CONFLICTED_EVIDENCE

        # If missing information is explicitly noted
        if payload.missing_information and resolved_status == AssistantAnswerStatus.ANSWERED:
            resolved_status = AssistantAnswerStatus.PARTIALLY_ANSWERED

        return ValidatedAssistantAnswer(
            answer=cleaned_answer.strip(),
            answer_status=resolved_status,
            claims=validated_claims,
            validated_citations=final_citations,
            uncertainty=payload.uncertainty,
            conflicts=payload.conflicts,
            missing_information=payload.missing_information,
            suggested_followup_questions=payload.suggested_followup_questions,
        )
