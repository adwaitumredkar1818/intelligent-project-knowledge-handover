"use client";

import React, { useEffect, useRef, useState } from "react";
import { ArrowRight, Check, ShieldCheck } from "lucide-react";

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

export function HandoversSection() {
  const ref = useReveal<HTMLElement>();
  const [activeTab, setActiveTab] = useState("Overview");

  const tabs = [
    "Overview",
    "Responsibilities",
    "Decisions",
    "Tasks",
    "Risks",
    "Evidence",
    "Report",
  ];

  return (
    <section ref={ref} id="handovers" className="scroll-mt-20 py-24 sm:py-32">
      <div className="mx-auto w-full max-w-[1240px] px-5 sm:px-8">
        <div className="grid items-center gap-14 grid-cols-1 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
          {/* Left Narrative Column */}
          <div>
            <div className="reveal">
              <p className="flex items-center gap-2 text-[12.5px] font-semibold uppercase tracking-[0.16em] text-[#315FBA]">
                <span className="h-px w-6 bg-current opacity-60" />
                Structured Handovers
              </p>
            </div>
            <h2 className="reveal mt-5 text-[34px] font-semibold leading-[1.06] tracking-[-0.035em] text-[#203653] sm:text-[44px] lg:text-[50px]">
              Make every transition a continuation, not a restart.
            </h2>
            <p className="reveal mt-6 text-[17px] leading-[1.65] text-[#56657c]">
              Bring verified project context together into an auditable transition package, ensuring successors understand architectural decisions, active responsibilities, and technical risks from day one.
            </p>

            <ul className="reveal mt-9 space-y-5 border-l-2 border-[#D9E1F0] pl-6">
              {[
                {
                  title: "Built from empirical evidence",
                  body: "Every section is assembled directly from verified project findings, with original commits and threads one click away.",
                },
                {
                  title: "Reviewed by the people who know",
                  body: "Outgoing members confirm, adjust, or reject findings. Designated project managers review and approve before publishing.",
                },
                {
                  title: "Actionable from day one",
                  body: "Provides incoming team members a clear path through system architecture, open blockers, and immediate priorities.",
                },
              ].map((item) => (
                <li key={item.title}>
                  <p className="text-[16px] font-semibold text-[#203653]">
                    {item.title}
                  </p>
                  <p className="mt-1 text-[14px] leading-relaxed text-[#718096]">
                    {item.body}
                  </p>
                </li>
              ))}
            </ul>
          </div>

          {/* Right Handover Package Mockup */}
          <div className="reveal relative">
            <div
              className="absolute -inset-6 rounded-[32px] opacity-75 pointer-events-none"
              style={{
                background:
                  "radial-gradient(ellipse at 70% 20%, rgba(165,160,217,0.25), transparent 60%)",
              }}
            />
            <div className="relative overflow-hidden rounded-[20px] border border-[#D9E1F0] bg-white shadow-pop">
              {/* Package Header */}
              <div className="border-b border-[#D9E1F0] p-5 sm:p-6 bg-white">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[11.5px] font-medium text-[#718096]">
                    HO-1042
                  </span>
                  <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-600/20">
                    Pending Review
                  </span>
                  <span className="rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 font-mono text-[10px] font-medium text-slate-500">
                    Demonstration Preview
                  </span>
                </div>

                <div className="mt-2.5 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                  <div className="min-w-0">
                    <h3 className="text-[18px] sm:text-[20px] font-semibold tracking-[-0.02em] text-[#203653] truncate sm:whitespace-normal">
                      Atlas Payments Platform
                    </h3>
                    <div className="mt-3 flex items-center gap-2.5 text-[12.5px]">
                      <span className="flex size-7 items-center justify-center rounded-full bg-[#203653]/10 text-[10px] font-bold text-[#203653]">
                        JO
                      </span>
                      <span className="font-medium text-[#203653]">James Okafor</span>
                      <ArrowRight className="size-3.5 text-[#315FBA]" />
                      <span className="flex size-7 items-center justify-center rounded-full bg-blue-50 text-[10px] font-bold text-[#315FBA]">
                        PN
                      </span>
                      <span className="font-medium text-[#203653]">Priya Nair</span>
                    </div>
                  </div>

                  {/* Circular Completion Ring */}
                  <div className="relative size-16 shrink-0">
                    <svg viewBox="0 0 64 64" className="-rotate-90">
                      <circle
                        cx="32"
                        cy="32"
                        r="27"
                        fill="none"
                        stroke="#EDF1F8"
                        strokeWidth="5"
                      />
                      <circle
                        cx="32"
                        cy="32"
                        r="27"
                        fill="none"
                        stroke="#299B80"
                        strokeWidth="5"
                        strokeLinecap="round"
                        strokeDasharray={`${0.86 * 170} 170`}
                      />
                    </svg>
                    <span className="absolute inset-0 flex items-center justify-center text-[13px] font-bold text-[#203653]">
                      86%
                    </span>
                  </div>
                </div>

                {/* Workflow Stage Bars */}
                <div className="mt-5 grid grid-cols-6 gap-1.5">
                  {["Draft", "Verify", "Review", "Approve", "Publish", "Ack"].map(
                    (stage, i) => (
                      <div key={stage}>
                        <div
                          className={`h-1.5 rounded-full relative overflow-hidden ${
                            i < 2
                              ? "bg-[#299B80]"
                              : i === 2
                              ? "bg-[#315FBA]"
                              : "bg-slate-200"
                          }`}
                        >
                          {i === 2 && (
                            <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/80 to-transparent animate-beam" />
                          )}
                        </div>
                        <p
                          className={`mt-1.5 hidden text-[10.5px] font-medium sm:block ${
                            i === 2 ? "text-[#315FBA] font-semibold" : "text-slate-400"
                          }`}
                        >
                          {stage}
                        </p>
                      </div>
                    )
                  )}
                </div>
              </div>

              {/* Navigation Tabs */}
              <div className="flex gap-5 overflow-x-auto border-b border-[#D9E1F0] px-6 text-[12.5px] font-medium text-[#718096] bg-[#F8FAFD]">
                {tabs.map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`shrink-0 border-b-2 py-2.5 transition-colors cursor-pointer ${
                      activeTab === tab
                        ? "border-[#315FBA] text-[#315FBA] font-semibold"
                        : "border-transparent text-[#718096] hover:text-[#203653]"
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {/* 6 Structured Overview Blocks */}
              <div className="grid gap-px bg-[#D9E1F0] sm:grid-cols-2">
                <div className="bg-white p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">
                    Project Overview
                  </p>
                  <p className="mt-2 text-[13px] leading-relaxed text-[#3e5373]">
                    Core payments ledger, asynchronous settlement worker, and acquirer integrations serving transactions across global gateways.
                  </p>
                </div>

                <div className="bg-white p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">
                    Responsibilities
                  </p>
                  <ul className="mt-2 space-y-1.5 text-[13px] text-[#203653]">
                    {[
                      "Settlement worker architecture",
                      "Ledger schema migrations",
                      "Acquirer credential rotation",
                    ].map((r) => (
                      <li key={r} className="flex items-center gap-2">
                        <Check className="size-3.5 text-[#299B80]" />
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-white p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">
                    Decisions & Rationale
                  </p>
                  <ul className="mt-2 space-y-2 text-[13px] text-[#203653]">
                    {[
                      { title: "Event-driven settlement via Kafka", ok: true },
                      { title: "Idempotency keys required in strict mode", ok: true },
                      { title: "Retention period set to 7 days", ok: false },
                    ].map((d) => (
                      <li
                        key={d.title}
                        className="flex items-center justify-between gap-2"
                      >
                        <span className="truncate">{d.title}</span>
                        {d.ok ? (
                          <ShieldCheck className="size-3.5 shrink-0 text-[#299B80]" />
                        ) : (
                          <span className="shrink-0 rounded bg-red-50 px-1.5 text-[10px] font-semibold text-red-700 ring-1 ring-inset ring-red-600/20">
                            Conflict
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-white p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">
                    Risks & Blockers
                  </p>
                  <ul className="mt-2 space-y-2 text-[13px] text-[#203653]">
                    {[
                      { sev: "Critical", text: "No retry logic on acquirer timeouts" },
                      { sev: "High", text: "Single technical maintainer for schema scripts" },
                    ].map((r) => (
                      <li key={r.text} className="flex items-center gap-2">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                            r.sev === "Critical"
                              ? "bg-red-50 text-red-700"
                              : "bg-amber-50 text-amber-700"
                          }`}
                        >
                          {r.sev}
                        </span>
                        <span className="truncate">{r.text}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-white p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">
                    Pending Handover Items
                  </p>
                  <ul className="mt-2 space-y-1.5 text-[13px] text-[#203653]">
                    {[
                      { item: "Refund reconciliation batch job", date: "Jun 27" },
                      { item: "Rotate acquirer certificates", date: "Jun 30" },
                    ].map((p) => (
                      <li key={p.item} className="flex justify-between gap-2">
                        <span className="truncate">{p.item}</span>
                        <span className="shrink-0 font-mono text-[11.5px] text-[#718096]">
                          {p.date}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-white p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">
                    Next Transition Actions
                  </p>
                  <ol className="mt-2 space-y-1.5 text-[13px] text-[#203653]">
                    {[
                      "Resolve Kafka retention parameter conflict",
                      "Manager approval and publication to successor",
                    ].map((a, i) => (
                      <li key={a} className="flex gap-2">
                        <span className="flex size-4 shrink-0 items-center justify-center rounded-full bg-blue-50 text-[10px] font-bold text-[#315FBA]">
                          {i + 1}
                        </span>
                        <span className="truncate">{a}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
