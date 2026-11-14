"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Users,
  AlertCircle,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import {
  Button,
  Card,
  Field,
  Input,
  Textarea,
  Select,
  Checkbox,
  PersonCell,
  AvatarGroup,
  Callout,
  cn,
} from "../ui";
import { SourceIcon, type BrandSourceType } from "../brand/brand";
import { useLiveApp } from "../../context/LiveAppContext";
import { api } from "../../lib/api";
import type { Project, OrganisationMember } from "../../lib/types";

const CP_STEPS = ["Details", "Team", "Sources & Scope"];

const CATEGORIES = [
  "Backend platform",
  "Mobile application",
  "Data & analytics",
  "Design system",
  "Infrastructure & Cloud",
  "Research & AI",
  "Other",
];

const SOURCES_CATALOG: {
  type: BrandSourceType;
  label: string;
  description: string;
}[] = [
  {
    type: "github",
    label: "GitHub",
    description: "Code repositories, pull requests, issues, and commit history.",
  },
  {
    type: "jira",
    label: "Jira Software",
    description: "Epics, stories, bugs, sprint velocity, and ticket comments.",
  },
  {
    type: "slack",
    label: "Slack Channels",
    description: "Discussions, operational decisions, incident war rooms.",
  },
  {
    type: "docs",
    label: "Project Documents",
    description: "Architecture diagrams, RFCs, and uploaded PDFs/DOCX files.",
  },
  {
    type: "confluence",
    label: "Confluence",
    description: "Project wikis, meeting minutes, and architectural runbooks.",
  },
  {
    type: "gdrive",
    label: "Google Drive",
    description: "Shared team folders, research papers, and technical memos.",
  },
];

const ROLE_OPTIONS = [
  { value: "project_manager", label: "Project Manager" },
  { value: "reviewer", label: "Reviewer (Verification Lead)" },
  { value: "departing_owner", label: "Outgoing Member" },
  { value: "incoming_assignee", label: "Incoming Member" },
  { value: "project_member", label: "Contributor / Member" },
];

export interface ProjectCreationWizardProps {
  onSuccess?: (project: Project) => void;
  onCancel?: () => void;
  isModal?: boolean;
}

export function ProjectCreationWizard({
  onSuccess,
  onCancel,
  isModal = false,
}: ProjectCreationWizardProps) {
  const router = useRouter();
  const {
    activeOrg,
    organisations,
    createProject,
    setActiveProject,
    user: currentUser,
  } = useLiveApp();

  const [step, setStep] = useState(0);
  const [selectedOrgId, setSelectedOrgId] = useState<string>(() => activeOrg?.id || organisations[0]?.id || "");

  // Form State
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [visibility, setVisibility] = useState<"private" | "organisation">("private");
  const [ownerId, setOwnerId] = useState<string>(currentUser?.id || "");
  const [startDate, setStartDate] = useState(() => new Date().toISOString().split("T")[0] || "");
  const [targetDate, setTargetDate] = useState(() => {
    const d = new Date();
    d.setMonth(d.getMonth() + 3);
    return d.toISOString().split("T")[0] || "";
  });

  // Org members for team selection
  const [orgMembers, setOrgMembers] = useState<OrganisationMember[]>([]);
  const [isLoadingMembers, setIsLoadingMembers] = useState(true);
  const [selectedTeam, setSelectedTeam] = useState<
    { userId: string; role: string; name: string; email: string }[]
  >([]);

  // Selected sources
  const [selectedSources, setSelectedSources] = useState<BrandSourceType[]>([
    "github",
    "docs",
  ]);

  // Validation & Submission State
  const [touched, setTouched] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch organisation members when org changes
  useEffect(() => {
    const orgId = selectedOrgId || activeOrg?.id || organisations[0]?.id;
    if (!orgId) return;

    let mounted = true;
    api.organisations
      .listMembers(orgId)
      .then((members) => {
        if (!mounted) return;
        setOrgMembers(members);
        setIsLoadingMembers(false);
        // Pre-select current user as manager
        if (currentUser) {
          const self = members.find((m) => m.user_id === currentUser.id);
          setSelectedTeam((prev) => {
            if (prev.length > 0) return prev;
            return [
              {
                userId: currentUser.id,
                role: "project_manager",
                name: self?.full_name || currentUser.full_name || "You",
                email: self?.email || currentUser.email || "",
              },
            ];
          });
          setOwnerId(currentUser.id);
        }
      })
      .catch(() => {
        if (mounted) setIsLoadingMembers(false);
      });

    return () => {
      mounted = false;
    };
  }, [selectedOrgId, activeOrg?.id, organisations, currentUser]);

  // Validations
  const nameError = !name.trim()
    ? "Project name is required"
    : name.trim().length < 2
      ? "Project name must be at least 2 characters"
      : "";

  const dateError =
    startDate && targetDate && targetDate < startDate
      ? "Target completion date must not precede start date"
      : "";

  const handleNext = () => {
    setTouched(true);
    setErrorMessage(null);
    if (step === 0) {
      if (nameError || dateError) return;
      setStep(1);
    } else if (step === 1) {
      setStep(2);
    }
  };

  const handleBack = () => {
    setErrorMessage(null);
    if (step > 0) {
      setStep(step - 1);
    } else if (onCancel) {
      onCancel();
    } else {
      router.push("/projects");
    }
  };

  const handleCreate = async () => {
    setTouched(true);
    setErrorMessage(null);
    if (nameError || dateError) {
      setStep(0);
      return;
    }

    const orgId = selectedOrgId || activeOrg?.id;
    if (!orgId) {
      setErrorMessage("Please select or create an organisation first.");
      return;
    }

    setIsSubmitting(true);
    try {
      // 1. Create project
      const newProj = await createProject(
        {
          name: name.trim(),
          description: description.trim() || undefined,
          target_handover_date: targetDate
            ? new Date(targetDate).toISOString()
            : undefined,
        },
        { orgId }
      );

      // 2. Add extra team members if any
      const extraMembers = selectedTeam.filter(
        (m) => m.userId !== currentUser?.id
      );
      for (const m of extraMembers) {
        try {
          await api.members.add(newProj.id, {
            user_id: m.userId,
            role_name: m.role,
          });
        } catch {
          // Continue adding remaining members
        }
      }

      setActiveProject(newProj);
      if (onSuccess) {
        onSuccess(newProj);
      } else {
        router.push(`/projects/${newProj.id}`);
      }
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to create project workspace."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleMember = (m: OrganisationMember) => {
    const exists = selectedTeam.some((t) => t.userId === m.user_id);
    if (exists) {
      setSelectedTeam(selectedTeam.filter((t) => t.userId !== m.user_id));
    } else {
      setSelectedTeam([
        ...selectedTeam,
        {
          userId: m.user_id,
          role: "project_member",
          name: m.full_name,
          email: m.email,
        },
      ]);
    }
  };

  const updateMemberRole = (userId: string, role: string) => {
    setSelectedTeam(
      selectedTeam.map((t) => (t.userId === userId ? { ...t, role } : t))
    );
  };

  const toggleSource = (t: BrandSourceType) => {
    if (selectedSources.includes(t)) {
      setSelectedSources(selectedSources.filter((x) => x !== t));
    } else {
      setSelectedSources([...selectedSources, t]);
    }
  };

  const ownerName =
    orgMembers.find((m) => m.user_id === ownerId)?.full_name ||
    currentUser?.full_name ||
    "Owner";

  return (
    <div className={cn("w-full", !isModal && "max-w-6xl mx-auto py-2")}>
      {!isModal && (
        <button
          type="button"
          onClick={handleBack}
          className="mb-4 inline-flex items-center gap-1.5 text-[13px] font-medium text-muted hover:text-navy transition-colors"
        >
          <ArrowLeft className="size-4" />
          <span>Back to Projects</span>
        </button>
      )}

      <div className="mb-6">
        <h1 className="text-xl font-bold tracking-tight text-navy">
          Create Project Workspace
        </h1>
        <p className="mt-1 text-xs text-muted">
          Set up an isolated project space, connect authoritative sources, and configure your handover team.
        </p>
      </div>

      {errorMessage && (
        <div className="mb-5">
          <Callout tone="red" title="Error creating project" icon={AlertCircle}>
            {errorMessage}
          </Callout>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Main Wizard Form Card */}
        <Card className="p-5 sm:p-7">
          {/* Step Progress Bar */}
          <ol className="mb-7 flex items-center gap-3">
            {CP_STEPS.map((label, idx) => (
              <li key={label} className="flex flex-1 items-center gap-2.5">
                <span
                  className={cn(
                    "flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold transition-colors",
                    idx < step
                      ? "bg-ok text-white"
                      : idx === step
                        ? "bg-brand text-white shadow-xs"
                        : "bg-slate-100 text-slate-400"
                  )}
                >
                  {idx < step ? <Check className="size-3.5 stroke-[2.5]" /> : idx + 1}
                </span>
                <span
                  className={cn(
                    "text-xs font-medium truncate",
                    idx === step ? "text-navy font-semibold" : "text-muted"
                  )}
                >
                  {label}
                </span>
                {idx < CP_STEPS.length - 1 && (
                  <span className="h-px flex-1 bg-line" />
                )}
              </li>
            ))}
          </ol>

          {/* STAGE 1: Details */}
          {step === 0 && (
            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <Field
                  label="Organisation Workspace"
                  className="sm:col-span-2"
                  hint="The parent organisation governing this project."
                >
                  <Select
                    value={selectedOrgId}
                    onChange={(e) => setSelectedOrgId(e.target.value)}
                    disabled={organisations.length <= 1}
                  >
                    {organisations.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.name}
                      </option>
                    ))}
                  </Select>
                </Field>

                <Field
                  label="Project Name"
                  required
                  className="sm:col-span-2"
                  error={touched ? nameError : undefined}
                >
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Billing Infrastructure Modernisation"
                    invalid={touched && !!nameError}
                    autoFocus
                  />
                </Field>

                <Field
                  label="Description"
                  className="sm:col-span-2"
                  hint="Helps the Qwen3 8B model scope knowledge reconstruction and boundary detection."
                >
                  <Textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="What does this project encompass, which systems depend on it, and what are the critical risks?"
                    rows={3}
                  />
                </Field>

                <Field label="Category / Domain">
                  <Input
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    placeholder="e.g. Backend platform, Mobile, Infrastructure"
                  />
                </Field>

                <Field label="Visibility">
                  <Select
                    value={visibility}
                    onChange={(e) =>
                      setVisibility(e.target.value as "private" | "organisation")
                    }
                  >
                    <option value="private">Private (Project Members Only)</option>
                    <option value="organisation">Organisation (All Org Members)</option>
                  </Select>
                </Field>

                <Field label="Project Owner">
                  <Select
                    value={ownerId}
                    onChange={(e) => setOwnerId(e.target.value)}
                  >
                    {orgMembers.length > 0 ? (
                      orgMembers.map((m) => (
                        <option key={m.user_id} value={m.user_id}>
                          {m.full_name} ({m.email})
                        </option>
                      ))
                    ) : (
                      <option value={currentUser?.id || ""}>
                        {currentUser?.full_name || "Current User"}
                      </option>
                    )}
                  </Select>
                </Field>

                <Field label="Start Date">
                  <Input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </Field>

                <Field
                  label="Target Completion Date"
                  error={touched ? dateError : undefined}
                >
                  <Input
                    type="date"
                    value={targetDate}
                    onChange={(e) => setTargetDate(e.target.value)}
                    invalid={touched && !!dateError}
                  />
                </Field>
              </div>
            </div>
          )}

          {/* STAGE 2: Team */}
          {step === 1 && (
            <div>
              <p className="mb-4 text-xs text-muted leading-relaxed">
                Select members from your organisation to add to this project and designate their initial project role. You can modify assignments and assign specific handover responsibilities at any time.
              </p>

              {isLoadingMembers ? (
                <div className="flex items-center justify-center p-8 text-xs text-muted gap-2">
                  <Loader2 className="size-4 animate-spin text-brand" />
                  <span>Loading organisation members...</span>
                </div>
              ) : orgMembers.length === 0 ? (
                <div className="rounded-xl border border-line bg-slate-50/50 p-6 text-center">
                  <Users className="mx-auto size-8 text-slate-300 mb-2" />
                  <p className="text-xs font-medium text-navy">
                    No other organisation members found
                  </p>
                  <p className="text-[11px] text-muted mt-1">
                    You will be assigned as the primary Project Manager. You can invite additional team members later.
                  </p>
                </div>
              ) : (
                <ul className="divide-y divide-line rounded-xl border border-line overflow-hidden max-h-[340px] overflow-y-auto">
                  {orgMembers.map((m) => {
                    const sel = selectedTeam.find((t) => t.userId === m.user_id);
                    const isSelf = m.user_id === currentUser?.id;
                    return (
                      <li
                        key={m.user_id}
                        className={cn(
                          "flex flex-wrap items-center gap-3 px-4 py-3 transition-colors",
                          sel ? "bg-tint/20" : "hover:bg-slate-50/50"
                        )}
                      >
                        <Checkbox
                          checked={!!sel}
                          onChange={() => !isSelf && toggleMember(m)}
                        />
                        <div className="min-w-[180px] flex-1">
                          <PersonCell
                            name={m.full_name}
                            email={m.email}
                            sub={isSelf ? "You (Owner)" : m.role_name}
                          />
                        </div>
                        {sel && (
                          <Select
                            value={sel.role}
                            onChange={(e) =>
                              updateMemberRole(m.user_id, e.target.value)
                            }
                            className="w-48 text-xs"
                          >
                            {ROLE_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </Select>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          )}

          {/* STAGE 3: Sources & Scope */}
          {step === 2 && (
            <div>
              <p className="mb-4 text-xs text-muted leading-relaxed">
                Select authoritative source providers to connect to this project workspace. Handover isolates each project into a dedicated vector collection in ChromaDB.
              </p>

              <div className="grid gap-3 sm:grid-cols-2">
                {SOURCES_CATALOG.map((source) => {
                  const isSelected = selectedSources.includes(source.type);
                  return (
                    <button
                      key={source.type}
                      type="button"
                      onClick={() => toggleSource(source.type)}
                      className={cn(
                        "flex items-start gap-3 rounded-xl border p-3.5 text-left transition-all cursor-pointer",
                        isSelected
                          ? "border-brand bg-tint/30 ring-2 ring-brand/15"
                          : "border-line bg-white hover:border-slate-300 hover:bg-slate-50/30"
                      )}
                    >
                      <SourceIcon type={source.type} size={32} />
                      <div className="flex-1 min-w-0">
                        <span className="block text-xs font-semibold text-navy">
                          {source.label}
                        </span>
                        <span className="block text-[11px] text-muted leading-relaxed mt-0.5">
                          {source.description}
                        </span>
                      </div>
                      <span
                        className={cn(
                          "flex size-5 shrink-0 items-center justify-center rounded-full border transition-colors mt-0.5",
                          isSelected
                            ? "border-brand bg-brand text-white"
                            : "border-slate-300 bg-white"
                        )}
                      >
                        {isSelected && <Check className="size-3 stroke-[2.5]" />}
                      </span>
                    </button>
                  );
                })}
              </div>

              <div className="mt-5">
                <Callout
                  tone="blue"
                  icon={ShieldCheck}
                  title="Zero-Fabrication & Strict Access Control"
                >
                  Handover strictly enforces source ACLs. Project membership does not grant automatic access to private GitHub repositories or restricted Jira issues connected by another user.
                </Callout>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="mt-8 flex justify-between border-t border-line pt-5">
            <Button
              variant="ghost"
              icon={ArrowLeft}
              onClick={handleBack}
              disabled={isSubmitting}
            >
              {step > 0 ? "Back" : "Cancel"}
            </Button>

            {step < CP_STEPS.length - 1 ? (
              <Button iconRight={ArrowRight} onClick={handleNext}>
                Continue
              </Button>
            ) : (
              <Button
                variant="primary"
                icon={CheckCircle2}
                onClick={handleCreate}
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="size-3.5 animate-spin" />
                    <span>Creating project...</span>
                  </span>
                ) : (
                  "Create Project Workspace"
                )}
              </Button>
            )}
          </div>
        </Card>

        {/* Real-Time Sticky Summary Card */}
        <Card className="h-fit p-5 lg:sticky lg:top-4 border-line">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Project Summary
          </p>
          <div className="mt-3 flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand text-xs font-bold text-white shadow-xs">
              {name.trim() ? name.slice(0, 3).toUpperCase() : "PRJ"}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-navy truncate">
                {name.trim() || "Untitled Project"}
              </p>
              <p className="text-[11px] text-muted">{category}</p>
            </div>
          </div>

          <dl className="mt-5 space-y-3 border-t border-line pt-4 text-xs">
            <div className="flex justify-between items-center">
              <dt className="text-muted">Owner</dt>
              <dd className="font-medium text-navy truncate max-w-[160px]">
                {ownerName}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-muted">Visibility</dt>
              <dd className="capitalize font-medium text-navy">{visibility}</dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-muted">Timeline</dt>
              <dd className="font-medium text-navy font-mono text-[11px]">
                {startDate} → {targetDate}
              </dd>
            </div>
            <div className="flex justify-between items-center pt-1">
              <dt className="text-muted">Members ({selectedTeam.length})</dt>
              <dd>
                <AvatarGroup
                  names={selectedTeam.map((t) => t.name)}
                  size={22}
                  max={4}
                />
              </dd>
            </div>
            <div className="flex justify-between items-center pt-1">
              <dt className="text-muted">Sources ({selectedSources.length})</dt>
              <dd className="flex items-center gap-1">
                {selectedSources.map((t) => (
                  <SourceIcon key={t} type={t} size={20} />
                ))}
              </dd>
            </div>
          </dl>
        </Card>
      </div>
    </div>
  );
}
