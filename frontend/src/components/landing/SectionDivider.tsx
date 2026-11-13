"use client";

import React, { useEffect, useRef, useState } from "react";

interface SectionDividerProps {
  className?: string;
  id?: string;
  label?: string;
}

export function SectionDivider({ className = "", id, label }: SectionDividerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    let timeoutId: ReturnType<typeof setTimeout>;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry) return;
        if (entry.isIntersecting) {
          setIsVisible(true);
          setIsTransitioning(true);
          timeoutId = setTimeout(() => {
            setIsTransitioning(false);
          }, 2400);
        } else {
          setIsVisible(false);
          setIsTransitioning(false);
        }
      },
      {
        threshold: 0.05,
        rootMargin: "60px 0px 60px 0px",
      }
    );

    observer.observe(el);

    return () => {
      observer.disconnect();
      clearTimeout(timeoutId);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      id={id}
      className={`relative w-full overflow-hidden ${className}`}
      aria-hidden="true"
    >
      {/* Base Hairline (#D9E1F0) */}
      <div className="h-px w-full bg-[#D9E1F0]/80" />

      {/* Travelling Gradient Beam (#315FBA -> #7997BE -> transparent) */}
      {isVisible && (
        <div
          className={`pointer-events-none absolute inset-y-0 left-0 h-px w-48 sm:w-80 transition-opacity duration-700 ${
            isTransitioning ? "opacity-90" : "opacity-45"
          }`}
          style={{
            animation: "beam-travel 3.6s cubic-bezier(0.22, 1, 0.36, 1) infinite",
            background:
              "linear-gradient(90deg, transparent 0%, rgba(49, 95, 186, 0.9) 50%, rgba(121, 151, 190, 0.6) 80%, transparent 100%)",
          }}
        />
      )}

      {/* Theme B Monospaced Section Identifier */}
      {label && (
        <div className="absolute right-6 top-1/2 -translate-y-1/2 select-none font-mono text-[9.5px] tracking-[0.14em] text-[#7997BE]/60 uppercase hidden sm:block">
          {label}
        </div>
      )}
    </div>
  );
}
