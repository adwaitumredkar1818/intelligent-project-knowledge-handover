"""FastAPI HTTP endpoints for Relationship Explorer module.

Provides:
- Graph projection for React Flow frontend (`/graph`)
- Entity listing and node detail side-panel (`/entities`, `/entities/{id}`)
- Relationship queries, evidence links, and human review queue
  (`/{id}`, `/{id}/evidence`, `/{id}/submit-for-review`)
- Decision-to-implementation traceability chains (`/traceability`, `/traceability/{decision_id}`)
- Directed dependency hierarchy with cycle detection (`/dependencies`)
- Chronological timeline event stream (`/timeline`)
- Asynchronous and on-demand graph reconstruction runs (`/reconstruct`, `/runs`)
- Multi-signal identity candidate review and reversible merge (`/identities/candidates`)

Enforces strict fail-closed source ACL checks on all endpoints.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db_session,
    get_llm_client,
    require_project_permission,
)
from app.models.enums import TraceabilityCompletenessStatus
from app.models.relationship import KnowledgeEntity
from app.repositories.relationship import (
    EntityRepository,
    RelationshipRepository,
    RelationshipRunRepository,
    TimelineRepository,
    TraceabilityRepository,
)
from app.schemas.relationship import (
    DecisionTraceabilityResponse,
    DependencyGraphResponse,
    EntityListResponse,
    GraphProjectionResponse,
    IdentityCandidateResponse,
    IdentityReviewRequest,
    KnowledgeEntityResponse,
    KnowledgeRelationshipResponse,
    NodeDetailResponse,
    ReconstructionTriggerRequest,
    RelationshipEvidenceLinkResponse,
    RelationshipListResponse,
    RelationshipReconstructionRunResponse,
    RelationshipReviewRequest,
    TimelineEventGraphResponse,
    TimelineGraphStreamResponse,
    TraceabilityListResponse,
)
from app.services.dependency_intelligence import DependencyIntelligenceService
from app.services.graph_projection import GraphProjectionService
from app.services.llm import StructuredLLMClient
from app.services.rbac import ProjectContext
from app.services.relationship_coordinator import RelationshipCoordinatorService
from app.services.traceability import DecisionTraceabilityService

router = APIRouter(tags=["Relationship Explorer"])


# ==============================================================================
# Graph Projection & Node Detail
# ==============================================================================


@router.get(
    "/projects/{project_id}/relationships/graph",
    response_model=GraphProjectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Project knowledge graph into React Flow format",
)
def get_graph_projection(
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
    center_node_id: Annotated[uuid.UUID | None, Query()] = None,
    depth: Annotated[int, Query(ge=1, le=5)] = 2,
    entity_type: Annotated[str | None, Query()] = None,
    verification_status: Annotated[str | None, Query()] = None,
    limit_nodes: Annotated[int, Query(ge=1, le=1000)] = 250,
    limit_edges: Annotated[int, Query(ge=1, le=2000)] = 500,
) -> GraphProjectionResponse:
    """Return a React Flow projection filtered strictly by caller source permissions."""
    service = GraphProjectionService(db_session)
    has_manage = project_ctx.has_permission("project.manage")
    return service.project_graph(
        project_id=project_ctx.project.id,
        viewer_user_id=project_ctx.principal.user_id,
        has_project_manage=has_manage,
        center_node_id=center_node_id,
        depth=depth,
        entity_type_filter=entity_type,
        verification_status_filter=verification_status,
        limit_nodes=limit_nodes,
        limit_edges=limit_edges,
    )


# ==============================================================================
# Entities
# ==============================================================================


@router.get(
    "/projects/{project_id}/relationships/entities",
    response_model=EntityListResponse,
    status_code=status.HTTP_200_OK,
    summary="List accessible entities in the project",
)
def list_entities(
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
    entity_type: Annotated[str | None, Query()] = None,
    resolution_status: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EntityListResponse:
    """Return paginated entities visible to caller."""
    repo = EntityRepository(db_session)
    has_manage = project_ctx.has_permission("project.manage")
    items, total = repo.list_accessible_entities(
        project_id=project_ctx.project.id,
        viewer_user_id=project_ctx.principal.user_id,
        has_project_manage=has_manage,
        entity_type=entity_type,
        resolution_status=resolution_status,
        query=q,
        limit=limit,
        offset=offset,
    )
    return EntityListResponse(
        items=[KnowledgeEntityResponse.model_validate(e) for e in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/projects/{project_id}/relationships/entities/{entity_id}",
    response_model=NodeDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get node side-panel details with adjacent edges",
)
def get_node_details(
    entity_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NodeDetailResponse:
    """Return comprehensive metadata and adjacent relationships for selected entity."""
    service = GraphProjectionService(db_session)
    has_manage = project_ctx.has_permission("project.manage")
    try:
        return service.get_node_details(
            project_id=project_ctx.project.id,
            entity_id=entity_id,
            viewer_user_id=project_ctx.principal.user_id,
            has_project_manage=has_manage,
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "SOURCE_ACCESS_DENIED: Entity primary evidence is restricted to external accounts."
            ),
        ) from None


# ==============================================================================
# Relationships & Review Queue
# ==============================================================================


@router.get(
    "/projects/{project_id}/relationships",
    response_model=RelationshipListResponse,
    status_code=status.HTTP_200_OK,
    summary="List accessible knowledge graph relationships",
)
def list_relationships(
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
    relationship_type: Annotated[str | None, Query()] = None,
    relationship_basis: Annotated[str | None, Query()] = None,
    verification_status: Annotated[str | None, Query()] = None,
    entity_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RelationshipListResponse:
    """Return paginated relationships where caller has access to supporting evidence."""
    repo = RelationshipRepository(db_session)
    has_manage = project_ctx.has_permission("project.manage")
    items, total = repo.list_accessible_relationships(
        project_id=project_ctx.project.id,
        viewer_user_id=project_ctx.principal.user_id,
        has_project_manage=has_manage,
        relationship_type=relationship_type,
        relationship_basis=relationship_basis,
        verification_status=verification_status,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )
    return RelationshipListResponse(
        items=[KnowledgeRelationshipResponse.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# ==============================================================================
# Decision Traceability
# ==============================================================================


@router.get(
    "/projects/{project_id}/relationships/traceability",
    response_model=TraceabilityListResponse,
    status_code=status.HTTP_200_OK,
    summary="List decision traceability chains",
)
def list_traceability_chains(
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
    completeness_status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TraceabilityListResponse:
    """Return 5-stage decision-to-implementation traceability chains."""
    repo = TraceabilityRepository(db_session)
    has_manage = project_ctx.has_permission("project.manage")
    items, total = repo.list_accessible_chains(
        project_id=project_ctx.project.id,
        viewer_user_id=project_ctx.principal.user_id,
        has_project_manage=has_manage,
        completeness_status=completeness_status,
        limit=limit,
        offset=offset,
    )

    # Counts
    complete_c = sum(
        1 for c in items if c.completeness_status == TraceabilityCompletenessStatus.COMPLETE.value
    )
    part_c = sum(
        1
        for c in items
        if c.completeness_status == TraceabilityCompletenessStatus.PARTIALLY_TRACED.value
    )
    untraced_c = sum(
        1 for c in items if c.completeness_status == TraceabilityCompletenessStatus.UNTRACED.value
    )
    conf_c = sum(
        1
        for c in items
        if c.completeness_status == TraceabilityCompletenessStatus.CONFLICTING.value
    )

    res_items = []
    for c in items:
        dec = db_session.get(KnowledgeEntity, c.decision_entity_id)
        resp = DecisionTraceabilityResponse.model_validate(c)
        resp.decision_name = dec.canonical_name if dec else None
        res_items.append(resp)

    return TraceabilityListResponse(
        items=res_items,
        total=total,
        complete_count=complete_c,
        partially_traced_count=part_c,
        untraced_count=untraced_c,
        conflicting_count=conf_c,
    )


@router.get(
    "/projects/{project_id}/relationships/traceability/{decision_entity_id}",
    response_model=DecisionTraceabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single decision traceability chain",
)
def get_decision_traceability(
    decision_entity_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> DecisionTraceabilityResponse:
    """Return single decision traceability chain."""
    repo = TraceabilityRepository(db_session)
    entity_repo = EntityRepository(db_session)
    has_manage = project_ctx.has_permission("project.manage")

    ent, denied = entity_repo.get_accessible_entity(
        decision_entity_id,
        project_id=project_ctx.project.id,
        viewer_user_id=project_ctx.principal.user_id,
        has_project_manage=has_manage,
    )
    if ent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision entity not found."
        )
    if denied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SOURCE_ACCESS_DENIED: Decision is restricted.",
        )

    chain = repo.get_chain_by_decision(
        project_id=project_ctx.project.id,
        decision_entity_id=decision_entity_id,
    )
    if chain is None:
        # Dynamically compute on demand
        service = DecisionTraceabilityService(db_session)
        analysis = service.analyze_decision_traceability(ent)
        chain = repo.create_or_update_chain(
            organisation_id=project_ctx.organisation.id,
            project_id=project_ctx.project.id,
            decision_entity_id=ent.id,
            completeness_status=analysis.completeness_status,
            work_item_ids_json=analysis.work_item_ids,
            pull_request_ids_json=analysis.pull_request_ids,
            commit_ids_json=analysis.commit_ids,
            component_ids_json=analysis.component_ids,
            relationship_ids_json=analysis.relationship_ids,
            missing_links_json=analysis.missing_links,
            uncertainty_reasons_json=analysis.uncertainty_reasons,
            aggregate_confidence=analysis.aggregate_confidence,
        )

    resp = DecisionTraceabilityResponse.model_validate(chain)
    resp.decision_name = ent.canonical_name
    return resp


# ==============================================================================
# Dependency Intelligence & Cycle Detection
# ==============================================================================


@router.get(
    "/projects/{project_id}/relationships/dependencies",
    response_model=DependencyGraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze dependency graph with cycle detection",
)
def get_dependencies_graph(
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
    root_entity_id: Annotated[uuid.UUID | None, Query()] = None,
    max_depth: Annotated[int, Query(ge=1, le=20)] = 10,
) -> DependencyGraphResponse:
    """Traverse directed dependency hierarchy, detect cycles, and identify root blockers."""
    service = DependencyIntelligenceService(db_session)
    return service.analyze_dependencies(
        project_id=project_ctx.project.id,
        root_entity_id=root_entity_id,
        max_depth=max_depth,
    )


# ==============================================================================
# Knowledge Timeline
# ==============================================================================


@router.get(
    "/projects/{project_id}/relationships/timeline",
    response_model=TimelineGraphStreamResponse,
    status_code=status.HTTP_200_OK,
    summary="Get chronological stream of graph timeline events",
)
def get_timeline_stream(
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
    entity_id: Annotated[uuid.UUID | None, Query()] = None,
    event_type: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TimelineGraphStreamResponse:
    """Return chronological event stream with verifiable timestamp precision."""
    repo = TimelineRepository(db_session)
    has_manage = project_ctx.has_permission("project.manage")
    events, total = repo.list_accessible_events(
        project_id=project_ctx.project.id,
        viewer_user_id=project_ctx.principal.user_id,
        has_project_manage=has_manage,
        entity_id=entity_id,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
    items = []
    for evt in events:
        e_resp = TimelineEventGraphResponse.model_validate(evt)
        ent = db_session.get(KnowledgeEntity, evt.entity_id)
        if ent:
            e_resp.entity_name = ent.canonical_name
            e_resp.entity_type = ent.entity_type
        items.append(e_resp)

    return TimelineGraphStreamResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ==============================================================================
# Reconstruction Runs
# ==============================================================================


@router.post(
    "/projects/{project_id}/relationships/reconstruct",
    response_model=RelationshipReconstructionRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger relationship discovery and graph rebuild",
)
def trigger_reconstruction(
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.manage"))],
    db_session: Annotated[Session, Depends(get_db_session)],
    llm_client: Annotated[StructuredLLMClient, Depends(get_llm_client)],
    payload: Annotated[ReconstructionTriggerRequest | None, Body()] = None,
) -> RelationshipReconstructionRunResponse:
    """Queue or execute relationship reconstruction across project evidence."""
    service = RelationshipCoordinatorService(db_session, llm_client=llm_client)
    req = payload or ReconstructionTriggerRequest()
    run = service.run_reconstruction(
        organisation_id=project_ctx.organisation.id,
        project_id=project_ctx.project.id,
        include_llm_suggestions=req.include_llm_suggestions,
    )
    return RelationshipReconstructionRunResponse.model_validate(run)


@router.get(
    "/projects/{project_id}/relationships/runs",
    response_model=list[RelationshipReconstructionRunResponse],
    status_code=status.HTTP_200_OK,
    summary="List relationship reconstruction runs",
)
def list_reconstruction_runs(
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RelationshipReconstructionRunResponse]:
    """Return historical reconstruction runs and discovery metrics."""
    repo = RelationshipRunRepository(db_session)
    runs, _ = repo.list_runs(project_id=project_ctx.project.id, limit=limit, offset=offset)
    return [RelationshipReconstructionRunResponse.model_validate(r) for r in runs]


@router.get(
    "/projects/{project_id}/relationships/runs/{run_id}",
    response_model=RelationshipReconstructionRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single reconstruction run telemetry",
)
def get_reconstruction_run(
    run_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RelationshipReconstructionRunResponse:
    """Return detailed progress telemetry for a run."""
    repo = RelationshipRunRepository(db_session)
    run = repo.get_run(run_id, project_id=project_ctx.project.id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Run {run_id} not found."
        )
    return RelationshipReconstructionRunResponse.model_validate(run)


# ==============================================================================
# Identity Candidate Review & Reversible Merge
# ==============================================================================


@router.get(
    "/projects/{project_id}/relationships/identities/candidates",
    response_model=list[IdentityCandidateResponse],
    status_code=status.HTTP_200_OK,
    summary="List candidate identity matches for review",
)
def list_identity_candidates(
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
    decision_status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[IdentityCandidateResponse]:
    """Return identity resolution candidate pairs."""
    repo = EntityRepository(db_session)
    candidates, _ = repo.list_identity_candidates(
        project_id=project_ctx.project.id,
        decision_status=decision_status,
        limit=limit,
        offset=offset,
    )
    result = []
    for c in candidates:
        c_resp = IdentityCandidateResponse.model_validate(c)
        l_ent = repo.get_entity_by_id(c.left_entity_id)
        r_ent = repo.get_entity_by_id(c.right_entity_id)
        if l_ent:
            c_resp.left_entity = KnowledgeEntityResponse.model_validate(l_ent)
        if r_ent:
            c_resp.right_entity = KnowledgeEntityResponse.model_validate(r_ent)
        result.append(c_resp)
    return result


@router.post(
    "/projects/{project_id}/relationships/identities/candidates/{candidate_id}/review",
    response_model=IdentityCandidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Review and merge/reject an identity candidate",
)
def review_identity_candidate(
    candidate_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.manage"))],
    db_session: Annotated[Session, Depends(get_db_session)],
    payload: Annotated[IdentityReviewRequest, Body()],
) -> IdentityCandidateResponse:
    """Accept (reversible merge) or reject identity candidate."""
    repo = EntityRepository(db_session)
    try:
        updated = repo.review_identity_candidate(
            candidate_id,
            user_id=project_ctx.principal.user_id,
            action=payload.action,
            rationale=payload.rationale,
        )
        return IdentityCandidateResponse.model_validate(updated)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.post(
    "/projects/{project_id}/relationships/identities/candidates/{candidate_id}/revert",
    response_model=IdentityCandidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Revert an accepted identity merge",
)
def revert_identity_candidate(
    candidate_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.manage"))],
    db_session: Annotated[Session, Depends(get_db_session)],
    payload: Annotated[dict[str, str] | None, Body()] = None,
) -> IdentityCandidateResponse:
    """Revert an accepted merge, restoring right entity to canonical status."""
    repo = EntityRepository(db_session)
    rationale = (payload or {}).get("rationale")
    try:
        updated = repo.revert_identity_candidate(
            candidate_id,
            user_id=project_ctx.principal.user_id,
            rationale=rationale,
        )
        return IdentityCandidateResponse.model_validate(updated)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


# ==============================================================================
# Parameterized Relationship Lookup & Review (MUST BE LAST ROUTE IN MODULE)
# ==============================================================================


@router.get(
    "/projects/{project_id}/relationships/{relationship_id}",
    response_model=KnowledgeRelationshipResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single relationship details and provenance",
)
def get_relationship_detail(
    relationship_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> KnowledgeRelationshipResponse:
    """Return single relationship detail; fails closed if evidence is restricted."""
    repo = RelationshipRepository(db_session)
    has_manage = project_ctx.has_permission("project.manage")
    rel, links, denied = repo.get_accessible_relationship(
        relationship_id,
        project_id=project_ctx.project.id,
        viewer_user_id=project_ctx.principal.user_id,
        has_project_manage=has_manage,
    )
    if rel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship {relationship_id} not found in project.",
        )
    if denied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SOURCE_ACCESS_DENIED: All supporting evidence links are restricted.",
        )

    return KnowledgeRelationshipResponse.model_validate(rel)


@router.get(
    "/projects/{project_id}/relationships/{relationship_id}/evidence",
    response_model=list[RelationshipEvidenceLinkResponse],
    status_code=status.HTTP_200_OK,
    summary="Get supporting evidence links for a relationship",
)
def get_relationship_evidence(
    relationship_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.read"))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[RelationshipEvidenceLinkResponse]:
    """Return supporting evidence links accessible to caller."""
    repo = RelationshipRepository(db_session)
    has_manage = project_ctx.has_permission("project.manage")
    rel, links, denied = repo.get_accessible_relationship(
        relationship_id,
        project_id=project_ctx.project.id,
        viewer_user_id=project_ctx.principal.user_id,
        has_project_manage=has_manage,
    )
    if rel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship {relationship_id} not found.",
        )
    if denied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SOURCE_ACCESS_DENIED: Supporting evidence is restricted.",
        )

    return [RelationshipEvidenceLinkResponse.model_validate(link) for link in links]


@router.post(
    "/projects/{project_id}/relationships/{relationship_id}/submit-for-review",
    response_model=KnowledgeRelationshipResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit review decision for a relationship",
)
def submit_relationship_review(
    relationship_id: uuid.UUID,
    project_ctx: Annotated[ProjectContext, Depends(require_project_permission("project.manage"))],
    db_session: Annotated[Session, Depends(get_db_session)],
    payload: Annotated[RelationshipReviewRequest, Body()],
) -> KnowledgeRelationshipResponse:
    """Verify, reject, dispute, or request evidence for candidate relationship."""
    repo = RelationshipRepository(db_session)
    try:
        updated = repo.review_relationship(
            relationship_id,
            user_id=project_ctx.principal.user_id,
            action=payload.action,
            note=payload.note,
        )
        return KnowledgeRelationshipResponse.model_validate(updated)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
