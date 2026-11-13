import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { AlertTriangle, ArrowLeft, ArrowRight, BookOpen, Bot, Check, CheckCircle2, ChevronRight, CircleAlert, Copy, Download, ExternalLink, FileDown, FileQuestion, FileText, History, Layers, Lightbulb, Link2, ListTodo, Lock, MessageSquare, MessageSquareText, Network, Pencil, Plus, Printer, Rocket, Send, Share2, ShieldCheck, ShieldX, Sparkles, ThumbsDown, ThumbsUp, UserRound, Users, X, Compass, Cpu } from 'lucide-react'
import { useStore } from '@/lib/store'
import { Link, navigate, useRoute } from '@/lib/router'
import { architecture, evidence, gaps, ME, personById, type Verification } from '@/lib/data'
import { Avatar, Badge, Button, Callout, Card, CardHeader, Checkbox, Confidence, EmptyState, Field, Input, Modal, Progress, Textarea, VerificationBadge, cn, VERIF, Tooltip } from '@/components/ui'
import { Logo } from '@/components/brand'
import { StackedBar, Ring } from '@/components/charts'
import { EvidenceCard, EvidenceChip, SeverityBadge, TaskStatus, allFindings, projectFindings, type AnyFinding } from '@/components/domain'
import { EvidenceTypeIcon } from '@/components/brand'
import { HandoverLayout, HandoverNotFound, handoverStats, useHandover } from './handovers'

/* ---------- 25. Review & Verification ---------- */
const ORDER: Verification[] = ['conflicting', 'insufficient', 'needs_review', 'rejected', 'verified']

export function Review({ id }: { id: string }) {
  return <HandoverLayout id={id} tab="review">{(h, role) => <ReviewBody hId={h.id} projectId={h.projectId} role={role} outgoingId={h.outgoingId} />}</HandoverLayout>
}

function ReviewBody({ hId, projectId, role, outgoingId }: { hId: string; projectId: string; role: string; outgoingId: string }) {
  const s = useStore()
  const { query } = useRoute()
  const all = useMemo(() => allFindings(projectId), [projectId])
  const status = (f: AnyFinding) => s.verif[f.id] ?? f.verification
  const sorted = [...all].sort((a, b) => ORDER.indexOf(status(a)) - ORDER.indexOf(status(b)) || a.confidence - b.confidence)
  const [filter, setFilter] = useState<'all' | Verification>('all')
  const [selId, setSelId] = useState(sorted[0]?.id)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [comment, setComment] = useState('')
  const [gapsOpen, setGapsOpen] = useState(query.get('gaps') === '1')
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const sel = all.find((f) => f.id === selId)
  const list = sorted.filter((f) => filter === 'all' || status(f) === filter)
  const counts = Object.fromEntries((Object.keys(VERIF) as Verification[]).map((v) => [v, all.filter((f) => status(f) === v).length])) as Record<Verification, number>
  const reviewed = all.length - counts.needs_review
  const projGaps = gaps.filter((g) => g.projectId === projectId)
  const openGaps = projGaps.filter((g) => !s.gapAnswers[g.id])
  const readOnly = role === 'incoming'
  useEffect(() => { setEditing(false); setComment('') }, [selId])
  if (!all.length) return <Card><EmptyState icon={Sparkles} title="No findings to review" body="Reconstruction hasn't produced findings for this project yet." /></Card>
  const act = (v: Verification) => {
    if (!sel) return
    s.setVerif((m) => ({ ...m, [sel.id]: v }))
    if (comment.trim()) s.setComments((m) => ({ ...m, [sel.id]: [...(m[sel.id] ?? []), { by: ME, text: comment, time: 'Just now' }] }))
    s.toast(`${VERIF[v].label}`, sel.title, v === 'verified' ? 'success' : 'info')
    const next = sorted.find((f) => f.id !== sel.id && status(f) === 'needs_review')
    if (next) setSelId(next.id)
    const h = s.handovers.find((x) => x.id === hId)
    if (h && h.status !== 'published' && h.status !== 'completed') s.updateHandover(hId, { progress: Math.min(95, Math.round(((reviewed + 1) / all.length) * 90)), updated: 'Just now' })
  }
  const st = sel ? status(sel) : 'needs_review'
  return (
    <>
      {readOnly && <div className="mb-4"><Callout tone="amber" icon={Lock}>Incoming members can see verification results but cannot verify findings.</Callout></div>}
      <Card className="mb-5 p-4 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
          <div className="flex-1">
            <div className="flex items-center justify-between text-[13px]"><span className="font-semibold text-navy">Review progress</span><span className="text-muted"><span className="font-semibold text-navy">{reviewed}</span> of {all.length} reviewed · {counts.verified} verified</span></div>
            <StackedBar className="mt-2.5" segments={[{ label: 'Verified', value: counts.verified, color: '#299B80' }, { label: 'Rejected', value: counts.rejected, color: '#E3A9AC' }, { label: 'Conflicting', value: counts.conflicting, color: '#D36D72' }, { label: 'Insufficient', value: counts.insufficient, color: '#A0AEC0' }, { label: 'Needs review', value: counts.needs_review, color: '#EBD5AC' }]} />
          </div>
          <Button variant={openGaps.length ? 'primary' : 'secondary'} icon={FileQuestion} onClick={() => setGapsOpen(true)}>Missing information {openGaps.length ? `(${openGaps.length})` : <Check className="size-3.5" />}</Button>
        </div>
        <div className="scrollbar-thin mt-4 flex gap-2 overflow-x-auto">
          {(['all', ...ORDER] as const).map((v) => <button key={v} onClick={() => setFilter(v)} className={cn('flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-[12.5px] font-medium', filter === v ? 'border-brand bg-tint text-brand' : 'border-line bg-white text-muted hover:text-navy')}>{v === 'all' ? 'All' : VERIF[v].label}<span className="text-slate-400">{v === 'all' ? all.length : counts[v]}</span></button>)}
        </div>
      </Card>
      <div className="grid gap-5 lg:grid-cols-[300px_1fr] 2xl:grid-cols-[300px_1fr_380px]">
        <Card className="h-fit overflow-hidden lg:sticky lg:top-0">
          <p className="border-b border-line px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Review queue · {list.length}</p>
          <ul className="scrollbar-thin max-h-[640px] overflow-y-auto">
            {list.map((f) => {
              const V = VERIF[status(f)]
              return (
                <li key={f.id}><button onClick={() => setSelId(f.id)} className={cn('flex w-full gap-3 border-b border-line/70 px-4 py-3 text-left transition', selId === f.id ? 'bg-tint/60' : 'hover:bg-slate-50')}>
                  <V.icon className={cn('mt-0.5 size-4 shrink-0', { green: 'text-ok', amber: 'text-warn', red: 'text-bad', gray: 'text-slate-400' }[V.tone as 'green'])} />
                  <span className="min-w-0 flex-1"><span className="line-clamp-2 text-[13px] font-medium text-navy">{f.title}</span><span className="mt-1 flex items-center gap-2 text-[11px] text-muted">{f.kind} · <Sparkles className="size-3 text-indigo-400" />{f.confidence}%</span></span>
                </button></li>
              )
            })}
            {!list.length && <li className="p-6 text-center text-[13px] text-muted">No findings in this state.</li>}
          </ul>
        </Card>
        {sel && (
          <div className="min-w-0 space-y-5">
            <Card className="p-5 sm:p-6">
              <div className="flex flex-wrap items-center gap-2"><Badge tone="indigo" icon={Sparkles}>AI-generated {sel.kind.toLowerCase()}</Badge><span className="text-xs text-muted">Attributed to {personById(sel.ownerId).name} · {sel.date}</span></div>
              <h2 className="mt-3 text-lg font-semibold leading-snug text-navy">{sel.title}</h2>
              {editing ? (
                <div className="mt-3"><Textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={4} autoFocus /><div className="mt-2 flex gap-2"><Button size="sm" onClick={() => { s.setEdits((m) => ({ ...m, [sel.id]: draft })); setEditing(false); s.toast('Finding edited', 'Your correction is recorded with the original AI text.') }}>Save correction</Button><Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button></div></div>
              ) : (
                <p className="mt-2 text-[14px] leading-relaxed text-slate-700">{s.edits[sel.id] ?? sel.summary}{s.edits[sel.id] && <Badge tone="blue" className="ml-2" icon={Pencil}>Edited by reviewer</Badge>}</p>
              )}
              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-dashed border-indigo-200 bg-indigo-50/40 p-4">
                  <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-indigo-500"><Sparkles className="size-3.5" />AI confidence</p>
                  <div className="mt-2 flex items-center gap-3"><span className="text-2xl font-semibold text-indigo-700">{sel.confidence}%</span><Confidence value={sel.confidence} /></div>
                  <p className="mt-2 text-xs leading-relaxed text-indigo-900/70">How strongly the model believes this, based on {sel.evidenceIds.length} source{sel.evidenceIds.length > 1 ? 's' : ''}. <span className="font-medium">Not a guarantee of correctness.</span></p>
                </div>
                <div className={cn('rounded-xl border p-4', st === 'verified' ? 'border-teal-200 bg-teal-50/40' : st === 'rejected' || st === 'conflicting' ? 'border-red-200 bg-red-50/30' : 'border-line bg-white')}>
                  <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500"><ShieldCheck className="size-3.5" />Human verification</p>
                  <div className="mt-2.5"><VerificationBadge status={st} /></div>
                  <p className="mt-2 text-xs leading-relaxed text-muted">{VERIF[st].hint}{st === 'verified' && ' Only verified findings count toward completeness.'}</p>
                </div>
              </div>
              {st === 'conflicting' && <div className="mt-4"><Callout tone="red" icon={AlertTriangle} title="Sources disagree">Compare the evidence on the right and decide which is current. Edit the finding if neither is fully correct.</Callout></div>}
              {st === 'insufficient' && <div className="mt-4"><Callout tone="amber" icon={CircleAlert} title="Not enough evidence">Only weak or single-mention evidence exists. Add details from your own knowledge, then verify.</Callout></div>}
              {!readOnly && (
                <div className="mt-5 border-t border-line pt-5">
                  <Field label="Reviewer comment (optional)"><Textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={2} placeholder="Explain your decision or add missing context…" /></Field>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button variant="success" icon={ShieldCheck} onClick={() => act('verified')}>Approve & verify</Button>
                    <Button variant="secondary" icon={Pencil} onClick={() => { setDraft(s.edits[sel.id] ?? sel.summary); setEditing(true) }}>Edit</Button>
                    <Button variant="secondary" icon={AlertTriangle} onClick={() => act('conflicting')}>Conflicting</Button>
                    <Button variant="secondary" icon={CircleAlert} onClick={() => act('insufficient')}>Insufficient</Button>
                    <Button variant="secondary" icon={ShieldX} className="text-red-600" onClick={() => act('rejected')}>Reject</Button>
                  </div>
                </div>
              )}
            </Card>
            <Card>
              <CardHeader title="Reviewer comments" icon={MessageSquare} />
              <div className="space-y-3 px-5 pb-5">
                {(s.comments[sel.id] ?? []).map((c, i) => <div key={i} className="flex gap-2.5"><Avatar id={c.by} size={26} /><div className="flex-1 rounded-xl bg-slate-50 px-3 py-2"><p className="text-xs font-medium text-navy">{personById(c.by).name} <span className="font-normal text-slate-400">· {c.time}</span></p><p className="text-[13px] text-slate-700">{c.text}</p></div></div>)}
                {!(s.comments[sel.id] ?? []).length && <p className="text-[13px] text-muted">No comments yet.</p>}
              </div>
            </Card>
            <div className="2xl:hidden"><EvidencePanel f={sel} /></div>
          </div>
        )}
        {sel && <div className="hidden 2xl:block"><EvidencePanel f={sel} /></div>}
      </div>
      <Modal open={gapsOpen} onClose={() => setGapsOpen(false)} size="lg" title="Complete missing information" subtitle="The AI found no evidence for these. Your answers are stored as human-provided evidence." footer={<><Button variant="secondary" onClick={() => setGapsOpen(false)}>Close</Button><Button disabled={readOnly} onClick={() => { s.setGapAnswers((m) => ({ ...m, ...Object.fromEntries(Object.entries(answers).filter(([, v]) => v.trim())) })); s.toast('Answers saved', 'They will appear in the report as outgoing-member statements.'); setGapsOpen(false) }}>Save answers</Button></>}>
        <div className="space-y-4">
          {projGaps.map((g) => (
            <div key={g.id} className="rounded-xl border border-line p-4">
              <div className="flex items-start justify-between gap-3"><p className="text-[13.5px] font-medium text-navy">{g.question}</p>{s.gapAnswers[g.id] && <Badge tone="green" icon={Check}>Answered</Badge>}</div>
              <p className="mt-0.5 text-xs text-muted">{g.context} · asked of {g.askedOf === outgoingId || g.askedOf === ME ? 'you' : personById(g.askedOf).name}</p>
              <Textarea className="mt-3" rows={2} disabled={readOnly} value={answers[g.id] ?? s.gapAnswers[g.id] ?? ''} onChange={(e) => setAnswers({ ...answers, [g.id]: e.target.value })} placeholder="Write the answer as you'd explain it to your successor…" />
            </div>
          ))}
          {!projGaps.length && <EmptyState icon={CheckCircle2} title="No knowledge gaps" body="Every topic has supporting evidence." />}
        </div>
      </Modal>
    </>
  )
}

function EvidencePanel({ f }: { f: AnyFinding }) {
  return (
    <Card className="h-fit">
      <CardHeader title="Supporting evidence" subtitle={`${f.evidenceIds.length} original sources`} icon={Link2} />
      <div className="space-y-3 px-5 pb-5">
        {f.evidenceIds.map((id) => {
          const e = evidence.find((x) => x.id === id)
          return (
            <div key={id}>
              <EvidenceCard id={id} />
              {e && <div className="mt-1.5 flex items-center justify-between px-1 text-[11px]"><span className="flex items-center gap-1 text-muted"><Sparkles className="size-3 text-indigo-400" />Used: “{e.extracted[0]}”</span><Link to={`/projects/${e.projectId}/evidence/${e.id}`} className="flex shrink-0 items-center gap-1 font-medium text-brand">Original<ExternalLink className="size-3" /></Link></div>}
            </div>
          )
        })}
      </div>
    </Card>
  )
}

/* ---------- 26. Report ---------- */
const SECTIONS = ['Project Overview', 'Role and Responsibilities', 'Completed Work', 'Ongoing Work', 'Pending Tasks', 'Technical Architecture', 'Important Decisions', 'Risks and Blockers', 'Dependencies', 'Important Contacts', 'Recommended Next Actions', 'Supporting Evidence']

export function Report({ id }: { id: string }) {
  const s = useStore()
  const [share, setShare] = useState(false)
  return (
    <HandoverLayout id={id} tab="report">
      {(h) => {
        const p = s.allProjects.find((x) => x.id === h.projectId)!
        const f = projectFindings(h.projectId)
        const v = (fid: string, def: Verification) => s.verif[fid] ?? def
        const Unv = ({ fid, def }: { fid: string; def: Verification }) => v(fid, def) !== 'verified' ? <span className="ml-1.5 inline-flex items-center rounded border border-amber-300 bg-amber-50 px-1 text-[10px] font-semibold uppercase text-amber-700">{VERIF[v(fid, def)].label}</span> : <ShieldCheck className="ml-1 inline size-3.5 text-ok" />
        const resp = s.members.find((m) => m.projectId === h.projectId && m.personId === h.outgoingId)?.responsibilities ?? []
        const contacts = s.members.filter((m) => m.projectId === h.projectId && m.personId !== h.outgoingId)
        const st = handoverStats(h, s.verif)
        const pubStatus = h.status === 'published' ? 'Published' : h.status === 'completed' ? 'Published · acknowledged' : h.status === 'approved' ? 'Approved · not yet published' : 'Draft · not published'
        const download = () => {
          const text = [`HANDOVER REPORT ${h.code}`, p.name, `${personById(h.outgoingId).name} -> ${personById(h.incomingId).name}`, '', 'DECISIONS', ...f.decisions.map((d) => `- ${d.title} [${VERIF[v(d.id, d.verification)].label}]`), '', 'TASKS', ...f.tasks.map((t) => `- ${t.title} (${t.status}, ${t.priority})`), '', 'RISKS', ...f.risks.map((r) => `- [${r.severity}] ${r.title}`)].join('\n')
          const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type: 'text/plain' })); a.download = `${h.code}-handover-report.txt`; a.click()
          s.toast('Report downloaded', `${h.code}-handover-report.txt`)
        }
        const sec = (n: number, children: ReactNode) => (
          <section id={`sec-${n}`} className="scroll-mt-4 border-t border-line pt-7 first:border-0 first:pt-0">
            <h2 className="mb-3 flex items-baseline gap-3 text-[17px] font-semibold text-navy"><span className="text-sm font-medium text-brand">{String(n).padStart(2, '0')}</span>{SECTIONS[n - 1]}</h2>
            <div className="text-[13.5px] leading-relaxed text-slate-700">{children}</div>
          </section>
        )
        return (
          <div className="grid gap-6 xl:grid-cols-[220px_1fr]">
            <div className="no-print hidden xl:block">
              <div className="sticky top-0 space-y-4">
                <Card className="p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Publication status</p>
                  <Badge tone={h.status === 'published' || h.status === 'completed' ? 'green' : h.status === 'approved' ? 'indigo' : 'gray'} dot className="mt-2">{pubStatus}</Badge>
                </Card>
                <nav className="space-y-0.5">{SECTIONS.map((x, i) => <a key={x} href={`#/handovers/${h.id}/report`} onClick={(e) => { e.preventDefault(); document.getElementById(`sec-${i + 1}`)?.scrollIntoView({ behavior: 'smooth' }) }} className="block rounded-lg px-3 py-1.5 text-[13px] text-muted hover:bg-white hover:text-navy">{i + 1}. {x}</a>)}</nav>
              </div>
            </div>
            <div>
              <div className="no-print mb-4 flex flex-wrap items-center gap-2">
                <Button icon={FileDown} onClick={() => { s.toast('Preparing PDF', 'Use “Save as PDF” in the print dialog.', 'info'); setTimeout(() => window.print(), 300) }}>Export PDF</Button>
                <Button variant="secondary" icon={Download} onClick={download}>Download</Button>
                <Button variant="secondary" icon={Share2} onClick={() => setShare(true)}>Share</Button>
                <Button variant="secondary" icon={Printer} onClick={() => window.print()}>Print</Button>
                <span className="ml-auto xl:hidden"><Badge tone="gray" dot>{pubStatus}</Badge></span>
              </div>
              <article className="mx-auto max-w-[860px] rounded-2xl border border-line bg-white px-6 py-8 shadow-card sm:px-12 sm:py-12">
                <header className="mb-8 border-b-2 border-navy pb-6">
                  <div className="flex items-center justify-between"><Logo size={24} /><span className="text-xs font-medium text-muted">{h.code} · Confidential</span></div>
                  <p className="mt-8 text-xs font-semibold uppercase tracking-[0.2em] text-brand">Handover Report</p>
                  <h1 className="mt-2 text-3xl font-semibold tracking-tight text-navy">{p.name}</h1>
                  <dl className="mt-6 grid grid-cols-2 gap-4 text-[13px] sm:grid-cols-4">
                    {[['Outgoing', personById(h.outgoingId).name], ['Incoming', personById(h.incomingId).name], ['Prepared', h.created], ['Verified', `${st.verified}/${st.all.length} findings`]].map(([k, val]) => <div key={k}><dt className="text-[11px] uppercase tracking-wide text-slate-400">{k}</dt><dd className="mt-0.5 font-medium text-navy">{val}</dd></div>)}
                  </dl>
                  <p className="mt-5 rounded-lg bg-slate-50 px-3 py-2 text-xs text-muted"><ShieldCheck className="mr-1 inline size-3.5 text-ok" />marks human-verified statements. Items tagged in amber were generated by AI and not confirmed by a person.</p>
                </header>
                <div className="space-y-7">
                  {sec(1, <p>{p.description} Scope of this handover: {h.scope}. Evidence was reconstructed from {s.sources.filter((x) => x.projectId === p.id && x.status !== 'disconnected').map((x) => x.name).join(', ')}.</p>)}
                  {sec(2, <><p>{personById(h.outgoingId).name} ({personById(h.outgoingId).title}) held the following responsibilities, which transfer to {personById(h.incomingId).name}:</p><ul className="mt-2 list-disc space-y-1 pl-5">{resp.map((r) => <li key={r}>{r}</li>)}</ul></>)}
                  {sec(3, <ul className="list-disc space-y-1 pl-5">{f.tasks.filter((t) => t.status === 'Done').map((t) => <li key={t.id}>{t.title} <Unv fid={t.id} def={t.verification} /></li>)}{f.decisions.filter((d) => v(d.id, d.verification) === 'verified').slice(0, 2).map((d) => <li key={d.id}>Implemented: {d.title} <Unv fid={d.id} def={d.verification} /></li>)}</ul>)}
                  {sec(4, <ul className="list-disc space-y-1 pl-5">{f.tasks.filter((t) => t.status === 'In progress').map((t) => <li key={t.id}><span className="font-medium text-navy">{t.title}</span>, {personById(t.ownerId).name}, due {t.due} <Unv fid={t.id} def={t.verification} /></li>)}</ul>)}
                  {sec(5, <table className="w-full text-[13px]"><thead><tr className="border-b border-line text-left text-xs text-muted"><th className="py-2 font-medium">Task</th><th className="font-medium">Priority</th><th className="font-medium">Status</th><th className="font-medium">Due</th></tr></thead><tbody>{f.tasks.filter((t) => t.status !== 'Done').map((t) => <tr key={t.id} className="border-b border-line/60"><td className="py-2 pr-3">{t.title}<Unv fid={t.id} def={t.verification} /></td><td>{t.priority}</td><td>{t.status}</td><td className="whitespace-nowrap">{t.due}</td></tr>)}</tbody></table>)}
                  {sec(6, <div className="space-y-2">{(architecture[p.id] ?? []).map((l) => <div key={l.layer} className="flex flex-wrap items-center gap-2 rounded-lg border border-line p-2.5"><span className="w-32 text-xs font-semibold text-muted">{l.layer}</span>{l.items.map((i) => <span key={i} className="rounded-md bg-tint px-2 py-0.5 text-xs font-medium text-navy">{i}</span>)}</div>)}{!architecture[p.id] && <p>No architecture recorded.</p>}</div>)}
                  {sec(7, <div className="space-y-4">{f.decisions.map((d) => <div key={d.id}><p className="font-semibold text-navy">{d.title}<Unv fid={d.id} def={d.verification} /></p><p className="mt-0.5">{d.reasoning}</p><p className="mt-1 text-xs text-muted">{personById(d.ownerId).name} · {d.date} · Evidence: {d.evidenceIds.map((e) => evidence.find((x) => x.id === e)?.ref).join('; ')}</p></div>)}</div>)}
                  {sec(8, <div className="space-y-3">{f.risks.map((r) => <div key={r.id} className="flex gap-3"><span className={cn('mt-1 h-auto w-1 shrink-0 rounded-full', { Critical: 'bg-bad', High: 'bg-warn', Medium: 'bg-sky', Low: 'bg-slate-300' }[r.severity])} /><div><p className="font-semibold text-navy">[{r.severity}] {r.title}<Unv fid={r.id} def={r.verification} /></p><p>Impact: {r.impact}. Mitigation: {r.mitigation.join('; ')}.</p></div></div>)}</div>)}
                  {sec(9, <ul className="list-disc space-y-1 pl-5">{f.dependencies.map((d) => <li key={d.id}>{d.from} → {d.to} ({d.depType}{d.blocking ? ', blocking' : ''})<Unv fid={d.id} def={d.verification} /></li>)}</ul>)}
                  {sec(10, <div className="grid gap-2 sm:grid-cols-2">{contacts.map((m) => <div key={m.personId} className="flex items-center gap-2.5 rounded-lg border border-line p-2.5"><Avatar id={m.personId} size={28} /><div><p className="text-[13px] font-medium text-navy">{personById(m.personId).name}</p><p className="text-xs text-muted">{m.responsibilities[0] ?? personById(m.personId).title} · {personById(m.personId).email}</p></div></div>)}</div>)}
                  {sec(11, <ol className="list-decimal space-y-1 pl-5">{f.tasks.filter((t) => t.status !== 'Done').sort((a, b) => ['Critical', 'High', 'Medium', 'Low'].indexOf(a.priority) - ['Critical', 'High', 'Medium', 'Low'].indexOf(b.priority)).slice(0, 3).map((t) => <li key={t.id}>{t.title} (before {t.due})</li>)}{f.risks.filter((r) => r.severity === 'Critical').map((r) => <li key={r.id}>Mitigate: {r.title}</li>)}{gaps.filter((g) => g.projectId === p.id).map((g) => <li key={g.id}>{s.gapAnswers[g.id] ? <>Outgoing member answered: “{s.gapAnswers[g.id]}”</> : <>Clarify with {personById(g.askedOf).name}: {g.question}</>}</li>)}</ol>)}
                  {sec(12, <div className="space-y-1.5">{f.evidence.map((e, i) => <p key={e.id} className="flex items-center gap-2 text-[12.5px]"><span className="w-6 text-right text-slate-400">[{i + 1}]</span><EvidenceTypeIcon type={e.type} className="size-5 [&_svg]:size-3" /><Link to={`/projects/${p.id}/evidence/${e.id}`} className="text-navy hover:text-brand">{e.title}</Link><span className="text-muted">· {e.ref}</span></p>)}</div>)}
                </div>
                <footer className="mt-10 border-t border-line pt-4 text-[11px] text-slate-400">Generated by Handover from authorised project sources. AI-generated content is marked; verify unmarked claims against linked evidence.</footer>
              </article>
              <Modal open={share} onClose={() => setShare(false)} title="Share report" subtitle="Only people with project access can open this link" footer={<Button onClick={() => setShare(false)}>Done</Button>}>
                <div className="flex gap-2"><Input readOnly value={`https://northwind.handover.app/r/${h.code.toLowerCase()}`} /><Button variant="secondary" icon={Copy} onClick={() => { navigator.clipboard?.writeText(`https://northwind.handover.app/r/${h.code.toLowerCase()}`); s.toast('Link copied') }}>Copy</Button></div>
                <p className="mb-2 mt-5 text-[13px] font-medium text-navy">People with access</p>
                <ul className="space-y-2">{[h.outgoingId, h.incomingId, 'maya'].filter((x, i, a) => a.indexOf(x) === i).map((pid) => <li key={pid} className="flex items-center gap-2.5"><Avatar id={pid} size={28} /><span className="flex-1 text-[13px] text-navy">{personById(pid).name}</span><span className="text-xs text-muted">{pid === h.incomingId ? 'Recipient' : pid === h.outgoingId ? 'Author' : 'Approver'}</span></li>)}</ul>
              </Modal>
            </div>
          </div>
        )
      }}
    </HandoverLayout>
  )
}

/* ---------- 29. Incoming member workspace ---------- */
const R_SECTIONS = [
  { id: 'intro', label: 'Project introduction', icon: Compass },
  { id: 'arch', label: 'Architecture', icon: Layers },
  { id: 'tech', label: 'Technical knowledge', icon: Cpu },
  { id: 'resp', label: 'Your responsibilities', icon: UserRound },
  { id: 'tasks', label: 'Pending tasks', icon: ListTodo },
  { id: 'risks', label: 'Risks', icon: AlertTriangle },
  { id: 'deps', label: 'Dependencies', icon: Network },
  { id: 'first', label: 'Recommended first steps', icon: Rocket },
] as const

export function RecipientWorkspace({ id }: { id: string }) {
  const s = useStore()
  const { h, project, role } = useHandover(id)
  const [cur, setCur] = useState(0)
  const [seen, setSeen] = useState<number[]>([0])
  const [ack, setAck] = useState(false)
  const [confirmRead, setConfirmRead] = useState(false)
  const [ackNote, setAckNote] = useState('')
  if (!h || !project) return <HandoverNotFound />
  if (h.status !== 'published' && h.status !== 'completed') return <Card><EmptyState icon={Lock} title="Not published yet" body={`This handover is ${h.status.replace('_', ' ')}. The recipient view becomes available once a manager publishes it.`} action={<Button onClick={() => navigate(`/handovers/${h.id}`)}>Back to workspace</Button>} /></Card>
  const f = projectFindings(h.projectId)
  const out = personById(h.outgoingId)
  const resp = s.members.find((m) => m.projectId === h.projectId && m.personId === h.outgoingId)?.responsibilities ?? []
  const go = (i: number) => { setCur(i); setSeen((x) => (x.includes(i) ? x : [...x, i])); document.getElementById('main-scroll')?.scrollTo({ top: 0, behavior: 'smooth' }) }
  const pct = Math.round((seen.length / R_SECTIONS.length) * 100)
  const done = h.status === 'completed'
  const verified = (fid: string, def: Verification) => (s.verif[fid] ?? def) === 'verified'
  const VTag = ({ fid, def }: { fid: string; def: Verification }) => verified(fid, def) ? <Tooltip content="Verified by a person"><ShieldCheck className="size-4 shrink-0 text-ok" /></Tooltip> : <Badge tone="amber">Unverified</Badge>
  const content: ReactNode[] = [
    <div key="intro" className="space-y-5">
      <p className="text-[15px] leading-relaxed text-slate-700">{project.description}</p>
      <div className="rounded-xl border border-line bg-slate-50/60 p-4"><p className="text-[13px] font-semibold text-navy">A note from {out.name.split(' ')[0]}</p><p className="mt-1 text-[13.5px] italic leading-relaxed text-slate-700">“Most of what you need is in the decisions and risks sections. Start with the month-end slot issue since finance depends on it. Omar knows the dbt side better than anyone; lean on him.”</p></div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{[['Decisions', f.decisions.length], ['Open tasks', f.tasks.filter((t) => t.status !== 'Done').length], ['Risks', f.risks.length], ['Evidence', f.evidence.length]].map(([l, v]) => <div key={l as string} className="rounded-xl border border-line p-3"><p className="text-xl font-semibold text-navy">{v}</p><p className="text-xs text-muted">{l}</p></div>)}</div>
      <div><p className="mb-2 text-[13px] font-semibold text-navy">Key people</p><div className="flex flex-wrap gap-2">{s.members.filter((m) => m.projectId === h.projectId && m.personId !== ME).map((m) => <span key={m.personId} className="flex items-center gap-2 rounded-full border border-line py-1 pl-1 pr-3 text-[13px]"><Avatar id={m.personId} size={24} />{personById(m.personId).name}<span className="text-xs text-muted">· {m.responsibilities[0]}</span></span>)}</div></div>
    </div>,
    <div key="arch">
      <p className="mb-4 text-[13.5px] text-muted">How the system fits together, top to bottom. Data flows downward.</p>
      <div className="space-y-2">{(architecture[project.id] ?? []).map((l, i, arr) => <div key={l.layer}><div className="flex flex-col gap-2 rounded-xl border border-line bg-white p-3 sm:flex-row sm:items-center"><span className="w-36 shrink-0 text-xs font-semibold uppercase tracking-wide text-muted">{l.layer}</span><div className="flex flex-wrap gap-2">{l.items.map((it) => <span key={it} className="rounded-lg border border-[#D9E1F0] bg-tint px-2.5 py-1 text-[13px] font-medium text-navy">{it}</span>)}</div></div>{i < arr.length - 1 && <div className="ml-[72px] h-3 w-px bg-slate-300" />}</div>)}</div>
    </div>,
    <div key="tech" className="space-y-3">{f.decisions.map((d) => <div key={d.id} className="rounded-xl border border-line p-4"><div className="flex items-start justify-between gap-3"><p className="text-[14px] font-semibold text-navy">{d.title}</p><VTag fid={d.id} def={d.verification} /></div><p className="mt-1.5 text-[13.5px] leading-relaxed text-slate-700"><span className="font-medium text-navy">Why: </span>{d.reasoning}</p><div className="mt-3 flex flex-wrap gap-1.5">{d.evidenceIds.map((e) => <EvidenceChip key={e} id={e} />)}</div></div>)}</div>,
    <div key="resp" className="space-y-2">{resp.map((r) => <div key={r} className="flex items-center gap-3 rounded-xl border border-line p-4"><span className="flex size-9 items-center justify-center rounded-lg bg-teal-50 text-ok"><CheckCircle2 className="size-4" /></span><div className="flex-1"><p className="text-[14px] font-medium text-navy">{r}</p><p className="text-xs text-muted">Previously owned by {out.name}</p></div></div>)}</div>,
    <div key="tasks" className="space-y-2">{f.tasks.filter((t) => t.status !== 'Done').map((t) => <div key={t.id} className="flex flex-col gap-2 rounded-xl border border-line p-4 sm:flex-row sm:items-center"><div className="flex-1"><p className="text-[14px] font-medium text-navy">{t.title}</p><p className="text-xs text-muted">{t.summary}</p></div><div className="flex items-center gap-2"><Badge tone={t.priority === 'Critical' ? 'red' : t.priority === 'High' ? 'amber' : 'blue'}>{t.priority}</Badge><TaskStatus status={t.status} /><span className="text-xs text-muted">Due {t.due}</span></div></div>)}</div>,
    <div key="risks" className="space-y-2">{f.risks.map((r) => <div key={r.id} className="rounded-xl border border-line p-4"><div className="flex flex-wrap items-center gap-2"><SeverityBadge level={r.severity} /><VTag fid={r.id} def={r.verification} /></div><p className="mt-2 text-[14px] font-medium text-navy">{r.title}</p><p className="mt-1 text-[13px] text-muted">{r.impact}</p><p className="mt-2 text-[13px] text-slate-700"><span className="font-medium">What to do: </span>{r.mitigation[0]}</p></div>)}</div>,
    <div key="deps" className="space-y-2">{f.dependencies.map((d) => <div key={d.id} className="flex items-center gap-3 rounded-xl border border-line p-4"><Badge tone={d.depType === 'External' ? 'amber' : d.depType === 'Task' ? 'green' : 'blue'}>{d.depType}</Badge><span className="flex-1 text-[13.5px] text-navy">{d.from} <ArrowRight className="inline size-3.5 text-slate-400" /> {d.to}</span><Avatar id={d.ownerId} size={24} /></div>)}</div>,
    <div key="first" className="space-y-3">
      {[['Get access', 'Request write access to the repositories and join the on-call rotation.'], ['Read the top two decisions', 'They explain most of the current architecture.'], [`Pick up “${f.tasks.find((t) => t.status !== 'Done')?.title ?? 'open work'}”`, 'Highest-priority work in your new area.'], ['Book 30 minutes with ' + out.name.split(' ')[0], 'Use the open questions the assistant could not answer.']].map(([t, d], i) => <div key={i} className="flex gap-3 rounded-xl border border-line p-4"><span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-brand text-xs font-semibold text-white">{i + 1}</span><div><p className="text-[14px] font-medium text-navy">{t}</p><p className="text-[13px] text-muted">{d}</p></div></div>)}
      <div className="grid gap-3 sm:grid-cols-2"><button onClick={() => navigate(`/projects/${h.projectId}/knowledge`)} className="flex items-center gap-3 rounded-xl border border-line p-4 text-left hover:border-brand/40"><Network className="size-5 text-brand" /><span><span className="block text-[13.5px] font-medium text-navy">Explore knowledge graph</span><span className="text-xs text-muted">See how everything connects</span></span></button><button onClick={() => navigate(`/handovers/${h.id}/assistant`)} className="flex items-center gap-3 rounded-xl border border-line p-4 text-left hover:border-brand/40"><MessageSquareText className="size-5 text-brand" /><span><span className="block text-[13.5px] font-medium text-navy">Ask the assistant</span><span className="text-xs text-muted">Answers cite verified evidence</span></span></button></div>
    </div>,
  ]
  const S = R_SECTIONS[cur]
  return (
    <>
      {role !== 'incoming' && <div className="mb-4"><Callout tone="blue" icon={UserRound}>You're previewing what {personById(h.incomingId).name} sees.</Callout></div>}
      <div className="relative mb-6 overflow-hidden rounded-2xl border border-line bg-white p-6 shadow-card sm:p-8">
        <div className="absolute inset-y-0 right-0 hidden w-1/2 opacity-70 sm:block" style={{ background: 'radial-gradient(circle at 85% 30%, #EDF2FA 0, transparent 55%)' }} />
        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2"><Badge tone="green" icon={BookOpen}>Your handover</Badge><span className="text-xs text-muted">{h.code} · published {h.publishedOn}</span></div>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight text-navy sm:text-[28px]">Welcome to {project.name}</h1>
            <p className="mt-1.5 text-sm text-muted">{out.name} prepared this for you. It covers {h.scope.toLowerCase()}.</p>
          </div>
          <div className="flex items-center gap-4">
            <Ring value={done ? 100 : pct} size={64} color={done ? '#299B80' : '#315FBA'} />
            {done ? <Badge tone="green" icon={CheckCircle2}>Acknowledged {h.acknowledgedOn}</Badge> : <Button icon={Check} onClick={() => setAck(true)} disabled={role !== 'incoming'}>Acknowledge handover</Button>}
          </div>
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <nav className="h-fit lg:sticky lg:top-0">
          <p className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">Your onboarding path</p>
          <ol className="scrollbar-thin flex gap-1 overflow-x-auto lg:flex-col">
            {R_SECTIONS.map((x, i) => (
              <li key={x.id} className="shrink-0"><button onClick={() => go(i)} className={cn('flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition', cur === i ? 'bg-white shadow-card' : 'hover:bg-white/60')}>
                <span className={cn('flex size-7 items-center justify-center rounded-lg', seen.includes(i) && cur !== i ? 'bg-teal-50 text-ok' : cur === i ? 'bg-brand text-white' : 'bg-slate-100 text-slate-400')}>{seen.includes(i) && cur !== i ? <Check className="size-3.5" /> : <x.icon className="size-3.5" />}</span>
                <span className={cn('text-[13px] font-medium', cur === i ? 'text-navy' : 'text-muted')}>{x.label}</span>
              </button></li>
            ))}
          </ol>
        </nav>
        <Card key={cur} className="animate-fade p-5 sm:p-8">
          <p className="text-xs font-medium text-brand">Section {cur + 1} of {R_SECTIONS.length}</p>
          <h2 className="mb-5 mt-1 flex items-center gap-2.5 text-xl font-semibold text-navy"><S.icon className="size-5 text-brand" />{S.label}</h2>
          {content[cur]}
          <div className="mt-8 flex justify-between border-t border-line pt-5">
            <Button variant="ghost" icon={ArrowLeft} disabled={cur === 0} onClick={() => go(cur - 1)}>Previous</Button>
            {cur < R_SECTIONS.length - 1 ? <Button iconRight={ArrowRight} onClick={() => go(cur + 1)}>Next: {R_SECTIONS[cur + 1].label}</Button> : !done && role === 'incoming' ? <Button icon={Check} onClick={() => setAck(true)}>Acknowledge handover</Button> : <Button variant="secondary" icon={MessageSquareText} onClick={() => navigate(`/handovers/${h.id}/assistant`)}>Ask the assistant</Button>}
          </div>
        </Card>
      </div>
      <Modal open={ack} onClose={() => setAck(false)} title="Acknowledge handover" subtitle={`Confirm you've received ${h.code}`} footer={<><Button variant="secondary" onClick={() => setAck(false)}>Not yet</Button><Button disabled={!confirmRead} icon={Check} onClick={() => { s.updateHandover(h.id, { status: 'completed', acknowledgedOn: 'Jun 18, 2025', updated: 'Just now' }); s.setNotifications((ns) => ns.map((n) => (n.id === 'n1' ? { ...n, read: true } : n))); s.toast('Handover acknowledged', `${out.name} and the project manager have been notified.`); setAck(false) }}>Acknowledge</Button></>}>
        <div className="space-y-4">
          <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-3"><Progress value={pct} className="flex-1" /><span className="text-xs text-muted">{seen.length}/{R_SECTIONS.length} sections viewed</span></div>
          {pct < 100 && <Callout tone="amber" icon={CircleAlert}>You haven't viewed every section. You can still acknowledge and come back later.</Callout>}
          <Checkbox checked={confirmRead} onChange={setConfirmRead} label="I've reviewed this handover and understand my new responsibilities" description="Acknowledging doesn't close the handover. You keep access to all knowledge and the assistant." />
          <Field label={`Open questions for ${out.name.split(' ')[0]} (optional)`}><Textarea value={ackNote} onChange={(e) => setAckNote(e.target.value)} placeholder="Anything you'd like clarified in a follow-up call…" /></Field>
        </div>
      </Modal>
    </>
  )
}

/* ---------- 30. AI assistant ---------- */
interface Msg { role: 'user' | 'ai'; text: string; cites?: string[]; findings?: AnyFinding[]; grounded?: 'verified' | 'partial' | 'none' }
const SUGGESTED = ['Why was this architecture selected?', 'Which tasks remain incomplete?', 'What issues were left unresolved?', 'Who is responsible for deployment?', 'What should I work on first?']

function answer(q: string, pid: string, verif: Record<string, Verification>): Msg {
  const f = projectFindings(pid)
  const all = allFindings(pid)
  const ql = q.toLowerCase()
  const isV = (x: AnyFinding) => (verif[x.id] ?? x.verification) === 'verified'
  if (ql.includes('architecture') || ql.includes('why')) {
    const d = f.decisions[0]
    if (d) return { role: 'ai', text: `The current architecture is shaped mainly by the decision to **${d.title.toLowerCase()}**. ${d.reasoning}${f.decisions[1] ? ` A related decision, “${f.decisions[1].title}”, followed: ${f.decisions[1].reasoning}` : ''}`, cites: [...d.evidenceIds, ...(f.decisions[1]?.evidenceIds ?? [])].slice(0, 4), findings: [{ ...d, kind: 'Decision' }, ...(f.decisions[1] ? [{ ...f.decisions[1], kind: 'Decision' as const }] : [])], grounded: isV({ ...d, kind: 'Decision' }) ? 'verified' : 'partial' }
  }
  if (ql.includes('task') || ql.includes('incomplete')) {
    const open = f.tasks.filter((t) => t.status !== 'Done')
    return { role: 'ai', text: `${open.length} tasks remain incomplete:\n${open.map((t) => `• **${t.title}** (${t.status.toLowerCase()}, ${t.priority} priority, due ${t.due}, owner ${personById(t.ownerId).name})`).join('\n')}`, cites: open.flatMap((t) => t.evidenceIds).slice(0, 5), findings: open.slice(0, 3).map((t) => ({ ...t, kind: 'Task' as const })), grounded: open.every((t) => isV({ ...t, kind: 'Task' })) ? 'verified' : 'partial' }
  }
  if (ql.includes('unresolved') || ql.includes('issue') || ql.includes('risk')) {
    const r = f.risks.filter((x) => x.resolution !== 'Resolved')
    return { role: 'ai', text: `These issues are still open:\n${r.map((x) => `• **[${x.severity}] ${x.title}**: ${x.impact}.`).join('\n')}${all.some((x) => (verif[x.id] ?? x.verification) === 'conflicting') ? '\n\nNote: some related findings have conflicting evidence and haven’t been resolved by a reviewer.' : ''}`, cites: r.flatMap((x) => x.evidenceIds).slice(0, 5), findings: r.slice(0, 3).map((x) => ({ ...x, kind: 'Risk' as const })), grounded: 'partial' }
  }
  if (ql.includes('deploy') || ql.includes('responsible')) {
    const ev = evidence.find((e) => e.projectId === pid && /deploy|release|rollout/i.test(e.content))
    if (ev) return { role: 'ai', text: `According to **${ev.title}**: ${ev.extracted.find((x) => /deploy|release|rollout/i.test(x)) ?? ev.extracted[0]}. No single named owner is recorded, so confirm who covers this with your manager.`, cites: [ev.id], grounded: ev.verification === 'verified' ? 'verified' : 'partial' }
    return { role: 'ai', text: 'I couldn’t find verified evidence naming a deployment owner for this project. I won’t guess. This has been logged as a knowledge gap; ask the outgoing member directly.', grounded: 'none' }
  }
  if (ql.includes('first') || ql.includes('start') || ql.includes('priority')) {
    const order = ['Critical', 'High', 'Medium', 'Low']
    const t = [...f.tasks].filter((x) => x.status !== 'Done').sort((a, b) => order.indexOf(a.priority) - order.indexOf(b.priority))[0]
    const r = f.risks.find((x) => x.severity === 'Critical' || x.severity === 'High')
    return { role: 'ai', text: `I'd start with **${t?.title ?? 'reviewing open tasks'}**. It's ${t?.priority.toLowerCase()} priority and due ${t?.due}.${r ? ` In parallel, get familiar with the risk “${r.title}”, since ${r.impact.toLowerCase()}.` : ''}`, cites: [...(t?.evidenceIds ?? []), ...(r?.evidenceIds ?? [])].slice(0, 4), findings: [t && { ...t, kind: 'Task' as const }, r && { ...r, kind: 'Risk' as const }].filter(Boolean) as AnyFinding[], grounded: 'partial' }
  }
  const words = ql.split(/\W+/).filter((w) => w.length > 3)
  const hits = all.map((x) => ({ x, score: words.filter((w) => (x.title + ' ' + x.summary).toLowerCase().includes(w)).length })).filter((h) => h.score > 0).sort((a, b) => b.score - a.score).slice(0, 2)
  if (hits.length) return { role: 'ai', text: hits.map(({ x }) => `**${x.title}**: ${x.summary}`).join('\n\n'), cites: hits.flatMap(({ x }) => x.evidenceIds).slice(0, 4), findings: hits.map(({ x }) => x), grounded: hits.every(({ x }) => isV(x)) ? 'verified' : 'partial' }
  return { role: 'ai', text: 'I couldn’t find evidence in this handover that answers that. I only answer from the project’s authorised, linked evidence. Try rephrasing, or send the question to the outgoing member.', grounded: 'none' }
}

function RichText({ text }: { text: string }) {
  return <>{text.split('\n').map((line, i) => <p key={i} className={line.startsWith('•') ? 'pl-1' : i ? 'mt-2' : ''}>{line.split(/(\*\*[^*]+\*\*)/).map((part, j) => part.startsWith('**') ? <strong key={j} className="font-semibold text-navy">{part.slice(2, -2)}</strong> : part)}</p>)}</>
}

export function Assistant({ id }: { id: string }) {
  const s = useStore()
  const { h, project } = useHandover(id)
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [typing, setTyping] = useState(false)
  const [conv, setConv] = useState('current')
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, typing])
  if (!h || !project) return <HandoverNotFound />
  const ask = (q: string) => {
    if (!q.trim() || typing) return
    setMsgs((m) => [...m, { role: 'user', text: q }])
    setInput('')
    setTyping(true)
    setTimeout(() => { setMsgs((m) => [...m, answer(q, h.projectId, s.verif)]); setTyping(false) }, 950)
  }
  const last = [...msgs].reverse().find((m) => m.role === 'ai')
  const history = [{ id: 'current', title: msgs[0]?.text ?? 'New conversation', when: 'Now' }, { id: 'c2', title: 'How does the slot reservation alert work?', when: 'Yesterday' }, { id: 'c3', title: 'Who owns dbt incremental models?', when: 'Jun 16' }]
  return (
    <>
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link to={h.status === 'published' || h.status === 'completed' ? `/handovers/${h.id}/recipient` : `/handovers/${h.id}`} className="mb-2 inline-flex items-center gap-1.5 text-[13px] font-medium text-muted hover:text-navy"><ArrowLeft className="size-4" />{h.code} · {project.name}</Link>
          <h1 className="flex items-center gap-2.5 text-[22px] font-semibold tracking-tight text-navy">Handover Assistant <Badge tone="indigo" icon={ShieldCheck}>Evidence-grounded</Badge></h1>
          <p className="mt-1 text-sm text-muted">Answers come only from this handover's linked evidence, with citations. It never invents facts.</p>
        </div>
      </div>
      <div className="grid h-[calc(100dvh-260px)] min-h-[520px] gap-5 lg:grid-cols-[240px_1fr] xl:grid-cols-[240px_1fr_320px]">
        <Card className="hidden flex-col overflow-hidden lg:flex">
          <div className="border-b border-line p-3"><Button variant="secondary" className="w-full" icon={Plus} onClick={() => { setMsgs([]); setConv('current') }}>New conversation</Button></div>
          <p className="px-4 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400">History</p>
          <ul className="flex-1 space-y-0.5 overflow-y-auto px-2">{history.map((c) => <li key={c.id}><button onClick={() => setConv(c.id)} className={cn('w-full rounded-lg px-2.5 py-2 text-left', conv === c.id ? 'bg-tint' : 'hover:bg-slate-50')}><span className="line-clamp-1 text-[13px] font-medium text-navy">{c.title}</span><span className="text-[11px] text-muted">{c.when}</span></button></li>)}</ul>
        </Card>
        <Card className="flex min-h-0 flex-col overflow-hidden">
          <div className="scrollbar-thin flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
            {conv !== 'current' ? <EmptyState icon={History} title="Past conversation" body="Archived conversations are read-only in this prototype. Start a new one to ask questions." action={<Button variant="secondary" onClick={() => setConv('current')}>Back to current</Button>} /> : !msgs.length ? (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <span className="flex size-12 items-center justify-center rounded-2xl bg-tint text-brand"><Sparkles className="size-5" /></span>
                <p className="mt-4 text-base font-semibold text-navy">Ask about {project.name}</p>
                <p className="mt-1 max-w-sm text-[13px] text-muted">Every answer links to the commits, issues, threads and documents it's based on.</p>
                <div className="mt-6 flex max-w-lg flex-wrap justify-center gap-2">{SUGGESTED.map((q) => <button key={q} onClick={() => ask(q)} className="rounded-full border border-line bg-white px-3 py-1.5 text-[13px] text-navy hover:border-brand/40 hover:bg-tint/40">{q}</button>)}</div>
              </div>
            ) : msgs.map((m, i) => m.role === 'user' ? (
              <div key={i} className="flex justify-end"><div className="max-w-[80%] rounded-2xl rounded-br-md bg-brand px-4 py-2.5 text-[13.5px] text-white">{m.text}</div></div>
            ) : (
              <div key={i} className="flex gap-3">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-tint text-brand"><Bot className="size-4" /></span>
                <div className="min-w-0 max-w-[88%] flex-1">
                  <div className="rounded-2xl rounded-tl-md border border-line bg-white px-4 py-3 text-[13.5px] leading-relaxed text-slate-700"><RichText text={m.text} />
                    {m.cites && !!m.cites.length && <div className="mt-3 flex flex-wrap gap-1.5 border-t border-line pt-3">{m.cites.map((c, ci) => <span key={c} className="flex items-center gap-1"><span className="text-[11px] font-semibold text-brand">[{ci + 1}]</span><EvidenceChip id={c} /></span>)}</div>}
                  </div>
                  <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[11px]">
                    {m.grounded === 'verified' && <Badge tone="green" icon={ShieldCheck}>Based on verified findings</Badge>}
                    {m.grounded === 'partial' && <Badge tone="amber" icon={CircleAlert}>Includes unverified findings</Badge>}
                    {m.grounded === 'none' && <Badge tone="gray" icon={FileQuestion}>No supporting evidence</Badge>}
                    {m.grounded === 'none' && <button className="font-medium text-brand" onClick={() => s.toast(`Question sent to ${personById(h.outgoingId).name}`, undefined, 'info')}>Ask {personById(h.outgoingId).name.split(' ')[0]} →</button>}
                    <span className="ml-auto flex gap-1"><button className="rounded p-1 text-slate-400 hover:text-navy" aria-label="Helpful" onClick={() => s.toast('Thanks for the feedback')}><ThumbsUp className="size-3.5" /></button><button className="rounded p-1 text-slate-400 hover:text-navy" aria-label="Not helpful" onClick={() => s.toast('Feedback recorded', 'A reviewer will look at this answer.', 'info')}><ThumbsDown className="size-3.5" /></button></span>
                  </div>
                </div>
              </div>
            ))}
            {typing && <div className="flex gap-3"><span className="flex size-8 items-center justify-center rounded-full bg-tint text-brand"><Bot className="size-4" /></span><div className="flex items-center gap-1 rounded-2xl border border-line bg-white px-4 py-3">{[0, 1, 2].map((d) => <span key={d} className="size-1.5 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: `${d * 0.15}s` }} />)}<span className="ml-2 text-xs text-muted">Searching evidence…</span></div></div>}
            <div ref={end} />
          </div>
          {conv === 'current' && (
            <div className="border-t border-line p-3">
              {!!msgs.length && <div className="scrollbar-thin mb-2 flex gap-1.5 overflow-x-auto">{SUGGESTED.filter((q) => !msgs.some((m) => m.text === q)).map((q) => <button key={q} onClick={() => ask(q)} className="shrink-0 rounded-full border border-line px-2.5 py-1 text-xs text-muted hover:text-navy">{q}</button>)}</div>}
              <form onSubmit={(e) => { e.preventDefault(); ask(input) }} className="flex items-end gap-2">
                <Textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(input) } }} rows={1} placeholder="Ask a question about this handover…" className="min-h-[42px] resize-none" />
                <Button type="submit" icon={Send} disabled={!input.trim() || typing} className="h-[42px]" aria-label="Send" />
              </form>
              <p className="mt-1.5 text-[11px] text-slate-400">Answers may include unverified findings; these are always labelled.</p>
            </div>
          )}
        </Card>
        <Card className="hidden overflow-y-auto xl:block">
          <CardHeader title="Sources in this answer" icon={Link2} />
          <div className="space-y-2 px-5 pb-4">{last?.cites?.length ? last.cites.map((c) => <EvidenceCard key={c} id={c} compact />) : <p className="text-[13px] text-muted">Citations for the latest answer appear here.</p>}</div>
          <CardHeader title="Related findings" icon={Sparkles} className="border-t border-line" />
          <ul className="space-y-2 px-5 pb-5">{last?.findings?.length ? last.findings.map((x) => <li key={x.id} className="rounded-xl border border-line p-3"><p className="text-[13px] font-medium text-navy">{x.title}</p><div className="mt-2 flex flex-wrap gap-1.5"><Badge tone="indigo">{x.kind}</Badge><VerificationBadge status={s.verif[x.id] ?? x.verification} /></div></li>) : <li className="text-[13px] text-muted">None yet.</li>}</ul>
        </Card>
      </div>
    </>
  )
}
