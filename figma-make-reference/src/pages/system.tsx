import { useEffect, useState } from 'react'
import { AlertTriangle, ArrowRight, Bell, Check, ChevronRight, Download, FileSearch, FolderKanban, Inbox, Layers, Pause, Play, Plus, RotateCcw, Search, Settings, ShieldCheck, Sparkles, Trash2, Users, Workflow, BrainCircuit, Database, Network, Monitor, Tablet, Smartphone, MousePointerClick, Lock, Film, Presentation, Megaphone } from 'lucide-react'
import { Logo, LogoMark, SourceIcon } from '@/components/brand'
import { Mono, Avatar, AvatarGroup, Badge, Button, Callout, Card, CardHeader, Checkbox, Confidence, ConfirmDialog, Dropdown, EmptyState, ErrorState, Field, IconButton, Input, MenuItem, Modal, PageHeader, Pagination, PasswordInput, Progress, Radio, ReconstructionLoader, SearchInput, Segmented, Select, Skeleton, SphereVisual, StatusBadge, Switch, Table, Tabs, Td, Th, Tooltip, VerificationBadge, cn } from '@/components/ui'
import { Donut, Legend, LineChart, BarChart } from '@/components/charts'
import { RoleBadge } from '@/components/Shell'
import { useStore } from '@/lib/store'
import { Link, navigate } from '@/lib/router'
import { activityTrend } from '@/lib/data'
import type { EmptyKind } from '@/components/OrganicScene'

const COLORS = [['Canvas', '#F6F8FC', 'App background'], ['Surface', '#FFFFFF', 'Cards, panels'], ['Sidebar', '#EDF2FA', 'Navigation, tints'], ['Primary Blue', '#315FBA', 'Interaction, selection'], ['Deep Navy', '#203653', 'Text, brand'], ['Muted Blue', '#7997BE', 'Secondary accents'], ['Soft Indigo', '#A5A0D9', 'AI visualisation'], ['Soft Teal', '#D9E9E5', 'Verified surfaces'], ['Border', '#D9E1F0', 'Dividers, inputs'], ['Secondary Text', '#718096', 'Metadata'], ['Verified', '#299B80', 'Success, verified'], ['Pending', '#D39B43', 'Warning, uncertain'], ['Critical', '#D36D72', 'Errors, critical'], ['AI Intelligence', '#8B78C9', 'AI confidence only']]
const SECTIONS = ['Brand identity', 'Colours', 'Typography', 'Spacing & grid', 'Radius & elevation', 'Icons', 'Buttons', 'Form controls', 'Navigation', 'Status indicators', 'Data display', 'Feedback', 'Overlays', 'Charts', 'Responsive', 'Motion', 'Layout rules', '3D sphere system']

function Sec({ id, title, desc, children }: { id: number; title: string; desc?: string; children: React.ReactNode }) {
  return (
    <section id={`ds-${id}`} className="scroll-mt-4">
      <div className="mb-4 flex items-baseline gap-3"><span className="text-xs font-semibold text-brand">{String(id + 1).padStart(2, '0')}</span><div><h2 className="text-lg font-semibold text-navy">{title}</h2>{desc && <p className="text-[13px] text-muted">{desc}</p>}</div></div>
      {children}
    </section>
  )
}

export function DesignSystem() {
  const s = useStore()
  const [tab, setTab] = useState('overview')
  const [seg, setSeg] = useState('a')
  const [chk, setChk] = useState(true)
  const [radio, setRadio] = useState(1)
  const [sw, setSw] = useState(true)
  const [modal, setModal] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const [page, setPage] = useState(2)
  return (
    <>
      <PageHeader eyebrow={<Badge tone="blue">04 · Design System 2.0</Badge>} title="Handover Design System 2.0" subtitle="One identity, two personalities: an expressive public website and a calm, information-rich application. Every screen is built from these tokens and components." actions={<><Button variant="secondary" icon={Sparkles} onClick={() => navigate('/brand')}>3D Brand & Launch Studio</Button><Button variant="secondary" iconRight={ArrowRight} onClick={() => navigate('/')}>View public website</Button></>} />
      <div className="grid gap-8 xl:grid-cols-[200px_1fr]">
        <nav className="hidden xl:block"><div className="sticky top-0 space-y-0.5">{SECTIONS.map((x, i) => <a key={x} href="#/design-system" onClick={(e) => { e.preventDefault(); document.getElementById(`ds-${i}`)?.scrollIntoView({ behavior: 'smooth' }) }} className="block rounded-lg px-3 py-1.5 text-[13px] text-muted hover:bg-white hover:text-navy">{x}</a>)}</div></nav>
        <div className="min-w-0 space-y-12">
          <Sec id={0} title="Brand identity" desc="Two interlocking pathways. The outgoing link (navy) and the incoming link (blue) pass through each other: two sides coming together, knowledge continuing.">
            <div className="grid gap-4 md:grid-cols-3">
              <Card className="flex flex-col items-center justify-center gap-3 p-8 md:col-span-2"><Logo size={64} /><p className="text-xs text-muted">Primary lockup · sidebar, login, website header</p></Card>
              <Card className="flex flex-col items-center justify-center gap-3 bg-navy p-8"><Logo size={40} light /><p className="text-xs text-slate-300">Reversed / mono</p></Card>
              <Card className="flex items-center justify-around p-6">{[16, 24, 32, 48].map((sz) => <div key={sz} className="flex flex-col items-center gap-2"><span className="flex items-center justify-center rounded-lg bg-tint" style={{ width: sz + 12, height: sz + 12 }}><LogoMark size={sz} /></span><span className="text-[11px] text-muted">{sz}px</span></div>)}</Card>
              <Card className="p-4"><p className="mb-3 text-xs text-muted">Mobile app header</p><div className="flex h-12 items-center justify-between rounded-xl border border-line px-3"><span className="text-muted">☰</span><Logo size={22} /><Avatar id="maya" size={26} /></div></Card>
              <Card className="flex flex-col items-center justify-center gap-2 p-6"><Logo size={30} wordmark={false} /><p className="text-xs text-muted">Icon-only mark</p></Card>
              <Card className="p-4"><p className="mb-3 text-xs text-muted">Browser favicon</p><div className="flex h-10 items-center gap-2 rounded-t-xl border border-line bg-slate-50 px-3"><img src="/favicon.svg" alt="" className="size-4" /><span className="text-xs text-navy">Handover — Dashboard</span></div></Card>
            </div>
            <p className="mt-3 text-xs text-muted">Don't: add gradients, rotate the mark, use AI-brain or handshake imagery, or recolour the arrows independently.</p>
          </Sec>
          <Sec id={1} title="Colours">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">{COLORS.map(([n, h, u]) => <Card key={n} className="overflow-hidden"><div className="h-16 border-b border-line" style={{ background: h }} /><div className="p-3"><p className="text-[13px] font-semibold text-navy">{n}</p><p className="font-mono text-xs text-muted">{h}</p><p className="mt-1 text-[11px] text-muted">{u}</p></div></Card>)}</div>
          </Sec>
          <Sec id={2} title="Typography" desc="Manrope for interface and editorial type, JetBrains Mono for identifiers, references and metadata. Weight does the work, not size alone.">
            <Card className="divide-y divide-line">{[['Hero · web', 'text-[44px] leading-none font-semibold tracking-[-0.045em]', '64–76 · 600'], ['Section · web', 'text-[34px] leading-tight font-semibold tracking-[-0.035em]', '42–52 · 600'], ['Page title · app', 'text-[28px] font-semibold tracking-[-0.025em]', '26–32 · 600'], ['Section · app', 'text-[18px] font-semibold tracking-[-0.015em]', '18–22 · 600'], ['Body · app', 'text-[14px]', '14–15 · 400'], ['Supporting', 'text-[12.5px] text-muted', '12–13 · 400'], ['Label', 'text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400', '11 · 600 caps'], ['Mono', 'font-mono text-[13px] text-navy', 'JetBrains Mono · 13']].map(([n, c, m]) => <div key={n} className="flex items-center gap-4 px-5 py-3.5"><span className="w-28 shrink-0 text-xs text-muted">{n}</span><span className={cn('flex-1 truncate text-navy', c)}>Knowledge that stays</span><span className="hidden font-mono text-xs text-muted sm:block">{m}</span></div>)}</Card>
          </Sec>
          <Sec id={3} title="Spacing & grid" desc="4px base unit. Layouts use 8px multiples; 12-column fluid grid with 20px gutters, max content width 1360px.">
            <Card className="p-5"><div className="flex flex-wrap items-end gap-4">{[4, 8, 12, 16, 20, 24, 32, 40, 48].map((n) => <div key={n} className="flex flex-col items-center gap-2"><div className="rounded bg-sky/60" style={{ width: n, height: n }} /><span className="font-mono text-[11px] text-muted">{n}</span></div>)}</div><div className="mt-6 grid grid-cols-12 gap-2">{Array.from({ length: 12 }).map((_, i) => <div key={i} className="h-10 rounded bg-tint" />)}</div></Card>
          </Sec>
          <Sec id={4} title="Radius & elevation" desc="Four-tier surface hierarchy: the ambient page canvas, passive content panels, interactive tiles (which rise 2px with a subtle blue border shift on hover), and overlays.">
            <div className="ambient-canvas rounded-2xl border border-line p-5">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="flex h-28 flex-col justify-between rounded-[14px] border border-dashed border-line p-4"><span className="font-mono text-[11px] text-brand">Tier 1</span><span><span className="block text-[13px] font-semibold text-navy">Page canvas</span><span className="text-[11.5px] text-muted">#F6F8FC + top-left blue light</span></span></div>
                <Card className="flex h-28 flex-col justify-between p-4"><span className="font-mono text-[11px] text-brand">Tier 2</span><span><span className="block text-[13px] font-semibold text-navy">Content panel</span><span className="text-[11.5px] text-muted">14px · #D9E1F0 · shadow-card</span></span></Card>
                <Card interactive className="flex h-28 cursor-pointer flex-col justify-between p-4"><span className="font-mono text-[11px] text-brand">Tier 3 · hover me</span><span><span className="block text-[13px] font-semibold text-navy">Interactive tile</span><span className="text-[11.5px] text-muted">2px lift · blue border tint</span></span></Card>
                <div className="flex h-28 flex-col justify-between rounded-2xl border border-line bg-white p-4 shadow-pop"><span className="font-mono text-[11px] text-brand">Tier 4</span><span><span className="block text-[13px] font-semibold text-navy">Overlay / dialog</span><span className="text-[11.5px] text-muted">16px · shadow-pop</span></span></div>
              </div>
            </div>
          </Sec>
          <Sec id={5} title="Icons" desc="Lucide, 1.75–2px stroke. 16px in buttons and tables, 18px in navigation, 20px in empty states.">
            <Card className="flex flex-wrap gap-5 p-5 text-navy">{[Workflow, FolderKanban, FileSearch, BrainCircuit, Network, Database, ShieldCheck, Sparkles, Inbox, Users, Bell, Settings, Search, Layers, AlertTriangle, Lock].map((I, i) => <I key={i} className="size-5" />)}<span className="flex gap-2">{(['github', 'jira', 'slack', 'docs'] as const).map((t) => <SourceIcon key={t} type={t} size={28} />)}</span></Card>
          </Sec>
          <Sec id={6} title="Buttons">
            <Card className="space-y-4 p-5">
              <div className="flex flex-wrap items-center gap-2"><Button>Primary</Button><Button variant="secondary">Secondary</Button><Button variant="subtle">Subtle</Button><Button variant="ghost">Ghost</Button><Button variant="success" icon={ShieldCheck}>Verify</Button><Button variant="danger" icon={Trash2}>Delete</Button><Button disabled>Disabled</Button></div>
              <div className="flex flex-wrap items-center gap-2"><Button size="sm" icon={Plus}>Small</Button><Button icon={Plus}>Medium</Button><Button size="lg" iconRight={ArrowRight}>Large</Button><IconButton icon={Bell} label="Icon button" badge={3} /><IconButton icon={Settings} label="Settings" /></div>
            </Card>
          </Sec>
          <Sec id={7} title="Form controls">
            <Card className="grid gap-5 p-5 sm:grid-cols-2">
              <Field label="Text input" hint="Helper text"><Input placeholder="Placeholder" /></Field>
              <Field label="Error state" error="This field is required"><Input invalid defaultValue="" placeholder="Invalid" /></Field>
              <Field label="Password"><PasswordInput defaultValue="handover" /></Field>
              <Field label="Search"><SearchInput placeholder="Search evidence" /></Field>
              <Field label="Select"><Select><option>Project Manager</option><option>Outgoing Member</option></Select></Field>
              <Field label="Dropdown menu"><Dropdown align="left" trigger={() => <Button variant="secondary" iconRight={ChevronRight}>Open menu</Button>}>{(c) => <><MenuItem icon={Download} onClick={c}>Export</MenuItem><MenuItem icon={Trash2} danger onClick={c}>Delete</MenuItem></>}</Dropdown></Field>
              <div className="space-y-3"><Checkbox checked={chk} onChange={setChk} label="Checkbox" description="With description" /><Radio checked={radio === 1} onChange={() => setRadio(1)} label="Radio option A" /><Radio checked={radio === 2} onChange={() => setRadio(2)} label="Radio option B" /></div>
              <div className="flex items-center gap-3"><Switch checked={sw} onChange={setSw} /><span className="text-sm text-navy">Switch</span></div>
            </Card>
          </Sec>
          <Sec id={8} title="Navigation" desc="Sidebar (expanded / collapsed / mobile drawer), top bar, breadcrumbs, tabs and segmented controls.">
            <Card className="space-y-5 p-5">
              <nav className="flex items-center gap-1.5 text-[13px]"><span className="text-muted">Projects</span><span className="text-slate-300">/</span><span className="text-muted">Atlas Payments</span><span className="text-slate-300">/</span><span className="font-medium text-navy">Evidence</span></nav>
              <Tabs tabs={[{ id: 'overview', label: 'Overview' }, { id: 'knowledge', label: 'Knowledge', count: 24 }, { id: 'team', label: 'Team' }]} value={tab} onChange={setTab} />
              <Segmented value={seg} onChange={setSeg} options={[{ id: 'a', label: 'Table' }, { id: 'b', label: 'Board' }]} />
              <div className="flex gap-3"><div className="w-56 space-y-0.5 rounded-xl bg-[#EDF2FA] p-2">{[['Dashboard', true], ['My Projects', false], ['All Handovers', false]].map(([l, a]) => <div key={l as string} className={cn('flex h-9 items-center gap-2 rounded-lg px-2.5 text-[13px] font-medium', a ? 'bg-white text-brand shadow-card' : 'text-[#3E5373]')}><Layers className="size-4" />{l as string}</div>)}</div><div className="w-14 space-y-1 rounded-xl bg-[#EDF2FA] p-2">{[1, 2, 3].map((i) => <div key={i} className={cn('flex h-9 items-center justify-center rounded-lg', i === 1 ? 'bg-white text-brand shadow-card' : 'text-[#7A8AA6]')}><Layers className="size-4" /></div>)}</div></div>
            </Card>
          </Sec>
          <Sec id={9} title="Status indicators" desc="One badge system for lifecycle, processing, verification and roles. AI confidence is deliberately styled differently from human verification.">
            <Card className="space-y-5 p-5">
              <div className="flex flex-wrap gap-2">{['draft', 'processing', 'completed', 'failed', 'pending', 'in_review', 'published', 'acknowledged', 'critical'].map((x) => <StatusBadge key={x} status={x} />)}</div>
              <div className="flex flex-wrap gap-2">{(['verified', 'needs_review', 'rejected', 'conflicting', 'insufficient'] as const).map((v) => <VerificationBadge key={v} status={v} />)}</div>
              <div className="flex flex-wrap items-center gap-2"><Confidence value={94} /><Confidence value={74} /><Confidence value={52} /><span className="text-xs text-muted">← AI confidence (indigo, dashed, sparkle)</span></div>
              <div className="flex flex-wrap gap-2"><RoleBadge role="manager" /><RoleBadge role="outgoing" /><RoleBadge role="incoming" /><Badge tone="navy">Owner</Badge><Badge>Admin</Badge><Badge>Member</Badge></div>
            </Card>
          </Sec>
          <Sec id={10} title="Data display">
            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="overflow-hidden"><Table><thead><tr><Th>Evidence</Th><Th>Author</Th><Th>Status</Th></tr></thead><tbody>{[['PR #412', 'james', 'processed'], ['PAY-1182', 'maya', 'processing'], ['Runbook v3', 'lucas', 'failed']].map(([a, b, c]) => <tr key={a}><Td className="font-medium text-navy">{a}</Td><Td><Avatar id={b} size={24} /></Td><Td><StatusBadge status={c} /></Td></tr>)}</tbody></Table><Pagination page={page} pages={4} onChange={setPage} total={32} /></Card>
              <Card><CardHeader title="Card header" subtitle="With subtitle and action" icon={Sparkles} action={<Button size="sm" variant="secondary">Action</Button>} /><div className="space-y-4 px-5 pb-5"><AvatarGroup ids={['maya', 'james', 'priya', 'lucas', 'sofia', 'omar']} /><Progress value={68} /><Progress value={100} tone="green" size="sm" /><Progress value={30} tone="amber" size="sm" /></div></Card>
            </div>
          </Sec>
          <Sec id={11} title="Feedback" desc="Loading, empty, error and success states.">
            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="space-y-3 p-5"><Skeleton className="h-4 w-1/3" /><Skeleton className="h-8 w-1/2" /><Skeleton className="h-24 w-full" /></Card>
              <Card><EmptyState icon={Inbox} title="Empty state" body="Explain why it's empty and what to do next." action={<Button size="sm">Primary action</Button>} /></Card>
              <ErrorState title="Error state" body="Slack authorisation expired. New messages aren't being ingested." action={<Button size="sm" variant="danger">Reconnect</Button>} />
              <div className="space-y-2"><Callout tone="green" icon={Check} title="Success">Handover published.</Callout><Button variant="secondary" onClick={() => s.toast('Toast notification', 'This is how confirmations appear.')}>Show toast</Button></div>
            </div>
          </Sec>
          <Sec id={12} title="Overlays">
            <Card className="flex flex-wrap items-center gap-3 p-5"><Button variant="secondary" onClick={() => setModal(true)}>Open modal</Button><Button variant="secondary" onClick={() => setConfirm(true)}>Confirmation dialog</Button><Tooltip content="Tooltips explain icons and states"><Button variant="ghost">Hover for tooltip</Button></Tooltip></Card>
            <Modal open={modal} onClose={() => setModal(false)} title="Modal title" subtitle="Supporting description" footer={<><Button variant="secondary" onClick={() => setModal(false)}>Cancel</Button><Button onClick={() => setModal(false)}>Confirm</Button></>}><p className="text-sm text-muted">Modal content goes here. On mobile, modals become bottom sheets.</p></Modal>
            <ConfirmDialog open={confirm} onClose={() => setConfirm(false)} tone="danger" title="Revoke access?" body="This immediately removes the recipient's access." confirmLabel="Revoke" onConfirm={() => s.toast('Confirmed', undefined, 'info')} />
          </Sec>
          <Sec id={13} title="Charts" desc="Each chart answers one question. Hover reveals values.">
            <div className="grid gap-4 lg:grid-cols-3">
              <Card className="p-5 lg:col-span-2"><p className="mb-2 text-[13px] font-medium text-navy">Line · trends over time</p><LineChart labels={activityTrend.map((a) => a.label)} series={[{ name: 'Evidence', color: '#315FBA', values: activityTrend.map((a) => a.evidence), area: true }]} height={160} /></Card>
              <Card className="flex flex-col items-center gap-3 p-5"><p className="self-start text-[13px] font-medium text-navy">Donut · distribution</p><Donut size={120} data={[{ label: 'Verified', value: 12, color: '#299B80' }, { label: 'Pending', value: 7, color: '#D39B43' }, { label: 'Conflicting', value: 2, color: '#D36D72' }]} center={<span className="text-lg font-semibold">21</span>} /></Card>
              <Card className="p-5 lg:col-span-3"><p className="mb-2 text-[13px] font-medium text-navy">Bar · comparisons</p><BarChart data={[320, 410, 280, 520, 460, 390, 610].map((v, i) => ({ label: `D${i + 1}`, value: v }))} height={140} /></Card>
            </div>
          </Sec>
          <Sec id={14} title="Responsive" desc="Every screen adapts rather than shrinks. Resize the browser to see each layout.">
            <div className="grid gap-4 md:grid-cols-3">{[[Monitor, 'Desktop · 1440', 'Expanded 260px sidebar, multi-column dashboards, side panels and full tables.'], [Tablet, 'Tablet · 1024', 'Collapsible 68px icon sidebar, two-column grids, adapted tables.'], [Smartphone, 'Mobile · 390', 'Drawer navigation, single-column cards, table → card lists, bottom-sheet modals.']].map(([I, t, d]) => { const Ic = I as typeof Monitor; return <Card key={t as string} className="p-5"><Ic className="size-5 text-brand" /><p className="mt-3 text-sm font-semibold text-navy">{t as string}</p><p className="mt-1 text-[13px] text-muted">{d as string}</p></Card> })}</div>
          </Sec>
          <Sec id={15} title="Motion" desc="Subtle and purposeful. Interface transitions run 200–350ms on a soft ease-out; nothing bounces, floats or glows. Reduced-motion preferences are respected.">
            <Card className="divide-y divide-line">{[['Page transition', 'Fade + 6px rise', '300ms'], ['Sidebar collapse', 'Width ease-out', '300ms'], ['Button press', 'Scale 0.98, colour', '200ms'], ['Card hover', 'Border + lift shadow', '200ms'], ['Tabs', 'Underline colour', '200ms'], ['Modal / drawer', 'Fade · slide in', '250–300ms'], ['Graph refocus', 'Nodes glide to new layout', '500ms'], ['Charts', 'Bars and lines grow on load', '600–700ms'], ['Toasts', 'Fade + rise, auto-dismiss', '4.2s']].map(([n, d, t]) => <div key={n} className="grid grid-cols-[1fr_1.4fr_auto] items-center gap-4 px-5 py-3 text-[13px]"><span className="font-semibold text-navy">{n}</span><span className="text-muted">{d}</span><Mono className="text-xs text-brand">{t}</Mono></div>)}</Card>
          </Sec>
          <Sec id={16} title="Layout rules" desc="Applied to every application screen.">
            <Card className="grid gap-px overflow-hidden bg-line sm:grid-cols-2">{[['Shell', '248px sidebar (64px collapsed) · 60px top bar · content max 1360px (1600px for wide data views)'], ['Rhythm', '4px base unit · 20px gaps between panels · 32px between page areas'], ['Metrics', 'Restrained metric tiles with subtle depth; interactive tiles lift 2px on hover while passive panels stay grounded'], ['Panels', 'Neutral white surfaces; colour is reserved for status and interaction'], ['Evidence', 'Every finding shows AI confidence and verification as separate attributes, with its sources one click away'], ['Density', 'Tables at 13px with 12px row padding; mobile converts tables to card lists']].map(([t, d]) => <div key={t} className="bg-white p-5"><p className="text-[13px] font-semibold text-navy">{t}</p><p className="mt-1 text-[13px] leading-relaxed text-muted">{d}</p></div>)}</Card>
          </Sec>
          <Sec id={17} title="3D sphere system" desc="The Organic Knowledge Sphere is a single parametric 3D asset system reused across landing, loading, empty states, onboarding, presentations, video sequences and launch materials.">
            <Card className="p-5 sm:p-6">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  ['Hero signature', 'hero', 'Layered frosted sphere with tagged hubs'],
                  ['Reconstruction loader', 'reconstruct', 'Progressive assembly from scattered nodes'],
                  ['Macro material study', 'macro', 'Close-up acrylic rims & filaments'],
                  ['Continuity bridge', 'continuity', 'Outgoing → incoming knowledge transfer'],
                ].map(([title, v, sub]) => (
                  <div key={title} className="tile flex flex-col items-center rounded-xl border p-4 text-center">
                    <SphereVisual variant={v as 'hero'} interactive={false} className="size-32" />
                    <p className="mt-2 text-[13px] font-semibold text-navy">{title}</p>
                    <p className="mt-0.5 text-[11.5px] text-muted">{sub}</p>
                  </div>
                ))}
              </div>
              <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
                <p className="text-[13px] text-muted">Explore all 7 applications—including presentation slides, the cinematic sequence player and launch assets—in the Brand & Experience Studio.</p>
                <Button iconRight={ArrowRight} onClick={() => navigate('/brand')}>Open 3D Brand Studio</Button>
              </div>
            </Card>
          </Sec>
        </div>
      </div>
    </>
  )
}

const EMPTY_SPECS: { kind: EmptyKind; title: string; state: string; explanation: string; action: string; to: string }[] = [
  { kind: 'project', title: 'Empty project space', state: 'No project seeded', explanation: 'Drifting seed nodes inside an open perimeter show a workspace ready for its first project.', action: 'Create project', to: '/projects/new' },
  { kind: 'sources', title: 'No connected sources', state: 'Disconnected clusters', explanation: 'Four outer source clusters hover outside the sphere with unbridged gaps toward the core.', action: 'Connect sources', to: '/projects/atlas/sources' },
  { kind: 'knowledge', title: 'No extracted knowledge', state: 'Awaiting reconstruction', explanation: 'The translucent frosted shell is formed, with sparse unlinked nodes awaiting extraction.', action: 'Run reconstruction', to: '/handovers/new' },
  { kind: 'relationships', title: 'Missing relationships', state: 'Unlinked pathway stubs', explanation: 'Nodes sit on the sphere with partial pathway stubs that have not yet been linked by evidence.', action: 'Open Explorer', to: '/projects/atlas/knowledge' },
  { kind: 'ingestion', title: 'Incomplete ingestion', state: 'Half-assembled hemisphere', explanation: 'The lower hemisphere is connected while upper-hemisphere records are still streaming in.', action: 'View ingestion', to: '/projects/atlas/ingestion' },
]

const VIDEO_ACTS = [
  { range: [0, 0.2], code: '01', title: 'Fragmented Signal', caption: 'Scattered commits, tickets and threads drift across isolated tools.' },
  { range: [0.2, 0.42], code: '02', title: 'Node Connections', caption: 'Pathways draw between related discussions, pull requests and architecture records.' },
  { range: [0.42, 0.65], code: '03', title: 'Macro Travelling Light', caption: 'Close-up camera tracks luminous pulses carrying context along organic filaments.' },
  { range: [0.65, 0.85], code: '04', title: 'Layered Frosted Core', caption: 'Translucent acrylic layers and internal illumination form the knowledge vessel.' },
  { range: [0.85, 1.01], code: '05', title: 'Organic Knowledge Sphere', caption: 'Decisions, responsibilities, risks and verified findings settle into continuity.' },
]

export function BrandSystem() {
  const s = useStore()
  const [loadPct, setLoadPct] = useState(58)
  const [autoLoad, setAutoLoad] = useState(true)
  const [vidPlaying, setVidPlaying] = useState(true)
  const [vidTime, setVidTime] = useState(0.18)
  const [aspect, setAspect] = useState<'16:9' | '1:1' | '9:16'>('16:9')
  const [presTheme, setPresTheme] = useState<'dark' | 'light'>('dark')

  useEffect(() => {
    if (!autoLoad) return
    const t = setInterval(() => setLoadPct((p) => (p >= 100 ? 8 : p + 2)), 140)
    return () => clearInterval(t)
  }, [autoLoad])

  useEffect(() => {
    if (!vidPlaying) return
    const t = setInterval(() => setVidTime((v) => (v >= 1 ? 0 : +(v + 0.008).toFixed(3))), 80)
    return () => clearInterval(t)
  }, [vidPlaying])

  const curAct = VIDEO_ACTS.find((a) => vidTime >= a.range[0] && vidTime <= a.range[1]) ?? VIDEO_ACTS[4]
  const exportFrame = (name: string) => s.toast('High-resolution render exported', `${name}.png saved at 2× pixel density.`)

  return (
    <>
      <PageHeader
        eyebrow={<Badge tone="indigo" icon={Sparkles}>Signature 3D Brand & Experience System</Badge>}
        title="Organic Knowledge Sphere System"
        subtitle="Handover’s reusable 3D visual identity across the public website, loading sequences, context-aware empty states, onboarding stories, brand presentations, promotional videos and launch materials."
        actions={<><Button variant="secondary" onClick={() => navigate('/design-system')}>Design System 2.0</Button><Button iconRight={ArrowRight} onClick={() => navigate('/')}>Public website</Button></>}
      />

      {/* 1. Landing Page System */}
      <Card className="mb-6 p-5 sm:p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div><p className="font-mono text-xs text-brand">01 · LANDING PAGE SYSTEM</p><h2 className="mt-1 text-lg font-semibold text-navy">Hero & Section Variations</h2><p className="text-[13px] text-muted">One parametric engine drives the hero sphere and the three secondary marketing scenes.</p></div>
          <Button size="sm" variant="secondary" iconRight={ArrowRight} onClick={() => navigate('/')}>Inspect on landing page</Button>
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { title: 'Signature Hero Sphere', v: 'hero' as const, desc: 'Full layered frosted sphere with 5 semantic hub tags and pointer parallax.' },
            { title: 'Introducing Handover', v: 'assemble' as const, desc: 'Scattered geometric beads converging into an elliptical frosted lens.' },
            { title: 'Knowledge Intelligence', v: 'network' as const, desc: 'Cropped peripheral filament network pulsing with category colour.' },
            { title: 'Final CTA Continuity', v: 'continuity' as const, desc: 'Outgoing and incoming spheres joined by luminous continuity strands.' },
          ].map((item) => (
            <div key={item.title} className="tile flex flex-col rounded-xl border p-4">
              <div className="ambient-hero flex h-40 items-center justify-center rounded-lg border border-line/60">
                <SphereVisual variant={item.v} progress={0.92} interactive={false} className="h-36 w-full" />
              </div>
              <p className="mt-3 text-[13.5px] font-semibold text-navy">{item.title}</p>
              <p className="mt-1 text-xs leading-relaxed text-muted">{item.desc}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* 2. Loading Experience & 4. Product Introduction */}
      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <Card className="p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div><p className="font-mono text-xs text-brand">02 · LOADING EXPERIENCE</p><h2 className="mt-1 text-lg font-semibold text-navy">Animated Knowledge Reconstruction</h2></div>
            <Button size="sm" variant="secondary" icon={autoLoad ? Pause : Play} onClick={() => setAutoLoad(!autoLoad)}>{autoLoad ? 'Pause cycle' : 'Auto-cycle'}</Button>
          </div>
          <p className="mt-1 text-[13px] text-muted">Begins with scattered nodes and disconnected pathways, then progressively links edges and blooms the frosted glass core.</p>
          <div className="mt-4 rounded-2xl border border-line bg-canvas/60 p-4">
            <ReconstructionLoader progress={loadPct} />
            <div className="mt-3 flex items-center gap-3 px-4">
              <span className="font-mono text-[11px] text-muted">Scrub stage</span>
              <input type="range" min={0} max={100} value={loadPct} onChange={(e) => { setAutoLoad(false); setLoadPct(+e.target.value) }} className="flex-1 accent-[#315FBA]" />
              <Mono className="w-10 text-right text-xs text-navy">{loadPct}%</Mono>
            </div>
          </div>
        </Card>

        <Card className="flex flex-col justify-between p-5 sm:p-6">
          <div>
            <div className="flex items-center justify-between"><p className="font-mono text-xs text-brand">04 · PRODUCT INTRODUCTION SCREENS</p><Button size="sm" variant="secondary" iconRight={ArrowRight} onClick={() => navigate('/onboarding')}>Open Onboarding</Button></div>
            <h2 className="mt-1 text-lg font-semibold text-navy">5-Act Animated Product Story</h2>
            <p className="mt-1 text-[13px] text-muted">Pairs 3D knowledge continuity with crisp 2D product interface previews across five narrative acts.</p>
            <ol className="mt-4 space-y-2">
              {[
                ['01 · Sources enter', 'GitHub, Jira, Slack & documents stream into outer clusters'],
                ['02 · Fragmented signals connect', 'Commits, threads & issues form curved surface pathways'],
                ['03 · Intelligence emerges', 'Decisions, responsibilities, risks & dependencies crystallise'],
                ['04 · Human verification', 'Macro inspection of AI confidence vs human Verified status'],
                ['05 · Structured handover', 'Continuity bridge transfers verified context to the recipient'],
              ].map(([t, d]) => (
                <li key={t} className="flex items-center justify-between gap-3 rounded-xl border border-line px-3.5 py-2 text-[12.5px]">
                  <span className="font-semibold text-navy">{t}</span>
                  <span className="truncate text-muted">{d}</span>
                </li>
              ))}
            </ol>
          </div>
          <div className="mt-4 flex items-center justify-between rounded-xl bg-tint/60 px-4 py-3 text-xs text-navy">
            <span>3D storytelling is always paired with flat, accurate 2D UI previews.</span>
            <Link to="/onboarding" className="font-semibold text-brand hover:underline">Launch story →</Link>
          </div>
        </Card>
      </div>

      {/* 3. Context-Aware Empty Knowledge States */}
      <Card className="mb-6 p-5 sm:p-6">
        <p className="font-mono text-xs text-brand">03 · EMPTY KNOWLEDGE STATES</p>
        <h2 className="mt-1 text-lg font-semibold text-navy">Context-Aware 3D Empty Variations</h2>
        <p className="mt-1 text-[13px] text-muted">Each empty state uses a specific structural state of the sphere—never a generic illustration—paired with an explanation and next action.</p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {EMPTY_SPECS.map((e) => (
            <div key={e.kind} className="tile flex flex-col justify-between rounded-xl border p-4 text-center">
              <div>
                <SphereVisual variant="empty" emptyKind={e.kind} interactive={false} className="mx-auto size-32" />
                <span className="mt-1 inline-block rounded-full border border-line bg-canvas px-2 py-0.5 font-mono text-[10px] text-muted">{e.state}</span>
                <p className="mt-2.5 text-[13.5px] font-semibold text-navy">{e.title}</p>
                <p className="mt-1 text-xs leading-relaxed text-muted">{e.explanation}</p>
              </div>
              <Button size="sm" variant="secondary" className="mt-4 w-full" onClick={() => navigate(e.to)}>{e.action}</Button>
            </div>
          ))}
        </div>
      </Card>

      {/* 5. Brand Presentations */}
      <Card className="mb-6 p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div><p className="font-mono text-xs text-brand"><Presentation className="mr-1 inline size-3.5" />05 · BRAND PRESENTATIONS</p><h2 className="mt-1 text-lg font-semibold text-navy">Studio Renders, Macro Details & Presentation Covers</h2></div>
          <Segmented value={presTheme} onChange={setPresTheme} options={[{ id: 'dark', label: 'Dark keynote' }, { id: 'light', label: 'Light editorial' }]} />
        </div>
        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          {[
            { title: 'Hero Studio Render', sub: 'Full-frame balanced sphere · 1:1', variant: 'hero' as const, zoom: 1.05, off: [0, 0] as [number, number] },
            { title: 'Close-Up Material Render', sub: 'Frosted acrylic rim & internal glow · 1.85×', variant: 'macro' as const, zoom: 1.15, off: [-0.08, 0.04] as [number, number] },
            { title: 'Pathway & Node Detail', sub: 'Surface arcs, hub halos & filaments · 2.1×', variant: 'hero' as const, zoom: 1.85, off: [0.18, -0.14] as [number, number] },
          ].map((r) => (
            <div key={r.title} className={cn('overflow-hidden rounded-2xl border', presTheme === 'dark' ? 'border-[#2c4566] bg-navy text-white' : 'border-line bg-white')}>
              <div className={cn('relative h-56', presTheme === 'light' && 'ambient-hero')}>
                <SphereVisual variant={r.variant} camZoom={r.zoom} camOffset={r.off} dark={presTheme === 'dark'} showTags={false} className="h-full w-full" />
              </div>
              <div className={cn('flex items-center justify-between border-t px-4 py-3', presTheme === 'dark' ? 'border-white/10' : 'border-line')}>
                <div><p className="text-[13px] font-semibold">{r.title}</p><p className={cn('text-xs', presTheme === 'dark' ? 'text-[#a9b8d0]' : 'text-muted')}>{r.sub}</p></div>
                <Button size="sm" variant="secondary" icon={Download} onClick={() => exportFrame(r.title)}>PNG</Button>
              </div>
            </div>
          ))}
        </div>
        {/* 16:9 Presentation Covers (Light & Dark) */}
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <div className="relative overflow-hidden rounded-2xl border border-[#2c4566] bg-navy p-6 text-white sm:p-8">
            <div className="pointer-events-none absolute inset-y-0 right-0 w-[62%]"><SphereVisual variant="hero" dark showTags={false} className="h-full w-full" /></div>
            <div className="relative z-10 flex min-h-[210px] max-w-sm flex-col justify-between">
              <Logo size={26} light />
              <div>
                <p className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-[#a9b8d0]">Executive Presentation · 16:9 Dark</p>
                <h3 className="mt-2 text-2xl font-semibold tracking-tight">Knowledge continues.</h3>
                <p className="mt-1.5 text-xs leading-relaxed text-[#c3cfe0]">Evidence-backed project knowledge reconstruction and transition management.</p>
              </div>
              <p className="font-mono text-[10px] text-[#8796ae]">handover.app · Confidential</p>
            </div>
          </div>
          <div className="ambient-hero relative overflow-hidden rounded-2xl border border-line p-6 sm:p-8">
            <div className="pointer-events-none absolute inset-y-0 right-0 w-[62%]"><SphereVisual variant="hero" showTags={false} className="h-full w-full" /></div>
            <div className="relative z-10 flex min-h-[210px] max-w-sm flex-col justify-between">
              <Logo size={26} />
              <div>
                <p className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-brand">Architecture Review · 16:9 Light</p>
                <h3 className="mt-2 text-2xl font-semibold tracking-tight text-navy">People change. Knowledge stays.</h3>
                <p className="mt-1.5 text-xs leading-relaxed text-muted">How Handover captures, verifies and transfers critical engineering context.</p>
              </div>
              <p className="font-mono text-[10px] text-muted">handover.app · Design System 2.0</p>
            </div>
          </div>
        </div>
      </Card>

      {/* 6. Promotional Videos — Cinematic Sequence Director */}
      <Card className="mb-6 p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><p className="font-mono text-xs text-brand"><Film className="mr-1 inline size-3.5" />06 · PROMOTIONAL VIDEO SEQUENCES</p><h2 className="mt-1 text-lg font-semibold text-navy">Cinematic Transformation Sequence</h2><p className="text-[13px] text-muted">Reusable 5-shot motion sequence for website reels, product demos, keynotes and social media.</p></div>
          <div className="flex flex-wrap items-center gap-2">
            <Segmented value={aspect} onChange={setAspect} options={[{ id: '16:9', label: '16:9 Web/Deck' }, { id: '1:1', label: '1:1 Social' }, { id: '9:16', label: '9:16 Vertical' }]} />
            <Button size="sm" variant="secondary" icon={vidPlaying ? Pause : Play} onClick={() => setVidPlaying(!vidPlaying)}>{vidPlaying ? 'Pause' : 'Play'}</Button>
            <Button size="sm" variant="ghost" icon={RotateCcw} onClick={() => setVidTime(0)} aria-label="Restart" />
          </div>
        </div>
        <div className="mt-5 flex justify-center rounded-2xl border border-line bg-[#0e1929] p-4 sm:p-6">
          <div className={cn('relative overflow-hidden rounded-xl border border-white/15 bg-navy text-white shadow-pop transition-all', aspect === '16:9' ? 'aspect-video w-full max-w-4xl' : aspect === '1:1' ? 'aspect-square w-full max-w-md' : 'aspect-[9/16] w-full max-w-[300px]')}>
            <SphereVisual variant="cinematic" progress={vidTime} dark className="h-full w-full" />
            <div className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between p-4 sm:p-5">
              <Logo size={22} light />
              <span className="rounded-full border border-white/15 bg-navy/70 px-2.5 py-0.5 font-mono text-[10.5px] text-[#c3cfe0] backdrop-blur">SHOT {curAct.code} / 05 · {aspect}</span>
            </div>
            <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#0b1523]/90 via-[#0b1523]/40 to-transparent p-4 sm:p-6">
              <p className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-[#a5a0d9]">{curAct.code} · {curAct.title}</p>
              <p className="mt-1 max-w-xl text-sm font-medium text-white sm:text-base">{curAct.caption}</p>
            </div>
          </div>
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-5">
          {VIDEO_ACTS.map((a) => {
            const active = curAct.code === a.code
            return (
              <button key={a.code} onClick={() => { setVidPlaying(false); setVidTime((a.range[0] + a.range[1]) / 2) }} className={cn('rounded-xl border p-3 text-left transition', active ? 'border-brand bg-tint/50' : 'border-line hover:bg-canvas')}>
                <p className="font-mono text-[10.5px] text-brand">Shot {a.code}</p>
                <p className="mt-0.5 text-[12.5px] font-semibold text-navy">{a.title}</p>
              </button>
            )
          })}
        </div>
      </Card>

      {/* 7. Product Launch Materials */}
      <Card className="p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div><p className="font-mono text-xs text-brand"><Megaphone className="mr-1 inline size-3.5" />07 · PRODUCT LAUNCH MATERIALS</p><h2 className="mt-1 text-lg font-semibold text-navy">Launch Banners, Social Assets & Feature Graphics</h2><p className="text-[13px] text-muted">Consistent materials, lighting, proportions and colour across every launch surface.</p></div>
          <Button size="sm" variant="secondary" icon={Download} onClick={() => exportFrame('handover-launch-kit')}>Download launch kit</Button>
        </div>
        {/* Launch Hero Announcement Banner */}
        <div className="ambient-hero relative mt-5 overflow-hidden rounded-2xl border border-line p-6 sm:p-8">
          <div className="grid items-center gap-6 lg:grid-cols-[1.15fr_0.85fr]">
            <div>
              <div className="flex items-center gap-2"><Logo size={24} /><Badge tone="blue">Launch Announcement</Badge></div>
              <h3 className="mt-4 text-2xl font-semibold tracking-tight text-navy sm:text-3xl">Your team’s knowledge shouldn’t leave when people do.</h3>
              <p className="mt-2 max-w-lg text-sm text-muted">Introducing Handover: AI-reconstructed, human-verified project knowledge continuity across GitHub, Jira, Slack and docs.</p>
              <div className="mt-4 flex flex-wrap items-center gap-3 text-xs font-semibold text-brand"><span>handover.app</span><span className="text-slate-300">·</span><span className="font-mono uppercase tracking-[0.14em] text-navy">Knowledge continues.</span></div>
            </div>
            <div className="grid grid-cols-2 items-center gap-3">
              <SphereVisual variant="hero" showTags={false} interactive={false} className="mx-auto size-40 sm:size-44" />
              <div className="rounded-xl border border-line bg-white/95 p-3.5 shadow-card">
                <p className="font-mono text-[10px] uppercase text-muted">Verified finding</p>
                <p className="mt-1 text-xs font-semibold text-navy">Decouple settlement via Kafka</p>
                <div className="mt-2 flex flex-wrap gap-1"><Confidence value={94} compact /><VerificationBadge status="verified" /></div>
              </div>
            </div>
          </div>
        </div>
        {/* Feature Launch Illustrations */}
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {[
            { tag: 'Feature 01 · Explorer', title: 'Every decision has a reason', body: '3D relationship continuity paired with a 3-panel interactive graph inspector.', v: 'network' as const },
            { tag: 'Feature 02 · Verification', title: 'AI reconstructs. People verify.', body: 'Distinct visual encoding for model certainty (94%) vs human confirmation.', v: 'macro' as const },
            { tag: 'Feature 03 · Continuity', title: 'Day-one project context', body: 'Structured handovers and an evidence-citing assistant for incoming members.', v: 'continuity' as const },
          ].map((f) => (
            <div key={f.tag} className="tile flex flex-col justify-between overflow-hidden rounded-xl border p-4">
              <div className="ambient-section flex h-36 items-center justify-center rounded-lg border border-line/60 bg-canvas">
                <SphereVisual variant={f.v} interactive={false} className="h-32 w-full" />
              </div>
              <div className="mt-3">
                <p className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-brand">{f.tag}</p>
                <p className="mt-1 text-[14px] font-semibold text-navy">{f.title}</p>
                <p className="mt-1 text-xs text-muted">{f.body}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </>
  )
}

const FLOWS: { title: string; who: string; steps: [string, string][] }[] = [
  { title: 'New user onboarding', who: 'Any', steps: [['Signup', '/signup'], ['Login', '/login?registered=1'], ['Onboarding: workspace', '/onboarding'], ['Create project', '/onboarding'], ['Dashboard', '/dashboard']] },
  { title: 'Project creation', who: 'Manager', steps: [['Dashboard', '/dashboard'], ['Create project', '/projects/new'], ['Add details & members', '/projects/new'], ['Project overview', '/projects/atlas']] },
  { title: 'Source connection', who: 'Manager · Atlas', steps: [['Project', '/projects/atlas'], ['Data sources', '/projects/atlas/sources'], ['GitHub → Authorise → Select repos', '/projects/atlas/sources'], ['Ingestion activity', '/projects/atlas/ingestion']] },
  { title: 'Knowledge reconstruction', who: 'Manager · Atlas', steps: [['Ingestion', '/projects/atlas/ingestion'], ['Intelligence overview', '/projects/atlas/intelligence'], ['Decisions', '/projects/atlas/intelligence/decisions'], ['Risks', '/projects/atlas/intelligence/risks'], ['Evidence verification', '/projects/atlas/evidence/ev-incident']] },
  { title: 'Handover creation', who: 'Manager', steps: [['Create handover', '/handovers/new'], ['Project → Members → Sources', '/handovers/new'], ['Scope → Generate', '/handovers/new'], ['Review', '/handovers/ho-1044']] },
  { title: 'Handover approval', who: 'Outgoing (Orion) → Manager', steps: [['Review findings', '/handovers/ho-1038/review'], ['Complete missing info', '/handovers/ho-1038/review?gaps=1'], ['Submit', '/handovers/ho-1038'], ['Manager review & approve', '/handovers/ho-1042/review'], ['Publish', '/handovers/ho-1033']] },
  { title: 'Incoming member', who: 'Incoming · Helix', steps: [['Notification', '/notifications'], ['Received handover', '/handovers/received'], ['Explore knowledge', '/handovers/ho-1035/recipient'], ['Ask AI', '/handovers/ho-1035/assistant'], ['Acknowledge', '/handovers/ho-1035/recipient']] },
  { title: 'Project switching', who: 'Any', steps: [['Project selector (sidebar)', '/dashboard'], ['Select Orion → Outgoing', '/projects/orion'], ['Navigation updates', '/projects/orion'], ['Dashboard updates', '/dashboard']] },
]
const PAGES: [string, [string, string][]][] = [
  ['Public website', [['Landing page', '/'], ['Log in', '/login'], ['Get started', '/signup']]],
  ['Authentication & Onboarding', [['01 Login', '/login'], ['02 Registration', '/signup'], ['03 Forgot password', '/forgot-password'], ['04 Onboarding', '/onboarding']]],
  ['Workspace & Projects', [['05 Dashboard', '/dashboard'], ['06 My projects', '/projects'], ['07 Create project', '/projects/new'], ['08 Project overview', '/projects/atlas'], ['09 Team & members', '/projects/atlas/team']]],
  ['Knowledge Hub', [['10 Data sources', '/projects/atlas/sources'], ['11 Source details', '/projects/atlas/sources/src-slack-atlas'], ['12 Evidence library', '/projects/atlas/evidence'], ['13 Evidence detail', '/projects/atlas/evidence/ev-412'], ['14 Ingestion', '/projects/atlas/ingestion'], ['15 Knowledge explorer', '/projects/atlas/knowledge']]],
  ['AI Intelligence', [['16 Overview', '/projects/atlas/intelligence'], ['17 Decisions', '/projects/atlas/intelligence/decisions'], ['18 Tasks', '/projects/atlas/intelligence/tasks'], ['19 Risks', '/projects/atlas/intelligence/risks'], ['20 Dependencies', '/projects/atlas/intelligence/dependencies'], ['21 Timeline', '/projects/atlas/intelligence/timeline']]],
  ['Handover Management', [['22 All handovers', '/handovers'], ['23 Create handover', '/handovers/new'], ['24 Workspace', '/handovers/ho-1042'], ['25 Review & verification', '/handovers/ho-1042/review'], ['26 Report', '/handovers/ho-1042/report'], ['27 Published', '/handovers/published'], ['28 Received', '/handovers/received']]],
  ['Incoming Member Experience', [['29 Recipient workspace', '/handovers/ho-1035/recipient'], ['30 AI assistant', '/handovers/ho-1035/assistant']]],
  ['Administration', [['31 Team management', '/settings/team'], ['32 Notifications', '/notifications'], ['33 Audit logs', '/settings/audit-logs'], ['34 Settings', '/settings'], ['35 Profile', '/settings/profile']]],
]

export function Flows() {
  return (
    <>
      <div className="relative mb-8 overflow-hidden rounded-2xl border border-line bg-white p-6 shadow-card sm:p-10">
        <div className="absolute inset-0 opacity-50" style={{ backgroundImage: 'radial-gradient(#D9E1F0 1px, transparent 1px)', backgroundSize: '20px 20px' }} />
        <div className="relative max-w-2xl">
          <Logo size={36} />
          <h1 className="mt-6 text-3xl font-semibold tracking-tight text-navy">Product overview & prototype map</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">Handover captures, reconstructs, verifies and transfers project knowledge between outgoing and incoming team members. You are signed in as <span className="font-medium text-navy">Maya Chen</span>, who holds a different role on each project, so every role experience can be explored in one session.</p>
          <div className="mt-5 flex flex-wrap gap-2"><span className="flex items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1 text-xs"><RoleBadge role="manager" />Atlas · Nova</span><span className="flex items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1 text-xs"><RoleBadge role="outgoing" />Orion</span><span className="flex items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1 text-xs"><RoleBadge role="incoming" />Helix</span></div>
        </div>
      </div>
      <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-navy"><MousePointerClick className="size-5 text-brand" />Interactive flows</h2>
      <div className="grid gap-4 lg:grid-cols-2">
        {FLOWS.map((f, i) => (
          <Card key={f.title} className="p-5">
            <div className="flex items-center justify-between"><p className="text-[15px] font-semibold text-navy"><span className="mr-2 text-brand">Flow {i + 1}</span>{f.title}</p><Badge tone="gray">{f.who}</Badge></div>
            <ol className="mt-4 flex flex-wrap items-center gap-1.5">{f.steps.map(([l, to], j) => <li key={j} className="flex items-center gap-1.5"><Link to={to} className="rounded-lg border border-line bg-white px-2.5 py-1.5 text-[12.5px] font-medium text-navy transition hover:border-brand hover:bg-tint/50 hover:text-brand">{l}</Link>{j < f.steps.length - 1 && <ChevronRight className="size-3.5 text-slate-300" />}</li>)}</ol>
          </Card>
        ))}
      </div>
      <h2 className="mb-4 mt-10 flex items-center gap-2 text-lg font-semibold text-navy"><Layers className="size-5 text-brand" />All 35 screens</h2>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {PAGES.map(([g, items]) => <Card key={g} className="p-5"><p className="text-[13px] font-semibold text-navy">{g}</p><ul className="mt-3 space-y-1">{items.map(([l, to]) => <li key={to + l}><Link to={to} className="flex items-center justify-between rounded-lg px-2 py-1.5 text-[13px] text-muted hover:bg-slate-50 hover:text-brand">{l}<ArrowRight className="size-3.5" /></Link></li>)}</ul></Card>)}
        <Card className="p-5"><p className="text-[13px] font-semibold text-navy">Brand & design system</p><ul className="mt-3 space-y-1"><li><Link to="/brand" className="flex items-center justify-between rounded-lg px-2 py-1.5 text-[13px] text-muted hover:bg-slate-50 hover:text-brand">3D Brand & Experience System (all 7 apps)<ArrowRight className="size-3.5" /></Link></li><li><Link to="/design-system" className="flex items-center justify-between rounded-lg px-2 py-1.5 text-[13px] text-muted hover:bg-slate-50 hover:text-brand">Brand identity, foundations & components<ArrowRight className="size-3.5" /></Link></li></ul></Card>
      </div>
    </>
  )
}
