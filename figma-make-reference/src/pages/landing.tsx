import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from 'react'
import { ArrowDown, ArrowRight, BookOpen, Check, ChevronDown, CircleAlert, ClipboardCheck, Compass, FileText, GitPullRequest, History, Layers, Link2, ListTodo, Lock, Menu, MessageSquare, Network, Plug, RefreshCw, Rocket, ScrollText, Search, ShieldCheck, Sparkles, SquareKanban, UserRound, Users, Workflow, X, AlertTriangle, Lightbulb, GitCommitHorizontal, Eye, Inbox, Send } from 'lucide-react'
import { Logo, LogoMark, SourceIcon } from '@/components/brand'
import { cn } from '@/components/ui'
import { navigate } from '@/lib/router'

const OrganicScene = lazy(() => import('@/components/OrganicScene'))

/** Lightweight placeholder shown while the 3D scene loads, and the no-JS fallback. Shares the sphere's material language. */
function StaticOrb({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center justify-center', className)} aria-hidden>
      <div className="relative aspect-square w-[68%] rounded-full" style={{ background: 'radial-gradient(circle at 32% 28%, rgba(255,255,255,0.95), rgba(237,242,250,0.6) 52%, rgba(165,160,217,0.25) 84%, rgba(121,151,190,0.34))', boxShadow: '0 40px 60px -40px rgba(32,54,83,0.35), inset 0 0 40px rgba(217,233,229,0.6)' }} />
    </div>
  )
}
function Scene(props: { variant: 'hero' | 'assemble' | 'network' | 'continuity'; className?: string; accent?: string; label?: string }) {
  return <Suspense fallback={<StaticOrb className={props.className} />}><OrganicScene {...props} /></Suspense>
}

/* ---------- primitives ---------- */
function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && (e.target.classList.add('is-in'), io.unobserve(e.target))), { threshold: 0.12 })
    el.querySelectorAll('.reveal').forEach((n) => io.observe(n))
    return () => io.disconnect()
  }, [])
  return ref
}
const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })

function Eyebrow({ children, tone = 'blue' }: { children: ReactNode; tone?: 'blue' | 'ai' | 'ok' }) {
  const c = { blue: 'text-brand', ai: 'text-ai', ok: 'text-ok' }[tone]
  return <p className={cn('flex items-center gap-2 text-[12.5px] font-semibold uppercase tracking-[0.16em]', c)}><span className="h-px w-6 bg-current opacity-60" />{children}</p>
}
function H2({ children, className }: { children: ReactNode; className?: string }) {
  return <h2 className={cn('text-[34px] font-semibold leading-[1.06] tracking-[-0.035em] text-navy sm:text-[44px] lg:text-[52px]', className)}>{children}</h2>
}
function Lead({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn('text-[17px] leading-[1.65] text-[#56657c] sm:text-[18px]', className)}>{children}</p>
}
function Primary({ children, onClick, className }: { children: ReactNode; onClick?: () => void; className?: string }) {
  return <button onClick={onClick} className={cn('group inline-flex h-12 items-center gap-2 rounded-[10px] bg-navy px-5 text-[15px] font-semibold text-white shadow-[0_1px_0_rgba(255,255,255,0.1)_inset,0_8px_20px_-8px_rgba(32,54,83,0.5)] transition-all duration-200 hover:bg-[#2a4467] active:scale-[0.98]', className)}>{children}<ArrowRight className="size-4 transition-transform duration-200 group-hover:translate-x-0.5" /></button>
}
const Wrap = ({ children, className }: { children: ReactNode; className?: string }) => <div className={cn('mx-auto w-full max-w-[1240px] px-5 sm:px-8', className)}>{children}</div>

/* ---------- navigation ---------- */
const PRODUCT_MENU = [
  { icon: Network, title: 'Knowledge Explorer', body: 'See how decisions, people and systems connect', id: 'explorer' },
  { icon: Sparkles, title: 'Knowledge intelligence', body: 'Decisions, responsibilities, risks, dependencies', id: 'intelligence' },
  { icon: Workflow, title: 'Structured handovers', body: 'Verified, publishable transition documents', id: 'handovers' },
  { icon: ShieldCheck, title: 'Evidence & verification', body: 'Every finding traced to its source', id: 'security' },
]
const SOLUTIONS_MENU = [
  { icon: Compass, title: 'Project managers', body: 'See every transition clearly', id: 'roles' },
  { icon: Send, title: 'Outgoing members', body: 'Leave the knowledge, not just the role', id: 'roles' },
  { icon: Inbox, title: 'Incoming members', body: 'Step into the project with context', id: 'roles' },
]

function NavDropdown({ label, items }: { label: string; items: typeof PRODUCT_MENU }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="relative" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button onClick={() => setOpen(!open)} aria-expanded={open} className="flex h-10 items-center gap-1 rounded-lg px-3 text-[14.5px] font-medium text-[#3e5373] transition hover:text-navy">{label}<ChevronDown className={cn('size-3.5 transition-transform duration-200', open && 'rotate-180')} /></button>
      <div className={cn('absolute left-1/2 top-full w-[380px] -translate-x-1/2 pt-2 transition-all duration-200', open ? 'visible translate-y-0 opacity-100' : 'invisible -translate-y-1 opacity-0')}>
        <div className="rounded-2xl border border-line bg-white p-2 shadow-pop">
          {items.map((i) => (
            <button key={i.title} onClick={() => { setOpen(false); scrollTo(i.id) }} className="flex w-full items-start gap-3 rounded-xl p-3 text-left transition hover:bg-canvas">
              <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border border-line bg-white text-brand"><i.icon className="size-4" /></span>
              <span><span className="block text-[14px] font-semibold text-navy">{i.title}</span><span className="block text-[13px] text-muted">{i.body}</span></span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function Nav() {
  const [scrolled, setScrolled] = useState(false)
  const [mobile, setMobile] = useState(false)
  useEffect(() => { const on = () => setScrolled(window.scrollY > 8); on(); window.addEventListener('scroll', on, { passive: true }); return () => window.removeEventListener('scroll', on) }, [])
  return (
    <header className={cn('sticky top-0 z-50 transition-all duration-300', scrolled ? 'border-b border-line/80 bg-white/80 backdrop-blur-xl' : 'border-b border-transparent bg-transparent')}>
      <Wrap className="flex h-[78px] items-center">
        <button onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} aria-label="Handover home"><Logo size={28} /></button>
        <nav className="mx-auto hidden items-center gap-1 lg:flex" aria-label="Primary">
          <NavDropdown label="Product" items={PRODUCT_MENU} />
          <button onClick={() => scrollTo('how')} className="h-10 rounded-lg px-3 text-[14.5px] font-medium text-[#3e5373] transition hover:text-navy">How it works</button>
          <NavDropdown label="Solutions" items={SOLUTIONS_MENU} />
          <button onClick={() => scrollTo('security')} className="h-10 rounded-lg px-3 text-[14.5px] font-medium text-[#3e5373] transition hover:text-navy">Security</button>
        </nav>
        <div className="ml-auto hidden items-center gap-2 lg:ml-0 lg:flex">
          <button onClick={() => navigate('/login')} className="h-10 rounded-lg px-4 text-[14.5px] font-semibold text-navy transition hover:bg-white/70">Log in</button>
          <button onClick={() => navigate('/signup')} className="group inline-flex h-10 items-center gap-1.5 rounded-[10px] bg-brand px-4 text-[14.5px] font-semibold text-white transition hover:bg-brand-dark">Get started<ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" /></button>
        </div>
        <button onClick={() => setMobile(true)} className="ml-auto flex size-10 items-center justify-center rounded-lg text-navy lg:hidden" aria-label="Open menu"><Menu className="size-5" /></button>
      </Wrap>
      {mobile && (
        <div className="animate-fade-only fixed inset-0 z-50 bg-navy/25 backdrop-blur-sm lg:hidden" onClick={() => setMobile(false)}>
          <div className="animate-slide ml-auto flex h-full w-[86%] max-w-sm flex-col bg-white p-5 shadow-pop" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between"><Logo size={26} /><button onClick={() => setMobile(false)} className="flex size-10 items-center justify-center rounded-lg" aria-label="Close menu"><X className="size-5" /></button></div>
            <div className="mt-8 space-y-1">
              <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Product</p>
              {PRODUCT_MENU.map((i) => <button key={i.title} onClick={() => { setMobile(false); setTimeout(() => scrollTo(i.id), 50) }} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-[15px] font-medium text-navy hover:bg-canvas"><i.icon className="size-4 text-brand" />{i.title}</button>)}
              <p className="px-3 pb-1 pt-4 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Explore</p>
              {[['How it works', 'how'], ['Solutions', 'roles'], ['Security', 'security'], ['FAQ', 'faq']].map(([l, id]) => <button key={id} onClick={() => { setMobile(false); setTimeout(() => scrollTo(id), 50) }} className="block w-full rounded-xl px-3 py-2.5 text-left text-[15px] font-medium text-navy hover:bg-canvas">{l}</button>)}
            </div>
            <div className="mt-auto space-y-2">
              <button onClick={() => navigate('/signup')} className="flex h-12 w-full items-center justify-center gap-2 rounded-[10px] bg-brand text-[15px] font-semibold text-white">Get started<ArrowRight className="size-4" /></button>
              <button onClick={() => navigate('/login')} className="h-12 w-full rounded-[10px] border border-line text-[15px] font-semibold text-navy">Log in</button>
            </div>
          </div>
        </div>
      )}
    </header>
  )
}

/* ---------- hero ---------- */
const SRC = [{ t: 'github' as const, label: 'Pull requests', y: 132 }, { t: 'jira' as const, label: 'Sprint issues', y: 212 }, { t: 'slack' as const, label: 'Discussions', y: 292 }, { t: 'docs' as const, label: 'ADRs & runbooks', y: 372 }]
const OUT = [{ icon: Lightbulb, label: 'Decisions', c: '#315FBA', y: 122 }, { icon: UserRound, label: 'Responsibilities', c: '#299B80', y: 192 }, { icon: AlertTriangle, label: 'Risks', c: '#D36D72', y: 262 }, { icon: Network, label: 'Dependencies', c: '#D39B43', y: 332 }, { icon: ShieldCheck, label: 'Verified knowledge', c: '#203653', y: 402 }]
const P = (x: number, y: number) => ({ left: `${(x / 640) * 100}%`, top: `${(y / 560) * 100}%` })

export function HeroVisual() {
  return (
    <div className="relative mx-auto aspect-[640/560] w-full max-w-[640px]">
      <div className="absolute inset-[6%] rounded-[32px] opacity-80" style={{ background: 'radial-gradient(ellipse at 50% 45%, rgba(165,160,217,0.22), transparent 60%), radial-gradient(ellipse at 30% 70%, rgba(121,151,190,0.18), transparent 55%)' }} />
      <svg viewBox="0 0 640 560" className="absolute inset-0 h-full w-full" aria-hidden>
        <circle cx="320" cy="262" r="118" fill="none" stroke="#D9E1F0" strokeDasharray="2 5" />
        <circle cx="320" cy="262" r="78" fill="none" stroke="#D9E1F0" />
        {SRC.map((s) => <g key={s.t}><path d={`M150 ${s.y} C 220 ${s.y}, 230 262, 276 262`} fill="none" stroke="#C3D2EC" strokeWidth="1.2" /><path d={`M150 ${s.y} C 220 ${s.y}, 230 262, 276 262`} fill="none" stroke="#7997BE" strokeWidth="1.2" className="animate-flow" /></g>)}
        {OUT.map((o) => <g key={o.label}><path d={`M364 262 C 410 262, 420 ${o.y}, 470 ${o.y}`} fill="none" stroke="#D9E1F0" strokeWidth="1.2" /><circle cx="470" cy={o.y} r="2.5" fill={o.c} /></g>)}
        <path d="M96 62 C 96 100, 96 100, 108 108" fill="none" stroke="#C3D2EC" strokeDasharray="3 4" />
        <path d="M556 452 C 556 470, 556 476, 556 486" fill="none" stroke="#C3D2EC" strokeDasharray="3 4" />
      </svg>
      <div className="absolute flex -translate-y-1/2 items-center gap-2.5 rounded-full border border-line bg-white py-1.5 pl-1.5 pr-3.5 shadow-card" style={P(22, 44)}>
        <span className="flex size-7 items-center justify-center rounded-full bg-[#203653] text-[11px] font-bold text-white">JO</span>
        <span className="text-[12px] leading-tight"><span className="block font-semibold text-navy">James Okafor</span><span className="text-muted">Outgoing · leaves Jun 30</span></span>
      </div>
      {SRC.map((s) => (
        <div key={s.t} className="absolute flex -translate-y-1/2 items-center gap-2 rounded-xl border border-line bg-white py-1.5 pl-1.5 pr-3 shadow-card" style={P(18, s.y)}>
          <SourceIcon type={s.t} size={26} /><span className="whitespace-nowrap text-[12px] font-medium text-navy">{s.label}</span>
        </div>
      ))}
      <div className="absolute flex size-[15%] -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-[22px] border border-line bg-white shadow-lift" style={P(320, 262)}>
        <LogoMark size={44} />
      </div>
      <p className="absolute -translate-x-1/2 whitespace-nowrap font-mono text-[10.5px] text-muted" style={P(320, 318)}>extract · link · verify</p>
      {OUT.map((o) => (
        <div key={o.label} className="absolute flex -translate-y-1/2 items-center gap-2 rounded-lg border border-line bg-white px-2.5 py-1.5 shadow-card" style={P(478, o.y)}>
          <o.icon className="size-3.5" style={{ color: o.c }} /><span className="whitespace-nowrap text-[12px] font-semibold text-navy">{o.label}</span>
        </div>
      ))}
      <div className="absolute -translate-y-1/2 rounded-full border border-line bg-white py-1.5 pl-1.5 pr-3.5 shadow-card" style={{ ...P(440, 502) }}>
        <span className="flex items-center gap-2.5"><span className="flex size-7 items-center justify-center rounded-full bg-[#315FBA] text-[11px] font-bold text-white">PN</span><span className="text-[12px] leading-tight"><span className="block font-semibold text-navy">Priya Nair</span><span className="text-muted">Incoming · starts with context</span></span></span>
      </div>
      <div className="absolute w-[47%] rounded-2xl border border-line bg-white p-3.5 shadow-pop" style={P(40, 430)}>
        <div className="flex items-center justify-between"><span className="flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-[0.1em] text-brand"><Lightbulb className="size-3" />Decision</span><span className="font-mono text-[10px] text-muted">HO-1042</span></div>
        <p className="mt-1.5 text-[13px] font-semibold leading-snug text-navy">Decouple settlement from the ledger with Kafka events</p>
        <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
          <span className="inline-flex items-center gap-1 rounded-md border border-dashed border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[10.5px] font-medium text-indigo-700"><Sparkles className="size-2.5" />AI 94%</span>
          <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-1.5 py-0.5 text-[10.5px] font-medium text-teal-700 ring-1 ring-inset ring-teal-600/15"><ShieldCheck className="size-2.5" />Verified</span>
          <span className="font-mono text-[10px] text-muted">3 sources</span>
        </div>
      </div>
    </div>
  )
}

function Hero() {
  return (
    <section className="ambient-hero relative overflow-hidden pb-16 pt-8 sm:pt-12 lg:pb-24">
      <Wrap className="relative grid grid-cols-1 items-center gap-6 [&>*]:min-w-0 lg:grid-cols-[45fr_55fr] lg:gap-4">
        <div className="animate-fade relative z-10 lg:py-10">
          <span className="inline-flex items-center gap-2 rounded-full border border-line bg-white/80 px-3 py-1 text-[12.5px] font-semibold text-[#3e5373] backdrop-blur"><span className="size-1.5 rounded-full bg-ok" />Project knowledge continuity</span>
          <h1 className="mt-6 text-[42px] font-semibold leading-[1.02] tracking-[-0.045em] text-navy sm:text-[58px] lg:text-[68px] xl:text-[74px]">Your team's knowledge shouldn't leave when people do.</h1>
          <Lead className="mt-6 max-w-[520px]">Projects are built on decisions, conversations, responsibilities and experience. Handover brings that knowledge together, verifies what matters and makes every transition seamless.</Lead>
          <div className="mt-9 flex flex-wrap items-center gap-3">
            <Primary onClick={() => navigate('/signup')}>Get started</Primary>
            <button onClick={() => scrollTo('how')} className="group inline-flex h-12 items-center gap-2 rounded-[10px] px-4 text-[15px] font-semibold text-navy transition hover:bg-canvas">Discover how it works<ArrowDown className="size-4 transition-transform group-hover:translate-y-0.5" /></button>
          </div>
          <p className="mt-10 flex flex-wrap items-center gap-x-5 gap-y-2 text-[13px] text-muted"><span className="flex items-center gap-1.5"><Plug className="size-3.5" />GitHub · Jira · Slack · Docs</span><span className="flex items-center gap-1.5"><ShieldCheck className="size-3.5" />Human-verified findings</span></p>
        </div>
        <div className="animate-fade relative [animation-delay:200ms]">
          <Scene variant="hero" className="mx-auto aspect-square w-full max-w-[340px] sm:max-w-[520px] lg:max-w-[720px]" label="Organic knowledge sphere: decisions, responsibilities, risks and dependencies connected into verified project knowledge" />
          <p className="pointer-events-none mt-1 text-center font-mono text-[11px] tracking-[0.18em] text-sky lg:-mt-6">KNOWLEDGE CONTINUES.</p>
        </div>
      </Wrap>
    </section>
  )
}

/* ---------- problem ---------- */
function Problem() {
  const ref = useReveal<HTMLElement>()
  const rows = [
    { n: '01', title: 'Scattered knowledge', body: 'Critical information is distributed across repositories, conversations and documents, with no single owner and no single place.', visual: (
      <div className="relative h-40 w-full">
        {[['github', 8, 18, -6], ['slack', 62, 6, 5], ['jira', 30, 58, -3], ['docs', 74, 60, 8]].map(([t, x, y, r]) => <div key={t as string} className="absolute flex items-center gap-2 rounded-xl border border-line bg-white px-2.5 py-2 shadow-card" style={{ left: `${x}%`, top: `${y}%`, transform: `rotate(${r}deg)` }}><SourceIcon type={t as 'github'} size={22} /><span className="h-1.5 w-12 rounded-full bg-slate-100" /></div>)}
        <svg className="absolute inset-0 h-full w-full" aria-hidden><path d="M90 50 L160 42" stroke="#D9E1F0" strokeDasharray="3 5" /><path d="M150 110 L230 112" stroke="#D9E1F0" strokeDasharray="3 5" /></svg>
      </div>) },
    { n: '02', title: 'Lost context', body: 'Teams inherit decisions without understanding why they were made: the constraints, the trade-offs, the alternatives that were rejected.', visual: (
      <div className="w-full max-w-[300px] rounded-2xl border border-line bg-white p-4 shadow-card">
        <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted">Decision · 2024</p>
        <p className="mt-1 text-[14px] font-semibold text-navy">Use logical replication for replicas</p>
        <p className="mt-3 text-[11px] font-semibold text-slate-400">WHY?</p>
        <div className="mt-1.5 space-y-1.5">{[90, 70, 82].map((w, i) => <span key={i} className="block h-2 rounded-full bg-slate-100" style={{ width: `${w}%` }} />)}</div>
        <p className="mt-3 flex items-center gap-1.5 text-[11.5px] text-red-600"><CircleAlert className="size-3" />Author left the project</p>
      </div>) },
    { n: '03', title: 'Repeated work', body: 'Incoming members spend their first weeks rediscovering what already existed, re-asking questions that were answered long ago.', visual: (
      <div className="flex w-full max-w-[300px] items-center gap-4">
        <svg width="96" height="96" viewBox="0 0 96 96" aria-hidden><circle cx="48" cy="48" r="36" fill="none" stroke="#EDF1F8" strokeWidth="8" /><path d="M48 12 A36 36 0 1 1 13 40" fill="none" stroke="#D39B43" strokeWidth="3" strokeLinecap="round" /><path d="M8 33 l5 7 7-5" fill="none" stroke="#D39B43" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /><RefreshCw x="36" y="36" width="24" height="24" color="#D39B43" /></svg>
        <div className="space-y-2 text-[12.5px]">{['Where is the deploy runbook?', 'Who owns Kafka retention?', 'Why are these tests skipped?'].map((q) => <p key={q} className="rounded-lg border border-line bg-white px-2.5 py-1.5 text-[#56657c]">{q}</p>)}</div>
      </div>) },
  ]
  return (
    <section ref={ref} className="border-t border-line/70 bg-white py-24 sm:py-32">
      <Wrap className="grid gap-14 grid-cols-1 [&>*]:min-w-0 lg:grid-cols-[0.9fr_1.1fr] lg:gap-20">
        <div className="lg:sticky lg:top-32 lg:self-start">
          <div className="reveal"><Eyebrow>The problem</Eyebrow></div>
          <H2 className="reveal mt-5">Projects don't lose progress. They lose context.</H2>
          <Lead className="reveal mt-6 max-w-md">When someone moves on, the next person doesn't just inherit tasks. They inherit decisions, assumptions, dependencies and years of accumulated understanding.</Lead>
        </div>
        <ol className="divide-y divide-line border-y border-line">
          {rows.map((r) => (
            <li key={r.n} className="reveal grid gap-6 py-10 sm:grid-cols-[1fr_300px] sm:items-center">
              <div><p className="font-mono text-[13px] text-sky">{r.n}</p><h3 className="mt-2 text-[26px] font-semibold tracking-[-0.025em] text-navy">{r.title}</h3><p className="mt-2.5 max-w-sm text-[15.5px] leading-relaxed text-[#56657c]">{r.body}</p></div>
              <div className="flex justify-start sm:justify-end">{r.visual}</div>
            </li>
          ))}
        </ol>
      </Wrap>
    </section>
  )
}

/* ---------- introducing ---------- */
function Introducing() {
  const ref = useReveal<HTMLElement>()
  return (
    <section ref={ref} id="product" className="ambient-section relative overflow-hidden py-24 sm:py-32">
      <Wrap className="relative">
        <div className="mx-auto max-w-3xl text-center">
          <div className="reveal flex justify-center"><Eyebrow>Introducing Handover</Eyebrow></div>
          <H2 className="reveal mt-5">One place for everything your project knows.</H2>
          <Lead className="reveal mx-auto mt-6 max-w-2xl">Handover brings your project's scattered information together, reconstructs the knowledge behind the work and makes it accessible to the people moving it forward.</Lead>
        </div>
        <div className="reveal relative mx-auto mt-12 max-w-[1100px]">
          <Scene variant="assemble" className="h-[220px] w-full sm:h-[300px]" label="Scattered project information elements gradually forming one connected knowledge structure" />
          <div className="pointer-events-none absolute inset-x-0 bottom-2 flex justify-between px-2 font-mono text-[11px] text-muted sm:px-6"><span>scattered across tools</span><span>connected by Handover</span></div>
        </div>
        <div className="reveal mt-10 grid gap-4 lg:grid-cols-[1fr_auto_1.15fr_auto_1.2fr] lg:items-stretch">
          <div className="tile rounded-[16px] border p-6">
            <p className="font-mono text-[11.5px] text-muted">01 · Connected sources</p>
            <ul className="mt-5 space-y-2.5">{([['github', 'atlas-settlement', '4,820 records'], ['jira', 'PAY · PAYOPS', '1,312 records'], ['slack', '#payments-arch', '9,240 messages'], ['docs', 'ADRs · Runbooks', '38 files']] as const).map(([t, n, c]) => <li key={t} className="flex items-center gap-3"><SourceIcon type={t} size={30} /><span className="flex-1"><span className="block font-mono text-[12.5px] text-navy">{n}</span><span className="text-[11.5px] text-muted">{c}</span></span><span className="size-1.5 rounded-full bg-ok" /></li>)}</ul>
          </div>
          <div className="hidden items-center lg:flex"><ArrowRight className="size-5 text-sky" /></div>
          <div className="relative overflow-hidden rounded-[20px] border border-[#2c4566] bg-navy p-6 text-white shadow-pop">
            <div className="absolute inset-0 opacity-[0.07] dot-grid" />
            <div className="relative">
              <p className="font-mono text-[11.5px] text-[#a9b8d0]">02 · Handover intelligence</p>
              <div className="mt-5 flex items-center gap-3"><span className="flex size-11 items-center justify-center rounded-xl bg-white"><LogoMark size={28} /></span><div><p className="text-[15px] font-semibold">Reconstructing knowledge</p><p className="text-[12px] text-[#a9b8d0]">15,410 records · 6 months</p></div></div>
              <ol className="mt-6 space-y-3">{['Extract decisions, tasks and risks', 'Link findings to their evidence', 'Detect conflicts and knowledge gaps', 'Score AI confidence per finding'].map((x, i) => <li key={x} className="flex items-center gap-3 text-[13px]"><span className={cn('flex size-5 items-center justify-center rounded-full text-[10px] font-bold', i < 3 ? 'bg-ok text-white' : 'border border-[#5a7091] text-[#a9b8d0]')}>{i < 3 ? <Check className="size-3" /> : i + 1}</span><span className={i < 3 ? 'text-white' : 'text-[#a9b8d0]'}>{x}</span></li>)}</ol>
              <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="animate-grow-x h-full w-[78%] rounded-full bg-gradient-to-r from-sky to-iris" /></div>
            </div>
          </div>
          <div className="hidden items-center lg:flex"><ArrowRight className="size-5 text-sky" /></div>
          <div className="tile rounded-[16px] border p-6">
            <p className="font-mono text-[11.5px] text-muted">03 · Structured project knowledge</p>
            <ul className="mt-5 divide-y divide-line">{[[Lightbulb, '#315FBA', 'Decision', 'Event-driven settlement via Kafka', true], [UserRound, '#299B80', 'Responsibility', 'Acquirer credential rotation', true], [AlertTriangle, '#D36D72', 'Risk', 'No retry on acquirer timeouts', false], [Network, '#D39B43', 'Dependency', 'Settlement → Platform Vault', false]].map(([I, c, k, t, v]) => { const Ic = I as typeof Lightbulb; return <li key={t as string} className="flex items-center gap-3 py-2.5"><Ic className="size-4 shrink-0" style={{ color: c as string }} /><span className="min-w-0 flex-1"><span className="block text-[11px] font-medium text-muted">{k as string}</span><span className="block truncate text-[13px] font-semibold text-navy">{t as string}</span></span>{v ? <ShieldCheck className="size-4 text-ok" /> : <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">Review</span>}</li> })}</ul>
          </div>
        </div>
      </Wrap>
    </section>
  )
}

/* ---------- how it works ---------- */
const STEPS = [
  { k: 'Connect', icon: Plug, body: 'Connect GitHub, Jira, Slack and project documentation.' },
  { k: 'Reconstruct', icon: Sparkles, body: 'AI extracts meaningful information from authorised sources.' },
  { k: 'Understand', icon: Compass, body: 'Discover decisions, responsibilities, risks, dependencies and history.' },
  { k: 'Verify', icon: ShieldCheck, body: 'Review findings against supporting evidence and confirm what matters.' },
  { k: 'Transfer', icon: Workflow, body: 'Generate structured handovers that help incoming members understand the project.' },
]
function StepPreview({ i }: { i: number }) {
  const frame = 'rounded-2xl border border-line bg-white p-5 shadow-card'
  if (i === 0) return <div className={frame}><p className="text-[13px] font-semibold text-navy">Select repositories</p><div className="mt-3 space-y-2">{['atlas-ledger', 'atlas-settlement', 'atlas-gateway'].map((r, j) => <label key={r} className="flex items-center gap-2.5 rounded-lg border border-line px-3 py-2"><span className={cn('flex size-4 items-center justify-center rounded', j < 2 ? 'bg-brand text-white' : 'border border-slate-300')}>{j < 2 && <Check className="size-3" />}</span><span className="font-mono text-[12.5px] text-navy">{r}</span></label>)}</div><p className="mt-3 flex items-center gap-1.5 text-[11.5px] text-muted"><Lock className="size-3" />Read-only access · you choose the scope</p></div>
  if (i === 1) return <div className={frame}><div className="flex items-center justify-between text-[13px]"><span className="font-semibold text-navy">Reconstruction</span><span className="font-mono text-muted">78%</span></div><div className="mt-3 h-1.5 rounded-full bg-slate-100"><div className="h-full w-[78%] rounded-full bg-brand" /></div><ul className="mt-4 space-y-2 text-[12.5px]">{[['Collecting evidence', 1], ['Extracting decisions & tasks', 1], ['Linking findings', 0]].map(([l, d]) => <li key={l as string} className="flex items-center gap-2">{d ? <Check className="size-3.5 text-ok" /> : <span className="size-3.5 animate-pulse-soft rounded-full border-2 border-brand" />}<span className={d ? 'text-navy' : 'text-muted'}>{l as string}</span></li>)}</ul></div>
  if (i === 2) return <div className={frame}><div className="grid grid-cols-2 gap-2">{[['Decisions', 6, '#315FBA'], ['Tasks', 8, '#299B80'], ['Risks', 6, '#D36D72'], ['Dependencies', 6, '#D39B43']].map(([l, n, c]) => <div key={l as string} className="rounded-xl bg-canvas p-3"><p className="text-[22px] font-semibold text-navy">{n as number}</p><p className="flex items-center gap-1.5 text-[12px] text-muted"><span className="size-1.5 rounded-full" style={{ background: c as string }} />{l as string}</p></div>)}</div></div>
  if (i === 3) return <div className={frame}><p className="text-[13px] font-semibold text-navy">Settlement worker has no retry on timeouts</p><div className="mt-3 flex gap-2"><span className="rounded-md border border-dashed border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[11px] font-medium text-indigo-700">AI 83%</span><span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">Needs review</span></div><div className="mt-4 flex gap-2"><span className="flex h-8 items-center gap-1.5 rounded-lg bg-ok px-3 text-[12px] font-semibold text-white"><ShieldCheck className="size-3.5" />Verify</span><span className="flex h-8 items-center rounded-lg border border-line px-3 text-[12px] font-semibold text-navy">Edit</span><span className="flex h-8 items-center rounded-lg border border-line px-3 text-[12px] font-semibold text-red-600">Reject</span></div></div>
  return <div className={frame}><div className="flex items-center gap-3"><span className="flex size-8 items-center justify-center rounded-full bg-navy text-[11px] font-bold text-white">JO</span><ArrowRight className="size-4 text-brand" /><span className="flex size-8 items-center justify-center rounded-full bg-brand text-[11px] font-bold text-white">PN</span><span className="ml-auto rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-brand">Published</span></div><p className="mt-3 text-[13px] font-semibold text-navy">HO-1042 · Atlas Payments Platform</p><div className="mt-3 grid grid-cols-6 gap-1">{[1, 1, 1, 1, 1, 0].map((d, j) => <span key={j} className={cn('h-1.5 rounded-full', d ? 'bg-ok' : 'bg-brand')} />)}</div></div>
}
function HowItWorks() {
  const ref = useReveal<HTMLElement>()
  const [active, setActive] = useState(0)
  return (
    <section ref={ref} id="how" className="scroll-mt-20 border-y border-line/70 bg-white py-24 sm:py-32">
      <Wrap>
        <div className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-end">
          <div><div className="reveal"><Eyebrow>How Handover works</Eyebrow></div><H2 className="reveal mt-5 max-w-3xl">From project activity to knowledge that moves forward.</H2></div>
          <p className="reveal text-[14px] text-muted">Select a step to preview it</p>
        </div>
        <ol className="reveal relative mt-16 grid gap-0 lg:grid-cols-5 lg:gap-4">
          <span className="absolute left-0 right-0 top-[19px] hidden h-px bg-line lg:block" />
          <span className="absolute left-0 top-[19px] hidden h-px bg-brand transition-all duration-500 lg:block" style={{ width: `${(active / 4) * 100}%` }} />
          <span className="absolute bottom-0 left-[19px] top-0 w-px bg-line lg:hidden" />
          {STEPS.map((s, i) => (
            <li key={s.k} className="relative pb-8 pl-14 lg:pb-0 lg:pl-0">
              <button onClick={() => setActive(i)} className="group w-full text-left">
                <span className={cn('absolute left-0 top-0 flex size-10 items-center justify-center rounded-full border bg-white transition-all duration-300 lg:relative', i <= active ? 'border-brand text-brand' : 'border-line text-slate-400 group-hover:border-sky', i === active && 'ring-4 ring-brand/10')}><s.icon className="size-4" /></span>
                <p className="font-mono text-[12px] text-muted lg:mt-5">Step {i + 1}</p>
                <h3 className={cn('mt-1 text-[22px] font-semibold tracking-[-0.02em] transition-colors', i === active ? 'text-navy' : 'text-[#56657c]')}>{s.k}</h3>
                <p className="mt-1.5 max-w-[240px] text-[14.5px] leading-relaxed text-muted">{s.body}</p>
              </button>
              <div className="mt-5 lg:hidden">{i === active && <div className="animate-fade"><StepPreview i={i} /></div>}</div>
            </li>
          ))}
        </ol>
        <div className="mt-14 hidden lg:grid lg:grid-cols-5 lg:gap-4"><div key={active} className="animate-fade" style={{ gridColumnStart: Math.min(active + 1, 4), gridColumnEnd: 'span 2' }}><StepPreview i={active} /></div></div>
      </Wrap>
    </section>
  )
}

/* ---------- knowledge intelligence ---------- */
const CATS = [
  { k: 'Decisions', icon: Lightbulb, c: '#315FBA', body: 'Understand what was decided, who made the decision and why.', finding: 'Decouple settlement via Kafka events', meta: 'James Okafor · Mar 6 · 3 sources', ev: [0, 1, 2] },
  { k: 'Responsibilities', icon: UserRound, c: '#299B80', body: 'Understand ownership, completed work and pending tasks.', finding: 'Rotate acquirer API credentials', meta: 'Owner James → Priya · due Jun 30', ev: [3, 2] },
  { k: 'Risks', icon: AlertTriangle, c: '#D36D72', body: 'Identify unresolved problems and potential blockers.', finding: 'No retry on acquirer timeouts', meta: 'Critical · Settlement Worker', ev: [1, 3] },
  { k: 'Dependencies', icon: Network, c: '#D39B43', body: 'Understand relationships between components, tasks and people.', finding: 'SOAP migration blocked by credential rotation', meta: 'Task dependency · blocking', ev: [3, 0] },
]
const FRAGS = [
  { icon: GitPullRequest, src: 'atlas-settlement#412', text: 'Move settlement out of the ledger transaction path…' },
  { icon: MessageSquare, src: '#payments-arch', text: '“Publish ledger events to Kafka and let settlement consume.”' },
  { icon: FileText, src: 'ADR-007.pdf', text: 'Status: Accepted. At-least-once with idempotent writes.' },
  { icon: SquareKanban, src: 'PAY-1204', text: 'Quarterly credential rotation. Blocks PAY-1150.' },
]
function Intelligence() {
  const ref = useReveal<HTMLElement>()
  const [cat, setCat] = useState(0)
  const C = CATS[cat]
  return (
    <section ref={ref} id="intelligence" className="ambient-section relative scroll-mt-20 overflow-hidden py-24 sm:py-32">
      <div className="pointer-events-none absolute inset-y-0 right-0 hidden w-[68%] [mask-image:linear-gradient(90deg,transparent,black_35%)] md:block">
        <Scene variant="network" accent={['49,95,186', '41,155,128', '211,109,114', '211,155,67'][cat]} className="h-full w-full opacity-90" label="Cropped organic network of relationships between project knowledge" />
      </div>
      <Wrap className="relative grid gap-14 grid-cols-1 [&>*]:min-w-0 lg:grid-cols-[0.85fr_1.15fr] lg:gap-16">
        <div>
          <div className="reveal"><Eyebrow tone="ai">Knowledge intelligence</Eyebrow></div>
          <H2 className="reveal mt-5">Understand the thinking behind the work.</H2>
          <Lead className="reveal mt-6">Handover reads authorised project activity and reconstructs it into structured knowledge, with every finding linked to the evidence that produced it.</Lead>
          <div className="reveal mt-10 space-y-1">
            {CATS.map((c, i) => (
              <button key={c.k} onClick={() => setCat(i)} className={cn('flex w-full items-start gap-4 rounded-2xl border p-4 text-left transition-all duration-300', i === cat ? 'tile border-line' : 'border-transparent hover:bg-white/70')}>
                <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl" style={{ background: `${c.c}14`, color: c.c }}><c.icon className="size-4" /></span>
                <span><span className="block text-[17px] font-semibold text-navy">{c.k}</span><span className={cn('block overflow-hidden text-[14.5px] leading-relaxed text-muted transition-all duration-300', i === cat ? 'mt-1 max-h-20 opacity-100' : 'max-h-0 opacity-0')}>{c.body}</span></span>
              </button>
            ))}
          </div>
        </div>
        <div className="reveal relative self-center rounded-[24px] border border-line bg-white/80 p-5 shadow-card backdrop-blur sm:p-8">
          <div className="grid gap-6 sm:grid-cols-[1fr_44px_1fr] sm:items-center">
            <div className="space-y-2.5">
              <p className="font-mono text-[11px] text-muted">raw evidence</p>
              {FRAGS.map((f, i) => (
                <div key={f.src} className={cn('rounded-xl border bg-white p-3 transition-all duration-300', C.ev.includes(i) ? 'border-sky/60 shadow-card' : 'border-line opacity-45')}>
                  <p className="flex items-center gap-1.5 font-mono text-[11px] text-muted"><f.icon className="size-3" />{f.src}</p>
                  <p className="mt-1 text-[12.5px] leading-snug text-[#3e5373]">{f.text}</p>
                </div>
              ))}
            </div>
            <div className="hidden h-full flex-col items-center justify-center gap-2 sm:flex"><span className="h-16 w-px bg-gradient-to-b from-transparent to-line" /><span className="flex size-10 items-center justify-center rounded-xl border border-line bg-white"><LogoMark size={22} /></span><span className="h-16 w-px bg-gradient-to-t from-transparent to-line" /></div>
            <div key={cat} className="animate-fade space-y-3">
              <p className="font-mono text-[11px] text-muted">reconstructed finding</p>
              <div className="rounded-2xl border border-line bg-white p-4 shadow-lift">
                <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.1em]" style={{ color: C.c }}><C.icon className="size-3.5" />{C.k.replace(/s$/, '').replace('Responsibilitie', 'Responsibility').replace('Dependencie', 'Dependency')}</p>
                <p className="mt-2 text-[16px] font-semibold leading-snug text-navy">{C.finding}</p>
                <p className="mt-1 text-[12.5px] text-muted">{C.meta}</p>
                <div className="mt-4 flex flex-wrap gap-1.5"><span className="inline-flex items-center gap-1 rounded-md border border-dashed border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[11px] font-medium text-indigo-700"><Sparkles className="size-3" />AI {[94, 86, 83, 90][cat]}%</span><span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium', cat === 0 || cat === 3 ? 'bg-teal-50 text-teal-700' : 'bg-amber-50 text-amber-700')}>{cat === 0 || cat === 3 ? <><ShieldCheck className="size-3" />Verified</> : 'Needs review'}</span></div>
              </div>
              <div className="rounded-xl border border-dashed border-line p-3 text-[12px] text-muted"><Link2 className="mr-1 inline size-3" />Linked to {C.ev.length} evidence records</div>
            </div>
          </div>
        </div>
      </Wrap>
    </section>
  )
}

/* ---------- explorer showcase ---------- */
type GN = { id: string; x: number; y: number; kind: 'Decision' | 'Task' | 'Risk' | 'Person' | 'Component' | 'Evidence'; label: string; desc: string; conf?: number; ver?: 'Verified' | 'Needs review' | 'Conflicting'; ev?: string[] }
const KC: Record<GN['kind'], string> = { Decision: '#315FBA', Task: '#299B80', Risk: '#D36D72', Person: '#7997BE', Component: '#203653', Evidence: '#A0AEC0' }
const GNODES: GN[] = [
  { id: 'd1', x: 360, y: 210, kind: 'Decision', label: 'Decouple settlement via Kafka', desc: 'Ledger publishes ledger.entry.posted events; the settlement worker consumes them asynchronously with idempotent writes.', conf: 94, ver: 'Verified', ev: ['atlas-settlement#412', '#payments-arch thread', 'ADR-007.pdf'] },
  { id: 'd2', x: 380, y: 62, kind: 'Decision', label: 'Idempotency keys required', desc: 'POST /payments and /refunds reject requests without an Idempotency-Key in strict mode.', conf: 91, ver: 'Verified', ev: ['atlas-gateway@a3f9c21'] },
  { id: 'p1', x: 150, y: 96, kind: 'Person', label: 'James Okafor', desc: 'Staff Backend Engineer. Outgoing owner of the settlement service and ledger migrations.' },
  { id: 'e1', x: 112, y: 232, kind: 'Evidence', label: 'PR #412', desc: 'Introduce Kafka-based settlement events. Merged Mar 14.' },
  { id: 'e2', x: 196, y: 352, kind: 'Evidence', label: 'ADR-007.pdf', desc: 'Architecture decision record: event-driven settlement. Status: Accepted.' },
  { id: 'c1', x: 586, y: 104, kind: 'Component', label: 'Settlement Worker', desc: 'Consumes ledger events and batches settlements to acquirers.' },
  { id: 'c2', x: 622, y: 246, kind: 'Component', label: 'Kafka Cluster', desc: 'Event backbone. Disk at 78% of threshold.' },
  { id: 'r1', x: 548, y: 364, kind: 'Risk', label: 'No retry on timeouts', desc: 'A 9-minute acquirer outage failed batches for 14 merchants; recovery was manual.', conf: 83, ver: 'Conflicting', ev: ['#incidents thread'] },
  { id: 't1', x: 368, y: 392, kind: 'Task', label: 'Add timeout retries', desc: 'Exponential backoff for acquirer timeouts before the July volume peak.', conf: 82, ver: 'Needs review', ev: ['#incidents thread', 'PAY-1182'] },
]
const GEDGES = [['d1', 'p1'], ['d1', 'e1'], ['d1', 'e2'], ['d1', 'c1'], ['d1', 'c2'], ['d1', 'd2'], ['c1', 'r1'], ['r1', 't1'], ['t1', 'd1'], ['p1', 'e1'], ['d2', 'c1']]
function Explorer() {
  const ref = useReveal<HTMLElement>()
  const [sel, setSel] = useState('d1')
  const n = GNODES.find((x) => x.id === sel)!
  const related = GEDGES.filter((e) => e.includes(sel)).map((e) => GNODES.find((x) => x.id === (e[0] === sel ? e[1] : e[0]))!)
  const relIds = new Set(related.map((r) => r.id))
  return (
    <section ref={ref} id="explorer" className="ambient-section scroll-mt-20 bg-[#f1f4fa] py-24 sm:py-32">
      <Wrap>
        <div className="mx-auto max-w-3xl text-center">
          <div className="reveal flex justify-center"><Eyebrow>Knowledge Explorer</Eyebrow></div>
          <H2 className="reveal mt-5">Every decision has a reason. Every task has a story.</H2>
          <Lead className="reveal mx-auto mt-6 max-w-2xl">Explore how people, decisions, tasks, risks and technical components connect across your project.</Lead>
        </div>
        <div className="reveal mt-14 overflow-hidden rounded-[22px] border border-line bg-white shadow-pop">
          <div className="flex items-center gap-3 border-b border-line px-4 py-3">
            <LogoMark size={18} /><span className="text-[13px] font-semibold text-navy">Atlas Payments Platform</span><span className="text-slate-300">/</span><span className="text-[13px] text-muted">Knowledge Explorer</span>
            <div className="ml-auto hidden items-center gap-3 sm:flex">{(Object.keys(KC) as GN['kind'][]).map((k) => <span key={k} className="flex items-center gap-1.5 text-[11.5px] text-muted"><span className="size-2 rounded-full" style={{ background: KC[k] }} />{k}</span>)}</div>
          </div>
          <div className="grid md:grid-cols-[1fr_320px]">
            <div className="relative hidden border-r border-line md:block">
              <div className="absolute inset-0 dot-grid opacity-70" />
              <svg viewBox="0 0 720 440" className="relative h-full w-full" role="img" aria-label="Knowledge graph preview">
                {GEDGES.map(([a, b]) => { const A = GNODES.find((x) => x.id === a)!, B = GNODES.find((x) => x.id === b)!; const on = a === sel || b === sel; return <line key={a + b} x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke={on ? '#7997BE' : '#DCE3EF'} strokeWidth={on ? 1.6 : 1} className="transition-all duration-300" /> })}
                {GNODES.map((g) => {
                  const on = g.id === sel, rel = relIds.has(g.id)
                  return (
                    <g key={g.id} onClick={() => setSel(g.id)} className="cursor-pointer" opacity={on || rel ? 1 : 0.45} style={{ transition: 'opacity .3s' }}>
                      {on && <circle cx={g.x} cy={g.y} r="22" fill={KC[g.kind]} opacity="0.1" />}
                      <circle cx={g.x} cy={g.y} r={on ? 11 : 8} fill={on ? KC[g.kind] : 'white'} stroke={KC[g.kind]} strokeWidth="2" style={{ transition: 'all .3s' }} />
                      <rect x={g.x - g.label.length * 3.4 - 8} y={g.y + 15} width={g.label.length * 6.8 + 16} height="20" rx="6" fill="white" stroke={on ? KC[g.kind] : '#E3E9F3'} />
                      <text x={g.x} y={g.y + 29} textAnchor="middle" fontSize="11.5" fontWeight={on ? 700 : 500} fill="#203653" fontFamily="Manrope, sans-serif">{g.label}</text>
                    </g>
                  )
                })}
              </svg>
            </div>
            <aside key={sel} className="animate-fade bg-white p-5 sm:p-6">
              <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em]" style={{ color: KC[n.kind] }}><span className="size-2 rounded-full" style={{ background: KC[n.kind] }} />{n.kind}</p>
              <h3 className="mt-2 text-[19px] font-semibold leading-snug tracking-[-0.02em] text-navy">{n.label}</h3>
              <p className="mt-2 text-[13.5px] leading-relaxed text-muted">{n.desc}</p>
              {n.conf && (
                <div className="mt-5 grid grid-cols-2 gap-2">
                  <div className="rounded-xl border border-dashed border-indigo-200 bg-indigo-50/50 p-3"><p className="text-[10.5px] font-semibold uppercase tracking-[0.1em] text-indigo-500">AI confidence</p><p className="mt-1 text-[20px] font-semibold text-indigo-700">{n.conf}%</p></div>
                  <div className={cn('rounded-xl border p-3', n.ver === 'Verified' ? 'border-teal-200 bg-teal-50/50' : n.ver === 'Conflicting' ? 'border-red-200 bg-red-50/40' : 'border-amber-200 bg-amber-50/40')}><p className="text-[10.5px] font-semibold uppercase tracking-[0.1em] text-slate-500">Verification</p><p className={cn('mt-1.5 flex items-center gap-1 text-[13px] font-semibold', n.ver === 'Verified' ? 'text-teal-700' : n.ver === 'Conflicting' ? 'text-red-700' : 'text-amber-700')}>{n.ver === 'Verified' ? <ShieldCheck className="size-4" /> : <CircleAlert className="size-4" />}{n.ver}</p></div>
                </div>
              )}
              <p className="mb-2 mt-5 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">Related · {related.length}</p>
              <div className="flex flex-wrap gap-1.5">{related.map((r) => <button key={r.id} onClick={() => setSel(r.id)} className="flex items-center gap-1.5 rounded-full border border-line px-2.5 py-1 text-[12px] text-navy transition hover:border-sky"><span className="size-1.5 rounded-full" style={{ background: KC[r.kind] }} />{r.label}</button>)}</div>
              {n.ev && <><p className="mb-2 mt-5 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">Supporting evidence</p><ul className="space-y-1.5">{n.ev.map((e) => <li key={e} className="flex items-center gap-2 rounded-lg border border-line px-2.5 py-1.5 font-mono text-[11.5px] text-navy"><Link2 className="size-3 text-sky" />{e}</li>)}</ul></>}
              <button onClick={() => navigate('/signup')} className="mt-6 flex h-10 w-full items-center justify-center gap-2 rounded-[10px] border border-line text-[13px] font-semibold text-navy transition hover:bg-canvas">Open details & verify<ArrowRight className="size-3.5" /></button>
            </aside>
          </div>
        </div>
        <p className="mt-4 text-center text-[13px] text-muted md:hidden">Tap related items to move through the graph.</p>
      </Wrap>
    </section>
  )
}

/* ---------- structured handovers ---------- */
function Handovers() {
  const ref = useReveal<HTMLElement>()
  return (
    <section ref={ref} id="handovers" className="scroll-mt-20 py-24 sm:py-32">
      <Wrap className="grid items-center gap-14 grid-cols-1 [&>*]:min-w-0 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
        <div>
          <div className="reveal"><Eyebrow>Structured handovers</Eyebrow></div>
          <H2 className="reveal mt-5">Make every transition a continuation, not a restart.</H2>
          <Lead className="reveal mt-6">Bring the right project knowledge together into a structured handover, so incoming members can understand their responsibilities, decisions and next steps from day one.</Lead>
          <ul className="reveal mt-9 space-y-5 border-l border-line pl-6">
            {[['Built from evidence', 'Every section is assembled from verified findings, with sources one click away.'], ['Reviewed by the people who know', 'Outgoing members confirm, correct or reject. Managers approve before publishing.'], ['Designed for day one', 'A guided path through architecture, responsibilities, risks and first steps.']].map(([t, b]) => <li key={t}><p className="text-[16px] font-semibold text-navy">{t}</p><p className="mt-1 text-[14.5px] leading-relaxed text-muted">{b}</p></li>)}
          </ul>
        </div>
        <div className="reveal relative">
          <div className="absolute -inset-6 rounded-[32px] opacity-80" style={{ background: 'radial-gradient(ellipse at 70% 20%, rgba(165,160,217,0.2), transparent 60%)' }} />
          <div className="relative overflow-hidden rounded-[20px] border border-line bg-white shadow-pop">
            <div className="border-b border-line p-5 sm:p-6">
              <div className="flex flex-wrap items-center gap-2"><span className="font-mono text-[11.5px] text-muted">HO-1042</span><span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-600/20">Pending review</span></div>
              <div className="mt-2 flex items-start justify-between gap-4">
                <div><p className="text-[20px] font-semibold tracking-[-0.02em] text-navy">Atlas Payments Platform</p><div className="mt-3 flex items-center gap-2.5 text-[12.5px]"><span className="flex size-7 items-center justify-center rounded-full bg-[#203653]/10 text-[10px] font-bold text-navy">JO</span><span className="font-medium text-navy">James Okafor</span><ArrowRight className="size-3.5 text-brand" /><span className="flex size-7 items-center justify-center rounded-full bg-blue-50 text-[10px] font-bold text-brand">PN</span><span className="font-medium text-navy">Priya Nair</span></div></div>
                <div className="relative size-16 shrink-0"><svg viewBox="0 0 64 64" className="-rotate-90"><circle cx="32" cy="32" r="27" fill="none" stroke="#EDF1F8" strokeWidth="5" /><circle cx="32" cy="32" r="27" fill="none" stroke="#299B80" strokeWidth="5" strokeLinecap="round" strokeDasharray={`${0.86 * 170} 170`} /></svg><span className="absolute inset-0 flex items-center justify-center text-[13px] font-semibold text-navy">86%</span></div>
              </div>
              <div className="mt-5 grid grid-cols-6 gap-1">{['Draft', 'Verify', 'Review', 'Approve', 'Publish', 'Ack'].map((s, i) => <div key={s}><div className={cn('h-1 rounded-full', i < 2 ? 'bg-ok' : i === 2 ? 'bg-brand' : 'bg-slate-200')} /><p className={cn('mt-1.5 hidden text-[10.5px] font-medium sm:block', i === 2 ? 'text-brand' : 'text-slate-400')}>{s}</p></div>)}</div>
            </div>
            <div className="flex gap-5 overflow-x-auto border-b border-line px-6 text-[12.5px] font-medium text-muted">{['Overview', 'Responsibilities', 'Decisions', 'Tasks', 'Risks', 'Evidence', 'Report'].map((t, i) => <span key={t} className={cn('shrink-0 border-b-2 py-2.5', i === 0 ? 'border-brand text-brand' : 'border-transparent')}>{t}</span>)}</div>
            <div className="grid gap-px bg-line sm:grid-cols-2">
              <div className="bg-white p-5"><p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Project overview</p><p className="mt-2 text-[13px] leading-relaxed text-[#3e5373]">Core payments ledger, settlement and acquirer integrations serving 1,200 merchants across the EU and UK.</p></div>
              <div className="bg-white p-5"><p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Responsibilities</p><ul className="mt-2 space-y-1.5 text-[13px] text-navy">{['Settlement service', 'Ledger schema migrations', 'Acquirer credential rotation'].map((r) => <li key={r} className="flex items-center gap-2"><Check className="size-3.5 text-ok" />{r}</li>)}</ul></div>
              <div className="bg-white p-5"><p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Decisions</p><ul className="mt-2 space-y-2 text-[13px] text-navy">{[['Event-driven settlement', true], ['Idempotency keys required', true], ['Kafka retention to 7 days', false]].map(([t, v]) => <li key={t as string} className="flex items-center justify-between gap-2"><span className="truncate">{t as string}</span>{v ? <ShieldCheck className="size-3.5 shrink-0 text-ok" /> : <span className="shrink-0 rounded bg-red-50 px-1.5 text-[10px] font-semibold text-red-700">Conflict</span>}</li>)}</ul></div>
              <div className="bg-white p-5"><p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Risks</p><ul className="mt-2 space-y-2 text-[13px] text-navy">{[['Critical', 'No retry on acquirer timeouts'], ['High', 'Single maintainer for migrations']].map(([s, t]) => <li key={t} className="flex items-center gap-2"><span className={cn('rounded px-1.5 text-[10px] font-semibold', s === 'Critical' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700')}>{s}</span><span className="truncate">{t}</span></li>)}</ul></div>
              <div className="bg-white p-5"><p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Pending work</p><ul className="mt-2 space-y-1.5 text-[13px] text-navy">{[['Refund reconciliation job', 'Jun 27'], ['Rotate acquirer credentials', 'Jun 30']].map(([t, d]) => <li key={t} className="flex justify-between gap-2"><span className="truncate">{t}</span><span className="shrink-0 font-mono text-[11.5px] text-muted">{d}</span></li>)}</ul></div>
              <div className="bg-white p-5"><p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">Next actions</p><ol className="mt-2 space-y-1.5 text-[13px] text-navy">{['Resolve retention conflict', 'Approve and publish to Priya'].map((t, i) => <li key={t} className="flex gap-2"><span className="flex size-4 shrink-0 items-center justify-center rounded-full bg-blue-50 text-[10px] font-bold text-brand">{i + 1}</span>{t}</li>)}</ol></div>
            </div>
          </div>
        </div>
      </Wrap>
    </section>
  )
}

/* ---------- roles ---------- */
function Roles() {
  const ref = useReveal<HTMLElement>()
  return (
    <section ref={ref} id="roles" className="ambient-section scroll-mt-20 border-t border-line/70 bg-white py-24 sm:py-32">
      <Wrap>
        <div className="max-w-3xl"><div className="reveal"><Eyebrow>Solutions</Eyebrow></div><H2 className="reveal mt-5">One platform. Every side of the transition.</H2><Lead className="reveal mt-6 max-w-2xl">Roles are set per project, so the same person can approve one handover, write another and receive a third.</Lead></div>
        <div className="mt-20 space-y-24 sm:space-y-28">
          {/* Manager */}
          <div className="reveal grid items-center gap-10 grid-cols-1 [&>*]:min-w-0 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-[12.5px] font-semibold text-brand"><Compass className="size-3.5" />Project manager</span>
              <h3 className="mt-5 text-[30px] font-semibold leading-tight tracking-[-0.03em] text-navy sm:text-[36px]">See every transition clearly.</h3>
              <p className="mt-4 max-w-md text-[16px] leading-relaxed text-muted">Monitor projects, manage handovers, review findings and keep transitions moving, with attention drawn to what actually blocks progress.</p>
            </div>
            <div className="rounded-[20px] border border-line bg-canvas p-4 sm:p-5">
              <div className="grid gap-3 sm:grid-cols-[1.2fr_1fr]">
                <div className="tile rounded-2xl border p-4"><p className="text-[12px] font-semibold text-navy">Attention required</p><ul className="mt-3 space-y-2.5">{[[ClipboardCheck, 'text-amber-600 bg-amber-50', 'HO-1042 awaiting approval'], [Plug, 'text-red-600 bg-red-50', 'Slack sync failing'], [AlertTriangle, 'text-red-600 bg-red-50', 'Critical risk unresolved']].map(([I, c, t]) => { const Ic = I as typeof Plug; return <li key={t as string} className="flex items-center gap-2.5"><span className={cn('flex size-6 items-center justify-center rounded-md', c as string)}><Ic className="size-3" /></span><span className="text-[12.5px] text-navy">{t as string}</span></li> })}</ul></div>
                <div className="tile rounded-2xl border p-4"><p className="text-[12px] font-semibold text-navy">Project health</p><ul className="mt-3 space-y-3">{[['Atlas', 82, '#299B80'], ['Orion', 64, '#D39B43'], ['Helix', 88, '#299B80']].map(([l, v, c]) => <li key={l as string}><div className="flex justify-between text-[11.5px]"><span className="text-navy">{l as string}</span><span className="font-mono text-muted">{v as number}%</span></div><div className="mt-1 h-1 rounded-full bg-slate-100"><div className="h-full rounded-full" style={{ width: `${v}%`, background: c as string }} /></div></li>)}</ul></div>
              </div>
            </div>
          </div>
          {/* Outgoing */}
          <div className="reveal grid items-center gap-10 grid-cols-1 [&>*]:min-w-0 lg:grid-cols-[1.1fr_0.9fr] lg:gap-16">
            <div className="order-2 lg:order-1">
              <div className="relative mx-auto max-w-md">
                <div className="absolute inset-x-6 -bottom-3 top-3 rounded-2xl border border-line bg-white/60" />
                <div className="tile relative rounded-2xl border p-5">
                  <div className="flex items-center justify-between"><span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted">Review queue · 7 of 23</span><span className="font-mono text-[11px] text-muted">HO-1038</span></div>
                  <p className="mt-3 text-[16px] font-semibold text-navy">Offline edits to bank details can silently overwrite</p>
                  <p className="mt-1.5 text-[13px] leading-relaxed text-muted">No conflict strategy defined for offline payout edits.</p>
                  <div className="mt-4 h-1.5 rounded-full bg-slate-100"><div className="h-full w-[30%] rounded-full bg-ok" /></div>
                  <div className="mt-4 flex flex-wrap gap-2"><span className="flex h-9 items-center gap-1.5 rounded-lg bg-ok px-3 text-[12.5px] font-semibold text-white"><ShieldCheck className="size-3.5" />Approve & verify</span><span className="flex h-9 items-center rounded-lg border border-line px-3 text-[12.5px] font-semibold text-navy">Add context</span></div>
                </div>
              </div>
            </div>
            <div className="order-1 lg:order-2">
              <span className="inline-flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1 text-[12.5px] font-semibold text-amber-700"><Send className="size-3.5" />Outgoing member</span>
              <h3 className="mt-5 text-[30px] font-semibold leading-tight tracking-[-0.03em] text-navy sm:text-[36px]">Leave the knowledge, not just the role.</h3>
              <p className="mt-4 max-w-md text-[16px] leading-relaxed text-muted">Capture project understanding, verify responsibilities and transfer important context. Answer only what the evidence couldn't.</p>
            </div>
          </div>
          {/* Incoming */}
          <div className="reveal grid items-center gap-10 grid-cols-1 [&>*]:min-w-0 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full bg-teal-50 px-3 py-1 text-[12.5px] font-semibold text-teal-700"><Inbox className="size-3.5" />Incoming member</span>
              <h3 className="mt-5 text-[30px] font-semibold leading-tight tracking-[-0.03em] text-navy sm:text-[36px]">Step into the project with context.</h3>
              <p className="mt-4 max-w-md text-[16px] leading-relaxed text-muted">Explore project knowledge, understand decisions and continue outstanding work. Ask questions and get answers that cite their sources.</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-[200px_1fr]">
              <ol className="rounded-2xl border border-line bg-white p-3">{[[Compass, 'Introduction', 1], [Layers, 'Architecture', 1], [UserRound, 'Responsibilities', 0], [ListTodo, 'Pending tasks', 0]].map(([I, l, d], i) => { const Ic = I as typeof Compass; return <li key={l as string} className={cn('flex items-center gap-2.5 rounded-lg px-2 py-2 text-[12.5px]', i === 2 && 'bg-canvas font-semibold')}><span className={cn('flex size-6 items-center justify-center rounded-md', d ? 'bg-teal-50 text-ok' : i === 2 ? 'bg-brand text-white' : 'bg-slate-100 text-slate-400')}>{d ? <Check className="size-3" /> : <Ic className="size-3" />}</span><span className="text-navy">{l as string}</span></li> })}</ol>
              <div className="tile rounded-2xl border p-4">
                <p className="ml-auto w-fit rounded-2xl rounded-br-md bg-brand px-3 py-2 text-[12.5px] text-white">Why was Dagster chosen over Airflow?</p>
                <div className="mt-3 rounded-2xl rounded-tl-md border border-line p-3 text-[12.5px] leading-relaxed text-[#3e5373]">Asset-based modelling matches dbt lineage, local testing is first-class, and it removed 40% of custom sensor code.<p className="mt-2 flex items-center gap-1.5 font-mono text-[11px] text-brand"><Link2 className="size-3" />[1] Orchestration proposal.pdf</p></div>
                <span className="mt-2 inline-flex items-center gap-1 rounded-full bg-teal-50 px-2 py-0.5 text-[11px] font-medium text-teal-700"><ShieldCheck className="size-3" />Based on verified findings</span>
              </div>
            </div>
          </div>
        </div>
      </Wrap>
    </section>
  )
}

/* ---------- trust ---------- */
function Trust() {
  const ref = useReveal<HTMLElement>()
  return (
    <section ref={ref} id="security" className="relative scroll-mt-20 overflow-hidden bg-navy py-24 text-white sm:py-32">
      <div className="pointer-events-none absolute inset-0 opacity-[0.035] hairline-grid" />
      <div className="pointer-events-none absolute -right-40 top-0 size-[620px] rounded-full" style={{ background: 'radial-gradient(circle, rgba(139,120,201,0.22), transparent 62%)' }} />
      <Wrap className="relative grid gap-14 grid-cols-1 [&>*]:min-w-0 lg:grid-cols-[1fr_1fr] lg:gap-16">
        <div>
          <p className="reveal flex items-center gap-2 text-[12.5px] font-semibold uppercase tracking-[0.16em] text-[#a9b8d0]"><span className="h-px w-6 bg-current opacity-60" />Trust & security</p>
          <h2 className="reveal mt-5 text-[34px] font-semibold leading-[1.06] tracking-[-0.035em] sm:text-[44px] lg:text-[52px]">AI can reconstruct knowledge. People make it trustworthy.</h2>
          <p className="reveal mt-6 max-w-lg text-[17px] leading-[1.65] text-[#c3cfe0]">Every important finding should have a traceable source. Handover connects reconstructed knowledge to the evidence behind it.</p>
          <ul className="reveal mt-10 space-y-6">
            {[[Link2, 'Source traceability', 'Explore the original evidence behind every finding.'], [ShieldCheck, 'Human verification', 'Review and confirm important information before it is transferred.'], [Lock, 'Controlled access', 'Manage project, workspace and handover permissions.']].map(([I, t, b]) => { const Ic = I as typeof Lock; return <li key={t as string} className="flex gap-4"><span className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-white/15 bg-white/5"><Ic className="size-4 text-[#c3cfe0]" /></span><div><p className="text-[16px] font-semibold">{t as string}</p><p className="mt-0.5 text-[14.5px] text-[#a9b8d0]">{b as string}</p></div></li> })}
          </ul>
        </div>
        <div className="reveal">
          <div className="rounded-[22px] border border-white/10 bg-white p-5 text-navy shadow-pop sm:p-7">
            <div className="flex items-center justify-between"><span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-brand"><Lightbulb className="size-3.5" />Reconstructed finding</span><span className="font-mono text-[11px] text-muted">d-kafka</span></div>
            <p className="mt-3 text-[19px] font-semibold leading-snug tracking-[-0.02em]">Decouple settlement from the ledger using Kafka events</p>
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-dashed border-indigo-200 bg-indigo-50/60 p-4">
                <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.1em] text-indigo-500"><Sparkles className="size-3.5" />AI confidence</p>
                <p className="mt-2 text-[34px] font-semibold leading-none tracking-[-0.03em] text-indigo-700">94%</p>
                <div className="mt-3 h-1.5 rounded-full bg-indigo-100"><div className="h-full w-[94%] rounded-full bg-indigo-500" /></div>
                <p className="mt-2.5 text-[12px] leading-snug text-indigo-900/70">How strongly the model believes it. Not proof.</p>
              </div>
              <div className="rounded-2xl border border-teal-200 bg-teal-50/60 p-4">
                <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.1em] text-teal-700"><UserRound className="size-3.5" />Human verification</p>
                <p className="mt-2 flex items-center gap-2 text-[22px] font-semibold text-teal-700"><ShieldCheck className="size-6" />Verified</p>
                <p className="mt-3 text-[12px] leading-snug text-teal-900/70">Confirmed by James Okafor · Jun 18. Counts toward completeness.</p>
              </div>
            </div>
            <p className="mb-2 mt-6 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">Supporting evidence</p>
            <ul className="divide-y divide-line rounded-xl border border-line">{[[GitPullRequest, 'GitHub pull request', 'atlas-settlement#412'], [MessageSquare, 'Project discussion', '#payments-arch · thread'], [FileText, 'Technical document', 'ADR-007 Event-driven settlement.pdf']].map(([I, k, v]) => { const Ic = I as typeof FileText; return <li key={k as string} className="flex items-center gap-3 px-3.5 py-2.5"><Ic className="size-4 text-sky" /><span className="flex-1"><span className="block text-[12px] text-muted">{k as string}</span><span className="block font-mono text-[12.5px] text-navy">{v as string}</span></span><ArrowRight className="size-3.5 text-slate-300" /></li> })}</ul>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-x-6 gap-y-3 text-[13.5px] text-[#c3cfe0] sm:grid-cols-3">{['Authorised, read-only integrations', 'Workspace boundaries', 'Project-specific permissions', 'Controlled sharing & revocation', 'Complete audit history'].map((x) => <p key={x} className="flex items-start gap-2"><Check className="mt-0.5 size-3.5 shrink-0 text-[#8fd1bf]" />{x}</p>)}</div>
        </div>
      </Wrap>
    </section>
  )
}

/* ---------- FAQ ---------- */
const FAQ = [
  ['What does Handover do?', 'Handover collects information from your authorised project tools, reconstructs it into decisions, responsibilities, risks and dependencies, lets people verify those findings against their evidence, and packages them into structured handovers for incoming team members.'],
  ['Which tools can it connect to?', 'GitHub, Jira, Slack and uploaded PDF or DOCX documents, with Confluence and Google Drive available as additional sources. You choose exactly which repositories, projects and channels are included.'],
  ['Does it replace project management tools?', 'No. Handover reads from the tools your team already uses and focuses on preserving and transferring knowledge. Work continues to be planned and tracked where it is today.'],
  ['How does Handover use AI?', 'AI extracts findings from authorised evidence, links them to their sources, detects conflicts and gaps, and assigns a confidence score. AI confidence is always shown separately from human verification.'],
  ['Can users verify AI-generated findings?', 'Yes. Outgoing members and managers can verify, edit, reject or flag findings as conflicting or insufficient. Only human-verified findings count toward a handover’s completeness.'],
  ['Who can use Handover?', 'Project managers who oversee transitions, outgoing members handing over their work, and incoming members receiving it, all within one workspace with Owner, Admin and Member roles.'],
  ['Can users belong to multiple projects?', 'Yes. Roles are assigned per project, so a person can be a manager on one project, an outgoing member on another and an incoming member on a third.'],
  ['Can existing project documentation be uploaded?', 'Yes. Upload PDF and DOCX files such as architecture decision records, runbooks and specifications. They are processed like any other evidence and linked to the findings they support.'],
]
function Faq() {
  const ref = useReveal<HTMLElement>()
  const [open, setOpen] = useState<number | null>(0)
  return (
    <section ref={ref} id="faq" className="scroll-mt-20 py-24 sm:py-32">
      <Wrap className="grid gap-12 grid-cols-1 [&>*]:min-w-0 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
        <div><div className="reveal"><Eyebrow>FAQ</Eyebrow></div><H2 className="reveal mt-5 text-[32px] sm:text-[40px] lg:text-[44px]">Questions about keeping knowledge in motion?</H2></div>
        <ul className="reveal divide-y divide-line border-y border-line">
          {FAQ.map(([q, a], i) => (
            <li key={q}>
              <button onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i} className="flex w-full items-center justify-between gap-6 py-5 text-left">
                <span className="text-[17px] font-semibold tracking-[-0.01em] text-navy">{q}</span>
                <span className={cn('flex size-8 shrink-0 items-center justify-center rounded-full border border-line transition-all duration-300', open === i && 'rotate-45 border-navy bg-navy text-white')}><span className="text-lg leading-none">+</span></span>
              </button>
              <div className={cn('grid transition-all duration-300 ease-out', open === i ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0')}><div className="overflow-hidden"><p className="max-w-2xl pb-6 text-[15.5px] leading-relaxed text-muted">{a}</p></div></div>
            </li>
          ))}
        </ul>
      </Wrap>
    </section>
  )
}

/* ---------- final CTA + footer ---------- */
function FinalCta() {
  const ref = useReveal<HTMLElement>()
  return (
    <section ref={ref} className="px-4 pb-24 sm:px-8">
      <div className="reveal relative mx-auto max-w-[1240px] overflow-hidden rounded-[28px] border border-line bg-white px-6 py-16 text-center sm:py-24">
        <div className="pointer-events-none absolute inset-0" style={{ background: 'radial-gradient(ellipse at 25% 100%, rgba(121,151,190,0.28), transparent 55%), radial-gradient(ellipse at 80% 0%, rgba(165,160,217,0.32), transparent 55%)' }} />
        <div className="relative mx-auto max-w-2xl">
          <div className="relative mx-auto -mt-6 mb-6 max-w-[520px] sm:-mt-10">
            <Scene variant="continuity" className="h-[150px] w-full sm:h-[180px]" label="Flowing glass structure connecting an outgoing and an incoming team member" />
            <div className="pointer-events-none absolute inset-x-0 bottom-0 flex justify-between px-[12%] font-mono text-[10.5px] tracking-[0.08em] text-muted"><span>outgoing</span><span>incoming</span></div>
          </div>
          <h2 className="text-[36px] font-semibold leading-[1.05] tracking-[-0.04em] text-navy sm:text-[52px]">The next person shouldn't have to start from zero.</h2>
          <p className="mx-auto mt-6 max-w-xl text-[17px] leading-relaxed text-[#56657c]">Preserve what your team knows. Understand what your project needs. Keep every transition moving forward.</p>
          <Primary className="mt-10" onClick={() => navigate('/signup')}>Get started with Handover</Primary>
        </div>
      </div>
    </section>
  )
}
function Footer() {
  const cols: [string, [string, () => void][]][] = [
    ['Product', [['Knowledge Explorer', () => scrollTo('explorer')], ['Intelligence', () => scrollTo('intelligence')], ['Structured handovers', () => scrollTo('handovers')], ['How it works', () => scrollTo('how')]]],
    ['Solutions', [['Project managers', () => scrollTo('roles')], ['Outgoing members', () => scrollTo('roles')], ['Incoming members', () => scrollTo('roles')]]],
    ['Resources', [['3D Brand Studio', () => navigate('/brand')], ['Design System 2.0', () => navigate('/design-system')], ['Security', () => scrollTo('security')], ['FAQ', () => scrollTo('faq')]]],
    ['Company', [['Contact', () => (window.location.href = 'mailto:hello@handover.app')], ['Privacy', () => {}], ['Terms', () => {}]]],
  ]
  return (
    <footer className="border-t border-line bg-white">
      <Wrap className="grid gap-12 py-16 grid-cols-2 [&>*]:min-w-0 md:grid-cols-[1.4fr_repeat(4,1fr)]">
        <div className="col-span-2 md:col-span-1"><Logo size={28} /><p className="mt-4 max-w-xs text-[14px] leading-relaxed text-muted">People change. Projects evolve. Knowledge should never disappear.</p><p className="mt-6 font-mono text-[12px] tracking-[0.18em] text-sky">KNOWLEDGE CONTINUES.</p></div>
        {cols.map(([t, links]) => <div key={t}><p className="text-[13px] font-semibold text-navy">{t}</p><ul className="mt-4 space-y-2.5">{links.map(([l, fn]) => <li key={l}><button onClick={fn} className="text-[14px] text-muted transition hover:text-navy">{l}</button></li>)}</ul></div>)}
      </Wrap>
      <Wrap className="flex flex-col gap-3 border-t border-line py-6 text-[13px] text-muted sm:flex-row sm:items-center sm:justify-between"><span>© 2025 Handover. All rights reserved.</span><span className="flex gap-5"><button className="hover:text-navy">Privacy</button><button className="hover:text-navy">Terms</button><button onClick={() => navigate('/login')} className="hover:text-navy">Log in</button></span></Wrap>
    </footer>
  )
}

export function Landing() {
  useEffect(() => { window.scrollTo(0, 0) }, [])
  return (
    <div className="ambient-canvas min-h-dvh overflow-x-clip text-navy">
      <Nav />
      <main>
        <Hero />
        <Problem />
        <Introducing />
        <HowItWorks />
        <Intelligence />
        <Explorer />
        <Handovers />
        <Roles />
        <Trust />
        <Faq />
        <FinalCta />
      </main>
      <Footer />
    </div>
  )
}
