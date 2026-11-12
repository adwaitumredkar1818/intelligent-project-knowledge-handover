"use client";

import React, { useState } from "react";
import {
  PlugZap,
  Plus,
  RefreshCw,
  FileText,
  ShieldCheck,
} from "lucide-react";
import { GithubIcon, JiraIcon, SlackIcon } from "../shared/BrandIcons";
import { usePrototype } from "../../context/PrototypeContext";
import type { SourceConnection } from "../../types";

export function ConnectedSourcesView() {
  const {
    sources,
    triggerSourceSync,
    setIsAddSourceModalOpen,
  } = usePrototype();

  const [inspectingSource, setInspectingSource] = useState<SourceConnection | null>(null);

  return (
    <div className="p-4 sm:p-6 space-y-5 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-[#25334B] tracking-tight flex items-center gap-2">
            <PlugZap className="w-6 h-6 text-[#4774A9]" />
            <span>Connected Organisational Sources</span>
          </h1>
          <p className="text-xs text-[#69778D] mt-1">
            Authorised data connectors, repository mappings, per-user OAuth tokens, and background ingestion schedules.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsAddSourceModalOpen(true)}
          className="px-3.5 py-2 rounded-md bg-[#4774A9] hover:bg-[#365F92] text-xs font-semibold text-white flex items-center gap-2 transition-colors shadow-xs shrink-0"
        >
          <Plus className="w-3.5 h-3.5 text-white" />
          <span>Connect New Source</span>
        </button>
      </div>

      {/* Security Info Card */}
      <div className="p-4 rounded-lg bg-[#E8EEF5] border border-[#DCE3EB] text-xs text-[#25334B] flex items-start gap-3 shadow-2xs">
        <ShieldCheck className="w-5 h-5 text-[#4774A9] shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-bold">
            Mandatory Security Rule: Project Membership != Source Access
          </div>
          <p className="text-[#69778D] leading-relaxed">
            Connected sources preserve personal authorization context. When a member connects an external source with their personal token, that access is not automatically shared with other project members unless explicitly configured or shared.
          </p>
        </div>
      </div>

      {/* Sources Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sources.map((source) => {
          const isGitHub = source.provider === "github";
          const isJira = source.provider === "jira";
          const isPdf = source.provider === "pdf";
          const isDocx = source.provider === "docx";
          const isSlack = source.provider === "slack";

          return (
            <div
              key={source.id}
              className={`bg-white rounded-lg border p-4 shadow-2xs space-y-3 flex flex-col justify-between ${
                source.status === "disabled"
                  ? "border-[#DCE3EB] opacity-75"
                  : "border-[#DCE3EB] hover:border-[#4774A9]/70"
              }`}
            >
              <div className="space-y-3">
                {/* Header */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-9 h-9 rounded-lg bg-[#F4F6F9] border border-[#DCE3EB] flex items-center justify-center shrink-0">
                      {isGitHub && <GithubIcon className="w-5 h-5 text-[#25334B]" />}
                      {isJira && <JiraIcon className="w-5 h-5 text-[#4774A9]" />}
                      {isPdf && <FileText className="w-5 h-5 text-[#C65B60]" />}
                      {isDocx && <FileText className="w-5 h-5 text-[#4774A9]" />}
                      {isSlack && <SlackIcon className="w-5 h-5 text-[#69778D]" />}
                    </div>
                    <div className="min-w-0">
                      <h2 className="font-bold text-[#25334B] text-sm uppercase tracking-wide truncate">
                        {source.provider}
                      </h2>
                      <div className="text-[11px] text-[#69778D] truncate font-mono">
                        {source.accountIdentifier}
                      </div>
                    </div>
                  </div>

                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                      source.status === "connected"
                        ? "bg-[#269878]/10 text-[#269878] border border-[#269878]/20"
                        : source.status === "syncing"
                        ? "bg-[#4774A9]/10 text-[#4774A9] border border-[#4774A9]/20"
                        : "bg-[#DCE3EB] text-[#69778D]"
                    }`}
                  >
                    {source.status}
                  </span>
                </div>

                {/* Details / Scopes */}
                <div className="text-xs space-y-1.5 pt-1">
                  <div className="flex items-center justify-between text-[#69778D]">
                    <span>Connected By:</span>
                    <span className="font-semibold text-[#25334B]">{source.connectedByName}</span>
                  </div>

                  <div className="flex items-center justify-between text-[#69778D]">
                    <span>Last Sync:</span>
                    <span className="font-mono text-[#25334B]">{source.lastSyncedAt || "Never"}</span>
                  </div>

                  {source.scopes.length > 0 && (
                    <div className="pt-1">
                      <span className="text-[10px] uppercase font-bold text-[#69778D] block mb-1">
                        Authorised Scopes:
                      </span>
                      <div className="flex items-center gap-1 flex-wrap">
                        {source.scopes.map((scope) => (
                          <span
                            key={scope}
                            className="text-[10px] font-mono bg-[#F4F6F9] border border-[#DCE3EB] px-1.5 py-0.5 rounded text-[#25334B]"
                          >
                            {scope}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Mappings */}
                  {source.mappings.length > 0 && (
                    <div className="pt-1">
                      <span className="text-[10px] uppercase font-bold text-[#69778D] block mb-1">
                        Mapped Resources ({source.mappings.length}):
                      </span>
                      <div className="space-y-1">
                        {source.mappings.map((m) => (
                          <div
                            key={m.id}
                            className="p-1.5 rounded bg-[#F4F6F9] border border-[#DCE3EB] text-[11px] flex items-center justify-between font-mono"
                          >
                            <span className="truncate">{m.externalResourceName}</span>
                            <span className="text-[#249E91] font-semibold shrink-0">
                              {m.recordsCount} items
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {source.errorMessage && (
                    <div className="p-2 rounded bg-[#C48A32]/10 border border-[#C48A32]/30 text-[#C48A32] text-[11px]">
                      {source.errorMessage}
                    </div>
                  )}
                </div>
              </div>

              {/* Footer Actions */}
              <div className="pt-3 border-t border-[#DCE3EB] flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setInspectingSource(source)}
                  className="text-xs font-semibold text-[#4774A9] hover:underline"
                >
                  View Details &amp; Mappings
                </button>

                {source.status !== "disabled" && (
                  <button
                    type="button"
                    disabled={source.status === "syncing"}
                    onClick={() => triggerSourceSync(source.id)}
                    className="px-2.5 py-1 rounded border border-[#DCE3EB] hover:bg-[#F4F6F9] text-xs font-semibold text-[#25334B] flex items-center gap-1.5 transition-colors disabled:opacity-50"
                  >
                    <RefreshCw
                      className={`w-3.5 h-3.5 text-[#4774A9] ${
                        source.status === "syncing" ? "animate-spin" : ""
                      }`}
                    />
                    <span>{source.status === "syncing" ? "Syncing..." : "Sync Now"}</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Source Details Modal */}
      {inspectingSource && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs select-none"
        >
          <div className="w-full max-w-lg bg-white rounded-lg border border-[#DCE3EB] shadow-2xl p-5 space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-[#DCE3EB] pb-2">
              <div className="font-bold text-sm text-[#25334B] flex items-center gap-2">
                <PlugZap className="w-4 h-4 text-[#4774A9]" />
                <span>
                  Source Details: {inspectingSource.provider.toUpperCase()} (Demo Preview)
                </span>
              </div>
              <button
                type="button"
                onClick={() => setInspectingSource(null)}
                className="text-[#69778D] hover:text-[#25334B]"
              >
                ✕
              </button>
            </div>

            <div className="p-3 rounded bg-[#F4F6F9] border border-[#DCE3EB] space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-[#25334B]">Account Identifier</span>
                <span className="font-mono text-[#4774A9]">{inspectingSource.accountIdentifier}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-bold text-[#25334B]">Connection Status</span>
                <span className="capitalize text-[#269878] font-semibold">
                  {inspectingSource.status}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-bold text-[#25334B]">Shared with Project</span>
                <span className="font-semibold">{inspectingSource.isShared ? "Yes" : "Private to Owner"}</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="text-[10px] uppercase font-bold text-[#69778D] tracking-wider block">
                Mapped Repositories / Project Boards:
              </span>
              {inspectingSource.mappings.map((m) => (
                <div
                  key={m.id}
                  className="p-2 rounded border border-[#DCE3EB] flex items-center justify-between text-xs font-mono"
                >
                  <div>
                    <div className="font-bold text-[#25334B]">{m.externalResourceName}</div>
                    <div className="text-[10px] text-[#69778D]">{m.externalResourceId}</div>
                  </div>
                  <span className="text-[#4774A9] font-bold">{m.recordsCount} records</span>
                </div>
              ))}
            </div>

            <div className="pt-2 border-t border-[#DCE3EB] flex justify-end">
              <button
                type="button"
                onClick={() => setInspectingSource(null)}
                className="px-3.5 py-1.5 rounded bg-[#4774A9] text-white font-semibold hover:bg-[#365F92]"
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
