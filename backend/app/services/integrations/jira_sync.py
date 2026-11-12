"""Jira Cloud delegated sync orchestrator handling ADF, worklogs, links, and security levels."""

from __future__ import annotations

import uuid
from datetime import UTC
from typing import Any

from app.core.config import Settings
from app.core.security import utc_now
from app.models.enums import (
    ConnectorExtractionMethod,
    EvidenceCategory,
    EvidenceSourceType,
    PageExtractionOutcome,
    SourcePermissionVerificationStatus,
)
from app.models.integration import ProjectSourceMapping, SourceAccessPolicy
from app.repositories.integration import IntegrationRepository
from app.services.document_extraction import ExtractedPageData
from app.services.integrations.access_policy import SourceAccessPolicyService
from app.services.integrations.errors import IntegrationAuthError, IntegrationProviderError
from app.services.integrations.evidence_ingestor import (
    NormalizedSourceEvidence,
    SourceEvidenceIngestor,
)
from app.services.integrations.github_sync import SyncExecutionReport
from app.services.integrations.http_utils import parse_provider_datetime
from app.services.integrations.jira_client import JiraClient, adf_to_text


def _page(page_num: int, text: str, section_name: str) -> ExtractedPageData:
    cleaned = text.strip()
    return ExtractedPageData(
        page_number=page_num,
        text_content=cleaned,
        extraction_outcome=(
            PageExtractionOutcome.DIGITAL_TEXT.value
            if cleaned
            else PageExtractionOutcome.EMPTY.value
        ),
        ocr_applied=False,
        ocr_truncated=False,
        structured_metadata={"section": section_name},
    )


def _jira_user_identity(user_obj: Any) -> str | None:
    if not isinstance(user_obj, dict):
        return None
    name = user_obj.get("displayName") or user_obj.get("emailAddress") or user_obj.get("accountId")
    return str(name) if name else None


def _build_issue_links_summary(fields: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    structured: list[dict[str, Any]] = []
    lines: list[str] = []

    parent_obj = fields.get("parent")
    if isinstance(parent_obj, dict) and parent_obj.get("key"):
        parent_key = str(parent_obj["key"])
        raw_parent_fields = parent_obj.get("fields")
        parent_fields: dict[str, Any] = (
            raw_parent_fields if isinstance(raw_parent_fields, dict) else {}
        )
        parent_summary = str(parent_fields.get("summary") or "")
        structured.append(
            {
                "relation": "parent",
                "target_key": parent_key,
                "target_summary": parent_summary or None,
            }
        )
        lines.append(f"- Parent: {parent_key} {parent_summary}".strip())

    raw_links_val = fields.get("issuelinks")
    raw_links: list[Any] = raw_links_val if isinstance(raw_links_val, list) else []
    for link in raw_links:
        if not isinstance(link, dict):
            continue
        raw_link_type = link.get("type")
        link_type: dict[str, Any] = raw_link_type if isinstance(raw_link_type, dict) else {}
        if isinstance(link.get("outwardIssue"), dict):
            target = link["outwardIssue"]
            rel = str(link_type.get("outward") or link_type.get("name") or "relates to")
        elif isinstance(link.get("inwardIssue"), dict):
            target = link["inwardIssue"]
            rel = str(link_type.get("inward") or link_type.get("name") or "relates to")
        else:
            continue
        t_key = str(target.get("key") or "")
        raw_t_fields = target.get("fields")
        t_fields: dict[str, Any] = raw_t_fields if isinstance(raw_t_fields, dict) else {}
        t_summary = str(t_fields.get("summary") or "")
        raw_t_status = t_fields.get("status")
        t_status_obj: dict[str, Any] = raw_t_status if isinstance(raw_t_status, dict) else {}
        t_status = str(t_status_obj["name"]) if t_status_obj.get("name") else None
        if t_key:
            structured.append(
                {
                    "relation": rel,
                    "target_key": t_key,
                    "target_summary": t_summary or None,
                    "target_status": t_status,
                }
            )
            status_suffix = f" [{t_status}]" if t_status else ""
            lines.append(f"- {rel}: {t_key} {t_summary}{status_suffix}".strip())

    return structured, lines


class JiraSyncOrchestrator:
    """Runs bounded initial/incremental Jira Cloud REST v3 evidence ingestion."""

    def __init__(
        self,
        *,
        settings: Settings,
        jira_client: JiraClient,
        integration_repo: IntegrationRepository,
        ingestor: SourceEvidenceIngestor,
        access_policy_service: SourceAccessPolicyService,
    ) -> None:
        self._settings = settings
        self._client = jira_client
        self._repo = integration_repo
        self._ingestor = ingestor
        self._policy_svc = access_policy_service

    def execute_sync(
        self,
        *,
        mapping: ProjectSourceMapping,
        policy: SourceAccessPolicy,
        access_token: str,
        actor_user_id: uuid.UUID,
        external_user_id: str,
        external_username: str | None,
        sync_mode: str,
        site_base_url: str | None = None,
    ) -> SyncExecutionReport:
        """Verify Jira project ACL, fetch issues/comments/worklogs/changelog/links, and upsert."""
        now = utc_now()
        cloud_id = mapping.external_site_id
        project_key = mapping.external_resource_key
        cursor_before = dict(mapping.sync_cursor_json or {})
        new_cursor = dict(cursor_before)
        config = dict(mapping.sync_config_json or {})
        report = SyncExecutionReport(new_cursor=new_cursor)
        seen_external_ids: set[str] = set()

        # 1. Fail-closed verification that caller can still inspect this Jira project
        allowed, project_candidate = self._client.verify_project_access(
            access_token=access_token,
            cloud_id=cloud_id,
            project_key_or_id=project_key,
        )
        if not allowed or project_candidate is None:
            policy.sync_permission_status = SourcePermissionVerificationStatus.REVOKED.value
            self._repo.remove_user_from_policy(
                policy=policy,
                user_id=actor_user_id,
                verified_at=now,
            )
            raise IntegrationAuthError(
                provider="jira",
                code="JIRA_PROJECT_ACCESS_REVOKED",
                message=(
                    "Calling user's delegated token no longer has access to "
                    f"Jira project '{project_key}'."
                ),
                status_code=403,
            )

        classification = self._policy_svc.classify_jira_project()
        policy.visibility_policy = classification.visibility_policy
        policy.sync_permission_status = SourcePermissionVerificationStatus.VERIFIED.value
        self._repo.add_verified_user_to_policy(
            policy=policy,
            user_id=actor_user_id,
            external_identity={
                "provider": "jira",
                "external_user_id": external_user_id,
                "external_username": external_username,
                "cloud_id": cloud_id,
            },
            verified_at=now,
        )

        # 2. Ingest Jira project metadata item
        proj_url = (
            f"{site_base_url.rstrip('/')}/browse/{project_candidate.key}"
            if site_base_url
            else project_candidate.url
        )
        proj_text = "\n".join(
            [
                f"# Jira Project: {project_candidate.name} ({project_candidate.key})",
                f"Cloud ID: {cloud_id}",
                f"Project Type: {project_candidate.project_type_key or 'unknown'}",
                f"Style: {project_candidate.style or 'unknown'}",
            ]
        )
        self._record_upsert(
            report=report,
            mapping=mapping,
            triggered_by_user_id=actor_user_id,
            now=now,
            seen_external_ids=seen_external_ids,
            record=NormalizedSourceEvidence(
                source_type=EvidenceSourceType.JIRA.value,
                source_provider="jira_cloud",
                category=EvidenceCategory.DESIGN_DOCUMENT.value,
                source_external_id=f"jira:{cloud_id}:project:{project_candidate.key}",
                source_url=proj_url,
                source_author_identity=None,
                title=f"Jira Project {project_candidate.key}: {project_candidate.name}",
                source_created_at=None,
                source_updated_at=None,
                extraction_method=ConnectorExtractionMethod.JIRA_API.value,
                acl_scope=classification.acl_scope,
                source_access_policy_id=policy.id,
                extracted_text=proj_text,
                pages=(_page(1, proj_text, "jira_project_metadata"),),
                metadata_json={
                    "mapping_id": str(mapping.id),
                    "jira_item_type": "project",
                    "cloud_id": cloud_id,
                    "project_key": project_candidate.key,
                    "project_name": project_candidate.name,
                    "source_item_state": "active",
                },
            ),
        )

        # 3. Build bounded project-scoped JQL with optional incremental timestamp cursor
        jql_clauses = [f'project = "{project_key}"']
        custom_filter = config.get("jql_filter")
        if isinstance(custom_filter, str) and custom_filter.strip():
            jql_clauses.append(f"({custom_filter.strip()})")
        incremental_active = False
        if sync_mode == "incremental" and cursor_before.get("last_updated_at"):
            last_dt = parse_provider_datetime(str(cursor_before["last_updated_at"]))
            if last_dt is not None:
                jira_ts = last_dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M")
                jql_clauses.append(f'updated >= "{jira_ts}"')
                incremental_active = True
        full_jql = " AND ".join(jql_clauses) + " ORDER BY updated ASC"

        max_items = self._settings.integrations.sync_max_items_per_run
        remaining_budget = max(1, max_items - report.items_discovered)
        search_res = self._client.search_issues(
            access_token=access_token,
            cloud_id=cloud_id,
            jql=full_jql,
            max_items=remaining_budget,
        )
        report.warnings.extend(search_res.warnings)

        latest_updated_dt = parse_provider_datetime(
            str(cursor_before["last_updated_at"])
            if sync_mode == "incremental" and cursor_before.get("last_updated_at")
            else None
        )

        for issue in search_res.issues:
            if report.items_discovered >= max_items:
                report.partial = True
                report.warnings.append(
                    f"Reached configured sync limit of {max_items} items per run."
                )
                break

            issue_key = str(issue.get("key") or "")
            if not issue_key:
                continue
            raw_fields = issue.get("fields")
            fields: dict[str, Any] = raw_fields if isinstance(raw_fields, dict) else {}
            issue_updated = parse_provider_datetime(
                str(fields["updated"]) if fields.get("updated") else None
            )
            if issue_updated and (latest_updated_dt is None or issue_updated > latest_updated_dt):
                latest_updated_dt = issue_updated

            # Enforce dedicated fail-closed sub-policy for Jira issue `security` levels
            item_policy = policy
            item_acl_scope = classification.acl_scope
            security_obj = fields.get("security")
            security_level_info: dict[str, Any] | None = None
            if isinstance(security_obj, dict) and security_obj.get("id"):
                sec_id = str(security_obj["id"])
                sec_name = str(security_obj.get("name") or sec_id)
                sec_class = self._policy_svc.classify_jira_security_level()
                item_acl_scope = sec_class.acl_scope
                security_level_info = {"id": sec_id, "name": sec_name}
                item_policy = self._repo.upsert_access_policy(
                    organisation_id=mapping.organisation_id,
                    project_id=mapping.project_id,
                    source_connection_id=mapping.source_connection_id,
                    provider="jira",
                    scope_identifier=f"{cloud_id}:{project_key}:security:{sec_id}",
                    visibility_policy=sec_class.visibility_policy,
                    sync_permission_status=SourcePermissionVerificationStatus.VERIFIED.value,
                    authorised_by_user_id=actor_user_id,
                    verified_user_id=actor_user_id,
                    external_identity={
                        "provider": "jira",
                        "external_user_id": external_user_id,
                        "external_username": external_username,
                        "cloud_id": cloud_id,
                    },
                    provider_visibility=f"security_level:{sec_name}",
                    verified_at=now,
                    metadata_json={
                        "security_id": sec_id,
                        "security_name": sec_name,
                        "sample_issue_key": issue_key,
                    },
                )

            item_warnings: list[str] = []
            comments: list[dict[str, Any]] = []
            worklogs: list[dict[str, Any]] = []
            try:
                if config.get("include_comments", True):
                    comments, comment_warn = self._client.fetch_issue_comments(
                        access_token=access_token,
                        cloud_id=cloud_id,
                        issue_key=issue_key,
                    )
                    if comment_warn:
                        item_warnings.append(comment_warn)
                        report.partial = True

                if config.get("include_worklogs", True):
                    worklogs, worklog_warn = self._client.fetch_issue_worklogs(
                        access_token=access_token,
                        cloud_id=cloud_id,
                        issue_key=issue_key,
                    )
                    if worklog_warn:
                        item_warnings.append(worklog_warn)
                        report.partial = True

                record = self._normalize_jira_issue(
                    mapping_id=mapping.id,
                    cloud_id=cloud_id,
                    project_key=project_key,
                    site_base_url=site_base_url,
                    issue=issue,
                    comments=comments,
                    worklogs=worklogs,
                    acl_scope=item_acl_scope,
                    policy_id=item_policy.id,
                    security_level_info=security_level_info,
                    include_links=bool(config.get("include_links", True)),
                    include_changelog=bool(config.get("include_changelog", True)),
                    warnings=tuple(item_warnings),
                )
                self._record_upsert(
                    report=report,
                    mapping=mapping,
                    triggered_by_user_id=actor_user_id,
                    now=now,
                    seen_external_ids=seen_external_ids,
                    record=record,
                )
            except IntegrationAuthError:
                raise
            except IntegrationProviderError as exc:
                if exc.retryable:
                    raise
                report.items_failed += 1
                report.partial = True
                report.warnings.append(f"Jira issue {issue_key} failed: {exc.message}")

        if (
            sync_mode in {"initial", "manual"}
            and not incremental_active
            and not custom_filter
            and not report.partial
            and report.items_discovered < max_items
        ):
            inaccessible_count = self._ingestor.reconcile_missing_snapshot_items(
                project_id=mapping.project_id,
                source_type=EvidenceSourceType.JIRA.value,
                mapping_id=mapping.id,
                seen_external_ids=seen_external_ids,
                reconciled_categories={EvidenceCategory.ISSUE.value},
                now=now,
            )
            if inaccessible_count > 0:
                report.items_inaccessible += inaccessible_count
                report.partial = True
                report.warnings.append(
                    f"{inaccessible_count} previously synced Jira issue(s) were deleted "
                    "or became inaccessible."
                )

        checkpoint_dt = latest_updated_dt or now
        new_cursor["last_updated_at"] = checkpoint_dt.astimezone(UTC).isoformat()
        new_cursor["last_completed_at"] = now.astimezone(UTC).isoformat()
        report.new_cursor = new_cursor
        return report

    def _record_upsert(
        self,
        *,
        report: SyncExecutionReport,
        mapping: ProjectSourceMapping,
        triggered_by_user_id: uuid.UUID,
        now: Any,
        seen_external_ids: set[str],
        record: NormalizedSourceEvidence,
    ) -> None:
        report.items_discovered += 1
        seen_external_ids.add(record.source_external_id)
        outcome = self._ingestor.upsert_record(
            organisation_id=mapping.organisation_id,
            project_id=mapping.project_id,
            source_connection_id=mapping.source_connection_id,
            triggered_by_user_id=triggered_by_user_id,
            record=record,
            now=now,
        )
        if outcome.action == "created":
            report.items_created += 1
        elif outcome.action == "updated":
            report.items_updated += 1
        else:
            report.items_unchanged += 1

    def _normalize_jira_issue(
        self,
        *,
        mapping_id: uuid.UUID,
        cloud_id: str,
        project_key: str,
        site_base_url: str | None,
        issue: dict[str, Any],
        comments: list[dict[str, Any]],
        worklogs: list[dict[str, Any]],
        acl_scope: str,
        policy_id: uuid.UUID,
        security_level_info: dict[str, Any] | None,
        include_links: bool,
        include_changelog: bool,
        warnings: tuple[str, ...],
    ) -> NormalizedSourceEvidence:
        issue_key = str(issue["key"])
        issue_id = str(issue.get("id") or issue_key)
        raw_fields = issue.get("fields")
        fields: dict[str, Any] = raw_fields if isinstance(raw_fields, dict) else {}

        summary = str(fields.get("summary") or issue_key)
        raw_issuetype = fields.get("issuetype")
        issuetype_obj: dict[str, Any] = raw_issuetype if isinstance(raw_issuetype, dict) else {}
        issue_type = (
            str(issuetype_obj["name"]) if issuetype_obj.get("name") else "Issue"
        )
        raw_status = fields.get("status")
        status_obj: dict[str, Any] = raw_status if isinstance(raw_status, dict) else {}
        status_name = (
            str(status_obj["name"]) if status_obj.get("name") else "Unknown"
        )
        raw_priority = fields.get("priority")
        priority_obj: dict[str, Any] = raw_priority if isinstance(raw_priority, dict) else {}
        priority_name = (
            str(priority_obj["name"]) if priority_obj.get("name") else None
        )
        raw_resolution = fields.get("resolution")
        resolution_obj: dict[str, Any] = (
            raw_resolution if isinstance(raw_resolution, dict) else {}
        )
        resolution_name = (
            str(resolution_obj["name"]) if resolution_obj.get("name") else None
        )
        assignee = _jira_user_identity(fields.get("assignee"))
        reporter = _jira_user_identity(fields.get("reporter") or fields.get("creator"))
        labels = [str(lbl) for lbl in (fields.get("labels") or []) if lbl]
        components = [
            str(c["name"])
            for c in (fields.get("components") or [])
            if isinstance(c, dict) and c.get("name")
        ]
        description_text = adf_to_text(fields.get("description")).strip()

        structured_links, link_lines = (
            _build_issue_links_summary(fields) if include_links else ([], [])
        )

        header_lines = [
            f"# [{issue_key}] ({issue_type}) {summary}",
            f"Status: {status_name}",
            f"Priority: {priority_name or 'unspecified'}",
            f"Resolution: {resolution_name or 'unresolved'}",
            f"Reporter: {reporter or 'unknown'}",
            f"Assignee: {assignee or 'unassigned'}",
            f"Labels: {', '.join(labels) if labels else 'none'}",
            f"Components: {', '.join(components) if components else 'none'}",
        ]
        if security_level_info:
            header_lines.append(f"Jira Security Level: {security_level_info['name']}")

        page1_parts = ["\n".join(header_lines), description_text or "_No description._"]
        if link_lines:
            page1_parts.append("## Issue Links & Hierarchy\n" + "\n".join(link_lines))
        page1_text = "\n\n".join(page1_parts).strip()

        pages: list[ExtractedPageData] = [_page(1, page1_text, "jira_issue_summary")]
        sections = [page1_text]
        next_page = 2

        if comments:
            comment_lines: list[str] = ["## Comments"]
            for idx, c in enumerate(comments, start=1):
                c_author = _jira_user_identity(c.get("author")) or "unknown"
                c_created = c.get("created") or ""
                c_body = adf_to_text(c.get("body")).strip()
                comment_lines.append(f"### Comment {idx} by {c_author} ({c_created})\n{c_body}")
            comments_text = "\n\n".join(comment_lines)
            pages.append(_page(next_page, comments_text, "jira_issue_comments"))
            sections.append(comments_text)
            next_page += 1

        history_lines: list[str] = []
        if include_changelog:
            raw_changelog = issue.get("changelog")
            changelog: dict[str, Any] = raw_changelog if isinstance(raw_changelog, dict) else {}
            raw_histories = changelog.get("histories")
            histories: list[Any] = raw_histories if isinstance(raw_histories, list) else []
            for h in histories[-20:]:
                if not isinstance(h, dict):
                    continue
                h_author = _jira_user_identity(h.get("author")) or "system"
                h_created = h.get("created") or ""
                for item in (h.get("items") or []):
                    if not isinstance(item, dict):
                        continue
                    f_name = item.get("field") or "field"
                    from_val = item.get("fromString") or "-"
                    to_val = item.get("toString") or "-"
                    history_lines.append(
                        f"- [{h_created}] {h_author} changed `{f_name}`: `{from_val}` -> `{to_val}`"
                    )
        if worklogs:
            for wl in worklogs[:20]:
                wl_author = _jira_user_identity(wl.get("author")) or "unknown"
                wl_spent = wl.get("timeSpent") or f"{wl.get('timeSpentSeconds', 0)}s"
                wl_comment = adf_to_text(wl.get("comment")).strip()
                suffix = f": {wl_comment}" if wl_comment else ""
                history_lines.append(f"- Worklog by {wl_author} ({wl_spent}){suffix}")

        if history_lines:
            hist_text = "## Activity, Changelog & Worklogs\n" + "\n".join(history_lines)
            pages.append(_page(next_page, hist_text, "jira_activity_and_worklogs"))
            sections.append(hist_text)

        issue_url = (
            f"{site_base_url.rstrip('/')}/browse/{issue_key}"
            if site_base_url
            else (str(issue["self"]) if issue.get("self") else None)
        )
        return NormalizedSourceEvidence(
            source_type=EvidenceSourceType.JIRA.value,
            source_provider="jira_cloud",
            category=EvidenceCategory.ISSUE.value,
            source_external_id=f"jira:{cloud_id}:issue:{issue_key}",
            source_url=issue_url,
            source_author_identity=reporter or assignee,
            title=f"{issue_key}: {summary}",
            source_created_at=parse_provider_datetime(
                str(fields["created"]) if fields.get("created") else None
            ),
            source_updated_at=parse_provider_datetime(
                str(fields["updated"]) if fields.get("updated") else None
            ),
            extraction_method=ConnectorExtractionMethod.JIRA_API.value,
            acl_scope=acl_scope,
            source_access_policy_id=policy_id,
            extracted_text="\n\n---\n\n".join(sections),
            pages=tuple(pages),
            warnings=warnings,
            metadata_json={
                "mapping_id": str(mapping_id),
                "jira_item_type": "issue",
                "cloud_id": cloud_id,
                "project_key": project_key,
                "jira_issue_id": issue_id,
                "jira_issue_key": issue_key,
                "issue_type": issue_type,
                "status": status_name,
                "priority": priority_name,
                "resolution": resolution_name,
                "assignee": assignee,
                "reporter": reporter,
                "labels": labels,
                "components": components,
                "issue_links": structured_links,
                "comments_count": len(comments),
                "worklogs_count": len(worklogs),
                "security_level": security_level_info,
                "source_item_state": "active",
            },
        )
