"""Live Ollama `qwen3:8b` knowledge reconstruction & grounding evaluation on synthetic fixtures."""

from __future__ import annotations

import json
import logging
import time
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
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import main as app_main
from app.core.config import clear_settings_cache, get_settings
from app.models.enums import (
    EpistemicStatus,
    EvidenceProcessingStatus,
    EvidenceSourceType,
    ExtractionRunStatus,
    IntegrationProvider,
    KnowledgeCategory,
    KnowledgeReviewStatus,
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
from app.services.llm import OllamaLLMClient
from app.services.reconstruction_worker import ReconstructionWorkerService
from tests.conftest import build_test_settings, register_and_login_user
from tests.helpers_retrieval import InMemoryEmbeddingService, InMemoryVectorStoreClient

logger = logging.getLogger("tests.qwen3_live_eval")
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


def _ollama_has_model(base_url: str, model_name: str) -> bool:
    try:
        resp = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=3.0)
        if resp.status_code != 200:
            return False
        models = resp.json().get("models") or []
        return any(str(m.get("name", "")).startswith(model_name) for m in models)
    except (httpx.HTTPError, ValueError):
        return False


def _page(text_content: str, *, page_number: int = 1, section: str = "body") -> ExtractedPageData:
    return ExtractedPageData(
        page_number=page_number,
        extraction_outcome="digital_text",
        ocr_applied=False,
        ocr_truncated=False,
        text_content=text_content,
        structured_metadata={"section": section},
    )


@pytest.mark.skipif(
    not _ROOT_ENV.exists(),
    reason="Root .env unavailable for live PostgreSQL / Ollama qwen3:8b evaluation test",
)
def test_live_qwen3_knowledge_reconstruction_grounding_and_metrics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    clear_settings_cache()
    live_cfg = get_settings()

    if not _ollama_has_model(live_cfg.ollama.base_url, live_cfg.ollama.llm_model):
        pytest.skip(
            f"Ollama LLM model '{live_cfg.ollama.llm_model}' is unavailable at "
            f"{live_cfg.ollama.base_url}."
        )

    password = live_cfg.database.password.get_secret_value()
    temp_db = f"ipkrh_know_eval_{uuid.uuid4().hex[:8]}"
    admin_dsn = (
        f"postgresql://{live_cfg.database.user}:{password}@127.0.0.1:{live_cfg.database.port}/postgres"
    )
    temp_url = (
        f"postgresql+psycopg://{live_cfg.database.user}:{password}"
        f"@127.0.0.1:{live_cfg.database.port}/{temp_db}"
    )

    try:
        with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
            admin_conn.execute(f'CREATE DATABASE "{temp_db}"')
    except psycopg.OperationalError as exc:
        pytest.skip(f"PostgreSQL server unreachable for live qwen3 evaluation: {exc}")

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
            upload_storage_path=tmp_path / "live_know_uploads",
            embedding_expected_dimensions=64,
            jwt_access_token_expire_minutes=60,
            ollama_base_url=live_cfg.ollama.base_url,
            ollama_llm_model=live_cfg.ollama.llm_model,
            ollama_llm_timeout_seconds=live_cfg.ollama.llm_timeout_seconds,
            ollama_llm_num_ctx=live_cfg.ollama.llm_num_ctx,
            ollama_llm_num_predict=live_cfg.ollama.llm_num_predict,
            ollama_llm_temperature=live_cfg.ollama.llm_temperature,
            ollama_llm_think=live_cfg.ollama.llm_think,
        )
        monkeypatch.setattr(app_main, "create_db_engine", lambda _s: engine)
        monkeypatch.setattr(app_main, "create_session_factory", lambda _e: session_factory)
        monkeypatch.setattr(app_main, "verify_database_connection", lambda _e: 1.0)

        fake_embed = InMemoryEmbeddingService(dims=64)
        fake_chroma = InMemoryVectorStoreClient(expected_dimensions=64)
        real_llm = OllamaLLMClient(
            base_url=live_cfg.ollama.base_url,
            model=live_cfg.ollama.llm_model,
            num_ctx=live_cfg.ollama.llm_num_ctx,
            num_predict=live_cfg.ollama.llm_num_predict,
            temperature=live_cfg.ollama.llm_temperature,
            timeout_seconds=live_cfg.ollama.llm_timeout_seconds,
            think=live_cfg.ollama.llm_think,
        )

        app = app_main.create_app(settings)
        app.state.embedding_service = fake_embed
        app.state.vector_store_client = fake_chroma
        app.state.llm_client = real_llm

        indexing_worker = IndexingWorkerService(
            session_factory=session_factory,
            chunking_service=ChunkingService(settings=settings.chunking),
            embedding_service=fake_embed,
            vector_store=fake_chroma,
            ingestion_settings=settings.ingestion,
        )
        recon_worker = ReconstructionWorkerService(
            session_factory=session_factory,
            llm_client=real_llm,
            extraction_settings=settings.extraction,
            ingestion_settings=settings.ingestion,
        )

        with TestClient(app) as client:
            owner = register_and_login_user(
                client, email="qwen-eval-owner@example.com", full_name="Synthetic Eval Owner"
            )
            org = client.post(
                "/api/v1/organisations",
                headers=owner.headers,
                json={"name": "Synthetic Eval Org"},
            ).json()
            proj = client.post(
                f"/api/v1/organisations/{org['id']}/projects",
                headers=owner.headers,
                json={
                    "name": "Synthetic Eval Project",
                    "status": "active",
                    "visibility": "private",
                },
            ).json()

            oid = uuid.UUID(org["id"])
            pid = uuid.UUID(proj["id"])
            t_now = datetime(2026, 10, 15, tzinfo=UTC)

            with session_factory() as session:
                ev_repo = EvidenceRepository(session)
                job_repo = BackgroundJobRepository(session)
                ingestor = SourceEvidenceIngestor(
                    session=session,
                    evidence_repository=ev_repo,
                    job_repository=job_repo,
                )

                adr_text = (
                    "SYNTHETIC FIXTURE — Architecture Decision Record ADR-002 (2026-10-12).\n"
                    "Decision: Alex Chen decided to keep PostgreSQL 16 as the canonical store "
                    "instead of introducing Neo4j because transactional ACID integrity and a "
                    "single backup pipeline reduce handover operational risk.\n"
                    "Architecture: The FastAPI route POST /api/v1/projects/{project_id}/knowledge/"
                    "extract queues asynchronous extraction jobs persisted in PostgreSQL table "
                    "knowledge_extraction_runs.\n"
                    "Dependencies: Knowledge reconstruction depends on local Ollama service "
                    "running qwen3:8b and ChromaDB HTTP server on port 8001."
                )
                doc_item = ev_repo.create_evidence_item(
                    organisation_id=oid,
                    project_id=pid,
                    uploaded_by_user_id=owner.user_id,
                    source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
                    source_provider="local_upload",
                    category="pdf_document",
                    source_external_id="synthetic:adr-002",
                    source_url=None,
                    source_author_identity="Alex Chen",
                    title="SYNTHETIC-ADR-002.pdf",
                    original_filename="SYNTHETIC-ADR-002.pdf",
                    mime_type="application/pdf",
                    file_size_bytes=len(adr_text.encode("utf-8")),
                    content_hash="a1" * 32,
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
                ev_repo.replace_extracted_content(
                    evidence_id=doc_item.id,
                    extracted_text=adr_text,
                    warnings=(),
                    pages=(_page(adr_text, section="ADR-002"),),
                )
                job_repo.create_job(
                    organisation_id=oid,
                    project_id=pid,
                    evidence_id=doc_item.id,
                    triggered_by_user_id=owner.user_id,
                    job_type="evidence_indexing",
                )

                gh_conn = SourceConnection(
                    organisation_id=oid,
                    provider=IntegrationProvider.GITHUB.value,
                    display_name="Synthetic Eval GitHub",
                    created_by_user_id=owner.user_id,
                    status="active",
                    metadata_json={"synthetic_fixture": True},
                )
                session.add(gh_conn)
                session.flush()
                gh_policy = SourceAccessPolicy(
                    organisation_id=oid,
                    project_id=pid,
                    source_connection_id=gh_conn.id,
                    provider=IntegrationProvider.GITHUB.value,
                    scope_identifier="synthetic/eval-repo",
                    visibility_policy=SourceVisibilityPolicy.PROJECT_MEMBERS_VERIFIED.value,
                    sync_permission_status=SourcePermissionVerificationStatus.VERIFIED.value,
                    allowed_user_ids=[str(owner.user_id)],
                )
                session.add(gh_policy)
                session.flush()

                pr_text = (
                    "SYNTHETIC FIXTURE — GitHub PR SYNTH-PR-55.\n"
                    "Completed work: Merged Alembic migration "
                    "20261112_0007_knowledge_reconstruction on 2026-10-14.\n"
                    "Unfinished work: Sliding-window API rate limiter middleware remains open and "
                    "unmerged pending Redis decision.\n"
                    "Ownership: @achen maintains backend/app/services/reconstruction_worker.py. "
                    "Priya Nair owns backend/app/services/chunking.py."
                )
                pr_outcome = ingestor.upsert_record(
                    organisation_id=oid,
                    project_id=pid,
                    source_connection_id=gh_conn.id,
                    triggered_by_user_id=owner.user_id,
                    record=NormalizedSourceEvidence(
                        source_type=EvidenceSourceType.GITHUB.value,
                        source_provider="github",
                        category="pull_request",
                        source_external_id="synthetic:pr:55",
                        source_url="https://example.invalid/synthetic/eval-repo/pull/55",
                        source_author_identity="@achen",
                        title="SYNTH-PR-55: Knowledge schema migration",
                        extraction_method="github_api",
                        extracted_text=pr_text,
                        pages=(_page(pr_text, section="PR #55"),),
                        source_created_at=t_now,
                        source_updated_at=t_now,
                        source_access_policy_id=gh_policy.id,
                        acl_scope="project_members",
                        metadata_json={"is_synthetic": True, "synthetic_fixture": True},
                    ),
                )

                jira_conn = SourceConnection(
                    organisation_id=oid,
                    provider=IntegrationProvider.JIRA.value,
                    display_name="Synthetic Eval Jira",
                    created_by_user_id=owner.user_id,
                    status="active",
                    metadata_json={"synthetic_fixture": True},
                )
                session.add(jira_conn)
                session.flush()
                jira_policy = SourceAccessPolicy(
                    organisation_id=oid,
                    project_id=pid,
                    source_connection_id=jira_conn.id,
                    provider=IntegrationProvider.JIRA.value,
                    scope_identifier="SYNTH",
                    visibility_policy=SourceVisibilityPolicy.PROJECT_MEMBERS_VERIFIED.value,
                    sync_permission_status=SourcePermissionVerificationStatus.VERIFIED.value,
                    allowed_user_ids=[str(owner.user_id)],
                )
                session.add(jira_policy)
                session.flush()

                jira_text = (
                    "SYNTHETIC FIXTURE — Jira Bug NEX-201.\n"
                    "Critical P1 blocker: Windows file locking prevents cleanup of temporary "
                    "upload files when PyMuPDF Document handle stays open during OCR fallback.\n"
                    "Risk note: Batch timeout during OCR retry should be reviewed before "
                    "production load testing."
                )
                jira_outcome = ingestor.upsert_record(
                    organisation_id=oid,
                    project_id=pid,
                    source_connection_id=jira_conn.id,
                    triggered_by_user_id=owner.user_id,
                    record=NormalizedSourceEvidence(
                        source_type=EvidenceSourceType.JIRA.value,
                        source_provider="jira",
                        category="issue",
                        source_external_id="synthetic:jira:NEX-201",
                        source_url="https://example.invalid/synthetic/browse/NEX-201",
                        source_author_identity="Priya Nair",
                        title="NEX-201: PyMuPDF Windows file handle lock",
                        extraction_method="jira_api",
                        extracted_text=jira_text,
                        pages=(_page(jira_text, section="NEX-201"),),
                        source_created_at=t_now,
                        source_updated_at=t_now,
                        source_access_policy_id=jira_policy.id,
                        acl_scope="project_members",
                        metadata_json={"is_synthetic": True, "synthetic_fixture": True},
                    ),
                )
                session.commit()

            assert indexing_worker.drain_pending_jobs(max_jobs=10) == 3

            # Trigger 3 targeted runs covering ALL 6 categories (6 focused live qwen3:8b calls)
            run_specs: list[tuple[uuid.UUID, list[str]]] = [
                (
                    doc_item.id,
                    [
                        KnowledgeCategory.DECISIONS_RATIONALE.value,
                        KnowledgeCategory.TECHNICAL_ARCHITECTURE.value,
                        KnowledgeCategory.DEPENDENCIES.value,
                    ],
                ),
                (
                    pr_outcome.evidence_item.id,
                    [
                        KnowledgeCategory.WORK_ITEMS.value,
                        KnowledgeCategory.RESPONSIBILITIES_OWNERSHIP.value,
                    ],
                ),
                (
                    jira_outcome.evidence_item.id,
                    [KnowledgeCategory.BUGS_BLOCKERS_RISKS.value],
                ),
            ]
            run_ids: list[str] = []
            for ev_id, cats in run_specs:
                trigger = client.post(
                    f"/api/v1/projects/{proj['id']}/evidence/{ev_id}/extract",
                    headers=owner.headers,
                    json={"categories": cats, "force_rerun": True},
                )
                assert trigger.status_code == 202, trigger.text
                run_ids.append(trigger.json()["run"]["id"])

            t_start = time.perf_counter()
            assert recon_worker.drain_pending_jobs(max_jobs=10) == 3
            wall_ms = int((time.perf_counter() - t_start) * 1000)

            run_details: list[dict[str, Any]] = []
            for rid in run_ids:
                r_resp = client.get(
                    f"/api/v1/projects/{proj['id']}/knowledge/runs/{rid}",
                    headers=owner.headers,
                )
                assert r_resp.status_code == 200, r_resp.text
                rd = r_resp.json()
                assert rd["status"] == ExtractionRunStatus.COMPLETED.value, rd
                assert rd["processed_evidence_items"] == 1
                assert rd["failed_evidence_items"] == 0
                run_details.append(rd)

            total_persisted = sum(int(rd["claims_persisted"]) for rd in run_details)
            assert total_persisted >= 4

            # Synthetic isolation check: default query MUST hide synthetic claims!
            def_resp = client.get(
                f"/api/v1/projects/{proj['id']}/knowledge/items",
                headers=owner.headers,
                params={"limit": 100},
            )
            assert def_resp.status_code == 200, def_resp.text
            assert def_resp.json()["total"] == 0

            syn_resp = client.get(
                f"/api/v1/projects/{proj['id']}/knowledge/items",
                headers=owner.headers,
                params={"include_synthetic": True, "limit": 100},
            )
            assert syn_resp.status_code == 200, syn_resp.text
            syn_items: list[dict[str, Any]] = syn_resp.json()["items"]
            assert len(syn_items) >= 4

            categories_seen: dict[str, int] = {}
            owners_seen: set[str] = set()
            all_excerpts_verified = True
            for summary in syn_items:
                assert summary["is_synthetic"] is True
                assert summary["epistemic_status"] in {
                    EpistemicStatus.EXTRACTED.value,
                    EpistemicStatus.AI_INTERPRETED.value,
                }
                assert summary["epistemic_status"] != EpistemicStatus.HUMAN_VERIFIED.value
                assert summary["review_status"] == KnowledgeReviewStatus.PENDING_REVIEW.value
                cat = str(summary["category"])
                categories_seen[cat] = categories_seen.get(cat, 0) + 1
                if summary["person_or_owner_label"]:
                    owners_seen.add(str(summary["person_or_owner_label"]))

                d_resp = client.get(
                    f"/api/v1/projects/{proj['id']}/knowledge/items/{summary['id']}",
                    headers=owner.headers,
                )
                assert d_resp.status_code == 200, d_resp.text
                detail = d_resp.json()
                links = detail["evidence_links"]
                assert len(links) >= 1
                for link in links:
                    if not link["excerpt_verified"] or not str(link["supporting_excerpt"]).strip():
                        all_excerpts_verified = False

            assert all_excerpts_verified is True
            # Verify coverage across at least 4 of the 6 categories with real qwen3:8b
            assert len(categories_seen) >= 4
            assert KnowledgeCategory.DECISIONS_RATIONALE.value in categories_seen

            report = {
                "model": live_cfg.ollama.llm_model,
                "think": live_cfg.ollama.llm_think,
                "num_ctx": live_cfg.ollama.llm_num_ctx,
                "wall_ms": wall_ms,
                "runs_duration_ms": sum(int(rd["duration_ms"] or 0) for rd in run_details),
                "batches_executed": sum(int(rd["batches_executed"]) for rd in run_details),
                "candidates_generated": sum(int(rd["candidates_generated"]) for rd in run_details),
                "claims_persisted": total_persisted,
                "claims_rejected_ungrounded": sum(
                    int(rd["claims_rejected_ungrounded"]) for rd in run_details
                ),
                "duplicates_merged": sum(int(rd["duplicates_merged"]) for rd in run_details),
                "prompt_tokens": sum(int(rd["prompt_tokens"]) for rd in run_details),
                "completion_tokens": sum(int(rd["completion_tokens"]) for rd in run_details),
                "warnings": [w for rd in run_details for w in rd["warnings"]],
                "categories_seen": categories_seen,
                "owners_seen": sorted(owners_seen),
                "all_excerpts_verified": all_excerpts_verified,
                "items_preview": [
                    {
                        "category": s["category"],
                        "title": s["title"],
                        "epistemic_status": s["epistemic_status"],
                        "support_classification": s["support_classification"],
                        "normalised_status": s["normalised_status"],
                        "person_or_owner_label": s["person_or_owner_label"],
                        "severity": s["structured_payload"].get("severity"),
                    }
                    for s in syn_items
                ],
            }
            logger.info("Qwen3 live evaluation metrics: %s", json.dumps(report, sort_keys=True))
            with capsys.disabled():
                print("\nQWEN3 LIVE EVALUATION METRICS:")
                print(json.dumps(report, indent=2, sort_keys=True))
    finally:
        if engine is not None:
            engine.dispose()
        with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as admin_conn:
            admin_conn.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid()
                """,
                (temp_db,),
            )
            admin_conn.execute(f'DROP DATABASE IF EXISTS "{temp_db}"')
        clear_settings_cache()
