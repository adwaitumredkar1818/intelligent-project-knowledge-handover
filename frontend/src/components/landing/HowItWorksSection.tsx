"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Plug,
  Sparkles,
  Compass,
  ShieldCheck,
  Workflow,
  Lock,
  Check,
  ArrowRight,
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

const STEPS = [
  {
    key: "Connect",
    icon: Plug,
    body: "Connect authorized GitHub, Jira, Slack and uploaded project documents.",
  },
  {
    key: "Reconstruct",
    icon: Sparkles,
    body: "AI extracts decisions, technical architecture, and risks with full source provenance.",
  },
  {
    key: "Understand",
    icon: Compass,
    body: "Discover decisions, responsibilities, risks, dependencies and historical context.",
  },
  {
    key: "Verify",
    icon: ShieldCheck,
    body: "Human reviewers evaluate candidate findings against original evidence.",
  },
  {
    key: "Transfer",
    icon: Workflow,
    body: "Generate structured, role-tailored handovers for incoming members.",
  },
];

function PreviewBadge() {
  return (
    <div className="mb-3 flex items-center justify-between border-b border-[#D9E1F0]/70 pb-2">
      <span className="font-mono text-[10px] uppercase tracking-wider text-[#718096]">
        Workflow Preview
      </span>
      <span className="rounded-full border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono text-[9px] font-medium text-slate-500">
        Illustrative Demo
      </span>
    </div>
  );
}

function StepPreview({ index }: { index: number }) {
  const frameClass =
    "rounded-2xl border border-[#D9E1F0] bg-white p-5 shadow-card max-w-md mx-auto";

  if (index === 0) {
    return (
      <div className={frameClass}>
        <PreviewBadge />
        <p className="text-[13px] font-semibold text-[#203653]">
          Select Connected Repositories
        </p>
        <div className="mt-3 space-y-2">
          {["payment-core-ledger", "settlement-worker", "gateway-api"].map(
            (r, j) => (
              <div
                key={r}
                className="flex items-center gap-2.5 rounded-lg border border-[#D9E1F0] px-3 py-2 text-xs"
              >
                <span
                  className={`flex size-4 items-center justify-center rounded ${
                    j < 2 ? "bg-[#315FBA] text-white" : "border border-slate-300"
                  }`}
                >
                  {j < 2 && <Check className="size-3" />}
                </span>
                <span className="font-mono text-[12px] text-[#203653]">{r}</span>
              </div>
            )
          )}
        </div>
        <p className="mt-3.5 flex items-center gap-1.5 text-[11.5px] text-[#718096]">
          <Lock className="size-3 text-[#315FBA]" />
          <span>Read-only access · Explicit user authorization</span>
        </p>
      </div>
    );
  }

  if (index === 1) {
    return (
      <div className={frameClass}>
        <PreviewBadge />
        <div className="flex items-center justify-between text-[13px]">
          <span className="font-semibold text-[#203653]">Knowledge Reconstruction</span>
          <span className="font-mono font-medium text-[#315FBA]">84%</span>
        </div>
        <div className="mt-3 h-1.5 rounded-full bg-slate-100 overflow-hidden">
          <div className="h-full w-[84%] rounded-full bg-[#315FBA]" />
        </div>
        <ul className="mt-4 space-y-2 text-[12.5px]">
          {[
            { label: "Collecting evidence records", done: true },
            { label: "Extracting decisions & ownership", done: true },
            { label: "Linking provenance citations", done: false },
          ].map((item) => (
            <li key={item.label} className="flex items-center gap-2">
              {item.done ? (
                <Check className="size-3.5 text-[#299B80]" />
              ) : (
                <span className="size-3.5 animate-pulse-soft rounded-full border-2 border-[#315FBA]" />
              )}
              <span className={item.done ? "text-[#203653]" : "text-[#718096]"}>
                {item.label}
              </span>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  if (index === 2) {
    return (
      <div className={frameClass}>
        <PreviewBadge />
        <p className="text-[13px] font-semibold text-[#203653] mb-3">
          Knowledge Domains Discovered
        </p>
        <div className="grid grid-cols-2 gap-2.5">
          {[
            { label: "Decisions", count: 8, color: "#315FBA" },
            { label: "Tasks", count: 12, color: "#299B80" },
            { label: "Risks", count: 5, color: "#D36D72" },
            { label: "Dependencies", count: 7, color: "#D39B43" },
          ].map((d) => (
            <div key={d.label} className="rounded-xl bg-[#F6F8FC] p-3 border border-[#D9E1F0]/60">
              <p className="text-[22px] font-semibold text-[#203653]">{d.count}</p>
              <p className="flex items-center gap-1.5 text-[12px] text-[#718096]">
                <span
                  className="size-1.5 rounded-full"
                  style={{ background: d.color }}
                />
                {d.label}
              </p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (index === 3) {
    return (
      <div className={frameClass}>
        <PreviewBadge />
        <p className="text-[13px] font-semibold text-[#203653]">
          Settlement worker lacks retry logic on acquirer timeouts
        </p>
        <div className="mt-2.5 flex items-center gap-2">
          <span className="rounded-md border border-dashed border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700">
            AI 83%
          </span>
          <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700 ring-1 ring-inset ring-amber-600/20">
            Human Review Queue
          </span>
        </div>
        <div className="mt-4 flex gap-2">
          <span className="flex h-8 items-center gap-1.5 rounded-lg bg-[#299B80] px-3 text-[12px] font-semibold text-white shadow-xs">
            <ShieldCheck className="size-3.5" />
            Verify
          </span>
          <span className="flex h-8 items-center rounded-lg border border-[#D9E1F0] px-3 text-[12px] font-semibold text-[#203653]">
            Edit Finding
          </span>
          <span className="flex h-8 items-center rounded-lg border border-[#D9E1F0] px-3 text-[12px] font-semibold text-red-600">
            Reject
          </span>
        </div>
      </div>
    );
  }

  // index === 4
  return (
    <div className={frameClass}>
      <PreviewBadge />
      <div className="flex items-center gap-3">
        <span className="flex size-8 items-center justify-center rounded-full bg-[#203653] text-[11px] font-bold text-white">
          JO
        </span>
        <ArrowRight className="size-4 text-[#315FBA]" />
        <span className="flex size-8 items-center justify-center rounded-full bg-[#315FBA] text-[11px] font-bold text-white">
          PN
        </span>
        <span className="ml-auto rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-[#315FBA] ring-1 ring-inset ring-blue-600/20">
          Published Handover
        </span>
      </div>
      <p className="mt-3 text-[13px] font-semibold text-[#203653]">
        HO-1042 · Payments Infrastructure Transition
      </p>
      <div className="mt-3.5 grid grid-cols-6 gap-1">
        {[1, 1, 1, 1, 1, 0].map((d, j) => (
          <span
            key={j}
            className={`h-1.5 rounded-full ${
              d ? "bg-[#299B80]" : "bg-[#315FBA]"
            }`}
          />
        ))}
      </div>
    </div>
  );
}

export function HowItWorksSection() {
  const ref = useReveal<HTMLElement>();
  const [activeStep, setActiveStep] = useState(0);

  return (
    <section
      ref={ref}
      id="how"
      className="scroll-mt-20 bg-white py-24 sm:py-32"
    >
      <div className="mx-auto w-full max-w-[1240px] px-5 sm:px-8">
        {/* Header */}
        <div className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <div className="reveal">
              <p className="flex items-center gap-2 text-[12.5px] font-semibold uppercase tracking-[0.16em] text-[#315FBA]">
                <span className="h-px w-6 bg-current opacity-60" />
                How Handover Works
              </p>
            </div>
            <h2 className="reveal mt-5 max-w-3xl text-[34px] font-semibold leading-[1.06] tracking-[-0.035em] text-[#203653] sm:text-[44px] lg:text-[52px]">
              From project activity to knowledge that moves forward.
            </h2>
          </div>
          <p className="reveal text-[14px] text-[#718096]">
            Select any step to preview its interface
          </p>
        </div>

        {/* Step Navigation Bar */}
        <ol className="reveal relative mt-16 grid gap-0 lg:grid-cols-5 lg:gap-4">
          {/* Connector Line Background */}
          <span className="absolute left-0 right-0 top-[19px] hidden h-px bg-[#D9E1F0] lg:block" />
          <span
            className="absolute left-0 top-[19px] hidden h-px bg-[#315FBA] transition-all duration-500 lg:block overflow-hidden"
            style={{ width: `${(activeStep / 4) * 100}%` }}
          >
            <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/70 to-transparent animate-beam" />
          </span>
          <span className="absolute bottom-0 left-[19px] top-0 w-px bg-[#D9E1F0] lg:hidden" />

          {STEPS.map((s, i) => (
            <li key={s.key} className="relative pb-8 pl-14 lg:pb-0 lg:pl-0">
              <button
                onClick={() => setActiveStep(i)}
                className="group w-full text-left cursor-pointer focus:outline-none"
              >
                <span
                  className={`absolute left-0 top-0 flex size-10 items-center justify-center rounded-full border bg-white transition-all duration-300 lg:relative ${
                    i <= activeStep
                      ? "border-[#315FBA] text-[#315FBA]"
                      : "border-[#D9E1F0] text-slate-400 group-hover:border-[#7997BE]"
                  } ${i === activeStep ? "ring-4 ring-[#315FBA]/15 shadow-xs scale-105" : ""}`}
                >
                  <s.icon className="size-4" />
                </span>
                <p className="font-mono text-[12px] text-[#718096] lg:mt-5">
                  Step 0{i + 1}
                </p>
                <h3
                  className={`mt-1 text-[20px] font-semibold tracking-[-0.02em] transition-colors ${
                    i === activeStep ? "text-[#203653]" : "text-[#56657c]"
                  }`}
                >
                  {s.key}
                </h3>
                <p className="mt-1.5 max-w-[240px] text-[14px] leading-relaxed text-[#718096]">
                  {s.body}
                </p>
              </button>

              {/* Mobile Embedded Preview */}
              <div className="mt-5 lg:hidden">
                {i === activeStep && (
                  <div className="animate-fade">
                    <StepPreview index={i} />
                  </div>
                )}
              </div>
            </li>
          ))}
        </ol>

        {/* Desktop Centered Interactive Preview */}
        <div className="mt-14 hidden lg:grid lg:grid-cols-5 lg:gap-4">
          <div
            key={activeStep}
            className="animate-fade"
            style={{
              gridColumnStart: Math.min(activeStep + 1, 4),
              gridColumnEnd: "span 2",
            }}
          >
            <StepPreview index={activeStep} />
          </div>
        </div>
      </div>
    </section>
  );
}
