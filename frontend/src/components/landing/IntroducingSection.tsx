"use client";

import React, { useEffect, useRef } from "react";
import {
  ArrowRight,
  Check,
  ShieldCheck,
  Lightbulb,
  UserRound,
  AlertTriangle,
  Network,
} from "lucide-react";
import { LogoMark, SourceIcon } from "../brand";
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

export function IntroducingSection() {
  const ref = useReveal<HTMLElement>();

  return (
    <section
      ref={ref}
      id="product"
      className="ambient-section relative overflow-hidden py-24 sm:py-32"
    >
      <div className="mx-auto w-full max-w-[1240px] px-5 sm:px-8">
        {/* Section Heading */}
        <div className="mx-auto max-w-3xl text-center">
          <div className="reveal flex justify-center">
            <p className="flex items-center gap-2 text-[12.5px] font-semibold uppercase tracking-[0.16em] text-[#315FBA]">
              <span className="h-px w-6 bg-current opacity-60" />
              Introducing Handover
            </p>
          </div>
          <h2 className="reveal mt-5 text-[34px] font-semibold leading-[1.06] tracking-[-0.035em] text-[#203653] sm:text-[44px] lg:text-[52px]">
            One place for everything your project knows.
          </h2>
          <p className="reveal mx-auto mt-6 max-w-2xl text-[17px] leading-[1.65] text-[#56657c]">
            Handover connects authorized organizational sources, reconstructs fragmented project context into structured records with full provenance, surfaces conflicts, and produces auditable transition packages.
          </p>
        </div>

        {/* Dynamic Assembly Canvas — Organic Knowledge Core */}
        <div className="reveal relative mx-auto mt-12 max-w-[1140px] rounded-2xl border border-[#D9E1F0]/70 bg-gradient-to-b from-white/70 via-[#F6F8FC]/50 to-white/80 p-2 sm:p-4 shadow-[0_4px_24px_-4px_rgba(32,54,83,0.06)] backdrop-blur-xs">
          <div className="h-[360px] w-full sm:h-[440px] lg:h-[480px]">
            <OrganicScene
              variant="assemble"
              className="h-full w-full"
              aria-label="Dimensional knowledge reconstruction core: scattered sources flowing into an organic knowledge core and reconstructing structured, verified project knowledge"
            />
          </div>
          <div className="pointer-events-none absolute inset-x-0 bottom-3 flex items-center justify-between px-3 font-mono text-[9.5px] uppercase tracking-[0.08em] text-[#718096] sm:px-8 sm:text-[10.5px] sm:tracking-[0.14em]">
            <span className="flex items-center gap-1.5 sm:gap-2">
              <span className="inline-block size-1.5 rounded-full bg-[#7997BE]/80" />
              Scattered sources
            </span>
            <span className="hidden sm:flex items-center gap-2 font-medium text-[#315FBA]">
              <span className="inline-block size-1.5 rounded-full bg-[#315FBA] animate-pulse" />
              Knowledge reconstruction
            </span>
            <span className="flex items-center gap-1.5 sm:gap-2 font-medium text-[#299B80]">
              <span className="inline-block size-1.5 rounded-full bg-[#299B80]" />
              Structured knowledge
            </span>
          </div>
        </div>

        {/* 3-Column Architecture Progression */}
        <div className="reveal mt-12 grid gap-4 lg:grid-cols-[1fr_auto_1.15fr_auto_1.2fr] lg:items-stretch">
          {/* Column 1: Connected Sources */}
          <div className="tile rounded-[16px] border border-[#D9E1F0] bg-white p-6 shadow-card">
            <p className="font-mono text-[11.5px] font-medium text-[#718096]">
              01 · Connected sources
            </p>
            <ul className="mt-5 space-y-3">
              {[
                { type: "github" as const, name: "core-ledger-repo", label: "Pull requests & commits" },
                { type: "jira" as const, name: "PAY · SPRINT-34", label: "Sprint issues & blockers" },
                { type: "slack" as const, name: "#arch-decisions", label: "Threaded discussions" },
                { type: "docs" as const, name: "ADRs & Runbooks", label: "Uploaded PDF & DOCX" },
              ].map((s) => (
                <li key={s.name} className="flex items-center gap-3">
                  <SourceIcon type={s.type} size={30} />
                  <span className="flex-1 min-w-0">
                    <span className="block truncate font-mono text-[12.5px] font-semibold text-[#203653]">
                      {s.name}
                    </span>
                    <span className="block text-[11.5px] text-[#718096]">
                      {s.label}
                    </span>
                  </span>
                  <span className="size-2 rounded-full bg-[#299B80] animate-pulse-soft" />
                </li>
              ))}
            </ul>
          </div>

          {/* Animated Flowing Synapse Stream 1 */}
          <div className="hidden items-center justify-center lg:flex px-1" aria-hidden="true">
            <svg width="44" height="24" viewBox="0 0 44 24" fill="none" className="overflow-visible">
              <path d="M0 12 H38" stroke="#D9E1F0" strokeWidth="1.5" />
              <path d="M0 12 H38" stroke="#315FBA" strokeWidth="1.5" className="animate-stream-flow" />
              <polygon points="36,8 44,12 36,16" fill="#315FBA" />
              <circle cx="0" cy="12" r="2.5" fill="#315FBA">
                <animate attributeName="cx" values="0;38" dur="2.2s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0;1;1;0" dur="2.2s" repeatCount="indefinite" />
              </circle>
            </svg>
          </div>

          {/* Column 2: Handover Intelligence */}
          <div className="relative overflow-hidden rounded-[20px] border border-[#2c4566] bg-[#203653] p-6 text-white shadow-pop">
            <div className="absolute inset-0 opacity-[0.08] dot-grid" />
            <div className="relative">
              <p className="font-mono text-[11.5px] text-[#a9b8d0]">
                02 · Handover intelligence
              </p>
              <div className="mt-5 flex items-center gap-3">
                <span className="flex size-11 items-center justify-center rounded-xl bg-white shadow-xs">
                  <LogoMark size={28} />
                </span>
                <div>
                  <p className="text-[15px] font-semibold">Reconstructing knowledge</p>
                  <p className="text-[12px] text-[#a9b8d0]">Full provenance · Strict ACLs</p>
                </div>
              </div>

              <ol className="mt-6 space-y-3">
                {[
                  "Extract decisions, ownership and risks",
                  "Link findings to original evidence",
                  "Surface contradictions and missing context",
                  "Four-tier epistemic separation",
                ].map((item, i) => (
                  <li key={item} className="flex items-center gap-3 text-[13px]">
                    <span
                      className={`flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                        i < 3
                          ? "bg-[#299B80] text-white"
                          : "border border-[#5a7091] text-[#a9b8d0]"
                      }`}
                    >
                      {i < 3 ? <Check className="size-3" /> : i + 1}
                    </span>
                    <span className={i < 3 ? "text-white" : "text-[#a9b8d0]"}>
                      {item}
                    </span>
                  </li>
                ))}
              </ol>

              <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-white/10">
                <div className="h-full w-[82%] rounded-full bg-gradient-to-r from-[#7997BE] to-[#A5A0D9]" />
              </div>
            </div>
          </div>

          {/* Animated Flowing Synapse Stream 2 */}
          <div className="hidden items-center justify-center lg:flex px-1" aria-hidden="true">
            <svg width="44" height="24" viewBox="0 0 44 24" fill="none" className="overflow-visible">
              <path d="M0 12 H38" stroke="#D9E1F0" strokeWidth="1.5" />
              <path d="M0 12 H38" stroke="#299B80" strokeWidth="1.5" className="animate-stream-flow" />
              <polygon points="36,8 44,12 36,16" fill="#299B80" />
              <circle cx="0" cy="12" r="2.5" fill="#299B80">
                <animate attributeName="cx" values="0;38" dur="2.2s" repeatCount="indefinite" begin="0.7s" />
                <animate attributeName="opacity" values="0;1;1;0" dur="2.2s" repeatCount="indefinite" begin="0.7s" />
              </circle>
            </svg>
          </div>

          {/* Column 3: Structured Project Knowledge */}
          <div className="tile rounded-[16px] border border-[#D9E1F0] bg-white p-6 shadow-card">
            <p className="font-mono text-[11.5px] font-medium text-[#718096]">
              03 · Structured project knowledge
            </p>
            <ul className="mt-5 divide-y divide-[#D9E1F0]">
              {[
                {
                  icon: Lightbulb,
                  color: "#315FBA",
                  kind: "Decision",
                  title: "Event-driven settlement via Kafka",
                  verified: true,
                },
                {
                  icon: UserRound,
                  color: "#299B80",
                  kind: "Responsibility",
                  title: "Acquirer credential rotation",
                  verified: true,
                },
                {
                  icon: AlertTriangle,
                  color: "#D36D72",
                  kind: "Risk",
                  title: "No retry on acquirer timeouts",
                  verified: false,
                },
                {
                  icon: Network,
                  color: "#D39B43",
                  kind: "Dependency",
                  title: "Settlement → Platform Vault",
                  verified: false,
                },
              ].map((item) => (
                <li key={item.title} className="flex items-center gap-3 py-3">
                  <item.icon
                    className="size-4 shrink-0"
                    style={{ color: item.color }}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block text-[11px] font-medium text-[#718096]">
                      {item.kind}
                    </span>
                    <span className="block truncate text-[13px] font-semibold text-[#203653]">
                      {item.title}
                    </span>
                  </span>
                  {item.verified ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2 py-0.5 text-[10.5px] font-semibold text-teal-700 ring-1 ring-inset ring-teal-600/20">
                      <ShieldCheck className="size-3" />
                      Verified
                    </span>
                  ) : (
                    <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10.5px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-600/20">
                      Review
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
