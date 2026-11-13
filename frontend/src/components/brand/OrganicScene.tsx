"use client";

import { useEffect, useRef } from "react";

/*
 * Handover "Organic Knowledge Sphere" — High-Performance Canvas 2D 3D Renderer
 * Evolves the visual identity into an ambient, organic knowledge network with:
 * - Multi-clustered organic volumetric geometry (not a simple rigid sphere)
 * - Layered frosted-glass surfaces with subtle internal illumination
 * - Delicate curved connection pathways and traveling knowledge pulses
 * - Depth-sorted nodes, hubs, filaments, and floating metadata badges
 * - Full SSR safety, dynamic DPI capping, and zero heavy dependencies
 */

export type SceneVariant =
  | "hero"
  | "assemble"
  | "network"
  | "continuity"
  | "reconstruct"
  | "empty"
  | "macro"
  | "cinematic";

export type EmptyKind =
  | "project"
  | "sources"
  | "knowledge"
  | "relationships"
  | "ingestion";

export type DetailLevel = "high" | "mid" | "low";

type V3 = [number, number, number];

interface Node {
  p: V3;
  baseP: V3;
  size: number;
  color: string;
  hub?: boolean;
  tag?: string;
  phase: number;
  speed: number;
  cluster: number;
}

interface Proj {
  x: number;
  y: number;
  z: number;
  s: number;
}

const C = {
  blue: "49,95,186",      // Primary brand blue #315FBA
  navy: "32,54,83",       // Deep navy #203653
  lav: "165,160,217",     // Soft lavender #A5A0D9
  ai: "139,120,201",      // AI purple #8B78C9
  teal: "41,155,128",     // Verified green/teal #299B80
  mint: "217,233,229",    // Soft mint highlight #D9E9E5
  sky: "121,151,190",     // Ambient sky #7997BE
  white: "255,255,255",
};

const NODE_PALETTE = [C.blue, C.navy, C.lav, C.teal, C.sky, C.ai];

function rng(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rotY = ([x, y, z]: V3, a: number): V3 => [
  x * Math.cos(a) + z * Math.sin(a),
  y,
  -x * Math.sin(a) + z * Math.cos(a),
];

const rotX = ([x, y, z]: V3, a: number): V3 => [
  x,
  y * Math.cos(a) - z * Math.sin(a),
  y * Math.sin(a) + z * Math.cos(a),
];

const norm = ([x, y, z]: V3): V3 => {
  const l = Math.hypot(x, y, z) || 1;
  return [x / l, y / l, z / l];
};

const dist = (a: V3, b: V3) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);

const smooth = (e0: number, e1: number, x: number) => {
  const t = Math.max(0, Math.min(1, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
};

/*
 * Generates an organic, multi-clustered knowledge network
 * Distinct from a regular sphere: features asymmetric lobes, branching tendrils,
 * and interstitial micro-nodes representing project knowledge relationships.
 */
function organicNodes(n: number, seed: number, tags: string[] = [], variant: SceneVariant = "hero") {
  const r = rng(seed);
  const nodes: Node[] = [];

  // 3 Cluster centers representing interconnected knowledge domains
  const clusters: { center: V3; weight: number; radius: number }[] = [
    { center: [0.08, -0.04, 0.05], weight: 0.52, radius: 0.95 },   // Core Architecture & Decisions
    { center: [-0.42, 0.38, 0.22], weight: 0.26, radius: 0.65 },   // People & Ownership Lobe
    { center: [0.46, -0.32, -0.18], weight: 0.22, radius: 0.58 },  // Dependencies & Risks Lobe
  ];

  const golden = Math.PI * (3 - Math.sqrt(5));

  for (let i = 0; i < n; i++) {
    // Choose cluster based on weights
    const cr = r();
    const clusterIdx = cr < 0.52 ? 0 : cr < 0.78 ? 1 : 2;
    const cl = clusters[clusterIdx]!;

    const y = 1 - (i / Math.max(1, n - 1)) * 2;
    const rad = Math.sqrt(Math.max(0, 1 - y * y));
    const th = golden * i + (r() - 0.5) * 0.7;

    // Organic harmonic wave perturbation: non-uniform surface modulation
    const harm =
      1 +
      0.16 * Math.sin(3 * th) * Math.cos(2 * y * Math.PI) +
      0.11 * Math.cos(5 * th + r());

    const span = cl.radius * (0.65 + r() * 0.45) * harm;

    const px = cl.center[0] + Math.cos(th) * rad * span;
    const py = cl.center[1] + y * span;
    const pz = cl.center[2] + Math.sin(th) * rad * span;

    const baseP: V3 = [px, py, pz];
    const isMicro = r() < 0.35;
    const size = isMicro ? 0.8 + r() * 0.6 : 1.3 + r() * 1.8;

    nodes.push({
      p: [...baseP],
      baseP,
      size,
      color: NODE_PALETTE[Math.floor(r() * NODE_PALETTE.length)] ?? C.blue,
      phase: r() * Math.PI * 2,
      speed: 0.4 + r() * 0.6,
      cluster: clusterIdx,
    });
  }

  // Branching constellation tendrils extending outward into the background
  const tendrilCount = variant === "hero" || variant === "network" ? Math.round(n * 0.22) : 8;
  for (let i = 0; i < tendrilCount; i++) {
    const d = norm([r() - 0.45, r() - 0.5, r() - 0.4]);
    const reach = 1.35 + r() * 0.95;
    const baseP: V3 = [d[0] * reach, d[1] * reach * 0.85, d[2] * reach];
    nodes.push({
      p: [...baseP],
      baseP,
      size: 0.9 + r() * 1.2,
      color: r() > 0.5 ? C.sky : C.lav,
      phase: r() * Math.PI * 2,
      speed: 0.3 + r() * 0.5,
      cluster: -1,
    });
  }

  // Major Knowledge Hubs
  const hubCount = Math.min(10, Math.max(5, Math.floor(n * 0.1)));
  for (let i = 0; i < hubCount; i++) {
    const idx = Math.floor(r() * (nodes.length - tendrilCount));
    const nd = nodes[idx];
    if (nd) {
      nd.hub = true;
      nd.size = 2.4 + r() * 1.4;
      nd.color = i % 2 === 0 ? C.blue : C.teal;
    }
  }

  // Anchor specific tags to prominent front-facing hubs
  tags.forEach((t, i) => {
    const targetIdx = Math.floor((i + 0.35) * ((nodes.length - tendrilCount) / tags.length));
    const nd = nodes[targetIdx];
    if (nd) {
      nd.tag = t;
      nd.hub = true;
      nd.size = 3.2;
      nd.color =
        t === "Verified"
          ? C.teal
          : t === "Risk"
          ? "211,109,114"
          : t === "Dependency"
          ? "211,155,67"
          : C.blue;
      nd.p = [nd.p[0] * 1.05, nd.p[1] * 1.05, Math.abs(nd.p[2]) * 0.9 + 0.15];
      nd.baseP = [...nd.p];
    }
  });

  return nodes;
}

/* Connects nearest neighbors with balanced density */
function knnEdges(nodes: Node[], k: number, maxDist: number) {
  const edges: [number, number][] = [];
  const seen = new Set<string>();

  nodes.forEach((a, i) => {
    nodes
      .map((b, j) => ({ j, d: dist(a.p, b.p) }))
      .filter((x) => x.j !== i && x.d < maxDist)
      .sort((x, y) => x.d - y.d)
      .slice(0, a.hub ? k + 2 : k)
      .forEach(({ j }) => {
        const key = i < j ? `${i}-${j}` : `${j}-${i}`;
        if (!seen.has(key)) {
          seen.add(key);
          edges.push([i, j]);
        }
      });
  });

  return edges;
}

/* Generates natural 3D curved paths with gentle organic curvature */
function arc(a: V3, b: V3, steps = 10, bow = 0.12): V3[] {
  const out: V3[] = [];
  const la = Math.hypot(...a);
  const lb = Math.hypot(...b);
  const midNorm = norm([a[0] + b[0], a[1] + b[1], a[2] + b[2]]);

  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const mx = a[0] + (b[0] - a[0]) * t;
    const my = a[1] + (b[1] - a[1]) * t;
    const mz = a[2] + (b[2] - a[2]) * t;

    // Organic outward bulge along the midpoint normal
    const lift = Math.sin(Math.PI * t) * bow * ((la + lb) * 0.5);
    out.push([
      mx + midNorm[0] * lift,
      my + midNorm[1] * lift,
      mz + midNorm[2] * lift,
    ]);
  }
  return out;
}

/* Floating organic ribbons / energy streamlines */
function ribbons(count: number, seed: number) {
  const r = rng(seed);
  return Array.from({ length: count }, (_, k) => {
    const ph = r() * 6.28;
    const ph2 = r() * 6.28;
    const a = 0.45 + r() * 0.5;
    const b = 0.15 + r() * 0.3;
    const tilt = (r() - 0.5) * 1.4;

    const pts: V3[] = [];
    const segments = 120;
    for (let i = 0; i <= segments; i++) {
      const t = (i / segments) * Math.PI * 2;
      const lat = a * Math.sin(2 * t + ph) + b * Math.sin(3 * t + ph2);
      const rad = 1.05 + 0.08 * Math.sin(4 * t + ph);
      pts.push(
        rotX(
          [Math.cos(t) * Math.cos(lat) * rad, Math.sin(lat) * rad, Math.sin(t) * Math.cos(lat) * rad],
          tilt
        )
      );
    }
    const pal = [C.lav, C.teal, C.blue, C.sky, C.ai];
    return { pts, color: pal[k % 5] ?? C.blue, width: 0.8 + r() * 1.3 };
  });
}

interface Pulse {
  e: number;
  t: number;
  dir: 1 | -1;
  speed: number;
}

export interface CoreSpline {
  p0: V3;
  p1: V3;
  p2: V3;
  p3?: V3;
  color: string;
  width: number;
  alpha: number;
  category: "inflow" | "core" | "outflow" | "structured" | "source";
}

export interface CorePulse {
  pathIndex: number;
  t: number;
  speed: number;
  color: string;
  size: number;
  glow: number;
}

export interface KnowledgeCoreData {
  nodes: Node[];
  splines: CoreSpline[];
  pulses: CorePulse[];
  strata: { phase: number; scale: number; speed: number; alpha: number; color: string }[];
  tags: { text: string; nodeIndex: number; color: string }[];
}

interface GeoResult {
  nodes: Node[];
  edges: [number, number][];
  paths: V3[][];
  rib: { pts: V3[]; color: string; width: number }[];
  scatter: V3[];
  stagger: number[];
  filaments: { off: number; ph: number; w: number; color: string }[];
  core?: KnowledgeCoreData;
}

function evalSpline3D(s: CoreSpline, u: number): V3 {
  const clampU = Math.max(0, Math.min(1, u));
  if (s.p3) {
    const u1 = 1 - clampU;
    const a = u1 * u1 * u1;
    const b = 3 * u1 * u1 * clampU;
    const c = 3 * u1 * clampU * clampU;
    const d = clampU * clampU * clampU;
    return [
      a * s.p0[0] + b * s.p1[0] + c * s.p2[0] + d * s.p3[0],
      a * s.p0[1] + b * s.p1[1] + c * s.p2[1] + d * s.p3[1],
      a * s.p0[2] + b * s.p1[2] + c * s.p2[2] + d * s.p3[2],
    ];
  }
  const u1 = 1 - clampU;
  const a = u1 * u1;
  const b = 2 * u1 * clampU;
  const c = clampU * clampU;
  return [
    a * s.p0[0] + b * s.p1[0] + c * s.p2[0],
    a * s.p0[1] + b * s.p1[1] + c * s.p2[1],
    a * s.p0[2] + b * s.p1[2] + c * s.p2[2],
  ];
}

/*
 * Generates the dimensional Organic Knowledge Core
 * Represents the Handover reconstruction narrative:
 * Left: Scattered Sources -> Center: Volumetric Knowledge Core -> Right: Structured Knowledge
 */
function buildKnowledgeCore(level: DetailLevel): KnowledgeCoreData {
  const r = rng(77);
  const nodes: Node[] = [];
  const splines: CoreSpline[] = [];
  const pulses: CorePulse[] = [];

  const addNode = (
    p: V3,
    size: number,
    color: string,
    cluster: number,
    hub = false,
    speed = 0.5,
    tag?: string
  ): number => {
    const idx = nodes.length;
    nodes.push({
      p: [...p],
      baseP: [...p],
      size,
      color,
      cluster,
      hub,
      tag,
      phase: r() * Math.PI * 2,
      speed,
    });
    return idx;
  };

  const addSpline = (
    p0: V3,
    p1: V3,
    p2: V3,
    p3: V3 | undefined,
    color: string,
    width: number,
    alpha: number,
    category: CoreSpline["category"]
  ): number => {
    const idx = splines.length;
    splines.push({ p0, p1, p2, p3, color, width, alpha, category });
    return idx;
  };

  // -------------------------------------------------------------
  // ZONE 1: SCATTERED SOURCES (LEFT: X in [-2.1, -0.9])
  // Disconnected tool silos (git commits, issues, docs)
  // -------------------------------------------------------------
  // Cluster A: Commits & PRs (Top-Left)
  const aHubIdx = addNode([-1.65, 0.44, 0.22], 3.8, C.sky, 0, true, 0.55);
  const aSats: number[] = [
    addNode([-1.85, 0.52, 0.12], 2.2, C.blue, 0, false, 0.65),
    addNode([-1.52, 0.62, 0.32], 2.0, C.navy, 0, false, 0.50),
    addNode([-1.78, 0.32, 0.38], 1.8, C.sky, 0, false, 0.70),
    addNode([-1.45, 0.38, 0.08], 2.4, C.blue, 0, false, 0.60),
    addNode([-1.60, 0.24, 0.25], 1.6, C.lav, 0, false, 0.45),
  ];
  addSpline(nodes[aHubIdx]!.baseP, [-1.75, 0.48, 0.17], nodes[aSats[0]!]!.baseP, undefined, C.sky, 0.9, 0.35, "source");
  addSpline(nodes[aHubIdx]!.baseP, [-1.58, 0.53, 0.27], nodes[aSats[1]!]!.baseP, undefined, C.sky, 0.8, 0.30, "source");
  addSpline(nodes[aHubIdx]!.baseP, [-1.72, 0.38, 0.30], nodes[aSats[2]!]!.baseP, undefined, C.blue, 0.85, 0.32, "source");
  addSpline(nodes[aHubIdx]!.baseP, [-1.55, 0.41, 0.15], nodes[aSats[3]!]!.baseP, undefined, C.sky, 0.9, 0.35, "source");

  // Cluster B: Issues & Blockers (Mid-Left)
  const bHubIdx = addNode([-1.82, -0.08, -0.22], 3.6, C.lav, 0, true, 0.48);
  const bSats: number[] = [
    addNode([-2.02, 0.02, -0.15], 2.0, C.navy, 0, false, 0.55),
    addNode([-1.68, -0.18, -0.32], 2.2, C.lav, 0, false, 0.62),
    addNode([-1.92, -0.22, -0.08], 1.7, C.sky, 0, false, 0.45),
    addNode([-1.72, 0.08, -0.28], 1.9, C.blue, 0, false, 0.58),
    addNode([-1.88, -0.32, -0.20], 1.5, C.lav, 0, false, 0.50),
  ];
  addSpline(nodes[bHubIdx]!.baseP, [-1.92, -0.03, -0.18], nodes[bSats[0]!]!.baseP, undefined, C.lav, 0.85, 0.32, "source");
  addSpline(nodes[bHubIdx]!.baseP, [-1.75, -0.13, -0.27], nodes[bSats[1]!]!.baseP, undefined, C.lav, 0.9, 0.35, "source");
  addSpline(nodes[bHubIdx]!.baseP, [-1.87, -0.15, -0.15], nodes[bSats[2]!]!.baseP, undefined, C.sky, 0.8, 0.30, "source");
  addSpline(nodes[bHubIdx]!.baseP, [-1.77, 0.00, -0.25], nodes[bSats[3]!]!.baseP, undefined, C.blue, 0.8, 0.30, "source");

  // Cluster C: Discussions & Docs (Bottom-Left)
  const cHubIdx = addNode([-1.50, -0.56, 0.25], 3.6, C.teal, 0, true, 0.52);
  const cSats: number[] = [
    addNode([-1.72, -0.48, 0.18], 2.1, C.teal, 0, false, 0.60),
    addNode([-1.38, -0.62, 0.35], 1.9, C.lav, 0, false, 0.52),
    addNode([-1.60, -0.68, 0.12], 1.8, C.sky, 0, false, 0.48),
    addNode([-1.35, -0.42, 0.22], 2.3, C.teal, 0, false, 0.65),
    addNode([-1.46, -0.74, 0.30], 1.5, C.navy, 0, false, 0.42),
  ];
  addSpline(nodes[cHubIdx]!.baseP, [-1.61, -0.52, 0.21], nodes[cSats[0]!]!.baseP, undefined, C.teal, 0.85, 0.32, "source");
  addSpline(nodes[cHubIdx]!.baseP, [-1.44, -0.59, 0.30], nodes[cSats[1]!]!.baseP, undefined, C.lav, 0.8, 0.30, "source");
  addSpline(nodes[cHubIdx]!.baseP, [-1.55, -0.62, 0.18], nodes[cSats[2]!]!.baseP, undefined, C.sky, 0.8, 0.30, "source");
  addSpline(nodes[cHubIdx]!.baseP, [-1.42, -0.49, 0.23], nodes[cSats[3]!]!.baseP, undefined, C.teal, 0.9, 0.35, "source");

  // Loose wandering fragments
  addNode([-1.25, 0.15, -0.10], 1.3, C.sky, 0, false, 0.40);
  addNode([-1.38, -0.22, 0.15], 1.2, C.lav, 0, false, 0.45);
  addNode([-1.15, -0.38, -0.12], 1.4, C.teal, 0, false, 0.38);
  addNode([-1.10, 0.35, 0.05], 1.3, C.blue, 0, false, 0.42);

  // -------------------------------------------------------------
  // ZONE 2: RECONSTRUCTION CORE (CENTER: X in [-0.5, 0.55])
  // Volumetric, multi-layered organic knowledge nucleus
  // -------------------------------------------------------------
  const coreHubMain = addNode([0.06, 0.10, 0.52], 6.2, C.blue, 1, true, 0.32);
  const coreHubInTop = addNode([-0.35, 0.36, 0.16], 5.0, C.sky, 1, true, 0.35);
  const coreHubInMid = addNode([-0.42, -0.12, 0.24], 5.2, C.lav, 1, true, 0.30);
  const coreHubInBot = addNode([-0.30, -0.42, -0.18], 4.8, C.teal, 1, true, 0.38);
  const coreHubOutTop = addNode([0.38, 0.32, 0.20], 5.2, C.teal, 1, true, 0.34);
  const coreHubOutBot = addNode([0.40, -0.20, -0.24], 5.0, C.blue, 1, true, 0.36);
  const coreHubDeep = addNode([0.04, -0.06, -0.44], 4.6, C.navy, 1, true, 0.28);

  const coreCount = level === "low" ? 12 : level === "mid" ? 20 : 26;
  const coreLatticeIndices: number[] = [];
  for (let i = 0; i < coreCount; i++) {
    const u = i / Math.max(1, coreCount - 1);
    const y = (1 - u * 2) * 0.68;
    const rad = Math.sqrt(Math.max(0, 1 - (y / 0.68) * (y / 0.68)));
    const th = i * 2.399963 + (r() - 0.5) * 0.4;
    const harm = 0.70 * (0.65 + 0.28 * Math.sin(3 * th) * Math.cos(2 * y * Math.PI) + 0.14 * Math.cos(5 * th + r()));
    const px = Math.cos(th) * rad * harm;
    const py = y + (r() - 0.5) * 0.08;
    const pz = Math.sin(th) * rad * harm;
    const isMicro = r() < 0.4;
    const size = isMicro ? 1.2 + r() * 0.6 : 1.8 + r() * 1.4;
    const pal = [C.blue, C.lav, C.sky, C.teal, C.navy];
    const cIdx = addNode([px, py, pz], size, pal[Math.floor(r() * pal.length)] ?? C.blue, 1, false, 0.25 + r() * 0.3);
    coreLatticeIndices.push(cIdx);
  }

  // -------------------------------------------------------------
  // ZONE 3: STRUCTURED KNOWLEDGE (RIGHT: X in [0.95, 2.1])
  // Verified, crystalline, beautifully organized project knowledge
  // -------------------------------------------------------------
  const decHubIdx = addNode([1.22, 0.34, 0.20], 6.0, C.teal, 2, true, 0.22, "Decision");
  const decSats: number[] = [
    addNode([1.05, 0.55, 0.10], 2.8, C.teal, 2, false, 0.25),
    addNode([1.42, 0.48, 0.28], 3.0, C.blue, 2, false, 0.24),
    addNode([1.48, 0.22, 0.08], 2.6, C.sky, 2, false, 0.20),
    addNode([1.18, 0.12, 0.32], 2.8, C.teal, 2, false, 0.22),
    addNode([0.96, 0.28, 0.16], 2.5, C.lav, 2, false, 0.24),
    addNode([1.30, 0.62, 0.15], 2.4, C.teal, 2, false, 0.26),
  ];

  const respHubIdx = addNode([1.48, -0.24, -0.10], 5.6, C.blue, 2, true, 0.20, "Responsibility");
  const depNexusIdx = addNode([1.80, 0.10, 0.18], 5.2, C.lav, 2, true, 0.22, "Dependency");
  const respSats: number[] = [
    addNode([1.30, -0.42, -0.22], 2.6, C.blue, 2, false, 0.22),
    addNode([1.65, -0.38, -0.05], 2.7, C.navy, 2, false, 0.24),
    addNode([1.68, -0.08, 0.06], 2.8, C.sky, 2, false, 0.20),
    addNode([1.40, -0.05, -0.15], 2.5, C.blue, 2, false, 0.23),
    addNode([1.92, -0.22, 0.12], 2.4, C.lav, 2, false, 0.25),
    addNode([1.60, -0.55, -0.18], 2.2, C.teal, 2, false, 0.26),
  ];

  const term0 = addNode([1.88, 0.32, 0.24], 2.2, C.teal, 2, false, 0.20);
  const term1 = addNode([2.02, -0.05, -0.08], 2.0, C.sky, 2, false, 0.22);
  const term2 = addNode([1.95, -0.42, 0.05], 2.1, C.blue, 2, false, 0.24);

  // -------------------------------------------------------------
  // PATHWAYS: SPLINE CONDUITS
  // -------------------------------------------------------------
  // Inflow Splines (Scattered Sources -> Core)
  const inflow0 = addSpline(nodes[aHubIdx]!.baseP, [-0.95, 0.56, 0.28], nodes[coreHubInTop]!.baseP, undefined, C.sky, 1.2, 0.55, "inflow");
  const inflow1 = addSpline(nodes[aSats[3]!]!.baseP, [-0.65, 0.30, 0.36], nodes[coreHubMain]!.baseP, undefined, C.blue, 1.1, 0.50, "inflow");
  const inflow2 = addSpline(nodes[bHubIdx]!.baseP, [-1.08, -0.02, 0.12], nodes[coreHubInMid]!.baseP, undefined, C.lav, 1.3, 0.60, "inflow");
  const inflow3 = addSpline(nodes[bSats[1]!]!.baseP, [-0.85, -0.14, -0.42], nodes[coreHubDeep]!.baseP, undefined, C.sky, 0.9, 0.40, "inflow");
  const inflow4 = addSpline(nodes[cHubIdx]!.baseP, [-0.92, -0.62, 0.10], nodes[coreHubInBot]!.baseP, undefined, C.teal, 1.2, 0.55, "inflow");
  const inflow5 = addSpline(nodes[cSats[3]!]!.baseP, [-0.82, -0.28, 0.28], nodes[coreHubInMid]!.baseP, undefined, C.teal, 1.1, 0.50, "inflow");

  // Core Internal Filaments
  const addCoreArc = (idxA: number, idxB: number, bow = 0.12, col = C.blue) => {
    const a = nodes[idxA]!.baseP;
    const b = nodes[idxB]!.baseP;
    const mid: V3 = [(a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5, (a[2] + b[2]) * 0.5];
    const n = norm(mid);
    const ctrl: V3 = [mid[0] + n[0] * bow, mid[1] + n[1] * bow, mid[2] + n[2] * bow];
    return addSpline(a, ctrl, b, undefined, col, 1.1, 0.45, "core");
  };

  const coreArcs: number[] = [
    addCoreArc(coreHubMain, coreHubInTop, 0.15, C.sky),
    addCoreArc(coreHubMain, coreHubInMid, 0.14, C.lav),
    addCoreArc(coreHubMain, coreHubOutTop, 0.16, C.teal),
    addCoreArc(coreHubMain, coreHubOutBot, 0.14, C.blue),
    addCoreArc(coreHubInTop, coreHubInMid, 0.10, C.lav),
    addCoreArc(coreHubInMid, coreHubInBot, 0.12, C.teal),
    addCoreArc(coreHubInBot, coreHubOutBot, 0.12, C.blue),
    addCoreArc(coreHubOutTop, coreHubOutBot, 0.15, C.teal),
    addCoreArc(coreHubDeep, coreHubInTop, 0.10, C.navy),
    addCoreArc(coreHubDeep, coreHubInBot, 0.10, C.navy),
    addCoreArc(coreHubDeep, coreHubOutBot, 0.12, C.sky),
    addCoreArc(coreHubDeep, coreHubOutTop, 0.12, C.lav),
  ];

  if (coreLatticeIndices.length >= 6) {
    addCoreArc(coreHubMain, coreLatticeIndices[0]!, 0.08, C.blue);
    addCoreArc(coreHubOutTop, coreLatticeIndices[2]!, 0.08, C.teal);
    addCoreArc(coreHubInMid, coreLatticeIndices[4]!, 0.08, C.lav);
  }

  // Outflow Splines (Core -> Structured Right)
  const outflow0 = addSpline(nodes[coreHubOutTop]!.baseP, [0.78, 0.40, 0.26], nodes[decHubIdx]!.baseP, undefined, C.teal, 1.4, 0.65, "outflow");
  const outflow1 = addSpline(nodes[coreHubMain]!.baseP, [0.65, 0.26, 0.42], nodes[decHubIdx]!.baseP, undefined, C.teal, 1.3, 0.60, "outflow");
  const outflow2 = addSpline(nodes[coreHubMain]!.baseP, [0.75, -0.05, 0.28], nodes[respHubIdx]!.baseP, undefined, C.blue, 1.3, 0.60, "outflow");
  const outflow3 = addSpline(nodes[coreHubOutBot]!.baseP, [0.92, -0.28, -0.20], nodes[respHubIdx]!.baseP, undefined, C.blue, 1.2, 0.55, "outflow");
  const outflow4 = addSpline(nodes[coreHubOutTop]!.baseP, [1.05, 0.28, 0.25], nodes[depNexusIdx]!.baseP, undefined, C.lav, 1.2, 0.55, "outflow");

  // Structured Right Lattice (Crystalline, geometric facets)
  const addFacet = (idxA: number, idxB: number, col = C.teal, w = 1.0, a = 0.45) => {
    const p0 = nodes[idxA]!.baseP;
    const p1 = nodes[idxB]!.baseP;
    const mid: V3 = [(p0[0] + p1[0]) * 0.5, (p0[1] + p1[1]) * 0.5, (p0[2] + p1[2]) * 0.5];
    return addSpline(p0, mid, p1, undefined, col, w, a, "structured");
  };

  decSats.forEach((sIdx) => addFacet(decHubIdx, sIdx, C.teal, 1.1, 0.50));
  for (let i = 0; i < decSats.length; i++) {
    const next = decSats[(i + 1) % decSats.length]!;
    addFacet(decSats[i]!, next, C.teal, 0.85, 0.35);
  }

  respSats.forEach((sIdx) => addFacet(respHubIdx, sIdx, C.blue, 1.1, 0.50));
  for (let i = 0; i < respSats.length; i++) {
    const next = respSats[(i + 1) % respSats.length]!;
    addFacet(respSats[i]!, next, C.blue, 0.85, 0.35);
  }

  addFacet(decHubIdx, respHubIdx, C.teal, 1.3, 0.60);
  addFacet(decHubIdx, depNexusIdx, C.lav, 1.2, 0.55);
  addFacet(respHubIdx, depNexusIdx, C.blue, 1.2, 0.55);
  addFacet(depNexusIdx, term0, C.teal, 0.9, 0.40);
  addFacet(depNexusIdx, term1, C.sky, 0.9, 0.40);
  addFacet(respHubIdx, term2, C.blue, 0.9, 0.40);

  // -------------------------------------------------------------
  // PULSES (Continuous Travelling Lights along Splines)
  // -------------------------------------------------------------
  const inflowSplines = [inflow0, inflow1, inflow2, inflow3, inflow4, inflow5];
  inflowSplines.forEach((sIdx, i) => {
    pulses.push({
      pathIndex: sIdx,
      t: (i / inflowSplines.length) * 0.85,
      speed: 0.20 + (i % 3) * 0.05,
      color: i % 2 === 0 ? C.sky : C.lav,
      size: 1.8,
      glow: 4.5,
    });
  });

  const coreSplinesPick = [coreArcs[0]!, coreArcs[2]!, coreArcs[3]!, coreArcs[7]!];
  coreSplinesPick.forEach((sIdx, i) => {
    pulses.push({
      pathIndex: sIdx,
      t: (i / coreSplinesPick.length) * 0.9,
      speed: 0.28 + (i % 2) * 0.06,
      color: i % 2 === 0 ? C.white : C.blue,
      size: 2.0,
      glow: 5.5,
    });
  });

  const outflowSplines = [outflow0, outflow1, outflow2, outflow3, outflow4];
  outflowSplines.forEach((sIdx, i) => {
    pulses.push({
      pathIndex: sIdx,
      t: (i / outflowSplines.length) * 0.85,
      speed: 0.22 + (i % 3) * 0.04,
      color: i % 2 === 0 ? C.teal : C.mint,
      size: 1.9,
      glow: 5.0,
    });
  });

  const strata = [
    { phase: 0.2, scale: 0.72, speed: 0.24, alpha: 0.18, color: C.lav },
    { phase: 1.8, scale: 0.52, speed: -0.28, alpha: 0.24, color: C.mint },
    { phase: 3.5, scale: 0.36, speed: 0.32, alpha: 0.28, color: C.teal },
  ];

  const tags = [
    { text: "Decision", nodeIndex: decHubIdx, color: C.teal },
    { text: "Responsibility", nodeIndex: respHubIdx, color: C.blue },
    { text: "Dependency", nodeIndex: depNexusIdx, color: C.lav },
  ];

  return { nodes, splines, pulses, strata, tags };
}

export interface SceneProps {
  variant?: SceneVariant;
  emptyKind?: EmptyKind;
  progress?: number;
  camZoom?: number;
  camOffset?: [number, number];
  dark?: boolean;
  showTags?: boolean;
  className?: string;
  accent?: string;
  interactive?: boolean;
  label?: string;
}

export function OrganicScene({
  variant = "hero",
  emptyKind = "knowledge",
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
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const accentRef = useRef(accent);
  accentRef.current = accent;
  const progRef = useRef(controlledProgress);
  progRef.current = controlledProgress;
  const zoomRef = useRef(camZoom);
  zoomRef.current = camZoom;
  const offRef = useRef(camOffset);
  offRef.current = camOffset;
  const darkRef = useRef(dark);
  darkRef.current = dark;

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const nav = navigator as Navigator & {
      deviceMemory?: number;
      connection?: { saveData?: boolean };
    };
    const lowPower =
      (nav.hardwareConcurrency ?? 8) <= 4 ||
      (nav.deviceMemory ?? 8) <= 4 ||
      !!nav.connection?.saveData;

    let W = 0,
      H = 0,
      dpr = 1;
    let detail: DetailLevel = "high";
    let geo: GeoResult = build("high");

    function build(level: DetailLevel): GeoResult {
      if (variant === "assemble") {
        const core = buildKnowledgeCore(level);
        return {
          nodes: core.nodes,
          edges: [],
          paths: [],
          rib: [],
          scatter: [],
          stagger: [],
          filaments: [],
          core,
        };
      }

      const isEmpty = variant === "empty";
      const n =
        variant === "network"
          ? level === "high"
            ? 160
            : level === "mid"
            ? 110
            : 60
          : variant === "hero" || variant === "macro" || variant === "cinematic"
          ? level === "high"
            ? 120
            : level === "mid"
            ? 78
            : 48
          : variant === "reconstruct"
          ? level === "low"
            ? 40
            : 70
          : isEmpty
          ? emptyKind === "project"
            ? 12
            : emptyKind === "knowledge"
            ? 18
            : emptyKind === "sources"
            ? 32
            : 40
          : 0;

      const wantTags =
        showTags ?? ((variant === "hero" || variant === "cinematic") && level !== "low");
      const tags = wantTags
        ? ["Decision", "Responsibility", "Risk", "Dependency", "Verified"]
        : [];

      const nodes =
        variant === "continuity"
          ? continuityNodes(level)
          : organicNodes(n, variant === "network" ? 17 : 42, tags, variant);

      if (isEmpty && emptyKind === "sources") {
        const clusters: V3[] = [
          [-1.35, -0.55, 0.2],
          [1.35, -0.5, -0.15],
          [-1.25, 0.65, -0.2],
          [1.3, 0.6, 0.2],
        ];
        nodes.forEach((nd, idx) => {
          const c = clusters[idx % 4] ?? [0, 0, 0];
          nd.p = [c[0] + nd.p[0] * 0.28, c[1] + nd.p[1] * 0.28, c[2] + nd.p[2] * 0.28];
          nd.baseP = [...nd.p];
          const pal = [C.navy, C.blue, C.lav, C.teal];
          nd.color = pal[idx % 4] ?? C.blue;
        });
      }

      const noEdges =
        variant === "continuity" ||
        (isEmpty && (emptyKind === "project" || emptyKind === "knowledge"));

      const maxD =
        variant === "network"
          ? 0.95
          : variant === "hero"
          ? 0.82
          : 0.68;

      const edges = noEdges
        ? []
        : knnEdges(nodes, variant === "network" ? 3 : 2, maxD);

      const paths = edges.map(([a, b]) => {
        const na = nodes[a]?.p ?? [0, 0, 0];
        const nb = nodes[b]?.p ?? [0, 0, 0];
        return arc(na, nb, variant === "network" ? 9 : 11, variant === "hero" ? 0.15 : 0.1);
      });

      const rib =
        variant === "hero" || variant === "macro" || variant === "cinematic"
          ? ribbons(level === "high" ? 6 : level === "mid" ? 4 : 3, 29)
          : variant === "reconstruct"
          ? ribbons(3, 11)
          : variant === "network"
          ? ribbons(5, 7)
          : [];

      const r = rng(53);
      const scatter = nodes.map((nd) => {
        if (variant === "reconstruct" || variant === "cinematic") {
          const d = norm([
            nd.p[0] + (r() - 0.5) * 0.9,
            nd.p[1] + (r() - 0.5) * 0.9,
            nd.p[2] + (r() - 0.5) * 0.9,
          ]);
          const k = 1.75 + r() * 1.1;
          return [d[0] * k, d[1] * k, d[2] * k] as V3;
        }
        return [(r() - 0.5) * 5.4, (r() - 0.5) * 2.5, (r() - 0.5) * 2] as V3;
      });

      const stagger = nodes.map(() => r() * 0.35);

      const filaments =
        variant === "continuity"
          ? Array.from({ length: level === "low" ? 6 : 10 }, (_, i) => ({
              off: (i / 9 - 0.5) * 1.15,
              ph: r() * 6.28,
              w: 0.7 + r() * 1.3,
              color: [C.blue, C.lav, C.teal, C.sky][i % 4] ?? C.blue,
            }))
          : [];

      return { nodes, edges, paths, rib, scatter, stagger, filaments };
    }

    function continuityNodes(level: DetailLevel) {
      const r = rng(23);
      const out: Node[] = [];
      const per = level === "low" ? 20 : 34;

      for (const side of [-1, 1]) {
        for (let i = 0; i < per; i++) {
          const d = norm([r() - 0.5, r() - 0.5, r() - 0.5]);
          const k = 0.18 + r() * 0.34;
          const baseP: V3 = [side * 1.05 + d[0] * k, d[1] * k, d[2] * k];
          out.push({
            p: [...baseP],
            baseP,
            size: 1 + r() * 1.6,
            color:
              side < 0
                ? r() > 0.4
                  ? C.navy
                  : C.sky
                : r() > 0.4
                ? C.blue
                : C.lav,
            phase: r() * Math.PI * 2,
            speed: 0.4 + r() * 0.5,
            cluster: side < 0 ? 0 : 1,
          });
        }
      }
      return out;
    }

    const pulses: Pulse[] = [];
    const resetPulses = () => {
      pulses.length = 0;
      if (variant === "assemble") return;
      const count =
        variant === "hero" || variant === "macro" || variant === "cinematic"
          ? 10
          : variant === "reconstruct"
          ? 6
          : variant === "network"
          ? 12
          : variant === "continuity"
          ? 7
          : 0;

      for (let i = 0; i < count; i++) {
        pulses.push({
          e: Math.floor(
            Math.random() * Math.max(1, geo.edges.length || geo.filaments.length)
          ),
          t: Math.random(),
          dir: Math.random() > 0.5 ? 1 : -1,
          speed: 0.16 + Math.random() * 0.22,
        });
      }
    };

    function resize() {
      const rect = wrap!.getBoundingClientRect();
      W = rect.width;
      H = rect.height;
      // Cap high-DPI scaling at 1.75 to ensure optimal framerate without GPU memory strain
      dpr = Math.min(window.devicePixelRatio || 1, lowPower ? 1.25 : 1.75);
      canvas!.width = Math.max(1, Math.round(W * dpr));
      canvas!.height = Math.max(1, Math.round(H * dpr));
      canvas!.style.width = `${W}px`;
      canvas!.style.height = `${H}px`;

      const next: DetailLevel = W < 540 ? "low" : W < 880 || lowPower ? "mid" : "high";
      if (next !== detail) {
        detail = next;
        geo = build(detail);
        resetPulses();
      }
    }

    geo = build(detail);
    resetPulses();

    let rotYa = variant === "network" ? 0.75 : variant === "assemble" ? 0.38 : 0.55;
    let tiltX = variant === "assemble" ? -0.10 : -0.18;
    let targetTx = 0;
    let targetTy = 0;
    let px = 0;
    let py = 0;
    let progress = 1;

    const onPointer = (e: PointerEvent) => {
      if (!interactive) return;
      const r = wrap!.getBoundingClientRect();
      const multX = variant === "assemble" ? 0.20 : 0.28;
      const multY = variant === "assemble" ? 0.26 : 0.38;
      targetTx = ((e.clientY - r.top) / r.height - 0.5) * multX;
      targetTy = ((e.clientX - r.left) / r.width - 0.5) * multY;
    };

    const host = wrap.closest("section") ?? wrap;
    host.addEventListener("pointermove", onPointer as EventListener);

    const project = (p: V3, cx: number, cy: number, R: number): Proj => {
      let q = rotY(p, rotYa + py);
      q = rotX(q, tiltX + px);
      const s = 3.4 / (3.4 - q[2]);
      return { x: cx + q[0] * R * s, y: cy + q[1] * R * s, z: q[2], s };
    };

    const projectLocal = (
      p: V3,
      origin: V3,
      cx: number,
      cy: number,
      R: number,
      spin: number
    ): Proj => {
      let q = rotY([p[0] - origin[0], p[1] - origin[1], p[2] - origin[2]], spin);
      q = [q[0] + origin[0], q[1] + origin[1], q[2] + origin[2]];
      q = rotX(rotY(q, py * 0.4), -0.06 + px * 0.4);
      const s = 3.4 / (3.4 - q[2]);
      return { x: cx + q[0] * R * s, y: cy + q[1] * R * s, z: q[2], s };
    };

    /*
     * Frosted Glass Volumetric Ambience & Caustic Illumination
     * Renders layered translucent light masses rather than a sharp billiard ball.
     */
    function ambientGlassAura(
      cx: number,
      cy: number,
      R: number,
      t: number,
      strength = 1,
      variantName: SceneVariant = "hero"
    ) {
      const isDark = darkRef.current;
      const breath = 0.85 + Math.sin(t * 0.45) * 0.15;

      // Soft diffuse ambient ground shadow / glow
      const sh = ctx!.createRadialGradient(cx, cy + R * 1.08, 0, cx, cy + R * 1.08, R * 1.15);
      sh.addColorStop(0, `rgba(${isDark ? "8,15,28" : C.navy},${(isDark ? 0.28 : 0.08) * strength})`);
      sh.addColorStop(1, "rgba(0,0,0,0)");
      ctx!.save();
      ctx!.scale(1, 0.28);
      ctx!.fillStyle = sh;
      ctx!.beginPath();
      ctx!.arc(cx, (cy + R * 1.08) / 0.28, R * 1.15, 0, Math.PI * 2);
      ctx!.fill();
      ctx!.restore();

      // Expansive volumetric background aura
      const auraRad = R * (variantName === "hero" ? 1.45 : 1.25);
      const aura = ctx!.createRadialGradient(
        cx + R * 0.15,
        cy - R * 0.12,
        R * 0.05,
        cx,
        cy,
        auraRad
      );

      if (isDark) {
        aura.addColorStop(0, `rgba(255,255,255,${0.18 * strength})`);
        aura.addColorStop(0.35, `rgba(${C.ai},${0.14 * strength * breath})`);
        aura.addColorStop(0.7, `rgba(${C.blue},${0.12 * strength})`);
        aura.addColorStop(1, "rgba(32,54,83,0)");
      } else {
        aura.addColorStop(0, `rgba(255,255,255,${0.85 * strength})`);
        aura.addColorStop(0.35, `rgba(${C.mint},${0.45 * strength * breath})`);
        aura.addColorStop(0.72, `rgba(${C.lav},${0.24 * strength})`);
        aura.addColorStop(0.92, `rgba(${C.sky},${0.16 * strength})`);
        aura.addColorStop(1, "rgba(246,248,252,0)");
      }

      ctx!.fillStyle = aura;
      ctx!.beginPath();
      ctx!.arc(cx, cy, auraRad, 0, Math.PI * 2);
      ctx!.fill();

      // Secondary translucent lobe illumination (Lavender & Mint highlights)
      const lobe1 = ctx!.createRadialGradient(
        cx - R * 0.35,
        cy - R * 0.38,
        0,
        cx - R * 0.35,
        cy - R * 0.38,
        R * 0.75
      );
      lobe1.addColorStop(0, `rgba(${C.lav},${(isDark ? 0.25 : 0.3) * breath * strength})`);
      lobe1.addColorStop(0.65, `rgba(${C.sky},${0.12 * strength})`);
      lobe1.addColorStop(1, "rgba(255,255,255,0)");

      ctx!.fillStyle = lobe1;
      ctx!.beginPath();
      ctx!.arc(cx - R * 0.35, cy - R * 0.38, R * 0.75, 0, Math.PI * 2);
      ctx!.fill();
    }

    /* Edge caustics and subtle glass reflection rim */
    function glassHighlights(cx: number, cy: number, R: number, strength = 1) {
      // Diffused specular sheen on top-left crest
      const hl = ctx!.createRadialGradient(
        cx - R * 0.38,
        cy - R * 0.44,
        0,
        cx - R * 0.38,
        cy - R * 0.44,
        R * 0.58
      );
      hl.addColorStop(0, `rgba(255,255,255,${0.75 * strength})`);
      hl.addColorStop(0.4, `rgba(255,255,255,${0.25 * strength})`);
      hl.addColorStop(1, "rgba(255,255,255,0)");

      ctx!.fillStyle = hl;
      ctx!.beginPath();
      ctx!.arc(cx, cy, R * 1.05, 0, Math.PI * 2);
      ctx!.fill();

      // Delicate organic rim reflection
      const rim = ctx!.createRadialGradient(cx, cy, R * 0.82, cx, cy, R * 1.02);
      rim.addColorStop(0, "rgba(255,255,255,0)");
      rim.addColorStop(0.75, `rgba(${C.sky},${0.22 * strength})`);
      rim.addColorStop(1, `rgba(255,255,255,${0.55 * strength})`);

      ctx!.fillStyle = rim;
      ctx!.beginPath();
      ctx!.arc(cx, cy, R * 1.02, 0, Math.PI * 2);
      ctx!.fill();
    }

    /* Frosted volumetric internal strata */
    function frostedStrata(cx: number, cy: number, R: number, t: number, back = true) {
      const isDark = darkRef.current;
      for (const [idx, scale, speed, a0, a1, col] of [
        [0, 0.82, 0.35, 0.16, 0.22, C.lav],
        [1, 0.58, -0.28, 0.2, 0.28, isDark ? C.blue : C.mint],
        [2, 0.38, 0.22, 0.24, 0.32, C.teal],
      ] as const) {
        const off = Math.sin(t * speed + idx * 1.8) * R * 0.04;
        const rad = R * scale + Math.cos(t * speed * 0.7) * R * 0.025;
        const lx = cx + off * 0.75;
        const ly = cy + off;

        const g = ctx!.createRadialGradient(
          lx - rad * 0.25,
          ly - rad * 0.25,
          0,
          lx,
          ly,
          rad
        );

        if (back) {
          g.addColorStop(0, `rgba(255,255,255,${a0 * (isDark ? 0.35 : 0.6)})`);
          g.addColorStop(0.7, `rgba(${col},${a0 * 0.75})`);
          g.addColorStop(1, `rgba(${col},0)`);
        } else {
          g.addColorStop(0, `rgba(255,255,255,${a1 * 0.8})`);
          g.addColorStop(0.65, `rgba(${col},${a1 * 0.4})`);
          g.addColorStop(1, "rgba(255,255,255,0)");
        }
        ctx!.fillStyle = g;
        ctx!.beginPath();
        ctx!.arc(lx, ly, rad, 0, Math.PI * 2);
        ctx!.fill();
      }
    }

    function strokePath(pts: Proj[], color: string, alpha: number, width: number) {
      if (pts.length < 2) return;
      ctx!.beginPath();
      pts.forEach((p, i) => (i ? ctx!.lineTo(p.x, p.y) : ctx!.moveTo(p.x, p.y)));
      ctx!.strokeStyle = `rgba(${color},${alpha})`;
      ctx!.lineWidth = width;
      ctx!.stroke();
    }

    function dot(
      x: number,
      y: number,
      r: number,
      color: string,
      alpha: number,
      halo = 0
    ) {
      if (halo > 0) {
        const g = ctx!.createRadialGradient(x, y, 0, x, y, r * halo);
        g.addColorStop(0, `rgba(${color},${alpha * 0.4})`);
        g.addColorStop(0.6, `rgba(${color},${alpha * 0.12})`);
        g.addColorStop(1, `rgba(${color},0)`);
        ctx!.fillStyle = g;
        ctx!.beginPath();
        ctx!.arc(x, y, r * halo, 0, Math.PI * 2);
        ctx!.fill();
      }
      ctx!.fillStyle = `rgba(${color},${alpha})`;
      ctx!.beginPath();
      ctx!.arc(x, y, Math.max(0.5, r), 0, Math.PI * 2);
      ctx!.fill();
    }

    function pointOnPath(pts: Proj[], t: number) {
      if (pts.length === 0) return { x: 0, y: 0, z: 0 };
      if (pts.length === 1) return { x: pts[0]!.x, y: pts[0]!.y, z: pts[0]!.z };
      const f = t * (pts.length - 1);
      const i = Math.min(pts.length - 2, Math.floor(f));
      const k = f - i;
      const p0 = pts[i]!;
      const p1 = pts[i + 1]!;
      return {
        x: p0.x + (p1.x - p0.x) * k,
        y: p0.y + (p1.y - p0.y) * k,
        z: p0.z + (p1.z - p0.z) * k,
      };
    }

    function drawNetwork(
      t: number,
      dt: number,
      cx: number,
      cy: number,
      R: number,
      opts: { shell: boolean; tags: boolean; edgeAlpha: number }
    ) {
      const isMorph =
        variant === "assemble" || variant === "reconstruct" || variant === "cinematic";
      const isEmpty = variant === "empty";
      const shellStrength =
        variant === "reconstruct" || variant === "cinematic"
          ? smooth(0.45, 0.95, progress)
          : isEmpty && emptyKind === "knowledge"
          ? 0.65
          : isEmpty && emptyKind === "ingestion"
          ? 0.55
          : 1;

      // Update node organic harmonic drift
      const proj = geo.nodes.map((n, i) => {
        let currentP: V3 = [...n.baseP];

        if (!reduced) {
          // Harmonic floating breathing motion
          const driftX = Math.sin(t * n.speed + n.phase) * 0.035;
          const driftY = Math.cos(t * n.speed * 0.8 + n.phase) * 0.035;
          const driftZ = Math.sin(t * n.speed * 0.6 + n.phase) * 0.025;
          currentP = [
            n.baseP[0] + driftX,
            n.baseP[1] + driftY,
            n.baseP[2] + driftZ,
          ];
        }

        if (isEmpty && emptyKind === "ingestion" && n.baseP[1] < 0) {
          const drift = Math.sin(t * 0.7 + i) * 0.06;
          return project([currentP[0] * 1.45, currentP[1] * 1.55 - 0.25 + drift, currentP[2] * 1.45], cx, cy, R);
        }
        if (isEmpty && emptyKind === "project") {
          const drift = Math.sin(t * 0.6 + i * 1.3) * 0.08;
          return project([currentP[0] * 1.2 + drift, currentP[1] * 1.2 - drift, currentP[2] * 1.2], cx, cy, R);
        }

        if (!isMorph) return project(currentP, cx, cy, R);

        const span = variant === "cinematic" ? 0.42 : 0.65;
        const stag = geo.stagger[i] ?? 0;
        const local = Math.max(
          0,
          Math.min(1, (progress - stag * (variant === "cinematic" ? 0.5 : 1)) / span)
        );
        const e = 1 - Math.pow(1 - local, 3);
        const s = geo.scatter[i] ?? [0, 0, 0];
        const p: V3 = [
          s[0] + (currentP[0] - s[0]) * e,
          s[1] + (currentP[1] - s[1]) * e + Math.sin(t * 0.6 + i) * 0.03 * (1 - e),
          s[2] + (currentP[2] - s[2]) * e,
        ];
        return project(p, cx, cy, R);
      });

      // 1. Back Layer: Ambient Frosted Aura & Illumination
      if (opts.shell && shellStrength > 0.02) {
        ambientGlassAura(cx, cy, R, t, shellStrength, variant);
      }
      if (opts.shell && shellStrength > 0.15) {
        frostedStrata(cx, cy, R, t, true);
      }

      // Empty State Circular Enclosures
      if (
        isEmpty &&
        (emptyKind === "project" || emptyKind === "sources" || emptyKind === "relationships")
      ) {
        ctx!.save();
        ctx!.setLineDash([4, 6]);
        ctx!.strokeStyle = darkRef.current
          ? "rgba(165,160,217,0.35)"
          : "rgba(121,151,190,0.45)";
        ctx!.lineWidth = 1.1;
        ctx!.beginPath();
        ctx!.arc(cx, cy, R * (emptyKind === "sources" ? 0.56 : 0.92), 0, Math.PI * 2);
        ctx!.stroke();
        ctx!.restore();
      }

      // Assemble Progress Form
      if (variant === "assemble") {
        const form = smooth(0.5, 1, progress);
        if (form > 0.01) {
          ctx!.save();
          ctx!.translate(cx, cy);
          ctx!.scale(2.2, 0.82);
          ambientGlassAura(0, 0, R * 1.05, t, form * 0.85, "assemble");
          ctx!.restore();
        }
      }

      // 2. Mid Layer: Curved 3D Pathways & Ribbons
      const pathProj = geo.paths.map((path) =>
        path.map((p) => project(p, cx, cy, R))
      );

      const ribScale =
        variant === "reconstruct" || variant === "cinematic"
          ? smooth(0.45, 0.92, progress)
          : 1;

      if (ribScale > 0.02) {
        for (const rb of geo.rib) {
          const pp = rb.pts.map((p) => project(p, cx, cy, R));
          for (let i = 1; i < pp.length; i++) {
            const p0 = pp[i - 1]!;
            const p1 = pp[i]!;
            const z = (p1.z + p0.z) / 2;
            ctx!.beginPath();
            ctx!.moveTo(p0.x, p0.y);
            ctx!.lineTo(p1.x, p1.y);
            ctx!.strokeStyle = `rgba(${rb.color},${
              (0.06 + smooth(-1, 1, z) * 0.3) * ribScale
            })`;
            ctx!.lineWidth = rb.width * (0.65 + smooth(-1, 1, z) * 0.55);
            ctx!.stroke();
          }
        }
      }

      const assembled =
        variant === "assemble"
          ? smooth(0.55, 1, progress)
          : variant === "reconstruct" || variant === "cinematic"
          ? smooth(0.22, 0.82, progress)
          : 1;

      // Depth sort edges
      const edgeOrder = geo.edges
        .map((e, i) => {
          const p0 = proj[e[0]];
          const p1 = proj[e[1]];
          const z = p0 && p1 ? (p0.z + p1.z) / 2 : 0;
          return { i, z };
        })
        .sort((a, b) => a.z - b.z);

      for (const { i, z } of edgeOrder) {
        const edge = geo.edges[i];
        if (!edge) continue;
        const [a, b] = edge;
        const nodeA = geo.nodes[a];
        const nodeB = geo.nodes[b];
        if (!nodeA || !nodeB) continue;

        const depth = smooth(-1, 1, z);
        const alpha = (0.05 + depth * 0.34) * opts.edgeAlpha * assembled;
        if (alpha < 0.01) continue;

        const pa = pathProj[i];
        if (!pa) continue;

        const projA = proj[a];
        const projB = proj[b];
        const pts =
          (variant === "assemble" || variant === "reconstruct" || variant === "cinematic") &&
          progress < 0.88 &&
          projA &&
          projB
            ? [projA, projB]
            : pa;

        const edgeCol =
          depth > 0.6
            ? darkRef.current
              ? C.lav
              : C.blue
            : depth > 0.3
            ? C.sky
            : C.lav;

        strokePath(
          pts,
          edgeCol,
          alpha * (darkRef.current ? 1.3 : 1),
          0.6 + depth * 0.65
        );
      }

      if (opts.shell && shellStrength > 0.15) {
        frostedStrata(cx, cy, R, t, false);
      }

      // 3. Traveling Knowledge Pulses along Active Relationships
      const acc = accentRef.current ?? C.blue;
      const canPulse =
        !reduced &&
        variant !== "assemble" &&
        !isEmpty &&
        (variant !== "reconstruct" && variant !== "cinematic" || progress > 0.5);

      if (canPulse && geo.edges.length > 0) {
        for (const pl of pulses) {
          pl.t += pl.speed * dt;
          if (pl.t > 1) {
            const edge = geo.edges[pl.e];
            if (edge) {
              const end = edge[pl.dir === 1 ? 1 : 0];
              const nexts = geo.edges
                .map((e, idx) => ({ e, i: idx }))
                .filter(({ e, i }) => i !== pl.e && (e[0] === end || e[1] === end));

              const pick = nexts.length
                ? nexts[Math.floor(Math.random() * nexts.length)]
                : {
                    e: geo.edges[Math.floor(Math.random() * geo.edges.length)],
                    i: Math.floor(Math.random() * geo.edges.length),
                  };

              if (pick && pick.e) {
                pl.e = pick.i;
                pl.dir = pick.e[0] === end ? 1 : -1;
                pl.t = 0;
              }
            }
          }

          const path = pathProj[pl.e];
          if (!path || path.length === 0) continue;

          const tt = pl.dir === 1 ? pl.t : 1 - pl.t;
          const head = pointOnPath(path, tt);
          const depth = smooth(-1, 1, head.z);

          const tail = pointOnPath(
            path,
            Math.max(0, Math.min(1, pl.dir === 1 ? tt - 0.32 : tt + 0.32))
          );

          // Pulse trail
          const g = ctx!.createLinearGradient(tail.x, tail.y, head.x, head.y);
          g.addColorStop(0, `rgba(${acc},0)`);
          g.addColorStop(1, `rgba(${acc},${0.8 * depth})`);

          ctx!.beginPath();
          ctx!.moveTo(tail.x, tail.y);
          ctx!.lineTo(head.x, head.y);
          ctx!.strokeStyle = g;
          ctx!.lineWidth = 1.6;
          ctx!.stroke();

          // Luminous pulse head
          dot(head.x, head.y, 1.8 + depth, "255,255,255", 0.95 * depth, 0);
          dot(head.x, head.y, 1.4 + depth * 0.9, acc, 0.9 * depth, 5);
        }
      }

      // 4. Foreground: Nodes & Knowledge Hubs
      const nOrder = proj
        .map((p, i) => ({ p, i }))
        .sort((a, b) => a.p.z - b.p.z);

      for (const { p, i } of nOrder) {
        const n = geo.nodes[i];
        if (!n) continue;

        const depth = smooth(-1, 1, p.z);
        const r = n.size * p.s * (1 - assembled * 0.12);

        // Core particle dot
        dot(p.x, p.y, r, n.color, 0.22 + depth * 0.75, n.hub ? 4.5 : 0);

        // Hub orbital halo ring for primary decision anchors
        if (n.hub && depth > 0.45) {
          ctx!.strokeStyle = `rgba(${n.color},${(depth - 0.45) * 0.65})`;
          ctx!.lineWidth = 0.85;
          ctx!.beginPath();
          ctx!.arc(p.x, p.y, r * 2.8, 0, Math.PI * 2);
          ctx!.stroke();
        }
      }

      // 5. Delicate Glass Edge Highlights
      if (opts.shell && shellStrength > 0.05) {
        glassHighlights(cx, cy, R, shellStrength);
      }

      if (variant === "assemble") {
        const form = smooth(0.6, 1, progress);
        if (form > 0.01) {
          ctx!.save();
          ctx!.translate(cx, cy);
          ctx!.scale(2.2, 0.82);
          glassHighlights(0, 0, R * 1.05, form * 0.7);
          ctx!.restore();
        }
      }

      // 6. Floating Verified Badges & Tags (Anchored to Hubs)
      const tagAlpha = variant === "cinematic" ? smooth(0.78, 0.96, progress) : 1;
      if (opts.tags && tagAlpha > 0.02) {
        for (const { p, i } of nOrder) {
          const n = geo.nodes[i];
          if (!n || !n.tag) continue;

          const vis = smooth(0.25, 0.75, p.z) * tagAlpha;
          if (vis < 0.04) continue;

          const side = p.x > cx ? 1 : -1;
          const lx = p.x + side * 28;
          const ly = p.y - 15;
          const isDark = darkRef.current;

          ctx!.globalAlpha = vis;

          // Elegant citation connecting hairline
          ctx!.strokeStyle = isDark
            ? "rgba(217,225,240,0.45)"
            : "rgba(49,95,186,0.32)";
          ctx!.lineWidth = 0.85;
          ctx!.beginPath();
          ctx!.moveTo(p.x + side * 5, p.y - 3);
          ctx!.lineTo(lx, ly);
          ctx!.stroke();

          ctx!.font = "600 11.5px Manrope, Inter, sans-serif";
          const tw = ctx!.measureText(n.tag).width;
          const bx = side > 0 ? lx : lx - tw - 24;

          // Pill container
          ctx!.fillStyle = isDark
            ? "rgba(22,38,62,0.92)"
            : "rgba(255,255,255,0.92)";
          roundRect(bx, ly - 11, tw + 24, 22, 11);
          ctx!.fill();

          ctx!.strokeStyle = isDark
            ? "rgba(121,151,190,0.45)"
            : "rgba(217,225,240,0.95)";
          ctx!.stroke();

          // Status indicator dot
          dot(
            bx + 9,
            ly,
            2.8,
            n.tag === "Verified"
              ? "41,155,128"
              : n.tag === "Risk"
              ? "211,109,114"
              : n.tag === "Dependency"
              ? "211,155,67"
              : C.blue,
            1
          );

          ctx!.fillStyle = isDark ? "#F6F8FC" : "#203653";
          ctx!.fillText(n.tag, bx + 17, ly + 4);
          ctx!.globalAlpha = 1;
        }
      }
    }

    function roundRect(
      x: number,
      y: number,
      w: number,
      h: number,
      r: number
    ) {
      ctx!.beginPath();
      ctx!.moveTo(x + r, y);
      ctx!.arcTo(x + w, y, x + w, y + h, r);
      ctx!.arcTo(x + w, y + h, x, y + h, r);
      ctx!.arcTo(x, y + h, x, y, r);
      ctx!.arcTo(x, y, x + w, y, r);
      ctx!.closePath();
    }

    /*
     * Organic Knowledge Core Renderer
     * Master rendering pipeline for the volumetric reconstruction visual:
     * - Multi-layered frosted glass envelope & soft internal luminescence
     * - Smooth curved 3D conduits linking Scattered Sources -> Core -> Structured Knowledge
     * - Depth-sorted rendering with midplane frosted refraction veil
     * - Continuous travelling light pulses along meaningful relationships
     * - Front-facing decision anchors & metadata badges
     */
    function drawKnowledgeCore(
      t: number,
      dt: number,
      cx: number,
      cy: number,
      R: number,
      opts: { tags: boolean; edgeAlpha: number }
    ) {
      const coreData = geo.core;
      if (!coreData) return;

      const isNarrow = W < 640;
      const isMobile = W < 500;
      const xCompress = isMobile ? 0.74 : isNarrow ? 0.82 : 1.0;
      const coreScale = isNarrow ? 0.88 : 1.0;

      const ry = rotYa + py;
      const rx = tiltX + px;

      const project3D = (p: V3): Proj => {
        const xp = p[0] * xCompress;
        let q = rotY([xp, p[1], p[2]], ry);
        q = rotX(q, rx);
        const s = 3.6 / (3.6 - q[2]);
        return {
          x: cx + q[0] * R * s,
          y: cy + q[1] * R * s,
          z: q[2],
          s,
        };
      };

      const breath = reduced ? 1 : 1 + Math.sin(t * 0.45) * 0.045;
      const coreCenterProj = project3D([0, 0, 0]);
      const coreR = R * 0.86 * breath * coreScale;

      // 1. Ambient Ground Shadows
      const isDark = darkRef.current;
      const shY = cy + coreR * 0.96;
      const shGrad = ctx!.createRadialGradient(cx, shY, 0, cx, shY, coreR * 1.25);
      shGrad.addColorStop(0, isDark ? "rgba(8,15,28,0.28)" : "rgba(32,54,83,0.07)");
      shGrad.addColorStop(0.7, isDark ? "rgba(8,15,28,0.05)" : "rgba(32,54,83,0.015)");
      shGrad.addColorStop(1, "rgba(0,0,0,0)");
      ctx!.save();
      ctx!.scale(1, 0.26);
      ctx!.fillStyle = shGrad;
      ctx!.beginPath();
      ctx!.arc(cx, shY / 0.26, coreR * 1.25, 0, Math.PI * 2);
      ctx!.fill();
      ctx!.restore();

      const rightCenterX = cx + R * 1.45 * xCompress;
      const rightCenterY = cy + coreR * 0.82;
      const shRight = ctx!.createRadialGradient(
        rightCenterX,
        rightCenterY,
        0,
        rightCenterX,
        rightCenterY,
        coreR * 0.85
      );
      shRight.addColorStop(0, isDark ? "rgba(8,15,28,0.18)" : "rgba(32,54,83,0.045)");
      shRight.addColorStop(1, "rgba(0,0,0,0)");
      ctx!.save();
      ctx!.scale(1, 0.24);
      ctx!.fillStyle = shRight;
      ctx!.beginPath();
      ctx!.arc(rightCenterX, rightCenterY / 0.24, coreR * 0.85, 0, Math.PI * 2);
      ctx!.fill();
      ctx!.restore();

      // 2. Volumetric Frosted Glass Aura
      const auraRad = coreR * 1.35;
      const aura = ctx!.createRadialGradient(
        coreCenterProj.x - coreR * 0.15,
        coreCenterProj.y - coreR * 0.18,
        coreR * 0.05,
        coreCenterProj.x,
        coreCenterProj.y,
        auraRad
      );
      if (isDark) {
        aura.addColorStop(0, "rgba(255,255,255,0.22)");
        aura.addColorStop(0.3, `rgba(${C.ai},0.15)`);
        aura.addColorStop(0.65, `rgba(${C.blue},0.10)`);
        aura.addColorStop(1, "rgba(32,54,83,0)");
      } else {
        aura.addColorStop(0, "rgba(255,255,255,0.88)");
        aura.addColorStop(0.28, `rgba(${C.mint},0.42)`);
        aura.addColorStop(0.58, `rgba(${C.lav},0.22)`);
        aura.addColorStop(0.82, `rgba(${C.sky},0.12)`);
        aura.addColorStop(1, "rgba(246,248,252,0)");
      }
      ctx!.fillStyle = aura;
      ctx!.beginPath();
      ctx!.arc(coreCenterProj.x, coreCenterProj.y, auraRad, 0, Math.PI * 2);
      ctx!.fill();

      // Secondary subtle ambient field for right cluster
      const rightAura = ctx!.createRadialGradient(
        rightCenterX,
        coreCenterProj.y - coreR * 0.1,
        0,
        rightCenterX,
        coreCenterProj.y,
        coreR * 0.95
      );
      rightAura.addColorStop(0, isDark ? `rgba(${C.teal},0.10)` : `rgba(${C.mint},0.24)`);
      rightAura.addColorStop(0.6, isDark ? `rgba(${C.blue},0.05)` : `rgba(${C.lav},0.08)`);
      rightAura.addColorStop(1, "rgba(255,255,255,0)");
      ctx!.fillStyle = rightAura;
      ctx!.beginPath();
      ctx!.arc(rightCenterX, coreCenterProj.y, coreR * 0.95, 0, Math.PI * 2);
      ctx!.fill();

      // Soft internal strata lobes
      for (const st of coreData.strata) {
        const offX = Math.sin(t * st.speed + st.phase) * coreR * 0.12;
        const offY = Math.cos(t * st.speed * 0.8 + st.phase) * coreR * 0.10;
        const lobeR = coreR * st.scale + Math.sin(t * 0.6 + st.phase) * coreR * 0.03;
        const lx = coreCenterProj.x + offX;
        const ly = coreCenterProj.y + offY;

        const lg = ctx!.createRadialGradient(
          lx - lobeR * 0.25,
          ly - lobeR * 0.25,
          0,
          lx,
          ly,
          lobeR
        );
        lg.addColorStop(0, `rgba(255,255,255,${st.alpha * 0.9})`);
        lg.addColorStop(0.6, `rgba(${st.color},${st.alpha * 0.55})`);
        lg.addColorStop(1, `rgba(${st.color},0)`);

        ctx!.fillStyle = lg;
        ctx!.beginPath();
        ctx!.arc(lx, ly, lobeR, 0, Math.PI * 2);
        ctx!.fill();
      }

      // 3. Project Nodes
      const projNodes = coreData.nodes.map((node, i) => {
        let p: V3 = [...node.baseP];
        if (!reduced) {
          const ampl = node.cluster === 0 ? 0.042 : node.cluster === 1 ? 0.022 : 0.014;
          p = [
            node.baseP[0] + Math.sin(t * node.speed + node.phase) * ampl,
            node.baseP[1] + Math.cos(t * node.speed * 0.85 + node.phase) * ampl,
            node.baseP[2] + Math.sin(t * node.speed * 0.65 + node.phase) * (ampl * 0.8),
          ];
        }
        const proj = project3D(p);
        return { node, proj, i, z: proj.z };
      });

      // 4. Project Splines
      const projSplines = coreData.splines.map((sp, idx) => {
        const pts: Proj[] = [];
        const steps = 14;
        let avgZ = 0;
        for (let s = 0; s <= steps; s++) {
          const u = s / steps;
          const p3d = evalSpline3D(sp, u);
          const pr = project3D(p3d);
          pts.push(pr);
          avgZ += pr.z;
        }
        avgZ /= (steps + 1);
        return { sp, pts, avgZ, idx };
      });

      // 5. Back Splines (z < 0)
      const backSplines = projSplines
        .filter((s) => s.avgZ < 0)
        .sort((a, b) => a.avgZ - b.avgZ);
      for (const { sp, pts, avgZ } of backSplines) {
        const depth = smooth(-1, 0, avgZ);
        const alpha = (0.06 + depth * 0.28) * sp.alpha * opts.edgeAlpha;
        if (alpha < 0.01) continue;
        strokePath(
          pts,
          sp.color,
          alpha * (isDark ? 1.2 : 1.0),
          sp.width * (0.65 + depth * 0.45)
        );
      }

      // 6. Back Nodes (z < 0)
      const backNodes = projNodes.filter((n) => n.z < 0).sort((a, b) => a.z - b.z);
      for (const { node, proj, z } of backNodes) {
        const depth = smooth(-1, 0, z);
        const r = node.size * proj.s * 0.85;
        dot(proj.x, proj.y, r, node.color, 0.22 + depth * 0.50, node.hub ? 3.0 : 0);
      }

      // 7. Midplane Frosted Refraction Veil
      const veil = ctx!.createRadialGradient(
        coreCenterProj.x,
        coreCenterProj.y,
        0,
        coreCenterProj.x,
        coreCenterProj.y,
        coreR * 0.95
      );
      veil.addColorStop(0, isDark ? "rgba(32,54,83,0.32)" : "rgba(255,255,255,0.42)");
      veil.addColorStop(0.7, isDark ? "rgba(32,54,83,0.16)" : "rgba(255,255,255,0.20)");
      veil.addColorStop(1, "rgba(255,255,255,0)");
      ctx!.fillStyle = veil;
      ctx!.beginPath();
      ctx!.arc(coreCenterProj.x, coreCenterProj.y, coreR * 0.95, 0, Math.PI * 2);
      ctx!.fill();

      // 8. Front Splines (z >= 0)
      const frontSplines = projSplines
        .filter((s) => s.avgZ >= 0)
        .sort((a, b) => a.avgZ - b.avgZ);
      for (const { sp, pts, avgZ } of frontSplines) {
        const depth = smooth(0, 1, avgZ);
        const alpha = (0.24 + depth * 0.65) * sp.alpha * opts.edgeAlpha;
        strokePath(
          pts,
          sp.color,
          alpha * (isDark ? 1.25 : 1.0),
          sp.width * (0.95 + depth * 0.85)
        );
      }

      // 9. Travelling Light Pulses
      for (const pulse of coreData.pulses) {
        if (!reduced) {
          pulse.t += pulse.speed * dt;
          if (pulse.t > 1) {
            pulse.t = 0;
          }
        }
        const sp = coreData.splines[pulse.pathIndex];
        if (!sp) continue;

        const head3D = evalSpline3D(sp, pulse.t);
        const headProj = project3D(head3D);
        const tailT = Math.max(0, pulse.t - 0.22);
        const tail3D = evalSpline3D(sp, tailT);
        const tailProj = project3D(tail3D);

        const depth = smooth(-0.8, 1, headProj.z);
        if (depth < 0.05) continue;

        // Luminous pulse tail gradient
        const tg = ctx!.createLinearGradient(tailProj.x, tailProj.y, headProj.x, headProj.y);
        tg.addColorStop(0, `rgba(${pulse.color},0)`);
        tg.addColorStop(0.6, `rgba(${pulse.color},${0.45 * depth})`);
        tg.addColorStop(1, `rgba(${pulse.color},${0.95 * depth})`);

        ctx!.beginPath();
        ctx!.moveTo(tailProj.x, tailProj.y);
        ctx!.lineTo(headProj.x, headProj.y);
        ctx!.strokeStyle = tg;
        ctx!.lineWidth = pulse.size * (0.8 + depth * 0.7);
        ctx!.stroke();

        // Luminous pulse head
        dot(headProj.x, headProj.y, pulse.size * (1.1 + depth * 0.8), "255,255,255", 0.98 * depth, 0);
        dot(headProj.x, headProj.y, pulse.size * (0.8 + depth * 0.6), pulse.color, 0.9 * depth, pulse.glow);
      }

      // 10. Front Nodes (z >= 0)
      const frontNodes = projNodes.filter((n) => n.z >= 0).sort((a, b) => a.z - b.z);
      for (const { node, proj, z } of frontNodes) {
        const depth = smooth(0, 1, z);
        const r = node.size * proj.s;

        // Particle core
        dot(proj.x, proj.y, r, node.color, 0.42 + depth * 0.58, node.hub ? 5.0 : 0);

        // Orbital halo ring for major hubs
        if (node.hub && depth > 0.30) {
          ctx!.strokeStyle = `rgba(${node.color},${(depth - 0.30) * 0.75})`;
          ctx!.lineWidth = 0.95;
          ctx!.beginPath();
          ctx!.arc(proj.x, proj.y, r * 2.6, 0, Math.PI * 2);
          ctx!.stroke();

          // Specular center pin
          dot(proj.x, proj.y, Math.max(0.8, r * 0.35), "255,255,255", 0.95 * depth, 0);
        }
      }

      // 11. Specular Crest & Glass Rim Reflection
      const specX = coreCenterProj.x - coreR * 0.36;
      const specY = coreCenterProj.y - coreR * 0.42;
      const specG = ctx!.createRadialGradient(specX, specY, 0, specX, specY, coreR * 0.55);
      specG.addColorStop(0, isDark ? "rgba(255,255,255,0.45)" : "rgba(255,255,255,0.85)");
      specG.addColorStop(0.35, isDark ? "rgba(255,255,255,0.15)" : "rgba(255,255,255,0.30)");
      specG.addColorStop(1, "rgba(255,255,255,0)");

      ctx!.fillStyle = specG;
      ctx!.beginPath();
      ctx!.arc(specX, specY, coreR * 0.55, 0, Math.PI * 2);
      ctx!.fill();

      // Delicate rim reflection arc on the upper crest
      ctx!.strokeStyle = isDark ? "rgba(165,160,217,0.35)" : "rgba(255,255,255,0.65)";
      ctx!.lineWidth = 1.2;
      ctx!.beginPath();
      ctx!.arc(coreCenterProj.x, coreCenterProj.y, coreR * 0.98, -Math.PI * 0.85, -Math.PI * 0.15);
      ctx!.stroke();

      // 12. Floating Verified Badges / Metadata Tags (Anchored to Right Hubs)
      if (opts.tags && W >= 600) {
        for (const tagItem of coreData.tags) {
          const pNode = projNodes[tagItem.nodeIndex];
          if (!pNode || pNode.z < 0.1) continue;

          const p = pNode.proj;
          const vis = smooth(0.1, 0.6, pNode.z);
          if (vis < 0.05) continue;

          const side = p.x > cx ? 1 : -1;
          const lx = p.x + side * 28;
          const ly = p.y - 14;

          ctx!.globalAlpha = vis;

          // Hairline connecting citation
          ctx!.strokeStyle = isDark ? "rgba(217,225,240,0.45)" : "rgba(49,95,186,0.32)";
          ctx!.lineWidth = 0.85;
          ctx!.beginPath();
          ctx!.moveTo(p.x + side * 6, p.y - 2);
          ctx!.lineTo(lx, ly);
          ctx!.stroke();

          ctx!.font = "600 11px Manrope, Inter, sans-serif";
          const tw = ctx!.measureText(tagItem.text).width;
          const bx = side > 0 ? lx : lx - tw - 24;

          // Translucent pill container
          ctx!.fillStyle = isDark ? "rgba(22,38,62,0.92)" : "rgba(255,255,255,0.94)";
          roundRect(bx, ly - 11, tw + 24, 22, 11);
          ctx!.fill();

          ctx!.strokeStyle = isDark ? "rgba(121,151,190,0.45)" : "rgba(217,225,240,0.95)";
          ctx!.stroke();

          // Status dot
          dot(bx + 9, ly, 2.8, tagItem.color, 1);

          ctx!.fillStyle = isDark ? "#F6F8FC" : "#203653";
          ctx!.fillText(tagItem.text, bx + 17, ly + 4);
          ctx!.globalAlpha = 1;
        }
      }
    }

    /* Continuity dual-lobed knowledge bridge */
    function drawContinuity(t: number, dt: number) {
      const cx = W / 2;
      const cy = H / 2;
      const R = Math.min(W / 5.2, H / 1.85);

      for (const side of [-1, 1]) {
        ambientGlassAura(cx + side * R * 1.05, cy, R * 0.55, t + side, 0.9, "continuity");
      }

      const fil = geo.filaments.map((f) => {
        const pts: Proj[] = [];
        for (let i = 0; i <= 44; i++) {
          const u = i / 44;
          const x = -1.05 + u * 2.1;
          const y =
            Math.sin(u * Math.PI) * f.off * 0.85 +
            (reduced ? 0 : Math.sin(t * 0.5 + f.ph + u * 3) * 0.05);
          const z = Math.cos(u * Math.PI * 2 + f.ph) * 0.18;
          pts.push(projectLocal([x, y, z], [0, 0, 0], cx, cy, R, 0));
        }
        return pts;
      });

      geo.filaments.forEach((f, k) => {
        const filItem = fil[k];
        if (filItem) strokePath(filItem, f.color, 0.45, f.w);
      });

      const projNodes = geo.nodes.map((n) =>
        projectLocal(
          n.p,
          [n.p[0] < 0 ? -1.05 : 1.05, 0, 0],
          cx,
          cy,
          R,
          rotYa * (n.p[0] < 0 ? 1 : -1)
        )
      );

      projNodes
        .map((p, i) => ({ p, i }))
        .sort((a, b) => a.p.z - b.p.z)
        .forEach(({ p, i }) => {
          const node = geo.nodes[i];
          if (node) dot(p.x, p.y, node.size * p.s, node.color, 0.35 + smooth(-1, 1, p.z) * 0.6);
        });

      if (!reduced && fil.length > 0) {
        for (const pl of pulses) {
          pl.t += pl.speed * dt * 0.8;
          if (pl.t > 1) {
            pl.t = 0;
            pl.e = Math.floor(Math.random() * fil.length);
          }
          const path = fil[pl.e % fil.length];
          if (path) {
            const h = pointOnPath(path, pl.t);
            dot(h.x, h.y, 2, C.blue, 0.85, 5);
          }
        }
      }

      for (const side of [-1, 1]) {
        glassHighlights(cx + side * R * 1.05, cy, R * 0.55, 0.9);
      }
    }

    let raf = 0;
    let last = performance.now();
    let start = last;
    let visible = true;
    let running = true;
    const minFrame = lowPower ? 1000 / 30 : 0;

    function frame(now: number) {
      if (!running) return;
      raf = requestAnimationFrame(frame);
      if (!visible || now - last < minFrame) return;

      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const t = (now - start) / 1000;
      render(t, dt);
    }

    function render(t: number, dt: number) {
      if (variant === "assemble") {
        progress = progRef.current !== undefined ? progRef.current : 1;
      } else if (variant === "reconstruct" || variant === "cinematic") {
        if (progRef.current !== undefined) {
          progress += (progRef.current - progress) * Math.min(1, dt * 6);
        } else {
          const cycle = (t % 6.5) / 6.5;
          progress =
            cycle < 0.78
              ? smooth(0, 0.72, cycle)
              : cycle < 0.92
              ? 1
              : 1 - smooth(0.92, 1, cycle);
        }
      }

      if (!reduced) {
        // Calm, continuous, stately rotation
        rotYa += dt * (variant === "network" ? 0.025 : variant === "assemble" ? 0.022 : 0.038);
        px += (targetTx - px) * Math.min(1, dt * 2.2);
        py += (targetTy - py) * Math.min(1, dt * 2.2);
      }

      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx!.clearRect(0, 0, W, H);

      const float = reduced ? 0 : Math.sin(t * 0.5) * Math.min(7, H * 0.01);
      const z = zoomRef.current;
      const [ox, oy] = offRef.current;

      const cx = W * (0.5 + ox);
      const cy = H * (0.5 + oy) + float;

      if (variant === "hero") {
        // Expansive radius filling the background with organic reach
        const heroR = Math.max(W * 0.38, Math.min(W, H) * 0.48) * z;
        drawNetwork(t, dt, cx, cy, heroR, {
          shell: true,
          tags: showTags ?? true,
          edgeAlpha: 1.15,
        });
      } else if (variant === "network") {
        // Ambient network extending across the section
        const netR = Math.max(W * 0.45, H * 0.72) * z;
        drawNetwork(t, dt, cx, cy, netR, {
          shell: false,
          tags: false,
          edgeAlpha: 1.3,
        });
      } else if (variant === "macro") {
        drawNetwork(
          t,
          dt,
          W * (0.34 + ox),
          H * (0.56 + oy) + float * 0.5,
          Math.min(W, H) * 0.62 * z,
          { shell: true, tags: false, edgeAlpha: 1.35 }
        );
      } else if (variant === "reconstruct") {
        drawNetwork(t, dt, cx, cy, Math.min(W, H) * 0.34 * z, {
          shell: true,
          tags: showTags ?? false,
          edgeAlpha: 1.15,
        });
      } else if (variant === "cinematic") {
        const p = progress;
        const cz =
          p < 0.2
            ? 0.92 + p * 0.8
            : p < 0.45
            ? 1.08 + smooth(0.2, 0.45, p) * 0.48
            : p < 0.7
            ? 1.56 - smooth(0.45, 0.7, p) * 0.38
            : 1.18 - smooth(0.7, 1, p) * 0.18;
        const cox =
          p >= 0.35 && p <= 0.72
            ? -0.1 * Math.sin(((p - 0.35) / 0.37) * Math.PI)
            : 0;
        drawNetwork(t, dt, W * (0.5 + cox + ox), cy, Math.min(W, H) * 0.34 * cz * z, {
          shell: true,
          tags: true,
          edgeAlpha: 1.2,
        });
      } else if (variant === "empty") {
        drawNetwork(t, dt, cx, cy, Math.min(W, H) * 0.32 * z, {
          shell: emptyKind === "knowledge" || emptyKind === "ingestion",
          tags: false,
          edgeAlpha: 1.1,
        });
      } else if (variant === "assemble") {
        if (geo.core) {
          drawKnowledgeCore(t, dt, cx, cy, Math.min(W / 4.6, H / 2.15) * z, {
            tags: showTags ?? (detail !== "low"),
            edgeAlpha: 1.35,
          });
        }
      } else {
        drawContinuity(t, dt);
      }
    }

    const ro = new ResizeObserver(() => {
      resize();
      const isLowDetail = (detail as string) === "low";
      if (reduced || isLowDetail) render(2, 0.016);
    });
    ro.observe(wrap);
    resize();

    // Intersection observer pauses execution when scrolled off-screen
    const io = new IntersectionObserver(([entry]) => {
      if (entry) visible = entry.isIntersecting;
    });
    io.observe(wrap);

    const onVis = () => {
      visible = document.visibilityState === "visible";
      last = performance.now();
    };
    document.addEventListener("visibilitychange", onVis);

    const isLowDetail = (detail as string) === "low";
    const animate = !reduced && !(isLowDetail && variant !== "assemble");
    if (animate) {
      raf = requestAnimationFrame(frame);
    } else {
      progress = progRef.current ?? 1;
      render(2, 0.016);
    }

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      ro.disconnect();
      io.disconnect();
      document.removeEventListener("visibilitychange", onVis);
      host.removeEventListener("pointermove", onPointer as EventListener);
    };
  }, [variant, emptyKind, interactive, showTags]);

  return (
    <div
      ref={wrapRef}
      className={className}
      role="img"
      aria-label={label ?? "Organic knowledge sphere: interconnected project knowledge"}
    >
      <canvas ref={canvasRef} className="block h-full w-full" />
    </div>
  );
}

export default OrganicScene;
