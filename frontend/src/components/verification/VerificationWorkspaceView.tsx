"use client";

import React, { useState, useEffect } from "react";
import {
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  RefreshCw,
  Search,
  Filter,
  ShieldCheck,
  FileText,
  Database,
  ArrowRight,
  User,
  Clock,
  Sparkles,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import { Button } from "../ui";

export function VerificationWorkspaceView({
  initialTab = "queue",
}: {
  initialTab?: "queue" | "conflicts" | "history";
} = {}) {
  const { activeProject } = useLiveApp();
  const [activeTab, setActiveTab] = useState<"queue" | "conflicts" | "history">(initialTab);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [cases, setCases] = useState<Array<Record<string, unknown>>>([]);
  const [selectedCase, setSelectedCase] = useState<Record<string, unknown> | null>(null);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isActing, setIsActing] = useState(false);

  const loadVerificationData = async (projectId: string) => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem("auth_token");
      const headers = { Authorization: `Bearer ${token}` };

      // Load summary
      const sumRes = await fetch(
        `http://127.0.0.1:8000/api/v1/projects/${projectId}/verification/summary`,
        { headers }
      );
      if (sumRes.ok) {
        const sumData = await sumRes.json();
        setSummary(sumData);
      }

      // Load queue
      const qRes = await fetch(
        `http://127.0.0.1:8000/api/v1/projects/${projectId}/verification/queue`,
        { headers }
      );
      if (qRes.ok) {
        const qData = await qRes.json();
        const items = qData.items || [];
        setCases(items);
        if (items.length > 0 && !selectedCase) {
          setSelectedCase(items[0]);
        }
      }
    } catch (err) {
      console.error("Failed to load verification queue:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (activeProject) {
      loadVerificationData(activeProject.id);
    }
  }, [activeProject]);

  const handleApprove = async (caseId: string) => {
    if (!activeProject) return;
    setIsActing(true);
    try {
      const token = localStorage.getItem("auth_token");
      await fetch(
        `http://127.0.0.1:8000/api/v1/projects/${activeProject.id}/verification/cases/${caseId}/approve`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ review_notes: "Approved in Verification Center review" }),
        }
      );
      await loadVerificationData(activeProject.id);
    } catch (err) {
      console.error("Failed to approve case:", err);
    } finally {
      setIsActing(false);
    }
  };

  const handleReject = async (caseId: string) => {
    if (!activeProject) return;
    setIsActing(true);
    try {
      const token = localStorage.getItem("auth_token");
      await fetch(
        `http://127.0.0.1:8000/api/v1/projects/${activeProject.id}/verification/cases/${caseId}/reject`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ rejection_reason: "Rejected by reviewer" }),
        }
      );
      await loadVerificationData(activeProject.id);
    } catch (err) {
      console.error("Failed to reject case:", err);
    } finally {
      setIsActing(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-[#DCE3EB]">
        <CheckCircle2 className="w-12 h-12 text-[#69778D] mb-3 mx-auto" />
        <div className="font-bold text-sm text-[#25334B]">No Active Project Selected</div>
        <p className="text-xs text-[#69778D] mt-1">Select a project workspace to open the Verification Center.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-[#4774A9] uppercase tracking-wider">
            <span>Validation &amp; Governance</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#249E91]" />
            <span className="text-[#69778D] font-normal">{activeProject.name}</span>
          </div>
          <h1 className="text-xl font-bold text-[#25334B] mt-1 tracking-tight">
            Verification Center &amp; Conflict Resolution
          </h1>
          <p className="text-xs text-[#69778D] mt-0.5">
            Human-in-the-loop review queue for candidate findings, evidence validation, and contradiction adjudication.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="secondary"
            icon={RefreshCw}
            onClick={() => loadVerificationData(activeProject.id)}
            disabled={isLoading}
          >
            Refresh Queue
          </Button>
        </div>
      </div>

      {/* KPI Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="text-[11px] font-semibold text-[#69778D] uppercase tracking-wider">Pending Review</div>
          <div className="text-2xl font-bold text-[#D39B43] mt-1">
            {summary?.pending_review ?? 0}
          </div>
          <div className="text-[11px] text-[#69778D] mt-0.5">Awaiting human sign-off</div>
        </div>

        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="text-[11px] font-semibold text-[#69778D] uppercase tracking-wider">Verified Findings</div>
          <div className="text-2xl font-bold text-[#249E91] mt-1">
            {summary?.verified_count ?? 0}
          </div>
          <div className="text-[11px] text-[#249E91] mt-0.5">Approved for handover</div>
        </div>

        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="text-[11px] font-semibold text-[#69778D] uppercase tracking-wider">Active Conflicts</div>
          <div className="text-2xl font-bold text-[#D36D72] mt-1">
            {summary?.conflicts_count ?? 0}
          </div>
          <div className="text-[11px] text-[#69778D] mt-0.5">Contradictory facts</div>
        </div>

        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="text-[11px] font-semibold text-[#69778D] uppercase tracking-wider">Verification Rate</div>
          <div className="text-2xl font-bold text-[#4774A9] mt-1">
            {summary?.verification_rate ? `${Math.round(summary.verification_rate)}%` : "0%"}
          </div>
          <div className="text-[11px] text-[#69778D] mt-0.5">Queue completion</div>
        </div>
      </div>

      {/* Epistemic Guidance Banner */}
      <div className="p-4 rounded-xl bg-blue-50/60 border border-blue-200 flex items-start gap-3 text-xs text-blue-950">
        <ShieldCheck className="w-5 h-5 text-[#4774A9] shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-semibold">Four-Tier Epistemic Separation:</span> Every verified item distinguishes between <strong>Original Source Evidence</strong>, <strong>Extracted Information</strong>, <strong>AI Interpretation</strong>, and <strong>Human-Verified Truth</strong>. The LLM cannot independently approve records or override human decisions.
        </div>
      </div>

      {/* Main Split-Screen Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[550px]">
        {/* Left Column: Verification Queue */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-[#DCE3EB] mb-3">
            <div className="text-xs font-bold text-[#25334B] uppercase tracking-wider">
              Verification Queue ({cases.length})
            </div>
            <div className="flex gap-1 text-[11px]">
              <button
                onClick={() => setStatusFilter("all")}
                className={`px-2 py-0.5 rounded ${
                  statusFilter === "all" ? "bg-[#E8EEF5] text-[#4774A9] font-bold" : "text-[#69778D]"
                }`}
              >
                All
              </button>
              <button
                onClick={() => setStatusFilter("pending")}
                className={`px-2 py-0.5 rounded ${
                  statusFilter === "pending" ? "bg-[#E8EEF5] text-[#4774A9] font-bold" : "text-[#69778D]"
                }`}
              >
                Pending
              </button>
            </div>
          </div>

          {cases.length === 0 ? (
            <div className="p-8 text-center my-auto">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mb-2 mx-auto" />
              <div className="font-bold text-sm text-[#25334B]">Verification Queue Clear</div>
              <p className="text-xs text-[#69778D] mt-1 max-w-xs mx-auto">
                No items are currently awaiting human review. Reconstructed items from new evidence will appear here automatically.
              </p>
            </div>
          ) : (
            <div className="space-y-2 overflow-y-auto max-h-[500px] pr-1">
              {cases.map((c) => (
                <div
                  key={c.id}
                  onClick={() => setSelectedCase(c)}
                  className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                    selectedCase?.id === c.id
                      ? "border-[#4774A9] bg-[#F6F8FC] shadow-2xs"
                      : "border-[#DCE3EB] bg-white hover:border-[#7997BE]"
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] text-[#69778D] mb-1">
                    <span className="font-mono font-bold uppercase text-[#4774A9]">
                      {c.domain_id || "Knowledge Item"}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full font-semibold ${
                        c.status === "approved"
                          ? "bg-emerald-50 text-emerald-700"
                          : c.status === "rejected"
                          ? "bg-rose-50 text-rose-700"
                          : "bg-amber-50 text-amber-700"
                      }`}
                    >
                      {c.status}
                    </span>
                  </div>
                  <h4 className="font-bold text-[#25334B] line-clamp-1">{c.title}</h4>
                  <p className="text-[11px] text-[#69778D] mt-0.5 line-clamp-2 leading-relaxed">
                    {c.summary || c.extracted_fact}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Case Inspection Split Screen */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs flex flex-col justify-between">
          {selectedCase ? (
            <div className="space-y-5">
              {/* Case Header */}
              <div className="border-b border-[#DCE3EB] pb-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#E8EEF5] text-[#4774A9] uppercase font-mono">
                    Case #{selectedCase.id.slice(0, 8)}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-[#69778D]">Confidence:</span>
                    <span className="text-xs font-mono font-bold text-[#25334B]">
                      {selectedCase.confidence_score ? `${Math.round(selectedCase.confidence_score * 100)}%` : "N/A"}
                    </span>
                  </div>
                </div>
                <h3 className="text-base font-bold text-[#25334B] mt-2">{selectedCase.title}</h3>
              </div>

              {/* Four-Tier Comparison Cards */}
              <div className="space-y-3">
                <div className="p-3.5 rounded-xl border border-[#DCE3EB] bg-[#F4F6F9]/60">
                  <div className="text-[10px] font-bold text-[#4774A9] uppercase tracking-wider flex items-center gap-1.5 mb-1.5">
                    <Database className="w-3.5 h-3.5" />
                    <span>Original Supporting Evidence</span>
                  </div>
                  <p className="text-xs text-[#25334B] leading-relaxed font-mono">
                    {selectedCase.source_excerpt || "Evidence citation linked from canonical document store."}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl border border-[#DCE3EB] bg-white">
                  <div className="text-[10px] font-bold text-[#69778D] uppercase tracking-wider flex items-center gap-1.5 mb-1.5">
                    <FileText className="w-3.5 h-3.5" />
                    <span>Extracted Statement</span>
                  </div>
                  <p className="text-xs text-[#25334B] leading-relaxed">
                    {selectedCase.extracted_fact || selectedCase.summary}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl border border-purple-200 bg-purple-50/40">
                  <div className="text-[10px] font-bold text-purple-700 uppercase tracking-wider flex items-center gap-1.5 mb-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>AI Interpretation &amp; Rationale</span>
                  </div>
                  <p className="text-xs text-purple-950 leading-relaxed">
                    {selectedCase.ai_rationale || "Reconstructed by Qwen3 8B with source attribution."}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-4 border-t border-[#DCE3EB] flex items-center justify-end gap-3">
                <Button
                  variant="danger"
                  icon={XCircle}
                  onClick={() => handleReject(selectedCase.id)}
                  disabled={isActing}
                >
                  Reject Finding
                </Button>
                <Button
                  variant="primary"
                  icon={CheckCircle2}
                  onClick={() => handleApprove(selectedCase.id)}
                  disabled={isActing}
                >
                  Approve for Handover
                </Button>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center my-auto">
              <FileText className="w-12 h-12 text-[#69778D] mb-3 mx-auto" />
              <div className="font-bold text-sm text-[#25334B]">No Case Selected</div>
              <p className="text-xs text-[#69778D] mt-1">Select a finding from the left queue to inspect evidence and verify.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
