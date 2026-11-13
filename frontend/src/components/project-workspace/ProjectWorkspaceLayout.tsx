"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  Database,
  Workflow,
  Sparkles,
  ShieldCheck,
  Loader2,
  FolderGit2,
} from "lucide-react";
import { Button, Card, RoleBadge, StatusBadge, cn } from "../ui";
import {
  PROJECT_TABS,
  getProjectCode,
  getProjectColor,
  type ProjectTabItem,
} from "./project-utils";
import { ProjectOverviewTab } from "./ProjectOverviewTab";
import { ProjectTeamTab } from "./ProjectTeamTab";
import { ProjectSettingsTab } from "./ProjectSettingsTab";
import { ProjectActivityTab } from "./ProjectActivityTab";
import { useLiveApp } from "../../context/LiveAppContext";
import { api } from "../../lib/api";
import type { Project, ProjectOverview, ProjectTransition } from "../../lib/types";

export interface ProjectWorkspaceLayoutProps {
  projectId: string;
}

export function ProjectWorkspaceLayout({
  projectId,
}: ProjectWorkspaceLayoutProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setActiveProject } = useLiveApp();

  const tabParam = searchParams.get("tab") as ProjectTabItem["id"] | null;
  const activeTab: ProjectTabItem["id"] =
    tabParam && ["overview", "team", "settings", "activity"].includes(tabParam)
      ? tabParam
      : "overview";

  const [project, setProject] = useState<Project | null>(null);
  const [overview, setOverview] = useState<ProjectOverview | null>(null);
  const [transition, setTransition] = useState<ProjectTransition | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load project details
  useEffect(() => {
    let mounted = true;

    Promise.all([
      api.projects.get(projectId),
      api.projects.getOverview(projectId).catch(() => null),
      api.projects.getTransition(projectId).catch(() => null),
    ])
      .then(([proj, ov, tr]) => {
        if (!mounted) return;
        setProject(proj);
        setOverview(ov);
        setTransition(tr);
        setActiveProject(proj);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load project workspace."
        );
      })
      .finally(() => {
        if (mounted) setIsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [projectId, setActiveProject]);

  const handleTabChange = (tabId: ProjectTabItem["id"]) => {
    router.replace(`/projects/${projectId}?tab=${tabId}`, { scroll: false });
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 text-center space-y-3">
        <Loader2 className="size-6 animate-spin text-brand" />
        <p className="text-xs text-muted font-medium">
          Loading project workspace...
        </p>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="p-8 max-w-xl mx-auto text-center space-y-4">
        <Card className="p-8">
          <FolderGit2 className="size-12 text-slate-300 mx-auto mb-3" />
          <h2 className="text-base font-bold text-navy">Project Workspace Not Found</h2>
          <p className="text-xs text-muted mt-1 mb-5">
            {error || "The requested project workspace does not exist or you lack access permissions."}
          </p>
          <Link href="/projects">
            <Button variant="secondary" icon={ArrowLeft}>
              Back to Projects Directory
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  const role = project.my_project_role || "project_member";
  const isManager =
    role.toLowerCase().includes("manager") ||
    project.effective_permissions?.includes("project.manage") ||
    false;

  const projectCode = getProjectCode(project.name, project.slug);
  const projectColor = getProjectColor(project.id);

  return (
    <div className="space-y-6">
      {/* Back Link */}
      <div>
        <Link
          href="/projects"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted hover:text-navy transition-colors"
        >
          <ArrowLeft className="size-3.5" />
          <span>Projects Directory</span>
        </Link>
      </div>

      {/* Project Header matching Figma Make */}
      <div className="border-b border-line pb-4">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3.5">
            <span
              className="flex size-12 shrink-0 items-center justify-center rounded-xl text-sm font-bold text-white shadow-xs"
              style={{ background: projectColor }}
            >
              {projectCode}
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-navy">
                  {project.name}
                </h1>
                <RoleBadge role={role} />
                <StatusBadge status={project.status || "active"} />
              </div>
              <p className="mt-1 max-w-2xl text-xs text-muted leading-relaxed">
                {project.description ||
                  "Authoritative handover project workspace with isolated vector collection."}
              </p>
            </div>
          </div>

          {/* Action Buttons based on User Role */}
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {isManager ? (
              <>
                <Link href="/evidence">
                  <Button variant="secondary" size="sm" icon={Database}>
                    Sources
                  </Button>
                </Link>
                <Link href="/handovers">
                  <Button variant="primary" size="sm" icon={Workflow}>
                    Create Handover
                  </Button>
                </Link>
              </>
            ) : role.includes("incoming") ? (
              <Link href="/evidence">
                <Button variant="primary" size="sm" icon={Sparkles}>
                  Explore Knowledge
                </Button>
              </Link>
            ) : role.includes("outgoing") ? (
              <Link href="/verification">
                <Button variant="primary" size="sm" icon={ShieldCheck}>
                  Verify Knowledge
                </Button>
              </Link>
            ) : (
              <Link href="/evidence">
                <Button variant="secondary" size="sm" icon={Database}>
                  View Evidence
                </Button>
              </Link>
            )}
          </div>
        </div>

        {/* Tab Navigation Strip */}
        <div className="mt-5 flex gap-1 border-t border-line/60 pt-2 overflow-x-auto scrollbar-none">
          {PROJECT_TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => handleTabChange(tab.id)}
                className={cn(
                  "relative flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-lg transition-colors cursor-pointer",
                  isActive
                    ? "text-brand bg-tint/40 font-semibold"
                    : "text-muted hover:text-navy hover:bg-slate-50"
                )}
              >
                <Icon className={cn("size-3.5", isActive && "text-brand")} />
                <span>{tab.label}</span>
                {isActive && (
                  <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-brand rounded-full" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Render Active Tab */}
      <div>
        {activeTab === "overview" && (
          <ProjectOverviewTab
            project={project}
            overview={overview}
            transition={transition}
            isLoading={isLoading}
            onNavigateTab={handleTabChange}
          />
        )}

        {activeTab === "team" && (
          <ProjectTeamTab project={project} canManage={isManager} />
        )}

        {activeTab === "settings" && (
          <ProjectSettingsTab
            project={project}
            transition={transition}
            canManage={isManager}
            onProjectUpdated={(upd) => setProject(upd)}
          />
        )}

        {activeTab === "activity" && <ProjectActivityTab project={project} />}
      </div>
    </div>
  );
}
