"use client";

import React, { useState, useRef, useEffect } from "react";
import { usePathname } from "next/navigation";
import {
  Search,
  Bell,
  Menu,
  ChevronDown,
  Plus,
  Check,
  Building2,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";
import { usePrototype } from "../../context/PrototypeContext";

export function TopNav() {
  const pathname = usePathname();
  const {
    projects,
    selectedProject,
    setSelectedProjectById,
    setIsGlobalSearchOpen,
    setIsCreateProjectModalOpen,
    setIsMobileSidebarOpen,
    addToast,
  } = usePrototype();

  const [isProjectDropdownOpen, setIsProjectDropdownOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  const projectDropdownRef = useRef<HTMLDivElement>(null);
  const notificationRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        projectDropdownRef.current &&
        !projectDropdownRef.current.contains(event.target as Node)
      ) {
        setIsProjectDropdownOpen(false);
      }
      if (
        notificationRef.current &&
        !notificationRef.current.contains(event.target as Node)
      ) {
        setIsNotificationsOpen(false);
      }
      if (
        profileRef.current &&
        !profileRef.current.contains(event.target as Node)
      ) {
        setIsProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Compute breadcrumbs
  const getBreadcrumbs = () => {
    const parts = [{ label: selectedProject.name, href: "/prototype/overview" }];
    if (pathname.includes("/overview")) {
      parts.push({ label: "Workspace", href: "/prototype/overview" });
      parts.push({ label: "Overview", href: "/prototype/overview" });
    } else if (pathname.includes("/projects")) {
      parts.push({ label: "Workspace", href: "/prototype/projects" });
      parts.push({ label: "Project Directory", href: "/prototype/projects" });
    } else if (pathname.includes("/team")) {
      parts.push({ label: "Workspace", href: "/prototype/team" });
      parts.push({ label: "Team Members", href: "/prototype/team" });
    } else if (pathname.includes("/evidence")) {
      parts.push({ label: "Project Intelligence", href: "/prototype/evidence" });
      parts.push({ label: "Evidence Center", href: "/prototype/evidence" });
    } else if (pathname.includes("/sources")) {
      parts.push({ label: "Administration", href: "/prototype/sources" });
      parts.push({ label: "Connected Sources", href: "/prototype/sources" });
    }
    return parts;
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <header className="h-14 bg-white border-b border-[#DCE3EB] px-4 flex items-center justify-between shrink-0 select-none z-30 sticky top-0 shadow-2xs">
      {/* Left: Mobile hamburger + Project Selector + Breadcrumbs */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onClick={() => setIsMobileSidebarOpen(true)}
          className="lg:hidden p-1.5 text-[#69778D] hover:text-[#25334B] hover:bg-[#F4F6F9] rounded"
          aria-label="Open sidebar navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Project Selector Dropdown */}
        <div className="relative" ref={projectDropdownRef}>
          <button
            type="button"
            onClick={() => setIsProjectDropdownOpen((prev) => !prev)}
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-md border border-[#DCE3EB] bg-[#F4F6F9] hover:bg-[#E8EEF5] text-xs font-semibold text-[#25334B] transition-colors focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
            title="Switch project workspace"
          >
            <Building2 className="w-3.5 h-3.5 text-[#4774A9] shrink-0" />
            <span className="max-w-[140px] sm:max-w-[180px] truncate">
              {selectedProject.name}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-[#69778D] shrink-0" />
          </button>

          {/* Project Dropdown Menu */}
          {isProjectDropdownOpen && (
            <div className="absolute left-0 mt-1 w-64 rounded-md border border-[#DCE3EB] bg-white shadow-lg py-1 z-50 text-xs">
              <div className="px-3 py-1.5 text-[10px] font-bold text-[#69778D] uppercase tracking-wider border-b border-[#DCE3EB]/60">
                Switch Project Workspace
              </div>
              <div className="max-h-60 overflow-y-auto py-1">
                {projects.map((proj) => {
                  const isCurrent = proj.id === selectedProject.id;
                  return (
                    <button
                      key={proj.id}
                      type="button"
                      onClick={() => {
                        setSelectedProjectById(proj.id);
                        setIsProjectDropdownOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-[#F4F6F9] transition-colors ${
                        isCurrent ? "bg-[#F4F6F9] font-semibold text-[#4774A9]" : "text-[#25334B]"
                      }`}
                    >
                      <div className="min-w-0 pr-2">
                        <div className="truncate font-medium">{proj.name}</div>
                        <div className="text-[10px] text-[#69778D] truncate">
                          {proj.organisationName} · {proj.status}
                        </div>
                      </div>
                      {isCurrent && <Check className="w-4 h-4 text-[#249E91] shrink-0" />}
                    </button>
                  );
                })}
              </div>
              <div className="border-t border-[#DCE3EB]/60 p-1">
                <button
                  type="button"
                  onClick={() => {
                    setIsProjectDropdownOpen(false);
                    setIsCreateProjectModalOpen(true);
                  }}
                  className="w-full text-left px-2.5 py-1.5 flex items-center gap-2 rounded text-[#4774A9] hover:bg-[#E8EEF5] font-semibold transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Create Project Workspace</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Separator */}
        <div className="hidden md:block w-px h-4 bg-[#DCE3EB]" />

        {/* Breadcrumb Navigation */}
        <nav
          aria-label="Breadcrumb"
          className="hidden md:flex items-center gap-1.5 text-xs text-[#69778D] min-w-0 truncate"
        >
          {breadcrumbs.map((crumb, idx) => (
            <React.Fragment key={`${crumb.label}-${idx}`}>
              {idx > 0 && <span className="text-[#DCE3EB]">›</span>}
              <span
                className={`truncate ${
                  idx === breadcrumbs.length - 1 ? "font-semibold text-[#25334B]" : "hover:text-[#25334B]"
                }`}
              >
                {crumb.label}
              </span>
            </React.Fragment>
          ))}
        </nav>
      </div>

      {/* Right: Global Search + Notifications + User Avatar */}
      <div className="flex items-center gap-2.5">
        {/* Global Search Button */}
        <button
          type="button"
          onClick={() => setIsGlobalSearchOpen(true)}
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-md border border-[#DCE3EB] bg-[#F4F6F9] hover:bg-[#E8EEF5] text-xs text-[#69778D] transition-colors focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
          title="Search projects, members, evidence (Ctrl+K)"
        >
          <Search className="w-3.5 h-3.5 text-[#69778D]" />
          <span className="hidden sm:inline">Global search...</span>
          <kbd className="hidden sm:inline px-1.5 py-0.5 text-[9px] font-mono bg-white border border-[#DCE3EB] rounded text-[#69778D]">
            /
          </kbd>
        </button>

        {/* Notifications Icon & Popover */}
        <div className="relative" ref={notificationRef}>
          <button
            type="button"
            onClick={() => setIsNotificationsOpen((prev) => !prev)}
            className="relative p-1.5 text-[#69778D] hover:text-[#25334B] hover:bg-[#F4F6F9] rounded-md transition-colors focus:outline-none"
            aria-label="Notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-[#C48A32]" />
          </button>

          {/* Notifications Panel */}
          {isNotificationsOpen && (
            <div className="absolute right-0 mt-1 w-80 rounded-md border border-[#DCE3EB] bg-white shadow-lg py-2 z-50 text-xs">
              <div className="px-3 pb-2 flex items-center justify-between border-b border-[#DCE3EB]">
                <span className="font-bold text-[#25334B]">Notifications (Demo)</span>
                <span className="text-[10px] bg-[#C48A32]/15 text-[#C48A32] font-semibold px-1.5 py-0.5 rounded">
                  3 attention items
                </span>
              </div>
              <div className="divide-y divide-[#DCE3EB]/60 max-h-72 overflow-y-auto">
                <div className="p-3 hover:bg-[#F4F6F9] transition-colors">
                  <div className="flex items-start gap-2">
                    <ShieldAlert className="w-4 h-4 text-[#C65B60] shrink-0 mt-0.5" />
                    <div>
                      <div className="font-semibold text-[#25334B]">
                        Conflicting Password Reset Status
                      </div>
                      <div className="text-[11px] text-[#69778D] mt-0.5">
                        Jira task NXA-289 claims completed, PR #112 tests failed.
                      </div>
                      <div className="text-[10px] text-[#69778D] mt-1 font-mono">15m ago</div>
                    </div>
                  </div>
                </div>
                <div className="p-3 hover:bg-[#F4F6F9] transition-colors">
                  <div className="flex items-start gap-2">
                    <span className="w-2 h-2 rounded-full bg-[#249E91] shrink-0 mt-1.5" />
                    <div>
                      <div className="font-semibold text-[#25334B]">
                        GitHub Repository Sync Succeeded
                      </div>
                      <div className="text-[11px] text-[#69778D] mt-0.5">
                        Imported 42 commits and PR #104 from nexora-backend.
                      </div>
                      <div className="text-[10px] text-[#69778D] mt-1 font-mono">35m ago</div>
                    </div>
                  </div>
                </div>
                <div className="p-3 hover:bg-[#F4F6F9] transition-colors">
                  <div className="flex items-start gap-2">
                    <span className="w-2 h-2 rounded-full bg-[#C48A32] shrink-0 mt-1.5" />
                    <div>
                      <div className="font-semibold text-[#25334B]">
                        Handover Target Date Approaching
                      </div>
                      <div className="text-[11px] text-[#69778D] mt-0.5">
                        Alex Vance → Daniel Cho scheduled for Nov 28, 2026.
                      </div>
                      <div className="text-[10px] text-[#69778D] mt-1 font-mono">Yesterday</div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="pt-2 px-3 border-t border-[#DCE3EB] text-center">
                <button
                  type="button"
                  onClick={() => {
                    setIsNotificationsOpen(false);
                    addToast({
                      type: "info",
                      title: "Notifications Cleared",
                      message: "All demo notifications marked as read.",
                    });
                  }}
                  className="text-[11px] text-[#4774A9] hover:underline font-medium"
                >
                  Mark all as read
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User Profile Avatar & Popover */}
        <div className="relative" ref={profileRef}>
          <button
            type="button"
            onClick={() => setIsProfileOpen((prev) => !prev)}
            className="flex items-center gap-2 p-1 rounded-md hover:bg-[#F4F6F9] transition-colors focus:outline-none"
            aria-label="User profile"
          >
            <div className="w-7 h-7 rounded-full bg-[#304563] text-white flex items-center justify-center font-bold text-xs border border-[#4774A9]">
              AV
            </div>
            <div className="hidden lg:flex flex-col text-left">
              <span className="text-xs font-semibold text-[#25334B] leading-none">
                Alex Vance
              </span>
              <span className="text-[10px] text-[#69778D] leading-none mt-0.5">
                Backend Lead (Departing)
              </span>
            </div>
          </button>

          {/* Profile Menu */}
          {isProfileOpen && (
            <div className="absolute right-0 mt-1 w-60 rounded-md border border-[#DCE3EB] bg-white shadow-lg py-2 z-50 text-xs">
              <div className="px-3 pb-2 border-b border-[#DCE3EB]">
                <div className="font-bold text-[#25334B]">Alex Vance</div>
                <div className="text-[11px] text-[#69778D]">alex.vance@nexora.internal</div>
                <div className="mt-1 inline-block bg-[#C48A32]/15 text-[#C48A32] text-[10px] font-semibold px-1.5 py-0.5 rounded">
                  Designated Departing Owner
                </div>
              </div>
              <div className="py-1">
                <div className="px-3 py-1.5 text-[#69778D] text-[11px]">
                  <strong>Organisation:</strong> Nexora Technologies
                </div>
                <div className="px-3 py-1.5 text-[#69778D] text-[11px]">
                  <strong>Role:</strong> Technical Lead
                </div>
              </div>
              <div className="border-t border-[#DCE3EB] pt-1 px-1">
                <button
                  type="button"
                  onClick={() => {
                    setIsProfileOpen(false);
                    addToast({
                      type: "info",
                      title: "Prototype Account",
                      message: "User session is local to the interactive prototype.",
                    });
                  }}
                  className="w-full text-left px-2.5 py-1.5 rounded text-[#25334B] hover:bg-[#F4F6F9] text-xs flex items-center justify-between"
                >
                  <span>Account Settings (Preview)</span>
                  <ExternalLink className="w-3 h-3 text-[#69778D]" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
