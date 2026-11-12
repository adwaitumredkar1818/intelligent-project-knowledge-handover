"use client";

import React, { useState } from "react";
import {
  Database,
  UploadCloud,
  PlugZap,
  RefreshCw,
  Search,
  FileText,
  FileCode,
  GitBranch,
  ShieldCheck,
  Download,
  ExternalLink,
  Layers,
  CheckCircle2,
  AlertCircle,
  Clock,
  ChevronRight,
  Copy,
  Check,
  Lock,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

export function EvidenceCenterView() {
  const {
    activeProject,
    sourceMappings,
    isLoadingSources,
    triggerSync,
    evidenceList,
    evidenceMetrics,
    selectedEvidenceId,
    selectedEvidence,
    setSelectedEvidenceId,
    isLoadingEvidence,
    isLoadingEvidenceDetail,
    evidenceFilter,
    setEvidenceFilter,
    setIsUploadModalOpen,
    setIsAddSourceModalOpen,
    downloadEvidence,
    addToast,
  } = useLiveApp();

  const [activeTab, setActiveTab] = useState<"chunks" | "metadata">("chunks");
  const [copiedHash, setCopiedHash] = useState(false);
  const [syncingMappingId, setSyncingMappingId] = useState<string | null>(null);

  const handleSync = async (mappingId: string) => {
    setSyncingMappingId(mappingId);
    try {
      await triggerSync(mappingId);
    } finally {
      setSyncingMappingId(null);
    }
  };

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  if (!activeProject) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-[#DCE3EB]">
        <Database className="w-12 h-12 text-[#69778D] mb-3 mx-auto" />
        <div className="font-bold text-sm text-[#25334B]">No Active Project Selected</div>
        <p className="text-xs text-[#69778D] mt-1">Select a project workspace to open the Evidence Center.</p>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-5.5rem)] flex flex-col gap-3">
      {/* Evidence Hub Top Summary Bar */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] px-4 py-2.5 shadow-2xs flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-[#249E91]" />
          <span className="font-bold text-xs text-[#25334B]">
            Evidence Workspace · 3-Panel Knowledge Center
          </span>
          <span className="text-[11px] text-[#69778D]">({activeProject.name})</span>
        </div>

        <div className="flex items-center gap-4 text-xs font-medium text-[#69778D]">
          <span>
            Total Evidence:{" "}
            <strong className="text-[#25334B]">{evidenceMetrics?.total_items ?? evidenceList.length}</strong>
          </span>
          <span className="hidden sm:inline">|</span>
          <span className="hidden sm:inline">
            Active Mappings:{" "}
            <strong className="text-[#25334B]">{sourceMappings.length}</strong>
          </span>
          <div className="flex items-center gap-1.5 text-[11px] text-[#249E91] font-semibold bg-[#F0FAF8] px-2 py-0.5 rounded-full border border-[#249E91]/30">
            <Lock className="w-3 h-3" />
            <span>AES-256 Envelope Encrypted</span>
          </div>
        </div>
      </div>

      {/* 3-Panel Main Area */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 min-h-0 overflow-hidden">
        {/* PANEL A: Connected Sources & Ingestion (Cols 1-3) */}
        <div className="lg:col-span-3 bg-white rounded-xl border border-[#DCE3EB] flex flex-col shadow-2xs overflow-hidden">
          {/* Panel Header */}
          <div className="px-3.5 py-3 border-b border-[#DCE3EB] bg-[#F4F6F9] flex items-center justify-between shrink-0">
            <div className="flex items-center gap-1.5 text-xs font-bold text-[#25334B]">
              <span className="w-4 h-4 rounded-full bg-[#4774A9] text-white flex items-center justify-center text-[10px] font-bold">
                A
              </span>
              <span>Connected Sources</span>
            </div>
            <button
              type="button"
              onClick={() => setIsAddSourceModalOpen(true)}
              className="text-[11px] text-[#4774A9] hover:underline font-semibold"
            >
              + Connect
            </button>
          </div>

          {/* Sources List */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {/* Document Upload Source Card */}
            <div className="p-3 rounded-lg border border-[#DCE3EB] bg-[#F4F6F9]/50 hover:border-[#249E91] transition-all">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-[#F0FAF8] text-[#249E91] flex items-center justify-center">
                    <UploadCloud className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="font-semibold text-xs text-[#25334B]">Uploaded Documents</div>
                    <div className="text-[10px] text-[#69778D]">PDF &amp; DOCX with GLM-OCR</div>
                  </div>
                </div>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700">
                  Ready
                </span>
              </div>

              <button
                type="button"
                onClick={() => setIsUploadModalOpen(true)}
                className="mt-3 w-full py-1.5 px-2.5 rounded-lg bg-[#249E91] hover:bg-[#1D8277] text-white text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-2xs"
              >
                <UploadCloud className="w-3.5 h-3.5" />
                <span>Upload Document</span>
              </button>
            </div>

            {/* Mapped External Sources */}
            <div className="pt-2">
              <div className="text-[10px] uppercase font-bold text-[#69778D] px-1 mb-2 tracking-wider">
                External Repositories &amp; Tools ({sourceMappings.length})
              </div>

              {sourceMappings.length === 0 ? (
                <div className="p-4 rounded-lg border border-dashed border-[#DCE3EB] text-center text-xs text-[#69778D]">
                  <PlugZap className="w-6 h-6 text-[#69778D] mx-auto mb-1 opacity-50" />
                  <div className="text-[11px] font-medium text-[#25334B]">No External Sources Mapped</div>
                  <p className="text-[10px] text-[#69778D] mt-0.5 mb-2">Connect a GitHub repository or Jira project.</p>
                  <button
                    type="button"
                    onClick={() => setIsAddSourceModalOpen(true)}
                    className="text-[11px] text-[#4774A9] font-semibold hover:underline"
                  >
                    + Connect GitHub / Jira
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {sourceMappings.map((mapping) => (
                    <div
                      key={mapping.id}
                      className="p-3 rounded-lg border border-[#DCE3EB] bg-white hover:border-[#4774A9] transition-all"
                    >
                      <div className="flex items-start justify-between gap-1">
                        <div className="flex items-center gap-1.5 min-w-0">
                          <GitBranch className="w-3.5 h-3.5 text-[#4774A9] shrink-0" />
                          <div className="font-semibold text-xs text-[#25334B] truncate">
                            {mapping.external_resource_name}
                          </div>
                        </div>
                        <span className={`text-[9px] uppercase px-1.5 py-0.5 rounded font-bold ${
                          mapping.status === "active" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
                        }`}>
                          {mapping.status}
                        </span>
                      </div>

                      <div className="text-[10px] text-[#69778D] mt-1 truncate">
                        Key: {mapping.external_resource_key}
                      </div>

                      <div className="mt-2.5 pt-2 border-t border-[#DCE3EB] flex items-center justify-between">
                        <span className="text-[10px] text-[#69778D]">
                          {mapping.last_synced_at
                            ? `Synced ${new Date(mapping.last_synced_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
                            : "Not synced yet"}
                        </span>
                        <button
                          type="button"
                          disabled={syncingMappingId === mapping.id}
                          onClick={() => handleSync(mapping.id)}
                          className="px-2 py-1 rounded bg-[#E8EEF5] hover:bg-[#DCE3EB] text-[#4774A9] text-[10px] font-semibold flex items-center gap-1 transition-colors disabled:opacity-50"
                        >
                          <RefreshCw className={`w-3 h-3 ${syncingMappingId === mapping.id ? "animate-spin" : ""}`} />
                          <span>Sync Now</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* PANEL B: Evidence Library (Cols 4-7) */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-[#DCE3EB] flex flex-col shadow-2xs overflow-hidden">
          {/* Panel Header */}
          <div className="px-3.5 py-3 border-b border-[#DCE3EB] bg-[#F4F6F9] shrink-0 space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-bold text-[#25334B]">
                <span className="w-4 h-4 rounded-full bg-[#4774A9] text-white flex items-center justify-center text-[10px] font-bold">
                  B
                </span>
                <span>Evidence Library</span>
              </div>
              <span className="text-[11px] text-[#69778D] font-medium">
                {evidenceList.length} items
              </span>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-[#69778D] absolute left-2.5 top-2" />
              <input
                type="text"
                value={evidenceFilter.q}
                onChange={(e) => setEvidenceFilter((prev) => ({ ...prev, q: e.target.value }))}
                placeholder="Filter evidence by title or keywords..."
                className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-[#DCE3EB] bg-white text-xs text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
              />
            </div>

            {/* Provider Filter Tabs */}
            <div className="flex items-center gap-1 overflow-x-auto text-[11px] font-semibold">
              {["all", "upload", "github", "jira"].map((prov) => (
                <button
                  key={prov}
                  type="button"
                  onClick={() => setEvidenceFilter((prev) => ({ ...prev, provider: prov }))}
                  className={`px-2.5 py-1 rounded transition-colors uppercase ${
                    evidenceFilter.provider === prov
                      ? "bg-[#4774A9] text-white shadow-2xs"
                      : "text-[#69778D] hover:bg-[#E8EEF5]"
                  }`}
                >
                  {prov}
                </button>
              ))}
            </div>
          </div>

          {/* Evidence List */}
          <div className="flex-1 overflow-y-auto divide-y divide-[#DCE3EB]">
            {isLoadingEvidence ? (
              <div className="p-8 text-center text-xs text-[#69778D]">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-[#4774A9]" />
                <span>Loading evidence items...</span>
              </div>
            ) : evidenceList.length === 0 ? (
              <div className="p-8 text-center text-xs text-[#69778D] flex flex-col items-center justify-center h-48">
                <Database className="w-8 h-8 text-[#69778D] opacity-40 mb-2" />
                <div className="font-semibold text-[#25334B]">No Evidence Available</div>
                <p className="text-[11px] max-w-xs mt-1">
                  Upload an architecture document in Panel A or trigger a GitHub repository sync.
                </p>
              </div>
            ) : (
              evidenceList.map((item) => {
                const isSelected = selectedEvidenceId === item.id;
                return (
                  <div
                    key={item.id}
                    onClick={() => setSelectedEvidenceId(item.id)}
                    className={`p-3 text-left cursor-pointer transition-colors flex items-start justify-between gap-2 ${
                      isSelected
                        ? "bg-[#F0FAF8] border-l-4 border-l-[#249E91]"
                        : "hover:bg-[#F4F6F9]"
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className="text-[9px] uppercase font-bold px-1.5 py-0.5 rounded bg-[#E8EEF5] text-[#4774A9]">
                          {item.provider}
                        </span>
                        <span className="text-[10px] text-[#69778D] font-mono">
                          {item.content_hash.slice(0, 8)}...
                        </span>
                      </div>
                      <div className="font-semibold text-xs text-[#25334B] truncate">
                        {item.title}
                      </div>
                      <div className="text-[10px] text-[#69778D] mt-0.5 flex items-center gap-2">
                        <span>{item.author_name || "Unknown Author"}</span>
                        <span>·</span>
                        <span>{new Date(item.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <ChevronRight className={`w-4 h-4 shrink-0 mt-2 ${isSelected ? "text-[#249E91]" : "text-[#DCE3EB]"}`} />
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* PANEL C: Evidence Details & Inspector (Cols 8-12) */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-[#DCE3EB] flex flex-col shadow-2xs overflow-hidden">
          {/* Panel Header */}
          <div className="px-3.5 py-3 border-b border-[#DCE3EB] bg-[#F4F6F9] flex items-center justify-between shrink-0">
            <div className="flex items-center gap-1.5 text-xs font-bold text-[#25334B]">
              <span className="w-4 h-4 rounded-full bg-[#4774A9] text-white flex items-center justify-center text-[10px] font-bold">
                C
              </span>
              <span>Evidence Details &amp; Inspector</span>
            </div>
            {selectedEvidence && (
              <button
                type="button"
                onClick={() => downloadEvidence(selectedEvidence.id, selectedEvidence.title)}
                className="px-2.5 py-1 rounded-lg bg-[#4774A9] hover:bg-[#365F92] text-white text-[11px] font-semibold flex items-center gap-1 transition-colors shadow-2xs"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Decrypted</span>
              </button>
            )}
          </div>

          {/* Panel Body */}
          {!selectedEvidence ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-xs text-[#69778D]">
              <FileText className="w-10 h-10 text-[#69778D] opacity-40 mb-2 stroke-[1.5]" />
              <div className="font-semibold text-[#25334B]">No Evidence Item Selected</div>
              <p className="text-[11px] max-w-xs mt-1">
                Select an evidence item from Panel B to inspect full metadata, extracted chunks, and decrypted content.
              </p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Item Overview */}
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-[#E8EEF5] text-[#4774A9]">
                    {selectedEvidence.source_type}
                  </span>
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700">
                    {selectedEvidence.indexing_status}
                  </span>
                </div>
                <h2 className="text-sm font-bold text-[#25334B] leading-snug">
                  {selectedEvidence.title}
                </h2>
                <div className="text-[11px] text-[#69778D] mt-1 flex items-center gap-3">
                  <span>Author: {selectedEvidence.author_name || "Internal Document"}</span>
                  <span>Ingested: {new Date(selectedEvidence.created_at).toLocaleString()}</span>
                </div>
              </div>

              {/* Security & Provenance Badge */}
              <div className="p-3 rounded-lg bg-[#F0FAF8] border border-[#249E91]/30 text-xs">
                <div className="flex items-center gap-1.5 font-bold text-[#249E91] text-[11px] mb-1">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Verified Canonical Evidence</span>
                </div>
                <div className="text-[11px] text-[#25334B] font-mono flex items-center justify-between gap-2 mt-1">
                  <span className="truncate">SHA-256: {selectedEvidence.content_hash}</span>
                  <button
                    type="button"
                    onClick={() => copyHash(selectedEvidence.content_hash)}
                    className="p-1 text-[#69778D] hover:text-[#25334B] shrink-0"
                    title="Copy full SHA-256 hash"
                  >
                    {copiedHash ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* Tabs: Chunks vs Metadata */}
              <div className="flex border-b border-[#DCE3EB] text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => setActiveTab("chunks")}
                  className={`pb-2 px-3 transition-colors ${
                    activeTab === "chunks"
                      ? "border-b-2 border-[#4774A9] text-[#4774A9]"
                      : "text-[#69778D] hover:text-[#25334B]"
                  }`}
                >
                  Extracted Text Chunks ({selectedEvidence.chunks?.length || 0})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("metadata")}
                  className={`pb-2 px-3 transition-colors ${
                    activeTab === "metadata"
                      ? "border-b-2 border-[#4774A9] text-[#4774A9]"
                      : "text-[#69778D] hover:text-[#25334B]"
                  }`}
                >
                  Source Metadata
                </button>
              </div>

              {/* Tab Content */}
              {activeTab === "chunks" ? (
                <div className="space-y-2.5">
                  {!selectedEvidence.chunks || selectedEvidence.chunks.length === 0 ? (
                    <div className="p-4 rounded-lg bg-[#F4F6F9] text-center text-xs text-[#69778D]">
                      {selectedEvidence.extracted_text_preview ? (
                        <div className="text-left font-mono text-[11px] whitespace-pre-wrap leading-relaxed text-[#25334B]">
                          {selectedEvidence.extracted_text_preview}
                        </div>
                      ) : (
                        "Text extraction in progress or raw binary asset."
                      )}
                    </div>
                  ) : (
                    selectedEvidence.chunks.map((chk) => (
                      <div
                        key={chk.id}
                        className="p-3 rounded-lg border border-[#DCE3EB] bg-[#F4F6F9]/50 text-xs"
                      >
                        <div className="flex items-center justify-between text-[10px] text-[#69778D] mb-1 font-mono">
                          <span>Chunk #{chk.chunk_index}</span>
                          <span>{chk.character_count} chars</span>
                        </div>
                        <p className="text-[11px] text-[#25334B] font-mono whitespace-pre-wrap leading-relaxed">
                          {chk.content_preview}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              ) : (
                <div className="space-y-2 text-xs font-mono">
                  <div className="p-2.5 rounded-lg bg-[#F4F6F9] border border-[#DCE3EB]">
                    <div className="text-[10px] text-[#69778D] uppercase font-bold">Evidence ID</div>
                    <div className="text-[#25334B] mt-0.5">{selectedEvidence.id}</div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-[#F4F6F9] border border-[#DCE3EB]">
                    <div className="text-[10px] text-[#69778D] uppercase font-bold">Platform Provider</div>
                    <div className="text-[#25334B] mt-0.5">{selectedEvidence.provider}</div>
                  </div>
                  {selectedEvidence.source_url && (
                    <div className="p-2.5 rounded-lg bg-[#F4F6F9] border border-[#DCE3EB]">
                      <div className="text-[10px] text-[#69778D] uppercase font-bold">Source URL</div>
                      <a
                        href={selectedEvidence.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[#4774A9] hover:underline flex items-center gap-1 mt-0.5"
                      >
                        <span>{selectedEvidence.source_url}</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
