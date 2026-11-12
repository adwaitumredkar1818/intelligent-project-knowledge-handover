"""Format-aware deterministic evidence chunking and FTS identifier extraction."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.config import ChunkingSettings
from app.models.enums import EvidenceChunkType, EvidenceProcessingStatus, EvidenceSourceType
from app.models.evidence import EvidenceItem
from app.services.integrations.github_client import is_excluded_binary_or_generated_path

_HEADING_LINE_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_TABLE_LINE_RE = re.compile(r"^\s*\|.+\|\s*$")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

_GH_ISSUE_COMMENT_RE = re.compile(
    r"^##\s+Comment\s+\d+\s+by\s+@([^\s(]+)\s*(?:\(([^)]*)\))?\s*$",
    re.MULTILINE,
)
_JIRA_ISSUE_COMMENT_RE = re.compile(
    r"^###\s+Comment\s+\d+\s+by\s+(.+?)\s*\(([^)]*)\)\s*$",
    re.MULTILINE,
)
_GH_PR_REVIEW_LINE_RE = re.compile(
    r"^-\s+(?:Review|Discussion comment|Inline comment on `[^`]+`)\s+.*?by\s+@([^\s:]+)",
)

_TICKET_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9_]{1,15}-\d+)\b")
_FILE_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+")
_ISSUE_HASH_REF_RE = re.compile(r"(?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+|PR)?#(\d+)\b", re.IGNORECASE)
_COMMIT_SHA_RE = re.compile(r"\b([0-9a-f]{7,40})\b", re.IGNORECASE)
_COMPOUND_IDENT_RE = re.compile(r"\b[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)+\b")
_CAMEL_WORD_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\b)|\d+")


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    """In-memory structured chunk produced prior to canonical DB persistence & embedding."""

    chunk_index: int
    chunk_type: str
    section_title: str | None
    page_number: int | None
    char_start: int
    char_end: int
    char_count: int
    token_estimate: int
    chunk_text: str
    chunk_content_hash: str
    search_identifier_text: str
    source_author_identity: str | None
    source_created_at: datetime | None
    metadata_json: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _MarkdownBlock:
    kind: str  # "text" | "table"
    text: str
    section_title: str | None


def estimate_tokens(text: str) -> int:
    """Estimate token count using empirically measured nomic-embed-text ~3.2 chars/token."""
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, int(math.ceil(len(stripped) / 3.2)))


def compute_chunk_content_hash(
    *,
    chunk_type: str,
    section_title: str | None,
    page_number: int | None,
    source_author_identity: str | None,
    chunk_text: str,
) -> str:
    """Compute deterministic SHA-256 hash enabling unchanged-chunk skip/reindex detection."""
    payload = {
        "chunk_type": chunk_type,
        "section_title": section_title,
        "page_number": page_number,
        "source_author_identity": source_author_identity,
        "chunk_text": chunk_text,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def extract_fts_identifier_tokens(*values: str | None, max_tokens: int = 120) -> str:
    """Expand ticket IDs, file paths, SHAs, PR refs & snake/kebab symbols for PG FTS."""
    tokens: list[str] = []
    seen: set[str] = set()

    def _add(tok: str) -> None:
        cleaned = tok.strip().strip(",.;:()[]{}\"'`")
        if not cleaned or len(cleaned) > 120:
            return
        lowered = cleaned.lower()
        if lowered not in seen:
            seen.add(lowered)
            tokens.append(cleaned)

    for raw in values:
        if not raw:
            continue
        for match in _TICKET_KEY_RE.finditer(raw):
            key = match.group(1)
            _add(key)
            prefix, num = key.split("-", 1)
            _add(prefix)
            _add(num)

        for match in _FILE_PATH_RE.finditer(raw):
            path_val = match.group(0)
            _add(path_val)
            segments = [seg for seg in path_val.split("/") if seg]
            if segments:
                _add(segments[-1])
            for seg in segments:
                _add(seg)
                for sub in re.split(r"[._-]+", seg):
                    if len(sub) >= 2:
                        _add(sub)

        for match in _ISSUE_HASH_REF_RE.finditer(raw):
            _add(match.group(0))
            _add(match.group(1))
            _add(f"#{match.group(1)}")

        for match in _COMMIT_SHA_RE.finditer(raw):
            sha = match.group(1)
            _add(sha)
            if len(sha) > 8:
                _add(sha[:8])
            if len(sha) > 12:
                _add(sha[:12])

        for match in _COMPOUND_IDENT_RE.finditer(raw):
            ident = match.group(0)
            _add(ident)
            for part in re.split(r"[._-]+", ident):
                if len(part) >= 2:
                    _add(part)

        # Split CamelCase symbols (e.g. AuthMiddleware -> Auth, Middleware)
        for word_match in re.finditer(r"\b[A-Za-z][A-Za-z0-9]{3,}\b", raw):
            word = word_match.group(0)
            camel_parts = _CAMEL_WORD_RE.findall(word)
            if len(camel_parts) > 1:
                _add(word)
                for cp in camel_parts:
                    if len(cp) >= 2:
                        _add(cp)

        if len(tokens) >= max_tokens:
            break

    return " ".join(tokens[:max_tokens])


def _parse_iso_dt(raw: str | None) -> datetime | None:
    if not raw or not raw.strip():
        return None
    cleaned = raw.strip()
    if cleaned.endswith("Z"):
        cleaned = f"{cleaned[:-1]}+00:00"
    if len(cleaned) >= 5 and (cleaned[-5] in {"+", "-"}) and cleaned[-4:].isdigit():
        cleaned = f"{cleaned[:-2]}:{cleaned[-2:]}"
    try:
        parsed = datetime.fromisoformat(cleaned)
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


def _parse_markdown_units(
    text: str,
    *,
    initial_stack: list[tuple[int, str]] | None = None,
    default_section: str | None = None,
) -> tuple[list[_MarkdownBlock], list[tuple[int, str]]]:
    """Segment markdown/plain text into heading-scoped text and intact table units."""
    stack: list[tuple[int, str]] = list(initial_stack or [])
    units: list[_MarkdownBlock] = []
    lines = text.splitlines()
    buf: list[str] = []
    table_buf: list[str] = []
    in_code_fence = False

    def _current_section() -> str | None:
        if not stack:
            return default_section
        return " > ".join(title for _, title in stack[-3:])[:500]

    def _flush_text() -> None:
        content = "\n".join(buf).strip()
        buf.clear()
        if content:
            units.append(
                _MarkdownBlock(kind="text", text=content, section_title=_current_section())
            )

    def _flush_table() -> None:
        content = "\n".join(table_buf).strip()
        table_buf.clear()
        if content:
            units.append(
                _MarkdownBlock(kind="table", text=content, section_title=_current_section())
            )

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            if table_buf:
                _flush_table()
            buf.append(line)
            continue

        if not in_code_fence:
            heading_match = _HEADING_LINE_RE.match(line)
            if heading_match:
                _flush_table()
                _flush_text()
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, heading_text))
                buf.append(line)
                continue

            if _TABLE_LINE_RE.match(line):
                if buf:
                    # Keep short heading line attached immediately above the table if only heading
                    if len(buf) == 1 and _HEADING_LINE_RE.match(buf[0]):
                        table_buf.append(buf.pop(0))
                    else:
                        _flush_text()
                table_buf.append(line)
                continue

        if table_buf:
            _flush_table()
        buf.append(line)

    _flush_table()
    _flush_text()
    return units, stack


def _split_oversized_segment(text: str, *, max_chars: int, overlap_chars: int) -> list[str]:
    cleaned = text.strip()
    if len(cleaned) <= max_chars:
        return [cleaned] if cleaned else []

    out: list[str] = []
    start = 0
    total = len(cleaned)
    while start < total:
        end = min(total, start + max_chars)
        if end < total:
            # Prefer clean newline or whitespace cut inside the last 35% of window
            min_cut = start + int(max_chars * 0.65)
            cut = cleaned.rfind("\n", min_cut, end)
            if cut < min_cut:
                cut = cleaned.rfind(" ", min_cut, end)
            if cut >= min_cut:
                end = cut
        piece = cleaned[start:end].strip()
        if piece:
            out.append(piece)
        if end >= total:
            break
        next_start = max(start + 1, end - overlap_chars)
        # Advance next_start past any mid-word fragment
        if next_start > start:
            ws = cleaned.find(" ", next_start, end)
            if ws != -1 and ws < end - 20:
                next_start = ws + 1
        start = next_start
    return out


def _split_text_bounded(
    text: str,
    *,
    target_chars: int,
    max_chars: int,
    overlap_chars: int,
    min_chars: int,
) -> list[str]:
    """Split text cleanly along paragraph/line/sentence boundaries within char budgets."""
    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    # Break into atomic paragraphs / sentences <= target_chars
    raw_paras = [p.strip() for p in re.split(r"\n{2,}", cleaned) if p.strip()]
    atoms: list[str] = []
    for para in raw_paras:
        if len(para) <= max_chars:
            atoms.append(para)
            continue
        lines = [ln.strip() for ln in para.splitlines() if ln.strip()]
        if all(len(ln) <= max_chars for ln in lines) and len(lines) > 1:
            atoms.extend(lines)
            continue
        sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(para) if s.strip()]
        for sent in sentences:
            if len(sent) <= max_chars:
                atoms.append(sent)
            else:
                atoms.extend(
                    _split_oversized_segment(
                        sent,
                        max_chars=max_chars,
                        overlap_chars=overlap_chars,
                    )
                )

    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for atom in atoms:
        sep_len = 2 if current_parts else 0
        if current_parts and (current_len + sep_len + len(atom) > target_chars):
            chunk_str = "\n\n".join(current_parts).strip()
            chunks.append(chunk_str)
            # Carry bounded semantic overlap from tail if single atom <= target_chars
            if overlap_chars > 0:
                tail = chunk_str[-overlap_chars:].lstrip()
                ws = tail.find(" ")
                if ws != -1 and len(tail) - ws > 30:
                    tail = tail[ws + 1 :].strip()
                if tail and len(tail) + 2 + len(atom) <= max_chars:
                    current_parts = [tail, atom]
                    current_len = len(tail) + 2 + len(atom)
                    continue
            current_parts = [atom]
            current_len = len(atom)
        else:
            current_parts.append(atom)
            current_len += sep_len + len(atom)

    if current_parts:
        trailing = "\n\n".join(current_parts).strip()
        if (
            chunks
            and len(trailing) < min_chars
            and len(chunks[-1]) + 2 + len(trailing) <= max_chars
        ):
            chunks[-1] = f"{chunks[-1]}\n\n{trailing}".strip()
        else:
            chunks.append(trailing)

    return [c for c in chunks if c.strip()]


def _split_table_preserving_rows(table_text: str, *, max_chars: int) -> list[str]:
    """Keep tables intact <= max_chars; split large tables cleanly at row boundaries w/ header."""
    cleaned = table_text.strip()
    if len(cleaned) <= max_chars:
        return [cleaned] if cleaned else []

    lines = [ln for ln in cleaned.splitlines() if ln.strip()]
    header_lines: list[str] = []
    body_start = 0
    for idx, ln in enumerate(lines[:3]):
        if _TABLE_LINE_RE.match(ln):
            header_lines = [ln]
            if idx + 1 < len(lines) and set(lines[idx + 1].replace("|", "").strip()) <= set("-: "):
                header_lines.append(lines[idx + 1])
                body_start = idx + 2
            else:
                body_start = idx + 1
            break
    if not header_lines or body_start >= len(lines):
        return _split_text_bounded(
            cleaned,
            target_chars=max_chars,
            max_chars=max_chars,
            overlap_chars=0,
            min_chars=40,
        )

    header_prefix = "\n".join(header_lines)
    chunks: list[str] = []
    current = list(header_lines)
    current_len = len(header_prefix)

    for row in lines[body_start:]:
        if len(current) > len(header_lines) and current_len + 1 + len(row) > max_chars:
            chunks.append("\n".join(current))
            current = list(header_lines)
            current_len = len(header_prefix)
        current.append(row)
        current_len += 1 + len(row)

    if len(current) > len(header_lines):
        chunks.append("\n".join(current))
    return chunks


class ChunkingService:
    """Structure-aware chunker preserving citations, authors, tables & FTS identifiers."""

    def __init__(self, *, settings: ChunkingSettings) -> None:
        self._settings = settings

    def chunk_evidence(self, evidence: EvidenceItem) -> list[ChunkDraft]:
        """Split an extracted EvidenceItem into deterministic, citation-ready chunks."""
        if evidence.processing_status == EvidenceProcessingStatus.DELETED.value:
            return []
        if evidence.deleted_at is not None:
            return []

        canonical_text = (
            evidence.content.extracted_text if evidence.content is not None else ""
        )
        if not canonical_text.strip():
            return []

        pages = sorted(evidence.pages or [], key=lambda p: int(p.page_number))
        meta = dict(evidence.metadata_json or {})

        raw_specs: list[
            tuple[str, str | None, int | None, str, str | None, datetime | None, dict[str, Any]]
        ] = []

        if evidence.source_type == EvidenceSourceType.DOCUMENT_UPLOAD.value:
            if evidence.category == "docx_document":
                raw_specs = self._chunk_docx_pages(
                    evidence=evidence,
                    pages=pages,
                    canonical_text=canonical_text,
                )
            else:
                raw_specs = self._chunk_pdf_pages(
                    evidence=evidence,
                    pages=pages,
                    canonical_text=canonical_text,
                )
        elif evidence.source_type == EvidenceSourceType.GITHUB.value:
            raw_specs = self._chunk_github(
                evidence=evidence,
                pages=pages,
                canonical_text=canonical_text,
                meta=meta,
            )
        elif evidence.source_type == EvidenceSourceType.JIRA.value:
            raw_specs = self._chunk_jira(
                evidence=evidence,
                pages=pages,
                canonical_text=canonical_text,
                meta=meta,
            )
        else:
            raw_specs = self._chunk_markdown_generic(
                chunk_type=EvidenceChunkType.TEXT_SEGMENT.value,
                text=canonical_text,
                page_number=1,
                section_default=evidence.title,
                author_identity=evidence.source_author_identity,
                source_created_at=evidence.source_created_at,
                extra_meta={},
            )

        return self._finalize_drafts(
            evidence=evidence,
            canonical_text=canonical_text,
            raw_specs=raw_specs,
        )

    def _chunk_pdf_pages(
        self,
        *,
        evidence: EvidenceItem,
        pages: Sequence[Any],
        canonical_text: str,
    ) -> list[tuple[str, str | None, int | None, str, str | None, datetime | None, dict[str, Any]]]:
        if not pages:
            return self._chunk_markdown_generic(
                chunk_type=EvidenceChunkType.DOCUMENT_SECTION.value,
                text=canonical_text,
                page_number=1,
                section_default=evidence.title,
                author_identity=evidence.source_author_identity,
                source_created_at=evidence.source_created_at,
                extra_meta={},
            )

        specs: list[
            tuple[str, str | None, int | None, str, str | None, datetime | None, dict[str, Any]]
        ] = []
        heading_stack: list[tuple[int, str]] = []
        for page in pages:
            page_text = (page.text_content or "").strip()
            if not page_text:
                continue
            chunk_type = (
                EvidenceChunkType.OCR_PAGE.value
                if page.ocr_applied
                else EvidenceChunkType.DOCUMENT_SECTION.value
            )
            default_sec = f"Page {page.page_number}"
            units, heading_stack = _parse_markdown_units(
                page_text,
                initial_stack=heading_stack,
                default_section=default_sec,
            )
            for unit in units:
                sub_type = (
                    EvidenceChunkType.TABLE_SEGMENT.value
                    if unit.kind == "table"
                    else chunk_type
                )
                pieces = (
                    _split_table_preserving_rows(unit.text, max_chars=self._settings.max_chars)
                    if unit.kind == "table"
                    else _split_text_bounded(
                        unit.text,
                        target_chars=self._settings.target_chars,
                        max_chars=self._settings.max_chars,
                        overlap_chars=self._settings.overlap_chars,
                        min_chars=self._settings.min_chars,
                    )
                )
                for piece in pieces:
                    specs.append(
                        (
                            sub_type,
                            unit.section_title or default_sec,
                            int(page.page_number),
                            piece,
                            evidence.source_author_identity,
                            evidence.source_created_at,
                            {"ocr_applied": bool(page.ocr_applied)},
                        )
                    )
        return specs

    def _chunk_docx_pages(
        self,
        *,
        evidence: EvidenceItem,
        pages: Sequence[Any],
        canonical_text: str,
    ) -> list[tuple[str, str | None, int | None, str, str | None, datetime | None, dict[str, Any]]]:
        if not pages:
            return self._chunk_markdown_generic(
                chunk_type=EvidenceChunkType.DOCUMENT_SECTION.value,
                text=canonical_text,
                page_number=1,
                section_default=evidence.title,
                author_identity=evidence.source_author_identity,
                source_created_at=evidence.source_created_at,
                extra_meta={},
            )

        specs: list[
            tuple[str, str | None, int | None, str, str | None, datetime | None, dict[str, Any]]
        ] = []
        heading_stack: list[tuple[int, str]] = []
        for page in pages:
            sec_text = (page.text_content or "").strip()
            if not sec_text:
                continue
            default_sec = f"Section {page.page_number}"
            units, heading_stack = _parse_markdown_units(
                sec_text,
                initial_stack=heading_stack,
                default_section=default_sec,
            )
            for unit in units:
                if unit.kind == "table":
                    pieces = _split_table_preserving_rows(
                        unit.text,
                        max_chars=self._settings.max_chars,
                    )
                    for piece in pieces:
                        specs.append(
                            (
                                EvidenceChunkType.TABLE_SEGMENT.value,
                                unit.section_title or default_sec,
                                int(page.page_number),
                                piece,
                                evidence.source_author_identity,
                                evidence.source_created_at,
                                {"content_kind": "table"},
                            )
                        )
                else:
                    pieces = _split_text_bounded(
                        unit.text,
                        target_chars=self._settings.target_chars,
                        max_chars=self._settings.max_chars,
                        overlap_chars=self._settings.overlap_chars,
                        min_chars=self._settings.min_chars,
                    )
                    for piece in pieces:
                        specs.append(
                            (
                                EvidenceChunkType.DOCUMENT_SECTION.value,
                                unit.section_title or default_sec,
                                int(page.page_number),
                                piece,
                                evidence.source_author_identity,
                                evidence.source_created_at,
                                {},
                            )
                        )
        return specs

    def _chunk_github(
        self,
        *,
        evidence: EvidenceItem,
        pages: Sequence[Any],
        canonical_text: str,
        meta: dict[str, Any],
    ) -> list[tuple[str, str | None, int | None, str, str | None, datetime | None, dict[str, Any]]]:
        item_type = str(meta.get("github_item_type") or "").strip().lower()
        repo_name = str(meta.get("repository") or meta.get("full_name") or "").strip() or None

        if item_type == "documentation":
            doc_path = str(meta.get("path") or evidence.original_filename or "")
            if doc_path and is_excluded_binary_or_generated_path(doc_path):
                return []
            return self._chunk_markdown_generic(
                chunk_type=EvidenceChunkType.DOCUMENTATION.value,
                text=canonical_text,
                page_number=1,
                section_default=doc_path or evidence.title,
                author_identity=evidence.source_author_identity,
                source_created_at=evidence.source_created_at,
                extra_meta={"path": doc_path, "repository": repo_name} if doc_path else {},
            )

        if item_type == "commit":
            sha = str(meta.get("sha") or "").strip() or None
            extra: dict[str, Any] = {"github_item_type": "commit"}
            if sha:
                extra["sha"] = sha
            if repo_name:
                extra["repository"] = repo_name
            return self._chunk_markdown_generic(
                chunk_type=EvidenceChunkType.COMMIT_MESSAGE.value,
                text=canonical_text,
                page_number=1,
                section_default=f"Commit {sha[:8]}" if sha else evidence.title,
                author_identity=evidence.source_author_identity,
                source_created_at=evidence.source_created_at,
                extra_meta=extra,
            )

        if item_type == "repository":
            return self._chunk_markdown_generic(
                chunk_type=EvidenceChunkType.REPOSITORY_OVERVIEW.value,
                text=canonical_text,
                page_number=1,
                section_default=repo_name or evidence.title,
                author_identity=evidence.source_author_identity,
                source_created_at=evidence.source_created_at,
                extra_meta={"github_item_type": "repository"},
            )

        if item_type == "discussion":
            return self._chunk_markdown_generic(
                chunk_type=EvidenceChunkType.DISCUSSION_THREAD.value,
                text=canonical_text,
                page_number=1,
                section_default=evidence.title,
                author_identity=evidence.source_author_identity,
                source_created_at=evidence.source_created_at,
                extra_meta={"github_item_type": "discussion"},
            )

        specs: list[
            tuple[str, str | None, int | None, str, str | None, datetime | None, dict[str, Any]]
        ] = []
        base_meta: dict[str, Any] = {"github_item_type": item_type or "issue"}
        if repo_name:
            base_meta["repository"] = repo_name
        if meta.get("number") is not None:
            base_meta["number"] = meta["number"]

        for page in pages or ():
            sec_name = str((page.structured_metadata or {}).get("section") or "")
            p_text = (page.text_content or "").strip()
            if not p_text:
                continue
            p_num = int(page.page_number)

            if sec_name in {"issue_body", "pull_request_body"} or p_num == 1:
                c_type = (
                    EvidenceChunkType.PR_BODY.value
                    if item_type == "pull_request"
                    else EvidenceChunkType.ISSUE_BODY.value
                )
                specs.extend(
                    self._chunk_markdown_generic(
                        chunk_type=c_type,
                        text=p_text,
                        page_number=p_num,
                        section_default="Description",
                        author_identity=evidence.source_author_identity,
                        source_created_at=evidence.source_created_at,
                        extra_meta=base_meta,
                    )
                )
            elif sec_name == "issue_comments":
                matches = list(_GH_ISSUE_COMMENT_RE.finditer(p_text))
                if not matches:
                    specs.extend(
                        self._chunk_markdown_generic(
                            chunk_type=EvidenceChunkType.ISSUE_COMMENT.value,
                            text=p_text,
                            page_number=p_num,
                            section_default="Issue Comments",
                            author_identity=evidence.source_author_identity,
                            source_created_at=evidence.source_created_at,
                            extra_meta=base_meta,
                        )
                    )
                else:
                    for idx, m in enumerate(matches):
                        block_start = m.start()
                        block_end = (
                            matches[idx + 1].start() if idx + 1 < len(matches) else len(p_text)
                        )
                        comment_block = p_text[block_start:block_end].strip()
                        c_author = m.group(1).strip()
                        c_dt = _parse_iso_dt(m.group(2)) or evidence.source_created_at
                        for piece in _split_text_bounded(
                            comment_block,
                            target_chars=self._settings.target_chars,
                            max_chars=self._settings.max_chars,
                            overlap_chars=self._settings.overlap_chars,
                            min_chars=self._settings.min_chars,
                        ):
                            specs.append(
                                (
                                    EvidenceChunkType.ISSUE_COMMENT.value,
                                    f"Comment by @{c_author}",
                                    p_num,
                                    piece,
                                    c_author,
                                    c_dt,
                                    dict(base_meta),
                                )
                            )
            elif sec_name == "pull_request_reviews_and_comments":
                entries = [ln.strip() for ln in p_text.splitlines() if ln.strip()]
                # Skip leading "## Reviews & Comments" header when grouping by entry
                body_entries = [
                    ln for ln in entries if not ln.lower().startswith("## reviews & comments")
                ] or entries
                specs.extend(
                    self._chunk_pr_review_lines(
                        lines=body_entries,
                        page_number=p_num,
                        fallback_author=evidence.source_author_identity,
                        source_created_at=evidence.source_created_at,
                        base_meta=base_meta,
                    )
                )
            elif sec_name == "changed_files_metadata":
                kept_lines: list[str] = []
                for ln in p_text.splitlines():
                    stripped = ln.strip()
                    if stripped.startswith("- `") and "`" in stripped[3:]:
                        fname = stripped[3:].split("`", 1)[0]
                        if is_excluded_binary_or_generated_path(fname):
                            continue
                    kept_lines.append(ln)
                filtered_text = "\n".join(kept_lines).strip()
                if filtered_text and filtered_text != "## Changed Files Metadata":
                    specs.extend(
                        self._chunk_markdown_generic(
                            chunk_type=EvidenceChunkType.PR_CHANGED_FILES.value,
                            text=filtered_text,
                            page_number=p_num,
                            section_default="Changed Files",
                            author_identity=evidence.source_author_identity,
                            source_created_at=evidence.source_created_at,
                            extra_meta=base_meta,
                        )
                    )
            else:
                specs.extend(
                    self._chunk_markdown_generic(
                        chunk_type=EvidenceChunkType.TEXT_SEGMENT.value,
                        text=p_text,
                        page_number=p_num,
                        section_default=sec_name or evidence.title,
                        author_identity=evidence.source_author_identity,
                        source_created_at=evidence.source_created_at,
                        extra_meta=base_meta,
                    )
                )

        if not specs:
            return self._chunk_markdown_generic(
                chunk_type=EvidenceChunkType.TEXT_SEGMENT.value,
                text=canonical_text,
                page_number=1,
                section_default=evidence.title,
                author_identity=evidence.source_author_identity,
                source_created_at=evidence.source_created_at,
                extra_meta=base_meta,
            )
        return specs

    def _chunk_pr_review_lines(
        self,
        *,
        lines: list[str],
        page_number: int,
        fallback_author: str | None,
        source_created_at: datetime | None,
        base_meta: dict[str, Any],
    ) -> list[tuple[str, str | None, int | None, str, str | None, datetime | None, dict[str, Any]]]:
        specs: list[
            tuple[str, str | None, int | None, str, str | None, datetime | None, dict[str, Any]]
        ] = []
        current_group: list[str] = []
        current_authors: list[str] = []
        current_len = 0

        def _flush() -> None:
            if not current_group:
                return
            joined = "## Reviews & Comments\n" + "\n".join(current_group)
            unique_authors = list(dict.fromkeys(current_authors))
            resolved_author = unique_authors[0] if len(unique_authors) == 1 else fallback_author
            is_review = any(ln.startswith("- Review ") for ln in current_group)
            c_type = (
                EvidenceChunkType.PR_REVIEW.value
                if is_review
                else EvidenceChunkType.PR_COMMENT.value
            )
            for piece in _split_text_bounded(
                joined,
                target_chars=self._settings.target_chars,
                max_chars=self._settings.max_chars,
                overlap_chars=0,
                min_chars=60,
            ):
                specs.append(
                    (
                        c_type,
                        "Reviews & Comments",
                        page_number,
                        piece,
                        resolved_author,
                        source_created_at,
                        dict(base_meta),
                    )
                )
            current_group.clear()
            current_authors.clear()

        for ln in lines:
            if current_group and current_len + len(ln) + 1 > self._settings.target_chars:
                _flush()
                current_len = 0
            current_group.append(ln)
            current_len += len(ln) + 1
            m = _GH_PR_REVIEW_LINE_RE.match(ln)
            if m:
                current_authors.append(m.group(1))
        _flush()
        return specs

    def _chunk_jira(
        self,
        *,
        evidence: EvidenceItem,
        pages: Sequence[Any],
        canonical_text: str,
        meta: dict[str, Any],
    ) -> list[tuple[str, str | None, int | None, str, str | None, datetime | None, dict[str, Any]]]:
        item_type = str(meta.get("jira_item_type") or "").strip().lower()
        issue_key = str(meta.get("jira_issue_key") or "").strip() or None
        project_key = str(meta.get("project_key") or "").strip() or None

        if item_type == "project":
            return self._chunk_markdown_generic(
                chunk_type=EvidenceChunkType.JIRA_PROJECT.value,
                text=canonical_text,
                page_number=1,
                section_default=f"Jira Project {project_key}" if project_key else evidence.title,
                author_identity=evidence.source_author_identity,
                source_created_at=evidence.source_created_at,
                extra_meta={"jira_item_type": "project", "project_key": project_key},
            )

        base_meta: dict[str, Any] = {"jira_item_type": item_type or "issue"}
        if issue_key:
            base_meta["jira_issue_key"] = issue_key
        if project_key:
            base_meta["project_key"] = project_key

        specs: list[
            tuple[str, str | None, int | None, str, str | None, datetime | None, dict[str, Any]]
        ] = []
        for page in pages or ():
            sec_name = str((page.structured_metadata or {}).get("section") or "")
            p_text = (page.text_content or "").strip()
            if not p_text:
                continue
            p_num = int(page.page_number)

            if sec_name == "jira_issue_summary" or p_num == 1:
                if "## Issue Links & Hierarchy" in p_text:
                    before_links, links_part = p_text.split("## Issue Links & Hierarchy", 1)
                    if before_links.strip():
                        specs.extend(
                            self._chunk_markdown_generic(
                                chunk_type=EvidenceChunkType.ISSUE_BODY.value,
                                text=before_links.strip(),
                                page_number=p_num,
                                section_default=f"{issue_key} Description"
                                if issue_key
                                else "Summary & Description",
                                author_identity=evidence.source_author_identity,
                                source_created_at=evidence.source_created_at,
                                extra_meta=base_meta,
                            )
                        )
                    links_block = f"## Issue Links & Hierarchy{links_part}".strip()
                    specs.extend(
                        self._chunk_markdown_generic(
                            chunk_type=EvidenceChunkType.ISSUE_HIERARCHY.value,
                            text=links_block,
                            page_number=p_num,
                            section_default=f"{issue_key} Links & Hierarchy"
                            if issue_key
                            else "Issue Links & Hierarchy",
                            author_identity=evidence.source_author_identity,
                            source_created_at=evidence.source_created_at,
                            extra_meta=base_meta,
                        )
                    )
                else:
                    specs.extend(
                        self._chunk_markdown_generic(
                            chunk_type=EvidenceChunkType.ISSUE_BODY.value,
                            text=p_text,
                            page_number=p_num,
                            section_default=f"{issue_key} Description"
                            if issue_key
                            else "Summary & Description",
                            author_identity=evidence.source_author_identity,
                            source_created_at=evidence.source_created_at,
                            extra_meta=base_meta,
                        )
                    )
            elif sec_name == "jira_issue_comments":
                matches = list(_JIRA_ISSUE_COMMENT_RE.finditer(p_text))
                if not matches:
                    specs.extend(
                        self._chunk_markdown_generic(
                            chunk_type=EvidenceChunkType.ISSUE_COMMENT.value,
                            text=p_text,
                            page_number=p_num,
                            section_default=f"{issue_key} Comments" if issue_key else "Comments",
                            author_identity=evidence.source_author_identity,
                            source_created_at=evidence.source_created_at,
                            extra_meta=base_meta,
                        )
                    )
                else:
                    for idx, m in enumerate(matches):
                        block_start = m.start()
                        block_end = (
                            matches[idx + 1].start() if idx + 1 < len(matches) else len(p_text)
                        )
                        c_author = m.group(1).strip()
                        c_dt = _parse_iso_dt(m.group(2)) or evidence.source_created_at
                        block_body = p_text[block_start:block_end].strip()
                        sec_label = (
                            f"{issue_key} Comment by {c_author}"
                            if issue_key
                            else f"Comment by {c_author}"
                        )
                        for piece in _split_text_bounded(
                            block_body,
                            target_chars=self._settings.target_chars,
                            max_chars=self._settings.max_chars,
                            overlap_chars=self._settings.overlap_chars,
                            min_chars=self._settings.min_chars,
                        ):
                            specs.append(
                                (
                                    EvidenceChunkType.ISSUE_COMMENT.value,
                                    sec_label,
                                    p_num,
                                    piece,
                                    c_author,
                                    c_dt,
                                    dict(base_meta),
                                )
                            )
            elif sec_name == "jira_activity_and_worklogs":
                specs.extend(
                    self._chunk_markdown_generic(
                        chunk_type=EvidenceChunkType.ISSUE_ACTIVITY.value,
                        text=p_text,
                        page_number=p_num,
                        section_default=f"{issue_key} Activity & Worklogs"
                        if issue_key
                        else "Activity, Changelog & Worklogs",
                        author_identity=evidence.source_author_identity,
                        source_created_at=evidence.source_created_at,
                        extra_meta=base_meta,
                    )
                )
            else:
                specs.extend(
                    self._chunk_markdown_generic(
                        chunk_type=EvidenceChunkType.TEXT_SEGMENT.value,
                        text=p_text,
                        page_number=p_num,
                        section_default=sec_name or evidence.title,
                        author_identity=evidence.source_author_identity,
                        source_created_at=evidence.source_created_at,
                        extra_meta=base_meta,
                    )
                )

        if not specs:
            return self._chunk_markdown_generic(
                chunk_type=EvidenceChunkType.TEXT_SEGMENT.value,
                text=canonical_text,
                page_number=1,
                section_default=evidence.title,
                author_identity=evidence.source_author_identity,
                source_created_at=evidence.source_created_at,
                extra_meta=base_meta,
            )
        return specs

    def _chunk_markdown_generic(
        self,
        *,
        chunk_type: str,
        text: str,
        page_number: int | None,
        section_default: str | None,
        author_identity: str | None,
        source_created_at: datetime | None,
        extra_meta: dict[str, Any],
    ) -> list[tuple[str, str | None, int | None, str, str | None, datetime | None, dict[str, Any]]]:
        units, _ = _parse_markdown_units(text, default_section=section_default)
        specs: list[
            tuple[str, str | None, int | None, str, str | None, datetime | None, dict[str, Any]]
        ] = []
        for unit in units:
            if unit.kind == "table":
                pieces = _split_table_preserving_rows(
                    unit.text,
                    max_chars=self._settings.max_chars,
                )
                unit_type = EvidenceChunkType.TABLE_SEGMENT.value
            else:
                pieces = _split_text_bounded(
                    unit.text,
                    target_chars=self._settings.target_chars,
                    max_chars=self._settings.max_chars,
                    overlap_chars=self._settings.overlap_chars,
                    min_chars=self._settings.min_chars,
                )
                unit_type = chunk_type
            for piece in pieces:
                specs.append(
                    (
                        unit_type,
                        unit.section_title or section_default,
                        page_number,
                        piece,
                        author_identity,
                        source_created_at,
                        dict(extra_meta),
                    )
                )
        return specs

    def _finalize_drafts(
        self,
        *,
        evidence: EvidenceItem,
        canonical_text: str,
        raw_specs: list[
            tuple[str, str | None, int | None, str, str | None, datetime | None, dict[str, Any]]
        ],
    ) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        cursor = 0
        total_len = len(canonical_text)

        for _idx, (
            chunk_type,
            section_title,
            page_number,
            chunk_text,
            author_identity,
            src_created,
            extra_meta,
        ) in enumerate(raw_specs):
            cleaned_text = chunk_text.strip()
            if not cleaned_text:
                continue

            # Resolve monotonic char_start/char_end offsets cleanly against canonical extracted_text
            probe = cleaned_text[: min(96, len(cleaned_text))]
            found_at = canonical_text.find(probe, cursor)
            if found_at == -1:
                found_at = canonical_text.find(probe)
            if found_at != -1:
                char_start = found_at
                char_end = min(total_len, char_start + len(cleaned_text))
                cursor = max(cursor, char_start)
            else:
                char_start = min(cursor, total_len)
                char_end = min(total_len, char_start + len(cleaned_text))

            clean_section = section_title.strip()[:500] if section_title else None
            ident_text = extract_fts_identifier_tokens(
                cleaned_text,
                clean_section,
                evidence.title,
                evidence.original_filename,
                evidence.source_external_id,
            )
            chunk_hash = compute_chunk_content_hash(
                chunk_type=chunk_type,
                section_title=clean_section,
                page_number=page_number,
                source_author_identity=author_identity,
                chunk_text=cleaned_text,
            )
            chunk_meta: dict[str, Any] = {
                key: val for key, val in extra_meta.items() if val is not None
            }
            if clean_section:
                chunk_meta["section_title"] = clean_section
            if page_number is not None:
                chunk_meta["page_number"] = page_number
            if author_identity:
                chunk_meta["source_author_identity"] = author_identity

            drafts.append(
                ChunkDraft(
                    chunk_index=len(drafts),
                    chunk_type=chunk_type,
                    section_title=clean_section,
                    page_number=page_number,
                    char_start=char_start,
                    char_end=max(char_start, char_end),
                    char_count=len(cleaned_text),
                    token_estimate=estimate_tokens(cleaned_text),
                    chunk_text=cleaned_text,
                    chunk_content_hash=chunk_hash,
                    search_identifier_text=ident_text,
                    source_author_identity=author_identity[:255] if author_identity else None,
                    source_created_at=src_created,
                    metadata_json=chunk_meta,
                )
            )
        return drafts
