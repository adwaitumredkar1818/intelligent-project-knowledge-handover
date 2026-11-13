import { useState } from 'react'
import { cn } from './ui'

export function Donut({ data, size = 150, thickness = 18, center }: { data: { label: string; value: number; color: string }[]; size?: number; thickness?: number; center?: React.ReactNode }) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1
  const r = (size - thickness) / 2
  const c = 2 * Math.PI * r
  let offset = 0
  const [hover, setHover] = useState<number | null>(null)
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#EDF1F8" strokeWidth={thickness} />
        {data.map((d, i) => {
          const len = (d.value / total) * c
          const el = (
            <circle key={d.label} cx={size / 2} cy={size / 2} r={r} fill="none" stroke={d.color} strokeWidth={hover === i ? thickness + 4 : thickness} strokeDasharray={`${Math.max(0, len - 2)} ${c}`} strokeDashoffset={-offset} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} className="cursor-pointer transition-all" />
          )
          offset += len
          return el
        })}
      </svg>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
        {hover !== null ? (<><span className="text-xl font-semibold text-navy">{data[hover].value}</span><span className="text-[11px] text-muted">{data[hover].label}</span></>) : center}
      </div>
    </div>
  )
}

export function Legend({ items, className }: { items: { label: string; value?: React.ReactNode; color: string }[]; className?: string }) {
  return (
    <ul className={cn('space-y-2', className)}>
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-2 text-[13px]">
          <span className="size-2.5 rounded-sm" style={{ background: i.color }} />
          <span className="flex-1 text-muted">{i.label}</span>
          {i.value !== undefined && <span className="font-medium text-navy">{i.value}</span>}
        </li>
      ))}
    </ul>
  )
}

export function LineChart({ labels, series, height = 200 }: { labels: string[]; series: { name: string; color: string; values: number[]; area?: boolean }[]; height?: number }) {
  const w = 600
  const pad = { l: 34, r: 8, t: 10, b: 24 }
  const max = Math.max(...series.flatMap((s) => s.values)) * 1.15 || 1
  const x = (i: number) => pad.l + (i * (w - pad.l - pad.r)) / Math.max(1, labels.length - 1)
  const y = (v: number) => pad.t + (1 - v / max) * (height - pad.t - pad.b)
  const [hi, setHi] = useState<number | null>(null)
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => Math.round(max * t))
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${w} ${height}`} className="w-full" preserveAspectRatio="none" style={{ height }} onMouseLeave={() => setHi(null)}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={w - pad.r} y1={y(t)} y2={y(t)} stroke="#EDF1F8" />
            <text x={pad.l - 8} y={y(t) + 4} textAnchor="end" fontSize="10" fill="#A0AEC0">{t}</text>
          </g>
        ))}
        {labels.map((l, i) => (i % Math.ceil(labels.length / 6) === 0 || i === labels.length - 1) && <text key={l} x={x(i)} y={height - 6} textAnchor="middle" fontSize="10" fill="#A0AEC0">{l}</text>)}
        {series.map((s) => {
          const d = s.values.map((v, i) => `${i ? 'L' : 'M'}${x(i)},${y(v)}`).join(' ')
          return (
            <g key={s.name}>
              {s.area && <path d={`${d} L${x(s.values.length - 1)},${y(0)} L${x(0)},${y(0)} Z`} fill={s.color} opacity="0.08" />}
              <path d={d} fill="none" stroke={s.color} strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
            </g>
          )
        })}
        {hi !== null && <line x1={x(hi)} x2={x(hi)} y1={pad.t} y2={height - pad.b} stroke="#C9D3E3" strokeDasharray="3 3" />}
        {hi !== null && series.map((s) => <circle key={s.name} cx={x(hi)} cy={y(s.values[hi])} r="4" fill="white" stroke={s.color} strokeWidth="2" />)}
        {labels.map((l, i) => <rect key={l} x={x(i) - (w / labels.length) / 2} y={0} width={w / labels.length} height={height} fill="transparent" onMouseEnter={() => setHi(i)} />)}
      </svg>
      {hi !== null && (
        <div className="pointer-events-none absolute top-1 rounded-lg border border-line bg-white px-2.5 py-1.5 text-xs shadow-pop" style={{ left: `clamp(0px, calc(${(x(hi) / w) * 100}% - 60px), calc(100% - 130px))` }}>
          <p className="mb-1 font-medium text-navy">{labels[hi]}</p>
          {series.map((s) => <p key={s.name} className="flex items-center gap-1.5 text-muted"><span className="size-2 rounded-full" style={{ background: s.color }} />{s.name}: <span className="font-medium text-navy">{s.values[hi]}</span></p>)}
        </div>
      )}
    </div>
  )
}

export function BarChart({ data, height = 180, color = '#315FBA' }: { data: { label: string; value: number; color?: string }[]; height?: number; color?: string }) {
  const max = Math.max(...data.map((d) => d.value)) || 1
  return (
    <div className="flex items-end gap-2" style={{ height }}>
      {data.map((d) => (
        <div key={d.label} className="group flex h-full flex-1 flex-col items-center justify-end gap-1.5">
          <span className="text-[11px] font-medium text-navy opacity-0 transition group-hover:opacity-100">{d.value}</span>
          <div className="w-full max-w-[28px] rounded-t-md transition-all group-hover:opacity-80" style={{ height: `${(d.value / max) * 78}%`, background: d.color ?? color }} />
          <span className="text-[10px] text-slate-400">{d.label}</span>
        </div>
      ))}
    </div>
  )
}

export function StackedBar({ segments, className }: { segments: { label: string; value: number; color: string }[]; className?: string }) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1
  return (
    <div className={cn('flex h-2.5 w-full gap-0.5 overflow-hidden rounded-full bg-slate-100', className)}>
      {segments.map((s) => s.value > 0 && <div key={s.label} title={`${s.label}: ${s.value}`} style={{ width: `${(s.value / total) * 100}%`, background: s.color }} />)}
    </div>
  )
}

export function Ring({ value, size = 56, color = '#315FBA', label }: { value: number; size?: number; color?: string; label?: React.ReactNode }) {
  const r = (size - 6) / 2
  const c = 2 * Math.PI * r
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#EDF1F8" strokeWidth="5" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="5" strokeLinecap="round" strokeDasharray={`${(value / 100) * c} ${c}`} className="transition-all duration-700" />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-navy">{label ?? `${value}%`}</span>
    </div>
  )
}
