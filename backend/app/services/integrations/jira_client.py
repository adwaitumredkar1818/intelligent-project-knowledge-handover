"""Read-only Atlassian Jira Cloud 3LO REST v3 client and ADF-to-text converter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings
from app.schemas.integrations import JiraProjectCandidate, JiraSiteCandidate
from app.services.integrations.errors import IntegrationProviderError
from app.services.integrations.http_utils import (
    create_integration_http_client,
    is_rate_limit_response,
    raise_for_provider_error,
)


def adf_to_text(node: Any, *, _indent: int = 0) -> str:
    """Convert Atlassian Document Format (ADF) JSON tree cleanly into readable Markdown/text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if not isinstance(node, dict):
        return str(node)

    node_type = str(node.get("type") or "")
    raw_attrs = node.get("attrs")
    attrs: dict[str, Any] = raw_attrs if isinstance(raw_attrs, dict) else {}
    raw_content = node.get("content")
    content: list[Any] = raw_content if isinstance(raw_content, list) else []

    if node_type == "text":
        return str(node.get("text") or "")
    if node_type == "hardBreak":
        return "\n"
    if node_type == "rule":
        return "\n---\n"
    if node_type == "mention":
        mention_text = attrs.get("text") or attrs.get("id") or "user"
        return str(mention_text)
    if node_type in {"inlineCard", "blockCard", "embedCard"}:
        url = attrs.get("url")
        return str(url) if url else ""
    if node_type == "emoji":
        return str(attrs.get("shortName") or attrs.get("text") or "")

    child_parts = [adf_to_text(child, _indent=_indent) for child in content]
    joined = "".join(child_parts)

    if node_type == "paragraph":
        return joined.strip() + "\n\n"
    if node_type == "heading":
        level = int(attrs.get("level") or 1)
        hashes = "#" * max(1, min(6, level))
        return f"{hashes} {joined.strip()}\n\n"
    if node_type == "blockquote":
        lines = [f"> {line}" for line in joined.strip().splitlines() if line.strip()]
        return "\n".join(lines) + "\n\n" if lines else ""
    if node_type == "codeBlock":
        lang = str(attrs.get("language") or "")
        return f"```{lang}\n{joined.strip()}\n```\n\n"
    if node_type == "listItem":
        cleaned = joined.strip().replace("\n\n", "\n")
        return cleaned
    if node_type in {"bulletList", "orderedList"}:
        items_out: list[str] = []
        for idx, child in enumerate(content, start=1):
            item_txt = adf_to_text(child, _indent=_indent + 1).strip()
            if item_txt:
                prefix = f"{idx}. " if node_type == "orderedList" else "- "
                items_out.append(f"{'  ' * _indent}{prefix}{item_txt}")
        return ("\n".join(items_out) + "\n\n") if items_out else ""
    if node_type in {"table", "tableRow", "tableCell", "tableHeader"}:
        if node_type == "tableRow":
            cells = [adf_to_text(child).strip() for child in content]
            return " | ".join(c for c in cells if c) + "\n"
        return "".join(adf_to_text(child) for child in content)

    return joined


@dataclass(frozen=True, slots=True)
class JiraProjectSearchResult:
    """Paginated Jira Cloud projects response."""

    projects: list[JiraProjectCandidate]
    start_at: int
    max_results: int
    total: int
    is_last: bool


@dataclass(frozen=True, slots=True)
class JiraIssueSearchResult:
    """Paginated JQL issue search response with optional changelog expansion."""

    issues: list[dict[str, Any]]
    total: int
    next_page_token: str | None = None
    warnings: list[str] = field(default_factory=list)


class JiraClient:
    """Delegated read-only Jira Cloud REST v3 wrapper routed through api.atlassian.com."""

    def __init__(
        self,
        *,
        settings: Settings,
        transport: Any = None,
    ) -> None:
        self._jira = settings.integrations.jira
        self._timeout = settings.integrations.http_timeout_seconds
        self._transport = transport

    def _base(self) -> str:
        return self._jira.api_base_url.rstrip("/")

    def _site_base(self, cloud_id: str) -> str:
        return f"{self._base()}/ex/jira/{cloud_id}/rest/api/3"

    @staticmethod
    def _headers(access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": "IPKRH-Platform/0.1",
        }

    def list_accessible_sites(self, *, access_token: str) -> list[JiraSiteCandidate]:
        """Discover Jira Cloud site `cloud_id` values authorised for this OAuth token."""
        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            resp = client.get(
                f"{self._base()}/oauth/token/accessible-resources",
                headers=self._headers(access_token),
            )
            raise_for_provider_error(resp, provider="jira", endpoint_label="accessible_resources")
            raw = resp.json()
            sites: list[JiraSiteCandidate] = []
            if isinstance(raw, list):
                for entry in raw:
                    if isinstance(entry, dict) and entry.get("id"):
                        sites.append(
                            JiraSiteCandidate(
                                cloud_id=str(entry["id"]),
                                name=str(entry.get("name") or entry["id"]),
                                url=str(entry["url"]) if entry.get("url") else None,
                                scopes=[str(s) for s in (entry.get("scopes") or [])],
                                avatar_url=(
                                    str(entry["avatarUrl"]) if entry.get("avatarUrl") else None
                                ),
                            )
                        )
            return sites

    def search_projects(
        self,
        *,
        access_token: str,
        cloud_id: str,
        start_at: int = 0,
        max_results: int = 50,
        query: str | None = None,
    ) -> JiraProjectSearchResult:
        """Fetch paginated Jira projects inside one authorised Jira Cloud site."""
        params: dict[str, Any] = {
            "startAt": max(0, start_at),
            "maxResults": min(100, max(1, max_results)),
            "expand": "description,lead,url",
        }
        if query and query.strip():
            params["query"] = query.strip()

        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            resp = client.get(
                f"{self._site_base(cloud_id)}/project/search",
                headers=self._headers(access_token),
                params=params,
            )
            raise_for_provider_error(resp, provider="jira", endpoint_label="project_search")
            payload = resp.json()
            values = payload.get("values") if isinstance(payload.get("values"), list) else []
            projects: list[JiraProjectCandidate] = []
            for entry in values:
                if isinstance(entry, dict) and entry.get("id") and entry.get("key"):
                    projects.append(
                        JiraProjectCandidate(
                            cloud_id=cloud_id,
                            external_resource_id=str(entry["id"]),
                            key=str(entry["key"]),
                            name=str(entry.get("name") or entry["key"]),
                            project_type_key=(
                                str(entry["projectTypeKey"])
                                if entry.get("projectTypeKey")
                                else None
                            ),
                            url=str(entry["self"]) if entry.get("self") else None,
                            is_private=(
                                bool(entry["isPrivate"])
                                if entry.get("isPrivate") is not None
                                else None
                            ),
                            style=str(entry["style"]) if entry.get("style") else None,
                            metadata_json={
                                "simplified": bool(entry.get("simplified", False)),
                            },
                        )
                    )
            return JiraProjectSearchResult(
                projects=projects,
                start_at=int(payload.get("startAt") or start_at),
                max_results=int(payload.get("maxResults") or max_results),
                total=int(payload.get("total") or len(projects)),
                is_last=bool(payload.get("isLast", True)),
            )

    def verify_project_access(
        self,
        *,
        access_token: str,
        cloud_id: str,
        project_key_or_id: str,
    ) -> tuple[bool, JiraProjectCandidate | None]:
        """Verify whether caller's delegated Jira token can inspect `{cloud_id}/{project_key}`."""
        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            resp = client.get(
                f"{self._site_base(cloud_id)}/project/{project_key_or_id}",
                headers=self._headers(access_token),
            )
            if resp.status_code == 200 and isinstance(resp.json(), dict):
                entry = resp.json()
                return True, JiraProjectCandidate(
                    cloud_id=cloud_id,
                    external_resource_id=str(entry.get("id") or project_key_or_id),
                    key=str(entry.get("key") or project_key_or_id),
                    name=str(entry.get("name") or project_key_or_id),
                    project_type_key=(
                        str(entry["projectTypeKey"]) if entry.get("projectTypeKey") else None
                    ),
                    url=str(entry["self"]) if entry.get("self") else None,
                    is_private=(
                        bool(entry["isPrivate"]) if entry.get("isPrivate") is not None else None
                    ),
                    style=str(entry["style"]) if entry.get("style") else None,
                    metadata_json={"simplified": bool(entry.get("simplified", False))},
                )
            if resp.status_code in {403, 404} and not is_rate_limit_response(resp):
                return False, None
            raise_for_provider_error(resp, provider="jira", endpoint_label="get_project")
            return False, None  # pragma: no cover

    def get_project(
        self,
        *,
        access_token: str,
        cloud_id: str,
        project_key_or_id: str,
    ) -> JiraProjectCandidate:
        allowed, candidate = self.verify_project_access(
            access_token=access_token,
            cloud_id=cloud_id,
            project_key_or_id=project_key_or_id,
        )
        if not allowed or candidate is None:
            raise IntegrationProviderError(
                provider="jira",
                code="JIRA_PROJECT_INACCESSIBLE",
                message=(
                    f"Jira project '{project_key_or_id}' on site '{cloud_id}' "
                    "does not exist or caller lacks access."
                ),
                status_code=403,
                retryable=False,
            )
        return candidate

    def verify_issue_access(
        self,
        *,
        access_token: str,
        cloud_id: str,
        issue_key: str,
    ) -> bool:
        """Verify caller's access to a security-restricted Jira issue via their own token."""
        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            resp = client.get(
                f"{self._site_base(cloud_id)}/issue/{issue_key}",
                headers=self._headers(access_token),
                params={"fields": "key,security"},
            )
            if resp.status_code == 200:
                return True
            if resp.status_code in {403, 404} and not is_rate_limit_response(resp):
                return False
            raise_for_provider_error(resp, provider="jira", endpoint_label="verify_issue_access")
            return False  # pragma: no cover

    def search_issues(
        self,
        *,
        access_token: str,
        cloud_id: str,
        jql: str,
        max_items: int = 100,
    ) -> JiraIssueSearchResult:
        """Fetch Jira issues with fields and changelog across bounded JQL pagination."""
        issues: list[dict[str, Any]] = []
        warnings: list[str] = []
        start_at = 0
        next_page_token: str | None = None
        total = 0

        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            while len(issues) < max_items:
                page_size = min(50, max_items - len(issues))
                params: dict[str, Any] = {
                    "jql": jql,
                    "maxResults": page_size,
                    "expand": "changelog",
                    "fields": (
                        "summary,description,issuetype,status,priority,assignee,reporter,"
                        "creator,labels,components,parent,issuelinks,resolution,"
                        "resolutiondate,created,updated,security,project"
                    ),
                }
                if next_page_token:
                    params["nextPageToken"] = next_page_token
                else:
                    params["startAt"] = start_at

                resp = client.get(
                    f"{self._site_base(cloud_id)}/search",
                    headers=self._headers(access_token),
                    params=params,
                )
                if resp.status_code in {403, 404} and not is_rate_limit_response(resp):
                    raise IntegrationProviderError(
                        provider="jira",
                        code="JIRA_PROJECT_SEARCH_INACCESSIBLE",
                        message=f"Jira issue search rejected with HTTP {resp.status_code}.",
                        status_code=resp.status_code,
                        retryable=False,
                    )
                raise_for_provider_error(resp, provider="jira", endpoint_label="search_issues")
                payload = resp.json()
                batch = payload.get("issues") if isinstance(payload.get("issues"), list) else []
                total = int(payload.get("total") or len(batch))
                for entry in batch:
                    if isinstance(entry, dict):
                        issues.append(entry)

                next_token_raw = payload.get("nextPageToken")
                if isinstance(next_token_raw, str) and next_token_raw:
                    next_page_token = next_token_raw
                    continue
                if payload.get("isLast") is True or not batch:
                    break
                start_at += len(batch)
                if start_at >= total or len(batch) < page_size:
                    break

        return JiraIssueSearchResult(issues=issues[:max_items], total=total, warnings=warnings)

    def fetch_issue_comments(
        self,
        *,
        access_token: str,
        cloud_id: str,
        issue_key: str,
        max_items: int = 50,
    ) -> tuple[list[dict[str, Any]], str | None]:
        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            resp = client.get(
                f"{self._site_base(cloud_id)}/issue/{issue_key}/comment",
                headers=self._headers(access_token),
                params={"startAt": 0, "maxResults": min(50, max_items)},
            )
            if resp.status_code in {403, 404} and not is_rate_limit_response(resp):
                return [], f"Issue {issue_key} comments restricted (HTTP {resp.status_code})."
            raise_for_provider_error(resp, provider="jira", endpoint_label="issue_comments")
            payload = resp.json()
            comments = (
                payload.get("comments") if isinstance(payload.get("comments"), list) else []
            )
            return [x for x in comments if isinstance(x, dict)][:max_items], None

    def fetch_issue_worklogs(
        self,
        *,
        access_token: str,
        cloud_id: str,
        issue_key: str,
        max_items: int = 30,
    ) -> tuple[list[dict[str, Any]], str | None]:
        with create_integration_http_client(
            timeout_seconds=self._timeout,
            transport=self._transport,
        ) as client:
            resp = client.get(
                f"{self._site_base(cloud_id)}/issue/{issue_key}/worklog",
                headers=self._headers(access_token),
                params={"startAt": 0, "maxResults": min(50, max_items)},
            )
            if resp.status_code in {403, 404} and not is_rate_limit_response(resp):
                return [], f"Issue {issue_key} worklogs restricted (HTTP {resp.status_code})."
            raise_for_provider_error(resp, provider="jira", endpoint_label="issue_worklogs")
            payload = resp.json()
            worklogs = (
                payload.get("worklogs") if isinstance(payload.get("worklogs"), list) else []
            )
            return [x for x in worklogs if isinstance(x, dict)][:max_items], None
