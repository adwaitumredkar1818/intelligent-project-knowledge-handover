"""Unit tests for Phase 2.5 structure-aware ChunkingService and FTS token expansion."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

from app.core.config import ChunkingSettings
from app.models.enums import (
    EvidenceChunkType,
    EvidenceProcessingStatus,
    EvidenceSourceType,
)
from app.models.evidence import EvidenceItem
from app.services.chunking import (
    ChunkingService,
    compute_chunk_content_hash,
    extract_fts_identifier_tokens,
)


def _fake_evidence(
    *,
    source_type: str,
    category: str,
    title: str,
    extracted_text: str,
    pages: list[tuple[int, str, bool, dict[str, Any]]] | None = None,
    metadata_json: dict[str, Any] | None = None,
    author: str | None = "alice",
    source_external_id: str = "ext-1",
    original_filename: str | None = None,
    processing_status: str = EvidenceProcessingStatus.EXTRACTED.value,
    deleted_at: datetime | None = None,
) -> EvidenceItem:
    ev_pages = [
        SimpleNamespace(
            page_number=pnum,
            text_content=ptext,
            ocr_applied=pocr,
            structured_metadata=pmeta,
        )
        for pnum, ptext, pocr, pmeta in (pages or [])
    ]
    fake = SimpleNamespace(
        id=uuid.uuid4(),
        organisation_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        source_type=source_type,
        source_provider="test_provider",
        category=category,
        title=title,
        source_external_id=source_external_id,
        original_filename=original_filename,
        source_author_identity=author,
        source_created_at=datetime(2026, 11, 10, 12, 0, tzinfo=UTC),
        processing_status=processing_status,
        deleted_at=deleted_at,
        metadata_json=metadata_json or {},
        content=SimpleNamespace(extracted_text=extracted_text),
        pages=ev_pages,
    )
    return cast(EvidenceItem, fake)


def test_extract_fts_identifier_tokens_and_hashing() -> None:
    ident = extract_fts_identifier_tokens(
        "Fix AuthMiddleware regression in backend/app/api/routes/evidence.py "
        "(NEX-142, PR#87, 9f4c2b1a8e7d6c5b).",
        "docs/handover-notes.md",
    )
    tokens_lower = ident.lower().split()
    assert "nex-142" in tokens_lower
    assert "nex" in tokens_lower
    assert "142" in tokens_lower
    assert "backend/app/api/routes/evidence.py" in tokens_lower
    assert "evidence.py" in tokens_lower
    assert "authmiddleware" in tokens_lower
    assert "middleware" in tokens_lower
    assert "9f4c2b1a8e7d6c5b" in tokens_lower
    assert "9f4c2b1a" in tokens_lower

    h1 = compute_chunk_content_hash(
        chunk_type="issue_body",
        section_title="Overview",
        page_number=1,
        source_author_identity="alice",
        chunk_text="Database ownership checklist.",
    )
    h2 = compute_chunk_content_hash(
        chunk_type="issue_body",
        section_title="Overview",
        page_number=1,
        source_author_identity="alice",
        chunk_text="Database ownership checklist.",
    )
    h3 = compute_chunk_content_hash(
        chunk_type="issue_comment",
        section_title="Overview",
        page_number=1,
        source_author_identity="alice",
        chunk_text="Database ownership checklist.",
    )
    assert len(h1) == 64
    assert h1 == h2
    assert h1 != h3


def test_chunking_skips_deleted_and_blank_evidence() -> None:
    service = ChunkingService(settings=ChunkingSettings())

    deleted_ev = _fake_evidence(
        source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
        category="pdf_document",
        title="deleted.pdf",
        extracted_text="Important text",
        processing_status=EvidenceProcessingStatus.DELETED.value,
        deleted_at=datetime.now(UTC),
    )
    assert service.chunk_evidence(deleted_ev) == []

    blank_ev = _fake_evidence(
        source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
        category="pdf_document",
        title="empty.pdf",
        extracted_text="   \n\t  ",
    )
    assert service.chunk_evidence(blank_ev) == []


def test_chunking_pdf_digital_and_ocr_pages() -> None:
    service = ChunkingService(
        settings=ChunkingSettings(target_chars=300, max_chars=450, overlap_chars=50, min_chars=50)
    )
    p1 = "# Architecture Overview\n\nPostgreSQL stores canonical structured platform data."
    p2 = (
        "## Incident Runbook\n\n"
        + ("Failover runbook step validates database read replicas carefully. " * 12)
    )
    canonical = f"{p1}\n\n{p2}"
    ev = _fake_evidence(
        source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
        category="pdf_document",
        title="architecture.pdf",
        original_filename="architecture.pdf",
        extracted_text=canonical,
        pages=[
            (1, p1, False, {"source": "digital"}),
            (2, p2, True, {"source": "ocr"}),
        ],
    )

    drafts = service.chunk_evidence(ev)
    assert len(drafts) >= 3
    assert drafts[0].chunk_type == EvidenceChunkType.DOCUMENT_SECTION.value
    assert drafts[0].page_number == 1
    assert drafts[0].section_title == "Architecture Overview"
    assert drafts[0].char_start == 0

    ocr_drafts = [d for d in drafts if d.page_number == 2]
    assert ocr_drafts
    assert all(d.chunk_type == EvidenceChunkType.OCR_PAGE.value for d in ocr_drafts)
    assert all(d.section_title == "Architecture Overview > Incident Runbook" for d in ocr_drafts)
    assert all(d.char_count <= 450 for d in drafts)
    assert [d.chunk_index for d in drafts] == list(range(len(drafts)))


def test_chunking_docx_preserves_intact_small_tables_and_splits_large_tables_by_row() -> None:
    service = ChunkingService(
        settings=ChunkingSettings(target_chars=320, max_chars=420, overlap_chars=60, min_chars=40)
    )
    small_table = "\n".join(
        [
            "# Service Owners",
            "| Service | Owner | Escalation |",
            "| :--- | :--- | :--- |",
            "| Auth API | Alice | #sec-oncall |",
            "| Retrieval Worker | Bob | #search-oncall |",
        ]
    )
    large_rows = [
        "| Key | Component | Owner Email Placeholder | Runbook |",
        "| :--- | :--- | :--- | :--- |",
        *[
            f"| SVC-{idx:03d} | worker-shard-{idx:03d} | team-{idx:03d} "
            f"| docs/runbooks/svc-{idx:03d}.md |"
            for idx in range(1, 14)
        ],
    ]
    large_table = "\n".join(large_rows)
    canonical = f"{small_table}\n\n{large_table}"

    ev = _fake_evidence(
        source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
        category="docx_document",
        title="service-catalogue.docx",
        original_filename="service-catalogue.docx",
        extracted_text=canonical,
        pages=[
            (1, small_table, False, {}),
            (2, large_table, False, {}),
        ],
    )

    drafts = service.chunk_evidence(ev)
    assert drafts
    assert drafts[0].chunk_type == EvidenceChunkType.TABLE_SEGMENT.value
    assert "| Auth API | Alice | #sec-oncall |" in drafts[0].chunk_text
    assert "| Retrieval Worker | Bob | #search-oncall |" in drafts[0].chunk_text

    large_table_chunks = [d for d in drafts if d.page_number == 2]
    assert len(large_table_chunks) >= 2
    for chunk in large_table_chunks:
        assert chunk.chunk_type == EvidenceChunkType.TABLE_SEGMENT.value
        assert chunk.char_count <= 420
        assert "| Key | Component | Owner Email Placeholder | Runbook |" in chunk.chunk_text


def test_chunking_github_issues_prs_commits_and_binary_doc_exclusions() -> None:
    service = ChunkingService(settings=ChunkingSettings())

    # 1. Binary/generated documentation item must be excluded cleanly
    lock_doc = _fake_evidence(
        source_type=EvidenceSourceType.GITHUB.value,
        category="documentation",
        title="yarn.lock",
        original_filename="yarn.lock",
        extracted_text="lockfile content should not be chunked",
        metadata_json={"github_item_type": "documentation", "path": "frontend/yarn.lock"},
    )
    assert service.chunk_evidence(lock_doc) == []

    # 2. Markdown doc succeeds
    readme = _fake_evidence(
        source_type=EvidenceSourceType.GITHUB.value,
        category="documentation",
        title="README.md",
        original_filename="README.md",
        extracted_text="# Handover Platform\n\nFollow docs/architecture/system-architecture.md.",
        metadata_json={
            "github_item_type": "documentation",
            "path": "docs/README.md",
            "repository": "acme/core",
        },
    )
    readme_chunks = service.chunk_evidence(readme)
    assert len(readme_chunks) == 1
    assert readme_chunks[0].chunk_type == EvidenceChunkType.DOCUMENTATION.value

    # 3. PR with body, reviews, comments, and changed files (filtering lockfiles)
    p1 = "# PR #42: Fix token refresh race\nFixes NEX-142 by rotating refresh family atomically."
    p2 = (
        "## Reviews & Comments\n"
        "- Review APPROVED by @carol (2026-11-11T09:00:00Z): Looks atomic.\n"
        "- Inline comment on `backend/app/services/auth.py` by @dave "
        "(2026-11-11T10:00:00Z): Check expiry."
    )
    p3 = (
        "## Changed Files Metadata\n"
        "- `backend/app/services/auth.py` (modified, +18/-4)\n"
        "- `frontend/package-lock.json` (modified, +900/-200)\n"
        "- `assets/diagram.png` (added, +0/-0)"
    )
    pr_ev = _fake_evidence(
        source_type=EvidenceSourceType.GITHUB.value,
        category="pull_request",
        title="PR #42: Fix token refresh race",
        extracted_text=f"{p1}\n\n{p2}\n\n{p3}",
        source_external_id="repo:90001:pr:42",
        author="bob",
        metadata_json={"github_item_type": "pull_request", "repository": "acme/core", "number": 42},
        pages=[
            (1, p1, False, {"section": "pull_request_body"}),
            (2, p2, False, {"section": "pull_request_reviews_and_comments"}),
            (3, p3, False, {"section": "changed_files_metadata"}),
        ],
    )
    pr_chunks = service.chunk_evidence(pr_ev)
    types = [c.chunk_type for c in pr_chunks]
    assert EvidenceChunkType.PR_BODY.value in types
    assert EvidenceChunkType.PR_REVIEW.value in types
    assert EvidenceChunkType.PR_CHANGED_FILES.value in types
    changed_files_chunk = next(
        c for c in pr_chunks if c.chunk_type == EvidenceChunkType.PR_CHANGED_FILES.value
    )
    assert "backend/app/services/auth.py" in changed_files_chunk.chunk_text
    assert "package-lock.json" not in changed_files_chunk.chunk_text
    assert "diagram.png" not in changed_files_chunk.chunk_text

    # 4. Issue with per-comment author identity & timestamp preservation
    ip1 = "Connection pool exhaustion under burst sync."
    ip2 = (
        "## Comment 1 by @erin (2026-11-11T14:20:00Z)\nReproduced with 50 concurrent workers.\n\n"
        "## Comment 2 by @frank (2026-11-11T15:45:00Z)\nRaised pool_size=15 to resolve."
    )
    issue_ev = _fake_evidence(
        source_type=EvidenceSourceType.GITHUB.value,
        category="issue_discussion",
        title="Issue #19",
        extracted_text=f"{ip1}\n\n{ip2}",
        metadata_json={"github_item_type": "issue", "repository": "acme/core", "number": 19},
        pages=[
            (1, ip1, False, {"section": "issue_body"}),
            (2, ip2, False, {"section": "issue_comments"}),
        ],
    )
    issue_chunks = service.chunk_evidence(issue_ev)
    comment_chunks = [
        c for c in issue_chunks if c.chunk_type == EvidenceChunkType.ISSUE_COMMENT.value
    ]
    assert len(comment_chunks) == 2
    assert comment_chunks[0].source_author_identity == "erin"
    assert comment_chunks[1].source_author_identity == "frank"
    assert comment_chunks[0].source_created_at == datetime(2026, 11, 11, 14, 20, tzinfo=UTC)
    assert comment_chunks[1].source_created_at == datetime(2026, 11, 11, 15, 45, tzinfo=UTC)


def test_chunking_jira_issues_links_comments_and_worklogs() -> None:
    service = ChunkingService(settings=ChunkingSettings())

    jp1 = (
        "# [NEX-142] Migrate Chroma search to hybrid RRF\n"
        "Status: In Progress\n\n"
        "## Description\nCombine PG FTS with Nomic embeddings.\n\n"
        "## Issue Links & Hierarchy\n"
        "- blocks: NEX-150 (API endpoint rollout)"
    )
    jp2 = (
        "### Comment 1 by Maya Lin (2026-11-10T08:15:00Z)\n"
        "Verified PG GIN latency stays below 12ms.\n\n"
        "### Comment 2 by Owen Park (2026-11-10T11:30:00Z)\n"
        "Added security revalidation before ranking."
    )
    jp3 = "## Recent Activity\n- Maya Lin logged 2h: Benchmark PG + Chroma pipeline."
    canonical = f"{jp1}\n\n{jp2}\n\n{jp3}"

    jira_ev = _fake_evidence(
        source_type=EvidenceSourceType.JIRA.value,
        category="jira_issue",
        title="[NEX-142] Migrate Chroma search to hybrid RRF",
        source_external_id="jira:cloud-1:issue:10042",
        extracted_text=canonical,
        author="Maya Lin",
        metadata_json={
            "jira_item_type": "issue",
            "jira_issue_key": "NEX-142",
            "project_key": "NEX",
        },
        pages=[
            (1, jp1, False, {"section": "jira_issue_summary"}),
            (2, jp2, False, {"section": "jira_issue_comments"}),
            (3, jp3, False, {"section": "jira_activity_and_worklogs"}),
        ],
    )

    chunks = service.chunk_evidence(jira_ev)
    chunk_types = [c.chunk_type for c in chunks]
    assert EvidenceChunkType.ISSUE_BODY.value in chunk_types
    assert EvidenceChunkType.ISSUE_HIERARCHY.value in chunk_types
    assert EvidenceChunkType.ISSUE_ACTIVITY.value in chunk_types
    comment_chunks = [c for c in chunks if c.chunk_type == EvidenceChunkType.ISSUE_COMMENT.value]
    assert len(comment_chunks) == 2
    assert comment_chunks[0].source_author_identity == "Maya Lin"
    assert comment_chunks[1].source_author_identity == "Owen Park"
    assert "nex-142" in chunks[0].search_identifier_text.lower()
