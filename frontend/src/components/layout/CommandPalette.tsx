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
  Bot,
  Plug,
  ScrollText,
  Settings,
  Sparkles,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import { cn } from "../../lib/utils";

interface CommandItem {
  id: string;
  title: string;
  sub: string;
  to: string;
  icon: React.ComponentType<{ className?: string }>;
  action?: () => void;
}

interface CommandGroup {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
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
    setIsCreateProjectModalOpen,
  } = useLiveApp();

  const [q, setQ] = useState("");

  // Global keyboard shortcut: ⌘K or Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (open) {
          onClose();
        } else {
          // Open palette
          // handled by parent or state
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
        to: "/overview",
        icon: LayoutDashboard,
      },
      {
        id: "nav-projects",
        title: "My Projects",
        sub: "Project workspace directory & coverage",
        to: "/projects",
        icon: FolderKanban,
      },
      {
        id: "nav-team",
        title: "Team Members",
        sub: "Project memberships, roles & transitions",
        to: "/team",
        icon: Users,
      },
      {
        id: "nav-evidence",
        title: "Evidence Center",
        sub: "Connected sources & document repository",
        to: "/evidence",
        icon: FileSearch,
      },
      {
        id: "nav-knowledge",
        title: "Knowledge Intelligence",
        sub: "Structured reconstruction across 8 domains",
        to: "/knowledge",
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
        title: "Project Knowledge Assistant",
        sub: "Permission-filtered conversational assistant",
        to: "/assistant",
        icon: Bot,
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
        to: "/audit",
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
    []
  );

  const groups: CommandGroup[] = useMemo(() => {
    const t = q.toLowerCase().trim();
    const has = (x: string) => !t || x.toLowerCase().includes(t);

    const projectItems: CommandItem[] = projects
      .filter((p) => has(`${p.name} ${p.slug || ""} ${p.description || ""}`))
      .map((p) => ({
        id: `proj-${p.id}`,
        title: p.name,
        sub: p.description || "Active project workspace",
        to: "/overview",
        icon: FolderKanban,
        action: () => setActiveProject(p),
      }));

    const navItems: CommandItem[] = baseNavItems.filter((item) =>
      has(`${item.title} ${item.sub}`)
    );

    const evidenceItems: CommandItem[] = evidenceList
      .filter((e) => has(`${e.title || ""} ${e.provider || ""} ${e.source_type || ""}`))
      .slice(0, 5)
      .map((e) => ({
        id: `ev-${e.id}`,
        title: e.title || "Evidence record",
        sub: `${(e.provider || "DOC").toUpperCase()} · ${e.source_type || "Source"}`,
        to: "/evidence",
        icon: FileSearch,
      }));

    const memberItems: CommandItem[] = members
      .filter((m) => has(`${m.user_full_name || ""} ${m.user_email || ""} ${m.role_name || ""}`))
      .slice(0, 4)
      .map((m) => ({
        id: `mem-${m.id}`,
        title: m.user_full_name || m.user_email || "Member",
        sub: `${m.user_email || ""} · ${m.transition_role || m.role_name || "Member"}`,
        to: "/team",
        icon: Users,
      }));

    const result: CommandGroup[] = [];

    if (projectItems.length > 0) {
      result.push({
        label: "Projects",
        icon: FolderKanban,
        items: projectItems.slice(0, t ? 6 : 4),
      });
    }

    if (navItems.length > 0) {
      result.push({
        label: "Navigation & Modules",
        icon: Sparkles,
        items: navItems.slice(0, t ? 8 : 5),
      });
    }

    if (evidenceItems.length > 0) {
      result.push({
        label: "Evidence Records",
        icon: FileSearch,
        items: evidenceItems,
      });
    }

    if (memberItems.length > 0) {
      result.push({
        label: "Team Members",
        icon: Users,
        items: memberItems,
      });
    }

    return result;
  }, [q, projects, baseNavItems, evidenceList, members, setActiveProject]);

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
        {/* Search Input Bar */}
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
            placeholder="Search projects, handovers, evidence and navigation…"
            className="h-14 flex-1 bg-transparent text-[15px] text-navy outline-none placeholder:text-slate-400"
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
                Try searching for a project name, evidence title, or module name.
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
                    <span className="flex size-7 items-center justify-center rounded-md bg-slate-100 text-slate-500 group-hover:bg-white group-hover:text-brand transition-colors">
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

        {/* Footer Bar */}
        <div className="flex items-center justify-between border-t border-line bg-slate-50/70 px-4 py-2 text-[11px] text-muted font-sans">
          <span>
            <kbd className="font-mono bg-white px-1 py-0.5 rounded border border-line">↵</kbd>{" "}
            open first result
          </span>
          <span>Results respect your active permissions</span>
        </div>
      </div>
    </div>
  );
}
