"use client";

import React from "react";
import Link from "next/link";
import {
  BrainCircuit,
  Network,
  CheckCircle2,
  AlertTriangle,
  FileCheck2,
  Archive,
  Bot,
  ScrollText,
  Sliders,
  ArrowRight,
  Database,
  Layers,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

interface Phase2ModuleViewProps {
  moduleKey:
    | "knowledge"
    | "relationships"
    | "verification"
    | "conflicts"
    | "handover"
    | "generated-handovers"
    | "assistant"
    | "audit"
    | "settings";
}

interface ModuleSpec {
  title: string;
  description: string;
  category: string;
  icon: React.ComponentType<{ className?: string }>;
  workflowStep: string;
  requirements: string[];
}

const MODULE_SPECS: Record<string, ModuleSpec> = {
  knowledge: {
    title: "Knowledge Intelligence",
    description:
      "Structured knowledge reconstruction across the 8 critical domains: Decisions & Rationale, Architecture, Work Status, Ownership, Dependencies, Risks & Blockers, Operational Procedures, and Context.",
    category: "PROJECT INTELLIGENCE",
    icon: BrainCircuit,
    workflowStep: "RECONSTRUCT",
    requirements: [
      "Requires ingested and chunked evidence in Evidence Workspace",
      "Executes Ollama Qwen3 8B reasoning with structured JSON extraction",
      "Assigns confidence scoring and provenance citation links",
    ],
  },
  relationships: {
    title: "Relationship Explorer",
    description:
      "Interactive relational knowledge graph visualizing dependencies, decisions, responsibilities, and architectural links across sources.",
    category: "PROJECT INTELLIGENCE",
    icon: Network,
    workflowStep: "RECONSTRUCT",
    requirements: [
      "Backed by canonical PostgreSQL relationships schema",
      "Visualized via React Flow and interactive graph layouts",
      "Strict project isolation and source ACL filtering",
    ],
  },
  verification: {
    title: "Verification Center",
    description:
      "Human review queue for candidate findings, evidence validation, and fact verification states before handover compilation.",
    category: "VALIDATION",
    icon: CheckCircle2,
    workflowStep: "VERIFY",
    requirements: [
      "Human-in-the-loop validation of AI-extracted facts",
      "Four-tier epistemic separation: Source -> Extracted -> AI -> Human Verified",
      "Immutable verification audit logs in PostgreSQL",
    ],
  },
  conflicts: {
    title: "Conflicts & Contradictions",
    description:
      "Automated detection and human adjudication of contradictory facts or conflicting timelines across disparate sources.",
    category: "VALIDATION",
    icon: AlertTriangle,
    workflowStep: "VERIFY",
    requirements: [
      "Cross-source contradiction analysis (e.g. Jira vs GitHub)",
      "Uncertainty disclosure: System never guesses when evidence conflicts",
      "Reviewer resolution interface with supporting citation comparison",
    ],
  },
  handover: {
    title: "Handover Workspace",
    description:
      "Compilation, role-specific checklists, and structured review workflows for producing auditable handover packages.",
    category: "KNOWLEDGE TRANSFER",
    icon: FileCheck2,
    workflowStep: "REVIEW & HANDOVER",
    requirements: [
      "Role-appropriate handover package tailoring (Dev, PM, Lead, Ops)",
      "Mandatory human reviewer approval before sharing",
      "Incoming assignee receipt acknowledgement governance",
    ],
  },
  "generated-handovers": {
    title: "Generated Handovers Archive",
    description:
      "Versioned, cryptographically sealed handover dossiers with full audit trails and receipt tracking.",
    category: "KNOWLEDGE TRANSFER",
    icon: Archive,
    workflowStep: "HANDOVER",
    requirements: [
      "Immutable snapshot storage of approved handover packages",
      "Multi-format export (Interactive Web, Markdown, PDF)",
      "Successor onboarding and receipt acknowledgement tracking",
    ],
  },
  assistant: {
    title: "Project Knowledge Assistant",
    description:
      "Permission-filtered hybrid RAG assistant with strict source citations, source ACL checks, and uncertainty disclosure.",
    category: "AI ASSISTANT",
    icon: Bot,
    workflowStep: "HYBRID RAG ASSISTANT",
    requirements: [
      "Pre-retrieval source permission check: Project membership != source access",
      "Hybrid retrieval: nomic-embed-text vector search + PostgreSQL full-text search",
      "Mandatory citation linking and explicit disclosure of missing evidence",
    ],
  },
  audit: {
    title: "Audit Logs",
    description:
      "Immutable PostgreSQL audit trail of all sensitive operations, credential modifications, and verification decisions.",
    category: "ADMINISTRATION",
    icon: ScrollText,
    workflowStep: "COMPLIANCE & GOVERNANCE",
    requirements: [
      "Append-only audit_logs records in PostgreSQL",
      "Captures actor identity, event type, metadata, and timestamps",
      "Non-repudiation for security and organizational accountability",
    ],
  },
  settings: {
    title: "System & Project Settings",
    description:
      "Configuration for organisation parameters, vector indexing thresholds, and local Ollama inference runtime parameters.",
    category: "ADMINISTRATION",
    icon: Sliders,
    workflowStep: "CONFIGURATION",
    requirements: [
      "Ollama inference concurrency limiter (RTX 4050 6GB VRAM bounds)",
      "ChromaDB collection health and vector dimension checks",
      "Supabase Auth and storage bucket parameters",
    ],
  },
};

export function Phase2ModuleView({ moduleKey }: Phase2ModuleViewProps) {
  const spec: ModuleSpec = MODULE_SPECS[moduleKey] ?? MODULE_SPECS["knowledge"]!;
  const Icon = spec.icon;
  const { activeProject } = useLiveApp();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] p-5 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-[#4774A9] uppercase tracking-wider">
            <span>{spec.category}</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#249E91]" />
            <span className="text-[#249E91] font-semibold">{spec.workflowStep}</span>
          </div>
          <h1 className="text-xl font-bold text-[#25334B] mt-1 tracking-tight">
            {spec.title}
          </h1>
          <p className="text-xs text-[#69778D] mt-0.5 max-w-2xl">
            {spec.description}
          </p>
        </div>

        <Link
          href="/evidence"
          className="px-4 py-2.5 rounded-lg bg-[#249E91] hover:bg-[#1D8277] text-white text-xs font-semibold flex items-center gap-2 transition-colors shadow-xs shrink-0"
        >
          <Database className="w-4 h-4" />
          <span>Go to Evidence Center</span>
        </Link>
      </div>

      {/* Architectural Boundary Card */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] p-6 shadow-2xs space-y-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#E8EEF5] text-[#4774A9] flex items-center justify-center shrink-0">
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-[#25334B]">
              Module Scheduled for Phase 2 Reconstruction
            </h3>
            <p className="text-xs text-[#69778D] mt-1 leading-relaxed max-w-3xl">
              In accordance with project engineering rules, backend schemas and data contracts for this module are established in the canonical database. Active user interaction begins once source connections and evidence ingestion are populated in <strong>Evidence Workspace (Module 2)</strong>.
            </p>
          </div>
        </div>

        {/* Requirements checklist */}
        <div className="pt-4 border-t border-[#DCE3EB]">
          <div className="text-xs font-bold text-[#25334B] uppercase tracking-wider mb-2.5">
            Architecture &amp; Pipeline Requirements
          </div>
          <ul className="space-y-2 text-xs text-[#69778D]">
            {spec.requirements.map((req, idx) => (
              <li key={idx} className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#4774A9]" />
                <span>{req}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="pt-4 border-t border-[#DCE3EB] flex items-center justify-between">
          <div className="text-[11px] text-[#69778D]">
            Active Workspace: <strong>{activeProject ? activeProject.name : "Select Project"}</strong>
          </div>
          <Link
            href="/overview"
            className="text-xs font-semibold text-[#4774A9] hover:underline flex items-center gap-1"
          >
            <span>Return to Workspace Overview</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
}
