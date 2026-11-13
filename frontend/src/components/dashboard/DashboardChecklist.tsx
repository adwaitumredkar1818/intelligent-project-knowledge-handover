"use client";

import React from "react";
import { CheckCircle2, ChevronRight } from "lucide-react";
import { Mono, cn } from "../ui";

export interface ChecklistStep {
  label: string;
  done: boolean;
  meta: string;
  onClick?: () => void;
}

export function DashboardChecklist({
  steps,
  className,
}: {
  steps: ChecklistStep[];
  className?: string;
}) {
  return (
    <ol className={cn("divide-y divide-line rounded-xl border border-line bg-white/60", className)}>
      {steps.map((c, i) => (
        <li
          key={c.label}
          onClick={c.onClick}
          className={cn(
            "flex items-center gap-3 px-4 py-3 transition-colors",
            c.onClick && "hover:bg-slate-50/70 cursor-pointer"
          )}
        >
          {c.done ? (
            <CheckCircle2 className="size-[18px] text-ok shrink-0" />
          ) : (
            <span className="flex size-[18px] shrink-0 items-center justify-center rounded-full border-[1.5px] border-slate-300 font-mono text-[10px] font-semibold text-slate-400">
              {i + 1}
            </span>
          )}
          <span
            className={cn(
              "flex-1 text-[13.5px]",
              c.done ? "text-muted line-through decoration-slate-300" : "font-medium text-navy"
            )}
          >
            {c.label}
          </span>
          <Mono className="text-[11.5px] text-muted shrink-0">{c.meta}</Mono>
          {c.onClick && <ChevronRight className="size-3.5 text-slate-400 shrink-0" />}
        </li>
      ))}
    </ol>
  );
}
