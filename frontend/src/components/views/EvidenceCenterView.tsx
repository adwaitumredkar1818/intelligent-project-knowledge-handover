"use client";

import React, { useState, useMemo, useEffect } from "react";
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
  ChevronDown,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

// Helper to render category badges consistently
function getCategoryBadge(category?: string, sourceType?: string) {
  const cat = (category || sourceType || "").toLowerCase();
  if (cat.includes("pdf")) {
    return { label: "PDF Document", bg: "bg-rose-50 text-rose-700 border-rose-200" };
  }
  if (cat.includes("docx") || cat.includes("doc")) {
    return { label: "DOCX Document", bg: "bg-blue-50 text-blue-700 border-blue-200" };
  }
  if (cat.includes("commit")) {
    return { label: "Git Commit", bg: "bg-slate-100 text-slate-700 border-slate-200" };
  }
  if (cat.includes("pull_request") || cat.includes("pr")) {
    return { label: "Pull Request", bg: "bg-purple-50 text-purple-700 border-purple-200" };
  }
  if (cat.includes("design") || cat.includes("architecture")) {
    return { label: "Architecture / Design", bg: "bg-amber-50 text-amber-800 border-amber-200" };
  }
  if (cat.includes("issue")) {
    return { label: "Issue", bg: "bg-emerald-50 text-emerald-700 border-emerald-200" };
  }
  if (cat.includes("code")) {
    return { label: "Source Code", bg: "bg-cyan-50 text-cyan-800 border-cyan-200" };
  }
  if (cat.includes("discussion")) {
    return { label: "Discussion", bg: "bg-indigo-50 text-indigo-700 border-indigo-200" };
  }
  return { label: category || "Document", bg: "bg-gray-100 text-gray-700 border-gray-200" };
}

function getProviderBadge(provider?: string, sourceType?: string) {
  const p = (provider || "").toLowerCase();
  const s = (sourceType || "").toLowerCase();
  if (
    p === "upload" ||
    p === "document_upload" ||
    p === "local_upload" ||
    p === "pdf" ||
    p === "docx" ||
    s === "document_upload" ||
    s === "local_upload"
  ) {
    return { label: "UPLOAD", bg: "bg-emerald-50 text-emerald-700 border-emerald-200" };
  }
  if (p === "github" || s === "github") {
    return { label: "GITHUB", bg: "bg-sky-50 text-sky-700 border-sky-200" };
  }
  if (p === "jira" || s === "jira") {
    return { label: "JIRA", bg: "bg-indigo-50 text-indigo-700 border-indigo-200" };
  }
  if (p === "slack" || s === "slack") {
    return { label: "SLACK", bg: "bg-purple-50 text-purple-700 border-purple-200" };
  }
  return { label: (p || s || "UNKNOWN").toUpperCase(), bg: "bg-gray-100 text-gray-700 border-gray-200" };
}

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
  const [copiedChunkId, setCopiedChunkId] = useState<string | null>(null);
  const [copiedMetadataKey, setCopiedMetadataKey] = useState<string | null>(null);
  const [expandedChunkIds, setExpandedChunkIds] = useState<Record<string, boolean>>({});
  const [syncingMappingId, setSyncingMappingId] = useState<string | null>(null);

  const formatBytes = (bytes?: number | null) => {
    if (!bytes || bytes <= 0) return "—";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB (${bytes.toLocaleString()} bytes)`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB (${bytes.toLocaleString()} bytes)`;
  };

  const copyChunk = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedChunkId(id);
    setTimeout(() => setCopiedChunkId(null), 2000);
  };

  const copyMetadata = (key: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMetadataKey(key);
    setTimeout(() => setCopiedMetadataKey(null), 2000);
  };

  const toggleChunkExpand = (id: string) => {
    setExpandedChunkIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

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

  const filteredEvidenceList = useMemo(() => {
    return evidenceList.filter((item) => {
      // 1. Filter by provider tab
      if (evidenceFilter.provider && evidenceFilter.provider !== "all") {
        const prov = (item.provider || "").toLowerCase();
        const srcType = (item.source_type || "").toLowerCase();
        const srcProv = (item.source_provider || "").toLowerCase();
        const cat = (item.category || "").toLowerCase();

        if (evidenceFilter.provider === "upload") {
          const isDocUpload =
            prov === "upload" ||
            prov === "pdf" ||
            prov === "docx" ||
            prov === "document_upload" ||
            prov === "local_upload" ||
            srcType === "document_upload" ||
            srcProv === "local_upload" ||
            cat === "pdf_document" ||
            cat === "docx_document";
          if (!isDocUpload) return false;
        } else if (evidenceFilter.provider === "github") {
          const isGithub = prov === "github" || srcType === "github" || srcProv === "github";
          if (!isGithub) return false;
        } else if (evidenceFilter.provider === "jira") {
          const isJira = prov === "jira" || srcType === "jira" || srcProv === "jira";
          if (!isJira) return false;
        }
      }

      // 2. Filter by search query
      if (evidenceFilter.q && evidenceFilter.q.trim()) {
        const query = evidenceFilter.q.trim().toLowerCase();
        const matchesTitle = item.title?.toLowerCase().includes(query);
        const matchesFilename = item.original_filename?.toLowerCase().includes(query);
        const matchesHash = item.content_hash?.toLowerCase().includes(query);
        const matchesAuthor = (item.author_name || item.source_author_identity || "").toLowerCase().includes(query);
        if (!matchesTitle && !matchesFilename && !matchesHash && !matchesAuthor) return false;
      }

      return true;
    });
  }, [evidenceList, evidenceFilter.provider, evidenceFilter.q]);

  // Keep selectedEvidenceId synchronized with the active filtered list
  useEffect(() => {
    if (filteredEvidenceList.length > 0) {
      if (!selectedEvidenceId || !filteredEvidenceList.some((it) => it.id === selectedEvidenceId)) {
        setSelectedEvidenceId(filteredEvidenceList[0]!.id);
      }
    } else {
      setSelectedEvidenceId(null);
    }
  }, [filteredEvidenceList, selectedEvidenceId, setSelectedEvidenceId]);

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
                {filteredEvidenceList.length} items
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
            ) : filteredEvidenceList.length === 0 ? (
              <div className="p-8 text-center text-xs text-[#69778D] flex flex-col items-center justify-center h-48">
                {evidenceFilter.provider === "upload" ? (
                  <>
                    <UploadCloud className="w-8 h-8 text-[#249E91] opacity-70 mb-2" />
                    <div className="font-semibold text-[#25334B]">No Uploaded Documents Found</div>
                    <p className="text-[11px] max-w-xs mt-1 text-[#69778D]">
                      Upload PDF or DOCX architecture specifications in Panel A.
                    </p>
                    <button
                      type="button"
                      onClick={() => setIsUploadModalOpen(true)}
                      className="mt-3 px-3 py-1.5 rounded-lg bg-[#249E91] hover:bg-[#1D8277] text-white text-[11px] font-semibold flex items-center gap-1.5 transition-colors shadow-2xs"
                    >
                      <UploadCloud className="w-3.5 h-3.5" />
                      <span>Upload Document</span>
                    </button>
                  </>
                ) : evidenceFilter.provider === "github" ? (
                  <>
                    <GitBranch className="w-8 h-8 text-[#4774A9] opacity-70 mb-2" />
                    <div className="font-semibold text-[#25334B]">No GitHub Evidence Found</div>
                    <p className="text-[11px] max-w-xs mt-1 text-[#69778D]">
                      Connect a repository in Panel A or trigger a sync to ingest commits &amp; PRs.
                    </p>
                  </>
                ) : evidenceFilter.provider === "jira" ? (
                  <>
                    <Database className="w-8 h-8 text-indigo-500 opacity-70 mb-2" />
                    <div className="font-semibold text-[#25334B]">No Jira Evidence Found</div>
                    <p className="text-[11px] max-w-xs mt-1 text-[#69778D]">
                      Connect a Jira project in Panel A or trigger a sync to ingest issues.
                    </p>
                  </>
                ) : (
                  <>
                    <Database className="w-8 h-8 text-[#69778D] opacity-40 mb-2" />
                    <div className="font-semibold text-[#25334B]">No Evidence Available</div>
                    <p className="text-[11px] max-w-xs mt-1">
                      Upload an architecture document in Panel A or trigger a GitHub repository sync.
                    </p>
                  </>
                )}
              </div>
            ) : (
              filteredEvidenceList.map((item) => {
                const isSelected = selectedEvidenceId === item.id;
                const provBadge = getProviderBadge(item.provider, item.source_type);
                const catBadge = getCategoryBadge(item.category, item.source_type);
                const isUpload = provBadge.label === "UPLOAD";

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
                      <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                        <span className={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded border ${provBadge.bg}`}>
                          {provBadge.label}
                        </span>
                        <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded border ${catBadge.bg}`}>
                          {catBadge.label}
                        </span>
                        <span className="text-[10px] text-[#69778D] font-mono">
                          {item.content_hash.slice(0, 8)}...
                        </span>
                      </div>
                      <div className="font-semibold text-xs text-[#25334B] truncate" title={item.title}>
                        {item.title}
                      </div>
                      {item.original_filename && item.original_filename !== item.title && (
                        <div className="text-[10px] text-[#4774A9] font-mono truncate mt-0.5">
                          {item.original_filename}
                        </div>
                      )}
                      <div className="text-[10px] text-[#69778D] mt-1 flex items-center gap-2 flex-wrap">
                        <span>{item.author_name || item.source_author_identity || (isUpload ? "Uploaded Document" : "System Ingested")}</span>
                        <span>·</span>
                        <span>{new Date(item.created_at).toLocaleDateString()}</span>
                        {item.page_count != null && item.page_count > 0 ? (
                          <>
                            <span>·</span>
                            <span>{item.page_count} {item.page_count === 1 ? "page" : "pages"}</span>
                          </>
                        ) : null}
                        {item.file_size_bytes != null && item.file_size_bytes > 0 ? (
                          <>
                            <span>·</span>
                            <span>{(item.file_size_bytes / 1024).toFixed(1)} KB</span>
                          </>
                        ) : null}
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
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${getProviderBadge(selectedEvidence.provider, selectedEvidence.source_type).bg}`}>
                    {getProviderBadge(selectedEvidence.provider, selectedEvidence.source_type).label}
                  </span>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${getCategoryBadge(selectedEvidence.category, selectedEvidence.source_type).bg}`}>
                    {getCategoryBadge(selectedEvidence.category, selectedEvidence.source_type).label}
                  </span>
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {selectedEvidence.processing_status || "extracted"}
                  </span>
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-sky-50 text-sky-700 border border-sky-200">
                    {selectedEvidence.indexing_status || "indexed"}
                  </span>
                </div>
                <h2 className="text-sm font-bold text-[#25334B] leading-snug">
                  {selectedEvidence.title}
                </h2>
                {selectedEvidence.original_filename && (
                  <div className="text-xs text-[#4774A9] font-mono mt-1 flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{selectedEvidence.original_filename}</span>
                  </div>
                )}
                <div className="text-[11px] text-[#69778D] mt-1.5 flex items-center gap-2 flex-wrap">
                  <span>Author: {selectedEvidence.author_name || selectedEvidence.source_author_identity || "Internal Document"}</span>
                  <span>·</span>
                  <span>Ingested: {new Date(selectedEvidence.created_at).toLocaleString()}</span>
                  {selectedEvidence.file_size_bytes != null && selectedEvidence.file_size_bytes > 0 && (
                    <>
                      <span>·</span>
                      <span>{(selectedEvidence.file_size_bytes / 1024).toFixed(1)} KB</span>
                    </>
                  )}
                  {selectedEvidence.page_count != null && selectedEvidence.page_count > 0 && (
                    <>
                      <span>·</span>
                      <span>{selectedEvidence.page_count} {selectedEvidence.page_count === 1 ? "page" : "pages"}</span>
                    </>
                  )}
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
                <div className="space-y-3">
                  {!selectedEvidence.chunks || selectedEvidence.chunks.length === 0 ? (
                    <div className="p-6 rounded-xl bg-[#F4F6F9] border border-[#DCE3EB] text-center text-xs text-[#69778D]">
                      {(selectedEvidence.extracted_content?.extracted_text || selectedEvidence.extracted_text_preview) ? (
                        <div>
                          <div className="text-[11px] font-semibold text-[#25334B] mb-2 uppercase tracking-wide text-left flex items-center justify-between">
                            <span className="flex items-center gap-1.5">
                              <FileText className="w-3.5 h-3.5 text-[#249E91]" />
                              <span>Extracted Text Content</span>
                            </span>
                            <span className="text-[10px] text-[#69778D] font-mono">
                              {(selectedEvidence.extracted_content?.char_count || (selectedEvidence.extracted_text_preview || "").length).toLocaleString()} chars
                            </span>
                          </div>
                          <div className="text-left font-mono text-[11px] whitespace-pre-wrap leading-relaxed text-[#25334B] bg-white p-3.5 rounded-lg border border-[#DCE3EB] max-h-96 overflow-y-auto">
                            {selectedEvidence.extracted_content?.extracted_text || selectedEvidence.extracted_text_preview}
                          </div>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center justify-center gap-1.5 py-4">
                          <FileText className="w-8 h-8 text-[#69778D]/40" />
                          <span className="font-semibold text-[#25334B]">No text chunks generated yet</span>
                          <span className="text-[11px]">Text extraction in progress or document is being indexed.</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    selectedEvidence.chunks.map((chk, idx) => {
                      const text = chk.content_text || chk.content_preview || "";
                      const charCount = chk.char_length ?? chk.character_count ?? text.length;
                      const wordCount = chk.word_count ?? (text ? text.split(/\s+/).filter(Boolean).length : 0);
                      const isLong = text.length > 500;
                      const isExpanded = expandedChunkIds[chk.id];

                      return (
                        <div
                          key={chk.id || idx}
                          className="rounded-xl border border-[#DCE3EB] bg-white shadow-2xs overflow-hidden transition-all hover:border-[#B5C6D8]"
                        >
                          {/* Chunk Header */}
                          <div className="px-3.5 py-2.5 bg-[#F8FAFC] border-b border-[#E2E8F0] flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2">
                              <span className="font-bold font-mono text-[#203653] bg-[#E8EEF5] px-2 py-0.5 rounded text-[11px]">
                                Chunk #{chk.chunk_index + 1}
                              </span>
                              {chk.page_number && (
                                <span className="text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.5 rounded">
                                  Page {chk.page_number}
                                </span>
                              )}
                              {chk.section_title && (
                                <span className="text-[11px] font-medium text-[#4774A9] truncate max-w-[200px]" title={chk.section_title}>
                                  {chk.section_title}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 font-mono text-[11px] text-[#69778D]">
                              <span>{charCount.toLocaleString()} chars</span>
                              <span>•</span>
                              <span>{wordCount.toLocaleString()} words</span>
                              <button
                                type="button"
                                onClick={() => copyChunk(chk.id, text)}
                                className="p-1 hover:text-[#25334B] text-[#69778D] rounded transition-colors"
                                title="Copy chunk text"
                              >
                                {copiedChunkId === chk.id ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                                ) : (
                                  <Copy className="w-3.5 h-3.5" />
                                )}
                              </button>
                            </div>
                          </div>

                          {/* Chunk Body */}
                          <div className="p-3.5">
                            <div
                              className={`text-[12px] text-[#25334B] font-mono whitespace-pre-wrap leading-relaxed select-text ${
                                isLong && !isExpanded ? "max-h-48 overflow-hidden relative" : "max-h-96 overflow-y-auto"
                              }`}
                            >
                              {text || <span className="text-[#94A3B8] italic">Empty chunk text</span>}
                              {isLong && !isExpanded && (
                                <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-white to-transparent pointer-events-none" />
                              )}
                            </div>

                            {isLong && (
                              <button
                                type="button"
                                onClick={() => toggleChunkExpand(chk.id)}
                                className="mt-2 text-[11px] font-semibold text-[#4774A9] hover:text-[#203653] flex items-center gap-1 cursor-pointer"
                              >
                                <span>{isExpanded ? "Show Less" : "Show Full Chunk Text"}</span>
                                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              ) : (
                <div className="space-y-3 text-xs">
                  {/* Identity & Origin Card */}
                  <div className="rounded-xl border border-[#DCE3EB] bg-white overflow-hidden shadow-2xs">
                    <div className="px-3.5 py-2 bg-[#F8FAFC] border-b border-[#E2E8F0] font-semibold text-[#25334B] flex items-center gap-1.5 text-[11px] uppercase tracking-wide">
                      <Layers className="w-3.5 h-3.5 text-[#4774A9]" />
                      <span>Evidence Identity &amp; Origin</span>
                    </div>
                    <div className="p-3.5 space-y-2.5 font-mono text-[11px]">
                      <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                        <span className="text-[#69778D]">Evidence ID</span>
                        <div className="flex items-center gap-1 text-[#25334B]">
                          <span className="truncate max-w-[240px]">{selectedEvidence.id}</span>
                          <button
                            type="button"
                            onClick={() => copyMetadata("id", selectedEvidence.id)}
                            className="p-0.5 text-[#69778D] hover:text-[#25334B]"
                            title="Copy Evidence ID"
                          >
                            {copiedMetadataKey === "id" ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                          </button>
                        </div>
                      </div>

                      <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                        <span className="text-[#69778D]">Platform &amp; Provider</span>
                        <span className="font-semibold text-[#203653]">
                          {selectedEvidence.source_type} ({selectedEvidence.provider || selectedEvidence.source_provider || "upload"})
                        </span>
                      </div>

                      <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                        <span className="text-[#69778D]">Category</span>
                        <span className="px-2 py-0.5 rounded bg-[#E8EEF5] text-[#203653] font-semibold text-[10px]">
                          {selectedEvidence.category || selectedEvidence.source_type}
                        </span>
                      </div>

                      {selectedEvidence.original_filename && (
                        <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                          <span className="text-[#69778D]">Original File</span>
                          <span className="text-[#25334B] truncate max-w-[220px]" title={selectedEvidence.original_filename}>
                            {selectedEvidence.original_filename}
                          </span>
                        </div>
                      )}

                      {selectedEvidence.source_external_id && (
                        <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                          <span className="text-[#69778D]">External ID</span>
                          <span className="text-[#25334B] truncate max-w-[220px]">
                            {selectedEvidence.source_external_id}
                          </span>
                        </div>
                      )}

                      <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                        <span className="text-[#69778D]">Author / Owner</span>
                        <span className="text-[#25334B]">
                          {selectedEvidence.source_author_identity || selectedEvidence.author_name || "Internal Document"}
                        </span>
                      </div>

                      {selectedEvidence.source_url && (
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[#69778D]">Source URL</span>
                          <a
                            href={selectedEvidence.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-[#4774A9] hover:underline flex items-center gap-1 truncate max-w-[220px]"
                          >
                            <span className="truncate">{selectedEvidence.source_url}</span>
                            <ExternalLink className="w-3 h-3 shrink-0" />
                          </a>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Document & Processing Details */}
                  <div className="rounded-xl border border-[#DCE3EB] bg-white overflow-hidden shadow-2xs">
                    <div className="px-3.5 py-2 bg-[#F8FAFC] border-b border-[#E2E8F0] font-semibold text-[#25334B] flex items-center gap-1.5 text-[11px] uppercase tracking-wide">
                      <FileCode className="w-3.5 h-3.5 text-[#249E91]" />
                      <span>Document &amp; Extraction Details</span>
                    </div>
                    <div className="p-3.5 space-y-2.5 font-mono text-[11px]">
                      <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                        <span className="text-[#69778D]">Processing Status</span>
                        <span className="px-2 py-0.5 rounded font-semibold text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {selectedEvidence.processing_status || "extracted"}
                        </span>
                      </div>

                      <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                        <span className="text-[#69778D]">Extraction Method</span>
                        <span className="text-[#25334B]">
                          {selectedEvidence.extraction_method || (selectedEvidence.provider === "pdf" ? "PyMuPDF Digital Parsing" : "Direct Ingestion")}
                        </span>
                      </div>

                      {selectedEvidence.file_size_bytes != null && (
                        <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                          <span className="text-[#69778D]">File Size</span>
                          <span className="text-[#25334B]">{formatBytes(selectedEvidence.file_size_bytes)}</span>
                        </div>
                      )}

                      {selectedEvidence.mime_type && (
                        <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                          <span className="text-[#69778D]">MIME Type</span>
                          <span className="text-[#25334B]">{selectedEvidence.mime_type}</span>
                        </div>
                      )}

                      {selectedEvidence.page_count != null && (
                        <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                          <span className="text-[#69778D]">Page Count</span>
                          <span className="text-[#25334B] font-semibold">{selectedEvidence.page_count} pages</span>
                        </div>
                      )}

                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[#69778D]">OCR Processing</span>
                        <span className="text-[#25334B]">
                          {selectedEvidence.ocr_pages_count && selectedEvidence.ocr_pages_count > 0
                            ? `${selectedEvidence.ocr_pages_count} pages OCR scanned (GLM-OCR)`
                            : "0 OCR pages (Digital native vector text)"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Security, ACL & Integrity */}
                  <div className="rounded-xl border border-[#DCE3EB] bg-white overflow-hidden shadow-2xs">
                    <div className="px-3.5 py-2 bg-[#F8FAFC] border-b border-[#E2E8F0] font-semibold text-[#25334B] flex items-center gap-1.5 text-[11px] uppercase tracking-wide">
                      <Lock className="w-3.5 h-3.5 text-amber-600" />
                      <span>Security, ACL &amp; Integrity</span>
                    </div>
                    <div className="p-3.5 space-y-2.5 font-mono text-[11px]">
                      <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                        <span className="text-[#69778D]">ACL Scope</span>
                        <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200 text-[10px] font-semibold">
                          {selectedEvidence.acl_scope || "project_members"}
                        </span>
                      </div>

                      <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                        <span className="text-[#69778D]">Encryption at Rest</span>
                        <span className="text-[#25334B] text-[10.5px]">AES-256-GCM Envelope Encryption</span>
                      </div>

                      <div className="flex items-start justify-between gap-2">
                        <span className="text-[#69778D] shrink-0 mt-0.5">SHA-256 Hash</span>
                        <div className="flex items-center gap-1 text-[#25334B] text-[10px] break-all">
                          <span className="max-w-[230px]">{selectedEvidence.content_hash}</span>
                          <button
                            type="button"
                            onClick={() => copyHash(selectedEvidence.content_hash)}
                            className="p-0.5 text-[#69778D] hover:text-[#25334B] shrink-0"
                            title="Copy SHA-256 Hash"
                          >
                            {copiedHash ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Vector Store & Retrieval Metadata */}
                  <div className="rounded-xl border border-[#DCE3EB] bg-white overflow-hidden shadow-2xs">
                    <div className="px-3.5 py-2 bg-[#F8FAFC] border-b border-[#E2E8F0] font-semibold text-[#25334B] flex items-center gap-1.5 text-[11px] uppercase tracking-wide">
                      <Database className="w-3.5 h-3.5 text-[#315FBA]" />
                      <span>Vector Store &amp; Retrieval Metadata</span>
                    </div>
                    <div className="p-3.5 space-y-2.5 font-mono text-[11px]">
                      <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                        <span className="text-[#69778D]">Indexing Status</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          selectedEvidence.indexing_status === "indexed"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : selectedEvidence.indexing_status === "in_progress"
                            ? "bg-blue-50 text-blue-700 border border-blue-200"
                            : "bg-slate-100 text-slate-700 border border-slate-200"
                        }`}>
                          {selectedEvidence.indexing_status}
                        </span>
                      </div>

                      <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                        <span className="text-[#69778D]">Extracted Chunks</span>
                        <span className="font-semibold text-[#203653]">
                          {selectedEvidence.chunks?.length || 0} chunks
                        </span>
                      </div>

                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[#69778D]">Embedding Model</span>
                        <span className="text-[#25334B]">{selectedEvidence.embedding_model || "nomic-embed-text (768-dim)"}</span>
                      </div>
                    </div>
                  </div>

                  {/* Lifecycle Timestamps */}
                  <div className="rounded-xl border border-[#DCE3EB] bg-white overflow-hidden shadow-2xs">
                    <div className="px-3.5 py-2 bg-[#F8FAFC] border-b border-[#E2E8F0] font-semibold text-[#25334B] flex items-center gap-1.5 text-[11px] uppercase tracking-wide">
                      <Clock className="w-3.5 h-3.5 text-[#69778D]" />
                      <span>Lifecycle Timestamps</span>
                    </div>
                    <div className="p-3.5 space-y-2 font-mono text-[11px]">
                      <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-1.5">
                        <span className="text-[#69778D]">Ingested At</span>
                        <span className="text-[#25334B]">{new Date(selectedEvidence.created_at).toLocaleString()}</span>
                      </div>
                      {selectedEvidence.source_created_at && (
                        <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-1.5">
                          <span className="text-[#69778D]">Source Created</span>
                          <span className="text-[#25334B]">{new Date(selectedEvidence.source_created_at).toLocaleString()}</span>
                        </div>
                      )}
                      {selectedEvidence.extracted_at && (
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[#69778D]">Extracted At</span>
                          <span className="text-[#25334B]">{new Date(selectedEvidence.extracted_at).toLocaleString()}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Additional Metadata JSON attributes */}
                  {selectedEvidence.metadata_json && Object.keys(selectedEvidence.metadata_json).length > 0 && (
                    <div className="rounded-xl border border-[#DCE3EB] bg-white overflow-hidden shadow-2xs">
                      <div className="px-3.5 py-2 bg-[#F8FAFC] border-b border-[#E2E8F0] font-semibold text-[#25334B] flex items-center gap-1.5 text-[11px] uppercase tracking-wide">
                        <Layers className="w-3.5 h-3.5 text-[#69778D]" />
                        <span>Connector Attributes</span>
                      </div>
                      <div className="p-3.5 space-y-2 font-mono text-[11px]">
                        {Object.entries(selectedEvidence.metadata_json).map(([k, v]) => (
                          <div key={k} className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-1.5 last:border-0 last:pb-0">
                            <span className="text-[#69778D]">{k}</span>
                            <span className="text-[#25334B] truncate max-w-[220px]">
                              {typeof v === "object" ? JSON.stringify(v) : String(v)}
                            </span>
                          </div>
                        ))}
                      </div>
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
