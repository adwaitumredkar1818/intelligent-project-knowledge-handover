"use client";

import React, { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  FolderPlus,
  LayoutGrid,
  List,
  Plus,
  Clock,
  Search,
  Loader2,
} from "lucide-react";
import {
  PageHeader,
  Button,
  Card,
  Table,
  Th,
  Td,
  SearchInput,
  Select,
  Segmented,
  RoleBadge,
  StatusBadge,
  Progress,
  AvatarGroup,
  EmptyState,
} from "../ui";
import { SourceIcon } from "../brand/brand";
import {
  getProjectCode,
  getProjectColor,
  normalizeProjectRole,
} from "../project-workspace/project-utils";
import { useLiveApp } from "../../context/LiveAppContext";
import type { Project } from "../../lib/types";

export function ProjectsView() {
  const router = useRouter();
  const {
    projects,
    activeProject,
    setActiveProject,
    setIsCreateProjectModalOpen,
    activeOrg,
    isLoadingProjects,
  } = useLiveApp();

  const [view, setView] = useState<"grid" | "list">("grid");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [roleFilter, setRoleFilter] = useState("all");

  const filteredProjects = useMemo(() => {
    return projects.filter((p) => {
      // Search filter
      const matchesSearch =
        p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (p.description &&
          p.description.toLowerCase().includes(searchTerm.toLowerCase())) ||
        p.slug.toLowerCase().includes(searchTerm.toLowerCase());

      if (!matchesSearch) return false;

      // Status filter
      if (statusFilter !== "all" && p.status !== statusFilter) {
        return false;
      }

      // Role filter
      if (roleFilter !== "all") {
        const normRole = (p.my_project_role || "").toLowerCase();
        if (roleFilter === "manager" && !normRole.includes("manager")) return false;
        if (roleFilter === "reviewer" && !normRole.includes("reviewer")) return false;
        if (
          roleFilter === "outgoing" &&
          !normRole.includes("outgoing") &&
          !normRole.includes("departing")
        )
          return false;
        if (
          roleFilter === "incoming" &&
          !normRole.includes("incoming") &&
          !normRole.includes("successor")
        )
          return false;
        if (roleFilter === "member" && normRole.includes("manager")) return false;
      }

      return true;
    });
  }, [projects, searchTerm, statusFilter, roleFilter]);

  const handleSelectProject = (project: Project) => {
    setActiveProject(project);
    router.push(`/projects/${project.id}`);
  };

  const handleClearFilters = () => {
    setSearchTerm("");
    setStatusFilter("all");
    setRoleFilter("all");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="My Projects"
        subtitle={`Projects you belong to in ${activeOrg?.name || "your organisation"}. Your role is set per project and determines what you can see and do.`}
        actions={
          <Button
            variant="primary"
            icon={Plus}
            onClick={() => setIsCreateProjectModalOpen(true)}
          >
            Create project
          </Button>
        }
      />

      {/* Filter Bar */}
      <div className="flex flex-col gap-3 md:flex-row md:items-center">
        <SearchInput
          placeholder="Search projects"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="md:w-72"
        />

        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-36 text-xs"
          >
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="planning">Planning</option>
            <option value="on_hold">On hold</option>
            <option value="completed">Completed</option>
            <option value="archived">Archived</option>
          </Select>

          <Select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="w-40 text-xs"
          >
            <option value="all">All my roles</option>
            <option value="manager">Project Manager</option>
            <option value="reviewer">Reviewer</option>
            <option value="outgoing">Outgoing Member</option>
            <option value="incoming">Incoming Member</option>
            <option value="member">General Member</option>
          </Select>
        </div>

        <div className="md:ml-auto flex items-center gap-2">
          <Segmented
            value={view}
            onChange={(v) => setView(v as "grid" | "list")}
            options={[
              { id: "grid", icon: LayoutGrid, label: "Grid" },
              { id: "list", icon: List, label: "List" },
            ]}
          />
        </div>
      </div>

      {/* Content Area */}
      {isLoadingProjects ? (
        <div className="flex items-center justify-center p-16 text-xs text-muted gap-2">
          <Loader2 className="size-4 animate-spin text-brand" />
          <span>Loading project workspaces...</span>
        </div>
      ) : projects.length === 0 ? (
        <Card>
          <EmptyState
            icon={FolderPlus}
            title="No projects yet"
            body="Create a project to connect sources, add members and start capturing knowledge."
            action={
              <Button
                variant="primary"
                icon={Plus}
                onClick={() => setIsCreateProjectModalOpen(true)}
              >
                Create project
              </Button>
            }
          />
        </Card>
      ) : filteredProjects.length === 0 ? (
        <Card>
          <EmptyState
            icon={Search}
            title="No matching projects"
            body="Try a different search term or clear active filters."
            action={
              <Button variant="secondary" onClick={handleClearFilters}>
                Clear filters
              </Button>
            }
          />
        </Card>
      ) : view === "grid" ? (
        /* GRID VIEW */
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filteredProjects.map((p) => {
            const projectCode = getProjectCode(p.name, p.slug);
            const projectColor = getProjectColor(p.id);
            const role = normalizeProjectRole(p.my_project_role);
            const isSelected = activeProject?.id === p.id;
            const coverage = 45; // Estimated coverage metric

            return (
              <div
                key={p.id}
                onClick={() => handleSelectProject(p)}
                className="group cursor-pointer"
              >
                <Card
                  className={`tile-target flex h-full flex-col p-5 transition duration-200 border ${
                    isSelected
                      ? "border-brand ring-2 ring-brand/15 bg-tint/10"
                      : "hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <span
                      className="flex size-10 items-center justify-center rounded-xl text-xs font-bold text-white shadow-2xs"
                      style={{ background: projectColor }}
                    >
                      {projectCode}
                    </span>
                    <StatusBadge status={p.status || "active"} />
                  </div>

                  <h3 className="mt-4 text-[15px] font-semibold text-navy group-hover:text-brand transition-colors">
                    {p.name}
                  </h3>

                  <p className="mt-1 line-clamp-2 flex-1 text-xs text-muted leading-relaxed">
                    {p.description || "No description provided."}
                  </p>

                  <div className="mt-4">
                    <RoleBadge role={role} />
                  </div>

                  <div className="mt-4">
                    <div className="mb-1.5 flex justify-between text-xs">
                      <span className="text-muted">Knowledge coverage</span>
                      <span className="font-medium text-navy">{coverage}%</span>
                    </div>
                    <Progress value={coverage} size="sm" />
                  </div>

                  <div className="mt-4 flex items-center justify-between border-t border-line pt-4">
                    <AvatarGroup names={["Lead", "Assignee"]} size={24} />
                    <div className="flex items-center gap-1">
                      <SourceIcon type="github" size={22} />
                      <SourceIcon type="docs" size={22} />
                    </div>
                  </div>

                  <p className="mt-3 flex items-center gap-1.5 text-[11px] text-muted font-mono">
                    <Clock className="size-3" />
                    <span>
                      Updated{" "}
                      {new Date(p.updated_at || p.created_at).toLocaleDateString(
                        "en-GB",
                        { month: "short", day: "numeric" }
                      )}
                    </span>
                  </p>
                </Card>
              </div>
            );
          })}
        </div>
      ) : (
        /* LIST VIEW */
        <Card className="overflow-hidden">
          <Table>
            <thead>
              <tr>
                <Th>Project</Th>
                <Th>Your Role</Th>
                <Th>Visibility</Th>
                <Th>Members</Th>
                <Th>Sources</Th>
                <Th>Last Updated</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {filteredProjects.map((p) => {
                const projectCode = getProjectCode(p.name, p.slug);
                const projectColor = getProjectColor(p.id);
                const role = normalizeProjectRole(p.my_project_role);

                return (
                  <tr
                    key={p.id}
                    onClick={() => handleSelectProject(p)}
                    className="cursor-pointer hover:bg-slate-50/70 transition-colors"
                  >
                    <Td>
                      <span className="flex items-center gap-3">
                        <span
                          className="flex size-8 shrink-0 items-center justify-center rounded-lg text-[10px] font-bold text-white shadow-2xs"
                          style={{ background: projectColor }}
                        >
                          {projectCode}
                        </span>
                        <span>
                          <span className="block font-semibold text-xs text-navy">
                            {p.name}
                          </span>
                          <span className="text-[11px] text-muted">
                            {p.slug}
                          </span>
                        </span>
                      </span>
                    </Td>
                    <Td>
                      <RoleBadge role={role} />
                    </Td>
                    <Td>
                      <span className="text-xs text-navy capitalize">
                        {p.visibility || "Private"}
                      </span>
                    </Td>
                    <Td>
                      <AvatarGroup names={["Lead", "Assignee"]} size={22} />
                    </Td>
                    <Td>
                      <span className="flex gap-1">
                        <SourceIcon type="github" size={22} />
                        <SourceIcon type="docs" size={22} />
                      </span>
                    </Td>
                    <Td className="text-xs text-muted font-mono">
                      {new Date(p.updated_at || p.created_at).toLocaleDateString(
                        "en-GB",
                        { month: "short", day: "numeric" }
                      )}
                    </Td>
                    <Td>
                      <StatusBadge status={p.status || "active"} />
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </Card>
      )}
    </div>
  );
}
