"""End-to-end API, RBAC, source-ACL, worker retry, and staleness tests for Phase 2.6."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.enums import (
    BackgroundJobStatus,
    BackgroundJobType,
    EpistemicStatus,
    EvidenceProcessingStatus,
    EvidenceSourceType,
    ExtractionRunStatus,
    IntegrationProvider,
    KnowledgeCategory,
    KnowledgeReviewStatus,
    OrganisationMembershipStatus,
    SourcePermissionVerificationStatus,
    SourceVisibilityPolicy,
    SupportClassification,
)
from app.models.integration import SourceAccessPolicy, SourceConnection
from app.models.job import BackgroundJob
from app.models.organisation import OrganisationMembership
from app.repositories.evidence import EvidenceRepository
from app.repositories.job import BackgroundJobRepository
from app.services.chunking import ChunkingService
from app.services.document_extraction import ExtractedPageData
from app.services.indexing_worker import IndexingWorkerService
from app.services.integrations.evidence_ingestor import (
    NormalizedSourceEvidence,
    SourceEvidenceIngestor,
)
from app.services.llm import (
    LLMExecutionError,
    LLMGenerationRequest,
    LLMGenerationResult,
)
from app.services.reconstruction_worker import ReconstructionWorkerService
from tests.conftest import (
    invite_and_accept_member,
    isolated_auth_app,
    register_and_login_user,
)
from tests.helpers_retrieval import InMemoryEmbeddingService, InMemoryVectorStoreClient


def _page(text: str, section: str | None = None) -> ExtractedPageData:
    return ExtractedPageData(
        page_number=1,
        extraction_outcome="digital_text",
        ocr_applied=False,
        ocr_truncated=False,
        text_content=text,
        structured_metadata={"section": section} if section else {},
    )


def _seed_project_member(
    client: TestClient,
    *,
    owner_headers: dict[str, str],
    org_id: str,
    proj_id: str,
    user: object,
    role_name: str,
) -> None:
    invite_and_accept_member(
        client,
        organisation_id=org_id,
        inviter_headers=owner_headers,
        invitee=user,  # type: ignore[arg-type]
        role_name="org_member",
    )
    add_m = client.post(
        f"/api/v1/projects/{proj_id}/members",
        headers=owner_headers,
        json={"user_id": str(user.user_id), "role_name": role_name},  # type: ignore[attr-defined]
    )
    assert add_m.status_code == 201


@dataclass
class ScriptedFakeLLMClient:
    """Deterministic test double implementing StructuredLLMClient protocol."""

    model: str = "qwen3:8b"
    seen_prompts: list[tuple[str, str]] = field(default_factory=list)
    fail_first_invalid_json: bool = False
    _invalid_json_emitted: bool = False
    raise_transient_error: bool = False

    @property
    def model_name(self) -> str:
        return self.model

    def generate_json(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        self.seen_prompts.append((request.system_prompt, request.user_prompt))
        if self.raise_transient_error:
            raise LLMExecutionError(
                code="LLM_UNAVAILABLE",
                message="Simulated temporary Ollama outage.",
                retryable=True,
                prompt_tokens=15,
                completion_tokens=0,
            )

        if self.fail_first_invalid_json and not self._invalid_json_emitted:
            self._invalid_json_emitted = True
            raise LLMExecutionError(
                code="LLM_INVALID_JSON",
                message="Simulated first-attempt malformed JSON.",
                retryable=True,
                prompt_tokens=40,
                completion_tokens=12,
            )

        chunk_ids: list[str] = []
        marker = 'chunk_id="'
        idx = 0
        while True:
            pos = request.user_prompt.find(marker, idx)
            if pos == -1:
                break
            start = pos + len(marker)
            end = request.user_prompt.find('"', start)
            if end != -1:
                chunk_ids.append(request.user_prompt[start:end])
            idx = start

        items: list[dict[str, object]] = []
        primary_cid = chunk_ids[0] if chunk_ids else str(uuid.uuid4())
        user_p = request.user_prompt

        if "decisions_rationale" in user_p:
            if "PostgreSQL 16 as our canonical store" in user_p:
                items.append(
                    {
                        "title": "Select PostgreSQL 16 as canonical store",
                        "description": "Team selected PostgreSQL 16 for durable records.",
                        "decision_category": "architectural",
                        "decision_maker": "Alex Chen",
                        "decision_date": "2026-10-15",
                        "rationale": "Strong relational integrity.",
                        "alternatives_considered": ["Neo4j"],
                        "chosen_approach": "PostgreSQL 16",
                        "decision_status": "accepted",
                        "is_interpretation": False,
                        "is_uncertain": False,
                        "confidence_level": "high",
                        "evidence_refs": [
                            {
                                "chunk_id": primary_cid,
                                "supporting_excerpt": (
                                    "selected PostgreSQL 16 as our canonical store"
                                ),
                                "support_type": "direct",
                            }
                        ],
                    }
                )
            # Also inject an ungrounded hallucinated item that MUST be dropped
            items.append(
                {
                    "title": "Hallucinated Redis decision",
                    "description": "Should be rejected by backend validator.",
                    "decision_status": "accepted",
                    "confidence_level": "high",
                    "evidence_refs": [
                        {
                            "chunk_id": primary_cid,
                            "supporting_excerpt": "Team migrated everything onto Redis Cluster.",
                            "support_type": "direct",
                        }
                    ],
                }
            )
        elif "responsibilities_ownership" in user_p:
            if "Priya Nair maintains the FastAPI ingestion worker" in user_p:
                items.append(
                    {
                        "person_identity": "Priya Nair",
                        "person_identifier_type": "display_name",
                        "title": "FastAPI ingestion worker maintainer",
                        "description": "Priya Nair maintains the FastAPI ingestion worker.",
                        "component_or_workstream": "backend/app/services/ingestion_worker.py",
                        "ownership_role": "maintainer",
                        "ownership_basis": "explicitly_assigned",
                        "ownership_status": "active",
                        "confidence_level": "high",
                        "evidence_refs": [
                            {
                                "chunk_id": primary_cid,
                                "supporting_excerpt": (
                                    "Priya Nair maintains the FastAPI ingestion worker"
                                ),
                                "support_type": "direct",
                            }
                        ],
                    }
                )
            if "Secret Ops Key Rotation belongs to Security Lead" in user_p:
                items.append(
                    {
                        "person_identity": "Security Lead",
                        "person_identifier_type": "role_label",
                        "title": "Secret Ops Key Rotation owner",
                        "description": "Security Lead handles restricted key rotation.",
                        "component_or_workstream": "secrets-vault",
                        "ownership_role": "owner",
                        "ownership_basis": "explicitly_assigned",
                        "ownership_status": "active",
                        "confidence_level": "high",
                        "evidence_refs": [
                            {
                                "chunk_id": primary_cid,
                                "supporting_excerpt": (
                                    "Secret Ops Key Rotation belongs to Security Lead"
                                ),
                                "support_type": "direct",
                            }
                        ],
                    }
                )
        elif "technical_architecture" in user_p:
            if "POST /api/v1/projects/{project_id}/knowledge/extract" in user_p:
                items.append(
                    {
                        "title": "Knowledge extract endpoint behavior",
                        "description": "Endpoint dispatches background reconstruction job.",
                        "technical_category": "api_behaviour",
                        "exact_identifiers": [
                            "POST /api/v1/projects/{project_id}/knowledge/extract"
                        ],
                        "components": ["knowledge-api"],
                        "technical_status": "active",
                        "confidence_level": "high",
                        "evidence_refs": [
                            {
                                "chunk_id": primary_cid,
                                "supporting_excerpt": (
                                    "POST /api/v1/projects/{project_id}/knowledge/extract"
                                ),
                                "support_type": "direct",
                            }
                        ],
                    }
                )

        return LLMGenerationResult(
            parsed_json={"items": items},
            raw_text="{}",
            model_name=self.model,
            prompt_tokens=110,
            completion_tokens=45,
            duration_ms=42,
            done_reason="stop",
            truncated=False,
        )


def test_knowledge_reconstruction_rbac_acl_grounding_and_filters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_embed = InMemoryEmbeddingService(dims=64)
    fake_chroma = InMemoryVectorStoreClient(expected_dimensions=64)
    fake_llm = ScriptedFakeLLMClient()

    with isolated_auth_app(
        monkeypatch,
        upload_storage_path=tmp_path / "know_uploads",
        embedding_expected_dimensions=64,
    ) as ctx:
        ctx.app.state.embedding_service = fake_embed
        ctx.app.state.vector_store_client = fake_chroma

        indexing_worker = IndexingWorkerService(
            session_factory=ctx.session_factory,
            chunking_service=ChunkingService(settings=ctx.settings.chunking),
            embedding_service=fake_embed,
            vector_store=fake_chroma,
            ingestion_settings=ctx.settings.ingestion,
        )
        recon_worker = ReconstructionWorkerService(
            session_factory=ctx.session_factory,
            llm_client=fake_llm,
            extraction_settings=ctx.settings.extraction,
            ingestion_settings=ctx.settings.ingestion,
        )

        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client, email="kr-owner@example.com", full_name="KR Owner"
            )
            contributor = register_and_login_user(
                client, email="kr-contrib@example.com", full_name="KR Contributor"
            )
            reviewer = register_and_login_user(
                client, email="kr-reviewer@example.com", full_name="KR Reviewer"
            )
            outsider = register_and_login_user(
                client, email="kr-outsider@example.com", full_name="KR Outsider"
            )

            org_a = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "KR Org A"},
            ).json()
            proj_a = client.post(
                f"/api/v1/organisations/{org_a['id']}/projects",
                headers=owner.headers,
                json={"name": "KR Project A", "status": "active", "visibility": "private"},
            ).json()
            org_b = client.post(
                "/api/v1/organisations",
                headers=outsider.headers,
                json={"name": "KR Org B"},
            ).json()
            proj_b = client.post(
                f"/api/v1/organisations/{org_b['id']}/projects",
                headers=outsider.headers,
                json={"name": "KR Project B", "status": "active", "visibility": "private"},
            ).json()

            _seed_project_member(
                client,
                owner_headers=owner.headers,
                org_id=org_a["id"],
                proj_id=proj_a["id"],
                user=contributor,
                role_name="project_member",
            )
            _seed_project_member(
                client,
                owner_headers=owner.headers,
                org_id=org_a["id"],
                proj_id=proj_a["id"],
                user=reviewer,
                role_name="reviewer",
            )

            pid = uuid.UUID(proj_a["id"])
            oid = uuid.UUID(org_a["id"])
            t_now = datetime(2026, 10, 15, tzinfo=UTC)

            # Seed shared doc + restricted GitHub issue + synthetic note directly
            with ctx.session_factory() as session:
                job_repo = BackgroundJobRepository(session)
                ev_repo = EvidenceRepository(session)
                ingestor = SourceEvidenceIngestor(
                    session=session,
                    evidence_repository=ev_repo,
                    job_repository=job_repo,
                )

                shared_text = (
                    "Alex Chen selected PostgreSQL 16 as our canonical store. "
                    "Priya Nair maintains the FastAPI ingestion worker. "
                    "API route POST /api/v1/projects/{project_id}/knowledge/extract "
                    "queues extraction."
                )
                shared_doc = ev_repo.create_evidence_item(
                    organisation_id=oid,
                    project_id=pid,
                    uploaded_by_user_id=owner.user_id,
                    source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
                    source_provider="local_upload",
                    category="pdf_document",
                    source_external_id="upload:shared-adr",
                    source_url=None,
                    source_author_identity="Alex Chen",
                    title="shared-adr.pdf",
                    original_filename="shared-adr.pdf",
                    mime_type="application/pdf",
                    file_size_bytes=1024,
                    content_hash="11" * 32,
                    storage_provider=None,
                    storage_object_key=None,
                    encryption_algorithm=None,
                    encryption_key_id=None,
                    acl_scope="project_members",
                    source_created_at=t_now,
                    source_updated_at=t_now,
                    extracted_at=t_now,
                    processing_status=EvidenceProcessingStatus.EXTRACTED.value,
                    extraction_method="pymupdf",
                    page_count=1,
                    metadata_json={},
                )
                ev_repo.replace_extracted_content(
                    evidence_id=shared_doc.id,
                    extracted_text=shared_text,
                    warnings=(),
                    pages=(_page(shared_text, section="ADR-001"),),
                )
                job_repo.create_job(
                    organisation_id=oid,
                    project_id=pid,
                    evidence_id=shared_doc.id,
                    triggered_by_user_id=owner.user_id,
                    job_type=BackgroundJobType.EVIDENCE_INDEXING.value,
                )

                # Restricted GitHub source ACL accessible ONLY to owner
                gh_conn = SourceConnection(
                    organisation_id=oid,
                    provider=IntegrationProvider.GITHUB.value,
                    display_name="Owner Private GH",
                    created_by_user_id=owner.user_id,
                    status="active",
                    metadata_json={},
                )
                session.add(gh_conn)
                session.flush()
                restricted_policy = SourceAccessPolicy(
                    organisation_id=oid,
                    project_id=pid,
                    source_connection_id=gh_conn.id,
                    provider=IntegrationProvider.GITHUB.value,
                    scope_identifier="acme/secret-repo",
                    visibility_policy=SourceVisibilityPolicy.RESTRICTED_FAIL_CLOSED.value,
                    sync_permission_status=SourcePermissionVerificationStatus.VERIFIED.value,
                    allowed_user_ids=[str(owner.user_id)],
                )
                session.add(restricted_policy)
                session.flush()

                restricted_text = (
                    "Secret Ops Key Rotation belongs to Security Lead and uses vault. "
                    "Alex Chen selected PostgreSQL 16 as our canonical store."
                )
                restricted_res = ingestor.upsert_record(
                    organisation_id=oid,
                    project_id=pid,
                    source_connection_id=gh_conn.id,
                    triggered_by_user_id=owner.user_id,
                    record=NormalizedSourceEvidence(
                        source_type=EvidenceSourceType.GITHUB.value,
                        source_provider="github",
                        category="issue",
                        source_external_id="acme/secret-repo#99",
                        title="Restricted Security Issue #99",
                        source_url="https://github.com/acme/secret-repo/issues/99",
                        source_author_identity="security-lead",
                        acl_scope="source_restricted",
                        source_access_policy_id=restricted_policy.id,
                        source_created_at=datetime(2026, 10, 20, tzinfo=UTC),
                        source_updated_at=datetime(2026, 10, 20, tzinfo=UTC),
                        extraction_method="github_api",
                        extracted_text=restricted_text,
                        pages=(_page(restricted_text, section="issue_body"),),
                        metadata_json={"repository": "acme/secret-repo", "number": 99},
                    ),
                )
                restricted_ev = restricted_res.evidence_item

                # Clearly marked synthetic evidence
                syn_text = "Alex Chen selected PostgreSQL 16 as our canonical store [synthetic]."
                synthetic_ev = ev_repo.create_evidence_item(
                    organisation_id=oid,
                    project_id=pid,
                    uploaded_by_user_id=owner.user_id,
                    source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
                    source_provider="local_upload",
                    category="design_document",
                    source_external_id="upload:synthetic-doc",
                    source_url=None,
                    source_author_identity="fixture-author",
                    title="synthetic-benchmark.pdf",
                    original_filename="synthetic-benchmark.pdf",
                    mime_type="application/pdf",
                    file_size_bytes=512,
                    content_hash="22" * 32,
                    storage_provider=None,
                    storage_object_key=None,
                    encryption_algorithm=None,
                    encryption_key_id=None,
                    acl_scope="project_members",
                    source_created_at=t_now,
                    source_updated_at=t_now,
                    extracted_at=t_now,
                    processing_status=EvidenceProcessingStatus.EXTRACTED.value,
                    extraction_method="pymupdf",
                    page_count=1,
                    metadata_json={"is_synthetic": True, "fixture_tag": "synthetic_eval"},
                )
                ev_repo.replace_extracted_content(
                    evidence_id=synthetic_ev.id,
                    extracted_text=syn_text,
                    warnings=(),
                    pages=(_page(syn_text),),
                )
                job_repo.create_job(
                    organisation_id=oid,
                    project_id=pid,
                    evidence_id=synthetic_ev.id,
                    triggered_by_user_id=owner.user_id,
                    job_type=BackgroundJobType.EVIDENCE_INDEXING.value,
                )
                session.commit()

            assert indexing_worker.drain_pending_jobs(max_jobs=10) == 3

            # 1. Unauthenticated / cross-tenant / reviewer-cannot-trigger guards
            unauth = client.post(f"/api/v1/projects/{proj_a['id']}/knowledge/extract")
            assert unauth.status_code == 401

            cross_org = client.get(
                f"/api/v1/projects/{proj_b['id']}/knowledge/items",
                headers=owner.headers,
            )
            assert cross_org.status_code == 404

            rev_trigger = client.post(
                f"/api/v1/projects/{proj_a['id']}/knowledge/extract",
                headers=reviewer.headers,
                json={},
            )
            assert rev_trigger.status_code == 403

            # 2. Contributor CANNOT extract restricted GitHub evidence directly (fail closed)
            contrib_restricted = client.post(
                f"/api/v1/projects/{proj_a['id']}/evidence/{restricted_ev.id}/extract",
                headers=contributor.headers,
                json={},
            )
            assert contrib_restricted.status_code == 403
            assert contrib_restricted.json()["error"]["code"] == "SOURCE_ACCESS_DENIED"

            # 3. Owner extracts ALL non-synthetic evidence (shared + restricted)
            trig_resp = client.post(
                f"/api/v1/projects/{proj_a['id']}/knowledge/extract",
                headers=owner.headers,
                json={"include_synthetic": False},
            )
            assert trig_resp.status_code == 202
            trig_data = trig_resp.json()
            assert trig_data["already_active"] is False
            run_id = trig_data["run"]["id"]

            # Active-run idempotency check
            dup_trig = client.post(
                f"/api/v1/projects/{proj_a['id']}/knowledge/extract",
                headers=owner.headers,
                json={},
            )
            assert dup_trig.status_code == 202
            assert dup_trig.json()["already_active"] is True
            assert dup_trig.json()["run"]["id"] == run_id

            # Execute reconstruction worker
            assert recon_worker.drain_pending_jobs(max_jobs=5) == 1

            run_detail = client.get(
                f"/api/v1/projects/{proj_a['id']}/knowledge/runs/{run_id}",
                headers=owner.headers,
            )
            assert run_detail.status_code == 200
            r_json = run_detail.json()
            assert r_json["status"] == ExtractionRunStatus.COMPLETED.value
            # 1 decision + 1 shared owner + 1 restricted owner + 1 tech = 4 persisted,
            # PostgreSQL decision corroborated across shared_doc & restricted_ev (1 merged!),
            # hallucinated Redis dropped across every DECISIONS batch!
            assert r_json["claims_persisted"] == 4
            assert r_json["duplicates_merged"] == 1
            assert r_json["claims_rejected_ungrounded"] >= 2
            assert r_json["prompt_tokens"] > 0

            # Verify ZERO cross-ACL prompt mixing: no single LLM user prompt contained BOTH items
            for _sys_p, usr_p in fake_llm.seen_prompts:
                assert not (
                    "Secret Ops Key Rotation" in usr_p and "Priya Nair maintains" in usr_p
                )

            # 4. Owner sees ALL 4 items (including Secret Ops + corroborated 2-link decision)
            owner_list = client.get(
                f"/api/v1/projects/{proj_a['id']}/knowledge/items",
                headers=owner.headers,
            )
            assert owner_list.status_code == 200
            owner_items = owner_list.json()["items"]
            assert owner_list.json()["total"] == 4
            pg_decision = next(
                it for it in owner_items if it["title"] == "Select PostgreSQL 16 as canonical store"
            )
            assert pg_decision["support_classification"] == SupportClassification.CORROBORATED.value
            assert pg_decision["evidence_links_count"] == 2
            assert pg_decision["epistemic_status"] == EpistemicStatus.EXTRACTED.value
            assert pg_decision["review_status"] == KnowledgeReviewStatus.PENDING_REVIEW.value

            secret_item = next(
                it for it in owner_items if it["title"] == "Secret Ops Key Rotation owner"
            )

            # 5. Contributor MUST NOT see Secret Ops item in list, MUST get 403 on detail,
            #    and on PostgreSQL decision sees ONLY 1 link (restricted GH link filtered!)
            contrib_list = client.get(
                f"/api/v1/projects/{proj_a['id']}/knowledge/items",
                headers=contributor.headers,
            )
            assert contrib_list.status_code == 200
            c_items = contrib_list.json()["items"]
            assert contrib_list.json()["total"] == 3
            assert all(it["id"] != secret_item["id"] for it in c_items)
            c_pg = next(
                it for it in c_items if it["title"] == "Select PostgreSQL 16 as canonical store"
            )
            assert c_pg["evidence_links_count"] == 1

            c_secret_detail = client.get(
                f"/api/v1/projects/{proj_a['id']}/knowledge/items/{secret_item['id']}",
                headers=contributor.headers,
            )
            assert c_secret_detail.status_code == 403
            assert c_secret_detail.json()["error"]["code"] == "SOURCE_ACCESS_DENIED"

            c_pg_detail = client.get(
                f"/api/v1/projects/{proj_a['id']}/knowledge/items/{pg_decision['id']}",
                headers=contributor.headers,
            )
            assert c_pg_detail.status_code == 200
            assert len(c_pg_detail.json()["evidence_links"]) == 1
            assert c_pg_detail.json()["evidence_links"][0]["evidence_id"] == str(shared_doc.id)

            # 6. Category, person, identifier, and status filters + synthetic exclusion
            by_person = client.get(
                f"/api/v1/projects/{proj_a['id']}/knowledge/items",
                headers=contributor.headers,
                params={
                    "category": KnowledgeCategory.RESPONSIBILITIES_OWNERSHIP.value,
                    "person": "Priya",
                },
            )
            assert by_person.status_code == 200
            assert by_person.json()["total"] == 1
            assert by_person.json()["items"][0]["person_or_owner_label"] == "Priya Nair"

            # Trigger synthetic evidence explicitly -> invisible unless include_synthetic=true
            syn_trig = client.post(
                f"/api/v1/projects/{proj_a['id']}/evidence/{synthetic_ev.id}/extract",
                headers=owner.headers,
                json={"categories": [KnowledgeCategory.DECISIONS_RATIONALE.value]},
            )
            assert syn_trig.status_code == 202
            assert recon_worker.drain_pending_jobs(max_jobs=5) == 1

            non_syn_list = client.get(
                f"/api/v1/projects/{proj_a['id']}/knowledge/items",
                headers=owner.headers,
                params={"include_synthetic": False},
            )
            assert non_syn_list.json()["total"] == 4
            with_syn_list = client.get(
                f"/api/v1/projects/{proj_a['id']}/knowledge/items",
                headers=owner.headers,
                params={"include_synthetic": True},
            )
            assert with_syn_list.json()["total"] == 5

            status_summary = client.get(
                f"/api/v1/projects/{proj_a['id']}/knowledge/status",
                headers=contributor.headers,
            )
            assert status_summary.status_code == 200
            assert status_summary.json()["total_accessible_items"] == 3

            # 7. Cancel & Retry endpoints
            single_re = client.post(
                f"/api/v1/projects/{proj_a['id']}/evidence/{shared_doc.id}/extract",
                headers=contributor.headers,
                json={"categories": [KnowledgeCategory.WORK_ITEMS.value]},
            )
            assert single_re.status_code == 202
            cancel_id = single_re.json()["run"]["id"]
            cancelled = client.post(
                f"/api/v1/projects/{proj_a['id']}/knowledge/runs/{cancel_id}/cancel",
                headers=contributor.headers,
            )
            assert cancelled.status_code == 200
            assert cancelled.json()["status"] == ExtractionRunStatus.CANCELLED.value

            retried = client.post(
                f"/api/v1/projects/{proj_a['id']}/knowledge/runs/{cancel_id}/retry",
                headers=contributor.headers,
            )
            assert retried.status_code == 202
            assert retried.json()["run"]["status"] == ExtractionRunStatus.QUEUED.value
            assert recon_worker.drain_pending_jobs(max_jobs=5) == 1

            # 8. Soft-deleting shared_doc marks all 3 linked items stale in PostgreSQL,
            #    while API reads only surface items that still have >= 1 active accessible link!
            del_resp = client.delete(
                f"/api/v1/evidence/{shared_doc.id}",
                headers=owner.headers,
            )
            assert del_resp.status_code == 204
            stale_list = client.get(
                f"/api/v1/projects/{proj_a['id']}/knowledge/items",
                headers=owner.headers,
                params={"stale_only": True},
            )
            assert stale_list.status_code == 200
            assert stale_list.json()["total"] == 1
            assert stale_list.json()["items"][0]["id"] == pg_decision["id"]
            assert stale_list.json()["items"][0]["is_stale"] is True
            assert (
                stale_list.json()["items"][0]["stale_reason"]
                == "supporting_evidence_deleted"
            )
            contrib_stale = client.get(
                f"/api/v1/projects/{proj_a['id']}/knowledge/items",
                headers=contributor.headers,
                params={"stale_only": True},
            )
            assert contrib_stale.status_code == 200
            assert contrib_stale.json()["total"] == 0

            # Verify ACL denial audit event + DB staleness across all 3 items backed by shared_doc
            from app.models.knowledge import KnowledgeItem

            with ctx.session_factory() as session:
                stale_db_items = list(
                    session.execute(
                        select(KnowledgeItem).where(
                            KnowledgeItem.project_id == pid,
                            KnowledgeItem.is_stale.is_(True),
                            KnowledgeItem.stale_reason == "supporting_evidence_deleted",
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(stale_db_items) == 3
                acl_audits = list(
                    session.execute(
                        select(AuditLog).where(
                            AuditLog.event_type == "knowledge.source_acl_denied"
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(acl_audits) >= 1


def test_worker_json_repair_transient_retry_permission_revocation_and_rechunk_staleness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_embed = InMemoryEmbeddingService(dims=64)
    fake_chroma = InMemoryVectorStoreClient(expected_dimensions=64)
    fake_llm = ScriptedFakeLLMClient(fail_first_invalid_json=True)

    with isolated_auth_app(
        monkeypatch,
        upload_storage_path=tmp_path / "know_retry_uploads",
        embedding_expected_dimensions=64,
        extraction_auto_reextract_on_update=True,
    ) as ctx:
        indexing_worker = IndexingWorkerService(
            session_factory=ctx.session_factory,
            chunking_service=ChunkingService(settings=ctx.settings.chunking),
            embedding_service=fake_embed,
            vector_store=fake_chroma,
            ingestion_settings=ctx.settings.ingestion,
            extraction_settings=ctx.settings.extraction,
            llm_model_name=ctx.settings.ollama.llm_model,
        )
        recon_worker = ReconstructionWorkerService(
            session_factory=ctx.session_factory,
            llm_client=fake_llm,
            extraction_settings=ctx.settings.extraction,
            ingestion_settings=ctx.settings.ingestion,
        )

        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client, email="kr2-owner@example.com", full_name="KR2 Owner"
            )
            contrib = register_and_login_user(
                client, email="kr2-contrib@example.com", full_name="KR2 Contrib"
            )
            org = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "KR2 Org"},
            ).json()
            proj = client.post(
                f"/api/v1/organisations/{org['id']}/projects",
                headers=owner.headers,
                json={"name": "KR2 Proj", "status": "active", "visibility": "private"},
            ).json()
            _seed_project_member(
                client,
                owner_headers=owner.headers,
                org_id=org["id"],
                proj_id=proj["id"],
                user=contrib,
                role_name="project_member",
            )

            oid = uuid.UUID(org["id"])
            pid = uuid.UUID(proj["id"])
            t_now = datetime(2026, 10, 15, tzinfo=UTC)
            with ctx.session_factory() as session:
                ev_repo = EvidenceRepository(session)
                t1_text = "Alex Chen selected PostgreSQL 16 as our canonical store."
                ev = ev_repo.create_evidence_item(
                    organisation_id=oid,
                    project_id=pid,
                    uploaded_by_user_id=contrib.user_id,
                    source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
                    source_provider="local_upload",
                    category="pdf_document",
                    source_external_id="upload:retry-doc",
                    source_url=None,
                    source_author_identity="Alex Chen",
                    title="retry-doc.pdf",
                    original_filename="retry-doc.pdf",
                    mime_type="application/pdf",
                    file_size_bytes=512,
                    content_hash="33" * 32,
                    storage_provider=None,
                    storage_object_key=None,
                    encryption_algorithm=None,
                    encryption_key_id=None,
                    acl_scope="project_members",
                    source_created_at=t_now,
                    source_updated_at=t_now,
                    extracted_at=t_now,
                    processing_status=EvidenceProcessingStatus.EXTRACTED.value,
                    extraction_method="pymupdf",
                    page_count=1,
                    metadata_json={},
                )
                ev_repo.replace_extracted_content(
                    evidence_id=ev.id,
                    extracted_text=t1_text,
                    warnings=(),
                    pages=(_page(t1_text, section="S1"),),
                )
                BackgroundJobRepository(session).create_job(
                    organisation_id=oid,
                    project_id=pid,
                    evidence_id=ev.id,
                    triggered_by_user_id=contrib.user_id,
                    job_type=BackgroundJobType.EVIDENCE_INDEXING.value,
                )
                session.commit()

            assert indexing_worker.drain_pending_jobs(max_jobs=5) == 1

            # 1. Invalid JSON on attempt 1 -> automatic repair prompt recovers cleanly!
            t1 = client.post(
                f"/api/v1/projects/{proj['id']}/evidence/{ev.id}/extract",
                headers=contrib.headers,
                json={"categories": [KnowledgeCategory.DECISIONS_RATIONALE.value]},
            )
            assert t1.status_code == 202
            run1_id = t1.json()["run"]["id"]
            assert recon_worker.drain_pending_jobs(max_jobs=5) == 1

            r1 = client.get(
                f"/api/v1/projects/{proj['id']}/knowledge/runs/{run1_id}",
                headers=contrib.headers,
            ).json()
            assert r1["status"] == ExtractionRunStatus.COMPLETED.value
            assert r1["claims_persisted"] == 1
            assert r1["batches_executed"] == 2  # 1 failed JSON + 1 repaired

            # 2. Re-indexing updated text marks old knowledge stale AND auto-queues reextraction!
            with ctx.session_factory() as session:
                ev_db_repo = EvidenceRepository(session)
                updated_text = "Alex Chen selected PostgreSQL 16 as our canonical store on Oct 18."
                ev_db_repo.replace_extracted_content(
                    evidence_id=ev.id,
                    extracted_text=updated_text,
                    warnings=(),
                    pages=(_page(updated_text, section="S1"),),
                )
                BackgroundJobRepository(session).create_job(
                    organisation_id=oid,
                    project_id=pid,
                    evidence_id=ev.id,
                    triggered_by_user_id=owner.user_id,
                    job_type=BackgroundJobType.EVIDENCE_REINDEXING.value,
                )
                session.commit()

            assert indexing_worker.drain_pending_jobs(max_jobs=5) == 1
            # Old claim must be stale AND a new knowledge_reconstruction job must now be queued!
            stale_resp = client.get(
                f"/api/v1/projects/{proj['id']}/knowledge/items",
                headers=owner.headers,
                params={"stale_only": True},
            )
            assert stale_resp.json()["total"] == 1
            assert recon_worker.drain_pending_jobs(max_jobs=5) == 1

            # 3. Transient LLM outage schedules job retry with backoff
            fake_llm.raise_transient_error = True
            t2 = client.post(
                f"/api/v1/projects/{proj['id']}/evidence/{ev.id}/extract",
                headers=contrib.headers,
                json={
                    "categories": [KnowledgeCategory.DECISIONS_RATIONALE.value],
                    "force_rerun": True,
                },
            )
            assert t2.status_code == 202
            run2_id = t2.json()["run"]["id"]
            assert recon_worker.process_next_job() is True
            r2 = client.get(
                f"/api/v1/projects/{proj['id']}/knowledge/runs/{run2_id}",
                headers=contrib.headers,
            ).json()
            assert r2["status"] == ExtractionRunStatus.QUEUED.value
            assert r2["error_code"] == "LLM_UNAVAILABLE"

            # 4. If actor org membership is suspended before queued job runs, worker fails closed!
            fake_llm.raise_transient_error = False
            with ctx.session_factory() as session:
                mem = session.execute(
                    select(OrganisationMembership).where(
                        OrganisationMembership.organisation_id == oid,
                        OrganisationMembership.user_id == contrib.user_id,
                    )
                ).scalar_one()
                mem.status = OrganisationMembershipStatus.SUSPENDED.value
                # Clear next_retry_at so worker can claim immediately
                queued_jobs = list(
                    session.execute(
                        select(BackgroundJob).where(
                            BackgroundJob.project_id == pid,
                            BackgroundJob.job_type
                            == BackgroundJobType.KNOWLEDGE_RECONSTRUCTION.value,
                            BackgroundJob.status == BackgroundJobStatus.QUEUED.value,
                        )
                    )
                    .scalars()
                    .all()
                )
                for job in queued_jobs:
                    job.next_retry_at = datetime.now(UTC) - timedelta(seconds=1)
                session.commit()

            assert recon_worker.process_next_job() is True
            r2_after = client.get(
                f"/api/v1/projects/{proj['id']}/knowledge/runs/{run2_id}",
                headers=owner.headers,
            ).json()
            assert r2_after["status"] == ExtractionRunStatus.FAILED.value
            assert r2_after["error_code"] == "EXTRACTION_PERMISSION_REVOKED"
