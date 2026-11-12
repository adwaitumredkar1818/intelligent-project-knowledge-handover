"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  PlugZap,
  FileCheck2,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Clock,
  FileText,
  Sparkles,
  Info,
  ShieldAlert,
} from "lucide-react";
import { GithubIcon, JiraIcon, SlackIcon } from "../shared/BrandIcons";
import { usePrototype } from "../../context/PrototypeContext";
import {
  DEMO_KNOWLEDGE_CATEGORIES,
  DEMO_ATTENTION_ITEMS,
  DEMO_RECENT_ACTIVITY,
  DEMO_TEAM_OWNERSHIP,
  DEMO_PENDING_REVIEWS,
} from "../../data/demo-projects";
import type { WorkflowStage } from "../../types";

const STAGES: { key: WorkflowStage; label: string; number: number }[] = [
  { key: "connect", label: "Connect", number: 1 },
  { key: "reconstruct", label: "Reconstruct", number: 2 },
  { key: "verify", label: "Verify", number: 3 },
  { key: "review", label: "Review", number: 4 },
  { key: "handover", label: "Handover", number: 5 },
];

export function DashboardView() {
  const router = useRouter();
  const {
    selectedProject,
    setIsAddSourceModalOpen,
    addToast,
  } = usePrototype();

  const [isHandoverPreviewOpen, setIsHandoverPreviewOpen] = useState(false);

  const transition = selectedProject.transition;
  const currentStageIndex = STAGES.findIndex(
    (s) => s.key === transition.workflowStage
  );

  return (
    <div className="p-4 sm:p-6 space-y-5 max-w-7xl mx-auto">
      {/* 1. Project Header (Reference 2: Item 1-4) */}
      <div className="bg-white rounded-lg border border-[#DCE3EB] p-4 sm:p-5 shadow-2xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="text-xs font-semibold text-[#69778D] uppercase tracking-wider">
                {selectedProject.organisationName}
              </span>
              <span className="text-[#DCE3EB]">/</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-[#269878]/10 text-[#269878] border border-[#269878]/20 capitalize">
                {selectedProject.status}
              </span>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-[#E8EEF5] text-[#4774A9]">
                Private Workspace
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-[#25334B] tracking-tight mt-1">
              {selectedProject.name}
            </h1>
            <p className="text-xs text-[#69778D] mt-1 max-w-3xl leading-relaxed">
              {selectedProject.description}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2.5 shrink-0">
            <button
              type="button"
              onClick={() => setIsAddSourceModalOpen(true)}
              className="px-3 py-2 rounded-md border border-[#DCE3EB] bg-white hover:bg-[#F4F6F9] text-xs font-semibold text-[#25334B] flex items-center gap-2 transition-colors shadow-2xs"
            >
              <PlugZap className="w-3.5 h-3.5 text-[#4774A9]" />
              <span>Connect Sources</span>
            </button>
            <button
              type="button"
              onClick={() => setIsHandoverPreviewOpen(true)}
              className="px-3.5 py-2 rounded-md bg-[#4774A9] hover:bg-[#365F92] text-xs font-semibold text-white flex items-center gap-2 transition-colors shadow-xs"
              title="Preview Handover Compilation"
            >
              <FileCheck2 className="w-3.5 h-3.5 text-white" />
              <span>Generate Handover</span>
            </button>
          </div>
        </div>

        {/* 2. Project Transition Bar (Reference 2: Item 5-6) */}
        <div className="mt-5 pt-4 border-t border-[#DCE3EB] grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
          {/* Departing -> Successor info */}
          <div className="lg:col-span-5 flex items-center gap-3 bg-[#F4F6F9] p-3 rounded-md border border-[#DCE3EB]">
            <div className="flex-1 min-w-0">
              <div className="text-[10px] uppercase font-bold tracking-wider text-[#C48A32]">
                Departing Member
              </div>
              <div className="text-xs font-bold text-[#25334B] truncate">
                {transition.departingMember.name}
              </div>
              <div className="text-[11px] text-[#69778D] truncate">
                {transition.departingMember.role}
              </div>
            </div>

            <div className="flex items-center justify-center w-7 h-7 rounded-full bg-[#E8EEF5] text-[#4774A9] shrink-0 font-bold text-xs">
              →
            </div>

            <div className="flex-1 min-w-0">
              <div className="text-[10px] uppercase font-bold tracking-wider text-[#249E91]">
                Incoming Successor
              </div>
              <div className="text-xs font-bold text-[#25334B] truncate">
                {transition.successor.name}
              </div>
              <div className="text-[11px] text-[#69778D] truncate">
                {transition.successor.role}
              </div>
            </div>
          </div>

          {/* Workflow Stage Stepper */}
          <div className="lg:col-span-7 bg-[#F4F6F9] p-3 rounded-md border border-[#DCE3EB]">
            <div className="text-[10px] uppercase font-bold tracking-wider text-[#69778D] mb-2 flex items-center justify-between">
              <span>Knowledge Transfer Lifecycle</span>
              <span className="text-[#4774A9] font-mono text-[10px] font-semibold">
                STAGE 2: RECONSTRUCT
              </span>
            </div>
            <div className="flex items-center justify-between relative">
              {STAGES.map((s, idx) => {
                const isPassed = idx < currentStageIndex;
                const isCurrent = idx === currentStageIndex;
                return (
                  <div key={s.key} className="flex-1 flex flex-col items-center relative">
                    {/* Connecting line */}
                    {idx > 0 && (
                      <div
                        className={`absolute right-1/2 left-[-50%] top-2.5 -translate-y-1/2 h-0.5 z-0 ${
                          idx <= currentStageIndex ? "bg-[#4774A9]" : "bg-[#DCE3EB]"
                        }`}
                      />
                    )}
                    <div
                      className={`relative z-10 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all ${
                        isCurrent
                          ? "bg-[#249E91] text-white ring-3 ring-[#249E91]/25 scale-110 shadow-xs"
                          : isPassed
                          ? "bg-[#4774A9] text-white"
                          : "bg-white border border-[#DCE3EB] text-[#69778D]"
                      }`}
                    >
                      {isPassed ? "✓" : s.number}
                    </div>
                    <span
                      className={`text-[10px] mt-1 font-medium truncate ${
                        isCurrent
                          ? "text-[#249E91] font-bold"
                          : isPassed
                          ? "text-[#25334B]"
                          : "text-[#69778D]"
                      }`}
                    >
                      {s.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* 3. Dashboard Panels Grid (Reference 2: Items 7-12) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* PANEL A: Connected Sources (Reference 2: Item 7) */}
        <section className="bg-white rounded-lg border border-[#DCE3EB] shadow-2xs overflow-hidden flex flex-col">
          <div className="p-3.5 sm:p-4 border-b border-[#DCE3EB] flex items-center justify-between bg-[#F4F6F9]/50">
            <div className="flex items-center gap-2">
              <PlugZap className="w-4 h-4 text-[#4774A9]" />
              <h2 className="font-bold text-[#25334B] text-xs uppercase tracking-wider">
                Connected Sources
              </h2>
            </div>
            <button
              type="button"
              onClick={() => router.push("/prototype/evidence")}
              className="text-xs font-semibold text-[#4774A9] hover:underline flex items-center gap-1"
            >
              <span>View Evidence Center</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="p-4 space-y-3 flex-1 text-xs">
            {/* GitHub Row */}
            <div className="p-2.5 rounded-md border border-[#DCE3EB] bg-[#F4F6F9] flex items-center justify-between">
              <div className="flex items-center gap-2.5 min-w-0">
                <GithubIcon className="w-4 h-4 text-[#25334B] shrink-0" />
                <div className="min-w-0">
                  <div className="font-semibold text-[#25334B] truncate">
                    GitHub: nexora-backend, nexora-auth-service
                  </div>
                  <div className="text-[10px] text-[#69778D]">
                    70 records · Synced 12 mins ago
                  </div>
                </div>
              </div>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#269878]/10 text-[#269878] border border-[#269878]/20 shrink-0">
                Connected
              </span>
            </div>

            {/* Jira Row */}
            <div className="p-2.5 rounded-md border border-[#DCE3EB] bg-[#F4F6F9] flex items-center justify-between">
              <div className="flex items-center gap-2.5 min-w-0">
                <JiraIcon className="w-4 h-4 text-[#4774A9] shrink-0" />
                <div className="min-w-0">
                  <div className="font-semibold text-[#25334B] truncate">
                    Jira: Nexora Assist Board (NXA)
                  </div>
                  <div className="text-[10px] text-[#69778D]">
                    64 issues &amp; epics · Synced 28 mins ago
                  </div>
                </div>
              </div>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#269878]/10 text-[#269878] border border-[#269878]/20 shrink-0">
                Connected
              </span>
            </div>

            {/* Document Stores */}
            <div className="grid grid-cols-2 gap-2">
              <div className="p-2.5 rounded-md border border-[#DCE3EB] bg-[#F4F6F9] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[#C65B60]" />
                  <div>
                    <div className="font-bold text-[#25334B]">14 PDFs</div>
                    <div className="text-[10px] text-[#69778D]">ADRs &amp; Notes</div>
                  </div>
                </div>
                <span className="text-[10px] text-[#249E91] font-semibold">Extracted</span>
              </div>
              <div className="p-2.5 rounded-md border border-[#DCE3EB] bg-[#F4F6F9] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[#4774A9]" />
                  <div>
                    <div className="font-bold text-[#25334B]">8 DOCX</div>
                    <div className="text-[10px] text-[#69778D]">Runbooks</div>
                  </div>
                </div>
                <span className="text-[10px] text-[#249E91] font-semibold">Extracted</span>
              </div>
            </div>

            {/* Slack Row (Disabled) */}
            <div className="p-2.5 rounded-md border border-[#DCE3EB] bg-[#F4F6F9]/60 flex items-center justify-between opacity-75">
              <div className="flex items-center gap-2.5 min-w-0">
                <SlackIcon className="w-4 h-4 text-[#69778D] shrink-0" />
                <div className="min-w-0">
                  <div className="font-semibold text-[#69778D] truncate">
                    Slack (Workspace Channels)
                  </div>
                  <div className="text-[10px] text-[#69778D]">
                    Not enabled in this prototype
                  </div>
                </div>
              </div>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#DCE3EB] text-[#69778D] shrink-0">
                Disabled
              </span>
            </div>
          </div>
        </section>

        {/* PANEL B: Knowledge Overview (Reference 2: Item 8) */}
        <section className="bg-white rounded-lg border border-[#DCE3EB] shadow-2xs overflow-hidden flex flex-col">
          <div className="p-3.5 sm:p-4 border-b border-[#DCE3EB] flex items-center justify-between bg-[#F4F6F9]/50">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#249E91]" />
              <h2 className="font-bold text-[#25334B] text-xs uppercase tracking-wider">
                Knowledge Overview
              </h2>
            </div>
            <span className="text-[10px] font-mono bg-[#C48A32]/10 text-[#C48A32] px-1.5 py-0.5 rounded font-semibold uppercase">
              SAMPLE DATA
            </span>
          </div>

          <div className="p-4 space-y-3.5 flex-1 text-xs">
            {DEMO_KNOWLEDGE_CATEGORIES.map((cat) => (
              <div key={cat.id} className="space-y-1">
                <div className="flex items-center justify-between font-medium">
                  <span className="text-[#25334B] font-semibold">{cat.category}</span>
                  <span className="text-[#4774A9] font-mono font-bold">
                    {cat.count} items ({cat.progressPercent}%)
                  </span>
                </div>
                <div className="w-full bg-[#E8EEF5] h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-[#4774A9] h-full rounded-full transition-all duration-300"
                    style={{ width: `${cat.progressPercent}%` }}
                  />
                </div>
                <div className="text-[10px] text-[#69778D] truncate">
                  {cat.description}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* PANEL C: Pending Reviews (Reference 2: Item 9) */}
        <section className="bg-white rounded-lg border border-[#DCE3EB] shadow-2xs overflow-hidden flex flex-col">
          <div className="p-3.5 sm:p-4 border-b border-[#DCE3EB] flex items-center justify-between bg-[#F4F6F9]/50">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#4774A9]" />
              <h2 className="font-bold text-[#25334B] text-xs uppercase tracking-wider">
                Pending Verification Reviews
              </h2>
            </div>
            <span className="text-[10px] font-mono bg-[#E8EEF5] text-[#4774A9] px-1.5 py-0.5 rounded font-semibold uppercase">
              PREVIEW ONLY
            </span>
          </div>

          <div className="p-4 space-y-2.5 flex-1 text-xs">
            {DEMO_PENDING_REVIEWS.map((rev) => (
              <div
                key={rev.id}
                className="p-2.5 rounded-md border border-[#DCE3EB] bg-[#F4F6F9] hover:bg-white transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="font-semibold text-[#25334B]">{rev.title}</div>
                  <span className="text-[9px] bg-[#C48A32]/10 text-[#C48A32] font-semibold px-1.5 py-0.5 rounded shrink-0">
                    {rev.confidence} match
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-[#69778D] mt-1.5">
                  <span>Source: {rev.source}</span>
                  <span className="text-[#4774A9] font-medium">{rev.owner}</span>
                </div>
              </div>
            ))}

            <div className="pt-2 text-center">
              <span className="text-[11px] text-[#69778D] italic">
                Verification Center workflow is previewed in Phase 2
              </span>
            </div>
          </div>
        </section>

        {/* PANEL D: Attention Required (Reference 2: Item 10) */}
        <section className="bg-white rounded-lg border border-[#DCE3EB] shadow-2xs overflow-hidden flex flex-col">
          <div className="p-3.5 sm:p-4 border-b border-[#DCE3EB] flex items-center justify-between bg-[#F4F6F9]/50">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[#C48A32]" />
              <h2 className="font-bold text-[#25334B] text-xs uppercase tracking-wider">
                Attention Required
              </h2>
            </div>
            <span className="text-[10px] font-mono bg-[#C65B60]/10 text-[#C65B60] px-1.5 py-0.5 rounded font-semibold uppercase">
              4 WARNINGS
            </span>
          </div>

          <div className="p-4 space-y-2.5 flex-1 text-xs">
            {DEMO_ATTENTION_ITEMS.map((item) => (
              <div
                key={item.id}
                className={`p-2.5 rounded-md border transition-colors ${
                  item.severity === "high"
                    ? "border-[#C65B60]/30 bg-[#C65B60]/5"
                    : "border-[#DCE3EB] bg-[#F4F6F9]"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="font-semibold text-[#25334B] flex items-center gap-1.5">
                    {item.severity === "high" ? (
                      <ShieldAlert className="w-3.5 h-3.5 text-[#C65B60] shrink-0" />
                    ) : (
                      <AlertTriangle className="w-3.5 h-3.5 text-[#C48A32] shrink-0" />
                    )}
                    <span>{item.title}</span>
                  </div>
                  <span
                    className={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded shrink-0 ${
                      item.severity === "high"
                        ? "bg-[#C65B60]/15 text-[#C65B60]"
                        : "bg-[#C48A32]/15 text-[#C48A32]"
                    }`}
                  >
                    {item.type}
                  </span>
                </div>
                <p className="text-[11px] text-[#69778D] mt-1 leading-snug">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* PANEL E: Recent Project Activity (Reference 2: Item 11) */}
        <section className="bg-white rounded-lg border border-[#DCE3EB] shadow-2xs overflow-hidden flex flex-col">
          <div className="p-3.5 sm:p-4 border-b border-[#DCE3EB] flex items-center justify-between bg-[#F4F6F9]/50">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-[#4774A9]" />
              <h2 className="font-bold text-[#25334B] text-xs uppercase tracking-wider">
                Recent Project Activity
              </h2>
            </div>
            <span className="text-[10px] text-[#69778D]">Chronological</span>
          </div>

          <div className="p-4 space-y-3 flex-1 text-xs">
            {DEMO_RECENT_ACTIVITY.map((act) => (
              <div key={act.id} className="flex items-start gap-2.5">
                <div className="w-6 h-6 rounded-full bg-[#304563] text-white flex items-center justify-center font-bold text-[9px] shrink-0 mt-0.5">
                  {act.actor.avatarInitials}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[#25334B] leading-snug">
                    <span className="font-semibold">{act.actor.name}</span>{" "}
                    <span className="text-[#69778D]">{act.action}</span>{" "}
                    <span className="font-semibold text-[#4774A9]">{act.target}</span>
                  </div>
                  <div className="text-[10px] text-[#69778D] mt-0.5 font-mono">
                    {act.timestamp}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* PANEL F: Team Knowledge Ownership (Reference 2: Item 12) */}
        <section className="bg-white rounded-lg border border-[#DCE3EB] shadow-2xs overflow-hidden flex flex-col">
          <div className="p-3.5 sm:p-4 border-b border-[#DCE3EB] flex items-center justify-between bg-[#F4F6F9]/50">
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-[#249E91]" />
              <h2 className="font-bold text-[#25334B] text-xs uppercase tracking-wider">
                Team Knowledge Ownership
              </h2>
            </div>
            <button
              type="button"
              onClick={() => router.push("/prototype/team")}
              className="text-xs font-semibold text-[#4774A9] hover:underline flex items-center gap-1"
            >
              <span>Manage Team</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="p-4 space-y-3 flex-1 text-xs">
            {DEMO_TEAM_OWNERSHIP.map((own) => (
              <div
                key={own.memberId}
                className="p-2.5 rounded-md border border-[#DCE3EB] bg-[#F4F6F9] space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded-full bg-[#4774A9] text-white flex items-center justify-center font-bold text-[9px]">
                      {own.initials}
                    </div>
                    <span className="font-bold text-[#25334B]">{own.name}</span>
                    <span className="text-[10px] text-[#69778D]">({own.role})</span>
                  </div>
                  <span className="font-mono text-[11px] font-bold text-[#249E91]">
                    {own.ownershipPercent}%
                  </span>
                </div>
                <div className="w-full bg-[#E8EEF5] h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-[#249E91] h-full rounded-full"
                    style={{ width: `${own.ownershipPercent}%` }}
                  />
                </div>
                <div className="text-[10px] text-[#69778D] truncate">
                  Domain: {own.domain}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Handover Preview Modal */}
      {isHandoverPreviewOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Handover generation preview"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs select-none"
        >
          <div className="w-full max-w-md bg-white rounded-lg border border-[#DCE3EB] shadow-2xl p-5 space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-[#DCE3EB] pb-2">
              <div className="font-bold text-sm text-[#25334B] flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-[#4774A9]" />
                <span>Handover Generation Preview</span>
              </div>
              <button
                type="button"
                onClick={() => setIsHandoverPreviewOpen(false)}
                className="text-[#69778D] hover:text-[#25334B]"
              >
                ✕
              </button>
            </div>
            <div className="p-3 rounded bg-[#C48A32]/10 border border-[#C48A32]/30 text-[#C48A32] space-y-1">
              <div className="font-semibold">Future-stage workflow preview</div>
              <p className="text-[11px] leading-relaxed">
                Handover package compilation occurs in Module 6 after evidence reconstruction and human verification reviews. The AI never independently approves the final handover.
              </p>
            </div>
            <div className="space-y-2 text-[#25334B]">
              <div><strong>Departing Owner:</strong> {transition.departingMember.name}</div>
              <div><strong>Incoming Successor:</strong> {transition.successor.name}</div>
              <div><strong>Target Handover Date:</strong> {transition.targetHandoverDate}</div>
              <div><strong>Required Approvals:</strong> Designated Reviewer &amp; Project Lead</div>
            </div>
            <div className="pt-2 border-t border-[#DCE3EB] flex justify-end">
              <button
                type="button"
                onClick={() => {
                  setIsHandoverPreviewOpen(false);
                  addToast({
                    type: "info",
                    title: "Handover Notice",
                    message: "Handover Workspace is scheduled for Module 6.",
                  });
                }}
                className="px-3.5 py-1.5 rounded bg-[#4774A9] text-white font-semibold hover:bg-[#365F92]"
              >
                Understood
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
