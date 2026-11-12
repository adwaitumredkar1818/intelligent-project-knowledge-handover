import Link from "next/link";
import { ArrowRight, Database } from "lucide-react";

export default function HomePage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#F4F6F9] p-6 text-[#25334B]">
      <div className="max-w-xl w-full rounded-xl border border-[#DCE3EB] bg-white p-6 sm:p-8 shadow-sm">
        <div className="flex items-center gap-2.5 text-xs font-semibold text-[#4774A9] uppercase tracking-wider mb-2">
          <div className="w-6 h-6 rounded bg-[#4774A9] text-white flex items-center justify-center font-bold text-xs">
            H
          </div>
          <span>The Handover · Interactive Prototype</span>
        </div>

        <h1 className="text-xl sm:text-2xl font-bold text-[#25334B] tracking-tight">
          Intelligent Project Knowledge Reconstruction &amp; Handover Platform
        </h1>

        <p className="mt-2 text-xs sm:text-sm text-[#69778D] leading-relaxed">
          Interactive evaluation prototype for <strong>Module 1 (Project Workspace)</strong> and{" "}
          <strong>Module 2 (Evidence Workspace)</strong>. Experience the persistent 6-group sidebar, project dashboard, and the 3-panel Evidence Center.
        </p>

        <div className="mt-4 p-3 rounded-lg bg-[#F4F6F9] border border-[#DCE3EB] text-xs space-y-1.5 font-mono text-[#69778D]">
          <div className="text-[10px] uppercase font-bold text-[#C48A32]">Demo Mode · Sample Data Only</div>
          <div>All interactive operations execute in local memory without modifying the backend.</div>
        </div>

        <div className="mt-6 flex flex-col sm:flex-row items-center gap-3">
          <Link
            href="/prototype/overview"
            className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-[#4774A9] hover:bg-[#365F92] text-white text-xs font-semibold flex items-center justify-center gap-2 transition-colors shadow-xs"
          >
            <span>Launch Project Workspace Prototype</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/prototype/evidence"
            className="w-full sm:w-auto px-4 py-2.5 rounded-lg bg-white hover:bg-[#F4F6F9] border border-[#DCE3EB] text-[#25334B] text-xs font-semibold flex items-center justify-center gap-2 transition-colors"
          >
            <Database className="w-4 h-4 text-[#249E91]" />
            <span>Open Evidence Center</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
