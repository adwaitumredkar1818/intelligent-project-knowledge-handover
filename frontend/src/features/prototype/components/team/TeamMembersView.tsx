"use client";

import React, { useState } from "react";
import {
  Users,
  UserPlus,
  Search,
  Filter,
  Trash2,
  Edit2,
  ArrowRightLeft,
  AlertCircle,
  ShieldCheck,
} from "lucide-react";
import { usePrototype } from "../../context/PrototypeContext";
import type { MemberRole, TeamMember } from "../../types";

export function TeamMembersView() {
  const {
    members,
    addMember,
    updateMember,
    removeMember,
    setTransitionRoles,
    addToast,
  } = usePrototype();

  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [designationFilter, setDesignationFilter] = useState<string>("all");

  // Modal states
  const [isAddMemberModalOpen, setIsAddMemberModalOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<TeamMember | null>(null);
  const [isTransitionModalOpen, setIsTransitionModalOpen] = useState(false);
  const [departingId, setDepartingId] = useState("");
  const [successorId, setSuccessorId] = useState("");

  // New member form
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newRole, setNewRole] = useState("Staff Backend Engineer");
  const [newRoleCode, setNewRoleCode] = useState<MemberRole>("developer");
  const [newResp, setNewResp] = useState("");

  const filteredMembers = members.filter((m) => {
    const matchesSearch =
      m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.responsibilities.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.role.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesRole = roleFilter === "all" ? true : m.roleCode === roleFilter;
    const matchesDesignation =
      designationFilter === "all"
        ? true
        : m.transitionDesignation === designationFilter;

    return matchesSearch && matchesRole && matchesDesignation;
  });

  function handleCreateMember(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim() || !newEmail.trim()) {
      addToast({
        type: "error",
        title: "Validation Error",
        message: "Name and email are required.",
      });
      return;
    }

    addMember({
      name: newName.trim(),
      email: newEmail.trim(),
      role: newRole.trim() || "Developer",
      roleCode: newRoleCode,
      responsibilities:
        newResp.trim() || "General engineering and service maintenance.",
      status: "active",
      transitionDesignation: "standard",
    });

    setIsAddMemberModalOpen(false);
    setNewName("");
    setNewEmail("");
    setNewResp("");
  }

  function handleSaveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editingMember) return;

    updateMember(editingMember.id, {
      role: editingMember.role,
      responsibilities: editingMember.responsibilities,
      status: editingMember.status,
    });
    setEditingMember(null);
  }

  function handleSaveTransition(e: React.FormEvent) {
    e.preventDefault();
    if (!departingId || !successorId) {
      addToast({
        type: "error",
        title: "Selection Required",
        message: "Please choose both a departing member and a successor.",
      });
      return;
    }

    const success = setTransitionRoles(departingId, successorId);
    if (success) {
      setIsTransitionModalOpen(false);
    }
  }

  return (
    <div className="p-4 sm:p-6 space-y-5 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-[#25334B] tracking-tight flex items-center gap-2">
            <Users className="w-6 h-6 text-[#4774A9]" />
            <span>Team Members &amp; Ownership</span>
          </h1>
          <p className="text-xs text-[#69778D] mt-1">
            Assigned project collaborators, role-based responsibilities, and designated handover transition participants.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => {
              const departing = members.find((m) => m.transitionDesignation === "departing_owner");
              const successor = members.find((m) => m.transitionDesignation === "successor");
              setDepartingId(departing?.id || members[0]?.id || "");
              setSuccessorId(successor?.id || members[1]?.id || "");
              setIsTransitionModalOpen(true);
            }}
            className="px-3 py-2 rounded-md border border-[#DCE3EB] bg-white hover:bg-[#F4F6F9] text-xs font-semibold text-[#25334B] flex items-center gap-2 transition-colors shadow-2xs"
          >
            <ArrowRightLeft className="w-3.5 h-3.5 text-[#249E91]" />
            <span>Configure Transition</span>
          </button>

          <button
            type="button"
            onClick={() => setIsAddMemberModalOpen(true)}
            className="px-3.5 py-2 rounded-md bg-[#4774A9] hover:bg-[#365F92] text-xs font-semibold text-white flex items-center gap-2 transition-colors shadow-xs"
          >
            <UserPlus className="w-3.5 h-3.5 text-white" />
            <span>Add Member</span>
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="bg-white rounded-lg border border-[#DCE3EB] p-3 flex flex-col md:flex-row items-center justify-between gap-3 text-xs shadow-2xs">
        <div className="flex items-center gap-2 w-full md:w-80">
          <div className="relative w-full">
            <Search className="w-3.5 h-3.5 text-[#69778D] absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name, role, email, or domain..."
              className="w-full pl-8 pr-3 py-1.5 rounded-md border border-[#DCE3EB] text-[#25334B] placeholder-[#69778D] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
            />
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto justify-end flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="text-[#69778D] font-medium">Role:</span>
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="px-2.5 py-1 rounded border border-[#DCE3EB] bg-white text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
            >
              <option value="all">All Roles</option>
              <option value="lead">Lead / Principal</option>
              <option value="developer">Developer</option>
              <option value="designer">Designer</option>
              <option value="reviewer">Reviewer</option>
              <option value="stakeholder">Stakeholder</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-[#69778D]" />
            <span className="text-[#69778D] font-medium">Designation:</span>
            <select
              value={designationFilter}
              onChange={(e) => setDesignationFilter(e.target.value)}
              className="px-2.5 py-1 rounded border border-[#DCE3EB] bg-white text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
            >
              <option value="all">All Designations</option>
              <option value="departing_owner">Departing Owner</option>
              <option value="successor">Incoming Successor</option>
              <option value="standard">Standard Member</option>
            </select>
          </div>

          <div className="text-[11px] text-[#69778D] font-medium pl-2">
            Showing {filteredMembers.length} of {members.length} members
          </div>
        </div>
      </div>

      {/* Team Table */}
      <div className="bg-white rounded-lg border border-[#DCE3EB] shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#F4F6F9] border-b border-[#DCE3EB] text-[#69778D] uppercase font-bold text-[10px] tracking-wider">
              <tr>
                <th className="py-2.5 px-4">Member</th>
                <th className="py-2.5 px-3">Role</th>
                <th className="py-2.5 px-3">Project Responsibilities</th>
                <th className="py-2.5 px-3">Transition Designation</th>
                <th className="py-2.5 px-3 text-center">Status</th>
                <th className="py-2.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#DCE3EB]">
              {filteredMembers.map((member) => (
                <tr
                  key={member.id}
                  className="hover:bg-[#F4F6F9]/80 transition-colors"
                >
                  {/* Member Name + Avatar + Email */}
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-[#304563] text-white flex items-center justify-center font-bold text-xs shrink-0">
                        {member.avatarInitials}
                      </div>
                      <div className="min-w-0">
                        <div className="font-semibold text-[#25334B] truncate">
                          {member.name}
                        </div>
                        <div className="text-[11px] text-[#69778D] truncate font-mono">
                          {member.email}
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* Role */}
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#E8EEF5] text-[#4774A9]">
                      {member.role}
                    </span>
                  </td>

                  {/* Responsibilities */}
                  <td className="py-3 px-3 max-w-xs">
                    <p className="text-xs text-[#25334B] leading-snug truncate" title={member.responsibilities}>
                      {member.responsibilities}
                    </p>
                  </td>

                  {/* Transition Designation */}
                  <td className="py-3 px-3">
                    {member.transitionDesignation === "departing_owner" ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-[#C48A32]/15 text-[#C48A32] border border-[#C48A32]/30">
                        <span>● Departing Owner</span>
                      </span>
                    ) : member.transitionDesignation === "successor" ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-[#249E91]/15 text-[#249E91] border border-[#249E91]/30">
                        <span>● Successor</span>
                      </span>
                    ) : (
                      <span className="text-[#69778D] text-[11px]">Standard Contributor</span>
                    )}
                  </td>

                  {/* Status */}
                  <td className="py-3 px-3 text-center">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#269878]/10 text-[#269878] border border-[#269878]/20 capitalize">
                      {member.status}
                    </span>
                  </td>

                  {/* Actions */}
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        type="button"
                        onClick={() => setEditingMember(member)}
                        className="p-1.5 text-[#69778D] hover:text-[#4774A9] hover:bg-[#E8EEF5] rounded transition-colors"
                        title="Edit member responsibilities"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => removeMember(member.id)}
                        className="p-1.5 text-[#69778D] hover:text-[#C65B60] hover:bg-[#C65B60]/10 rounded transition-colors"
                        title="Remove member from workspace"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 1. Add Member Modal */}
      {isAddMemberModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs select-none"
        >
          <div className="w-full max-w-md bg-white rounded-lg border border-[#DCE3EB] shadow-2xl p-5 space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-[#DCE3EB] pb-2">
              <div className="font-bold text-sm text-[#25334B] flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-[#4774A9]" />
                <span>Add Team Member to Project</span>
              </div>
              <button
                type="button"
                onClick={() => setIsAddMemberModalOpen(false)}
                className="text-[#69778D] hover:text-[#25334B]"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateMember} className="space-y-3">
              <div>
                <label className="block font-semibold text-[#25334B] mb-1">Full Name</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Jordan Reed"
                  className="w-full px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-[#25334B] mb-1">Email</label>
                <input
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="e.g. jordan.reed@nexora.internal"
                  className="w-full px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-[#25334B] mb-1">Project Role Title</label>
                <input
                  type="text"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  placeholder="e.g. Senior Security Engineer"
                  className="w-full px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
                />
              </div>

              <div>
                <label className="block font-semibold text-[#25334B] mb-1">Role Classification</label>
                <select
                  value={newRoleCode}
                  onChange={(e) => setNewRoleCode(e.target.value as MemberRole)}
                  className="w-full px-2.5 py-1.5 rounded border border-[#DCE3EB] bg-white text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
                >
                  <option value="lead">Lead / Principal</option>
                  <option value="developer">Developer / Engineer</option>
                  <option value="designer">Designer</option>
                  <option value="reviewer">Reviewer</option>
                  <option value="stakeholder">Stakeholder</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-[#25334B] mb-1">Responsibilities</label>
                <textarea
                  value={newResp}
                  onChange={(e) => setNewResp(e.target.value)}
                  rows={2}
                  placeholder="Specific modules, services, or architecture areas owned by this member..."
                  className="w-full px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
                />
              </div>

              <div className="pt-2 border-t border-[#DCE3EB] flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsAddMemberModalOpen(false)}
                  className="px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3.5 py-1.5 rounded bg-[#4774A9] text-white font-semibold hover:bg-[#365F92]"
                >
                  Add Member (Demo)
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 2. Edit Member Modal */}
      {editingMember && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs select-none"
        >
          <div className="w-full max-w-md bg-white rounded-lg border border-[#DCE3EB] shadow-2xl p-5 space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-[#DCE3EB] pb-2">
              <div className="font-bold text-sm text-[#25334B] flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-[#4774A9]" />
                <span>Edit Member Responsibilities</span>
              </div>
              <button
                type="button"
                onClick={() => setEditingMember(null)}
                className="text-[#69778D] hover:text-[#25334B]"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="space-y-3">
              <div>
                <label className="block font-semibold text-[#25334B] mb-1">Member Name</label>
                <input
                  type="text"
                  value={editingMember.name}
                  disabled
                  className="w-full px-3 py-1.5 rounded border border-[#DCE3EB] bg-[#F4F6F9] text-[#69778D]"
                />
              </div>

              <div>
                <label className="block font-semibold text-[#25334B] mb-1">Role Title</label>
                <input
                  type="text"
                  value={editingMember.role}
                  onChange={(e) =>
                    setEditingMember({ ...editingMember, role: e.target.value })
                  }
                  className="w-full px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
                />
              </div>

              <div>
                <label className="block font-semibold text-[#25334B] mb-1">Responsibilities</label>
                <textarea
                  value={editingMember.responsibilities}
                  onChange={(e) =>
                    setEditingMember({
                      ...editingMember,
                      responsibilities: e.target.value,
                    })
                  }
                  rows={3}
                  className="w-full px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
                />
              </div>

              <div className="pt-2 border-t border-[#DCE3EB] flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setEditingMember(null)}
                  className="px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3.5 py-1.5 rounded bg-[#4774A9] text-white font-semibold hover:bg-[#365F92]"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 3. Configure Transition Modal */}
      {isTransitionModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs select-none"
        >
          <div className="w-full max-w-lg bg-white rounded-lg border border-[#DCE3EB] shadow-2xl p-5 space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-[#DCE3EB] pb-2">
              <div className="font-bold text-sm text-[#25334B] flex items-center gap-2">
                <ArrowRightLeft className="w-4 h-4 text-[#249E91]" />
                <span>Configure Knowledge Handover Transition</span>
              </div>
              <button
                type="button"
                onClick={() => setIsTransitionModalOpen(false)}
                className="text-[#69778D] hover:text-[#25334B]"
              >
                ✕
              </button>
            </div>

            <div className="p-3 rounded bg-[#E8EEF5] border border-[#DCE3EB] text-[11px] text-[#25334B] flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 text-[#4774A9] shrink-0 mt-0.5" />
              <span>
                Designate the departing knowledge owner and incoming successor. The system will align reconstructed evidence and verification checklists between these individuals.
              </span>
            </div>

            <form onSubmit={handleSaveTransition} className="space-y-3.5">
              <div>
                <label className="block font-semibold text-[#25334B] mb-1">
                  Departing Knowledge Owner
                </label>
                <select
                  value={departingId}
                  onChange={(e) => setDepartingId(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded border border-[#DCE3EB] bg-white text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
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
                  Incoming Successor
                </label>
                <select
                  value={successorId}
                  onChange={(e) => setSuccessorId(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded border border-[#DCE3EB] bg-white text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
                >
                  {members.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({m.role})
                    </option>
                  ))}
                </select>
              </div>

              {departingId === successorId && (
                <div className="p-2.5 rounded bg-[#C65B60]/10 border border-[#C65B60]/30 text-[#C65B60] flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>The departing member and successor cannot be the same person.</span>
                </div>
              )}

              <div className="pt-2 border-t border-[#DCE3EB] flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsTransitionModalOpen(false)}
                  className="px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={departingId === successorId}
                  className="px-3.5 py-1.5 rounded bg-[#249E91] text-white font-semibold hover:bg-[#1f877c] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Save Transition Configuration
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
