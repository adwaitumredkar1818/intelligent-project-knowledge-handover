"use client";

import React from "react";
import { MetricBand, Sparkline, type Tone } from "../ui";

export { MetricBand, Sparkline };
export type { Tone };

export interface DashboardKpiItem {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  tone?: Tone;
  spark?: number[];
  onClick?: () => void;
}

export function DashboardKpiBand({
  items,
  className,
}: {
  items: DashboardKpiItem[];
  className?: string;
}) {
  return <MetricBand items={items} className={className} />;
}
