import { useEffect, useState, type ReactNode } from 'react'
import { AlertTriangle, ArrowLeft, ArrowRight, BookOpen, Calendar, Check, CheckCircle2, ClipboardCheck, Clock, Database, Eye, FileText, Filter, FolderKanban, Inbox, KeyRound, LayoutGrid, Lightbulb, List, ListTodo, Loader2, Lock, MessageSquareText, Network, Pencil, Plus, Send, ShieldCheck, Sparkles, Undo2, UserRoundCog, Users, Workflow, XCircle, Link2, Ban, FileQuestion, Search } from 'lucide-react'
import { useStore } from '@/lib/store'
import { Link, navigate, useRoute } from '@/lib/router'
import { gaps, ME, personById, ROLE_LABEL, HANDOVER_STATUS_LABEL, type Handover, type HandoverStatus, type ProjectRole } from '@/lib/data'
import { MetricBand, Avatar, Badge, Button, Callout, Card, CardHeader, Checkbox, ConfirmDialog, EmptyState, Field, Input, Kpi, Modal, PageHeader, Progress, Radio, ReconstructionLoader, SearchInput, Segmented, Select, SphereVisual, StatusBadge, Switch, Table, Tabs, Td, Textarea, Th, Tooltip, VerificationBadge, cn, Confidence } from '@/components/ui'
import { Ring } from '@/components/charts'
import { SourceIcon, EvidenceTypeIcon, EVIDENCE_TYPE_LABEL } from '@/components/brand'
import { RoleBadge, ROLE_TONE } from '@/components/Shell'
import { allFindings, EvidenceChip, FindingDrawer, HandoverTable, handoverPerspective, projectFindings, SeverityBadge, StageDots, TaskStatus, type AnyFinding, FindingRowMeta } from '@/components/domain'

/* ---------- helpers ---------- */
export function useHandover(id: string) {
  const s = useStore()
  const h = s.handovers.find((x) => x.id === id)
  const project = h && s.allProjects.find((p) => p.id === h.projectId)
  useEffect(() => { if (project && s.currentProject?.id !== project.id) s.switchProject(project.id, true) }, [project?.id])
  const role = h && project ? handoverPerspective(h, project.role, s.perspective[h.id]) : 'incoming'
  return { h, project, role }
}

export function handoverStats(h: Handover, verif: Record<string, string>) {
  const all = allFindings(h.projectId)
  const reviewed = all.filter((f) => (verif[f.id] ?? f.verification) !== 'needs_review').length
  const verified = all.filter((f) => (verif[f.id] ?? f.verification) === 'verified').length
  return { all, reviewed, verified, pct: all.length ? Math.round((reviewed / all.length) * 100) : 0, completeness: all.length ? Math.round((verified / all.length) * 100) : 0 }
}

export function HandoverNotFound() {
  return <EmptyState icon={Workflow} title="Handover not found" body="It may have been revoked, or you may not have access." action={<Button onClick={() => navigate('/handovers')}>All handovers</Button>} />
}

/* ---------- 22. All handovers ---------- */
const FILTERS: ('all' | HandoverStatus)[] = ['all', 'draft', 'in_progress', 'pending_review', 'approved', 'published', 'completed']
export function AllHandovers() {
  const s = useStore()
  const [f, setF] = useState<'all' | HandoverStatus>('all')
  const [q, setQ] = useState('')
  const [proj, setProj] = useState('all')
  const [view, setView] = useState<'table' | 'cards'>('table')
  const list = s.handovers.filter((h) => (f === 'all' || h.status === f) && (proj === 'all' || h.projectId === proj) && `${h.code} ${personById(h.outgoingId).name} ${personById(h.incomingId).name} ${h.scope}`.toLowerCase().includes(q.toLowerCase()))
  const canCreate = s.projects.some((p) => p.role === 'manager')
  return (
    <>
      <PageHeader title="All Handovers" subtitle="Every knowledge transfer across your projects, from draft to acknowledgement." actions={canCreate && <Button icon={Plus} onClick={() => navigate('/handovers/new')}>Create handover</Button>} />
      <MetricBand className="mb-5" items={[{ label: "In progress", value: s.handovers.filter((h) => ['draft', 'in_progress'].includes(h.status)).length }, { label: "Pending review", value: s.handovers.filter((h) => h.status === 'pending_review').length, tone: "amber" }, { label: "Published", value: s.handovers.filter((h) => h.status === 'published').length, tone: "indigo", hint: "awaiting acknowledgement" }, { label: "Completed", value: s.handovers.filter((h) => h.status === 'completed').length, tone: "green" }]} />
      <Card className="overflow-hidden">
        <div className="px-4 pt-3"><Tabs tabs={FILTERS.map((x) => ({ id: x, label: x === 'all' ? 'All' : HANDOVER_STATUS_LABEL[x], count: x === 'all' ? s.handovers.length : s.handovers.filter((h) => h.status === x).length }))} value={f} onChange={setF} /></div>
        <div className="flex flex-col gap-2 border-b border-line p-3 sm:flex-row sm:items-center">
          <SearchInput placeholder="Search by code, person or scope" value={q} onChange={(e) => setQ(e.target.value)} className="sm:w-72" />
          <Select value={proj} onChange={(e) => setProj(e.target.value)} className="sm:w-56"><option value="all">All projects</option>{s.projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</Select>
          <div className="sm:ml-auto"><Segmented value={view} onChange={setView} options={[{ id: 'table', icon: List, label: 'Table' }, { id: 'cards', icon: LayoutGrid, label: 'Cards' }]} /></div>
        </div>
        {view === 'table' ? (
          <HandoverTable items={list} empty={<EmptyState icon={s.handovers.length ? Filter : Workflow} title={s.handovers.length ? 'No handovers match' : 'No handovers yet'} body={s.handovers.length ? 'Try another status or search.' : 'Create your first handover when someone is leaving or changing roles.'} action={!s.handovers.length && canCreate && <Button icon={Plus} onClick={() => navigate('/handovers/new')}>Create handover</Button>} />} />
        ) : (
          <div className="grid gap-4 p-4 sm:grid-cols-2 xl:grid-cols-3">
            {list.map((h) => <HandoverCard key={h.id} h={h} />)}
            {!list.length && <EmptyState className="col-span-full" icon={Filter} title="No handovers match" body="Try another filter." />}
          </div>
        )}
      </Card>
    </>
  )
}

function HandoverCard({ h, footer }: { h: Handover; footer?: ReactNode }) {
  const s = useStore()
  const p = s.allProjects.find((x) => x.id === h.projectId)
  return (
    <Card interactive className="flex flex-col p-5">
      <div className="flex items-center justify-between"><span className="text-xs font-medium text-muted">{h.code}</span><StatusBadge status={h.status} /></div>
      <Link to={`/handovers/${h.id}`} className="mt-2 text-[15px] font-semibold text-navy hover:text-brand">{p?.name}</Link>
      <p className="mt-0.5 line-clamp-1 text-[13px] text-muted">{h.scope}</p>
      <div className="mt-4 flex items-center gap-2"><Avatar id={h.outgoingId} size={28} /><div className="h-px flex-1 border-t border-dashed border-slate-300" /><ArrowRight className="size-3.5 text-brand" /><div className="h-px flex-1 border-t border-dashed border-slate-300" /><Avatar id={h.incomingId} size={28} /></div>
      <div className="mt-1 flex justify-between text-xs text-muted"><span>{personById(h.outgoingId).name}</span><span>{personById(h.incomingId).name}</span></div>
      <div className="mt-4"><div className="mb-1 flex justify-between text-xs"><span className="text-muted">Progress</span><span className="font-medium text-navy">{h.progress}%</span></div><Progress value={h.progress} size="sm" tone={h.progress === 100 ? 'green' : 'blue'} /></div>
      {footer ?? <div className="mt-4 flex items-center justify-between border-t border-line pt-3 text-xs text-muted"><span>Created {h.created}</span><StageDots status={h.status} /></div>}
    </Card>
  )
}

/* ---------- 23. Create handover ---------- */
const WZ = ['Project', 'Members', 'Sources', 'Scope', 'Review', 'Generate', 'Results', 'Submit']
const RECON_STAGES = ['Collecting authorised evidence', 'Extracting decisions, tasks and risks', 'Linking findings to evidence', 'Detecting conflicts and gaps', 'Drafting handover document']

export function CreateHandover() {
  const s = useStore()
  const { query } = useRoute()
  const managed = s.projects.filter((p) => p.role === 'manager')
  const [step, setStep] = useState(0)
  const [maxStep, setMaxStep] = useState(0)
  const [pid, setPid] = useState(query.get('project') && managed.some((p) => p.id === query.get('project')) ? query.get('project')! : managed[0]?.id ?? '')
  const members = s.members.filter((m) => m.projectId === pid)
  const [out, setOut] = useState('')
  const [inc, setInc] = useState('')
  const srcs = s.sources.filter((x) => x.projectId === pid && x.status !== 'disconnected')
  const [srcSel, setSrcSel] = useState<string[]>([])
  const [scope, setScope] = useState({ from: '2024-06-01', to: '2025-06-18', due: '2025-07-31', onlyOutgoing: true, areas: ['Decisions', 'Tasks', 'Risks', 'Dependencies', 'Architecture', 'Contacts'], notes: '' })
  const [genPct, setGenPct] = useState(0)
  const [submitMode, setSubmitMode] = useState<'verify' | 'approve'>('verify')
  useEffect(() => {
    const o = members.find((m) => m.role === 'outgoing')?.personId ?? members.find((m) => m.personId !== ME)?.personId ?? ''
    const i = members.find((m) => m.role === 'incoming')?.personId ?? ''
    setOut(o); setInc(i); setSrcSel(srcs.filter((x) => x.status !== 'error').map((x) => x.id))
  }, [pid])
  useEffect(() => {
    if (step !== 5 || genPct === 0 || genPct >= 100) return
    const t = setTimeout(() => setGenPct((x) => Math.min(100, x + 4)), 120)
    return () => clearTimeout(t)
  }, [step, genPct])
  const go = (n: number) => { setStep(n); setMaxStep((m) => Math.max(m, n)) }
  const project = s.projects.find((p) => p.id === pid)
  const f = projectFindings(pid)
  const all = allFindings(pid)
  const projGaps = gaps.filter((g) => g.projectId === pid)
  const valid = [!!pid, !!out && !!inc && out !== inc, srcSel.length > 0, scope.areas.length > 0 && scope.from < scope.to, true, genPct >= 100, true, true][step]
  const submit = () => {
    const n = 1045 + s.handovers.length
    const id = `ho-${n}`
    s.setHandovers((hs) => [{ id, code: `HO-${n}`, projectId: pid, outgoingId: out, incomingId: inc, created: 'Jun 18, 2025', updated: 'Just now', status: submitMode === 'verify' ? 'in_progress' : 'pending_review', progress: submitMode === 'verify' ? 34 : 70, due: new Date(scope.due).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }), scope: scope.areas.join(', ') }, ...hs])
    s.toast(submitMode === 'verify' ? `Sent to ${personById(out).name} for verification` : 'Submitted for approval', `HO-${n} created for ${project?.name}.`)
    navigate(`/handovers/${id}`)
  }
  if (!managed.length) return <Card><EmptyState icon={Lock} title="Only Project Managers can create handovers" body="You aren't a Project Manager on any project in this workspace. Ask a manager to start a handover for you." action={<Button variant="secondary" onClick={() => navigate('/handovers')}>Back to handovers</Button>} /></Card>
  return (
    <>
      <Link to="/handovers" className="mb-4 inline-flex items-center gap-1.5 text-[13px] font-medium text-muted hover:text-navy"><ArrowLeft className="size-4" />Handovers</Link>
      <PageHeader title="Create handover" subtitle="Configure what to reconstruct, generate the draft, then send it for human verification." />
      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <ol className="scrollbar-thin flex gap-1 overflow-x-auto lg:flex-col">
          {WZ.map((l, i) => {
            const reachable = i <= maxStep && step < 5 ? true : i <= maxStep && (i < 5 || genPct >= 100)
            return (
              <li key={l} className="shrink-0">
                <button disabled={!reachable || (step >= 5 && i < 5 && genPct > 0 && genPct < 100)} onClick={() => go(i)} className={cn('flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition disabled:cursor-not-allowed', i === step ? 'bg-white shadow-card' : reachable ? 'hover:bg-white/60' : 'opacity-50')}>
                  <span className={cn('flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold', i < step || (i <= maxStep && i !== step) ? 'bg-ok text-white' : i === step ? 'bg-brand text-white' : 'bg-slate-200 text-slate-500')}>{i < step || (i <= maxStep && i !== step) ? <Check className="size-3" /> : i + 1}</span>
                  <span className={cn('text-[13px] font-medium', i === step ? 'text-navy' : 'text-muted')}>{l}</span>
                </button>
              </li>
            )
          })}
        </ol>
        <Card className="p-5 sm:p-7">
          <p className="text-xs font-medium text-brand">Step {step + 1} of {WZ.length}</p>
          {step === 0 && (<>
            <h2 className="mt-1 text-lg font-semibold text-navy">Select project</h2><p className="mt-1 text-sm text-muted">You can create handovers on projects where you're the Project Manager.</p>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {s.projects.map((p) => {
                const ok = p.role === 'manager'
                return (
                  <button key={p.id} disabled={!ok} onClick={() => setPid(p.id)} className={cn('flex items-start gap-3 rounded-xl border p-4 text-left transition disabled:cursor-not-allowed disabled:opacity-55', pid === p.id ? 'border-brand bg-tint/40 ring-4 ring-brand/10' : 'border-line hover:border-slate-300')}>
                    <span className="flex size-9 items-center justify-center rounded-lg text-[11px] font-bold text-white" style={{ background: p.color }}>{p.code}</span>
                    <span className="flex-1"><span className="block text-sm font-semibold text-navy">{p.name}</span><span className="mt-1 flex items-center gap-1.5 text-xs text-muted">{ok ? `${s.sources.filter((x) => x.projectId === p.id && x.status !== 'disconnected').length} sources · ${s.members.filter((m) => m.projectId === p.id).length} members` : <><Lock className="size-3" />{ROLE_LABEL[p.role]} · no permission</>}</span></span>
                    {pid === p.id && <CheckCircle2 className="size-5 text-brand" />}
                  </button>
                )
              })}
            </div>
          </>)}
          {step === 1 && (<>
            <h2 className="mt-1 text-lg font-semibold text-navy">Select outgoing and incoming members</h2><p className="mt-1 text-sm text-muted">The outgoing member verifies findings; the incoming member receives the published handover.</p>
            <div className="mt-6 grid items-end gap-4 sm:grid-cols-[1fr_auto_1fr]">
              <Field label="Outgoing member"><Select value={out} onChange={(e) => setOut(e.target.value)}><option value="">Select…</option>{members.map((m) => <option key={m.personId} value={m.personId}>{personById(m.personId).name} · {ROLE_LABEL[m.role]}</option>)}</Select></Field>
              <ArrowRight className="mx-auto mb-3 hidden size-5 text-brand sm:block" />
              <Field label="Incoming member"><Select value={inc} onChange={(e) => setInc(e.target.value)}><option value="">Select…</option>{members.map((m) => <option key={m.personId} value={m.personId}>{personById(m.personId).name} · {ROLE_LABEL[m.role]}</option>)}</Select></Field>
            </div>
            {out && inc && out === inc && <p className="mt-3 text-[13px] text-bad">Outgoing and incoming members must be different people.</p>}
            {out && inc && out !== inc && (
              <div className="mt-6 flex items-center gap-4 rounded-xl bg-slate-50 p-4">
                <div className="flex-1 text-center"><Avatar id={out} size={44} className="mx-auto" /><p className="mt-2 text-sm font-semibold text-navy">{personById(out).name}</p><p className="text-xs text-muted">{s.members.find((m) => m.personId === out && m.projectId === pid)?.responsibilities.join(', ') || personById(out).title}</p></div>
                <div className="flex flex-col items-center text-brand"><Workflow className="size-5" /><span className="mt-1 text-[11px] font-medium">hands over to</span></div>
                <div className="flex-1 text-center"><Avatar id={inc} size={44} className="mx-auto" /><p className="mt-2 text-sm font-semibold text-navy">{personById(inc).name}</p><p className="text-xs text-muted">{personById(inc).title}</p></div>
              </div>
            )}
          </>)}
          {step === 2 && (<>
            <h2 className="mt-1 text-lg font-semibold text-navy">Select authorised knowledge sources</h2><p className="mt-1 text-sm text-muted">Only evidence from selected sources is used. Recipients will see source references for every finding.</p>
            <div className="mt-5 space-y-2.5">
              {srcs.map((x) => (
                <div key={x.id} className={cn('flex items-center gap-3 rounded-xl border p-4', srcSel.includes(x.id) ? 'border-brand/40 bg-tint/30' : 'border-line')}>
                  <SourceIcon type={x.type} />
                  <div className="flex-1"><p className="text-sm font-semibold text-navy">{x.name} <span className="font-normal text-muted">· {x.account}</span></p><p className="text-xs text-muted">{x.records.toLocaleString()} records · {x.scope.join(', ')}</p>{x.status === 'error' && <p className="mt-1 flex items-center gap-1 text-xs text-bad"><AlertTriangle className="size-3" />Sync failing; evidence may be up to 2 days old</p>}</div>
                  <Switch checked={srcSel.includes(x.id)} onChange={(v) => setSrcSel(v ? [...srcSel, x.id] : srcSel.filter((y) => y !== x.id))} label={x.name} />
                </div>
              ))}
              {!srcs.length && <EmptyState icon={Database} title="No connected sources" body="Connect at least one source on this project first." action={<Button onClick={() => navigate(`/projects/${pid}/sources`)}>Connect sources</Button>} />}
            </div>
          </>)}
          {step === 3 && (<>
            <h2 className="mt-1 text-lg font-semibold text-navy">Define reconstruction scope</h2><p className="mt-1 text-sm text-muted">Narrow the date range and focus areas to keep the handover relevant.</p>
            <div className="mt-5 grid gap-4 sm:grid-cols-3">
              <Field label="Evidence from"><Input type="date" value={scope.from} onChange={(e) => setScope({ ...scope, from: e.target.value })} /></Field>
              <Field label="Evidence to" error={scope.from >= scope.to ? 'Must be after start' : undefined}><Input type="date" value={scope.to} onChange={(e) => setScope({ ...scope, to: e.target.value })} /></Field>
              <Field label="Handover due"><Input type="date" value={scope.due} onChange={(e) => setScope({ ...scope, due: e.target.value })} /></Field>
            </div>
            <p className="mb-2 mt-5 text-[13px] font-medium text-navy">Focus areas</p>
            <div className="grid gap-2 sm:grid-cols-3">{['Decisions', 'Tasks', 'Risks', 'Dependencies', 'Architecture', 'Contacts'].map((a) => <div key={a} className="rounded-lg border border-line px-3 py-2.5"><Checkbox checked={scope.areas.includes(a)} onChange={(v) => setScope({ ...scope, areas: v ? [...scope.areas, a] : scope.areas.filter((x) => x !== a) })} label={a} /></div>)}</div>
            <div className="mt-5 flex items-center justify-between rounded-xl border border-line p-4"><div><p className="text-[13px] font-medium text-navy">Only evidence authored by or involving {personById(out).name}</p><p className="text-xs text-muted">Recommended. Reduces noise and keeps the handover personal to their responsibilities.</p></div><Switch checked={scope.onlyOutgoing} onChange={(v) => setScope({ ...scope, onlyOutgoing: v })} /></div>
            <Field label="Notes for the AI (optional)" className="mt-4"><Textarea value={scope.notes} onChange={(e) => setScope({ ...scope, notes: e.target.value })} placeholder="e.g. Emphasise on-call duties and the July volume peak." /></Field>
          </>)}
          {step === 4 && (<>
            <h2 className="mt-1 text-lg font-semibold text-navy">Review configuration</h2><p className="mt-1 text-sm text-muted">Check everything before starting reconstruction.</p>
            <dl className="mt-5 divide-y divide-line rounded-xl border border-line">
              {[['Project', project?.name, 0], ['Members', `${personById(out).name} → ${personById(inc).name}`, 1], ['Sources', srcs.filter((x) => srcSel.includes(x.id)).map((x) => x.name).join(', '), 2], ['Date range', `${scope.from} → ${scope.to}`, 3], ['Focus areas', scope.areas.join(', '), 3], ['Due', scope.due, 3]].map(([k, v, st]) => (
                <div key={k as string} className="flex items-center gap-4 px-4 py-3"><dt className="w-28 text-[13px] text-muted">{k}</dt><dd className="flex-1 text-[13px] font-medium text-navy">{v}</dd><button onClick={() => go(st as number)} className="flex items-center gap-1 text-xs font-medium text-brand"><Pencil className="size-3" />Edit</button></div>
              ))}
            </dl>
            <div className="mt-4"><Callout icon={Lock} title="Privacy">Only the selected sources and date range are processed. The outgoing member can remove any finding before publication.</Callout></div>
          </>)}
          {step === 5 && (<>
            <h2 className="mt-1 text-lg font-semibold text-navy">Start AI knowledge reconstruction</h2><p className="mt-1 text-sm text-muted">Handover reads the authorised evidence and drafts structured findings. Typically takes 2–6 minutes.</p>
            {genPct === 0 ? (
              <div className="mt-6 flex flex-col items-center rounded-2xl border border-dashed border-[#D9E1F0] bg-tint/30 py-8 text-center">
                <SphereVisual variant="empty" emptyKind="sources" interactive={false} className="size-40" />
                <p className="mt-2 text-sm font-semibold text-navy">Ready to reconstruct {srcs.filter((x) => srcSel.includes(x.id)).reduce((a, b) => a + b.records, 0).toLocaleString()} records</p>
                <p className="mt-1 max-w-sm text-xs text-muted">Scattered source records will be linked into the project’s Organic Knowledge Sphere.</p>
                <Button className="mt-5" icon={Sparkles} onClick={() => setGenPct(2)}>Start reconstruction</Button>
              </div>
            ) : (
              <div className="mt-6">
                <div className="rounded-2xl border border-line bg-canvas/60 p-4">
                  <ReconstructionLoader
                    progress={genPct}
                    title={genPct < 100 ? RECON_STAGES[Math.min(4, Math.floor(genPct / 20))] + '…' : 'Reconstruction complete'}
                    subtitle="Scattered source signals are converging into connected decisions, responsibilities, risks and dependencies."
                  />
                </div>
                <ol className="mt-6 space-y-2">{RECON_STAGES.map((st, i) => { const done = genPct >= (i + 1) * 20; const active = !done && genPct >= i * 20; return <li key={st} className="flex items-center gap-3 text-[13px]">{done ? <CheckCircle2 className="size-4 text-ok" /> : active ? <Loader2 className="size-4 animate-spin text-brand" /> : <span className="size-4 rounded-full border-2 border-slate-200" />}<span className={done ? 'text-navy' : active ? 'font-medium text-navy' : 'text-slate-400'}>{st}</span></li> })}</ol>
              </div>
            )}
          </>)}
          {step === 6 && (<>
            <h2 className="mt-1 text-lg font-semibold text-navy">Review generated handover</h2><p className="mt-1 text-sm text-muted">This is an AI draft. Nothing is verified yet; {personById(out).name} will confirm each finding.</p>
            <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">{[['Decisions', f.decisions.length, Lightbulb], ['Tasks', f.tasks.length, ListTodo], ['Risks', f.risks.length, AlertTriangle], ['Gaps', projGaps.length, FileQuestion]].map(([l, v, I]) => { const Ic = I as typeof Lightbulb; return <div key={l as string} className="rounded-xl border border-line p-3"><Ic className="size-4 text-brand" /><p className="mt-2 text-xl font-semibold text-navy">{v as number}</p><p className="text-xs text-muted">{l as string}</p></div> })}</div>
            <p className="mb-2 mt-5 text-xs font-semibold uppercase tracking-wide text-slate-400">Sample findings</p>
            <ul className="divide-y divide-line rounded-xl border border-line">{all.slice(0, 5).map((x) => <li key={x.id} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center"><Badge tone="indigo" className="w-fit">{x.kind}</Badge><span className="flex-1 text-[13px] font-medium text-navy">{x.title}</span><Confidence value={x.confidence} compact /></li>)}</ul>
            {!!all.filter((x) => x.verification === 'conflicting').length && <div className="mt-4"><Callout tone="amber" icon={AlertTriangle} title={`${all.filter((x) => x.verification === 'conflicting').length} findings have conflicting evidence`}>These are flagged for the outgoing member to resolve first.</Callout></div>}
          </>)}
          {step === 7 && (<>
            <h2 className="mt-1 text-lg font-semibold text-navy">Submit</h2><p className="mt-1 text-sm text-muted">Choose the next stage for this handover.</p>
            <div className="mt-5 space-y-3">
              <div className={cn('rounded-xl border p-4', submitMode === 'verify' ? 'border-brand bg-tint/30' : 'border-line')}><Radio checked={submitMode === 'verify'} onChange={() => setSubmitMode('verify')} label={<span className="font-medium">Send to {personById(out).name} for verification <Badge tone="blue" className="ml-1">Recommended</Badge></span>} description="They review findings, answer gaps, then submit for your approval." /></div>
              <div className={cn('rounded-xl border p-4', submitMode === 'approve' ? 'border-brand bg-tint/30' : 'border-line')}><Radio checked={submitMode === 'approve'} onChange={() => setSubmitMode('approve')} label={<span className="font-medium">Submit directly for approval</span>} description="Skip outgoing verification. Unverified findings stay clearly marked as unverified." /></div>
            </div>
            <p className="mt-4 flex items-center gap-1.5 text-xs text-muted"><Lock className="size-3" />{personById(out).name} and approvers will be notified. Nothing is visible to {personById(inc).name} until you publish.</p>
          </>)}
          <div className="mt-8 flex justify-between border-t border-line pt-5">
            <Button variant="ghost" icon={ArrowLeft} onClick={() => (step ? go(step - 1) : navigate('/handovers'))} disabled={step === 5 && genPct > 0 && genPct < 100}>{step ? 'Back' : 'Cancel'}</Button>
            {step < 7 ? <Button iconRight={ArrowRight} disabled={!valid} onClick={() => go(step + 1)}>{step === 4 ? 'Continue to generation' : 'Continue'}</Button> : <Button icon={Send} onClick={submit}>{submitMode === 'verify' ? 'Send for verification' : 'Submit for approval'}</Button>}
          </div>
        </Card>
      </div>
    </>
  )
}

/* ---------- 24. Handover layout + workspace ---------- */
const H_TABS = ['overview', 'knowledge', 'responsibilities', 'decisions', 'tasks', 'risks', 'dependencies', 'evidence', 'review', 'report'] as const
type HTab = (typeof H_TABS)[number]
const STAGE_LABELS = [['draft', 'Draft'], ['in_progress', 'Verification'], ['pending_review', 'Manager review'], ['approved', 'Approved'], ['published', 'Published'], ['completed', 'Acknowledged']] as const

export function HandoverLayout({ id, tab, children }: { id: string; tab: HTab; children: (h: Handover, role: ProjectRole) => ReactNode }) {
  const s = useStore()
  const { h, project, role } = useHandover(id)
  const [dlg, setDlg] = useState<null | 'submit' | 'approve' | 'publish' | 'changes' | 'start'>(null)
  const [note, setNote] = useState('')
  if (!h || !project) return <HandoverNotFound />
  const st = handoverStats(h, s.verif)
  const idx = STAGE_LABELS.findIndex(([k]) => k === h.status)
  const notify = (title: string, body: string, link: string) => s.setNotifications((ns) => [{ id: `n${Date.now()}`, type: 'approval', title, body, time: 'Just now', read: false, link, group: 'Today' }, ...ns])
  const actions: ReactNode[] = []
  if (role === 'outgoing' && (h.status === 'in_progress' || h.status === 'draft')) actions.push(<Button key="s" icon={Send} onClick={() => setDlg('submit')}>Submit for approval</Button>)
  if (role === 'manager' && h.status === 'draft') actions.push(<Button key="st" icon={Sparkles} onClick={() => setDlg('start')}>Start verification</Button>)
  if (role === 'manager' && h.status === 'pending_review') actions.push(<Button key="c" variant="secondary" icon={Undo2} onClick={() => setDlg('changes')}>Request changes</Button>, <Button key="a" variant="success" icon={ShieldCheck} onClick={() => setDlg('approve')}>Approve</Button>)
  if (role === 'manager' && h.status === 'approved') actions.push(<Button key="p" icon={Send} onClick={() => setDlg('publish')}>Publish to {personById(h.incomingId).name.split(' ')[0]}</Button>)
  if (role === 'incoming' && (h.status === 'published' || h.status === 'completed')) actions.push(<Button key="r" icon={BookOpen} onClick={() => navigate(`/handovers/${h.id}/recipient`)}>Open recipient view</Button>)
  const tabs = H_TABS.filter((t) => role !== 'incoming' || t !== 'review')
  const counts: Partial<Record<HTab, number>> = { decisions: projectFindings(h.projectId).decisions.length, tasks: projectFindings(h.projectId).tasks.length, risks: projectFindings(h.projectId).risks.length, dependencies: projectFindings(h.projectId).dependencies.length, evidence: projectFindings(h.projectId).evidence.length }
  return (
    <>
      <div className="no-print">
        <Card className="mb-5 overflow-hidden">
          <div className="p-5 sm:p-6">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2"><span className="text-xs font-semibold text-muted">{h.code}</span><StatusBadge status={h.status} /><Tooltip content="Your perspective on this handover, based on your role in the project."><span><RoleBadge role={role} /></span></Tooltip></div>
                <h1 className="mt-2 text-[22px] font-semibold tracking-tight text-navy">{project.name}</h1>
                <p className="mt-0.5 text-[13px] text-muted">{h.scope}</p>
                <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-3 text-[13px]">
                  <span className="flex items-center gap-2"><Avatar id={h.outgoingId} size={28} /><span><span className="block text-[11px] text-muted">Outgoing</span><span className="font-medium text-navy">{personById(h.outgoingId).name}</span></span></span>
                  <ArrowRight className="size-4 text-brand" />
                  <span className="flex items-center gap-2"><Avatar id={h.incomingId} size={28} /><span><span className="block text-[11px] text-muted">Incoming</span><span className="font-medium text-navy">{personById(h.incomingId).name}</span></span></span>
                  <span className="hidden h-8 w-px bg-line sm:block" />
                  <span><span className="block text-[11px] text-muted">Last updated</span><span className="font-medium text-navy">{h.updated}</span></span>
                  <span><span className="block text-[11px] text-muted">Due</span><span className="font-medium text-navy">{h.due}</span></span>
                </div>
              </div>
              <div className="flex shrink-0 flex-col items-start gap-3 lg:items-end">
                <div className="flex items-center gap-3"><Ring value={h.progress} size={56} /><div><p className="text-[11px] text-muted">Completion</p><p className="text-[13px] font-medium text-navy">{st.reviewed}/{st.all.length} reviewed</p></div></div>
                <div className="flex flex-wrap gap-2">{actions}<Button variant="secondary" icon={FileText} onClick={() => navigate(`/handovers/${h.id}/report`)}>Report</Button></div>
              </div>
            </div>
            <ol className="mt-6 grid grid-cols-6 gap-1.5">
              {STAGE_LABELS.map(([k, l], i) => (
                <li key={k}><div className={cn('h-1.5 rounded-full', i < idx ? 'bg-ok' : i === idx ? 'bg-brand' : 'bg-slate-200')} /><p className={cn('mt-1.5 hidden text-[11px] font-medium sm:block', i === idx ? 'text-brand' : i < idx ? 'text-navy' : 'text-slate-400')}>{l}</p></li>
              ))}
            </ol>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line bg-slate-50/60 px-5 py-2 text-xs text-muted">
            <span className="flex items-center gap-1.5"><Eye className="size-3.5" />Prototype: preview this handover as</span>
            <Segmented value={role} onChange={(v) => s.setPerspective((m) => ({ ...m, [h.id]: v }))} options={(['manager', 'outgoing', 'incoming'] as const).map((r) => ({ id: r, label: ROLE_LABEL[r].replace(' Member', '').replace('Project ', '') }))} />
          </div>
        </Card>
        <Tabs className="mb-5" tabs={tabs.map((t) => ({ id: t, label: t[0].toUpperCase() + t.slice(1), count: counts[t] }))} value={tab} onChange={(t) => navigate(t === 'review' ? `/handovers/${h.id}/review` : t === 'report' ? `/handovers/${h.id}/report` : t === 'overview' ? `/handovers/${h.id}` : `/handovers/${h.id}?tab=${t}`)} />
      </div>
      {children(h, role)}
      <ConfirmDialog open={dlg === 'submit'} onClose={() => setDlg(null)} title="Submit for manager approval?" confirmLabel="Submit" body={<>{st.all.length - st.reviewed > 0 ? <span className="mb-2 block rounded-lg bg-amber-50 p-2.5 text-amber-800">{st.all.length - st.reviewed} findings are still unreviewed. They'll be marked “Needs review” in the report.</span> : null}Your manager will review the verified findings and your answers before publishing to {personById(h.incomingId).name}.</>} onConfirm={() => { s.updateHandover(h.id, { status: 'pending_review', progress: Math.max(h.progress, 85), updated: 'Just now' }); notify('Approval requested', `${h.code} submitted for review.`, `/handovers/${h.id}/review`); s.toast('Submitted for approval', 'Your manager has been notified.') }} />
      <ConfirmDialog open={dlg === 'start'} onClose={() => setDlg(null)} title="Send for verification?" confirmLabel="Send" body={<>{personById(h.outgoingId).name} will be asked to verify the reconstructed findings.</>} onConfirm={() => { s.updateHandover(h.id, { status: 'in_progress', progress: 30, updated: 'Just now' }); s.toast('Sent for verification') }} />
      <ConfirmDialog open={dlg === 'approve'} onClose={() => setDlg(null)} title="Approve this handover?" confirmLabel="Approve" body={<>{st.verified} of {st.all.length} findings are verified. After approval you can publish the report to {personById(h.incomingId).name}.</>} onConfirm={() => { s.updateHandover(h.id, { status: 'approved', progress: 100, updated: 'Just now' }); s.toast('Handover approved', 'Ready to publish.') }} />
      <ConfirmDialog open={dlg === 'publish'} onClose={() => setDlg(null)} title={`Publish to ${personById(h.incomingId).name}?`} confirmLabel="Publish" body={<>They'll get access to the report, verified knowledge, linked evidence and the AI assistant. You can update or revoke access at any time from Published Handovers.</>} onConfirm={() => { s.updateHandover(h.id, { status: 'published', publishedOn: 'Jun 18, 2025', access: 'Active', updated: 'Just now' }); notify('Handover published', `${h.code} is now available to ${personById(h.incomingId).name}.`, '/handovers/published'); s.toast('Handover published', `${personById(h.incomingId).name} has been notified.`) }} />
      <Modal open={dlg === 'changes'} onClose={() => setDlg(null)} title="Request changes" subtitle={`Return ${h.code} to ${personById(h.outgoingId).name}`} footer={<><Button variant="secondary" onClick={() => setDlg(null)}>Cancel</Button><Button disabled={!note.trim()} onClick={() => { s.updateHandover(h.id, { status: 'in_progress', updated: 'Just now' }); s.toast('Changes requested', personById(h.outgoingId).name + ' has been notified.', 'info'); setDlg(null); setNote('') }}>Send request</Button></>}>
        <Field label="What needs to change?"><Textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Please resolve the Kafka retention conflict and document the month-end step." /></Field>
      </Modal>
    </>
  )
}

function FindingList({ items, onOpen }: { items: AnyFinding[]; onOpen: (f: AnyFinding) => void }) {
  if (!items.length) return <Card><EmptyState icon={Sparkles} title="Nothing here yet" body="No findings of this type were reconstructed for this handover." /></Card>
  return (
    <Card className="divide-y divide-line">
      {items.map((f) => (
        <button key={f.id} onClick={() => onOpen(f)} className="flex w-full flex-col gap-2 px-5 py-4 text-left hover:bg-slate-50 lg:flex-row lg:items-center">
          <div className="min-w-0 flex-1"><p className="text-[13.5px] font-medium text-navy">{f.title}</p><p className="mt-0.5 line-clamp-1 text-xs text-muted">{f.summary}</p></div>
          <span className="flex items-center gap-2 text-xs text-muted"><Avatar id={f.ownerId} size={20} /></span>
          <FindingRowMeta f={f} />
        </button>
      ))}
    </Card>
  )
}

export function HandoverWorkspace({ id }: { id: string }) {
  const s = useStore()
  const { query } = useRoute()
  const tab = (query.get('tab') as HTab) || 'overview'
  const [open, setOpen] = useState<AnyFinding>()
  return (
    <HandoverLayout id={id} tab={tab}>
      {(h, role) => {
        const f = projectFindings(h.projectId)
        const all = allFindings(h.projectId)
        const st = handoverStats(h, s.verif)
        const resp = s.members.find((m) => m.projectId === h.projectId && m.personId === h.outgoingId)?.responsibilities ?? []
        const myTasks = f.tasks.filter((t) => t.ownerId === h.outgoingId)
        const project = s.allProjects.find((p) => p.id === h.projectId)!
        const pg = gaps.filter((g) => g.projectId === h.projectId)
        const nextActions = role === 'manager' ? [h.status === 'pending_review' ? 'Review verification decisions and approve' : h.status === 'approved' ? 'Publish the report to the incoming member' : 'Monitor verification progress', 'Resolve conflicting evidence before approval', 'Confirm the incoming member has repository and on-call access'] : role === 'outgoing' ? [`Verify ${all.length - st.reviewed} remaining findings`, `Answer ${pg.filter((g) => !s.gapAnswers[g.id]).length} knowledge gaps`, 'Submit for approval'] : ['Read the project introduction and architecture', `Pick up “${f.tasks.find((t) => t.status !== 'Done')?.title ?? 'open tasks'}”`, 'Ask the assistant about anything unclear']
        let body: ReactNode = null
        if (tab === 'overview') body = (
          <div className="grid gap-5 lg:grid-cols-3">
            <Card className="p-5 lg:col-span-2">
              <p className="text-[15px] font-semibold text-navy">Project summary</p>
              <p className="mt-2 text-[13.5px] leading-relaxed text-slate-700">{project.description} {personById(h.outgoingId).name} has been responsible for {resp.join(', ').toLowerCase() || 'core project work'}. This handover transfers those responsibilities to {personById(h.incomingId).name}.</p>
              <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">{[['Decisions', f.decisions.length], ['Pending work', f.tasks.filter((t) => t.status !== 'Done').length], ['Open risks', f.risks.filter((r) => r.resolution !== 'Resolved').length], ['Dependencies', f.dependencies.length]].map(([l, v]) => <div key={l as string} className="rounded-xl bg-slate-50 p-3"><p className="text-xl font-semibold text-navy">{v}</p><p className="text-xs text-muted">{l}</p></div>)}</div>
            </Card>
            <Card className="p-5">
              <p className="text-[15px] font-semibold text-navy">Knowledge completeness</p>
              <div className="mt-4 flex items-center gap-4"><Ring value={st.completeness} size={76} color="#299B80" /><div className="text-[13px]"><p><span className="font-semibold text-navy">{st.verified}</span> <span className="text-muted">verified</span></p><p><span className="font-semibold text-navy">{st.reviewed - st.verified}</span> <span className="text-muted">rejected / flagged</span></p><p><span className="font-semibold text-navy">{st.all.length - st.reviewed}</span> <span className="text-muted">awaiting review</span></p></div></div>
              <p className="mt-4 text-xs text-muted">Completeness counts only human-verified findings, not AI confidence.</p>
            </Card>
            <Card>
              <CardHeader title="Important responsibilities" icon={UserRoundCog} />
              <ul className="space-y-2 px-5 pb-5">{resp.map((r) => <li key={r} className="flex items-center gap-2 text-[13px] text-navy"><CheckCircle2 className="size-4 text-ok" />{r}</li>)}{!resp.length && <li className="text-[13px] text-muted">None recorded.</li>}</ul>
            </Card>
            <Card>
              <CardHeader title="Pending work" icon={ListTodo} />
              <ul className="space-y-2.5 px-5 pb-5">{f.tasks.filter((t) => t.status !== 'Done').slice(0, 4).map((t) => <li key={t.id} className="flex items-center gap-2"><span className="flex-1 truncate text-[13px] text-navy">{t.title}</span><TaskStatus status={t.status} /></li>)}</ul>
            </Card>
            <Card>
              <CardHeader title="Recommended next actions" icon={Sparkles} />
              <ol className="space-y-2.5 px-5 pb-5">{nextActions.map((a, i) => <li key={a} className="flex items-start gap-2.5 text-[13px] text-navy"><span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-tint text-[11px] font-semibold text-brand">{i + 1}</span>{a}</li>)}</ol>
            </Card>
            <Card className="lg:col-span-2">
              <CardHeader title="Important decisions" icon={Lightbulb} action={<button className="text-[13px] font-medium text-brand" onClick={() => navigate(`/handovers/${h.id}?tab=decisions`)}>All</button>} />
              <ul className="divide-y divide-line px-5 pb-3">{f.decisions.slice(0, 3).map((d) => <li key={d.id}><button onClick={() => setOpen({ ...d, kind: 'Decision' })} className="flex w-full flex-col gap-2 py-3 text-left sm:flex-row sm:items-center"><span className="flex-1 text-[13px] font-medium text-navy">{d.title}</span><VerificationBadge status={s.verif[d.id] ?? d.verification} /></button></li>)}</ul>
            </Card>
            <Card>
              <CardHeader title="Unresolved risks" icon={AlertTriangle} />
              <ul className="space-y-2.5 px-5 pb-5">{f.risks.filter((r) => r.resolution !== 'Resolved').slice(0, 3).map((r) => <li key={r.id} className="flex items-start gap-2"><SeverityBadge level={r.severity} /><span className="text-[13px] text-navy">{r.title}</span></li>)}</ul>
            </Card>
            <Card className="lg:col-span-3">
              <CardHeader title="Dependencies" icon={Network} />
              <div className="grid gap-2 px-5 pb-5 sm:grid-cols-2 lg:grid-cols-3">{f.dependencies.map((d) => <div key={d.id} className={cn('rounded-xl border p-3', d.blocking ? 'border-red-200 bg-red-50/30' : 'border-line')}><p className="text-[13px] font-medium text-navy">{d.from} → {d.to}</p><p className="mt-1 flex items-center gap-1.5 text-xs text-muted"><Badge tone={d.depType === 'External' ? 'amber' : d.depType === 'Task' ? 'green' : 'blue'}>{d.depType}</Badge>{d.blocking && <Badge tone="red" icon={Ban}>Blocking</Badge>}</p></div>)}</div>
            </Card>
          </div>
        )
        if (tab === 'knowledge') body = (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[['Decisions', f.decisions.length, Lightbulb, 'decisions'], ['Tasks', f.tasks.length, ListTodo, 'tasks'], ['Risks', f.risks.length, AlertTriangle, 'risks'], ['Dependencies', f.dependencies.length, Network, 'dependencies']].map(([l, v, I, t]) => { const Ic = I as typeof Lightbulb; return <button key={l as string} onClick={() => navigate(`/handovers/${h.id}?tab=${t}`)} className="tile rounded-[14px] border p-5 text-left"><Ic className="size-5 text-brand" /><p className="mt-3 text-2xl font-semibold text-navy">{v as number}</p><p className="text-[13px] text-muted">{l as string}</p></button> })}
            <Card className="sm:col-span-2 lg:col-span-4"><EmptyState icon={Network} title="Explore relationships in the Knowledge Explorer" body="See how decisions, tasks, risks, people and components connect, with supporting evidence." action={<Button icon={Network} onClick={() => navigate(`/projects/${h.projectId}/knowledge`)}>Open Knowledge Explorer</Button>} /></Card>
          </div>
        )
        if (tab === 'responsibilities') body = (
          <div className="grid gap-5 lg:grid-cols-2">
            <Card><CardHeader title={`${personById(h.outgoingId).name}'s responsibilities`} subtitle="Transferring to the incoming member" icon={UserRoundCog} />
              <ul className="space-y-2 px-5 pb-5">{resp.map((r) => <li key={r} className="flex items-center gap-3 rounded-xl border border-line p-3"><Avatar id={h.outgoingId} size={24} /><span className="flex-1 text-[13px] font-medium text-navy">{r}</span><ArrowRight className="size-3.5 text-brand" /><Avatar id={h.incomingId} size={24} /></li>)}</ul>
            </Card>
            <Card><CardHeader title="Owned tasks" icon={ListTodo} /><ul className="divide-y divide-line px-5 pb-3">{myTasks.map((t) => <li key={t.id} className="flex items-center gap-2 py-3"><span className="flex-1 text-[13px] text-navy">{t.title}</span><TaskStatus status={t.status} /></li>)}{!myTasks.length && <li className="py-3 text-[13px] text-muted">No tasks owned.</li>}</ul></Card>
          </div>
        )
        if (tab === 'decisions') body = <FindingList items={f.decisions.map((x) => ({ ...x, kind: 'Decision' as const }))} onOpen={setOpen} />
        if (tab === 'tasks') body = <FindingList items={f.tasks.map((x) => ({ ...x, kind: 'Task' as const }))} onOpen={setOpen} />
        if (tab === 'risks') body = <FindingList items={f.risks.map((x) => ({ ...x, kind: 'Risk' as const }))} onOpen={setOpen} />
        if (tab === 'dependencies') body = <FindingList items={f.dependencies.map((x) => ({ ...x, kind: 'Dependency' as const }))} onOpen={setOpen} />
        if (tab === 'evidence') body = (
          <Card className="overflow-hidden"><Table><thead><tr><Th>Evidence</Th><Th>Author</Th><Th>Date</Th><Th>Used by</Th><Th>Verification</Th></tr></thead>
            <tbody>{f.evidence.map((e) => <tr key={e.id} className="cursor-pointer hover:bg-slate-50/70" onClick={() => navigate(`/projects/${h.projectId}/evidence/${e.id}`)}><Td><span className="flex items-center gap-3"><EvidenceTypeIcon type={e.type} /><span><span className="block font-medium text-navy">{e.title}</span><span className="text-xs text-muted">{EVIDENCE_TYPE_LABEL[e.type]} · {e.ref}</span></span></span></Td><Td className="text-[13px]">{personById(e.authorId).name}</Td><Td className="text-[13px] text-muted">{e.date.split(' ')[0]}</Td><Td className="text-[13px]">{all.filter((x) => x.evidenceIds.includes(e.id)).length} findings</Td><Td><VerificationBadge status={e.verification} /></Td></tr>)}</tbody>
          </Table></Card>
        )
        return <>{body}<FindingDrawer finding={open} onClose={() => setOpen(undefined)} /></>
      }}
    </HandoverLayout>
  )
}

/* ---------- 27. Published ---------- */
export function PublishedHandovers() {
  const s = useStore()
  const [edit, setEdit] = useState<Handover | null>(null)
  const [revoke, setRevoke] = useState<Handover | null>(null)
  const [expiry, setExpiry] = useState('none')
  const list = s.handovers.filter((h) => h.status === 'published' || h.status === 'completed')
  return (
    <>
      <PageHeader title="Published Handovers" subtitle="Control who can access published knowledge and track acknowledgement." />
      <Card className="overflow-hidden">
        {!list.length ? <EmptyState icon={Send} title="Nothing published yet" body="Approved handovers you publish to incoming members appear here." /> : (
          <Table>
            <thead><tr><Th>Handover</Th><Th>Project</Th><Th>Recipient</Th><Th>Published</Th><Th>Access</Th><Th>Acknowledgement</Th><Th className="text-right">Actions</Th></tr></thead>
            <tbody>{list.map((h) => {
              const manager = s.projectRole(h.projectId) === 'manager'
              return (
                <tr key={h.id} className="hover:bg-slate-50/50">
                  <Td><Link to={`/handovers/${h.id}/report`} className="font-medium text-navy hover:text-brand">{h.code}</Link><p className="text-xs text-muted">from {personById(h.outgoingId).name}</p></Td>
                  <Td className="text-[13px]">{s.allProjects.find((p) => p.id === h.projectId)?.name}</Td>
                  <Td><span className="flex items-center gap-2 whitespace-nowrap text-[13px]"><Avatar id={h.incomingId} size={24} />{personById(h.incomingId).name}</span></Td>
                  <Td className="whitespace-nowrap text-[13px] text-muted">{h.publishedOn}</Td>
                  <Td><Badge tone={h.access === 'Revoked' ? 'red' : h.access?.startsWith('Expires') ? 'amber' : 'green'} dot>{h.access ?? 'Active'}</Badge></Td>
                  <Td>{h.status === 'completed' ? <Badge tone="green" icon={CheckCircle2}>Acknowledged {h.acknowledgedOn}</Badge> : <Badge tone="amber" icon={Clock}>Pending</Badge>}</Td>
                  <Td className="text-right"><div className="flex justify-end gap-1.5">{manager ? <><Button size="sm" variant="secondary" icon={KeyRound} onClick={() => setEdit(h)}>Update access</Button><Button size="sm" variant="ghost" className="text-red-600" disabled={h.access === 'Revoked'} onClick={() => setRevoke(h)}>Revoke</Button></> : <span className="text-xs text-muted"><Lock className="mr-1 inline size-3" />Manager only</span>}</div></Td>
                </tr>
              )
            })}</tbody>
          </Table>
        )}
      </Card>
      <Modal open={!!edit} onClose={() => setEdit(null)} title="Update access" subtitle={edit ? `${edit.code} · ${personById(edit.incomingId).name}` : ''} footer={<><Button variant="secondary" onClick={() => setEdit(null)}>Cancel</Button><Button onClick={() => { if (edit) s.updateHandover(edit.id, { access: expiry === 'none' ? 'Active' : 'Expires Jul 31' }); s.toast('Access updated'); setEdit(null) }}>Save</Button></>}>
        <div className="space-y-4">
          <div className="space-y-3"><Radio checked={expiry === 'none'} onChange={() => setExpiry('none')} label="No expiry" description="Recipient keeps access while they're on the project." /><Radio checked={expiry === 'jul'} onChange={() => setExpiry('jul')} label="Expire on Jul 31, 2025" description="Access is removed automatically." /></div>
          <div className="space-y-2 rounded-xl border border-line p-4"><p className="text-[13px] font-medium text-navy">Recipient can access</p><Checkbox checked onChange={() => {}} label="Handover report" /><Checkbox checked onChange={() => {}} label="Linked evidence" /><Checkbox checked onChange={() => {}} label="AI assistant" /></div>
        </div>
      </Modal>
      <ConfirmDialog open={!!revoke} onClose={() => setRevoke(null)} tone="danger" title="Revoke access?" confirmLabel="Revoke access" body={revoke && <>{personById(revoke.incomingId).name} will immediately lose access to {revoke.code}, including the assistant. This is recorded in the audit log.</>} onConfirm={() => { if (revoke) s.updateHandover(revoke.id, { access: 'Revoked' }); s.toast('Access revoked', undefined, 'info') }} />
    </>
  )
}

/* ---------- 28. Received ---------- */
export function ReceivedHandovers() {
  const s = useStore()
  const list = s.handovers.filter((h) => h.incomingId === ME && (h.status === 'published' || h.status === 'completed'))
  const pending = list.filter((h) => h.status === 'published')
  return (
    <>
      <PageHeader title="Received Handovers" subtitle="Knowledge transferred to you. Start with anything awaiting acknowledgement." />
      {!list.length ? <Card><EmptyState icon={Inbox} title="Your inbox is empty" body="When someone publishes a handover to you, it appears here with everything you need to get started." /></Card> : (
        <>
          {!!pending.length && <div className="mb-5"><Callout tone="blue" icon={Inbox} title={`${pending.length} handover${pending.length > 1 ? 's' : ''} awaiting your acknowledgement`}>Review the knowledge, ask questions, then acknowledge so the outgoing member and manager know you're ready.</Callout></div>}
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {list.map((h) => {
              const p = s.allProjects.find((x) => x.id === h.projectId)!
              const f = projectFindings(h.projectId)
              return (
                <Card key={h.id} interactive className={cn('flex flex-col overflow-hidden', h.status === 'published' && 'ring-2 ring-brand/20')}>
                  <div className="h-1.5" style={{ background: p.color }} />
                  <div className="flex flex-1 flex-col p-5">
                    <div className="flex items-center justify-between"><span className="text-xs font-medium text-muted">{h.code}</span>{h.status === 'published' ? <Badge tone="amber" icon={Clock}>Pending acknowledgement</Badge> : <Badge tone="green" icon={CheckCircle2}>Acknowledged</Badge>}</div>
                    <h3 className="mt-3 text-base font-semibold text-navy">{p.name}</h3>
                    <p className="mt-0.5 text-[13px] text-muted">{h.scope}</p>
                    <div className="mt-4 flex items-center gap-2.5 text-[13px]"><Avatar id={h.outgoingId} size={28} /><div><p className="font-medium text-navy">{personById(h.outgoingId).name}</p><p className="text-xs text-muted">Published {h.publishedOn}</p></div></div>
                    <div className="mt-4 grid grid-cols-3 gap-2 text-center">{[['Decisions', f.decisions.length], ['Tasks', f.tasks.length], ['Risks', f.risks.length]].map(([l, v]) => <div key={l as string} className="rounded-lg bg-slate-50 py-2"><p className="text-sm font-semibold text-navy">{v}</p><p className="text-[11px] text-muted">{l}</p></div>)}</div>
                    <div className="mt-4"><div className="mb-1 flex justify-between text-xs"><span className="text-muted">Completion</span><span className="font-medium text-navy">{h.status === 'completed' ? 100 : 40}%</span></div><Progress value={h.status === 'completed' ? 100 : 40} size="sm" tone={h.status === 'completed' ? 'green' : 'blue'} /></div>
                    <div className="mt-5 flex gap-2"><Button className="flex-1" iconRight={ArrowRight} onClick={() => navigate(`/handovers/${h.id}/recipient`)}>Open handover</Button><Button variant="secondary" icon={MessageSquareText} onClick={() => navigate(`/handovers/${h.id}/assistant`)} aria-label="Ask assistant" /></div>
                  </div>
                </Card>
              )
            })}
          </div>
        </>
      )}
    </>
  )
}
