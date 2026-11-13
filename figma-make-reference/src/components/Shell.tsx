import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  Bell, BookOpen, Boxes, BrainCircuit, Building2, CheckCircle2, ChevronDown, ChevronsLeft, ChevronsRight, ChevronsUpDown, CircleHelp, Database, FileSearch,
  FolderKanban, HelpCircle, Inbox, Keyboard, LayoutDashboard, LifeBuoy, LogOut, Menu, MessageSquareText, Network, Palette, Plug, Plus, ScrollText, Search,
  Send, Settings, ShieldCheck, User, Users, Workflow, X, XCircle, Info, ArrowRight, Layers, ClipboardCheck, Sparkles, History, ChevronRight,
} from 'lucide-react'
import { Logo, LogoMark } from './brand'
import { Avatar, Badge, Dropdown, IconButton, MenuItem, cn, Tooltip } from './ui'
import { useStore, WORKSPACES } from '@/lib/store'
import { Link, navigate, useRoute } from '@/lib/router'
import { decisions, evidence, ME, personById, risks, ROLE_LABEL, tasks, HANDOVER_STATUS_LABEL, type ProjectRole } from '@/lib/data'

export const ROLE_TONE: Record<ProjectRole, 'blue' | 'amber' | 'green'> = { manager: 'blue', outgoing: 'amber', incoming: 'green' }
export function RoleBadge({ role, className }: { role: ProjectRole; className?: string }) {
  return <Badge tone={ROLE_TONE[role]} dot className={className}>{ROLE_LABEL[role]}</Badge>
}

interface NavItem { label: string; to: string; icon: typeof Bell; badge?: number; match?: string; accent?: boolean }

function useNav() {
  const s = useStore()
  const p = s.currentProject
  const unread = s.notifications.filter((n) => !n.read).length
  const received = s.handovers.filter((h) => h.incomingId === ME && h.status === 'published').length
  const isManagerSomewhere = s.projects.some((x) => x.role === 'manager')
  const groups: { label: string; items: NavItem[] }[] = [
    { label: 'Workspace', items: [
      { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
      { label: 'My Projects', to: '/projects', icon: FolderKanban, match: '/projects$|/projects/new' },
      { label: 'Team', to: '/settings/team', icon: Users },
    ] },
    { label: 'Handovers', items: [
      { label: 'All Handovers', to: '/handovers', icon: Workflow, match: '^/handovers$|/handovers/ho-' },
      ...(isManagerSomewhere ? [{ label: 'Create Handover', to: '/handovers/new', icon: Plus }] : []),
      { label: 'Received', to: '/handovers/received', icon: Inbox, badge: received },
      { label: 'Published', to: '/handovers/published', icon: Send },
    ] },
  ]
  if (p) {
    const base = `/projects/${p.id}`
    const items: NavItem[] = [
      { label: 'Overview', to: base, icon: Layers, match: `^${base}$` },
      { label: 'Knowledge Explorer', to: `${base}/knowledge`, icon: Network },
      { label: 'Intelligence', to: `${base}/intelligence`, icon: BrainCircuit },
      { label: 'Evidence Library', to: `${base}/evidence`, icon: FileSearch },
    ]
    if (p.role === 'manager') items.push({ label: 'Data Sources', to: `${base}/sources`, icon: Database }, { label: 'Ingestion', to: `${base}/ingestion`, icon: Boxes })
    items.push({ label: 'Project Handovers', to: `${base}/handovers`, icon: Workflow }, { label: 'Activity', to: `${base}/activity`, icon: History }, { label: 'Members', to: `${base}/team`, icon: Users })
    if (p.role === 'outgoing') {
      const h = s.handovers.find((x) => x.projectId === p.id && x.outgoingId === ME)
      if (h) items.push({ label: 'Verify my handover', to: `/handovers/${h.id}/review`, icon: ClipboardCheck, accent: true })
    }
    if (p.role === 'incoming') {
      const h = s.handovers.find((x) => x.projectId === p.id && x.incomingId === ME && (x.status === 'published' || x.status === 'completed'))
      if (h) items.push({ label: 'My handover', to: `/handovers/${h.id}/recipient`, icon: BookOpen, accent: true }, { label: 'Ask assistant', to: `/handovers/${h.id}/assistant`, icon: MessageSquareText })
    }
    groups.push({ label: 'Project', items })
  }
  groups.push({ label: 'Settings', items: [
    { label: 'Settings', to: '/settings', icon: Settings, match: '^/settings(\\?.*)?$|^/settings/audit-logs' },
    { label: 'Notifications', to: '/notifications', icon: Bell, badge: unread },
    { label: 'Profile', to: '/settings/profile', icon: User },
  ] })
  return groups
}

function ProjectSwitcher({ collapsed, onDone }: { collapsed: boolean; onDone?: () => void }) {
  const s = useStore()
  const p = s.currentProject
  if (!p) return null
  return (
    <Dropdown width="w-72" align="left" trigger={() => (
      collapsed ? (
        <Tooltip content={`${p.name} · ${ROLE_LABEL[p.role]}`}><button className="mx-auto flex size-9 items-center justify-center rounded-lg text-xs font-bold text-white" style={{ background: p.color }}>{p.code.slice(0, 2)}</button></Tooltip>
      ) : (
        <button className="flex w-full items-center gap-2.5 rounded-[10px] border border-[#d4ddec] bg-white px-2 py-1.5 text-left transition duration-200 hover:border-[#b9c7de] hover:shadow-lift" aria-label="Switch project">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-[7px] text-[10px] font-bold text-white" style={{ background: p.color }}>{p.code}</span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[13px] font-semibold text-navy">{p.name}</span>
            <span className="mt-0.5 flex items-center gap-1 text-[11px] text-muted"><span className={cn('size-1.5 rounded-full', { manager: 'bg-brand', outgoing: 'bg-warn', incoming: 'bg-ok' }[p.role])} />{ROLE_LABEL[p.role]}</span>
          </span>
          <ChevronsUpDown className="size-4 text-slate-400" />
        </button>
      )
    )}>
      {(close) => (
        <div>
          <p className="px-2.5 pb-1 pt-1.5 text-[11px] font-medium uppercase tracking-wide text-slate-400">Switch project · your role</p>
          {s.projects.map((x) => (
            <button key={x.id} onClick={() => { s.switchProject(x.id); close(); onDone?.(); navigate(`/projects/${x.id}`) }} className={cn('flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left hover:bg-tint', x.id === p.id && 'bg-tint')}>
              <span className="flex size-7 shrink-0 items-center justify-center rounded-md text-[10px] font-bold text-white" style={{ background: x.color }}>{x.code}</span>
              <span className="min-w-0 flex-1"><span className="block truncate text-[13px] font-medium text-navy">{x.name}</span><span className="text-[11px] text-muted">{ROLE_LABEL[x.role]}</span></span>
              {x.id === p.id && <CheckCircle2 className="size-4 text-brand" />}
            </button>
          ))}
          <div className="my-1 border-t border-line" />
          <MenuItem icon={Plus} onClick={() => { close(); onDone?.(); navigate('/projects/new') }}>Create project</MenuItem>
        </div>
      )}
    </Dropdown>
  )
}

function WorkspaceSwitcher({ collapsed }: { collapsed: boolean }) {
  const s = useStore()
  const ws = WORKSPACES.find((w) => w.id === s.workspaceId)!
  return (
    <Dropdown width="w-64" align="left" trigger={() => (
      <button className={cn('flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left transition hover:bg-white/70', collapsed && 'justify-center')} aria-label="Switch workspace">
        <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-navy text-[10px] font-bold text-white">{ws.name[0]}</span>
        {!collapsed && <><span className="min-w-0 flex-1 truncate text-[13px] font-medium text-navy">{ws.name}</span><ChevronDown className="size-3.5 text-slate-400" /></>}
      </button>
    )}>
      {(close) => (
        <div>
          <p className="px-2.5 pb-1 pt-1.5 text-[11px] font-medium uppercase tracking-wide text-slate-400">Workspaces</p>
          {WORKSPACES.map((w) => (
            <MenuItem key={w.id} icon={Building2} active={w.id === s.workspaceId} onClick={() => { s.setWorkspaceId(w.id); close(); s.toast(`Switched to ${w.name}`, undefined, 'info'); navigate('/dashboard') }} hint={undefined}>
              <span className="block">{w.name}</span><span className="block text-[11px] text-muted">{w.plan}</span>
            </MenuItem>
          ))}
          <div className="my-1 border-t border-line" />
          <MenuItem icon={Plus} onClick={() => { close(); navigate('/onboarding') }}>Create or join workspace</MenuItem>
        </div>
      )}
    </Dropdown>
  )
}

function SidebarContent({ collapsed, onNavigate }: { collapsed: boolean; onNavigate?: () => void }) {
  const s = useStore()
  const { path, query } = useRoute()
  const full = path + (query.toString() ? `?${query}` : '')
  const groups = useNav()
  const isActive = (i: NavItem) => (i.match ? new RegExp(i.match).test(full) : path === i.to || path.startsWith(i.to + '/'))
  const me = personById(ME)
  return (
    <div className="flex h-full flex-col">
      <div className={cn('flex h-[60px] shrink-0 items-center px-4', collapsed && 'justify-center px-0')}>
        <Link to="/dashboard" onClick={onNavigate}>{collapsed ? <LogoMark size={26} /> : <Logo size={24} />}</Link>
      </div>
      <div className={cn('space-y-2 px-3', collapsed && 'px-2')}>
        <WorkspaceSwitcher collapsed={collapsed} />
        <button onClick={() => s.setPaletteOpen(true)} className={cn('flex h-8 w-full items-center gap-2 rounded-lg border border-[#d4ddec] bg-white/60 px-2.5 text-[12.5px] text-slate-400 transition duration-200 hover:border-[#c3cfe3] hover:bg-white', collapsed && 'justify-center px-0')} aria-label="Search">
          <Search className="size-3.5" />
          {!collapsed && <><span className="flex-1 text-left">Search</span><kbd className="rounded border border-line bg-white px-1 font-mono text-[10px] text-slate-500">⌘K</kbd></>}
        </button>
      </div>
      <nav className="scrollbar-thin mt-4 flex-1 space-y-5 overflow-y-auto px-3 pb-4" aria-label="Main">
        {groups.map((g) => (
          <div key={g.label}>
            {g.label === 'Project' ? (
              <div className="mb-2">
                {!collapsed && <p className="mb-1.5 px-2 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-[#97a3b8]">Current project</p>}
                <ProjectSwitcher collapsed={collapsed} onDone={onNavigate} />
              </div>
            ) : !collapsed ? <p className="mb-1 px-2 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-[#97a3b8]">{g.label}</p> : <div className="mx-auto mb-2 h-px w-6 bg-[#d4ddec]" />}
            <ul className="space-y-0.5">
              {g.items.map((i) => {
                const active = isActive(i)
                const el = (
                  <Link to={i.to} onClick={onNavigate} aria-current={active ? 'page' : undefined} className={cn('group relative flex h-8 items-center gap-2.5 rounded-[8px] px-2.5 text-[13.5px] transition-colors duration-200', active ? 'bg-white font-semibold text-navy shadow-[0_1px_2px_rgba(32,54,83,0.06),0_0_0_1px_rgba(217,225,240,0.9)]' : 'font-medium text-[#4a5d7c] hover:bg-white/55 hover:text-navy', i.accent && !active && 'text-brand', collapsed && 'justify-center px-0')}>
                    <i.icon className={cn('size-4 shrink-0', active || i.accent ? 'text-brand' : 'text-[#8796ae] group-hover:text-navy')} strokeWidth={1.9} />
                    {!collapsed && <span className="flex-1 truncate">{i.label}</span>}
                    {!!i.badge && (collapsed ? <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-bad" /> : <span className="rounded-md bg-blue-100 px-1.5 font-mono text-[10.5px] font-medium text-brand">{i.badge}</span>)}
                  </Link>
                )
                return <li key={i.label}>{collapsed ? <Tooltip content={i.label}>{el}</Tooltip> : el}</li>
              })}
            </ul>
          </div>
        ))}
      </nav>
      <div className={cn('border-t border-[#D9E1F0] p-3', collapsed && 'px-2')}>
        <Link to="/settings/profile" onClick={onNavigate} className={cn('flex items-center gap-2.5 rounded-lg p-1.5 hover:bg-white/60', collapsed && 'justify-center')}>
          <Avatar id={ME} size={32} />
          {!collapsed && <span className="min-w-0 flex-1"><span className="block truncate text-[13px] font-semibold text-navy">{me.name}</span><span className="block truncate text-[11px] text-muted">Workspace {me.wsRole}</span></span>}
        </Link>
      </div>
    </div>
  )
}

function Breadcrumbs({ crumbs }: { crumbs: { label: string; to?: string }[] }) {
  const s = useStore()
  const ws = WORKSPACES.find((w) => w.id === s.workspaceId)!
  return (
    <nav aria-label="Breadcrumb" className="hidden min-w-0 items-center gap-1.5 text-[13px] md:flex">
      <span className="flex shrink-0 items-center gap-1.5 text-muted"><span className="flex size-[18px] items-center justify-center rounded-[5px] bg-navy text-[9px] font-bold text-white">{ws.name[0]}</span><span className="hidden lg:inline">{ws.name}</span></span>
      {crumbs.map((c, i) => (
        <span key={i} className="flex min-w-0 items-center gap-1.5">
          <ChevronRight className="size-3.5 shrink-0 text-slate-300" />
          {c.to && i < crumbs.length - 1 ? <Link to={c.to} className="truncate text-muted transition-colors hover:text-navy">{c.label}</Link> : <span className={cn('truncate', i === crumbs.length - 1 ? 'font-semibold text-navy' : 'text-muted')}>{c.label}</span>}
        </span>
      ))}
    </nav>
  )
}

function ContextChip() {
  const s = useStore()
  const p = s.currentProject
  if (!p) return null
  return (
    <Tooltip content="Your role in the current project. It changes navigation, widgets and actions." side="bottom">
      <span className="hidden items-center gap-2 rounded-full border border-line bg-white py-1 pl-1 pr-2.5 text-[12px] font-medium text-navy 2xl:flex">
        <span className="flex size-5 items-center justify-center rounded-full text-[8.5px] font-bold text-white" style={{ background: p.color }}>{p.code.slice(0, 2)}</span>
        {p.name.split(' ')[0]}<span className="text-slate-300">·</span><span className={cn('flex items-center gap-1', { manager: 'text-brand', outgoing: 'text-amber-700', incoming: 'text-teal-700' }[p.role])}><span className={cn('size-1.5 rounded-full', { manager: 'bg-brand', outgoing: 'bg-warn', incoming: 'bg-ok' }[p.role])} />{ROLE_LABEL[p.role]}</span>
      </span>
    </Tooltip>
  )
}

function NotificationsMenu() {
  const s = useStore()
  const unread = s.notifications.filter((n) => !n.read)
  return (
    <Dropdown width="w-[340px] max-w-[calc(100vw-24px)]" trigger={() => <IconButton icon={Bell} label="Notifications" badge={unread.length} />}>
      {(close) => (
        <div>
          <div className="flex items-center justify-between px-3 py-2">
            <p className="text-sm font-semibold text-navy">Notifications</p>
            <button className="text-xs font-medium text-brand hover:underline" onClick={() => s.setNotifications((ns) => ns.map((n) => ({ ...n, read: true })))}>Mark all read</button>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {s.notifications.slice(0, 5).map((n) => (
              <button key={n.id} onClick={() => { s.setNotifications((ns) => ns.map((x) => (x.id === n.id ? { ...x, read: true } : x))); close(); navigate(n.link) }} className="flex w-full gap-2.5 rounded-lg px-3 py-2.5 text-left hover:bg-tint">
                <span className={cn('mt-1.5 size-2 shrink-0 rounded-full', n.read ? 'bg-transparent' : 'bg-brand')} />
                <span className="min-w-0"><span className="block text-[13px] font-medium text-navy">{n.title}</span><span className="line-clamp-2 block text-xs text-muted">{n.body}</span><span className="text-[11px] text-slate-400">{n.time}</span></span>
              </button>
            ))}
          </div>
          <button onClick={() => { close(); navigate('/notifications') }} className="mt-1 flex w-full items-center justify-center gap-1 border-t border-line py-2 text-[13px] font-medium text-brand">View all <ArrowRight className="size-3.5" /></button>
        </div>
      )}
    </Dropdown>
  )
}

function CommandPalette() {
  const s = useStore()
  const [q, setQ] = useState('')
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); s.setPaletteOpen(true) }
      if (e.key === 'Escape') s.setPaletteOpen(false)
    }
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [s])
  useEffect(() => { if (!s.paletteOpen) setQ('') }, [s.paletteOpen])
  const results = useMemo(() => {
    const t = q.toLowerCase().trim()
    const has = (x: string) => !t || x.toLowerCase().includes(t)
    const pids = new Set(s.projects.map((p) => p.id))
    const groups = [
      { label: 'Projects', icon: FolderKanban, items: s.projects.filter((p) => has(p.name)).map((p) => ({ title: p.name, sub: ROLE_LABEL[p.role], to: `/projects/${p.id}` })) },
      { label: 'Handovers', icon: Workflow, items: s.handovers.filter((h) => has(`${h.code} ${personById(h.outgoingId).name} ${personById(h.incomingId).name} ${h.scope}`)).map((h) => ({ title: `${h.code} · ${personById(h.outgoingId).name} → ${personById(h.incomingId).name}`, sub: HANDOVER_STATUS_LABEL[h.status], to: `/handovers/${h.id}` })) },
      { label: 'Knowledge', icon: Sparkles, items: [...decisions.map((d) => ({ ...d, k: 'decisions', l: 'Decision' })), ...tasks.map((d) => ({ ...d, k: 'tasks', l: 'Task' })), ...risks.map((d) => ({ ...d, k: 'risks', l: 'Risk' }))].filter((f) => pids.has(f.projectId) && has(f.title)).map((f) => ({ title: f.title, sub: f.l, to: `/projects/${f.projectId}/intelligence/${f.k}?id=${f.id}` })) },
      { label: 'Evidence', icon: FileSearch, items: evidence.filter((e) => pids.has(e.projectId) && has(e.title + e.ref)).map((e) => ({ title: e.title, sub: e.ref, to: `/projects/${e.projectId}/evidence/${e.id}` })) },
    ]
    return groups.map((g) => ({ ...g, items: g.items.slice(0, t ? 6 : 3) })).filter((g) => g.items.length)
  }, [q, s.projects, s.handovers])
  if (!s.paletteOpen) return null
  const first = results[0]?.items[0]
  return (
    <div className="fixed inset-0 z-[70] flex items-start justify-center bg-navy/30 p-3 pt-[10vh] backdrop-blur-[2px]" onMouseDown={() => s.setPaletteOpen(false)}>
      <div className="animate-fade w-full max-w-xl overflow-hidden rounded-2xl bg-white shadow-pop" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 border-b border-line px-4">
          <Search className="size-5 text-slate-400" />
          <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && first) { navigate(first.to); s.setPaletteOpen(false) } }} placeholder="Search projects, handovers, knowledge and evidence…" className="h-14 flex-1 bg-transparent text-[15px] text-navy outline-none placeholder:text-slate-400" />
          <kbd className="rounded border border-line px-1.5 text-[11px] text-slate-500">Esc</kbd>
        </div>
        <div className="max-h-[60vh] overflow-y-auto p-2">
          {results.length === 0 ? (
            <div className="px-4 py-10 text-center"><p className="text-sm font-medium text-navy">No results for “{q}”</p><p className="mt-1 text-xs text-muted">Try a project name, handover code (HO-1042) or evidence reference.</p></div>
          ) : results.map((g) => (
            <div key={g.label} className="mb-2">
              <p className="px-2.5 py-1.5 text-[11px] font-medium uppercase tracking-wide text-slate-400">{g.label}</p>
              {g.items.map((i) => (
                <button key={i.to + i.title} onClick={() => { navigate(i.to); s.setPaletteOpen(false) }} className="group flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left hover:bg-tint">
                  <span className="flex size-7 items-center justify-center rounded-md bg-slate-100 text-slate-500 group-hover:bg-white group-hover:text-brand"><g.icon className="size-3.5" /></span>
                  <span className="min-w-0 flex-1"><span className="block truncate text-[13px] font-medium text-navy">{i.title}</span><span className="block truncate text-[11px] text-muted">{i.sub}</span></span>
                  <ArrowRight className="size-3.5 text-slate-300 group-hover:text-brand" />
                </button>
              ))}
            </div>
          ))}
        </div>
        <div className="flex items-center gap-4 border-t border-line bg-slate-50/70 px-4 py-2 text-[11px] text-muted"><span><kbd className="font-sans">↵</kbd> open first result</span><span>Results respect your project permissions</span></div>
      </div>
    </div>
  )
}

export function Toaster() {
  const { toasts } = useStore()
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[80] flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2">
      {toasts.map((t) => {
        const I = t.tone === 'success' ? CheckCircle2 : t.tone === 'error' ? XCircle : Info
        return (
          <div key={t.id} role="status" className="animate-fade pointer-events-auto flex items-start gap-3 rounded-xl border border-line bg-white p-3.5 shadow-pop">
            <I className={cn('mt-0.5 size-5 shrink-0', t.tone === 'success' ? 'text-ok' : t.tone === 'error' ? 'text-bad' : 'text-brand')} />
            <div className="min-w-0"><p className="text-sm font-semibold text-navy">{t.title}</p>{t.body && <p className="mt-0.5 text-[13px] text-muted">{t.body}</p>}</div>
          </div>
        )
      })}
    </div>
  )
}

export function Shell({ crumbs, children, wide }: { crumbs: { label: string; to?: string }[]; children: ReactNode; wide?: boolean }) {
  const s = useStore()
  const [mobile, setMobile] = useState(false)
  const me = personById(ME)
  return (
    <div className="flex h-dvh overflow-hidden bg-canvas">
      <aside className={cn('no-print hidden shrink-0 border-r border-[#dbe3f0] bg-tint transition-[width] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] lg:block', s.collapsed ? 'w-[64px]' : 'w-[248px]')}>
        <SidebarContent collapsed={s.collapsed} />
      </aside>
      {mobile && (
        <div className="fixed inset-0 z-[60] bg-navy/30 lg:hidden" onClick={() => setMobile(false)}>
          <aside className="animate-slide-left h-full w-[280px] bg-[#EDF2FA] shadow-pop" onClick={(e) => e.stopPropagation()}>
            <button onClick={() => setMobile(false)} className="absolute left-[244px] top-4 rounded-lg p-1 text-muted" aria-label="Close menu"><X className="size-5" /></button>
            <SidebarContent collapsed={false} onNavigate={() => setMobile(false)} />
          </aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="no-print flex h-[60px] shrink-0 items-center gap-2 border-b border-line/80 bg-white/85 px-3 backdrop-blur-xl sm:px-5">
          <IconButton icon={Menu} label="Open menu" className="lg:hidden" onClick={() => setMobile(true)} />
          <IconButton icon={s.collapsed ? ChevronsRight : ChevronsLeft} label={s.collapsed ? 'Expand sidebar' : 'Collapse sidebar'} className="hidden lg:inline-flex" onClick={() => s.setCollapsed(!s.collapsed)} />
          <Link to="/dashboard" className="lg:hidden md:hidden"><Logo size={24} /></Link>
          <Breadcrumbs crumbs={crumbs} />
          <div className="ml-auto flex items-center gap-1">
            <button onClick={() => s.setPaletteOpen(true)} className="mr-1 hidden h-9 w-60 items-center gap-2 rounded-[9px] border border-line bg-slate-50/80 px-3 text-[13px] text-slate-400 hover:border-slate-300 xl:flex"><Search className="size-4" />Search everything<kbd className="ml-auto rounded border border-line bg-white px-1.5 text-[10px]">⌘K</kbd></button>
            <IconButton icon={Search} label="Search" className="xl:hidden" onClick={() => s.setPaletteOpen(true)} />
            <ContextChip />
            <Tooltip content="Prototype content. Production replaces this with live backend data." side="bottom"><span className="mr-1 hidden rounded-full border border-dashed border-slate-300 px-2 py-0.5 text-[11px] font-medium text-slate-500 sm:inline">Sample data</span></Tooltip>
            <NotificationsMenu />
            <Dropdown trigger={() => <IconButton icon={CircleHelp} label="Help" className="hidden sm:inline-flex" />}>
              {(close) => (<div>
                <MenuItem icon={BookOpen} onClick={() => { close(); navigate('/flows') }}>Prototype flows</MenuItem>
                <MenuItem icon={Sparkles} onClick={() => { close(); navigate('/brand') }}>3D Brand & Launch Studio</MenuItem>
                <MenuItem icon={Palette} onClick={() => { close(); navigate('/design-system') }}>Design system</MenuItem>
                <MenuItem icon={Keyboard} onClick={() => { close(); s.setPaletteOpen(true) }} hint={<kbd className="text-[11px] text-slate-400">⌘K</kbd>}>Keyboard shortcuts</MenuItem>
                <MenuItem icon={LifeBuoy} onClick={() => { close(); s.toast('Support request opened', 'Our team typically replies within 2 hours.', 'info') }}>Contact support</MenuItem>
              </div>)}
            </Dropdown>
            <Dropdown width="w-60" trigger={() => <button className="ml-1 flex items-center gap-1.5 rounded-full p-0.5 pr-1.5 hover:bg-tint" aria-label="Account menu"><Avatar id={ME} size={30} /><ChevronDown className="hidden size-3.5 text-slate-400 sm:block" /></button>}>
              {(close) => (<div>
                <div className="flex items-center gap-2.5 px-2.5 py-2"><Avatar id={ME} size={34} /><div className="min-w-0"><p className="truncate text-sm font-semibold text-navy">{me.name}</p><p className="truncate text-xs text-muted">{me.email}</p></div></div>
                <div className="my-1 border-t border-line" />
                <MenuItem icon={User} onClick={() => { close(); navigate('/settings/profile') }}>Profile & account</MenuItem>
                <MenuItem icon={Settings} onClick={() => { close(); navigate('/settings') }}>Settings</MenuItem>
                <MenuItem icon={ShieldCheck} onClick={() => { close(); navigate('/settings/audit-logs') }}>Audit logs</MenuItem>
                <MenuItem icon={HelpCircle} onClick={() => { close(); navigate('/flows') }}>Prototype flows</MenuItem>
                <div className="my-1 border-t border-line" />
                <MenuItem icon={LogOut} danger onClick={() => { close(); s.setAuthed(false); navigate('/login') }}>Sign out</MenuItem>
              </div>)}
            </Dropdown>
          </div>
        </header>
        <main id="main-scroll" className="ambient-canvas scrollbar-thin flex-1 overflow-y-auto">
          <div key={crumbs.map((c) => c.label).join('/')} className={cn('animate-fade mx-auto w-full px-4 py-6 sm:px-6 lg:px-8 lg:py-8', wide ? 'max-w-[1600px]' : 'max-w-[1360px]')}>{children}</div>
        </main>
      </div>
      <CommandPalette />
    </div>
  )
}
