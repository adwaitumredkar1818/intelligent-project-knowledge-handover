"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  Clock,
  ShieldAlert,
  FileText,
  UserCheck,
  Search,
  Filter,
  RefreshCw,
  ChevronRight,
  ExternalLink,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { api } from "../../lib/api";
import { useLiveApp } from "../../context/LiveAppContext";

interface VerificationQueueItem {
  id: string;
  target_type: string;
  target_id: string;
  status: string;
  risk_level: string;
  confidence_score: number;
  created_at: string;
  issue_count: number;
  assigned_to_user_id?: string;
  finding?: {
    title: string;
    summary: string;
    domain: string;
    category?: string;
  };
}

interface VerificationSummary {
  total_cases: number;
  pending_review: number;
  approved: number;
  rejected: number;
  unresolved: number;
  conflicts_count: number;
  stale_count: number;
  handover_eligible_count: number;
}

interface CaseDetail {
  id: string;
  project_id: string;
  target_type: string;
  target_id: string;
  status: string;
  risk_level: string;
  confidence_score: number;
  issues: Array<{
    id: string;
    issue_type: string;
    severity: string;
    description: string;
  }>;
  events: Array<{
    id: string;
    event_type: string;
    actor_user_id: string;
    created_at: string;
    payload: Record<string, unknown>;
  }>;
}

export function VerificationCenterWorkspace() {
  const { activeProject } = useLiveApp();
  const [summary, setSummary] = useState<VerificationSummary | null>(null);
  const [queue, setQueue] = useState<VerificationQueueItem[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseDetail | null>(null);
  const [caseEvidence, setCaseEvidence] = useState<Array<{ id: string; source_name: string; source_type: string; content_snippet: string }>>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [reviewNotes, setReviewNotes] = useState<string>("");

  const loadData = useCallback(async () => {
    if (!activeProject?.id) return;
    setLoading(true);
    try {
      const [sumRes, queueRes] = await Promise.all([
        api.verification.getSummary(activeProject.id).catch(() => ({
          total_cases: 0,
          pending_review: 0,
          approved: 0,
          rejected: 0,
          unresolved: 0,
          conflicts_count: 0,
          stale_count: 0,
          handover_eligible_count: 0,
        })),
        api.verification.getQueue(activeProject.id, statusFilter === "all" ? undefined : statusFilter).catch(() => ({
          items: [],
          total: 0,
        })),
      ]);
      setSummary(sumRes);
      setQueue(queueRes.items || []);
      if (queueRes.items && queueRes.items.length > 0 && !selectedCase && queueRes.items[0]) {
        loadCaseDetails(queueRes.items[0].id);
      }
    } finally {
      setLoading(false);
    }
  }, [activeProject?.id, statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const loadCaseDetails = async (caseId: string) => {
    if (!activeProject?.id) return;
    try {
      const [caseData, evidenceData] = await Promise.all([
        api.verification.getCaseDetail(activeProject.id, caseId),
        api.verification.getCaseEvidence(activeProject.id, caseId).catch(() => ({ evidence: [] })),
      ]);
      setSelectedCase(caseData);
      setCaseEvidence(evidenceData.evidence || []);
    } catch {
      // Graceful fallback
    }
  };

  const handleApprove = async () => {
    if (!activeProject?.id || !selectedCase) return;
    setActionLoading(true);
    try {
      await api.verification.approveCase(activeProject.id, selectedCase.id, reviewNotes || "Verified by human auditor");
      setReviewNotes("");
      await loadData();
      await loadCaseDetails(selectedCase.id);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!activeProject?.id || !selectedCase) return;
    setActionLoading(true);
    try {
      await api.verification.rejectCase(activeProject.id, selectedCase.id, reviewNotes || "Rejected due to insufficient evidence");
      setReviewNotes("");
      await loadData();
      await loadCaseDetails(selectedCase.id);
    } finally {
      setActionLoading(false);
    }
  };

  const handleMarkUnresolved = async () => {
    if (!activeProject?.id || !selectedCase) return;
    setActionLoading(true);
    try {
      await api.verification.markUnresolved(activeProject.id, selectedCase.id, reviewNotes || "Flagged for expert team clarification");
      setReviewNotes("");
      await loadData();
      await loadCaseDetails(selectedCase.id);
    } finally {
      setActionLoading(false);
    }
  };

  const filteredQueue = queue.filter((item) => {
    if (!searchTerm) return true;
    const title = item.finding?.title?.toLowerCase() || "";
    const summary = item.finding?.summary?.toLowerCase() || "";
    const term = searchTerm.toLowerCase();
    return title.includes(term) || summary.includes(term) || item.target_type.toLowerCase().includes(term);
  });

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Top Banner / Summary KPI Bar */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <CheckCircle2 className="w-7 h-7 text-emerald-400" />
            Verification Center
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Human-in-the-loop review queue for candidate findings, evidence validation, and epistemic truth classification.
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3">
            <div className="text-xs font-medium text-slate-400">Total Cases</div>
            <div className="text-xl font-bold text-white mt-1">{summary.total_cases}</div>
          </div>
          <div className="bg-amber-950/20 border border-amber-800/40 rounded-xl p-3">
            <div className="text-xs font-medium text-amber-400">Pending</div>
            <div className="text-xl font-bold text-amber-300 mt-1">{summary.pending_review}</div>
          </div>
          <div className="bg-emerald-950/20 border border-emerald-800/40 rounded-xl p-3">
            <div className="text-xs font-medium text-emerald-400">Approved</div>
            <div className="text-xl font-bold text-emerald-300 mt-1">{summary.approved}</div>
          </div>
          <div className="bg-rose-950/20 border border-rose-800/40 rounded-xl p-3">
            <div className="text-xs font-medium text-rose-400">Rejected</div>
            <div className="text-xl font-bold text-rose-300 mt-1">{summary.rejected}</div>
          </div>
          <div className="bg-purple-950/20 border border-purple-800/40 rounded-xl p-3">
            <div className="text-xs font-medium text-purple-400">Unresolved</div>
            <div className="text-xl font-bold text-purple-300 mt-1">{summary.unresolved}</div>
          </div>
          <div className="bg-rose-950/20 border border-rose-700/40 rounded-xl p-3">
            <div className="text-xs font-medium text-rose-300 flex items-center gap-1">
              <ShieldAlert className="w-3.5 h-3.5" /> Conflicts
            </div>
            <div className="text-xl font-bold text-rose-200 mt-1">{summary.conflicts_count}</div>
          </div>
          <div className="bg-blue-950/20 border border-blue-800/40 rounded-xl p-3">
            <div className="text-xs font-medium text-blue-400 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" /> Stale
            </div>
            <div className="text-xl font-bold text-blue-300 mt-1">{summary.stale_count}</div>
          </div>
          <div className="bg-teal-950/20 border border-teal-800/40 rounded-xl p-3">
            <div className="text-xs font-medium text-teal-400 flex items-center gap-1">
              <UserCheck className="w-3.5 h-3.5" /> Handover Ready
            </div>
            <div className="text-xl font-bold text-teal-300 mt-1">{summary.handover_eligible_count}</div>
          </div>
        </div>
      )}

      {/* Main 3-Panel Inspection Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-[500px]">
        {/* Panel A: Findings Awaiting Review (Queue) */}
        <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-xl flex flex-col overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <FileText className="w-4 h-4 text-emerald-400" />
                Review Queue ({filteredQueue.length})
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
                <input
                  type="text"
                  placeholder="Filter findings..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded-lg p-1 text-xs">
                <Filter className="w-3 h-3 text-slate-400 ml-1" />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-transparent text-slate-300 text-xs focus:outline-none pr-1"
                >
                  <option value="all">All</option>
                  <option value="pending">Pending</option>
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                  <option value="unresolved">Unresolved</option>
                </select>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60">
            {filteredQueue.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-sm">
                No verification cases found matching current filters.
              </div>
            ) : (
              filteredQueue.map((item) => {
                const isSelected = selectedCase?.id === item.id;
                return (
                  <div
                    key={item.id}
                    onClick={() => loadCaseDetails(item.id)}
                    className={`p-3.5 cursor-pointer transition-colors ${
                      isSelected ? "bg-slate-800/80 border-l-4 border-l-emerald-500" : "hover:bg-slate-800/40"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-medium text-xs text-slate-100 line-clamp-1">
                        {item.finding?.title || `Finding: ${item.target_id.slice(0, 8)}...`}
                      </div>
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                          item.status === "approved"
                            ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                            : item.status === "rejected"
                            ? "bg-rose-950 text-rose-400 border border-rose-800"
                            : item.status === "unresolved"
                            ? "bg-purple-950 text-purple-400 border border-purple-800"
                            : "bg-amber-950 text-amber-400 border border-amber-800"
                        }`}
                      >
                        {item.status.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 line-clamp-2 mt-1">
                      {item.finding?.summary || "Candidate project knowledge item requiring human verification."}
                    </p>
                    <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-500">
                      <span>Domain: {item.finding?.domain || "General"}</span>
                      <span>Confidence: {(item.confidence_score * 100).toFixed(0)}%</span>
                      {item.issue_count > 0 && (
                        <span className="text-rose-400 flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" /> {item.issue_count} issue(s)
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Panel B & C: Case Details, Supporting Evidence & Human Review Action Controls */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {selectedCase ? (
            <>
              {/* Panel B: Deep-dive Evidence & Issues */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs uppercase font-mono tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        Case #{selectedCase.id.slice(0, 8)}
                      </span>
                      <span
                        className={`text-xs font-semibold px-2 py-0.5 rounded ${
                          selectedCase.risk_level === "high"
                            ? "bg-rose-950 text-rose-400"
                            : selectedCase.risk_level === "medium"
                            ? "bg-amber-950 text-amber-400"
                            : "bg-blue-950 text-blue-400"
                        }`}
                      >
                        {selectedCase.risk_level.toUpperCase()} RISK
                      </span>
                    </div>
                    <h3 className="text-lg font-bold text-white mt-2">
                      Target Entity / Item: {selectedCase.target_type} ({selectedCase.target_id.slice(0, 8)}...)
                    </h3>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-slate-400">Confidence Score</div>
                    <div className="text-lg font-bold text-emerald-400">
                      {(selectedCase.confidence_score * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>

                {/* Issues List */}
                {selectedCase.issues && selectedCase.issues.length > 0 && (
                  <div className="bg-rose-950/20 border border-rose-900/50 rounded-lg p-3">
                    <h4 className="text-xs font-semibold text-rose-400 uppercase tracking-wider flex items-center gap-1.5 mb-2">
                      <AlertTriangle className="w-3.5 h-3.5" /> Detected Issues & Contradictions
                    </h4>
                    <div className="space-y-1.5">
                      {selectedCase.issues.map((issue) => (
                        <div key={issue.id} className="text-xs text-rose-200/90 flex items-start gap-2">
                          <span className="font-mono text-rose-400">[{issue.issue_type}]</span>
                          <span>{issue.description}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Supporting Source Evidence */}
                <div>
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5 mb-2">
                    <ExternalLink className="w-3.5 h-3.5 text-emerald-400" /> Supporting Grounding Evidence
                  </h4>
                  {caseEvidence.length === 0 ? (
                    <div className="text-xs text-slate-500 italic p-3 bg-slate-950 rounded border border-slate-800">
                      No supporting raw evidence chunks currently linked to this candidate.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {caseEvidence.map((ev) => (
                        <div key={ev.id} className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs">
                          <div className="flex items-center justify-between text-slate-400 font-mono text-[10px] mb-1">
                            <span>Source: {ev.source_name} ({ev.source_type})</span>
                            <span>ID: {ev.id.slice(0, 8)}</span>
                          </div>
                          <p className="text-slate-300 font-serif italic text-xs leading-relaxed">
                            &quot;{ev.content_snippet}&quot;
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Audit Event Log */}
                {selectedCase.events && selectedCase.events.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Verification Audit Trail
                    </h4>
                    <div className="space-y-1">
                      {selectedCase.events.map((evt) => (
                        <div key={evt.id} className="text-[11px] text-slate-400 flex items-center justify-between bg-slate-950 px-2 py-1 rounded">
                          <span>{evt.event_type}</span>
                          <span className="text-slate-500 font-mono">{new Date(evt.created_at).toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Panel C: Human Review Action Controls */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-2">
                  <UserCheck className="w-4 h-4 text-emerald-400" />
                  Human Auditor Decision
                </h3>

                <div>
                  <label className="text-xs font-medium text-slate-400 block mb-1">
                    Auditor Review Rationale / Correction Notes
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Enter explicit review notes or justification before taking action..."
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
                  <button
                    onClick={handleMarkUnresolved}
                    disabled={actionLoading}
                    className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-purple-950/60 hover:bg-purple-900/80 border border-purple-800 text-purple-200 transition-colors"
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                    Mark Unresolved
                  </button>
                  <button
                    onClick={handleReject}
                    disabled={actionLoading}
                    className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-rose-950/60 hover:bg-rose-900/80 border border-rose-800 text-rose-200 transition-colors"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    Reject Finding
                  </button>
                  <button
                    onClick={handleApprove}
                    disabled={actionLoading}
                    className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-950/50 transition-colors"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Verify & Approve for Handover
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-500 flex flex-col items-center justify-center h-full">
              <CheckCircle2 className="w-10 h-10 text-slate-700 mb-3" />
              <p className="text-sm font-medium text-slate-400">Select a case from the queue to review</p>
              <p className="text-xs text-slate-500 mt-1">
                Validate evidence citations, inspect detected conflicts, and record human verification.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
