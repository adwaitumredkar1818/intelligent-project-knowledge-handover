"""FastAPI HTTP endpoints for Handover Workspace (Module 4 / Knowledge Transfer Area).

Provides:
- Handover case management and 14-state lifecycle progression
- Deterministic 8-domain package assembly and versioning
- 9-category readiness evaluation with blocker gating
- Dynamic offboarding checklists and task completion tracking
- Responsibility transfer mapping (departing -> successor)
- Three-phase human sign-offs (departing -> reviewer -> successor)
- Secure package delivery and receipt acknowledgement
- Explicit internal ownership transfers with rollback capability
- AI-assisted narrative drafting and section editing
- Handover eligibility verification gate checks
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db_session,
    get_llm_client,
    require_project_permission,
)
from app.models.enums import RoleName, VerificationTargetType
from app.repositories.handover import (
    HandoverCaseRepository,
    HandoverPackageVersionRepository,
    HandoverReadinessRepository,
    HandoverSectionRepository,
    HandoverSignoffRepository,
)
from app.schemas.handover import (
    AcknowledgementRequest,
    ChecklistItemUpdateRequest,
    DeliveryRequest,
    HandoverAcknowledgementResponse,
    HandoverCaseCreateRequest,
    HandoverCaseDetailResponse,
    HandoverCaseListItem,
    HandoverCaseResponse,
    HandoverCaseUpdateRequest,
    HandoverChecklistItemResponse,
    HandoverChecklistResponse,
    HandoverContentLinkResponse,
    HandoverDeliveryResponse,
    HandoverEligibilityCheckResponse,
    HandoverOwnershipTransferResponse,
    HandoverPackageDetailResponse,
    HandoverPackageResponse,
    HandoverPackageVersionResponse,
    HandoverReadinessAssessmentResponse,
    HandoverReadinessSummaryResponse,
    HandoverResponsibilityTransferResponse,
    HandoverSectionResponse,
    HandoverSignoffResponse,
    HandoverStatusHistoryResponse,
    NarrativeDraftRequest,
    OwnershipTransferRequest,
    OwnershipTransferRollbackRequest,
    PackageAssemblyRequest,
    PaginatedHandoverCaseResponse,
    ReadinessAssessmentRequest,
    ResponsibilityTransferBulkRequest,
    SectionEditRequest,
    SignoffRequest,
)
from app.services.handover_assembly import PackageAssemblyService
from app.services.handover_case import HandoverCaseService
from app.services.handover_checklist import ChecklistService
from app.services.handover_eligibility import HandoverEligibilityService
from app.services.handover_narrative import HandoverNarrativeService
from app.services.handover_ownership import OwnershipTransferService
from app.services.handover_signoff import HandoverSignoffService
from app.services.llm import StructuredLLMClient
from app.services.rbac import ProjectContext

router = APIRouter(
    prefix="/projects/{project_id}/handover",
    tags=["Handover Workspace"],
)


# ---------------------------------------------------------------------------
# 1. Handover Cases
# ---------------------------------------------------------------------------


@router.get(
    "/cases",
    response_model=PaginatedHandoverCaseResponse,
    summary="List project handover cases",
)
def list_handover_cases(
    project_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.read"))],
    session: Annotated[Session, Depends(get_db_session)],
    status: str | None = Query(None, description="Filter by HandoverCaseStatus"),
    departing_member_id: uuid.UUID | None = Query(None),
    successor_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedHandoverCaseResponse:
    """List handover cases in the current project with pagination and filters."""
    service = HandoverCaseService(session)
    offset = (page - 1) * page_size
    items, total = service.list_cases(
        project_id=project_id,
        status=status,
        departing_member_id=departing_member_id,
        successor_id=successor_id,
        offset=offset,
        limit=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedHandoverCaseResponse(
        items=[
            HandoverCaseListItem(
                id=c.id,
                title=c.title,
                status=c.status,
                departing_member_id=c.departing_member_id,
                successor_id=c.successor_id,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/cases",
    response_model=HandoverCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new handover case",
)
def create_handover_case(
    project_id: uuid.UUID,
    request: HandoverCaseCreateRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.create"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> HandoverCaseResponse:
    """Create a new handover case in DRAFT status."""
    service = HandoverCaseService(session)
    case = service.create_case(
        organisation_id=project_ctx.organisation.id,
        project_id=project_id,
        user_id=project_ctx.user_id,
        request=request,
    )
    return HandoverCaseResponse.model_validate(case)


@router.get(
    "/cases/{case_id}",
    response_model=HandoverCaseDetailResponse,
    summary="Get full handover case details",
)
def get_handover_case_details(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.read"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> HandoverCaseDetailResponse:
    """Get comprehensive case details including package versions, signoffs, and history."""
    service = HandoverCaseService(session)
    case = service.get_case(case_id, project_id=project_id, load_relationships=True)

    packages = [HandoverPackageResponse.model_validate(case.package)] if case.package else []
    current_version = next((v for v in case.versions if v.is_current), None)

    return HandoverCaseDetailResponse(
        case=HandoverCaseResponse.model_validate(case),
        packages=packages,
        current_version=HandoverPackageVersionResponse.model_validate(current_version) if current_version else None,
        signoffs=[HandoverSignoffResponse.model_validate(s) for s in case.signoffs],
        status_history=[HandoverStatusHistoryResponse.model_validate(h) for h in case.status_history],
        responsibility_transfers=[
            HandoverResponsibilityTransferResponse.model_validate(t)
            for t in case.responsibility_transfers
        ],
    )


@router.patch(
    "/cases/{case_id}",
    response_model=HandoverCaseResponse,
    summary="Update handover case metadata",
)
def update_handover_case(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    request: HandoverCaseUpdateRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.edit"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> HandoverCaseResponse:
    """Update title, description, or successor of an editable handover case."""
    service = HandoverCaseService(session)
    updated = service.update_case(
        case_id,
        project_id=project_id,
        user_id=project_ctx.user_id,
        request=request,
    )
    return HandoverCaseResponse.model_validate(updated)


# ---------------------------------------------------------------------------
# 2. Package Assembly & Versions
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/assemble",
    response_model=HandoverPackageVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assemble handover package version",
)
def assemble_handover_package(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    request: PackageAssemblyRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.compile"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> HandoverPackageVersionResponse:
    """Run deterministic compilation of verified project knowledge into an immutable package version."""
    service = PackageAssemblyService(session)
    has_manage = project_ctx.has_permission("project.manage")
    version = service.assemble_package_version(
        case_id=case_id,
        project_id=project_id,
        user_id=project_ctx.user_id,
        request=request,
        has_project_manage=has_manage,
    )
    return HandoverPackageVersionResponse.model_validate(version)


@router.get(
    "/cases/{case_id}/versions",
    response_model=list[HandoverPackageVersionResponse],
    summary="List package versions for a case",
)
def list_package_versions(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.read"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> list[HandoverPackageVersionResponse]:
    """List all version snapshots compiled for this handover case."""
    case_repo = HandoverCaseRepository(session)
    case = case_repo.get_by_id(case_id, load_relationships=False)
    if not case or case.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    version_repo = HandoverPackageVersionRepository(session)
    if case.package:
        versions = version_repo.list_by_package(case.package.id)
    else:
        versions = []
    return [HandoverPackageVersionResponse.model_validate(v) for v in versions]


@router.get(
    "/cases/{case_id}/versions/{version_id}",
    response_model=HandoverPackageDetailResponse,
    summary="Get package version details with sections",
)
def get_package_version_details(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    version_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.read"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> HandoverPackageDetailResponse:
    """Get full package version content including 8 domain sections and content links."""
    version_repo = HandoverPackageVersionRepository(session)
    version = version_repo.get_by_id(version_id, load_sections=True)
    if not version or version.project_id != project_id or version.case_id != case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found.")

    readiness_repo = HandoverReadinessRepository(session)
    assessments = readiness_repo.list_by_version(version_id)
    readiness_summary = None
    if assessments:
        overall = next((a for a in assessments if a.category == "overall_quality"), None)
        all_blockers = [b for a in assessments for b in a.blockers_json]
        all_warnings = [w for a in assessments for w in a.warnings_json]
        readiness_summary = HandoverReadinessSummaryResponse(
            version_id=version_id,
            overall_score=overall.score if overall else 0,
            overall_level=overall.level if overall else "not_ready",
            categories=[HandoverReadinessAssessmentResponse.model_validate(a) for a in assessments],
            is_ready_for_signoff=(overall.score >= 70 if overall else False) and len(all_blockers) == 0,
            blocker_count=len(all_blockers),
            warning_count=len(all_warnings),
        )

    checklist_repo = ChecklistService(session)
    checklists = checklist_repo.list_checklists(case_id, project_id=project_id)

    sections_res = [
        HandoverSectionResponse(
            id=s.id,
            version_id=s.version_id,
            section_type=s.section_type,
            section_title=s.section_title,
            section_content=s.section_content,
            content_summary=s.content_summary,
            section_order=s.section_order,
            knowledge_item_count=s.knowledge_item_count,
            relationship_count=s.relationship_count,
            created_at=s.created_at,
            updated_at=s.created_at,
        )
        for s in version.sections
    ]

    checklists_res = [
        HandoverChecklistResponse(
            id=c.id,
            case_id=c.case_id,
            generated_for_version_id=c.version_id,
            checklist_type=c.checklist_type,
            created_at=c.created_at,
            items=[
                HandoverChecklistItemResponse.model_validate(i) for i in c.items
            ],
        )
        for c in checklists
    ]

    return HandoverPackageDetailResponse(
        version=HandoverPackageVersionResponse.model_validate(version),
        sections=sections_res,
        readiness=readiness_summary,
        checklists=checklists_res,
    )


# ---------------------------------------------------------------------------
# 3. Readiness Assessments
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/readiness",
    response_model=HandoverReadinessSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Assess package readiness",
)
def assess_package_readiness(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    request: ReadinessAssessmentRequest,
    project_ctx: Annotated[
        ProjectContext, Depends(require_project_permission("handover.readiness.assess"))
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> HandoverReadinessSummaryResponse:
    """Run 9-category readiness evaluation across verified knowledge for a package version."""
    engine = HandoverReadinessEngine(session)
    summary = engine.assess_version(
        version_id=request.version_id,
        project_id=project_id,
        user_id=project_ctx.user_id,
        notes=request.notes,
    )
    return summary


@router.get(
    "/cases/{case_id}/readiness/{version_id}",
    response_model=HandoverReadinessSummaryResponse,
    summary="Get readiness assessment summary",
)
def get_readiness_assessment(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    version_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.read"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> HandoverReadinessSummaryResponse:
    """Get previously computed 9-category readiness scores for a package version."""
    readiness_repo = HandoverReadinessRepository(session)
    assessments = readiness_repo.list_by_version(version_id)
    if not assessments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No readiness assessment found for this version.",
        )

    overall = next((a for a in assessments if a.category == "overall_quality"), None)
    all_blockers = [b for a in assessments for b in a.blockers_json]
    all_warnings = [w for a in assessments for w in a.warnings_json]

    return HandoverReadinessSummaryResponse(
        version_id=version_id,
        overall_score=overall.score if overall else 0,
        overall_level=overall.level if overall else "not_ready",
        categories=[HandoverReadinessAssessmentResponse.model_validate(a) for a in assessments],
        is_ready_for_signoff=(overall.score >= 70 if overall else False) and len(all_blockers) == 0,
        blocker_count=len(all_blockers),
        warning_count=len(all_warnings),
    )


# ---------------------------------------------------------------------------
# 4. Checklists
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/checklists/generate",
    response_model=list[HandoverChecklistResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate transition checklists",
)
def generate_checklists(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.edit"))],
    session: Annotated[Session, Depends(get_db_session)],
    version_id: uuid.UUID | None = Query(None),
) -> list[HandoverChecklistResponse]:
    """Generate dynamic transition checklists (pre-handover, knowledge-transfer, access)."""
    service = ChecklistService(session)
    checklists = service.generate_checklists_for_case(
        case_id=case_id,
        project_id=project_id,
        user_id=project_ctx.user_id,
        version_id=version_id,
    )
    return [
        HandoverChecklistResponse(
            id=c.id,
            case_id=c.case_id,
            generated_for_version_id=c.version_id,
            checklist_type=c.checklist_type,
            created_at=c.created_at,
            items=[HandoverChecklistItemResponse.model_validate(i) for i in c.items],
        )
        for c in checklists
    ]


@router.get(
    "/cases/{case_id}/checklists",
    response_model=list[HandoverChecklistResponse],
    summary="List checklists for a case",
)
def list_case_checklists(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.read"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> list[HandoverChecklistResponse]:
    """List all checklists and items attached to this handover case."""
    service = ChecklistService(session)
    checklists = service.list_checklists(case_id, project_id=project_id)
    return [
        HandoverChecklistResponse(
            id=c.id,
            case_id=c.case_id,
            generated_for_version_id=c.version_id,
            checklist_type=c.checklist_type,
            created_at=c.created_at,
            items=[HandoverChecklistItemResponse.model_validate(i) for i in c.items],
        )
        for c in checklists
    ]


@router.patch(
    "/checklists/items/{item_id}",
    response_model=HandoverChecklistItemResponse,
    summary="Update checklist item completion status",
)
def update_checklist_item(
    project_id: uuid.UUID,
    item_id: uuid.UUID,
    request: ChecklistItemUpdateRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.edit"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> HandoverChecklistItemResponse:
    """Update status (pending, in_progress, completed, skipped, blocked) of a checklist item."""
    service = ChecklistService(session)
    item = service.update_item_status(
        item_id=item_id,
        project_id=project_id,
        user_id=project_ctx.user_id,
        request=request,
    )
    return HandoverChecklistItemResponse.model_validate(item)


# ---------------------------------------------------------------------------
# 5. Responsibilities
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/responsibilities",
    response_model=list[HandoverResponsibilityTransferResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Map departing member responsibilities",
)
def create_responsibility_transfers(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    request: ResponsibilityTransferBulkRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.edit"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> list[HandoverResponsibilityTransferResponse]:
    """Define explicit responsibility transfer mappings from departing member to successor."""
    service = OwnershipTransferService(session)
    created = service.create_responsibility_transfers(
        case_id=case_id,
        project_id=project_id,
        user_id=project_ctx.user_id,
        request=request,
    )
    return [HandoverResponsibilityTransferResponse.model_validate(t) for t in created]


@router.get(
    "/cases/{case_id}/responsibilities",
    response_model=list[HandoverResponsibilityTransferResponse],
    summary="List mapped responsibilities",
)
def list_responsibility_transfers(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.read"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> list[HandoverResponsibilityTransferResponse]:
    """List mapped responsibilities for a handover case."""
    service = OwnershipTransferService(session)
    transfers = service.list_responsibility_transfers(case_id=case_id, project_id=project_id)
    return [HandoverResponsibilityTransferResponse.model_validate(t) for t in transfers]


@router.patch(
    "/responsibilities/{transfer_id}",
    response_model=HandoverResponsibilityTransferResponse,
    summary="Update responsibility transfer status",
)
def update_responsibility_status(
    project_id: uuid.UUID,
    transfer_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.edit"))],
    session: Annotated[Session, Depends(get_db_session)],
    status_value: str = Query(..., alias="status"),
    notes: str | None = Query(None),
) -> HandoverResponsibilityTransferResponse:
    """Update status (pending, in_progress, completed, rolled_back) of a responsibility transfer."""
    service = OwnershipTransferService(session)
    updated = service.update_responsibility_status(
        transfer_id=transfer_id,
        project_id=project_id,
        user_id=project_ctx.user_id,
        status=status_value,
        notes=notes,
    )
    return HandoverResponsibilityTransferResponse.model_validate(updated)


# ---------------------------------------------------------------------------
# 6. Sign-Offs & Deliveries
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/signoffs",
    response_model=HandoverSignoffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit human sign-off",
)
def submit_handover_signoff(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    request: SignoffRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.review"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> HandoverSignoffResponse:
    """Submit Phase 1 (departing), Phase 2 (reviewer approval), or Phase 3 (successor) sign-off."""
    service = HandoverSignoffService(session)
    is_org_admin = project_ctx.organisation_role.name in (
        RoleName.ORG_OWNER.value,
        RoleName.ORG_ADMIN.value,
    )
    signoff = service.submit_signoff(
        case_id=case_id,
        project_id=project_id,
        user_id=project_ctx.user_id,
        request=request,
        is_org_admin=is_org_admin,
    )
    return HandoverSignoffResponse.model_validate(signoff)


@router.get(
    "/cases/{case_id}/signoffs",
    response_model=list[HandoverSignoffResponse],
    summary="List sign-offs for case",
)
def list_handover_signoffs(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.read"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> list[HandoverSignoffResponse]:
    """List all human sign-offs recorded for this handover case."""
    repo = HandoverSignoffRepository(session)
    signoffs = repo.list_by_case(case_id)
    return [HandoverSignoffResponse.model_validate(s) for s in signoffs]


@router.post(
    "/cases/{case_id}/deliver",
    response_model=list[HandoverDeliveryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Deliver approved package version",
)
def deliver_handover_package(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    request: DeliveryRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.deliver"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> list[HandoverDeliveryResponse]:
    """Deliver an approved package version to successors."""
    service = HandoverSignoffService(session)
    deliveries = service.deliver_package(
        case_id=case_id,
        project_id=project_id,
        user_id=project_ctx.user_id,
        request=request,
    )
    return [HandoverDeliveryResponse.model_validate(d) for d in deliveries]


@router.post(
    "/deliveries/{delivery_id}/acknowledge",
    response_model=HandoverAcknowledgementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Successor receipt acknowledgement",
)
def acknowledge_delivery(
    project_id: uuid.UUID,
    delivery_id: uuid.UUID,
    request: AcknowledgementRequest,
    project_ctx: Annotated[
        ProjectContext, Depends(require_project_permission("handover.acknowledge"))
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> HandoverAcknowledgementResponse:
    """Successor submits formal acknowledgement of delivered handover package."""
    service = HandoverSignoffService(session)
    ack = service.acknowledge_delivery(
        delivery_id=delivery_id,
        project_id=project_id,
        user_id=project_ctx.user_id,
        request=request,
    )
    return HandoverAcknowledgementResponse.model_validate(ack)


# ---------------------------------------------------------------------------
# 7. Ownership Transfer (Separate Operation)
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/transfer-ownership",
    response_model=HandoverOwnershipTransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute explicit project ownership transfer",
)
def transfer_project_ownership(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    request: OwnershipTransferRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.transfer"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> HandoverOwnershipTransferResponse:
    """Execute an explicit project ownership transfer after package approval and delivery."""
    service = OwnershipTransferService(session)
    transfer = service.execute_ownership_transfer(
        case_id=case_id,
        project_id=project_id,
        user_id=project_ctx.user_id,
        request=request,
    )
    return HandoverOwnershipTransferResponse.model_validate(transfer)


@router.post(
    "/ownership-transfers/{transfer_id}/rollback",
    response_model=HandoverOwnershipTransferResponse,
    status_code=status.HTTP_200_OK,
    summary="Rollback an ownership transfer",
)
def rollback_ownership_transfer(
    project_id: uuid.UUID,
    transfer_id: uuid.UUID,
    request: OwnershipTransferRollbackRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.admin"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> HandoverOwnershipTransferResponse:
    """Revert a previously executed ownership transfer with documented reason."""
    service = OwnershipTransferService(session)
    rolled_back = service.rollback_ownership_transfer(
        transfer_id=transfer_id,
        project_id=project_id,
        user_id=project_ctx.user_id,
        request=request,
    )
    return HandoverOwnershipTransferResponse.model_validate(rolled_back)


# ---------------------------------------------------------------------------
# 8. Narrative Drafting & Section Editing
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/narrative/draft",
    summary="Draft narrative for a section",
)
def draft_section_narrative(
    project_id: uuid.UUID,
    case_id: uuid.UUID,
    request: NarrativeDraftRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.edit"))],
    session: Annotated[Session, Depends(get_db_session)],
    llm_client: Annotated[StructuredLLMClient | None, Depends(get_llm_client)] = None,
) -> dict[str, Any]:
    """Generate an AI draft narrative grounded strictly in verified findings for a section."""
    service = HandoverNarrativeService(session, llm_client=llm_client)
    return service.draft_section_narrative(
        project_id=project_id,
        request=request,
    )


@router.patch(
    "/sections/{section_id}",
    response_model=HandoverSectionResponse,
    summary="Edit section content",
)
def edit_section_content(
    project_id: uuid.UUID,
    section_id: uuid.UUID,
    request: SectionEditRequest,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.edit"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> HandoverSectionResponse:
    """Human editor edits section content narrative text or summary."""
    service = HandoverNarrativeService(session)
    updated = service.edit_section_content(
        section_id=section_id,
        project_id=project_id,
        user_id=project_ctx.user_id,
        request=request,
    )
    return HandoverSectionResponse(
        id=updated.id,
        version_id=updated.version_id,
        section_type=updated.section_type,
        section_title=updated.section_title,
        section_content=updated.section_content,
        content_summary=updated.content_summary,
        section_order=updated.section_order,
        knowledge_item_count=updated.knowledge_item_count,
        relationship_count=updated.relationship_count,
        created_at=updated.created_at,
        updated_at=updated.created_at,
    )


# ---------------------------------------------------------------------------
# 9. Eligibility Gate Check
# ---------------------------------------------------------------------------


@router.get(
    "/eligibility/{target_type}/{target_id}",
    response_model=HandoverEligibilityCheckResponse,
    summary="Check handover eligibility for a knowledge item or relationship",
)
def check_handover_eligibility(
    project_id: uuid.UUID,
    target_type: str,
    target_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("handover.read"))],
    session: Annotated[Session, Depends(get_db_session)],
) -> HandoverEligibilityCheckResponse:
    """Pre-check whether a knowledge item or relationship edge meets handover eligibility rules."""
    service = HandoverEligibilityService(session)
    has_manage = project_ctx.has_permission("project.manage")
    if target_type == VerificationTargetType.KNOWLEDGE_ITEM.value:
        res = service.check_knowledge_item_eligibility(
            target_id,
            viewer_user_id=project_ctx.user_id,
            has_project_manage=has_manage,
        )
    elif target_type == VerificationTargetType.RELATIONSHIP.value:
        res = service.check_relationship_eligibility(
            target_id,
            viewer_user_id=project_ctx.user_id,
            has_project_manage=has_manage,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target type '{target_type}'. Must be 'knowledge_item' or 'relationship'.",
        )

    return HandoverEligibilityCheckResponse(
        target_type=target_type,
        target_id=target_id,
        is_eligible=res.is_eligible,
        case_status=res.case_status,
        epistemic_status=res.epistemic_status,
        blockers=res.blockers,
        warnings=res.warnings,
    )
