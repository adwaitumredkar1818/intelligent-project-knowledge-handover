"use client";

import React, { type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, ChevronRight } from "lucide-react";
import { Button, cn } from "../ui";

export function NextAction({
  title,
  body,
  cta,
  to,
  tone = "blue",
  onClick,
}: {
  title: string;
  body: string;
  cta: string;
  to?: string;
  tone?: "blue" | "amber" | "green";
  onClick?: () => void;
}) {
  const router = useRouter();
  const rail = { blue: "bg-brand", amber: "bg-warn", green: "bg-ok" }[tone];

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else if (to) {
      router.push(to);
    }
  };

  return (
    <div className="relative flex flex-col gap-3 overflow-hidden rounded-[14px] border border-line bg-white py-3.5 pl-5 pr-3.5 sm:flex-row sm:items-center shadow-card">
      <span className={cn("absolute inset-y-0 left-0 w-1", rail)} />
      <div className="flex-1 min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">
          Next best action
        </p>
        <p className="mt-0.5 text-[14px] font-semibold text-navy truncate">
          {title}
        </p>
        <p className="text-[12.5px] text-muted line-clamp-1">{body}</p>
      </div>
      <Button
        variant={tone === "amber" ? "primary" : "secondary"}
        iconRight={ArrowRight}
        onClick={handleClick}
        className="shrink-0 cursor-pointer"
      >
        {cta}
      </Button>
    </div>
  );
}

export function ViewLink({
  to,
  children = "View all",
}: {
  to: string;
  children?: ReactNode;
}) {
  return (
    <Link
      href={to}
      className="group flex shrink-0 items-center gap-0.5 text-[12.5px] font-semibold text-brand hover:underline"
    >
      <span>{children}</span>
      <ChevronRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}

export function ActivityTimeline({
  activities,
  limit = 5,
}: {
  activities: Array<{
    id: string;
    event_type: string;
    description: string;
    actor_name?: string | null;
    timestamp: string;
  }>;
  limit?: number;
}) {
  const items = activities.slice(0, limit);

  if (items.length === 0) {
    return (
      <div className="px-5 pb-5 text-xs text-muted sm:px-6">
        No recent activity recorded for this workspace.
      </div>
    );
  }

  return (
    <ol className="px-5 pb-5 sm:px-6">
      {items.map((t, i) => (
        <li key={t.id || i} className="relative flex gap-3 pb-3.5 last:pb-0">
          {i < items.length - 1 && (
            <span className="absolute left-[11px] top-6 h-[calc(100%-18px)] w-px bg-line" />
          )}
          <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold text-navy border border-line">
            {t.actor_name ? t.actor_name.charAt(0).toUpperCase() : "H"}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[13px] leading-snug text-navy">
              <span className="font-semibold">{t.actor_name || "System"}</span>{" "}
              <span className="text-[#4a5d7c]">{t.description}</span>
            </p>
            <p className="mt-0.5 truncate text-[11px] text-muted">
              Event: {t.event_type}
            </p>
          </div>
          <span className="shrink-0 font-mono text-[11px] text-slate-400">
            {t.timestamp
              ? new Date(t.timestamp).toLocaleDateString("en-GB", {
                  day: "numeric",
                  month: "short",
                })
              : ""}
          </span>
        </li>
      ))}
    </ol>
  );
}
