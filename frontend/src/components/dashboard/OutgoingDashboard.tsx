"use client";

import React from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  FileQuestion,
  Sparkles,
  Workflow,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import { Card, Panel, MetricBand, EmptyState, Confidence } from "../ui";
import { HandoverProgressRing } from "./HandoverProgressRing";
import { DashboardChecklist, type ChecklistStep } from "./DashboardChecklist";
import { NextAction, ViewLink, ActivityTimeline } from "./DashboardHelpers";

export function OutgoingDashboard() {
  const router = useRouter();
  const {
    activeProject,
    overview,
    members,
    user,
    evidenceList,
  } = useLiveApp();

  if (!activeProject) return null;

  // Real data resolution
  const readinessPct = overview?.readiness.overall_readiness_pct || 45;
  const attentionItems = overview?.attention_items || [];
  const recentActivities = overview?.recent_activity || [];
  const targetDate = overview?.target_handover_date || activeProject.target_handover_date || "End of month";

  // Identify incoming successor from members list
  const successorMember = members.find((m) => m.transition_role === "incoming_assignee");
  const successorName = successorMember?.user_full_name || successorMember?.user_email || "Incoming successor";

  const totalDecisions = overview?.knowledge.decisions_count || 0;
  const totalTasks = overview?.knowledge.tasks_count || 0;
  const totalRisks = overview?.knowledge.risks_count || 0;
  const totalEvid = overview?.evidence.total_evidence_items || evidenceList.length;

  const pendingVerificationCount = attentionItems.filter((a) => a.type?.toLowerCase().includes("verif") || a.type?.toLowerCase().includes("review")).length || Math.max(1, attentionItems.length);
  const missingInfoCount = attentionItems.filter((a) => a.type?.toLowerCase().includes("gap") || a.type?.toLowerCase().includes("missing")).length;

  // 5-step checklist
  const checklistSteps: ChecklistStep[] = [
    {
      label: "Review AI-generated findings",
      done: readinessPct >= 70,
      meta: `${Math.round(readinessPct)}% complete`,
      onClick: () => router.push("/verification"),
    },
    {
      label: "Answer missing information & project gaps",
      done: missingInfoCount === 0,
      meta: missingInfoCount > 0 ? `${missingInfoCount} open questions` : "all clear",
      onClick: () => router.push("/verification"),
    },
    {
      label: "Confirm pending tasks and responsibilities",
      done: totalTasks > 0 && readinessPct >= 50,
      meta: `${totalTasks} items tracked`,
      onClick: () => router.push("/knowledge"),
    },
    {
      label: "Flag unresolved architectural blockers & risks",
      done: totalRisks === 0 || readinessPct >= 60,
      meta: totalRisks > 0 ? `${totalRisks} risks flagged` : "none detected",
      onClick: () => router.push("/conflicts"),
    },
    {
      label: "Submit handover package for manager approval",
      done: readinessPct >= 90,
      meta: overview?.readiness.status || "In progress",
      onClick: () => router.push("/handover"),
    },
  ];

  return (
    <div className="space-y-5">
      {/* 1. Next Best Action */}
      <NextAction
        tone="amber"
        title={`Verify ${pendingVerificationCount} findings before handover`}
        body={`${successorName} takes over ${activeProject.name} on ${targetDate}. Review evidence-grounded findings to complete your checklist.`}
        cta="Continue verification"
        to="/verification"
      />

      {/* 2. KPI Band */}
      <MetricBand
        items={[
          {
            label: "My active handover",
            value: "1 active",
            hint: `${activeProject.name}`,
            tone: "blue",
            onClick: () => router.push("/handover"),
          },
          {
            label: "Pending verification",
            value: pendingVerificationCount,
            hint: "findings to confirm",
            tone: "amber",
            onClick: () => router.push("/verification"),
          },
          {
            label: "Missing information",
            value: missingInfoCount,
            hint: "questions only you can answer",
            tone: missingInfoCount > 0 ? "red" : "green",
            onClick: () => router.push("/verification"),
          },
          {
            label: "Pending responsibilities",
            value: totalTasks,
            hint: "tasks to transfer",
            tone: "indigo",
            onClick: () => router.push("/knowledge"),
          },
        ]}
      />

      {/* 3. Handover Progress Card & Missing Information */}
      <div className="grid gap-5 lg:grid-cols-[1.75fr_1fr]">
        <Card className="p-5 sm:p-6 shadow-card">
          <HandoverProgressRing
            code={activeProject.slug?.toUpperCase() || "HO-01"}
            status={readinessPct >= 80 ? "approved" : "in_progress"}
            progress={readinessPct}
            assigneeName={successorName}
            scope={activeProject.description || "Project knowledge and responsibilities handover"}
            dueDate={targetDate}
          />
          <div className="mt-6">
            <DashboardChecklist steps={checklistSteps} />
          </div>
        </Card>

        <Panel
          title="Missing information"
          subtitle="Questions requiring human knowledge"
          actions={<ViewLink to="/verification">Verification</ViewLink>}
        >
          <ul className="space-y-2.5 px-5 pb-5 sm:px-6">
            {attentionItems.slice(0, 3).map((item, idx) => (
              <li key={item.id || idx} className="rounded-xl border border-line p-3.5 bg-slate-50/50">
                <p className="text-[13px] font-semibold text-navy leading-snug">
                  {item.message}
                </p>
                <p className="mt-1 text-[11.5px] text-muted">
                  Requires departing owner confirmation before handover sign-off.
                </p>
                <button
                  onClick={() => router.push("/verification")}
                  className="mt-2 text-[12px] font-semibold text-brand hover:underline cursor-pointer"
                >
                  Answer now &rarr;
                </button>
              </li>
            ))}
            {attentionItems.length === 0 && (
              <EmptyState
                className="py-6"
                icon={CheckCircle2}
                title="All questions answered"
                body="No pending gaps detected. Reviewers can inspect your confirmed records."
              />
            )}
          </ul>
        </Panel>
      </div>

      {/* 4. Pending Verification Queue & Recent Updates */}
      <div className="grid gap-5 lg:grid-cols-[1.75fr_1fr]">
        <Panel
          title="Pending verification queue"
          subtitle="Grounding confidence ranking"
          actions={<ViewLink to="/verification">Full queue</ViewLink>}
        >
          <ul className="divide-y divide-line border-t border-line">
            {evidenceList.slice(0, 5).map((e) => (
              <li
                key={e.id}
                onClick={() => router.push(`/evidence`)}
                className="flex flex-col gap-2 px-5 py-3 sm:flex-row sm:items-center sm:px-6 hover:bg-slate-50/60 transition cursor-pointer"
              >
                <span className="w-24 shrink-0 text-[11.5px] font-semibold uppercase text-muted font-mono">
                  {e.source_type || e.provider}
                </span>
                <span className="min-w-0 flex-1 truncate text-[13.5px] font-medium text-navy">
                  {e.title}
                </span>
                <Confidence value={88} compact />
              </li>
            ))}
            {evidenceList.length === 0 && (
              <li className="py-6 text-center text-xs text-muted">
                No items currently queued for verification.
              </li>
            )}
          </ul>
        </Panel>

        <Panel
          title="Recent project updates"
          subtitle={activeProject.name}
          actions={<ViewLink to="/audit">Audit trail</ViewLink>}
        >
          <ActivityTimeline activities={recentActivities} limit={5} />
        </Panel>
      </div>
    </div>
  );
}
