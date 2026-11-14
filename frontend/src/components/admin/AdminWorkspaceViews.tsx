"use client";

import React, { useState, useEffect } from "react";
import {
  ScrollText,
  Search,
  Filter,
  ShieldCheck,
  Calendar,
  User,
  Clock,
  RefreshCw,
  Sliders,
  Database,
  Lock,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import { Button } from "../ui";

export function AuditWorkspaceView() {
  const { activeOrg, user } = useLiveApp();
  const [auditEvents, setAuditEvents] = useState<Array<Record<string, unknown>>>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterType, setFilterType] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  const loadAuditLogs = async (orgId: string) => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem("auth_token");
      const res = await fetch(
        `http://127.0.0.1:8000/api/v1/organisations/${orgId}/audit-events?limit=50`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        setAuditEvents(data.items || []);
      }
    } catch (err) {
      console.error("Failed to load audit logs:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (activeOrg) {
      loadAuditLogs(activeOrg.id);
    }
  }, [activeOrg]);

  const filteredEvents = auditEvents.filter((ev) => {
    if (filterType !== "all" && ev.event_type !== filterType) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (ev.event_type && ev.event_type.toLowerCase().includes(q)) ||
      (ev.actor_email && ev.actor_email.toLowerCase().includes(q)) ||
      (ev.description && ev.description.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-[#4774A9] uppercase tracking-wider">
            <span>Governance &amp; Non-Repudiation</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#249E91]" />
            <span className="text-[#69778D] font-normal">{activeOrg?.name || "Organisation"}</span>
          </div>
          <h1 className="text-xl font-bold text-[#25334B] mt-1 tracking-tight">
            Immutable Audit Trail &amp; System Logs
          </h1>
          <p className="text-xs text-[#69778D] mt-0.5">
            Cryptographic PostgreSQL audit logging of all sensitive operations, verification decisions, and credential changes.
          </p>
        </div>

        <Button
          variant="secondary"
          icon={RefreshCw}
          onClick={() => activeOrg && loadAuditLogs(activeOrg.id)}
          disabled={isLoading}
        >
          Refresh Logs
        </Button>
      </div>

      {/* Security Guidance Banner */}
      <div className="p-4 rounded-xl bg-slate-50 border border-[#DCE3EB] flex items-start gap-3 text-xs text-[#25334B]">
        <ShieldCheck className="w-5 h-5 text-[#249E91] shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-semibold">Append-Only Audit Policy:</span> All logged events in the <code>audit_logs</code> table are immutable and cannot be edited or deleted by users, managers, or platform administrators.
        </div>
      </div>

      {/* Audit Log Table Container */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs space-y-4">
        {/* Search & Filter Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#DCE3EB]">
          <div className="flex items-center gap-2 bg-[#F6F8FC] px-3 py-1.5 rounded-lg border border-[#DCE3EB] flex-1 max-w-sm">
            <Search className="w-4 h-4 text-[#69778D]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by actor, event type, description..."
              className="w-full text-xs bg-transparent focus:outline-none text-[#25334B] placeholder:text-[#69778D]"
            />
          </div>

          <div className="text-xs text-[#69778D]">
            Showing <strong>{filteredEvents.length}</strong> recorded events
          </div>
        </div>

        {/* Audit Table */}
        {filteredEvents.length === 0 ? (
          <div className="p-12 text-center">
            <ScrollText className="w-12 h-12 text-[#69778D] mb-3 mx-auto" />
            <div className="font-bold text-sm text-[#25334B]">No Audit Events Recorded</div>
            <p className="text-xs text-[#69778D] mt-1 max-w-sm mx-auto">
              State-changing events such as document uploads, verification approvals, and handover actions will appear here automatically.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#DCE3EB] text-[#69778D] uppercase font-bold text-[10px]">
                  <th className="pb-2.5">Timestamp</th>
                  <th className="pb-2.5">Event Type</th>
                  <th className="pb-2.5">Actor</th>
                  <th className="pb-2.5">Description</th>
                  <th className="pb-2.5 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#DCE3EB]">
                {filteredEvents.map((ev) => (
                  <tr key={ev.id} className="hover:bg-[#F6F8FC]">
                    <td className="py-2.5 font-mono text-[11px] text-[#69778D]">
                      {new Date(ev.created_at).toLocaleString()}
                    </td>
                    <td className="py-2.5">
                      <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-[#E8EEF5] text-[#4774A9] font-bold">
                        {ev.event_type}
                      </span>
                    </td>
                    <td className="py-2.5 text-[#25334B] font-medium">{ev.actor_email || "System"}</td>
                    <td className="py-2.5 text-[#69778D]">{ev.description || "State-changing operation"}</td>
                    <td className="py-2.5 text-right font-mono text-[10px] text-[#4774A9]">
                      #{ev.id.slice(0, 8)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export function SettingsWorkspaceView() {
  const { activeOrg, user } = useLiveApp();

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
            System &amp; Workspace Settings
          </h1>
          <p className="text-xs text-[#69778D] mt-0.5">
            Manage organization configuration, private storage parameters, and local Ollama inference settings.
          </p>
        </div>
      </div>

      {/* Settings Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Organization Config */}
        <div className="bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs space-y-4">
          <div className="text-xs font-bold text-[#25334B] uppercase tracking-wider pb-2 border-b border-[#DCE3EB]">
            Organization Profile
          </div>
          <div className="space-y-3 text-xs">
            <div>
              <label className="text-[11px] font-semibold text-[#69778D] block mb-1">Organization Name</label>
              <input
                type="text"
                value={activeOrg?.name || ""}
                disabled
                className="w-full px-3 py-2 rounded-lg bg-[#F6F8FC] border border-[#DCE3EB] text-[#25334B]"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-[#69778D] block mb-1">Organization Slug</label>
              <input
                type="text"
                value={activeOrg?.slug || ""}
                disabled
                className="w-full px-3 py-2 rounded-lg bg-[#F6F8FC] border border-[#DCE3EB] text-[#25334B] font-mono text-[11px]"
              />
            </div>
          </div>
        </div>

        {/* Runtime & Inference Config */}
        <div className="bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs space-y-4">
          <div className="text-xs font-bold text-[#25334B] uppercase tracking-wider pb-2 border-b border-[#DCE3EB]">
            Local AI &amp; Inference Pipeline
          </div>
          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-lg border border-[#DCE3EB] bg-[#F6F8FC] flex items-center justify-between">
              <div>
                <div className="font-bold text-[#25334B]">Ollama Runtime</div>
                <div className="text-[11px] text-[#69778D]">Qwen3 8B (Reasoning) + GLM OCR</div>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700">
                Active
              </span>
            </div>

            <div className="p-3 rounded-lg border border-[#DCE3EB] bg-[#F6F8FC] flex items-center justify-between">
              <div>
                <div className="font-bold text-[#25334B]">Embedding Model</div>
                <div className="text-[11px] text-[#69778D]">nomic-embed-text (768 Dimensions)</div>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700">
                Connected
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
