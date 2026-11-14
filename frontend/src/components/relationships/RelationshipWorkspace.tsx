"use client";

import React, { useState, useEffect } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Network,
  Search,
  Filter,
  Layers,
  GitBranch,
  ShieldAlert,
  Clock,
  Eye,
  RefreshCw,
} from "lucide-react";
import { api } from "../../lib/api";

interface RelationshipWorkspaceProps {
  projectId: string;
}

export function RelationshipWorkspace({ projectId }: RelationshipWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<
    "graph" | "entities" | "traceability" | "dependencies" | "timeline" | "candidates"
  >("graph");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Graph state
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  // Entities state
  const [entities, setEntities] = useState<Array<Record<string, unknown>>>([]);
  const [entityFilter, setEntityFilter] = useState<string>("");

  // Traceability state
  const [traceChains, setTraceChains] = useState<Array<Record<string, unknown>>>([]);

  // Dependencies state
  const [depGraph, setDepGraph] = useState<Record<string, unknown> | null>(null);

  // Timeline state
  const [timelineEvents, setTimelineEvents] = useState<Array<Record<string, unknown>>>([]);

  // Candidates state
  const [candidates, setCandidates] = useState<Array<Record<string, unknown>>>([]);

  const loadGraphData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const graphData = await api.relationships.getGraph(projectId);
      
      // Calculate circle or grid layout
      const flowNodes = graphData.nodes.map((n, idx) => {
        const angle = (idx / Math.max(1, graphData.nodes.length)) * 2 * Math.PI;
        const radius = 260 + (idx % 3) * 60;
        return {
          id: n.id,
          data: { label: `${n.canonical_name}\n[${n.type}]`, raw: n },
          position: {
            x: 400 + radius * Math.cos(angle),
            y: 300 + radius * Math.sin(angle),
          },
          style: {
            background: n.type === "decision" ? "#fef3c7" : n.type === "person" ? "#e0e7ff" : "#f1f5f9",
            color: "#0f172a",
            border: "1px solid #94a3b8",
            borderRadius: "8px",
            fontSize: "12px",
            padding: "8px 12px",
            textAlign: "center" as const,
            whiteSpace: "pre-wrap" as const,
          },
        };
      });

      const flowEdges = graphData.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.type.toLowerCase().replace(/_/g, " "),
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: "#64748b" },
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (err: unknown) {
      setError((err as Error)?.message || "Failed to load relationship graph");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadGraphData();
  }, [loadGraphData]);

  async function loadTabDetails(tab: typeof activeTab) {
    setActiveTab(tab);
    setError(null);
    try {
      if (tab === "entities" && entities.length === 0) {
        const res = await api.relationships.listEntities(projectId);
        setEntities(res.items || []);
      } else if (tab === "traceability" && traceChains.length === 0) {
        const res = await api.relationships.getTraceability(projectId);
        setTraceChains(res.chains || []);
      } else if (tab === "dependencies" && !depGraph) {
        const res = await api.relationships.getDependencies(projectId);
        setDepGraph(res);
      } else if (tab === "timeline" && timelineEvents.length === 0) {
        const res = await api.relationships.getTimeline(projectId);
        setTimelineEvents(res.items || []);
      } else if (tab === "candidates" && candidates.length === 0) {
        const res = await api.relationships.listIdentityCandidates(projectId);
        setCandidates(res || []);
      }
    } catch (err: unknown) {
      setError((err as Error)?.message || `Failed to load ${tab} data`);
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] bg-slate-50 border border-slate-200 rounded-xl overflow-hidden shadow-sm">
      {/* Tab Navigation */}
      <div className="flex items-center justify-between px-6 py-3 bg-white border-b border-slate-200">
        <div className="flex items-center gap-2">
          <Network className="w-5 h-5 text-indigo-600" />
          <h2 className="font-semibold text-slate-800 text-lg">Knowledge Intelligence & Graph</h2>
        </div>
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-sm font-medium">
          <button
            onClick={() => loadTabDetails("graph")}
            className={`px-3 py-1.5 rounded-md transition-all ${
              activeTab === "graph" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Graph Explorer
          </button>
          <button
            onClick={() => loadTabDetails("entities")}
            className={`px-3 py-1.5 rounded-md transition-all ${
              activeTab === "entities" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Entities
          </button>
          <button
            onClick={() => loadTabDetails("traceability")}
            className={`px-3 py-1.5 rounded-md transition-all ${
              activeTab === "traceability" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Traceability
          </button>
          <button
            onClick={() => loadTabDetails("dependencies")}
            className={`px-3 py-1.5 rounded-md transition-all ${
              activeTab === "dependencies" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Dependencies
          </button>
          <button
            onClick={() => loadTabDetails("timeline")}
            className={`px-3 py-1.5 rounded-md transition-all ${
              activeTab === "timeline" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Timeline
          </button>
          <button
            onClick={() => loadTabDetails("candidates")}
            className={`px-3 py-1.5 rounded-md transition-all ${
              activeTab === "candidates" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Entity Resolution
          </button>
        </div>
      </div>

      {/* Main Tab Panels */}
      <div className="flex-1 relative overflow-hidden">
        {error && (
          <div className="absolute top-4 left-4 right-4 z-50 bg-red-50 text-red-700 border border-red-200 px-4 py-3 rounded-lg text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-800 font-bold">×</button>
          </div>
        )}

        {/* 1. GRAPH EXPLORER */}
        {activeTab === "graph" && (
          <div className="w-full h-full relative">
            {loading ? (
              <div className="flex items-center justify-center h-full text-slate-500">
                <RefreshCw className="w-6 h-6 animate-spin mr-2" /> Loading Knowledge Graph...
              </div>
            ) : nodes.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-500">
                <Network className="w-12 h-12 text-slate-300 mb-2" />
                <p className="font-medium text-slate-700">No Graph Relationships Reconstructed Yet</p>
                <p className="text-sm text-slate-400">Trigger relationship reconstruction in the Evidence or Settings panel.</p>
              </div>
            ) : (
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={(_, node) => setSelectedNode(node.data.raw)}
                fitView
              >
                <Background />
                <Controls />
                <MiniMap />
              </ReactFlow>
            )}

            {/* Selected Node Details Drawer */}
            {selectedNode && (
              <div className="absolute right-4 top-4 bottom-4 w-80 bg-white border border-slate-200 rounded-xl shadow-lg p-5 z-20 overflow-y-auto">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 uppercase">
                    {selectedNode.type}
                  </span>
                  <button onClick={() => setSelectedNode(null)} className="text-slate-400 hover:text-slate-700 text-lg">×</button>
                </div>
                <h3 className="font-semibold text-slate-900 mt-3 text-base">{selectedNode.canonical_name}</h3>
                <p className="text-xs text-slate-500 mt-1">ID: {selectedNode.id}</p>
                <div className="mt-4 space-y-2 text-sm text-slate-600">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Confidence:</span>
                    <span className="font-medium text-slate-800">{(selectedNode.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Resolution:</span>
                    <span className="font-medium text-slate-800 capitalize">{selectedNode.resolution_status}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 2. ENTITY EXPLORER */}
        {activeTab === "entities" && (
          <div className="p-6 h-full overflow-y-auto">
            <div className="flex items-center gap-3 mb-6">
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter entities by name or type..."
                  value={entityFilter}
                  onChange={(e) => setEntityFilter(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {entities
                .filter((e) =>
                  e.canonical_name.toLowerCase().includes(entityFilter.toLowerCase()) ||
                  e.entity_type.toLowerCase().includes(entityFilter.toLowerCase())
                )
                .map((ent) => (
                  <div key={ent.id} className="bg-white p-4 border border-slate-200 rounded-xl shadow-xs hover:border-indigo-300 transition-all">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 uppercase">
                        {ent.entity_type}
                      </span>
                      <span className="text-xs text-slate-400">{(ent.confidence_score * 100).toFixed(0)}% conf</span>
                    </div>
                    <h4 className="font-medium text-slate-900 text-sm">{ent.canonical_name}</h4>
                    {ent.description && <p className="text-xs text-slate-500 mt-2 line-clamp-2">{ent.description}</p>}
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* 3. DECISION TRACEABILITY */}
        {activeTab === "traceability" && (
          <div className="p-6 h-full overflow-y-auto">
            <h3 className="text-base font-semibold text-slate-900 mb-4">Decision-to-Implementation Traceability Chains</h3>
            <div className="space-y-4">
              {traceChains.map((tc) => (
                <div key={tc.id} className="bg-white p-5 border border-slate-200 rounded-xl shadow-xs">
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-semibold text-slate-800 text-sm">{tc.decision_name}</span>
                    <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                      tc.completeness_status === "complete" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" :
                      tc.completeness_status === "partially_traced" ? "bg-amber-50 text-amber-700 border border-amber-200" :
                      "bg-slate-100 text-slate-600"
                    }`}>
                      {tc.completeness_status.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-500 mt-2">
                    <span>Work items: {tc.work_item_count}</span>
                    <span>•</span>
                    <span>Pull requests: {tc.pr_count}</span>
                    <span>•</span>
                    <span>Commits: {tc.commit_count}</span>
                    <span>•</span>
                    <span>Components: {tc.component_count}</span>
                  </div>
                  {tc.missing_links && tc.missing_links.length > 0 && (
                    <div className="mt-3 p-2.5 bg-amber-50 rounded-lg text-xs text-amber-800">
                      <strong>Missing Links:</strong> {tc.missing_links.join(", ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 4. DEPENDENCIES & BLOCKERS */}
        {activeTab === "dependencies" && (
          <div className="p-6 h-full overflow-y-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white p-5 border border-slate-200 rounded-xl">
                <h4 className="font-semibold text-slate-800 text-sm mb-3 flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-red-500" /> Root Blockers
                </h4>
                {depGraph?.root_blockers?.length === 0 ? (
                  <p className="text-xs text-slate-500">No active root blockers identified.</p>
                ) : (
                  <ul className="space-y-2">
                    {depGraph?.root_blockers?.map((b: string, i: number) => (
                      <li key={i} className="text-xs bg-red-50 text-red-700 p-2 rounded-md border border-red-100">
                        {b}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="bg-white p-5 border border-slate-200 rounded-xl">
                <h4 className="font-semibold text-slate-800 text-sm mb-3 flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-amber-500" /> Cycle Detection
                </h4>
                {depGraph?.cycles?.length === 0 ? (
                  <p className="text-xs text-emerald-600 font-medium">✓ Valid Directed Acyclic Graph (DAG): Zero circular dependencies detected.</p>
                ) : (
                  <ul className="space-y-2">
                    {depGraph?.cycles?.map((cyc: string[], idx: number) => (
                      <li key={idx} className="text-xs bg-amber-50 text-amber-800 p-2 rounded-md border border-amber-200">
                        Cycle #{idx + 1}: {cyc.join(" ➔ ")}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 5. TIMELINE */}
        {activeTab === "timeline" && (
          <div className="p-6 h-full overflow-y-auto">
            <h3 className="text-base font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-indigo-600" /> Reconstructed Project Timeline
            </h3>
            <div className="relative pl-6 border-l-2 border-slate-200 space-y-6">
              {timelineEvents.map((evt) => (
                <div key={evt.id} className="relative">
                  <div className="absolute -left-[31px] top-1 w-3.5 h-3.5 rounded-full bg-indigo-500 border-2 border-white shadow-xs" />
                  <div className="bg-white p-4 border border-slate-200 rounded-xl shadow-xs">
                    <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                      <span>{new Date(evt.occurred_at).toLocaleString()}</span>
                      <span className="uppercase font-semibold">{evt.event_type}</span>
                    </div>
                    <h5 className="font-semibold text-slate-900 text-sm">{evt.title}</h5>
                    {evt.summary && <p className="text-xs text-slate-600 mt-1">{evt.summary}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 6. ENTITY RESOLUTION */}
        {activeTab === "candidates" && (
          <div className="p-6 h-full overflow-y-auto">
            <h3 className="text-base font-semibold text-slate-900 mb-4">Identity Merge Candidates (Review Queue)</h3>
            <div className="space-y-4">
              {candidates.length === 0 ? (
                <p className="text-sm text-slate-500">Zero pending identity candidates requiring manual review.</p>
              ) : (
                candidates.map((cand) => (
                  <div key={cand.id} className="bg-white p-5 border border-slate-200 rounded-xl shadow-xs flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                        <span>{cand.left_entity_name || cand.left_entity_id}</span>
                        <span className="text-slate-400">⇄</span>
                        <span>{cand.right_entity_name || cand.right_entity_id}</span>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">
                        Match Score: {(cand.match_score * 100).toFixed(1)}% • Band: {cand.policy_band}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={async () => {
                          await api.relationships.reviewCandidate(projectId, cand.id, "accept");
                          setCandidates((prev) => prev.filter((c) => c.id !== cand.id));
                        }}
                        className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700"
                      >
                        Accept Merge
                      </button>
                      <button
                        onClick={async () => {
                          await api.relationships.reviewCandidate(projectId, cand.id, "reject");
                          setCandidates((prev) => prev.filter((c) => c.id !== cand.id));
                        }}
                        className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-200"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
