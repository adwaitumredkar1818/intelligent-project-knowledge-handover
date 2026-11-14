"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  FolderKanban,
  Users,
  Database,
  BrainCircuit,
  Network,
  ClipboardCheck,
  AlertTriangle,
  Workflow,
  Send,
  Plug,
  ScrollText,
  Settings,
  X,
  LogOut,
  ChevronDown,
  ChevronsUpDown,
  Search,
  Plus,
  Building2,
  FileSearch,
  CheckCircle2,
  MessageSquareText,
  type LucideIcon,
} from "lucide-react";
import { Logo, LogoMark } from "../figma-ui/brand";
import {
  Avatar,
  Badge,
  Dropdown,
  MenuItem,
  Tooltip,
  cn,
} from "../figma-ui/index";
import { useLiveApp } from "../../context/LiveAppContext";
import {
  ROLE_LABEL,
  type ProjectRole,
} from "../../lib/figmaStore";

export const ROLE_TONE: Record<ProjectRole, "blue" | "amber" | "green"> = {
  manager: "blue",
  outgoing: "amber",
  incoming: "green",
};

export function RoleBadge({
  role,
  className,
}: {
  role: ProjectRole | string;
  className?: string;
}) {
  const norm = (
    typeof role === "string" ? role.toLowerCase() : role
  ) as ProjectRole;
  const tone = ROLE_TONE[norm] || "blue";
  const label =
    ROLE_LABEL[norm as keyof typeof ROLE_LABEL] ||
    (typeof role === "string" ? role : "Member");
  return (
    <Badge tone={tone} dot className={className}>
      {label}
    </Badge>
  );
}

interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon | React.ComponentType<{ className?: string; strokeWidth?: number }>;
  badge?: number;
  match?: string;
  accent?: boolean;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

function WorkspaceSwitcher({ collapsed }: { collapsed: boolean }) {
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => {
    setMounted(true);
  }, []);

  const { organisations, activeOrg, setActiveOrg, setIsCreateOrgModalOpen } =
    useLiveApp();

  const activeName =
    mounted && activeOrg?.name
      ? activeOrg.name
      : "The Handover";
  const initial = activeName.charAt(0).toUpperCase();

  const orgList = organisations;

  return (
    <Dropdown
      width="w-64"
      align="left"
      trigger={() => (
        <button
          className={cn(
            "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left transition hover:bg-white/70 cursor-pointer",
            collapsed && "justify-center px-0"
          )}
          aria-label="Switch workspace"
        >
          <span
            className="flex size-6 shrink-0 items-center justify-center rounded-md bg-navy text-[10px] font-bold text-white shadow-2xs"
            suppressHydrationWarning
          >
            {initial}
          </span>
          {!collapsed && (
            <>
              <span
                className="min-w-0 flex-1 truncate text-[13px] font-medium text-navy"
                suppressHydrationWarning
              >
                {activeName}
              </span>
              <ChevronDown className="size-3.5 text-slate-400 shrink-0" />
            </>
          )}
        </button>
      )}
    >
      {(close) => (
        <div>
          <p className="px-2.5 pb-1 pt-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Workspaces
          </p>
          {orgList.map((org) => {
            const isSelected = activeOrg?.id === org.id;
            return (
              <MenuItem
                key={org.id}
                icon={Building2}
                active={isSelected}
                onClick={() => {
                  setActiveOrg(org);
                  close();
                }}
              >
                <span className="block truncate font-medium">{org.name}</span>
                <span className="block text-[11px] text-muted truncate">
                  {org.slug || "Workspace"}
                </span>
              </MenuItem>
            );
          })}
          <div className="my-1 border-t border-line" />
          <MenuItem
            icon={Plus}
            onClick={() => {
              close();
              setIsCreateOrgModalOpen(true);
            }}
          >
            Create organisation
          </MenuItem>
        </div>
      )}
    </Dropdown>
  );
}

function ProjectSwitcher({
  collapsed,
  onDone,
}: {
  collapsed: boolean;
  onDone?: () => void;
}) {
  const router = useRouter();
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => {
    setMounted(true);
  }, []);

  const {
    projects,
    activeProject,
    setActiveProject,
    setIsCreateProjectModalOpen,
    user,
    members,
  } = useLiveApp();

  const effectiveProjects = projects;

  const currentMember = mounted
    ? members.find((m) => m.user_id === user?.id || m.user_email === user?.email)
    : undefined;

  const currentRole =
    currentMember?.transition_role === "departing_owner"
      ? "Outgoing"
      : currentMember?.transition_role === "incoming_assignee"
      ? "Incoming"
      : currentMember?.role_name || "Manager";

  const effectiveProject = mounted ? activeProject : null;

  const projectCode =
    effectiveProject?.name
      ?.replace(/[^A-Za-z]/g, "")
      .slice(0, 3)
      .toUpperCase() ||
    (effectiveProject as unknown as { settings?: { code?: string } })?.settings?.code ||
    "PRJ";

  const projectColor =
    (effectiveProject as unknown as { settings?: { color?: string } })?.settings?.color ||
    "#315FBA";

  return (
    <Dropdown
      width="w-72"
      align="left"
      trigger={() =>
        collapsed ? (
          <Tooltip
            content={`${effectiveProject?.name || "All Projects"} · ${currentRole}`}
          >
            <button
              className="mx-auto flex size-8 items-center justify-center rounded-lg text-xs font-bold text-white shadow-2xs cursor-pointer"
              style={{ background: projectColor }}
              aria-label="Switch project"
              suppressHydrationWarning
            >
              <span suppressHydrationWarning>{projectCode.slice(0, 2)}</span>
            </button>
          </Tooltip>
        ) : (
          <button
            className="flex w-full items-center gap-2.5 rounded-[10px] border border-[#d4ddec] bg-white px-2 py-1.5 text-left transition duration-200 hover:border-[#b9c7de] hover:shadow-lift cursor-pointer"
            aria-label="Switch project"
          >
            <span
              className="flex size-7 shrink-0 items-center justify-center rounded-[7px] text-[10px] font-bold text-white shadow-2xs"
              style={{ background: projectColor }}
              suppressHydrationWarning
            >
              {projectCode}
            </span>
            <span className="min-w-0 flex-1">
              <span
                className="block truncate text-[13px] font-semibold text-navy"
                suppressHydrationWarning
              >
                {effectiveProject?.name || "All Projects"}
              </span>
              <span
                className="mt-0.5 flex items-center gap-1 text-[11px] text-muted"
                suppressHydrationWarning
              >
                <span className="size-1.5 rounded-full bg-brand" />
                {currentRole}
              </span>
            </span>
            <ChevronsUpDown className="size-4 text-slate-400 shrink-0" />
          </button>
        )
      }
    >
      {(close) => (
        <div>
          <p className="px-2.5 pb-1 pt-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Switch project
          </p>
          <button
            onClick={() => {
              setActiveProject(null);
              close();
              onDone?.();
              router.push("/dashboard");
            }}
            className={cn(
              "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left hover:bg-tint transition-colors cursor-pointer mb-1",
              !activeProject && "bg-tint"
            )}
          >
            <span className="flex size-7 shrink-0 items-center justify-center rounded-md text-[10px] font-bold text-slate-700 bg-slate-200 shadow-2xs">
              ALL
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[13px] font-medium text-navy">
                Workspace Overview
              </span>
              <span className="text-[11px] text-muted truncate block">
                All projects aggregated
              </span>
            </span>
            {!activeProject && (
              <CheckCircle2 className="size-4 text-brand shrink-0" />
            )}
          </button>
          {effectiveProjects.map((p) => {
            const pCode =
              (p as unknown as { settings?: { code?: string } })?.settings?.code ||
              p.name
                ?.replace(/[^A-Za-z]/g, "")
                .slice(0, 3)
                .toUpperCase() ||
              "PRJ";
            const pCol =
              (p as unknown as { settings?: { color?: string } })?.settings?.color ||
              "#315FBA";
            const isSelected = p.id === activeProject?.id;
            return (
              <button
                key={p.id}
                onClick={() => {
                  setActiveProject(p as unknown as Parameters<typeof setActiveProject>[0]);
                  close();
                  onDone?.();
                  router.push(`/projects/${p.id}`);
                }}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left hover:bg-tint transition-colors cursor-pointer",
                  isSelected && "bg-tint"
                )}
              >
                <span
                  className="flex size-7 shrink-0 items-center justify-center rounded-md text-[10px] font-bold text-white shadow-2xs"
                  style={{ background: pCol }}
                >
                  {pCode}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] font-medium text-navy">
                    {p.name}
                  </span>
                  <span className="text-[11px] text-muted truncate block">
                    {p.description || "Project workspace"}
                  </span>
                </span>
                {isSelected && (
                  <CheckCircle2 className="size-4 text-brand shrink-0" />
                )}
              </button>
            );
          })}
          <div className="my-1 border-t border-line" />
          <MenuItem
            icon={Plus}
            onClick={() => {
              close();
              setIsCreateProjectModalOpen(true);
              onDone?.();
            }}
          >
            Create project
          </MenuItem>
        </div>
      )}
    </Dropdown>
  );
}

function SidebarContent({
  collapsed,
  onNavigate,
  onOpenSearch,
}: {
  collapsed: boolean;
  onNavigate?: () => void;
  onOpenSearch?: () => void;
}) {
  const pathname = usePathname();
  const { activeProject, user, members, logout } = useLiveApp();

  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => {
    setMounted(true);
  }, []);

  const currentMember = mounted
    ? members.find((m) => m.user_id === user?.id || m.user_email === user?.email)
    : undefined;
  const userProjectRole =
    currentMember?.transition_role === "departing_owner"
      ? "outgoing"
      : currentMember?.transition_role === "incoming_assignee"
      ? "incoming"
      : currentMember?.role_name?.toLowerCase() || "manager";

  // Exact 6-section canonical navigation structure from AGENTS.md & Figma Make Shell
  const navGroups: NavGroup[] = [
    {
      label: "WORKSPACE",
      items: [
        {
          label: "Overview",
          to: "/dashboard",
          icon: LayoutDashboard,
          match: "^/dashboard$|^/overview$",
        },
        {
          label: "Projects",
          to: "/projects",
          icon: FolderKanban,
          match: "^/projects$|^/projects/new",
        },
        {
          label: "Team Members",
          to: "/settings/team",
          icon: Users,
          match: "^/settings/team$|^/team$",
        },
      ],
    },
    {
      label: "PROJECT INTELLIGENCE",
      items: [
        {
          label: "Evidence Center",
          to: activeProject
            ? `/projects/${activeProject.id}/evidence`
            : "/evidence",
          icon: FileSearch,
          match: "^/projects/.+/evidence|^/evidence",
        },
        {
          label: "Knowledge Intelligence",
          to: activeProject
            ? `/projects/${activeProject.id}/knowledge`
            : "/knowledge",
          icon: BrainCircuit,
          match: "^/projects/.+/knowledge|^/knowledge",
        },
        {
          label: "Relationship Explorer",
          to: "/relationships",
          icon: Network,
          match: "^/relationships",
        },
      ],
    },
    {
      label: "VALIDATION",
      items: [
        {
          label: "Verification Center",
          to: "/verification",
          icon: ClipboardCheck,
          match: "^/verification",
        },
        {
          label: "Conflicts",
          to: "/conflicts",
          icon: AlertTriangle,
          match: "^/conflicts",
        },
        ...(userProjectRole === "outgoing"
          ? [
              {
                label: "Verify my handover",
                to: "/verification",
                icon: ClipboardCheck,
                accent: true,
              },
            ]
          : []),
      ],
    },
    {
      label: "KNOWLEDGE TRANSFER",
      items: [
        {
          label: "Handover Workspace",
          to: "/handover",
          icon: Workflow,
          match: "^/handover$|^/handovers",
        },
        {
          label: "Generated Handovers",
          to: "/generated-handovers",
          icon: Send,
          match: "^/generated-handovers",
        },
        ...(userProjectRole === "incoming"
          ? [
              {
                label: "Ask assistant",
                to: "/assistant",
                icon: MessageSquareText,
                accent: true,
              },
            ]
          : []),
      ],
    },
    {
      label: "AI ASSISTANT",
      items: [
        {
          label: "AI Assistant",
          to: "/assistant",
          icon: MessageSquareText,
          match: "^/assistant",
        },
      ],
    },
    {
      label: "ADMINISTRATION",
      items: [
        {
          label: "Connected Sources",
          to: "/sources",
          icon: Plug,
          match: "^/sources",
        },
        {
          label: "Audit Logs",
          to: "/settings/audit-logs",
          icon: ScrollText,
          match: "^/settings/audit-logs$|^/audit$",
        },
        {
          label: "Settings",
          to: "/settings",
          icon: Settings,
          match: "^/settings$|^/settings/profile",
        },
      ],
    },
  ];

  const isActive = (item: NavItem) => {
    if (item.match) {
      return new RegExp(item.match).test(pathname);
    }
    if (item.to === "/dashboard") {
      return pathname === "/dashboard" || pathname === "/overview";
    }
    return pathname === item.to || pathname.startsWith(item.to + "/");
  };

  const userName =
    mounted && user ? user.full_name || user.email?.split("@")[0] || "User" : "User";
  const userSubtitle =
    mounted && user?.email
      ? user.email
      : currentMember?.role_name || "Workspace Member";

  return (
    <div className="flex h-full flex-col font-sans select-none">
      {/* Brand Header */}
      <div
        className={cn(
          "flex h-[60px] shrink-0 items-center px-4",
          collapsed && "justify-center px-0"
        )}
      >
        <Link
          href="/dashboard"
          onClick={onNavigate}
          className="focus:outline-none"
          title="The Handover"
        >
          {collapsed ? <LogoMark size={26} /> : <Logo size={24} />}
        </Link>
      </div>

      {/* Switchers & Search */}
      <div className={cn("space-y-2 px-3 relative z-30", collapsed && "px-2")}>
        <WorkspaceSwitcher collapsed={collapsed} />
        <ProjectSwitcher collapsed={collapsed} onDone={onNavigate} />
        <button
          type="button"
          onClick={onOpenSearch}
          className={cn(
            "flex h-8 w-full items-center gap-2 rounded-lg border border-[#d4ddec] bg-white/60 px-2.5 text-[12.5px] text-slate-400 transition duration-200 hover:border-[#c3cfe3] hover:bg-white cursor-pointer",
            collapsed && "justify-center px-0"
          )}
          aria-label="Search"
          title="Search (⌘K)"
        >
          <Search className="size-3.5 shrink-0" />
          {!collapsed && (
            <>
              <span className="flex-1 text-left">Search</span>
              <kbd className="rounded border border-line bg-white px-1 font-mono text-[10px] text-slate-500 shadow-2xs">
                ⌘K
              </kbd>
            </>
          )}
        </button>
      </div>

      {/* Navigation Groups */}
      <nav
        className="scrollbar-thin mt-4 flex-1 space-y-5 overflow-y-auto px-3 pb-4"
        aria-label="Main"
      >
        {navGroups.map((group) => (
          <div key={group.label}>
            {!collapsed ? (
              <p className="mb-1 px-2 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-[#97a3b8]">
                {group.label}
              </p>
            ) : (
              <div className="mx-auto mb-2 h-px w-6 bg-[#d4ddec]" />
            )}

            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const active = isActive(item);
                const Icon = item.icon;

                const linkElement = (
                  <Link
                    href={item.to}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "group relative flex h-8 items-center gap-2.5 rounded-[8px] px-2.5 text-[13.5px] transition-colors duration-200",
                      active
                        ? "bg-white font-semibold text-navy shadow-[0_1px_2px_rgba(32,54,83,0.06),0_0_0_1px_rgba(217,225,240,0.9)]"
                        : "font-medium text-[#4a5d7c] hover:bg-white/55 hover:text-navy",
                      item.accent && !active && "text-brand",
                      collapsed && "justify-center px-0"
                    )}
                  >
                    <Icon
                      className={cn(
                        "size-4 shrink-0 transition-colors",
                        active || item.accent
                          ? "text-brand"
                          : "text-[#8796ae] group-hover:text-navy"
                      )}
                      strokeWidth={1.9}
                    />
                    {!collapsed && (
                      <span className="flex-1 truncate">{item.label}</span>
                    )}
                    {item.badge !== undefined && (
                      <span className="rounded-md bg-blue-100 px-1.5 font-mono text-[10px] font-semibold text-brand">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );

                return (
                  <li key={item.label}>
                    {collapsed ? (
                      <Tooltip content={item.label}>{linkElement}</Tooltip>
                    ) : (
                      linkElement
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Footer User Profile & Sign Out */}
      <div className={cn("border-t border-[#D9E1F0] p-3", collapsed && "px-2")}>
        <div
          className={cn(
            "flex items-center gap-2.5 rounded-lg p-1.5 transition hover:bg-white/60",
            collapsed && "justify-center"
          )}
        >
          <Link
            href="/settings/profile"
            onClick={onNavigate}
            className="flex items-center gap-2.5 min-w-0 flex-1 overflow-hidden"
          >
            <Avatar name={userName} size={30} />
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <span
                  className="block truncate text-[13px] font-semibold text-navy leading-tight"
                  suppressHydrationWarning
                >
                  {userName}
                </span>
                <span
                  className="block truncate text-[11px] text-muted"
                  suppressHydrationWarning
                >
                  {userSubtitle}
                </span>
              </div>
            )}
          </Link>
          {!collapsed && (
            <button
              type="button"
              onClick={logout}
              title="Sign out"
              className="p-1 text-slate-400 hover:text-red-600 rounded transition-colors cursor-pointer"
            >
              <LogOut className="size-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function Sidebar({
  collapsed,
  onToggleCollapse,
  onOpenSearch,
}: {
  collapsed: boolean;
  onToggleCollapse?: () => void;
  onOpenSearch?: () => void;
}) {
  const { isMobileSidebarOpen, setIsMobileSidebarOpen } = useLiveApp();

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside
        className={cn(
          "no-print hidden shrink-0 border-r border-[#dbe3f0] bg-[#EDF2FA] transition-[width] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] lg:block",
          collapsed ? "w-[64px]" : "w-[248px]"
        )}
      >
        <SidebarContent collapsed={collapsed} onOpenSearch={onOpenSearch} />
      </aside>

      {/* Mobile Drawer (Screens < 1024px) */}
      {isMobileSidebarOpen && (
        <div
          className="fixed inset-0 z-[60] bg-navy/30 backdrop-blur-[2px] lg:hidden"
          onClick={() => setIsMobileSidebarOpen(false)}
        >
          <aside
            className="animate-slide-left h-full w-[280px] bg-[#EDF2FA] shadow-pop relative"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setIsMobileSidebarOpen(false)}
              className="absolute right-3 top-4 rounded-lg p-1.5 text-muted hover:text-navy cursor-pointer"
              aria-label="Close menu"
            >
              <X className="size-5" />
            </button>
            <SidebarContent
              collapsed={false}
              onNavigate={() => setIsMobileSidebarOpen(false)}
              onOpenSearch={() => {
                setIsMobileSidebarOpen(false);
                onOpenSearch?.();
              }}
            />
          </aside>
        </div>
      )}
    </>
  );
}
