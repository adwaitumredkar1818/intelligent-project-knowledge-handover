"use client";

import React, { useState, useEffect } from "react";
import { X, PlugZap, ShieldAlert, ArrowRight, AlertCircle, Lock } from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

export function ConnectSourceModal() {
  const {
    isAddSourceModalOpen,
    setIsAddSourceModalOpen,
    initialSourceProvider,
    connectSource,
    createMapping,
    triggerSync,
  } = useLiveApp();

  const [provider, setProvider] = useState<"github" | "jira" | "slack">("github");
  const [accountIdentifier, setAccountIdentifier] = useState("");
  const [token, setToken] = useState("");
  const [resourceKey, setResourceKey] = useState("");
  const [resourceName, setResourceName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isAddSourceModalOpen) {
      if (initialSourceProvider) {
        setProvider(initialSourceProvider);
      }
      setError(null);
    }
  }, [isAddSourceModalOpen, initialSourceProvider]);

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
      const cleanResourceKey =
        provider === "github" && resourceKey.includes("/")
          ? resourceKey
              .split("/")
              .map((s) => s.trim())
              .filter(Boolean)
              .join("/")
          : resourceKey.trim();

      // 1. Connect source at organisation level with AES-256-GCM envelope encryption
      const conn = await connectSource(provider, token.trim(), accountIdentifier.trim());

      // 2. Map resource to project workspace
      const externalUrl =
        provider === "github"
          ? `https://github.com/${cleanResourceKey}`
          : provider === "slack"
          ? `https://${accountIdentifier.replace(/^https?:\/\//, "")}/archives/${cleanResourceKey.replace("#", "")}`
          : undefined;

      const mapping = await createMapping({
        source_connection_id: conn.id,
        external_resource_key: cleanResourceKey,
        external_resource_name: resourceName.trim() || cleanResourceKey,
        external_resource_url: externalUrl,
      });

      // 3. Automatically trigger initial sync to retrieve documentation & source records
      if (mapping?.id) {
        try {
          await triggerSync(mapping.id);
        } catch {
          // Sync queued in background worker
        }
      }

      setAccountIdentifier("");
      setToken("");
      setResourceKey("");
      setResourceName("");
      setIsAddSourceModalOpen(false);
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
          <div className="grid grid-cols-3 gap-2.5">
            <button
              type="button"
              onClick={() => setProvider("github")}
              className={`p-2.5 rounded-xl border text-left flex items-center gap-2 transition-all ${
                provider === "github"
                  ? "border-[#4774A9] bg-[#E8EEF5] text-[#25334B] shadow-2xs font-semibold"
                  : "border-[#DCE3EB] bg-white text-[#69778D] hover:bg-[#F4F6F9]"
              }`}
            >
              <div className="w-6 h-6 rounded-md bg-[#25334B] text-white flex items-center justify-center font-bold text-[10px] shrink-0">
                GH
              </div>
              <div className="text-xs truncate">GitHub</div>
            </button>

            <button
              type="button"
              onClick={() => setProvider("jira")}
              className={`p-2.5 rounded-xl border text-left flex items-center gap-2 transition-all ${
                provider === "jira"
                  ? "border-[#4774A9] bg-[#E8EEF5] text-[#25334B] shadow-2xs font-semibold"
                  : "border-[#DCE3EB] bg-white text-[#69778D] hover:bg-[#F4F6F9]"
              }`}
            >
              <div className="w-6 h-6 rounded-md bg-[#0052CC] text-white flex items-center justify-center font-bold text-[10px] shrink-0">
                Jira
              </div>
              <div className="text-xs truncate">Jira</div>
            </button>

            <button
              type="button"
              onClick={() => setProvider("slack")}
              className={`p-2.5 rounded-xl border text-left flex items-center gap-2 transition-all ${
                provider === "slack"
                  ? "border-[#4774A9] bg-[#E8EEF5] text-[#25334B] shadow-2xs font-semibold"
                  : "border-[#DCE3EB] bg-white text-[#69778D] hover:bg-[#F4F6F9]"
              }`}
            >
              <div className="w-6 h-6 rounded-md bg-[#4A154B] text-white flex items-center justify-center font-bold text-[10px] shrink-0">
                Slack
              </div>
              <div className="text-xs truncate">Slack</div>
            </button>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#25334B] mb-1">
              {provider === "github"
                ? "GitHub Username / Account Identifier"
                : provider === "jira"
                ? "Atlassian Account Email"
                : "Slack Workspace Domain / Team ID"}{" "}
              <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={accountIdentifier}
              onChange={(e) => setAccountIdentifier(e.target.value)}
              placeholder={
                provider === "github"
                  ? "e.g. shubham392007-sketch"
                  : provider === "jira"
                  ? "user@company.com"
                  : "e.g. myworkspace.slack.com"
              }
              className="w-full px-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#25334B] mb-1">
              {provider === "github"
                ? "Personal Access Token (PAT)"
                : provider === "jira"
                ? "Atlassian API Token"
                : "Slack Bot User OAuth Token"}{" "}
              <span className="text-rose-500">*</span>
            </label>
            <input
              type="password"
              required
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder={
                provider === "github"
                  ? "ghp_•••••••••••• or github_pat_••••••••••••"
                  : provider === "jira"
                  ? "API token from id.atlassian.com"
                  : "xoxb-••••••••••••-••••••••••••"
              }
              className="w-full px-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
            />
            <div className="text-[11px] text-[#69778D] mt-1">
              {provider === "github"
                ? "Read-only scopes required: repo, read:org. Reads repository README, docs, issues, PRs and commits."
                : provider === "jira"
                ? "Read-only scopes required: read:jira-work. Ingests issues, epics, changelogs, assignees, and status history."
                : "Read-only scopes required: channels:read, channels:history. Ingests discussions and decisions from selected channels."}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#25334B] mb-1">
              {provider === "github"
                ? "Target Repository Identifier (owner/repo)"
                : provider === "jira"
                ? "Target Jira Project Key"
                : "Target Channel Name or Channel ID"}{" "}
              <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={resourceKey}
              onChange={(e) => {
                setResourceKey(e.target.value);
                if (!resourceName) setResourceName(e.target.value);
              }}
              placeholder={
                provider === "github"
                  ? "e.g. shubham392007-sketch/HackMatrix-5.0-MISC02"
                  : provider === "jira"
                  ? "e.g. PAY or PROJ"
                  : "e.g. #architecture, #general, or C01234567"
              }
              className="w-full px-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
            />
            {provider === "github" && (
              <div className="text-[11px] text-[#69778D] mt-1">
                Format must be <span className="font-mono text-[#25334B]">owner/repo</span> (e.g.{" "}
                <span className="font-mono text-[#25334B]">shubham392007-sketch/HackMatrix-5.0-MISC02</span>).
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#25334B] mb-1">
              Display Label (Optional)
            </label>
            <input
              type="text"
              value={resourceName}
              onChange={(e) => setResourceName(e.target.value)}
              placeholder={
                provider === "github"
                  ? "e.g. Payment Service Core"
                  : provider === "jira"
                  ? "e.g. Payments Tracker"
                  : "e.g. Engineering Announcements"
              }
              className="w-full px-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
            />
          </div>

          {/* ACL Boundary & Encryption Notice */}
          <div className="p-3 rounded-lg bg-amber-50/70 border border-amber-200 flex items-start gap-2.5 text-amber-950 text-[11px] leading-relaxed">
            <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Project Membership != Source Access:</span> The backend strictly verifies delegated source access before indexing or answering queries. Users without access to this source cannot read its raw evidence.
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between border-t border-[#DCE3EB]">
            <div className="flex items-center gap-1.5 text-[11px] text-[#249E91] font-semibold">
              <Lock className="w-3.5 h-3.5" />
              <span>AES-256 Envelope Encrypted</span>
            </div>
            <div className="flex items-center gap-3">
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
          </div>
        </form>
      </div>
    </div>
  );
}
