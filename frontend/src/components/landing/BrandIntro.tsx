"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";

export type IntroStage =
  | "intro"
  | "logo-enter"
  | "logo-hold"
  | "transformation"
  | "network-reveal"
  | "page-reveal"
  | "complete";

interface SphereNode {
  // Target 3D coordinates on unit sphere
  sx: number;
  sy: number;
  sz: number;
  // Current 3D coordinates
  x: number;
  y: number;
  z: number;
  // Origin offset from center
  ox: number;
  oy: number;
  oz: number;
  // Node properties
  radius: number;
  color: string;
  cluster: number;
  phase: number;
  speed: number;
}

const BRAND_PALETTE = [
  { r: 49, g: 95, b: 186 },  // Blue #315FBA
  { r: 41, g: 155, b: 128 }, // Teal #299B80
  { r: 165, g: 160, b: 217 },// Lavender #A5A0D9
  { r: 121, g: 151, b: 190 },// Sky #7997BE
  { r: 139, g: 120, b: 201 },// AI Purple #8B78C9
];

export function BrandIntro() {
  const [stage, setStage] = useState<IntroStage>("intro");

  const [reducedMotion, setReducedMotion] = useState(false);
  const [showDevReplay, setShowDevReplay] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number | null>(null);
  const timersRef = useRef<NodeJS.Timeout[]>([]);

  const clearAllTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  const startAnimationSequence = useCallback((reduced: boolean) => {
    clearAllTimers();

    if (reduced) {
      setStage("logo-enter");
      const t1 = setTimeout(() => setStage("page-reveal"), 800);
      const t2 = setTimeout(() => {
        setStage("complete");
        document.body.style.overflow = "";
        try {
          sessionStorage.setItem("handover_intro_seen", "1");
        } catch {}
      }, 1300);
      timersRef.current = [t1, t2];
      return;
    }

    // Precise timed stages
    // 0ms - 50ms: Clean white screen
    // 50ms - 500ms: Logo fades & scales in smoothly
    // 500ms - 1200ms: Logo held clearly with tagline "KNOWLEDGE CONTINUES."
    // 1200ms - 2000ms: Logo mark transforms into radiant 3D brand particles
    // 2000ms - 3100ms: Particles assemble into the rotating Organic Knowledge Sphere
    // 3100ms - 3800ms: White background veil fades away, revealing the landing page
    // 3800ms: Complete, unmounted, body scroll restored
    const t0 = setTimeout(() => setStage("logo-enter"), 50);
    const t1 = setTimeout(() => setStage("logo-hold"), 500);
    const t2 = setTimeout(() => setStage("transformation"), 1200);
    const t3 = setTimeout(() => setStage("network-reveal"), 2000);
    const t4 = setTimeout(() => setStage("page-reveal"), 3100);
    const t5 = setTimeout(() => {
      setStage("complete");
      document.body.style.overflow = "";
      try {
        sessionStorage.setItem("handover_intro_seen", "1");
      } catch {}
    }, 3900);

    timersRef.current = [t0, t1, t2, t3, t4, t5];
  }, [clearAllTimers]);

  // Main lifecycle
  useEffect(() => {
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setReducedMotion(prefersReduced);

    const isDev =
      process.env.NODE_ENV !== "production" ||
      window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1";
    setShowDevReplay(isDev);

    const params = new URLSearchParams(window.location.search);
    const forceReplay = params.get("replay") === "1" || params.get("intro") === "1";
    const alreadySeen = sessionStorage.getItem("handover_intro_seen") === "1";

    // In production, skip if already seen unless forced
    if (alreadySeen && !forceReplay && process.env.NODE_ENV === "production") {
      setStage("complete");
      return;
    }

    // Lock body scrolling during the brand introduction
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    startAnimationSequence(prefersReduced);

    return () => {
      clearAllTimers();
      document.body.style.overflow = prevOverflow;
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [startAnimationSequence, clearAllTimers]);

  // 3D Knowledge Particle & Sphere Emergence Renderer
  useEffect(() => {
    if (
      stage === "intro" ||
      stage === "logo-enter" ||
      stage === "logo-hold" ||
      stage === "complete" ||
      reducedMotion
    ) {
      if (animRef.current) {
        cancelAnimationFrame(animRef.current);
        animRef.current = null;
      }
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let W = (canvas.width = window.innerWidth);
    let H = (canvas.height = window.innerHeight);

    const onResize = () => {
      if (!canvas) return;
      W = canvas.width = window.innerWidth;
      H = canvas.height = window.innerHeight;
    };
    window.addEventListener("resize", onResize);

    // Build 64 3D nodes distributed organically on a sphere surface (Fibonacci spiral)
    const nodeCount = W < 640 ? 42 : 68;
    const nodes: SphereNode[] = [];
    const phi = Math.PI * (3 - Math.sqrt(5)); // Golden angle

    for (let i = 0; i < nodeCount; i++) {
      const y = 1 - (i / (nodeCount - 1)) * 2; // y goes from 1 to -1
      const radiusAtY = Math.sqrt(1 - y * y);
      const theta = phi * i;

      const sx = Math.cos(theta) * radiusAtY;
      const sy = y;
      const sz = Math.sin(theta) * radiusAtY;

      // Random jittered offset at origin
      const angle = Math.random() * Math.PI * 2;
      const initialR = 15 + Math.random() * 35;
      const ox = Math.cos(angle) * initialR;
      const oy = Math.sin(angle) * initialR;
      const oz = (Math.random() - 0.5) * 20;

      const colorObj = BRAND_PALETTE[i % BRAND_PALETTE.length]!;

      nodes.push({
        sx,
        sy,
        sz,
        x: ox,
        y: oy,
        z: oz,
        ox,
        oy,
        oz,
        radius: 1.6 + Math.random() * 2.2,
        color: `${colorObj.r}, ${colorObj.g}, ${colorObj.b}`,
        cluster: i % 4,
        phase: Math.random() * Math.PI * 2,
        speed: 0.6 + Math.random() * 0.8,
      });
    }

    let rotY = 0.4;
    const startTime = performance.now();
    let lastTime = startTime;

    const render = (now: number) => {
      const dt = Math.min((now - lastTime) / 1000, 0.05);
      lastTime = now;
      const elapsed = (now - startTime) / 1000;

      // Progress metrics
      // 0.0 -> 1.0 during transformation and network-reveal
      const transformProgress = Math.min(1, Math.max(0, (elapsed - 0.1) / 1.6));
      const smoothProg =
        transformProgress < 0.5
          ? 2 * transformProgress * transformProgress
          : 1 - Math.pow(-2 * transformProgress + 2, 2) / 2;

      ctx.clearRect(0, 0, W, H);

      const cx = W / 2;
      const cy = H / 2;
      const sphereRadius = Math.min(W * 0.38, H * 0.38, 220);

      // Slow elegant 3D rotation
      rotY += dt * 0.45;
      const cosR = Math.cos(rotY);
      const sinR = Math.sin(rotY);

      // 3D Perspective Projection
      const fov = 480;
      interface ProjectedNode {
        px: number;
        py: number;
        pz: number;
        scale: number;
        color: string;
        r: number;
        alpha: number;
      }

      const projected: ProjectedNode[] = [];

      nodes.forEach((n) => {
        // Interpolate position from origin to spherical target
        const targetX = n.sx * sphereRadius;
        const targetY = n.sy * sphereRadius;
        const targetZ = n.sz * sphereRadius;

        // Micro-organic breathing
        const breathe = Math.sin(elapsed * 1.8 + n.phase) * 6 * smoothProg;
        const curX = n.ox * (1 - smoothProg) + (targetX + n.sx * breathe) * smoothProg;
        const curY = n.oy * (1 - smoothProg) + (targetY + n.sy * breathe) * smoothProg;
        const curZ = n.oz * (1 - smoothProg) + (targetZ + n.sz * breathe) * smoothProg;

        // Rotate around Y-axis
        const rx = curX * cosR - curZ * sinR;
        const rz = curX * sinR + curZ * cosR;
        const ry = curY;

        // Perspective scaling
        const scale = fov / (fov + rz + sphereRadius * 1.2);
        const px = cx + rx * scale;
        const py = cy + ry * scale;

        // Alpha calculation: fade in progressively, depth modulated
        const depthAlpha = Math.max(0.15, Math.min(1, (rz + sphereRadius) / (sphereRadius * 2)));
        const baseAlpha = Math.min(1, elapsed * 1.4);
        const alpha = baseAlpha * (0.25 + 0.75 * depthAlpha);

        projected.push({
          px,
          py,
          pz: rz,
          scale,
          color: n.color,
          r: n.radius * scale,
          alpha,
        });
      });

      // Sort back to front for proper depth layering
      projected.sort((a, b) => a.pz - b.pz);

      // Draw delicate 3D connection filaments between nearby nodes
      ctx.lineWidth = 0.9;
      for (let i = 0; i < projected.length; i++) {
        for (let j = i + 1; j < projected.length; j++) {
          const a = projected[i]!;
          const b = projected[j]!;
          const dx = a.px - b.px;
          const dy = a.py - b.py;
          const dist = Math.hypot(dx, dy);

          const maxDist = 85 * smoothProg;
          if (dist < maxDist) {
            const lineAlpha = (1 - dist / maxDist) * Math.min(a.alpha, b.alpha) * 0.42;
            ctx.beginPath();
            ctx.moveTo(a.px, a.py);
            ctx.lineTo(b.px, b.py);
            ctx.strokeStyle = `rgba(${a.color}, ${lineAlpha})`;
            ctx.stroke();
          }
        }
      }

      // Draw 3D orbital rings as the sphere solidifies
      if (smoothProg > 0.4) {
        const ringAlpha = (smoothProg - 0.4) * 0.35;
        const ringRadii = [sphereRadius * 0.98, sphereRadius * 0.65];

        ringRadii.forEach((rr, rIdx) => {
          ctx.beginPath();
          ctx.ellipse(cx, cy, rr, rr * 0.35, rotY * 0.2 + rIdx * 0.5, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(49, 95, 186, ${ringAlpha})`;
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 7]);
          ctx.stroke();
          ctx.setLineDash([]);
        });
      }

      // Draw node particles
      projected.forEach((p) => {
        if (p.alpha <= 0.01) return;

        // Radiant halo
        const halo = ctx.createRadialGradient(p.px, p.py, 0, p.px, p.py, p.r * 3.5);
        halo.addColorStop(0, `rgba(${p.color}, ${p.alpha * 0.45})`);
        halo.addColorStop(1, `rgba(${p.color}, 0)`);
        ctx.fillStyle = halo;
        ctx.beginPath();
        ctx.arc(p.px, p.py, p.r * 3.5, 0, Math.PI * 2);
        ctx.fill();

        // Node center
        ctx.fillStyle = `rgba(${p.color}, ${p.alpha})`;
        ctx.beginPath();
        ctx.arc(p.px, p.py, p.r, 0, Math.PI * 2);
        ctx.fill();
      });

      animRef.current = requestAnimationFrame(render);
    };

    animRef.current = requestAnimationFrame(render);

    return () => {
      window.removeEventListener("resize", onResize);
      if (animRef.current) {
        cancelAnimationFrame(animRef.current);
        animRef.current = null;
      }
    };
  }, [stage, reducedMotion]);

  const handleSkip = () => {
    clearAllTimers();
    if (animRef.current) cancelAnimationFrame(animRef.current);
    document.body.style.overflow = "";
    setStage("complete");
    try {
      sessionStorage.setItem("handover_intro_seen", "1");
    } catch {}
  };

  const handleReplay = () => {
    if (animRef.current) cancelAnimationFrame(animRef.current);
    clearAllTimers();
    document.body.style.overflow = "hidden";
    setStage("intro");
    startAnimationSequence(reducedMotion);
  };

  if (stage === "complete") {
    // In dev mode, show a subtle floating pill to replay the intro anytime
    if (showDevReplay) {
      return (
        <button
          onClick={handleReplay}
          className="fixed bottom-4 left-16 z-40 flex items-center gap-1.5 rounded-full border border-[#D9E1F0] bg-white/90 px-3 py-1.5 font-mono text-[11px] font-semibold text-[#315FBA] shadow-md backdrop-blur-md hover:bg-white hover:border-[#315FBA] transition active:scale-95 cursor-pointer"
          title="Replay Branded Opening Animation"
        >
          <span className="size-2 rounded-full bg-[#315FBA] animate-pulse" />
          Replay Intro
        </button>
      );
    }
    return null;
  }

  const isFadingVeil = stage === "page-reveal";

  return (
    <div
      className={`fixed inset-0 z-50 flex flex-col items-center justify-center bg-white transition-opacity duration-800 ease-out select-none ${
        isFadingVeil ? "opacity-0 pointer-events-none" : "opacity-100 pointer-events-auto"
      }`}
      aria-label="Handover Brand Introduction"
    >
      {/* Background 3D Particle & Sphere Emergence Canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 pointer-events-none z-0"
      />

      {/* Skip Button */}
      <button
        onClick={handleSkip}
        className="absolute top-6 right-6 z-20 rounded-lg px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider text-[#718096]/70 hover:text-[#203653] hover:bg-slate-50 transition cursor-pointer"
        aria-label="Skip brand intro"
      >
        Skip
      </button>

      {/* Center Brand Identity Container */}
      <div className="relative z-10 flex flex-col items-center justify-center text-center px-6">
        {/* Logo Container */}
        <div
          className={`flex items-center justify-center transition-all duration-700 ease-out ${
            stage === "intro"
              ? "opacity-0 scale-95 translate-y-1"
              : stage === "logo-enter" || stage === "logo-hold"
              ? "opacity-100 scale-100 translate-y-0"
              : stage === "transformation"
              ? "opacity-80 scale-105 -translate-y-1 blur-[0.5px]"
              : "opacity-0 scale-125 -translate-y-2 pointer-events-none"
          }`}
        >
          {stage === "transformation" || stage === "network-reveal" ? (
            /* Radiant Symbol Mark dissolving into particles */
            <img
              src="/handover-mark.png"
              alt="Handover"
              className="h-11 sm:h-13 w-auto object-contain drop-shadow-[0_4px_24px_rgba(49,95,186,0.22)] animate-pulse"
            />
          ) : (
            /* Full Official Logo during Opening Screen */
            <img
              src="/handover-logo.png"
              alt="Handover"
              className="h-12 sm:h-14 w-auto object-contain drop-shadow-[0_2px_12px_rgba(32,54,83,0.06)]"
            />
          )}
        </div>

        {/* Tagline */}
        <p
          className={`mt-4 font-mono text-[11px] sm:text-[12.5px] font-semibold uppercase tracking-[0.26em] text-[#7997BE] transition-all duration-500 ease-out ${
            stage === "logo-enter" || stage === "logo-hold"
              ? "opacity-100 translate-y-0"
              : "opacity-0 -translate-y-2 pointer-events-none"
          }`}
        >
          Knowledge Continues.
        </p>
      </div>
    </div>
  );
}

export default BrandIntro;
