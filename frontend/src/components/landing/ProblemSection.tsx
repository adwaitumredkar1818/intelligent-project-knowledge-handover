"use client";

import React, { useEffect, useRef } from "react";
import { CircleAlert, RefreshCw } from "lucide-react";
import { SourceIcon } from "../brand";

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

export function ProblemSection() {
  const ref = useReveal<HTMLElement>();

  const rows = [
    {
      num: "01",
      title: "Scattered knowledge",
      body: "Critical information is distributed across repositories, pull requests, issue trackers, conversations and private documents, with no single owner and no unified place.",
      visual: (
        <div className="relative h-40 w-full max-w-[320px]">
          {[
            { type: "github" as const, x: 8, y: 18, rot: -6, animClass: "animate-float-1" },
            { type: "slack" as const, x: 62, y: 8, rot: 5, animClass: "animate-float-2" },
            { type: "jira" as const, x: 28, y: 60, rot: -3, animClass: "animate-float-3" },
            { type: "docs" as const, x: 74, y: 62, rot: 7, animClass: "animate-float-4" },
          ].map((item) => (
            <div
              key={item.type}
              className={`absolute flex items-center gap-2 rounded-xl border border-[#D9E1F0] bg-white px-3 py-2 shadow-card ${item.animClass}`}
              style={{
                left: `${item.x}%`,
                top: `${item.y}%`,
              }}
            >
              <SourceIcon type={item.type} size={22} />
              <span className="h-1.5 w-12 rounded-full bg-slate-100" />
            </div>
          ))}
          <svg className="absolute inset-0 h-full w-full pointer-events-none" aria-hidden>
            {/* Broken dashed paths with subtle flicker to convey fragmented context */}
            <path d="M90 50 L160 42" stroke="#D9E1F0" strokeDasharray="3 5" className="animate-flicker" />
            <path d="M150 110 L230 112" stroke="#D9E1F0" strokeDasharray="3 5" className="animate-flicker" style={{ animationDelay: "1.4s" }} />

            {/* Faint fragmented evidence particles that travel along connections before dissolving */}
            <circle cx="0" cy="0" r="2.5" fill="#315FBA" className="animate-particle-1" />
            <circle cx="0" cy="0" r="2.5" fill="#7997BE" className="animate-particle-2" />
          </svg>
        </div>
      ),
    },
    {
      num: "02",
      title: "Lost context",
      body: "Teams inherit architecture and legacy code without understanding why choices were made: the operational constraints, rejected alternatives, and trade-offs made under pressure.",
      visual: (
        <div className="w-full max-w-[310px] rounded-2xl border border-[#D9E1F0] bg-white p-4.5 shadow-card">
          <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[#718096]">
            Decision · Architecture
          </p>
          <p className="mt-1 text-[14px] font-semibold text-[#203653]">
            Decouple settlement via Kafka event stream
          </p>
          <p className="mt-3 text-[11px] font-semibold text-slate-400">
            WHY WAS THIS CHOSEN?
          </p>
          <div className="mt-1.5 space-y-1.5">
            {[88, 65, 78].map((w, i) => (
              <span
                key={i}
                className="block h-2 rounded-full bg-slate-100 animate-soft-shimmer"
                style={{ width: `${w}%`, animationDelay: `${i * 0.4}s` }}
              />
            ))}
          </div>
          <div className="mt-3.5 flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11.5px] font-medium text-red-600 animate-alert-breathe">
            <CircleAlert className="size-3.5 shrink-0" />
            <span>Author left the team without documentation</span>
          </div>
        </div>
      ),
    },
    {
      num: "03",
      title: "Repeated work",
      body: "Incoming team members spend their first months rediscovering what already existed, re-asking settled questions, and stumbling into risks that were identified long ago.",
      visual: (
        <div className="flex w-full max-w-[320px] items-center gap-4">
          <div className="relative shrink-0">
            <svg width="84" height="84" viewBox="0 0 96 96" aria-hidden>
              <circle cx="48" cy="48" r="36" fill="none" stroke="#EDF1F8" strokeWidth="8" />
              <path
                d="M48 12 A36 36 0 1 1 13 40"
                fill="none"
                stroke="#D39B43"
                strokeWidth="3.5"
                strokeLinecap="round"
              />
              <path
                d="M8 33 l5 7 7-5"
                fill="none"
                stroke="#D39B43"
                strokeWidth="3.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <RefreshCw className="absolute inset-0 m-auto size-6 text-[#D39B43] animate-spin-12" />
          </div>
          <div className="space-y-2 text-[12.5px] min-w-0 flex-1">
            {[
              { text: "Where is the deploy runbook?", animClass: "animate-queue-1" },
              { text: "Who owns credential rotation?", animClass: "animate-queue-2" },
              { text: "Why was this retry skipped?", animClass: "animate-queue-3" },
            ].map((q) => (
              <p
                key={q.text}
                className={`truncate rounded-lg border border-[#D9E1F0] bg-white px-3 py-1.5 text-[#56657c] shadow-xs ${q.animClass}`}
              >
                {q.text}
              </p>
            ))}
          </div>
        </div>
      ),
    },
  ];

  return (
    <section ref={ref} className="bg-white py-24 sm:py-32">
      <div className="mx-auto w-full max-w-[1240px] px-5 sm:px-8">
        <div className="grid gap-14 grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] lg:gap-20">
          {/* Left Sticky Problem Anchor */}
          <div className="lg:sticky lg:top-32 lg:self-start">
            <div className="reveal">
              <p className="flex items-center gap-2 text-[12.5px] font-semibold uppercase tracking-[0.16em] text-[#315FBA]">
                <span className="h-px w-6 bg-current opacity-60" />
                The Problem
                <span className="ml-auto font-mono text-[10px] tracking-[0.12em] text-[#7997BE]/70 sm:hidden">
                  SEC_01
                </span>
              </p>
            </div>
            <h2 className="reveal mt-5 text-[34px] font-semibold leading-[1.06] tracking-[-0.035em] text-[#203653] sm:text-[44px] lg:text-[50px]">
              Projects don&apos;t lose progress. They lose context.
            </h2>
            <p className="reveal mt-6 max-w-md text-[17px] leading-[1.65] text-[#56657c]">
              When someone moves on, the next person doesn&apos;t just inherit tasks.
              They inherit decisions, unwritten assumptions, technical dependencies, and years of accumulated understanding.
            </p>
          </div>

          {/* Right Structured Problem List */}
          <ol className="divide-y divide-[#D9E1F0] border-y border-[#D9E1F0]">
            {rows.map((r) => (
              <li
                key={r.num}
                className="reveal grid gap-6 py-10 sm:grid-cols-[1fr_310px] sm:items-center"
              >
                <div>
                  <p className="font-mono text-[13px] text-[#7997BE]">{r.num}</p>
                  <h3 className="mt-2 text-[26px] font-semibold tracking-[-0.025em] text-[#203653]">
                    {r.title}
                  </h3>
                  <p className="mt-2.5 max-w-sm text-[15.5px] leading-relaxed text-[#56657c]">
                    {r.body}
                  </p>
                </div>
                <div className="flex justify-start sm:justify-end">{r.visual}</div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
