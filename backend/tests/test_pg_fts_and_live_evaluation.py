"""Live PostgreSQL FTS + Ollama `nomic-embed-text` + ChromaDB v2 retrieval & evaluation suite."""

from __future__ import annotations

import logging
import math
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app import main as app_main
from app.core.config import clear_settings_cache, get_settings
from app.models.enums import (
    BackgroundJobType,
    EvidenceProcessingStatus,
    EvidenceSourceType,
    SourceVisibilityPolicy,
)
from app.models.integration import SourceAccessPolicy, SourceConnection
from app.repositories.evidence import EvidenceRepository
from app.repositories.job import BackgroundJobRepository
from app.services.chunking import ChunkingService
from app.services.document_extraction import ExtractedPageData
from app.services.embedding import OllamaEmbeddingService
from app.services.indexing_worker import IndexingWorkerService
from app.services.integrations.evidence_ingestor import (
    NormalizedSourceEvidence,
    SourceEvidenceIngestor,
)
from app.services.vector_store import ChromaV2HttpVectorStore
from tests.conftest import (
    build_test_settings,
    invite_and_accept_member,
    register_and_login_user,
)

logger = logging.getLogger("tests.pg_fts_live_eval")
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


def _service_reachable(url: str) -> bool:
    try:
        resp = httpx.get(url, timeout=3.0)
        return resp.status_code < 500
    except httpx.HTTPError:
        return False


def _ollama_has_model(base_url: str, model_name: str) -> bool:
    try:
        resp = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=3.0)
        if resp.status_code != 200:
            return False
        models = resp.json().get("models") or []
        return any(str(m.get("name", "")).startswith(model_name) for m in models)
    except (httpx.HTTPError, ValueError):
        return False


def _seed_project_member(
    client: TestClient,
    *,
    owner_headers: dict[str, str],
    org_id: str,
    proj_id: str,
    user: Any,
    role_name: str,
) -> None:
    invite_and_accept_member(
        client,
        organisation_id=org_id,
        inviter_headers=owner_headers,
        invitee=user,
        role_name="org_member",
    )
    resp = client.post(
        f"/api/v1/projects/{proj_id}/members",
        headers=owner_headers,
        json={"user_id": str(user.user_id), "role_name": role_name},
    )
    assert resp.status_code in (200, 201), resp.text


def _page(text_content: str, *, page_number: int = 1, section: str = "body") -> ExtractedPageData:
    return ExtractedPageData(
        page_number=page_number,
        extraction_outcome="digital_text",
        ocr_applied=False,
        ocr_truncated=False,
        text_content=text_content,
        structured_metadata={"section": section},
    )


def _evaluate_query_set(
    *,
    client: TestClient,
    proj_id: str,
    headers: dict[str, str],
    mode: str,
    queries: list[tuple[str, set[str]]],
) -> dict[str, float]:
    precisions_at_3: list[float] = []
    recalls_at_5: list[float] = []
    reciprocal_ranks: list[float] = []
    latencies_ms: list[int] = []

    for query_text, expected_ids in queries:
        resp = client.post(
            f"/api/v1/projects/{proj_id}/search",
            headers=headers,
            json={
                "query": query_text,
                "mode": mode,
                "top_k": 5,
                "filters": {"include_synthetic": True},
            },
        )
        assert resp.status_code == 200, f"Search failed ({mode}, {query_text}): {resp.text}"
        data = resp.json()
        assert data["degraded"] is False
        latencies_ms.append(int(data["latency_ms"]))

        # Deduplicate ranked hits at the evidence-item level to measure item retrieval quality
        ranked_ev_ids: list[str] = []
        for hit in data["results"]:
            ev_id = str(hit["evidence_id"])
            if ev_id not in ranked_ev_ids:
                ranked_ev_ids.append(ev_id)

        top3 = ranked_ev_ids[:3]
        denom_p3 = min(3, len(top3)) if top3 else 3
        p3 = sum(1 for eid in top3 if eid in expected_ids) / float(denom_p3) if top3 else 0.0
        r5 = sum(1 for eid in ranked_ev_ids[:5] if eid in expected_ids) / float(len(expected_ids))
        rr = 0.0
        for rank_idx, eid in enumerate(ranked_ev_ids, start=1):
            if eid in expected_ids:
                rr = 1.0 / float(rank_idx)
                break

        precisions_at_3.append(p3)
        recalls_at_5.append(r5)
        reciprocal_ranks.append(rr)

    return {
        "precision_at_3": round(sum(precisions_at_3) / len(queries), 4),
        "recall_at_5": round(sum(recalls_at_5) / len(queries), 4),
        "mrr": round(sum(reciprocal_ranks) / len(queries), 4),
        "mean_latency_ms": round(sum(latencies_ms) / len(queries), 2),
    }


@pytest.mark.skipif(
    not _ROOT_ENV.exists(),
    reason="Root .env unavailable for live PostgreSQL/Ollama/ChromaDB integration test",
)
def test_live_pg_fts_ollama_chroma_hybrid_retrieval_and_synthetic_evaluation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    clear_settings_cache()
    live_cfg = get_settings()

    if not _service_reachable(f"{live_cfg.chroma.base_url}/api/v2/heartbeat"):
        pytest.skip("ChromaDB v2 HTTP service is not reachable on configured host/port.")
    if not _ollama_has_model(live_cfg.ollama.base_url, live_cfg.ollama.embedding_model):
        pytest.skip(
            f"Ollama embedding model '{live_cfg.ollama.embedding_model}' is unavailable."
        )

    password = live_cfg.database.password.get_secret_value()
    temp_db = f"ipkrh_fts_eval_{uuid.uuid4().hex[:8]}"
    temp_collection = f"ipkrh_eval_{uuid.uuid4().hex[:8]}"
    admin_dsn = (
        f"postgresql://{live_cfg.database.user}:{password}@127.0.0.1:{live_cfg.database.port}/postgres"
    )
    temp_url = (
        f"postgresql+psycopg://{live_cfg.database.user}:{password}"
        f"@127.0.0.1:{live_cfg.database.port}/{temp_db}?sslmode=disable"
    )

    try:
        with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
            admin_conn.execute(f'CREATE DATABASE "{temp_db}"')
    except psycopg.OperationalError as exc:
        pytest.skip(f"PostgreSQL server unreachable for live FTS evaluation: {exc}")

    real_chroma = ChromaV2HttpVectorStore(
        base_url=live_cfg.chroma.base_url,
        collection_name_override=temp_collection,
        embedding_model=live_cfg.ollama.embedding_model,
        index_version="v1",
        expected_dimensions=768,
        auth_token=(
            live_cfg.chroma.auth_token.get_secret_value()
            if live_cfg.chroma.auth_token is not None
            else None
        ),
        request_timeout_seconds=15.0,
    )
    real_embed = OllamaEmbeddingService(
        base_url=live_cfg.ollama.base_url,
        model=live_cfg.ollama.embedding_model,
        expected_dimensions=768,
        timeout_seconds=30.0,
        batch_size=8,
    )

    engine = None
    try:
        alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", temp_url)
        command.upgrade(cfg, "head")

        engine = create_engine(temp_url, connect_args={"connect_timeout": 5})
        session_factory: sessionmaker[Session] = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )

        settings = build_test_settings(
            database_url=temp_url,
            upload_storage_path=tmp_path / "live_eval_uploads",
            chroma_host=live_cfg.chroma.host,
            chroma_port=live_cfg.chroma.port,
            ollama_base_url=live_cfg.ollama.base_url,
            ollama_embedding_model=live_cfg.ollama.embedding_model,
            embedding_expected_dimensions=768,
        )
        monkeypatch.setattr(app_main, "create_db_engine", lambda _s: engine)
        monkeypatch.setattr(app_main, "create_session_factory", lambda _e: session_factory)
        monkeypatch.setattr(app_main, "verify_database_connection", lambda _e: 1.0)

        app = app_main.create_app(settings)
        app.state.embedding_service = real_embed
        app.state.vector_store_client = real_chroma

        indexing_worker = IndexingWorkerService(
            session_factory=session_factory,
            chunking_service=ChunkingService(settings=settings.chunking),
            embedding_service=real_embed,
            vector_store=real_chroma,
            ingestion_settings=settings.ingestion,
        )

        with TestClient(app) as client:
            owner = register_and_login_user(
                client, email="pg-eval-owner@example.com", full_name="PG Eval Owner"
            )
            reviewer = register_and_login_user(
                client, email="pg-eval-rev@example.com", full_name="PG Eval Reviewer"
            )
            org = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "PG Live Eval Org"},
            ).json()
            proj = client.post(
                f"/api/v1/organisations/{org['id']}/projects",
                headers=owner.headers,
                json={"name": "PG Live Eval Project", "status": "active", "visibility": "private"},
            ).json()
            org_id = uuid.UUID(org["id"])
            proj_id = uuid.UUID(proj["id"])

            _seed_project_member(
                client,
                owner_headers=owner.headers,
                org_id=org["id"],
                proj_id=proj["id"],
                user=reviewer,
                role_name="reviewer",
            )

            t_now = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
            with session_factory() as s:
                ev_repo = EvidenceRepository(s)
                job_repo = BackgroundJobRepository(s)
                ingestor = SourceEvidenceIngestor(
                    session=s,
                    evidence_repository=ev_repo,
                    job_repository=job_repo,
                )

                gh_conn = SourceConnection(
                    organisation_id=org_id,
                    provider="github",
                    display_name="Synthetic Fixture GitHub",
                    created_by_user_id=owner.user_id,
                    status="active",
                    metadata_json={"is_synthetic": True},
                )
                jira_conn = SourceConnection(
                    organisation_id=org_id,
                    provider="jira",
                    display_name="Synthetic Fixture Jira",
                    created_by_user_id=owner.user_id,
                    status="active",
                    metadata_json={"is_synthetic": True},
                )
                s.add_all([gh_conn, jira_conn])
                s.flush()

                public_gh_policy = SourceAccessPolicy(
                    organisation_id=org_id,
                    project_id=proj_id,
                    source_connection_id=gh_conn.id,
                    provider="github",
                    scope_identifier="synthetic:repo:1",
                    visibility_policy=SourceVisibilityPolicy.PROJECT_MEMBERS_VERIFIED.value,
                    allowed_user_ids=[str(owner.user_id)],
                )
                public_jira_policy = SourceAccessPolicy(
                    organisation_id=org_id,
                    project_id=proj_id,
                    source_connection_id=jira_conn.id,
                    provider="jira",
                    scope_identifier="synthetic:jira:NEX",
                    visibility_policy=SourceVisibilityPolicy.PROJECT_MEMBERS_VERIFIED.value,
                    allowed_user_ids=[str(owner.user_id)],
                )
                restricted_sec_policy = SourceAccessPolicy(
                    organisation_id=org_id,
                    project_id=proj_id,
                    source_connection_id=jira_conn.id,
                    provider="jira",
                    scope_identifier="synthetic:jira:SEC-777",
                    visibility_policy=SourceVisibilityPolicy.RESTRICTED_FAIL_CLOSED.value,
                    allowed_user_ids=[str(owner.user_id)],
                )
                s.add_all([public_gh_policy, public_jira_policy, restricted_sec_policy])
                s.flush()

                # 1. Synthetic PDF Architecture Note
                ev_pdf = ev_repo.create_evidence_item(
                    organisation_id=org_id,
                    project_id=proj_id,
                    uploaded_by_user_id=owner.user_id,
                    source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
                    source_provider="local_upload",
                    category="pdf_document",
                    source_external_id=f"synthetic:pdf:{uuid.uuid4()}",
                    source_url=None,
                    source_author_identity="fixture-architect",
                    title="Synthetic Auth Token Rotation Specification",
                    original_filename="auth-rotation-spec.pdf",
                    mime_type="application/pdf",
                    file_size_bytes=2048,
                    content_hash="1" * 64,
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
                    metadata_json={"is_synthetic": True, "synthetic_fixture": True},
                )
                pdf_text = (
                    "Refresh sessions use SHA-256 token digests inside a single token_family_id. "
                    "When a previously rotated credential is replayed or presented out of "
                    "sequence, the platform invalidates the entire session family immediately "
                    "and clears the cookie."
                )
                ev_repo.replace_extracted_content(
                    evidence_id=ev_pdf.id,
                    extracted_text=pdf_text,
                    warnings=(),
                    pages=(_page(pdf_text),),
                )
                job_repo.create_job(
                    organisation_id=org_id,
                    project_id=proj_id,
                    evidence_id=ev_pdf.id,
                    triggered_by_user_id=owner.user_id,
                    job_type=BackgroundJobType.EVIDENCE_INDEXING.value,
                )

                # 2. Synthetic DOCX Disaster Recovery Runbook
                ev_docx = ev_repo.create_evidence_item(
                    organisation_id=org_id,
                    project_id=proj_id,
                    uploaded_by_user_id=owner.user_id,
                    source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
                    source_provider="local_upload",
                    category="docx_document",
                    source_external_id=f"synthetic:docx:{uuid.uuid4()}",
                    source_url=None,
                    source_author_identity="fixture-sre",
                    title="Synthetic Operational Failover Runbook",
                    original_filename="failover-runbook.docx",
                    mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    file_size_bytes=3072,
                    content_hash="2" * 64,
                    storage_provider=None,
                    storage_object_key=None,
                    encryption_algorithm=None,
                    encryption_key_id=None,
                    acl_scope="project_members",
                    source_created_at=t_now,
                    source_updated_at=t_now,
                    extracted_at=t_now,
                    processing_status=EvidenceProcessingStatus.EXTRACTED.value,
                    extraction_method="python_docx",
                    page_count=1,
                    metadata_json={"is_synthetic": True, "synthetic_fixture": True},
                )
                docx_text = (
                    "# Standby Database Promotion Steps\n\n"
                    "| Step | Command | Purpose |\n"
                    "| --- | --- | --- |\n"
                    "| 1 | pg_ctl promote | Elevate warm replica to writable primary |\n"
                    "| 2 | POST /indexing/reindex | Rebuild secondary vector store cleanly |"
                )
                ev_repo.replace_extracted_content(
                    evidence_id=ev_docx.id,
                    extracted_text=docx_text,
                    warnings=(),
                    pages=(_page(docx_text),),
                )
                job_repo.create_job(
                    organisation_id=org_id,
                    project_id=proj_id,
                    evidence_id=ev_docx.id,
                    triggered_by_user_id=owner.user_id,
                    job_type=BackgroundJobType.EVIDENCE_INDEXING.value,
                )

                # 3. Synthetic GitHub PR with path & SHA prefix
                pr_text = (
                    "Updated backend/app/services/auth.py in commit "
                    "9f8e7d6c5b4a32109876543210fedcba98765432. "
                    "Requests to POST /api/v1/auth/refresh reject untrusted origins "
                    "with HTTP 403 CSRF_VALIDATION_FAILED "
                    "and block stolen refresh cookies from replaying active sessions."
                )
                ev_pr = ingestor.upsert_record(
                    organisation_id=org_id,
                    project_id=proj_id,
                    source_connection_id=gh_conn.id,
                    triggered_by_user_id=owner.user_id,
                    record=NormalizedSourceEvidence(
                        source_type=EvidenceSourceType.GITHUB.value,
                        source_provider="github",
                        category="pull_request",
                        source_external_id="synthetic:gh:pr:42",
                        source_url="https://github.com/synthetic-org/synthetic-repo/pull/42",
                        source_author_identity="fixture-dev",
                        title="[SYNTHETIC] PR #42: Harden session refresh CSRF checks",
                        source_created_at=t_now,
                        source_updated_at=t_now,
                        extraction_method="github_api_v3",
                        acl_scope="project_members",
                        source_access_policy_id=public_gh_policy.id,
                        extracted_text=pr_text,
                        pages=(_page(pr_text, section="pull_request_body"),),
                        metadata_json={
                            "is_synthetic": True,
                            "synthetic_fixture": True,
                            "github_item_type": "pull_request",
                            "repository": "synthetic-org/synthetic-repo",
                            "number": 42,
                        },
                    ),
                ).evidence_item

                # 4. Synthetic Jira Ticket NEX-142
                jira_text = (
                    "Ticket NEX-142 investigated truncated text output during optical scanning "
                    "of dense engineering diagrams. "
                    "Setting OLLAMA_OCR_NUM_CTX to 8192 and capping OLLAMA_OCR_NUM_PREDICT "
                    "at 4096 prevented silent incomplete pages."
                )
                ev_jira = ingestor.upsert_record(
                    organisation_id=org_id,
                    project_id=proj_id,
                    source_connection_id=jira_conn.id,
                    triggered_by_user_id=owner.user_id,
                    record=NormalizedSourceEvidence(
                        source_type=EvidenceSourceType.JIRA.value,
                        source_provider="jira",
                        category="issue",
                        source_external_id="synthetic:jira:NEX-142",
                        source_url="https://synthetic.atlassian.net/browse/NEX-142",
                        source_author_identity="fixture-ml",
                        title="[SYNTHETIC] [NEX-142] Fix optical page output truncation",
                        source_created_at=t_now,
                        source_updated_at=t_now,
                        extraction_method="jira_rest_v3",
                        acl_scope="project_members",
                        source_access_policy_id=public_jira_policy.id,
                        extracted_text=jira_text,
                        pages=(_page(jira_text, section="jira_issue_summary"),),
                        metadata_json={
                            "is_synthetic": True,
                            "synthetic_fixture": True,
                            "jira_item_type": "issue",
                            "jira_issue_key": "NEX-142",
                            "project_key": "NEX",
                        },
                    ),
                ).evidence_item

                # 5. Restricted Synthetic Security Ticket SEC-777 (owner only)
                sec_text = (
                    "Confidential SEC-777 procedure: emergency JWT_SECRET_KEY rotation "
                    "invalidates active signing certificates."
                )
                ev_sec = ingestor.upsert_record(
                    organisation_id=org_id,
                    project_id=proj_id,
                    source_connection_id=jira_conn.id,
                    triggered_by_user_id=owner.user_id,
                    record=NormalizedSourceEvidence(
                        source_type=EvidenceSourceType.JIRA.value,
                        source_provider="jira",
                        category="issue",
                        source_external_id="synthetic:jira:SEC-777",
                        source_url="https://synthetic.atlassian.net/browse/SEC-777",
                        source_author_identity="fixture-sec",
                        title="[SYNTHETIC] [SEC-777] Emergency key rotation",
                        source_created_at=t_now,
                        source_updated_at=t_now,
                        extraction_method="jira_rest_v3",
                        acl_scope="source_restricted",
                        source_access_policy_id=restricted_sec_policy.id,
                        extracted_text=sec_text,
                        pages=(_page(sec_text, section="jira_issue_summary"),),
                        metadata_json={
                            "is_synthetic": True,
                            "synthetic_fixture": True,
                            "jira_item_type": "issue",
                            "jira_issue_key": "SEC-777",
                            "project_key": "SEC",
                        },
                    ),
                ).evidence_item

                # 6. Non-synthetic local project note to test default `include_synthetic=False`
                ev_real = ev_repo.create_evidence_item(
                    organisation_id=org_id,
                    project_id=proj_id,
                    uploaded_by_user_id=owner.user_id,
                    source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
                    source_provider="local_upload",
                    category="pdf_document",
                    source_external_id=f"local:{uuid.uuid4()}",
                    source_url=None,
                    source_author_identity="eval-uploader",
                    title="Platform Readiness Probe Notes",
                    original_filename="readiness-notes.pdf",
                    mime_type="application/pdf",
                    file_size_bytes=512,
                    content_hash="3" * 64,
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
                real_text = (
                    "GET /health/ready returns HTTP 200 degraded when PostgreSQL is reachable "
                    "but Ollama or ChromaDB is down."
                )
                ev_repo.replace_extracted_content(
                    evidence_id=ev_real.id,
                    extracted_text=real_text,
                    warnings=(),
                    pages=(_page(real_text),),
                )
                job_repo.create_job(
                    organisation_id=org_id,
                    project_id=proj_id,
                    evidence_id=ev_real.id,
                    triggered_by_user_id=owner.user_id,
                    job_type=BackgroundJobType.EVIDENCE_INDEXING.value,
                )
                s.commit()

            # Execute worker indexing with real Ollama + live ChromaDB v2 + PG GIN TSVECTOR
            assert indexing_worker.drain_pending_jobs(max_jobs=20) == 6

            with session_factory() as s:
                gin_count = s.execute(
                    text(
                        "SELECT count(*) FROM evidence_chunks "
                        "WHERE project_id = :pid AND search_vector IS NOT NULL"
                    ),
                    {"pid": proj_id},
                ).scalar_one()
                assert gin_count >= 6

            # Live Health & Status endpoints
            health = client.get(
                f"/api/v1/projects/{proj['id']}/indexing/health",
                headers=owner.headers,
            )
            assert health.status_code == 200, health.text
            h_json = health.json()
            assert h_json["postgresql_fts_ready"] is True
            assert h_json["chroma_reachable"] is True
            assert h_json["chroma_collection_exists"] is True
            assert h_json["collection_compatible"] is True
            assert h_json["expected_dimensions"] == 768
            assert h_json["chroma_vector_count"] == gin_count

            # Default search (include_synthetic=False) hides synthetic fixtures in PG & Chroma
            for mode in ("keyword", "semantic", "hybrid"):
                r_no_syn = client.post(
                    f"/api/v1/projects/{proj['id']}/search",
                    headers=owner.headers,
                    json={"query": "OLLAMA_OCR_NUM_CTX NEX-142", "mode": mode},
                )
                assert r_no_syn.status_code == 200
                returned_ids = {hit["evidence_id"] for hit in r_no_syn.json()["results"]}
                assert str(ev_jira.id) not in returned_ids
                assert str(ev_sec.id) not in returned_ids

                r_real = client.post(
                    f"/api/v1/projects/{proj['id']}/search",
                    headers=owner.headers,
                    json={"query": "readiness probe PostgreSQL degraded", "mode": mode},
                )
                assert r_real.status_code == 200
                assert str(ev_real.id) in {
                    hit["evidence_id"] for hit in r_real.json()["results"]
                }

            # Live ACL across real PG FTS & Chroma metadata filtering: reviewer cannot see SEC-777
            for mode in ("keyword", "semantic", "hybrid"):
                r_rev = client.post(
                    f"/api/v1/projects/{proj['id']}/search",
                    headers=reviewer.headers,
                    json={
                        "query": "SEC-777 emergency JWT_SECRET_KEY rotation",
                        "mode": mode,
                        "filters": {"include_synthetic": True},
                    },
                )
                assert r_rev.status_code == 200
                assert str(ev_sec.id) not in {
                    h["evidence_id"] for h in r_rev.json()["results"]
                }

            r_own_sec = client.post(
                f"/api/v1/projects/{proj['id']}/search",
                headers=owner.headers,
                json={
                    "query": "SEC-777",
                    "mode": "hybrid",
                    "filters": {"include_synthetic": True},
                },
            )
            assert r_own_sec.status_code == 200
            assert str(ev_sec.id) in {h["evidence_id"] for h in r_own_sec.json()["results"]}

            # Synthetic Fixture Retrieval Benchmark (IDs, paths, SHA & conceptual queries)
            benchmark_queries: list[tuple[str, set[str]]] = [
                ("NEX-142", {str(ev_jira.id)}),
                ("backend/app/services/auth.py", {str(ev_pr.id)}),
                ("9f8e7d6c5b4a", {str(ev_pr.id)}),
                (
                    "procedure to recover the primary database after an outage",
                    {str(ev_docx.id)},
                ),
                (
                    "how the system stops stolen refresh cookies from being replayed",
                    {str(ev_pdf.id), str(ev_pr.id)},
                ),
                (
                    "why did optical character recognition cut off long scanned pages",
                    {str(ev_jira.id)},
                ),
            ]

            metrics_by_mode: dict[str, dict[str, float]] = {}
            for mode in ("keyword", "semantic", "hybrid"):
                metrics_by_mode[mode] = _evaluate_query_set(
                    client=client,
                    proj_id=proj["id"],
                    headers=owner.headers,
                    mode=mode,
                    queries=benchmark_queries,
                )

            with capsys.disabled():
                print(
                    "\n[Phase 2.5 Synthetic Development Fixture Retrieval Benchmark]",
                    metrics_by_mode,
                )

            assert metrics_by_mode["hybrid"]["recall_at_5"] >= 0.83
            assert metrics_by_mode["hybrid"]["mrr"] >= 0.75
            assert not math.isnan(metrics_by_mode["semantic"]["precision_at_3"])
            # Hybrid fusion should match or exceed single-mode recall across the benchmark
            kw_rec = metrics_by_mode["keyword"]["recall_at_5"]
            sem_rec = metrics_by_mode["semantic"]["recall_at_5"]
            assert metrics_by_mode["hybrid"]["recall_at_5"] >= kw_rec
            assert metrics_by_mode["hybrid"]["recall_at_5"] >= sem_rec

    finally:
        if engine is not None:
            engine.dispose()
        try:
            real_chroma.delete_collection()
        except Exception:
            logger.warning(
                "Best-effort cleanup of temp Chroma collection '%s' failed.",
                temp_collection,
            )
        with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
            admin_conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (temp_db,),
            )
            admin_conn.execute(f'DROP DATABASE IF EXISTS "{temp_db}"')
