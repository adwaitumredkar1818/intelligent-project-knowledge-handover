"""GitHub delegated sync orchestrator producing normalised evidence items cleanly."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
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
from app.services.integrations.github_client import GitHubClient
from app.services.integrations.http_utils import parse_provider_datetime

_ISSUE_REF_RE = re.compile(
    r"(?:(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+)?#(\d+)",
    re.IGNORECASE,
)


@dataclass(slots=True)
class SyncExecutionReport:
    """Aggregated outcomes and checkpoint updates produced by a connector sync run."""

    items_discovered: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_unchanged: int = 0
    items_inaccessible: int = 0
    items_failed: int = 0
    warnings: list[str] = field(default_factory=list)
    new_cursor: dict[str, Any] = field(default_factory=dict)
    partial: bool = False


def _extract_referenced_issue_numbers(*texts: str | None) -> list[int]:
    found: list[int] = []
    seen: set[int] = set()
    for text in texts:
        if not text:
            continue
        for match in _ISSUE_REF_RE.finditer(text):
            num = int(match.group(1))
            if num not in seen:
                seen.add(num)
                found.append(num)
    return found


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


class GitHubSyncOrchestrator:
    """Runs bounded initial/incremental GitHub repository evidence ingestion."""

    def __init__(
        self,
        *,
        settings: Settings,
        github_client: GitHubClient,
        integration_repo: IntegrationRepository,
        ingestor: SourceEvidenceIngestor,
        access_policy_service: SourceAccessPolicyService,
    ) -> None:
        self._settings = settings
        self._client = github_client
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
    ) -> SyncExecutionReport:
        """Ingest repo metadata, issues, PRs, commits, README/docs, and discussions."""
        now = utc_now()
        owner_repo = mapping.external_resource_key
        if "/" not in owner_repo:
            raise IntegrationProviderError(
                provider="github",
                code="GITHUB_INVALID_MAPPING_KEY",
                message=f"Invalid GitHub repository key '{owner_repo}'.",
                status_code=400,
                retryable=False,
            )
        raw_owner, raw_repo = owner_repo.split("/", 1)
        owner, repo_name = raw_owner.strip(), raw_repo.strip()
        cursor_before = dict(mapping.sync_cursor_json or {})
        new_cursor = dict(cursor_before)
        config = dict(mapping.sync_config_json or {})
        report = SyncExecutionReport(new_cursor=new_cursor)
        seen_external_ids: set[str] = set()
        reconciled_categories: set[str] = set()
        had_collection_warning = False

        # 1. Fail-closed verification that caller's token can read this repository right now
        allowed, repo_candidate = self._client.verify_repository_access(
            access_token=access_token,
            owner=owner,
            repo=repo_name,
        )
        if not allowed or repo_candidate is None:
            policy.sync_permission_status = SourcePermissionVerificationStatus.REVOKED.value
            self._repo.remove_user_from_policy(
                policy=policy,
                user_id=actor_user_id,
                verified_at=now,
            )
            raise IntegrationAuthError(
                provider="github",
                code="GITHUB_REPO_ACCESS_REVOKED",
                message=(
                    f"Calling user's delegated token no longer has access to '{owner_repo}'."
                ),
                status_code=403,
            )

        # Ensure caller's verified identity is on the repo access policy and refresh visibility
        restrict_flag = bool(config.get("restrict_to_verified_users"))
        classification = self._policy_svc.classify_github_repository(
            visibility=repo_candidate.visibility,
            is_private=repo_candidate.is_private,
            restrict_to_verified_users=restrict_flag,
        )
        policy.visibility_policy = classification.visibility_policy
        policy.provider_visibility = repo_candidate.visibility
        policy.sync_permission_status = SourcePermissionVerificationStatus.VERIFIED.value
        self._repo.add_verified_user_to_policy(
            policy=policy,
            user_id=actor_user_id,
            external_identity={
                "provider": "github",
                "external_user_id": external_user_id,
                "external_username": external_username,
            },
            verified_at=now,
        )
        mapping.provider_visibility = repo_candidate.visibility
        mapping.default_branch = repo_candidate.default_branch or mapping.default_branch
        mapping.external_resource_url = repo_candidate.html_url or mapping.external_resource_url

        repo_id = mapping.external_resource_id
        acl_scope = classification.acl_scope
        max_items = self._settings.integrations.sync_max_items_per_run
        since_cursor = (
            str(cursor_before.get("last_updated_since"))
            if sync_mode == "incremental" and cursor_before.get("last_updated_since")
            else None
        )
        issues_etag = (
            str(cursor_before.get("issues_etag"))
            if sync_mode == "incremental" and cursor_before.get("issues_etag")
            else None
        )
        commits_etag = (
            str(cursor_before.get("commits_etag"))
            if sync_mode == "incremental" and cursor_before.get("commits_etag")
            else None
        )

        # 2. Ingest repository overview record
        repo_overview_text = "\n".join(
            line
            for line in (
                f"# Repository: {repo_candidate.full_name}",
                f"Visibility: {repo_candidate.visibility} (private={repo_candidate.is_private})",
                f"Default branch: {repo_candidate.default_branch or 'unknown'}",
                f"URL: {repo_candidate.html_url or ''}",
                "",
                repo_candidate.description or "No repository description provided.",
            )
            if line is not None
        ).strip()
        self._record_upsert(
            report=report,
            mapping=mapping,
            triggered_by_user_id=actor_user_id,
            now=now,
            seen_external_ids=seen_external_ids,
            record=NormalizedSourceEvidence(
                source_type=EvidenceSourceType.GITHUB.value,
                source_provider="github",
                category=EvidenceCategory.DESIGN_DOCUMENT.value,
                source_external_id=f"github:{repo_id}:repository",
                source_url=repo_candidate.html_url,
                source_author_identity=repo_candidate.owner_login or None,
                title=f"GitHub Repository: {repo_candidate.full_name}",
                source_created_at=None,
                source_updated_at=repo_candidate.updated_at,
                extraction_method=ConnectorExtractionMethod.GITHUB_API.value,
                acl_scope=acl_scope,
                source_access_policy_id=policy.id,
                extracted_text=repo_overview_text,
                pages=(_page(1, repo_overview_text, "repository_overview"),),
                metadata_json={
                    "mapping_id": str(mapping.id),
                    "github_item_type": "repository",
                    "full_name": repo_candidate.full_name,
                    "default_branch": repo_candidate.default_branch,
                    "visibility": repo_candidate.visibility,
                    "source_item_state": "active",
                },
            ),
        )

        latest_seen_dt = parse_provider_datetime(since_cursor)

        # 3. Issues and Pull Requests
        if config.get("include_issues", True) or config.get("include_pull_requests", True):
            issues_res = self._client.fetch_issues_and_prs(
                access_token=access_token,
                owner=owner,
                repo=repo_name,
                since=since_cursor,
                etag=issues_etag,
                max_items=max_items,
            )
            report.warnings.extend(issues_res.warnings)
            if issues_res.warnings:
                report.partial = True
                had_collection_warning = True
            if issues_res.not_modified:
                had_collection_warning = True
            else:
                if config.get("include_issues", True):
                    reconciled_categories.add(EvidenceCategory.ISSUE.value)
                if config.get("include_pull_requests", True):
                    reconciled_categories.add(EvidenceCategory.PULL_REQUEST.value)
            if issues_res.etag:
                new_cursor["issues_etag"] = issues_res.etag

            for item in issues_res.items:
                if report.items_discovered >= max_items:
                    report.warnings.append(
                        f"Reached configured sync limit of {max_items} items per run."
                    )
                    report.partial = True
                    break

                is_pr = isinstance(item.get("pull_request"), dict)
                if is_pr and not config.get("include_pull_requests", True):
                    continue
                if not is_pr and not config.get("include_issues", True):
                    continue

                item_updated = parse_provider_datetime(
                    str(item["updated_at"]) if item.get("updated_at") else None
                )
                if item_updated and (latest_seen_dt is None or item_updated > latest_seen_dt):
                    latest_seen_dt = item_updated

                number = int(item.get("number") or 0)
                if number <= 0:
                    continue

                item_warnings: list[str] = []
                try:
                    comments, comment_warn = self._client.fetch_issue_comments(
                        access_token=access_token,
                        owner=owner,
                        repo=repo_name,
                        issue_number=number,
                    )
                    if comment_warn:
                        item_warnings.append(comment_warn)
                        report.partial = True

                    if is_pr:
                        pr_detail, reviews, review_comments, files, pr_warns = (
                            self._client.fetch_pull_request_bundle(
                                access_token=access_token,
                                owner=owner,
                                repo=repo_name,
                                pr_number=number,
                            )
                        )
                        item_warnings.extend(pr_warns)
                        if pr_warns:
                            report.partial = True
                        record = self._normalize_pull_request(
                            repo_id=repo_id,
                            owner_repo=owner_repo,
                            mapping_id=mapping.id,
                            policy_id=policy.id,
                            acl_scope=acl_scope,
                            issue_item=item,
                            pr_detail=pr_detail,
                            comments=comments,
                            reviews=reviews,
                            review_comments=review_comments,
                            files=files,
                            warnings=tuple(item_warnings),
                        )
                    else:
                        record = self._normalize_issue(
                            repo_id=repo_id,
                            owner_repo=owner_repo,
                            mapping_id=mapping.id,
                            policy_id=policy.id,
                            acl_scope=acl_scope,
                            issue_item=item,
                            comments=comments,
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
                    report.warnings.append(f"GitHub item #{number} failed: {exc.message}")

        # 4. Commits (bounded metadata, optional since cursor)
        if config.get("include_commits", True) and report.items_discovered < max_items:
            commits_limit = min(
                self._settings.integrations.default_github_commits_limit,
                max_items - report.items_discovered,
            )
            commits_res = self._client.fetch_commits(
                access_token=access_token,
                owner=owner,
                repo=repo_name,
                sha=repo_candidate.default_branch,
                since=since_cursor,
                etag=commits_etag,
                max_items=commits_limit,
            )
            report.warnings.extend(commits_res.warnings)
            if commits_res.etag:
                new_cursor["commits_etag"] = commits_res.etag
            for commit in commits_res.items:
                sha = str(commit.get("sha") or "")
                if not sha:
                    continue
                record = self._normalize_commit(
                    repo_id=repo_id,
                    owner_repo=owner_repo,
                    mapping_id=mapping.id,
                    policy_id=policy.id,
                    acl_scope=acl_scope,
                    commit=commit,
                )
                self._record_upsert(
                    report=report,
                    mapping=mapping,
                    triggered_by_user_id=actor_user_id,
                    now=now,
                    seen_external_ids=seen_external_ids,
                    record=record,
                )

        # 5. README and Markdown documentation / ADRs
        if config.get("include_docs", True) and report.items_discovered < max_items:
            docs_limit = min(
                self._settings.integrations.default_github_docs_limit,
                max_items - report.items_discovered,
            )
            docs, doc_warns = self._client.fetch_readme_and_docs(
                access_token=access_token,
                owner=owner,
                repo=repo_name,
                default_branch=repo_candidate.default_branch,
                max_docs=docs_limit,
            )
            report.warnings.extend(doc_warns)
            if doc_warns:
                report.partial = True
            for doc in docs:
                record = self._normalize_doc(
                    repo_id=repo_id,
                    owner_repo=owner_repo,
                    mapping_id=mapping.id,
                    policy_id=policy.id,
                    acl_scope=acl_scope,
                    doc=doc,
                    repo_updated_at=repo_candidate.updated_at,
                )
                self._record_upsert(
                    report=report,
                    mapping=mapping,
                    triggered_by_user_id=actor_user_id,
                    now=now,
                    seen_external_ids=seen_external_ids,
                    record=record,
                )

        # 6. Discussions (optional / graceful skip when repo disables discussions)
        if config.get("include_discussions", True) and report.items_discovered < max_items:
            discussions, disc_warns = self._client.fetch_discussions(
                access_token=access_token,
                owner=owner,
                repo=repo_name,
                max_items=min(30, max_items - report.items_discovered),
            )
            report.warnings.extend(disc_warns)
            for disc in discussions:
                record = self._normalize_discussion(
                    repo_id=repo_id,
                    owner_repo=owner_repo,
                    mapping_id=mapping.id,
                    policy_id=policy.id,
                    acl_scope=acl_scope,
                    discussion=disc,
                )
                self._record_upsert(
                    report=report,
                    mapping=mapping,
                    triggered_by_user_id=actor_user_id,
                    now=now,
                    seen_external_ids=seen_external_ids,
                    record=record,
                )

        # Safely reconcile disappeared items only on complete non-incremental snapshot runs
        if (
            sync_mode in {"initial", "manual"}
            and since_cursor is None
            and not had_collection_warning
            and not report.partial
            and reconciled_categories
            and report.items_discovered < max_items
        ):
            inaccessible_count = self._ingestor.reconcile_missing_snapshot_items(
                project_id=mapping.project_id,
                source_type=EvidenceSourceType.GITHUB.value,
                mapping_id=mapping.id,
                seen_external_ids=seen_external_ids,
                reconciled_categories=reconciled_categories,
                now=now,
            )
            if inaccessible_count > 0:
                report.items_inaccessible += inaccessible_count
                report.partial = True
                report.warnings.append(
                    f"{inaccessible_count} previously synced GitHub item(s) were deleted "
                    "or became inaccessible."
                )

        checkpoint_dt = latest_seen_dt or now
        new_cursor["last_updated_since"] = checkpoint_dt.astimezone(UTC).isoformat()
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

    def _normalize_issue(
        self,
        *,
        repo_id: str,
        owner_repo: str,
        mapping_id: uuid.UUID,
        policy_id: uuid.UUID,
        acl_scope: str,
        issue_item: dict[str, Any],
        comments: list[dict[str, Any]],
        warnings: tuple[str, ...],
    ) -> NormalizedSourceEvidence:
        number = int(issue_item["number"])
        title = str(issue_item.get("title") or f"Issue #{number}")
        body = str(issue_item.get("body") or "").strip()
        raw_user = issue_item.get("user")
        user_obj: dict[str, Any] = raw_user if isinstance(raw_user, dict) else {}
        author = str(user_obj.get("login")) if user_obj.get("login") else None
        labels = [
            str(lbl["name"])
            for lbl in (issue_item.get("labels") or [])
            if isinstance(lbl, dict) and lbl.get("name")
        ]
        assignees = [
            str(a["login"])
            for a in (issue_item.get("assignees") or [])
            if isinstance(a, dict) and a.get("login")
        ]
        state = str(issue_item.get("state") or "open")
        raw_milestone = issue_item.get("milestone")
        milestone_obj: dict[str, Any] = raw_milestone if isinstance(raw_milestone, dict) else {}
        milestone_title = (
            str(milestone_obj["title"]) if milestone_obj.get("title") else None
        )

        header_lines = [
            f"# [{owner_repo}#{number}] {title}",
            f"State: {state}",
            f"Author: {author or 'unknown'}",
            f"Assignees: {', '.join(assignees) if assignees else 'unassigned'}",
            f"Labels: {', '.join(labels) if labels else 'none'}",
        ]
        if milestone_title:
            header_lines.append(f"Milestone: {milestone_title}")
        page1_text = "\n".join(header_lines) + "\n\n" + (body or "_No description._")

        comment_blocks: list[str] = []
        for idx, c in enumerate(comments, start=1):
            raw_c_user = c.get("user")
            c_user: dict[str, Any] = raw_c_user if isinstance(raw_c_user, dict) else {}
            c_author = c_user.get("login") or "unknown"
            c_created = c.get("created_at") or ""
            c_body = str(c.get("body") or "").strip()
            comment_blocks.append(f"## Comment {idx} by @{c_author} ({c_created})\n{c_body}")

        pages: list[ExtractedPageData] = [_page(1, page1_text, "issue_body")]
        full_sections = [page1_text]
        if comment_blocks:
            comments_text = "\n\n".join(comment_blocks)
            pages.append(_page(2, comments_text, "issue_comments"))
            full_sections.append(comments_text)

        referenced = _extract_referenced_issue_numbers(
            body,
            *(str(c.get("body") or "") for c in comments),
        )
        return NormalizedSourceEvidence(
            source_type=EvidenceSourceType.GITHUB.value,
            source_provider="github",
            category=EvidenceCategory.ISSUE.value,
            source_external_id=f"github:{repo_id}:issue:{number}",
            source_url=str(issue_item["html_url"]) if issue_item.get("html_url") else None,
            source_author_identity=author,
            title=f"{owner_repo}#{number}: {title}",
            source_created_at=parse_provider_datetime(
                str(issue_item["created_at"]) if issue_item.get("created_at") else None
            ),
            source_updated_at=parse_provider_datetime(
                str(issue_item["updated_at"]) if issue_item.get("updated_at") else None
            ),
            extraction_method=ConnectorExtractionMethod.GITHUB_API.value,
            acl_scope=acl_scope,
            source_access_policy_id=policy_id,
            extracted_text="\n\n---\n\n".join(full_sections),
            pages=tuple(pages),
            warnings=warnings,
            metadata_json={
                "mapping_id": str(mapping_id),
                "github_item_type": "issue",
                "repository": owner_repo,
                "number": number,
                "state": state,
                "labels": labels,
                "assignees": assignees,
                "milestone": milestone_title,
                "comments_count": len(comments),
                "referenced_issue_numbers": referenced,
                "source_item_state": "active",
            },
        )

    def _normalize_pull_request(
        self,
        *,
        repo_id: str,
        owner_repo: str,
        mapping_id: uuid.UUID,
        policy_id: uuid.UUID,
        acl_scope: str,
        issue_item: dict[str, Any],
        pr_detail: dict[str, Any],
        comments: list[dict[str, Any]],
        reviews: list[dict[str, Any]],
        review_comments: list[dict[str, Any]],
        files: list[dict[str, Any]],
        warnings: tuple[str, ...],
    ) -> NormalizedSourceEvidence:
        merged_source = {**issue_item, **pr_detail}
        number = int(merged_source["number"])
        title = str(merged_source.get("title") or f"PR #{number}")
        body = str(merged_source.get("body") or "").strip()
        raw_user = merged_source.get("user")
        user_obj: dict[str, Any] = raw_user if isinstance(raw_user, dict) else {}
        author = str(user_obj.get("login")) if user_obj.get("login") else None
        merged = bool(merged_source.get("merged") or merged_source.get("merged_at"))
        merged_at = merged_source.get("merged_at")
        state = "merged" if merged else str(merged_source.get("state") or "open")
        head_ref = (
            str(merged_source["head"].get("ref"))
            if isinstance(merged_source.get("head"), dict) and merged_source["head"].get("ref")
            else None
        )
        base_ref = (
            str(merged_source["base"].get("ref"))
            if isinstance(merged_source.get("base"), dict) and merged_source["base"].get("ref")
            else None
        )
        labels = [
            str(lbl["name"])
            for lbl in (merged_source.get("labels") or [])
            if isinstance(lbl, dict) and lbl.get("name")
        ]

        header_lines = [
            f"# [PR {owner_repo}#{number}] {title}",
            f"Status: {state} (merged={merged})",
            f"Author: {author or 'unknown'}",
            f"Branches: {head_ref or '?'} -> {base_ref or '?'}",
            f"Labels: {', '.join(labels) if labels else 'none'}",
        ]
        if merged_at:
            header_lines.append(f"Merged at: {merged_at}")
        page1_text = "\n".join(header_lines) + "\n\n" + (body or "_No pull request description._")

        review_lines: list[str] = []
        for rev in reviews:
            raw_r_user = rev.get("user")
            r_user: dict[str, Any] = raw_r_user if isinstance(raw_r_user, dict) else {}
            r_author = r_user.get("login") or "unknown"
            r_state = rev.get("state") or "COMMENTED"
            r_body = str(rev.get("body") or "").strip()
            review_lines.append(f"- Review by @{r_author} [{r_state}]: {r_body or '(no comment)'}")
        for rc in review_comments:
            raw_rc_user = rc.get("user")
            rc_user: dict[str, Any] = raw_rc_user if isinstance(raw_rc_user, dict) else {}
            rc_author = rc_user.get("login") or "unknown"
            rc_path = rc.get("path") or "unknown"
            rc_body = str(rc.get("body") or "").strip()
            review_lines.append(f"- Inline comment on `{rc_path}` by @{rc_author}: {rc_body}")
        for c in comments:
            raw_c_user = c.get("user")
            c_user: dict[str, Any] = raw_c_user if isinstance(raw_c_user, dict) else {}
            c_author = c_user.get("login") or "unknown"
            c_body = str(c.get("body") or "").strip()
            review_lines.append(f"- Discussion comment by @{c_author}: {c_body}")

        changed_files_meta = [
            {
                "filename": str(f.get("filename") or ""),
                "status": str(f.get("status") or "modified"),
                "additions": int(f.get("additions") or 0),
                "deletions": int(f.get("deletions") or 0),
                "changes": int(f.get("changes") or 0),
            }
            for f in files
            if f.get("filename")
        ]
        files_text = "\n".join(
            f"- `{f['filename']}` ({f['status']}, +{f['additions']}/-{f['deletions']})"
            for f in changed_files_meta
        )

        pages: list[ExtractedPageData] = [_page(1, page1_text, "pull_request_body")]
        sections = [page1_text]
        next_page = 2
        if review_lines:
            rev_text = "## Reviews & Comments\n" + "\n".join(review_lines)
            pages.append(_page(next_page, rev_text, "pull_request_reviews_and_comments"))
            sections.append(rev_text)
            next_page += 1
        if files_text:
            f_text = "## Changed Files Metadata\n" + files_text
            pages.append(_page(next_page, f_text, "changed_files_metadata"))
            sections.append(f_text)

        referenced = _extract_referenced_issue_numbers(
            title,
            body,
            *(str(c.get("body") or "") for c in comments),
            *(str(r.get("body") or "") for r in reviews),
        )
        return NormalizedSourceEvidence(
            source_type=EvidenceSourceType.GITHUB.value,
            source_provider="github",
            category=EvidenceCategory.PULL_REQUEST.value,
            source_external_id=f"github:{repo_id}:pr:{number}",
            source_url=str(merged_source["html_url"]) if merged_source.get("html_url") else None,
            source_author_identity=author,
            title=f"PR {owner_repo}#{number}: {title}",
            source_created_at=parse_provider_datetime(
                str(merged_source["created_at"]) if merged_source.get("created_at") else None
            ),
            source_updated_at=parse_provider_datetime(
                str(merged_source["updated_at"]) if merged_source.get("updated_at") else None
            ),
            extraction_method=ConnectorExtractionMethod.GITHUB_API.value,
            acl_scope=acl_scope,
            source_access_policy_id=policy_id,
            extracted_text="\n\n---\n\n".join(sections),
            pages=tuple(pages),
            warnings=warnings,
            metadata_json={
                "mapping_id": str(mapping_id),
                "github_item_type": "pull_request",
                "repository": owner_repo,
                "number": number,
                "state": state,
                "merged": merged,
                "merged_at": merged_at,
                "base_ref": base_ref,
                "head_ref": head_ref,
                "labels": labels,
                "reviews_count": len(reviews),
                "review_comments_count": len(review_comments),
                "changed_files": changed_files_meta[:100],
                "referenced_issue_numbers": referenced,
                "source_item_state": "active",
            },
        )

    def _normalize_commit(
        self,
        *,
        repo_id: str,
        owner_repo: str,
        mapping_id: uuid.UUID,
        policy_id: uuid.UUID,
        acl_scope: str,
        commit: dict[str, Any],
    ) -> NormalizedSourceEvidence:
        sha = str(commit["sha"])
        raw_commit_inner = commit.get("commit")
        commit_inner: dict[str, Any] = (
            raw_commit_inner if isinstance(raw_commit_inner, dict) else {}
        )
        raw_author_inner = commit_inner.get("author")
        author_inner: dict[str, Any] = (
            raw_author_inner if isinstance(raw_author_inner, dict) else {}
        )
        raw_gh_author = commit.get("author")
        gh_author: dict[str, Any] = raw_gh_author if isinstance(raw_gh_author, dict) else {}
        message = str(commit_inner.get("message") or "").strip()
        first_line = message.splitlines()[0] if message else sha[:12]
        author_identity = (
            str(gh_author.get("login"))
            if gh_author.get("login")
            else str(author_inner.get("email") or author_inner.get("name") or "") or None
        )
        authored_at = parse_provider_datetime(
            str(author_inner["date"]) if author_inner.get("date") else None
        )
        body_text = "\n".join(
            [
                f"# Commit {sha[:12]} ({owner_repo})",
                f"Author: {author_identity or 'unknown'}",
                f"Date: {author_inner.get('date') or ''}",
                "",
                message,
            ]
        ).strip()
        referenced = _extract_referenced_issue_numbers(message)
        return NormalizedSourceEvidence(
            source_type=EvidenceSourceType.GITHUB.value,
            source_provider="github",
            category=EvidenceCategory.COMMIT.value,
            source_external_id=f"github:{repo_id}:commit:{sha}",
            source_url=str(commit["html_url"]) if commit.get("html_url") else None,
            source_author_identity=author_identity,
            title=f"{owner_repo}@{sha[:8]}: {first_line[:200]}",
            source_created_at=authored_at,
            source_updated_at=authored_at,
            extraction_method=ConnectorExtractionMethod.GITHUB_API.value,
            acl_scope=acl_scope,
            source_access_policy_id=policy_id,
            extracted_text=body_text,
            pages=(_page(1, body_text, "commit_message"),),
            metadata_json={
                "mapping_id": str(mapping_id),
                "github_item_type": "commit",
                "repository": owner_repo,
                "sha": sha,
                "referenced_issue_numbers": referenced,
                "source_item_state": "active",
            },
        )

    def _normalize_doc(
        self,
        *,
        repo_id: str,
        owner_repo: str,
        mapping_id: uuid.UUID,
        policy_id: uuid.UUID,
        acl_scope: str,
        doc: dict[str, Any],
        repo_updated_at: Any,
    ) -> NormalizedSourceEvidence:
        path = str(doc["path"])
        text = str(doc.get("text") or "").strip()
        return NormalizedSourceEvidence(
            source_type=EvidenceSourceType.GITHUB.value,
            source_provider="github",
            category=EvidenceCategory.DESIGN_DOCUMENT.value,
            source_external_id=f"github:{repo_id}:doc:{path}",
            source_url=str(doc["html_url"]) if doc.get("html_url") else None,
            source_author_identity=None,
            title=f"{owner_repo}: {path}",
            source_created_at=None,
            source_updated_at=repo_updated_at,
            extraction_method=ConnectorExtractionMethod.GITHUB_API.value,
            acl_scope=acl_scope,
            source_access_policy_id=policy_id,
            extracted_text=text,
            pages=(_page(1, text, f"doc:{path}"),),
            original_filename=path.split("/")[-1][:255],
            metadata_json={
                "mapping_id": str(mapping_id),
                "github_item_type": "documentation",
                "repository": owner_repo,
                "path": path,
                "git_blob_sha": doc.get("sha"),
                "source_item_state": "active",
            },
        )

    def _normalize_discussion(
        self,
        *,
        repo_id: str,
        owner_repo: str,
        mapping_id: uuid.UUID,
        policy_id: uuid.UUID,
        acl_scope: str,
        discussion: dict[str, Any],
    ) -> NormalizedSourceEvidence:
        disc_num = str(discussion.get("number") or discussion.get("id") or "0")
        title = str(discussion.get("title") or f"Discussion #{disc_num}")
        body = str(discussion.get("body") or "").strip()
        raw_user = discussion.get("user")
        user_obj: dict[str, Any] = raw_user if isinstance(raw_user, dict) else {}
        author = str(user_obj.get("login")) if user_obj.get("login") else None
        raw_cat = discussion.get("category")
        category_obj: dict[str, Any] = raw_cat if isinstance(raw_cat, dict) else {}
        disc_category = str(category_obj.get("name") or "") or None
        text = f"# Discussion #{disc_num}: {title}\n\n{body}".strip()
        return NormalizedSourceEvidence(
            source_type=EvidenceSourceType.GITHUB.value,
            source_provider="github",
            category=EvidenceCategory.DISCUSSION_THREAD.value,
            source_external_id=f"github:{repo_id}:discussion:{disc_num}",
            source_url=str(discussion["html_url"]) if discussion.get("html_url") else None,
            source_author_identity=author,
            title=f"{owner_repo} Discussion #{disc_num}: {title}",
            source_created_at=parse_provider_datetime(
                str(discussion["created_at"]) if discussion.get("created_at") else None
            ),
            source_updated_at=parse_provider_datetime(
                str(discussion["updated_at"]) if discussion.get("updated_at") else None
            ),
            extraction_method=ConnectorExtractionMethod.GITHUB_API.value,
            acl_scope=acl_scope,
            source_access_policy_id=policy_id,
            extracted_text=text,
            pages=(_page(1, text, "discussion_body"),),
            metadata_json={
                "mapping_id": str(mapping_id),
                "github_item_type": "discussion",
                "repository": owner_repo,
                "discussion_category": disc_category,
                "source_item_state": "active",
            },
        )
