"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  ArrowRight,
  FolderKanban,
  FileSearch,
  LayoutDashboard,
  Users,
  BrainCircuit,
  Network,
  ClipboardCheck,
  AlertTriangle,
  Workflow,
  Send,
  Plug,
  ScrollText,
  Settings,
  Sparkles,
  MessageSquareText,
  type LucideIcon,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import {
  ROLE_LABEL,
  HANDOVER_STATUS_LABEL,
  type ProjectRole,
} from "../../lib/figmaStore";
import { cn } from "../figma-ui/index";

export interface CommandItem {
  id: string;
  title: string;
  sub: string;
  to: string;
  icon: LucideIcon | React.ComponentType<{ className?: string }>;
  action?: () => void;
}

export interface CommandGroup {
  label: string;
  icon: LucideIcon | React.ComponentType<{ className?: string }>;
  items: CommandItem[];
}

export function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const {
    projects,
    activeProject,
    setActiveProject,
    evidenceList,
    members,
  } = useLiveApp();

  const [q, setQ] = useState("");

  // Global keyboard shortcut: ⌘K or Ctrl+K and Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (open) {
          onClose();
        }
      }
      if (e.key === "Escape" && open) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  // Reset query on open/close
  useEffect(() => {
    if (!open) {
      setQ("");
    }
  }, [open]);

  const baseNavItems: CommandItem[] = useMemo(
    () => [
      {
        id: "nav-overview",
        title: "Overview & Dashboard",
        sub: "Cross-project command center & health",
        to: "/dashboard",
        icon: LayoutDashboard,
      },
      {
        id: "nav-projects",
        title: "Projects",
        sub: "Project workspace directory & coverage",
        to: "/projects",
        icon: FolderKanban,
      },
      {
        id: "nav-team",
        title: "Team Members",
        sub: "Project memberships, roles & transitions",
        to: "/settings/team",
        icon: Users,
      },
      {
        id: "nav-evidence",
        title: "Evidence Center",
        sub: "Connected sources & document repository",
        to: activeProject ? `/projects/${activeProject.id}/evidence` : "/evidence",
        icon: FileSearch,
      },
      {
        id: "nav-knowledge",
        title: "Knowledge Intelligence",
        sub: "Structured reconstruction across 8 domains",
        to: activeProject ? `/projects/${activeProject.id}/knowledge` : "/knowledge",
        icon: BrainCircuit,
      },
      {
        id: "nav-relationships",
        title: "Relationship Explorer",
        sub: "Relational knowledge & dependency graph",
        to: "/relationships",
        icon: Network,
      },
      {
        id: "nav-verification",
        title: "Verification Center",
        sub: "Human-in-the-loop review queue",
        to: "/verification",
        icon: ClipboardCheck,
      },
      {
        id: "nav-conflicts",
        title: "Conflicts",
        sub: "Cross-source contradiction detection",
        to: "/conflicts",
        icon: AlertTriangle,
      },
      {
        id: "nav-handover",
        title: "Handover Workspace",
        sub: "Transition package compiler & checklist",
        to: "/handover",
        icon: Workflow,
      },
      {
        id: "nav-generated-handovers",
        title: "Generated Handovers",
        sub: "Published handover dossiers & sign-offs",
        to: "/generated-handovers",
        icon: Send,
      },
      {
        id: "nav-assistant",
        title: "AI Assistant",
        sub: "Permission-filtered conversational assistant",
        to: "/assistant",
        icon: MessageSquareText,
      },
      {
        id: "nav-sources",
        title: "Connected Sources",
        sub: "GitHub, Jira, Slack & document connectors",
        to: "/sources",
        icon: Plug,
      },
      {
        id: "nav-audit",
        title: "Audit Logs",
        sub: "Immutable PostgreSQL audit trail",
        to: "/settings/audit-logs",
        icon: ScrollText,
      },
      {
        id: "nav-settings",
        title: "Settings",
        sub: "Workspace & project configurations",
        to: "/settings",
        icon: Settings,
      },
    ],
    [activeProject]
  );

  const groups: CommandGroup[] = useMemo(() => {
    const t = q.toLowerCase().trim();
    const has = (x: string) => !t || x.toLowerCase().includes(t);

    // Only show live projects from context
    const allProjects = projects;

    const projectItems: CommandItem[] = allProjects
      .filter((p) => has(`${p.name} ${(p as { slug?: string }).slug || ""} ${p.description || ""}`))
      .map((p) => ({
        id: `proj-${p.id}`,
        title: p.name,
        sub: (p as { role?: string }).role
          ? ROLE_LABEL[(p as { role?: string }).role as ProjectRole] || p.description || "Active project"
          : p.description || "Active project workspace",
        to: `/projects/${p.id}`,
        icon: FolderKanban,
        action: () => {
          if ("organisation_id" in p) {
            setActiveProject(p as unknown as Parameters<typeof setActiveProject>[0]);
          }
        },
      }));

    // Handovers from figmaStore
    const handoverItems: CommandItem[] = [];

    // Knowledge (Decisions, Tasks, Risks)
    const knowledgeItems: CommandItem[] = [];

    // Evidence
    const allEvidence = evidenceList.map((e) => ({
      id: e.id,
      title: e.title || "Evidence record",
      sub: `${(e.provider || "DOC").toUpperCase()} · ${e.source_type || "Source"}`,
      to: `/evidence`,
    }));

    const matchedEvidence: CommandItem[] = allEvidence
      .filter((e) => has(`${e.title} ${e.sub}`))
      .slice(0, 5)
      .map((e) => ({
        id: `ev-${e.id}`,
        title: e.title,
        sub: e.sub,
        to: e.to,
        icon: FileSearch,
      }));

    // Navigation & Modules
    const navItems: CommandItem[] = baseNavItems.filter((item) =>
      has(`${item.title} ${item.sub}`)
    );

    const result: CommandGroup[] = [];

    if (projectItems.length > 0) {
      result.push({
        label: "Projects",
        icon: FolderKanban,
        items: projectItems.slice(0, t ? 6 : 3),
      });
    }

    if (handoverItems.length > 0) {
      result.push({
        label: "Handovers",
        icon: Workflow,
        items: handoverItems.slice(0, t ? 6 : 3),
      });
    }

    if (knowledgeItems.length > 0) {
      result.push({
        label: "Knowledge & Intelligence",
        icon: Sparkles,
        items: knowledgeItems.slice(0, t ? 6 : 3),
      });
    }

    if (matchedEvidence.length > 0) {
      result.push({
        label: "Evidence",
        icon: FileSearch,
        items: matchedEvidence.slice(0, t ? 6 : 3),
      });
    }

    if (navItems.length > 0) {
      result.push({
        label: "Navigation & Modules",
        icon: LayoutDashboard,
        items: navItems.slice(0, t ? 8 : 4),
      });
    }

    return result;
  }, [q, projects, baseNavItems, evidenceList, setActiveProject]);

  if (!open) return null;

  const allItems = groups.flatMap((g) => g.items);
  const firstItem = allItems[0];

  const handleSelect = (item: CommandItem) => {
    if (item.action) {
      item.action();
    }
    router.push(item.to);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-[70] flex items-start justify-center bg-navy/30 p-3 pt-[10vh] backdrop-blur-[2px]"
      onMouseDown={onClose}
    >
      <div
        className="animate-fade w-full max-w-xl overflow-hidden rounded-2xl bg-white shadow-pop border border-line"
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Search Input Header */}
        <div className="flex items-center gap-3 border-b border-line px-4">
          <Search className="size-5 text-slate-400 shrink-0" />
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && firstItem) {
                handleSelect(firstItem);
              }
            }}
            placeholder="Search projects, handovers, knowledge and evidence…"
            className="h-14 flex-1 bg-transparent text-[15px] text-navy outline-none placeholder:text-slate-400 font-sans"
          />
          <kbd className="rounded border border-line px-1.5 py-0.5 text-[11px] font-mono text-slate-500 bg-slate-50">
            Esc
          </kbd>
        </div>

        {/* Results List */}
        <div className="max-h-[60vh] overflow-y-auto p-2 scrollbar-thin">
          {groups.length === 0 ? (
            <div className="px-4 py-10 text-center">
              <p className="text-sm font-semibold text-navy">No results for “{q}”</p>
              <p className="mt-1 text-xs text-muted">
                Try a project name, handover code (HO-1042) or evidence reference.
              </p>
            </div>
          ) : (
            groups.map((group) => (
              <div key={group.label} className="mb-2">
                <p className="px-2.5 py-1 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-[#97a3b8]">
                  {group.label}
                </p>
                {group.items.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => handleSelect(item)}
                    className="group flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left hover:bg-tint transition-colors cursor-pointer"
                  >
                    <span className="flex size-7 items-center justify-center rounded-md bg-slate-100 text-slate-500 group-hover:bg-white group-hover:text-brand transition-colors shrink-0">
                      <item.icon className="size-3.5" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[13.5px] font-medium text-navy">
                        {item.title}
                      </span>
                      <span className="block truncate text-[11px] text-muted">
                        {item.sub}
                      </span>
                    </span>
                    <ArrowRight className="size-3.5 text-slate-300 group-hover:text-brand transition-colors shrink-0" />
                  </button>
                ))}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-line bg-slate-50/70 px-4 py-2 text-[11px] text-muted font-sans">
          <span>
            <kbd className="font-mono bg-white px-1 py-0.5 rounded border border-line">
              ↵
            </kbd>{" "}
            open first result
          </span>
          <span>Results respect your active permissions</span>
        </div>
      </div>
    </div>
  );
}
