"""Integration tests for Phase 2.5 async indexing worker, outages, reindex & cleanup."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import docx
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import utc_now
from app.models.audit import AuditLog
from app.models.enums import (
    BackgroundJobStatus,
    BackgroundJobType,
    EvidenceChunkType,
    EvidenceIndexingStatus,
    EvidenceProcessingStatus,
    EvidenceSourceType,
    SourceVisibilityPolicy,
)
from app.models.evidence import EvidenceChunk, EvidenceItem
from app.models.integration import SourceAccessPolicy, SourceConnection
from app.models.job import BackgroundJob
from app.repositories.evidence import EvidenceRepository
from app.repositories.job import BackgroundJobRepository
from app.services.chunking import ChunkingService
from app.services.document_extraction import DocumentExtractionService, ExtractedPageData
from app.services.indexing_worker import IndexingWorkerService
from app.services.ingestion_worker import IngestionWorkerService
from app.services.integrations.evidence_ingestor import (
    NormalizedSourceEvidence,
    SourceEvidenceIngestor,
)
from app.services.integrations.sync_worker import SourceSyncWorkerService
from app.services.ocr import OCRPageRequest, OCRPageResult
from app.services.storage import LocalPrivateStorageBackend
from app.services.token_encryption import LocalTokenEncryptionService
from app.worker import CompositeWorkerService
from tests.conftest import isolated_auth_app, register_and_login_user
from tests.helpers_retrieval import InMemoryEmbeddingService, InMemoryVectorStoreClient


class _NoopOCR:
    model_name = "noop-ocr"

    def extract_page_text(self, request: OCRPageRequest) -> OCRPageResult:
        return OCRPageResult(
            page_number=request.page_number,
            text="",
            model_name=self.model_name,
            truncated=False,
            done_reason="stop",
            prompt_eval_count=0,
            eval_count=0,
            duration_ms=1,
        )


def _docx_bytes() -> bytes:
    doc = docx.Document()
    doc.add_heading("Platform Architecture", level=1)
    doc.add_paragraph(
        "PostgreSQL holds canonical evidence records, extracted text, and full-text search vectors."
    )
    doc.add_heading("Secondary Vector Storage", level=2)
    doc.add_paragraph(
        "ChromaDB serves similarity retrieval using nomic-embed-text and can be rebuilt from PG."
    )
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_upload_auto_indexing_outage_partial_recovery_and_delete_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    upload_dir = tmp_path / "idx_worker_uploads"
    fake_embed = InMemoryEmbeddingService(dims=64)
    fake_chroma = InMemoryVectorStoreClient(expected_dimensions=64)

    with isolated_auth_app(
        monkeypatch,
        upload_storage_path=upload_dir,
        embedding_expected_dimensions=64,
        worker_max_attempts=2,
        worker_retry_base_seconds=5,
        chunk_target_chars=260,
        chunk_max_chars=400,
        chunk_overlap_chars=40,
        chunk_min_chars=40,
    ) as ctx:
        ctx.app.state.embedding_service = fake_embed
        ctx.app.state.vector_store_client = fake_chroma

        storage = LocalPrivateStorageBackend(
            root_path=upload_dir,
            file_encryption_key=ctx.settings.security.file_encryption_key.get_secret_value(),
        )
        ingestion_worker = IngestionWorkerService(
            session_factory=ctx.session_factory,
            storage_backend=storage,
            extraction_service=DocumentExtractionService(
                ocr_service=_NoopOCR(),
                ingestion_settings=ctx.settings.ingestion,
            ),
            ingestion_settings=ctx.settings.ingestion,
        )
        sync_worker = SourceSyncWorkerService(
            session_factory=ctx.session_factory,
            settings=ctx.settings,
            token_encryption=LocalTokenEncryptionService(
                token_encryption_key=ctx.settings.security.token_encryption_key.get_secret_value()
            ),
            http_transport=httpx.MockTransport(lambda _r: httpx.Response(200, json={})),
        )
        indexing_worker = IndexingWorkerService(
            session_factory=ctx.session_factory,
            chunking_service=ChunkingService(settings=ctx.settings.chunking),
            embedding_service=fake_embed,
            vector_store=fake_chroma,
            ingestion_settings=ctx.settings.ingestion,
        )
        composite = CompositeWorkerService(
            ingestion_worker=ingestion_worker,
            sync_worker=sync_worker,
            indexing_worker=indexing_worker,
        )

        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client,
                email="idx-owner@example.com",
                full_name="Index Owner",
            )
            org = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "Index Org"},
            ).json()
            proj = client.post(
                f"/api/v1/organisations/{org['id']}/projects",
                headers=owner.headers,
                json={"name": "Index Project", "status": "active", "visibility": "private"},
            ).json()
            proj_id = proj["id"]

            # 1. Simulate ChromaDB outage BEFORE indexing -> extraction + chunking + PG FTS succeed,
            # while evidence becomes partially_indexed and vector retries schedule cleanly!
            fake_chroma.fail_upsert = True
            up_resp = client.post(
                f"/api/v1/projects/{proj_id}/evidence/documents",
                headers=owner.headers,
                files={
                    "file": (
                        "architecture.docx",
                        _docx_bytes(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                data={"title": "Platform Handover Architecture"},
            )
            assert up_resp.status_code == 201
            ev_id = up_resp.json()["evidence"]["id"]
            assert up_resp.json()["evidence"]["indexing_status"] == "not_indexed"
            assert fake_embed.embed_calls == []  # No in-request synchronous embedding!

            # Step A: extraction queues evidence_indexing; Step B: indexing hits outage
            processed = composite.drain_pending_jobs(max_jobs=10)
            assert processed == 2

            detail_partial = client.get(f"/api/v1/evidence/{ev_id}", headers=owner.headers)
            assert detail_partial.status_code == 200
            d_json = detail_partial.json()
            assert d_json["processing_status"] == EvidenceProcessingStatus.EXTRACTED.value
            assert d_json["indexing_status"] == EvidenceIndexingStatus.PARTIALLY_INDEXED.value
            assert d_json["chunk_count"] >= 2
            assert d_json["index_error_code"] == "CHROMA_UNAVAILABLE"
            assert d_json["latest_job"]["job_type"] == BackgroundJobType.DOCUMENT_INGESTION.value
            assert (
                d_json["latest_indexing_job"]["job_type"]
                == BackgroundJobType.EVIDENCE_INDEXING.value
            )
            assert d_json["latest_indexing_job"]["status"] == BackgroundJobStatus.QUEUED.value

            # PG keyword search STILL works immediately despite Chroma upsert outage!
            kw_search = client.post(
                f"/api/v1/projects/{proj_id}/search",
                headers=owner.headers,
                json={"query": "canonical evidence PostgreSQL", "mode": "keyword"},
            )
            assert kw_search.status_code == 200
            assert kw_search.json()["mode_executed"] == "keyword"
            assert kw_search.json()["degraded"] is False
            assert kw_search.json()["total_returned"] >= 1

            # And when Chroma query is also unreachable, hybrid degrades cleanly to keyword!
            fake_chroma.fail_query = True
            deg_hybrid = client.post(
                f"/api/v1/projects/{proj_id}/search",
                headers=owner.headers,
                json={"query": "canonical evidence PostgreSQL", "mode": "hybrid"},
            )
            assert deg_hybrid.status_code == 200
            assert deg_hybrid.json()["mode_executed"] == "keyword"
            assert deg_hybrid.json()["degraded"] is True
            assert deg_hybrid.json()["total_returned"] >= 1
            fake_chroma.fail_query = False

            status_partial = client.get(
                f"/api/v1/projects/{proj_id}/indexing/status",
                headers=owner.headers,
            ).json()
            assert status_partial["fts_ready_items"] == 1
            assert status_partial["vector_synced_items"] == 0
            assert status_partial["pending_vector_chunks"] >= 2

            # Exhaust remaining attempt while Chroma still down
            with ctx.session_factory() as s:
                idx_job = s.execute(
                    select(BackgroundJob).where(
                        BackgroundJob.job_type == BackgroundJobType.EVIDENCE_INDEXING.value
                    )
                ).scalar_one()
                idx_job.next_retry_at = utc_now() - timedelta(seconds=1)
                s.commit()

            assert composite.drain_pending_jobs(max_jobs=5) == 1
            detail_failed_vec = client.get(
                f"/api/v1/evidence/{ev_id}", headers=owner.headers
            ).json()
            assert (
                detail_failed_vec["latest_indexing_job"]["status"]
                == BackgroundJobStatus.FAILED.value
            )
            assert (
                detail_failed_vec["indexing_status"]
                == EvidenceIndexingStatus.PARTIALLY_INDEXED.value
            )

            # 2. Recover ChromaDB and execute targeted `vectors_only` reindex without re-chunking!
            fake_chroma.fail_upsert = False
            embed_calls_before = len(fake_embed.embed_calls)
            reindex_resp = client.post(
                f"/api/v1/projects/{proj_id}/indexing/reindex",
                headers=owner.headers,
                json={"target": "vectors_only", "evidence_ids": [ev_id]},
            )
            assert reindex_resp.status_code == 202
            reindex_job_id = reindex_resp.json()["job"]["id"]
            assert reindex_resp.json()["already_running"] is False

            # Duplicate reindex trigger while active returns idempotent `already_running=True`
            dup_reindex = client.post(
                f"/api/v1/projects/{proj_id}/indexing/reindex",
                headers=owner.headers,
                json={"target": "vectors_only", "evidence_ids": [ev_id]},
            )
            assert dup_reindex.status_code == 202
            assert dup_reindex.json()["already_running"] is True
            assert dup_reindex.json()["job"]["id"] == reindex_job_id

            assert composite.drain_pending_jobs(max_jobs=5) == 1
            assert len(fake_embed.embed_calls) > embed_calls_before

            job_info = client.get(
                f"/api/v1/projects/{proj_id}/indexing/jobs/{reindex_job_id}",
                headers=owner.headers,
            ).json()
            assert job_info["status"] == BackgroundJobStatus.SUCCEEDED.value
            assert job_info["result_json"]["indexed_items"] == 1

            status_ok = client.get(
                f"/api/v1/projects/{proj_id}/indexing/status",
                headers=owner.headers,
            ).json()
            assert status_ok["vector_synced_items"] == 1
            assert status_ok["pending_vector_chunks"] == 0
            assert status_ok["indexed_chunks"] == status_ok["total_chunks"] >= 2

            health_ok = client.get(
                f"/api/v1/projects/{proj_id}/indexing/health",
                headers=owner.headers,
            ).json()
            assert health_ok["postgresql_fts_ready"] is True
            assert health_ok["chroma_reachable"] is True
            assert health_ok["chroma_collection_exists"] is True
            assert health_ok["collection_compatible"] is True
            assert health_ok["chroma_vector_count"] == status_ok["total_chunks"]
            # Check strict allowlist in Chroma: never store secrets or internal paths
            for _vec, meta in fake_chroma.records.values():
                assert "storage_object_key" not in meta
                assert "chunk_text" not in meta
                assert "access_token" not in meta

            # 3. Soft-delete evidence -> immediate PG chunk wipe + async Chroma cleanup job
            del_resp = client.delete(f"/api/v1/evidence/{ev_id}", headers=owner.headers)
            assert del_resp.status_code == 204

            with ctx.session_factory() as s:
                remaining_chunks = s.execute(
                    select(EvidenceChunk).where(EvidenceChunk.project_id == uuid.UUID(proj_id))
                ).scalars().all()
                assert remaining_chunks == []

            # Chroma still holds vectors until cleanup worker executes
            assert fake_chroma.count_records() >= 2
            assert composite.drain_pending_jobs(max_jobs=5) == 1
            assert fake_chroma.count_records() == 0

            with ctx.session_factory() as s:
                audit_events = {
                    row.event_type
                    for row in s.execute(
                        select(AuditLog).where(AuditLog.project_id == uuid.UUID(proj_id))
                    ).scalars()
                }
                assert "evidence.indexing_partially_indexed" in audit_events
                assert "evidence.reindex_completed" in audit_events
                assert "evidence.index_cleanup_completed" in audit_events


def test_source_upsert_rechunk_prunes_obsolete_vectors_and_skips_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_embed = InMemoryEmbeddingService(dims=64)
    fake_chroma = InMemoryVectorStoreClient(expected_dimensions=64)

    with isolated_auth_app(
        monkeypatch,
        upload_storage_path=tmp_path / "upsert_uploads",
        embedding_expected_dimensions=64,
        chunk_target_chars=200,
        chunk_max_chars=300,
        chunk_overlap_chars=0,
        chunk_min_chars=40,
    ) as ctx:
        indexing_worker = IndexingWorkerService(
            session_factory=ctx.session_factory,
            chunking_service=ChunkingService(settings=ctx.settings.chunking),
            embedding_service=fake_embed,
            vector_store=fake_chroma,
            ingestion_settings=ctx.settings.ingestion,
        )

        with TestClient(ctx.app) as client:
            owner = register_and_login_user(
                client,
                email="upsert-owner@example.com",
                full_name="Upsert Owner",
            )
            org = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "Upsert Org"},
            ).json()
            proj = client.post(
                f"/api/v1/organisations/{org['id']}/projects",
                headers=owner.headers,
                json={"name": "Upsert Project", "status": "active", "visibility": "private"},
            ).json()
            org_id = uuid.UUID(org["id"])
            proj_id = uuid.UUID(proj["id"])

            with ctx.session_factory() as s:
                conn = SourceConnection(
                    organisation_id=org_id,
                    provider="github",
                    display_name="GH Conn",
                    created_by_user_id=owner.user_id,
                    status="active",
                )
                s.add(conn)
                s.flush()
                policy = SourceAccessPolicy(
                    organisation_id=org_id,
                    project_id=proj_id,
                    source_connection_id=conn.id,
                    provider="github",
                    scope_identifier="repo:123",
                    visibility_policy=SourceVisibilityPolicy.VERIFIED_SOURCE_ACL.value,
                    allowed_user_ids=[str(owner.user_id)],
                )
                s.add(policy)
                s.commit()
                conn_id = conn.id
                policy_id = policy.id

            def _make_record(body_text: str) -> NormalizedSourceEvidence:
                return NormalizedSourceEvidence(
                    source_type=EvidenceSourceType.GITHUB.value,
                    source_provider="github",
                    category="pull_request",
                    source_external_id="repo:123:pr:7",
                    source_url="https://github.com/acme/repo/pull/7",
                    source_author_identity="alice",
                    title="PR #7: Retrieval rollout",
                    source_created_at=datetime(2026, 11, 11, 10, 0, tzinfo=UTC),
                    source_updated_at=datetime(2026, 11, 11, 10, 0, tzinfo=UTC),
                    extraction_method="github_api_v3",
                    acl_scope="source_restricted",
                    source_access_policy_id=policy_id,
                    extracted_text=body_text,
                    pages=(
                        ExtractedPageData(
                            page_number=1,
                            extraction_outcome="digital_text",
                            ocr_applied=False,
                            ocr_truncated=False,
                            text_content=body_text,
                            structured_metadata={"section": "pull_request_body"},
                        ),
                    ),
                    metadata_json={
                        "github_item_type": "pull_request",
                        "repository": "acme/repo",
                        "number": 7,
                    },
                )

            # 1. Create long PR body producing 3+ chunks
            long_text = (
                "# Summary\n"
                + ("PostgreSQL full-text indexing covers NEX-142 reliably.\n\n" * 12)
            )
            with ctx.session_factory() as s:
                ingestor = SourceEvidenceIngestor(
                    session=s,
                    evidence_repository=EvidenceRepository(s),
                    job_repository=BackgroundJobRepository(s),
                )
                out1 = ingestor.upsert_record(
                    organisation_id=org_id,
                    project_id=proj_id,
                    source_connection_id=conn_id,
                    triggered_by_user_id=owner.user_id,
                    record=_make_record(long_text),
                )
                assert out1.action == "created"
                ev_id = out1.evidence_item.id
                s.commit()

            assert indexing_worker.drain_pending_jobs(max_jobs=5) == 1
            first_vec_count = fake_chroma.count_records()
            assert first_vec_count >= 3

            # 2. Identical record re-upsert -> unchanged, ZERO new indexing jobs queued!
            with ctx.session_factory() as s:
                ingestor = SourceEvidenceIngestor(
                    session=s,
                    evidence_repository=EvidenceRepository(s),
                    job_repository=BackgroundJobRepository(s),
                )
                out_same = ingestor.upsert_record(
                    organisation_id=org_id,
                    project_id=proj_id,
                    source_connection_id=conn_id,
                    triggered_by_user_id=owner.user_id,
                    record=_make_record(long_text),
                )
                assert out_same.action == "unchanged"
                queued_cnt = s.execute(
                    select(BackgroundJob).where(
                        BackgroundJob.evidence_id == ev_id,
                        BackgroundJob.status == BackgroundJobStatus.QUEUED.value,
                    )
                ).scalars().all()
                assert queued_cnt == []

            # 3. Short 1-chunk body -> worker re-chunks and deletes stale `:1`, `:2` vectors!
            short_text = "Short single-chunk update closing NEX-142."
            with ctx.session_factory() as s:
                ingestor = SourceEvidenceIngestor(
                    session=s,
                    evidence_repository=EvidenceRepository(s),
                    job_repository=BackgroundJobRepository(s),
                )
                out_upd = ingestor.upsert_record(
                    organisation_id=org_id,
                    project_id=proj_id,
                    source_connection_id=conn_id,
                    triggered_by_user_id=owner.user_id,
                    record=_make_record(short_text),
                )
                assert out_upd.action == "updated"
                s.commit()

            assert indexing_worker.drain_pending_jobs(max_jobs=5) == 1
            assert fake_chroma.count_records() == 1
            assert f"{ev_id}:0" in fake_chroma.records
            assert f"{ev_id}:1" not in fake_chroma.records

            with ctx.session_factory() as s:
                ev = s.get(EvidenceItem, ev_id)
                assert ev is not None
                assert ev.chunk_count == 1
                chunks = s.execute(
                    select(EvidenceChunk).where(EvidenceChunk.evidence_id == ev_id)
                ).scalars().all()
                assert len(chunks) == 1
                assert chunks[0].chunk_type == EvidenceChunkType.PR_BODY.value
                audit_events = {
                    row.event_type
                    for row in s.execute(
                        select(AuditLog).where(AuditLog.project_id == proj_id)
                    ).scalars()
                }
                assert "evidence.indexing_completed" in audit_events
