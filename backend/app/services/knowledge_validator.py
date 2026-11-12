"""Independent backend grounding, schema, citation & dedup validator (`NO EVIDENCE -> NO CLAIM`)."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from app.models.enums import (
    ConfidenceLevel,
    EpistemicStatus,
    KnowledgeCategory,
    KnowledgeReviewStatus,
    SupportClassification,
)
from app.schemas.knowledge import (
    CandidateEvidenceRef,
    ConfidenceMetadata,
    DecisionCandidate,
    DependencyCandidate,
    ResponsibilityCandidate,
    RiskBlockerCandidate,
    TechnicalKnowledgeCandidate,
    WorkItemCandidate,
)
from app.services.extraction_prompts import ChunkPromptInput

_WHITESPACE_RE = re.compile(r"\s+")
_FINGERPRINT_SLUG_RE = re.compile(r"[^a-z0-9]+")
_EXPLICIT_SEVERITY_RE = re.compile(
    r"\b(critical|blocker|blocking|sev[- ]?[0-4]|p[0-3]"
    r"|high(?:er|est)?\s+(?:severity|priority|risk)"
    r"|medium\s+(?:severity|priority|risk)|low\s+(?:severity|priority|risk)"
    r"|urgent|major|minor)\b",
    flags=re.IGNORECASE,
)

_CANDIDATE_MODEL_BY_CATEGORY: dict[KnowledgeCategory, type[Any]] = {
    KnowledgeCategory.DECISIONS_RATIONALE: DecisionCandidate,
    KnowledgeCategory.WORK_ITEMS: WorkItemCandidate,
    KnowledgeCategory.RESPONSIBILITIES_OWNERSHIP: ResponsibilityCandidate,
    KnowledgeCategory.TECHNICAL_ARCHITECTURE: TechnicalKnowledgeCandidate,
    KnowledgeCategory.BUGS_BLOCKERS_RISKS: RiskBlockerCandidate,
    KnowledgeCategory.DEPENDENCIES: DependencyCandidate,
}


@dataclass(frozen=True, slots=True)
class VerifiedEvidenceLinkDraft:
    """Validated provenance link verified against a concrete supplied EvidenceChunk."""

    evidence_id: uuid.UUID
    evidence_chunk_id: uuid.UUID
    support_type: str
    source_location: dict[str, Any]
    supporting_excerpt: str
    excerpt_match_mode: str
    source_metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ValidatedKnowledgeItemDraft:
    """Fully verified knowledge item ready for transactional persistence in PostgreSQL."""

    category: KnowledgeCategory
    epistemic_status: str
    review_status: str
    support_classification: str
    title: str
    structured_summary: str
    structured_payload: dict[str, Any]
    normalised_status: str | None
    person_or_owner_label: str | None
    source_attribution: dict[str, Any]
    fingerprint: str
    confidence_metadata: dict[str, Any]
    uncertainty_reason: str | None
    source_observed_at: datetime | None
    is_synthetic: bool
    evidence_links: tuple[VerifiedEvidenceLinkDraft, ...]


@dataclass(slots=True)
class BatchValidationReport:
    """Aggregated outcome and rejection audit breakdown for one LLM batch response."""

    accepted_items: list[ValidatedKnowledgeItemDraft] = field(default_factory=list)
    candidates_received: int = 0
    rejected_schema_count: int = 0
    rejected_ungrounded_count: int = 0
    rejection_reasons: list[str] = field(default_factory=list)


def _normalize_text_for_matching(value: str) -> str:
    """Normalize typography and whitespace cleanly without altering word boundaries."""
    normalized = (
        value.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )
    return _WHITESPACE_RE.sub(" ", normalized).strip().lower()


def verify_excerpt_in_chunk(
    *,
    excerpt: str,
    chunk_text: str,
) -> tuple[bool, str | None, str]:
    """Verify verbatim or whitespace-normalised quote presence inside `chunk_text`."""
    cleaned_excerpt = excerpt.strip()
    if len(cleaned_excerpt) < 8:
        return False, None, "excerpt_too_short"

    if cleaned_excerpt in chunk_text:
        return True, "exact", cleaned_excerpt

    norm_excerpt = _normalize_text_for_matching(cleaned_excerpt)
    norm_chunk = _normalize_text_for_matching(chunk_text)
    if len(norm_excerpt) >= 8 and norm_excerpt in norm_chunk:
        return True, "normalized_whitespace", cleaned_excerpt

    return False, None, "excerpt_not_found_in_chunk"


def _slugify_key(value: str) -> str:
    lowered = _normalize_text_for_matching(value)
    slug = _FINGERPRINT_SLUG_RE.sub("-", lowered).strip("-")
    return slug[:160]


def _extract_normalised_status(category: KnowledgeCategory, payload: dict[str, Any]) -> str | None:
    field_map = {
        KnowledgeCategory.DECISIONS_RATIONALE: "decision_status",
        KnowledgeCategory.WORK_ITEMS: "work_status",
        KnowledgeCategory.RESPONSIBILITIES_OWNERSHIP: "ownership_status",
        KnowledgeCategory.TECHNICAL_ARCHITECTURE: "technical_status",
        KnowledgeCategory.BUGS_BLOCKERS_RISKS: "risk_status",
        KnowledgeCategory.DEPENDENCIES: "dependency_status",
    }
    raw = payload.get(field_map[category])
    return str(raw).strip() if raw is not None else None


def _extract_person_label(category: KnowledgeCategory, payload: dict[str, Any]) -> str | None:
    if category == KnowledgeCategory.RESPONSIBILITIES_OWNERSHIP:
        val = payload.get("person_identity")
        return str(val).strip() if val else None
    if category == KnowledgeCategory.WORK_ITEMS:
        val = payload.get("assignee") or payload.get("creator")
        return str(val).strip() if val else None
    if category == KnowledgeCategory.DECISIONS_RATIONALE:
        val = payload.get("decision_maker")
        return str(val).strip() if val else None
    if category == KnowledgeCategory.BUGS_BLOCKERS_RISKS:
        val = payload.get("responsible_person")
        return str(val).strip() if val else None
    return None


def compute_conservative_fingerprint(
    *,
    category: KnowledgeCategory,
    title: str,
    payload: dict[str, Any],
    normalised_status: str | None,
    person_or_owner_label: str | None,
) -> str:
    """Compute conservative deduplication hash preserving statuses and unmerged identities."""
    status_key = _slugify_key(normalised_status or "unknown")
    if category == KnowledgeCategory.RESPONSIBILITIES_OWNERSHIP:
        # Preserve distinct person_identity representations cleanly without merging near-matches.
        raw_identity = str(payload.get("person_identity") or "").strip().lower()
        comp_slug = _slugify_key(str(payload.get("component_or_workstream") or ""))
        role_slug = _slugify_key(str(payload.get("ownership_role") or ""))
        material = f"{category.value}|{raw_identity}|{comp_slug}|{role_slug}|{status_key}"
    elif category == KnowledgeCategory.DEPENDENCIES:
        src_slug = _slugify_key(str(payload.get("source_item") or ""))
        dst_slug = _slugify_key(str(payload.get("target_item") or ""))
        dep_type = _slugify_key(str(payload.get("dependency_type") or ""))
        direction = _slugify_key(str(payload.get("direction") or ""))
        material = f"{category.value}|{src_slug}|{dst_slug}|{dep_type}|{direction}|{status_key}"
    else:
        title_slug = _slugify_key(title)
        identity_suffix = (person_or_owner_label or "").strip().lower()
        material = f"{category.value}|{title_slug}|{status_key}|{identity_suffix}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _parse_optional_source_timestamp(chunks: list[ChunkPromptInput]) -> datetime | None:
    for ch in chunks:
        if ch.source_created_at_iso:
            try:
                return datetime.fromisoformat(ch.source_created_at_iso)
            except ValueError:
                continue
    return None


def _build_confidence_and_uncertainty(
    *,
    category: KnowledgeCategory,
    candidate: Any,
    payload: dict[str, Any],
    verified_links: list[VerifiedEvidenceLinkDraft],
    normalised_status: str | None,
) -> tuple[dict[str, Any], str | None, str, str]:
    """Compute honest epistemic status, support classification & missing-field flags."""
    missing_fields: list[str] = []
    if category == KnowledgeCategory.DECISIONS_RATIONALE:
        if not payload.get("decision_maker"):
            missing_fields.append("decision_maker")
        if not payload.get("decision_date"):
            missing_fields.append("decision_date")
        if not payload.get("rationale"):
            missing_fields.append("rationale")
    elif category == KnowledgeCategory.WORK_ITEMS:
        if not payload.get("assignee"):
            missing_fields.append("assignee")
        if not (
            payload.get("created_date")
            or payload.get("updated_date")
            or payload.get("completed_date")
        ):
            missing_fields.append("work_dates")
    elif category == KnowledgeCategory.RESPONSIBILITIES_OWNERSHIP:
        if not payload.get("start_or_observed_date"):
            missing_fields.append("start_or_observed_date")
    elif category == KnowledgeCategory.BUGS_BLOCKERS_RISKS:
        if payload.get("severity") == "unspecified":
            missing_fields.append("severity")
        if not payload.get("reported_date"):
            missing_fields.append("reported_date")

    has_date = bool(
        payload.get("decision_date")
        or payload.get("completed_date")
        or payload.get("updated_date")
        or payload.get("created_date")
        or payload.get("start_or_observed_date")
        or payload.get("reported_date")
    )
    temporal_certainty = "exact_date" if has_date else "missing"

    has_attribution = bool(
        payload.get("decision_maker")
        or payload.get("assignee")
        or payload.get("creator")
        or payload.get("person_identity")
        or payload.get("responsible_person")
    )
    attribution_certainty = "explicit" if has_attribution else "missing"
    if (
        category == KnowledgeCategory.RESPONSIBILITIES_OWNERSHIP
        and payload.get("ownership_basis") in {"inferred_contribution", "unconfirmed"}
    ):
        attribution_certainty = "inferred"

    is_interpretation = bool(candidate.is_interpretation) or any(
        link.support_type == "interpretation" for link in verified_links
    )
    if (
        category == KnowledgeCategory.RESPONSIBILITIES_OWNERSHIP
        and payload.get("ownership_basis") == "inferred_contribution"
    ):
        is_interpretation = True

    is_uncertain = (
        bool(candidate.is_uncertain)
        or normalised_status in {"unclear", "unknown", "unconfirmed"}
        or any(link.support_type == "uncertain" for link in verified_links)
    )

    if is_uncertain:
        support_classification = SupportClassification.UNCERTAIN.value
    elif is_interpretation:
        support_classification = SupportClassification.INTERPRETATION.value
    elif len({link.evidence_id for link in verified_links}) > 1:
        support_classification = SupportClassification.CORROBORATED.value
    else:
        support_classification = SupportClassification.DIRECT.value

    # LLM may NEVER produce `human_verified`.
    epistemic_status = (
        EpistemicStatus.AI_INTERPRETED.value
        if is_interpretation
        else EpistemicStatus.EXTRACTED.value
    )

    uncertainty_reason = candidate.uncertainty_reason
    if (is_uncertain or is_interpretation) and not uncertainty_reason:
        if normalised_status in {"unclear", "unknown", "unconfirmed"}:
            uncertainty_reason = f"Status could not be confirmed beyond '{normalised_status}'."
        elif is_interpretation:
            uncertainty_reason = "Derived via AI interpretation of supporting source evidence."
        else:
            uncertainty_reason = "Source evidence contains ambiguity or missing details."

    completeness = (
        "complete"
        if not missing_fields
        else ("partial" if len(missing_fields) <= 2 else "incomplete")
    )
    evidence_quality = (
        "weak_or_indirect"
        if support_classification in {SupportClassification.UNCERTAIN.value}
        else ("partial" if is_interpretation else "explicit")
    )

    confidence_meta = ConfidenceMetadata(
        extraction_confidence=ConfidenceLevel(candidate.confidence_level),
        evidence_support_quality=evidence_quality,
        information_completeness=completeness,
        attribution_certainty=attribution_certainty,
        temporal_certainty=temporal_certainty,
        missing_fields=missing_fields,
        conflict_or_ambiguity_flag=bool(is_uncertain),
    ).model_dump(mode="json")

    return confidence_meta, uncertainty_reason, epistemic_status, support_classification


class KnowledgeCandidateValidator:
    """Validates raw LLM JSON items against category schemas and canonical chunk texts."""

    def validate_batch_response(
        self,
        *,
        category: KnowledgeCategory,
        parsed_json: dict[str, Any],
        supplied_chunks: list[ChunkPromptInput],
        is_synthetic: bool,
    ) -> BatchValidationReport:
        report = BatchValidationReport()
        raw_items = parsed_json.get("items")
        if not isinstance(raw_items, list):
            report.rejection_reasons.append("missing_items_array")
            return report

        supplied_by_id = {str(ch.chunk_id): ch for ch in supplied_chunks}
        model_cls = _CANDIDATE_MODEL_BY_CATEGORY[category]
        report.candidates_received = len(raw_items)

        for raw_entry in raw_items:
            if not isinstance(raw_entry, dict):
                report.rejected_schema_count += 1
                report.rejection_reasons.append("candidate_not_object")
                continue

            try:
                candidate = model_cls.model_validate(raw_entry)
            except ValidationError as exc:
                report.rejected_schema_count += 1
                first_err = exc.errors()[0].get("loc", ("schema",))
                loc_tag = ".".join(map(str, first_err))
                report.rejection_reasons.append(f"schema_validation_failed:{loc_tag}")
                continue

            verified_links: list[VerifiedEvidenceLinkDraft] = []
            cited_chunks: list[ChunkPromptInput] = []
            seen_link_keys: set[tuple[uuid.UUID, str]] = set()
            ref_rejection: str | None = None

            ref_list: list[CandidateEvidenceRef] = candidate.evidence_refs
            for ref in ref_list:
                chunk_input = supplied_by_id.get(ref.chunk_id)
                if chunk_input is None:
                    ref_rejection = "cited_chunk_not_in_supplied_context"
                    continue
                ok, match_mode, match_err = verify_excerpt_in_chunk(
                    excerpt=ref.supporting_excerpt,
                    chunk_text=chunk_input.chunk_text,
                )
                if not ok or match_mode is None:
                    ref_rejection = match_err
                    continue

                dedup_key = (chunk_input.chunk_id, ref.supporting_excerpt)
                if dedup_key in seen_link_keys:
                    continue
                seen_link_keys.add(dedup_key)

                cited_chunks.append(chunk_input)
                verified_links.append(
                    VerifiedEvidenceLinkDraft(
                        evidence_id=chunk_input.evidence_id,
                        evidence_chunk_id=chunk_input.chunk_id,
                        support_type=ref.support_type,
                        source_location={
                            "chunk_index": chunk_input.chunk_index,
                            "chunk_type": chunk_input.chunk_type,
                            "page_number": chunk_input.page_number,
                            "section_title": chunk_input.section_title,
                            "char_start": chunk_input.char_start,
                            "char_end": chunk_input.char_end,
                        },
                        supporting_excerpt=ref.supporting_excerpt,
                        excerpt_match_mode=match_mode,
                        source_metadata={
                            "source_type": chunk_input.source_type,
                            "source_provider": chunk_input.source_provider,
                            "source_external_id": chunk_input.source_external_id,
                            "source_url": chunk_input.source_url,
                            "title": chunk_input.title,
                            "source_author_identity": chunk_input.source_author_identity,
                            "source_created_at": chunk_input.source_created_at_iso,
                            "source_updated_at": chunk_input.source_updated_at_iso,
                            "extracted_at": chunk_input.extracted_at_iso,
                            "evidence_content_hash": chunk_input.evidence_content_hash,
                            "chunk_content_hash": chunk_input.chunk_content_hash,
                        },
                    )
                )

            if not verified_links:
                report.rejected_ungrounded_count += 1
                report.rejection_reasons.append(ref_rejection or "no_verified_evidence_links")
                continue

            payload = candidate.model_dump(
                mode="json",
                exclude={
                    "title",
                    "description",
                    "is_interpretation",
                    "is_uncertain",
                    "uncertainty_reason",
                    "confidence_level",
                    "evidence_refs",
                },
            )
            payload["description"] = candidate.description

            # Guard against hallucinated severity in bugs_blockers_risks.
            if (
                category == KnowledgeCategory.BUGS_BLOCKERS_RISKS
                and payload.get("severity") not in (None, "unspecified")
            ):
                combined_excerpts = " ".join(link.supporting_excerpt for link in verified_links)
                combined_chunks = " ".join(ch.chunk_text for ch in cited_chunks)
                if not (
                    _EXPLICIT_SEVERITY_RE.search(combined_excerpts)
                    or _EXPLICIT_SEVERITY_RE.search(combined_chunks)
                ):
                    payload["severity"] = "unspecified"

            normalised_status = _extract_normalised_status(category, payload)
            person_label = _extract_person_label(category, payload)
            confidence_meta, uncertainty_reason, epistemic_status, support_classification = (
                _build_confidence_and_uncertainty(
                    category=category,
                    candidate=candidate,
                    payload=payload,
                    verified_links=verified_links,
                    normalised_status=normalised_status,
                )
            )
            fingerprint = compute_conservative_fingerprint(
                category=category,
                title=candidate.title,
                payload=payload,
                normalised_status=normalised_status,
                person_or_owner_label=person_label,
            )

            primary = cited_chunks[0]
            source_attribution = {
                "source_type": primary.source_type,
                "source_provider": primary.source_provider,
                "source_external_id": primary.source_external_id,
                "source_url": primary.source_url,
                "source_author_identity": primary.source_author_identity,
                "title": primary.title,
                "source_created_at": primary.source_created_at_iso,
                "evidence_count": len({link.evidence_id for link in verified_links}),
            }

            report.accepted_items.append(
                ValidatedKnowledgeItemDraft(
                    category=category,
                    epistemic_status=epistemic_status,
                    review_status=KnowledgeReviewStatus.PENDING_REVIEW.value,
                    support_classification=support_classification,
                    title=candidate.title,
                    structured_summary=candidate.description,
                    structured_payload=payload,
                    normalised_status=normalised_status,
                    person_or_owner_label=person_label,
                    source_attribution=source_attribution,
                    fingerprint=fingerprint,
                    confidence_metadata=confidence_meta,
                    uncertainty_reason=uncertainty_reason,
                    source_observed_at=_parse_optional_source_timestamp(cited_chunks),
                    is_synthetic=is_synthetic,
                    evidence_links=tuple(verified_links),
                )
            )

        return report
