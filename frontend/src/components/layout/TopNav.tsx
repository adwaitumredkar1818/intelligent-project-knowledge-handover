"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Menu,
  ChevronsLeft,
  ChevronsRight,
  Search,
  Bell,
  CircleHelp,
  ChevronDown,
  User,
  Settings,
  ShieldCheck,
  LogOut,
  Workflow,
  ArrowRight,
  Keyboard,
  LifeBuoy,
  BookOpen,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Palette,
  HelpCircle,
} from "lucide-react";
import { Logo } from "../figma-ui/brand";
import {
  Avatar,
  Dropdown,
  IconButton,
  MenuItem,
  Tooltip,
  cn,
} from "../figma-ui/index";
import { Breadcrumbs } from "./Breadcrumbs";
import { useLiveApp } from "../../context/LiveAppContext";
import { ROLE_LABEL, type ProjectRole } from "../../lib/figmaStore";

function ContextChip() {
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => {
    setMounted(true);
  }, []);

  const { activeProject, user, members } = useLiveApp();
  if (!mounted || !activeProject) return null;

  const currentMember = members.find(
    (m) => m.user_id === user?.id || m.user_email === user?.email
  );
  const currentRole = (
    currentMember?.transition_role === "departing_owner"
      ? "outgoing"
      : currentMember?.transition_role === "incoming_assignee"
      ? "incoming"
      : currentMember?.role_name?.toLowerCase() || "manager"
  ) as ProjectRole;

  const roleLabel =
    ROLE_LABEL[currentRole as keyof typeof ROLE_LABEL] || "Project Member";

  const projectCode =
    (activeProject as unknown as { settings?: { code?: string } })?.settings?.code ||
    activeProject.name
      ?.replace(/[^A-Za-z]/g, "")
      .slice(0, 3)
      .toUpperCase() ||
    "PRJ";

  const projectColor =
    (activeProject as unknown as { settings?: { color?: string } })?.settings?.color ||
    "#315FBA";

  const isOutgoing = currentRole === "outgoing";
  const isIncoming = currentRole === "incoming";

  const roleTextTone = isOutgoing
    ? "text-amber-700"
    : isIncoming
    ? "text-teal-700"
    : "text-brand";

  const roleBgTone = isOutgoing
    ? "bg-warn"
    : isIncoming
    ? "bg-ok"
    : "bg-brand";

  return (
    <Tooltip
      content={`Your active role in ${activeProject.name}: ${roleLabel}. It changes navigation, widgets and actions.`}
      side="bottom"
    >
      <span className="hidden items-center gap-2 rounded-full border border-line bg-white py-1 pl-1 pr-2.5 text-[12px] font-medium text-navy 2xl:flex shadow-2xs">
        <span
          className="flex size-5 items-center justify-center rounded-full text-[8.5px] font-bold text-white shadow-2xs"
          style={{ background: projectColor }}
        >
          {projectCode.slice(0, 2)}
        </span>
        <span className="truncate max-w-[120px] font-semibold text-navy">
          {activeProject.name.split(" ")[0]}
        </span>
        <span className="text-slate-300">·</span>
        <span className={cn("flex items-center gap-1 font-semibold", roleTextTone)}>
          <span className={cn("size-1.5 rounded-full shrink-0", roleBgTone)} />
          {roleLabel}
        </span>
      </span>
    </Tooltip>
  );
}

function NotificationsMenu() {
  const router = useRouter();
  const { overview } = useLiveApp();
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => {
    setMounted(true);
  }, []);

  const attentionItems = overview?.attention_items || [];

  return (
    <Dropdown
      width="w-[340px] max-w-[calc(100vw-24px)]"
      trigger={() => (
        <IconButton
          icon={Bell}
          label="Notifications"
          badge={attentionItems.length > 0 ? attentionItems.length : undefined}
        />
      )}
    >
      {(close) => (
        <div>
          <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-line">
            <p className="text-sm font-semibold text-navy">Notifications & Attention</p>
            {attentionItems.length > 0 && (
              <span className="text-[11px] font-medium text-brand">
                {attentionItems.length} active
              </span>
            )}
          </div>
          <div className="max-h-72 overflow-y-auto divide-y divide-line/60 scrollbar-thin">
            {attentionItems.length === 0 ? (
              <div className="p-4 text-center text-xs text-muted">
                <CheckCircle2 className="size-6 text-ok mx-auto mb-1.5" />
                <p className="font-semibold text-navy">All clear</p>
                <p className="mt-0.5 text-[11px]">
                  All source connections and evidence repositories are operational.
                </p>
              </div>
            ) : (
              attentionItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    close();
                    router.push("/dashboard");
                  }}
                  className="flex w-full gap-2.5 px-3 py-2 text-left hover:bg-tint transition-colors cursor-pointer"
                >
                  <AlertTriangle className="size-4 text-amber-500 shrink-0 mt-0.5" />
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-medium text-navy leading-snug">
                      {item.message}
                    </p>
                    <p className="text-[10.5px] text-muted mt-0.5">
                      Type: {item.type}
                    </p>
                  </div>
                </button>
              ))
            )}
          </div>
          <button
            onClick={() => {
              close();
              router.push("/dashboard");
            }}
            className="flex w-full items-center justify-center gap-1 border-t border-line py-2 text-[12px] font-medium text-brand hover:underline cursor-pointer bg-slate-50/50"
          >
            View project overview <ArrowRight className="size-3.5" />
          </button>
        </div>
      )}
    </Dropdown>
  );
}

export function TopNav({
  collapsed,
  onToggleCollapse,
  onOpenSearch,
}: {
  collapsed: boolean;
  onToggleCollapse: () => void;
  onOpenSearch: () => void;
}) {
  const router = useRouter();
  const { user, logout, addToast, setIsMobileSidebarOpen } = useLiveApp();

  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => {
    setMounted(true);
  }, []);

  const userName =
    (mounted && (user?.full_name || user?.email?.split("@")[0])) || "User";
  const userEmail = (mounted && user?.email) || "";

  return (
    <header className="no-print flex h-[60px] shrink-0 items-center gap-2 border-b border-line/80 bg-white/85 px-3 backdrop-blur-xl sm:px-5 font-sans select-none z-30">
      {/* Mobile Menu Trigger */}
      <IconButton
        icon={Menu}
        label="Open menu"
        className="lg:hidden"
        onClick={() => setIsMobileSidebarOpen(true)}
      />

      {/* Desktop Sidebar Collapse Toggle */}
      <IconButton
        icon={collapsed ? ChevronsRight : ChevronsLeft}
        label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        className="hidden lg:inline-flex"
        onClick={onToggleCollapse}
      />

      {/* Mobile Logo */}
      <Link href="/dashboard" className="lg:hidden md:hidden">
        <Logo size={24} />
      </Link>

      {/* Dynamic Breadcrumbs */}
      <Breadcrumbs />

      {/* Right Controls */}
      <div className="ml-auto flex items-center gap-1">
        {/* Global Search Button (⌘K) */}
        <button
          type="button"
          onClick={onOpenSearch}
          className="mr-1 hidden h-9 w-60 items-center gap-2 rounded-[9px] border border-line bg-slate-50/80 px-3 text-[13px] text-slate-400 hover:border-slate-300 xl:flex cursor-pointer transition"
          title="Search (⌘K)"
        >
          <Search className="size-4 shrink-0 text-slate-400" />
          <span>Search everything</span>
          <kbd className="ml-auto rounded border border-line bg-white px-1.5 text-[10px] font-mono text-slate-500 shadow-2xs">
            ⌘K
          </kbd>
        </button>

        {/* Small Screen Search Icon */}
        <IconButton
          icon={Search}
          label="Search"
          className="xl:hidden"
          onClick={onOpenSearch}
        />

        {/* Project Role Context Chip */}
        <ContextChip />

        {/* Live / Prototype Data Badge */}
        <Tooltip
          content="Production environment connected with live evidence ingestion and PostgreSQL canonical storage."
          side="bottom"
        >
          <span className="mr-1 hidden rounded-full border border-dashed border-slate-300 px-2 py-0.5 text-[11px] font-medium text-slate-500 sm:inline">
            Production mode
          </span>
        </Tooltip>

        {/* Notifications Menu */}
        <NotificationsMenu />

        {/* Help & Support Menu */}
        <Dropdown
          trigger={() => (
            <IconButton
              icon={CircleHelp}
              label="Help & guides"
              className="hidden sm:inline-flex"
            />
          )}
        >
          {(close) => (
            <div>
              <MenuItem
                icon={BookOpen}
                onClick={() => {
                  close();
                  router.push("/flows");
                }}
              >
                Prototype flows
              </MenuItem>
              <MenuItem
                icon={Sparkles}
                onClick={() => {
                  close();
                  router.push("/brand");
                }}
              >
                3D Brand & Launch Studio
              </MenuItem>
              <MenuItem
                icon={Palette}
                onClick={() => {
                  close();
                  router.push("/design-system");
                }}
              >
                Design system
              </MenuItem>
              <MenuItem
                icon={Keyboard}
                onClick={() => {
                  close();
                  onOpenSearch();
                }}
                hint={<kbd className="text-[11px] font-mono text-slate-400">⌘K</kbd>}
              >
                Keyboard shortcuts
              </MenuItem>
              <div className="my-1 border-t border-line" />
              <MenuItem
                icon={LifeBuoy}
                onClick={() => {
                  close();
                  addToast({
                    type: "info",
                    title: "Support request logged",
                    message: "Engineering support has received your diagnostic request.",
                  });
                }}
              >
                Contact support
              </MenuItem>
            </div>
          )}
        </Dropdown>

        {/* User Account Dropdown */}
        <Dropdown
          width="w-60"
          trigger={() => (
            <button
              className="ml-1 flex items-center gap-1.5 rounded-full p-0.5 pr-1.5 hover:bg-tint transition cursor-pointer"
              aria-label="Account menu"
            >
              <Avatar name={userName} size={30} />
              <ChevronDown className="hidden size-3.5 text-slate-400 sm:block" />
            </button>
          )}
        >
          {(close) => (
            <div>
              <div className="flex items-center gap-2.5 px-3 py-2.5">
                <Avatar name={userName} size={34} />
                <div className="min-w-0">
                  <p
                    className="truncate text-sm font-semibold text-navy"
                    suppressHydrationWarning
                  >
                    {userName}
                  </p>
                  <p
                    className="truncate text-xs text-muted"
                    suppressHydrationWarning
                  >
                    {userEmail}
                  </p>
                </div>
              </div>
              <div className="my-1 border-t border-line" />
              <MenuItem
                icon={User}
                onClick={() => {
                  close();
                  router.push("/settings/profile");
                }}
              >
                Profile & account
              </MenuItem>
              <MenuItem
                icon={Settings}
                onClick={() => {
                  close();
                  router.push("/settings");
                }}
              >
                Settings
              </MenuItem>
              <MenuItem
                icon={ShieldCheck}
                onClick={() => {
                  close();
                  router.push("/settings/audit-logs");
                }}
              >
                Audit logs
              </MenuItem>
              <MenuItem
                icon={HelpCircle}
                onClick={() => {
                  close();
                  router.push("/flows");
                }}
              >
                Prototype flows
              </MenuItem>
              <div className="my-1 border-t border-line" />
              <MenuItem
                icon={LogOut}
                danger
                onClick={() => {
                  close();
                  logout();
                }}
              >
                Sign out
              </MenuItem>
            </div>
          )}
        </Dropdown>
      </div>
    </header>
  );
}
