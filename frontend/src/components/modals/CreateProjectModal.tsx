"use client";

import React, { useState } from "react";
import { X, FolderGit2, Calendar, FileText, ArrowRight, AlertCircle } from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

export function CreateProjectModal() {
  const { isCreateProjectModalOpen, setIsCreateProjectModalOpen, createProject, activeOrg } = useLiveApp();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isCreateProjectModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Project name is required");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await createProject({
        name: name.trim(),
        description: description.trim() || undefined,
        target_handover_date: targetDate ? new Date(targetDate).toISOString() : undefined,
      });
      setName("");
      setDescription("");
      setTargetDate("");
    } catch (err: any) {
      setError(err.message || "Failed to create project");
    } finally {
      setIsSubmitting(false);
    }
  };

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
              className="px-4 py-2 rounded-lg bg-[#4774A9] hover:bg-[#365F92] text-white text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
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
