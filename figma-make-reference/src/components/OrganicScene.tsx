import { useEffect, useRef } from 'react'

/*
 * Handover "Organic Knowledge Sphere" — a lightweight 3D renderer on Canvas 2D.
 * No WebGL dependency: geometry is projected with perspective, depth-sorted and shaded,
 * then layered with frosted-glass gradients. Loaded lazily from the landing page.
 */

export type SceneVariant = 'hero' | 'assemble' | 'network' | 'continuity' | 'reconstruct' | 'empty' | 'macro' | 'cinematic'
export type EmptyKind = 'project' | 'sources' | 'knowledge' | 'relationships' | 'ingestion'
type V3 = [number, number, number]
interface Node { p: V3; size: number; color: string; hub?: boolean; tag?: string }
interface Proj { x: number; y: number; z: number; s: number }

const C = { blue: '49,95,186', navy: '32,54,83', lav: '165,160,217', ai: '139,120,201', teal: '95,163,147', mint: '217,233,229', sky: '121,151,190' }
const NODE_COLORS = [C.blue, C.navy, C.lav, C.teal, C.sky, C.blue]

function rng(seed: number) {
  let a = seed
  return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296 }
}
const rotY = ([x, y, z]: V3, a: number): V3 => [x * Math.cos(a) + z * Math.sin(a), y, -x * Math.sin(a) + z * Math.cos(a)]
const rotX = ([x, y, z]: V3, a: number): V3 => [x, y * Math.cos(a) - z * Math.sin(a), y * Math.sin(a) + z * Math.cos(a)]
const norm = ([x, y, z]: V3): V3 => { const l = Math.hypot(x, y, z) || 1; return [x / l, y / l, z / l] }
const dist = (a: V3, b: V3) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2])
const smooth = (e0: number, e1: number, x: number) => { const t = Math.max(0, Math.min(1, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t) }

function sphereNodes(n: number, seed: number, tags: string[] = []) {
  const r = rng(seed)
  const nodes: Node[] = []
  const golden = Math.PI * (3 - Math.sqrt(5))
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2
    const rad = Math.sqrt(1 - y * y)
    const th = golden * i + (r() - 0.5) * 0.5
    const k = 0.8 + r() * 0.2
    nodes.push({ p: [Math.cos(th) * rad * k, y * k, Math.sin(th) * rad * k], size: 1.2 + r() * 1.6, color: NODE_COLORS[Math.floor(r() * NODE_COLORS.length)] })
  }
  for (let i = 0; i < Math.round(n * 0.18); i++) {
    const d = norm([r() - 0.5, r() - 0.5, r() - 0.5]); const k = 0.32 + r() * 0.3
    nodes.push({ p: [d[0] * k, d[1] * k, d[2] * k], size: 1 + r(), color: C.lav })
  }
  for (let i = 0; i < 7; i++) nodes[Math.floor(r() * n)].hub = true
  tags.forEach((t, i) => { const idx = Math.floor((i + 0.5) * (n / tags.length)); nodes[idx].tag = t; nodes[idx].hub = true; nodes[idx].p = norm(nodes[idx].p).map((v) => v * 0.97) as V3 })
  return nodes
}
function knnEdges(nodes: Node[], k: number, max: number) {
  const edges: [number, number][] = []
  const seen = new Set<string>()
  nodes.forEach((a, i) => {
    nodes.map((b, j) => ({ j, d: dist(a.p, b.p) })).filter((x) => x.j !== i && x.d < max).sort((x, y) => x.d - y.d).slice(0, k).forEach(({ j }) => {
      const key = i < j ? `${i}-${j}` : `${j}-${i}`
      if (!seen.has(key)) { seen.add(key); edges.push([i, j]) }
    })
  })
  return edges
}
/** Organic pathway: arc between two points that bows outward, so connections follow the sphere's surface. */
function arc(a: V3, b: V3, steps = 10, bow = 0.08): V3[] {
  const out: V3[] = []
  const la = Math.hypot(...a), lb = Math.hypot(...b)
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    const m: V3 = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]
    const target = (la + (lb - la) * t) * (1 + Math.sin(Math.PI * t) * bow)
    const n = norm(m); out.push([n[0] * target, n[1] * target, n[2] * target])
  }
  return out
}
function ribbons(count: number, seed: number) {
  const r = rng(seed)
  return Array.from({ length: count }, (_, k) => {
    const ph = r() * 6.28, ph2 = r() * 6.28, a = 0.35 + r() * 0.45, b = 0.1 + r() * 0.25, tilt = (r() - 0.5) * 1.2
    const pts: V3[] = []
    for (let i = 0; i <= 140; i++) {
      const t = (i / 140) * Math.PI * 2
      const lat = a * Math.sin(2 * t + ph) + b * Math.sin(3 * t + ph2)
      const rad = 0.96 + 0.035 * Math.sin(5 * t + ph)
      pts.push(rotX([Math.cos(t) * Math.cos(lat) * rad, Math.sin(lat) * rad, Math.sin(t) * Math.cos(lat) * rad], tilt))
    }
    return { pts, color: [C.lav, C.teal, C.blue, C.sky, C.ai][k % 5], width: 0.8 + r() * 1.4 }
  })
}

interface Pulse { e: number; t: number; dir: 1 | -1; speed: number }

export interface SceneProps {
  variant?: SceneVariant
  emptyKind?: EmptyKind
  progress?: number
  camZoom?: number
  camOffset?: [number, number]
  dark?: boolean
  showTags?: boolean
  className?: string
  accent?: string
  interactive?: boolean
  label?: string
}

export default function OrganicScene({
  variant = 'hero',
  emptyKind = 'knowledge',
  progress: controlledProgress,
  camZoom = 1,
  camOffset = [0, 0],
  dark = false,
  showTags,
  className,
  accent,
  interactive = true,
  label,
}: SceneProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const accentRef = useRef(accent)
  accentRef.current = accent
  const progRef = useRef(controlledProgress)
  progRef.current = controlledProgress
  const zoomRef = useRef(camZoom)
  zoomRef.current = camZoom
  const offRef = useRef(camOffset)
  offRef.current = camOffset
  const darkRef = useRef(dark)
  darkRef.current = dark

  useEffect(() => {
    const canvas = canvasRef.current!, wrap = wrapRef.current!
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const nav = navigator as Navigator & { deviceMemory?: number; connection?: { saveData?: boolean } }
    const lowPower = (nav.hardwareConcurrency ?? 8) <= 4 || (nav.deviceMemory ?? 8) <= 4 || !!nav.connection?.saveData
    let W = 0, H = 0, dpr = 1, detail: 'high' | 'mid' | 'low' = 'high'
    let geo = build('high')

    function build(level: 'high' | 'mid' | 'low') {
      const isEmpty = variant === 'empty'
      const n =
        variant === 'network' ? (level === 'high' ? 150 : 90)
        : variant === 'hero' || variant === 'macro' || variant === 'cinematic' ? (level === 'high' ? 96 : level === 'mid' ? 64 : 44)
        : variant === 'reconstruct' ? (level === 'low' ? 36 : 64)
        : variant === 'assemble' ? (level === 'low' ? 26 : 42)
        : isEmpty ? (emptyKind === 'project' ? 9 : emptyKind === 'knowledge' ? 14 : emptyKind === 'sources' ? 28 : 34)
        : 0
      const wantTags = showTags ?? ((variant === 'hero' || variant === 'cinematic') && level !== 'low')
      const tags = wantTags ? ['Decision', 'Responsibility', 'Risk', 'Dependency', 'Verified'] : []
      const nodes = variant === 'continuity' ? continuityNodes(level) : sphereNodes(n, variant === 'network' ? 7 : 3, tags)
      if (variant === 'assemble') nodes.forEach((nd) => { nd.p = [nd.p[0] * 2.02, nd.p[1] * 0.72, nd.p[2] * 0.75] })
      if (isEmpty && emptyKind === 'sources') {
        const clusters: V3[] = [[-1.35, -0.55, 0.2], [1.35, -0.5, -0.15], [-1.25, 0.65, -0.2], [1.3, 0.6, 0.2]]
        nodes.forEach((nd, idx) => {
          const c = clusters[idx % 4]
          nd.p = [c[0] + nd.p[0] * 0.28, c[1] + nd.p[1] * 0.28, c[2] + nd.p[2] * 0.28]
          nd.color = [C.navy, C.blue, C.lav, C.teal][idx % 4]
        })
      }
      const noEdges = variant === 'continuity' || (isEmpty && (emptyKind === 'project' || emptyKind === 'knowledge'))
      const edges = noEdges ? [] : knnEdges(nodes, variant === 'network' ? 3 : 2, variant === 'assemble' ? 0.95 : 0.62)
      const paths = edges.map(([a, b]) => arc(nodes[a].p, nodes[b].p, variant === 'network' ? 8 : 10))
      const rib =
        variant === 'hero' || variant === 'macro' || variant === 'cinematic' ? ribbons(level === 'high' ? 6 : level === 'mid' ? 4 : 3, 11)
        : variant === 'reconstruct' ? ribbons(3, 9)
        : variant === 'network' ? ribbons(4, 5)
        : []
      const r = rng(19)
      const scatter = nodes.map((nd) => {
        if (variant === 'reconstruct' || variant === 'cinematic') {
          const d = norm([nd.p[0] + (r() - 0.5) * 0.9, nd.p[1] + (r() - 0.5) * 0.9, nd.p[2] + (r() - 0.5) * 0.9])
          const k = 1.65 + r() * 0.95
          return [d[0] * k, d[1] * k, d[2] * k] as V3
        }
        return [(r() - 0.5) * 5.2, (r() - 0.5) * 2.4, (r() - 0.5) * 2] as V3
      })
      const stagger = nodes.map(() => r() * 0.35)
      const filaments = variant === 'continuity' ? Array.from({ length: level === 'low' ? 5 : 9 }, (_, i) => ({ off: (i / 8 - 0.5) * 1.1, ph: r() * 6.28, w: 0.7 + r() * 1.2, color: [C.blue, C.lav, C.teal, C.sky][i % 4] })) : []
      return { nodes, edges, paths, rib, scatter, stagger, filaments }
    }
    function continuityNodes(level: string) {
      const r = rng(23); const out: Node[] = []
      const per = level === 'low' ? 18 : 30
      for (const side of [-1, 1]) for (let i = 0; i < per; i++) {
        const d = norm([r() - 0.5, r() - 0.5, r() - 0.5]); const k = 0.18 + r() * 0.3
        out.push({ p: [side * 1.05 + d[0] * k, d[1] * k, d[2] * k], size: 1 + r() * 1.6, color: side < 0 ? (r() > 0.4 ? C.navy : C.sky) : r() > 0.4 ? C.blue : C.lav })
      }
      return out
    }

    const pulses: Pulse[] = []
    const resetPulses = () => {
      pulses.length = 0
      const count = variant === 'hero' || variant === 'macro' || variant === 'cinematic' ? 8 : variant === 'reconstruct' ? 5 : variant === 'network' ? 9 : variant === 'continuity' ? 6 : 0
      for (let i = 0; i < count; i++) pulses.push({ e: Math.floor(Math.random() * Math.max(1, geo.edges.length || geo.filaments.length)), t: Math.random(), dir: 1, speed: 0.18 + Math.random() * 0.22 })
    }

    function resize() {
      const rect = wrap.getBoundingClientRect()
      W = rect.width; H = rect.height
      dpr = Math.min(window.devicePixelRatio || 1, lowPower ? 1.25 : 2)
      canvas.width = Math.max(1, Math.round(W * dpr)); canvas.height = Math.max(1, Math.round(H * dpr))
      canvas.style.width = `${W}px`; canvas.style.height = `${H}px`
      const next = W < 520 ? 'low' : W < 760 || lowPower ? 'mid' : 'high'
      if (next !== detail) { detail = next; geo = build(detail); resetPulses() }
    }
    geo = build(detail); resetPulses()

    let rotYa = variant === 'network' ? 0.9 : variant === 'assemble' ? 0 : 0.6, tiltX = -0.22, targetTx = 0, targetTy = 0, px = 0, py = 0
    let progress = variant === 'assemble' ? 0 : 1
    const onPointer = (e: PointerEvent) => {
      if (!interactive) return
      const r = wrap.getBoundingClientRect()
      targetTx = ((e.clientY - r.top) / r.height - 0.5) * 0.35
      targetTy = ((e.clientX - r.left) / r.width - 0.5) * 0.5
    }
    const host = wrap.closest('section') ?? wrap
    host.addEventListener('pointermove', onPointer as EventListener)

    /** Rotate around a local centre (used for each person cluster) with only pointer parallax applied globally. */
    const projectLocal = (p: V3, origin: V3, cx: number, cy: number, R: number, spin: number): Proj => {
      let q = rotY([p[0] - origin[0], p[1] - origin[1], p[2] - origin[2]], spin)
      q = [q[0] + origin[0], q[1] + origin[1], q[2] + origin[2]]
      q = rotX(rotY(q, py * 0.5), -0.08 + px * 0.5)
      const s = 3.2 / (3.2 - q[2])
      return { x: cx + q[0] * R * s, y: cy + q[1] * R * s, z: q[2], s }
    }
    const project = (p: V3, cx: number, cy: number, R: number): Proj => {
      let q = rotY(p, rotYa + py)
      q = rotX(q, tiltX + px)
      const s = 3.2 / (3.2 - q[2])
      return { x: cx + q[0] * R * s, y: cy + q[1] * R * s, z: q[2], s }
    }

    function glassSphere(cx: number, cy: number, R: number, t: number, strength = 1) {
      const isDark = darkRef.current
      // Contact shadow
      const sh = ctx!.createRadialGradient(cx, cy + R * 1.16, 0, cx, cy + R * 1.16, R * 0.9)
      sh.addColorStop(0, `rgba(${isDark ? '8,15,28' : C.navy},${(isDark ? 0.36 : 0.14) * strength})`); sh.addColorStop(1, `rgba(${C.navy},0)`)
      ctx!.save(); ctx!.scale(1, 0.22); ctx!.fillStyle = sh; ctx!.beginPath(); ctx!.arc(cx, (cy + R * 1.16) / 0.22, R * 0.9, 0, Math.PI * 2); ctx!.fill(); ctx!.restore()
      // Frosted body
      const body = ctx!.createRadialGradient(cx - R * 0.35, cy - R * 0.42, R * 0.05, cx, cy, R)
      if (isDark) {
        body.addColorStop(0, `rgba(255,255,255,${0.22 * strength})`)
        body.addColorStop(0.5, `rgba(${C.blue},${0.18 * strength})`)
        body.addColorStop(0.84, `rgba(${C.lav},${0.22 * strength})`)
        body.addColorStop(1, `rgba(${C.sky},${0.34 * strength})`)
      } else {
        body.addColorStop(0, `rgba(255,255,255,${0.92 * strength})`)
        body.addColorStop(0.55, `rgba(237,242,250,${0.55 * strength})`)
        body.addColorStop(0.86, `rgba(${C.lav},${0.2 * strength})`)
        body.addColorStop(1, `rgba(${C.sky},${0.32 * strength})`)
      }
      ctx!.fillStyle = body; ctx!.beginPath(); ctx!.arc(cx, cy, R, 0, Math.PI * 2); ctx!.fill()
      // Breathing internal illumination
      const breath = 0.75 + Math.sin(t * 0.45) * 0.25
      const glow = ctx!.createRadialGradient(cx + R * 0.1, cy + R * 0.12, 0, cx, cy, R * 0.85)
      glow.addColorStop(0, `rgba(${C.lav},${(isDark ? 0.42 : 0.34) * breath * strength})`); glow.addColorStop(0.5, `rgba(${isDark ? C.teal : C.mint},${0.26 * breath * strength})`); glow.addColorStop(1, `rgba(${C.mint},0)`)
      ctx!.fillStyle = glow; ctx!.beginPath(); ctx!.arc(cx, cy, R, 0, Math.PI * 2); ctx!.fill()
    }
    function glassHighlights(cx: number, cy: number, R: number, strength = 1) {
      const hl = ctx!.createRadialGradient(cx - R * 0.42, cy - R * 0.5, 0, cx - R * 0.42, cy - R * 0.5, R * 0.55)
      hl.addColorStop(0, `rgba(255,255,255,${0.75 * strength})`); hl.addColorStop(1, 'rgba(255,255,255,0)')
      ctx!.fillStyle = hl; ctx!.beginPath(); ctx!.arc(cx, cy, R, 0, Math.PI * 2); ctx!.fill()
      const rim = ctx!.createLinearGradient(cx, cy - R, cx, cy + R)
      rim.addColorStop(0, `rgba(255,255,255,${0.95 * strength})`); rim.addColorStop(0.6, `rgba(${C.lav},${0.45 * strength})`); rim.addColorStop(1, `rgba(${C.blue},${0.35 * strength})`)
      ctx!.strokeStyle = rim; ctx!.lineWidth = 1.2; ctx!.beginPath(); ctx!.arc(cx, cy, R, 0, Math.PI * 2); ctx!.stroke()
    }
    /** Translucent acrylic discs intersecting the sphere, giving layered depth. */
    function frostedLayers(cx: number, cy: number, R: number, t: number, back: boolean) {
      for (let i = 0; i < 2; i++) {
        const a = t * 0.06 * (i ? -1 : 1) + i * 1.3 + rotYa * 0.3
        ctx!.save(); ctx!.translate(cx, cy); ctx!.rotate(a * 0.35 + (i ? 0.6 : -0.35))
        const ry = R * (0.22 + 0.06 * Math.sin(t * 0.2 + i))
        ctx!.beginPath(); ctx!.ellipse(0, 0, R * 0.94, ry, 0, back ? Math.PI : 0, back ? Math.PI * 2 : Math.PI)
        ctx!.strokeStyle = `rgba(255,255,255,${back ? 0.28 : 0.7})`; ctx!.lineWidth = 1; ctx!.stroke()
        if (!back) { ctx!.beginPath(); ctx!.ellipse(0, 0, R * 0.94, ry, 0, 0, Math.PI * 2); ctx!.fillStyle = `rgba(255,255,255,0.09)`; ctx!.fill() }
        ctx!.restore()
      }
    }
    function strokePath(pts: Proj[], color: string, alpha: number, width: number) {
      ctx!.beginPath(); pts.forEach((p, i) => (i ? ctx!.lineTo(p.x, p.y) : ctx!.moveTo(p.x, p.y)))
      ctx!.strokeStyle = `rgba(${color},${alpha})`; ctx!.lineWidth = width; ctx!.stroke()
    }
    function dot(x: number, y: number, r: number, color: string, alpha: number, halo = 0) {
      if (halo) { const g = ctx!.createRadialGradient(x, y, 0, x, y, r * halo); g.addColorStop(0, `rgba(${color},${alpha * 0.35})`); g.addColorStop(1, `rgba(${color},0)`); ctx!.fillStyle = g; ctx!.beginPath(); ctx!.arc(x, y, r * halo, 0, Math.PI * 2); ctx!.fill() }
      ctx!.fillStyle = `rgba(${color},${alpha})`; ctx!.beginPath(); ctx!.arc(x, y, r, 0, Math.PI * 2); ctx!.fill()
    }
    function pointOnPath(pts: Proj[], t: number) {
      const f = t * (pts.length - 1); const i = Math.min(pts.length - 2, Math.floor(f)); const k = f - i
      return { x: pts[i].x + (pts[i + 1].x - pts[i].x) * k, y: pts[i].y + (pts[i + 1].y - pts[i].y) * k, z: pts[i].z + (pts[i + 1].z - pts[i].z) * k }
    }

    function drawNetwork(t: number, dt: number, cx: number, cy: number, R: number, opts: { shell: boolean; tags: boolean; edgeAlpha: number }) {
      const isMorph = variant === 'assemble' || variant === 'reconstruct' || variant === 'cinematic'
      const isEmpty = variant === 'empty'
      const shellStrength = variant === 'reconstruct' || variant === 'cinematic' ? smooth(0.45, 0.95, progress) : isEmpty && emptyKind === 'knowledge' ? 0.65 : isEmpty && emptyKind === 'ingestion' ? 0.55 : 1
      const proj = geo.nodes.map((n, i) => {
        if (isEmpty && emptyKind === 'ingestion' && n.p[1] < 0) {
          const drift = Math.sin(t * 0.7 + i) * 0.06
          return project([n.p[0] * 1.45, n.p[1] * 1.55 - 0.25 + drift, n.p[2] * 1.45], cx, cy, R)
        }
        if (isEmpty && emptyKind === 'project') {
          const drift = Math.sin(t * 0.6 + i * 1.3) * 0.08
          return project([n.p[0] * 1.2 + drift, n.p[1] * 1.2 - drift, n.p[2] * 1.2], cx, cy, R)
        }
        if (!isMorph) return project(n.p, cx, cy, R)
        const span = variant === 'cinematic' ? 0.42 : 0.65
        const local = Math.max(0, Math.min(1, (progress - geo.stagger[i] * (variant === 'cinematic' ? 0.5 : 1)) / span))
        const e = 1 - Math.pow(1 - local, 3)
        const s = geo.scatter[i]
        const p: V3 = [s[0] + (n.p[0] - s[0]) * e, s[1] + (n.p[1] - s[1]) * e + Math.sin(t * 0.6 + i) * 0.03 * (1 - e), s[2] + (n.p[2] - s[2]) * e]
        return project(p, cx, cy, R)
      })
      if (opts.shell && shellStrength > 0.02) glassSphere(cx, cy, R, t, shellStrength)
      if (opts.shell && shellStrength > 0.15) frostedLayers(cx, cy, R, t, true)
      if (isEmpty && (emptyKind === 'project' || emptyKind === 'sources' || emptyKind === 'relationships')) {
        ctx!.save()
        ctx!.setLineDash([4, 6])
        ctx!.strokeStyle = darkRef.current ? 'rgba(165,160,217,0.35)' : 'rgba(121,151,190,0.45)'
        ctx!.lineWidth = 1.1
        ctx!.beginPath(); ctx!.arc(cx, cy, R * (emptyKind === 'sources' ? 0.56 : 0.92), 0, Math.PI * 2); ctx!.stroke()
        if (emptyKind === 'sources') {
          for (const ang of [0.45, 2.65, -0.5, -2.6]) {
            ctx!.beginPath()
            ctx!.moveTo(cx + Math.cos(ang) * R * 1.12, cy + Math.sin(ang) * R * 0.72)
            ctx!.lineTo(cx + Math.cos(ang) * R * 0.64, cy + Math.sin(ang) * R * 0.52)
            ctx!.stroke()
          }
        }
        ctx!.restore()
      }
      if (variant === 'assemble') {
        const form = smooth(0.5, 1, progress)
        if (form > 0.01) { ctx!.save(); ctx!.translate(cx, cy); ctx!.scale(2.18, 0.8); glassSphere(0, 0, R * 1.04, t, form * 0.85); ctx!.restore() }
      }
      const pathProj = geo.paths.map((path) => path.map((p) => {
        if (variant !== 'assemble') return project(p, cx, cy, R)
        return project(p, cx, cy, R)
      }))
      // Organic flowing ribbons
      const ribScale = variant === 'reconstruct' || variant === 'cinematic' ? smooth(0.45, 0.92, progress) : 1
      if (ribScale > 0.02) for (const rb of geo.rib) {
        const pp = rb.pts.map((p) => project(p, cx, cy, R))
        for (let i = 1; i < pp.length; i++) {
          const z = (pp[i].z + pp[i - 1].z) / 2
          ctx!.beginPath(); ctx!.moveTo(pp[i - 1].x, pp[i - 1].y); ctx!.lineTo(pp[i].x, pp[i].y)
          ctx!.strokeStyle = `rgba(${rb.color},${(0.08 + smooth(-1, 1, z) * 0.34) * ribScale})`; ctx!.lineWidth = rb.width * (0.7 + smooth(-1, 1, z) * 0.6); ctx!.stroke()
        }
      }
      // Pathways, back to front
      const assembled = variant === 'assemble' ? smooth(0.55, 1, progress) : variant === 'reconstruct' || variant === 'cinematic' ? smooth(0.22, 0.82, progress) : 1
      const order = geo.edges.map((e, i) => ({ i, z: (proj[e[0]].z + proj[e[1]].z) / 2 })).sort((a, b) => a.z - b.z)
      for (const { i, z } of order) {
        const [a, b] = geo.edges[i]
        if (isEmpty && emptyKind === 'ingestion' && (geo.nodes[a].p[1] < 0 || geo.nodes[b].p[1] < 0)) continue
        const depth = smooth(-1, 1, z)
        const alpha = (0.06 + depth * 0.32) * opts.edgeAlpha * assembled
        if (alpha < 0.01) continue
        if (isEmpty && emptyKind === 'relationships') {
          const pa = pathProj[i]
          strokePath(pa.slice(0, 4), C.sky, alpha * 1.15, 0.85)
          strokePath(pa.slice(-4), C.sky, alpha * 1.15, 0.85)
          continue
        }
        const pts = (variant === 'assemble' || variant === 'reconstruct' || variant === 'cinematic') && progress < 0.88 ? [proj[a], proj[b]] : pathProj[i]
        strokePath(pts, depth > 0.55 ? (darkRef.current ? C.lav : C.blue) : C.sky, alpha * (darkRef.current ? 1.35 : 1), 0.6 + depth * 0.5)
      }
      if (opts.shell && shellStrength > 0.15) frostedLayers(cx, cy, R, t, false)
      // Light travelling along pathways
      const acc = accentRef.current ?? C.blue
      const canPulse = !reduced && variant !== 'assemble' && !isEmpty && (variant !== 'reconstruct' && variant !== 'cinematic' || progress > 0.5)
      if (canPulse && geo.edges.length > 0) for (const pl of pulses) {
        pl.t += pl.speed * dt
        if (pl.t > 1) {
          const end = geo.edges[pl.e][pl.dir === 1 ? 1 : 0]
          const nexts = geo.edges.map((e, i) => ({ e, i })).filter(({ e, i }) => i !== pl.e && (e[0] === end || e[1] === end))
          const pick = nexts.length ? nexts[Math.floor(Math.random() * nexts.length)] : { e: geo.edges[Math.floor(Math.random() * geo.edges.length)], i: Math.floor(Math.random() * geo.edges.length) }
          pl.e = pick.i; pl.dir = pick.e[0] === end ? 1 : -1; pl.t = 0
        }
        const path = pathProj[pl.e]; if (!path) continue
        const tt = pl.dir === 1 ? pl.t : 1 - pl.t
        const head = pointOnPath(path, tt)
        const depth = smooth(-1, 1, head.z)
        const tail = pointOnPath(path, Math.max(0, Math.min(1, pl.dir === 1 ? tt - 0.35 : tt + 0.35)))
        const g = ctx!.createLinearGradient(tail.x, tail.y, head.x, head.y)
        g.addColorStop(0, `rgba(${acc},0)`); g.addColorStop(1, `rgba(${acc},${0.75 * depth})`)
        ctx!.beginPath(); ctx!.moveTo(tail.x, tail.y); ctx!.lineTo(head.x, head.y); ctx!.strokeStyle = g; ctx!.lineWidth = 1.6; ctx!.stroke()
        dot(head.x, head.y, 1.8 + depth, '255,255,255', 0.9 * depth, 0)
        dot(head.x, head.y, 1.3 + depth * 0.8, acc, 0.9 * depth, 5)
      }
      // Nodes
      const nOrder = proj.map((p, i) => ({ p, i })).sort((a, b) => a.p.z - b.p.z)
      for (const { p, i } of nOrder) {
        const n = geo.nodes[i]
        const depth = smooth(-1, 1, p.z)
        const wob = reduced ? 0 : Math.sin(t * 0.8 + i * 1.7) * 0.35
        const r = (n.size + wob * 0.4) * p.s * (n.hub ? 1.5 : 1) * (W < 520 ? 0.85 : 1)
        if ((variant === 'assemble' || variant === 'reconstruct' || variant === 'cinematic') && progress < 0.96) {
          // Scattered information elements: frosted glass beads that settle into the structure.
          const beadR = r * 2.4
          const g = ctx!.createRadialGradient(p.x - beadR * 0.3, p.y - beadR * 0.35, 0, p.x, p.y, beadR)
          g.addColorStop(0, 'rgba(255,255,255,0.95)'); g.addColorStop(0.7, `rgba(${n.color},0.18)`); g.addColorStop(1, `rgba(${n.color},0.35)`)
          ctx!.fillStyle = g; ctx!.beginPath(); ctx!.arc(p.x, p.y, beadR * (1 - assembled * 0.55), 0, Math.PI * 2); ctx!.fill()
        }
        dot(p.x, p.y, r, n.color, 0.25 + depth * 0.7, n.hub ? 4.2 : 0)
        if (n.hub && depth > 0.5) { ctx!.strokeStyle = `rgba(${n.color},${(depth - 0.5) * 0.7})`; ctx!.lineWidth = 0.8; ctx!.beginPath(); ctx!.arc(p.x, p.y, r * 2.6, 0, Math.PI * 2); ctx!.stroke() }
      }
      if (opts.shell && shellStrength > 0.05) glassHighlights(cx, cy, R, shellStrength)
      if (variant === 'assemble') { const form = smooth(0.6, 1, progress); if (form > 0.01) { ctx!.save(); ctx!.translate(cx, cy); ctx!.scale(2.18, 0.8); glassHighlights(0, 0, R * 1.04, form * 0.7); ctx!.restore() } }
      // Story labels anchored to knowledge nodes; they fade as their node turns away.
      const tagAlpha = variant === 'cinematic' ? smooth(0.78, 0.96, progress) : 1
      if (opts.tags && tagAlpha > 0.02) for (const { p, i } of nOrder) {
        const n = geo.nodes[i]; if (!n.tag) continue
        const vis = smooth(0.25, 0.75, p.z) * tagAlpha; if (vis < 0.03) continue
        const side = p.x > cx ? 1 : -1
        const lx = p.x + side * 26, ly = p.y - 14
        const isDark = darkRef.current
        ctx!.globalAlpha = vis
        ctx!.strokeStyle = isDark ? 'rgba(217,225,240,0.45)' : 'rgba(32,54,83,0.35)'; ctx!.lineWidth = 0.8; ctx!.beginPath(); ctx!.moveTo(p.x + side * 5, p.y - 3); ctx!.lineTo(lx, ly); ctx!.stroke()
        ctx!.font = '600 11.5px Manrope, Inter, sans-serif'
        const tw = ctx!.measureText(n.tag).width
        const bx = side > 0 ? lx : lx - tw - 22
        ctx!.fillStyle = isDark ? 'rgba(22,38,62,0.9)' : 'rgba(255,255,255,0.88)'; roundRect(bx, ly - 11, tw + 22, 22, 11); ctx!.fill()
        ctx!.strokeStyle = isDark ? 'rgba(121,151,190,0.45)' : 'rgba(217,225,240,1)'; ctx!.stroke()
        dot(bx + 9, ly, 2.6, n.tag === 'Verified' ? '41,155,128' : n.tag === 'Risk' ? '211,109,114' : n.tag === 'Dependency' ? '211,155,67' : C.blue, 1)
        ctx!.fillStyle = isDark ? '#F6F8FC' : '#203653'; ctx!.fillText(n.tag, bx + 16, ly + 4)
        ctx!.globalAlpha = 1
      }
    }
    function roundRect(x: number, y: number, w: number, h: number, r: number) {
      ctx!.beginPath(); ctx!.moveTo(x + r, y); ctx!.arcTo(x + w, y, x + w, y + h, r); ctx!.arcTo(x + w, y + h, x, y + h, r); ctx!.arcTo(x, y + h, x, y, r); ctx!.arcTo(x, y, x + w, y, r); ctx!.closePath()
    }

    function drawContinuity(t: number, dt: number) {
      const cx = W / 2, cy = H / 2, R = Math.min(W / 5.4, H / 1.9)
      for (const side of [-1, 1]) glassSphere(cx + side * R * 1.05, cy, R * 0.52, t + side, 0.9)
      // Flowing filaments joining the two people
      const fil = geo.filaments.map((f) => {
        const pts: Proj[] = []
        for (let i = 0; i <= 40; i++) {
          const u = i / 40
          const x = -1.05 + u * 2.1
          const y = Math.sin(u * Math.PI) * f.off * 0.85 + (reduced ? 0 : Math.sin(t * 0.5 + f.ph + u * 3) * 0.05)
          const z = Math.cos(u * Math.PI * 2 + f.ph) * 0.18
          pts.push(projectLocal([x, y, z], [0, 0, 0], cx, cy, R, 0))
        }
        return pts
      })
      geo.filaments.forEach((f, k) => strokePath(fil[k], f.color, 0.42, f.w))
      const proj = geo.nodes.map((n) => projectLocal(n.p, [n.p[0] < 0 ? -1.05 : 1.05, 0, 0], cx, cy, R, rotYa * (n.p[0] < 0 ? 1 : -1)))
      proj.map((p, i) => ({ p, i })).sort((a, b) => a.p.z - b.p.z).forEach(({ p, i }) => dot(p.x, p.y, geo.nodes[i].size * p.s, geo.nodes[i].color, 0.35 + smooth(-1, 1, p.z) * 0.6))
      if (!reduced) for (const pl of pulses) {
        pl.t += pl.speed * dt * 0.8
        if (pl.t > 1) { pl.t = 0; pl.e = Math.floor(Math.random() * fil.length) }
        const path = fil[pl.e % fil.length]; const h = pointOnPath(path, pl.t)
        dot(h.x, h.y, 2, C.blue, 0.85, 5)
      }
      for (const side of [-1, 1]) glassHighlights(cx + side * R * 1.05, cy, R * 0.52, 0.9)
    }

    let raf = 0, last = performance.now(), start = last, visible = true, running = true
    const minFrame = lowPower ? 1000 / 30 : 0
    function frame(now: number) {
      if (!running) return
      raf = requestAnimationFrame(frame)
      if (!visible || now - last < minFrame) return
      const dt = Math.min(0.05, (now - last) / 1000); last = now
      const t = (now - start) / 1000
      render(t, dt)
    }
    function render(t: number, dt: number) {
      if (variant === 'assemble') {
        if (progRef.current !== undefined) progress += (progRef.current - progress) * Math.min(1, dt * 5)
        else {
          const r = wrap.getBoundingClientRect()
          const target = smooth(0.08, 0.82, (window.innerHeight - r.top) / (window.innerHeight * 0.55))
          progress += (target - progress) * Math.min(1, dt * 3)
        }
      } else if (variant === 'reconstruct' || variant === 'cinematic') {
        if (progRef.current !== undefined) progress += (progRef.current - progress) * Math.min(1, dt * 6)
        else {
          const cycle = (t % 6.5) / 6.5
          progress = cycle < 0.78 ? smooth(0, 0.72, cycle) : cycle < 0.92 ? 1 : 1 - smooth(0.92, 1, cycle)
        }
      }
      if (!reduced) {
        rotYa += dt * (variant === 'network' ? 0.035 : variant === 'assemble' ? 0 : 0.05)
        px += (targetTx - px) * Math.min(1, dt * 2.2); py += (targetTy - py) * Math.min(1, dt * 2.2)
      }
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx!.clearRect(0, 0, W, H)
      const float = reduced ? 0 : Math.sin(t * 0.55) * Math.min(8, H * 0.012)
      const z = zoomRef.current
      const [ox, oy] = offRef.current
      const cx = W * (0.5 + ox), cy = H * (0.5 + oy) + float
      if (variant === 'hero') drawNetwork(t, dt, cx, cy, Math.min(W, H) * 0.34 * z, { shell: true, tags: showTags ?? true, edgeAlpha: 1 })
      else if (variant === 'macro') drawNetwork(t, dt, W * (0.34 + ox), H * (0.56 + oy) + float * 0.5, Math.min(W, H) * 0.62 * z, { shell: true, tags: false, edgeAlpha: 1.35 })
      else if (variant === 'reconstruct') drawNetwork(t, dt, cx, cy, Math.min(W, H) * 0.33 * z, { shell: true, tags: showTags ?? false, edgeAlpha: 1.15 })
      else if (variant === 'cinematic') {
        const p = progress
        const cz = p < 0.2 ? 0.92 + p * 0.8 : p < 0.45 ? 1.08 + smooth(0.2, 0.45, p) * 0.48 : p < 0.7 ? 1.56 - smooth(0.45, 0.7, p) * 0.38 : 1.18 - smooth(0.7, 1, p) * 0.18
        const cox = p >= 0.35 && p <= 0.72 ? -0.1 * Math.sin(((p - 0.35) / 0.37) * Math.PI) : 0
        drawNetwork(t, dt, W * (0.5 + cox + ox), cy, Math.min(W, H) * 0.34 * cz * z, { shell: true, tags: true, edgeAlpha: 1.2 })
      }
      else if (variant === 'empty') drawNetwork(t, dt, cx, cy, Math.min(W, H) * 0.32 * z, { shell: emptyKind === 'knowledge' || emptyKind === 'ingestion', tags: false, edgeAlpha: 1.1 })
      else if (variant === 'network') drawNetwork(t, dt, W * 0.62, H * 0.52, Math.max(W, H) * 0.55, { shell: false, tags: false, edgeAlpha: 1.25 })
      else if (variant === 'assemble') drawNetwork(t, dt, W / 2, H / 2 + float * 0.5, Math.min(W / 5.2, H / 2.3), { shell: false, tags: false, edgeAlpha: 1.4 })
      else drawContinuity(t, dt)
    }

    const ro = new ResizeObserver(() => { resize(); if (reduced || detail === 'low') render(2, 0.016) })
    ro.observe(wrap)
    resize()
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting })
    io.observe(wrap)
    const onVis = () => { visible = document.visibilityState === 'visible'; last = performance.now() }
    document.addEventListener('visibilitychange', onVis)
    const animate = !reduced && !((detail as string) === 'low' && variant !== 'assemble')
    if (animate) raf = requestAnimationFrame(frame)
    else { progress = progRef.current ?? 1; render(2, 0.016) }
    return () => { running = false; cancelAnimationFrame(raf); ro.disconnect(); io.disconnect(); document.removeEventListener('visibilitychange', onVis); host.removeEventListener('pointermove', onPointer as EventListener) }
  }, [variant, emptyKind, interactive, showTags])

  return (
    <div ref={wrapRef} className={className} role="img" aria-label={label ?? 'Organic knowledge sphere: interconnected project knowledge'}>
      <canvas ref={canvasRef} className="block h-full w-full" />
    </div>
  )
}
