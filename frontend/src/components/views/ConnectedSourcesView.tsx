"use client";

import React from "react";
import { PlugZap, Plus, ShieldCheck, CheckCircle2, RefreshCw, KeyRound, AlertCircle } from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

export function ConnectedSourcesView() {
  const {
    activeOrg,
    orgConnections,
    isLoadingSources,
    setIsAddSourceModalOpen,
  } = useLiveApp();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-[#4774A9] uppercase tracking-wider">
            <span>Administration</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#249E91]" />
            <span className="text-[#69778D] font-normal">{activeOrg?.name || "Organisation"}</span>
          </div>
          <h1 className="text-xl font-bold text-[#25334B] mt-1 tracking-tight">
            Connected Sources &amp; Authorisations
          </h1>
          <p className="text-xs text-[#69778D] mt-0.5">
            Manage organization-wide OAuth connections, delegated personal access tokens, and external tool credentials.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsAddSourceModalOpen(true)}
          className="px-4 py-2.5 rounded-lg bg-[#4774A9] hover:bg-[#365F92] text-white text-xs font-semibold flex items-center gap-2 transition-colors shadow-xs shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Connect New Source</span>
        </button>
      </div>

      {/* Security Guidance */}
      <div className="p-4 rounded-xl bg-emerald-50/60 border border-emerald-200 flex items-start gap-3 text-xs text-emerald-950">
        <ShieldCheck className="w-5 h-5 text-[#249E91] shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-semibold">Zero Credential Leakage:</span> All external tokens (GitHub PATs, Jira API keys, OAuth tokens) are encrypted symmetrically at rest in PostgreSQL using AES-256-GCM via <code>TOKEN_ENCRYPTION_KEY</code> and are never returned to client-side code.
        </div>
      </div>

      {/* Connections List */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] shadow-2xs overflow-hidden">
        <div className="px-5 py-3.5 border-b border-[#DCE3EB] bg-[#F4F6F9] flex items-center justify-between text-xs font-semibold text-[#69778D]">
          <span>Source Connection</span>
          <span>Status &amp; Encryption</span>
        </div>

        {orgConnections.length === 0 ? (
          <div className="p-8 text-center">
            <PlugZap className="w-10 h-10 text-[#69778D] opacity-40 mx-auto mb-2" />
            <div className="text-xs font-semibold text-[#25334B]">No Connected Sources</div>
            <p className="text-[11px] text-[#69778D] mt-1">
              Connect GitHub or Jira with read-only credentials to enable project workspace mapping.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[#DCE3EB]">
            {orgConnections.map((conn) => (
              <div
                key={conn.id}
                className="p-4 flex items-center justify-between hover:bg-[#F4F6F9]/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-[#253650] text-white flex items-center justify-center font-bold text-xs">
                    {conn.provider === "github" ? "GH" : "JR"}
                  </div>
                  <div>
                    <div className="font-semibold text-xs text-[#25334B]">
                      {conn.display_name}
                    </div>
                    <div className="text-[10px] text-[#69778D]">
                      Provider: {conn.provider.toUpperCase()} · ID: {conn.id.slice(0, 8)}...
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {conn.status}
                  </span>
                  <span className="text-[11px] text-[#69778D] font-mono">
                    AES-256 Protected
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
