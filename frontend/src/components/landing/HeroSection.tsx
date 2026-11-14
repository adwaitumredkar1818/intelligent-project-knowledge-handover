"use client";

import React, { useState, useEffect } from "react";
import { ArrowDown, ArrowRight, Plug, ShieldCheck } from "lucide-react";
import { OrganicScene } from "../brand/OrganicScene";
import { useLiveApp } from "../../context/LiveAppContext";
import { useRouter } from "next/navigation";

export function HeroSection() {
  const { user } = useLiveApp();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleGetStarted = () => {
    if (user) {
      router.push("/overview");
    } else {
      router.push("/signup");
    }
  };

  const scrollToHow = () => {
    const el = document.getElementById("how");
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <section className="ambient-hero relative min-h-[640px] sm:min-h-[700px] lg:min-h-[760px] overflow-hidden pb-16 pt-8 sm:pt-14 lg:pb-24 flex items-center">
      {/* 1. Stacking Architecture: Background Organic Knowledge Network (Lowest Layer) */}
      <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
        {/* Full-bleed Canvas */}
        <OrganicScene
          variant="hero"
          camZoom={1.3}
          camOffset={[0.26, -0.04]}
          showTags={true}
          className="h-full w-full"
          aria-label="Expansive organic knowledge network representing connected project decisions, responsibilities, risks and dependencies"
        />

        {/* 2. Soft Ambient Gradient & Contrast Masks (Above Canvas, Below Content) */}
        {/* Left-to-right fade mask: guarantees pristine contrast for all text */}
        <div
          className="absolute inset-y-0 left-0 w-full sm:w-[72%] lg:w-[60%] z-[1]"
          style={{
            background:
              "linear-gradient(to right, #F6F8FC 0%, rgba(246,248,252,0.96) 35%, rgba(246,248,252,0.72) 70%, transparent 100%)",
          }}
        />

        {/* Seamless edge blending with page header and next sections */}
        <div className="absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-[#F6F8FC] to-transparent z-[1]" />
        <div className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-[#F6F8FC] via-[#F6F8FC]/70 to-transparent z-[1]" />
        <div className="absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-[#F6F8FC]/60 to-transparent z-[1]" />
      </div>

      {/* 3. Hero Content Layer: Text & Interactive Controls (Highest Layer) */}
      <div className="relative z-10 mx-auto w-full max-w-[1240px] px-5 sm:px-8">
        <div className="max-w-[620px] lg:py-12">
          {/* Context Pill */}
          <div className="inline-flex items-center gap-2 rounded-full border border-[#D9E1F0] bg-white/90 px-3.5 py-1 text-[12.5px] font-semibold text-[#3e5373] shadow-xs backdrop-blur-xs">
            <span className="size-2 rounded-full bg-[#299B80] animate-pulse-soft" />
            <span>Project Knowledge Continuity</span>
          </div>

          {/* Signature Headline */}
          <h1 className="mt-6 text-[36px] min-[400px]:text-[42px] font-semibold leading-[1.05] tracking-[-0.038em] text-[#203653] sm:text-[58px] lg:text-[68px] xl:text-[74px]">
            Your team&apos;s knowledge shouldn&apos;t leave when people do.
          </h1>

          {/* Lead Narrative */}
          <p className="mt-6 text-[17px] leading-[1.65] text-[#56657c] sm:text-[18.5px]">
            Projects are built on architectural decisions, team discussions, ownership and hard-won experience.
            Handover reconstructs that fragmented context from your tools, verifies what matters, and produces
            auditable handovers for incoming members.
          </p>

          {/* Action Buttons */}
          <div className="mt-9 flex flex-wrap items-center gap-3.5">
            <button
              onClick={handleGetStarted}
              className="group inline-flex h-12 items-center gap-2 rounded-[10px] bg-[#203653] px-6 text-[15px] font-semibold text-white shadow-[0_1px_0_rgba(255,255,255,0.1)_inset,0_8px_20px_-8px_rgba(32,54,83,0.5)] transition-all duration-200 hover:bg-[#2a4467] active:scale-[0.98] cursor-pointer"
            >
              <span>{mounted && user ? "Go to Workspace" : "Get started"}</span>
              <ArrowRight className="size-4 transition-transform duration-200 group-hover:translate-x-0.5" />
            </button>

            <button
              onClick={scrollToHow}
              className="group inline-flex h-12 items-center gap-2 rounded-[10px] border border-[#D9E1F0]/80 bg-white/80 px-4.5 text-[15px] font-semibold text-[#203653] shadow-xs backdrop-blur-xs transition hover:bg-white cursor-pointer"
            >
              <span>Discover how it works</span>
              <ArrowDown className="size-4 text-[#7997BE] transition-transform duration-200 group-hover:translate-y-0.5" />
            </button>
          </div>

          {/* Assurance Footnote */}
          <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px] text-[#718096]">
            <span className="flex items-center gap-1.5">
              <Plug className="size-3.5 text-[#315FBA]" />
              <span>GitHub · Jira · Slack · Documents</span>
            </span>
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="size-3.5 text-[#299B80]" />
              <span>Human-verified findings</span>
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
