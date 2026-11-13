"use client";

import React, { useState } from "react";
import { X, FolderGit2, Calendar, ArrowRight, AlertCircle, Building2, Plus } from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

export function CreateProjectModal() {
  const {
    isCreateProjectModalOpen,
    setIsCreateProjectModalOpen,
    createProject,
    organisations,
    activeOrg,
  } = useLiveApp();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");
  const [isCreatingNewOrg, setIsCreatingNewOrg] = useState(false);
  const [newOrgName, setNewOrgName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync selected organisation when modal opens or org list updates
  useEffect(() => {
    setError(null);
    if (activeOrg) {
      setSelectedOrgId(activeOrg.id);
      setIsCreatingNewOrg(false);
    } else if (organisations && organisations.length > 0 && organisations[0]) {
      setSelectedOrgId(organisations[0].id);
      setIsCreatingNewOrg(false);
    } else {
      setIsCreatingNewOrg(true);
    }
  }, [activeOrg, organisations, isCreateProjectModalOpen]);
  if (!isCreateProjectModalOpen) return null;

  const effectiveSelectedOrgId =
    selectedOrgId && organisations.some((o) => o.id === selectedOrgId)
      ? selectedOrgId
      : activeOrg?.id || organisations[0]?.id || "";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Project name is required");
      return;
    }

    const needsNewOrg = (organisations.length === 0 || isCreatingNewOrg);
    if (needsNewOrg && !newOrgName.trim()) {
      setError("Please enter an organisation workspace name (e.g. Acme Engineering)");
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      const options = needsNewOrg
        ? { newOrgName: newOrgName.trim() }
        : { orgId: effectiveSelectedOrgId || activeOrg?.id };

      await createProject(
        {
          name: name.trim(),
          description: description.trim() || undefined,
          target_handover_date: targetDate ? new Date(targetDate).toISOString() : undefined,
        },
        options
      );

      setName("");
      setDescription("");
      setTargetDate("");
      setNewOrgName("");
      setSelectedOrgId("");
      setIsCreatingNewOrg(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setIsSubmitting(false);
    }
  };

  const showNewOrgInput = organisations.length === 0 || isCreatingNewOrg;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-2xs p-4">
      <div className="w-full max-w-lg bg-white rounded-xl shadow-xl border border-[#DCE3EB] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-[#F4F6F9] border-b border-[#DCE3EB] flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-bold text-[#25334B]">
            <FolderGit2 className="w-4 h-4 text-[#4774A9]" />
            <span>Create New Project Workspace</span>
          </div>
          <button
            type="button"
            onClick={() => setIsCreateProjectModalOpen(false)}
            className="p-1 rounded text-[#69778D] hover:text-[#25334B]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Organisation Workspace Selector or Creator */}
          {showNewOrgInput ? (
            <div>
              <label className="block text-xs font-semibold text-[#25334B] mb-1">
                Organisation Workspace <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <Building2 className="w-4 h-4 text-[#69778D] absolute left-3 top-2.5" />
                <input
                  type="text"
                  required
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  placeholder="e.g. Acme Corporation or Engineering Team"
                  className="w-full pl-9 pr-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
                />
              </div>
              <div className="flex items-center justify-between mt-1">
                <p className="text-[11px] text-[#69778D]">
                  Every project belongs to an organisation container.
                </p>
                {organisations.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setIsCreatingNewOrg(false)}
                    className="text-[11px] text-[#4774A9] hover:underline font-semibold"
                  >
                    Select existing organisation
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-[#25334B]">
                  Organisation Workspace <span className="text-rose-500">*</span>
                </label>
                <button
                  type="button"
                  onClick={() => setIsCreatingNewOrg(true)}
                  className="text-[11px] text-[#4774A9] hover:underline font-semibold flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" />
                  <span>New Org</span>
                </button>
              </div>
              <div className="relative">
                <Building2 className="w-4 h-4 text-[#69778D] absolute left-3 top-2.5 pointer-events-none" />
                <select
                  value={effectiveSelectedOrgId}
                  onChange={(e) => setSelectedOrgId(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B] bg-white"
                >
                  {organisations.map((org) => (
                    <option key={org.id} value={org.id}>
                      {org.name} ({org.slug})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-[#25334B] mb-1">
              Project Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Core Banking Migration 2026"
              className="w-full px-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#25334B] mb-1">
              Description &amp; Handover Scope
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="State the purpose, architecture domain, and transitioning responsibilities..."
              className="w-full px-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B] resize-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#25334B] mb-1">
              Target Handover Date (Optional)
            </label>
            <div className="relative">
              <Calendar className="w-4 h-4 text-[#69778D] absolute left-3 top-2.5" />
              <input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                className="w-full pl-9 pr-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
              />
            </div>
          </div>

          <div className="pt-2 flex items-center justify-end gap-3 border-t border-[#DCE3EB]">
            <button
              type="button"
              onClick={() => setIsCreateProjectModalOpen(false)}
              className="px-4 py-2 rounded-lg border border-[#DCE3EB] text-xs font-semibold text-[#69778D] hover:bg-[#F4F6F9]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg bg-[#4774A9] hover:bg-[#365F92] text-white text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer shadow-xs"
            >
              <span>{isSubmitting ? "Creating..." : "Create Project"}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
