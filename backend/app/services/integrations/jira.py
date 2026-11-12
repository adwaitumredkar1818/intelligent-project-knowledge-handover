"""Jira source integration service for project discovery and issue sync pipelines."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.exceptions import BadRequestError
from app.services.integrations.github import DiscoveredEvidenceRecord

logger = logging.getLogger("app.integrations.jira")


@dataclass
class JiraProjectSummary:
    """Discovered Jira project."""

    id: str
    key: str
    name: str
    project_type_key: str
    lead_name: str | None


class JiraIntegrationService:
    """Handles Atlassian Jira Cloud API operations, project discovery, and issue sync."""

    def __init__(
        self,
        *,
        base_url: str,
        email: str | None = None,
        api_token: str | None = None,
        bearer_token: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "TheHandover-KnowledgeEngine/1.0",
        }
        if bearer_token:
            self._headers["Authorization"] = f"Bearer {bearer_token}"
            self._auth = None
        elif email and api_token:
            self._auth = httpx.BasicAuth(email, api_token)
        else:
            raise BadRequestError(
                "Either bearer_token or email+api_token must be provided for Jira.",
                code="INVALID_JIRA_AUTH",
            )

    def list_accessible_projects(self) -> list[JiraProjectSummary]:
        """Discover Jira projects accessible to the authenticated credentials."""
        try:
            with httpx.Client(timeout=15.0, auth=self._auth) as client:
                resp = client.get(
                    f"{self._base_url}/rest/api/3/project",
                    headers=self._headers,
                )
                if resp.status_code != 200:
                    raise BadRequestError(
                        f"Failed to query Jira projects: {resp.text[:200]}",
                        code="JIRA_API_ERROR",
                    )
                projects_data = resp.json()
                return [
                    JiraProjectSummary(
                        id=str(p["id"]),
                        key=p["key"],
                        name=p["name"],
                        project_type_key=p.get("projectTypeKey", "software"),
                        lead_name=p.get("lead", {}).get("displayName"),
                    )
                    for p in projects_data
                ]
        except httpx.RequestError as exc:
            raise BadRequestError(
                f"Network error communicating with Jira: {exc}",
                code="JIRA_CONNECTION_FAILED",
            ) from exc

    def sync_project_issues(
        self,
        project_key: str,
        max_results: int = 50,
    ) -> list[DiscoveredEvidenceRecord]:
        """Fetch issues, descriptions, assignees, and comments for a given Jira project."""
        records: list[DiscoveredEvidenceRecord] = []

        try:
            with httpx.Client(timeout=20.0, auth=self._auth) as client:
                # Query issues via Jira Search API using JQL
                jql = f"project = '{project_key}' ORDER BY updated DESC"
                resp = client.get(
                    f"{self._base_url}/rest/api/3/search",
                    headers=self._headers,
                    params={"jql": jql, "maxResults": max_results},
                )
                if resp.status_code != 200:
                    raise BadRequestError(
                        f"Jira search API returned error: {resp.text[:200]}",
                        code="JIRA_SEARCH_ERROR",
                    )
                issues_data = resp.json().get("issues", [])

                for issue in issues_data:
                    key = issue.get("key", "UNKNOWN")
                    fields = issue.get("fields", {})
                    summary = fields.get("summary", "No summary")
                    issuetype = fields.get("issuetype", {}).get("name", "Task")
                    status_name = fields.get("status", {}).get("name", "Open")
                    reporter = fields.get("reporter", {}).get("displayName", "Unknown")
                    assignee = fields.get("assignee", {}).get("displayName") or "Unassigned"
                    priority = fields.get("priority", {}).get("name", "Medium")

                    # Extract plain text from description (ADF or string)
                    desc_raw = fields.get("description")
                    desc_text = ""
                    if isinstance(desc_raw, str):
                        desc_text = desc_raw
                    elif isinstance(desc_raw, dict):
                        # Extract text nodes from ADF
                        desc_text = self._extract_adf_text(desc_raw)
                    else:
                        desc_text = "No description provided."

                    title = f"[{key}] {summary}"
                    raw_content = (
                        f"Issue: {key}\n"
                        f"Type: {issuetype}\n"
                        f"Status: {status_name}\n"
                        f"Priority: {priority}\n"
                        f"Reporter: {reporter}\n"
                        f"Assignee: {assignee}\n\n"
                        f"Description:\n{desc_text}"
                    )
                    content_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

                    created_str = fields.get("created")
                    dt = (
                        datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        if created_str
                        else datetime.now(UTC)
                    )

                    web_url = f"{self._base_url}/browse/{key}"

                    markdown = (
                        f"## [{key}] {summary}\n\n"
                        f"- **Type**: `{issuetype}`\n"
                        f"- **Status**: `{status_name}`\n"
                        f"- **Priority**: `{priority}`\n"
                        f"- **Assignee**: `{assignee}`\n"
                        f"- **Reporter**: `{reporter}`\n\n"
                        f"### Description\n{desc_text}"
                    )

                    records.append(
                        DiscoveredEvidenceRecord(
                            source_platform="jira",
                            source_provider="jira",
                            source_original_id=key,
                            source_url=web_url,
                            title=title,
                            author_name=reporter,
                            captured_at=dt,
                            content_hash=content_hash,
                            item_type="jira_issue",
                            raw_content=raw_content,
                            markdown_content=markdown,
                            attributes={
                                "issue_key": key,
                                "issue_type": issuetype,
                                "status": status_name,
                                "priority": priority,
                                "assignee": assignee,
                                "reporter": reporter,
                                "project_key": project_key,
                            },
                        )
                    )

        except httpx.RequestError as exc:
            logger.warning("Network failure during Jira sync: %s", exc)
            raise BadRequestError(
                f"Failed to complete Jira sync: {exc}",
                code="JIRA_SYNC_FAILED",
            ) from exc

        return records

    @staticmethod
    def _extract_adf_text(adf_dict: dict[str, Any]) -> str:
        """Helper to recursively extract text from Atlassian Document Format JSON."""
        texts: list[str] = []

        def _traverse(node: Any) -> None:
            if isinstance(node, dict):
                if node.get("type") == "text" and "text" in node:
                    texts.append(node["text"])
                for value in node.values():
                    _traverse(value)
            elif isinstance(node, list):
                for item in node:
                    _traverse(item)

        _traverse(adf_dict)
        return " ".join(texts)
