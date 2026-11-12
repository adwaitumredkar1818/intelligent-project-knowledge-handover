"use client";

import React, { useState } from "react";
import { X, PlugZap, FileText, AlertCircle, ShieldCheck } from "lucide-react";
import { GithubIcon, JiraIcon, SlackIcon } from "../shared/BrandIcons";
import { usePrototype } from "../../context/PrototypeContext";
import type { SourceProvider } from "../../types";

export function AddSourceModal() {
  const {
    isAddSourceModalOpen,
    setIsAddSourceModalOpen,
    addMockSource,
    addToast,
  } = usePrototype();

  const [selectedProvider, setSelectedProvider] = useState<SourceProvider>("github");
  const [accountIdentifier, setAccountIdentifier] = useState("");

  if (!isAddSourceModalOpen) return null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (selectedProvider === "slack") {
      addToast({
        type: "warning",
        title: "Integration Disabled",
        message: "Slack integration is not enabled in this prototype.",
      });
      return;
    }

    const identifier = accountIdentifier.trim() || `${selectedProvider}-user-demo`;
    addMockSource(selectedProvider, identifier);
    setIsAddSourceModalOpen(false);
    setAccountIdentifier("");
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-source-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs select-none"
    >
      <div className="w-full max-w-lg bg-white rounded-lg border border-[#DCE3EB] shadow-2xl overflow-hidden flex flex-col text-xs">
        {/* Header */}
        <div className="px-4 py-3 bg-[#F4F6F9] border-b border-[#DCE3EB] flex items-center justify-between">
          <div className="flex items-center gap-2 text-[#25334B] font-bold text-sm">
            <PlugZap className="w-4 h-4 text-[#4774A9]" />
            <span id="add-source-modal-title">Connect Organisational Source</span>
          </div>
          <button
            type="button"
            onClick={() => setIsAddSourceModalOpen(false)}
            className="p-1 text-[#69778D] hover:text-[#25334B] rounded"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Prototype Warning Banner */}
        <div className="px-4 py-2 bg-[#C48A32]/10 border-b border-[#C48A32]/20 text-[11px] text-[#C48A32] flex items-start gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold">Prototype preview — no real source authorisation has occurred.</div>
            <div>External credentials and OAuth tokens are never transmitted or stored.</div>
          </div>
        </div>

        {/* Provider Selector */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block font-semibold text-[#25334B] mb-2">
              Select Source Provider
            </label>
            <div className="grid grid-cols-2 gap-2">
              {/* GitHub */}
              <button
                type="button"
                onClick={() => setSelectedProvider("github")}
                className={`p-2.5 rounded-lg border text-left flex items-start gap-2.5 transition-all ${
                  selectedProvider === "github"
                    ? "border-[#4774A9] bg-[#E8EEF5]/60 text-[#25334B] ring-1 ring-[#4774A9]"
                    : "border-[#DCE3EB] hover:bg-[#F4F6F9] text-[#69778D]"
                }`}
              >
                <GithubIcon className="w-5 h-5 text-[#25334B] shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-[#25334B]">GitHub</div>
                  <div className="text-[10px]">Repos, PRs, commits &amp; issues</div>
                </div>
              </button>

              {/* Jira */}
              <button
                type="button"
                onClick={() => setSelectedProvider("jira")}
                className={`p-2.5 rounded-lg border text-left flex items-start gap-2.5 transition-all ${
                  selectedProvider === "jira"
                    ? "border-[#4774A9] bg-[#E8EEF5]/60 text-[#25334B] ring-1 ring-[#4774A9]"
                    : "border-[#DCE3EB] hover:bg-[#F4F6F9] text-[#69778D]"
                }`}
              >
                <JiraIcon className="w-5 h-5 text-[#4774A9] shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-[#25334B]">Jira</div>
                  <div className="text-[10px]">Boards, epics, tasks &amp; bugs</div>
                </div>
              </button>

              {/* PDF Document Store */}
              <button
                type="button"
                onClick={() => setSelectedProvider("pdf")}
                className={`p-2.5 rounded-lg border text-left flex items-start gap-2.5 transition-all ${
                  selectedProvider === "pdf"
                    ? "border-[#4774A9] bg-[#E8EEF5]/60 text-[#25334B] ring-1 ring-[#4774A9]"
                    : "border-[#DCE3EB] hover:bg-[#F4F6F9] text-[#69778D]"
                }`}
              >
                <FileText className="w-5 h-5 text-[#C65B60] shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-[#25334B]">PDF Documents</div>
                  <div className="text-[10px]">PyMuPDF structural extraction</div>
                </div>
              </button>

              {/* Slack (Disabled) */}
              <button
                type="button"
                disabled
                className="p-2.5 rounded-lg border border-[#DCE3EB] bg-[#F4F6F9] text-left flex items-start gap-2.5 opacity-60 cursor-not-allowed"
                title="Slack integration is gated and disabled in this prototype"
              >
                <SlackIcon className="w-5 h-5 text-[#69778D] shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-[#69778D] flex items-center gap-1.5">
                    <span>Slack</span>
                    <span className="text-[9px] bg-[#DCE3EB] text-[#69778D] px-1 rounded uppercase">Disabled</span>
                  </div>
                  <div className="text-[10px] text-[#69778D]">Scope review required</div>
                </div>
              </button>
            </div>
          </div>

          {/* Account Identifier */}
          <div>
            <label className="block font-semibold text-[#25334B] mb-1">
              Account Identifier / Workspace Handle
            </label>
            <input
              type="text"
              value={accountIdentifier}
              onChange={(e) => setAccountIdentifier(e.target.value)}
              placeholder={
                selectedProvider === "github"
                  ? "e.g. nexora-tech or your-github-handle"
                  : selectedProvider === "jira"
                  ? "e.g. nexora-assist.atlassian.net"
                  : "e.g. Core Architecture Store"
              }
              className="w-full px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] placeholder-[#69778D] focus:outline-none focus:ring-1 focus:ring-[#4774A9]"
            />
          </div>

          {/* OAuth Preview Box */}
          <div className="p-3 rounded bg-[#F4F6F9] border border-[#DCE3EB] space-y-1.5">
            <div className="font-semibold text-[#25334B] flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-[#249E91]" />
              <span>Delegated OAuth 2.0 Security Flow (Preview)</span>
            </div>
            <p className="text-[11px] text-[#69778D] leading-relaxed">
              In production, connecting {selectedProvider.toUpperCase()} redirects to the provider&apos;s delegated consent screen. Permissions are tied to the authorizing user account. Project membership does NOT grant source access to unshared repositories.
            </p>
          </div>

          {/* Actions */}
          <div className="pt-2 border-t border-[#DCE3EB] flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsAddSourceModalOpen(false)}
              className="px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] hover:bg-[#F4F6F9] font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded bg-[#4774A9] hover:bg-[#365F92] text-white font-semibold transition-colors shadow-xs"
            >
              Simulate Connection (Demo)
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
