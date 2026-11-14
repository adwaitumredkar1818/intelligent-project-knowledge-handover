"""Multi-signal Identity Resolution service for Relationship Explorer.

Evaluates candidate entity duplicates across sources (e.g. GitHub vs Jira vs Slack)
using 5 weighted signals:
1. Exact canonical string match (weight 0.40)
2. Normalized email/handle match (weight 0.25)
3. Source provider cross-reference (weight 0.15)
4. Shared context/file overlap (weight 0.10)
5. Semantic embedding similarity (weight 0.10)

Policy bands:
- auto_merge: score >= 0.95 (NON-PERSON entities ONLY)
- manual_review: 0.70 <= score < 0.95
- unresolved: score < 0.70

SAFETY OVERRIDE:
Entities with `entity_type == 'person'` are NEVER auto-merged. Even at 1.00 score,
they are placed in `manual_review` for authorized human verification.
"""

from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.enums import (
    EntityResolutionStatus,
    EntityType,
    IdentityCandidateStatus,
    IdentityPolicyBand,
)
from app.models.relationship import IdentityResolutionCandidate, KnowledgeEntity
from app.repositories.relationship import EntityRepository

logger = logging.getLogger("app.services.identity_resolution")

# Signal Weights
W_NAME_EXACT: float = 0.40
W_HANDLE_EMAIL: float = 0.25
W_SOURCE_XREF: float = 0.15
W_SHARED_CONTEXT: float = 0.10
W_SEMANTIC_SIM: float = 0.10


@dataclass(frozen=True, slots=True)
class IdentityMatchSignal:
    """Breakdown of individual signal scores comparing two entities."""

    name_exact_score: float
    handle_email_score: float
    source_xref_score: float
    shared_context_score: float
    semantic_score: float
    aggregate_score: float
    policy_band: str


class IdentityResolutionService:
    """Calculates identity match scores, enforces person safety, and manages reversible merges."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._entity_repo = EntityRepository(session)

    def compute_match_signal(
        self,
        left: KnowledgeEntity,
        right: KnowledgeEntity,
        *,
        semantic_similarity: float = 0.0,
    ) -> IdentityMatchSignal:
        """Compute the weighted 5-signal identity match score between two entities."""
        # 1. Exact / Fuzzy Canonical Name Score (weight 0.40)
        norm_left = (left.canonical_name or "").strip().lower()
        norm_right = (right.canonical_name or "").strip().lower()
        if norm_left == norm_right:
            name_score = 1.0
        else:
            name_score = difflib.SequenceMatcher(None, norm_left, norm_right).ratio()

        # 2. Normalized Email / Handle Score (weight 0.25)
        left_aliases = {a.normalized_alias for a in left.aliases}
        right_aliases = {a.normalized_alias for a in right.aliases}
        common_aliases = left_aliases.intersection(right_aliases)
        handle_score = 1.0 if common_aliases else 0.0

        # 3. Source Provider Cross-Reference (weight 0.15)
        # If one entity is GitHub and other is Jira/Slack, cross-provider matching is valued
        left_providers = {left.source_provider} | {a.source_provider for a in left.aliases}
        right_providers = {right.source_provider} | {a.source_provider for a in right.aliases}
        left_providers.discard(None)
        right_providers.discard(None)
        # If they come from different providers but share handles/names, strong xref
        if left_providers and right_providers and not left_providers.intersection(right_providers):
            xref_score = 1.0 if (name_score > 0.8 or handle_score > 0.5) else 0.0
        else:
            xref_score = 0.5 if (name_score > 0.8) else 0.0

        # 4. Shared Context / Metadata Overlap (weight 0.10)
        left_meta = left.metadata_json or {}
        right_meta = right.metadata_json or {}
        shared_keys = set(left_meta.keys()).intersection(right_meta.keys())
        context_score = 0.0
        if shared_keys:
            matches = sum(
                1 for k in shared_keys if str(left_meta[k]).lower() == str(right_meta[k]).lower()
            )
            context_score = matches / len(shared_keys)

        # 5. Semantic Embedding Similarity (weight 0.10)
        sem_score = max(0.0, min(1.0, semantic_similarity))

        aggregate = (
            (W_NAME_EXACT * name_score)
            + (W_HANDLE_EMAIL * handle_score)
            + (W_SOURCE_XREF * xref_score)
            + (W_SHARED_CONTEXT * context_score)
            + (W_SEMANTIC_SIM * sem_score)
        )
        aggregate = round(aggregate, 3)

        # Determine Policy Band with Safety Override
        is_person = (
            left.entity_type == EntityType.PERSON.value
            or right.entity_type == EntityType.PERSON.value
        )

        if aggregate >= 0.95:
            # Person entities MUST NEVER be auto-merged
            band = (
                IdentityPolicyBand.MANUAL_REVIEW.value
                if is_person
                else IdentityPolicyBand.AUTO_MERGE.value
            )
        elif aggregate >= 0.70:
            band = IdentityPolicyBand.MANUAL_REVIEW.value
        else:
            band = IdentityPolicyBand.UNRESOLVED.value

        return IdentityMatchSignal(
            name_exact_score=round(name_score, 3),
            handle_email_score=round(handle_score, 3),
            source_xref_score=round(xref_score, 3),
            shared_context_score=round(context_score, 3),
            semantic_score=round(sem_score, 3),
            aggregate_score=aggregate,
            policy_band=band,
        )

    def evaluate_and_record_candidate(
        self,
        left: KnowledgeEntity,
        right: KnowledgeEntity,
        *,
        semantic_similarity: float = 0.0,
    ) -> IdentityResolutionCandidate | None:
        """Evaluate two entities and record candidate if score >= 0.70.

        Strict Safety Boundaries:
        1. Never merge across organisations.
        2. Never merge across projects without explicit boundary scope.
        3. Never self-reference.
        4. Never merge mismatched entity types.
        """
        if left.id == right.id:
            return None
        if left.organisation_id != right.organisation_id:
            logger.warning(
                "Rejected candidate: cross-organisation entities %s and %s", left.id, right.id
            )
            return None
        if left.project_id != right.project_id:
            logger.warning(
                "Rejected candidate: cross-project entities %s and %s", left.id, right.id
            )
            return None
        if left.entity_type != right.entity_type:
            return None

        signal = self.compute_match_signal(left, right, semantic_similarity=semantic_similarity)
        if signal.aggregate_score < 0.70:
            return None

        breakdown = {
            "name_exact_score": signal.name_exact_score,
            "handle_email_score": signal.handle_email_score,
            "source_xref_score": signal.source_xref_score,
            "shared_context_score": signal.shared_context_score,
            "semantic_score": signal.semantic_score,
            "aggregate_score": signal.aggregate_score,
            "is_person_safety_applied": (left.entity_type == EntityType.PERSON.value),
        }

        cand = self._entity_repo.create_identity_candidate(
            organisation_id=left.organisation_id,
            project_id=left.project_id,
            left_entity_id=left.id,
            right_entity_id=right.id,
            match_score=signal.aggregate_score,
            signal_breakdown_json=breakdown,
            policy_band=signal.policy_band,
        )

        # If auto-merge policy applies (strictly non-person entities)
        if signal.policy_band == IdentityPolicyBand.AUTO_MERGE.value:
            cand.decision_status = IdentityCandidateStatus.ACCEPTED.value
            cand.decision_rationale = (
                "Auto-merged based on identity policy band (score >= 0.95, non-person)."
            )
            right.resolution_status = EntityResolutionStatus.MERGED.value
            right.merged_into_entity_id = left.id
            cand.previous_state_json = {
                "right_entity_id": str(right.id),
                "resolution_status": EntityResolutionStatus.CANONICAL.value,
                "merged_into_entity_id": None,
            }
            self._session.flush()

        return cand
