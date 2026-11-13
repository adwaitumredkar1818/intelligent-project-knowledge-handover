"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Settings,
  Workflow,
  Archive,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Save,
} from "lucide-react";
import {
  Card,
  CardHeader,
  Button,
  Field,
  Input,
  Textarea,
  Select,
  ConfirmDialog,
  Callout,
} from "../ui";
import { api } from "../../lib/api";
import type {
  Project,
  ProjectMember,
  ProjectTransition,
} from "../../lib/types";

export interface ProjectSettingsTabProps {
  project: Project;
  transition: ProjectTransition | null;
  canManage: boolean;
  onProjectUpdated: (updated: Project) => void;
}

export function ProjectSettingsTab({
  project,
  transition: initialTransition,
  canManage,
  onProjectUpdated,
}: ProjectSettingsTabProps) {
  const router = useRouter();

  // Project General Details State
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description || "");
  const [status, setStatus] = useState(project.status || "active");
  const [visibility, setVisibility] = useState<"private" | "organisation">(
    (project.visibility as "private" | "organisation") || "private"
  );
  const [targetDate, setTargetDate] = useState(
    project.target_completion_date ||
      (project.target_handover_date
        ? project.target_handover_date.split("T")[0]
        : "")
  );
  const [isSavingGeneral, setIsSavingGeneral] = useState(false);
  const [generalSuccess, setGeneralSuccess] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);

  // Transition Configuration State
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [departingUserId, setDepartingUserId] = useState<string>(
    initialTransition?.departing_user?.id || ""
  );
  const [successorUserId, setSuccessorUserId] = useState<string>(
    initialTransition?.successor_user?.id || ""
  );
  const [workflowStage, setWorkflowStage] = useState(
    initialTransition?.workflow_stage || "planning"
  );
  const [handoverScope, setHandoverScope] = useState(
    initialTransition?.handover_scope || ""
  );
  const [captureStart, setCaptureStart] = useState(
    initialTransition?.capture_start_date || ""
  );
  const [captureEnd, setCaptureEnd] = useState(
    initialTransition?.capture_end_date || ""
  );
  const [contextNotes, setContextNotes] = useState(
    initialTransition?.context_notes || ""
  );
  const [isSavingTransition, setIsSavingTransition] = useState(false);
  const [transitionSuccess, setTransitionSuccess] = useState(false);
  const [transitionError, setTransitionError] = useState<string | null>(null);

  // Archive Project State
  const [isArchiveConfirmOpen, setIsArchiveConfirmOpen] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);

  // Load project members for transition participant pickers
  useEffect(() => {
    let mounted = true;
    api.members
      .list(project.id)
      .then((m) => {
        if (!mounted) return;
        setMembers(m);
        setDepartingUserId((prev) => {
          if (prev) return prev;
          const departing = m.find((x) =>
            x.role_name.includes("departing") || x.role_name.includes("outgoing")
          );
          return departing ? departing.user_id : "";
        });
        setSuccessorUserId((prev) => {
          if (prev) return prev;
          const incoming = m.find((x) =>
            x.role_name.includes("incoming") || x.role_name.includes("successor")
          );
          return incoming ? incoming.user_id : "";
        });
      })
      .catch(() => {});

    return () => {
      mounted = false;
    };
  }, [project.id]);

  // Handle General Settings Update
  const handleSaveGeneral = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canManage) return;

    setIsSavingGeneral(true);
    setGeneralError(null);
    setGeneralSuccess(false);

    try {
      const updated = await api.projects.update(project.id, {
        name: name.trim(),
        description: description.trim() || undefined,
        status,
        visibility,
        target_completion_date: targetDate || undefined,
      });
      onProjectUpdated(updated);
      setGeneralSuccess(true);
      setTimeout(() => setGeneralSuccess(false), 3000);
    } catch (err: unknown) {
      setGeneralError(
        err instanceof Error ? err.message : "Failed to update project details"
      );
    } finally {
      setIsSavingGeneral(false);
    }
  };

  // Handle Transition Upsert
  const handleSaveTransition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canManage) return;

    if (!departingUserId || !successorUserId) {
      setTransitionError("Please select both a departing member and a successor.");
      return;
    }

    if (departingUserId === successorUserId) {
      setTransitionError(
        "Departing member and successor must be distinct users."
      );
      return;
    }

    setIsSavingTransition(true);
    setTransitionError(null);
    setTransitionSuccess(false);

    try {
      await api.projects.upsertTransition(project.id, {
        departing_user_id: departingUserId,
        successor_user_id: successorUserId,
        workflow_stage: workflowStage,
        handover_scope: handoverScope.trim() || undefined,
        capture_start_date: captureStart || undefined,
        capture_end_date: captureEnd || undefined,
        context_notes: contextNotes.trim() || undefined,
      });
      setTransitionSuccess(true);
      setTimeout(() => setTransitionSuccess(false), 3000);
    } catch (err: unknown) {
      setTransitionError(
        err instanceof Error
          ? err.message
          : "Failed to update handover transition configuration"
      );
    } finally {
      setIsSavingTransition(false);
    }
  };

  // Handle Archive
  const handleArchiveProject = async () => {
    if (!canManage) return;

    setIsArchiving(true);
    try {
      const archived = await api.projects.archive(project.id);
      setIsArchiveConfirmOpen(false);
      onProjectUpdated(archived);
      router.push("/projects");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to archive project");
    } finally {
      setIsArchiving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {!canManage && (
        <Callout tone="amber" icon={Lock} title="Settings Read-Only">
          You have read-only access to project settings. Only designated Project Managers can update workspace configuration or manage transition participants.
        </Callout>
      )}

      {/* 1. General Project Details Form Card */}
      <Card className="p-5 sm:p-6">
        <CardHeader
          title="General Project Settings"
          subtitle="Workspace identity, lifecycle status and visibility"
          icon={Settings}
        />

        <form onSubmit={handleSaveGeneral} className="mt-5 space-y-4">
          {generalError && (
            <Callout tone="red" title="Update failed">
              {generalError}
            </Callout>
          )}

          {generalSuccess && (
            <Callout tone="green" title="Changes saved" icon={CheckCircle2}>
              Project settings have been successfully updated.
            </Callout>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Project Name" required className="sm:col-span-2">
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={!canManage || isSavingGeneral}
              />
            </Field>

            <Field label="Workspace Slug (Read-Only)">
              <Input value={project.slug} disabled className="font-mono text-xs" />
            </Field>

            <Field label="Lifecycle Status">
              <Select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                disabled={!canManage || isSavingGeneral}
              >
                <option value="planning">Planning</option>
                <option value="active">Active</option>
                <option value="on_hold">On Hold</option>
                <option value="completed">Completed</option>
              </Select>
            </Field>

            <Field label="Visibility">
              <Select
                value={visibility}
                onChange={(e) =>
                  setVisibility(e.target.value as "private" | "organisation")
                }
                disabled={!canManage || isSavingGeneral}
              >
                <option value="private">Private (Project Members Only)</option>
                <option value="organisation">
                  Organisation (All Org Members)
                </option>
              </Select>
            </Field>

            <Field label="Target Handover / Completion Date">
              <Input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                disabled={!canManage || isSavingGeneral}
              />
            </Field>

            <Field
              label="Description & Scope"
              className="sm:col-span-2"
              hint="Provides boundary grounding for AI knowledge reconstruction."
            >
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={!canManage || isSavingGeneral}
                rows={3}
              />
            </Field>
          </div>

          {canManage && (
            <div className="flex justify-end pt-3 border-t border-line">
              <Button
                type="submit"
                variant="primary"
                icon={Save}
                disabled={isSavingGeneral}
              >
                {isSavingGeneral ? "Saving..." : "Save Project Settings"}
              </Button>
            </div>
          )}
        </form>
      </Card>

      {/* 2. Knowledge Transition Configuration Card */}
      <Card className="p-5 sm:p-6">
        <CardHeader
          title="Handover Transition Governance"
          subtitle="Configure departing owner, incoming successor, and capture parameters"
          icon={Workflow}
        />

        <form onSubmit={handleSaveTransition} className="mt-5 space-y-4">
          {transitionError && (
            <Callout tone="red" title="Transition configuration error">
              {transitionError}
            </Callout>
          )}

          {transitionSuccess && (
            <Callout tone="green" title="Transition configured" icon={CheckCircle2}>
              Handover participants and knowledge capture scope updated.
            </Callout>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Departing Knowledge Owner"
              required
              hint="The team member transitioning out of this role."
            >
              <Select
                value={departingUserId}
                onChange={(e) => setDepartingUserId(e.target.value)}
                disabled={!canManage || isSavingTransition}
              >
                <option value="">Select departing member...</option>
                {members.map((m) => (
                  <option key={m.user_id} value={m.user_id}>
                    {m.full_name || m.user_full_name} ({m.email || m.user_email})
                  </option>
                ))}
              </Select>
            </Field>

            <Field
              label="Incoming Successor / Assignee"
              required
              hint="The team member assuming knowledge ownership."
            >
              <Select
                value={successorUserId}
                onChange={(e) => setSuccessorUserId(e.target.value)}
                disabled={!canManage || isSavingTransition}
              >
                <option value="">Select incoming successor...</option>
                {members.map((m) => (
                  <option key={m.user_id} value={m.user_id}>
                    {m.full_name || m.user_full_name} ({m.email || m.user_email})
                  </option>
                ))}
              </Select>
            </Field>

            <Field label="Workflow Stage">
              <Select
                value={workflowStage}
                onChange={(e) => setWorkflowStage(e.target.value)}
                disabled={!canManage || isSavingTransition}
              >
                <option value="planning">Planning & Scoping</option>
                <option value="knowledge_capture">Knowledge Capture</option>
                <option value="verification">Human Verification</option>
                <option value="review">Review & Revisions</option>
                <option value="handover_ready">Ready for Sign-Off</option>
                <option value="completed">Completed & Acknowledged</option>
              </Select>
            </Field>

            <Field label="Capture Start Date">
              <Input
                type="date"
                value={captureStart}
                onChange={(e) => setCaptureStart(e.target.value)}
                disabled={!canManage || isSavingTransition}
              />
            </Field>

            <Field label="Capture End Date">
              <Input
                type="date"
                value={captureEnd}
                onChange={(e) => setCaptureEnd(e.target.value)}
                disabled={!canManage || isSavingTransition}
              />
            </Field>

            <Field
              label="Handover Scope & Boundaries"
              className="sm:col-span-2"
              hint="Define which systems, repositories, or operational procedures are included."
            >
              <Textarea
                value={handoverScope}
                onChange={(e) => setHandoverScope(e.target.value)}
                placeholder="e.g. Focus on deployment pipeline, AWS IAM credentials, and customer escalations."
                disabled={!canManage || isSavingTransition}
                rows={2}
              />
            </Field>

            <Field
              label="Context Notes"
              className="sm:col-span-2"
              hint="Private notes for reviewer and successor."
            >
              <Textarea
                value={contextNotes}
                onChange={(e) => setContextNotes(e.target.value)}
                placeholder="Any special operational constraints or background context."
                disabled={!canManage || isSavingTransition}
                rows={2}
              />
            </Field>
          </div>

          {canManage && (
            <div className="flex justify-end pt-3 border-t border-line">
              <Button
                type="submit"
                variant="primary"
                icon={Save}
                disabled={isSavingTransition}
              >
                {isSavingTransition
                  ? "Saving Configuration..."
                  : "Save Transition Configuration"}
              </Button>
            </div>
          )}
        </form>
      </Card>

      {/* 3. Danger Zone / Archive Project */}
      {canManage && (
        <Card className="p-5 sm:p-6 border-red-200 bg-red-50/10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold text-bad flex items-center gap-2">
                <AlertTriangle className="size-4" />
                <span>Archive Project Workspace</span>
              </h3>
              <p className="mt-1 text-xs text-muted max-w-xl leading-relaxed">
                Archiving marks this project as read-only. Members cannot connect new sources or trigger extractions, but existing verified handovers and audit records remain permanently accessible.
              </p>
            </div>

            <Button
              variant="danger"
              icon={Archive}
              onClick={() => setIsArchiveConfirmOpen(true)}
              disabled={project.status === "archived"}
            >
              {project.status === "archived" ? "Archived" : "Archive Project"}
            </Button>
          </div>
        </Card>
      )}

      {/* Archive Confirmation Dialog */}
      <ConfirmDialog
        open={isArchiveConfirmOpen}
        onClose={() => setIsArchiveConfirmOpen(false)}
        onConfirm={handleArchiveProject}
        title="Archive Project Workspace?"
        tone="danger"
        confirmLabel="Archive Project"
        isLoading={isArchiving}
        body={
          <div>
            <p>
              Are you sure you want to archive{" "}
              <strong className="text-navy">{project.name}</strong>?
            </p>
            <p className="mt-2 text-xs text-muted">
              This action disables future ingestion and locks the workspace. An audit record will be logged in PostgreSQL.
            </p>
          </div>
        }
      />
    </div>
  );
}
