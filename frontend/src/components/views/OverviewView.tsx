"use client";

import React from "react";
import {
  UploadCloud,
  PlugZap,
  Users,
  CheckCircle2,
  AlertTriangle,
  FolderGit2,
  Calendar,
  Clock,
  ArrowUpRight,
  Database,
  BrainCircuit,
  ShieldCheck,
  Activity,
  Plus,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

export function OverviewView() {
  const {
    activeProject,
    overview,
    isLoadingOverview,
    setIsUploadModalOpen,
    setIsAddSourceModalOpen,
    setIsAddMemberModalOpen,
    setIsCreateProjectModalOpen,
  } = useLiveApp();

  if (!activeProject) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[450px] p-8 text-center bg-white rounded-xl border border-[#DCE3EB] shadow-2xs">
        <FolderGit2 className="w-12 h-12 text-[#4774A9] mb-3 stroke-[1.5]" />
        <h2 className="text-base font-bold text-[#25334B]">No Active Project Selected</h2>
        <p className="text-xs text-[#69778D] max-w-sm mt-1 mb-5">
          Create or select a project workspace to track handover readiness, connect authorised sources, and ingest evidence.
        </p>
        <button
          type="button"
          onClick={() => setIsCreateProjectModalOpen(true)}
          className="px-4 py-2.5 rounded-lg bg-[#4774A9] hover:bg-[#365F92] text-white text-xs font-semibold flex items-center gap-2 transition-colors shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>Create First Project Workspace</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Workspace Header & Quick Actions */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-[#4774A9] uppercase tracking-wider">
            <span>Project Workspace Overview</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#249E91]" />
            <span className="text-[#249E91] font-medium lowercase">live canonical state</span>
          </div>
          <h1 className="text-xl font-bold text-[#25334B] mt-1 tracking-tight">
            {activeProject.name}
          </h1>
          <p className="text-xs text-[#69778D] mt-0.5 max-w-2xl line-clamp-2">
            {activeProject.description || "Structured knowledge handover workspace with provenance tracking and source ACL isolation."}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
          <button
            type="button"
            onClick={() => setIsUploadModalOpen(true)}
            className="px-3.5 py-2 rounded-lg bg-[#249E91] hover:bg-[#1D8277] text-white text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-2xs"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            <span>Ingest Document</span>
          </button>
          <button
            type="button"
            onClick={() => setIsAddSourceModalOpen(true)}
            className="px-3.5 py-2 rounded-lg bg-[#4774A9] hover:bg-[#365F92] text-white text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-2xs"
          >
            <PlugZap className="w-3.5 h-3.5" />
            <span>Connect Source</span>
          </button>
          <button
            type="button"
            onClick={() => setIsAddMemberModalOpen(true)}
            className="px-3.5 py-2 rounded-lg bg-white hover:bg-[#F4F6F9] border border-[#DCE3EB] text-[#25334B] text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Users className="w-3.5 h-3.5 text-[#4774A9]" />
            <span>Add Member</span>
          </button>
        </div>
      </div>

      {/* 4 Core KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Handover Readiness */}
        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="flex items-center justify-between text-xs text-[#69778D] mb-2 font-medium">
            <span>Handover Readiness</span>
            <CheckCircle2 className="w-4 h-4 text-[#249E91]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-[#25334B]">
              {overview?.readiness.overall_readiness_pct ?? 0}%
            </span>
            <span className="text-[11px] font-semibold text-[#249E91] uppercase">
              {overview?.readiness.status || "In Preparation"}
            </span>
          </div>
          {/* Progress bar */}
          <div className="w-full bg-[#E8EEF5] h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-[#249E91] h-full rounded-full transition-all duration-500"
              style={{ width: `${overview?.readiness.overall_readiness_pct ?? 0}%` }}
            />
          </div>
          <div className="mt-2.5 text-[11px] text-[#69778D] flex items-center justify-between">
            <span>Target: {activeProject.target_handover_date ? new Date(activeProject.target_handover_date).toLocaleDateString() : "Flexible"}</span>
            {overview?.readiness.days_remaining !== null && (
              <span>{overview?.readiness.days_remaining}d remaining</span>
            )}
          </div>
        </div>

        {/* 2. Connected Sources */}
        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="flex items-center justify-between text-xs text-[#69778D] mb-2 font-medium">
            <span>Connected Sources</span>
            <PlugZap className="w-4 h-4 text-[#4774A9]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-[#25334B]">
              {overview?.sources.connected_count ?? 0}
            </span>
            <span className="text-[11px] text-[#69778D]">active mappings</span>
          </div>
          <div className="mt-4 pt-2 border-t border-[#DCE3EB] flex items-center justify-between text-[11px] text-[#69778D]">
            <span>Synced: {overview?.sources.active_count ?? 0}</span>
            <span className={overview?.sources.failed_count ? "text-rose-600 font-semibold" : ""}>
              Issues: {overview?.sources.failed_count ?? 0}
            </span>
          </div>
        </div>

        {/* 3. Evidence Items */}
        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="flex items-center justify-between text-xs text-[#69778D] mb-2 font-medium">
            <span>Evidence Items</span>
            <Database className="w-4 h-4 text-[#4774A9]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-[#25334B]">
              {overview?.evidence.total_evidence_items ?? 0}
            </span>
            <span className="text-[11px] text-[#249E91] font-medium">
              {overview?.evidence.indexed_chunks_count ?? 0} chunks
            </span>
          </div>
          <div className="mt-4 pt-2 border-t border-[#DCE3EB] flex items-center justify-between text-[11px] text-[#69778D]">
            <span>AES-256 encrypted</span>
            <span>Nomic 768-dim</span>
          </div>
        </div>

        {/* 4. Reconstructed Knowledge */}
        <div className="bg-white rounded-xl border border-[#DCE3EB] p-4 shadow-2xs">
          <div className="flex items-center justify-between text-xs text-[#69778D] mb-2 font-medium">
            <span>Knowledge Domains</span>
            <BrainCircuit className="w-4 h-4 text-[#4774A9]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-[#25334B]">
              {(overview?.knowledge.decisions_count ?? 0) + (overview?.knowledge.tasks_count ?? 0) + (overview?.knowledge.risks_count ?? 0)}
            </span>
            <span className="text-[11px] text-[#69778D]">extracted entities</span>
          </div>
          <div className="mt-4 pt-2 border-t border-[#DCE3EB] flex items-center justify-between text-[11px] text-[#69778D]">
            <span>Qwen3 8B reasoning</span>
            <span className="text-[#249E91] font-medium">Phase 2</span>
          </div>
        </div>
      </div>

      {/* Attention Required & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Attention Required Card */}
        <div className="bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              <h3 className="text-xs font-bold text-[#25334B] uppercase tracking-wider">
                Attention Required
              </h3>
            </div>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-semibold border border-amber-200">
              {overview?.attention_items.length ?? 0} items
            </span>
          </div>

          <div className="flex-1 space-y-2.5">
            {!overview?.attention_items || overview.attention_items.length === 0 ? (
              <div className="p-4 rounded-lg bg-[#F4F6F9] text-center text-xs text-[#69778D] flex flex-col items-center justify-center h-32">
                <ShieldCheck className="w-6 h-6 text-[#249E91] mb-1.5" />
                <span>All source connections and evidence repositories are operational.</span>
              </div>
            ) : (
              overview.attention_items.map((item) => (
                <div
                  key={item.id}
                  className="p-3 rounded-lg border border-amber-200 bg-amber-50/50 text-xs flex items-start gap-2.5"
                >
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <div className="font-semibold text-amber-900">{item.message}</div>
                    <div className="text-[10px] text-amber-700 mt-0.5">Type: {item.type}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Activity Card */}
        <div className="bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-[#4774A9]" />
              <h3 className="text-xs font-bold text-[#25334B] uppercase tracking-wider">
                Recent Audit Trail Activity
              </h3>
            </div>
            <span className="text-[11px] text-[#69778D]">PostgreSQL Audit Log</span>
          </div>

          <div className="flex-1 space-y-2.5">
            {!overview?.recent_activity || overview.recent_activity.length === 0 ? (
              <div className="p-4 rounded-lg bg-[#F4F6F9] text-center text-xs text-[#69778D] flex flex-col items-center justify-center h-32">
                <Clock className="w-6 h-6 text-[#69778D] mb-1.5" />
                <span>No recent activity recorded yet. Ingest documents or connect sources to populate.</span>
              </div>
            ) : (
              overview.recent_activity.map((act) => (
                <div
                  key={act.id}
                  className="p-2.5 rounded-lg border border-[#DCE3EB] bg-[#F4F6F9]/60 text-xs flex items-start justify-between gap-3"
                >
                  <div className="min-w-0">
                    <div className="font-medium text-[#25334B] truncate">
                      {act.description}
                    </div>
                    <div className="text-[10px] text-[#69778D] mt-0.5">
                      Actor: {act.actor_name || "System"} · {act.event_type}
                    </div>
                  </div>
                  <span className="text-[10px] text-[#69778D] shrink-0 whitespace-nowrap">
                    {new Date(act.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
