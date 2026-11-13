"use client";

import React, { type ReactNode } from "react";
import Link from "next/link";
import { GitBranch, ShieldCheck, Sparkles } from "lucide-react";
import { Logo } from "../brand";
import { OrganicScene } from "../brand/OrganicScene";

function TransferGraphic() {
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[440px]">
      <svg viewBox="0 0 460 460" className="absolute inset-0 h-full w-full" aria-hidden>
        <defs>
          <linearGradient id="bridge-grad" x1="0" x2="1">
            <stop offset="0" stopColor="#203653" />
            <stop offset="1" stopColor="#315FBA" />
          </linearGradient>
        </defs>
        {[60, 120, 180].map((r) => (
          <circle
            key={r}
            cx="230"
            cy="230"
            r={r}
            fill="none"
            stroke="#D9E1F0"
            strokeDasharray="2 6"
          />
        ))}
        {[
          [110, 150],
          [80, 250],
          [140, 320],
          [150, 210],
        ].map(([x, y], i) => (
          <line
            key={i}
            x1={x}
            y1={y}
            x2="190"
            y2="230"
            stroke="#A9B8D0"
            strokeWidth="1.2"
          />
        ))}
        {[
          [350, 150],
          [380, 250],
          [320, 320],
          [310, 210],
        ].map(([x, y], i) => (
          <line
            key={i}
            x1="270"
            y1="230"
            x2={x}
            y2={y}
            stroke="#A9BFE0"
            strokeWidth="1.2"
          />
        ))}
        <path
          d="M190 230 C 215 200, 245 200, 270 230"
          fill="none"
          stroke="url(#bridge-grad)"
          strokeWidth="3"
        />
        <path
          d="M190 230 C 215 260, 245 260, 270 230"
          fill="none"
          stroke="url(#bridge-grad)"
          strokeWidth="3"
          strokeDasharray="5 6"
        >
          <animate
            attributeName="stroke-dashoffset"
            from="22"
            to="0"
            dur="1.4s"
            repeatCount="indefinite"
          />
        </path>
        {[
          [110, 150],
          [80, 250],
          [140, 320],
          [150, 210],
        ].map(([x, y], i) => (
          <circle
            key={i}
            cx={x}
            cy={y}
            r="6"
            fill="#fff"
            stroke="#203653"
            strokeWidth="2"
          />
        ))}
        {[
          [350, 150],
          [380, 250],
          [320, 320],
          [310, 210],
        ].map(([x, y], i) => (
          <circle
            key={i}
            cx={x}
            cy={y}
            r="6"
            fill="#fff"
            stroke="#315FBA"
            strokeWidth="2"
          />
        ))}
        <circle cx="190" cy="230" r="19" fill="#203653" />
        <circle cx="270" cy="230" r="19" fill="#315FBA" />
        <text
          x="190"
          y="234"
          textAnchor="middle"
          fontSize="10"
          fontWeight="700"
          fill="#fff"
          letterSpacing="0.05em"
        >
          OUT
        </text>
        <text
          x="270"
          y="234"
          textAnchor="middle"
          fontSize="10"
          fontWeight="700"
          fill="#fff"
          letterSpacing="0.05em"
        >
          IN
        </text>
      </svg>

      {/* Floating Finding Badge */}
      <div className="absolute left-0 top-[12%] rounded-xl border border-white bg-white/95 p-3 shadow-pop">
        <p className="flex items-center gap-1.5 text-[11px] font-medium text-[#718096]">
          <GitBranch className="size-3 text-[#315FBA]" /> PR #412 · Slack · ADR-007
        </p>
        <p className="mt-1 text-[13px] font-semibold text-[#203653]">
          Decision reconstructed
        </p>
        <span className="mt-1.5 inline-flex items-center gap-1 rounded-md border border-dashed border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[11px] font-medium text-indigo-700">
          <Sparkles className="size-3" />
          AI confidence 94%
        </span>
      </div>

      {/* Floating Verification Badge */}
      <div className="absolute bottom-[10%] right-0 rounded-xl border border-white bg-white/95 p-3 shadow-pop">
        <p className="text-[11px] font-medium text-[#718096]">Human review</p>
        <p className="mt-1 flex items-center gap-1.5 text-[13px] font-semibold text-[#203653]">
          <ShieldCheck className="size-4 text-[#299B80]" />
          Verified by James O.
        </p>
        <div className="mt-2 h-1.5 w-36 rounded-full bg-slate-100 overflow-hidden">
          <div className="h-full w-[86%] rounded-full bg-[#299B80]" />
        </div>
      </div>
    </div>
  );
}

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-[1fr_1.05fr]">
      {/* Left Column: Form & Links */}
      <div className="flex flex-col px-6 py-8 sm:px-12 lg:px-16 justify-between">
        <div className="flex items-center justify-between">
          <Link href="/" className="w-fit" aria-label="Handover home">
            <Logo size={28} />
          </Link>
          <Link
            href="/"
            className="text-[13px] font-medium text-[#718096] hover:text-[#203653] transition"
          >
            ← Back to Home
          </Link>
        </div>

        <div className="mx-auto flex w-full max-w-[400px] flex-1 flex-col justify-center py-10">
          {children}
        </div>

        <p className="text-center text-xs text-[#718096] lg:text-left">
          © 2026 The Handover ·{" "}
          <Link href="/#security" className="hover:text-[#203653] transition">
            Security
          </Link>{" "}
          ·{" "}
          <Link href="/#faq" className="hover:text-[#203653] transition">
            Documentation
          </Link>
        </p>
      </div>

      {/* Right Column: Figma Make Ambient Graphic Panel */}
      <div className="relative hidden overflow-hidden bg-[#F6F8FC] lg:flex lg:flex-col lg:justify-center lg:p-14 border-l border-[#D9E1F0]/70">
        <div
          className="absolute inset-0 opacity-60"
          style={{
            backgroundImage: "radial-gradient(#D9E1F0 1.2px, transparent 1.2px)",
            backgroundSize: "22px 22px",
          }}
        />
        <div className="relative z-10 flex flex-col items-center">
          <TransferGraphic />
          <div className="mx-auto mt-8 max-w-md text-center">
            <h2 className="text-[22px] font-semibold tracking-[-0.025em] text-[#203653]">
              People change. Projects evolve. Knowledge continues.
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-[#56657c]">
              Handover reconstructs decisions, responsibilities and risks from your tools, then lets people verify them before anything is transferred.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
