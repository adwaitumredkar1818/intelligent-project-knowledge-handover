"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  CheckCircle2,
  FileSearch,
  FolderPlus,
  GitBranch,
  ShieldCheck,
  Sparkles,
  Upload,
  UserPlus,
  Users,
  Workflow,
  BookOpen,
  ClipboardCheck,
} from "lucide-react";
import { Logo, SourceIcon } from "../brand";
import { SphereVisual } from "../ui";
import { useLiveApp } from "../../context/LiveAppContext";

const OB_STEPS = [
  "Welcome",
  "Profile",
  "Workspace",
  "Role",
  "Project",
  "How it works",
];

function ProductIntroStory() {
  const [act, setAct] = useState(0);
  const acts = [
    {
      id: "sources",
      icon: GitBranch,
      title: "1. Authorised sources enter",
      sub: "GitHub, Jira, Slack and project documents stream in with read-only scopes.",
      scene: (
        <SphereVisual
          variant="empty"
          emptyKind="sources"
          className="h-52 w-full"
        />
      ),
      ui: (
        <div className="space-y-2 rounded-xl border border-[#D9E1F0] bg-white p-3.5 text-left shadow-card min-w-0 overflow-hidden">
          <p className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-[#718096] truncate">
            2D interface · Data sources
          </p>
          {(["github", "jira", "slack", "docs"] as const).map((t, i) => (
            <div
              key={t}
              className="flex items-center gap-2 rounded-lg border border-[#D9E1F0]/80 px-2.5 py-1.5 text-[12px] min-w-0 overflow-hidden"
            >
              <span className="shrink-0 flex items-center">
                <SourceIcon type={t} size={22} />
              </span>
              <span className="flex-1 min-w-0 truncate font-medium text-[#203653]">
                {[
                  "atlas-settlement, atlas-ledger",
                  "PAY · Sprint records",
                  "#payments-arch, #incidents",
                  "ADR-007.pdf, Runbook v3.docx",
                ][i]}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2 py-0.5 text-[11px] font-semibold text-[#299B80] shrink-0">
                <span className="size-1.5 rounded-full bg-[#299B80]" />
                Authorised
              </span>
            </div>
          ))}
        </div>
      ),
    },
    {
      id: "reconstruct",
      icon: Sparkles,
      title: "2. Fragmented signals connect",
      sub: "Disconnected commits, threads and tickets converge into linked relationships.",
      scene: (
        <SphereVisual
          variant="reconstruct"
          progress={0.62}
          className="h-52 w-full"
        />
      ),
      ui: (
        <div className="space-y-3 rounded-xl border border-[#D9E1F0] bg-white p-3.5 text-left shadow-card min-w-0 overflow-hidden">
          <div className="flex items-center justify-between gap-2 min-w-0">
            <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-[#718096] truncate">
              2D interface · Reconstruction pipeline
            </span>
            <span className="font-mono text-[11px] text-[#315FBA] shrink-0">
              15,410 records
            </span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
            <div className="h-full w-[68%] rounded-full bg-[#315FBA]" />
          </div>
          <ul className="space-y-1.5 text-[12px] text-[#203653]">
            <li className="flex items-start gap-2 min-w-0">
              <CheckCircle2 className="size-3.5 text-[#299B80] shrink-0 mt-0.5" />
              <span className="leading-tight break-words">Extracted 25 candidate findings from 4 sources</span>
            </li>
            <li className="flex items-start gap-2 min-w-0">
              <CheckCircle2 className="size-3.5 text-[#299B80] shrink-0 mt-0.5" />
              <span className="leading-tight break-words">Linked PR #412 ↔ #payments-arch ↔ ADR-007</span>
            </li>
            <li className="flex items-start gap-2 min-w-0">
              <Sparkles className="size-3.5 text-[#315FBA] shrink-0 mt-0.5" />
              <span className="leading-tight break-words">Flagged 1 retention conflict & 3 knowledge gaps</span>
            </li>
          </ul>
        </div>
      ),
    },
    {
      id: "emerge",
      icon: FileSearch,
      title: "3. Structured intelligence emerges",
      sub: "Decisions, responsibilities, risks and dependencies crystallise on the sphere.",
      scene: (
        <SphereVisual variant="hero" showTags className="h-52 w-full" />
      ),
      ui: (
        <div className="grid grid-cols-2 gap-2 rounded-xl border border-[#D9E1F0] bg-white p-3.5 text-left shadow-card min-w-0">
          <p className="col-span-2 font-mono text-[10.5px] uppercase tracking-[0.1em] text-[#718096]">
            2D interface · Reconstructed intelligence
          </p>
          {[
            ["Decisions", "6 reconstructed", "Why Kafka replaced sync settlement", "#315FBA"],
            ["Responsibilities", "4 transferring", "Settlement service & Vault rotation", "#299B80"],
            ["Risks", "1 critical", "No retry on acquirer 504 timeouts", "#D36D72"],
            ["Dependencies", "2 blocking", "SOAP cutover blocked by PAY-1204", "#D39B43"],
          ].map(([k, m, d, c]) => (
            <div key={k} className="rounded-lg border border-[#D9E1F0]/80 p-2.5 min-w-0 overflow-hidden bg-white">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="size-1.5 shrink-0 rounded-full" style={{ background: c }} />
                <span className="text-[11.5px] font-semibold text-[#203653] truncate">{k}</span>
              </div>
              <span className="mt-0.5 block font-mono text-[10px] text-[#718096] truncate">{m}</span>
              <p className="mt-1 truncate text-[11px] text-[#718096]" title={d}>{d}</p>
            </div>
          ))}
        </div>
      ),
    },
    {
      id: "verify",
      icon: ClipboardCheck,
      title: "4. Human verification & evidence",
      sub: "Outgoing members inspect AI confidence against original source evidence.",
      scene: <SphereVisual variant="macro" className="h-52 w-full" />,
      ui: (
        <div className="space-y-2.5 rounded-xl border border-[#D9E1F0] bg-white p-3.5 text-left shadow-card min-w-0 overflow-hidden">
          <p className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-[#718096] truncate">
            2D interface · Review & verification
          </p>
          <p className="text-[13px] font-semibold text-[#203653] leading-snug break-words">
            Decouple settlement from ledger using Kafka events
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">
              <Sparkles className="size-3" />
              94% confidence
            </span>
            <span className="inline-flex items-center gap-1 rounded-md border border-teal-200 bg-teal-50 px-2 py-0.5 text-xs font-semibold text-[#299B80]">
              <ShieldCheck className="size-3" />
              Human Verified
            </span>
            <span className="font-mono text-[11px] text-[#718096]">
              3 linked sources
            </span>
          </div>
          <p className="rounded-lg bg-[#F6F8FC] px-2.5 py-1.5 text-[11.5px] text-[#718096] leading-relaxed break-words">
            AI confidence (model certainty) is never conflated with human verification.
          </p>
        </div>
      ),
    },
    {
      id: "transfer",
      icon: BookOpen,
      title: "5. Structured handover continues",
      sub: "Managers approve and publish; incoming members step in with full context.",
      scene: <SphereVisual variant="continuity" className="h-52 w-full" />,
      ui: (
        <div className="space-y-2.5 rounded-xl border border-[#D9E1F0] bg-white p-3.5 text-left shadow-card min-w-0 overflow-hidden">
          <div className="flex items-center justify-between gap-2 min-w-0">
            <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-[#718096] truncate">
              2D interface · Published handover
            </span>
            <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2 py-0.5 text-[11px] font-semibold text-[#299B80] shrink-0">
              <span className="size-1.5 rounded-full bg-[#299B80]" />
              HO-1042 · Published
            </span>
          </div>
          <p className="text-[13px] font-semibold text-[#203653] leading-snug break-words">
            James Okafor → Priya Nair · Atlas Payments
          </p>
          <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
            <div className="h-full w-full rounded-full bg-[#299B80]" />
          </div>
          <p className="text-[11.5px] text-[#718096] leading-relaxed break-words">
            Includes 12-section report, interactive knowledge graph and evidence-grounded AI assistant.
          </p>
        </div>
      ),
    },
  ];

  const cur = acts[act] ?? acts[0]!;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-xl font-semibold text-[#203653]">How Handover works</h2>
          <p className="mt-1 text-sm text-[#718096]">
            3D knowledge continuity paired with precise 2D verification and handover workflows.
          </p>
        </div>
        <span className="font-mono text-xs text-[#315FBA]">
          Act {act + 1} of {acts.length}
        </span>
      </div>

      <div className="mt-5 grid grid-cols-5 gap-1.5">
        {acts.map((a, i) => (
          <button
            key={a.id}
            type="button"
            onClick={() => setAct(i)}
            className={`rounded-xl border p-2 text-left transition cursor-pointer min-w-0 overflow-hidden ${
              i === act
                ? "border-[#315FBA] bg-indigo-50/60 shadow-xs"
                : "border-[#D9E1F0] bg-white hover:bg-[#F6F8FC]"
            }`}
          >
            <a.icon
              className={`size-4 shrink-0 ${i === act ? "text-[#315FBA]" : "text-[#718096]"}`}
            />
            <p className="mt-1.5 text-[11px] sm:text-[11.5px] font-semibold text-[#203653] truncate">
              {["1. Sources", "2. Connect", "3. Emerge", "4. Verify", "5. Transfer"][i]}
            </p>
          </button>
        ))}
      </div>

      <div
        key={cur.id}
        className="mt-4 grid items-center gap-4 rounded-2xl border border-[#D9E1F0] bg-[#F6F8FC]/60 p-4 sm:grid-cols-2 min-w-0"
      >
        <div className="flex flex-col items-center min-w-0 w-full">
          {cur.scene}
          <div className="mt-2 text-center max-w-full px-2">
            <p className="text-[14px] font-semibold text-[#203653] break-words">{cur.title}</p>
            <p className="mt-0.5 text-[12.5px] text-[#718096] break-words">{cur.sub}</p>
          </div>
        </div>
        <div className="min-w-0 w-full">{cur.ui}</div>
      </div>
    </div>
  );
}

export function OnboardingPage() {
  const router = useRouter();
  const { user } = useLiveApp();

  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState({
    name: user?.full_name || "Maya Chen",
    title: "Engineering Manager",
    team: "Platform & Payments",
  });
  const [wsMode, setWsMode] = useState<"create" | "join">("join");
  const [wsName, setWsName] = useState("");
  const [role, setRole] = useState<"manager" | "outgoing" | "incoming">("manager");
  const [projMode, setProjMode] = useState<"invite" | "create">("invite");
  const [proj, setProj] = useState({
    name: "",
    category: "Backend platform",
  });
  const [accepted, setAccepted] = useState<string[]>(["orion", "helix"]);

  const next = () => setStep((x) => Math.min(OB_STEPS.length - 1, x + 1));
  const finish = () => {
    router.push("/overview");
  };

  const canNext = step !== 2 || wsMode === "join" || wsName.trim().length > 1;

  return (
    <div className="min-h-screen bg-[#F6F8FC]">
      {/* Header */}
      <header className="flex h-16 items-center justify-between border-b border-[#D9E1F0] bg-white px-5 sm:px-8">
        <Link href="/" aria-label="Handover home">
          <Logo size={28} />
        </Link>
        <button
          onClick={finish}
          className="text-[13px] font-medium text-[#718096] hover:text-[#203653] transition cursor-pointer"
        >
          Skip for now
        </button>
      </header>

      {/* Main Container */}
      <div className="mx-auto max-w-3xl px-4 py-8 sm:py-12">
        {/* Step Progress Bar */}
        <ol className="mb-8 flex items-center gap-2">
          {OB_STEPS.map((l, i) => (
            <li key={l} className="flex flex-1 flex-col gap-2">
              <span
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  i <= step ? "bg-[#315FBA]" : "bg-slate-200"
                }`}
              />
              <span
                className={`hidden text-xs font-medium sm:block ${
                  i === step ? "text-[#203653] font-semibold" : "text-slate-400"
                }`}
              >
                {i + 1}. {l}
              </span>
            </li>
          ))}
        </ol>

        {/* Step Card */}
        <div className="rounded-2xl border border-[#D9E1F0] bg-white p-6 shadow-card sm:p-10">
          {/* Step 0: Welcome */}
          {step === 0 && (
            <div className="text-center">
              <div className="mx-auto size-48 sm:size-56">
                <SphereVisual variant="hero" className="size-full" />
              </div>
              <h1 className="mt-3 text-2xl font-semibold tracking-tight text-[#203653] sm:text-3xl">
                Welcome to Handover
              </h1>
              <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-[#718096]">
                In a few steps you&apos;ll set up your profile and workspace. If a teammate already invited you to a project, you can jump straight into it.
              </p>
              <div className="mt-8 grid gap-3 text-left sm:grid-cols-3">
                {[
                  [FileSearch, "Capture", "Ingest code, issues, chats and documents"],
                  [ShieldCheck, "Verify", "People confirm AI findings with evidence"],
                  [Workflow, "Transfer", "Publish structured, trusted handovers"],
                ].map(([I, t, d]) => {
                  const Ic = I as typeof FileSearch;
                  return (
                    <div
                      key={t as string}
                      className="rounded-xl border border-[#D9E1F0] p-4 bg-[#F6F8FC]/50 hover:bg-[#F6F8FC] transition"
                    >
                      <Ic className="size-5 text-[#315FBA]" />
                      <p className="mt-2 text-sm font-semibold text-[#203653]">{t as string}</p>
                      <p className="mt-0.5 text-xs text-[#718096]">{d as string}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Step 1: Complete your profile */}
          {step === 1 && (
            <div>
              <h2 className="text-xl font-semibold text-[#203653]">Complete your profile</h2>
              <p className="mt-1 text-sm text-[#718096]">
                Your name and role help teammates know who verified what.
              </p>
              <div className="mt-6 flex items-center gap-4">
                <span className="flex size-16 items-center justify-center rounded-full bg-indigo-50 text-xl font-semibold text-[#315FBA]">
                  {profile.name
                    .split(" ")
                    .map((x) => x[0])
                    .join("")
                    .slice(0, 2)
                    .toUpperCase()}
                </span>
                <button
                  type="button"
                  className="flex items-center gap-1.5 rounded-xl border border-[#D9E1F0] bg-white px-3.5 py-2 text-xs font-semibold text-[#203653] hover:bg-[#F6F8FC] transition cursor-pointer"
                >
                  <Upload className="size-3.5" />
                  Upload photo
                </button>
              </div>
              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#718096] mb-1.5">
                    Full name
                  </label>
                  <input
                    value={profile.name}
                    onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                    className="w-full h-11 rounded-xl border border-[#D9E1F0] bg-white px-3.5 text-sm text-[#203653] focus:border-[#315FBA] focus:outline-none focus:ring-1 focus:ring-[#315FBA] transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#718096] mb-1.5">
                    Job title
                  </label>
                  <input
                    value={profile.title}
                    onChange={(e) => setProfile({ ...profile, title: e.target.value })}
                    className="w-full h-11 rounded-xl border border-[#D9E1F0] bg-white px-3.5 text-sm text-[#203653] focus:border-[#315FBA] focus:outline-none focus:ring-1 focus:ring-[#315FBA] transition"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#718096] mb-1.5">
                    Team
                  </label>
                  <input
                    value={profile.team}
                    onChange={(e) => setProfile({ ...profile, team: e.target.value })}
                    className="w-full h-11 rounded-xl border border-[#D9E1F0] bg-white px-3.5 text-sm text-[#203653] focus:border-[#315FBA] focus:outline-none focus:ring-1 focus:ring-[#315FBA] transition"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Create or join workspace */}
          {step === 2 && (
            <div>
              <h2 className="text-xl font-semibold text-[#203653]">Create or join a workspace</h2>
              <p className="mt-1 text-sm text-[#718096]">
                A workspace holds your organisation&apos;s projects, members and integrations.
              </p>
              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                {[
                  ["join", Users, "Join existing", "You have 1 pending invitation"],
                  ["create", Building2, "Create new", "Start a fresh workspace for your team"],
                ].map(([id, I, t, d]) => {
                  const Ic = I as typeof Users;
                  return (
                    <button
                      key={id as string}
                      onClick={() => setWsMode(id as "join" | "create")}
                      className={`rounded-xl border p-4 text-left transition cursor-pointer ${
                        wsMode === id
                          ? "border-[#315FBA] bg-indigo-50/40 ring-2 ring-[#315FBA]/20"
                          : "border-[#D9E1F0] hover:border-slate-300"
                      }`}
                    >
                      <Ic className="size-5 text-[#315FBA]" />
                      <p className="mt-2 text-sm font-semibold text-[#203653]">{t as string}</p>
                      <p className="text-xs text-[#718096]">{d as string}</p>
                    </button>
                  );
                })}
              </div>

              {wsMode === "join" ? (
                <div className="mt-5 flex items-center gap-3 rounded-xl border border-[#D9E1F0] p-4 bg-[#F6F8FC]/50">
                  <span className="flex size-10 items-center justify-center rounded-lg bg-[#203653] text-sm font-bold text-white">
                    N
                  </span>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-[#203653]">Northwind Labs</p>
                    <p className="text-xs text-[#718096]">Invited by Tom Whitfield · 42 members</p>
                  </div>
                  <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2.5 py-1 text-xs font-semibold text-[#299B80]">
                    <Check className="size-3.5" />
                    Will join
                  </span>
                </div>
              ) : (
                <div className="mt-5 grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-[#718096] mb-1.5">
                      Workspace name
                    </label>
                    <input
                      value={wsName}
                      onChange={(e) => setWsName(e.target.value)}
                      placeholder="Acme Engineering"
                      className="w-full h-11 rounded-xl border border-[#D9E1F0] bg-white px-3.5 text-sm text-[#203653] focus:border-[#315FBA] focus:outline-none focus:ring-1 focus:ring-[#315FBA] transition"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-[#718096] mb-1.5">
                      Workspace URL
                    </label>
                    <input
                      value={`${
                        wsName.toLowerCase().replace(/[^a-z0-9]+/g, "-") || "acme"
                      }.handover.app`}
                      readOnly
                      className="w-full h-11 rounded-xl border border-[#D9E1F0] bg-slate-50 px-3.5 text-sm text-[#718096]"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Role Selection */}
          {step === 3 && (
            <div>
              <h2 className="text-xl font-semibold text-[#203653]">
                How will you mostly use Handover?
              </h2>
              <p className="mt-1 text-sm text-[#718096]">
                This personalises your first dashboard. Roles are assigned per project, so you can be a manager on one project and an incoming member on another.
              </p>
              <div className="mt-6 space-y-3">
                {[
                  {
                    id: "manager" as const,
                    title: "I manage projects and approve handovers",
                    desc: "Connect sources, monitor reconstruction, approve and publish.",
                    badge: "Project Manager",
                  },
                  {
                    id: "outgoing" as const,
                    title: "I'm leaving a project and handing it over",
                    desc: "Verify what the AI found, fill gaps, submit for approval.",
                    badge: "Outgoing Owner",
                  },
                  {
                    id: "incoming" as const,
                    title: "I'm joining a project and receiving knowledge",
                    desc: "Explore a published handover and ask grounded questions.",
                    badge: "Incoming Successor",
                  },
                ].map((item) => (
                  <div
                    key={item.id}
                    onClick={() => setRole(item.id)}
                    className={`flex items-start gap-3 rounded-xl border p-4 transition cursor-pointer ${
                      role === item.id
                        ? "border-[#315FBA] bg-indigo-50/40 ring-1 ring-[#315FBA]"
                        : "border-[#D9E1F0] hover:border-slate-300"
                    }`}
                  >
                    <input
                      type="radio"
                      name="role"
                      checked={role === item.id}
                      onChange={() => setRole(item.id)}
                      className="mt-1 size-4 text-[#315FBA] focus:ring-[#315FBA]"
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-[#203653]">{item.title}</span>
                        <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-[#718096]">
                          {item.badge}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-[#718096]">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Step 4: First Project */}
          {step === 4 && (
            <div>
              <h2 className="text-xl font-semibold text-[#203653]">
                {role === "manager"
                  ? "Create your first project"
                  : "Accept your project invitations"}
              </h2>
              <p className="mt-1 text-sm text-[#718096]">
                {role === "manager"
                  ? "Or accept projects you were invited to."
                  : "You don't need to create a project. Accept the invitations below to continue."}
              </p>

              <div className="mt-5 inline-flex rounded-xl border border-[#D9E1F0] bg-slate-50 p-1">
                {(["invite", "create"] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setProjMode(m)}
                    className={`rounded-lg px-3.5 py-1.5 text-xs font-semibold transition cursor-pointer ${
                      projMode === m
                        ? "bg-white text-[#203653] shadow-xs"
                        : "text-[#718096] hover:text-[#203653]"
                    }`}
                  >
                    {m === "invite" ? "Invitations (2)" : "Create project"}
                  </button>
                ))}
              </div>

              {projMode === "invite" ? (
                <div className="mt-4 space-y-2.5">
                  {[
                    { id: "orion", name: "Orion Mobile App", by: "Sofia Alvarez", role: "Outgoing" },
                    { id: "helix", name: "Helix Data Pipeline", by: "Tom Whitfield", role: "Incoming" },
                  ].map((p) => (
                    <div
                      key={p.id}
                      className="flex flex-wrap items-center gap-3 rounded-xl border border-[#D9E1F0] p-4 bg-[#F6F8FC]/50"
                    >
                      <FolderPlus className="size-5 text-[#315FBA]" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-[#203653]">{p.name}</p>
                        <p className="text-xs text-[#718096]">Invited by {p.by}</p>
                      </div>
                      <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-[#718096]">
                        {p.role}
                      </span>
                      <button
                        type="button"
                        onClick={() =>
                          setAccepted((a) =>
                            a.includes(p.id) ? a.filter((x) => x !== p.id) : [...a, p.id]
                          )
                        }
                        className={`inline-flex items-center gap-1 rounded-xl px-3 py-1.5 text-xs font-semibold transition cursor-pointer ${
                          accepted.includes(p.id)
                            ? "bg-teal-50 text-[#299B80] border border-teal-200"
                            : "bg-white text-[#203653] border border-[#D9E1F0] hover:bg-[#F6F8FC]"
                        }`}
                      >
                        {accepted.includes(p.id) ? (
                          <>
                            <Check className="size-3" />
                            Accepted
                          </>
                        ) : (
                          "Accept"
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-[#718096] mb-1.5">
                      Project name
                    </label>
                    <input
                      value={proj.name}
                      onChange={(e) => setProj({ ...proj, name: e.target.value })}
                      placeholder="e.g. Billing Revamp"
                      className="w-full h-11 rounded-xl border border-[#D9E1F0] bg-white px-3.5 text-sm text-[#203653] focus:border-[#315FBA] focus:outline-none focus:ring-1 focus:ring-[#315FBA] transition"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-[#718096] mb-1.5">
                      Category
                    </label>
                    <select
                      value={proj.category}
                      onChange={(e) => setProj({ ...proj, category: e.target.value })}
                      className="w-full h-11 rounded-xl border border-[#D9E1F0] bg-white px-3 text-sm text-[#203653] focus:border-[#315FBA] focus:outline-none focus:ring-1 focus:ring-[#315FBA] transition"
                    >
                      {[
                        "Backend platform",
                        "Mobile",
                        "Data & analytics",
                        "Design system",
                        "Infrastructure",
                      ].map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 5: How it works story */}
          {step === 5 && <ProductIntroStory />}

          {/* Navigation Controls */}
          <div className="mt-10 flex items-center justify-between border-t border-[#D9E1F0] pt-5">
            <button
              type="button"
              disabled={step === 0}
              onClick={() => setStep(step - 1)}
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#718096] hover:text-[#203653] disabled:opacity-0 transition cursor-pointer"
            >
              <ArrowLeft className="size-4" />
              Back
            </button>

            {step < OB_STEPS.length - 1 ? (
              <button
                type="button"
                disabled={!canNext}
                onClick={next}
                className="inline-flex items-center gap-1.5 rounded-xl bg-[#203653] px-5 py-2.5 text-sm font-semibold text-white shadow-xs hover:bg-[#2b466c] active:scale-[0.99] disabled:opacity-50 transition cursor-pointer"
              >
                {step === 0 ? "Get started" : "Continue"}
                <ArrowRight className="size-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={finish}
                className="inline-flex items-center gap-1.5 rounded-xl bg-[#315FBA] px-5 py-2.5 text-sm font-semibold text-white shadow-xs hover:bg-[#203653] active:scale-[0.99] transition cursor-pointer"
              >
                Go to workspace
                <ArrowRight className="size-4" />
              </button>
            )}
          </div>
        </div>

        <p className="mt-4 flex items-center justify-center gap-1.5 text-xs text-[#718096]">
          <UserPlus className="size-3.5" />
          Step {step + 1} of {OB_STEPS.length}
        </p>
      </div>
    </div>
  );
}
