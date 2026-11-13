"use client";

import React, { useState, type ReactNode } from "react";
import { cn } from "../../lib/utils";

export interface LineChartSeries {
  name: string;
  color: string;
  values: number[];
  area?: boolean;
}

export function LineChart({
  labels,
  series,
  height = 200,
}: {
  labels: string[];
  series: LineChartSeries[];
  height?: number;
}) {
  const w = 600;
  const pad = { l: 34, r: 8, t: 10, b: 24 };
  const allValues = series.flatMap((s) => s.values);
  const max = Math.max(1, ...allValues) * 1.15;
  const x = (i: number) => pad.l + (i * (w - pad.l - pad.r)) / Math.max(1, labels.length - 1);
  const y = (v: number) => pad.t + (1 - v / max) * (height - pad.t - pad.b);
  const [hi, setHi] = useState<number | null>(null);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => Math.round(max * t));

  return (
    <div className="relative select-none">
      <svg
        viewBox={`0 0 ${w} ${height}`}
        className="w-full overflow-visible"
        preserveAspectRatio="none"
        style={{ height }}
        onMouseLeave={() => setHi(null)}
        aria-label="Knowledge processing activity trend"
      >
        {/* Horizontal grid lines & ticks */}
        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={pad.l}
              x2={w - pad.r}
              y1={y(t)}
              y2={y(t)}
              stroke="#EDF1F8"
              strokeDasharray="2 2"
            />
            <text
              x={pad.l - 8}
              y={y(t) + 4}
              textAnchor="end"
              fontSize="10"
              className="fill-slate-400 font-mono"
            >
              {t}
            </text>
          </g>
        ))}

        {/* X-axis labels */}
        {labels.map(
          (l, i) =>
            (i % Math.ceil(labels.length / 6) === 0 || i === labels.length - 1) && (
              <text
                key={l + i}
                x={x(i)}
                y={height - 6}
                textAnchor="middle"
                fontSize="10"
                className="fill-slate-400 font-mono"
              >
                {l}
              </text>
            )
        )}

        {/* Series area & lines */}
        {series.map((s) => {
          if (!s.values.length) return null;
          const d = s.values
            .map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`)
            .join(" ");
          return (
            <g key={s.name}>
              {s.area && (
                <path
                  d={`${d} L${x(s.values.length - 1)},${height - pad.b} L${x(0)},${
                    height - pad.b
                  } Z`}
                  fill={s.color}
                  opacity="0.1"
                />
              )}
              <path
                d={d}
                fill="none"
                stroke={s.color}
                strokeWidth="2.2"
                strokeLinejoin="round"
                strokeLinecap="round"
                vectorEffect="non-scaling-stroke"
              />
            </g>
          );
        })}

        {/* Hover hairline */}
        {hi !== null && (
          <line
            x1={x(hi)}
            x2={x(hi)}
            y1={pad.t}
            y2={height - pad.b}
            stroke="#C9D3E3"
            strokeDasharray="3 3"
          />
        )}

        {/* Hover points */}
        {hi !== null &&
          series.map((s) => (
            <circle
              key={s.name}
              cx={x(hi)}
              cy={y(s.values[hi] ?? 0)}
              r="4"
              fill="white"
              stroke={s.color}
              strokeWidth="2"
            />
          ))}

        {/* Hover trigger columns */}
        {labels.map((l, i) => (
          <rect
            key={l + i}
            x={x(i) - w / labels.length / 2}
            y={0}
            width={w / labels.length}
            height={height}
            fill="transparent"
            onMouseEnter={() => setHi(i)}
            className="cursor-crosshair"
          />
        ))}
      </svg>

      {/* Floating tooltip */}
      {hi !== null && (
        <div
          className="pointer-events-none absolute top-1 rounded-lg border border-line bg-white px-3 py-2 text-xs shadow-pop animate-fade"
          style={{
            left: `clamp(0px, calc(${(x(hi) / w) * 100}% - 60px), calc(100% - 140px))`,
          }}
        >
          <p className="mb-1.5 font-semibold text-navy">{labels[hi]}</p>
          {series.map((s) => (
            <p key={s.name} className="flex items-center gap-2 text-muted">
              <span
                className="size-2 rounded-full shrink-0"
                style={{ background: s.color }}
              />
              <span className="flex-1">{s.name}:</span>
              <span className="font-semibold text-navy font-mono">
                {s.values[hi] ?? 0}
              </span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

export function Ring({
  value,
  size = 56,
  color = "#315FBA",
  label,
}: {
  value: number;
  size?: number;
  color?: string;
  label?: ReactNode;
}) {
  const r = (size - 6) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, value));

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#EDF1F8"
          strokeWidth="6"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={`${(clamped / 100) * c} ${c}`}
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-navy">
        {label ?? `${Math.round(clamped)}%`}
      </span>
    </div>
  );
}

export function BarChart({
  data,
  height = 180,
  color = "#315FBA",
}: {
  data: { label: string; value: number; color?: string }[];
  height?: number;
  color?: string;
}) {
  const max = Math.max(1, ...data.map((d) => d.value));

  return (
    <div className="flex items-end gap-2" style={{ height }}>
      {data.map((d) => (
        <div
          key={d.label}
          className="group flex h-full flex-1 flex-col items-center justify-end gap-1.5"
        >
          <span className="text-[11px] font-mono font-medium text-navy opacity-0 transition group-hover:opacity-100">
            {d.value}
          </span>
          <div
            className="w-full max-w-[28px] rounded-t-md transition-all group-hover:opacity-85"
            style={{
              height: `${Math.max(4, (d.value / max) * 78)}%`,
              background: d.color ?? color,
            }}
          />
          <span className="text-[10.5px] text-slate-400 font-mono truncate max-w-full">
            {d.label}
          </span>
        </div>
      ))}
    </div>
  );
}

export function StackedBar({
  segments,
  className,
}: {
  segments: { label: string; value: number; color: string }[];
  className?: string;
}) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  return (
    <div
      className={cn(
        "flex h-2.5 w-full gap-0.5 overflow-hidden rounded-full bg-slate-100",
        className
      )}
    >
      {segments.map(
        (s) =>
          s.value > 0 && (
            <div
              key={s.label}
              title={`${s.label}: ${s.value}`}
              style={{
                width: `${(s.value / total) * 100}%`,
                background: s.color,
              }}
            />
          )
      )}
    </div>
  );
}

export function Legend({
  items,
  className,
}: {
  items: { label: string; value?: ReactNode; color: string }[];
  className?: string;
}) {
  return (
    <ul className={cn("space-y-2", className)}>
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-2 text-[13px]">
          <span
            className="size-2.5 rounded-xs shrink-0"
            style={{ background: i.color }}
          />
          <span className="flex-1 text-muted">{i.label}</span>
          {i.value !== undefined && (
            <span className="font-semibold text-navy font-mono">{i.value}</span>
          )}
        </li>
      ))}
    </ul>
  );
}
