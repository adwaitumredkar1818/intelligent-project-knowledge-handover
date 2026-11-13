"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  FolderPlus,
  Plus,
  Sparkles,
  ClipboardCheck,
  Inbox,
  UserPlus,
  Layers,
  ArrowRight,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import { Button, RoleBadge, cn } from "../ui";
import { ManagerDashboard } from "./ManagerDashboard";
import { OutgoingDashboard } from "./OutgoingDashboard";
import { IncomingDashboard } from "./IncomingDashboard";
import { MemberDashboard } from "./MemberDashboard";
import { WorkspaceDashboard } from "./WorkspaceDashboard";
import { EmptyWorkspaceDashboard } from "./EmptyWorkspaceDashboard";

export type DashboardRole = "manager" | "outgoing" | "incoming" | "member" | "workspace" | "empty";

export function DashboardRouter() {
  const router = useRouter();
  const {
    user,
    activeOrg,
    projects,
    activeProject,
    setActiveProject,
    members,
    overview,
    setIsCreateProjectModalOpen,
    setIsAddMemberModalOpen,
  } = useLiveApp();

  const [mounted, setMounted] = useState(false);
  const [roleOverride, setRoleOverride] = useState<DashboardRole | null>(null);
  const [greetingText, setGreetingText] = useState("Welcome back");
  const [todayText, setTodayText] = useState("Project Workspace");

  useEffect(() => {
    setMounted(true);
    const h = new Date().getHours();
    setGreetingText(h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening");
    setTodayText(
      new Date().toLocaleDateString("en-GB", {
        weekday: "long",
        day: "numeric",
        month: "long",
      })
    );

    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const forcedRole = params.get("role") as DashboardRole | null;
      if (forcedRole && ["manager", "outgoing", "incoming", "member", "workspace", "empty"].includes(forcedRole)) {
        setRoleOverride(forcedRole);
      }
    }
  }, []);

  // 1. Resolve role from real ProjectMember and transition_role
  let resolvedRole: DashboardRole = "empty";

  if (projects.length === 0) {
    resolvedRole = "empty";
  } else if (!activeProject) {
    resolvedRole = "workspace";
  } else {
    const currentMember = members.find(
      (m) => m.user_id === user?.id || m.user_email === user?.email
    );
    const transRole = currentMember?.transition_role;
    const roleName = currentMember?.role_name?.toLowerCase() || "";

    if (transRole === "departing_owner") {
      resolvedRole = "outgoing";
    } else if (transRole === "incoming_assignee") {
      resolvedRole = "incoming";
    } else if (
      transRole === "reviewer" ||
      roleName.includes("manager") ||
      roleName.includes("admin") ||
      roleName.includes("owner") ||
      roleName.includes("lead")
    ) {
      resolvedRole = "manager";
    } else if (currentMember) {
      resolvedRole = "member";
    } else {
      // Default to manager for project owner/lead
      resolvedRole = "manager";
    }
  }

  // Allow URL query parameter for testing/audit without bypassing auth
  const activeRole: DashboardRole = roleOverride ?? resolvedRole;

  const userName = user?.full_name?.split(" ")[0] || (mounted && user?.email?.split("@")[0]) || "there";

  // Contextual header text
  const roleDisplayLabel =
    activeRole === "manager"
      ? "Manager"
      : activeRole === "outgoing"
      ? "Outgoing"
      : activeRole === "incoming"
      ? "Incoming"
      : activeRole === "member"
      ? "Collaborator"
      : "Workspace";

  const attentionCount = overview?.attention_items?.length || 0;

  const summary = {
    manager: activeProject ? (
      <>
        Managing <span className="font-semibold text-navy">{activeProject.name}</span>.{" "}
        {attentionCount > 0 ? (
          <>
            <span className="font-semibold text-navy">{attentionCount} item{attentionCount === 1 ? "" : "s"} require your attention</span>.
          </>
        ) : (
          "All knowledge streams and handovers are progressing normally."
        )}
      </>
    ) : (
      <>Cross-project command center across your accessible workspaces.</>
    ),
    outgoing: activeProject ? (
      <>
        You&apos;re handing over <span className="font-semibold text-navy">{activeProject.name}</span>. Verify what the AI found and fill the gaps only you know.
      </>
    ) : null,
    incoming: activeProject ? (
      <>
        You&apos;ve joined <span className="font-semibold text-navy">{activeProject.name}</span>. Everything below is evidence-grounded knowledge from the previous owner.
      </>
    ) : null,
    member: activeProject ? (
      <>
        Collaborating on <span className="font-semibold text-navy">{activeProject.name}</span>. Browse structured knowledge, decisions, and evidence.
      </>
    ) : null,
    workspace: (
      <>
        Viewing all accessible projects across <span className="font-semibold text-navy">{activeOrg?.name || "The Handover"}</span>.
      </>
    ),
    empty: (
      <>
        Welcome to <span className="font-semibold text-navy">{activeOrg?.name || "The Handover"}</span>. Complete the onboarding steps below to begin.
      </>
    ),
  }[activeRole];

  // Quick action buttons
  const quickActions = {
    manager: [
      {
        label: "New project",
        icon: FolderPlus,
        action: () => setIsCreateProjectModalOpen(true),
        primary: false,
      },
      {
        label: "Manage handovers",
        icon: Plus,
        action: () => router.push("/handover"),
        primary: true,
      },
    ],
    outgoing: [
      {
        label: "Knowledge",
        icon: Sparkles,
        action: () => router.push("/knowledge"),
        primary: false,
      },
      {
        label: "Verify findings",
        icon: ClipboardCheck,
        action: () => router.push("/verification"),
        primary: true,
      },
    ],
    incoming: [
      {
        label: "Explore knowledge",
        icon: Sparkles,
        action: () => router.push("/knowledge"),
        primary: false,
      },
      {
        label: "Open received",
        icon: Inbox,
        action: () => router.push("/handover"),
        primary: true,
      },
    ],
    member: [
      {
        label: "Explore knowledge",
        icon: Sparkles,
        action: () => router.push("/knowledge"),
        primary: false,
      },
      {
        label: "Evidence center",
        icon: Layers,
        action: () => router.push("/evidence"),
        primary: true,
      },
    ],
    workspace: [
      {
        label: "Invite team",
        icon: UserPlus,
        action: () => setIsAddMemberModalOpen(true),
        primary: false,
      },
      {
        label: "Create project",
        icon: Plus,
        action: () => setIsCreateProjectModalOpen(true),
        primary: true,
      },
    ],
    empty: [
      {
        label: "Create project",
        icon: Plus,
        action: () => setIsCreateProjectModalOpen(true),
        primary: true,
      },
    ],
  }[activeRole];

  return (
    <div className="space-y-6">
      {/* 1. Header with Greeting & Quick Actions */}
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-2xl">
          <p className="flex flex-wrap items-center gap-2 text-[12.5px] text-muted">
            <span>{todayText}</span>
            <span className="text-slate-300">·</span>
            <RoleBadge role={roleDisplayLabel} />
          </p>
          <h1 className="mt-2 text-[28px] font-semibold tracking-[-0.03em] text-navy sm:text-[32px]">
            {greetingText}, {userName}
          </h1>
          <p className="mt-1.5 text-[14.5px] leading-relaxed text-[#4a5d7c]">
            {summary}
          </p>
        </div>

        {quickActions && (
          <div className="flex flex-wrap gap-2 shrink-0">
            {quickActions.map((q) => {
              const Icon = q.icon;
              return (
                <Button
                  key={q.label}
                  variant={q.primary ? "primary" : "secondary"}
                  icon={Icon}
                  onClick={q.action}
                  className="cursor-pointer text-xs"
                >
                  {q.label}
                </Button>
              );
            })}
          </div>
        )}
      </header>

      {/* 2. Horizontal Project Switcher Strip */}
      {projects.length > 0 && activeRole !== "empty" && (
        <div className="border-b border-line pb-3">
          <div
            className="scrollbar-thin -mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1"
            role="tablist"
            aria-label="Switch project context"
          >
            {/* All Projects / Workspace Tab */}
            <button
              type="button"
              role="tab"
              aria-selected={!activeProject && activeRole === "workspace"}
              onClick={() => {
                setActiveProject(null as unknown as any);
                setRoleOverride(null);
              }}
              className={cn(
                "flex shrink-0 items-center gap-2 rounded-[10px] border px-3 py-1.5 text-left transition-all duration-200 cursor-pointer",
                !activeProject && activeRole === "workspace"
                  ? "border-line bg-white shadow-2xs font-semibold text-navy"
                  : "border-transparent text-slate-500 hover:bg-white/60 hover:text-navy"
              )}
            >
              <span className="flex size-5.5 items-center justify-center rounded-md bg-navy text-[9.5px] font-bold text-white">
                ALL
              </span>
              <span className="text-[13px]">Workspace Overview</span>
              <span className="font-mono text-[11px] text-muted">({projects.length})</span>
            </button>

            {/* Individual Project Tabs */}
            {projects.map((p) => {
              const isSelected = activeProject?.id === p.id && activeRole !== "workspace";
              const code = p.name.replace(/[^A-Za-z]/g, "").slice(0, 3).toUpperCase() || "PRJ";
              return (
                <button
                  key={p.id}
                  type="button"
                  role="tab"
                  aria-selected={isSelected}
                  onClick={() => {
                    setActiveProject(p);
                    setRoleOverride(null);
                  }}
                  className={cn(
                    "flex shrink-0 items-center gap-2.5 rounded-[10px] border px-3 py-1.5 text-left transition-all duration-200 cursor-pointer",
                    isSelected
                      ? "border-line bg-white shadow-2xs"
                      : "border-transparent hover:bg-white/60"
                  )}
                >
                  <span
                    className="flex size-5.5 items-center justify-center rounded-md text-[9.5px] font-bold text-white shadow-2xs"
                    style={{ background: "#315FBA" }}
                  >
                    {code.slice(0, 2)}
                  </span>
                  <span
                    className={cn(
                      "text-[13px] truncate max-w-[140px]",
                      isSelected ? "font-semibold text-navy" : "font-medium text-[#4a5d7c]"
                    )}
                  >
                    {p.name}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* 3. Render Resolved Dashboard View */}
      <div className="animate-fade">
        {activeRole === "empty" && <EmptyWorkspaceDashboard />}
        {activeRole === "workspace" && <WorkspaceDashboard />}
        {activeRole === "manager" && <ManagerDashboard />}
        {activeRole === "outgoing" && <OutgoingDashboard />}
        {activeRole === "incoming" && <IncomingDashboard />}
        {activeRole === "member" && <MemberDashboard />}
      </div>
    </div>
  );
}
