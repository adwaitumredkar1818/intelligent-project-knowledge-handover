"use client";

import React from "react";
import {
  FolderPlus,
  Plug,
  UserPlus,
  Workflow,
  Plus,
  Building2,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import {
  Card,
  MetricBand,
  Button,
  Mono,
  SectionLabel,
  SphereVisual,
} from "../ui";

export function EmptyWorkspaceDashboard() {
  const {
    activeOrg,
    organisations,
    setIsCreateProjectModalOpen,
    setIsAddSourceModalOpen,
    setIsAddMemberModalOpen,
    setIsCreateOrgModalOpen,
  } = useLiveApp();

  const orgName = activeOrg?.name || (organisations[0]?.name ?? "Workspace Sandbox");

  const steps = [
    {
      icon: FolderPlus,
      title: "Create your first project",
      body: "Projects group evidence sources, team members and handover workflows.",
      action: () => setIsCreateProjectModalOpen(true),
      cta: "Create project",
      primary: true,
    },
    {
      icon: Plug,
      title: "Connect a data source",
      body: "Connect authorized GitHub repositories, Jira instances, or document files.",
      action: () => setIsAddSourceModalOpen(true),
      cta: "Connect source",
      primary: false,
    },
    {
      icon: UserPlus,
      title: "Invite your team members",
      body: "Define managers, departing owners, and incoming assignees.",
      action: () => setIsAddMemberModalOpen(true),
      cta: "Invite team",
      primary: false,
    },
    {
      icon: Workflow,
      title: "Start knowledge handover",
      body: "Reconstruct knowledge and establish full evidence-grounded provenance.",
      action: () => setIsCreateProjectModalOpen(true),
      cta: "Start handover",
      primary: false,
    },
  ];

  return (
    <div className="space-y-5">
      {/* 1. Empty Metric Band */}
      <MetricBand
        items={[
          { label: "Projects", value: <span className="text-slate-300 font-mono">—</span>, hint: "No data yet", tone: "gray" },
          { label: "Active handovers", value: <span className="text-slate-300 font-mono">—</span>, hint: "No data yet", tone: "gray" },
          { label: "Connected sources", value: <span className="text-slate-300 font-mono">—</span>, hint: "No data yet", tone: "gray" },
          { label: "Verified findings", value: <span className="text-slate-300 font-mono">—</span>, hint: "No data yet", tone: "gray" },
        ]}
      />

      {/* 2. Onboarding Stepper Card */}
      <Card className="p-6 sm:p-8 shadow-card">
        <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-center">
          <div>
            <SectionLabel>Getting started · 0 of 4</SectionLabel>
            <h2 className="mt-3 text-[22px] font-semibold tracking-[-0.02em] text-navy">
              Set up {orgName}
            </h2>
            <p className="mt-1 max-w-xl text-[14px] text-muted">
              This workspace has no projects or handovers configured yet. As you connect tools
              and verify findings, the Organic Knowledge Sphere and handover records assemble automatically.
            </p>
          </div>
          <SphereVisual
            variant="empty"
            emptyKind="project"
            interactive={false}
            className="mx-auto size-36 shrink-0 sm:mx-0"
          />
        </div>

        {/* 4 Steps Grid */}
        <ol className="mt-7 grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((st, i) => {
            const Icon = st.icon;
            return (
              <li key={st.title} className="flex flex-col bg-white p-5">
                <div className="flex items-center justify-between">
                  <Icon className="size-5 text-brand" />
                  <Mono className="text-[11px] text-slate-400">0{i + 1}</Mono>
                </div>
                <p className="mt-4 text-[14px] font-semibold text-navy">
                  {st.title}
                </p>
                <p className="mt-1 flex-1 text-[12.5px] text-muted">
                  {st.body}
                </p>
                <Button
                  size="sm"
                  variant={st.primary ? "primary" : "secondary"}
                  className="mt-5 w-full cursor-pointer text-xs"
                  onClick={st.action}
                >
                  {st.cta}
                </Button>
              </li>
            );
          })}
        </ol>
      </Card>
    </div>
  );
}
