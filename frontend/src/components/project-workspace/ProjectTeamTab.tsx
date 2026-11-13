"use client";

import React, { useState, useEffect } from "react";
import {
  Users,
  UserPlus,
  ShieldCheck,
  Mail,
  Lock,
  Check,
  Trash2,
  Loader2,
  AlertCircle,
} from "lucide-react";
import {
  Card,
  CardHeader,
  Button,
  Badge,
  Table,
  Th,
  Td,
  PersonCell,
  Select,
  Modal,
  Field,
  Textarea,
  ConfirmDialog,
  Callout,
} from "../ui";
import { useLiveApp } from "../../context/LiveAppContext";
import { api } from "../../lib/api";
import type {
  Project,
  ProjectMember,
  OrganisationMember,
} from "../../lib/types";

const ROLE_LABEL: Record<string, string> = {
  project_manager: "Project Manager",
  manager: "Project Manager",
  reviewer: "Reviewer",
  departing_owner: "Outgoing Member",
  outgoing: "Outgoing Member",
  incoming_assignee: "Incoming Member",
  incoming: "Incoming Member",
  project_member: "Member",
  contributor: "Member",
  viewer: "Viewer",
};

const PERMS_MATRIX: [string, boolean, boolean, boolean, boolean][] = [
  ["View verified knowledge", true, true, true, true],
  ["View evidence & sources", true, true, true, false],
  ["Verify / reject candidate findings", true, true, false, false],
  ["Add missing architectural context", true, true, false, false],
  ["Connect & configure sources", true, false, false, false],
  ["Create & approve handover packages", true, false, false, false],
  ["Publish auditable handovers", true, false, false, false],
  ["Acknowledge received handover", false, false, true, false],
];

export interface ProjectTeamTabProps {
  project: Project;
  canManage: boolean;
}

export function ProjectTeamTab({ project, canManage }: ProjectTeamTabProps) {
  const { user: currentUser, activeOrg } = useLiveApp();

  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [orgMembers, setOrgMembers] = useState<OrganisationMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Add Member Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [newMemberRole, setNewMemberRole] = useState("project_member");
  const [responsibility, setResponsibility] = useState("");
  const [isAddingMember, setIsAddingMember] = useState(false);

  // Remove Member Confirm Dialog State
  const [memberToRemove, setMemberToRemove] = useState<ProjectMember | null>(
    null
  );
  const [isRemovingMember, setIsRemovingMember] = useState(false);

  // Load project members and parent organisation members
  const refreshMembers = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [projMembers, oMembers] = await Promise.all([
        api.members.list(project.id),
        activeOrg?.id
          ? api.organisations.listMembers(activeOrg.id).catch(() => [])
          : Promise.resolve([]),
      ]);
      setMembers(projMembers);
      setOrgMembers(oMembers);
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to load team members"
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let mounted = true;
    Promise.all([
      api.members.list(project.id),
      activeOrg?.id
        ? api.organisations.listMembers(activeOrg.id).catch(() => [])
        : Promise.resolve([]),
    ])
      .then(([projMembers, oMembers]) => {
        if (!mounted) return;
        setMembers(projMembers);
        setOrgMembers(oMembers);
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        setErrorMessage(
          err instanceof Error ? err.message : "Failed to load team members"
        );
        setIsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [project.id, activeOrg?.id]);

  // Handle Inline Role Change (by Manager)
  const handleRoleChange = async (member: ProjectMember, newRole: string) => {
    try {
      const updated = await api.members.updateRole(project.id, member.user_id, {
        role_name: newRole,
      });
      setMembers((prev) =>
        prev.map((m) =>
          m.user_id === member.user_id ? { ...m, role_name: updated.role_name } : m
        )
      );
    } catch (err: unknown) {
      alert(
        err instanceof Error ? err.message : "Failed to update member role"
      );
    }
  };

  // Handle Add Member
  const handleAddMemberSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId) return;

    setIsAddingMember(true);
    try {
      await api.members.add(project.id, {
        user_id: selectedUserId,
        role_name: newMemberRole,
        responsibility_description: responsibility.trim() || undefined,
      });
      setIsAddModalOpen(false);
      setSelectedUserId("");
      setResponsibility("");
      await refreshMembers();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to add member");
    } finally {
      setIsAddingMember(false);
    }
  };

  // Handle Remove Member
  const handleConfirmRemove = async () => {
    if (!memberToRemove) return;

    setIsRemovingMember(true);
    try {
      await api.members.remove(project.id, memberToRemove.user_id);
      setMemberToRemove(null);
      await refreshMembers();
    } catch (err: unknown) {
      alert(
        err instanceof Error ? err.message : "Failed to remove project member"
      );
    } finally {
      setIsRemovingMember(false);
    }
  };

  // Eligible org members who are not yet added to this project
  const eligibleOrgMembers = orgMembers.filter(
    (om) => !members.some((pm) => pm.user_id === om.user_id)
  );

  return (
    <div className="space-y-6">
      {/* Top Banner if user is not manager */}
      {!canManage && (
        <Callout tone="amber" icon={Lock} title="View-Only Project Membership">
          You are viewing this project with member-level permissions. Only designated Project Managers can add or remove members or modify project-scoped roles.
        </Callout>
      )}

      {errorMessage && (
        <Callout tone="red" icon={AlertCircle} title="Error loading team">
          {errorMessage}
        </Callout>
      )}

      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        {/* Main Members Table Card */}
        <Card className="overflow-hidden">
          <CardHeader
            title="Project Members"
            subtitle={`${members.length} team members participating in this workspace`}
            icon={Users}
            action={
              canManage && (
                <Button
                  size="sm"
                  icon={UserPlus}
                  onClick={() => {
                    if (eligibleOrgMembers.length > 0 && eligibleOrgMembers[0]) {
                      setSelectedUserId(eligibleOrgMembers[0].user_id);
                    }
                    setIsAddModalOpen(true);
                  }}
                >
                  Add Member
                </Button>
              )
            }
          />

          {isLoading ? (
            <div className="flex items-center justify-center p-12 text-xs text-muted gap-2">
              <Loader2 className="size-4 animate-spin text-brand" />
              <span>Loading team members...</span>
            </div>
          ) : members.length === 0 ? (
            <div className="p-8 text-center text-xs text-muted">
              No members assigned to this project yet.
            </div>
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Member</Th>
                  <Th>Project Role</Th>
                  <Th>Responsibilities</Th>
                  <Th className="text-center">Assigned Tasks</Th>
                  {canManage && <Th className="w-12 text-right" />}
                </tr>
              </thead>
              <tbody>
                {members.map((m) => {
                  const isSelf = m.user_id === currentUser?.id;
                  const roleLabel =
                    ROLE_LABEL[m.role_name] ||
                    ROLE_LABEL[m.transition_role || ""] ||
                    m.role_name;

                  return (
                    <tr
                      key={m.id || m.user_id}
                      className="hover:bg-slate-50/60 transition-colors"
                    >
                      <Td>
                        <PersonCell
                          name={m.full_name || m.user_full_name || "Member"}
                          email={m.email || m.user_email || ""}
                          sub={isSelf ? "You" : undefined}
                        />
                      </Td>
                      <Td>
                        {canManage && !isSelf ? (
                          <Select
                            value={m.role_name}
                            onChange={(e) =>
                              handleRoleChange(m, e.target.value)
                            }
                            className="w-44 text-xs"
                          >
                            <option value="project_manager">Project Manager</option>
                            <option value="reviewer">Reviewer</option>
                            <option value="departing_owner">Outgoing Member</option>
                            <option value="incoming_assignee">Incoming Member</option>
                            <option value="project_member">Member</option>
                          </Select>
                        ) : (
                          <Badge
                            tone={
                              m.role_name.includes("manager")
                                ? "blue"
                                : m.role_name.includes("departing") ||
                                    m.role_name.includes("outgoing")
                                  ? "amber"
                                  : m.role_name.includes("incoming")
                                    ? "green"
                                    : "gray"
                            }
                          >
                            {roleLabel}
                          </Badge>
                        )}
                      </Td>
                      <Td>
                        {m.responsibility_description ? (
                          <span className="text-xs text-navy line-clamp-1 max-w-[200px]">
                            {m.responsibility_description}
                          </span>
                        ) : (
                          <span className="text-xs text-slate-400">
                            General handover participant
                          </span>
                        )}
                      </Td>
                      <Td className="text-center">
                        <span className="text-xs font-semibold text-navy font-mono">
                          0
                        </span>
                      </Td>
                      {canManage && (
                        <Td className="text-right">
                          {!isSelf && (
                            <button
                              type="button"
                              onClick={() => setMemberToRemove(m)}
                              className="p-1.5 rounded-lg text-slate-400 hover:text-bad hover:bg-red-50 transition-colors cursor-pointer"
                              title="Remove member"
                            >
                              <Trash2 className="size-4" />
                            </button>
                          )}
                        </Td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          )}
        </Card>

        {/* Right Column: Invitations & Permission Matrix */}
        <div className="space-y-6">
          {/* Pending Invitations Card */}
          <Card>
            <CardHeader
              title="Pending Invitations"
              subtitle="0 awaiting acceptance"
              icon={Mail}
            />
            <div className="p-5 text-center text-xs text-muted">
              <p>No pending invitations for this project.</p>
              <p className="text-[11px] text-slate-400 mt-1">
                Invited members receive secure access links via organisation email.
              </p>
            </div>
          </Card>

          {/* Permission Management Matrix Card */}
          <Card>
            <CardHeader
              title="Role Permissions Matrix"
              subtitle="Enforced access controls by role"
              icon={ShieldCheck}
            />
            <div className="overflow-x-auto px-5 pb-5">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-muted border-b border-line">
                    <th className="py-2 text-left font-semibold">Capability</th>
                    <th className="px-1 py-2 font-semibold text-center">PM</th>
                    <th className="px-1 py-2 font-semibold text-center">Out</th>
                    <th className="px-1 py-2 font-semibold text-center">In</th>
                    <th className="px-1 py-2 font-semibold text-center">Mem</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/60">
                  {PERMS_MATRIX.map(([label, pm, out, inc, mem]) => (
                    <tr key={label} className="hover:bg-slate-50/40">
                      <td className="py-2 pr-2 text-navy text-[11px]">
                        {label}
                      </td>
                      <td className="px-1 text-center">
                        {pm ? (
                          <Check className="mx-auto size-3.5 text-ok stroke-[2.5]" />
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="px-1 text-center">
                        {out ? (
                          <Check className="mx-auto size-3.5 text-ok stroke-[2.5]" />
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="px-1 text-center">
                        {inc ? (
                          <Check className="mx-auto size-3.5 text-ok stroke-[2.5]" />
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="px-1 text-center">
                        {mem ? (
                          <Check className="mx-auto size-3.5 text-ok stroke-[2.5]" />
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <p className="mt-3 flex items-start gap-1.5 text-[11px] text-muted leading-relaxed">
                <Lock className="mt-0.5 size-3 shrink-0 text-slate-400" />
                <span>
                  Permissions are strictly validated server-side. Project membership does not bypass source ACLs or allow unauthorized handover approvals.
                </span>
              </p>
            </div>
          </Card>
        </div>
      </div>

      {/* Add Member Modal */}
      <Modal
        open={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add Project Member"
        subtitle={`Assign a team member from ${activeOrg?.name || "your organisation"} to ${project.name}`}
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => setIsAddModalOpen(false)}
              disabled={isAddingMember}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleAddMemberSubmit}
              disabled={!selectedUserId || isAddingMember}
            >
              {isAddingMember ? "Adding..." : "Add to Project"}
            </Button>
          </>
        }
      >
        <form onSubmit={handleAddMemberSubmit} className="space-y-4">
          <Field
            label="Organisation Member"
            required
            hint="Select an active member from the parent organisation."
          >
            {eligibleOrgMembers.length > 0 ? (
              <Select
                value={selectedUserId}
                onChange={(e) => setSelectedUserId(e.target.value)}
              >
                {eligibleOrgMembers.map((om) => (
                  <option key={om.user_id} value={om.user_id}>
                    {om.full_name} ({om.email})
                  </option>
                ))}
              </Select>
            ) : (
              <div className="rounded-lg border border-line bg-slate-50 p-3 text-xs text-muted">
                All organisation members are already assigned to this project workspace.
              </div>
            )}
          </Field>

          <Field label="Project Role" required>
            <Select
              value={newMemberRole}
              onChange={(e) => setNewMemberRole(e.target.value)}
            >
              <option value="project_manager">Project Manager</option>
              <option value="reviewer">Reviewer</option>
              <option value="departing_owner">Outgoing Member</option>
              <option value="incoming_assignee">Incoming Member</option>
              <option value="project_member">Member / Contributor</option>
            </Select>
          </Field>

          <Field
            label="Responsibility / Handover Notes"
            hint="Optional context about their ownership domains."
          >
            <Textarea
              value={responsibility}
              onChange={(e) => setResponsibility(e.target.value)}
              placeholder="e.g. Lead for authentication microservices and Stripe webhooks."
              rows={2}
            />
          </Field>
        </form>
      </Modal>

      {/* Remove Member Confirmation Dialog */}
      <ConfirmDialog
        open={!!memberToRemove}
        onClose={() => setMemberToRemove(null)}
        onConfirm={handleConfirmRemove}
        title="Remove Member from Project?"
        tone="danger"
        confirmLabel="Remove Member"
        isLoading={isRemovingMember}
        body={
          memberToRemove && (
            <div>
              <p>
                Are you sure you want to remove{" "}
                <strong className="text-navy">
                  {memberToRemove.full_name || memberToRemove.user_full_name}
                </strong>{" "}
                from <strong className="text-navy">{project.name}</strong>?
              </p>
              <p className="mt-2 text-xs text-muted">
                They will lose access to this project&apos;s evidence and verification queues. Their previously reconstructed findings and audit history will remain intact.
              </p>
            </div>
          )
        }
      />
    </div>
  );
}
