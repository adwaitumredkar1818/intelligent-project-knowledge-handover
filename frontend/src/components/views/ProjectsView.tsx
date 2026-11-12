"use client";

import React, { useState } from "react";
import {
  FolderGit2,
  Plus,
  Calendar,
  CheckCircle2,
  ArrowRight,
  Search,
  Check,
  Building2,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

export function ProjectsView() {
  const {
    projects,
    activeProject,
    setActiveProject,
    setIsCreateProjectModalOpen,
    activeOrg,
    isLoadingProjects,
  } = useLiveApp();

  const [searchTerm, setSearchTerm] = useState("");

  const filteredProjects = projects.filter((p) =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (p.description && p.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-[#4774A9] uppercase tracking-wider">
            <span>Project Workspaces</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#249E91]" />
            <span className="text-[#69778D] font-normal">{activeOrg?.name || "Active Org"}</span>
          </div>
          <h1 className="text-xl font-bold text-[#25334B] mt-1 tracking-tight">
            Projects Directory
          </h1>
          <p className="text-xs text-[#69778D] mt-0.5">
            Select an active project workspace or configure new handover scopes with project-specific vector isolation.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsCreateProjectModalOpen(true)}
          className="px-4 py-2.5 rounded-lg bg-[#4774A9] hover:bg-[#365F92] text-white text-xs font-semibold flex items-center gap-2 transition-colors shadow-xs shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>New Project Workspace</span>
        </button>
      </div>

      {/* Search Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-[#69778D] absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search projects by name or scope..."
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-[#DCE3EB] bg-white text-xs text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
          />
        </div>
        <div className="text-xs text-[#69778D] font-medium">
          {filteredProjects.length} of {projects.length} projects
        </div>
      </div>

      {/* Projects Grid */}
      {filteredProjects.length === 0 ? (
        <div className="p-8 text-center bg-white rounded-xl border border-[#DCE3EB] shadow-2xs flex flex-col items-center justify-center">
          <FolderGit2 className="w-12 h-12 text-[#69778D] mb-3 stroke-[1.5]" />
          <div className="font-bold text-sm text-[#25334B]">No Projects Found</div>
          <p className="text-xs text-[#69778D] max-w-sm mt-1 mb-4">
            {searchTerm
              ? "No project workspaces matched your search query."
              : "No project workspaces exist yet under this organisation. Create one to begin."}
          </p>
          <button
            type="button"
            onClick={() => setIsCreateProjectModalOpen(true)}
            className="px-4 py-2 rounded-lg bg-[#4774A9] hover:bg-[#365F92] text-white text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Project</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProjects.map((proj) => {
            const isSelected = activeProject?.id === proj.id;
            return (
              <div
                key={proj.id}
                className={`bg-white rounded-xl border p-5 shadow-2xs flex flex-col justify-between transition-all ${
                  isSelected
                    ? "border-[#249E91] ring-1 ring-[#249E91]"
                    : "border-[#DCE3EB] hover:border-[#4774A9]"
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-[#E8EEF5] text-[#4774A9] flex items-center justify-center font-bold text-xs">
                        <FolderGit2 className="w-4 h-4" />
                      </div>
                      <div>
                        <h3 className="font-bold text-xs text-[#25334B] leading-tight">
                          {proj.name}
                        </h3>
                        <span className="text-[10px] text-[#69778D]">{proj.slug}</span>
                      </div>
                    </div>
                    <span
                      className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                        proj.status === "active"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : "bg-gray-100 text-gray-700 border border-gray-200"
                      }`}
                    >
                      {proj.status}
                    </span>
                  </div>

                  <p className="text-xs text-[#69778D] mt-3 line-clamp-3 leading-relaxed">
                    {proj.description || "No description provided for this handover project workspace."}
                  </p>
                </div>

                <div className="mt-5 pt-3 border-t border-[#DCE3EB]">
                  <div className="flex items-center justify-between text-[11px] text-[#69778D] mb-3">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      {proj.target_handover_date
                        ? new Date(proj.target_handover_date).toLocaleDateString()
                        : "Target: Unset"}
                    </span>
                    <span>Created: {new Date(proj.created_at).toLocaleDateString()}</span>
                  </div>

                  <button
                    type="button"
                    onClick={() => setActiveProject(proj)}
                    disabled={isSelected}
                    className={`w-full py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors ${
                      isSelected
                        ? "bg-[#F0FAF8] text-[#249E91] border border-[#249E91]/30 cursor-default"
                        : "bg-[#4774A9] hover:bg-[#365F92] text-white"
                    }`}
                  >
                    {isSelected ? (
                      <>
                        <Check className="w-3.5 h-3.5" />
                        <span>Active Project Workspace</span>
                      </>
                    ) : (
                      <>
                        <span>Select Workspace</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
