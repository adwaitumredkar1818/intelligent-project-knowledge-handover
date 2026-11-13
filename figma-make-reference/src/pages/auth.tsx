import { useState, type FormEvent, type ReactNode } from 'react'
import { ArrowLeft, ArrowRight, Building2, Check, CheckCircle2, FileSearch, FolderPlus, GitBranch, Loader2, Mail, MailCheck, ShieldCheck, Sparkles, Upload, UserPlus, Users, Workflow, BookOpen, ClipboardCheck } from 'lucide-react'
import { Logo, SourceIcon } from '@/components/brand'
import { Button, Callout, Checkbox, Confidence, Field, Input, Mono, PasswordInput, Progress, Radio, Select, SphereVisual, VerificationBadge, cn, Badge } from '@/components/ui'
import { Link, navigate, useRoute } from '@/lib/router'
import { useStore } from '@/lib/store'
import { RoleBadge } from '@/components/Shell'
import { HeroVisual } from './landing'

function TransferGraphic() {
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[460px]">
      <svg viewBox="0 0 460 460" className="absolute inset-0 h-full w-full">
        <defs>
          <linearGradient id="bridge" x1="0" x2="1"><stop offset="0" stopColor="#203653" /><stop offset="1" stopColor="#315FBA" /></linearGradient>
        </defs>
        {[60, 120, 180].map((r) => <circle key={r} cx="230" cy="230" r={r} fill="none" stroke="#D9E1F0" strokeDasharray="2 6" />)}
        {[[110, 150], [80, 250], [140, 320], [150, 210]].map(([x, y], i) => <line key={i} x1={x} y1={y} x2="190" y2="230" stroke="#A9B8D0" strokeWidth="1.2" />)}
        {[[350, 150], [380, 250], [320, 320], [310, 210]].map(([x, y], i) => <line key={i} x1="270" y1="230" x2={x} y2={y} stroke="#A9BFE0" strokeWidth="1.2" />)}
        <path d="M190 230 C 215 200, 245 200, 270 230" fill="none" stroke="url(#bridge)" strokeWidth="3" />
        <path d="M190 230 C 215 260, 245 260, 270 230" fill="none" stroke="url(#bridge)" strokeWidth="3" strokeDasharray="5 6"><animate attributeName="stroke-dashoffset" from="22" to="0" dur="1.4s" repeatCount="indefinite" /></path>
        {[[110, 150], [80, 250], [140, 320], [150, 210]].map(([x, y], i) => <circle key={i} cx={x} cy={y} r="7" fill="#fff" stroke="#203653" strokeWidth="2" />)}
        {[[350, 150], [380, 250], [320, 320], [310, 210]].map(([x, y], i) => <circle key={i} cx={x} cy={y} r="7" fill="#fff" stroke="#315FBA" strokeWidth="2" />)}
        <circle cx="190" cy="230" r="20" fill="#203653" />
        <circle cx="270" cy="230" r="20" fill="#315FBA" />
        <text x="190" y="234" textAnchor="middle" fontSize="11" fontWeight="600" fill="#fff">OUT</text>
        <text x="270" y="234" textAnchor="middle" fontSize="11" fontWeight="600" fill="#fff">IN</text>
      </svg>
      <div className="animate-fade absolute left-0 top-[14%] rounded-xl border border-white bg-white/95 p-3 shadow-pop" style={{ animationDelay: '.2s' }}>
        <p className="flex items-center gap-1.5 text-[11px] font-medium text-muted"><GitBranch className="size-3" /> PR #412 · Slack · ADR-007</p>
        <p className="mt-1 text-[13px] font-semibold text-navy">Decision reconstructed</p>
        <span className="mt-1.5 inline-flex items-center gap-1 rounded-md border border-dashed border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[11px] font-medium text-indigo-700"><Sparkles className="size-3" />AI confidence 94%</span>
      </div>
      <div className="animate-fade absolute bottom-[12%] right-0 rounded-xl border border-white bg-white/95 p-3 shadow-pop" style={{ animationDelay: '.45s' }}>
        <p className="text-[11px] font-medium text-muted">Human review</p>
        <p className="mt-1 flex items-center gap-1.5 text-[13px] font-semibold text-navy"><ShieldCheck className="size-4 text-ok" />Verified by James O.</p>
        <div className="mt-2 h-1.5 w-40 rounded-full bg-slate-100"><div className="h-full w-[86%] rounded-full bg-ok" /></div>
      </div>
    </div>
  )
}

function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-dvh bg-white lg:grid-cols-[1fr_1.05fr]">
      <div className="flex flex-col px-6 py-8 sm:px-12 lg:px-16">
        <button onClick={() => navigate('/')} className="w-fit" aria-label="Handover home"><Logo size={30} /></button>
        <div className="mx-auto flex w-full max-w-[400px] flex-1 flex-col justify-center py-10">{children}</div>
        <p className="text-center text-xs text-muted lg:text-left">© 2025 Handover · <a href="#/login" className="hover:text-navy">Terms</a> · <a href="#/login" className="hover:text-navy">Privacy</a> · <a href="#/login" className="hover:text-navy">Security</a></p>
      </div>
      <div className="relative hidden overflow-hidden bg-tint lg:flex lg:flex-col lg:justify-center lg:p-14">
        <div className="absolute inset-0 opacity-60" style={{ backgroundImage: 'radial-gradient(#D9E1F0 1px, transparent 1px)', backgroundSize: '22px 22px' }} />
        <div className="relative">
          <HeroVisual />
          <div className="mx-auto mt-8 max-w-md text-center">
            <h2 className="text-[22px] font-semibold tracking-[-0.025em] text-navy">People change. Projects evolve. Knowledge continues.</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">Handover reconstructs decisions, responsibilities and risks from your tools, then lets people verify them before anything is transferred.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function GoogleButton({ label }: { label: string }) {
  return (
    <Button type="button" variant="secondary" size="lg" className="w-full" onClick={() => navigate('/dashboard')}>
      <svg width="16" height="16" viewBox="0 0 24 24"><path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.2-2.1 3.5-5.1 3.5-8.8Z" /><path fill="#34A853" d="M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24Z" /><path fill="#FBBC05" d="M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6h-4a12 12 0 0 0 0 10.8l4-3.1Z" /><path fill="#EA4335" d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.9 3.6-4.9 6.7-4.9Z" /></svg>
      {label}
    </Button>
  )
}

const emailOk = (e: string) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(e)

export function Login() {
  const s = useStore()
  const { query } = useRoute()
  const registered = query.get('registered') === '1'
  const [email, setEmail] = useState(registered ? 'maya.chen@northwind.io' : 'maya.chen@northwind.io')
  const [pw, setPw] = useState(registered ? '' : 'handover-demo')
  const [remember, setRemember] = useState(true)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!emailOk(email)) return setErr('Enter a valid work email address.')
    if (pw.length < 8) return setErr('Incorrect email or password. Passwords are at least 8 characters.')
    setErr('')
    setLoading(true)
    setTimeout(() => { s.setAuthed(true); navigate(registered ? '/onboarding' : '/dashboard') }, 800)
  }
  return (
    <AuthLayout>
      <h1 className="text-2xl font-semibold tracking-tight text-navy">Welcome back</h1>
      <p className="mt-1.5 text-sm text-muted">Sign in to continue to your Handover workspace.</p>
      {registered && <div className="mt-5"><Callout tone="green" icon={CheckCircle2} title="Account created">Sign in to set up your workspace.</Callout></div>}
      <div className="mt-6"><GoogleButton label="Continue with Google" /></div>
      <div className="my-5 flex items-center gap-3 text-xs text-slate-400"><span className="h-px flex-1 bg-line" />or sign in with email<span className="h-px flex-1 bg-line" /></div>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field label="Work email"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" autoComplete="email" invalid={!!err && !emailOk(email)} /></Field>
        <Field label="Password"><PasswordInput value={pw} onChange={(e) => setPw(e.target.value)} placeholder="Enter your password" autoComplete="current-password" invalid={!!err && pw.length < 8} /></Field>
        {err && <p className="text-[13px] text-bad" role="alert">{err}</p>}
        <div className="flex items-center justify-between">
          <Checkbox checked={remember} onChange={setRemember} label="Remember me" />
          <Link to="/forgot-password" className="text-[13px] font-medium text-brand hover:underline">Forgot password?</Link>
        </div>
        <Button size="lg" className="w-full" disabled={loading}>{loading ? <><Loader2 className="size-4 animate-spin" />Signing in…</> : 'Sign in'}</Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">New to Handover? <Link to="/signup" className="font-medium text-brand hover:underline">Create an account</Link></p>
      <p className="mt-3 text-center text-xs text-slate-400">By signing in you agree to our <a href="#/login" className="underline">Terms</a> and <a href="#/login" className="underline">Privacy Policy</a>.</p>
    </AuthLayout>
  )
}

export function Signup() {
  const [f, setF] = useState({ name: '', email: '', pw: '', confirm: '' })
  const [terms, setTerms] = useState(false)
  const [touched, setTouched] = useState(false)
  const [loading, setLoading] = useState(false)
  const strength = [f.pw.length >= 8, /[A-Z]/.test(f.pw), /\d/.test(f.pw), /[^A-Za-z0-9]/.test(f.pw)].filter(Boolean).length
  const errors = { name: !f.name.trim() && 'Enter your full name', email: !emailOk(f.email) && 'Enter a valid work email', pw: f.pw.length < 8 && 'Use at least 8 characters', confirm: f.confirm !== f.pw && 'Passwords do not match', terms: !terms && 'Accept the terms to continue' }
  const valid = !Object.values(errors).some(Boolean)
  const submit = (e: FormEvent) => {
    e.preventDefault()
    setTouched(true)
    if (!valid) return
    setLoading(true)
    setTimeout(() => navigate('/login?registered=1'), 800)
  }
  return (
    <AuthLayout>
      <h1 className="text-2xl font-semibold tracking-tight text-navy">Create your account</h1>
      <p className="mt-1.5 text-sm text-muted">Start capturing project knowledge before it walks out the door.</p>
      <div className="mt-6"><GoogleButton label="Sign up with Google" /></div>
      <div className="my-5 flex items-center gap-3 text-xs text-slate-400"><span className="h-px flex-1 bg-line" />or<span className="h-px flex-1 bg-line" /></div>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field label="Full name" error={touched ? errors.name || undefined : undefined}><Input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Maya Chen" invalid={touched && !!errors.name} /></Field>
        <Field label="Work email" error={touched ? errors.email || undefined : undefined}><Input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} placeholder="you@company.com" invalid={touched && !!errors.email} /></Field>
        <Field label="Password" error={touched ? errors.pw || undefined : undefined}>
          <PasswordInput value={f.pw} onChange={(e) => setF({ ...f, pw: e.target.value })} placeholder="At least 8 characters" invalid={touched && !!errors.pw} />
          <div className="mt-2 flex gap-1">{[1, 2, 3, 4].map((i) => <span key={i} className={cn('h-1 flex-1 rounded-full', i <= strength ? (strength < 2 ? 'bg-bad' : strength < 4 ? 'bg-warn' : 'bg-ok') : 'bg-slate-200')} />)}</div>
          <span className="mt-1 block text-xs text-muted">{['Add a password', 'Weak', 'Fair', 'Good', 'Strong'][strength]}</span>
        </Field>
        <Field label="Confirm password" error={touched ? errors.confirm || undefined : undefined}><PasswordInput value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} placeholder="Repeat password" invalid={touched && !!errors.confirm} /></Field>
        <div>
          <Checkbox checked={terms} onChange={setTerms} label={<>I agree to the <a href="#/signup" className="text-brand underline">Terms of Service</a> and <a href="#/signup" className="text-brand underline">Privacy Policy</a></>} />
          {touched && errors.terms && <p className="mt-1 text-xs text-bad">{errors.terms}</p>}
        </div>
        <Button size="lg" className="w-full" disabled={loading}>{loading ? <><Loader2 className="size-4 animate-spin" />Creating account…</> : 'Create account'}</Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">Already have an account? <Link to="/login" className="font-medium text-brand hover:underline">Sign in</Link></p>
    </AuthLayout>
  )
}

export function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  return (
    <AuthLayout>
      <Link to="/login" className="mb-6 inline-flex items-center gap-1.5 text-[13px] font-medium text-muted hover:text-navy"><ArrowLeft className="size-4" />Back to sign in</Link>
      {sent ? (
        <div className="animate-fade">
          <span className="flex size-12 items-center justify-center rounded-2xl bg-teal-50 text-ok"><MailCheck className="size-6" /></span>
          <h1 className="mt-5 text-2xl font-semibold tracking-tight text-navy">Check your inbox</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">If an account exists for <span className="font-medium text-navy">{email}</span>, we sent a link to reset your password. The link expires in 30 minutes.</p>
          <div className="mt-6 space-y-2"><Button size="lg" className="w-full" onClick={() => navigate('/login')}>Return to sign in</Button><Button variant="ghost" className="w-full" onClick={() => setSent(false)}>Didn't get it? Resend</Button></div>
        </div>
      ) : (
        <>
          <span className="flex size-12 items-center justify-center rounded-2xl bg-tint text-brand"><Mail className="size-6" /></span>
          <h1 className="mt-5 text-2xl font-semibold tracking-tight text-navy">Reset your password</h1>
          <p className="mt-1.5 text-sm text-muted">Enter the email you use for Handover and we'll send reset instructions.</p>
          <form className="mt-6 space-y-4" noValidate onSubmit={(e) => { e.preventDefault(); if (!emailOk(email)) return setErr('Enter a valid email address'); setErr(''); setLoading(true); setTimeout(() => { setLoading(false); setSent(true) }, 700) }}>
            <Field label="Work email" error={err || undefined}><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" invalid={!!err} /></Field>
            <Button size="lg" className="w-full" disabled={loading}>{loading ? <><Loader2 className="size-4 animate-spin" />Sending…</> : 'Send reset link'}</Button>
          </form>
        </>
      )}
    </AuthLayout>
  )
}

const OB_STEPS = ['Welcome', 'Profile', 'Workspace', 'Role', 'Project', 'How it works']

function ProductIntroStory() {
  const [act, setAct] = useState(0)
  const acts = [
    {
      id: 'sources',
      icon: GitBranch,
      title: '1. Authorised sources enter',
      sub: 'GitHub, Jira, Slack and project documents stream in with read-only scopes.',
      scene: <SphereVisual variant="empty" emptyKind="sources" className="h-52 w-full" />,
      ui: (
        <div className="space-y-2 rounded-xl border border-line bg-white p-3.5 text-left shadow-card">
          <p className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">2D interface · Data sources</p>
          {(['github', 'jira', 'slack', 'docs'] as const).map((t, i) => (
            <div key={t} className="flex items-center gap-2.5 rounded-lg border border-line/80 px-2.5 py-1.5 text-[12px]">
              <SourceIcon type={t} size={22} />
              <span className="flex-1 font-medium text-navy">{['atlas-settlement, atlas-ledger', 'PAY · Sprint records', '#payments-arch, #incidents', 'ADR-007.pdf, Runbook v3.docx'][i]}</span>
              <Badge tone="green" dot>Authorised</Badge>
            </div>
          ))}
        </div>
      ),
    },
    {
      id: 'reconstruct',
      icon: Sparkles,
      title: '2. Fragmented signals connect',
      sub: 'Disconnected commits, threads and tickets converge into linked relationships.',
      scene: <SphereVisual variant="reconstruct" progress={0.62} className="h-52 w-full" />,
      ui: (
        <div className="space-y-3 rounded-xl border border-line bg-white p-3.5 text-left shadow-card">
          <div className="flex items-center justify-between"><span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">2D interface · Reconstruction pipeline</span><Mono className="text-[11px] text-brand">15,410 records</Mono></div>
          <Progress value={68} size="sm" />
          <ul className="space-y-1.5 text-[12px] text-navy">
            <li className="flex items-center gap-2"><CheckCircle2 className="size-3.5 text-ok" />Extracted 25 candidate findings from 4 sources</li>
            <li className="flex items-center gap-2"><CheckCircle2 className="size-3.5 text-ok" />Linked PR #412 ↔ #payments-arch ↔ ADR-007</li>
            <li className="flex items-center gap-2"><Sparkles className="size-3.5 text-ai" />Flagged 1 retention conflict & 3 knowledge gaps</li>
          </ul>
        </div>
      ),
    },
    {
      id: 'emerge',
      icon: FileSearch,
      title: '3. Structured intelligence emerges',
      sub: 'Decisions, responsibilities, risks and dependencies crystallise on the sphere.',
      scene: <SphereVisual variant="hero" showTags className="h-52 w-full" />,
      ui: (
        <div className="grid grid-cols-2 gap-2 rounded-xl border border-line bg-white p-3.5 text-left shadow-card">
          <p className="col-span-2 font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">2D interface · Reconstructed intelligence</p>
          {[
            ['Decisions', '6 reconstructed', 'Why Kafka replaced sync settlement', '#315FBA'],
            ['Responsibilities', '4 transferring', 'Settlement service & Vault rotation', '#299B80'],
            ['Risks', '1 critical', 'No retry on acquirer 504 timeouts', '#D36D72'],
            ['Dependencies', '2 blocking', 'SOAP cutover blocked by PAY-1204', '#D39B43'],
          ].map(([k, m, d, c]) => (
            <div key={k} className="rounded-lg border border-line/80 p-2.5">
              <div className="flex items-center justify-between"><span className="flex items-center gap-1.5 text-[11.5px] font-semibold text-navy"><span className="size-1.5 rounded-full" style={{ background: c }} />{k}</span><Mono className="text-[10px] text-muted">{m}</Mono></div>
              <p className="mt-1 truncate text-[11px] text-muted">{d}</p>
            </div>
          ))}
        </div>
      ),
    },
    {
      id: 'verify',
      icon: ClipboardCheck,
      title: '4. Human verification & evidence',
      sub: 'Outgoing members inspect AI confidence against original source evidence.',
      scene: <SphereVisual variant="macro" className="h-52 w-full" />,
      ui: (
        <div className="space-y-2.5 rounded-xl border border-line bg-white p-3.5 text-left shadow-card">
          <p className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">2D interface · Review & verification</p>
          <p className="text-[13px] font-semibold text-navy">Decouple settlement from ledger using Kafka events</p>
          <div className="flex flex-wrap items-center gap-2">
            <Confidence value={94} />
            <VerificationBadge status="verified" />
            <Mono className="text-[11px] text-muted">3 linked sources</Mono>
          </div>
          <p className="rounded-lg bg-canvas px-2.5 py-1.5 text-[11.5px] text-muted">AI confidence (model certainty) is never conflated with human verification.</p>
        </div>
      ),
    },
    {
      id: 'transfer',
      icon: BookOpen,
      title: '5. Structured handover continues',
      sub: 'Managers approve and publish; incoming members step in with full context.',
      scene: <SphereVisual variant="continuity" className="h-52 w-full" />,
      ui: (
        <div className="space-y-2.5 rounded-xl border border-line bg-white p-3.5 text-left shadow-card">
          <div className="flex items-center justify-between"><span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">2D interface · Published handover</span><Badge tone="green" dot>HO-1042 · Published</Badge></div>
          <p className="text-[13px] font-semibold text-navy">James Okafor → Priya Nair · Atlas Payments</p>
          <Progress value={100} size="sm" tone="green" />
          <p className="text-[11.5px] text-muted">Includes 12-section report, interactive knowledge graph and evidence-grounded AI assistant.</p>
        </div>
      ),
    },
  ]
  const cur = acts[act]
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-xl font-semibold text-navy">How Handover works</h2>
          <p className="mt-1 text-sm text-muted">3D knowledge continuity paired with precise 2D verification and handover workflows.</p>
        </div>
        <span className="font-mono text-xs text-brand">Act {act + 1} of {acts.length}</span>
      </div>
      <div className="mt-5 grid grid-cols-5 gap-1.5">
        {acts.map((a, i) => (
          <button
            key={a.id}
            type="button"
            onClick={() => setAct(i)}
            className={cn('rounded-xl border p-2.5 text-left transition', i === act ? 'border-brand bg-tint/60 shadow-card' : 'border-line bg-white hover:bg-canvas')}
          >
            <a.icon className={cn('size-4', i === act ? 'text-brand' : 'text-muted')} />
            <p className="mt-1.5 text-[11.5px] font-semibold text-navy">{['1. Sources', '2. Connect', '3. Emerge', '4. Verify', '5. Transfer'][i]}</p>
          </button>
        ))}
      </div>
      <div key={cur.id} className="animate-fade mt-4 grid items-center gap-4 rounded-2xl border border-line bg-canvas/60 p-4 sm:grid-cols-2">
        <div className="flex flex-col items-center">
          {cur.scene}
          <div className="mt-2 text-center">
            <p className="text-[14px] font-semibold text-navy">{cur.title}</p>
            <p className="mt-0.5 text-[12.5px] text-muted">{cur.sub}</p>
          </div>
        </div>
        {cur.ui}
      </div>
    </div>
  )
}

export function Onboarding() {
  const s = useStore()
  const [step, setStep] = useState(0)
  const [profile, setProfile] = useState({ name: 'Maya Chen', title: 'Engineering Manager', team: 'Payments' })
  const [wsMode, setWsMode] = useState<'create' | 'join'>('join')
  const [wsName, setWsName] = useState('')
  const [role, setRole] = useState<'manager' | 'outgoing' | 'incoming'>('manager')
  const [projMode, setProjMode] = useState<'invite' | 'create'>('invite')
  const [proj, setProj] = useState({ name: '', category: 'Backend platform' })
  const [accepted, setAccepted] = useState<string[]>(['orion', 'helix'])
  const next = () => setStep((x) => Math.min(OB_STEPS.length - 1, x + 1))
  const finish = () => {
    if (projMode === 'create' && proj.name.trim()) {
      const id = proj.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 24) || 'new-project'
      s.setProjects((ps) => [...ps, { id, workspaceId: 'northwind', name: proj.name, code: proj.name.slice(0, 3).toUpperCase(), description: 'New project created during onboarding.', category: proj.category, status: 'planning', health: 0, ownerId: 'maya', role: 'manager', lastActivity: 'Just now', coverage: 0, startDate: '2025-06-18', endDate: '2025-12-31', color: '#5B8BC9' }])
      s.switchProject(id, true)
    }
    s.setWorkspaceId('northwind')
    s.toast('Your workspace is ready', 'Connect a data source to start reconstructing knowledge.')
    navigate('/dashboard')
  }
  const canNext = step !== 2 || wsMode === 'join' || wsName.trim().length > 1
  return (
    <div className="min-h-dvh bg-canvas">
      <header className="flex h-16 items-center justify-between border-b border-line bg-white px-5 sm:px-8">
        <Logo size={26} />
        <button onClick={finish} className="text-[13px] font-medium text-muted hover:text-navy">Skip for now</button>
      </header>
      <div className="mx-auto max-w-3xl px-4 py-8 sm:py-12">
        <ol className="mb-8 flex items-center gap-2">
          {OB_STEPS.map((l, i) => (
            <li key={l} className="flex flex-1 flex-col gap-2">
              <span className={cn('h-1 rounded-full transition', i <= step ? 'bg-brand' : 'bg-slate-200')} />
              <span className={cn('hidden text-xs font-medium sm:block', i === step ? 'text-navy' : 'text-slate-400')}>{i + 1}. {l}</span>
            </li>
          ))}
        </ol>
        <div key={step} className="animate-fade rounded-2xl border border-line bg-white p-6 shadow-card sm:p-10">
          {step === 0 && (
            <div className="text-center">
              <SphereVisual variant="hero" className="mx-auto size-48 sm:size-56" />
              <h1 className="mt-3 text-2xl font-semibold tracking-tight text-navy sm:text-3xl">Welcome to Handover</h1>
              <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-muted">In a few steps you'll set up your profile and workspace. If a teammate already invited you to a project, you can jump straight into it.</p>
              <div className="mt-8 grid gap-3 text-left sm:grid-cols-3">
                {[[FileSearch, 'Capture', 'Ingest code, issues, chats and documents'], [ShieldCheck, 'Verify', 'People confirm AI findings with evidence'], [Workflow, 'Transfer', 'Publish structured, trusted handovers']].map(([I, t, d]) => {
                  const Ic = I as typeof FileSearch
                  return <div key={t as string} className="tile rounded-xl border p-4"><Ic className="size-5 text-brand" /><p className="mt-2 text-sm font-semibold text-navy">{t as string}</p><p className="mt-0.5 text-xs text-muted">{d as string}</p></div>
                })}
              </div>
            </div>
          )}
          {step === 1 && (
            <div>
              <h2 className="text-xl font-semibold text-navy">Complete your profile</h2>
              <p className="mt-1 text-sm text-muted">Your name and role help teammates know who verified what.</p>
              <div className="mt-6 flex items-center gap-4">
                <span className="flex size-16 items-center justify-center rounded-full bg-tint text-xl font-semibold text-brand">{profile.name.split(' ').map((x) => x[0]).join('').slice(0, 2)}</span>
                <Button variant="secondary" size="sm" icon={Upload} onClick={() => s.toast('Photo uploaded', undefined)}>Upload photo</Button>
              </div>
              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                <Field label="Full name"><Input value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} /></Field>
                <Field label="Job title"><Input value={profile.title} onChange={(e) => setProfile({ ...profile, title: e.target.value })} /></Field>
                <Field label="Team" className="sm:col-span-2"><Input value={profile.team} onChange={(e) => setProfile({ ...profile, team: e.target.value })} /></Field>
              </div>
            </div>
          )}
          {step === 2 && (
            <div>
              <h2 className="text-xl font-semibold text-navy">Create or join a workspace</h2>
              <p className="mt-1 text-sm text-muted">A workspace holds your organisation's projects, members and integrations.</p>
              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                {[['join', Users, 'Join existing', 'You have 1 pending invitation'], ['create', Building2, 'Create new', 'Start a fresh workspace for your team']].map(([id, I, t, d]) => {
                  const Ic = I as typeof Users
                  return (
                    <button key={id as string} onClick={() => setWsMode(id as 'join')} className={cn('rounded-xl border p-4 text-left transition', wsMode === id ? 'border-brand bg-tint/50 ring-4 ring-brand/10' : 'border-line hover:border-slate-300')}>
                      <Ic className="size-5 text-brand" /><p className="mt-2 text-sm font-semibold text-navy">{t as string}</p><p className="text-xs text-muted">{d as string}</p>
                    </button>
                  )
                })}
              </div>
              {wsMode === 'join' ? (
                <div className="mt-5 flex items-center gap-3 rounded-xl border border-line p-4">
                  <span className="flex size-10 items-center justify-center rounded-lg bg-navy text-sm font-bold text-white">N</span>
                  <div className="flex-1"><p className="text-sm font-semibold text-navy">Northwind Labs</p><p className="text-xs text-muted">Invited by Tom Whitfield · 42 members</p></div>
                  <Badge tone="green" icon={Check}>Will join</Badge>
                </div>
              ) : (
                <div className="mt-5 grid gap-4 sm:grid-cols-2">
                  <Field label="Workspace name" required><Input value={wsName} onChange={(e) => setWsName(e.target.value)} placeholder="Acme Engineering" /></Field>
                  <Field label="Workspace URL" hint="You can change this later"><Input value={`${wsName.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'acme'}.handover.app`} readOnly /></Field>
                </div>
              )}
            </div>
          )}
          {step === 3 && (
            <div>
              <h2 className="text-xl font-semibold text-navy">How will you mostly use Handover?</h2>
              <p className="mt-1 text-sm text-muted">This personalises your first dashboard. Roles are assigned per project, so you can be a manager on one project and an incoming member on another.</p>
              <div className="mt-6 space-y-3">
                {([['manager', 'I manage projects and approve handovers', 'Connect sources, monitor reconstruction, approve and publish.'], ['outgoing', "I'm leaving a project and handing it over", 'Verify what the AI found, fill gaps, submit for approval.'], ['incoming', "I'm joining a project and receiving knowledge", 'Explore a published handover and ask grounded questions.']] as const).map(([id, t, d]) => (
                  <div key={id} className={cn('rounded-xl border p-4 transition', role === id ? 'border-brand bg-tint/40' : 'border-line')}>
                    <Radio checked={role === id} onChange={() => setRole(id)} label={<span className="flex flex-wrap items-center gap-2 font-medium">{t}<RoleBadge role={id} /></span>} description={d} />
                  </div>
                ))}
              </div>
            </div>
          )}
          {step === 4 && (
            <div>
              <h2 className="text-xl font-semibold text-navy">{role === 'manager' ? 'Create your first project' : 'Accept your project invitations'}</h2>
              <p className="mt-1 text-sm text-muted">{role === 'manager' ? 'Or accept projects you were invited to.' : "You don't need to create a project. Accept the invitations below to continue."}</p>
              <div className="mt-5 inline-flex rounded-[10px] border border-line bg-slate-50 p-0.5">
                {(['invite', 'create'] as const).map((m) => <button key={m} onClick={() => setProjMode(m)} className={cn('h-8 rounded-lg px-3 text-[13px] font-medium', projMode === m ? 'bg-white text-navy shadow-sm' : 'text-muted')}>{m === 'invite' ? 'Invitations (2)' : 'Create project'}</button>)}
              </div>
              {projMode === 'invite' ? (
                <div className="mt-4 space-y-2.5">
                  {[{ id: 'orion', name: 'Orion Mobile App', by: 'Sofia Alvarez', role: 'outgoing' as const }, { id: 'helix', name: 'Helix Data Pipeline', by: 'Tom Whitfield', role: 'incoming' as const }].map((p) => (
                    <div key={p.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-line p-4">
                      <FolderPlus className="size-5 text-brand" />
                      <div className="min-w-0 flex-1"><p className="text-sm font-semibold text-navy">{p.name}</p><p className="text-xs text-muted">Invited by {p.by}</p></div>
                      <RoleBadge role={p.role} />
                      <Button size="sm" variant={accepted.includes(p.id) ? 'subtle' : 'secondary'} icon={accepted.includes(p.id) ? Check : undefined} onClick={() => setAccepted((a) => (a.includes(p.id) ? a.filter((x) => x !== p.id) : [...a, p.id]))}>{accepted.includes(p.id) ? 'Accepted' : 'Accept'}</Button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <Field label="Project name" required><Input value={proj.name} onChange={(e) => setProj({ ...proj, name: e.target.value })} placeholder="e.g. Billing Revamp" /></Field>
                  <Field label="Category"><Select value={proj.category} onChange={(e) => setProj({ ...proj, category: e.target.value })}>{['Backend platform', 'Mobile', 'Data & analytics', 'Design system', 'Infrastructure'].map((c) => <option key={c}>{c}</option>)}</Select></Field>
                </div>
              )}
            </div>
          )}
          {step === 5 && (
            <ProductIntroStory />
          )}
          <div className="mt-10 flex items-center justify-between border-t border-line pt-5">
            <Button variant="ghost" icon={ArrowLeft} disabled={step === 0} onClick={() => setStep(step - 1)} className="disabled:opacity-0">Back</Button>
            {step < OB_STEPS.length - 1 ? <Button iconRight={ArrowRight} disabled={!canNext} onClick={next}>{step === 0 ? 'Get started' : 'Continue'}</Button> : <Button iconRight={ArrowRight} onClick={finish}>Go to dashboard</Button>}
          </div>
        </div>
        <p className="mt-4 flex items-center justify-center gap-1.5 text-xs text-muted"><UserPlus className="size-3.5" />Step {step + 1} of {OB_STEPS.length}</p>
      </div>
    </div>
  )
}
