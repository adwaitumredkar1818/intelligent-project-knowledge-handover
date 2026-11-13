"use client";

import React from "react";
import { useRouter } from "next/navigation";
import {
  BrainCircuit,
  Database,
  FileSearch,
  Network,
  Users,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import { Card, Panel, MetricBand, Button, RoleBadge } from "../ui";
import { ViewLink, ActivityTimeline } from "./DashboardHelpers";

export function MemberDashboard() {
  const router = useRouter();
  const {
    activeProject,
    overview,
    members,
    sourceMappings,
    evidenceList,
  } = useLiveApp();

  if (!activeProject) return null;

  const totalDecisions = overview?.knowledge.decisions_count || 0;
  const totalTasks = overview?.knowledge.tasks_count || 0;
  const totalRisks = overview?.knowledge.risks_count || 0;
  const totalEvid = overview?.evidence.total_evidence_items || evidenceList.length;
  const recentActivities = overview?.recent_activity || [];

  return (
    <div className="space-y-5">
      {/* 1. KPI Band */}
      <MetricBand
        items={[
          {
            label: "Project status",
            value: activeProject.status === "active" ? "Active" : "Archived",
            hint: `${activeProject.name}`,
            tone: "blue",
            onClick: () => router.push("/projects"),
          },
          {
            label: "Knowledge items",
            value: totalEvid > 0 ? totalEvid : totalDecisions + totalTasks,
            hint: "extracted & indexed records",
            tone: "green",
            onClick: () => router.push("/knowledge"),
          },
          {
            label: "Connected sources",
            value: sourceMappings.length,
            hint: "active data connectors",
            tone: sourceMappings.length > 0 ? "indigo" : "gray",
            onClick: () => router.push("/sources"),
          },
          {
            label: "Team members",
            value: members.length,
            hint: "collaborators & participants",
            tone: "navy",
            onClick: () => router.push("/team"),
          },
        ]}
      />

      {/* 2. Project Exploration Hub */}
      <div className="grid gap-5 lg:grid-cols-[1.75fr_1fr]">
        <Card className="p-6 sm:p-7 shadow-card">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <RoleBadge role="Member" />
            <span className="text-xs text-muted">Collaborator View</span>
          </div>

          <h2 className="text-[22px] font-semibold tracking-[-0.02em] text-navy">
            {activeProject.name} Knowledge Hub
          </h2>
          <p className="mt-1 text-[13.5px] text-muted max-w-xl">
            {activeProject.description ||
              "Explore verified technical decisions, ownership boundaries, and architectural dependencies extracted across connected repositories and documentation."}
          </p>

          <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <button
              type="button"
              onClick={() => router.push("/knowledge")}
              className="flex flex-col p-4 rounded-xl border border-line bg-slate-50/50 hover:bg-white hover:border-slate-300 hover:shadow-xs transition text-left cursor-pointer"
            >
              <BrainCircuit className="size-5 text-brand mb-2" />
              <span className="text-sm font-semibold text-navy">Knowledge Explorer</span>
              <span className="text-xs text-muted mt-0.5">
                {totalDecisions} decisions, {totalTasks} tasks
              </span>
            </button>

            <button
              type="button"
              onClick={() => router.push("/relationships")}
              className="flex flex-col p-4 rounded-xl border border-line bg-slate-50/50 hover:bg-white hover:border-slate-300 hover:shadow-xs transition text-left cursor-pointer"
            >
              <Network className="size-5 text-indigo-600 mb-2" />
              <span className="text-sm font-semibold text-navy">Relationship Explorer</span>
              <span className="text-xs text-muted mt-0.5">Dependency graph</span>
            </button>

            <button
              type="button"
              onClick={() => router.push("/evidence")}
              className="flex flex-col p-4 rounded-xl border border-line bg-slate-50/50 hover:bg-white hover:border-slate-300 hover:shadow-xs transition text-left cursor-pointer"
            >
              <FileSearch className="size-5 text-teal-600 mb-2" />
              <span className="text-sm font-semibold text-navy">Evidence Center</span>
              <span className="text-xs text-muted mt-0.5">
                {totalEvid} source documents
              </span>
            </button>
          </div>
        </Card>

        <Panel
          title="Team members"
          subtitle={`${members.length} members in workspace`}
          actions={<ViewLink to="/team">All members</ViewLink>}
        >
          <ul className="px-5 pb-5 sm:px-6 space-y-3">
            {members.slice(0, 5).map((m) => (
              <li key={m.id} className="flex items-center justify-between text-xs">
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-navy truncate">
                    {m.user_full_name || m.user_email || "Member"}
                  </p>
                  <p className="text-[11px] text-muted truncate">
                    {m.user_email}
                  </p>
                </div>
                <RoleBadge role={m.role_name || "Member"} />
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      {/* 3. Recent Activity */}
      <Panel
        title="Recent project activity"
        subtitle="Chronological audit history"
        actions={<ViewLink to="/audit">Audit trail</ViewLink>}
      >
        <ActivityTimeline activities={recentActivities} limit={5} />
      </Panel>
    </div>
  );
}
