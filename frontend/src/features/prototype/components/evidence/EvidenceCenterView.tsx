"use client";

import React, { useState, useMemo } from "react";
import {
  Database,
  Search,
  Plus,
  UploadCloud,
  FileText,
  Copy,
  Check,
  X,
  ExternalLink,
  Sparkles,
} from "lucide-react";
import { GithubIcon, JiraIcon, SlackIcon } from "../shared/BrandIcons";
import { usePrototype } from "../../context/PrototypeContext";
import type {
  EvidenceProcessingStatus,
  EvidenceRecordType,
} from "../../types";

export function EvidenceCenterView() {
  const {
    evidenceList,
    selectedEvidenceId,
    selectedEvidence,
    setSelectedEvidenceId,
    evidenceFilters,
    setEvidenceFilters,
    setIsAddSourceModalOpen,
    setIsUploadModalOpen,
    addToast,
  } = usePrototype();

  const [copiedRef, setCopiedRef] = useState(false);
  const [activeMobileTab, setActiveMobileTab] = useState<"sources" | "library" | "details">("library");

  // Filtering logic
  const filteredEvidence = useMemo(() => {
    return evidenceList.filter((item) => {
      // 1. Search Query
      if (evidenceFilters.searchQuery.trim()) {
        const q = evidenceFilters.searchQuery.toLowerCase();
        const matchesQ =
          item.name.toLowerCase().includes(q) ||
          item.author.toLowerCase().includes(q) ||
          item.extractedContent.excerpt.toLowerCase().includes(q) ||
          item.sourceReference.toLowerCase().includes(q);
        if (!matchesQ) return false;
      }

      // 2. Provider Filter
      if (
        evidenceFilters.selectedProvider !== "all" &&
        item.source !== evidenceFilters.selectedProvider
      ) {
        return false;
      }

      // 3. Record Type Filter
      if (
        evidenceFilters.selectedRecordType !== "all" &&
        item.recordType !== evidenceFilters.selectedRecordType
      ) {
        return false;
      }

      // 4. Status Filter
      if (
        evidenceFilters.selectedStatus !== "all" &&
        item.status !== evidenceFilters.selectedStatus
      ) {
        return false;
      }

      return true;
    });
  }, [evidenceList, evidenceFilters]);

  // Copy sample reference
  function handleCopyReference(refText: string) {
    navigator.clipboard?.writeText(refText);
    setCopiedRef(true);
    addToast({
      type: "info",
      title: "Reference Copied",
      message: `Copied "${refText}" to clipboard.`,
    });
    setTimeout(() => setCopiedRef(false), 2000);
  }

  return (
    <div className="h-[calc(100vh-5.5rem)] flex flex-col bg-[#F4F6F9] select-none overflow-hidden">
      {/* Mobile Tab Switcher */}
      <div className="lg:hidden bg-white border-b border-[#DCE3EB] px-3 py-2 flex items-center justify-around text-xs shrink-0 font-semibold">
        <button
          type="button"
          onClick={() => setActiveMobileTab("sources")}
          className={`px-3 py-1.5 rounded ${
            activeMobileTab === "sources"
              ? "bg-[#4774A9] text-white"
              : "text-[#69778D] hover:bg-[#F4F6F9]"
          }`}
        >
          1. Sources
        </button>
        <button
          type="button"
          onClick={() => setActiveMobileTab("library")}
          className={`px-3 py-1.5 rounded ${
            activeMobileTab === "library"
              ? "bg-[#4774A9] text-white"
              : "text-[#69778D] hover:bg-[#F4F6F9]"
          }`}
        >
          2. Library ({filteredEvidence.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveMobileTab("details")}
          className={`px-3 py-1.5 rounded ${
            activeMobileTab === "details"
              ? "bg-[#4774A9] text-white"
              : "text-[#69778D] hover:bg-[#F4F6F9]"
          }`}
        >
          3. Details {selectedEvidence ? "•" : ""}
        </button>
      </div>

      {/* 3-Panel Main Layout (Reference 3) */}
      <div className="flex-1 flex overflow-hidden">
        {/* ================================================================= */}
        {/* PANEL 1 — CONNECTED SOURCES (Col 1: Width ~210px-240px) */}
        {/* ================================================================= */}
        <section
          aria-label="Connected sources"
          className={`w-full lg:w-60 bg-white border-r border-[#DCE3EB] flex flex-col shrink-0 overflow-hidden ${
            activeMobileTab === "sources" ? "flex" : "hidden lg:flex"
          }`}
        >
          {/* Panel Header */}
          <div className="p-3 border-b border-[#DCE3EB] bg-[#F4F6F9] flex items-center justify-between">
            <div className="flex items-center gap-1.5 font-bold text-xs text-[#25334B] uppercase tracking-wider">
              <Database className="w-3.5 h-3.5 text-[#4774A9]" />
              <span>Connected Sources</span>
            </div>
            <button
              type="button"
              onClick={() => setIsAddSourceModalOpen(true)}
              className="p-1 text-[#4774A9] hover:bg-[#E8EEF5] rounded transition-colors"
              title="Add or connect another source"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          {/* Sources List */}
          <div className="flex-1 overflow-y-auto p-2.5 space-y-2 text-xs">
            {/* Filter by all */}
            <button
              type="button"
              onClick={() =>
                setEvidenceFilters((prev) => ({ ...prev, selectedProvider: "all" }))
              }
              className={`w-full text-left p-2 rounded border transition-all ${
                evidenceFilters.selectedProvider === "all"
                  ? "border-[#4774A9] bg-[#E8EEF5]/70 font-semibold text-[#4774A9]"
                  : "border-[#DCE3EB] hover:bg-[#F4F6F9] text-[#25334B]"
              }`}
            >
              <div className="flex items-center justify-between">
                <span>All Providers</span>
                <span className="text-[10px] bg-white px-1.5 py-0.2 rounded border border-[#DCE3EB] font-mono">
                  {evidenceList.length}
                </span>
              </div>
            </button>

            {/* GitHub Card */}
            <div
              onClick={() => {
                setEvidenceFilters((prev) => ({ ...prev, selectedProvider: "github" }));
                setActiveMobileTab("library");
              }}
              className={`p-2.5 rounded border transition-all cursor-pointer ${
                evidenceFilters.selectedProvider === "github"
                  ? "border-[#4774A9] bg-[#E8EEF5]/60 ring-1 ring-[#4774A9]"
                  : "border-[#DCE3EB] hover:bg-[#F4F6F9]"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 font-bold text-[#25334B]">
                  <GithubIcon className="w-4 h-4 text-[#25334B]" />
                  <span>GitHub</span>
                </div>
                <span className="w-2 h-2 rounded-full bg-[#269878]" title="Connected" />
              </div>
              <div className="text-[11px] text-[#69778D] mt-1.5 truncate">
                alex-nexora
              </div>
              <div className="text-[10px] text-[#69778D] font-mono mt-0.5">
                nexora-backend, auth-service
              </div>
              <div className="flex items-center justify-between text-[10px] text-[#249E91] font-medium mt-2 pt-1.5 border-t border-[#DCE3EB]/60">
                <span>70 records</span>
                <span>Synced 12m ago</span>
              </div>
            </div>

            {/* Jira Card */}
            <div
              onClick={() => {
                setEvidenceFilters((prev) => ({ ...prev, selectedProvider: "jira" }));
                setActiveMobileTab("library");
              }}
              className={`p-2.5 rounded border transition-all cursor-pointer ${
                evidenceFilters.selectedProvider === "jira"
                  ? "border-[#4774A9] bg-[#E8EEF5]/60 ring-1 ring-[#4774A9]"
                  : "border-[#DCE3EB] hover:bg-[#F4F6F9]"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 font-bold text-[#25334B]">
                  <JiraIcon className="w-4 h-4 text-[#4774A9]" />
                  <span>Jira</span>
                </div>
                <span className="w-2 h-2 rounded-full bg-[#269878]" title="Connected" />
              </div>
              <div className="text-[11px] text-[#69778D] mt-1.5 truncate">
                Nexora Assist Board
              </div>
              <div className="text-[10px] text-[#69778D] font-mono mt-0.5">
                Project Key: NXA
              </div>
              <div className="flex items-center justify-between text-[10px] text-[#249E91] font-medium mt-2 pt-1.5 border-t border-[#DCE3EB]/60">
                <span>64 issues</span>
                <span>Synced 28m ago</span>
              </div>
            </div>

            {/* PDF Card */}
            <div
              onClick={() => {
                setEvidenceFilters((prev) => ({ ...prev, selectedProvider: "pdf" }));
                setActiveMobileTab("library");
              }}
              className={`p-2.5 rounded border transition-all cursor-pointer ${
                evidenceFilters.selectedProvider === "pdf"
                  ? "border-[#4774A9] bg-[#E8EEF5]/60 ring-1 ring-[#4774A9]"
                  : "border-[#DCE3EB] hover:bg-[#F4F6F9]"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 font-bold text-[#25334B]">
                  <FileText className="w-4 h-4 text-[#C65B60]" />
                  <span>PDF Uploads</span>
                </div>
                <span className="text-[10px] font-mono text-[#269878] font-semibold">Ready</span>
              </div>
              <div className="text-[11px] text-[#69778D] mt-1.5 truncate">
                Architecture Specs &amp; ADRs
              </div>
              <div className="flex items-center justify-between text-[10px] text-[#69778D] mt-2 pt-1.5 border-t border-[#DCE3EB]/60">
                <span>14 documents</span>
                <span>PyMuPDF</span>
              </div>
            </div>

            {/* DOCX Card */}
            <div
              onClick={() => {
                setEvidenceFilters((prev) => ({ ...prev, selectedProvider: "docx" }));
                setActiveMobileTab("library");
              }}
              className={`p-2.5 rounded border transition-all cursor-pointer ${
                evidenceFilters.selectedProvider === "docx"
                  ? "border-[#4774A9] bg-[#E8EEF5]/60 ring-1 ring-[#4774A9]"
                  : "border-[#DCE3EB] hover:bg-[#F4F6F9]"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 font-bold text-[#25334B]">
                  <FileText className="w-4 h-4 text-[#4774A9]" />
                  <span>DOCX Uploads</span>
                </div>
                <span className="text-[10px] font-mono text-[#269878] font-semibold">Ready</span>
              </div>
              <div className="text-[11px] text-[#69778D] mt-1.5 truncate">
                Operational Runbooks
              </div>
              <div className="flex items-center justify-between text-[10px] text-[#69778D] mt-2 pt-1.5 border-t border-[#DCE3EB]/60">
                <span>8 documents</span>
                <span>python-docx</span>
              </div>
            </div>

            {/* Slack (Disabled) */}
            <div className="p-2.5 rounded border border-[#DCE3EB] bg-[#F4F6F9]/60 opacity-70">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 font-bold text-[#69778D]">
                  <SlackIcon className="w-4 h-4 text-[#69778D]" />
                  <span>Slack</span>
                </div>
                <span className="text-[9px] bg-[#DCE3EB] text-[#69778D] px-1 rounded uppercase">Disabled</span>
              </div>
              <div className="text-[10px] text-[#69778D] mt-1">
                Gated integration (not enabled in prototype)
              </div>
            </div>
          </div>

          {/* Add Source Action Button */}
          <div className="p-2.5 border-t border-[#DCE3EB] bg-[#F4F6F9]">
            <button
              type="button"
              onClick={() => setIsAddSourceModalOpen(true)}
              className="w-full py-1.5 px-3 rounded bg-white hover:bg-[#E8EEF5] border border-[#DCE3EB] text-[#4774A9] font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-2xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Source Connection</span>
            </button>
          </div>
        </section>

        {/* ================================================================= */}
        {/* PANEL 2 — EVIDENCE LIBRARY (Col 2: Flexible dominant width) */}
        {/* ================================================================= */}
        <section
          aria-label="Evidence library"
          className={`flex-1 bg-white border-r border-[#DCE3EB] flex flex-col min-w-0 overflow-hidden ${
            activeMobileTab === "library" ? "flex" : "hidden lg:flex"
          }`}
        >
          {/* Header & Upload Action */}
          <div className="p-3 border-b border-[#DCE3EB] bg-[#F4F6F9] flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-bold text-xs text-[#25334B] uppercase tracking-wider">
                  Evidence Library
                </h1>
                <span className="text-[11px] text-[#69778D] font-mono">
                  ({filteredEvidence.length} of {evidenceList.length} sample records)
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsUploadModalOpen(true)}
                className="px-3 py-1.5 rounded bg-[#4774A9] hover:bg-[#365F92] text-white font-semibold text-xs flex items-center gap-1.5 transition-colors shadow-xs"
              >
                <UploadCloud className="w-3.5 h-3.5" />
                <span>Upload Document</span>
              </button>
            </div>
          </div>

          {/* Filter Toolbar */}
          <div className="px-3 py-2 border-b border-[#DCE3EB] bg-white flex flex-wrap items-center justify-between gap-2 text-xs">
            {/* Search Input */}
            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 text-[#69778D] absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={evidenceFilters.searchQuery}
                onChange={(e) =>
                  setEvidenceFilters((prev) => ({
                    ...prev,
                    searchQuery: e.target.value,
                  }))
                }
                placeholder="Search evidence..."
                className="w-full pl-8 pr-3 py-1 rounded border border-[#DCE3EB] text-[#25334B] placeholder-[#69778D] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
              />
            </div>

            {/* Filter Dropdowns */}
            <div className="flex items-center gap-2 flex-wrap">
              {/* Type Filter */}
              <select
                value={evidenceFilters.selectedRecordType}
                onChange={(e) =>
                  setEvidenceFilters((prev) => ({
                    ...prev,
                    selectedRecordType: e.target.value as EvidenceRecordType | "all",
                  }))
                }
                className="px-2 py-1 rounded border border-[#DCE3EB] bg-white text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
              >
                <option value="all">All Types</option>
                <option value="pull_request">Pull Requests</option>
                <option value="issue">Issues &amp; Bugs</option>
                <option value="commit">Commits</option>
                <option value="document">Documents</option>
                <option value="task">Tasks</option>
              </select>

              {/* Status Filter */}
              <select
                value={evidenceFilters.selectedStatus}
                onChange={(e) =>
                  setEvidenceFilters((prev) => ({
                    ...prev,
                    selectedStatus: e.target.value as EvidenceProcessingStatus | "all",
                  }))
                }
                className="px-2 py-1 rounded border border-[#DCE3EB] bg-white text-[#25334B] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
              >
                <option value="all">All Statuses</option>
                <option value="extracted">Extracted</option>
                <option value="indexed">Indexed</option>
                <option value="pending_extraction">Pending</option>
              </select>

              {/* Reset filter */}
              {(evidenceFilters.searchQuery ||
                evidenceFilters.selectedProvider !== "all" ||
                evidenceFilters.selectedRecordType !== "all" ||
                evidenceFilters.selectedStatus !== "all") && (
                <button
                  type="button"
                  onClick={() =>
                    setEvidenceFilters({
                      searchQuery: "",
                      selectedProvider: "all",
                      selectedRecordType: "all",
                      selectedStatus: "all",
                      sortBy: "newest",
                    })
                  }
                  className="text-[11px] text-[#4774A9] hover:underline px-1 font-medium"
                >
                  Reset
                </button>
              )}
            </div>
          </div>

          {/* Table Container */}
          <div className="flex-1 overflow-y-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F4F6F9] border-b border-[#DCE3EB] text-[#69778D] uppercase font-bold text-[10px] tracking-wider sticky top-0 z-10">
                <tr>
                  <th className="py-2 px-3">Name</th>
                  <th className="py-2 px-2.5">Source</th>
                  <th className="py-2 px-2.5">Type</th>
                  <th className="py-2 px-2.5">Author</th>
                  <th className="py-2 px-2.5">Time</th>
                  <th className="py-2 px-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#DCE3EB]">
                {filteredEvidence.map((item) => {
                  const isSelected = item.id === selectedEvidenceId;

                  return (
                    <tr
                      key={item.id}
                      onClick={() => {
                        setSelectedEvidenceId(item.id);
                        if (window.innerWidth < 1024) {
                          setActiveMobileTab("details");
                        }
                      }}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? "bg-[#E8EEF5] text-[#25334B] font-semibold border-l-3 border-[#249E91]"
                          : "hover:bg-[#F4F6F9] text-[#25334B]"
                      }`}
                    >
                      {/* Name */}
                      <td className="py-2 px-3 max-w-[240px] xl:max-w-xs truncate">
                        <span className="truncate block" title={item.name}>
                          {item.name}
                        </span>
                      </td>

                      {/* Source */}
                      <td className="py-2 px-2.5 shrink-0">
                        <span className="inline-flex items-center gap-1 font-mono uppercase text-[9px] font-bold px-1.5 py-0.5 rounded bg-[#F4F6F9] border border-[#DCE3EB]">
                          {item.source === "github" && <GithubIcon className="w-2.5 h-2.5" />}
                          {item.source === "jira" && <JiraIcon className="w-2.5 h-2.5 text-[#4774A9]" />}
                          {item.source === "pdf" && <FileText className="w-2.5 h-2.5 text-[#C65B60]" />}
                          {item.source === "docx" && <FileText className="w-2.5 h-2.5 text-[#4774A9]" />}
                          <span>{item.source}</span>
                        </span>
                      </td>

                      {/* Type */}
                      <td className="py-2 px-2.5 capitalize text-[#69778D]">
                        {item.recordType.replace("_", " ")}
                      </td>

                      {/* Author */}
                      <td className="py-2 px-2.5 text-[#25334B] font-medium truncate max-w-[100px]">
                        {item.author}
                      </td>

                      {/* Time */}
                      <td className="py-2 px-2.5 text-[#69778D] font-mono text-[11px] whitespace-nowrap">
                        {item.timestamp}
                      </td>

                      {/* Status */}
                      <td className="py-2 px-3 text-right shrink-0">
                        <span
                          className={`inline-flex items-center px-1.5 py-0.2 rounded text-[9px] font-semibold uppercase ${
                            item.status === "extracted"
                              ? "bg-[#269878]/10 text-[#269878] border border-[#269878]/20"
                              : item.status === "indexed"
                              ? "bg-[#4774A9]/10 text-[#4774A9] border border-[#4774A9]/20"
                              : "bg-[#C48A32]/10 text-[#C48A32] border border-[#C48A32]/20"
                          }`}
                        >
                          {item.status.replace("_", " ")}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {filteredEvidence.length === 0 && (
              <div className="p-12 text-center text-[#69778D]">
                <Database className="w-8 h-8 text-[#69778D]/40 mx-auto mb-2" />
                <p className="font-semibold text-[#25334B]">No matching evidence records</p>
                <p className="text-[11px] mt-1">Adjust search query or filter options above.</p>
              </div>
            )}
          </div>
        </section>

        {/* ================================================================= */}
        {/* PANEL 3 — EVIDENCE DETAILS (Col 3: Width ~260px-340px) */}
        {/* ================================================================= */}
        <section
          aria-label="Evidence details"
          className={`w-full lg:w-80 xl:w-96 bg-[#F4F6F9] flex flex-col shrink-0 overflow-hidden ${
            activeMobileTab === "details" ? "flex" : "hidden lg:flex"
          }`}
        >
          {/* Header */}
          <div className="p-3 border-b border-[#DCE3EB] bg-white flex items-center justify-between">
            <div className="font-bold text-xs text-[#25334B] uppercase tracking-wider flex items-center gap-1.5">
              <span>Evidence Details</span>
              {selectedEvidence && (
                <span className="text-[10px] text-[#249E91] font-mono">
                  [PROVENANCE ACTIVE]
                </span>
              )}
            </div>
            {selectedEvidence && (
              <button
                type="button"
                onClick={() => setSelectedEvidenceId(null)}
                className="p-1 text-[#69778D] hover:text-[#25334B] rounded"
                title="Clear selected evidence"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Details Content */}
          {selectedEvidence ? (
            <div className="flex-1 overflow-y-auto p-3.5 space-y-4 text-xs">
              {/* Evidence Title & Badge */}
              <div className="bg-white p-3 rounded-lg border border-[#DCE3EB] shadow-2xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-mono uppercase font-bold px-1.5 py-0.5 rounded bg-[#E8EEF5] text-[#4774A9]">
                    {selectedEvidence.source} · {selectedEvidence.recordType}
                  </span>
                  <span className="text-[9px] font-mono text-[#269878] font-bold">
                    STATUS: {selectedEvidence.status.toUpperCase()}
                  </span>
                </div>
                <h3 className="font-bold text-sm text-[#25334B] leading-snug">
                  {selectedEvidence.name}
                </h3>
              </div>

              {/* 1. Original Source */}
              <div className="bg-white p-3 rounded-lg border border-[#DCE3EB] shadow-2xs space-y-1.5">
                <div className="text-[10px] uppercase font-bold text-[#69778D] tracking-wider">
                  Original Source Container
                </div>
                <div className="font-semibold text-[#25334B] flex items-center gap-1.5">
                  <span className="truncate">{selectedEvidence.originalSource.containerName}</span>
                </div>
                <div className="text-[11px] text-[#69778D] font-mono truncate">
                  Resource: {selectedEvidence.originalSource.resourceName}
                </div>
                {selectedEvidence.originalSource.externalUrl && (
                  <div className="pt-1">
                    <span className="text-[10px] text-[#4774A9] flex items-center gap-1 font-mono truncate">
                      <ExternalLink className="w-3 h-3 shrink-0" />
                      <span className="truncate">{selectedEvidence.originalSource.externalUrl}</span>
                    </span>
                  </div>
                )}
              </div>

              {/* 2. Author and Timestamp */}
              <div className="bg-white p-3 rounded-lg border border-[#DCE3EB] shadow-2xs space-y-1.5">
                <div className="text-[10px] uppercase font-bold text-[#69778D] tracking-wider">
                  Author &amp; Ingestion Provenance
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-[#69778D] block text-[10px]">Author:</span>
                    <span className="font-semibold text-[#25334B]">
                      {selectedEvidence.author}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#69778D] block text-[10px]">Source Event Time:</span>
                    <span className="font-mono text-[#25334B]">
                      {selectedEvidence.timestamp}
                    </span>
                  </div>
                </div>
                <div className="text-[10px] text-[#69778D] pt-1 border-t border-[#DCE3EB]/60 font-mono">
                  Ingested: {selectedEvidence.ingestedAt}
                </div>
              </div>

              {/* 3. Extracted Content */}
              <div className="bg-white p-3 rounded-lg border border-[#DCE3EB] shadow-2xs space-y-2">
                <div className="flex items-center justify-between">
                  <div className="text-[10px] uppercase font-bold text-[#69778D] tracking-wider">
                    Extracted Content &amp; Excerpt
                  </div>
                  {selectedEvidence.extractedContent.pageNumber && (
                    <span className="text-[10px] font-mono text-[#4774A9]">
                      Page {selectedEvidence.extractedContent.pageNumber}
                    </span>
                  )}
                </div>

                <div className="p-2.5 rounded bg-[#F4F6F9] border border-[#DCE3EB] text-[#25334B] text-xs leading-relaxed font-sans">
                  {selectedEvidence.extractedContent.excerpt}
                </div>

                {selectedEvidence.extractedContent.diffSummary && (
                  <div className="text-[11px] text-[#69778D] font-mono bg-white p-1.5 rounded border border-[#DCE3EB]">
                    Diff: {selectedEvidence.extractedContent.diffSummary}
                  </div>
                )}

                {selectedEvidence.extractedContent.commitSha && (
                  <div className="text-[10px] font-mono text-[#4774A9]">
                    Commit SHA: {selectedEvidence.extractedContent.commitSha}
                  </div>
                )}
              </div>

              {/* 4. Source Reference */}
              <div className="bg-white p-3 rounded-lg border border-[#DCE3EB] shadow-2xs space-y-1.5">
                <div className="text-[10px] uppercase font-bold text-[#69778D] tracking-wider">
                  Source Reference Identifier
                </div>
                <div className="flex items-center justify-between bg-[#F4F6F9] p-2 rounded border border-[#DCE3EB]">
                  <span className="font-mono text-[11px] font-bold text-[#4774A9]">
                    {selectedEvidence.sourceReference}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleCopyReference(selectedEvidence.sourceReference)}
                    className="p-1 text-[#69778D] hover:text-[#4774A9] rounded"
                    title="Copy sample reference"
                  >
                    {copiedRef ? (
                      <Check className="w-3.5 h-3.5 text-[#269878]" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              {/* 5. Related Records */}
              {selectedEvidence.relatedRecords.length > 0 && (
                <div className="bg-white p-3 rounded-lg border border-[#DCE3EB] shadow-2xs space-y-2">
                  <div className="text-[10px] uppercase font-bold text-[#69778D] tracking-wider">
                    Linked Supporting Records ({selectedEvidence.relatedRecords.length})
                  </div>
                  <div className="space-y-1">
                    {selectedEvidence.relatedRecords.map((rel) => (
                      <button
                        key={rel.id}
                        type="button"
                        onClick={() => setSelectedEvidenceId(rel.id)}
                        className="w-full text-left p-1.5 rounded hover:bg-[#F4F6F9] border border-[#DCE3EB]/60 flex items-center justify-between transition-colors group"
                      >
                        <div className="min-w-0 pr-2">
                          <span className="font-semibold text-[#25334B] group-hover:text-[#4774A9] truncate block">
                            {rel.name}
                          </span>
                          <span className="text-[10px] text-[#69778D] uppercase font-mono">
                            {rel.source} · {rel.recordType}
                          </span>
                        </div>
                        <span className="text-xs text-[#4774A9]">→</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* 6. Associated Knowledge (Preview) */}
              {selectedEvidence.associatedKnowledge.length > 0 && (
                <div className="bg-white p-3 rounded-lg border border-[#DCE3EB] shadow-2xs space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="text-[10px] uppercase font-bold text-[#69778D] tracking-wider flex items-center gap-1">
                      <Sparkles className="w-3 h-3 text-[#249E91]" />
                      <span>Associated Knowledge</span>
                    </div>
                    <span className="text-[9px] bg-[#E8EEF5] text-[#4774A9] font-mono px-1 rounded uppercase">
                      PREVIEW
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    {selectedEvidence.associatedKnowledge.map((k) => (
                      <div
                        key={k.id}
                        className="p-2 rounded bg-[#F4F6F9] border border-[#DCE3EB] text-[11px]"
                      >
                        <div className="font-semibold text-[#25334B]">{k.title}</div>
                        <div className="text-[10px] text-[#69778D] mt-0.5">{k.summary}</div>
                        <div className="mt-1 text-[9px] font-mono text-[#249E91]">
                          Confidence: {(k.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Designed Empty State */
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-[#69778D]">
              <div className="w-12 h-12 rounded-full bg-white border border-[#DCE3EB] flex items-center justify-center mb-3 shadow-2xs">
                <Database className="w-6 h-6 text-[#69778D]/60" />
              </div>
              <h4 className="font-bold text-sm text-[#25334B]">No Evidence Record Selected</h4>
              <p className="text-xs mt-1 max-w-xs text-[#69778D] leading-relaxed">
                Click any row in the Evidence Library (Panel 2) to inspect extracted text, provenance, timestamps, and linked records.
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
