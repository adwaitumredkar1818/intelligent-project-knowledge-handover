"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  ShieldCheck,
  CircleAlert,
  Link2,
  ArrowRight,
} from "lucide-react";
import { LogoMark } from "../brand";
import { useLiveApp } from "../../context/LiveAppContext";
import { useRouter } from "next/navigation";

function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("is-in");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    el.querySelectorAll(".reveal").forEach((n) => io.observe(n));
    return () => io.disconnect();
  }, []);
  return ref;
}

type GraphNode = {
  id: string;
  x: number;
  y: number;
  kind: "Decision" | "Task" | "Risk" | "Person" | "Component" | "Evidence";
  label: string;
  desc: string;
  conf?: number;
  ver?: "Verified" | "Needs review" | "Conflicting";
  ev?: string[];
};

const KIND_COLORS: Record<GraphNode["kind"], string> = {
  Decision: "#315FBA",
  Task: "#299B80",
  Risk: "#D36D72",
  Person: "#7997BE",
  Component: "#203653",
  Evidence: "#A0AEC0",
};

const GRAPH_NODES: GraphNode[] = [
  {
    id: "d1",
    x: 360,
    y: 210,
    kind: "Decision",
    label: "Decouple settlement via Kafka",
    desc: "Ledger publishes ledger.entry.posted events; the settlement worker consumes them asynchronously with idempotent writes.",
    conf: 94,
    ver: "Verified",
    ev: ["atlas-settlement#412", "#payments-arch thread", "ADR-007.pdf"],
  },
  {
    id: "d2",
    x: 380,
    y: 62,
    kind: "Decision",
    label: "Idempotency keys required",
    desc: "POST /payments and /refunds reject requests without an Idempotency-Key in strict mode.",
    conf: 91,
    ver: "Verified",
    ev: ["atlas-gateway@a3f9c21"],
  },
  {
    id: "p1",
    x: 150,
    y: 96,
    kind: "Person",
    label: "James Okafor",
    desc: "Staff Backend Engineer. Outgoing technical owner of the settlement service and ledger schema migrations.",
  },
  {
    id: "e1",
    x: 112,
    y: 232,
    kind: "Evidence",
    label: "PR #412",
    desc: "Introduce Kafka-based asynchronous settlement event consumer. Merged Mar 14.",
  },
  {
    id: "e2",
    x: 196,
    y: 352,
    kind: "Evidence",
    label: "ADR-007.pdf",
    desc: "Architecture decision record: event-driven settlement decoupling. Status: Accepted.",
  },
  {
    id: "c1",
    x: 586,
    y: 104,
    kind: "Component",
    label: "Settlement Worker",
    desc: "Consumes ledger events from Kafka and batches settlement payouts to connected acquirers.",
  },
  {
    id: "c2",
    x: 622,
    y: 246,
    kind: "Component",
    label: "Kafka Cluster",
    desc: "Primary distributed event backbone. Partition replication factor set to 3.",
  },
  {
    id: "r1",
    x: 548,
    y: 364,
    kind: "Risk",
    label: "No retry on timeouts",
    desc: "A 9-minute acquirer outage failed batches for 14 merchants; recovery required manual database intervention.",
    conf: 83,
    ver: "Conflicting",
    ev: ["#incidents thread"],
  },
  {
    id: "t1",
    x: 368,
    y: 392,
    kind: "Task",
    label: "Add timeout retries",
    desc: "Implement exponential backoff and dead-letter queue for acquirer timeouts before peak volume.",
    conf: 82,
    ver: "Needs review",
    ev: ["#incidents thread", "PAY-1182"],
  },
];

const GRAPH_EDGES = [
  ["d1", "p1"],
  ["d1", "e1"],
  ["d1", "e2"],
  ["d1", "c1"],
  ["d1", "c2"],
  ["d1", "d2"],
  ["c1", "r1"],
  ["r1", "t1"],
  ["t1", "d1"],
  ["p1", "e1"],
  ["d2", "c1"],
];

export function ExplorerSection() {
  const ref = useReveal<HTMLElement>();
  const [selectedId, setSelectedId] = useState("d1");
  const { user } = useLiveApp();
  const router = useRouter();

  const selectedNode =
    GRAPH_NODES.find((x) => x.id === selectedId) || GRAPH_NODES[0]!;

  const relatedNodes = GRAPH_EDGES.filter((e) => e.includes(selectedId))
    .map((e) =>
      GRAPH_NODES.find((x) => x.id === (e[0] === selectedId ? e[1] : e[0]))
    )
    .filter((x): x is GraphNode => Boolean(x));

  const relIdSet = new Set(relatedNodes.map((r) => r.id));

  const handleAction = () => {
    if (user) {
      router.push("/relationships");
    } else {
      router.push("/signup");
    }
  };

  return (
    <section
      ref={ref}
      id="explorer"
      className="ambient-section scroll-mt-20 bg-[#f1f4fa] py-24 sm:py-32"
    >
      <div className="mx-auto w-full max-w-[1240px] px-5 sm:px-8">
        {/* Section Header */}
        <div className="mx-auto max-w-3xl text-center">
          <div className="reveal flex justify-center">
            <p className="flex items-center gap-2 text-[12.5px] font-semibold uppercase tracking-[0.16em] text-[#315FBA]">
              <span className="h-px w-6 bg-current opacity-60" />
              Knowledge Explorer
            </p>
          </div>
          <h2 className="reveal mt-5 text-[34px] font-semibold leading-[1.06] tracking-[-0.035em] text-[#203653] sm:text-[44px] lg:text-[50px]">
            Every decision has a reason. Every task has a story.
          </h2>
          <p className="reveal mx-auto mt-6 max-w-2xl text-[17px] leading-[1.65] text-[#56657c]">
            Explore how team members, architectural decisions, technical components, risks, and evidence connect across the project knowledge graph.
          </p>
        </div>

        {/* Interactive Explorer Container */}
        <div className="reveal mt-14 overflow-hidden rounded-[22px] border border-[#D9E1F0] bg-white shadow-pop">
          {/* Header Bar */}
          <div className="flex items-center gap-2.5 border-b border-[#D9E1F0] px-4 py-3 bg-white min-w-0">
            <LogoMark size={18} />
            <span className="truncate text-[13px] font-semibold text-[#203653]">
              Atlas Payments Platform
            </span>
            <span className="hidden sm:inline text-slate-300">/</span>
            <span className="hidden sm:inline text-[13px] text-[#718096]">
              Knowledge Explorer
            </span>
            <span className="hidden min-[480px]:inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 font-mono text-[10px] font-medium text-slate-500">
              Illustrative Demo Preview
            </span>

            {/* Category Badges */}
            <div className="ml-auto hidden items-center gap-3 sm:flex">
              {(Object.keys(KIND_COLORS) as GraphNode["kind"][]).map((k) => (
                <span key={k} className="flex items-center gap-1.5 text-[11.5px] text-[#718096]">
                  <span
                    className="size-2 rounded-full"
                    style={{ background: KIND_COLORS[k] }}
                  />
                  <span>{k}</span>
                </span>
              ))}
            </div>
          </div>

          {/* Graph View & Detail Pane */}
          <div className="grid md:grid-cols-[1fr_330px]">
            {/* SVG Interactive Canvas */}
            <div className="relative hidden border-r border-[#D9E1F0] md:block bg-[#F8FAFD]">
              <div className="absolute inset-0 dot-grid opacity-75" />
              <svg
                viewBox="0 0 720 440"
                className="relative h-full w-full"
                role="img"
                aria-label="Knowledge graph interactive view"
              >
                {/* Edges */}
                {GRAPH_EDGES.map(([a, b]) => {
                  const nodeA = GRAPH_NODES.find((x) => x.id === a);
                  const nodeB = GRAPH_NODES.find((x) => x.id === b);
                  if (!nodeA || !nodeB) return null;
                  const isActive = a === selectedId || b === selectedId;
                  return (
                    <line
                      key={`${a}-${b}`}
                      x1={nodeA.x}
                      y1={nodeA.y}
                      x2={nodeB.x}
                      y2={nodeB.y}
                      stroke={isActive ? "#315FBA" : "#DCE3EF"}
                      strokeWidth={isActive ? 2 : 1}
                      strokeDasharray={isActive ? "4 4" : undefined}
                      className={`transition-all duration-300 ${isActive ? "animate-stream-flow" : ""}`}
                    />
                  );
                })}

                {/* Nodes */}
                {GRAPH_NODES.map((g) => {
                  const isSelected = g.id === selectedId;
                  const isRelated = relIdSet.has(g.id);
                  const opacity = isSelected || isRelated ? 1 : 0.45;
                  const color = KIND_COLORS[g.kind];

                  return (
                    <g
                      key={g.id}
                      onClick={() => setSelectedId(g.id)}
                      className="cursor-pointer"
                      opacity={opacity}
                      style={{ transition: "opacity .3s ease" }}
                    >
                      {isSelected && (
                        <circle
                          cx={g.x}
                          cy={g.y}
                          r="24"
                          fill={color}
                          opacity="0.12"
                        />
                      )}
                      <circle
                        cx={g.x}
                        cy={g.y}
                        r={isSelected ? 11 : 8}
                        fill={isSelected ? color : "white"}
                        stroke={color}
                        strokeWidth="2.5"
                        style={{ transition: "all .3s ease" }}
                      />
                      <rect
                        x={g.x - g.label.length * 3.4 - 8}
                        y={g.y + 15}
                        width={g.label.length * 6.8 + 16}
                        height="20"
                        rx="6"
                        fill="white"
                        stroke={isSelected ? color : "#E3E9F3"}
                        className="shadow-xs"
                      />
                      <text
                        x={g.x}
                        y={g.y + 29}
                        textAnchor="middle"
                        fontSize="11.5"
                        fontWeight={isSelected ? 700 : 500}
                        fill="#203653"
                        fontFamily="var(--font-sans), sans-serif"
                      >
                        {g.label}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>

            {/* Selected Node Details Drawer */}
            <aside key={selectedId} className="animate-fade bg-white p-5 sm:p-6">
              <p
                className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em]"
                style={{ color: KIND_COLORS[selectedNode.kind] }}
              >
                <span
                  className="size-2 rounded-full"
                  style={{ background: KIND_COLORS[selectedNode.kind] }}
                />
                <span>{selectedNode.kind}</span>
              </p>
              <h3 className="mt-2 text-[18px] font-semibold leading-snug tracking-[-0.02em] text-[#203653]">
                {selectedNode.label}
              </h3>
              <p className="mt-2 text-[13px] leading-relaxed text-[#718096]">
                {selectedNode.desc}
              </p>

              {selectedNode.conf && (
                <div className="mt-5 grid grid-cols-2 gap-2">
                  <div className="rounded-xl border border-dashed border-indigo-200 bg-indigo-50/50 p-2.5">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-indigo-500">
                      AI confidence
                    </p>
                    <p className="mt-1 text-[18px] font-semibold text-indigo-700">
                      {selectedNode.conf}%
                    </p>
                  </div>
                  <div
                    className={`rounded-xl border p-2.5 ${
                      selectedNode.ver === "Verified"
                        ? "border-teal-200 bg-teal-50/50"
                        : selectedNode.ver === "Conflicting"
                        ? "border-red-200 bg-red-50/40"
                        : "border-amber-200 bg-amber-50/40"
                    }`}
                  >
                    <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">
                      Verification
                    </p>
                    <p
                      className={`mt-1 flex items-center gap-1 text-[12px] font-semibold ${
                        selectedNode.ver === "Verified"
                          ? "text-teal-700"
                          : selectedNode.ver === "Conflicting"
                          ? "text-red-700"
                          : "text-amber-700"
                      }`}
                    >
                      {selectedNode.ver === "Verified" ? (
                        <ShieldCheck className="size-3.5" />
                      ) : (
                        <CircleAlert className="size-3.5" />
                      )}
                      <span>{selectedNode.ver}</span>
                    </p>
                  </div>
                </div>
              )}

              {/* Related Entities */}
              <p className="mb-2 mt-5 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">
                Related Entities · {relatedNodes.length}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {relatedNodes.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => setSelectedId(r.id)}
                    className="flex items-center gap-1.5 rounded-full border border-[#D9E1F0] px-2.5 py-1 text-[11.5px] text-[#203653] transition hover:border-[#315FBA] cursor-pointer"
                  >
                    <span
                      className="size-1.5 rounded-full"
                      style={{ background: KIND_COLORS[r.kind] }}
                    />
                    <span>{r.label}</span>
                  </button>
                ))}
              </div>

              {/* Supporting Evidence */}
              {selectedNode.ev && (
                <>
                  <p className="mb-2 mt-5 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">
                    Supporting Evidence
                  </p>
                  <ul className="space-y-1.5">
                    {selectedNode.ev.map((e) => (
                      <li
                        key={e}
                        className="flex items-center gap-2 rounded-lg border border-[#D9E1F0] px-2.5 py-1.5 font-mono text-[11px] text-[#203653]"
                      >
                        <Link2 className="size-3 text-[#315FBA]" />
                        <span>{e}</span>
                      </li>
                    ))}
                  </ul>
                </>
              )}

              <button
                onClick={handleAction}
                className="mt-6 flex h-9.5 w-full items-center justify-center gap-2 rounded-[10px] border border-[#D9E1F0] text-[12.5px] font-semibold text-[#203653] transition hover:bg-[#F6F8FC] cursor-pointer"
              >
                <span>Inspect in Relationship Explorer</span>
                <ArrowRight className="size-3.5 text-[#315FBA]" />
              </button>
            </aside>
          </div>
        </div>

        <p className="mt-4 text-center text-[13px] text-[#718096] md:hidden">
          Tap related items to navigate through the knowledge graph.
        </p>
      </div>
    </section>
  );
}
