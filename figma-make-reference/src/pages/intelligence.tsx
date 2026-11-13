import { useEffect, useState, type ReactNode } from 'react'
import { ChevronRight, ClipboardCheck, AlertTriangle, ArrowRight, BrainCircuit, CalendarClock, CheckCircle2, Columns3, FileQuestion, GitCommitHorizontal, GitPullRequest, Lightbulb, Link2, List, ListTodo, MessageSquare, Milestone, Network, ShieldCheck, Sparkles, UserRoundCog, Zap, Ban, Flag, Search, Filter } from 'lucide-react'
import { useStore } from '@/lib/store'
import { navigate, useRoute } from '@/lib/router'
import { gaps, personById, timeline, evidence, type Decision, type Task, type Risk, type Dependency, type Verification, type TimelineEvent } from '@/lib/data'
import { Avatar, Badge, Button, Card, CardHeader, EmptyState, Kpi, PageHeader, Segmented, Select, SearchInput, Table, Td, Th, VerificationBadge, Confidence, Tabs, cn, VERIF } from '@/components/ui'
import { Donut, Legend, BarChart, StackedBar, Ring } from '@/components/charts'
import { SourceIcon } from '@/components/brand'
import { allFindings, ConfidenceLegend, EvidenceChip, FindingDrawer, ProjectNotFound, SeverityBadge, TaskStatus, projectFindings, useProject, useVerification, type AnyFinding } from '@/components/domain'
import { DependencyFlow } from '@/components/graph'
import type { Project } from '@/lib/data'

const SUB = [
  { id: 'overview', label: 'Overview', path: '' },
  { id: 'decisions', label: 'Decisions', path: '/decisions' },
  { id: 'tasks', label: 'Tasks & Responsibilities', path: '/tasks' },
  { id: 'risks', label: 'Risks & Blockers', path: '/risks' },
  { id: 'dependencies', label: 'Dependencies', path: '/dependencies' },
  { id: 'timeline', label: 'Timeline', path: '/timeline' },
] as const

function IntelHeader({ p, tab, title, subtitle, actions }: { p: Project; tab: (typeof SUB)[number]['id']; title: string; subtitle: string; actions?: ReactNode }) {
  return (
    <>
      <PageHeader eyebrow={<span className="flex items-center gap-2"><Badge tone="indigo" icon={BrainCircuit}>AI Intelligence</Badge><span className="text-xs text-muted">{p.name}</span></span>} title={title} subtitle={subtitle} actions={actions} />
      <Tabs className="mb-5" tabs={SUB.map((s) => ({ id: s.id, label: s.label }))} value={tab} onChange={(id) => navigate(`/projects/${p.id}/intelligence${SUB.find((s) => s.id === id)!.path}`)} />
    </>
  )
}

function useDrawerFromQuery(list: AnyFinding[]) {
  const { query } = useRoute()
  const [open, setOpen] = useState<AnyFinding>()
  useEffect(() => { const id = query.get('id'); if (id) setOpen(list.find((f) => f.id === id)) }, [query.get('id')])
  return [open, setOpen] as const
}

function VerifFilter({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return <Select value={value} onChange={(e) => onChange(e.target.value)} className="sm:w-48"><option value="all">Any verification</option>{(Object.keys(VERIF) as Verification[]).map((v) => <option key={v} value={v}>{VERIF[v].label}</option>)}</Select>
}

function NoData({ p }: { p: Project }) {
  return <Card><EmptyState icon={BrainCircuit} title="Nothing reconstructed yet" body="Intelligence appears once evidence from connected sources has been processed." action={p.role === 'manager' && <Button onClick={() => navigate(`/projects/${p.id}/sources`)}>Connect sources</Button>} /></Card>
}

/* 16. Overview */
const V_COLOR: Record<Verification, string> = { verified: '#299B80', needs_review: '#D39B43', conflicting: '#D36D72', insufficient: '#A0AEC0', rejected: '#E3A9AC' }
function AreaLabel({ letter, title, sub }: { letter: string; title: string; sub?: string }) {
  return <div className="mb-3 flex items-baseline gap-2.5"><span className="font-mono text-[11px] text-sky">{letter}</span><h2 className="text-[17px] font-semibold tracking-[-0.015em] text-navy">{title}</h2>{sub && <span className="hidden text-[12.5px] text-muted sm:inline">{sub}</span>}</div>
}

export function IntelligenceOverview({ projectId }: { projectId: string }) {
  const s = useStore()
  const p = useProject(projectId)
  const [hoverDot, setHoverDot] = useState<string | null>(null)
  if (!p) return <ProjectNotFound />
  const f = projectFindings(p.id)
  const all = allFindings(p.id)
  const st = (x: AnyFinding) => (s.verif[x.id] ?? x.verification) as Verification
  const count = (v: Verification) => all.filter((x) => st(x) === v).length
  const srcs = s.sources.filter((x) => x.projectId === p.id)
  const projGaps = gaps.filter((g) => g.projectId === p.id)
  const openGaps = projGaps.filter((g) => !s.gapAnswers[g.id])
  if (!all.length) return (<><IntelHeader p={p} tab="overview" title="Intelligence Overview" subtitle="Structured knowledge reconstructed from project evidence." /><NoData p={p} /></>)
  const verified = count('verified')
  const buckets = [[90, 101, '90–100'], [80, 90, '80–89'], [70, 80, '70–79'], [60, 70, '60–69'], [0, 60, '<60']].reverse() as [number, number, string][]
  const bucketN = buckets.map(([lo, hi]) => all.filter((x) => x.confidence >= lo && x.confidence < hi).length)
  const maxB = Math.max(1, ...bucketN)
  const highUnverified = all.filter((x) => x.confidence >= 85 && st(x) !== 'verified').length
  const critical = f.risks.filter((r) => r.severity === 'Critical' && r.resolution !== 'Resolved')
  const importantUnverified = [...f.risks.filter((r) => ['Critical', 'High'].includes(r.severity)).map((r) => ({ ...r, kind: 'Risk' as const })), ...f.tasks.filter((t) => ['Critical', 'High'].includes(t.priority)).map((t) => ({ ...t, kind: 'Task' as const }))].filter((x) => st(x) === 'needs_review')
  const blocked = f.tasks.filter((t) => t.status === 'Blocked')
  const conflicts = all.filter((x) => st(x) === 'conflicting')
  const reviewHo = s.handovers.find((h) => h.projectId === p.id && ['in_progress', 'pending_review'].includes(h.status))
  const kinds = [
    { k: 'Decisions', items: f.decisions, to: 'decisions', c: '#315FBA', extra: `${f.decisions.filter((d) => st({ ...d, kind: 'Decision' }) === 'conflicting').length} conflicting` },
    { k: 'Active tasks', items: f.tasks.filter((t) => t.status !== 'Done'), to: 'tasks', c: '#299B80', extra: `${blocked.length} blocked` },
    { k: 'Risks', items: f.risks, to: 'risks', c: '#D36D72', extra: `${critical.length} critical` },
    { k: 'Dependencies', items: f.dependencies, to: 'dependencies', c: '#D39B43', extra: `${f.dependencies.filter((d) => d.blocking).length} blocking` },
  ]
  const attention: { group: string; tone: string; items: { title: string; sub: string; ev: number; to: string; cta: string }[] }[] = [
    { group: 'Critical unresolved risks', tone: 'bg-bad', items: critical.map((r) => ({ title: r.title, sub: `${r.component} · ${r.impact}`, ev: r.evidenceIds.length, to: `/projects/${p.id}/intelligence/risks?id=${r.id}`, cta: 'Open' })) },
    { group: 'Knowledge conflicts', tone: 'bg-bad', items: conflicts.map((x) => ({ title: x.title, sub: `${x.kind} · sources disagree`, ev: x.evidenceIds.length, to: reviewHo ? `/handovers/${reviewHo.id}/review` : `/projects/${p.id}/intelligence/decisions?id=${x.id}`, cta: 'Resolve' })) },
    { group: 'Important unverified findings', tone: 'bg-warn', items: importantUnverified.slice(0, 4).map((x) => ({ title: x.title, sub: `${x.kind} · AI ${x.confidence}% · not yet confirmed`, ev: x.evidenceIds.length, to: reviewHo ? `/handovers/${reviewHo.id}/review` : `/projects/${p.id}/intelligence/${x.kind === 'Risk' ? 'risks' : 'tasks'}?id=${x.id}`, cta: 'Verify' })) },
    { group: 'Missing information', tone: 'bg-slate-300', items: openGaps.map((g) => ({ title: g.question, sub: `${g.context} · ask ${personById(g.askedOf).name}`, ev: 0, to: reviewHo ? `/handovers/${reviewHo.id}/review?gaps=1` : `/projects/${p.id}/intelligence`, cta: 'Answer' })) },
    { group: 'Blocked tasks', tone: 'bg-warn', items: blocked.map((t) => ({ title: t.title, sub: `${personById(t.ownerId).name} · due ${t.due}`, ev: t.evidenceIds.length, to: `/projects/${p.id}/intelligence/dependencies`, cta: 'View' })) },
  ].filter((g) => g.items.length)
  return (
    <>
      <IntelHeader p={p} tab="overview" title="Intelligence Overview" subtitle="What Handover has reconstructed for this project, how much of it people have confirmed, and what still needs attention." actions={reviewHo && <Button icon={ClipboardCheck} onClick={() => navigate(`/handovers/${reviewHo.id}/review`)}>Open review queue</Button>} />
      <Card className="relative mb-8 overflow-hidden p-5 sm:p-6">
        <span className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-brand to-ai" />
        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">Briefing</p>
        <p className="mt-2 max-w-4xl text-[16px] leading-relaxed text-[#3e5373] sm:text-[17px]">
          Handover reconstructed <span className="font-semibold text-navy">{all.length} findings</span> from {srcs.length} sources. People have verified <span className="font-semibold text-teal-700">{verified}</span>.{' '}
          {conflicts.length > 0 && <><span className="font-semibold text-red-700">{conflicts.length} have conflicting evidence</span>{critical.length ? ' and ' : '. '}</>}
          {critical.length > 0 && <><span className="font-semibold text-red-700">{critical.length} critical risk{critical.length > 1 ? 's are' : ' is'} unresolved</span>. </>}
          {highUnverified > 0 && <>{highUnverified} high-confidence findings are still unverified: confidence alone isn't confirmation.</>}
        </p>
      </Card>

      <section className="mb-8">
        <AreaLabel letter="A" title="Knowledge health" sub="How well the project is covered by evidence" />
        <Card className="grid divide-y divide-line lg:grid-cols-[1fr_1fr_1.3fr] lg:divide-x lg:divide-y-0">
          <div className="flex items-center gap-5 p-5 sm:p-6">
            <Ring value={p.coverage} size={84} color="#315FBA" label={<span className="text-[17px]">{p.coverage}%</span>} />
            <div><p className="text-[14px] font-semibold text-navy">Evidence coverage</p><p className="mt-1 text-[12.5px] leading-relaxed text-muted">Share of project areas backed by at least one linked source.</p></div>
          </div>
          <div className="p-5 sm:p-6">
            <div className="flex items-baseline gap-2"><p className="text-[30px] font-semibold leading-none tracking-[-0.03em] text-navy">{openGaps.length}</p><p className="text-[14px] font-semibold text-navy">knowledge gaps</p></div>
            <p className="mt-1 text-[12.5px] text-muted">{projGaps.length - openGaps.length} answered by people</p>
            {openGaps[0] && <p className="mt-3 rounded-lg bg-canvas px-3 py-2 text-[12.5px] leading-snug text-[#3e5373]">“{openGaps[0].question}”</p>}
          </div>
          <div className="p-5 sm:p-6">
            <p className="text-[14px] font-semibold text-navy">Source coverage</p>
            <ul className="mt-3 space-y-2.5">
              {srcs.map((x) => {
                const n = all.filter((fi) => fi.evidenceIds.some((e) => evidence.find((ev) => ev.id === e)?.sourceId === x.id)).length
                return <li key={x.id} className="grid grid-cols-[22px_76px_1fr_74px] items-center gap-2.5"><SourceIcon type={x.type} size={22} /><span className="truncate text-[12.5px] text-navy">{x.name}</span><span className="h-1.5 overflow-hidden rounded-full bg-[#eef2f8]"><span className="animate-grow-x block h-full rounded-full bg-sky" style={{ width: `${(n / all.length) * 100}%` }} /></span><span className="whitespace-nowrap text-right font-mono text-[11.5px] text-muted">{n} · {x.status === 'error' ? <span className="text-red-600">stale</span> : 'live'}</span></li>
              })}
            </ul>
          </div>
        </Card>
      </section>

      <section className="mb-8">
        <AreaLabel letter="B" title="Reconstructed intelligence" sub="Verified share shown under each count" />
        <div className="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
          {kinds.map((k) => {
            const v = k.items.filter((x) => (s.verif[x.id] ?? x.verification) === 'verified').length
            return (
              <button key={k.k} onClick={() => navigate(`/projects/${p.id}/intelligence/${k.to}`)} className="tile group rounded-[14px] border p-5 text-left sm:p-6">
                <p className="flex items-center gap-2 text-[12.5px] font-medium text-muted"><span className="size-1.5 rounded-full" style={{ background: k.c }} />{k.k}<ChevronRight className="ml-auto size-3.5 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-brand" /></p>
                <p className="mt-2.5 text-[30px] font-semibold leading-none tracking-[-0.035em] text-navy">{k.items.length}</p>
                <div className="mt-3 flex h-1 gap-0.5 overflow-hidden rounded-full bg-[#eef2f8]"><span className="h-full rounded-full bg-ok" style={{ width: `${(v / Math.max(1, k.items.length)) * 100}%` }} /></div>
                <p className="mt-1.5 text-[11.5px] text-muted">{v} verified · {k.extra}</p>
              </button>
            )
          })}
        </div>
      </section>

      <div className="mb-8 grid gap-6 lg:grid-cols-2">
        <section>
          <AreaLabel letter="C" title="Verification" sub="Has a person confirmed it?" />
          <Card className="p-5 sm:p-6">
            <div className="flex items-end justify-between"><div><p className="text-[30px] font-semibold leading-none tracking-[-0.035em] text-teal-700">{Math.round((verified / all.length) * 100)}%</p><p className="mt-1 text-[12.5px] text-muted">verified by people</p></div><ShieldCheck className="size-5 text-ok" /></div>
            <div className="mt-5 flex h-3 gap-[2px] overflow-hidden rounded-full">{(['verified', 'needs_review', 'conflicting', 'insufficient', 'rejected'] as Verification[]).map((v) => count(v) > 0 && <span key={v} className="animate-grow-x h-full" style={{ width: `${(count(v) / all.length) * 100}%`, background: V_COLOR[v] }} title={`${VERIF[v].label}: ${count(v)}`} />)}</div>
            <table className="mt-5 w-full text-[13px]"><tbody>
              {(['verified', 'needs_review', 'conflicting', 'insufficient', 'rejected'] as Verification[]).map((v) => (
                <tr key={v} className="border-t border-line/70"><td className="py-2"><span className="flex items-center gap-2 text-navy"><span className="size-2 rounded-sm" style={{ background: V_COLOR[v] }} />{VERIF[v].label}</span></td><td className="w-12 text-right font-mono text-navy">{count(v)}</td><td className="w-14 text-right font-mono text-muted">{Math.round((count(v) / all.length) * 100)}%</td></tr>
              ))}
            </tbody></table>
            <p className="mt-3 text-[12px] text-muted">Only verified findings count toward handover completeness.</p>
          </Card>
        </section>
        <section>
          <AreaLabel letter="D" title="Confidence distribution" sub="How certain is the model?" />
          <Card className="p-5 sm:p-6">
            <div className="flex items-end gap-3" style={{ height: 132 }}>
              {buckets.map(([, , l], i) => (
                <div key={l} className="flex h-full flex-1 flex-col items-center justify-end gap-1.5">
                  <span className="font-mono text-[11px] text-navy">{bucketN[i]}</span>
                  <div className="animate-grow-y w-full max-w-[44px] rounded-t-md" style={{ height: `${Math.max(4, (bucketN[i] / maxB) * 100)}%`, background: ['#D3CCEC', '#BDB3E2', '#A59BD7', '#8B78C9', '#7462B5'][i], animationDelay: `${i * 70}ms` }} />
                  <span className="font-mono text-[10.5px] text-muted">{l}%</span>
                </div>
              ))}
            </div>
            <div className="mt-6 border-t border-line pt-4">
              <p className="flex items-center justify-between text-[12px] text-muted"><span className="font-medium text-navy">Findings by confidence</span><span>colour = verification</span></p>
              <div className="relative mt-3 h-12">
                <div className="absolute inset-x-0 top-1/2 h-px bg-line" />
                {[50, 60, 70, 80, 90, 100].map((t) => <span key={t} className="absolute top-full -translate-x-1/2 font-mono text-[10px] text-slate-400" style={{ left: `${((t - 50) / 50) * 100}%` }}>{t}</span>)}
                {all.map((x, i) => (
                  <button key={x.id} onMouseEnter={() => setHoverDot(x.id)} onMouseLeave={() => setHoverDot(null)} onClick={() => navigate(`/projects/${p.id}/intelligence/${x.kind === 'Decision' ? 'decisions' : x.kind === 'Task' ? 'tasks' : x.kind === 'Risk' ? 'risks' : 'dependencies'}?id=${x.id}`)} className="absolute size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow-sm transition-transform hover:scale-150" style={{ left: `${Math.max(0, ((x.confidence - 50) / 50) * 100)}%`, top: `${50 + ((i % 3) - 1) * 26}%`, background: V_COLOR[st(x)] }} aria-label={x.title} />
                ))}
                {hoverDot && (() => { const x = all.find((y) => y.id === hoverDot)!; return <div className="pointer-events-none absolute -top-14 z-10 w-60 -translate-x-1/2 rounded-lg bg-navy px-2.5 py-1.5 text-[11.5px] text-white shadow-pop" style={{ left: `${Math.min(80, Math.max(20, ((x.confidence - 50) / 50) * 100))}%` }}><p className="truncate font-semibold">{x.title}</p><p className="text-[#c3cfe0]">AI {x.confidence}% · {VERIF[st(x)].label}</p></div> })()}
              </div>
              <p className="mt-6 text-[12px] text-muted">{highUnverified} findings above 85% confidence are not yet verified.</p>
            </div>
          </Card>
        </section>
      </div>

      <section>
        <AreaLabel letter="E" title="Attention required" sub="Every item links back to its evidence" />
        <Card className="divide-y divide-line overflow-hidden">
          {attention.map((g) => (
            <div key={g.group} className="grid lg:grid-cols-[220px_1fr]">
              <div className="flex items-center gap-2.5 bg-[#f8fafd] px-5 py-3 lg:items-start lg:py-4"><span className={cn('size-2 rounded-full', g.tone)} /><span className="text-[13px] font-semibold text-navy">{g.group}</span><span className="ml-auto font-mono text-[11.5px] text-muted lg:ml-0">{g.items.length}</span></div>
              <ul className="divide-y divide-line/70">
                {g.items.map((it) => (
                  <li key={it.title} className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-[#f9fbfe]">
                    <div className="min-w-0 flex-1"><p className="truncate text-[13.5px] font-medium text-navy">{it.title}</p><p className="truncate text-[12px] text-muted">{it.sub}</p></div>
                    {it.ev > 0 && <span className="hidden items-center gap-1 font-mono text-[11px] text-muted sm:flex"><Link2 className="size-3" />{it.ev}</span>}
                    <Button size="sm" variant="secondary" onClick={() => navigate(it.to)}>{it.cta}</Button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {!attention.length && <EmptyState icon={CheckCircle2} title="Nothing needs attention" body="No conflicts, gaps or critical risks right now." />}
        </Card>
      </section>
    </>
  )
}

/* 17. Decisions */
export function Decisions({ projectId }: { projectId: string }) {
  const s = useStore()
  const p = useProject(projectId)
  const list = p ? projectFindings(p.id).decisions.map((d) => ({ ...d, kind: 'Decision' as const })) : []
  const [open, setOpen] = useDrawerFromQuery(list)
  const [q, setQ] = useState('')
  const [vf, setVf] = useState('all')
  if (!p) return <ProjectNotFound />
  const shown = list.filter((d) => d.title.toLowerCase().includes(q.toLowerCase()) && (vf === 'all' || (s.verif[d.id] ?? d.verification) === vf))
  const od = open as (Decision & { kind: 'Decision' }) | undefined
  return (
    <>
      <IntelHeader p={p} tab="decisions" title="Decisions" subtitle="Why the project is the way it is, reconstructed from PRs, discussions and records." />
      <div className="mb-4 flex flex-col gap-2 sm:flex-row"><SearchInput placeholder="Search decisions" value={q} onChange={(e) => setQ(e.target.value)} className="sm:w-72" /><VerifFilter value={vf} onChange={setVf} /></div>
      {!list.length ? <NoData p={p} /> : (
        <div className="space-y-3">
          {shown.map((d) => (
            <Card key={d.id} interactive className="cursor-pointer p-5" onClick={() => setOpen(d)}>
              <div className="flex flex-col gap-4 lg:flex-row">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2"><Lightbulb className="size-4 text-brand" /><h3 className="text-[15px] font-semibold text-navy">{d.title}</h3></div>
                  <p className="mt-1.5 text-[13px] leading-relaxed text-muted">{d.summary}</p>
                  <div className="mt-3 rounded-xl bg-slate-50 p-3"><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Reasoning</p><p className="mt-1 text-[13px] leading-relaxed text-slate-700">{d.reasoning}</p></div>
                  <div className="mt-3 flex flex-wrap items-center gap-2">{d.evidenceIds.map((e) => <EvidenceChip key={e} id={e} />)}</div>
                </div>
                <div className="flex shrink-0 flex-row flex-wrap gap-4 border-t border-line pt-3 text-[13px] lg:w-56 lg:flex-col lg:border-l lg:border-t-0 lg:pl-5 lg:pt-0">
                  <div><p className="text-xs text-muted">Decision maker</p><p className="mt-1 flex items-center gap-1.5 font-medium text-navy"><Avatar id={d.ownerId} size={20} />{personById(d.ownerId).name}</p></div>
                  <div><p className="text-xs text-muted">Decided</p><p className="mt-1 font-medium text-navy">{d.date}</p></div>
                  <div><p className="text-xs text-muted">Related discussions</p>{d.discussions.map((x) => <p key={x} className="mt-1 flex items-center gap-1.5 text-navy"><MessageSquare className="size-3 text-muted" />{x}</p>)}</div>
                  <div className="flex flex-col gap-1.5"><Confidence value={d.confidence} /><VerificationBadge status={s.verif[d.id] ?? d.verification} /></div>
                </div>
              </div>
            </Card>
          ))}
          {!shown.length && <Card><EmptyState icon={Search} title="No decisions match" body="Adjust your search or verification filter." /></Card>}
        </div>
      )}
      <FindingDrawer finding={open} onClose={() => setOpen(undefined)} extra={od?.reasoning && <div className="rounded-xl bg-slate-50 p-3"><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Reasoning</p><p className="mt-1 text-[13px] text-slate-700">{od.reasoning}</p></div>} />
    </>
  )
}

/* 18. Tasks */
const PRI_TONE = { Critical: 'red', High: 'amber', Medium: 'blue', Low: 'gray' } as const
export function Tasks({ projectId }: { projectId: string }) {
  const s = useStore()
  const p = useProject(projectId)
  const list = p ? projectFindings(p.id).tasks.map((d) => ({ ...d, kind: 'Task' as const })) : []
  const [open, setOpen] = useDrawerFromQuery(list)
  const [view, setView] = useState<'table' | 'board'>('table')
  const [owner, setOwner] = useState('all')
  const [pri, setPri] = useState('all')
  if (!p) return <ProjectNotFound />
  const shown = list.filter((t) => (owner === 'all' || t.ownerId === owner) && (pri === 'all' || t.priority === pri))
  const ot = open as (Task & { kind: 'Task' }) | undefined
  return (
    <>
      <IntelHeader p={p} tab="tasks" title="Tasks & Responsibilities" subtitle="Outstanding work and who owns it, including ownership changes over time." actions={<Segmented value={view} onChange={setView} options={[{ id: 'table', icon: List, label: 'Table' }, { id: 'board', icon: Columns3, label: 'Board' }]} />} />
      <div className="mb-4 flex flex-col gap-2 sm:flex-row">
        <Select value={owner} onChange={(e) => setOwner(e.target.value)} className="sm:w-48"><option value="all">All assignees</option>{Array.from(new Set(list.map((t) => t.ownerId))).map((o) => <option key={o} value={o}>{personById(o).name}</option>)}</Select>
        <Select value={pri} onChange={(e) => setPri(e.target.value)} className="sm:w-40"><option value="all">All priorities</option>{['Critical', 'High', 'Medium', 'Low'].map((x) => <option key={x}>{x}</option>)}</Select>
      </div>
      {!list.length ? <NoData p={p} /> : view === 'table' ? (
        <Card className="overflow-hidden">
          <Table>
            <thead><tr><Th>Task</Th><Th>Assigned</Th><Th>Priority</Th><Th>Status</Th><Th>Due</Th><Th>Evidence</Th><Th>AI · Verification</Th></tr></thead>
            <tbody>{shown.map((t) => (
              <tr key={t.id} onClick={() => setOpen(t)} className="cursor-pointer hover:bg-slate-50/70">
                <Td><p className="max-w-[300px] font-medium text-navy">{t.title}</p><p className="max-w-[300px] truncate text-xs text-muted">{t.summary}</p></Td>
                <Td><span className="flex items-center gap-2 whitespace-nowrap"><Avatar id={t.ownerId} size={24} /><span className="text-[13px]">{personById(t.ownerId).name}</span></span>{t.history.length > 1 && <p className="mt-1 flex items-center gap-1 text-[11px] text-amber-700"><UserRoundCog className="size-3" />Ownership changed</p>}</Td>
                <Td><Badge tone={PRI_TONE[t.priority]}>{t.priority}</Badge></Td>
                <Td><TaskStatus status={t.status} /></Td>
                <Td className="whitespace-nowrap text-[13px]">{t.due}</Td>
                <Td><span className="flex items-center gap-1 text-xs text-muted"><Link2 className="size-3" />{t.evidenceIds.length}</span></Td>
                <Td><div className="flex flex-col items-start gap-1"><Confidence value={t.confidence} compact /><VerificationBadge status={s.verif[t.id] ?? t.verification} /></div></Td>
              </tr>
            ))}</tbody>
          </Table>
        </Card>
      ) : (
        <div className="scrollbar-thin grid grid-flow-col gap-4 overflow-x-auto pb-2" style={{ gridAutoColumns: 'minmax(260px, 1fr)' }}>
          {(['To do', 'In progress', 'Blocked', 'Done'] as const).map((col) => {
            const items = shown.filter((t) => t.status === col)
            return (
              <div key={col} className="rounded-2xl bg-[#EDF2FA] p-3">
                <div className="mb-3 flex items-center justify-between px-1"><TaskStatus status={col} /><span className="text-xs text-muted">{items.length}</span></div>
                <div className="space-y-2.5">
                  {items.map((t) => (
                    <button key={t.id} onClick={() => setOpen(t)} className="tile w-full rounded-xl border p-3.5 text-left">
                      <div className="flex items-center justify-between"><Badge tone={PRI_TONE[t.priority]}>{t.priority}</Badge><span className="flex items-center gap-1 text-[11px] text-muted"><CalendarClock className="size-3" />{t.due}</span></div>
                      <p className="mt-2 text-[13px] font-medium text-navy">{t.title}</p>
                      <div className="mt-3 flex items-center justify-between"><Avatar id={t.ownerId} size={22} /><VerificationBadge status={s.verif[t.id] ?? t.verification} /></div>
                    </button>
                  ))}
                  {!items.length && <p className="rounded-xl border border-dashed border-[#D9E1F0] p-4 text-center text-xs text-muted">No tasks</p>}
                </div>
              </div>
            )
          })}
        </div>
      )}
      <FindingDrawer finding={open} onClose={() => setOpen(undefined)} extra={ot?.history && (
        <div>
          <div className="mb-3 flex flex-wrap gap-2"><Badge tone={PRI_TONE[ot.priority]}>{ot.priority}</Badge><TaskStatus status={ot.status} /><Badge tone="gray" icon={CalendarClock}>Due {ot.due}</Badge></div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Ownership history</p>
          <ol className="space-y-2 border-l border-line pl-4">{ot.history.map((h, i) => <li key={i} className="relative text-[13px]"><span className="absolute -left-[21px] top-1.5 size-2.5 rounded-full border-2 border-white bg-brand" /><span className="font-medium text-navy">{personById(h.personId).name}</span> <span className="text-muted">· {h.note} · {h.date}</span></li>)}</ol>
        </div>
      )} />
    </>
  )
}

/* 19. Risks */
export function Risks({ projectId }: { projectId: string }) {
  const s = useStore()
  const p = useProject(projectId)
  const list = p ? projectFindings(p.id).risks.map((d) => ({ ...d, kind: 'Risk' as const })) : []
  const [open, setOpen] = useDrawerFromQuery(list)
  const [sev, setSev] = useState('all')
  if (!p) return <ProjectNotFound />
  const shown = list.filter((r) => sev === 'all' || r.severity === sev)
  const counts = ['Critical', 'High', 'Medium', 'Low'].map((x) => list.filter((r) => r.severity === x).length)
  const or = open as (Risk & { kind: 'Risk' }) | undefined
  return (
    <>
      <IntelHeader p={p} tab="risks" title="Risks & Blockers" subtitle="What could go wrong after the handover, and what to do about it." />
      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        {(['Critical', 'High', 'Medium', 'Low'] as const).map((x, i) => (
          <button key={x} onClick={() => setSev(sev === x ? 'all' : x)} className={cn('tile rounded-[14px] border p-4 text-left', sev === x && 'border-brand ring-4 ring-brand/10')}>
            <SeverityBadge level={x} /><p className="mt-2 text-2xl font-semibold text-navy">{counts[i]}</p><p className="text-xs text-muted">{x.toLowerCase()} risks</p>
          </button>
        ))}
      </div>
      {!list.length ? <NoData p={p} /> : (
        <div className="grid gap-4 lg:grid-cols-2">
          {shown.map((r) => (
            <Card key={r.id} interactive className={cn('cursor-pointer overflow-hidden', r.severity === 'Critical' && 'border-red-200')} onClick={() => setOpen(r)}>
              <div className={cn('h-1', { Critical: 'bg-bad', High: 'bg-warn', Medium: 'bg-sky', Low: 'bg-slate-300' }[r.severity])} />
              <div className="p-5">
                <div className="flex flex-wrap items-center gap-2"><SeverityBadge level={r.severity} /><TaskStatus status={r.resolution} /><Badge tone="gray">{r.component}</Badge></div>
                <h3 className="mt-3 text-[15px] font-semibold text-navy">{r.title}</h3>
                <p className="mt-1 text-[13px] text-muted">{r.summary}</p>
                <p className="mt-3 flex items-start gap-2 text-[13px]"><Zap className="mt-0.5 size-3.5 shrink-0 text-warn" /><span><span className="font-medium text-navy">Impact:</span> <span className="text-slate-700">{r.impact}</span></span></p>
                <div className="mt-3 rounded-xl border border-dashed border-indigo-200 bg-indigo-50/30 p-3">
                  <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-indigo-500"><Sparkles className="size-3" />Suggested mitigation</p>
                  <ul className="mt-1.5 space-y-1">{r.mitigation.map((m) => <li key={m} className="text-[13px] text-slate-700">• {m}</li>)}</ul>
                </div>
                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3">
                  <span className="flex items-center gap-2 text-[13px]"><Avatar id={r.ownerId} size={22} />{personById(r.ownerId).name}</span>
                  <span className="flex items-center gap-1.5"><Confidence value={r.confidence} compact /><VerificationBadge status={s.verif[r.id] ?? r.verification} /></span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
      <FindingDrawer finding={open} onClose={() => setOpen(undefined)} extra={or?.mitigation && (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2"><SeverityBadge level={or.severity} /><TaskStatus status={or.resolution} /><Badge tone="gray">{or.component}</Badge></div>
          <p className="text-[13px]"><span className="font-medium text-navy">Impact:</span> {or.impact}</p>
          <div className="rounded-xl border border-dashed border-indigo-200 bg-indigo-50/30 p-3"><p className="text-[11px] font-semibold uppercase text-indigo-500">AI-suggested mitigation</p><ul className="mt-1 space-y-1">{or.mitigation.map((m) => <li key={m} className="text-[13px]">• {m}</li>)}</ul></div>
        </div>
      )} />
    </>
  )
}

/* 20. Dependencies */
export function Dependencies({ projectId }: { projectId: string }) {
  const s = useStore()
  const p = useProject(projectId)
  const list = p ? projectFindings(p.id).dependencies.map((d) => ({ ...d, kind: 'Dependency' as const })) : []
  const [open, setOpen] = useDrawerFromQuery(list)
  const [type, setType] = useState('all')
  const [sel, setSel] = useState<string>()
  if (!p) return <ProjectNotFound />
  const shown = list.filter((d) => type === 'all' || d.depType === type)
  const blockedTasks = projectFindings(p.id).tasks.filter((t) => t.status === 'Blocked')
  return (
    <>
      <IntelHeader p={p} tab="dependencies" title="Dependencies" subtitle="Technical, task and external dependencies the incoming member needs to know about." />
      <div className="mb-4 flex flex-wrap gap-2">{['all', 'Technical', 'Task', 'External'].map((t) => <button key={t} onClick={() => setType(t)} className={cn('rounded-full border px-3 py-1 text-[13px] font-medium', type === t ? 'border-brand bg-tint text-brand' : 'border-line bg-white text-muted')}>{t === 'all' ? `All (${list.length})` : `${t} (${list.filter((d) => d.depType === t).length})`}</button>)}</div>
      {!list.length ? <NoData p={p} /> : (
        <>
          <Card className="mb-5">
            <CardHeader title="Dependency graph" subtitle="Click an edge to inspect it" icon={Network} action={<div className="hidden gap-3 text-[11px] text-muted sm:flex"><span className="flex items-center gap-1"><span className="h-0.5 w-4 bg-brand" />Technical</span><span className="flex items-center gap-1"><span className="h-0.5 w-4 bg-ok" />Task</span><span className="flex items-center gap-1"><span className="h-0.5 w-4 bg-warn" />External</span><span className="flex items-center gap-1"><span className="h-0.5 w-4 border-t-2 border-dashed border-bad" />Blocking</span></div>} />
            <div className="scrollbar-thin overflow-x-auto px-3 pb-4"><DependencyFlow deps={shown} selected={sel} onSelect={(id) => { setSel(id); setOpen(shown.find((d) => d.id === id)) }} /></div>
          </Card>
          <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
            <Card className="overflow-hidden">
              <Table>
                <thead><tr><Th>Dependency</Th><Th>Type</Th><Th>From → To</Th><Th>Responsible</Th><Th>Verification</Th></tr></thead>
                <tbody>{shown.map((d) => (
                  <tr key={d.id} onClick={() => { setSel(d.id); setOpen(d) }} className={cn('cursor-pointer hover:bg-slate-50/70', sel === d.id && 'bg-tint/40')}>
                    <Td><p className="font-medium text-navy">{d.title}</p>{d.blocking && <Badge tone="red" icon={Ban} className="mt-1">Blocking</Badge>}</Td>
                    <Td><Badge tone={d.depType === 'Technical' ? 'blue' : d.depType === 'Task' ? 'green' : 'amber'}>{d.depType}</Badge></Td>
                    <Td className="text-[13px]">{d.from} <ArrowRight className="inline size-3 text-slate-400" /> {d.to}</Td>
                    <Td><span className="flex items-center gap-2 whitespace-nowrap text-[13px]"><Avatar id={d.ownerId} size={22} />{personById(d.ownerId).name}</span></Td>
                    <Td><VerificationBadge status={s.verif[d.id] ?? d.verification} /></Td>
                  </tr>
                ))}</tbody>
              </Table>
            </Card>
            <Card>
              <CardHeader title="Blocked tasks" subtitle="Cannot progress until a dependency clears" icon={Ban} />
              <ul className="space-y-2 px-5 pb-5">
                {blockedTasks.map((t) => <li key={t.id} className="rounded-xl border border-red-200 bg-red-50/40 p-3"><p className="text-[13px] font-medium text-navy">{t.title}</p><p className="mt-1 flex items-center gap-1.5 text-xs text-muted"><Avatar id={t.ownerId} size={18} />{personById(t.ownerId).name} · due {t.due}</p></li>)}
                {!blockedTasks.length && <p className="text-[13px] text-muted">No blocked tasks.</p>}
              </ul>
            </Card>
          </div>
        </>
      )}
      <FindingDrawer finding={open} onClose={() => { setOpen(undefined); setSel(undefined) }} />
    </>
  )
}

/* 21. Timeline */
const TL_META: Record<TimelineEvent['type'], { icon: typeof Milestone; color: string; label: string }> = {
  milestone: { icon: Flag, color: '#203653', label: 'Milestone' }, commit: { icon: GitCommitHorizontal, color: '#718096', label: 'Commit' }, pr: { icon: GitPullRequest, color: '#8B78C9', label: 'Pull request' },
  decision: { icon: Lightbulb, color: '#315FBA', label: 'Decision' }, task: { icon: CheckCircle2, color: '#299B80', label: 'Task' }, discussion: { icon: MessageSquare, color: '#B5728E', label: 'Discussion' },
  ownership: { icon: UserRoundCog, color: '#D39B43', label: 'Ownership' }, event: { icon: AlertTriangle, color: '#D36D72', label: 'Event' },
}
export function Timeline({ projectId }: { projectId: string }) {
  const p = useProject(projectId)
  const [types, setTypes] = useState<string[]>([])
  const [selected, setSelected] = useState<string>()
  if (!p) return <ProjectNotFound />
  const all = timeline.filter((t) => t.projectId === p.id)
  const list = all.filter((t) => !types.length || types.includes(t.type))
  const months = Array.from(new Set(list.map((t) => t.date.slice(0, 7))))
  return (
    <>
      <IntelHeader p={p} tab="timeline" title="Project Timeline" subtitle="A chronological history of milestones, code, decisions, discussions and ownership changes." />
      <div className="mb-5 flex flex-wrap gap-2">
        {(Object.keys(TL_META) as TimelineEvent['type'][]).map((k) => {
          const on = types.includes(k)
          const M = TL_META[k]
          return <button key={k} onClick={() => setTypes(on ? types.filter((x) => x !== k) : [...types, k])} className={cn('flex items-center gap-1.5 rounded-full border px-3 py-1 text-[13px] font-medium transition', on ? 'border-transparent text-white' : 'border-line bg-white text-muted hover:text-navy')} style={on ? { background: M.color } : undefined}><M.icon className="size-3.5" />{M.label}</button>
        })}
        {!!types.length && <button onClick={() => setTypes([])} className="text-[13px] font-medium text-brand">Clear</button>}
      </div>
      {!all.length ? <NoData p={p} /> : (
        <Card className="p-5 sm:p-7">
          {months.map((m) => (
            <div key={m} className="mb-6 last:mb-0">
              <p className="sticky top-0 z-10 mb-3 inline-block rounded-full bg-tint px-3 py-1 text-xs font-semibold text-brand">{new Date(m + '-01').toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })}</p>
              <ol className="relative ml-4 border-l-2 border-line">
                {list.filter((t) => t.date.startsWith(m)).map((t) => {
                  const M = TL_META[t.type]
                  const open = selected === t.id
                  return (
                    <li key={t.id} className="relative mb-3 pl-7">
                      <span className="absolute -left-[13px] top-2 flex size-6 items-center justify-center rounded-full border-2 border-white text-white shadow-sm" style={{ background: M.color }}><M.icon className="size-3" /></span>
                      <button onClick={() => setSelected(open ? undefined : t.id)} className={cn('w-full rounded-xl border px-4 py-3 text-left transition', open ? 'border-brand/40 bg-tint/30' : 'border-transparent hover:border-line hover:bg-slate-50')}>
                        <div className="flex flex-wrap items-center gap-2"><span className="text-xs font-medium text-muted">{new Date(t.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</span><Badge tone="gray">{M.label}</Badge>{t.type === 'milestone' && <Badge tone="navy">Milestone</Badge>}</div>
                        <p className={cn('mt-1 text-navy', t.type === 'milestone' ? 'text-[15px] font-semibold' : 'text-[13.5px] font-medium')}>{t.title}</p>
                        <p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted"><Avatar id={t.personId} size={16} />{personById(t.personId).name} · {t.detail}</p>
                        {open && t.evidenceId && <div className="mt-3" onClick={(e) => e.stopPropagation()}><EvidenceChip id={t.evidenceId} /></div>}
                      </button>
                    </li>
                  )
                })}
              </ol>
            </div>
          ))}
          {!list.length && <EmptyState icon={Filter} title="No events of this type" body="Choose another filter." />}
        </Card>
      )}
    </>
  )
}
