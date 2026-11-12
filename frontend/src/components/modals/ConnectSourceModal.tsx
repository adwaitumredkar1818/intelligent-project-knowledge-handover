"use client";

import React, { useState } from "react";
import { X, PlugZap, ShieldAlert, ArrowRight, AlertCircle } from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

export function ConnectSourceModal() {
  const { isAddSourceModalOpen, setIsAddSourceModalOpen, connectSource, createMapping } = useLiveApp();
  const [provider, setProvider] = useState<"github" | "jira">("github");
  const [accountIdentifier, setAccountIdentifier] = useState("");
  const [token, setToken] = useState("");
  const [resourceKey, setResourceKey] = useState("");
  const [resourceName, setResourceName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isAddSourceModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accountIdentifier.trim() || !token.trim() || !resourceKey.trim()) {
      setError("Please fill in all required credential and resource fields");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      // 1. Connect source at organisation level
      const conn = await connectSource(provider, token.trim(), accountIdentifier.trim());
      // 2. Map resource to project workspace
      await createMapping({
        source_connection_id: conn.id,
        external_resource_key: resourceKey.trim(),
        external_resource_name: resourceName.trim() || resourceKey.trim(),
        external_resource_url: provider === "github" ? `https://github.com/${resourceKey.trim()}` : undefined,
      });
      setAccountIdentifier("");
      setToken("");
      setResourceKey("");
      setResourceName("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to connect source and map resource");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-2xs p-4">
      <div className="w-full max-w-lg bg-white rounded-xl shadow-xl border border-[#DCE3EB] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-[#F4F6F9] border-b border-[#DCE3EB] flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-bold text-[#25334B]">
            <PlugZap className="w-4 h-4 text-[#4774A9]" />
            <span>Connect Authorised Source</span>
          </div>
          <button
            type="button"
            onClick={() => setIsAddSourceModalOpen(false)}
            className="p-1 rounded text-[#69778D] hover:text-[#25334B]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Provider selector */}
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setProvider("github")}
              className={`p-3 rounded-xl border text-left flex items-center gap-2.5 transition-all ${
                provider === "github"
                  ? "border-[#4774A9] bg-[#E8EEF5] text-[#25334B] shadow-2xs font-semibold"
                  : "border-[#DCE3EB] bg-white text-[#69778D] hover:bg-[#F4F6F9]"
              }`}
            >
              <div className="w-7 h-7 rounded-lg bg-[#25334B] text-white flex items-center justify-center font-bold text-xs">
                GH
              </div>
              <div className="text-xs">GitHub Repository</div>
            </button>

            <button
              type="button"
              onClick={() => setProvider("jira")}
              className={`p-3 rounded-xl border text-left flex items-center gap-2.5 transition-all ${
                provider === "jira"
                  ? "border-[#4774A9] bg-[#E8EEF5] text-[#25334B] shadow-2xs font-semibold"
                  : "border-[#DCE3EB] bg-white text-[#69778D] hover:bg-[#F4F6F9]"
              }`}
            >
              <div className="w-7 h-7 rounded-lg bg-[#0052CC] text-white flex items-center justify-center font-bold text-xs">
                Jira
              </div>
              <div className="text-xs">Jira Project</div>
            </button>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#25334B] mb-1">
              Account Identifier / Username <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={accountIdentifier}
              onChange={(e) => setAccountIdentifier(e.target.value)}
              placeholder={provider === "github" ? "e.g. octocat or company-eng" : "user@company.atlassian.net"}
              className="w-full px-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#25334B] mb-1">
              {provider === "github" ? "Personal Access Token (PAT)" : "Atlassian API Token"} <span className="text-rose-500">*</span>
            </label>
            <input
              type="password"
              required
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="ghp_••••••••••••••••••••••••••••••••••••"
              className="w-full px-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
            />
            <div className="text-[11px] text-[#69778D] mt-1">
              Read-only token scopes required: {provider === "github" ? "repo, read:org" : "read:jira-work"}. Stored encrypted with AES-256-GCM.
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#25334B] mb-1">
              {provider === "github" ? "Target Repository Identifier (owner/repo)" : "Target Jira Project Key"} <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={resourceKey}
              onChange={(e) => {
                setResourceKey(e.target.value);
                if (!resourceName) setResourceName(e.target.value);
              }}
              placeholder={provider === "github" ? "e.g. acme-corp/payment-service" : "PAY"}
              className="w-full px-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#25334B] mb-1">
              Display Label (Optional)
            </label>
            <input
              type="text"
              value={resourceName}
              onChange={(e) => setResourceName(e.target.value)}
              placeholder="e.g. Payment Service Core"
              className="w-full px-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
            />
          </div>

          {/* ACL Boundary Notice */}
          <div className="p-3 rounded-lg bg-amber-50/70 border border-amber-200 flex items-start gap-2.5 text-amber-950 text-[11px] leading-relaxed">
            <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Project Membership != Source Access:</span> The backend strictly verifies delegated source access before indexing or answering queries. Users without access to this source cannot read its raw evidence.
            </div>
          </div>

          <div className="pt-2 flex items-center justify-end gap-3 border-t border-[#DCE3EB]">
            <button
              type="button"
              onClick={() => setIsAddSourceModalOpen(false)}
              className="px-4 py-2 rounded-lg border border-[#DCE3EB] text-xs font-semibold text-[#69778D] hover:bg-[#F4F6F9]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg bg-[#4774A9] hover:bg-[#365F92] text-white text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <span>{isSubmitting ? "Connecting & Verifying..." : "Connect & Map Resource"}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
