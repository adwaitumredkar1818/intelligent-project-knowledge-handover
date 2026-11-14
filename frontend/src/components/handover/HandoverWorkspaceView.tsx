"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  FileCheck2,
  Package,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
  ShieldCheck,
  User,
  Users,
  Download,
  Share2,
  Sparkles,
  FileText,
  RefreshCw,
  Plus,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import { Button } from "../ui";

export function HandoverWorkspaceView() {
  const { activeProject, user } = useLiveApp();
  const [activeTab, setActiveTab] = useState<"packages" | "checklists" | "dossier">("packages");
  const [cases, setCases] = useState<Array<Record<string, unknown>>>([]);
  const [selectedCase, setSelectedCase] = useState<Record<string, unknown> | null>(null);
  const [versions, setVersions] = useState<Array<Record<string, unknown>>>([]);
  const [checklists, setChecklists] = useState<Array<Record<string, unknown>>>([]);
  const [readiness, setReadiness] = useState<Record<string, unknown> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAssembling, setIsAssembling] = useState(false);

  const loadHandoverData = async (projectId: string) => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem("auth_token");
      const headers = { Authorization: `Bearer ${token}` };

      // Load handover cases
      const res = await fetch(`http://127.0.0.1:8000/api/v1/cases?project_id=${projectId}`, {
        headers,
      });
      if (res.ok) {
        const data = await res.json();
        const items = data.items || [];
        setCases(items);
        if (items.length > 0) {
          const current = items[0];
          setSelectedCase(current);

          // Load readiness
          const rRes = await fetch(
            `http://127.0.0.1:8000/api/v1/cases/${current.id}/readiness`,
            {
              method: "POST",
              headers,
            }
          );
          if (rRes.ok) setReadiness(await rRes.json());

          // Load checklists
          const cRes = await fetch(
            `http://127.0.0.1:8000/api/v1/cases/${current.id}/checklists`,
            { headers }
          );
          if (cRes.ok) setChecklists(await cRes.json());
        }
      }
    } catch (err) {
      console.error("Failed to load handover data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (activeProject) {
      loadHandoverData(activeProject.id);
    }
  }, [activeProject]);

  const handleAssemble = async () => {
    if (!selectedCase) return;
    setIsAssembling(true);
    try {
      const token = localStorage.getItem("auth_token");
      await fetch(`http://127.0.0.1:8000/api/v1/cases/${selectedCase.id}/assemble`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (activeProject) await loadHandoverData(activeProject.id);
    } catch (err) {
      console.error("Failed to assemble handover package:", err);
    } finally {
      setIsAssembling(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-[#DCE3EB]">
        <FileCheck2 className="w-12 h-12 text-[#69778D] mb-3 mx-auto" />
        <div className="font-bold text-sm text-[#25334B]">No Active Project Selected</div>
        <p className="text-xs text-[#69778D] mt-1">Select a project workspace to access Handover Management.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-[#4774A9] uppercase tracking-wider">
            <span>Knowledge Transfer</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#249E91]" />
            <span className="text-[#69778D] font-normal">{activeProject.name}</span>
          </div>
          <h1 className="text-xl font-bold text-[#25334B] mt-1 tracking-tight">
            Handover Lifecycle &amp; Dossiers
          </h1>
          <p className="text-xs text-[#69778D] mt-0.5">
            Structured knowledge packaging, transition checklists, and designated human reviewer approval workflows.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="secondary"
            icon={RefreshCw}
            onClick={() => loadHandoverData(activeProject.id)}
            disabled={isLoading}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            icon={Package}
            onClick={handleAssemble}
            disabled={isAssembling || !selectedCase}
          >
            {isAssembling ? "Assembling Package..." : "Assemble New Dossier"}
          </Button>
        </div>
      </div>

      {/* KPI Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="text-[11px] font-semibold text-[#69778D] uppercase tracking-wider">Handover Cases</div>
          <div className="text-2xl font-bold text-[#25334B] mt-1">{cases.length}</div>
          <div className="text-[11px] text-[#69778D] mt-0.5">Active transition packages</div>
        </div>

        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="text-[11px] font-semibold text-[#69778D] uppercase tracking-wider">Readiness Score</div>
          <div className="text-2xl font-bold text-[#249E91] mt-1">
            {readiness?.overall_readiness_pct ? `${Math.round(readiness.overall_readiness_pct)}%` : "0%"}
          </div>
          <div className="text-[11px] text-[#249E91] mt-0.5">Eligibility assessment</div>
        </div>

        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="text-[11px] font-semibold text-[#69778D] uppercase tracking-wider">Checklist Items</div>
          <div className="text-2xl font-bold text-[#4774A9] mt-1">
            {checklists.reduce((acc, c) => acc + (c.items?.length || 0), 0)}
          </div>
          <div className="text-[11px] text-[#69778D] mt-0.5">Transition tasks</div>
        </div>

        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="text-[11px] font-semibold text-[#69778D] uppercase tracking-wider">Review Status</div>
          <div className="text-2xl font-bold text-[#D39B43] mt-1">
            {selectedCase?.status || "Draft"}
          </div>
          <div className="text-[11px] text-[#69778D] mt-0.5">Human reviewer required</div>
        </div>
      </div>

      {/* Main Handover Content */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] p-6 shadow-2xs space-y-6">
        <div className="flex border-b border-[#DCE3EB] gap-6 text-xs font-semibold pb-3">
          <span className="text-[#4774A9] flex items-center gap-1.5">
            <Package className="w-4 h-4" />
            <span>Active Transition Dossier</span>
          </span>
        </div>

        {selectedCase ? (
          <div className="space-y-6">
            {/* Transition Header Card */}
            <div className="p-4 rounded-xl border border-[#DCE3EB] bg-[#F4F6F9]/50 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-[#25334B]">{selectedCase.title}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#E8EEF5] text-[#4774A9]">
                    {selectedCase.status}
                  </span>
                </div>
                <p className="text-xs text-[#69778D]">
                  {selectedCase.description || "Comprehensive project knowledge transfer package with evidence citations."}
                </p>
              </div>

              <div className="flex items-center gap-4 text-xs font-mono">
                <div className="text-right">
                  <div className="text-[10px] text-[#69778D] uppercase">Target Date</div>
                  <div className="text-[#25334B] font-bold">
                    {selectedCase.target_handover_date
                      ? new Date(selectedCase.target_handover_date).toLocaleDateString()
                      : "Open"}
                  </div>
                </div>
              </div>
            </div>

            {/* Transition Roles Banner */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-3.5 rounded-lg border border-[#DCE3EB] bg-white">
                <div className="text-[10px] font-bold text-[#69778D] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-[#D36D72]" />
                  <span>Departing Owner</span>
                </div>
                <div className="text-xs font-bold text-[#25334B]">
                  {selectedCase.departing_user?.email || "Lead Engineer (Departing)"}
                </div>
                <div className="text-[11px] text-[#69778D]">Prepares knowledge transfer</div>
              </div>

              <div className="p-3.5 rounded-lg border border-[#DCE3EB] bg-white">
                <div className="text-[10px] font-bold text-[#69778D] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-[#249E91]" />
                  <span>Incoming Successor</span>
                </div>
                <div className="text-xs font-bold text-[#25334B]">
                  {selectedCase.successor_user?.email || "Successor Assignee"}
                </div>
                <div className="text-[11px] text-[#69778D]">Acknowledges receipt</div>
              </div>

              <div className="p-3.5 rounded-lg border border-[#DCE3EB] bg-white">
                <div className="text-[10px] font-bold text-[#69778D] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#4774A9]" />
                  <span>Designated Reviewer</span>
                </div>
                <div className="text-xs font-bold text-[#25334B]">
                  {selectedCase.reviewer_user?.email || "Project Reviewer"}
                </div>
                <div className="text-[11px] text-[#69778D]">Mandatory human approval</div>
              </div>
            </div>

            {/* Structured Dossier Sections */}
            <div className="border border-[#DCE3EB] rounded-xl p-5 bg-white space-y-4">
              <div className="text-xs font-bold text-[#25334B] uppercase tracking-wider">
                Reconstructed Handover Dossier Sections
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-lg border border-[#DCE3EB] bg-[#F4F6F9]/50">
                  <div className="font-bold text-[#25334B] mb-1">1. Architectural Decisions &amp; Rationale</div>
                  <p className="text-[11px] text-[#69778D]">
                    Core technical choices, rejected alternatives, and trade-offs.
                  </p>
                </div>
                <div className="p-3 rounded-lg border border-[#DCE3EB] bg-[#F4F6F9]/50">
                  <div className="font-bold text-[#25334B] mb-1">2. Completed &amp; Unfinished Work</div>
                  <p className="text-[11px] text-[#69778D]">
                    In-flight PRs, pending issues, and development status.
                  </p>
                </div>
                <div className="p-3 rounded-lg border border-[#DCE3EB] bg-[#F4F6F9]/50">
                  <div className="font-bold text-[#25334B] mb-1">3. Active Risks &amp; Critical Blockers</div>
                  <p className="text-[11px] text-[#69778D]">
                    Delivery hazards, open questions, and mitigation strategies.
                  </p>
                </div>
                <div className="p-3 rounded-lg border border-[#DCE3EB] bg-[#F4F6F9]/50">
                  <div className="font-bold text-[#25334B] mb-1">4. Operational Runbooks &amp; Deployment</div>
                  <p className="text-[11px] text-[#69778D]">
                    CI/CD pipelines, environment configs, and troubleshooting runbooks.
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-12 text-center">
            <Package className="w-12 h-12 text-[#69778D] mb-3 mx-auto" />
            <div className="font-bold text-sm text-[#25334B]">No Handover Case Created</div>
            <p className="text-xs text-[#69778D] mt-1 max-w-sm mx-auto">
              Create a transition case to assemble verified findings, assign incoming successors, and generate auditable dossiers.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
