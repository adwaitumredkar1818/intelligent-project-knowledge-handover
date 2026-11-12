"""Security, tenant isolation, source ACL, degraded-mode & API tests for Phase 2.5 retrieval."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.enums import (
    EvidenceChunkType,
    EvidenceProcessingStatus,
    EvidenceSourceType,
    SourcePermissionVerificationStatus,
    SourceVisibilityPolicy,
)
from app.models.integration import SourceAccessPolicy, SourceConnection
from app.repositories.evidence import EvidenceRepository
from app.repositories.job import BackgroundJobRepository
from app.services.chunking import ChunkingService
from app.services.document_extraction import ExtractedPageData
from app.services.indexing_worker import IndexingWorkerService
from app.services.integrations.evidence_ingestor import (
    NormalizedSourceEvidence,
    SourceEvidenceIngestor,
)
from tests.conftest import (
    invite_and_accept_member,
    isolated_auth_app,
    register_and_login_user,
)
from tests.helpers_retrieval import (
    InMemoryEmbeddingService,
    InMemoryVectorStoreClient,
    _text_to_unit_vector,
)


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


def test_retrieval_rbac_source_acl_stale_chroma_filter_and_degraded_modes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_embed = InMemoryEmbeddingService(dims=64)
    fake_chroma = InMemoryVectorStoreClient(expected_dimensions=64)

    with isolated_auth_app(
        monkeypatch,
        upload_storage_path=tmp_path / "retrieval_uploads",
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

        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client, email="ret-owner@example.com", full_name="Ret Owner"
            )
            reviewer = register_and_login_user(
                client, email="ret-reviewer@example.com", full_name="Ret Reviewer"
            )
            contributor = register_and_login_user(
                client, email="ret-contrib@example.com", full_name="Ret Contributor"
            )
            org_non_member = register_and_login_user(
                client, email="ret-orgmem@example.com", full_name="Org Member"
            )
            outsider = register_and_login_user(
                client, email="ret-outsider@example.com", full_name="Outsider"
            )

            org_a = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "Retrieval Org A"},
            ).json()
            org_b = client.post(
                "/api/v1/organisations",
                headers=outsider.headers,
                json={"name": "Retrieval Org B"},
            ).json()

            priv_proj = client.post(
                f"/api/v1/organisations/{org_a['id']}/projects",
                headers=owner.headers,
                json={"name": "Private Core", "status": "active", "visibility": "private"},
            ).json()
            org_vis_proj = client.post(
                f"/api/v1/organisations/{org_a['id']}/projects",
                headers=owner.headers,
                json={"name": "Org Visible Core", "status": "active", "visibility": "organisation"},
            ).json()
            other_org_proj = client.post(
                f"/api/v1/organisations/{org_b['id']}/projects",
                headers=outsider.headers,
                json={"name": "Foreign Org Project", "status": "active", "visibility": "private"},
            ).json()

            proj_id = priv_proj["id"]
            org_a_id = uuid.UUID(org_a["id"])
            proj_uuid = uuid.UUID(proj_id)

            _seed_project_member(
                client,
                owner_headers=owner.headers,
                org_id=org_a["id"],
                proj_id=proj_id,
                user=reviewer,
                role_name="reviewer",
            )
            _seed_project_member(
                client,
                owner_headers=owner.headers,
                org_id=org_a["id"],
                proj_id=proj_id,
                user=contributor,
                role_name="project_member",
            )
            invite_and_accept_member(
                client,
                organisation_id=org_a["id"],
                inviter_headers=owner.headers,
                invitee=org_non_member,
                role_name="org_member",
            )

            # Seed multi-source evidence with distinct ACL scopes & dates
            with ctx.session_factory() as s:
                ev_repo = EvidenceRepository(s)
                job_repo = BackgroundJobRepository(s)
                ingestor = SourceEvidenceIngestor(
                    session=s,
                    evidence_repository=ev_repo,
                    job_repository=job_repo,
                )

                gh_conn = SourceConnection(
                    organisation_id=org_a_id,
                    provider="github",
                    display_name="GitHub Enterprise",
                    created_by_user_id=owner.user_id,
                    status="active",
                )
                jira_conn = SourceConnection(
                    organisation_id=org_a_id,
                    provider="jira",
                    display_name="Jira Cloud",
                    created_by_user_id=owner.user_id,
                    status="active",
                )
                s.add_all([gh_conn, jira_conn])
                s.flush()

                public_policy = SourceAccessPolicy(
                    organisation_id=org_a_id,
                    project_id=proj_uuid,
                    source_connection_id=gh_conn.id,
                    provider="github",
                    scope_identifier="repo:public-1",
                    visibility_policy=SourceVisibilityPolicy.PROJECT_MEMBERS_VERIFIED.value,
                    allowed_user_ids=[str(owner.user_id)],
                )
                restricted_gh_policy = SourceAccessPolicy(
                    organisation_id=org_a_id,
                    project_id=proj_uuid,
                    source_connection_id=gh_conn.id,
                    provider="github",
                    scope_identifier="repo:priv-99",
                    visibility_policy=SourceVisibilityPolicy.VERIFIED_SOURCE_ACL.value,
                    allowed_user_ids=[str(owner.user_id), str(contributor.user_id)],
                )
                restricted_jira_policy = SourceAccessPolicy(
                    organisation_id=org_a_id,
                    project_id=proj_uuid,
                    source_connection_id=jira_conn.id,
                    provider="jira",
                    scope_identifier="jira:SEC-1",
                    visibility_policy=SourceVisibilityPolicy.RESTRICTED_FAIL_CLOSED.value,
                    allowed_user_ids=[str(owner.user_id)],
                )
                s.add_all([public_policy, restricted_gh_policy, restricted_jira_policy])
                s.flush()

                t_old = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
                t_new = datetime(2026, 11, 10, 10, 0, tzinfo=UTC)

                # A: Public project-visible GitHub doc
                ev_public = ingestor.upsert_record(
                    organisation_id=org_a_id,
                    project_id=proj_uuid,
                    source_connection_id=gh_conn.id,
                    triggered_by_user_id=owner.user_id,
                    record=NormalizedSourceEvidence(
                        source_type=EvidenceSourceType.GITHUB.value,
                        source_provider="github",
                        category="design_document",
                        source_external_id="repo:pub:doc:1",
                        source_url="https://github.com/acme/pub/blob/main/docs/failover.md",
                        source_author_identity="alice-public",
                        title="Database Failover Runbook",
                        original_filename="docs/failover.md",
                        source_created_at=t_new,
                        source_updated_at=t_new,
                        extraction_method="github_api_v3",
                        acl_scope="project_members",
                        source_access_policy_id=public_policy.id,
                        extracted_text=(
                            "# Database Failover Runbook\n\n"
                            "PostgreSQL failover runbook requires promoting replica and verifying "
                            "ChromaDB hybrid retrieval health after NEX-142 deployment."
                        ),
                        pages=(
                            _page(
                                "# Database Failover Runbook\n\n"
                                "PostgreSQL failover runbook requires promoting replica and "
                                "verifying ChromaDB hybrid retrieval health after NEX-142 "
                                "deployment."
                            ),
                        ),
                        metadata_json={
                            "github_item_type": "documentation",
                            "path": "docs/failover.md",
                            "repository": "acme/pub",
                        },
                    ),
                ).evidence_item

                # B: Restricted private GitHub PR (owner + contributor only, NOT reviewer!)
                ev_priv_gh = ingestor.upsert_record(
                    organisation_id=org_a_id,
                    project_id=proj_uuid,
                    source_connection_id=gh_conn.id,
                    triggered_by_user_id=owner.user_id,
                    record=NormalizedSourceEvidence(
                        source_type=EvidenceSourceType.GITHUB.value,
                        source_provider="github",
                        category="pull_request",
                        source_external_id="repo:priv:pr:88",
                        source_url="https://github.com/acme/priv/pull/88",
                        source_author_identity="bob-secret",
                        title="PR #88: Secret Failover Key Rotation",
                        source_created_at=t_old,
                        source_updated_at=t_old,
                        extraction_method="github_api_v3",
                        acl_scope="source_restricted",
                        source_access_policy_id=restricted_gh_policy.id,
                        extracted_text=(
                            "PR #88 implements automated PostgreSQL failover runbook "
                            "secret rotation."
                        ),
                        pages=(
                            _page(
                                "PR #88 implements automated PostgreSQL failover runbook "
                                "secret rotation.",
                                "pull_request_body",
                            ),
                        ),
                        metadata_json={
                            "github_item_type": "pull_request",
                            "repository": "acme/priv",
                            "number": 88,
                        },
                    ),
                ).evidence_item

                # C: Restricted Jira security issue (owner ONLY!)
                ev_priv_jira = ingestor.upsert_record(
                    organisation_id=org_a_id,
                    project_id=proj_uuid,
                    source_connection_id=jira_conn.id,
                    triggered_by_user_id=owner.user_id,
                    record=NormalizedSourceEvidence(
                        source_type=EvidenceSourceType.JIRA.value,
                        source_provider="jira",
                        category="issue",
                        source_external_id="jira:sec:999",
                        source_url="https://acme.atlassian.net/browse/SEC-999",
                        source_author_identity="carol-security",
                        title="[SEC-999] Restricted Failover Incident",
                        source_created_at=t_new,
                        source_updated_at=t_new,
                        extraction_method="jira_rest_v3",
                        acl_scope="source_restricted",
                        source_access_policy_id=restricted_jira_policy.id,
                        extracted_text=(
                            "Confidential SEC-999 PostgreSQL failover runbook incident remediation."
                        ),
                        pages=(
                            _page(
                                "Confidential SEC-999 PostgreSQL failover runbook "
                                "incident remediation.",
                                "jira_issue_summary",
                            ),
                        ),
                        metadata_json={
                            "jira_item_type": "issue",
                            "jira_issue_key": "SEC-999",
                            "project_key": "SEC",
                        },
                    ),
                ).evidence_item

                # D: Restricted upload (owner/manager only; storage_object_key never leaks!)
                ev_restricted_upload = ev_repo.create_evidence_item(
                    organisation_id=org_a_id,
                    project_id=proj_uuid,
                    uploaded_by_user_id=owner.user_id,
                    source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
                    source_provider="local_upload",
                    category="pdf_document",
                    source_external_id=f"upload:{uuid.uuid4()}",
                    source_url=None,
                    source_author_identity="owner-uploader",
                    title="restricted-board-failover.pdf",
                    original_filename="restricted-board-failover.pdf",
                    mime_type="application/pdf",
                    file_size_bytes=512,
                    content_hash="a" * 64,
                    storage_provider="local_private",
                    storage_object_key="internal/secret/path/should_never_leak.enc",
                    encryption_algorithm="fernet",
                    encryption_key_id="k1",
                    acl_scope="source_restricted",
                    source_created_at=t_new,
                    source_updated_at=t_new,
                    extracted_at=t_new,
                    processing_status=EvidenceProcessingStatus.EXTRACTED.value,
                    extraction_method="pymupdf",
                    page_count=1,
                    metadata_json={},
                )
                ev_repo.replace_extracted_content(
                    evidence_id=ev_restricted_upload.id,
                    extracted_text="Board-confidential PostgreSQL failover SLA runbook addendum.",
                    warnings=(),
                    pages=(_page("Board-confidential PostgreSQL failover SLA runbook addendum."),),
                )
                job_repo.create_job(
                    organisation_id=org_a_id,
                    project_id=proj_uuid,
                    evidence_id=ev_restricted_upload.id,
                    triggered_by_user_id=owner.user_id,
                    job_type="evidence_indexing",
                )

                # E: Synthetic evaluation fixture (excluded by default!)
                ev_synthetic = ev_repo.create_evidence_item(
                    organisation_id=org_a_id,
                    project_id=proj_uuid,
                    uploaded_by_user_id=owner.user_id,
                    source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
                    source_provider="local_upload",
                    category="pdf_document",
                    source_external_id=f"synthetic:{uuid.uuid4()}",
                    source_url=None,
                    source_author_identity="fixture-bot",
                    title="Synthetic Failover Fixture",
                    original_filename="synthetic.pdf",
                    mime_type="application/pdf",
                    file_size_bytes=200,
                    content_hash="b" * 64,
                    storage_provider=None,
                    storage_object_key=None,
                    encryption_algorithm=None,
                    encryption_key_id=None,
                    acl_scope="project_members",
                    source_created_at=t_new,
                    source_updated_at=t_new,
                    extracted_at=t_new,
                    processing_status=EvidenceProcessingStatus.EXTRACTED.value,
                    extraction_method="synthetic",
                    page_count=1,
                    metadata_json={"is_synthetic": True, "synthetic_fixture": True},
                )
                ev_repo.replace_extracted_content(
                    evidence_id=ev_synthetic.id,
                    extracted_text="Synthetic test fixture about PostgreSQL failover runbook.",
                    warnings=(),
                    pages=(_page("Synthetic test fixture about PostgreSQL failover runbook."),),
                )
                job_repo.create_job(
                    organisation_id=org_a_id,
                    project_id=proj_uuid,
                    evidence_id=ev_synthetic.id,
                    triggered_by_user_id=owner.user_id,
                    job_type="evidence_indexing",
                )

                # F: Foreign project item + rogue Chroma vector (must never leak cross-tenant!)
                ev_foreign = ev_repo.create_evidence_item(
                    organisation_id=uuid.UUID(org_b["id"]),
                    project_id=uuid.UUID(other_org_proj["id"]),
                    uploaded_by_user_id=outsider.user_id,
                    source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
                    source_provider="local_upload",
                    category="pdf_document",
                    source_external_id=f"foreign:{uuid.uuid4()}",
                    source_url=None,
                    source_author_identity="foreign-user",
                    title="foreign-failover.pdf",
                    original_filename="foreign-failover.pdf",
                    mime_type="application/pdf",
                    file_size_bytes=120,
                    content_hash="c" * 64,
                    storage_provider=None,
                    storage_object_key=None,
                    encryption_algorithm=None,
                    encryption_key_id=None,
                    acl_scope="project_members",
                    source_created_at=t_new,
                    source_updated_at=t_new,
                    extracted_at=t_new,
                    processing_status=EvidenceProcessingStatus.EXTRACTED.value,
                    extraction_method="pymupdf",
                    page_count=1,
                    metadata_json={},
                )
                ev_repo.replace_extracted_content(
                    evidence_id=ev_foreign.id,
                    extracted_text="Foreign org PostgreSQL failover secret.",
                    warnings=(),
                    pages=(_page("Foreign org PostgreSQL failover secret."),),
                )
                job_repo.create_job(
                    organisation_id=uuid.UUID(org_b["id"]),
                    project_id=uuid.UUID(other_org_proj["id"]),
                    evidence_id=ev_foreign.id,
                    triggered_by_user_id=outsider.user_id,
                    job_type="evidence_indexing",
                )
                s.commit()

            assert indexing_worker.drain_pending_jobs(max_jobs=20) == 6

            # 1. Cross-tenant outsider & non-project org_member isolation (404/403)
            search_body = {"query": "PostgreSQL failover runbook", "mode": "hybrid"}
            for outsider_url in (
                f"/api/v1/projects/{proj_id}/search",
                f"/api/v1/projects/{proj_id}/indexing/status",
                f"/api/v1/projects/{proj_id}/indexing/health",
                f"/api/v1/projects/{proj_id}/indexing/reindex",
            ):
                if outsider_url.endswith(("/search", "/reindex")):
                    r_out = client.post(outsider_url, headers=outsider.headers, json=search_body)
                else:
                    r_out = client.get(outsider_url, headers=outsider.headers)
                assert r_out.status_code == 404

            # Private project hides existence from org_member (404); org-visible denies (403)
            r_priv_om = client.post(
                f"/api/v1/projects/{proj_id}/search",
                headers=org_non_member.headers,
                json=search_body,
            )
            assert r_priv_om.status_code == 404
            r_org_om = client.post(
                f"/api/v1/projects/{org_vis_proj['id']}/search",
                headers=org_non_member.headers,
                json=search_body,
            )
            assert r_org_om.status_code == 403

            # 2. Owner sees A, B, C, D (4 real items), excludes E & F, zero leaked keys
            for mode in ("keyword", "semantic", "hybrid"):
                r_own = client.post(
                    f"/api/v1/projects/{proj_id}/search",
                    headers=owner.headers,
                    json={"query": "PostgreSQL failover runbook", "mode": mode, "top_k": 10},
                )
                assert r_own.status_code == 200
                body = r_own.json()
                returned_ev_ids = {hit["evidence_id"] for hit in body["results"]}
                assert returned_ev_ids == {
                    str(ev_public.id),
                    str(ev_priv_gh.id),
                    str(ev_priv_jira.id),
                    str(ev_restricted_upload.id),
                }
                assert str(ev_synthetic.id) not in returned_ev_ids
                assert str(ev_foreign.id) not in returned_ev_ids
                assert "should_never_leak" not in r_own.text
                # Verify citation metadata integrity
                first_cit = body["results"][0]["citation"]
                assert first_cit["chunk_content_hash"]
                assert first_cit["content_hash"]
                assert first_cit["is_synthetic"] is False

            # Explicit include_synthetic=True reveals E cleanly with badge flag
            r_syn = client.post(
                f"/api/v1/projects/{proj_id}/search",
                headers=owner.headers,
                json={
                    "query": "PostgreSQL failover runbook",
                    "mode": "hybrid",
                    "filters": {"include_synthetic": True},
                },
            )
            assert r_syn.status_code == 200
            assert str(ev_synthetic.id) in {h["evidence_id"] for h in r_syn.json()["results"]}
            syn_hit = next(
                h for h in r_syn.json()["results"] if h["evidence_id"] == str(ev_synthetic.id)
            )
            assert syn_hit["citation"]["is_synthetic"] is True

            # 3. Reviewer lacks priv repo, Jira SEC-999 & restricted PDF -> only sees A!
            for mode in ("keyword", "semantic", "hybrid"):
                r_rev = client.post(
                    f"/api/v1/projects/{proj_id}/search",
                    headers=reviewer.headers,
                    json={"query": "PostgreSQL failover runbook", "mode": mode, "top_k": 10},
                )
                assert r_rev.status_code == 200
                rev_json = r_rev.json()
                assert rev_json["total_returned"] == 1
                assert rev_json["results"][0]["evidence_id"] == str(ev_public.id)

            # 4. Stale Chroma simulation: even if Chroma ignores metadata filters & returns
            # restricted/cross-project vectors, PG post-revalidation strips all of them!
            fake_chroma.bypass_where_to_simulate_stale_chroma = True
            fake_chroma.records["rogue-vector"] = (
                _text_to_unit_vector("PostgreSQL failover runbook", dims=64),
                {
                    "organisation_id": str(org_a_id),
                    "project_id": str(proj_uuid),
                    "evidence_id": str(uuid.uuid4()),
                    "chunk_id": str(uuid.uuid4()),
                    "permission_scope_key": "project_members",
                    "is_synthetic": False,
                },
            )
            for mode in ("semantic", "hybrid"):
                r_stale = client.post(
                    f"/api/v1/projects/{proj_id}/search",
                    headers=reviewer.headers,
                    json={"query": "PostgreSQL failover runbook", "mode": mode, "top_k": 10},
                )
                assert r_stale.status_code == 200
                stale_json = r_stale.json()
                assert stale_json["total_returned"] == 1
                assert stale_json["results"][0]["evidence_id"] == str(ev_public.id)
            fake_chroma.bypass_where_to_simulate_stale_chroma = False
            fake_chroma.records.pop("rogue-vector", None)

            # 5. Contributor sees A and B (permitted in restricted_gh_policy), never C or D!
            # Revoke contributor's GitHub policy in PG (no Chroma reindex) -> blocked!
            r_con_before = client.post(
                f"/api/v1/projects/{proj_id}/search",
                headers=contributor.headers,
                json={"query": "PostgreSQL failover runbook", "mode": "hybrid"},
            )
            assert {h["evidence_id"] for h in r_con_before.json()["results"]} == {
                str(ev_public.id),
                str(ev_priv_gh.id),
            }

            with ctx.session_factory() as s:
                pol = s.get(SourceAccessPolicy, restricted_gh_policy.id)
                assert pol is not None
                pol.sync_permission_status = SourcePermissionVerificationStatus.REVOKED.value
                s.commit()

            for mode in ("keyword", "semantic", "hybrid"):
                r_con_after = client.post(
                    f"/api/v1/projects/{proj_id}/search",
                    headers=contributor.headers,
                    json={"query": "PostgreSQL failover runbook", "mode": mode},
                )
                assert {h["evidence_id"] for h in r_con_after.json()["results"]} == {
                    str(ev_public.id)
                }

            # 6. Chunk detail endpoint enforces source ACL and audits denials
            owner_hits = client.post(
                f"/api/v1/projects/{proj_id}/search",
                headers=owner.headers,
                json={"query": "SEC-999", "mode": "keyword"},
            ).json()["results"]
            sec_chunk_id = owner_hits[0]["chunk_id"]
            pub_chunk_id = client.post(
                f"/api/v1/projects/{proj_id}/search",
                headers=reviewer.headers,
                json={"query": "NEX-142", "mode": "keyword"},
            ).json()["results"][0]["chunk_id"]

            assert (
                client.get(
                    f"/api/v1/projects/{proj_id}/chunks/{pub_chunk_id}",
                    headers=reviewer.headers,
                ).status_code
                == 200
            )
            denied_chunk = client.get(
                f"/api/v1/projects/{proj_id}/chunks/{sec_chunk_id}",
                headers=reviewer.headers,
            )
            assert denied_chunk.status_code == 403
            assert denied_chunk.json()["error"]["code"] == "SOURCE_ACCESS_DENIED"

            # 7. Filters work cleanly across source_types, categories, chunk_types, author, dates
            r_filtered = client.post(
                f"/api/v1/projects/{proj_id}/search",
                headers=owner.headers,
                json={
                    "query": "failover",
                    "mode": "hybrid",
                    "filters": {
                        "source_types": ["jira"],
                        "chunk_types": [EvidenceChunkType.ISSUE_BODY.value],
                        "author": "carol-security",
                        "date_from": (t_new - timedelta(days=1)).isoformat(),
                    },
                },
            )
            assert r_filtered.status_code == 200
            assert [h["evidence_id"] for h in r_filtered.json()["results"]] == [
                str(ev_priv_jira.id)
            ]

            # 8. Reindex permission enforcement: reviewer denied (403), contributor permitted (202)
            r_rev_reidx = client.post(
                f"/api/v1/projects/{proj_id}/indexing/reindex",
                headers=reviewer.headers,
                json={"target": "full"},
            )
            assert r_rev_reidx.status_code == 403
            r_con_reidx = client.post(
                f"/api/v1/projects/{proj_id}/indexing/reindex",
                headers=contributor.headers,
                json={"target": "fts_only"},
            )
            assert r_con_reidx.status_code == 202

            # 9. Degraded retrieval semantics: Chroma outage degrades `hybrid` -> `keyword`,
            # while explicit `semantic` mode fails closed with HTTP 503!
            fake_chroma.fail_query = True
            r_deg_hybrid = client.post(
                f"/api/v1/projects/{proj_id}/search",
                headers=owner.headers,
                json={"query": "NEX-142 failover", "mode": "hybrid"},
            )
            assert r_deg_hybrid.status_code == 200
            deg_json = r_deg_hybrid.json()
            assert deg_json["mode_requested"] == "hybrid"
            assert deg_json["mode_executed"] == "keyword"
            assert deg_json["degraded"] is True
            assert deg_json["degraded_reason"] == "CHROMA_UNAVAILABLE"
            assert deg_json["warnings"]
            assert deg_json["total_returned"] >= 1

            r_deg_sem = client.post(
                f"/api/v1/projects/{proj_id}/search",
                headers=owner.headers,
                json={"query": "NEX-142 failover", "mode": "semantic"},
            )
            assert r_deg_sem.status_code == 503
            assert r_deg_sem.json()["error"]["code"] == "CHROMA_UNAVAILABLE"

            # Health endpoint truthfully reports Chroma unreachability while PG FTS remains True
            fake_chroma.fail_inspect = True
            health_deg = client.get(
                f"/api/v1/projects/{proj_id}/indexing/health",
                headers=owner.headers,
            )
            assert health_deg.status_code == 200
            assert health_deg.json()["postgresql_fts_ready"] is True
            assert health_deg.json()["chroma_reachable"] is False
            assert health_deg.json()["collection_compatible"] is False

            with ctx.session_factory() as s:
                ev_types = {
                    row.event_type
                    for row in s.execute(
                        select(AuditLog).where(AuditLog.project_id == proj_uuid)
                    ).scalars()
                }
                assert "evidence.search_executed" in ev_types
                assert "evidence.source_acl_denied" in ev_types
                assert "evidence.reindex_denied" in ev_types
                assert "evidence.reindex_queued" in ev_types
