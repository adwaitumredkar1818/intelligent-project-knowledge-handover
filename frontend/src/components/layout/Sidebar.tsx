"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderGit2,
  Users,
  Database,
  BrainCircuit,
  Network,
  CheckCircle2,
  AlertTriangle,
  FileCheck2,
  Archive,
  Bot,
  PlugZap,
  ScrollText,
  Sliders,
  X,
  LogOut,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: "active" | "coming_soon" | "preview";
}

interface NavGroup {
  group: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    group: "WORKSPACE",
    items: [
      { label: "Overview", href: "/overview", icon: LayoutDashboard },
      { label: "Projects", href: "/projects", icon: FolderGit2 },
      { label: "Team Members", href: "/team", icon: Users },
    ],
  },
  {
    group: "PROJECT INTELLIGENCE",
    items: [
      { label: "Evidence Center", href: "/evidence", icon: Database },
      { label: "Knowledge Intelligence", href: "/knowledge", icon: BrainCircuit, badge: "coming_soon" },
      { label: "Relationship Explorer", href: "/relationships", icon: Network, badge: "coming_soon" },
    ],
  },
  {
    group: "VALIDATION",
    items: [
      { label: "Verification Center", href: "/verification", icon: CheckCircle2, badge: "preview" },
      { label: "Conflicts", href: "/conflicts", icon: AlertTriangle, badge: "preview" },
    ],
  },
  {
    group: "KNOWLEDGE TRANSFER",
    items: [
      { label: "Handover Workspace", href: "/handover", icon: FileCheck2, badge: "preview" },
      { label: "Generated Handovers", href: "/generated-handovers", icon: Archive, badge: "preview" },
    ],
  },
  {
    group: "AI ASSISTANT",
    items: [
      { label: "Project Knowledge Assistant", href: "/assistant", icon: Bot, badge: "coming_soon" },
    ],
  },
  {
    group: "ADMINISTRATION",
    items: [
      { label: "Connected Sources", href: "/sources", icon: PlugZap },
      { label: "Audit Logs", href: "/audit", icon: ScrollText, badge: "preview" },
      { label: "Settings", href: "/settings", icon: Sliders, badge: "preview" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { isMobileSidebarOpen, setIsMobileSidebarOpen, activeProject, user, logout } = useLiveApp();

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 lg:hidden"
          onClick={() => setIsMobileSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Persistent Sidebar */}
      <aside
        className={`fixed lg:static top-0 bottom-0 left-0 z-40 w-64 bg-[#253650] text-[#DCE3EB] flex flex-col border-r border-[#304563] transition-transform duration-200 ease-in-out shrink-0 select-none ${
          isMobileSidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        {/* Brand Header */}
        <div className="h-14 px-4 flex items-center justify-between border-b border-[#304563] bg-[#253650]">
          <Link
            href="/overview"
            className="flex items-center gap-2.5 focus:outline-none"
            onClick={() => setIsMobileSidebarOpen(false)}
          >
            <div className="w-8 h-8 rounded bg-[#4774A9] text-white flex items-center justify-center font-bold text-lg shadow-sm border border-[#249E91]/40">
              H
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-white text-sm tracking-tight leading-none">
                The Handover
              </span>
              <span className="text-[10px] text-[#249E91] font-medium leading-tight mt-0.5">
                Knowledge Reconstruction
              </span>
            </div>
          </Link>
          <button
            type="button"
            className="lg:hidden p-1.5 text-[#69778D] hover:text-white rounded"
            onClick={() => setIsMobileSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Active Project Context Badge */}
        <div className="px-3 py-2 bg-[#1E2C42] border-b border-[#304563] text-xs">
          <div className="text-[10px] uppercase font-semibold tracking-wider text-[#69778D]">
            Active Workspace
          </div>
          <div className="text-white font-medium truncate mt-0.5 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#249E91] shrink-0" />
            <span className="truncate">{activeProject ? activeProject.name : "No Project Selected"}</span>
          </div>
        </div>

        {/* Navigation List */}
        <div className="flex-1 overflow-y-auto px-2 py-3 space-y-4 text-xs font-medium">
          {NAV_GROUPS.map((group) => (
            <div key={group.group} className="space-y-0.5">
              <div className="px-2 py-1 text-[10px] uppercase font-bold tracking-wider text-[#69778D]">
                {group.group}
              </div>
              <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;

                  return (
                    <li key={item.label}>
                      <Link
                        href={item.href}
                        onClick={() => setIsMobileSidebarOpen(false)}
                        className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded transition-colors group relative ${
                          isActive
                            ? "bg-[#4774A9] text-white font-semibold shadow-xs"
                            : "text-[#DCE3EB]/80 hover:bg-[#304563] hover:text-white"
                        }`}
                      >
                        <Icon
                          className={`w-4 h-4 shrink-0 ${
                            isActive
                              ? "text-white"
                              : "text-[#DCE3EB]/60 group-hover:text-white"
                          }`}
                        />
                        <span className="truncate flex-1">{item.label}</span>
                        {item.badge === "coming_soon" && (
                          <span className="text-[9px] uppercase px-1 py-0.2 rounded bg-[#304563] text-[#A0AEC0]">
                            Phase 2
                          </span>
                        )}
                        {item.badge === "preview" && (
                          <span className="text-[9px] uppercase px-1 py-0.2 rounded bg-[#304563] text-[#249E91]">
                            Spec
                          </span>
                        )}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        {/* Footer User Profile & Sign Out */}
        <div className="p-3 border-t border-[#304563] bg-[#1E2C42] flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-full bg-[#4774A9] text-white font-bold text-xs flex items-center justify-center shrink-0">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
            </div>
            <div className="truncate text-xs">
              <div className="font-semibold text-white truncate leading-tight">
                {user?.full_name || "User"}
              </div>
              <div className="text-[10px] text-[#A0AEC0] truncate">
                {user?.email || "Signed in"}
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={logout}
            title="Sign out"
            className="p-1.5 text-[#A0AEC0] hover:text-white hover:bg-[#304563] rounded transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </aside>
    </>
  );
}
