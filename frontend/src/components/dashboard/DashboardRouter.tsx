"use client";

import React, { useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import {
  FolderPlus,
  Plus,
  Sparkles,
  ClipboardCheck,
  Inbox,
  UserPlus,
  Layers,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import { Button, RoleBadge, cn } from "../ui";
import { ManagerDashboard } from "./ManagerDashboard";
import { ReviewerDashboard } from "./ReviewerDashboard";
import { OutgoingDashboard } from "./OutgoingDashboard";
import { IncomingDashboard } from "./IncomingDashboard";
import { MemberDashboard } from "./MemberDashboard";
import { WorkspaceDashboard } from "./WorkspaceDashboard";
import { EmptyWorkspaceDashboard } from "./EmptyWorkspaceDashboard";

export type DashboardRole = "manager" | "reviewer" | "outgoing" | "incoming" | "member" | "workspace" | "empty";

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

  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );

  const h = new Date().getHours();
  const greetingText = mounted
    ? h < 12
      ? "Good morning"
      : h < 18
      ? "Good afternoon"
      : "Good evening"
    : "Welcome back";

  const todayText = mounted
    ? new Date().toLocaleDateString("en-GB", {
        weekday: "long",
        day: "numeric",
        month: "long",
      })
    : "Project Workspace";

  // 1. Authoritative role resolution from real ProjectMember, ProjectTransition and Overview
  let resolvedRole: DashboardRole = "empty";

  if (projects.length === 0) {
    resolvedRole = "empty";
  } else if (!activeProject) {
    resolvedRole = "workspace";
  } else {
    // Isolate context to the currently active project
    const currentOverview = overview && overview.project_id === activeProject.id ? overview : null;
    const currentMembers = members.filter((m) => m.project_id === activeProject.id);

    // Match current user in active project membership
    const currentMember = currentMembers.find(
      (m) =>
        m.user_id === user?.id ||
        (m.user_email && m.user_email === user?.email) ||
        (m.email && m.email === user?.email)
    );

    const isDeparting =
      currentMember?.transition_role === "departing_owner" ||
      (currentOverview?.departing_member?.id != null && currentOverview?.departing_member?.id === user?.id) ||
      (currentOverview?.departing_member?.email != null && currentOverview?.departing_member?.email === user?.email);

    const isSuccessor =
      currentMember?.transition_role === "incoming_assignee" ||
      (currentOverview?.successor?.id != null && currentOverview?.successor?.id === user?.id) ||
      (currentOverview?.successor?.email != null && currentOverview?.successor?.email === user?.email);

    const roleName =
      currentMember?.role_name?.toLowerCase() ||
      activeProject.my_project_role?.toLowerCase() ||
      "";

    if (isDeparting) {
      resolvedRole = "outgoing";
    } else if (isSuccessor) {
      resolvedRole = "incoming";
    } else if (roleName === "reviewer") {
      resolvedRole = "reviewer";
    } else if (
      roleName.includes("manager") ||
      roleName.includes("admin") ||
      roleName.includes("owner") ||
      activeProject.owner_id === user?.id
    ) {
      resolvedRole = "manager";
    } else if (currentMember) {
      resolvedRole = "member";
    } else {
      resolvedRole = "member";
    }
  }

  // Security enforcement: Role cannot be spoofed or overridden via URL query parameters
  const activeRole: DashboardRole = resolvedRole;

  const userName = user?.full_name?.split(" ")[0] || (mounted && user?.email?.split("@")[0]) || "there";

  // Contextual header text
  const roleDisplayLabel =
    activeRole === "manager"
      ? "Manager"
      : activeRole === "reviewer"
      ? "Reviewer"
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
    reviewer: activeProject ? (
      <>
        Reviewing <span className="font-semibold text-navy">{activeProject.name}</span>. Inspect reconstructed knowledge, resolve conflicts, and issue handover approvals.
      </>
    ) : null,
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
    reviewer: [
      {
        label: "Conflicts",
        icon: Sparkles,
        action: () => router.push("/conflicts"),
        primary: false,
      },
      {
        label: "Verification Center",
        icon: ClipboardCheck,
        action: () => router.push("/verification"),
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
                setActiveProject(null);
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
        {activeRole === "reviewer" && <ReviewerDashboard />}
        {activeRole === "outgoing" && <OutgoingDashboard />}
        {activeRole === "incoming" && <IncomingDashboard />}
        {activeRole === "member" && <MemberDashboard />}
      </div>
    </div>
  );
}
