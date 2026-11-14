"""Strict read-only GitHub REST API v3 client for delegated discovery and evidence sync."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings
from app.schemas.integrations import GitHubRepositoryCandidate
from app.services.integrations.errors import IntegrationProviderError
from app.services.integrations.http_utils import (
    create_integration_http_client,
    is_rate_limit_response,
    parse_provider_datetime,
    raise_for_provider_error,
)

_NEXT_LINK_RE = re.compile(r'<[^>]+>;\s*rel="next"')

_DOC_PATH_KEYWORDS = (
    "readme",
    "architecture",
    "adr",
    "design",
    "decision",
    "runbook",
    "playbook",
    "onboarding",
    "handover",
    "changelog",
    "contributing",
    "docs/",
    "doc/",
)
_DOC_EXTENSIONS = (".md", ".mdx", ".rst", ".txt", ".adoc")
_CODE_EXTENSIONS = (
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".sql",
    ".sh",
    ".html",
    ".css",
    ".go",
    ".rs",
    ".java",
)
_MAX_DOC_FILE_BYTES = 200 * 1024

_EXCLUDED_PATH_DIRS = frozenset(
    {
        "node_modules",
        "dist",
        "build",
        "vendor",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "target",
        "coverage",
        ".next",
        "get-shit-done",
        ".turbo",
        ".idea",
        ".vscode",
    }
)
_EXCLUDED_BINARY_OR_GENERATED_SUFFIXES = (
    ".min.js",
    ".min.css",
    ".map",
    ".lock",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".pyc",
    ".pyo",
    ".class",
    ".jar",
    ".bin",
)
_EXCLUDED_LOCKFILE_NAMES = frozenset(
    {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "cargo.lock",
        "composer.lock",
        "pipfile.lock",
        "uv.lock",
        "gemfile.lock",
    }
)


def is_excluded_binary_or_generated_path(path: str) -> bool:
    """Return True when a repository path targets binary, minified, lockfile, or vendor files."""
    normalized = path.replace("\\", "/").strip().strip("/").lower()
    if not normalized:
        return True
    parts = [part for part in normalized.split("/") if part]
    if any(part in _EXCLUDED_PATH_DIRS for part in parts[:-1]):
        return True
    basename = parts[-1] if parts else normalized
    if basename in _EXCLUDED_LOCKFILE_NAMES:
        return True
    if normalized.endswith(_EXCLUDED_BINARY_OR_GENERATED_SUFFIXES):
        return True
    return False


@dataclass(frozen=True, slots=True)
class GitHubPaginatedResult:
    """Bounded collection response supporting ETag 304 checks and pagination metadata."""

    items: list[dict[str, Any]]
    etag: str | None = None
    not_modified: bool = False
    warnings: list[str] = field(default_factory=list)


def _has_next_link(link_header: str | None) -> bool:
    if not link_header:
        return False
    return bool(_NEXT_LINK_RE.search(link_header))


def _repo_candidate_from_json(raw: dict[str, Any]) -> GitHubRepositoryCandidate:
    raw_owner = raw.get("owner")
    owner_obj: dict[str, Any] = raw_owner if isinstance(raw_owner, dict) else {}
    raw_perms = raw.get("permissions")
    perms_obj: dict[str, Any] = raw_perms if isinstance(raw_perms, dict) else {}
    is_private = bool(raw.get("private", True))
    raw_visibility = str(raw.get("visibility") or ("private" if is_private else "public"))
    return GitHubRepositoryCandidate(
        external_resource_id=str(raw.get("id") or ""),
        full_name=str(raw.get("full_name") or ""),
        name=str(raw.get("name") or ""),
        owner_login=str(owner_obj.get("login") or ""),
        description=str(raw["description"]) if raw.get("description") else None,
        default_branch=str(raw["default_branch"]) if raw.get("default_branch") else None,
        visibility=raw_visibility.lower(),
        is_private=is_private,
        html_url=str(raw["html_url"]) if raw.get("html_url") else None,
        updated_at=parse_provider_datetime(
            str(raw["updated_at"]) if raw.get("updated_at") else None
        ),
        permissions={str(k): bool(v) for k, v in perms_obj.items()},
    )


def _is_candidate_doc_path(path: str, include_code: bool = False) -> bool:
    if is_excluded_binary_or_generated_path(path):
        return False
    lowered = path.lower().strip("/")
    parts = [p for p in lowered.split("/") if p]
    if any(p in _EXCLUDED_PATH_DIRS for p in parts):
        return False
    basename = parts[-1] if parts else lowered
    if basename in {"dockerfile", "makefile", "procfile", "caddyfile"}:
        return include_code
    if lowered.endswith(_DOC_EXTENSIONS):
        if not include_code and lowered.count("/") == 0:
            return any(kw in lowered for kw in _DOC_PATH_KEYWORDS)
        return True
    if include_code and lowered.endswith(_CODE_EXTENSIONS):
        return True
    return False


class GitHubClient:
    """Delegated read-only GitHub REST API wrapper."""

    def __init__(
        self,
        *,
        settings: Settings,
        transport: Any = None,
    ) -> None:
        self._gh = settings.integrations.github
        self._timeout = settings.integrations.http_timeout_seconds
        self._transport = transport

    def _headers(self, access_token: str, *, etag: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "IPKRH-Platform/0.1",
        }
        if etag:
            headers["If-None-Match"] = etag
        return headers

    def _base(self) -> str:
        return self._gh.api_base_url.rstrip("/")

    def list_repositories(
        self,
        *,
        access_token: str,
        page: int = 1,
        per_page: int = 30,
    ) -> tuple[list[GitHubRepositoryCandidate], bool]:
        """List explicitly accessible repositories for the calling authenticated user."""
        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            resp = client.get(
                f"{self._base()}/user/repos",
                headers=self._headers(access_token),
                params={
                    "page": page,
                    "per_page": per_page,
                    "sort": "updated",
                    "direction": "desc",
                    "affiliation": "owner,collaborator,organization_member",
                },
            )
            raise_for_provider_error(resp, provider="github", endpoint_label="list_repositories")
            raw_list = resp.json()
            candidates: list[GitHubRepositoryCandidate] = []
            if isinstance(raw_list, list):
                for entry in raw_list:
                    if isinstance(entry, dict) and entry.get("id") and entry.get("full_name"):
                        candidates.append(_repo_candidate_from_json(entry))
            has_next = _has_next_link(resp.headers.get("link")) or (len(candidates) == per_page)
            return candidates, has_next

    def verify_repository_access(
        self,
        *,
        access_token: str,
        owner: str,
        repo: str,
    ) -> tuple[bool, GitHubRepositoryCandidate | None]:
        """Verify whether the caller's delegated token can inspect `{owner}/{repo}`."""
        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            resp = client.get(
                f"{self._base()}/repos/{owner}/{repo}",
                headers=self._headers(access_token),
            )
            if resp.status_code == 200:
                payload = resp.json()
                if isinstance(payload, dict) and payload.get("id"):
                    return True, _repo_candidate_from_json(payload)
                return False, None
            if resp.status_code in {403, 404} and not is_rate_limit_response(resp):
                return False, None
            raise_for_provider_error(resp, provider="github", endpoint_label="get_repository")
            return False, None  # pragma: no cover

    def get_repository(
        self,
        *,
        access_token: str,
        owner: str,
        repo: str,
    ) -> GitHubRepositoryCandidate:
        """Fetch repository metadata or raise typed IntegrationProviderError."""
        allowed, candidate = self.verify_repository_access(
            access_token=access_token,
            owner=owner,
            repo=repo,
        )
        if not allowed or candidate is None:
            raise IntegrationProviderError(
                provider="github",
                code="GITHUB_REPO_INACCESSIBLE",
                message=(
                    f"GitHub repository '{owner}/{repo}' does not exist or caller lacks access."
                ),
                status_code=403,
                retryable=False,
            )
        return candidate

    def fetch_issues_and_prs(
        self,
        *,
        access_token: str,
        owner: str,
        repo: str,
        since: str | None = None,
        etag: str | None = None,
        max_items: int = 100,
    ) -> GitHubPaginatedResult:
        """Fetch repository issues and pull requests with ETag & incremental `since` support."""
        collected: list[dict[str, Any]] = []
        warnings: list[str] = []
        first_etag: str | None = etag
        page = 1
        per_page = min(100, max(1, max_items))

        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            while len(collected) < max_items:
                params: dict[str, Any] = {
                    "state": "all",
                    "sort": "updated",
                    "direction": "asc" if since else "desc",
                    "per_page": min(per_page, max_items - len(collected)),
                    "page": page,
                }
                if since:
                    params["since"] = since
                resp = client.get(
                    f"{self._base()}/repos/{owner}/{repo}/issues",
                    headers=self._headers(
                        access_token,
                        etag=etag if page == 1 else None,
                    ),
                    params=params,
                )
                if page == 1 and resp.status_code == 304:
                    return GitHubPaginatedResult(
                        items=[],
                        etag=resp.headers.get("etag") or etag,
                        not_modified=True,
                    )
                if resp.status_code in {403, 404} and not is_rate_limit_response(resp):
                    warnings.append(
                        f"GitHub issues endpoint returned HTTP {resp.status_code}; "
                        "issue ingestion skipped or restricted."
                    )
                    break
                raise_for_provider_error(resp, provider="github", endpoint_label="list_issues")
                if page == 1 and resp.headers.get("etag"):
                    first_etag = resp.headers.get("etag")
                batch = resp.json()
                if not isinstance(batch, list) or not batch:
                    break
                for item in batch:
                    if isinstance(item, dict):
                        collected.append(item)
                if not _has_next_link(resp.headers.get("link")) and len(batch) < params["per_page"]:
                    break
                if len(batch) < params["per_page"]:
                    break
                page += 1
        return GitHubPaginatedResult(
            items=collected[:max_items],
            etag=first_etag,
            warnings=warnings,
        )

    def fetch_issue_comments(
        self,
        *,
        access_token: str,
        owner: str,
        repo: str,
        issue_number: int,
        max_items: int = 50,
    ) -> tuple[list[dict[str, Any]], str | None]:
        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            resp = client.get(
                f"{self._base()}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                headers=self._headers(access_token),
                params={"per_page": min(100, max_items), "page": 1},
            )
            if resp.status_code in {403, 404} and not is_rate_limit_response(resp):
                return [], f"Issue #{issue_number} comments restricted (HTTP {resp.status_code})."
            raise_for_provider_error(resp, provider="github", endpoint_label="issue_comments")
            payload = resp.json()
            items = [x for x in payload if isinstance(x, dict)] if isinstance(payload, list) else []
            return items[:max_items], None

    def fetch_pull_request_bundle(
        self,
        *,
        access_token: str,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> tuple[
        dict[str, Any],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[str],
    ]:
        """Fetch PR detail, reviews, inline review comments, and changed file metadata."""
        warnings: list[str] = []
        pr_detail: dict[str, Any] = {}
        reviews: list[dict[str, Any]] = []
        review_comments: list[dict[str, Any]] = []
        files: list[dict[str, Any]] = []

        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            headers = self._headers(access_token)
            detail_resp = client.get(
                f"{self._base()}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=headers,
            )
            if detail_resp.status_code == 200 and isinstance(detail_resp.json(), dict):
                pr_detail = detail_resp.json()
            elif detail_resp.status_code in {403, 404} and not is_rate_limit_response(detail_resp):
                warnings.append(
                    f"PR #{pr_number} details unavailable (HTTP {detail_resp.status_code})."
                )
            else:
                raise_for_provider_error(detail_resp, provider="github", endpoint_label="pr_detail")

            for sub_label, url_path, target in (
                ("reviews", f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews", reviews),
                (
                    "review_comments",
                    f"/repos/{owner}/{repo}/pulls/{pr_number}/comments",
                    review_comments,
                ),
                ("files", f"/repos/{owner}/{repo}/pulls/{pr_number}/files", files),
            ):
                sub_resp = client.get(
                    f"{self._base()}{url_path}",
                    headers=headers,
                    params={"per_page": 100, "page": 1},
                )
                if sub_resp.status_code == 200 and isinstance(sub_resp.json(), list):
                    target.extend(x for x in sub_resp.json() if isinstance(x, dict))
                elif sub_resp.status_code in {403, 404} and not is_rate_limit_response(sub_resp):
                    warnings.append(
                        f"PR #{pr_number} {sub_label} restricted (HTTP {sub_resp.status_code})."
                    )
                else:
                    raise_for_provider_error(
                        sub_resp,
                        provider="github",
                        endpoint_label=f"pr_{sub_label}",
                    )
        return pr_detail, reviews, review_comments, files, warnings

    def fetch_commits(
        self,
        *,
        access_token: str,
        owner: str,
        repo: str,
        sha: str | None = None,
        since: str | None = None,
        etag: str | None = None,
        max_items: int = 50,
    ) -> GitHubPaginatedResult:
        """Fetch bounded repository commit history metadata (never clones git repo)."""
        collected: list[dict[str, Any]] = []
        warnings: list[str] = []
        first_etag: str | None = etag
        page = 1
        per_page = min(100, max(1, max_items))

        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            while len(collected) < max_items:
                params: dict[str, Any] = {
                    "per_page": min(per_page, max_items - len(collected)),
                    "page": page,
                }
                if sha:
                    params["sha"] = sha
                if since:
                    params["since"] = since
                resp = client.get(
                    f"{self._base()}/repos/{owner}/{repo}/commits",
                    headers=self._headers(access_token, etag=etag if page == 1 else None),
                    params=params,
                )
                if page == 1 and resp.status_code == 304:
                    return GitHubPaginatedResult(
                        items=[],
                        etag=resp.headers.get("etag") or etag,
                        not_modified=True,
                    )
                if resp.status_code == 409:
                    warnings.append("GitHub repository is empty (no commits yet).")
                    break
                if resp.status_code in {403, 404} and not is_rate_limit_response(resp):
                    warnings.append(
                        f"GitHub commits restricted or missing (HTTP {resp.status_code})."
                    )
                    break
                raise_for_provider_error(resp, provider="github", endpoint_label="list_commits")
                if page == 1 and resp.headers.get("etag"):
                    first_etag = resp.headers.get("etag")
                batch = resp.json()
                if not isinstance(batch, list) or not batch:
                    break
                collected.extend(x for x in batch if isinstance(x, dict))
                if not _has_next_link(resp.headers.get("link")) or len(batch) < params["per_page"]:
                    break
                page += 1
        return GitHubPaginatedResult(
            items=collected[:max_items],
            etag=first_etag,
            warnings=warnings,
        )

    def fetch_readme_and_docs(
        self,
        *,
        access_token: str,
        owner: str,
        repo: str,
        default_branch: str | None = None,
        max_docs: int = 20,
        include_code: bool = False,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Fetch README, documentation, and repository code files via read-only REST API."""
        docs: list[dict[str, Any]] = []
        warnings: list[str] = []
        seen_paths: set[str] = set()

        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            headers = self._headers(access_token)
            readme_resp = client.get(
                f"{self._base()}/repos/{owner}/{repo}/readme",
                headers=headers,
            )
            if readme_resp.status_code == 200 and isinstance(readme_resp.json(), dict):
                readme_obj = readme_resp.json()
                decoded = self._decode_content_payload(readme_obj)
                if decoded is not None:
                    path = str(readme_obj.get("path") or "README.md")
                    seen_paths.add(path.lower())
                    docs.append(
                        {
                            "path": path,
                            "sha": str(readme_obj.get("sha") or path),
                            "html_url": readme_obj.get("html_url"),
                            "size": int(readme_obj.get("size") or len(decoded)),
                            "text": decoded,
                        }
                    )
            elif readme_resp.status_code not in {404} and is_rate_limit_response(readme_resp):
                raise_for_provider_error(readme_resp, provider="github", endpoint_label="readme")

            if len(docs) >= max_docs:
                return docs, warnings

            tree_ref = default_branch or "HEAD"
            tree_resp = client.get(
                f"{self._base()}/repos/{owner}/{repo}/git/trees/{tree_ref}",
                headers=headers,
                params={"recursive": "1"},
            )
            if tree_resp.status_code == 200 and isinstance(tree_resp.json(), dict):
                tree_items = tree_resp.json().get("tree") or []
                candidate_paths = [
                    str(entry.get("path"))
                    for entry in tree_items
                    if isinstance(entry, dict)
                    and entry.get("type") == "blob"
                    and isinstance(entry.get("path"), str)
                    and int(entry.get("size") or 0) <= _MAX_DOC_FILE_BYTES
                    and _is_candidate_doc_path(str(entry["path"]), include_code=include_code)
                    and str(entry["path"]).lower() not in seen_paths
                ]

                def _path_priority(p: str) -> tuple[int, str]:
                    low = p.lower()
                    if "readme" in low:
                        return (0, p)
                    if any(kw in low for kw in ("architecture", "adr", "design", "decision", "handover", "onboarding")):
                        return (1, p)
                    if low.startswith("docs/") or "/docs/" in low:
                        return (2, p)
                    if "/src/" in low or low.startswith("src/"):
                        return (3, p)
                    if "/app/" in low or low.startswith("app/"):
                        return (4, p)
                    if "/lib/" in low or low.startswith("lib/"):
                        return (5, p)
                    if "test" in low:
                        return (7, p)
                    return (6, p)

                candidate_paths.sort(key=_path_priority)
                for path in candidate_paths[: max(0, max_docs - len(docs))]:
                    file_resp = client.get(
                        f"{self._base()}/repos/{owner}/{repo}/contents/{path}",
                        headers=headers,
                        params={"ref": tree_ref} if default_branch else None,
                    )
                    if file_resp.status_code == 200 and isinstance(file_resp.json(), dict):
                        file_obj = file_resp.json()
                        decoded = self._decode_content_payload(file_obj)
                        if decoded is not None:
                            seen_paths.add(path.lower())
                            docs.append(
                                {
                                    "path": path,
                                    "sha": str(file_obj.get("sha") or path),
                                    "html_url": file_obj.get("html_url"),
                                    "size": int(file_obj.get("size") or len(decoded)),
                                    "text": decoded,
                                }
                            )
                    elif file_resp.status_code in {403, 404} and not is_rate_limit_response(
                        file_resp
                    ):
                        warnings.append(
                            f"Documentation file '{path}' could not be read "
                            f"(HTTP {file_resp.status_code})."
                        )
                    else:
                        raise_for_provider_error(
                            file_resp,
                            provider="github",
                            endpoint_label="doc_file",
                        )
            elif is_rate_limit_response(tree_resp) or tree_resp.status_code >= 500:
                raise_for_provider_error(tree_resp, provider="github", endpoint_label="git_tree")

        return docs, warnings

    def fetch_discussions(
        self,
        *,
        access_token: str,
        owner: str,
        repo: str,
        max_items: int = 50,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Fetch repository discussions when enabled/supported without failing disabled repos."""
        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            resp = client.get(
                f"{self._base()}/repos/{owner}/{repo}/discussions",
                headers=self._headers(access_token),
                params={"per_page": min(100, max_items), "page": 1},
            )
            if resp.status_code == 200 and isinstance(resp.json(), list):
                items = [x for x in resp.json() if isinstance(x, dict)][:max_items]
                return items, []
            if resp.status_code in {403, 404, 410} and not is_rate_limit_response(resp):
                return [], [
                    f"GitHub discussions unavailable or disabled (HTTP {resp.status_code})."
                ]
            raise_for_provider_error(resp, provider="github", endpoint_label="discussions")
            return [], []

    @staticmethod
    def _decode_content_payload(payload: dict[str, Any]) -> str | None:
        raw_content = payload.get("content")
        encoding = str(payload.get("encoding") or "").lower()
        if not isinstance(raw_content, str):
            return None
        if encoding == "base64":
            try:
                decoded = base64.b64decode(raw_content.encode("ascii"), validate=False)
                if len(decoded) > _MAX_DOC_FILE_BYTES:
                    return None
                return decoded.decode("utf-8", errors="replace")
            except Exception:
                return None
        return raw_content[:_MAX_DOC_FILE_BYTES]
