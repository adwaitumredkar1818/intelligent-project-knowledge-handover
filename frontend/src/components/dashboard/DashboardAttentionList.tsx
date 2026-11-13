"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, ChevronRight, type LucideIcon } from "lucide-react";
import { Button, EmptyState, cn } from "../ui";

export interface AttentionItem {
  id?: string;
  tone: "amber" | "red" | "ai" | "blue";
  icon: LucideIcon;
  title: string;
  sub: string;
  cta: string;
  to: string;
}

export function DashboardAttentionList({
  items,
  max = 5,
  emptyTitle = "Nothing needs attention",
  emptyBody = "Approvals, sync failures and critical risks will appear here.",
}: {
  items: AttentionItem[];
  max?: number;
  emptyTitle?: string;
  emptyBody?: string;
}) {
  const router = useRouter();

  const toneRails: Record<string, string> = {
    amber: "bg-warn",
    red: "bg-bad",
    ai: "bg-ai",
    blue: "bg-brand",
  };

  const displayed = items.slice(0, max);

  if (displayed.length === 0) {
    return (
      <div className="py-2">
        <EmptyState
          className="py-8"
          icon={CheckCircle2}
          title={emptyTitle}
          body={emptyBody}
        />
      </div>
    );
  }

  return (
    <ul className="divide-y divide-line border-t border-line">
      {displayed.map((item, idx) => {
        const Icon = item.icon;
        return (
          <li
            key={item.id || item.title + idx}
            className="group relative flex items-center gap-3.5 px-5 py-3 transition-colors hover:bg-[#f9fbfe] sm:px-6"
          >
            <span
              className={cn(
                "absolute inset-y-3 left-0 w-[3px] rounded-r",
                toneRails[item.tone] || "bg-brand"
              )}
            />
            <Icon className="size-4 shrink-0 text-slate-400 group-hover:text-navy transition-colors" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13.5px] font-semibold text-navy">
                {item.title}
              </p>
              <p className="truncate text-[12px] text-muted">{item.sub}</p>
            </div>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => router.push(item.to)}
              className="shrink-0 text-xs"
            >
              <span>{item.cta}</span>
              <ChevronRight className="size-3.5" />
            </Button>
          </li>
        );
      })}
    </ul>
  );
}
