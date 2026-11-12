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
} from "lucide-react";
import { usePrototype } from "../../context/PrototypeContext";

interface NavItem {
  label: string;
  href?: string;
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
      { label: "Overview", href: "/prototype/overview", icon: LayoutDashboard },
      { label: "Projects", href: "/prototype/projects", icon: FolderGit2 },
      { label: "Team Members", href: "/prototype/team", icon: Users },
    ],
  },
  {
    group: "PROJECT INTELLIGENCE",
    items: [
      { label: "Evidence Center", href: "/prototype/evidence", icon: Database },
      { label: "Knowledge Intelligence", icon: BrainCircuit, badge: "coming_soon" },
      { label: "Relationship Explorer", icon: Network, badge: "coming_soon" },
    ],
  },
  {
    group: "VALIDATION",
    items: [
      { label: "Verification Center", icon: CheckCircle2, badge: "preview" },
      { label: "Conflicts", icon: AlertTriangle, badge: "preview" },
    ],
  },
  {
    group: "KNOWLEDGE TRANSFER",
    items: [
      { label: "Handover Workspace", icon: FileCheck2, badge: "preview" },
      { label: "Generated Handovers", icon: Archive, badge: "preview" },
    ],
  },
  {
    group: "AI ASSISTANT",
    items: [
      { label: "Project Knowledge Assistant", icon: Bot, badge: "coming_soon" },
    ],
  },
  {
    group: "ADMINISTRATION",
    items: [
      { label: "Connected Sources", href: "/prototype/sources", icon: PlugZap },
      { label: "Audit Logs", icon: ScrollText, badge: "preview" },
      { label: "Settings", icon: Sliders, badge: "preview" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { isMobileSidebarOpen, setIsMobileSidebarOpen, selectedProject } = usePrototype();

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
            href="/prototype/overview"
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

        {/* Project Context Badge */}
        <div className="px-3 py-2 bg-[#1E2C42] border-b border-[#304563] text-xs">
          <div className="text-[10px] uppercase font-semibold tracking-wider text-[#69778D]">
            Active Workspace
          </div>
          <div className="text-white font-medium truncate mt-0.5 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#249E91] shrink-0" />
            <span className="truncate">{selectedProject.name}</span>
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
                  const isActive = item.href ? pathname === item.href : false;

                  if (item.href) {
                    return (
                      <li key={item.label}>
                        <Link
                          href={item.href}
                          onClick={() => setIsMobileSidebarOpen(false)}
                          className={`relative flex items-center gap-2.5 px-2.5 py-1.5 rounded transition-colors text-xs ${
                            isActive
                              ? "bg-[#304563] text-white font-semibold shadow-xs"
                              : "text-[#DCE3EB]/85 hover:bg-[#304563]/60 hover:text-white"
                          }`}
                        >
                          {isActive && (
                            <span className="absolute left-0 top-1 bottom-1 w-1 bg-[#249E91] rounded-r" />
                          )}
                          <Icon
                            className={`w-4 h-4 shrink-0 ${
                              isActive ? "text-[#249E91]" : "text-[#DCE3EB]/70"
                            }`}
                          />
                          <span className="truncate">{item.label}</span>
                        </Link>
                      </li>
                    );
                  }

                  // Non-implemented module preview
                  return (
                    <li key={item.label}>
                      <div
                        className="flex items-center justify-between px-2.5 py-1.5 text-xs text-[#69778D] cursor-not-allowed rounded opacity-75"
                        title="Module under design - available in subsequent phases"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <Icon className="w-4 h-4 shrink-0 text-[#69778D]/80" />
                          <span className="truncate">{item.label}</span>
                        </div>
                        {item.badge === "coming_soon" && (
                          <span className="text-[9px] bg-[#304563] text-[#DCE3EB]/60 px-1.5 py-0.5 rounded font-mono uppercase tracking-wider shrink-0">
                            Later
                          </span>
                        )}
                        {item.badge === "preview" && (
                          <span className="text-[9px] bg-[#304563]/80 text-[#C48A32] px-1.5 py-0.5 rounded font-mono uppercase tracking-wider shrink-0">
                            Preview
                          </span>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-[#304563] text-[11px] text-[#69778D] bg-[#1E2C42]">
          <div className="flex items-center justify-between">
            <span className="truncate">Nexora Platform v0.1</span>
            <span className="text-[#249E91] font-mono text-[10px]">STAGE 1</span>
          </div>
        </div>
      </aside>
    </>
  );
}
