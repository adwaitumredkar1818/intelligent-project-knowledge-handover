"use client";

import React, { useState, useEffect } from "react";
import { Activity, Loader2, Filter, Clock } from "lucide-react";
import { Card, EmptyState, Badge, Avatar, cn } from "../ui";
import { api } from "../../lib/api";
import type { Project, ProjectActivityCard } from "../../lib/types";

const ACTIVITY_FILTERS = [
  "all",
  "knowledge",
  "evidence",
  "membership",
  "handover",
  "system",
];

export interface ProjectActivityTabProps {
  project: Project;
}

export function ProjectActivityTab({ project }: ProjectActivityTabProps) {
  const [items, setItems] = useState<ProjectActivityCard[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    let mounted = true;
    api.projects
      .getActivity(project.id, 50, 0)
      .then((res) => {
        if (!mounted) return;
        setItems(res.items);
      })
      .catch(() => {
        if (!mounted) return;
        setItems([]);
      })
      .finally(() => {
        if (mounted) setIsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [project.id]);

  const filteredItems = items.filter((item) => {
    if (filter === "all") return true;
    const type = (item.event_type || "").toLowerCase();
    return type.includes(filter);
  });

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Filter Pills */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-muted flex items-center gap-1.5 mr-1">
          <Filter className="size-3.5" />
          <span>Filter:</span>
        </span>
        {ACTIVITY_FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium capitalize transition-all cursor-pointer",
              filter === f
                ? "border-brand bg-tint text-brand shadow-2xs font-semibold"
                : "border-line bg-white text-muted hover:text-navy hover:border-slate-300"
            )}
          >
            {f === "all" ? "All Activity" : f}
          </button>
        ))}
      </div>

      {/* Main Activity Timeline Card */}
      <Card className="p-5 sm:p-6">
        {isLoading ? (
          <div className="flex items-center justify-center p-12 text-xs text-muted gap-2">
            <Loader2 className="size-4 animate-spin text-brand" />
            <span>Loading chronological activity stream...</span>
          </div>
        ) : filteredItems.length === 0 ? (
          <EmptyState
            icon={Activity}
            title="No activity recorded"
            body="Events appear here as team members configure handovers, connect sources, and verify reconstructed findings."
          />
        ) : (
          <ol className="space-y-0">
            {filteredItems.map((item, idx) => {
              const isSys = !item.actor_name || item.actor_name.toLowerCase() === "system";
              const dateStr = new Date(item.timestamp).toLocaleString("en-GB", {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              });

              return (
                <li key={item.id} className="relative flex gap-3.5 pb-6 last:pb-1">
                  {idx < filteredItems.length - 1 && (
                    <span className="absolute left-[13px] top-8 h-[calc(100%-20px)] w-px bg-line" />
                  )}

                  {isSys ? (
                    <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold text-slate-500 border border-line">
                      SYS
                    </span>
                  ) : (
                    <Avatar name={item.actor_name || undefined} size={28} />
                  )}

                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-navy leading-relaxed">
                      <span className="font-semibold">
                        {isSys ? "Platform System" : item.actor_name}
                      </span>{" "}
                      — {item.description}
                    </p>
                    <p className="mt-0.5 text-[11px] text-muted flex items-center gap-1">
                      <Clock className="size-3" />
                      <span>{dateStr}</span>
                    </p>
                  </div>

                  <div className="text-right shrink-0">
                    <Badge tone="gray" className="capitalize text-[10px]">
                      {item.event_type || "Activity"}
                    </Badge>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </Card>
    </div>
  );
}
