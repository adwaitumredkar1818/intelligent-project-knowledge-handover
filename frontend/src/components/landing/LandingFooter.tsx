"use client";

import React from "react";
import { Logo } from "../brand";
import { useLiveApp } from "../../context/LiveAppContext";
import { useRouter } from "next/navigation";

const scrollToSection = (id: string) => {
  const el = document.getElementById(id);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
};

export function LandingFooter() {
  const { user } = useLiveApp();
  const router = useRouter();

  const handleAuth = (mode: "login" | "register") => {
    if (user) {
      router.push("/overview");
    } else {
      router.push(mode === "login" ? "/login" : "/signup");
    }
  };

  const columns: {
    title: string;
    links: { label: string; action: () => void }[];
  }[] = [
    {
      title: "Product",
      links: [
        { label: "Knowledge Explorer", action: () => scrollToSection("explorer") },
        { label: "Knowledge Intelligence", action: () => scrollToSection("intelligence") },
        { label: "Structured Handovers", action: () => scrollToSection("handovers") },
        { label: "How It Works", action: () => scrollToSection("how") },
      ],
    },
    {
      title: "Solutions",
      links: [
        { label: "Project Managers", action: () => scrollToSection("roles") },
        { label: "Outgoing Members", action: () => scrollToSection("roles") },
        { label: "Incoming Successors", action: () => scrollToSection("roles") },
      ],
    },
    {
      title: "Trust & Governance",
      links: [
        { label: "Evidence & Verification", action: () => scrollToSection("security") },
        { label: "Frequently Asked Questions", action: () => scrollToSection("faq") },
      ],
    },
    {
      title: "Access",
      links: [
        { label: "Sign In to Workspace", action: () => handleAuth("login") },
        { label: "Create Account", action: () => handleAuth("register") },
        { label: "Project Overview", action: () => router.push("/overview") },
      ],
    },
  ];

  return (
    <footer className="border-t border-[#D9E1F0] bg-white">
      <div className="mx-auto w-full max-w-[1240px] px-5 sm:px-8">
        {/* Main Footer Columns */}
        <div className="grid gap-12 py-16 grid-cols-2 md:grid-cols-[1.4fr_repeat(4,1fr)]">
          <div className="col-span-2 md:col-span-1">
            <button
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              className="cursor-pointer focus:outline-none"
              aria-label="Handover home"
            >
              <Logo size={28} />
            </button>
            <p className="mt-4 max-w-xs text-[14px] leading-relaxed text-[#718096]">
              People change. Projects evolve. Critical knowledge should never disappear.
            </p>
            <p className="mt-6 font-mono text-[12px] tracking-[0.18em] text-[#7997BE] uppercase">
              KNOWLEDGE CONTINUES.
            </p>
          </div>

          {columns.map((col) => (
            <div key={col.title}>
              <p className="text-[13px] font-semibold text-[#203653] uppercase tracking-[0.05em]">
                {col.title}
              </p>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <button
                      onClick={link.action}
                      className="text-[14px] text-[#718096] transition hover:text-[#203653] cursor-pointer text-left"
                    >
                      {link.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom Subfooter */}
        <div className="flex flex-col gap-3 border-t border-[#D9E1F0] py-6 text-[13px] text-[#718096] sm:flex-row sm:items-center sm:justify-between">
          <span>© 2026 The Handover. All rights reserved.</span>
          <span className="font-mono text-[11px] sm:text-[12px] text-[#7997BE] max-w-xs sm:max-w-none text-center sm:text-left">
            Prevent Critical Knowledge From Leaving With People.
          </span>
          <div className="flex gap-5 justify-center sm:justify-end">
            <button
              onClick={() => handleAuth("login")}
              className="hover:text-[#203653] cursor-pointer"
            >
              Sign In
            </button>
            <button
              onClick={() => handleAuth("register")}
              className="hover:text-[#203653] cursor-pointer font-medium text-[#315FBA]"
            >
              Get Started
            </button>
          </div>
        </div>
      </div>
    </footer>
  );
}
