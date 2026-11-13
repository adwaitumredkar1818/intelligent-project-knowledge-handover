"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Inbox,
  ListTodo,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import {
  Badge,
  Button,
  Card,
  Panel,
  MetricBand,
  StatusBadge,
  RoleBadge,
  SeverityBadge,
} from "../ui";
import { ViewLink } from "./DashboardHelpers";

export function IncomingDashboard() {
  const router = useRouter();
  const {
    activeProject,
    projects,
    overview,
    members,
    user,
  } = useLiveApp();

  const project = activeProject ?? projects[0] ?? null;
  if (!project) return null;

  // Departing member
  const departingMember = members.find((m) => m.transition_role === "departing_owner");
  const departingName = departingMember?.user_full_name || departingMember?.user_email || "Departing Owner";

  const totalDecisions = overview?.knowledge.decisions_count || 0;
  const totalTasks = overview?.knowledge.tasks_count || 0;
  const totalRisks = overview?.knowledge.risks_count || 0;
  const totalEvid = overview?.evidence.total_evidence_items || 0;
  const attentionItems = overview?.attention_items || [];

  const recommendedSteps = [
    {
      icon: BookOpen,
      title: "Read architecture & design rationale",
      sub: `${totalDecisions} documented decisions`,
      to: "/knowledge",
    },
    {
      icon: ListTodo,
      title: `Pick up ${totalTasks} active responsibilities`,
      sub: "Open tasks transferred to incoming owner",
      to: "/knowledge",
    },
    {
      icon: AlertTriangle,
      title: "Review operational risks & dependencies",
      sub: `${totalRisks} flagged architectural risks`,
      to: "/conflicts",
    },
    {
      icon: MessageSquareText,
      title: "Ask AI Assistant about anything unclear",
      sub: "Answers cite verified source evidence",
      to: "/assistant",
    },
  ];

  return (
    <div className="space-y-5">
      {/* 1. KPI Band */}
      <MetricBand
        items={[
          {
            label: "Received handover",
            value: "1 active",
            hint: `${project.name}`,
            tone: "blue",
            onClick: () => router.push("/handover"),
          },
          {
            label: "Knowledge available",
            value: totalEvid > 0 ? `${totalEvid} items` : `${totalDecisions + totalTasks} findings`,
            hint: "verified evidence records",
            tone: "green",
            onClick: () => router.push("/knowledge"),
          },
          {
            label: "Pending acknowledgement",
            value: overview?.readiness.status === "completed" ? 0 : 1,
            hint: "receipt confirmation",
            tone: "amber",
            onClick: () => router.push("/handover"),
          },
          {
            label: "My projects",
            value: projects.length,
            hint: "accessible workspaces",
            tone: "navy",
            onClick: () => router.push("/projects"),
          },
        ]}
      />

      {/* 2. Received Handover Hero Card & Recommended First Month Actions */}
      <div className="grid gap-5 lg:grid-cols-[1.75fr_1fr]">
        <Card className="relative overflow-hidden p-6 sm:p-7 shadow-card">
          <div
            className="pointer-events-none absolute -right-20 -top-20 size-80 rounded-full"
            style={{
              background: "radial-gradient(circle, rgba(217,233,229,0.7), transparent 65%)",
            }}
          />
          <div className="relative z-10">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="green" icon={Inbox}>
                Received Handover
              </Badge>
              <StatusBadge status={overview?.readiness.status || "in_progress"} />
            </div>

            <h3 className="mt-4 text-[24px] font-semibold tracking-[-0.025em] text-navy">
              {project.name}
            </h3>
            <p className="mt-1 text-[13.5px] text-muted">
              Transferred from <span className="font-semibold text-navy">{departingName}</span> ·{" "}
              {project.description || "Core repository knowledge and operational handover"}
            </p>

            <dl className="mt-6 grid grid-cols-3 divide-x divide-line rounded-xl border border-line bg-white/80 shadow-2xs">
              <div className="px-4 py-3">
                <dd className="text-[22px] font-semibold tracking-[-0.02em] text-navy font-mono">
                  {totalDecisions}
                </dd>
                <dt className="text-[12px] text-muted font-medium">Decisions</dt>
              </div>
              <div className="px-4 py-3">
                <dd className="text-[22px] font-semibold tracking-[-0.02em] text-navy font-mono">
                  {totalTasks}
                </dd>
                <dt className="text-[12px] text-muted font-medium">Open tasks</dt>
              </div>
              <div className="px-4 py-3">
                <dd className="text-[22px] font-semibold tracking-[-0.02em] text-navy font-mono">
                  {totalRisks}
                </dd>
                <dt className="text-[12px] text-muted font-medium">Risks</dt>
              </div>
            </dl>

            <div className="mt-6 flex flex-wrap gap-2.5">
              <Button
                variant="primary"
                iconRight={ArrowRight}
                onClick={() => router.push("/handover")}
                className="cursor-pointer"
              >
                Open handover
              </Button>
              <Button
                variant="secondary"
                icon={MessageSquareText}
                onClick={() => router.push("/assistant")}
                className="cursor-pointer"
              >
                Ask assistant
              </Button>
            </div>
          </div>
        </Card>

        <Panel title="Recommended next actions" subtitle="Your transition roadmap">
          <ol className="px-3 pb-4">
            {recommendedSteps.map((st, i) => {
              const Icon = st.icon;
              return (
                <li key={st.title}>
                  <Link
                    href={st.to}
                    className="flex items-start gap-3 rounded-lg px-2 py-2.5 transition-colors hover:bg-slate-50"
                  >
                    <span className="flex size-6 shrink-0 items-center justify-center rounded-full border border-line font-mono text-[11px] font-semibold text-brand">
                      {i + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <span className="block text-[13.5px] font-medium text-navy">
                        {st.title}
                      </span>
                      <span className="block truncate text-[12px] text-muted">
                        {st.sub}
                      </span>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ol>
        </Panel>
      </div>

      {/* 3. Important Updates, My Projects, and Attention Items */}
      <div className="grid gap-5 lg:grid-cols-3">
        <Panel title="Important updates" actions={<ViewLink to="/conflicts">All risks</ViewLink>}>
          <ul className="space-y-3 px-5 pb-5 sm:px-6">
            {attentionItems.slice(0, 3).map((item, idx) => (
              <li key={item.id || idx} className="flex items-start gap-2.5">
                <SeverityBadge level="Medium" />
                <span className="text-[13px] leading-snug text-navy truncate">
                  {item.message}
                </span>
              </li>
            ))}
            {attentionItems.length === 0 && (
              <li className="text-xs text-muted py-2">
                No active conflicts or unresolved risks recorded.
              </li>
            )}
          </ul>
        </Panel>

        <Panel title="My projects" actions={<ViewLink to="/projects">View all</ViewLink>}>
          <ul className="px-3 pb-4 space-y-1">
            {projects.slice(0, 4).map((p) => {
              const code = p.name.replace(/[^A-Za-z]/g, "").slice(0, 3).toUpperCase() || "PRJ";
              return (
                <li key={p.id}>
                  <Link
                    href="/overview"
                    className="flex items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-slate-50"
                  >
                    <span
                      className="flex size-6 shrink-0 items-center justify-center rounded-md text-[9.5px] font-bold text-white shadow-2xs"
                      style={{ background: "#315FBA" }}
                    >
                      {code.slice(0, 2)}
                    </span>
                    <span className="flex-1 truncate text-[13px] font-medium text-navy">
                      {p.name}
                    </span>
                    <RoleBadge role="Incoming" />
                  </Link>
                </li>
              );
            })}
          </ul>
        </Panel>

        <Panel title="Project notifications" actions={<ViewLink to="/audit">Audit</ViewLink>}>
          <ul className="px-3 pb-4 space-y-1">
            {attentionItems.slice(0, 3).map((n) => (
              <li key={n.id}>
                <div className="flex gap-2.5 rounded-lg px-2 py-2">
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-brand" />
                  <div className="min-w-0">
                    <span className="block truncate text-[13px] font-medium text-navy">
                      {n.message}
                    </span>
                    <span className="block text-[11px] text-muted">
                      Type: {n.type}
                    </span>
                  </div>
                </div>
              </li>
            ))}
            {attentionItems.length === 0 && (
              <li className="text-xs text-muted py-4 text-center">
                All clear. No notifications.
              </li>
            )}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
