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
  FolderGit2,
  ShieldCheck,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

export function TopNav() {
  const pathname = usePathname();
  const {
    organisations,
    activeOrg,
    setActiveOrg,
    projects,
    activeProject,
    setActiveProject,
    setIsCreateProjectModalOpen,
    setIsCreateOrgModalOpen,
    setIsMobileSidebarOpen,
    user,
  } = useLiveApp();

  const [isOrgDropdownOpen, setIsOrgDropdownOpen] = useState(false);
  const [isProjectDropdownOpen, setIsProjectDropdownOpen] = useState(false);
  const orgDropdownRef = useRef<HTMLDivElement>(null);
  const projectDropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        orgDropdownRef.current &&
        !orgDropdownRef.current.contains(event.target as Node)
      ) {
        setIsOrgDropdownOpen(false);
      }
      if (
        projectDropdownRef.current &&
        !projectDropdownRef.current.contains(event.target as Node)
      ) {
        setIsProjectDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Compute breadcrumbs
  const getBreadcrumbs = () => {
    const parts = [
      { label: activeProject ? activeProject.name : "Select Project", href: "/overview" },
    ];
    if (pathname.includes("/overview")) {
      parts.push({ label: "Workspace", href: "/overview" });
      parts.push({ label: "Overview", href: "/overview" });
    } else if (pathname.includes("/projects")) {
      parts.push({ label: "Workspace", href: "/projects" });
      parts.push({ label: "Projects Directory", href: "/projects" });
    } else if (pathname.includes("/team")) {
      parts.push({ label: "Workspace", href: "/team" });
      parts.push({ label: "Team Members", href: "/team" });
    } else if (pathname.includes("/evidence")) {
      parts.push({ label: "Project Intelligence", href: "/evidence" });
      parts.push({ label: "Evidence Center", href: "/evidence" });
    } else if (pathname.includes("/sources")) {
      parts.push({ label: "Administration", href: "/sources" });
      parts.push({ label: "Connected Sources", href: "/sources" });
    } else if (pathname.includes("/knowledge")) {
      parts.push({ label: "Project Intelligence", href: "/knowledge" });
      parts.push({ label: "Knowledge Intelligence", href: "/knowledge" });
    } else if (pathname.includes("/relationships")) {
      parts.push({ label: "Project Intelligence", href: "/relationships" });
      parts.push({ label: "Relationship Explorer", href: "/relationships" });
    } else if (pathname.includes("/verification")) {
      parts.push({ label: "Validation", href: "/verification" });
      parts.push({ label: "Verification Center", href: "/verification" });
    } else if (pathname.includes("/conflicts")) {
      parts.push({ label: "Validation", href: "/conflicts" });
      parts.push({ label: "Conflicts", href: "/conflicts" });
    } else if (pathname.includes("/handover")) {
      parts.push({ label: "Knowledge Transfer", href: "/handover" });
      parts.push({ label: "Handover Workspace", href: "/handover" });
    } else if (pathname.includes("/generated-handovers")) {
      parts.push({ label: "Knowledge Transfer", href: "/generated-handovers" });
      parts.push({ label: "Generated Handovers", href: "/generated-handovers" });
    } else if (pathname.includes("/assistant")) {
      parts.push({ label: "AI Assistant", href: "/assistant" });
      parts.push({ label: "Project Knowledge Assistant", href: "/assistant" });
    } else if (pathname.includes("/audit")) {
      parts.push({ label: "Administration", href: "/audit" });
      parts.push({ label: "Audit Logs", href: "/audit" });
    } else if (pathname.includes("/settings")) {
      parts.push({ label: "Administration", href: "/settings" });
      parts.push({ label: "Settings", href: "/settings" });
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

        {/* Real Organisation Selector Dropdown */}
        <div className="relative" ref={orgDropdownRef}>
          <button
            type="button"
            onClick={() => setIsOrgDropdownOpen(!isOrgDropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#DCE3EB] bg-[#F4F6F9] hover:bg-[#E8EEF5] text-xs font-semibold text-[#25334B] transition-colors max-w-[200px]"
          >
            <Building2 className="w-4 h-4 text-[#249E91] shrink-0" />
            <span className="truncate">
              {activeOrg ? activeOrg.name : "Select Org"}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-[#69778D] shrink-0 ml-0.5" />
          </button>

          {isOrgDropdownOpen && (
            <div className="absolute top-full left-0 mt-1.5 w-60 bg-white rounded-xl shadow-lg border border-[#DCE3EB] py-1.5 z-50 text-xs">
              <div className="px-3 py-1 text-[10px] uppercase font-bold text-[#69778D] tracking-wider">
                Organisation Workspaces
              </div>
              <div className="max-h-56 overflow-y-auto py-1">
                {organisations.length === 0 ? (
                  <div className="px-3 py-2 text-[#69778D] text-center text-xs">
                    No organisations yet
                  </div>
                ) : (
                  organisations.map((org) => {
                    const isSelected = activeOrg?.id === org.id;
                    return (
                      <button
                        key={org.id}
                        type="button"
                        onClick={() => {
                          setActiveOrg(org);
                          setIsOrgDropdownOpen(false);
                        }}
                        className={`w-full px-3 py-2 text-left flex items-center justify-between hover:bg-[#F4F6F9] transition-colors ${
                          isSelected ? "bg-[#F0FAF8] text-[#249E91] font-semibold" : "text-[#25334B]"
                        }`}
                      >
                        <span className="truncate">{org.name}</span>
                        {isSelected && <Check className="w-3.5 h-3.5 text-[#249E91] shrink-0" />}
                      </button>
                    );
                  })
                )}
              </div>
              <div className="border-t border-[#DCE3EB] pt-1 px-1">
                <button
                  type="button"
                  onClick={() => {
                    setIsOrgDropdownOpen(false);
                    setIsCreateOrgModalOpen(true);
                  }}
                  className="w-full px-2.5 py-1.5 rounded-lg text-left text-[#249E91] hover:bg-[#F0FAF8] font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Create Organisation</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Real Project Selector Dropdown */}
        <div className="relative" ref={projectDropdownRef}>
          <button
            type="button"
            onClick={() => setIsProjectDropdownOpen(!isProjectDropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#DCE3EB] bg-[#F4F6F9] hover:bg-[#E8EEF5] text-xs font-semibold text-[#25334B] transition-colors max-w-[220px]"
          >
            <FolderGit2 className="w-4 h-4 text-[#4774A9] shrink-0" />
            <span className="truncate">
              {activeProject ? activeProject.name : "Select Project"}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-[#69778D] shrink-0 ml-0.5" />
          </button>

          {isProjectDropdownOpen && (
            <div className="absolute top-full left-0 mt-1.5 w-64 bg-white rounded-xl shadow-lg border border-[#DCE3EB] py-1.5 z-50 text-xs">
              <div className="px-3 py-1 text-[10px] uppercase font-bold text-[#69778D] tracking-wider">
                Organisation Projects ({activeOrg?.name || "Active Org"})
              </div>
              <div className="max-h-56 overflow-y-auto py-1">
                {projects.length === 0 ? (
                  <div className="px-3 py-2 text-[#69778D] text-center text-xs">
                    No projects found
                  </div>
                ) : (
                  projects.map((proj) => {
                    const isSelected = activeProject?.id === proj.id;
                    return (
                      <button
                        key={proj.id}
                        type="button"
                        onClick={() => {
                          setActiveProject(proj);
                          setIsProjectDropdownOpen(false);
                        }}
                        className={`w-full px-3 py-2 text-left flex items-center justify-between hover:bg-[#F4F6F9] transition-colors ${
                          isSelected ? "bg-[#F0FAF8] text-[#249E91] font-semibold" : "text-[#25334B]"
                        }`}
                      >
                        <span className="truncate">{proj.name}</span>
                        {isSelected && <Check className="w-3.5 h-3.5 text-[#249E91] shrink-0" />}
                      </button>
                    );
                  })
                )}
              </div>
              <div className="border-t border-[#DCE3EB] pt-1 px-1">
                <button
                  type="button"
                  onClick={() => {
                    setIsProjectDropdownOpen(false);
                    setIsCreateProjectModalOpen(true);
                  }}
                  className="w-full px-2.5 py-1.5 rounded-lg text-left text-[#4774A9] hover:bg-[#E8EEF5] font-semibold flex items-center gap-1.5 transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Create New Project</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Breadcrumb Navigation */}
        <div className="hidden md:flex items-center gap-1.5 text-xs text-[#69778D]">
          {breadcrumbs.map((crumb, idx) => (
            <React.Fragment key={`${crumb.label}-${idx}`}>
              {idx > 0 && <span className="text-[#DCE3EB]">/</span>}
              <span
                className={
                  idx === breadcrumbs.length - 1
                    ? "font-semibold text-[#25334B]"
                    : "hover:text-[#25334B]"
                }
              >
                {crumb.label}
              </span>
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Right Controls: Global Search + Notifications + User Avatar */}
      <div className="flex items-center gap-3">
        {/* Global Search Bar */}
        <div className="relative hidden sm:block w-48 md:w-64">
          <Search className="w-3.5 h-3.5 text-[#69778D] absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Global search (FTS / nomic)..."
            className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-[#DCE3EB] bg-[#F4F6F9] text-xs text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9] placeholder:text-[#69778D]"
          />
        </div>

        {/* Notifications */}
        <button
          type="button"
          title="Notifications"
          className="p-2 text-[#69778D] hover:text-[#25334B] hover:bg-[#F4F6F9] rounded-lg transition-colors relative"
        >
          <Bell className="w-4 h-4" />
          <span className="w-2 h-2 rounded-full bg-[#249E91] absolute top-1.5 right-1.5" />
        </button>

        {/* User Avatar */}
        <div className="flex items-center gap-2 pl-2 border-l border-[#DCE3EB]">
          <div className="w-8 h-8 rounded-full bg-[#253650] text-white font-bold text-xs flex items-center justify-center shadow-xs border border-[#249E91]/40">
            {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
          </div>
        </div>
      </div>
    </header>
  );
}
