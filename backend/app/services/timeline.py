"""Chronological project knowledge and evidence timeline synthesis service."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import Field
from sqlalchemy.orm import Session

from app.models.enums import KnowledgeReviewStatus
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.common import BaseSchema
from app.services.knowledge_domains import map_category_to_domain

_ISO_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class TimelineEventResponse(BaseSchema):
    """Normalized chronological timeline event synthesizing knowledge and evidence."""

    id: str
    event_type: str
    event_title: str
    event_summary: str
    primary_domain: str
    category: str
    timestamp: datetime
    timestamp_precision: Literal["second", "day"]
    source_provider: str
    source_url: str | None = None
    author_label: str | None = None
    epistemic_status: str
    review_status: str
    support_classification: str
    confidence_level: str
    is_verified: bool
    evidence_count: int
    knowledge_item_id: uuid.UUID | None = None
    evidence_id: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectTimelineResponse(BaseSchema):
    """Paginated timeline event stream with summary metrics."""

    items: list[TimelineEventResponse]
    total_events: int
    domains_represented: list[str]
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
    limit: int
    offset: int


def _parse_flexible_timestamp(
    raw_val: Any, fallback: datetime
) -> tuple[datetime, Literal["second", "day"]]:
    """Parse string or datetime into a UTC datetime and precision indicator."""
    if isinstance(raw_val, datetime):
        dt = raw_val if raw_val.tzinfo else raw_val.replace(tzinfo=UTC)
        return dt, "second"

    if isinstance(raw_val, str):
        val_str = raw_val.strip()
        if _ISO_DAY_RE.match(val_str):
            try:
                parsed_day = datetime.strptime(val_str, "%Y-%m-%d").replace(tzinfo=UTC)
                return parsed_day, "day"
            except ValueError:
                pass
        try:
            # ISO timestamp
            parsed_iso = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
            if not parsed_iso.tzinfo:
                parsed_iso = parsed_iso.replace(tzinfo=UTC)
            return parsed_iso, "second"
        except (ValueError, TypeError):
            pass

    fb_dt = fallback if fallback.tzinfo else fallback.replace(tzinfo=UTC)
    return fb_dt, "second"


def _derive_event_type(category: str, payload: dict[str, Any], status: str | None) -> str:
    """Map category and structured payload into a domain-specific event type."""
    cat_upper = category.upper()
    st_lower = (status or "").lower()

    if "DECISION" in cat_upper:
        return (
            f"decision_{st_lower}"
            if st_lower in {"accepted", "proposed", "superseded", "rejected"}
            else "decision"
        )
    if "WORK" in cat_upper:
        if st_lower in {"completed", "done", "closed"}:
            return "work_completed"
        if st_lower in {"in_progress", "active"}:
            return "work_in_progress"
        return "work_item"
    if "RISK" in cat_upper or "BUG" in cat_upper:
        if st_lower in {"resolved", "mitigated"}:
            return "risk_resolved"
        return "risk_reported"
    if "OPERATIONAL" in cat_upper or "HISTORICAL" in cat_upper:
        k_type = str(payload.get("knowledge_type") or "").lower()
        if "incident" in k_type:
            return "incident"
        if "deployment" in k_type:
            return "deployment"
        return "historical_milestone"
    if "OVERVIEW" in cat_upper:
        return "project_charter"
    if "ARCHITECTURE" in cat_upper or "TECHNICAL" in cat_upper:
        return "architecture_record"
    if "DEPENDENCY" in cat_upper or "DEPENDENCIES" in cat_upper:
        return "dependency_defined"
    if "RESPONSIBILITY" in cat_upper or "OWNERSHIP" in cat_upper:
        return "ownership_assignment"
    return "general_event"


class ProjectTimelineService:
    """Synthesizes chronological timeline events from permission-filtered knowledge items."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = KnowledgeRepository(session)

    def get_timeline(
        self,
        *,
        project_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
        has_project_manage: bool,
        domain: str | None = None,
        source_provider: str | None = None,
        event_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_order: Literal["asc", "desc"] = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> ProjectTimelineResponse:
        """Query accessible knowledge items and compile a unified chronological event stream."""
        # Query items across the project with source ACL enforcement
        accessible_results, total_count = self._repo.list_accessible_items_for_project(
            project_id=project_id,
            viewer_user_id=viewer_user_id,
            has_project_manage=has_project_manage,
            domain=domain,
            source_provider=source_provider,
            date_from=date_from,
            date_to=date_to,
            include_stale=False,
            stale_only=False,
            include_synthetic=False,
            limit=500,  # pull up to 500 candidate items to construct the chronological stream
            offset=0,
        )

        events: list[TimelineEventResponse] = []
        domains_found: set[str] = set()

        for res in accessible_results:
            item = res.item
            payload = dict(item.structured_payload or {})
            attribution = dict(item.source_attribution_json or {})
            confidence = dict(item.confidence_metadata_json or {})

            # Extract the most meaningful date for the event
            raw_date = (
                item.source_observed_at
                or payload.get("event_timestamp")
                or payload.get("decision_date")
                or payload.get("completed_date")
                or payload.get("reported_date")
                or payload.get("start_or_observed_date")
                or payload.get("created_date")
            )
            event_dt, precision = _parse_flexible_timestamp(raw_date, fallback=item.created_at)

            # Date range filter check if not filtered at SQL level
            if date_from and event_dt < date_from:
                continue
            if date_to and event_dt > date_to:
                continue

            primary_dom = item.primary_domain or map_category_to_domain(item.category).value
            domains_found.add(primary_dom)

            derived_type = _derive_event_type(item.category, payload, item.normalised_status)
            if event_type and event_type.lower() != derived_type.lower():
                continue

            # First accessible evidence link for direct navigation
            primary_link = res.accessible_links[0] if res.accessible_links else None
            source_url = (
                primary_link.source_metadata_json.get("source_url")
                if primary_link and primary_link.source_metadata_json
                else attribution.get("source_url")
            )
            provider = (
                primary_link.source_metadata_json.get("source_provider")
                if primary_link and primary_link.source_metadata_json
                else attribution.get("source_provider", "unknown")
            )

            is_verified = (item.review_status == KnowledgeReviewStatus.APPROVED.value) or (
                item.epistemic_status == "human_verified"
            )

            events.append(
                TimelineEventResponse(
                    id=str(item.id),
                    event_type=derived_type,
                    event_title=item.title,
                    event_summary=item.structured_summary,
                    primary_domain=primary_dom,
                    category=item.category,
                    timestamp=event_dt,
                    timestamp_precision=precision,
                    source_provider=str(provider),
                    source_url=source_url,
                    author_label=item.person_or_owner_label
                    or attribution.get("source_author_identity"),
                    epistemic_status=item.epistemic_status,
                    review_status=item.review_status,
                    support_classification=item.support_classification,
                    confidence_level=str(confidence.get("extraction_confidence", "medium")),
                    is_verified=is_verified,
                    evidence_count=len(res.accessible_links),
                    knowledge_item_id=item.id,
                    evidence_id=primary_link.evidence_id if primary_link else None,
                    metadata={
                        "normalised_status": item.normalised_status,
                        "uncertainty_reason": item.uncertainty_reason,
                        "match_mode": primary_link.excerpt_match_mode if primary_link else None,
                    },
                )
            )

        # Sort chronologically
        reverse = sort_order == "desc"
        events.sort(key=lambda ev: ev.timestamp, reverse=reverse)

        total_evs = len(events)
        paged_events = events[offset : offset + limit]

        date_start = (
            events[-1].timestamp
            if events and reverse
            else (events[0].timestamp if events else None)
        )
        date_end = (
            events[0].timestamp
            if events and reverse
            else (events[-1].timestamp if events else None)
        )

        return ProjectTimelineResponse(
            items=paged_events,
            total_events=total_evs,
            domains_represented=sorted(domains_found),
            date_range_start=date_start,
            date_range_end=date_end,
            limit=limit,
            offset=offset,
        )
