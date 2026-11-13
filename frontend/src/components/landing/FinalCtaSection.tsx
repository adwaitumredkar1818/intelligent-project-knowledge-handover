"use client";

import React, { useEffect, useRef } from "react";
import { ArrowRight } from "lucide-react";
import { OrganicScene } from "../brand/OrganicScene";
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

export function FinalCtaSection() {
  const ref = useReveal<HTMLElement>();
  const { user } = useLiveApp();
  const router = useRouter();

  const handleAction = () => {
    if (user) {
      router.push("/overview");
    } else {
      router.push("/signup");
    }
  };

  return (
    <section ref={ref} className="px-4 pb-24 sm:px-8">
      <div className="reveal relative mx-auto max-w-[1240px] overflow-hidden rounded-[28px] border border-[#D9E1F0] bg-white px-6 py-16 text-center shadow-card transition-colors duration-500 hover:border-[#315FBA]/35 sm:py-24">
        {/* Theme B Monospaced Identifier */}
        <div className="absolute right-6 top-6 hidden font-mono text-[9.5px] uppercase tracking-[0.14em] text-[#7997BE]/60 sm:block">
          SEC_10 // CONTINUITY
        </div>

        {/* Ambient Breathing Gradient Background */}
        <div
          className="pointer-events-none absolute inset-0 animate-pulse-soft"
          style={{
            background:
              "radial-gradient(ellipse at 25% 100%, rgba(121,151,190,0.22), transparent 55%), radial-gradient(ellipse at 80% 0%, rgba(165,160,217,0.24), transparent 55%)",
          }}
        />

        <div className="relative mx-auto max-w-2xl">
          {/* Organic Continuity Bridge Visual */}
          <div className="relative mx-auto -mt-6 mb-6 max-w-[520px] sm:-mt-10">
            <div className="h-[150px] w-full sm:h-[180px]">
              <OrganicScene
                variant="continuity"
                className="h-full w-full"
                aria-label="Flowing structure connecting an outgoing and an incoming team member"
              />
            </div>
            <div className="pointer-events-none absolute inset-x-0 bottom-0 flex justify-between px-[12%] font-mono text-[10.5px] tracking-[0.1em] text-[#718096]">
              <span>outgoing</span>
              <span>incoming</span>
            </div>
          </div>

          <h2 className="text-[34px] font-semibold leading-[1.05] tracking-[-0.04em] text-[#203653] sm:text-[48px] lg:text-[52px]">
            The next person shouldn&apos;t have to start from zero.
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-[17px] leading-relaxed text-[#56657c]">
            Preserve what your team knows. Understand what your project needs.
            Keep every transition moving forward with verifiable provenance.
          </p>

          <button
            onClick={handleAction}
            className="group mt-10 inline-flex h-12 items-center gap-2 rounded-[10px] bg-[#203653] px-6 text-[15px] font-semibold text-white shadow-[0_1px_0_rgba(255,255,255,0.1)_inset,0_8px_20px_-8px_rgba(32,54,83,0.5)] transition-all duration-200 hover:bg-[#2a4467] active:scale-[0.98] cursor-pointer"
          >
            <span>{user ? "Open Project Workspace" : "Get started with Handover"}</span>
            <ArrowRight className="size-4 transition-transform duration-200 group-hover:translate-x-0.5" />
          </button>
        </div>
      </div>
    </section>
  );
}
