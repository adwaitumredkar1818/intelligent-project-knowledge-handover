"use client";

import React from "react";
import Link from "next/link";
import {
  Sparkles,
  Users,
  Database,
  Workflow,
  Lightbulb,
  AlertTriangle,
  ListTodo,
  Activity,
  Plus,
  ArrowRight,
} from "lucide-react";
import {
  Card,
  CardHeader,
  Button,
  Badge,
  StatusBadge,
  SeverityBadge,
  PersonCell,
  EmptyState,
  Avatar,
} from "../ui";
import { Ring, StackedBar } from "../dashboard/DashboardCharts";
import { SourceIcon } from "../brand/brand";
import type { Project, ProjectOverview, ProjectTransition } from "../../lib/types";

export interface ProjectOverviewTabProps {
  project: Project;
  overview: ProjectOverview | null;
  transition?: ProjectTransition | null;
  isLoading?: boolean;
  onNavigateTab?: (tabId: "overview" | "team" | "settings" | "activity") => void;
}

export function ProjectOverviewTab({
  project,
  overview,
  transition,
  onNavigateTab,
}: ProjectOverviewTabProps) {
  const readinessPct = overview?.readiness?.overall_readiness_pct ?? 15;
  const sourcesCount = overview?.sources?.connected_count ?? 0;
  const evidenceCount = overview?.evidence?.total_evidence_items ?? 0;
  const decisionsCount = overview?.knowledge?.decisions_count ?? 0;
  const tasksCount = overview?.knowledge?.tasks_count ?? 0;
  const risksCount = overview?.knowledge?.risks_count ?? 0;
  const isNew = sourcesCount === 0 && evidenceCount === 0;

  const targetDateStr = project.target_completion_date || project.target_handover_date;
  const formattedTargetDate = targetDateStr
    ? new Date(targetDateStr).toLocaleDateString("en-GB", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Not set";

  const formattedStartDate = project.start_date
    ? new Date(project.start_date).toLocaleDateString("en-GB", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Active";

  return (
    <div className="space-y-5">
      {/* Empty State / Initial Configuration Callout */}
      {isNew && (
        <Card className="p-5 border-amber-200/60 bg-amber-50/20">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-amber-800">
                <Database className="size-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-navy">
                  Connect data sources to start reconstructing knowledge
                </h3>
                <p className="mt-0.5 text-xs text-muted max-w-xl leading-relaxed">
                  This project workspace has no connected sources or ingested documents yet. Connect GitHub, Jira, or upload architecture documents to begin extraction.
                </p>
              </div>
            </div>
            <Link href="/evidence">
              <Button size="sm" icon={Plus}>
                Connect Sources & Evidence
              </Button>
            </Link>
          </div>
        </Card>
      )}

      {/* Grid of Metric Cards */}
      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        {/* 1. Project Summary Card */}
        <Card className="p-5 flex flex-col justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Project Health & Summary
            </p>
            <div className="mt-4 flex items-center gap-4">
              <Ring
                value={readinessPct}
                size={70}
                color={
                  readinessPct >= 80
                    ? "#299B80"
                    : readinessPct >= 40
                      ? "#315FBA"
                      : "#D39B43"
                }
                label={`${readinessPct}%`}
              />
              <div className="min-w-0">
                <p className="text-sm font-semibold text-navy">
                  {readinessPct >= 80
                    ? "Ready for Handover"
                    : readinessPct >= 40
                      ? "Reconstruction Active"
                      : "Knowledge Scoping"}
                </p>
                <p className="text-xs text-muted mt-0.5">
                  {overview?.readiness?.status || "Initial ingestion active"}
                </p>
                <div className="mt-1.5">
                  <StatusBadge status={project.status || "active"} />
                </div>
              </div>
            </div>
          </div>

          <dl className="mt-5 space-y-2.5 border-t border-line pt-4 text-xs">
            <div className="flex justify-between items-center">
              <dt className="text-muted">Owner</dt>
              <dd className="font-medium text-navy">
                {overview?.owner?.full_name || "Assigned Manager"}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-muted">Visibility</dt>
              <dd className="font-medium text-navy capitalize">
                {project.visibility || "Private"}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-muted">Timeline</dt>
              <dd className="font-medium text-navy font-mono text-[11px]">
                {formattedStartDate} – {formattedTargetDate}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-muted">Vector Index</dt>
              <dd className="font-mono text-[11px] text-brand">
                Isolated ChromaDB
              </dd>
            </div>
          </dl>
        </Card>

        {/* 2. Knowledge Coverage Card */}
        <Card className="flex flex-col justify-between">
          <CardHeader
            title="Knowledge Coverage"
            subtitle="Share of reconstructed domains with verified evidence"
            icon={Sparkles}
          />
          <div className="px-5 pb-5">
            <div className="flex items-end gap-2">
              <span className="text-3xl font-semibold text-navy tracking-tight">
                {readinessPct}%
              </span>
              <span className="mb-1 text-xs text-muted">
                {evidenceCount} evidence items indexed
              </span>
            </div>

            <StackedBar
              className="mt-3"
              segments={[
                {
                  label: "Verified",
                  value: Math.max(1, Math.round(evidenceCount * 0.4)),
                  color: "#299B80",
                },
                {
                  label: "Candidate",
                  value: Math.max(1, Math.round(evidenceCount * 0.5)),
                  color: "#315FBA",
                },
                {
                  label: "Gaps / Risks",
                  value: Math.max(1, risksCount),
                  color: "#D36D72",
                },
              ]}
            />

            <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 border border-line/60">
                <Lightbulb className="size-3.5 text-muted shrink-0" />
                <span className="flex-1 text-muted">Decisions</span>
                <span className="font-semibold text-navy">{decisionsCount}</span>
              </div>
              <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 border border-line/60">
                <ListTodo className="size-3.5 text-muted shrink-0" />
                <span className="flex-1 text-muted">Tasks</span>
                <span className="font-semibold text-navy">{tasksCount}</span>
              </div>
              <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 border border-line/60">
                <AlertTriangle className="size-3.5 text-muted shrink-0" />
                <span className="flex-1 text-muted">Risks</span>
                <span className="font-semibold text-navy">{risksCount}</span>
              </div>
              <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 border border-line/60">
                <Database className="size-3.5 text-muted shrink-0" />
                <span className="flex-1 text-muted">Evidence</span>
                <span className="font-semibold text-navy">{evidenceCount}</span>
              </div>
            </div>
          </div>
        </Card>

        {/* 3. Team Members Preview Card */}
        <Card className="flex flex-col justify-between">
          <CardHeader
            title="Team & Ownership"
            subtitle="Project participants & roles"
            icon={Users}
            action={
              onNavigateTab && (
                <button
                  type="button"
                  onClick={() => onNavigateTab("team")}
                  className="text-xs font-semibold text-brand hover:underline inline-flex items-center gap-1 cursor-pointer"
                >
                  <span>Manage</span>
                  <ArrowRight className="size-3" />
                </button>
              )
            }
          />
          <div className="px-5 pb-5 space-y-3">
            {overview?.departing_member && (
              <div className="flex items-center justify-between gap-2 p-2.5 rounded-lg bg-amber-50/50 border border-amber-200/50">
                <PersonCell
                  name={overview.departing_member.full_name}
                  email={overview.departing_member.email}
                  sub="Outgoing Knowledge Owner"
                />
                <Badge tone="amber">Outgoing</Badge>
              </div>
            )}

            {overview?.successor && (
              <div className="flex items-center justify-between gap-2 p-2.5 rounded-lg bg-emerald-50/50 border border-emerald-200/50">
                <PersonCell
                  name={overview.successor.full_name}
                  email={overview.successor.email}
                  sub="Incoming Assignee"
                />
                <Badge tone="green">Incoming</Badge>
              </div>
            )}

            {overview?.owner && (
              <div className="flex items-center justify-between gap-2 p-2.5 rounded-lg bg-slate-50 border border-line/60">
                <PersonCell
                  name={overview.owner.full_name}
                  email={overview.owner.email}
                  sub="Project Lead"
                />
                <Badge tone="blue">Manager</Badge>
              </div>
            )}

            {!overview?.departing_member && !overview?.successor && (
              <div className="py-4 text-center">
                <p className="text-xs text-muted">
                  No departing owner or successor transition roles configured yet.
                </p>
                {onNavigateTab && (
                  <button
                    type="button"
                    onClick={() => onNavigateTab("settings")}
                    className="mt-2 text-xs font-medium text-brand hover:underline cursor-pointer"
                  >
                    Configure transition in Settings
                  </button>
                )}
              </div>
            )}
          </div>
        </Card>

        {/* 4. Connected Sources Card */}
        <Card className="flex flex-col justify-between">
          <CardHeader
            title="Connected Data Sources"
            subtitle={`${sourcesCount} source connections mapped`}
            icon={Database}
            action={
              <Link
                href="/evidence"
                className="text-xs font-semibold text-brand hover:underline inline-flex items-center gap-1"
              >
                <span>Sources</span>
                <ArrowRight className="size-3" />
              </Link>
            }
          />
          <div className="px-5 pb-5">
            {sourcesCount === 0 ? (
              <div className="py-6 text-center">
                <p className="text-xs text-muted">No external sources connected.</p>
                <Link href="/evidence">
                  <Button size="sm" variant="secondary" className="mt-3">
                    Connect Provider
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-2.5">
                {overview?.sources?.active_count ? (
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-line">
                    <div className="flex items-center gap-2.5">
                      <SourceIcon type="github" size={28} />
                      <div>
                        <p className="text-xs font-semibold text-navy">
                          GitHub Repository
                        </p>
                        <p className="text-[11px] text-muted">
                          Commits & Pull Requests
                        </p>
                      </div>
                    </div>
                    <Badge tone="green">Connected</Badge>
                  </div>
                ) : null}

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-line">
                  <div className="flex items-center gap-2.5">
                    <SourceIcon type="docs" size={28} />
                    <div>
                      <p className="text-xs font-semibold text-navy">
                        Document Ingestion
                      </p>
                      <p className="text-[11px] text-muted">
                        PDF, DOCX & GLM OCR
                      </p>
                    </div>
                  </div>
                  <Badge tone="blue">Ready</Badge>
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* 5. Active Handover Package / Stage (Span 2 cols on lg) */}
        <Card className="lg:col-span-2 flex flex-col justify-between">
          <CardHeader
            title="Active Handover Workflow"
            subtitle="Governance, approval stage & knowledge compilation"
            icon={Workflow}
            action={
              <Link href="/handovers">
                <Button size="sm" variant="secondary">
                  View Handovers
                </Button>
              </Link>
            }
          />
          <div className="px-5 pb-5">
            {transition ? (
              <div className="rounded-xl border border-line bg-slate-50/50 p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
                  <div>
                    <span className="text-[11px] font-semibold text-muted uppercase tracking-wider">
                      Current Stage
                    </span>
                    <h4 className="text-sm font-bold text-navy capitalize mt-0.5">
                      {transition.workflow_stage.replace("_", " ")}
                    </h4>
                  </div>
                  <Badge tone="blue">In Progress</Badge>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 text-xs">
                  <div>
                    <span className="text-muted block">Departing Member:</span>
                    <span className="font-semibold text-navy">
                      {transition.departing_user.full_name}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted block">Incoming Successor:</span>
                    <span className="font-semibold text-navy">
                      {transition.successor_user.full_name}
                    </span>
                  </div>
                  {transition.handover_scope && (
                    <div className="sm:col-span-2">
                      <span className="text-muted block">Handover Scope:</span>
                      <p className="text-slate-600 mt-0.5 line-clamp-2 leading-relaxed">
                        {transition.handover_scope}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <EmptyState
                icon={Workflow}
                title="No active handover configured"
                body="Configure departing and incoming team members to track structured knowledge transfer."
                action={
                  onNavigateTab && (
                    <Button
                      size="sm"
                      onClick={() => onNavigateTab("settings")}
                    >
                      Configure Handover
                    </Button>
                  )
                }
              />
            )}
          </div>
        </Card>

        {/* 6. Outstanding Risks Card */}
        <Card className="flex flex-col justify-between">
          <CardHeader
            title="Outstanding Risks"
            subtitle="Identified architectural & knowledge gaps"
            icon={AlertTriangle}
          />
          <div className="px-5 pb-5">
            {risksCount === 0 ? (
              <p className="text-xs text-muted py-4 text-center">
                No active knowledge risks identified.
              </p>
            ) : (
              <ul className="space-y-2.5">
                <li className="flex items-start gap-2.5 text-xs">
                  <SeverityBadge level="High" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-navy truncate">
                      Deployment credentials undocumented
                    </p>
                    <p className="text-[11px] text-muted">
                      Knowledge held by single engineer
                    </p>
                  </div>
                </li>
                <li className="flex items-start gap-2.5 text-xs">
                  <SeverityBadge level="Medium" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-navy truncate">
                      Database migration rollback procedures missing
                    </p>
                    <p className="text-[11px] text-muted">
                      Awaiting verification
                    </p>
                  </div>
                </li>
              </ul>
            )}
          </div>
        </Card>

        {/* 7. Pending Tasks Card */}
        <Card className="flex flex-col justify-between">
          <CardHeader
            title="Pending Handover Tasks"
            subtitle="Actions required before sign-off"
            icon={ListTodo}
          />
          <div className="px-5 pb-5">
            {tasksCount === 0 ? (
              <p className="text-xs text-muted py-4 text-center">
                No pending tasks remaining.
              </p>
            ) : (
              <ul className="space-y-2.5">
                <li className="flex items-center justify-between gap-2 text-xs">
                  <span className="font-medium text-navy truncate">
                    Verify architectural runbook
                  </span>
                  <Badge tone="amber">Pending</Badge>
                </li>
                <li className="flex items-center justify-between gap-2 text-xs">
                  <span className="font-medium text-navy truncate">
                    Validate production access transfer
                  </span>
                  <Badge tone="blue">In Review</Badge>
                </li>
              </ul>
            )}
          </div>
        </Card>

        {/* 8. Recent Activity Card */}
        <Card className="flex flex-col justify-between">
          <CardHeader
            title="Recent Activity"
            subtitle="Latest project actions"
            icon={Activity}
            action={
              onNavigateTab && (
                <button
                  type="button"
                  onClick={() => onNavigateTab("activity")}
                  className="text-xs font-semibold text-brand hover:underline inline-flex items-center gap-1 cursor-pointer"
                >
                  <span>All</span>
                  <ArrowRight className="size-3" />
                </button>
              )
            }
          />
          <div className="px-5 pb-5">
            {overview?.recent_activity && overview.recent_activity.length > 0 ? (
              <ul className="space-y-3">
                {overview.recent_activity.slice(0, 4).map((act) => (
                  <li key={act.id} className="flex items-start gap-2.5 text-xs">
                    <Avatar name={act.actor_name || "System"} size={22} />
                    <div className="flex-1 min-w-0">
                      <p className="text-navy font-medium truncate">
                        {act.description}
                      </p>
                      <p className="text-[11px] text-muted">
                        {new Date(act.timestamp).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}{" "}
                        · {act.actor_name || "System"}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted py-4 text-center">
                No recent activity recorded.
              </p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
