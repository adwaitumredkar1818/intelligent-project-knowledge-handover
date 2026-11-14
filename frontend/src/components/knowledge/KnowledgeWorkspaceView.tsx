"use client";

import React, { useState, useEffect, useTransition } from "react";
import Link from "next/link";
import {
  BrainCircuit,
  Search,
  Filter,
  Layers,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldCheck,
  ChevronRight,
  Database,
  ExternalLink,
  RefreshCw,
  GitCommit,
  Cpu,
  FileText,
  AlertCircle,
  HelpCircle,
  FolderSync,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import { api } from "../../lib/api";
import { Card, CardHeader, Button, Badge, EmptyState } from "../ui";
import { RelationshipWorkspace } from "../relationships/RelationshipWorkspace";

export interface KnowledgeDomainItem {
  domain_id: string;
  code: number;
  display_name: string;
  description: string;
  item_count: number;
  verified_count: number;
  pending_review_count: number;
  rejected_count: number;
  stale_count: number;
  high_confidence_count: number;
  medium_confidence_count: number;
  low_confidence_count: number;
  uncertain_count: number;
  completeness_score: number;
  sources_breakdown: Record<string, number>;
  last_extracted_at: string | null;
}

export interface KnowledgeIntelligenceSummary {
  project_id: string;
  total_findings: number;
  verified_findings: number;
  pending_verification: number;
  rejected_findings: number;
  stale_findings: number;
  overall_confidence_score: number;
  overall_readiness_pct: number;
  domain_coverage: KnowledgeDomainItem[];
  active_runs_count: number;
}

export function KnowledgeWorkspaceView() {
  const { activeProject } = useLiveApp();
  const [activeTab, setActiveTab] = useState<"registers" | "graph" | "timeline">("registers");
  const [selectedDomain, setSelectedDomain] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [summary, setSummary] = useState<KnowledgeIntelligenceSummary | null>(null);
  const [findings, setFindings] = useState<Array<Record<string, unknown>>>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isPending, startTransition] = useTransition();

  const loadKnowledgeData = async (projectId: string) => {
    setIsLoading(true);
    try {
      const summaryData = (await api.knowledgeIntelligence.getSummary(projectId)) as unknown as KnowledgeIntelligenceSummary;
      setSummary(summaryData);

      const findingsRes = await api.knowledgeIntelligence.listFindings(
        projectId,
        selectedDomain === "all" ? undefined : selectedDomain
      );
      setFindings(findingsRes.items || []);
    } catch (err) {
      console.error("Failed to load knowledge intelligence:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (activeProject) {
      loadKnowledgeData(activeProject.id);
    }
  }, [activeProject, selectedDomain]);

  const handleTriggerExtraction = async () => {
    if (!activeProject) return;
    setIsExtracting(true);
    try {
      await fetch(`http://127.0.0.1:8000/api/v1/projects/${activeProject.id}/knowledge-intelligence/extract`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("auth_token")}`,
        },
      });
      await loadKnowledgeData(activeProject.id);
    } catch (err) {
      console.error("Failed to trigger extraction:", err);
    } finally {
      setIsExtracting(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-[#DCE3EB]">
        <BrainCircuit className="w-12 h-12 text-[#69778D] mb-3 mx-auto" />
        <div className="font-bold text-sm text-[#25334B]">No Active Project Selected</div>
        <p className="text-xs text-[#69778D] mt-1">Select a project workspace to access Knowledge Intelligence.</p>
      </div>
    );
  }

  const filteredFindings = findings.filter((f) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (f.title && f.title.toLowerCase().includes(q)) ||
      (f.summary && f.summary.toLowerCase().includes(q)) ||
      (f.category && f.category.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-[#4774A9] uppercase tracking-wider">
            <span>Project Intelligence</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#249E91]" />
            <span className="text-[#69778D] font-normal">{activeProject.name}</span>
          </div>
          <h1 className="text-xl font-bold text-[#25334B] mt-1 tracking-tight">
            Knowledge Intelligence &amp; Registers
          </h1>
          <p className="text-xs text-[#69778D] mt-0.5">
            Structured project knowledge reconstructed across the 8 canonical domains with evidence attribution.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="secondary"
            icon={RefreshCw}
            onClick={() => loadKnowledgeData(activeProject.id)}
            disabled={isLoading}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            icon={Sparkles}
            onClick={handleTriggerExtraction}
            disabled={isExtracting}
          >
            {isExtracting ? "Extracting Knowledge..." : "Reconstruct Knowledge"}
          </Button>
        </div>
      </div>

      {/* KPI Metrics Band */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="text-[11px] font-semibold text-[#69778D] uppercase tracking-wider">Total Findings</div>
          <div className="text-2xl font-bold text-[#25334B] mt-1">
            {summary ? summary.total_findings : 0}
          </div>
          <div className="text-[11px] text-[#249E91] mt-0.5 flex items-center gap-1">
            <span>Across 8 domains</span>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="text-[11px] font-semibold text-[#69778D] uppercase tracking-wider">Verified Findings</div>
          <div className="text-2xl font-bold text-[#249E91] mt-1">
            {summary ? summary.verified_findings : 0}
          </div>
          <div className="text-[11px] text-[#69778D] mt-0.5">
            {summary && summary.total_findings > 0
              ? `${Math.round((summary.verified_findings / summary.total_findings) * 100)}% verified`
              : "0% verified"}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="text-[11px] font-semibold text-[#69778D] uppercase tracking-wider">Pending Review</div>
          <div className="text-2xl font-bold text-[#D39B43] mt-1">
            {summary ? summary.pending_verification : 0}
          </div>
          <div className="text-[11px] text-[#69778D] mt-0.5">Awaiting human sign-off</div>
        </div>

        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="text-[11px] font-semibold text-[#69778D] uppercase tracking-wider">Readiness Score</div>
          <div className="text-2xl font-bold text-[#4774A9] mt-1">
            {summary ? `${Math.round(summary.overall_readiness_pct)}%` : "0%"}
          </div>
          <div className="text-[11px] text-[#69778D] mt-0.5">Transition readiness</div>
        </div>
      </div>

      {/* Main Tab View Switcher */}
      <div className="flex border-b border-[#DCE3EB] gap-6 text-xs font-semibold">
        <button
          onClick={() => setActiveTab("registers")}
          className={`pb-3 transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === "registers"
              ? "border-[#4774A9] text-[#4774A9]"
              : "border-transparent text-[#69778D] hover:text-[#25334B]"
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Intelligence Registers (8 Domains)</span>
        </button>

        <button
          onClick={() => setActiveTab("graph")}
          className={`pb-3 transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === "graph"
              ? "border-[#4774A9] text-[#4774A9]"
              : "border-transparent text-[#69778D] hover:text-[#25334B]"
          }`}
        >
          <BrainCircuit className="w-4 h-4" />
          <span>Interactive Knowledge Graph</span>
        </button>
      </div>

      {/* Registers Tab Content */}
      {activeTab === "registers" && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Domain Picker Sidebar */}
          <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs space-y-1">
            <div className="text-xs font-bold text-[#25334B] uppercase tracking-wider mb-3 px-2">
              Knowledge Domains
            </div>
            <button
              onClick={() => setSelectedDomain("all")}
              className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors flex items-center justify-between ${
                selectedDomain === "all"
                  ? "bg-[#E8EEF5] text-[#4774A9] font-bold"
                  : "text-[#69778D] hover:bg-[#F4F6F9] hover:text-[#25334B]"
              }`}
            >
              <span>All Reconstructed Knowledge</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono">
                {summary ? summary.total_findings : 0}
              </span>
            </button>

            {summary?.domain_coverage?.map((d) => (
              <button
                key={d.domain_id}
                onClick={() => setSelectedDomain(d.domain_id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors flex items-center justify-between ${
                  selectedDomain === d.domain_id
                    ? "bg-[#E8EEF5] text-[#4774A9] font-bold"
                    : "text-[#69778D] hover:bg-[#F4F6F9] hover:text-[#25334B]"
                }`}
              >
                <span className="truncate pr-2">{d.display_name}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono">
                  {d.item_count}
                </span>
              </button>
            ))}
          </div>

          {/* Findings List Area */}
          <div className="lg:col-span-3 space-y-4">
            {/* Search Input */}
            <div className="bg-white rounded-xl border border-[#DCE3EB] p-3 shadow-2xs flex items-center gap-2">
              <Search className="w-4 h-4 text-[#69778D]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search findings, decisions, architecture, tasks..."
                className="w-full text-xs text-[#25334B] placeholder:text-[#69778D] focus:outline-none"
              />
            </div>

            {/* Empty State */}
            {filteredFindings.length === 0 ? (
              <div className="bg-white rounded-xl border border-[#DCE3EB] p-8 text-center shadow-2xs">
                <BrainCircuit className="w-12 h-12 text-[#69778D] mb-3 mx-auto" />
                <div className="font-bold text-sm text-[#25334B]">No Knowledge Items Found</div>
                <p className="text-xs text-[#69778D] mt-1 max-w-md mx-auto">
                  {summary && summary.total_findings === 0
                    ? "Knowledge has not yet been extracted for this project. Connect sources or click 'Reconstruct Knowledge' to run the extraction pipeline."
                    : "No items match your active filters or search terms."}
                </p>
                {summary && summary.total_findings === 0 && (
                  <div className="mt-4">
                    <Button
                      variant="primary"
                      icon={Sparkles}
                      onClick={handleTriggerExtraction}
                      disabled={isExtracting}
                    >
                      {isExtracting ? "Extracting..." : "Reconstruct Knowledge Now"}
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                {filteredFindings.map((finding) => (
                  <div
                    key={finding.id}
                    className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs hover:border-[#4774A9] transition-all"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#E8EEF5] text-[#4774A9] uppercase font-mono">
                            {finding.category || "General"}
                          </span>
                          <span
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                              finding.verification_status === "verified"
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : finding.verification_status === "rejected"
                                ? "bg-rose-50 text-rose-700 border border-rose-200"
                                : "bg-amber-50 text-amber-700 border border-amber-200"
                            }`}
                          >
                            {finding.verification_status || "candidate"}
                          </span>
                        </div>
                        <h4 className="text-sm font-bold text-[#25334B]">{finding.title}</h4>
                        <p className="text-xs text-[#69778D] mt-1 leading-relaxed">
                          {finding.summary || finding.content}
                        </p>
                      </div>
                    </div>

                    {/* Metadata & Evidence Attribution */}
                    {finding.evidence_citations && finding.evidence_citations.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-[#DCE3EB] flex items-center gap-2 text-[11px] text-[#69778D]">
                        <Database className="w-3.5 h-3.5 text-[#4774A9]" />
                        <span>Supporting Evidence:</span>
                        <span className="font-mono text-[#25334B]">
                          {finding.evidence_citations.length} sources cited
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Graph Tab Content */}
      {activeTab === "graph" && (
        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs min-h-[500px]">
          <RelationshipWorkspace projectId={activeProject.id} />
        </div>
      )}
    </div>
  );
}
