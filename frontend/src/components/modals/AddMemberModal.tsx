"use client";

import React, { useState } from "react";
import { X, Users, Mail, ArrowRight, AlertCircle } from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

export function AddMemberModal() {
  const { isAddMemberModalOpen, setIsAddMemberModalOpen, addMember } = useLiveApp();
  const [email, setEmail] = useState("");
  const [roleName, setRoleName] = useState("project_contributor");
  const [transitionRole, setTransitionRole] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isAddMemberModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setError("Email address is required");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await addMember({
        email: email.trim(),
        role_name: roleName,
        transition_role: transitionRole || undefined,
      });
      setEmail("");
      setRoleName("project_contributor");
      setTransitionRole("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add member to project workspace");
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
            <Users className="w-4 h-4 text-[#4774A9]" />
            <span>Add Member / Transition Participant</span>
          </div>
          <button
            type="button"
            onClick={() => setIsAddMemberModalOpen(false)}
            className="p-1 rounded text-[#69778D] hover:text-[#25334B]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-[#25334B] mb-1">
              Member Email Address <span className="text-rose-500">*</span>
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-[#69778D] absolute left-3 top-2.5" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="colleague@organization.com"
                className="w-full pl-9 pr-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#25334B] mb-1">
              Workspace Role
            </label>
            <select
              value={roleName}
              onChange={(e) => setRoleName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B] bg-white"
            >
              <option value="project_admin">Project Admin (Full Workspace Control)</option>
              <option value="project_lead">Project Lead (Manage Members &amp; Approvals)</option>
              <option value="project_contributor">Project Contributor (Upload &amp; Verify)</option>
              <option value="project_viewer">Project Viewer (Read-only)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#25334B] mb-1">
              Handover Transition Role (Optional)
            </label>
            <select
              value={transitionRole}
              onChange={(e) => setTransitionRole(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B] bg-white"
            >
              <option value="">No Transition Responsibility Assigned</option>
              <option value="departing_owner">Departing Knowledge Owner (Transferring responsibilities)</option>
              <option value="incoming_assignee">Incoming Assignee (Receiving handover package)</option>
              <option value="reviewer">Handover Reviewer (Approves verified package)</option>
              <option value="observer">Transition Observer (Stakeholder audit view)</option>
            </select>
          </div>

          <div className="pt-2 flex items-center justify-end gap-3 border-t border-[#DCE3EB]">
            <button
              type="button"
              onClick={() => setIsAddMemberModalOpen(false)}
              className="px-4 py-2 rounded-lg border border-[#DCE3EB] text-xs font-semibold text-[#69778D] hover:bg-[#F4F6F9]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg bg-[#4774A9] hover:bg-[#365F92] text-white text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <span>{isSubmitting ? "Adding..." : "Add to Project"}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
