"use client";

import React from "react";
import { useRouter } from "next/navigation";
import {
  Building2,
  FolderGit2,
  Plus,
  ArrowRight,
  ShieldCheck,
  Plug,
  Layers,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import {
  Card,
  Panel,
  MetricBand,
  Button,
  RoleBadge,
  Mono,
  EmptyState,
  cn,
} from "../ui";
import { ViewLink } from "./DashboardHelpers";

export function WorkspaceDashboard() {
  const router = useRouter();
  const {
    organisations,
    activeOrg,
    projects,
    setActiveProject,
    setIsCreateProjectModalOpen,
  } = useLiveApp();

  const totalProjects = projects.length;
  const activeCount = projects.filter((p) => p.status === "active").length;

  return (
    <div className="space-y-6">
      {/* 1. Cross-Project Workspace KPI Band */}
      <MetricBand
        items={[
          {
            label: "Total projects",
            value: totalProjects,
            hint: `${activeCount} active in ${activeOrg?.name || "workspace"}`,
            tone: "navy",
            onClick: () => router.push("/projects"),
          },
          {
            label: "Accessible handovers",
            value: totalProjects > 0 ? `${totalProjects} available` : "0",
            hint: "across your active teams",
            tone: "blue",
            onClick: () => router.push("/handover"),
          },
          {
            label: "Active organisation",
            value: activeOrg?.name || "The Handover",
            hint: activeOrg?.slug ? `@${activeOrg.slug}` : "enterprise workspace",
            tone: "indigo",
          },
          {
            label: "Workspace status",
            value: "Ready",
            hint: "all services operational",
            tone: "green",
          },
        ]}
      />

      {/* 2. Accessible Projects Hub */}
      <Panel
        title="Accessible Project Workspaces"
        subtitle={`Select a project to enter its role-aware handover dashboard (${projects.length} available)`}
        actions={
          <Button
            size="sm"
            icon={Plus}
            variant="primary"
            onClick={() => setIsCreateProjectModalOpen(true)}
          >
            New project
          </Button>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-5 sm:p-6 border-t border-line">
          {projects.map((p) => {
            const code = p.name.replace(/[^A-Za-z]/g, "").slice(0, 3).toUpperCase() || "PRJ";
            return (
              <div
                key={p.id}
                onClick={() => {
                  setActiveProject(p);
                }}
                className="group relative flex flex-col justify-between rounded-xl border border-line bg-white p-5 shadow-card transition-all duration-200 hover:border-slate-300 hover:shadow-lift cursor-pointer"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span
                      className="flex size-7 items-center justify-center rounded-lg text-[10px] font-bold text-white shadow-2xs"
                      style={{ background: "#315FBA" }}
                    >
                      {code}
                    </span>
                    <RoleBadge role="Member" />
                  </div>
                  <h3 className="text-base font-semibold text-navy group-hover:text-brand transition-colors line-clamp-1">
                    {p.name}
                  </h3>
                  <p className="mt-1 text-xs text-muted line-clamp-2 min-h-[32px]">
                    {p.description || "Project knowledge reconstruction workspace."}
                  </p>
                </div>

                <div className="mt-5 pt-3 border-t border-line flex items-center justify-between text-xs">
                  <span className="font-mono text-[11px] text-slate-400">
                    Status: <span className="font-semibold text-navy uppercase">{p.status}</span>
                  </span>
                  <span className="flex items-center gap-1 font-semibold text-brand group-hover:translate-x-0.5 transition-transform">
                    Enter dashboard <ArrowRight className="size-3.5" />
                  </span>
                </div>
              </div>
            );
          })}

          {projects.length === 0 && (
            <div className="col-span-full py-8">
              <EmptyState
                icon={FolderGit2}
                title="No project workspaces"
                body="Create a project to begin tracking handovers and reconstructing knowledge."
                action={
                  <Button
                    icon={Plus}
                    onClick={() => setIsCreateProjectModalOpen(true)}
                  >
                    Create first project
                  </Button>
                }
              />
            </div>
          )}
        </div>
      </Panel>
    </div>
  );
}
