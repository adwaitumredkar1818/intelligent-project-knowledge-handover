"use client";

import React from "react";
import { Ring } from "./DashboardCharts";
import { Mono, StatusBadge } from "../ui";

export function HandoverProgressRing({
  code,
  status = "in_progress",
  progress = 0,
  assigneeName,
  scope,
  dueDate,
}: {
  code?: string;
  status?: string;
  progress?: number;
  assigneeName?: string;
  scope?: string;
  dueDate?: string;
}) {
  return (
    <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
      <Ring
        value={progress}
        size={84}
        label={<span className="text-[17px] font-bold font-mono">{Math.round(progress)}%</span>}
        color={progress >= 80 ? "#299B80" : progress >= 40 ? "#315FBA" : "#D39B43"}
      />
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          {code && <Mono className="text-[12px] text-muted">{code}</Mono>}
          <StatusBadge status={status} />
        </div>
        <h3 className="mt-1 text-[19px] font-semibold tracking-[-0.02em] text-navy truncate">
          Your handover {assigneeName ? `to ${assigneeName}` : "workspace"}
        </h3>
        <p className="mt-0.5 text-[13px] text-muted truncate">
          {scope || "Comprehensive project knowledge capture"}
          {dueDate && ` · target ${dueDate}`}
        </p>
      </div>
    </div>
  );
}
