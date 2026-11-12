"use client";

import React, { useState } from "react";
import { X, FolderPlus, AlertCircle } from "lucide-react";
import { usePrototype } from "../../context/PrototypeContext";
import type { ProjectStatus, ProjectVisibility } from "../../types";

export function CreateProjectModal() {
  const {
    isCreateProjectModalOpen,
    setIsCreateProjectModalOpen,
    createProject,
    members,
  } = usePrototype();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [ownerId, setOwnerId] = useState(members[5]?.id || "");
  const [managerId, setManagerId] = useState(members[5]?.id || "");
  const [status, setStatus] = useState<ProjectStatus>("active");
  const [visibility] = useState<ProjectVisibility>("private");
  const [startDate, setStartDate] = useState("2026-11-15");
  const [targetCompletionDate, setTargetCompletionDate] = useState("2027-04-30");
  const [error, setError] = useState<string | null>(null);

  if (!isCreateProjectModalOpen) return null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Project name is required.");
      return;
    }
    if (name.trim().length < 3) {
      setError("Project name must be at least 3 characters.");
      return;
    }
    if (startDate && targetCompletionDate && targetCompletionDate < startDate) {
      setError("Target completion date must not precede start date.");
      return;
    }

    const defaultMember = members[0] || {
      id: "default-owner",
      name: "Alex Vance",
      role: "Backend Lead",
      email: "alex.vance@nexora.internal",
    };
    const defaultSuccessor = members[1] || {
      id: "default-successor",
      name: "Daniel Cho",
      role: "Incoming Developer",
      email: "daniel.cho@nexora.internal",
    };

    const ownerMember = members.find((m) => m.id === ownerId) || defaultMember;
    const managerMember = members.find((m) => m.id === managerId) || defaultMember;
    const slug = name
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "");

    createProject({
      name: name.trim(),
      slug: slug || "new-project",
      organisationName: "Nexora Technologies",
      description: description.trim() || "Created in interactive prototype session.",
      status,
      visibility,
      owner: {
        id: ownerMember.id,
        name: ownerMember.name,
        role: ownerMember.role,
        email: ownerMember.email,
      },
      projectManager: {
        id: managerMember.id,
        name: managerMember.name,
        role: managerMember.role,
        email: managerMember.email,
      },
      startDate,
      targetCompletionDate,
      transition: {
        departingMember: {
          id: defaultMember.id,
          name: defaultMember.name,
          role: defaultMember.role,
          email: defaultMember.email,
        },
        successor: {
          id: defaultSuccessor.id,
          name: defaultSuccessor.name,
          role: defaultSuccessor.role,
          email: defaultSuccessor.email,
        },
        targetHandoverDate: targetCompletionDate,
        workflowStage: "connect",
        handoverScope: "Initial scope defined in prototype.",
      },
    });

    setIsCreateProjectModalOpen(false);
    setName("");
    setDescription("");
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-project-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs select-none"
    >
      <div className="w-full max-w-lg bg-white rounded-lg border border-[#DCE3EB] shadow-2xl overflow-hidden flex flex-col text-xs">
        {/* Header */}
        <div className="px-4 py-3 bg-[#F4F6F9] border-b border-[#DCE3EB] flex items-center justify-between">
          <div className="flex items-center gap-2 text-[#25334B] font-bold text-sm">
            <FolderPlus className="w-4 h-4 text-[#4774A9]" />
            <span id="create-project-modal-title">Create Project Workspace</span>
          </div>
          <button
            type="button"
            onClick={() => setIsCreateProjectModalOpen(false)}
            className="p-1 text-[#69778D] hover:text-[#25334B] rounded"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Prototype Banner */}
        <div className="px-4 py-1.5 bg-[#C48A32]/10 border-b border-[#C48A32]/20 text-[11px] text-[#C48A32] flex items-center justify-between font-mono">
          <span>PROTOTYPE ONLY · DATA RESETS ON REFRESH</span>
          <span>NO BACKEND WRITES</span>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-3.5">
          {error && (
            <div className="p-2.5 rounded bg-[#C65B60]/10 border border-[#C65B60]/30 text-[#C65B60] flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block font-semibold text-[#25334B] mb-1">
              Project Name <span className="text-[#C65B60]">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Settlement Rail Modernization"
              className="w-full px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] placeholder-[#69778D] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
              required
            />
          </div>

          <div>
            <label className="block font-semibold text-[#25334B] mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Brief summary of project objectives and architecture scope..."
              className="w-full px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] placeholder-[#69778D] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-[#25334B] mb-1">
                Project Owner
              </label>
              <select
                value={ownerId}
                onChange={(e) => setOwnerId(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] bg-white focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
              >
                {members.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.role})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block font-semibold text-[#25334B] mb-1">
                Project Manager
              </label>
              <select
                value={managerId}
                onChange={(e) => setManagerId(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] bg-white focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
              >
                {members.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.role})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block font-semibold text-[#25334B] mb-1">
                Project Status
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as ProjectStatus)}
                className="w-full px-2.5 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] bg-white focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
              >
                <option value="active">Active</option>
                <option value="planning">Planning</option>
                <option value="completed">Completed</option>
                <option value="archived">Archived</option>
              </select>
            </div>
            <div>
              <label className="block font-semibold text-[#25334B] mb-1">
                Start Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] bg-white focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
              />
            </div>
            <div>
              <label className="block font-semibold text-[#25334B] mb-1">
                Target Completion
              </label>
              <input
                type="date"
                value={targetCompletionDate}
                onChange={(e) => setTargetCompletionDate(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] bg-white focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
              />
            </div>
          </div>

          {/* Actions */}
          <div className="pt-3 border-t border-[#DCE3EB] flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsCreateProjectModalOpen(false)}
              className="px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] hover:bg-[#F4F6F9] font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded bg-[#4774A9] hover:bg-[#365F92] text-white font-semibold transition-colors shadow-xs"
            >
              Create Workspace (Demo)
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
