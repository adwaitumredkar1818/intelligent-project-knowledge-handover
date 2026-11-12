"use client";

import React from "react";
import {
  Users,
  Plus,
  Shield,
  UserCheck,
  UserX,
  Mail,
  Award,
  ArrowRight,
  Info,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

export function TeamMembersView() {
  const {
    activeProject,
    members,
    isLoadingMembers,
    setIsAddMemberModalOpen,
    updateMember,
  } = useLiveApp();

  const handleRoleChange = async (memberId: string, transitionRole: string) => {
    try {
      await updateMember(memberId, {
        transition_role: transitionRole || undefined,
      });
    } catch (err) {
      console.error(err);
    }
  };

  if (!activeProject) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-[#DCE3EB]">
        <Users className="w-12 h-12 text-[#69778D] mb-3 mx-auto" />
        <div className="font-bold text-sm text-[#25334B]">No Active Project Selected</div>
        <p className="text-xs text-[#69778D] mt-1">Select a project to inspect team members and transition roles.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-[#4774A9] uppercase tracking-wider">
            <span>Project Workspace Team</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#249E91]" />
            <span className="text-[#69778D] font-normal">{activeProject.name}</span>
          </div>
          <h1 className="text-xl font-bold text-[#25334B] mt-1 tracking-tight">
            Team Members &amp; Transition Roles
          </h1>
          <p className="text-xs text-[#69778D] mt-0.5">
            Configure project contributors and assign transition responsibilities (Departing Owner, Incoming Assignee, Reviewer, Observer).
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsAddMemberModalOpen(true)}
          className="px-4 py-2.5 rounded-lg bg-[#4774A9] hover:bg-[#365F92] text-white text-xs font-semibold flex items-center gap-2 transition-colors shadow-xs shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Add Team Member</span>
        </button>
      </div>

      {/* Information Banner */}
      <div className="p-4 rounded-xl bg-sky-50/70 border border-sky-200 flex items-start gap-3 text-xs text-sky-950">
        <Info className="w-4 h-4 text-[#4774A9] shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-semibold">Handover Governance Rule:</span> Handover packages require formal approval by a designated <strong>Reviewer</strong>. The <strong>Incoming Assignee</strong> acknowledges receipt, which cannot substitute for reviewer approval.
        </div>
      </div>

      {/* Members Table */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] shadow-2xs overflow-hidden">
        <div className="px-5 py-3.5 border-b border-[#DCE3EB] bg-[#F4F6F9] flex items-center justify-between text-xs font-semibold text-[#69778D]">
          <span>Project Participant ({members.length})</span>
          <span>Transition Responsibility</span>
        </div>

        {members.length === 0 ? (
          <div className="p-8 text-center">
            <Users className="w-10 h-10 text-[#69778D] mx-auto mb-2 opacity-50" />
            <div className="text-xs font-semibold text-[#25334B]">No Members Configured</div>
            <p className="text-[11px] text-[#69778D] mt-1">Add colleagues to this workspace to assign transition roles.</p>
          </div>
        ) : (
          <div className="divide-y divide-[#DCE3EB]">
            {members.map((member) => {
              const transitionBadgeClasses: Record<string, string> = {
                departing_owner: "bg-rose-50 text-rose-700 border-rose-200",
                incoming_assignee: "bg-emerald-50 text-emerald-700 border-emerald-200",
                reviewer: "bg-indigo-50 text-indigo-700 border-indigo-200",
                observer: "bg-gray-100 text-gray-700 border-gray-200",
              };

              return (
                <div
                  key={member.id}
                  className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-[#F4F6F9]/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-[#253650] text-white font-bold text-xs flex items-center justify-center shrink-0 border border-[#249E91]/40">
                      {member.user_full_name ? member.user_full_name.charAt(0).toUpperCase() : "U"}
                    </div>
                    <div>
                      <div className="font-semibold text-xs text-[#25334B] flex items-center gap-2">
                        <span>{member.user_full_name || "Workspace Member"}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#E8EEF5] text-[#4774A9] font-medium">
                          {member.role_name.replace("project_", "").toUpperCase()}
                        </span>
                      </div>
                      <div className="text-[11px] text-[#69778D] flex items-center gap-1.5 mt-0.5">
                        <Mail className="w-3 h-3 text-[#69778D]" />
                        <span>{member.user_email || "user@org.internal"}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <select
                      value={member.transition_role || ""}
                      onChange={(e) => handleRoleChange(member.id, e.target.value)}
                      className="px-3 py-1.5 rounded-lg border border-[#DCE3EB] text-xs font-semibold text-[#25334B] bg-white focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
                    >
                      <option value="">No Transition Role</option>
                      <option value="departing_owner">Departing Knowledge Owner</option>
                      <option value="incoming_assignee">Incoming Assignee</option>
                      <option value="reviewer">Handover Reviewer (Approver)</option>
                      <option value="observer">Transition Observer</option>
                    </select>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
