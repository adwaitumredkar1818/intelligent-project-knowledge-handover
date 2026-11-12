"use client";

import React from "react";
import { Info } from "lucide-react";

export function DemoBanner() {
  return (
    <aside
      aria-label="Demo notice"
      className="bg-[#253650] text-[#DCE3EB] border-b border-[#304563] text-xs py-1.5 px-4 flex items-center justify-between z-50 shrink-0 select-none"
    >
      <div className="flex items-center gap-2 font-mono">
        <span className="inline-flex items-center justify-center bg-[#C48A32] text-white px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase">
          Prototype
        </span>
        <span className="font-semibold text-white tracking-wide">
          DEMO WORKSPACE · SAMPLE DATA ONLY
        </span>
        <span className="hidden md:inline text-[#69778D]">|</span>
        <span className="hidden md:inline text-[#DCE3EB]/80 text-[11px]">
          Local frontend evaluation mode. All actions operate on isolated in-memory fixtures.
        </span>
      </div>
      <div className="flex items-center gap-2 text-[11px] text-[#249E91]">
        <Info className="w-3.5 h-3.5" aria-hidden="true" />
        <span className="hidden sm:inline font-medium">Zero backend modification</span>
      </div>
    </aside>
  );
}
