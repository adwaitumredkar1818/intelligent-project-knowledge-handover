"use client";

import React, { useEffect, useRef } from "react";
import {
  Compass,
  Send,
  Inbox,
  ClipboardCheck,
  Plug,
  AlertTriangle,
  ShieldCheck,
  Check,
  Layers,
  UserRound,
  ListTodo,
  Link2,
} from "lucide-react";

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

export function RolesSection() {
  const ref = useReveal<HTMLElement>();

  return (
    <section
      ref={ref}
      id="roles"
      className="ambient-section scroll-mt-20 bg-white py-24 sm:py-32"
    >
      <div className="mx-auto w-full max-w-[1240px] px-5 sm:px-8">
        {/* Section Heading */}
        <div className="max-w-3xl">
          <div className="reveal">
            <p className="flex items-center gap-2 text-[12.5px] font-semibold uppercase tracking-[0.16em] text-[#315FBA]">
              <span className="h-px w-6 bg-current opacity-60" />
              Role-Based Experiences
            </p>
          </div>
          <h2 className="reveal mt-5 text-[34px] font-semibold leading-[1.06] tracking-[-0.035em] text-[#203653] sm:text-[44px] lg:text-[50px]">
            One platform. Every side of the transition.
          </h2>
          <p className="reveal mt-6 max-w-2xl text-[17px] leading-[1.65] text-[#56657c]">
            Transition participants have distinct responsibilities. Handover adapts per project, allowing the same team member to approve one handover, compile another, and receive a third.
          </p>
        </div>

        {/* 3 Role Showcases */}
        <div className="mt-20 space-y-24 sm:space-y-28">
          {/* 1. Project Manager */}
          <div className="reveal grid items-center gap-10 grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-[12.5px] font-semibold text-[#315FBA] ring-1 ring-inset ring-blue-600/20">
                <Compass className="size-3.5" />
                Project Manager
              </span>
              <h3 className="mt-5 text-[28px] font-semibold leading-tight tracking-[-0.03em] text-[#203653] sm:text-[34px]">
                See every transition clearly.
              </h3>
              <p className="mt-4 max-w-md text-[16px] leading-relaxed text-[#718096]">
                Monitor ongoing transitions, manage participant roles, inspect verification queues, and keep handovers moving forward with instant visibility into blockers.
              </p>
            </div>

            <div className="rounded-[20px] border border-[#D9E1F0] bg-[#F6F8FC] p-4 sm:p-5 shadow-xs">
              <div className="mb-3 flex items-center justify-between border-b border-[#D9E1F0]/80 pb-2">
                <span className="font-mono text-[10.5px] uppercase tracking-wider text-[#718096]">
                  Transition Overview Demo
                </span>
                <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 font-mono text-[9.5px] font-medium text-slate-500">
                  Illustrative
                </span>
              </div>
              <div className="grid gap-3 sm:grid-cols-[1.2fr_1fr]">
                <div className="tile rounded-2xl border border-[#D9E1F0] bg-white p-4 shadow-card">
                  <p className="text-[12px] font-semibold text-[#203653]">
                    Attention Required
                  </p>
                  <ul className="mt-3 space-y-2.5">
                    {[
                      {
                        icon: ClipboardCheck,
                        color: "text-amber-600 bg-amber-50",
                        text: "HO-1042 awaiting manager approval",
                      },
                      {
                        icon: Plug,
                        color: "text-red-600 bg-red-50",
                        text: "Slack OAuth scope re-authorization needed",
                      },
                      {
                        icon: AlertTriangle,
                        color: "text-red-600 bg-red-50",
                        text: "Critical timeout risk unresolved",
                      },
                    ].map((item) => (
                      <li key={item.text} className="flex items-center gap-2.5">
                        <span
                          className={`flex size-6 shrink-0 items-center justify-center rounded-md ${item.color}`}
                        >
                          <item.icon className="size-3" />
                        </span>
                        <span className="text-[12px] text-[#203653] leading-snug">
                          {item.text}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="tile rounded-2xl border border-[#D9E1F0] bg-white p-4 shadow-card">
                  <p className="text-[12px] font-semibold text-[#203653]">
                    Transition Readiness
                  </p>
                  <ul className="mt-3 space-y-3">
                    {[
                      { name: "Payments Core", val: 86, color: "#299B80" },
                      { name: "Gateway API", val: 64, color: "#D39B43" },
                      { name: "Settlement Batch", val: 92, color: "#299B80" },
                    ].map((p) => (
                      <li key={p.name}>
                        <div className="flex justify-between text-[11.5px]">
                          <span className="font-medium text-[#203653]">{p.name}</span>
                          <span className="font-mono text-[#718096]">{p.val}%</span>
                        </div>
                        <div className="mt-1 h-1 rounded-full bg-slate-100 overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${p.val}%`, background: p.color }}
                          />
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* 2. Outgoing Member */}
          <div className="reveal grid items-center gap-10 grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] lg:gap-16">
            <div className="order-2 lg:order-1">
              <div className="relative mx-auto max-w-md">
                <div className="absolute inset-x-6 -bottom-3 top-3 rounded-2xl border border-[#D9E1F0] bg-white/60 pointer-events-none" />
                <div className="tile relative rounded-2xl border border-[#D9E1F0] bg-white p-5 shadow-card">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[#718096]">
                      Review Queue Demo · 7 of 23
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span className="rounded-sm bg-slate-100 px-1.5 py-0.5 font-mono text-[9px] font-medium text-slate-500">
                        Sample Item
                      </span>
                      <span className="font-mono text-[11px] text-[#718096]">
                        HO-1038
                      </span>
                    </div>
                  </div>
                  <p className="mt-3 text-[15px] font-semibold text-[#203653]">
                    Offline edits to merchant banking details can silently overwrite
                  </p>
                  <p className="mt-1.5 text-[13px] leading-relaxed text-[#718096]">
                    No concurrency conflict resolution strategy was defined for offline payout modifications.
                  </p>
                  <div className="mt-4 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                    <div className="h-full w-[35%] rounded-full bg-[#299B80]" />
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <span className="flex h-9 items-center gap-1.5 rounded-lg bg-[#299B80] px-3.5 text-[12.5px] font-semibold text-white shadow-xs">
                      <ShieldCheck className="size-3.5" />
                      Approve & verify
                    </span>
                    <span className="flex h-9 items-center rounded-lg border border-[#D9E1F0] px-3.5 text-[12.5px] font-semibold text-[#203653]">
                      Add context
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="order-1 lg:order-2">
              <span className="inline-flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1 text-[12.5px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-600/20">
                <Send className="size-3.5" />
                Outgoing Member
              </span>
              <h3 className="mt-5 text-[28px] font-semibold leading-tight tracking-[-0.03em] text-[#203653] sm:text-[34px]">
                Leave the knowledge, not just the role.
              </h3>
              <p className="mt-4 max-w-md text-[16px] leading-relaxed text-[#718096]">
                Eliminate grueling exit interview checklists. Review AI-reconstructed findings from your actual work, add critical color where needed, and confirm ownership in minutes.
              </p>
            </div>
          </div>

          {/* Directional Knowledge Transmission Bridge */}
          <div className="reveal relative z-20 flex items-center justify-center py-4" aria-hidden="true">
            <div className="relative z-20 flex items-center gap-3 rounded-full border border-[#D9E1F0] bg-white px-5 py-2 shadow-sm ring-1 ring-slate-900/5 transition hover:border-[#315FBA]/40">
              <span className="font-mono text-[10.5px] font-semibold text-amber-700 uppercase tracking-wider">Outgoing</span>
              <svg width="40" height="12" viewBox="0 0 40 12" fill="none" className="overflow-visible" aria-hidden="true">
                <path d="M0 6 H34" stroke="#D9E1F0" strokeWidth="1.5" />
                <path d="M0 6 H34" stroke="#315FBA" strokeWidth="1.5" className="animate-stream-flow" />
                <polygon points="32,3 40,6 32,9" fill="#315FBA" />
              </svg>
              <span className="font-mono text-[10.5px] font-semibold text-[#315FBA] uppercase tracking-wider">Continuous Handover</span>
              <svg width="40" height="12" viewBox="0 0 40 12" fill="none" className="overflow-visible" aria-hidden="true">
                <path d="M0 6 H34" stroke="#D9E1F0" strokeWidth="1.5" />
                <path d="M0 6 H34" stroke="#299B80" strokeWidth="1.5" className="animate-stream-flow" />
                <polygon points="32,3 40,6 32,9" fill="#299B80" />
              </svg>
              <span className="font-mono text-[10.5px] font-semibold text-teal-700 uppercase tracking-wider">Incoming</span>
            </div>
          </div>

          {/* 3. Incoming Member */}
          <div className="reveal grid items-center gap-10 grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full bg-teal-50 px-3 py-1 text-[12.5px] font-semibold text-teal-700 ring-1 ring-inset ring-teal-600/20">
                <Inbox className="size-3.5" />
                Incoming Successor
              </span>
              <h3 className="mt-5 text-[28px] font-semibold leading-tight tracking-[-0.03em] text-[#203653] sm:text-[34px]">
                Step into the project with context.
              </h3>
              <p className="mt-4 max-w-md text-[16px] leading-relaxed text-[#718096]">
                Explore verified project decisions, understand architectural assumptions, and query the project assistant with complete source attribution.
              </p>
            </div>

            <div className="rounded-[20px] border border-[#D9E1F0] bg-[#F6F8FC] p-4 sm:p-5 shadow-xs">
              <div className="mb-3 flex items-center justify-between border-b border-[#D9E1F0]/80 pb-2">
                <span className="font-mono text-[10.5px] uppercase tracking-wider text-[#718096]">
                  Successor Onboarding Demo
                </span>
                <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 font-mono text-[9.5px] font-medium text-slate-500">
                  Illustrative
                </span>
              </div>
              <div className="grid gap-3 sm:grid-cols-[200px_1fr]">
                <ol className="rounded-2xl border border-[#D9E1F0] bg-white p-3 shadow-xs">
                  {[
                    { icon: Compass, label: "System Overview", done: true },
                    { icon: Layers, label: "Architecture", done: true },
                    { icon: UserRound, label: "Responsibilities", done: false },
                    { icon: ListTodo, label: "Pending Tasks", done: false },
                  ].map((item, i) => (
                    <li
                      key={item.label}
                      className={`flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] ${
                        i === 2 ? "bg-[#F6F8FC] font-semibold text-[#203653]" : ""
                      }`}
                    >
                      <span
                        className={`flex size-6 items-center justify-center rounded-md ${
                          item.done
                            ? "bg-teal-50 text-[#299B80]"
                            : i === 2
                            ? "bg-[#315FBA] text-white"
                            : "bg-slate-100 text-slate-400"
                        }`}
                      >
                        {item.done ? (
                          <Check className="size-3" />
                        ) : (
                          <item.icon className="size-3" />
                        )}
                      </span>
                      <span className="text-[#203653]">{item.label}</span>
                    </li>
                  ))}
                </ol>

                <div className="tile rounded-2xl border border-[#D9E1F0] bg-white p-4 shadow-card">
                  <p className="ml-auto w-fit rounded-2xl rounded-br-xs bg-[#315FBA] px-3.5 py-2 text-[12.5px] text-white">
                    Why was Kafka chosen over RabbitMQ for settlement?
                  </p>
                  <div className="mt-3 rounded-2xl rounded-tl-xs border border-[#D9E1F0] bg-[#F8FAFD] p-3 text-[12.5px] leading-relaxed text-[#3e5373]">
                    Decoupled transaction lock path, persistent audit event log, and native horizontal scaling for batch acquirer reconciliations.
                    <p className="mt-2 flex items-center gap-1.5 font-mono text-[11px] text-[#315FBA]">
                      <Link2 className="size-3" />
                      [1] ADR-007 Event-driven settlement.pdf
                    </p>
                  </div>
                  <span className="mt-2.5 inline-flex items-center gap-1 rounded-full bg-teal-50 px-2.5 py-0.5 text-[11px] font-medium text-teal-700 ring-1 ring-inset ring-teal-600/20">
                    <ShieldCheck className="size-3" />
                    Grounded in verified project findings
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
