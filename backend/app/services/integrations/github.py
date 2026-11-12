"""GitHub source integration compatibility module for discovery and evidence sync pipelines."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.exceptions import BadRequestError

logger = logging.getLogger("app.integrations.github")


@dataclass
class GitHubRepoSummary:
    """Discovered GitHub repository."""

    id: int
    name: str
    full_name: str
    description: str | None
    html_url: str
    default_branch: str
    is_private: bool
    owner_login: str


@dataclass
class DiscoveredEvidenceRecord:
    """A normalised evidence record pulled from an external source."""

    source_platform: str
    source_provider: str
    source_original_id: str
    source_url: str | None
    title: str
    author_name: str | None
    captured_at: datetime
    content_hash: str
    item_type: str
    raw_content: str
    markdown_content: str
    attributes: dict[str, Any]


class GitHubIntegrationService:
    """Handles GitHub API operations, discovery, and sync extraction pipelines."""

    def __init__(self, token: str = "", base_url: str = "https://api.github.com") -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "TheHandover-KnowledgeEngine/1.0",
        }

    def list_accessible_repositories(self) -> list[GitHubRepoSummary]:
        """Discover repositories the user has authorized access to."""
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    f"{self._base_url}/user/repos?per_page=100&sort=updated",
                    headers=self._headers,
                )
                if resp.status_code != 200:
                    raise BadRequestError(
                        f"Failed to query GitHub repositories: {resp.text[:200]}",
                        code="GITHUB_API_ERROR",
                    )
                repos_data = resp.json()
                return [
                    GitHubRepoSummary(
                        id=r["id"],
                        name=r["name"],
                        full_name=r["full_name"],
                        description=r.get("description"),
                        html_url=r.get("html_url", ""),
                        default_branch=r.get("default_branch", "main"),
                        is_private=bool(r.get("private", False)),
                        owner_login=r.get("owner", {}).get("login", "unknown"),
                    )
                    for r in repos_data
                ]
        except httpx.RequestError as exc:
            raise BadRequestError(
                f"Network error communicating with GitHub: {exc}",
                code="GITHUB_CONNECTION_FAILED",
            ) from exc

    def sync_repository(
        self,
        full_name: str,
        limit_per_category: int = 50,
    ) -> list[DiscoveredEvidenceRecord]:
        """Fetch commits, pull requests, and issues from the repository into evidence records."""
        records: list[DiscoveredEvidenceRecord] = []

        try:
            with httpx.Client(timeout=20.0) as client:
                # 1. Fetch Pull Requests
                pr_resp = client.get(
                    f"{self._base_url}/repos/{full_name}/pulls?state=all&per_page={limit_per_category}",
                    headers=self._headers,
                )
                if pr_resp.status_code == 200:
                    for pr in pr_resp.json():
                        pr_body = pr.get("body") or "No description provided."
                        pr_num = pr.get("number")
                        title = f"PR #{pr_num}: {pr.get('title', 'Untitled PR')}"
                        pr_user = pr.get("user", {}).get("login")
                        pr_state = pr.get("state")
                        raw_text = f"{title}\nAuthor: {pr_user}\nState: {pr_state}\n\n{pr_body}"
                        h = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
                        created_str = pr.get("created_at")
                        dt = (
                            datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                            if created_str
                            else datetime.now(UTC)
                        )
                        is_merged = pr.get("merged_at") is not None
                        md_content = (
                            f"## {title}\n\n"
                            f"- **Author**: `{pr_user}`\n"
                            f"- **State**: `{pr_state}`\n"
                            f"- **Merged**: `{is_merged}`\n\n"
                            f"### Description\n{pr_body}"
                        )
                        records.append(
                            DiscoveredEvidenceRecord(
                                source_platform="github",
                                source_provider="github",
                                source_original_id=f"pr:{pr_num}",
                                source_url=pr.get("html_url"),
                                title=title,
                                author_name=pr_user,
                                captured_at=dt,
                                content_hash=h,
                                item_type="pull_request",
                                raw_content=raw_text,
                                markdown_content=md_content,
                                attributes={
                                    "pr_number": pr_num,
                                    "state": pr_state,
                                    "is_merged": is_merged,
                                    "merged_at": pr.get("merged_at"),
                                    "branch": pr.get("head", {}).get("ref"),
                                },
                            )
                        )

                # 2. Fetch Issues
                iss_resp = client.get(
                    f"{self._base_url}/repos/{full_name}/issues?state=all&per_page={limit_per_category}",
                    headers=self._headers,
                )
                if iss_resp.status_code == 200:
                    for iss in iss_resp.json():
                        if "pull_request" in iss:
                            continue
                        iss_body = iss.get("body") or "No description provided."
                        iss_num = iss.get("number")
                        title = f"Issue #{iss_num}: {iss.get('title', 'Untitled Issue')}"
                        iss_user = iss.get("user", {}).get("login")
                        iss_state = iss.get("state")
                        raw_text = f"{title}\nReporter: {iss_user}\nState: {iss_state}\n\n{iss_body}"
                        h = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
                        created_str = iss.get("created_at")
                        dt = (
                            datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                            if created_str
                            else datetime.now(UTC)
                        )
                        labels: list[str] = [
                            str(label["name"])
                            for label in iss.get("labels", [])
                            if isinstance(label, dict) and "name" in label
                        ]
                        lbl_str = ", ".join(labels) if labels else "None"
                        md_issue = (
                            f"## {title}\n\n"
                            f"- **Reporter**: `{iss_user}`\n"
                            f"- **State**: `{iss_state}`\n"
                            f"- **Labels**: {lbl_str}\n\n"
                            f"### Details\n{iss_body}"
                        )
                        records.append(
                            DiscoveredEvidenceRecord(
                                source_platform="github",
                                source_provider="github",
                                source_original_id=f"issue:{iss_num}",
                                source_url=iss.get("html_url"),
                                title=title,
                                author_name=iss_user,
                                captured_at=dt,
                                content_hash=h,
                                item_type="issue",
                                raw_content=raw_text,
                                markdown_content=md_issue,
                                attributes={
                                    "issue_number": iss_num,
                                    "state": iss_state,
                                    "labels": labels,
                                    "comments_count": iss.get("comments", 0),
                                },
                            )
                        )

                # 3. Fetch Recent Commits
                commits_resp = client.get(
                    f"{self._base_url}/repos/{full_name}/commits?per_page={limit_per_category}",
                    headers=self._headers,
                )
                if commits_resp.status_code == 200:
                    for c in commits_resp.json():
                        sha = c.get("sha", "")
                        short_sha = sha[:8]
                        commit_meta = c.get("commit", {})
                        message = commit_meta.get("message", "Commit")
                        first_line = message.split("\n")[0]
                        author = commit_meta.get("author", {}).get("name") or "Unknown"
                        raw_text = f"Commit {sha}\nAuthor: {author}\nMessage: {message}"
                        h = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
                        date_str = commit_meta.get("author", {}).get("date")
                        dt = (
                            datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            if date_str
                            else datetime.now(UTC)
                        )
                        records.append(
                            DiscoveredEvidenceRecord(
                                source_platform="github",
                                source_provider="github",
                                source_original_id=f"commit:{sha}",
                                source_url=c.get("html_url"),
                                title=f"Commit [{short_sha}]: {first_line}",
                                author_name=author,
                                captured_at=dt,
                                content_hash=h,
                                item_type="commit",
                                raw_content=raw_text,
                                markdown_content=(
                                    f"## Commit `{short_sha}`\n\n"
                                    f"- **Author**: `{author}`\n"
                                    f"- **Full SHA**: `{sha}`\n\n"
                                    f"### Commit Message\n```text\n{message}\n```"
                                ),
                                attributes={
                                    "sha": sha,
                                    "short_sha": short_sha,
                                    "committer": commit_meta.get("committer", {}).get("name"),
                                },
                            )
                        )

        except httpx.RequestError as exc:
            logger.warning("Network failure during GitHub sync: %s", exc)
            raise BadRequestError(
                f"Failed to complete GitHub sync: {exc}",
                code="GITHUB_SYNC_FAILED",
            ) from exc

        return records
