"""Handover Human Sign-Off and Approval Service.

Platform: The Handover
Module: Handover Workspace (Module 4 / Knowledge Transfer Area)

Enforces:
1. Three-phase human sign-off protocol (departing -> reviewer -> successor)
2. Strict separation of duties (departing member cannot be the reviewer)
3. Quality gating (packages with active blockers cannot be approved without explicit override)
4. Cryptographic signature hash verification
5. Immutable audit history
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.security import utc_now
from app.models.audit import AuditLog
from app.models.enums import (
    AuditOutcome,
    HandoverCaseStatus,
    HandoverDeliveryMethod,
    SignoffDecision,
    SignoffType,
)
from app.models.handover import (
    HandoverAcknowledgement,
    HandoverCase,
    HandoverDelivery,
    HandoverPackageVersion,
    HandoverSignoff,
)
from app.repositories.audit import AuditLogRepository
from app.repositories.handover import (
    HandoverAcknowledgementRepository,
    HandoverCaseRepository,
    HandoverDeliveryRepository,
    HandoverPackageVersionRepository,
    HandoverReadinessRepository,
    HandoverSignoffRepository,
)
from app.schemas.handover import (
    AcknowledgementRequest,
    DeliveryRequest,
    SignoffRequest,
)
from app.services.audit import AuditService
from app.services.handover_case import HandoverCaseService


class HandoverSignoffService:
    """Manages the 3-phase human approval lifecycle for handover packages."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.case_repo = HandoverCaseRepository(session)
        self.version_repo = HandoverPackageVersionRepository(session)
        self.signoff_repo = HandoverSignoffRepository(session)
        self.delivery_repo = HandoverDeliveryRepository(session)
        self.ack_repo = HandoverAcknowledgementRepository(session)
        self.readiness_repo = HandoverReadinessRepository(session)
        self.case_service = HandoverCaseService(session)
        self.audit_service = AuditService(audit_repository=AuditLogRepository(session))

    def submit_signoff(
        self,
        case_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        request: SignoffRequest,
        is_org_admin: bool = False,
    ) -> HandoverSignoff:
        """Process a sign-off or approval action with separation-of-duties validation."""
        case = self.case_service.get_case(case_id, project_id=project_id, load_relationships=False)
        version = self.version_repo.get_by_id(request.version_id, load_sections=False)
        if not version or version.case_id != case.id:
            raise NotFoundError(f"Package version {request.version_id} does not belong to case {case_id}.")

        # Phase 1: Departing Member Sign-Off
        if request.signoff_type == SignoffType.DEPARTING_SIGNOFF.value:
            if user_id != case.departing_member_id and not is_org_admin:
                raise ForbiddenError("Only the designated departing member or an administrator can submit Phase 1 sign-off.")

            # Record signoff
            signoff = self._record_signoff(
                case=case,
                version=version,
                signoff_type=request.signoff_type,
                signer_user_id=user_id,
                decision=request.decision,
                comments=request.comments,
            )

            if request.decision == SignoffDecision.APPROVED.value:
                # Transition case to REVIEW_PENDING if currently readiness_assessed or assembled
                if case.status in (
                    HandoverCaseStatus.ASSEMBLED.value,
                    HandoverCaseStatus.READINESS_ASSESSED.value,
                    HandoverCaseStatus.DRAFT.value,
                ):
                    self.case_service.transition_status(
                        case_id,
                        project_id=project_id,
                        new_status=HandoverCaseStatus.REVIEW_PENDING.value,
                        user_id=user_id,
                        change_reason="Departing member completed Phase 1 sign-off",
                    )
            return signoff

        # Phase 2: Reviewer Approval
        elif request.signoff_type == SignoffType.REVIEWER_APPROVAL.value:
            # Separation of duties: Reviewer cannot be the departing member
            if user_id == case.departing_member_id:
                raise ForbiddenError(
                    "Separation of duties violation: The departing member cannot act as the approving reviewer."
                )

            # Check readiness blockers
            assessments = self.readiness_repo.list_by_version(version.id)
            has_blockers = any(len(a.blockers_json) > 0 for a in assessments)

            if request.decision == SignoffDecision.APPROVED.value:
                if has_blockers and not is_org_admin:
                    raise BadRequestError(
                        "Package cannot be approved because unresolved readiness blockers exist. "
                        "Only an Organisation Administrator can override blockers with documented rationale."
                    )

                signoff = self._record_signoff(
                    case=case,
                    version=version,
                    signoff_type=request.signoff_type,
                    signer_user_id=user_id,
                    decision=request.decision,
                    comments=request.comments,
                )

                # Transition case to APPROVED
                self.case_service.transition_status(
                    case_id,
                    project_id=project_id,
                    new_status=HandoverCaseStatus.APPROVED.value,
                    user_id=user_id,
                    change_reason=f"Approved by reviewer ({user_id})",
                )
                return signoff

            elif request.decision == SignoffDecision.REJECTED.value:
                signoff = self._record_signoff(
                    case=case,
                    version=version,
                    signoff_type=request.signoff_type,
                    signer_user_id=user_id,
                    decision=request.decision,
                    comments=request.comments,
                )
                self.case_service.transition_status(
                    case_id,
                    project_id=project_id,
                    new_status=HandoverCaseStatus.REJECTED.value,
                    user_id=user_id,
                    change_reason=f"Rejected by reviewer: {request.comments or 'No reason provided'}",
                )
                return signoff

            elif request.decision == SignoffDecision.RETURNED_FOR_REVISION.value:
                signoff = self._record_signoff(
                    case=case,
                    version=version,
                    signoff_type=request.signoff_type,
                    signer_user_id=user_id,
                    decision=request.decision,
                    comments=request.comments,
                )
                self.case_service.transition_status(
                    case_id,
                    project_id=project_id,
                    new_status=HandoverCaseStatus.UNDER_REVIEW.value,
                    user_id=user_id,
                    change_reason=f"Returned for revision: {request.comments or 'Revision requested'}",
                )
                return signoff

            else:
                raise BadRequestError(f"Unsupported sign-off decision '{request.decision}'.")

        # Phase 3: Successor Acknowledgement
        elif request.signoff_type == SignoffType.SUCCESSOR_ACKNOWLEDGEMENT.value:
            if user_id != case.successor_id and not is_org_admin:
                raise ForbiddenError("Only the designated successor can submit Phase 3 acknowledgement.")

            signoff = self._record_signoff(
                case=case,
                version=version,
                signoff_type=request.signoff_type,
                signer_user_id=user_id,
                decision=request.decision,
                comments=request.comments,
            )

            if request.decision == SignoffDecision.APPROVED.value:
                if case.status == HandoverCaseStatus.DELIVERED.value:
                    self.case_service.transition_status(
                        case_id,
                        project_id=project_id,
                        new_status=HandoverCaseStatus.ACKNOWLEDGED.value,
                        user_id=user_id,
                        change_reason="Successor acknowledged handover package receipt",
                    )
            return signoff

        else:
            raise BadRequestError(f"Unsupported sign-off type '{request.signoff_type}'.")

    def deliver_package(
        self,
        case_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        request: DeliveryRequest,
    ) -> list[HandoverDelivery]:
        """Deliver an approved package version to successors."""
        case = self.case_service.get_case(case_id, project_id=project_id, load_relationships=False)
        version = self.version_repo.get_by_id(request.version_id, load_sections=False)
        if not version or version.case_id != case.id:
            raise NotFoundError(f"Package version {request.version_id} not found for this case.")

        # Delivery requires the case to be APPROVED
        if case.status != HandoverCaseStatus.APPROVED.value:
            raise BadRequestError(
                f"Cannot deliver package version in case status '{case.status}'. "
                "The package must have completed Phase 2 reviewer approval."
            )

        deliveries: list[HandoverDelivery] = []
        for target_user_id in request.deliver_to_user_ids:
            delivery = HandoverDelivery(
                organisation_id=case.organisation_id,
                project_id=project_id,
                case_id=case.id,
                version_id=version.id,
                delivered_to_user_id=target_user_id,
                delivered_by_user_id=user_id,
                delivery_method=request.delivery_method or HandoverDeliveryMethod.INTERNAL_DOWNLOAD.value,
                artifact_checksum=version.content_hash,
                is_active=True,
            )
            created_d = self.delivery_repo.create(delivery)
            deliveries.append(created_d)

        # Transition Case to DELIVERED
        self.case_service.transition_status(
            case_id,
            project_id=project_id,
            new_status=HandoverCaseStatus.DELIVERED.value,
            user_id=user_id,
            change_reason=f"Delivered package version {version.version_number} to {len(deliveries)} recipients",
        )

        self.audit_service.record_event(
            event_type="handover.package.delivered",
            resource_type="handover_package_version",
            resource_id=str(version.id),
            actor_user_id=user_id,
            organisation_id=case.organisation_id,
            project_id=project_id,
            outcome=AuditOutcome.SUCCESS.value,
            metadata={"recipients_count": len(deliveries)},
        )

        return deliveries

    def acknowledge_delivery(
        self,
        delivery_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        request: AcknowledgementRequest,
    ) -> HandoverAcknowledgement:
        """Successor submits formal acknowledgement of delivered package."""
        delivery = self.delivery_repo.get_by_id(delivery_id)
        if not delivery or delivery.project_id != project_id:
            raise NotFoundError(f"Delivery {delivery_id} not found in this project.")

        if delivery.delivered_to_user_id != user_id:
            raise ForbiddenError("Only the designated recipient can acknowledge this delivery.")

        existing_ack = self.ack_repo.get_by_delivery(delivery.id)
        if existing_ack:
            raise BadRequestError("This delivery has already been acknowledged.")

        now = utc_now()
        ack_str = f"{delivery.id}:{user_id}:{now.isoformat()}:{request.acknowledgement_notes or ''}"
        ack_hash = hashlib.sha256(ack_str.encode("utf-8")).hexdigest()

        ack = HandoverAcknowledgement(
            organisation_id=delivery.organisation_id,
            project_id=project_id,
            delivery_id=delivery.id,
            case_id=delivery.case_id,
            version_id=delivery.version_id,
            acknowledged_by_user_id=user_id,
            acknowledged_at=now,
            acknowledgement_notes=request.acknowledgement_notes,
            acknowledgement_hash=ack_hash,
        )
        created_ack = self.ack_repo.create(ack)

        # Transition case to ACKNOWLEDGED
        case = self.case_service.get_case(delivery.case_id, project_id=project_id, load_relationships=False)
        if case.status == HandoverCaseStatus.DELIVERED.value:
            self.case_service.transition_status(
                case.id,
                project_id=project_id,
                new_status=HandoverCaseStatus.ACKNOWLEDGED.value,
                user_id=user_id,
                change_reason=f"Successor acknowledged receipt (hash: {ack_hash[:12]}...)",
            )

        self.audit_service.record_event(
            event_type="handover.delivery.acknowledged",
            resource_type="handover_delivery",
            resource_id=str(delivery.id),
            actor_user_id=user_id,
            organisation_id=delivery.organisation_id,
            project_id=project_id,
            outcome=AuditOutcome.SUCCESS.value,
            metadata={"acknowledgement_hash": ack_hash},
        )

        return created_ack

    def _record_signoff(
        self,
        *,
        case: HandoverCase,
        version: HandoverPackageVersion,
        signoff_type: str,
        signer_user_id: uuid.UUID,
        decision: str,
        comments: str | None,
    ) -> HandoverSignoff:
        now = utc_now()
        sig_data = f"{version.id}:{signoff_type}:{decision}:{signer_user_id}:{now.isoformat()}:{comments or ''}"
        sig_hash = hashlib.sha256(sig_data.encode("utf-8")).hexdigest()

        signoff = HandoverSignoff(
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            case_id=case.id,
            version_id=version.id,
            signoff_type=signoff_type,
            signer_user_id=signer_user_id,
            decision=decision,
            comments=comments,
            signed_at=now,
            signature_hash=sig_hash,
        )
        created_sig = self.signoff_repo.create(signoff)

        self.audit_service.record_event(
            event_type="handover.signoff.recorded",
            resource_type="handover_signoff",
            resource_id=str(created_sig.id),
            actor_user_id=signer_user_id,
            organisation_id=case.organisation_id,
            project_id=case.project_id,
            outcome=AuditOutcome.SUCCESS.value,
            metadata={
                "signoff_type": signoff_type,
                "decision": decision,
                "signature_hash": sig_hash,
            },
        )
        return created_sig
