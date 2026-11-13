"""FastAPI HTTP endpoints for Verification Center (Module 3 / Validation Area).

Provides:
- Paginated human review queue and summary metrics
- Case detail inspection with side-by-side evidence and conflict comparison
- Atomic human review actions (approve, reject, edit, mark unresolved, assign)
- In-platform context requests and response handling
- Handover eligibility verification gate checks
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db_session, require_project_permission
from app.models.enums import (
    ContextRequestStatus,
    VerificationCaseStatus,
    VerificationPriority,
    VerificationTargetType,
)
from app.models.knowledge import KnowledgeEvidenceLink, KnowledgeItem
from app.models.relationship import KnowledgeRelationship
from app.models.verification import VerificationCase
from app.repositories.verification import (
    VerificationCaseRepository,
    VerificationContextRequestRepository,
)
from app.schemas.verification import (
    ApproveCaseRequest,
    AssignReviewerRequest,
    EditFindingRequest,
    HandoverEligibilityResponse,
    MarkUnresolvedRequest,
    RejectCaseRequest,
    RequestContextRequest,
    RespondContextRequest,
    VerificationCaseDetailResponse,
    VerificationCaseItemResponse,
    VerificationConflictResponse,
    VerificationContextRequestResponse,
    VerificationIssueResponse,
    VerificationQueueResponse,
    VerificationReviewEventResponse,
    VerificationSummaryResponse,
)
from app.services.handover_eligibility import (
    HandoverEligibilityService,
    check_evidence_accessibility,
)
from app.services.rbac import ProjectContext
from app.services.verification_engine import DeterministicVerificationEngine
from app.services.verification_review import (
    ConcurrencyConflictError,
    HumanReviewService,
    ReviewValidationError,
)

router = APIRouter(tags=["Verification Center"])


def _str_val(val: Any) -> str:
    if hasattr(val, "value"):
        return str(val.value)
    return str(val) if val is not None else ""


def _to_case_item_response(case: VerificationCase) -> VerificationCaseItemResponse:
    open_issues = [
        i for i in getattr(case, "issues", []) if getattr(i, "resolution_state", "") == "open"
    ]
    open_conflicts = [
        c
        for c in getattr(case, "conflicts", [])
        if getattr(c, "resolution_state", "") == "unresolved"
    ]
    return VerificationCaseItemResponse(
        id=case.id,
        organisation_id=case.organisation_id,
        project_id=case.project_id,
        target_type=_str_val(case.target_type),
        target_id=case.target_id,
        case_status=_str_val(case.case_status),
        machine_assessment_status=_str_val(case.machine_assessment_status),
        priority=_str_val(case.priority),
        assigned_reviewer_id=case.assigned_reviewer_id,
        machine_assessment_json=case.machine_assessment_json or {},
        version=case.version,
        open_issues_count=len(open_issues),
        open_conflicts_count=len(open_conflicts),
        last_assessed_at=case.last_assessed_at,
        last_reviewed_at=case.last_reviewed_at,
        resolved_at=case.resolved_at,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


def _to_case_detail_response(
    case: VerificationCase, session: Session, *, viewer_user_id: uuid.UUID, has_manage: bool
) -> VerificationCaseDetailResponse:
    # Fetch target data
    target_data: dict[str, Any] = {}
    if _str_val(case.target_type) == _str_val(VerificationTargetType.KNOWLEDGE_ITEM):
        item = session.get(KnowledgeItem, case.target_id)
        if item:
            target_data = {
                "id": str(item.id),
                "title": item.title,
                "summary": getattr(item, "structured_summary", None)
                or getattr(item, "summary", ""),
                "knowledge_domain": getattr(item, "primary_domain", None)
                or getattr(item, "category", ""),
                "epistemic_status": _str_val(item.epistemic_status),
                "review_status": _str_val(item.review_status),
                "confidence_score": float(item.confidence_score)
                if getattr(item, "confidence_score", None) is not None
                else None,
                "item_payload": getattr(item, "structured_payload", None)
                or getattr(item, "item_payload", {}),
            }
    elif _str_val(case.target_type) == _str_val(VerificationTargetType.RELATIONSHIP):
        rel = session.get(KnowledgeRelationship, case.target_id)
        if rel:
            target_data = {
                "id": str(rel.id),
                "relationship_type": rel.relationship_type,
                "relationship_basis": rel.relationship_basis,
                "source_entity_id": str(rel.source_entity_id),
                "target_entity_id": str(rel.target_entity_id),
                "verification_status": rel.verification_status,
                "confidence_score": float(rel.confidence_score)
                if rel.confidence_score is not None
                else None,
            }

    issues_resp = [VerificationIssueResponse.model_validate(i) for i in getattr(case, "issues", [])]
    conflicts_resp = [
        VerificationConflictResponse.model_validate(c) for c in getattr(case, "conflicts", [])
    ]
    events_resp = [
        VerificationReviewEventResponse.model_validate(e)
        for e in getattr(case, "review_events", [])
    ]
    context_resp = [
        VerificationContextRequestResponse.model_validate(r)
        for r in getattr(case, "context_requests", [])
    ]

    return VerificationCaseDetailResponse(
        id=case.id,
        organisation_id=case.organisation_id,
        project_id=case.project_id,
        target_type=_str_val(case.target_type),
        target_id=case.target_id,
        case_status=_str_val(case.case_status),
        machine_assessment_status=_str_val(case.machine_assessment_status),
        priority=_str_val(case.priority),
        assigned_reviewer_id=case.assigned_reviewer_id,
        machine_assessment_json=case.machine_assessment_json or {},
        version=case.version,
        last_assessed_at=case.last_assessed_at,
        last_reviewed_at=case.last_reviewed_at,
        resolved_at=case.resolved_at,
        created_at=case.created_at,
        updated_at=case.updated_at,
        target_data=target_data,
        issues=issues_resp,
        conflicts=conflicts_resp,
        review_events=events_resp,
        context_requests=context_resp,
    )


# ==============================================================================
# Queue & Summary
# ==============================================================================


@router.get(
    "/projects/{project_id}/verification/queue",
    response_model=VerificationQueueResponse,
    status_code=status.HTTP_200_OK,
    summary="List verification cases in the human review queue",
)
def list_verification_queue(
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
    case_status: Annotated[VerificationCaseStatus | None, Query()] = None,
    priority: Annotated[VerificationPriority | None, Query()] = None,
    target_type: Annotated[VerificationTargetType | None, Query()] = None,
    assigned_reviewer_id: Annotated[uuid.UUID | None, Query()] = None,
    unassigned_only: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> VerificationQueueResponse:
    repo = VerificationCaseRepository(db_session)
    items = repo.list_queue(
        project_ctx.project.id,
        case_status=case_status,
        priority=priority,
        target_type=target_type,
        assigned_reviewer_id=assigned_reviewer_id,
        unassigned_only=unassigned_only,
        limit=limit,
        offset=offset,
    )
    total = repo.count_queue(
        project_ctx.project.id,
        case_status=case_status,
        priority=priority,
        target_type=target_type,
        assigned_reviewer_id=assigned_reviewer_id,
        unassigned_only=unassigned_only,
    )
    return VerificationQueueResponse(
        items=[_to_case_item_response(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/projects/{project_id}/verification/summary",
    response_model=VerificationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Aggregated project verification statistics",
)
def get_verification_summary(
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VerificationSummaryResponse:
    repo = VerificationCaseRepository(db_session)
    summary_data = repo.get_summary(project_ctx.project.id)
    return VerificationSummaryResponse(**summary_data)


# ==============================================================================
# Case Details & Evidence Inspection
# ==============================================================================


@router.get(
    "/projects/{project_id}/verification/cases/{case_id}",
    response_model=VerificationCaseDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get complete details, issues, and audit history of a verification case",
)
def get_verification_case(
    case_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VerificationCaseDetailResponse:
    repo = VerificationCaseRepository(db_session)
    case = repo.get_by_id(case_id, load_relationships=True)
    if not case or case.project_id != project_ctx.project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Verification case not found."
        )

    has_manage = project_ctx.has_permission("project.manage")
    return _to_case_detail_response(
        case, db_session, viewer_user_id=project_ctx.user_id, has_manage=has_manage
    )


@router.get(
    "/projects/{project_id}/verification/cases/{case_id}/evidence",
    status_code=status.HTTP_200_OK,
    summary="Get side-by-side supporting and contradictory evidence for a case",
)
def get_case_evidence_details(
    case_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    repo = VerificationCaseRepository(db_session)
    case = repo.get_by_id(case_id, load_relationships=True)
    if not case or case.project_id != project_ctx.project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Verification case not found."
        )

    has_manage = project_ctx.has_permission("project.manage")

    # Fetch supporting links
    supporting_evidence: list[dict[str, Any]] = []
    if _str_val(case.target_type) == _str_val(VerificationTargetType.KNOWLEDGE_ITEM):
        links = list(
            db_session.execute(
                select(KnowledgeEvidenceLink)
                .where(KnowledgeEvidenceLink.knowledge_item_id == case.target_id)
                .options(
                    selectinload(KnowledgeEvidenceLink.evidence_item),
                    selectinload(KnowledgeEvidenceLink.evidence_chunk),
                )
            )
            .scalars()
            .all()
        )
        for link in links:
            ev = link.evidence_item
            if not ev:
                continue
            accessible, _ = check_evidence_accessibility(
                db_session,
                [ev.id],
                project_id=case.project_id,
                viewer_user_id=project_ctx.user_id,
                has_project_manage=has_manage,
            )
            if not accessible:
                supporting_evidence.append(
                    {
                        "evidence_id": str(ev.id),
                        "restricted": True,
                        "reason": "Source restricted by project ACLs",
                    }
                )
                continue

            supporting_evidence.append(
                {
                    "evidence_id": str(ev.id),
                    "title": ev.title,
                    "source_type": ev.source_type,
                    "source_url": ev.source_url,
                    "supporting_excerpt": link.supporting_excerpt,
                    "chunk_id": str(link.evidence_chunk_id) if link.evidence_chunk_id else None,
                    "chunk_text": getattr(link.evidence_chunk, "chunk_text", None),
                    "confidence_score": float(link.confidence_score)
                    if getattr(link, "confidence_score", None) is not None
                    else None,
                    "restricted": False,
                }
            )

    # Conflicts
    conflicts_data: list[dict[str, Any]] = []
    for c in getattr(case, "conflicts", []):
        conflicts_data.append(
            {
                "id": str(c.id),
                "conflict_type": _str_val(c.conflict_type),
                "claim_a_text": c.claim_a_text,
                "claim_a_evidence_id": str(c.claim_a_source_evidence_id),
                "claim_a_timestamp": c.claim_a_source_timestamp.isoformat()
                if c.claim_a_source_timestamp
                else None,
                "claim_b_text": c.claim_b_text,
                "claim_b_evidence_id": str(c.claim_b_source_evidence_id),
                "claim_b_timestamp": c.claim_b_source_timestamp.isoformat()
                if c.claim_b_source_timestamp
                else None,
                "explanation": c.explanation,
                "temporal_comparison": _str_val(c.temporal_comparison),
                "resolution_state": _str_val(c.resolution_state),
            }
        )

    return {
        "case_id": str(case.id),
        "target_type": _str_val(case.target_type),
        "target_id": str(case.target_id),
        "supporting_evidence": supporting_evidence,
        "conflicts": conflicts_data,
    }


# ==============================================================================
# Human Review Actions (Require project.knowledge.review)
# ==============================================================================


@router.post(
    "/projects/{project_id}/verification/cases/{case_id}/approve",
    response_model=VerificationCaseDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve finding as human-verified project knowledge",
)
def approve_case(
    case_id: uuid.UUID,
    payload: ApproveCaseRequest,
    project_ctx: Annotated[
        ProjectContext, Depends(require_project_permission("project.knowledge.review"))
    ],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VerificationCaseDetailResponse:
    service = HumanReviewService(db_session)
    try:
        case = service.approve(
            case_id=case_id,
            reviewer_user_id=project_ctx.user_id,
            expected_version=payload.expected_version,
            review_notes=payload.review_notes,
        )
        db_session.commit()
    except ConcurrencyConflictError as exc:
        db_session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ReviewValidationError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:
        db_session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    has_manage = project_ctx.has_permission("project.manage")
    return _to_case_detail_response(
        case, db_session, viewer_user_id=project_ctx.user_id, has_manage=has_manage
    )


@router.post(
    "/projects/{project_id}/verification/cases/{case_id}/reject",
    response_model=VerificationCaseDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject candidate finding or relationship",
)
def reject_case(
    case_id: uuid.UUID,
    payload: RejectCaseRequest,
    project_ctx: Annotated[
        ProjectContext, Depends(require_project_permission("project.knowledge.review"))
    ],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VerificationCaseDetailResponse:
    service = HumanReviewService(db_session)
    try:
        case = service.reject(
            case_id=case_id,
            reviewer_user_id=project_ctx.user_id,
            expected_version=payload.expected_version,
            reason=payload.reason,
            review_notes=payload.review_notes,
        )
        db_session.commit()
    except ConcurrencyConflictError as exc:
        db_session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        db_session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    has_manage = project_ctx.has_permission("project.manage")
    return _to_case_detail_response(
        case, db_session, viewer_user_id=project_ctx.user_id, has_manage=has_manage
    )


@router.patch(
    "/projects/{project_id}/verification/cases/{case_id}/finding",
    response_model=VerificationCaseDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Correct finding fields with version tracking and full audit diff",
)
def edit_case_finding(
    case_id: uuid.UUID,
    payload: EditFindingRequest,
    project_ctx: Annotated[
        ProjectContext, Depends(require_project_permission("project.knowledge.review"))
    ],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VerificationCaseDetailResponse:
    service = HumanReviewService(db_session)
    try:
        case = service.edit_finding(
            case_id=case_id,
            reviewer_user_id=project_ctx.user_id,
            expected_version=payload.expected_version,
            patch_data=payload.patch_data,
            reason=payload.reason,
        )
        db_session.commit()
    except ConcurrencyConflictError as exc:
        db_session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ReviewValidationError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:
        db_session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    has_manage = project_ctx.has_permission("project.manage")
    return _to_case_detail_response(
        case, db_session, viewer_user_id=project_ctx.user_id, has_manage=has_manage
    )


@router.post(
    "/projects/{project_id}/verification/cases/{case_id}/request-context",
    response_model=VerificationContextRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch clarification question to team member",
)
def request_case_context(
    case_id: uuid.UUID,
    payload: RequestContextRequest,
    project_ctx: Annotated[
        ProjectContext, Depends(require_project_permission("project.knowledge.review"))
    ],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VerificationContextRequestResponse:
    service = HumanReviewService(db_session)
    try:
        req = service.request_context(
            case_id=case_id,
            reviewer_user_id=project_ctx.user_id,
            requested_from_user_id=payload.requested_from_user_id,
            question=payload.question,
            requested_information_type=payload.requested_information_type,
            expected_version=payload.expected_version,
        )
        db_session.commit()
    except ConcurrencyConflictError as exc:
        db_session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        db_session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return VerificationContextRequestResponse.model_validate(req)


@router.post(
    "/projects/{project_id}/verification/cases/{case_id}/mark-unresolved",
    response_model=VerificationCaseDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark case as unresolved when consensus cannot be established",
)
def mark_case_unresolved(
    case_id: uuid.UUID,
    payload: MarkUnresolvedRequest,
    project_ctx: Annotated[
        ProjectContext, Depends(require_project_permission("project.knowledge.review"))
    ],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VerificationCaseDetailResponse:
    service = HumanReviewService(db_session)
    try:
        case = service.mark_unresolved(
            case_id=case_id,
            reviewer_user_id=project_ctx.user_id,
            expected_version=payload.expected_version,
            explanation=payload.explanation,
        )
        db_session.commit()
    except ConcurrencyConflictError as exc:
        db_session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        db_session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    has_manage = project_ctx.has_permission("project.manage")
    return _to_case_detail_response(
        case, db_session, viewer_user_id=project_ctx.user_id, has_manage=has_manage
    )


@router.post(
    "/projects/{project_id}/verification/cases/{case_id}/assign",
    response_model=VerificationCaseDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign or reassign review case",
)
def assign_case_reviewer(
    case_id: uuid.UUID,
    payload: AssignReviewerRequest,
    project_ctx: Annotated[
        ProjectContext, Depends(require_project_permission("project.knowledge.review"))
    ],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VerificationCaseDetailResponse:
    service = HumanReviewService(db_session)
    try:
        case = service.assign_reviewer(
            case_id=case_id,
            actor_user_id=project_ctx.user_id,
            assignee_user_id=payload.assignee_user_id,
            expected_version=payload.expected_version,
        )
        db_session.commit()
    except ConcurrencyConflictError as exc:
        db_session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        db_session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    has_manage = project_ctx.has_permission("project.manage")
    return _to_case_detail_response(
        case, db_session, viewer_user_id=project_ctx.user_id, has_manage=has_manage
    )


# ==============================================================================
# Context Requests
# ==============================================================================


@router.get(
    "/projects/{project_id}/verification/context-requests",
    response_model=list[VerificationContextRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="List clarification requests directed to the current user",
)
def list_user_context_requests(
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
    status_filter: Annotated[ContextRequestStatus | None, Query()] = None,
) -> list[VerificationContextRequestResponse]:
    repo = VerificationContextRequestRepository(db_session)
    items = repo.list_by_user(project_ctx.project.id, project_ctx.user_id, status=status_filter)
    return [VerificationContextRequestResponse.model_validate(r) for r in items]


@router.post(
    "/projects/{project_id}/verification/context-requests/{request_id}/respond",
    response_model=VerificationContextRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit response to clarification question",
)
def respond_context_request(
    request_id: uuid.UUID,
    payload: RespondContextRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VerificationContextRequestResponse:
    repo = VerificationContextRequestRepository(db_session)
    req = repo.get_by_id(request_id)
    if not req or req.project_id != project_ctx.project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Context request not found."
        )

    if req.requested_from_user_id != project_ctx.user_id and not project_ctx.has_permission(
        "project.knowledge.review"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to respond to this request.",
        )

    updated = repo.respond(
        request_id,
        payload.response_text,
        evidence_id=payload.response_evidence_id,
    )
    db_session.commit()
    return VerificationContextRequestResponse.model_validate(updated)


# ==============================================================================
# Handover Eligibility Gate
# ==============================================================================


@router.get(
    "/projects/{project_id}/verification/cases/{case_id}/eligibility",
    response_model=HandoverEligibilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify if finding is eligible for handover package inclusion",
)
def check_case_handover_eligibility(
    case_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> HandoverEligibilityResponse:
    case_repo = VerificationCaseRepository(db_session)
    case = case_repo.get_by_id(case_id, load_relationships=False)
    if not case or case.project_id != project_ctx.project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Verification case not found."
        )

    has_manage = project_ctx.has_permission("project.manage")
    eligibility_service = HandoverEligibilityService(db_session)

    if case.target_type == VerificationTargetType.KNOWLEDGE_ITEM:
        res = eligibility_service.check_knowledge_item_eligibility(
            case.target_id,
            viewer_user_id=project_ctx.user_id,
            has_project_manage=has_manage,
        )
    else:
        res = eligibility_service.check_relationship_eligibility(
            case.target_id,
            viewer_user_id=project_ctx.user_id,
            has_project_manage=has_manage,
        )

    return HandoverEligibilityResponse(
        is_eligible=res.is_eligible,
        target_type=_str_val(res.target_type),
        target_id=res.target_id,
        case_status=res.case_status,
        epistemic_status=res.epistemic_status,
        blockers=res.blockers,
        warnings=res.warnings,
    )


# ==============================================================================
# Assessment Trigger (Deterministic)
# ==============================================================================


@router.post(
    "/projects/{project_id}/verification/assess",
    response_model=VerificationCaseDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger deterministic verification assessment on finding or relationship",
)
def trigger_deterministic_assessment(
    target_type: Annotated[VerificationTargetType, Query()],
    target_id: Annotated[uuid.UUID, Query()],
    project_ctx: Annotated[
        ProjectContext, Depends(require_project_permission("project.knowledge.review"))
    ],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> VerificationCaseDetailResponse:
    engine = DeterministicVerificationEngine(db_session)
    if target_type == VerificationTargetType.KNOWLEDGE_ITEM:
        item = db_session.get(KnowledgeItem, target_id)
        if not item or item.project_id != project_ctx.project.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge item not found."
            )
        res = engine.assess_knowledge_item(item)
    elif target_type == VerificationTargetType.RELATIONSHIP:
        rel = db_session.get(KnowledgeRelationship, target_id)
        if not rel or rel.project_id != project_ctx.project.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found."
            )
        res = engine.assess_relationship(rel)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported target type."
        )

    case = engine.persist_assessment(res)
    db_session.commit()

    has_manage = project_ctx.has_permission("project.manage")
    return _to_case_detail_response(
        case, db_session, viewer_user_id=project_ctx.user_id, has_manage=has_manage
    )
