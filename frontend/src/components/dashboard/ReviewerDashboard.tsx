"use client";

import React from "react";
import { useRouter } from "next/navigation";
import {
  ClipboardCheck,
  Sparkles,
  AlertTriangle,
  Plug,
  CheckCircle2,
  FileCheck2,
  Inbox,
  ShieldCheck,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import { Card, Panel, MetricBand, Badge, RoleBadge, Mono, EmptyState, cn } from "../ui";
import { DashboardAttentionList, type AttentionItem } from "./DashboardAttentionList";
import { NextAction, ViewLink, ActivityTimeline } from "./DashboardHelpers";

export function ReviewerDashboard() {
  const router = useRouter();
  const {
    activeProject,
    projects,
    overview,
    evidenceList,
    user,
  } = useLiveApp();

  const project = activeProject ?? projects[0] ?? null;
  if (!project) return null;

  // Real data calculations
  const readinessPct = overview?.readiness.overall_readiness_pct || 0;
  const attentionItems = overview?.attention_items || [];
  const recentActivities = overview?.recent_activity || [];
  const totalEvidence = overview?.evidence.total_evidence_items || evidenceList.length;
  const totalDecisions = overview?.knowledge.decisions_count || 0;
  const totalTasks = overview?.knowledge.tasks_count || 0;
  const totalRisks = overview?.knowledge.risks_count || 0;

  // Reviewer attention items
  const reviewerAttention: AttentionItem[] = attentionItems.map((item) => {
    const isConflict = item.type?.toLowerCase().includes("conflict");
    const isApproval = item.type?.toLowerCase().includes("approval") || item.type?.toLowerCase().includes("handover");
    return {
      id: item.id,
      tone: isConflict ? "ai" : isApproval ? "amber" : "blue",
      icon: isConflict ? Sparkles : isApproval ? ClipboardCheck : FileCheck2,
      title: item.message,
      sub: `${project.name} · Human Verification Required`,
      cta: isConflict ? "Resolve" : isApproval ? "Review sign-off" : "Verify",
      to: isConflict ? "/conflicts" : isApproval ? "/handover" : "/verification",
    };
  });

  const nextActionItem = reviewerAttention[0];

  // Handover stages progression
  const handoverStages = [
    { label: "Draft", count: project.status === "active" && readinessPct < 30 ? 1 : 0 },
    { label: "In progress", count: project.status === "active" && readinessPct >= 30 && readinessPct < 70 ? 1 : 0 },
    { label: "Pending review", count: attentionItems.length > 0 ? 1 : 0 },
    { label: "Approved", count: readinessPct >= 80 ? 1 : 0 },
    { label: "Published", count: project.status === "completed" ? 1 : 0 },
    { label: "Completed", count: project.status === "completed" ? 1 : 0 },
  ];

  return (
    <div className="space-y-5">
      {/* 1. Next Best Action Banner */}
      {nextActionItem ? (
        <NextAction
          tone={nextActionItem.tone === "ai" ? "amber" : "amber"}
          title={nextActionItem.title}
          body={`Designated reviewer action required on ${project.name}. Reconstructed findings and candidate facts await your human validation.`}
          cta={nextActionItem.cta}
          to={nextActionItem.to}
        />
      ) : (
        <NextAction
          tone="green"
          title="All candidate evidence verified"
          body="No pending reviews or conflicts detected. Handover packages can proceed to final sign-off."
          cta="Verification Center"
          to="/verification"
        />
      )}

      {/* 2. Reviewer KPI Band */}
      <MetricBand
        items={[
          {
            label: "Pending approvals",
            value: attentionItems.length > 0 ? attentionItems.length : 0,
            hint: attentionItems.length > 0 ? "packages waiting sign-off" : "nothing pending",
            tone: attentionItems.length > 0 ? "amber" : "green",
            onClick: () => router.push("/handover"),
          },
          {
            label: "Verification queue",
            value: totalEvidence,
            hint: "evidence items to inspect",
            tone: "blue",
            onClick: () => router.push("/verification"),
          },
          {
            label: "Conflicting evidence",
            value: attentionItems.filter((a) => a.type?.toLowerCase().includes("conflict")).length,
            hint: "contradictory facts",
            tone: attentionItems.some((a) => a.type?.toLowerCase().includes("conflict")) ? "red" : "green",
            onClick: () => router.push("/conflicts"),
          },
          {
            label: "Verified findings",
            value: totalDecisions + totalTasks + totalRisks,
            hint: "grounded knowledge records",
            tone: "indigo",
            onClick: () => router.push("/knowledge"),
          },
        ]}
      />

      {/* 3. Reviewer Verification Queue & Handover Stage Progress */}
      <div className="grid gap-5 lg:grid-cols-[1.75fr_1fr]">
        <Panel
          title="Human Verification & Review Queue"
          subtitle={`Designated review items for ${project.name}`}
          actions={
            <Badge tone={attentionItems.length ? "amber" : "green"}>
              {attentionItems.length} open
            </Badge>
          }
        >
          <DashboardAttentionList
            items={reviewerAttention}
            emptyTitle="All findings verified"
            emptyBody="Candidate facts and handover approval packages will appear here when ready for human review."
          />
        </Panel>

        <Panel
          title="Handover stage progress"
          subtitle={`Workspace progression · ${project.name}`}
          actions={<ViewLink to="/handover">Handovers</ViewLink>}
        >
          <ul className="space-y-3 px-5 pb-5 sm:px-6">
            {handoverStages.map(({ label, count }) => (
              <li key={label}>
                <div className="group grid w-full grid-cols-[110px_1fr_24px] items-center gap-3 text-left">
                  <span className="text-[12.5px] font-medium text-[#4a5d7c] group-hover:text-navy truncate">
                    {label}
                  </span>
                  <span className="h-2 overflow-hidden rounded-full bg-slate-100 flex-1">
                    <span
                      className="block h-full rounded-full transition-all duration-500"
                      style={{
                        width: count > 0 ? "100%" : "0%",
                        background:
                          label === "Completed" || label === "Approved"
                            ? "#299B80"
                            : label === "Pending review"
                            ? "#D39B43"
                            : "#315FBA",
                      }}
                    />
                  </span>
                  <Mono className="text-right text-[11.5px] text-slate-400 font-semibold">
                    {count}
                  </Mono>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      {/* 4. Recent Audit Trail & Knowledge Category Overview */}
      <div className="grid gap-5 lg:grid-cols-[1.75fr_1fr]">
        <Panel
          title="Recent review activity"
          subtitle="Audit log of verification and sign-off actions"
          actions={<ViewLink to="/audit">Audit logs</ViewLink>}
        >
          <ActivityTimeline activities={recentActivities} limit={5} />
        </Panel>

        <Panel
          title="Reconstructed knowledge breakdown"
          subtitle={project.name}
          actions={<ViewLink to="/knowledge">Knowledge hub</ViewLink>}
        >
          <div className="space-y-3 px-5 pb-5 sm:px-6">
            <div className="flex items-center justify-between rounded-lg border border-line p-3">
              <span className="text-xs font-medium text-navy">Decisions & Rationale</span>
              <Mono className="text-xs font-semibold text-brand">{totalDecisions}</Mono>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-line p-3">
              <span className="text-xs font-medium text-navy">Transferred Tasks & Ownership</span>
              <Mono className="text-xs font-semibold text-brand">{totalTasks}</Mono>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-line p-3">
              <span className="text-xs font-medium text-navy">Architectural Blockers & Risks</span>
              <Mono className="text-xs font-semibold text-bad">{totalRisks}</Mono>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
