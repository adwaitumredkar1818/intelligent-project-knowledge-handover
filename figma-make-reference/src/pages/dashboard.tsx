import type { ReactNode } from 'react'
import { AlertTriangle, ArrowRight, BookOpen, CheckCircle2, ClipboardCheck, Database, FileQuestion, FolderPlus, Inbox, ListTodo, MessageSquareText, Plug, Plus, ShieldCheck, Sparkles, UserPlus, Workflow, Lightbulb, CircleDashed, ChevronRight } from 'lucide-react'
import { useStore } from '@/lib/store'
import { Link, navigate } from '@/lib/router'
import { activityTrend, gaps, ME, personById, timeline, ROLE_LABEL, HANDOVER_STATUS_LABEL, type Project } from '@/lib/data'
import { Avatar, Badge, Button, Card, EmptyState, MetricBand, ReconstructionLoader, Skeleton, SphereVisual, StatusBadge, cn, useFakeLoading, Confidence, SectionLabel, Mono } from '@/components/ui'
import { LineChart, Ring } from '@/components/charts'
import { RoleBadge } from '@/components/Shell'
import { allFindings, projectFindings, SeverityBadge } from '@/components/domain'
import { SourceIcon } from '@/components/brand'

function greeting() {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
}
const today = new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })

/* Section header used inside dashboard panels: calmer than a card header, with an optional link. */
function Panel({ title, sub, action, children, className }: { title: string; sub?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <Card className={cn('flex flex-col', className)}>
      <div className="flex items-start justify-between gap-3 px-5 pb-3 pt-4 sm:px-6 sm:pt-5">
        <div><h3 className="text-[15px] font-semibold tracking-[-0.01em] text-navy">{title}</h3>{sub && <p className="mt-0.5 text-[12.5px] text-muted">{sub}</p>}</div>
        {action}
      </div>
      {children}
    </Card>
  )
}
const ViewLink = ({ to, children = 'View all' }: { to: string; children?: ReactNode }) => <Link to={to} className="group flex shrink-0 items-center gap-0.5 text-[12.5px] font-semibold text-brand">{children}<ChevronRight className="size-3.5 transition-transform group-hover:translate-x-0.5" /></Link>

function ProjectSwitcherStrip() {
  const s = useStore()
  return (
    <div className="scrollbar-thin -mx-1 flex gap-1 overflow-x-auto px-1 pb-1" role="tablist" aria-label="Switch project">
      {s.projects.map((p) => {
        const active = p.id === s.currentProject?.id
        return (
          <button key={p.id} role="tab" aria-selected={active} onClick={() => s.switchProject(p.id)} className={cn('flex shrink-0 items-center gap-2.5 rounded-[10px] border px-3 py-2 text-left transition-all duration-200', active ? 'border-line bg-white shadow-[0_1px_2px_rgba(32,54,83,0.06)]' : 'border-transparent hover:bg-white/60')}>
            <span className="flex size-6 items-center justify-center rounded-md text-[9.5px] font-bold text-white" style={{ background: p.color }}>{p.code}</span>
            <span className={cn('text-[13px]', active ? 'font-semibold text-navy' : 'font-medium text-[#4a5d7c]')}>{p.name}</span>
            <span className={cn('flex items-center gap-1 text-[11.5px]', { manager: 'text-brand', outgoing: 'text-amber-700', incoming: 'text-teal-700' }[p.role])}><span className={cn('size-1.5 rounded-full', { manager: 'bg-brand', outgoing: 'bg-warn', incoming: 'bg-ok' }[p.role])} />{ROLE_LABEL[p.role].replace(' Member', '').replace('Project ', '')}</span>
          </button>
        )
      })}
    </div>
  )
}

function NextAction({ title, body, cta, to, tone = 'blue' }: { title: string; body: string; cta: string; to: string; tone?: 'blue' | 'amber' | 'green' }) {
  const rail = { blue: 'bg-brand', amber: 'bg-warn', green: 'bg-ok' }[tone]
  return (
    <div className="relative flex flex-col gap-3 overflow-hidden rounded-[14px] border border-line bg-white py-3.5 pl-5 pr-3.5 sm:flex-row sm:items-center">
      <span className={cn('absolute inset-y-0 left-0 w-1', rail)} />
      <div className="flex-1"><p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">Next best action</p><p className="mt-0.5 text-[14px] font-semibold text-navy">{title}</p><p className="text-[12.5px] text-muted">{body}</p></div>
      <Button iconRight={ArrowRight} onClick={() => navigate(to)}>{cta}</Button>
    </div>
  )
}

function DashSkeleton() {
  return (
    <div className="space-y-5">
      <Card className="grid grid-cols-2 gap-6 p-6 lg:grid-cols-4">{[1, 2, 3, 4].map((i) => <div key={i} className="space-y-3"><Skeleton className="h-3 w-24" /><Skeleton className="h-8 w-16" /></div>)}</Card>
      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="flex items-center justify-center p-6 lg:col-span-2"><ReconstructionLoader compact title="Syncing project knowledge context" /></Card>
        <Card className="space-y-4 p-6">{[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-6 w-full" />)}</Card>
      </div>
    </div>
  )
}

function ActivityList({ pid, limit = 6 }: { pid?: string; limit?: number }) {
  const items = timeline.filter((t) => !pid || t.projectId === pid).slice(0, limit)
  return (
    <ol className="px-5 pb-5 sm:px-6">
      {items.map((t, i) => (
        <li key={t.id} className="relative flex gap-3 pb-3.5 last:pb-0">
          {i < items.length - 1 && <span className="absolute left-[11px] top-7 h-[calc(100%-22px)] w-px bg-line" />}
          <Avatar id={t.personId} size={22} />
          <div className="min-w-0 flex-1"><p className="text-[13px] leading-snug text-navy"><span className="font-semibold">{personById(t.personId).name.split(' ')[0]}</span> <span className="text-[#4a5d7c]">{t.title.charAt(0).toLowerCase() + t.title.slice(1)}</span></p><p className="mt-0.5 truncate text-[11.5px] text-muted">{t.detail}</p></div>
          <span className="shrink-0 font-mono text-[11px] text-slate-400">{new Date(t.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</span>
        </li>
      ))}
    </ol>
  )
}

/* ---------------- Manager ---------------- */
function ManagerDash({ project }: { project: Project }) {
  const s = useStore()
  const managed = s.projects.filter((p) => p.role === 'manager')
  const active = s.handovers.filter((h) => ['in_progress', 'pending_review', 'draft', 'approved'].includes(h.status))
  const pending = s.handovers.filter((h) => h.status === 'pending_review')
  const connected = s.sources.filter((x) => x.status !== 'disconnected' && s.projects.some((p) => p.id === x.projectId))
  const failing = s.sources.filter((x) => x.status === 'error' && managed.some((p) => p.id === x.projectId))
  const f = projectFindings(project.id)
  const stages = (['draft', 'in_progress', 'pending_review', 'approved', 'published', 'completed'] as const).map((st) => ({ st, n: s.handovers.filter((h) => h.status === st).length }))
  const maxStage = Math.max(1, ...stages.map((x) => x.n))
  const attention = [
    ...pending.map((h) => ({ tone: 'amber', icon: ClipboardCheck, title: `${h.code} is waiting for your approval`, sub: `${personById(h.outgoingId).name} → ${personById(h.incomingId).name} · ${s.allProjects.find((p) => p.id === h.projectId)?.name}`, cta: 'Review', to: `/handovers/${h.id}/review` })),
    ...failing.map((x) => ({ tone: 'red', icon: Plug, title: `${x.name} has stopped syncing`, sub: `${x.account} · last success ${x.lastSync}`, cta: 'Reconnect', to: `/projects/${x.projectId}/sources/${x.id}` })),
    ...f.risks.filter((r) => r.severity === 'Critical').map((r) => ({ tone: 'red', icon: AlertTriangle, title: r.title, sub: `Critical risk · ${r.component}`, cta: 'Open', to: `/projects/${r.projectId}/intelligence/risks?id=${r.id}` })),
    ...f.decisions.filter((d) => s.verif[d.id] === 'conflicting').map((d) => ({ tone: 'ai', icon: Sparkles, title: 'Conflicting evidence on a decision', sub: d.title, cta: 'Resolve', to: `/projects/${d.projectId}/intelligence/decisions?id=${d.id}` })),
  ]
  const toneCls: Record<string, string> = { amber: 'bg-warn', red: 'bg-bad', ai: 'bg-ai' }
  const projSources = s.sources.filter((x) => x.projectId === project.id)
  const weekEvidence = activityTrend.slice(-5).reduce((a, b) => a + b.evidence, 0)
  const weekFindings = activityTrend.slice(-5).reduce((a, b) => a + b.findings, 0)
  return (
    <div className="space-y-5">
      {pending[0] ? <NextAction tone="amber" title={`Review ${pending[0].code} before ${pending[0].due}`} body={`${personById(pending[0].outgoingId).name} submitted the handover to ${personById(pending[0].incomingId).name}. ${allFindings(pending[0].projectId).filter((x) => s.verif[x.id] === 'conflicting').length} findings still have conflicting evidence.`} cta="Start review" to={`/handovers/${pending[0].id}/review`} /> : <NextAction tone="green" title="No approvals waiting" body="Start a handover when someone changes roles." cta="Create handover" to="/handovers/new" />}
      <MetricBand items={[
        { label: 'Total projects', value: s.projects.length, hint: `${managed.length} you manage`, tone: 'navy', onClick: () => navigate('/projects') },
        { label: 'Active handovers', value: active.length, hint: `${s.handovers.filter((h) => h.status === 'in_progress').length} in verification`, tone: 'blue', spark: [2, 3, 3, 4, 3, 5, active.length], onClick: () => navigate('/handovers') },
        { label: 'Pending approvals', value: pending.length, hint: pending.length ? 'oldest submitted 12 min ago' : 'nothing waiting', tone: 'amber', onClick: () => navigate('/handovers?status=pending_review') },
        { label: 'Connected sources', value: connected.length, hint: failing.length ? <span className="text-red-600">{failing.length} need attention</span> : 'all healthy', tone: failing.length ? 'red' : 'green', onClick: () => navigate(`/projects/${project.id}/sources`) },
      ]} />
      <div className="grid gap-5 lg:grid-cols-[1.75fr_1fr]">
        <Panel title="Knowledge processing activity" sub={`${project.name} · last 10 working days`} action={<ViewLink to={`/projects/${project.id}/ingestion`}>Ingestion</ViewLink>}>
          <div className="flex flex-wrap gap-x-8 gap-y-2 px-5 sm:px-6">
            <div><p className="flex items-center gap-1.5 text-[12px] text-muted"><span className="h-0.5 w-3 rounded bg-brand" />Evidence records</p><p className="mt-0.5 text-[20px] font-semibold tracking-[-0.02em] text-navy tabular-nums">{weekEvidence.toLocaleString()} <span className="text-[12px] font-medium text-muted">this week</span></p></div>
            <div><p className="flex items-center gap-1.5 text-[12px] text-muted"><span className="h-0.5 w-3 rounded bg-ai" />Findings extracted</p><p className="mt-0.5 text-[20px] font-semibold tracking-[-0.02em] text-navy tabular-nums">{weekFindings} <span className="text-[12px] font-medium text-muted">this week</span></p></div>
          </div>
          <div className="px-3 pb-4 pt-3 sm:px-4"><LineChart height={210} labels={activityTrend.map((a) => a.label)} series={[{ name: 'Evidence', color: '#315FBA', values: activityTrend.map((a) => a.evidence), area: true }, { name: 'Findings ×5', color: '#8B78C9', values: activityTrend.map((a) => a.findings * 5) }]} /></div>
        </Panel>
        <Panel title="Handover completion" sub={`${s.handovers.length} handovers across the workspace`} action={<ViewLink to="/handovers" />}>
          <ul className="space-y-2.5 px-5 pb-5 sm:px-6">
            {stages.map(({ st, n }, i) => (
              <li key={st}>
                <button onClick={() => navigate('/handovers')} className="group grid w-full grid-cols-[104px_1fr_24px] items-center gap-3 text-left">
                  <span className="text-[12.5px] text-[#4a5d7c] group-hover:text-navy">{HANDOVER_STATUS_LABEL[st]}</span>
                  <span className="h-2 overflow-hidden rounded-full bg-[#eef2f8]"><span className="animate-grow-x block h-full rounded-full" style={{ width: `${(n / maxStage) * 100}%`, background: ['#C9D3E3', '#7997BE', '#D39B43', '#A5A0D9', '#315FBA', '#299B80'][i], animationDelay: `${i * 60}ms` }} /></span>
                  <span className="text-right font-mono text-[12px] text-navy">{n}</span>
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-auto flex items-center justify-between border-t border-line px-5 py-3 text-[12.5px] sm:px-6"><span className="text-muted">Completion rate</span><span className="font-semibold text-navy">{Math.round((s.handovers.filter((h) => h.status === 'completed').length / Math.max(1, s.handovers.length)) * 100)}% acknowledged</span></div>
        </Panel>
      </div>
      <div className="grid gap-5 lg:grid-cols-[1.25fr_1fr]">
        <Panel title="Attention required" sub="Ordered by impact on active handovers" action={<Badge tone={attention.length ? 'amber' : 'green'}>{attention.length} open</Badge>}>
          <ul className="divide-y divide-line border-t border-line">
            {attention.slice(0, 5).map((a, i) => (
              <li key={i} className="group relative flex items-center gap-3.5 px-5 py-3 transition-colors hover:bg-[#f9fbfe] sm:px-6">
                <span className={cn('absolute inset-y-3 left-0 w-[3px] rounded-r', toneCls[a.tone])} />
                <a.icon className="size-4 shrink-0 text-slate-400" />
                <div className="min-w-0 flex-1"><p className="truncate text-[13.5px] font-semibold text-navy">{a.title}</p><p className="truncate text-[12px] text-muted">{a.sub}</p></div>
                <Button size="sm" variant="secondary" onClick={() => navigate(a.to)}>{a.cta}</Button>
              </li>
            ))}
            {!attention.length && <li><EmptyState className="py-8" icon={CheckCircle2} title="Nothing needs attention" body="Approvals, sync failures and critical risks will appear here." /></li>}
          </ul>
        </Panel>
        <Panel title="Project health" sub="Coverage, risk and source status" action={<ViewLink to="/projects" />}>
          <div className="border-t border-line">
            <div className="grid grid-cols-[1fr_64px_56px_40px] gap-2 px-5 py-2 text-[11px] font-medium text-slate-400 sm:px-6"><span>Project</span><span className="text-right">Health</span><span className="text-right">Risks</span><span className="text-right">Sync</span></div>
            {s.projects.map((p) => {
              const risks = projectFindings(p.id).risks.filter((r) => r.resolution !== 'Resolved').length
              const src = s.sources.filter((x) => x.projectId === p.id)
              const sync = src.some((x) => x.status === 'error') ? 'bg-bad' : src.length ? 'bg-ok' : 'bg-slate-300'
              return (
                <Link key={p.id} to={`/projects/${p.id}`} className="grid grid-cols-[1fr_64px_56px_40px] items-center gap-2 border-t border-line/70 px-5 py-2.5 transition-colors hover:bg-[#f9fbfe] sm:px-6">
                  <span className="flex min-w-0 items-center gap-2.5"><span className="size-2 shrink-0 rounded-full" style={{ background: p.color }} /><span className="truncate text-[13px] font-medium text-navy">{p.name}</span></span>
                  <span className="flex items-center justify-end gap-1.5"><span className="h-1 w-6 overflow-hidden rounded-full bg-slate-100"><span className="block h-full rounded-full" style={{ width: `${p.health}%`, background: p.health >= 80 ? '#299B80' : p.health >= 60 ? '#D39B43' : '#C9D3E3' }} /></span><span className="font-mono text-[12px] text-navy">{p.health || '—'}</span></span>
                  <span className={cn('text-right font-mono text-[12px]', risks ? 'text-navy' : 'text-slate-400')}>{risks}</span>
                  <span className="flex justify-end"><span className={cn('size-2 rounded-full', sync)} /></span>
                </Link>
              )
            })}
          </div>
        </Panel>
      </div>
      <div className="grid gap-5 lg:grid-cols-[1.75fr_1fr]">
        <Panel title="Recent activity" sub="Across the team" action={<ViewLink to={`/projects/${project.id}/activity`} />}><ActivityList /></Panel>
        <Panel title="Knowledge processing status" sub={project.name}>
          <ul className="space-y-3.5 px-5 pb-5 sm:px-6">
            {projSources.map((x) => (
              <li key={x.id}><Link to={`/projects/${project.id}/sources/${x.id}`} className="flex items-center gap-3">
                <SourceIcon type={x.type} size={28} />
                <div className="min-w-0 flex-1"><p className="flex items-center justify-between text-[13px]"><span className="font-medium text-navy">{x.name}</span><Mono className="text-[11.5px] text-muted">{x.records.toLocaleString()}</Mono></p><p className="text-[11.5px] text-muted">{x.status === 'error' ? <span className="text-red-600">Sync failing · {x.lastSync}</span> : `Synced ${x.lastSync}`}</p></div>
              </Link></li>
            ))}
            {!projSources.length && <EmptyState className="py-4" icon={Database} title="No sources" body="Connect a source to start processing." action={<Button size="sm" onClick={() => navigate(`/projects/${project.id}/sources`)}>Connect</Button>} />}
          </ul>
        </Panel>
      </div>
    </div>
  )
}

/* ---------------- Outgoing ---------------- */
function OutgoingDash({ project }: { project: Project }) {
  const s = useStore()
  const h = s.handovers.find((x) => x.projectId === project.id && x.outgoingId === ME)
  const findings = allFindings(project.id)
  const status = (f: (typeof findings)[number]) => s.verif[f.id] ?? f.verification
  const pending = findings.filter((f) => !['verified', 'rejected'].includes(status(f)))
  const projGaps = gaps.filter((g) => g.projectId === project.id && !s.gapAnswers[g.id])
  const myTasks = projectFindings(project.id).tasks.filter((t) => t.ownerId === ME && t.status !== 'Done')
  const reviewed = findings.length - findings.filter((f) => status(f) === 'needs_review').length
  const checklist = [
    { label: 'Review AI-generated findings', done: pending.length === 0, meta: `${reviewed}/${findings.length}` },
    { label: 'Answer missing information', done: projGaps.length === 0, meta: `${projGaps.length} open` },
    { label: 'Confirm pending responsibilities', done: false, meta: `${myTasks.length} tasks` },
    { label: 'Flag unresolved blockers', done: true, meta: '1 flagged' },
    { label: 'Submit for manager approval', done: h?.status === 'pending_review' || h?.status === 'approved' || h?.status === 'published', meta: h ? HANDOVER_STATUS_LABEL[h.status] : '' },
  ]
  return (
    <div className="space-y-5">
      {h && h.status === 'in_progress' && <NextAction tone="amber" title={`Verify ${pending.length} findings in ${h.code}`} body={`${personById(h.incomingId).name} takes over on ${h.due}. Conflicting findings are queued first.`} cta="Continue review" to={`/handovers/${h.id}/review`} />}
      <MetricBand items={[
        { label: 'My active handovers', value: s.handovers.filter((x) => x.outgoingId === ME && x.status !== 'completed').length, tone: 'blue', onClick: () => navigate('/handovers') },
        { label: 'Pending verification', value: pending.length, hint: 'findings to confirm', tone: 'amber', onClick: h ? () => navigate(`/handovers/${h.id}/review`) : undefined },
        { label: 'Missing information', value: projGaps.length, hint: 'questions only you can answer', tone: 'red', onClick: h ? () => navigate(`/handovers/${h.id}/review?gaps=1`) : undefined },
        { label: 'Pending responsibilities', value: myTasks.length, hint: 'tasks to transfer', tone: 'indigo', onClick: () => navigate(`/projects/${project.id}/intelligence/tasks`) },
      ]} />
      <div className="grid gap-5 lg:grid-cols-[1.75fr_1fr]">
        <Card>
          {h ? (
            <div className="p-5 sm:p-6">
              <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
                <Ring value={h.progress} size={84} label={<span className="text-[17px]">{h.progress}%</span>} />
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2"><Mono className="text-[12px] text-muted">{h.code}</Mono><StatusBadge status={h.status} /></div>
                  <h3 className="mt-1 text-[19px] font-semibold tracking-[-0.02em] text-navy">Your handover to {personById(h.incomingId).name}</h3>
                  <p className="mt-0.5 text-[13px] text-muted">{h.scope} · due {h.due}</p>
                </div>
              </div>
              <ol className="mt-6 divide-y divide-line rounded-xl border border-line">
                {checklist.map((c, i) => (
                  <li key={c.label} className="flex items-center gap-3 px-4 py-3">
                    {c.done ? <CheckCircle2 className="size-[18px] text-ok" /> : <span className="flex size-[18px] items-center justify-center rounded-full border-[1.5px] border-slate-300 font-mono text-[10px] text-slate-400">{i + 1}</span>}
                    <span className={cn('flex-1 text-[13.5px]', c.done ? 'text-muted line-through decoration-slate-300' : 'font-medium text-navy')}>{c.label}</span>
                    <Mono className="text-[11.5px] text-muted">{c.meta}</Mono>
                  </li>
                ))}
              </ol>
            </div>
          ) : <EmptyState icon={Workflow} title="No active handover" body="When a manager starts a handover for you on this project, it appears here." />}
        </Card>
        <Panel title="Missing information" sub="No evidence found for these">
          <ul className="space-y-2 px-5 pb-5 sm:px-6">
            {projGaps.map((g) => (
              <li key={g.id} className="rounded-xl border border-line p-3">
                <p className="text-[13px] font-medium leading-snug text-navy">{g.question}</p>
                <p className="mt-1 text-[11.5px] text-muted">{g.context}</p>
                {h && <button onClick={() => navigate(`/handovers/${h.id}/review?gaps=1`)} className="mt-2 text-[12px] font-semibold text-brand hover:underline">Answer now</button>}
              </li>
            ))}
            {!projGaps.length && <EmptyState className="py-6" icon={CheckCircle2} title="All gaps answered" body="Reviewers can see your answers." />}
          </ul>
        </Panel>
      </div>
      <div className="grid gap-5 lg:grid-cols-[1.75fr_1fr]">
        <Panel title="Pending verification" sub="Lowest AI confidence first" action={h && <ViewLink to={`/handovers/${h.id}/review`}>Review queue</ViewLink>}>
          <ul className="divide-y divide-line border-t border-line">
            {[...pending].sort((a, b) => a.confidence - b.confidence).slice(0, 5).map((f) => (
              <li key={f.id} className="flex flex-col gap-2 px-5 py-3 sm:flex-row sm:items-center sm:px-6">
                <span className="w-24 shrink-0 text-[11.5px] font-medium text-muted">{f.kind}</span>
                <span className="min-w-0 flex-1 truncate text-[13.5px] font-medium text-navy">{f.title}</span>
                <Confidence value={f.confidence} compact />
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="Recent project updates" sub={project.name}><ActivityList pid={project.id} limit={5} /></Panel>
      </div>
    </div>
  )
}

/* ---------------- Incoming ---------------- */
function IncomingDash({ project }: { project: Project }) {
  const s = useStore()
  const received = s.handovers.filter((h) => h.incomingId === ME && (h.status === 'published' || h.status === 'completed'))
  const pendingAck = received.filter((h) => h.status === 'published')
  const main = received.find((h) => h.projectId === project.id && h.status === 'published') ?? received.find((h) => h.projectId === project.id)
  const verified = allFindings(project.id).filter((f) => (s.verif[f.id] ?? f.verification) === 'verified')
  const f = projectFindings(project.id)
  const steps = [
    { icon: BookOpen, title: 'Read the introduction & architecture', sub: 'About 10 minutes', to: main ? `/handovers/${main.id}/recipient` : '#' },
    { icon: ListTodo, title: `Pick up ${f.tasks.filter((t) => t.status !== 'Done').length} open tasks`, sub: f.tasks[0]?.title ?? '', to: `/projects/${project.id}/intelligence/tasks` },
    { icon: AlertTriangle, title: 'Review open risks', sub: f.risks[0]?.title ?? 'No risks', to: `/projects/${project.id}/intelligence/risks` },
    { icon: MessageSquareText, title: 'Ask about anything unclear', sub: 'Answers cite verified evidence', to: main ? `/handovers/${main.id}/assistant` : '#' },
  ]
  return (
    <div className="space-y-5">
      <MetricBand items={[
        { label: 'Received handovers', value: received.length, tone: 'blue', onClick: () => navigate('/handovers/received') },
        { label: 'Knowledge available', value: verified.length, hint: 'verified findings', tone: 'green', onClick: () => navigate(`/projects/${project.id}/knowledge`) },
        { label: 'Pending acknowledgements', value: pendingAck.length, tone: 'amber' },
        { label: 'My projects', value: s.projects.length, tone: 'navy', onClick: () => navigate('/projects') },
      ]} />
      <div className="grid gap-5 lg:grid-cols-[1.75fr_1fr]">
        <Card className="relative overflow-hidden">
          {main ? (
            <div className="relative p-6 sm:p-7">
              <div className="pointer-events-none absolute -right-20 -top-20 size-80 rounded-full" style={{ background: 'radial-gradient(circle, rgba(217,233,229,0.9), transparent 65%)' }} />
              <div className="relative">
                <div className="flex flex-wrap items-center gap-2"><Badge tone="green" icon={Inbox}>Received {main.publishedOn}</Badge><StatusBadge status={main.status === 'completed' ? 'acknowledged' : 'pending'} /></div>
                <h3 className="mt-4 text-[24px] font-semibold tracking-[-0.025em] text-navy">{project.name}</h3>
                <p className="mt-1 text-[13.5px] text-muted">From <span className="font-semibold text-navy">{personById(main.outgoingId).name}</span> · {main.scope}</p>
                <dl className="mt-6 grid grid-cols-3 divide-x divide-line rounded-xl border border-line bg-white/80">
                  {[['Decisions', f.decisions.length], ['Open tasks', f.tasks.filter((t) => t.status !== 'Done').length], ['Risks', f.risks.length]].map(([l, v]) => <div key={l as string} className="px-4 py-3"><dd className="text-[22px] font-semibold tracking-[-0.02em] text-navy">{v}</dd><dt className="text-[12px] text-muted">{l}</dt></div>)}
                </dl>
                <div className="mt-6 flex flex-wrap gap-2"><Button iconRight={ArrowRight} onClick={() => navigate(`/handovers/${main.id}/recipient`)}>Open handover</Button><Button variant="secondary" icon={MessageSquareText} onClick={() => navigate(`/handovers/${main.id}/assistant`)}>Ask assistant</Button></div>
              </div>
            </div>
          ) : <EmptyState icon={Inbox} title="Nothing received yet" body="When a handover is published to you, it will appear here." />}
        </Card>
        <Panel title="Recommended next actions" sub="Your first week">
          <ol className="px-3 pb-4">
            {steps.map((st, i) => (
              <li key={i}><Link to={st.to} className="flex items-start gap-3 rounded-lg px-2 py-2.5 transition-colors hover:bg-[#f6f8fc]">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full border border-line font-mono text-[11px] text-brand">{i + 1}</span>
                <span className="min-w-0"><span className="block text-[13.5px] font-medium text-navy">{st.title}</span><span className="block truncate text-[12px] text-muted">{st.sub}</span></span>
              </Link></li>
            ))}
          </ol>
        </Panel>
      </div>
      <div className="grid gap-5 lg:grid-cols-3">
        <Panel title="Important updates">
          <ul className="space-y-3 px-5 pb-5 sm:px-6">
            {f.risks.slice(0, 3).map((r) => <li key={r.id} className="flex items-start gap-2.5"><SeverityBadge level={r.severity} /><span className="text-[13px] leading-snug text-navy">{r.title}</span></li>)}
            {timeline.filter((t) => t.projectId === project.id && t.type === 'ownership').map((t) => <li key={t.id} className="flex items-start gap-2.5"><Badge tone="indigo">Ownership</Badge><span className="text-[13px] text-navy">{t.detail}</span></li>)}
          </ul>
        </Panel>
        <Panel title="My projects">
          <ul className="px-3 pb-4">{s.projects.map((p) => <li key={p.id}><Link to={`/projects/${p.id}`} className="flex items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-[#f6f8fc]"><span className="flex size-6 items-center justify-center rounded-md text-[9.5px] font-bold text-white" style={{ background: p.color }}>{p.code}</span><span className="flex-1 truncate text-[13px] font-medium text-navy">{p.name}</span><RoleBadge role={p.role} /></Link></li>)}</ul>
        </Panel>
        <Panel title="Notifications" action={<ViewLink to="/notifications" />}>
          <ul className="px-3 pb-4">{s.notifications.slice(0, 4).map((n) => <li key={n.id}><Link to={n.link} className="flex gap-2.5 rounded-lg px-2 py-2 transition-colors hover:bg-[#f6f8fc]"><span className={cn('mt-1.5 size-1.5 shrink-0 rounded-full', n.read ? 'bg-slate-200' : 'bg-brand')} /><span className="min-w-0"><span className="block truncate text-[13px] font-medium text-navy">{n.title}</span><span className="line-clamp-1 text-[12px] text-muted">{n.body}</span></span></Link></li>)}</ul>
        </Panel>
      </div>
    </div>
  )
}

function EmptyWorkspace() {
  const steps = [
    { icon: FolderPlus, title: 'Create your first project', body: 'Projects group sources, members and handovers.', to: '/projects/new', cta: 'Create project' },
    { icon: Plug, title: 'Connect a data source', body: 'GitHub, Jira, Slack or document uploads.', to: '/projects/new', cta: 'Connect source' },
    { icon: UserPlus, title: 'Invite your team', body: 'Managers, outgoing and incoming members.', to: '/settings/team', cta: 'Invite' },
    { icon: Workflow, title: 'Start a handover', body: 'Reconstruct knowledge and verify it with people.', to: '/handovers/new', cta: 'Create handover' },
  ]
  return (
    <div className="space-y-5">
      <MetricBand items={['Projects', 'Active handovers', 'Connected sources', 'Verified findings'].map((l) => ({ label: l, value: <span className="text-slate-300">—</span>, hint: 'No data yet', tone: 'gray' as const }))} />
      <Card className="p-6 sm:p-8">
        <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-center">
          <div>
            <SectionLabel>Getting started · 0 of 4</SectionLabel>
            <h2 className="mt-3 text-[22px] font-semibold tracking-[-0.02em] text-navy">Set up Acme Sandbox</h2>
            <p className="mt-1 max-w-xl text-[14px] text-muted">This workspace has no projects, sources or handovers yet. As you connect tools and verify findings, the Organic Knowledge Sphere assembles automatically.</p>
          </div>
          <SphereVisual variant="empty" emptyKind="project" interactive={false} className="mx-auto size-36 shrink-0 sm:mx-0" />
        </div>
        <ol className="mt-7 grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((st, i) => (
            <li key={st.title} className="flex flex-col bg-white p-5">
              <div className="flex items-center justify-between"><st.icon className="size-5 text-brand" /><Mono className="text-[11px] text-slate-400">0{i + 1}</Mono></div>
              <p className="mt-4 text-[14px] font-semibold text-navy">{st.title}</p>
              <p className="mt-1 flex-1 text-[12.5px] text-muted">{st.body}</p>
              <Button size="sm" variant={i === 0 ? 'primary' : 'secondary'} className="mt-5 w-full" onClick={() => navigate(st.to)}>{st.cta}</Button>
            </li>
          ))}
        </ol>
      </Card>
    </div>
  )
}

export function Dashboard() {
  const s = useStore()
  const p = s.currentProject
  const loading = useFakeLoading(550, [p?.id, s.workspaceId])
  const me = personById(ME)
  if (!p) return (<><div className="mb-6"><p className="text-[12.5px] text-muted">{today}</p><h1 className="mt-1 text-[30px] font-semibold tracking-[-0.03em] text-navy">Welcome, {me.name.split(' ')[0]}</h1></div><EmptyWorkspace /></>)
  const pending = s.handovers.filter((h) => h.status === 'pending_review').length
  const failing = s.sources.filter((x) => x.status === 'error').length
  const summary = {
    manager: <>{s.handovers.filter((h) => ['in_progress', 'pending_review', 'approved'].includes(h.status)).length} handovers are moving. {pending ? <><span className="font-semibold text-navy">{pending} need{pending === 1 ? 's' : ''} your approval</span>{failing ? ', and ' : '.'}</> : null}{failing ? <span className="font-semibold text-navy">{failing} source{failing > 1 ? 's have' : ' has'} stopped syncing.</span> : null}</>,
    outgoing: <>You're handing over <span className="font-semibold text-navy">{p.name}</span>. Verify what the AI found and fill the gaps only you know.</>,
    incoming: <>You've joined <span className="font-semibold text-navy">{p.name}</span>. Everything below is verified knowledge from the previous owner.</>,
  }[p.role]
  const quick = {
    manager: [{ label: 'New project', icon: FolderPlus, to: '/projects/new' }, { label: 'Create handover', icon: Plus, to: '/handovers/new', primary: true }],
    outgoing: [{ label: 'Knowledge', icon: Sparkles, to: `/projects/${p.id}/knowledge` }, { label: 'Verify findings', icon: ClipboardCheck, to: `/handovers/${s.handovers.find((h) => h.outgoingId === ME && h.projectId === p.id)?.id ?? 'ho-1038'}/review`, primary: true }],
    incoming: [{ label: 'Explore knowledge', icon: Sparkles, to: `/projects/${p.id}/knowledge` }, { label: 'Open received', icon: Inbox, to: '/handovers/received', primary: true }],
  }[p.role]
  return (
    <>
      <header className="mb-6 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-2xl">
          <p className="flex flex-wrap items-center gap-2 text-[12.5px] text-muted">{today}<span className="text-slate-300">·</span><RoleBadge role={p.role} /></p>
          <h1 className="mt-2 text-[28px] font-semibold tracking-[-0.03em] text-navy sm:text-[32px]">{greeting()}, {me.name.split(' ')[0]}</h1>
          <p className="mt-1.5 text-[15px] leading-relaxed text-[#4a5d7c]">{summary}</p>
        </div>
        <div className="flex flex-wrap gap-2">{quick.map((q) => <Button key={q.label} variant={'primary' in q && q.primary ? 'primary' : 'secondary'} icon={q.icon} onClick={() => navigate(q.to)}>{q.label}</Button>)}</div>
      </header>
      <div className="mb-5 border-b border-line pb-3"><ProjectSwitcherStrip /></div>
      {loading ? <DashSkeleton /> : <div key={p.id} className="animate-fade">{p.role === 'manager' ? <ManagerDash project={p} /> : p.role === 'outgoing' ? <OutgoingDash project={p} /> : <IncomingDash project={p} />}</div>}
    </>
  )
}
