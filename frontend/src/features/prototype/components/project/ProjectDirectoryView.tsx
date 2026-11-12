"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  FolderGit2,
  Plus,
  Search,
  Filter,
  Users,
  Clock,
  ArrowRight,
  Building2,
} from "lucide-react";
import { usePrototype } from "../../context/PrototypeContext";

export function ProjectDirectoryView() {
  const router = useRouter();
  const {
    projects,
    selectedProject,
    setSelectedProjectById,
    setIsCreateProjectModalOpen,
  } = usePrototype();

  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"name" | "recent">("recent");

  const filteredProjects = projects.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.organisationName.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus =
      statusFilter === "all" ? true : p.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="p-4 sm:p-6 space-y-5 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-[#25334B] tracking-tight flex items-center gap-2">
            <FolderGit2 className="w-6 h-6 text-[#4774A9]" />
            <span>Project Workspaces</span>
          </h1>
          <p className="text-xs text-[#69778D] mt-1">
            Multi-tenant workspace directory with tenant isolation, participant tracking, and knowledge handover status.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsCreateProjectModalOpen(true)}
          className="px-3.5 py-2 rounded-md bg-[#4774A9] hover:bg-[#365F92] text-xs font-semibold text-white flex items-center gap-2 transition-colors shadow-xs shrink-0"
        >
          <Plus className="w-3.5 h-3.5 text-white" />
          <span>Create Project</span>
        </button>
      </div>

      {/* Toolbar: Search & Filters */}
      <div className="bg-white rounded-lg border border-[#DCE3EB] p-3 flex flex-col md:flex-row items-center justify-between gap-3 text-xs shadow-2xs">
        <div className="flex items-center gap-2 w-full md:w-80">
          <div className="relative w-full">
            <Search className="w-3.5 h-3.5 text-[#69778D] absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search projects by name or keywords..."
              className="w-full pl-8 pr-3 py-1.5 rounded-md border border-[#DCE3EB] text-[#25334B] placeholder-[#69778D] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
            />
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto justify-end flex-wrap">
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-[#69778D]" />
            <span className="text-[#69778D] font-medium">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1 rounded border border-[#DCE3EB] bg-white text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
            >
              <option value="all">All Statuses</option>
              <option value="active">Active</option>
              <option value="planning">Planning</option>
              <option value="completed">Completed</option>
              <option value="archived">Archived</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[#69778D] font-medium">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as "name" | "recent")}
              className="px-2.5 py-1 rounded border border-[#DCE3EB] bg-white text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
            >
              <option value="recent">Most Recent</option>
              <option value="name">Project Name (A-Z)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Projects Grid / Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredProjects.map((proj) => {
          const isSelected = proj.id === selectedProject.id;
          return (
            <div
              key={proj.id}
              className={`bg-white rounded-lg border transition-all p-4 flex flex-col justify-between shadow-2xs ${
                isSelected
                  ? "border-[#4774A9] ring-2 ring-[#4774A9]/20"
                  : "border-[#DCE3EB] hover:border-[#4774A9]/60"
              }`}
            >
              <div className="space-y-3">
                {/* Header */}
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-[10px] text-[#69778D] font-semibold uppercase tracking-wider flex items-center gap-1">
                      <Building2 className="w-3 h-3 text-[#69778D]" />
                      <span>{proj.organisationName}</span>
                    </div>
                    <h2 className="text-base font-bold text-[#25334B] tracking-tight mt-0.5 truncate">
                      {proj.name}
                    </h2>
                  </div>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold capitalize shrink-0 ${
                      proj.status === "active"
                        ? "bg-[#269878]/10 text-[#269878] border border-[#269878]/20"
                        : proj.status === "planning"
                        ? "bg-[#C48A32]/10 text-[#C48A32] border border-[#C48A32]/20"
                        : "bg-[#E8EEF5] text-[#4774A9]"
                    }`}
                  >
                    {proj.status}
                  </span>
                </div>

                {/* Description */}
                <p className="text-xs text-[#69778D] line-clamp-2 leading-relaxed">
                  {proj.description}
                </p>

                {/* Transition Participants Badge */}
                <div className="p-2.5 rounded bg-[#F4F6F9] border border-[#DCE3EB] text-[11px] space-y-1">
                  <div className="text-[10px] uppercase font-bold text-[#69778D] tracking-wider">
                    Transition Participants
                  </div>
                  <div className="text-[#25334B] flex items-center justify-between font-medium">
                    <span className="truncate">{proj.transition.departingMember.name}</span>
                    <span className="text-[#4774A9] font-bold px-1">→</span>
                    <span className="truncate">{proj.transition.successor.name}</span>
                  </div>
                </div>

                {/* Metadata */}
                <div className="grid grid-cols-2 gap-2 text-[11px] text-[#69778D] pt-1">
                  <div className="flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5 text-[#4774A9]" />
                    <span>{proj.membersCount} members</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-[#249E91]" />
                    <span>Active {proj.lastActivityAt}</span>
                  </div>
                </div>
              </div>

              {/* Actions Footer */}
              <div className="mt-4 pt-3 border-t border-[#DCE3EB] flex items-center justify-between">
                <span className="text-[10px] text-[#69778D] font-mono">
                  Owner: {proj.owner.name.split(" ")[0]}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedProjectById(proj.id);
                    router.push("/prototype/overview");
                  }}
                  className={`px-3 py-1 rounded text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                    isSelected
                      ? "bg-[#249E91] text-white hover:bg-[#1f877c]"
                      : "bg-[#E8EEF5] text-[#4774A9] hover:bg-[#4774A9] hover:text-white"
                  }`}
                >
                  <span>{isSelected ? "Active Workspace" : "Open Workspace"}</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {filteredProjects.length === 0 && (
        <div className="bg-white rounded-lg border border-[#DCE3EB] p-12 text-center text-xs text-[#69778D]">
          <FolderGit2 className="w-10 h-10 text-[#69778D]/40 mx-auto mb-2" />
          <p className="font-semibold text-[#25334B] text-sm">No projects found</p>
          <p className="mt-1">Try adjusting your search query or status filter.</p>
        </div>
      )}
    </div>
  );
}
