'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Maximize2, Minus, Plus } from 'lucide-react'
import { cn } from './index'
import { evidence, personById, type Dependency } from '../../lib/figmaStore'
import { allFindings } from './domain'

export type NodeKind = 'Decision' | 'Task' | 'Risk' | 'Dependency' | 'Person' | 'Component' | 'Evidence'
export interface GNode { id: string; label: string; kind: NodeKind }
export const NODE_COLOR: Record<NodeKind, string> = { Decision: '#315FBA', Task: '#299B80', Risk: '#D36D72', Dependency: '#D39B43', Person: '#7997BE', Component: '#203653', Evidence: '#A0AEC0' }

export function buildGraph(pid: string) {
  const nodes = new Map<string, GNode>()
  const adj = new Map<string, Set<string>>()
  const add = (n: GNode) => { if (!nodes.has(n.id)) nodes.set(n.id, n); if (!adj.has(n.id)) adj.set(n.id, new Set()) }
  const link = (a: string, b: string) => { adj.get(a)?.add(b); adj.get(b)?.add(a) }
  for (const f of allFindings(pid)) {
    add({ id: f.id, label: f.title, kind: f.kind })
    add({ id: `p:${f.ownerId}`, label: personById(f.ownerId)?.name ?? f.ownerId, kind: 'Person' }); link(f.id, `p:${f.ownerId}`)
    for (const e of f.evidenceIds) { const ev = evidence.find((x) => x.id === e); if (ev) { add({ id: e, label: ev.ref, kind: 'Evidence' }); link(f.id, e) } }
    const comp = (f as unknown as { component?: string }).component
    if (comp) { add({ id: `c:${comp}`, label: comp, kind: 'Component' }); link(f.id, `c:${comp}`) }
    if (f.kind === 'Dependency') {
      const d = f as unknown as Dependency
      if (d.depType === 'Technical') for (const c of [d.from, d.to]) { add({ id: `c:${c}`, label: c, kind: 'Component' }); link(f.id, `c:${c}`) }
    }
  }
  return { nodes, adj }
}

export interface Viewport { k: number; x: number; y: number }

/** Radial focus layout: the selected node sits at the centre, direct relationships on an inner ring, second-degree on an outer ring. */
export function layoutFocus(nodes: Map<string, GNode>, adj: Map<string, Set<string>>, centerId: string, W: number, H: number, filter?: (n: GNode) => boolean) {
  const c = nodes.get(centerId) ?? [...nodes.values()][0]
  const pos = new Map<string, { x: number; y: number; ring: 0 | 1 | 2; parent?: string; more?: number }>()
  if (!c) return { c, pos }
  const cx = W / 2, cy = H / 2
  const n1 = [...(adj.get(c.id) ?? [])].map((id) => nodes.get(id)!).filter((n) => !filter || filter(n)).slice(0, 12)
  const n1ids = new Set(n1.map((n) => n.id))
  const n2: { node: GNode; parent: string }[] = []
  const hidden = new Map<string, number>()
  // Controlled density: at most 3 second-degree nodes per relationship; the rest are summarised as a count.
  for (const n of n1) {
    let k = 0
    for (const id of adj.get(n.id) ?? []) {
      if (id === c.id || n1ids.has(id) || n2.some((x) => x.node.id === id)) continue
      const node = nodes.get(id)!
      if (filter && !filter(node)) continue
      if (k < 3 && n2.length < 16) { n2.push({ node, parent: n.id }); k++ } else hidden.set(n.id, (hidden.get(n.id) ?? 0) + 1)
    }
  }
  const r1x = Math.min(W * 0.3, 320), r1y = Math.min(H * 0.3, 200), r2x = Math.min(W * 0.45, 480), r2y = H * 0.43
  pos.set(c.id, { x: cx, y: cy, ring: 0 })
  n1.forEach((n, i) => { const a = ((i + 0.5) / n1.length) * Math.PI * 2 - Math.PI / 2; pos.set(n.id, { x: cx + Math.cos(a) * r1x, y: cy + Math.sin(a) * r1y, ring: 1 }) })
  const per = new Map<string, number>(), seen = new Map<string, number>()
  n2.forEach(({ parent }) => per.set(parent, (per.get(parent) ?? 0) + 1))
  n2.forEach(({ node, parent }) => {
    const p = pos.get(parent)!
    const base = Math.atan2((p.y - cy) / r1y, (p.x - cx) / r1x)
    const k = seen.get(parent) ?? 0; seen.set(parent, k + 1)
    const a = base + (k - (per.get(parent)! - 1) / 2) * (0.9 / Math.max(2, n1.length / 2))
    pos.set(node.id, { x: Math.max(70, Math.min(W - 70, cx + Math.cos(a) * r2x)), y: Math.max(30, Math.min(H - 60, cy + Math.sin(a) * r2y)), ring: 2, parent })
  })
  for (const [id, n] of hidden) { const p = pos.get(id); if (p) (p as { more?: number }).more = n }
  return { c, pos }
}

export function KnowledgeCanvas({ pid, center, onSelect, filter, className, focusLabel = true }: { pid: string; center: string; onSelect: (id: string) => void; filter?: (n: GNode) => boolean; className?: string; focusLabel?: boolean }) {
  const { nodes, adj } = useMemo(() => buildGraph(pid), [pid])
  const boxRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ w: 900, h: 600 })
  useEffect(() => {
    const el = boxRef.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => { if (!e) return; const r = e.contentRect; if (r.width > 0 && r.height > 0) setSize({ w: Math.round(r.width), h: Math.round(r.height) }) })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  // One SVG unit = one CSS pixel, so labels stay at their designed size at every panel width.
  const W = size.w, H = size.h
  const { c, pos } = useMemo(() => layoutFocus(nodes, adj, center, W, H, filter), [nodes, adj, center, filter, W, H])
  const [vp, setVp] = useState<Viewport>({ k: 1, x: 0, y: 0 })
  const [hover, setHover] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const svgRef = useRef<SVGSVGElement>(null)
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null)
  useEffect(() => setVp({ k: 1, x: 0, y: 0 }), [center])
  useEffect(() => {
    const el = svgRef.current
    if (!el) return
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      setVp((v) => ({ ...v, k: Math.max(0.5, Math.min(2.4, v.k * (e.deltaY > 0 ? 0.92 : 1.08))) }))
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [])
  if (!c) return null
  const trunc = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1) + '…' : s)
  const edges: [string, string, number][] = []
  for (const [id, p] of pos) { if (p.ring === 1) edges.push([c.id, id, 1]); if (p.ring === 2 && p.parent) edges.push([p.parent, id, 2]) }
  const zoom = (f: number) => setVp((v) => ({ ...v, k: Math.max(0.5, Math.min(2.4, v.k * f)) }))
  return (
    <div ref={boxRef} className={cn('relative h-full w-full overflow-hidden', className)}>
      <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet" className={cn('h-full w-full touch-none select-none', isDragging ? 'cursor-grabbing' : 'cursor-grab')}
        onPointerDown={(e) => { if ((e.target as Element).closest('[data-node]')) return; (e.target as Element).setPointerCapture?.(e.pointerId); drag.current = { x: e.clientX, y: e.clientY, vx: vp.x, vy: vp.y }; setIsDragging(true) }}
        onPointerMove={(e) => { if (!drag.current) return; const r = svgRef.current!.getBoundingClientRect(); const s = W / r.width; setVp((v) => ({ ...v, x: drag.current!.vx + (e.clientX - drag.current!.x) * s, y: drag.current!.vy + (e.clientY - drag.current!.y) * s })) }}
        onPointerUp={() => { drag.current = null; setIsDragging(false) }} onPointerLeave={() => { drag.current = null; setIsDragging(false) }}
        role="img" aria-label={`Knowledge graph focused on ${c.label}`}>
        <g transform={`translate(${vp.x + (W / 2) * (1 - vp.k)} ${vp.y + (H / 2) * (1 - vp.k)}) scale(${vp.k})`} style={{ transition: isDragging ? 'none' : 'transform .3s cubic-bezier(.22,1,.36,1)' }}>
          {edges.map(([a, b, ring]) => { const A = pos.get(a)!, B = pos.get(b)!; const lit = hover === a || hover === b; const kind = nodes.get(b)!.kind; return <line key={`${a}-${b}`} x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke={ring === 1 ? NODE_COLOR[kind] : '#D9E1F0'} strokeOpacity={ring === 1 ? (lit ? 0.9 : 0.42) : lit ? 1 : 0.9} strokeWidth={ring === 1 ? 1.4 : 1} strokeDasharray={ring === 2 ? '3 4' : undefined} style={{ transition: 'all .45s cubic-bezier(.22,1,.36,1)' }} /> })}
          {[...pos.entries()].sort((a, b) => b[1].ring - a[1].ring).map(([id, p]) => {
            const n = nodes.get(id)!
            const col = NODE_COLOR[n.kind]
            const isC = p.ring === 0, lit = hover === id
            const label = trunc(n.label, isC ? 34 : p.ring === 1 ? 26 : 18)
            const lw = label.length * (isC ? 7.2 : p.ring === 1 ? 6.4 : 5.6) + (isC ? 24 : 16)
            return (
              <g key={id} data-node onClick={() => onSelect(id)} onMouseEnter={() => setHover(id)} onMouseLeave={() => setHover(null)} className="cursor-pointer" style={{ transform: `translate(${p.x}px, ${p.y}px)`, transition: 'transform .5s cubic-bezier(.22,1,.36,1)' }}>
                <g className="animate-fade-only">
                  <title>{`${n.kind}: ${n.label}`}</title>
                  {isC && <circle r="30" fill={col} opacity="0.08" />}
                  {isC && <circle r="21" fill="none" stroke={col} strokeOpacity="0.3" strokeWidth="1" />}
                  <circle r={isC ? 13 : p.ring === 1 ? (lit ? 10 : 8) : lit ? 6 : 4.5} fill={isC ? col : 'white'} stroke={col} strokeWidth={isC ? 0 : p.ring === 1 ? 2 : 1.5} style={{ transition: 'r .2s' }} />
                  {(isC || p.ring === 1 || lit) && (
                    <g transform={`translate(0 ${isC ? 32 : 20})`}>
                      <rect x={-lw / 2} y={0} width={lw} height={isC ? 26 : 21} rx={isC ? 8 : 6} fill="white" stroke={isC ? col : lit ? '#B9C7DE' : '#E1E7F1'} strokeWidth={isC ? 1.2 : 1} />
                      <text y={isC ? 17 : 14.2} textAnchor="middle" fontSize={isC ? 12.5 : 11.2} fontWeight={isC ? 700 : 600} fill="#203653" fontFamily="Manrope, Inter, sans-serif">{label}</text>
                    </g>
                  )}
                  {p.ring === 1 && p.more ? <g transform="translate(12 -14)"><rect x={0} y={-8} width={26} height={16} rx={8} fill="#EDF2FA" stroke="#D9E1F0" /><text x={13} y={3.5} textAnchor="middle" fontSize="9.5" fontWeight="600" fill="#4a5d7c" fontFamily="JetBrains Mono, monospace">+{p.more}</text></g> : null}
                  {p.ring === 2 && !lit && <text y={16} textAnchor="middle" fontSize="9.8" fill="#8796ae" fontFamily="Manrope, Inter, sans-serif">{label}</text>}
                </g>
              </g>
            )
          })}
          {focusLabel && <text x={W / 2} y={H / 2 - 40} textAnchor="middle" fontSize="10" fontWeight="700" letterSpacing="1.4" fill={NODE_COLOR[c.kind]} fontFamily="Manrope, Inter, sans-serif">{c.kind.toUpperCase()}</text>}
        </g>
      </svg>
      <div className="absolute right-3 top-3 flex items-center gap-0.5 rounded-[10px] border border-line bg-white/95 p-0.5 shadow-card backdrop-blur">
        <button onClick={() => zoom(0.85)} className="flex size-7 items-center justify-center rounded-md text-muted hover:bg-canvas hover:text-navy" aria-label="Zoom out"><Minus className="size-3.5" /></button>
        <span className="w-10 text-center font-mono text-[11px] text-muted">{Math.round(vp.k * 100)}%</span>
        <button onClick={() => zoom(1.18)} className="flex size-7 items-center justify-center rounded-md text-muted hover:bg-canvas hover:text-navy" aria-label="Zoom in"><Plus className="size-3.5" /></button>
        <span className="mx-0.5 h-4 w-px bg-line" />
        <button onClick={() => setVp({ k: 1, x: 0, y: 0 })} className="flex size-7 items-center justify-center rounded-md text-muted hover:bg-canvas hover:text-navy" aria-label="Fit to view"><Maximize2 className="size-3.5" /></button>
      </div>
    </div>
  )
}

export function DependencyFlow({ deps, onSelect, selected }: { deps: Dependency[]; onSelect: (id: string) => void; selected?: string }) {
  const froms = Array.from(new Set(deps.map((d) => d.from)))
  const tos = Array.from(new Set(deps.map((d) => d.to)))
  const rowH = 56, H = Math.max(froms.length, tos.length) * rowH + 40, W = 760
  const fy = (s: string) => 30 + froms.indexOf(s) * rowH + (H - 40 - froms.length * rowH) / 2 + rowH / 2
  const ty = (s: string) => 30 + tos.indexOf(s) * rowH + (H - 40 - tos.length * rowH) / 2 + rowH / 2
  const color = { Technical: '#315FBA', Task: '#299B80', External: '#D39B43' }
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: 560 }}>
      <text x="20" y="18" fontSize="11" fill="#A0AEC0" fontWeight="600">DEPENDS ON →</text>
      {deps.map((d) => {
        const y1 = fy(d.from), y2 = ty(d.to)
        const sel = selected === d.id
        return (
          <g key={d.id} className="cursor-pointer" onClick={() => onSelect(d.id)}>
            <path d={`M230 ${y1} C 380 ${y1}, 380 ${y2}, 530 ${y2}`} fill="none" stroke={d.blocking ? '#D36D72' : color[d.depType]} strokeWidth={sel ? 3.5 : 2} strokeDasharray={d.blocking ? '6 4' : undefined} opacity={selected && !sel ? 0.3 : 0.85} />
            <circle cx="530" cy={y2} r="4" fill={d.blocking ? '#D36D72' : color[d.depType]} />
          </g>
        )
      })}
      {froms.map((f) => <g key={f}><rect x="20" y={fy(f) - 18} width="210" height="36" rx="10" fill="white" stroke="#D9E1F0" /><text x="34" y={fy(f) + 4} fontSize="12" fontWeight="500" fill="#203653">{f.length > 28 ? f.slice(0, 27) + '…' : f}</text></g>)}
      {tos.map((t) => <g key={t}><rect x="530" y={ty(t) - 18} width="210" height="36" rx="10" fill="#F6F8FC" stroke="#D9E1F0" /><text x="544" y={ty(t) + 4} fontSize="12" fontWeight="500" fill="#203653">{t.length > 28 ? t.slice(0, 27) + '…' : t}</text></g>)}
    </svg>
  )
}
