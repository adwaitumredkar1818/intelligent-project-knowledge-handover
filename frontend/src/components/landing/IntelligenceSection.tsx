"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Lightbulb,
  UserRound,
  AlertTriangle,
  Network,
  GitPullRequest,
  MessageSquare,
  FileText,
  SquareKanban,
  Sparkles,
  ShieldCheck,
  Link2,
} from "lucide-react";
import { LogoMark } from "../brand";
import { OrganicScene } from "../brand/OrganicScene";

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

const CATEGORIES = [
  {
    key: "Decisions",
    icon: Lightbulb,
    color: "#315FBA",
    accentRgb: "49,95,186",
    body: "Understand what architectural choices were made, who decided them, and the underlying trade-offs.",
    finding: "Decouple settlement from ledger via Kafka event stream",
    meta: "James Okafor · Accepted · 3 evidence sources",
    evidenceIndices: [0, 1, 2],
    confidence: 94,
    verified: true,
  },
  {
    key: "Responsibilities",
    icon: UserRound,
    color: "#299B80",
    accentRgb: "41,155,128",
    body: "Track system ownership, operational duties, active tickets, and unfinished transition items.",
    finding: "Rotate acquirer API credentials and update certificates",
    meta: "Primary: James → Successor: Priya · Due Jun 30",
    evidenceIndices: [3, 2],
    confidence: 86,
    verified: false,
  },
  {
    key: "Risks",
    icon: AlertTriangle,
    color: "#D36D72",
    accentRgb: "211,109,114",
    body: "Identify unresolved failure modes, single points of failure, technical debt, and pending blockers.",
    finding: "Settlement worker has no retry mechanism on acquirer timeouts",
    meta: "High severity · Settlement Service · Manual recovery required",
    evidenceIndices: [1, 3],
    confidence: 83,
    verified: false,
  },
  {
    key: "Dependencies",
    icon: Network,
    color: "#D39B43",
    accentRgb: "211,155,67",
    body: "Map relationships between microservices, database schemas, third-party APIs, and team owners.",
    finding: "SOAP migration is blocked until acquirer credential rotation is complete",
    meta: "Component blocking dependency · Critical path",
    evidenceIndices: [3, 0],
    confidence: 90,
    verified: true,
  },
];

const RAW_EVIDENCE = [
  {
    icon: GitPullRequest,
    source: "atlas-settlement#412",
    text: "Move settlement out of the ledger transaction path to prevent lock contention.",
  },
  {
    icon: MessageSquare,
    source: "#payments-arch",
    text: "“Publish ledger.entry.posted events to Kafka and let settlement worker consume asynchronously.”",
  },
  {
    icon: FileText,
    source: "ADR-007.pdf",
    text: "Status: Accepted. At-least-once delivery with idempotent consumer writes.",
  },
  {
    icon: SquareKanban,
    source: "PAY-1204",
    text: "Quarterly acquirer credential rotation. Blocks gateway cutover PAY-1150.",
  },
];

export function IntelligenceSection() {
  const ref = useReveal<HTMLElement>();
  const [activeCategory, setActiveCategory] = useState(0);
  const current = CATEGORIES[activeCategory] ?? CATEGORIES[0]!;

  return (
    <section
      ref={ref}
      id="intelligence"
      className="ambient-section relative scroll-mt-20 overflow-hidden py-24 sm:py-32"
    >
      {/* 1. Expansive Background Knowledge Network */}
      <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
        <OrganicScene
          variant="network"
          accent={current.accentRgb}
          camZoom={1.38}
          camOffset={[0.24, 0.02]}
          className="h-full w-full opacity-90"
          aria-label="Expansive organic knowledge network representing relationship graphs of project knowledge"
        />
        {/* Soft edge masking and readability gradients */}
        <div
          className="absolute inset-y-0 left-0 w-full sm:w-[54%] lg:w-[44%] z-[1]"
          style={{
            background:
              "linear-gradient(to right, #F6F8FC 0%, rgba(246,248,252,0.94) 40%, rgba(246,248,252,0.7) 75%, transparent 100%)",
          }}
        />
        <div className="absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-[#F6F8FC] to-transparent z-[1]" />
        <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-[#F6F8FC] to-transparent z-[1]" />
      </div>

      <div className="relative z-10 mx-auto w-full max-w-[1240px] px-5 sm:px-8">
        <div className="relative grid gap-14 grid-cols-1 lg:grid-cols-[0.85fr_1.15fr] lg:gap-16">
          {/* Left Column: Category Navigation */}
          <div>
            <div className="reveal">
              <p className="flex items-center gap-2 text-[12.5px] font-semibold uppercase tracking-[0.16em] text-[#8B78C9]">
                <span className="h-px w-6 bg-current opacity-60" />
                Knowledge Intelligence
              </p>
            </div>
            <h2 className="reveal mt-5 text-[34px] font-semibold leading-[1.06] tracking-[-0.035em] text-[#203653] sm:text-[44px] lg:text-[50px]">
              Understand the thinking behind the work.
            </h2>
            <p className="reveal mt-6 text-[17px] leading-[1.65] text-[#56657c]">
              Handover parses authorized project artifacts and reconstructs them into structured knowledge across 8 canonical domains, linking every finding directly to supporting evidence.
            </p>

            {/* Category Buttons */}
            <div className="reveal mt-10 space-y-1.5">
              {CATEGORIES.map((c, i) => (
                <button
                  key={c.key}
                  onClick={() => setActiveCategory(i)}
                  className={`flex w-full items-start gap-4 rounded-2xl border p-4 text-left transition-all duration-300 cursor-pointer ${
                    i === activeCategory
                      ? "tile border-[#D9E1F0] bg-white shadow-card ring-1 ring-[#315FBA]/25"
                      : "border-transparent hover:bg-white/60"
                  }`}
                >
                  <span
                    className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl"
                    style={{ background: `${c.color}15`, color: c.color }}
                  >
                    <c.icon className="size-4" />
                  </span>
                  <span>
                    <span className="block text-[17px] font-semibold text-[#203653]">
                      {c.key}
                    </span>
                    <span
                      className={`block overflow-hidden text-[14px] leading-relaxed text-[#718096] transition-all duration-300 ${
                        i === activeCategory
                          ? "mt-1 max-h-24 opacity-100"
                          : "max-h-0 opacity-0"
                      }`}
                    >
                      {c.body}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Right Column: Evidence -> Reconstructed Finding Card */}
          <div className="reveal relative self-center rounded-[24px] border border-[#D9E1F0] bg-white/90 p-5 shadow-card backdrop-blur-xs sm:p-7">
            {/* Illustrative Architecture Preview Banner */}
            <div className="mb-5 flex flex-wrap items-center justify-between gap-2 border-b border-[#D9E1F0] pb-3">
              <span className="font-mono text-[11px] uppercase tracking-wider text-[#718096]">
                Architecture Preview · Sample Data
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 font-mono text-[10px] font-semibold text-slate-500">
                Illustrative demonstration · Not live data
              </span>
            </div>

            <div className="grid gap-6 sm:grid-cols-[1fr_40px_1fr] sm:items-center">
              {/* Raw Evidence List */}
              <div className="space-y-2.5">
                <p className="font-mono text-[11px] font-medium text-[#718096]">
                  RAW EVIDENCE CHUNKS
                </p>
                {RAW_EVIDENCE.map((f, i) => (
                  <div
                    key={f.source}
                    className={`rounded-xl border bg-white p-3 transition-all duration-300 ${
                      current.evidenceIndices.includes(i)
                        ? "border-[#7997BE]/80 shadow-xs ring-1 ring-[#7997BE]/20"
                        : "border-[#D9E1F0] opacity-45"
                    }`}
                  >
                    <p className="flex items-center gap-1.5 font-mono text-[11px] text-[#718096]">
                      <f.icon className="size-3 text-[#315FBA]" />
                      <span>{f.source}</span>
                    </p>
                    <p className="mt-1 text-[12px] leading-snug text-[#3e5373]">
                      {f.text}
                    </p>
                  </div>
                ))}
              </div>

              {/* Connecting Brand Anchor with animated stream */}
              <div className="hidden h-full flex-col items-center justify-center gap-2 sm:flex" aria-hidden="true">
                <span className="relative h-16 w-px bg-[#D9E1F0] overflow-hidden">
                  <span className="absolute inset-0 bg-gradient-to-b from-transparent via-[#315FBA] to-transparent animate-beam" />
                </span>
                <span className="flex size-10 items-center justify-center rounded-xl border border-[#D9E1F0] bg-white shadow-xs transition-transform duration-300 hover:scale-105">
                  <LogoMark size={22} />
                </span>
                <span className="relative h-16 w-px bg-[#D9E1F0] overflow-hidden">
                  <span className="absolute inset-0 bg-gradient-to-t from-transparent via-[#299B80] to-transparent animate-beam" style={{ animationDelay: "1.2s" }} />
                </span>
              </div>

              {/* Reconstructed Finding Box */}
              <div key={activeCategory} className="animate-fade space-y-3">
                <p className="font-mono text-[11px] font-medium text-[#718096]">
                  STRUCTURED FINDING
                </p>
                <div className="rounded-2xl border border-[#D9E1F0] bg-white p-4.5 shadow-lift">
                  <p
                    className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.1em]"
                    style={{ color: current.color }}
                  >
                    <current.icon className="size-3.5" />
                    <span>{current.key.replace(/s$/, "")}</span>
                  </p>
                  <p className="mt-2 text-[15px] font-semibold leading-snug text-[#203653]">
                    {current.finding}
                  </p>
                  <p className="mt-1 text-[12px] text-[#718096]">{current.meta}</p>

                  <div className="mt-4 flex flex-wrap items-center gap-1.5">
                    <span className="inline-flex items-center gap-1 rounded-md border border-dashed border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700">
                      <Sparkles className="size-3" />
                      AI {current.confidence}%
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${
                        current.verified
                          ? "bg-teal-50 text-teal-700 ring-teal-600/20"
                          : "bg-amber-50 text-amber-700 ring-amber-600/20"
                      }`}
                    >
                      {current.verified ? (
                        <>
                          <ShieldCheck className="size-3" />
                          Verified
                        </>
                      ) : (
                        "Needs Review"
                      )}
                    </span>
                  </div>
                </div>

                <div className="rounded-xl border border-dashed border-[#D9E1F0] p-3 text-[12px] text-[#718096] bg-[#F6F8FC]/50">
                  <Link2 className="mr-1.5 inline size-3 text-[#315FBA]" />
                  Linked to {current.evidenceIndices.length} raw evidence records with provenance hash
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
