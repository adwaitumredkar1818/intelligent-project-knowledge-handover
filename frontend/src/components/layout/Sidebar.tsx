"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
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
  Bot,
  Plug,
  ScrollText,
  Settings,
  X,
  LogOut,
  ChevronDown,
  ChevronsUpDown,
  Search,
  Layers,
  Plus,
  Building2,
  FileSearch,
  CheckCircle2,
  MessageSquareText,
} from "lucide-react";
import { Logo, LogoMark } from "../brand";
import {
  Avatar,
  Badge,
  Dropdown,
  MenuItem,
  Tooltip,
  RoleBadge,
  cn,
} from "../ui";
import { useLiveApp } from "../../context/LiveAppContext";
import type { Project } from "../../lib/types";

export { RoleBadge };

interface NavItem {
  label: string;
  to: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  badge?: number | string;
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

  const isQueryOpen =
    typeof window !== "undefined" && window.location.search.includes("openOrg=true");

  const orgName = (mounted && activeOrg?.name) || "The Handover";
  const orgInitial = orgName.charAt(0).toUpperCase();

  return (
    <Dropdown
      width="w-64"
      align="left"
      defaultOpen={isQueryOpen}
      trigger={() => (
        <button
          className={cn(
            "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left transition hover:bg-white/70 cursor-pointer",
            collapsed && "justify-center px-0"
          )}
          aria-label="Switch workspace"
        >
          <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-navy text-[10px] font-bold text-white shadow-2xs">
            {orgInitial}
          </span>
          {!collapsed && (
            <>
              <span
                className="min-w-0 flex-1 truncate text-[13px] font-medium text-navy"
                suppressHydrationWarning
              >
                {orgName}
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
            Workspaces / Organisations
          </p>
          {organisations.map((org) => (
            <MenuItem
              key={org.id}
              icon={Building2}
              active={org.id === activeOrg?.id}
              onClick={() => {
                setActiveOrg(org);
                close();
              }}
            >
              <span className="block truncate font-medium">{org.name}</span>
              <span className="block text-[11px] text-muted truncate">
                {org.slug || "Enterprise workspace"}
              </span>
            </MenuItem>
          ))}
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

  const isQueryOpen =
    typeof window !== "undefined" && window.location.search.includes("openProject=true");

  if (!mounted || (!activeProject && projects.length === 0 && !isQueryOpen)) return null;

  const currentMember = members.find(
    (m) => m.user_id === user?.id || m.user_email === user?.email
  );
  const currentRole =
    currentMember?.transition_role === "departing_owner"
      ? "Outgoing"
      : currentMember?.transition_role === "incoming_assignee"
      ? "Incoming"
      : currentMember?.role_name || "Member";

  const projectCode =
    activeProject?.name
      ?.replace(/[^A-Za-z]/g, "")
      .slice(0, 3)
      .toUpperCase() || "PRJ";

  const projectColor = "#315FBA";

  return (
    <Dropdown
      width="w-72"
      align="left"
      defaultOpen={isQueryOpen}
      trigger={() =>
        collapsed ? (
          <Tooltip content={`${activeProject?.name || "Select Project"} · ${currentRole}`}>
            <button
              className="mx-auto flex size-8 items-center justify-center rounded-lg text-xs font-bold text-white shadow-2xs cursor-pointer"
              style={{ background: projectColor }}
            >
              {projectCode.slice(0, 2)}
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
            >
              {projectCode}
            </span>
            <span className="min-w-0 flex-1">
              <span
                className="block truncate text-[13px] font-semibold text-navy"
                suppressHydrationWarning
              >
                {activeProject?.name || "Select Project"}
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
          {projects.map((p) => {
            const pCode =
              p.name
                ?.replace(/[^A-Za-z]/g, "")
                .slice(0, 3)
                .toUpperCase() || "PRJ";
            const isSelected = p.id === activeProject?.id;
            return (
              <button
                key={p.id}
                onClick={() => {
                  setActiveProject(p);
                  close();
                  onDone?.();
                }}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left hover:bg-tint transition-colors cursor-pointer",
                  isSelected && "bg-tint"
                )}
              >
                <span
                  className="flex size-7 shrink-0 items-center justify-center rounded-md text-[10px] font-bold text-white shadow-2xs"
                  style={{ background: projectColor }}
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
                {isSelected && <CheckCircle2 className="size-4 text-brand shrink-0" />}
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
      : currentMember?.role_name?.toLowerCase() || "member";

  // Build Figma navigation groups dynamically
  const navGroups: NavGroup[] = [
    {
      label: "Workspace",
      items: [
        { label: "Dashboard", to: "/overview", icon: LayoutDashboard },
        { label: "My Projects", to: "/projects", icon: FolderKanban },
        { label: "Team", to: "/team", icon: Users },
      ],
    },
    {
      label: "Handovers",
      items: [
        { label: "All Handovers", to: "/handover", icon: Workflow },
        { label: "Generated Handovers", to: "/generated-handovers", icon: Send },
        { label: "Verification Center", to: "/verification", icon: ClipboardCheck },
        { label: "Conflicts", to: "/conflicts", icon: AlertTriangle },
      ],
    },
  ];

  // Dynamic Current Project Section
  const isProjectQueryOpen =
    typeof window !== "undefined" && window.location.search.includes("openProject=true");

  if (mounted && (activeProject || isProjectQueryOpen)) {
    const projectItems: NavItem[] = [
      { label: "Overview", to: "/overview", icon: Layers },
      { label: "Knowledge Explorer", to: "/knowledge", icon: BrainCircuit },
      { label: "Relationship Explorer", to: "/relationships", icon: Network },
      { label: "Evidence Center", to: "/evidence", icon: FileSearch },
      { label: "Data Sources", to: "/sources", icon: Database },
    ];

    // Role-specific action pills
    if (userProjectRole === "outgoing") {
      projectItems.push({
        label: "Verify my handover",
        to: "/verification",
        icon: ClipboardCheck,
        accent: true,
      });
    } else if (userProjectRole === "incoming") {
      projectItems.push({
        label: "Ask assistant",
        to: "/assistant",
        icon: MessageSquareText,
        accent: true,
      });
    }

    navGroups.push({
      label: "Current Project",
      items: projectItems,
    });
  }

  // Settings & System Section
  navGroups.push({
    label: "Settings",
    items: [
      { label: "Connected Sources", to: "/sources", icon: Plug },
      { label: "Audit Logs", to: "/audit", icon: ScrollText },
      { label: "Settings", to: "/settings", icon: Settings },
    ],
  });

  const isActive = (item: NavItem) => {
    if (item.to === "/overview") {
      return pathname === "/overview";
    }
    return pathname === item.to || pathname.startsWith(item.to + "/");
  };

  const userName = mounted && user ? (user.full_name || user.email?.split("@")[0] || "User") : "User";
  const userRole = mounted && currentMember?.role_name ? currentMember.role_name : "Workspace Member";
  const userSubtitle = mounted && user?.email ? user.email : userRole;

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
          href="/overview"
          onClick={onNavigate}
          className="focus:outline-none"
          title="The Handover"
        >
          {collapsed ? <LogoMark size={26} /> : <Logo size={24} />}
        </Link>
      </div>

      {/* Workspace Switcher & Global Search Button */}
      <div className={cn("space-y-2 px-3 relative z-30", collapsed && "px-2")}>
        <WorkspaceSwitcher collapsed={collapsed} />
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
            {group.label === "Current Project" ? (
              <div className="mb-2">
                {!collapsed && (
                  <p className="mb-1.5 px-2 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-[#97a3b8]">
                    Current project
                  </p>
                )}
                <ProjectSwitcher collapsed={collapsed} onDone={onNavigate} />
              </div>
            ) : !collapsed ? (
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
                    {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
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
          "no-print hidden shrink-0 border-r border-[#dbe3f0] bg-tint transition-[width] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] lg:block",
          collapsed ? "w-[64px]" : "w-[248px]"
        )}
      >
        <SidebarContent
          collapsed={collapsed}
          onOpenSearch={onOpenSearch}
        />
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
