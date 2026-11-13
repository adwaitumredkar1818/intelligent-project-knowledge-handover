"use client";

import React, { useEffect, useRef } from "react";
import {
  Link2,
  ShieldCheck,
  Lock,
  Lightbulb,
  Sparkles,
  UserRound,
  GitPullRequest,
  MessageSquare,
  FileText,
  ArrowRight,
  Check,
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

export function TrustSection() {
  const ref = useReveal<HTMLElement>();

  return (
    <section
      ref={ref}
      id="security"
      className="relative scroll-mt-20 overflow-hidden bg-[#203653] py-24 text-white sm:py-32"
    >
      <div className="pointer-events-none absolute inset-0 opacity-[0.04] hairline-grid" />
      <div
        className="pointer-events-none absolute -right-40 top-0 size-[620px] rounded-full"
        style={{
          background:
            "radial-gradient(circle, rgba(139,120,201,0.22), transparent 62%)",
        }}
      />

      <div className="mx-auto w-full max-w-[1240px] px-5 sm:px-8">
        <div className="relative grid gap-14 grid-cols-1 lg:grid-cols-[1fr_1fr] lg:gap-16">
          {/* Left Narrative */}
          <div>
            <p className="reveal flex items-center gap-2 text-[12.5px] font-semibold uppercase tracking-[0.16em] text-[#a9b8d0]">
              <span className="h-px w-6 bg-current opacity-60" />
              Trust &amp; Governance
            </p>
            <h2 className="reveal mt-5 text-[34px] font-semibold leading-[1.06] tracking-[-0.035em] sm:text-[44px] lg:text-[50px]">
              AI can reconstruct knowledge. People make it trustworthy.
            </h2>
            <p className="reveal mt-6 max-w-lg text-[17px] leading-[1.65] text-[#c3cfe0]">
              Every important finding must have an unambiguous, traceable source. Handover connects reconstructed project records directly to the evidence behind them.
            </p>

            <ul className="reveal mt-10 space-y-6">
              {[
                {
                  icon: Link2,
                  title: "Source Traceability",
                  body: "Every decision, responsibility, and risk cites the exact commits, pull requests, issue threads, or documents from which it was derived.",
                },
                {
                  icon: ShieldCheck,
                  title: "Human Verification",
                  body: "AI models cannot approve handovers or resolve conflicts independently. Designated human reviewers confirm what enters official records.",
                },
                {
                  icon: Lock,
                  title: "Strict Source Access Control",
                  body: "Project membership does not grant automatic access to private repos or issues. External source ACLs are strictly enforced at read time.",
                },
              ].map((item) => (
                <li key={item.title} className="flex gap-4">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-white/15 bg-white/5">
                    <item.icon className="size-4 text-[#c3cfe0]" />
                  </span>
                  <div>
                    <p className="text-[16px] font-semibold">{item.title}</p>
                    <p className="mt-0.5 text-[14px] leading-relaxed text-[#a9b8d0]">
                      {item.body}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {/* Right Epistemic Separation Showcase */}
          <div className="reveal">
            <div className="rounded-[22px] border border-white/10 bg-white p-5 text-[#203653] shadow-pop sm:p-7">
              {/* Illustrative Architecture Showcase Banner */}
              <div className="mb-4 flex items-center justify-between border-b border-[#D9E1F0] pb-2.5">
                <span className="font-mono text-[10.5px] uppercase tracking-wider text-[#718096]">
                  Epistemic Separation Model
                </span>
                <span className="rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 font-mono text-[9.5px] font-medium text-slate-500">
                  Illustrative Architecture Sample
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#315FBA]">
                  <Lightbulb className="size-3.5" />
                  Reconstructed Finding
                </span>
                <span className="font-mono text-[11px] text-[#718096]">d-kafka-01</span>
              </div>
              <p className="mt-3 text-[18px] font-semibold leading-snug tracking-[-0.02em]">
                Decouple settlement worker from ledger using Kafka events
              </p>

              {/* Four-tier Epistemic Separation Comparison */}
              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-dashed border-indigo-200 bg-indigo-50/60 p-4">
                  <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.1em] text-indigo-500">
                    <Sparkles className="size-3.5" />
                    AI Confidence
                  </p>
                  <p className="mt-2 text-[32px] font-semibold leading-none tracking-[-0.03em] text-indigo-700">
                    94%
                  </p>
                  <div className="mt-3 h-1.5 rounded-full bg-indigo-100 overflow-hidden">
                    <div className="h-full w-[94%] rounded-full bg-indigo-500" />
                  </div>
                  <p className="mt-2.5 text-[11.5px] leading-snug text-indigo-900/70">
                    How strongly the model extracted the finding. Not verified proof.
                  </p>
                </div>

                <div className="rounded-2xl border border-teal-200 bg-teal-50/60 p-4">
                  <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.1em] text-teal-700">
                    <UserRound className="size-3.5" />
                    Human Verification
                  </p>
                  <p className="mt-2 flex items-center gap-2 text-[20px] font-semibold text-teal-700">
                    <ShieldCheck className="size-5.5" />
                    Verified
                  </p>
                  <p className="mt-3 text-[11.5px] leading-snug text-teal-900/70">
                    Confirmed by James Okafor. Required for transition completion.
                  </p>
                </div>
              </div>

              {/* Supporting Evidence List */}
              <p className="mb-2 mt-6 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">
                Supporting Source Evidence
              </p>
              <ul className="divide-y divide-[#D9E1F0] rounded-xl border border-[#D9E1F0]">
                {[
                  {
                    icon: GitPullRequest,
                    type: "GitHub Pull Request",
                    ref: "atlas-settlement#412",
                  },
                  {
                    icon: MessageSquare,
                    type: "Slack Architectural Discussion",
                    ref: "#payments-arch · 8 replies",
                  },
                  {
                    icon: FileText,
                    type: "Uploaded Architecture Decision Record",
                    ref: "ADR-007 Event-driven settlement.pdf",
                  },
                ].map((item) => (
                  <li
                    key={item.ref}
                    className="flex items-center gap-3 px-3.5 py-2.5"
                  >
                    <item.icon className="size-4 text-[#7997BE]" />
                    <span className="flex-1 min-w-0">
                      <span className="block text-[11.5px] text-[#718096]">
                        {item.type}
                      </span>
                      <span className="block truncate font-mono text-[12px] font-semibold text-[#203653]">
                        {item.ref}
                      </span>
                    </span>
                    <ArrowRight className="size-3.5 text-slate-300" />
                  </li>
                ))}
              </ul>
            </div>

            {/* Platform Security Badges */}
            <div className="mt-6 grid grid-cols-2 gap-x-6 gap-y-3 text-[13px] text-[#c3cfe0] sm:grid-cols-3">
              {[
                "Authorized read-only connectors",
                "Strict source ACL enforcement",
                "Zero synthetic data fabrication",
                "AES-256-GCM encrypted storage",
                "Immutable PostgreSQL audit trail",
              ].map((x) => (
                <p key={x} className="flex items-start gap-2">
                  <Check className="mt-0.5 size-3.5 shrink-0 text-[#299B80]" />
                  <span>{x}</span>
                </p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
