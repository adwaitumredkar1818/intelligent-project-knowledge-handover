'use client'

import { useEffect, useState, type ReactNode } from 'react'
import { AlertOctagon, AlertTriangle, ArrowRight, ExternalLink, Flag, Lock, MessageSquare, Send, ShieldCheck, Sparkles, Link2 } from 'lucide-react'
import { useFigmaStore } from '../../lib/figmaStore'
import {
  decisions, dependencies, evidence, personById, risks, tasks, ROLE_LABEL, ME,
  type FindingBase, type Verification, type Project, type Handover,
} from '../../lib/figmaStore'
import { Avatar, Badge, Button, Callout, ConfidenceBadge as Confidence, Drawer, EmptyState, Tabs, Textarea, VerifyBadge as VerificationBadge, cn, VERIF, type Tone } from './index'
import { EvidenceTypeIcon, EVIDENCE_TYPE_LABEL } from './brand'
import { FolderX } from 'lucide-react'

// RoleBadge — inline here (Shell.tsx not ported to figma-ui, keep self-contained)
import { ROLE_TONE } from './Shell'
export { ROLE_TONE }

export function RoleBadge({ role, className }: { role: 'manager' | 'outgoing' | 'incoming'; className?: string }) {
  return <Badge tone={ROLE_TONE[role]} dot className={className}>{ROLE_LABEL[role]}</Badge>
}

// Router shim — Next.js Link used for navigation; plain <a> for now
function LinkTo({ to, className, children, onClick }: { to: string; className?: string; children: ReactNode; onClick?: () => void }) {
  return <a href={to} className={className} onClick={onClick}>{children}</a>
}

function navigate(to: string) {
  if (typeof window !== 'undefined') window.location.href = to
}

export function useProject(projectId?: string) {
  const s = useFigmaStore()
  const project = s.projects.find((p) => p.id === projectId)
  useEffect(() => {
    if (project && s.currentProject?.id !== project.id) s.switchProject(project.id, true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project?.id])
  return project
}

export function ProjectNotFound() {
  return <EmptyState icon={FolderX} title="Project not found" body="It may belong to another workspace, or you may not have access to it." action={<Button onClick={() => navigate('/projects')}>Back to projects</Button>} />
}

export function projectFindings(pid: string) {
  return {
    decisions: decisions.filter((d) => d.projectId === pid),
    tasks: tasks.filter((d) => d.projectId === pid),
    risks: risks.filter((d) => d.projectId === pid),
    dependencies: dependencies.filter((d) => d.projectId === pid),
    evidence: evidence.filter((d) => d.projectId === pid),
  }
}
export type AnyFinding = FindingBase & { kind: 'Decision' | 'Task' | 'Risk' | 'Dependency' }
export function allFindings(pid: string): AnyFinding[] {
  const f = projectFindings(pid)
  return [
    ...f.decisions.map((x) => ({ ...x, kind: 'Decision' as const })),
    ...f.tasks.map((x) => ({ ...x, kind: 'Task' as const })),
    ...f.risks.map((x) => ({ ...x, kind: 'Risk' as const })),
    ...f.dependencies.map((x) => ({ ...x, kind: 'Dependency' as const })),
  ]
}
export function findingById(id: string): AnyFinding | undefined {
  const d = decisions.find((x) => x.id === id); if (d) return { ...d, kind: 'Decision' }
  const t = tasks.find((x) => x.id === id); if (t) return { ...t, kind: 'Task' }
  const r = risks.find((x) => x.id === id); if (r) return { ...r, kind: 'Risk' }
  const p = dependencies.find((x) => x.id === id); if (p) return { ...p, kind: 'Dependency' }
}

export const SEV_TONE: Record<string, Tone> = { Critical: 'red', High: 'amber', Medium: 'blue', Low: 'gray' }
export function SeverityBadge({ level }: { level: string }) {
  return <Badge tone={SEV_TONE[level]} icon={level === 'Critical' ? AlertOctagon : level === 'High' ? AlertTriangle : Flag}>{level}</Badge>
}
export function TaskStatus({ status }: { status: string }) {
  const t: Record<string, Tone> = { 'To do': 'gray', 'In progress': 'blue', Blocked: 'red', Done: 'green', Open: 'red', Mitigating: 'amber', Resolved: 'green' }
  return <Badge tone={t[status]} dot>{status}</Badge>
}

export function EvidenceChip({ id }: { id: string }) {
  const e = evidence.find((x) => x.id === id)
  if (!e) return null
  return (
    <LinkTo to={`/projects/${e.projectId}/evidence/${e.id}`} className="tile group inline-flex max-w-full items-center gap-1.5 rounded-lg border py-1 pl-1 pr-2 text-xs text-navy">
      <EvidenceTypeIcon type={e.type} className="size-5 rounded-md [&_svg]:size-3" />
      <span className="truncate font-medium">{e.ref}</span>
      <ExternalLink className="size-3 shrink-0 text-slate-400 group-hover:text-brand" />
    </LinkTo>
  )
}

export function EvidenceCard({ id, compact }: { id: string; compact?: boolean }) {
  const e = evidence.find((x) => x.id === id)
  if (!e) return null
  return (
    <div className="tile rounded-xl border p-3.5">
      <div className="flex items-start gap-2.5">
        <EvidenceTypeIcon type={e.type} />
        <div className="min-w-0 flex-1">
          <LinkTo to={`/projects/${e.projectId}/evidence/${e.id}`} className="block truncate text-[13px] font-semibold text-navy hover:text-brand">{e.title}</LinkTo>
          <p className="text-[11px] text-muted">{EVIDENCE_TYPE_LABEL[e.type]} · {e.ref} · {personById(e.authorId)?.name ?? ''} · {e.date.split(' ')[0]}</p>
        </div>
      </div>
      {!compact && <p className="mt-2.5 line-clamp-4 whitespace-pre-line border-l-2 border-sky pl-3 text-[12.5px] leading-relaxed text-slate-600">{e.content}</p>}
    </div>
  )
}

/** The verification state from the store (human), never the AI confidence. */
export function useVerification(id: string): Verification {
  return useFigmaStore().verif[id] ?? 'needs_review'
}

export function FindingDrawer({ finding, onClose, extra }: { finding?: AnyFinding; onClose: () => void; extra?: ReactNode }) {
  const s = useFigmaStore()
  const [text, setText] = useState('')
  if (!finding) return null
  const status = s.verif[finding.id] ?? finding.verification
  const role = s.projectRole(finding.projectId)
  const canVerify = role !== 'incoming'
  const set = (v: Verification) => { s.setVerif((m) => ({ ...m, [finding.id]: v })); s.toast(`Marked as ${VERIF[v].label.toLowerCase()}`, finding.title) }
  return (
    <Drawer open onClose={onClose} width="max-w-xl" title={<span className="flex items-center gap-2"><Badge tone="indigo">{finding.kind}</Badge><span className="truncate">{finding.title}</span></span>}
      footer={canVerify ? <>
        <Button variant="success" icon={ShieldCheck} className="flex-1" onClick={() => set('verified')}>Verify</Button>
        <Button variant="secondary" className="flex-1" onClick={() => set('conflicting')}>Flag conflict</Button>
        <Button variant="secondary" className="flex-1 text-red-600" onClick={() => set('rejected')}>Reject</Button>
      </> : <p className="flex items-center gap-2 text-xs text-muted"><Lock className="size-3.5" />Incoming members can read verified knowledge but cannot change verification.</p>}>
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-dashed border-indigo-200 bg-indigo-50/40 p-3"><p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-indigo-500">AI confidence</p><Confidence value={finding.confidence} /></div>
          <div className="rounded-xl border border-line p-3"><p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-slate-400">Human verification</p><VerificationBadge status={status} /></div>
        </div>
        <p className="text-sm leading-relaxed text-slate-700">{s.edits[finding.id] ?? finding.summary}</p>
        {extra}
        <div className="flex items-center gap-2 text-[13px] text-muted"><Avatar id={finding.ownerId} size={22} />Owner: <span className="font-medium text-navy">{personById(finding.ownerId)?.name ?? ''}</span> · {finding.date}</div>
        <div>
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400"><Link2 className="size-3.5" />Evidence chain · {finding.evidenceIds.length} sources</p>
          <div className="space-y-2">{finding.evidenceIds.map((e) => <EvidenceCard key={e} id={e} />)}</div>
        </div>
        <div>
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400"><MessageSquare className="size-3.5" />Reviewer comments</p>
          <div className="space-y-2">
            {(s.comments[finding.id] ?? []).map((c, i) => (
              <div key={i} className="flex gap-2.5"><Avatar id={c.by} size={24} /><div className="flex-1 rounded-xl bg-slate-50 px-3 py-2"><p className="text-xs font-medium text-navy">{personById(c.by)?.name ?? ''} <span className="font-normal text-slate-400">· {c.time}</span></p><p className="text-[13px] text-slate-700">{c.text}</p></div></div>
            ))}
            <div className="flex gap-2">
              <Textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Add a comment for reviewers…" className="min-h-[40px]" rows={1} />
              <Button variant="secondary" icon={Send} disabled={!text.trim()} onClick={() => { s.setComments((m) => ({ ...m, [finding.id]: [...(m[finding.id] ?? []), { by: ME, text, time: 'Just now' }] })); setText('') }} aria-label="Post comment" />
            </div>
          </div>
        </div>
      </div>
    </Drawer>
  )
}

const PROJECT_TABS = [
  { id: 'overview', label: 'Overview', path: '' },
  { id: 'knowledge', label: 'Knowledge', path: '/knowledge' },
  { id: 'team', label: 'Team', path: '/team' },
  { id: 'sources', label: 'Sources', path: '/sources' },
  { id: 'handovers', label: 'Handovers', path: '/handovers' },
  { id: 'activity', label: 'Activity', path: '/activity' },
] as const

export function ProjectHeader({ project, tab, actions }: { project: Project; tab?: (typeof PROJECT_TABS)[number]['id']; actions?: ReactNode }) {
  return (
    <div className="mb-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3.5">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-xl text-sm font-bold text-white shadow-sm" style={{ background: project.color }}>{project.code}</span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2"><h1 className="text-[22px] font-semibold tracking-tight text-navy">{project.name}</h1><RoleBadge role={project.role} /></div>
            <p className="mt-1 max-w-2xl text-sm text-muted">{project.description}</p>
          </div>
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
      {tab && <Tabs className="mt-5" tabs={PROJECT_TABS.map((t) => ({ id: t.id, label: t.label }))} value={tab} onChange={(id) => navigate(`/projects/${project.id}${PROJECT_TABS.find((t) => t.id === id)!.path}`)} />}
    </div>
  )
}

export function PermissionNote({ role, action }: { role: string; action: string }) {
  return (
    <Callout tone="amber" icon={Lock} title={`View only · ${ROLE_LABEL[role as 'manager']}`}>
      Only Project Managers can {action}. Controls are hidden here for clarity; permissions are always enforced by the server.
    </Callout>
  )
}

export function handoverPerspective(h: Handover, projectRole: string, override?: string) {
  if (override) return override as 'manager' | 'outgoing' | 'incoming'
  if (h.outgoingId === ME) return 'outgoing'
  if (h.incomingId === ME) return 'incoming'
  return projectRole as 'manager' | 'outgoing' | 'incoming'
}

export function FindingRowMeta({ f }: { f: AnyFinding }) {
  const v = useVerification(f.id)
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Confidence value={f.confidence} compact />
      <VerificationBadge status={v} />
      <span className="inline-flex items-center gap-1 text-xs text-muted"><Link2 className="size-3" />{f.evidenceIds.length}</span>
    </div>
  )
}

export function ConfidenceLegend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-line bg-white px-4 py-2.5 text-xs text-muted">
      <span className="flex items-center gap-1.5"><Sparkles className="size-3.5 text-indigo-500" /><span className="font-medium text-navy">AI confidence</span> = model certainty</span>
      <span className="flex items-center gap-1.5"><ShieldCheck className="size-3.5 text-ok" /><span className="font-medium text-navy">Verification</span> = a person confirmed it</span>
      <span className="hidden items-center gap-1 sm:flex">High confidence is not the same as verified<ArrowRight className="size-3" /></span>
    </div>
  )
}

export const cnx = cn

export function HandoverTable({ items, empty }: { items: Handover[]; empty?: ReactNode }) {
  const s = useFigmaStore()
  if (!items.length) return <>{empty}</>
  return (
    <>
      <div className="hidden md:block">
        <table className="w-full text-left text-sm">
          <thead><tr>{['Handover', 'Project', 'Outgoing → Incoming', 'Created', 'Progress', 'Review stage', 'Status'].map((h) => <th key={h} className="whitespace-nowrap border-b border-line bg-slate-50/70 px-4 py-2.5 text-xs font-medium text-muted first:pl-5 last:pr-5">{h}</th>)}</tr></thead>
          <tbody>
            {items.map((h) => {
              const p = s.allProjects.find((x) => x.id === h.projectId)
              return (
                <tr key={h.id} className="cursor-pointer border-b border-line/70 hover:bg-slate-50/70" onClick={() => navigate(`/handovers/${h.id}`)}>
                  <td className="py-3 pl-5 pr-4"><p className="font-medium text-navy">{h.code}</p><p className="max-w-[220px] truncate text-xs text-muted">{h.scope}</p></td>
                  <td className="px-4 py-3"><span className="flex items-center gap-2"><span className="size-2 rounded-full" style={{ background: p?.color }} /><span className="whitespace-nowrap text-[13px] text-navy">{p?.name}</span></span></td>
                  <td className="px-4 py-3"><span className="flex items-center gap-1.5 whitespace-nowrap"><Avatar id={h.outgoingId} size={24} /><ArrowRight className="size-3 text-slate-400" /><Avatar id={h.incomingId} size={24} /><span className="ml-1 text-[13px] text-muted">{personById(h.outgoingId)?.name?.split(' ')[0] ?? ''} → {personById(h.incomingId)?.name?.split(' ')[0] ?? ''}</span></span></td>
                  <td className="whitespace-nowrap px-4 py-3 text-[13px] text-muted">{h.created}</td>
                  <td className="w-36 px-4 py-3"><div className="flex items-center gap-2"><div className="h-1.5 flex-1 rounded-full bg-slate-100"><div className={cn('h-full rounded-full', h.progress === 100 ? 'bg-ok' : 'bg-brand')} style={{ width: `${h.progress}%` }} /></div><span className="text-xs text-muted">{h.progress}%</span></div></td>
                  <td className="px-4 py-3"><StageDots status={h.status} /></td>
                  <td className="py-3 pl-4 pr-5"><StatusPill status={h.status} /></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <ul className="divide-y divide-line md:hidden">
        {items.map((h) => (
          <li key={h.id}><LinkTo to={`/handovers/${h.id}`} className="block px-4 py-3.5">
            <div className="flex items-center justify-between"><p className="font-medium text-navy">{h.code}</p><StatusPill status={h.status} /></div>
            <p className="mt-0.5 text-xs text-muted">{s.allProjects.find((x) => x.id === h.projectId)?.name} · {personById(h.outgoingId)?.name?.split(' ')[0] ?? ''} → {personById(h.incomingId)?.name?.split(' ')[0] ?? ''}</p>
            <div className="mt-2 h-1.5 rounded-full bg-slate-100"><div className="h-full rounded-full bg-brand" style={{ width: `${h.progress}%` }} /></div>
          </LinkTo></li>
        ))}
      </ul>
    </>
  )
}

const STAGE_ORDER = ['draft', 'in_progress', 'pending_review', 'approved', 'published', 'completed']
export function StageDots({ status }: { status: string }) {
  const idx = STAGE_ORDER.indexOf(status)
  return (
    <span className="flex items-center gap-1" title={`Stage ${idx + 1} of 6`}>
      {STAGE_ORDER.map((st, i) => <span key={st} className={cn('h-1.5 w-4 rounded-full', i < idx ? 'bg-ok' : i === idx ? 'bg-brand' : 'bg-slate-200')} />)}
    </span>
  )
}
function StatusPill({ status }: { status: string }) {
  const map: Record<string, [Tone, string]> = { draft: ['gray', 'Draft'], in_progress: ['blue', 'In progress'], pending_review: ['amber', 'Pending review'], approved: ['indigo', 'Approved'], published: ['blue', 'Published'], completed: ['green', 'Completed'] }
  const [t, l] = map[status] ?? ['gray', status]
  return <Badge tone={t} dot>{l}</Badge>
}
