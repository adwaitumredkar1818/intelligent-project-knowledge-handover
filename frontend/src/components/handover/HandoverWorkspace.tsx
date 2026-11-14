"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  FileCheck2,
  Package,
  Layers,
  CheckSquare,
  Users,
  PenTool,
  Download,
  Plus,
  RefreshCw,
  ChevronRight,
  ShieldCheck,
  AlertCircle,
  FileCode,
  FileText,
} from "lucide-react";
import { api } from "../../lib/api";
import { useLiveApp } from "../../context/LiveAppContext";

interface HandoverCaseItem {
  id: string;
  project_id: string;
  title: string;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
  outgoing_owner_user_id?: string;
  incoming_owner_user_id?: string;
}

interface PackageVersion {
  id: string;
  version_number: number;
  package_hash: string;
  assembled_at: string;
  readiness_score?: number;
}

interface ChecklistItem {
  id: string;
  title: string;
  is_mandatory: boolean;
  status: string;
}

interface SignoffItem {
  id: string;
  role: string;
  user_id: string;
  signed_at?: string;
  status: string;
}

export function HandoverWorkspace() {
  const { activeProject } = useLiveApp();
  const [cases, setCases] = useState<HandoverCaseItem[]>([]);
  const [selectedCase, setSelectedCase] = useState<HandoverCaseItem | null>(null);
  const [versions, setVersions] = useState<PackageVersion[]>([]);
  const [checklists, setChecklists] = useState<ChecklistItem[]>([]);
  const [signoffs, setSignoffs] = useState<SignoffItem[]>([]);
  const [readiness, setReadiness] = useState<{
    readiness_score: number;
    dimension_scores: Record<string, number>;
    unmet_requirements: string[];
    recommendations: string[];
  } | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [newCaseTitle, setNewCaseTitle] = useState<string>("");
  const [isCreatingCase, setIsCreatingCase] = useState<boolean>(false);
  const [exportPreview, setExportPreview] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!activeProject?.id) return;
    setLoading(true);
    try {
      const res = await api.handover.listCases(activeProject.id).catch(() => ({ items: [], total: 0 }));
      setCases(res.items || []);
      if (res.items && res.items.length > 0 && !selectedCase && res.items[0]) {
        selectCase(res.items[0]);
      }
    } finally {
      setLoading(false);
    }
  }, [activeProject?.id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const selectCase = async (c: HandoverCaseItem) => {
    setSelectedCase(c);
    setExportPreview(null);
    if (!activeProject?.id) return;
    try {
      const [versRes, checkRes, signRes] = await Promise.all([
        api.handover.getVersions(activeProject.id, c.id).catch(() => []),
        api.handover.getChecklists(activeProject.id, c.id).catch(() => []),
        api.handover.getSignoffs(activeProject.id, c.id).catch(() => []),
      ]);
      setVersions(versRes);
      setChecklists(checkRes);
      setSignoffs(signRes);

      if (versRes.length > 0 && versRes[0]) {
        const readRes = await api.handover.getReadiness(activeProject.id, c.id, versRes[0].id).catch(() => null);
        setReadiness(readRes);
      } else {
        setReadiness(null);
      }
    } catch {
      // Graceful fallback
    }
  };

  const handleCreateCase = async () => {
    if (!activeProject?.id || !newCaseTitle.trim()) return;
    setActionLoading(true);
    try {
      const created = await api.handover.createCase(activeProject.id, {
        title: newCaseTitle.trim(),
      });
      setNewCaseTitle("");
      setIsCreatingCase(false);
      await loadData();
      if (created?.id) {
        const fullCase = await api.handover.getCase(activeProject.id, created.id);
        selectCase(fullCase);
      }
    } finally {
      setActionLoading(false);
    }
  };

  const handleAssemblePackage = async () => {
    if (!activeProject?.id || !selectedCase) return;
    setActionLoading(true);
    try {
      await api.handover.assemblePackage(activeProject.id, selectedCase.id, selectedCase.version);
      await selectCase(selectedCase);
      await loadData();
    } finally {
      setActionLoading(false);
    }
  };

  const handleExportMarkdown = async () => {
    if (!activeProject?.id || !selectedCase) return;
    try {
      const md = await api.handover.exportMarkdown(activeProject.id, selectedCase.id);
      setExportPreview(typeof md === "string" ? md : JSON.stringify(md, null, 2));
    } catch {
      setExportPreview("# Handover Export Error\nUnable to fetch markdown export.");
    }
  };

  const handleSignoff = async (signoffId: string, role: string) => {
    if (!activeProject?.id || !selectedCase) return;
    setActionLoading(true);
    try {
      await api.handover.recordSignoff(activeProject.id, selectedCase.id, {
        signoff_id: signoffId,
        role,
        notes: "Approved via Handover Workspace",
      });
      await selectCase(selectedCase);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Top Bar */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <FileCheck2 className="w-7 h-7 text-teal-400" />
            Handover Workspace
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Reconstruct, audit, compile, and execute structured, evidence-backed project handover packages.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsCreatingCase(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-teal-600 hover:bg-teal-500 text-white transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            New Handover Case
          </button>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* New Case Modal / Drawer */}
      {isCreatingCase && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center gap-3">
          <input
            type="text"
            placeholder="Handover Title (e.g. Lead Engineer Transition to Successor)"
            value={newCaseTitle}
            onChange={(e) => setNewCaseTitle(e.target.value)}
            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
          />
          <button
            onClick={handleCreateCase}
            disabled={actionLoading || !newCaseTitle.trim()}
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-teal-600 hover:bg-teal-500 text-white transition-colors"
          >
            Create Case
          </button>
          <button
            onClick={() => setIsCreatingCase(false)}
            className="px-3 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 transition-colors"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-[500px]">
        {/* Left Column: Handover Cases List */}
        <div className="lg:col-span-4 bg-slate-900 border border-slate-800 rounded-xl flex flex-col overflow-hidden">
          <div className="p-4 border-b border-slate-800">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Package className="w-4 h-4 text-teal-400" />
              Handover Cases ({cases.length})
            </h2>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60">
            {cases.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs">
                No handover cases created yet. Click &quot;New Handover Case&quot; to begin.
              </div>
            ) : (
              cases.map((c) => {
                const isSelected = selectedCase?.id === c.id;
                return (
                  <div
                    key={c.id}
                    onClick={() => selectCase(c)}
                    className={`p-3.5 cursor-pointer transition-colors ${
                      isSelected ? "bg-slate-800/80 border-l-4 border-l-teal-500" : "hover:bg-slate-800/40"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-semibold text-xs text-white line-clamp-1">{c.title}</div>
                      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-teal-950 text-teal-400 border border-teal-800">
                        {c.status}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2">
                      <span>Version: v{c.version}</span>
                      <span>{new Date(c.updated_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Case Deep-Dive, Assembly & Sign-off */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {selectedCase ? (
            <>
              {/* Header Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      Case #{selectedCase.id.slice(0, 8)}
                    </span>
                    <span className="text-xs uppercase font-bold px-2 py-0.5 rounded bg-teal-950 text-teal-300">
                      STATUS: {selectedCase.status}
                    </span>
                  </div>
                  <h2 className="text-xl font-bold text-white mt-2">{selectedCase.title}</h2>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleAssemblePackage}
                    disabled={actionLoading}
                    className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-teal-600 hover:bg-teal-500 text-white shadow transition-colors"
                  >
                    <Layers className="w-3.5 h-3.5" />
                    Assemble Package (v{selectedCase.version})
                  </button>
                  <button
                    onClick={handleExportMarkdown}
                    className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Export
                  </button>
                </div>
              </div>

              {/* Readiness Assessment KPI Bar */}
              {readiness && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-teal-400" />
                      Handover Readiness Score
                    </h3>
                    <div className="text-lg font-bold text-teal-400">{readiness.readiness_score}/100</div>
                  </div>
                  <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden mb-3">
                    <div
                      className="bg-teal-500 h-full transition-all duration-500"
                      style={{ width: `${readiness.readiness_score}%` }}
                    />
                  </div>
                  {readiness.recommendations && readiness.recommendations.length > 0 && (
                    <div className="text-xs text-slate-400 bg-slate-950 p-2.5 rounded border border-slate-800/80">
                      <span className="font-semibold text-slate-300">Recommendation:</span>{" "}
                      {readiness.recommendations[0]}
                    </div>
                  )}
                </div>
              )}

              {/* Assembled Package Versions & Checklists */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Assembled Versions */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 mb-3">
                    <Layers className="w-3.5 h-3.5 text-teal-400" /> Assembled Package Versions ({versions.length})
                  </h3>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {versions.length === 0 ? (
                      <div className="text-xs text-slate-500 italic">No package versions assembled yet.</div>
                    ) : (
                      versions.map((v) => (
                        <div key={v.id} className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs flex items-center justify-between">
                          <div>
                            <div className="font-semibold text-white">Version v{v.version_number}</div>
                            <div className="font-mono text-[10px] text-slate-500 truncate w-40">
                              Hash: {v.package_hash.slice(0, 16)}...
                            </div>
                          </div>
                          <span className="text-[10px] text-teal-400 bg-teal-950 px-2 py-0.5 rounded border border-teal-800">
                            Readiness: {v.readiness_score ?? "N/A"}%
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Transition Checklists */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 mb-3">
                    <CheckSquare className="w-3.5 h-3.5 text-teal-400" /> Mandatory Checklists ({checklists.length})
                  </h3>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {checklists.length === 0 ? (
                      <div className="text-xs text-slate-500 italic">No checklist items defined for this case.</div>
                    ) : (
                      checklists.map((ch) => (
                        <div key={ch.id} className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs flex items-center justify-between">
                          <span className="text-slate-200 line-clamp-1">{ch.title}</span>
                          <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                            {ch.status}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Sign-offs & Approvals */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 mb-3">
                  <PenTool className="w-3.5 h-3.5 text-teal-400" /> Role-Based Sign-offs & Acknowledgements
                </h3>
                <div className="space-y-2">
                  {signoffs.length === 0 ? (
                    <div className="text-xs text-slate-500 italic">No sign-off stakeholders assigned.</div>
                  ) : (
                    signoffs.map((s) => (
                      <div key={s.id} className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs flex items-center justify-between">
                        <div>
                          <div className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">{s.role}</div>
                          <div className="text-[10px] text-slate-500 font-mono">
                            User: {s.user_id.slice(0, 8)}... {s.signed_at && `• Signed: ${new Date(s.signed_at).toLocaleDateString()}`}
                          </div>
                        </div>
                        {s.signed_at ? (
                          <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-950 px-2 py-1 rounded border border-emerald-800">
                            SIGNED
                          </span>
                        ) : (
                          <button
                            onClick={() => handleSignoff(s.id, s.role)}
                            disabled={actionLoading}
                            className="px-3 py-1 text-xs font-semibold rounded bg-teal-600 hover:bg-teal-500 text-white transition-colors"
                          >
                            Sign Off
                          </button>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Export Preview Modal */}
              {exportPreview && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-teal-400 flex items-center gap-1">
                      <FileText className="w-3.5 h-3.5" /> Markdown Export Preview
                    </h3>
                    <button
                      onClick={() => setExportPreview(null)}
                      className="text-xs text-slate-500 hover:text-slate-300"
                    >
                      Close Preview
                    </button>
                  </div>
                  <pre className="bg-slate-950 p-4 rounded-lg text-[11px] font-mono text-slate-300 max-h-64 overflow-y-auto whitespace-pre-wrap border border-slate-800">
                    {exportPreview}
                  </pre>
                </div>
              )}
            </>
          ) : (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-500 flex flex-col items-center justify-center h-full">
              <Package className="w-10 h-10 text-slate-700 mb-3" />
              <p className="text-sm font-medium text-slate-400">Select a handover case to review</p>
              <p className="text-xs text-slate-500 mt-1">
                Inspect package readiness, compile multi-domain versions, and track role sign-offs.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
