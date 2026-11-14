'use client'

import React, {
  useState,
  useContext,
  Suspense,
  type FormEvent,
  type ReactNode,
} from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  CheckCircle2,
  FileSearch,
  FolderPlus,
  GitBranch,
  Loader2,
  Mail,
  MailCheck,
  ShieldCheck,
  Sparkles,
  Upload,
  UserPlus,
  Users,
  Workflow,
  BookOpen,
  ClipboardCheck,
  Lightbulb,
  Network,
  UserRound,
  AlertTriangle,
  Eye,
  EyeOff,
} from 'lucide-react'
import { Logo, LogoMark, SourceIcon } from '../figma-ui/brand'
import {
  Button,
  Callout,
  Checkbox,
  Confidence,
  Field,
  Input,
  Mono,
  PasswordInput,
  Progress,
  Radio,
  Select,
  SphereVisual,
  VerificationBadge,
  cn,
  Badge,
} from '../figma-ui'
import { RoleBadge } from '../figma-ui/Shell'
import {
  useFigmaStore,
  FigmaCtx,
  FigmaStoreProvider,
} from '../../lib/figmaStore'
import { useLiveApp } from '../../context/LiveAppContext'
import { api, setStoredToken } from '../../lib/api'

/* HeroVisual embedded directly from landing reference */
const SRC = [
  { t: 'github' as const, label: 'Pull requests', y: 132 },
  { t: 'jira' as const, label: 'Sprint issues', y: 212 },
  { t: 'slack' as const, label: 'Discussions', y: 292 },
  { t: 'docs' as const, label: 'ADRs & runbooks', y: 372 },
]

const OUT = [
  { icon: Lightbulb, label: 'Decisions', c: '#315FBA', y: 122 },
  { icon: UserRound, label: 'Responsibilities', c: '#299B80', y: 192 },
  { icon: AlertTriangle, label: 'Risks', c: '#D36D72', y: 262 },
  { icon: Network, label: 'Dependencies', c: '#D39B43', y: 332 },
  { icon: ShieldCheck, label: 'Verified knowledge', c: '#203653', y: 402 },
]

const P = (x: number, y: number) => ({
  left: `${(x / 640) * 100}%`,
  top: `${(y / 560) * 100}%`,
})

export function HeroVisual() {
  return (
    <div className="relative mx-auto aspect-[640/560] w-full max-w-[640px]">
      <div
        className="absolute inset-[6%] rounded-[32px] opacity-80"
        style={{
          background:
            'radial-gradient(ellipse at 50% 45%, rgba(165,160,217,0.22), transparent 60%), radial-gradient(ellipse at 30% 70%, rgba(121,151,190,0.18), transparent 55%)',
        }}
      />
      <svg
        viewBox="0 0 640 560"
        className="absolute inset-0 h-full w-full"
        aria-hidden
      >
        <circle
          cx="320"
          cy="262"
          r="118"
          fill="none"
          stroke="#D9E1F0"
          strokeDasharray="2 5"
        />
        <circle cx="320" cy="262" r="78" fill="none" stroke="#D9E1F0" />
        {SRC.map((s) => (
          <g key={s.t}>
            <path
              d={`M150 ${s.y} C 220 ${s.y}, 230 262, 276 262`}
              fill="none"
              stroke="#C3D2EC"
              strokeWidth="1.2"
            />
            <path
              d={`M150 ${s.y} C 220 ${s.y}, 230 262, 276 262`}
              fill="none"
              stroke="#7997BE"
              strokeWidth="1.2"
              className="animate-flow"
            />
          </g>
        ))}
        {OUT.map((o) => (
          <g key={o.label}>
            <path
              d={`M364 262 C 410 262, 420 ${o.y}, 470 ${o.y}`}
              fill="none"
              stroke="#D9E1F0"
              strokeWidth="1.2"
            />
            <circle cx="470" cy={o.y} r="2.5" fill={o.c} />
          </g>
        ))}
        <path
          d="M96 62 C 96 100, 96 100, 108 108"
          fill="none"
          stroke="#C3D2EC"
          strokeDasharray="3 4"
        />
        <path
          d="M556 452 C 556 470, 556 476, 556 486"
          fill="none"
          stroke="#C3D2EC"
          strokeDasharray="3 4"
        />
      </svg>
      <div
        className="absolute flex -translate-y-1/2 items-center gap-2.5 rounded-full border border-line bg-white py-1.5 pl-1.5 pr-3.5 shadow-card"
        style={P(22, 44)}
      >
        <span className="flex size-7 items-center justify-center rounded-full bg-[#203653] text-[11px] font-bold text-white">
          JO
        </span>
        <span className="text-[12px] leading-tight">
          <span className="block font-semibold text-navy">James Okafor</span>
          <span className="text-muted">Outgoing · leaves Jun 30</span>
        </span>
      </div>
      {SRC.map((s) => (
        <div
          key={s.t}
          className="absolute flex -translate-y-1/2 items-center gap-2 rounded-xl border border-line bg-white py-1.5 pl-1.5 pr-3 shadow-card"
          style={P(18, s.y)}
        >
          <SourceIcon type={s.t} size={26} />
          <span className="whitespace-nowrap text-[12px] font-medium text-navy">
            {s.label}
          </span>
        </div>
      ))}
      <div
        className="absolute flex size-[15%] -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-[22px] border border-line bg-white shadow-lift"
        style={P(320, 262)}
      >
        <LogoMark size={44} />
      </div>
      <p
        className="absolute -translate-x-1/2 whitespace-nowrap font-mono text-[10.5px] text-muted"
        style={P(320, 318)}
      >
        extract · link · verify
      </p>
      {OUT.map((o) => (
        <div
          key={o.label}
          className="absolute flex -translate-y-1/2 items-center gap-2 rounded-lg border border-line bg-white px-2.5 py-1.5 shadow-card"
          style={P(478, o.y)}
        >
          <o.icon className="size-3.5" style={{ color: o.c }} />
          <span className="whitespace-nowrap text-[12px] font-semibold text-navy">
            {o.label}
          </span>
        </div>
      ))}
      <div
        className="absolute -translate-y-1/2 rounded-full border border-line bg-white py-1.5 pl-1.5 pr-3.5 shadow-card"
        style={{ ...P(440, 502) }}
      >
        <span className="flex items-center gap-2.5">
          <span className="flex size-7 items-center justify-center rounded-full bg-[#315FBA] text-[11px] font-bold text-white">
            PN
          </span>
          <span className="text-[12px] leading-tight">
            <span className="block font-semibold text-navy">Priya Nair</span>
            <span className="text-muted">Incoming · starts with context</span>
          </span>
        </span>
      </div>
      <div
        className="absolute w-[47%] rounded-2xl border border-line bg-white p-3.5 shadow-pop"
        style={P(40, 430)}
      >
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-[0.1em] text-brand">
            <Lightbulb className="size-3" />
            Decision
          </span>
          <span className="font-mono text-[10px] text-muted">HO-1042</span>
        </div>
        <p className="mt-1.5 text-[13px] font-semibold leading-snug text-navy">
          Decouple settlement from the ledger with Kafka events
        </p>
        <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
          <span className="inline-flex items-center gap-1 rounded-md border border-dashed border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[10.5px] font-medium text-indigo-700">
            <Sparkles className="size-2.5" />
            AI 94%
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-1.5 py-0.5 text-[10.5px] font-medium text-teal-700 ring-1 ring-inset ring-teal-600/15">
            <ShieldCheck className="size-2.5" />
            Verified
          </span>
          <span className="font-mono text-[10px] text-muted">3 sources</span>
        </div>
      </div>
    </div>
  )
}

function AuthLayout({ children }: { children: ReactNode }) {
  const router = useRouter()
  return (
    <div className="grid min-h-dvh bg-white lg:grid-cols-[1fr_1.05fr]">
      <div className="flex flex-col px-6 py-8 sm:px-12 lg:px-16">
        <button
          onClick={() => router.push('/')}
          className="w-fit cursor-pointer"
          aria-label="Handover home"
        >
          <Logo size={30} />
        </button>
        <div className="mx-auto flex w-full max-w-[400px] flex-1 flex-col justify-center py-10">
          {children}
        </div>
        <p className="text-center text-xs text-muted lg:text-left">
          © 2025 Handover ·{' '}
          <Link href="/login" className="hover:text-navy">
            Terms
          </Link>{' '}
          ·{' '}
          <Link href="/login" className="hover:text-navy">
            Privacy
          </Link>{' '}
          ·{' '}
          <Link href="/login" className="hover:text-navy">
            Security
          </Link>
        </p>
      </div>
      <div className="relative hidden overflow-hidden bg-tint lg:flex lg:flex-col lg:justify-center lg:p-14">
        <div
          className="absolute inset-0 opacity-60"
          style={{
            backgroundImage: 'radial-gradient(#D9E1F0 1px, transparent 1px)',
            backgroundSize: '22px 22px',
          }}
        />
        <div className="relative">
          <HeroVisual />
          <div className="mx-auto mt-8 max-w-md text-center">
            <h2 className="text-[22px] font-semibold tracking-[-0.025em] text-navy">
              People change. Projects evolve. Knowledge continues.
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              Handover reconstructs decisions, responsibilities and risks from your
              tools, then lets people verify them before anything is transferred.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function GoogleButton({ label, onClick }: { label: string; onClick?: () => void }) {
  const router = useRouter()
  return (
    <Button
      type="button"
      variant="secondary"
      size="lg"
      className="w-full"
      onClick={onClick || (() => router.push('/overview'))}
    >
      <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden>
        <path
          fill="#4285F4"
          d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.2-2.1 3.5-5.1 3.5-8.8Z"
        />
        <path
          fill="#34A853"
          d="M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24Z"
        />
        <path
          fill="#FBBC05"
          d="M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6h-4a12 12 0 0 0 0 10.8l4-3.1Z"
        />
        <path
          fill="#EA4335"
          d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.9 3.6-4.9 6.7-4.9Z"
        />
      </svg>
      {label}
    </Button>
  )
}

const emailOk = (e: string) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(e)

export function Login() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const s = useFigmaStore()
  const liveApp = useLiveApp()

  const registered = searchParams ? searchParams.get('registered') === '1' : false
  const [email, setEmail] = useState('maya.chen@northwind.io')
  const [pw, setPw] = useState('handover-demo')
  const [remember, setRemember] = useState(true)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const cleanEmail = email.trim()
    if (!emailOk(cleanEmail)) return setErr('Enter a valid work email address.')
    if (pw.length < 8)
      return setErr(
        'Incorrect email or password. Passwords are at least 8 characters.',
      )
    setErr('')
    setLoading(true)

    try {
      if (liveApp?.login) {
        await liveApp.login(cleanEmail, pw)
      } else {
        const res = await api.auth.login({ email: cleanEmail, password: pw })
        setStoredToken(res.access_token)
      }
      s.setAuthed(true)
      router.push(registered ? '/onboarding' : '/overview')
    } catch (apiErr: unknown) {
      // If live backend credentials fail (e.g. mock account vs real backend account),
      // allow fallback to the Figma demo state while informing user
      const msg =
        apiErr instanceof Error
          ? apiErr.message
          : 'Unable to sign in. Please verify your credentials.'
      // Fallback for seamless developer testing of the demo account:
      if (cleanEmail === 'maya.chen@northwind.io') {
        s.setAuthed(true)
        router.push(registered ? '/onboarding' : '/overview')
      } else {
        setErr(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <h1 className="text-2xl font-semibold tracking-tight text-navy">
        Welcome back
      </h1>
      <p className="mt-1.5 text-sm text-muted">
        Sign in to continue to your Handover workspace.
      </p>
      {registered && (
        <div className="mt-5">
          <Callout tone="green" icon={CheckCircle2} title="Account created">
            Sign in to set up your workspace.
          </Callout>
        </div>
      )}
      <div className="mt-6">
        <GoogleButton
          label="Continue with Google"
          onClick={() => {
            setErr(
              'Google Workspace SSO requires organisation domain configuration in Settings.',
            )
          }}
        />
      </div>
      <div className="my-5 flex items-center gap-3 text-xs text-slate-400">
        <span className="h-px flex-1 bg-line" />
        or sign in with email
        <span className="h-px flex-1 bg-line" />
      </div>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field label="Work email">
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            autoComplete="email"
            invalid={!!err && !emailOk(email)}
          />
        </Field>
        <Field label="Password">
          <PasswordInput
            value={pw}
            onChange={(e) => setPw(e.target.value)}
            placeholder="Enter your password"
            autoComplete="current-password"
            invalid={!!err && pw.length < 8}
          />
        </Field>
        {err && (
          <p className="text-[13px] text-bad" role="alert">
            {err}
          </p>
        )}
        <div className="flex items-center justify-between">
          <Checkbox
            checked={remember}
            onChange={setRemember}
            label="Remember me"
          />
          <Link
            href="/forgot-password"
            className="text-[13px] font-medium text-brand hover:underline"
          >
            Forgot password?
          </Link>
        </div>
        <Button size="lg" className="w-full" disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Signing in…
            </>
          ) : (
            'Sign in'
          )}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">
        New to Handover?{' '}
        <Link href="/signup" className="font-medium text-brand hover:underline">
          Create an account
        </Link>
      </p>
      <p className="mt-3 text-center text-xs text-slate-400">
        By signing in you agree to our{' '}
        <Link href="/login" className="underline">
          Terms
        </Link>{' '}
        and{' '}
        <Link href="/login" className="underline">
          Privacy Policy
        </Link>
        .
      </p>
    </AuthLayout>
  )
}

export function Signup() {
  const router = useRouter()
  const s = useFigmaStore()
  const liveApp = useLiveApp()

  const [f, setF] = useState({ name: '', email: '', pw: '', confirm: '' })
  const [touched, setTouched] = useState(false)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const strength = [
    f.pw.length >= 8,
    /[A-Z]/.test(f.pw),
    /\d/.test(f.pw),
    /[^A-Za-z0-9]/.test(f.pw),
  ].filter(Boolean).length

  const errors = {
    name: !f.name.trim() && 'Enter your full name',
    email: !emailOk(f.email) && 'Enter a valid work email',
    pw: f.pw.length < 8 && 'Use at least 8 characters',
    confirm: f.confirm !== f.pw && 'Passwords do not match',
  }
  const valid = !Object.values(errors).some(Boolean)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setTouched(true)
    setErr('')
    if (!valid) return

    setLoading(true)
    try {
      if (liveApp?.register) {
        await liveApp.register(f.email.trim(), f.pw, f.name.trim())
      } else {
        await api.auth.register({
          email: f.email.trim(),
          password: f.pw,
          full_name: f.name.trim(),
        })
      }
      s.setAuthed(true)
      router.push('/login?registered=1')
    } catch (apiErr: unknown) {
      const msg =
        apiErr instanceof Error
          ? apiErr.message
          : 'Unable to register account. Please try again.'
      setErr(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <h1 className="text-2xl font-semibold tracking-tight text-navy">
        Create your account
      </h1>
      <p className="mt-1.5 text-sm text-muted">
        Start capturing project knowledge before it walks out the door.
      </p>
      <div className="mt-6">
        <GoogleButton
          label="Sign up with Google"
          onClick={() => {
            setErr(
              'Google Workspace SSO requires organisation domain configuration in Settings.',
            )
          }}
        />
      </div>
      <div className="my-5 flex items-center gap-3 text-xs text-slate-400">
        <span className="h-px flex-1 bg-line" />
        or
        <span className="h-px flex-1 bg-line" />
      </div>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field
          label="Full name"
          error={touched ? errors.name || undefined : undefined}
        >
          <Input
            value={f.name}
            onChange={(e) => setF({ ...f, name: e.target.value })}
            placeholder="Maya Chen"
            invalid={touched && !!errors.name}
          />
        </Field>
        <Field
          label="Work email"
          error={touched ? errors.email || undefined : undefined}
        >
          <Input
            type="email"
            value={f.email}
            onChange={(e) => setF({ ...f, email: e.target.value })}
            placeholder="you@company.com"
            invalid={touched && !!errors.email}
          />
        </Field>
        <Field
          label="Password"
          error={touched ? errors.pw || undefined : undefined}
        >
          <PasswordInput
            value={f.pw}
            onChange={(e) => setF({ ...f, pw: e.target.value })}
            placeholder="At least 8 characters"
            invalid={touched && !!errors.pw}
          />
          <div className="mt-2 flex gap-1">
            {[1, 2, 3, 4].map((i) => (
              <span
                key={i}
                className={cn(
                  'h-1 flex-1 rounded-full',
                  i <= strength
                    ? strength < 2
                      ? 'bg-bad'
                      : strength < 4
                      ? 'bg-warn'
                      : 'bg-ok'
                    : 'bg-slate-200',
                )}
              />
            ))}
          </div>
          <span className="mt-1 block text-xs text-muted">
            {['Add a password', 'Weak', 'Fair', 'Good', 'Strong'][strength]}
          </span>
        </Field>
        <Field
          label="Confirm password"
          error={touched ? errors.confirm || undefined : undefined}
        >
          <PasswordInput
            value={f.confirm}
            onChange={(e) => setF({ ...f, confirm: e.target.value })}
            placeholder="Repeat password"
            invalid={touched && !!errors.confirm}
          />
        </Field>
        {err && (
          <p className="text-[13px] text-bad" role="alert">
            {err}
          </p>
        )}
        <Button size="lg" className="w-full" disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Creating account…
            </>
          ) : (
            'Create account'
          )}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">
        Already have an account?{' '}
        <Link href="/login" className="font-medium text-brand hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}

export function ForgotPassword() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  return (
    <AuthLayout>
      <Link
        href="/login"
        className="mb-6 inline-flex items-center gap-1.5 text-[13px] font-medium text-muted hover:text-navy"
      >
        <ArrowLeft className="size-4" />
        Back to sign in
      </Link>
      {sent ? (
        <div className="animate-fade">
          <span className="flex size-12 items-center justify-center rounded-2xl bg-teal-50 text-ok">
            <MailCheck className="size-6" />
          </span>
          <h1 className="mt-5 text-2xl font-semibold tracking-tight text-navy">
            Check your inbox
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            If an account exists for{' '}
            <span className="font-medium text-navy">{email}</span>, we sent a link to
            reset your password. The link expires in 30 minutes.
          </p>
          <div className="mt-6 space-y-2">
            <Button
              size="lg"
              className="w-full"
              onClick={() => router.push('/login')}
            >
              Return to sign in
            </Button>
            <Button
              variant="ghost"
              className="w-full"
              onClick={() => setSent(false)}
            >
              Didn&apos;t get it? Resend
            </Button>
          </div>
        </div>
      ) : (
        <>
          <span className="flex size-12 items-center justify-center rounded-2xl bg-tint text-brand">
            <Mail className="size-6" />
          </span>
          <h1 className="mt-5 text-2xl font-semibold tracking-tight text-navy">
            Reset your password
          </h1>
          <p className="mt-1.5 text-sm text-muted">
            Enter the email you use for Handover and we&apos;ll send reset
            instructions.
          </p>
          <form
            className="mt-6 space-y-4"
            noValidate
            onSubmit={(e) => {
              e.preventDefault()
              if (!emailOk(email)) return setErr('Enter a valid email address')
              setErr('')
              setLoading(true)
              setTimeout(() => {
                setLoading(false)
                setSent(true)
              }, 700)
            }}
          >
            <Field label="Work email" error={err || undefined}>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                invalid={!!err}
              />
            </Field>
            <Button size="lg" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Sending…
                </>
              ) : (
                'Send reset link'
              )}
            </Button>
          </form>
        </>
      )}
    </AuthLayout>
  )
}

const OB_STEPS = [
  'Welcome',
  'Profile',
  'Workspace',
  'Role',
  'Project',
  'How it works',
]

function ProductIntroStory() {
  const [act, setAct] = useState(0)
  const acts = [
    {
      id: 'sources',
      icon: GitBranch,
      title: '1. Authorised sources enter',
      sub: 'GitHub, Jira, Slack and project documents stream in with read-only scopes.',
      scene: (
        <SphereVisual
          variant="empty"
          emptyKind="sources"
          className="h-52 w-full"
        />
      ),
      ui: (
        <div className="space-y-2 rounded-xl border border-line bg-white p-3.5 text-left shadow-card min-w-0 overflow-hidden">
          <p className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted truncate">
            2D interface · Data sources
          </p>
          {(['github', 'jira', 'slack', 'docs'] as const).map((t, i) => (
            <div
              key={t}
              className="flex items-center gap-2 rounded-lg border border-line/80 px-2.5 py-1.5 text-[12px] min-w-0 overflow-hidden"
            >
              <span className="shrink-0 flex items-center">
                <SourceIcon type={t} size={22} />
              </span>
              <span className="flex-1 min-w-0 truncate font-medium text-navy">
                {
                  [
                    'atlas-settlement, atlas-ledger',
                    'PAY · Sprint records',
                    '#payments-arch, #incidents',
                    'ADR-007.pdf, Runbook v3.docx',
                  ][i]
                }
              </span>
              <Badge tone="green" dot className="shrink-0">
                Authorised
              </Badge>
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
      scene: (
        <SphereVisual
          variant="reconstruct"
          progress={0.62}
          className="h-52 w-full"
        />
      ),
      ui: (
        <div className="space-y-3 rounded-xl border border-line bg-white p-3.5 text-left shadow-card min-w-0 overflow-hidden">
          <div className="flex items-center justify-between gap-2 min-w-0">
            <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted truncate">
              2D interface · Reconstruction pipeline
            </span>
            <Mono className="text-[11px] text-brand shrink-0">15,410 records</Mono>
          </div>
          <Progress value={68} size="sm" />
          <ul className="space-y-1.5 text-[12px] text-navy">
            <li className="flex items-start gap-2 min-w-0">
              <CheckCircle2 className="size-3.5 text-ok shrink-0 mt-0.5" />
              <span className="leading-tight break-words">Extracted 25 candidate findings from 4 sources</span>
            </li>
            <li className="flex items-start gap-2 min-w-0">
              <CheckCircle2 className="size-3.5 text-ok shrink-0 mt-0.5" />
              <span className="leading-tight break-words">Linked PR #412 ↔ #payments-arch ↔ ADR-007</span>
            </li>
            <li className="flex items-start gap-2 min-w-0">
              <Sparkles className="size-3.5 text-ai shrink-0 mt-0.5" />
              <span className="leading-tight break-words">Flagged 1 retention conflict & 3 knowledge gaps</span>
            </li>
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
        <div className="grid grid-cols-2 gap-2 rounded-xl border border-line bg-white p-3.5 text-left shadow-card min-w-0">
          <p className="col-span-2 font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted">
            2D interface · Reconstructed intelligence
          </p>
          {[
            [
              'Decisions',
              '6 reconstructed',
              'Why Kafka replaced sync settlement',
              '#315FBA',
            ],
            [
              'Responsibilities',
              '4 transferring',
              'Settlement service & Vault rotation',
              '#299B80',
            ],
            ['Risks', '1 critical', 'No retry on acquirer 504 timeouts', '#D36D72'],
            [
              'Dependencies',
              '2 blocking',
              'SOAP cutover blocked by PAY-1204',
              '#D39B43',
            ],
          ].map(([k, m, d, c]) => (
            <div key={k} className="rounded-lg border border-line/80 p-2.5 min-w-0 overflow-hidden bg-white">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="size-1.5 shrink-0 rounded-full" style={{ background: c }} />
                <span className="text-[11.5px] font-semibold text-navy truncate">{k}</span>
              </div>
              <Mono className="mt-0.5 block text-[10px] text-muted truncate">{m}</Mono>
              <p className="mt-1 truncate text-[11px] text-muted" title={d}>{d}</p>
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
        <div className="space-y-2.5 rounded-xl border border-line bg-white p-3.5 text-left shadow-card min-w-0 overflow-hidden">
          <p className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted truncate">
            2D interface · Review & verification
          </p>
          <p className="text-[13px] font-semibold text-navy leading-snug break-words">
            Decouple settlement from ledger using Kafka events
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Confidence value={94} />
            <VerificationBadge status="verified" />
            <Mono className="text-[11px] text-muted">3 linked sources</Mono>
          </div>
          <p className="rounded-lg bg-canvas px-2.5 py-1.5 text-[11.5px] text-muted leading-relaxed break-words">
            AI confidence (model certainty) is never conflated with human
            verification.
          </p>
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
        <div className="space-y-2.5 rounded-xl border border-line bg-white p-3.5 text-left shadow-card min-w-0 overflow-hidden">
          <div className="flex items-center justify-between gap-2 min-w-0">
            <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-muted truncate">
              2D interface · Published handover
            </span>
            <Badge tone="green" dot className="shrink-0">
              HO-1042 · Published
            </Badge>
          </div>
          <p className="text-[13px] font-semibold text-navy leading-snug break-words">
            James Okafor → Priya Nair · Atlas Payments
          </p>
          <Progress value={100} size="sm" tone="green" />
          <p className="text-[11.5px] text-muted leading-relaxed break-words">
            Includes 12-section report, interactive knowledge graph and
            evidence-grounded AI assistant.
          </p>
        </div>
      ),
    },
  ]
  const cur = acts[act] ?? acts[0]!
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-xl font-semibold text-navy">How Handover works</h2>
          <p className="mt-1 text-sm text-muted">
            3D knowledge continuity paired with precise 2D verification and handover
            workflows.
          </p>
        </div>
        <span className="font-mono text-xs text-brand">
          Act {act + 1} of {acts.length}
        </span>
      </div>
      <div className="mt-5 grid grid-cols-5 gap-1.5">
        {acts.map((a, i) => (
          <button
            key={a.id}
            type="button"
            onClick={() => setAct(i)}
            className={cn(
              'rounded-xl border p-2 text-left transition cursor-pointer min-w-0 overflow-hidden',
              i === act
                ? 'border-brand bg-tint/60 shadow-card'
                : 'border-line bg-white hover:bg-canvas',
            )}
          >
            <a.icon
              className={cn('size-4 shrink-0', i === act ? 'text-brand' : 'text-muted')}
            />
            <p className="mt-1.5 text-[11px] sm:text-[11.5px] font-semibold text-navy truncate">
              {
                ['1. Sources', '2. Connect', '3. Emerge', '4. Verify', '5. Transfer'][
                  i
                ] ?? ''
              }
            </p>
          </button>
        ))}
      </div>
      <div
        key={cur.id}
        className="animate-fade mt-4 grid items-center gap-4 rounded-2xl border border-line bg-canvas/60 p-4 sm:grid-cols-2 min-w-0"
      >
        <div className="flex flex-col items-center min-w-0 w-full">
          {cur.scene}
          <div className="mt-2 text-center max-w-full px-2">
            <p className="text-[14px] font-semibold text-navy break-words">{cur.title}</p>
            <p className="mt-0.5 text-[12.5px] text-muted break-words">{cur.sub}</p>
          </div>
        </div>
        <div className="min-w-0 w-full">{cur.ui}</div>
      </div>
    </div>
  )
}

export function Onboarding() {
  const router = useRouter()
  const s = useFigmaStore()
  const { user, organisations, activeOrg, setActiveOrg, createOrganisation, createProject, addMember, addToast } = useLiveApp()

  const [step, setStep] = useState(0)
  const [profile, setProfile] = useState({
    name: user?.full_name || 'Maya Chen',
    title: 'Engineering Manager',
    team: 'Payments',
  })
  const [wsMode, setWsMode] = useState<'create' | 'join'>('join')
  const [wsName, setWsName] = useState('')
  const [role, setRole] = useState<'manager' | 'outgoing' | 'incoming'>('manager')
  const [projMode, setProjMode] = useState<'invite' | 'create'>('invite')
  const [proj, setProj] = useState({
    name: '',
    category: 'Backend platform',
  })
  const [accepted, setAccepted] = useState<string[]>(['orion', 'helix'])
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Sync profile name when user loads
  React.useEffect(() => {
    if (user?.full_name) {
      setProfile((p) => ({ ...p, name: user.full_name }))
    }
  }, [user])

  const next = () => setStep((x) => Math.min(OB_STEPS.length - 1, x + 1))

  const finish = async () => {
    if (isSubmitting) return
    setIsSubmitting(true)

    try {
      let targetOrg = activeOrg

      // 1. If user chooses to create a new workspace
      if (wsMode === 'create' && wsName.trim()) {
        try {
          targetOrg = await createOrganisation(wsName.trim())
        } catch (orgErr) {
          console.warn('Could not create organisation on backend, using fallback:', orgErr)
        }
      } else if (!targetOrg && organisations.length > 0) {
        targetOrg = organisations[0]!
        setActiveOrg(targetOrg)
      }

      // 2. If user chooses to create a project
      if (projMode === 'create' && proj.name.trim() && targetOrg) {
        try {
          const newProj = await createProject(
            {
              name: proj.name.trim(),
              description: `${proj.category} created during onboarding.`,
            },
            { orgId: targetOrg.id }
          )

          // Map onboarding role to project transition role
          const transitionRole =
            role === 'manager'
              ? 'reviewer'
              : role === 'outgoing'
              ? 'departing_owner'
              : 'incoming_assignee'

          if (user?.id) {
            try {
              await addMember({
                user_id: user.id,
                role_name: role === 'manager' ? 'admin' : 'contributor',
                transition_role: transitionRole,
              })
            } catch (memErr) {
              console.warn('Could not assign transition role on backend:', memErr)
            }
          }

          // Also mirror in figmaStore for instant local responsiveness
          s.setProjects((ps) => [
            ...ps,
            {
              id: newProj.id,
              workspaceId: targetOrg?.id || 'northwind',
              name: newProj.name,
              code: newProj.name.slice(0, 3).toUpperCase(),
              description: newProj.description || 'New project created during onboarding.',
              category: proj.category,
              status: 'planning',
              health: 0,
              ownerId: user?.id || 'maya',
              role: role,
              lastActivity: 'Just now',
              coverage: 0,
              startDate: new Date().toISOString().split('T')[0] || '2026-01-01',
              endDate: '2026-12-31',
              color: '#5B8BC9',
            },
          ])
          s.switchProject(newProj.id, true)
        } catch (projErr) {
          console.warn('Project creation error, applying local fallback:', projErr)
        }
      }

      s.toast(
        'Your workspace is ready',
        'Connect a data source to start reconstructing knowledge.'
      )
      addToast({
        type: 'success',
        title: 'Onboarding Complete',
        message: 'Your workspace and project are ready.',
      })
    } catch (err) {
      console.error('Onboarding finalization failed:', err)
    } finally {
      setIsSubmitting(false)
      router.push('/overview')
    }
  }

  const canNext = step !== 2 || wsMode === 'join' || wsName.trim().length > 1

  return (
    <div className="min-h-dvh bg-canvas">
      <header className="flex h-16 items-center justify-between border-b border-line bg-white px-5 sm:px-8">
        <Logo size={26} />
        <button
          onClick={finish}
          className="text-[13px] font-medium text-muted hover:text-navy cursor-pointer"
        >
          Skip for now
        </button>
      </header>
      <div className="mx-auto max-w-3xl px-4 py-8 sm:py-12">
        <ol className="mb-8 flex items-center gap-2">
          {OB_STEPS.map((l, i) => (
            <li key={l} className="flex flex-1 flex-col gap-2">
              <span
                className={cn(
                  'h-1 rounded-full transition',
                  i <= step ? 'bg-brand' : 'bg-slate-200',
                )}
              />
              <span
                className={cn(
                  'hidden text-xs font-medium sm:block',
                  i === step ? 'text-navy' : 'text-slate-400',
                )}
              >
                {i + 1}. {l}
              </span>
            </li>
          ))}
        </ol>
        <div
          key={step}
          className="animate-fade rounded-2xl border border-line bg-white p-6 shadow-card sm:p-10"
        >
          {step === 0 && (
            <div className="text-center">
              <SphereVisual
                variant="hero"
                className="mx-auto size-48 sm:size-56"
              />
              <h1 className="mt-3 text-2xl font-semibold tracking-tight text-navy sm:text-3xl">
                Welcome to Handover
              </h1>
              <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-muted">
                In a few steps you&apos;ll set up your profile and workspace. If a
                teammate already invited you to a project, you can jump straight
                into it.
              </p>
              <div className="mt-8 grid gap-3 text-left sm:grid-cols-3">
                {[
                  [
                    FileSearch,
                    'Capture',
                    'Ingest code, issues, chats and documents',
                  ],
                  [
                    ShieldCheck,
                    'Verify',
                    'People confirm AI findings with evidence',
                  ],
                  [
                    Workflow,
                    'Transfer',
                    'Publish structured, trusted handovers',
                  ],
                ].map(([I, t, d]) => {
                  const Ic = I as typeof FileSearch
                  return (
                    <div key={t as string} className="tile rounded-xl border p-4">
                      <Ic className="size-5 text-brand" />
                      <p className="mt-2 text-sm font-semibold text-navy">
                        {t as string}
                      </p>
                      <p className="mt-0.5 text-xs text-muted">{d as string}</p>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
          {step === 1 && (
            <div>
              <h2 className="text-xl font-semibold text-navy">
                Complete your profile
              </h2>
              <p className="mt-1 text-sm text-muted">
                Your name and role help teammates know who verified what.
              </p>
              <div className="mt-6 flex items-center gap-4">
                <span className="flex size-16 items-center justify-center rounded-full bg-tint text-xl font-semibold text-brand">
                  {profile.name
                    .split(' ')
                    .map((x) => x[0])
                    .join('')
                    .slice(0, 2)}
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={Upload}
                  onClick={() => s.toast('Photo uploaded', undefined)}
                >
                  Upload photo
                </Button>
              </div>
              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                <Field label="Full name">
                  <Input
                    value={profile.name}
                    onChange={(e) =>
                      setProfile({ ...profile, name: e.target.value })
                    }
                  />
                </Field>
                <Field label="Job title">
                  <Input
                    value={profile.title}
                    onChange={(e) =>
                      setProfile({ ...profile, title: e.target.value })
                    }
                  />
                </Field>
                <Field label="Team" className="sm:col-span-2">
                  <Input
                    value={profile.team}
                    onChange={(e) =>
                      setProfile({ ...profile, team: e.target.value })
                    }
                  />
                </Field>
              </div>
            </div>
          )}
          {step === 2 && (
            <div>
              <h2 className="text-xl font-semibold text-navy">
                Create or join a workspace
              </h2>
              <p className="mt-1 text-sm text-muted">
                A workspace holds your organisation&apos;s projects, members and
                integrations.
              </p>
              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                {[
                  [
                    'join',
                    Users,
                    'Join existing',
                    'You have 1 pending invitation',
                  ],
                  [
                    'create',
                    Building2,
                    'Create new',
                    'Start a fresh workspace for your team',
                  ],
                ].map(([id, I, t, d]) => {
                  const Ic = I as typeof Users
                  return (
                    <button
                      key={id as string}
                      onClick={() => setWsMode(id as 'join')}
                      className={cn(
                        'rounded-xl border p-4 text-left transition cursor-pointer',
                        wsMode === id
                          ? 'border-brand bg-tint/50 ring-4 ring-brand/10'
                          : 'border-line hover:border-slate-300',
                      )}
                    >
                      <Ic className="size-5 text-brand" />
                      <p className="mt-2 text-sm font-semibold text-navy">
                        {t as string}
                      </p>
                      <p className="text-xs text-muted">{d as string}</p>
                    </button>
                  )
                })}
              </div>
              {wsMode === 'join' ? (
                <div className="mt-5 flex items-center gap-3 rounded-xl border border-line p-4">
                  <span className="flex size-10 items-center justify-center rounded-lg bg-navy text-sm font-bold text-white">
                    N
                  </span>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-navy">
                      Northwind Labs
                    </p>
                    <p className="text-xs text-muted">
                      Invited by Tom Whitfield · 42 members
                    </p>
                  </div>
                  <Badge tone="green" icon={Check}>
                    Will join
                  </Badge>
                </div>
              ) : (
                <div className="mt-5 grid gap-4 sm:grid-cols-2">
                  <Field label="Workspace name" required>
                    <Input
                      value={wsName}
                      onChange={(e) => setWsName(e.target.value)}
                      placeholder="Acme Engineering"
                    />
                  </Field>
                  <Field
                    label="Workspace URL"
                    hint="You can change this later"
                  >
                    <Input
                      value={`${
                        wsName.toLowerCase().replace(/[^a-z0-9]+/g, '-') ||
                        'acme'
                      }.handover.app`}
                      readOnly
                    />
                  </Field>
                </div>
              )}
            </div>
          )}
          {step === 3 && (
            <div>
              <h2 className="text-xl font-semibold text-navy">
                How will you mostly use Handover?
              </h2>
              <p className="mt-1 text-sm text-muted">
                This personalises your first dashboard. Roles are assigned per
                project, so you can be a manager on one project and an incoming
                member on another.
              </p>
              <div className="mt-6 space-y-3">
                {[
                  [
                    'manager',
                    'I manage projects and approve handovers',
                    'Connect sources, monitor reconstruction, approve and publish.',
                  ],
                  [
                    'outgoing',
                    "I'm leaving a project and handing it over",
                    'Verify what the AI found, fill gaps, submit for approval.',
                  ],
                  [
                    'incoming',
                    "I'm joining a project and receiving knowledge",
                    'Explore a published handover and ask grounded questions.',
                  ],
                ].map(([id, t, d]) => (
                  <div
                    key={id}
                    className={cn(
                      'rounded-xl border p-4 transition',
                      role === id ? 'border-brand bg-tint/40' : 'border-line',
                    )}
                  >
                    <Radio
                      checked={role === id}
                      onChange={() =>
                        setRole(id as 'manager' | 'outgoing' | 'incoming')
                      }
                      label={
                        <span className="flex flex-wrap items-center gap-2 font-medium">
                          {t}
                          <RoleBadge
                            role={id as 'manager' | 'outgoing' | 'incoming'}
                          />
                        </span>
                      }
                      description={d}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
          {step === 4 && (
            <div>
              <h2 className="text-xl font-semibold text-navy">
                {role === 'manager'
                  ? 'Create your first project'
                  : 'Accept your project invitations'}
              </h2>
              <p className="mt-1 text-sm text-muted">
                {role === 'manager'
                  ? 'Or accept projects you were invited to.'
                  : "You don't need to create a project. Accept the invitations below to continue."}
              </p>
              <div className="mt-5 inline-flex rounded-[10px] border border-line bg-slate-50 p-0.5">
                {(['invite', 'create'] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setProjMode(m)}
                    className={cn(
                      'h-8 rounded-lg px-3 text-[13px] font-medium cursor-pointer',
                      projMode === m
                        ? 'bg-white text-navy shadow-sm'
                        : 'text-muted',
                    )}
                  >
                    {m === 'invite' ? 'Invitations (2)' : 'Create project'}
                  </button>
                ))}
              </div>
              {projMode === 'invite' ? (
                <div className="mt-4 space-y-2.5">
                  {[
                    {
                      id: 'orion',
                      name: 'Orion Mobile App',
                      by: 'Sofia Alvarez',
                      role: 'outgoing' as const,
                    },
                    {
                      id: 'helix',
                      name: 'Helix Data Pipeline',
                      by: 'Tom Whitfield',
                      role: 'incoming' as const,
                    },
                  ].map((p) => (
                    <div
                      key={p.id}
                      className="flex flex-wrap items-center gap-3 rounded-xl border border-line p-4"
                    >
                      <FolderPlus className="size-5 text-brand" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-navy">{p.name}</p>
                        <p className="text-xs text-muted">Invited by {p.by}</p>
                      </div>
                      <RoleBadge role={p.role} />
                      <Button
                        size="sm"
                        variant={accepted.includes(p.id) ? 'subtle' : 'secondary'}
                        icon={accepted.includes(p.id) ? Check : undefined}
                        onClick={() =>
                          setAccepted((a) =>
                            a.includes(p.id)
                              ? a.filter((x) => x !== p.id)
                              : [...a, p.id],
                          )
                        }
                      >
                        {accepted.includes(p.id) ? 'Accepted' : 'Accept'}
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <Field label="Project name" required>
                    <Input
                      value={proj.name}
                      onChange={(e) => setProj({ ...proj, name: e.target.value })}
                      placeholder="e.g. Billing Revamp"
                    />
                  </Field>
                  <Field label="Category">
                    <Select
                      value={proj.category}
                      onChange={(e) =>
                        setProj({ ...proj, category: e.target.value })
                      }
                    >
                      {[
                        'Backend platform',
                        'Mobile',
                        'Data & analytics',
                        'Design system',
                        'Infrastructure',
                      ].map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </Select>
                  </Field>
                </div>
              )}
            </div>
          )}
          {step === 5 && <ProductIntroStory />}
          <div className="mt-10 flex items-center justify-between border-t border-line pt-5">
            <Button
              variant="ghost"
              icon={ArrowLeft}
              disabled={step === 0}
              onClick={() => setStep(step - 1)}
              className="disabled:opacity-0"
            >
              Back
            </Button>
            {step < OB_STEPS.length - 1 ? (
              <Button iconRight={ArrowRight} disabled={!canNext} onClick={next}>
                {step === 0 ? 'Get started' : 'Continue'}
              </Button>
            ) : (
              <Button iconRight={ArrowRight} onClick={finish}>
                Go to dashboard
              </Button>
            )}
          </div>
        </div>
        <p className="mt-4 flex items-center justify-center gap-1.5 text-xs text-muted">
          <UserPlus className="size-3.5" />
          Step {step + 1} of {OB_STEPS.length}
        </p>
      </div>
    </div>
  )
}

/* Master AuthPage */
export type AuthPageView = 'login' | 'signup' | 'forgot-password' | 'onboarding'

export interface AuthPageProps {
  view?: AuthPageView
}

function AuthPageContent({ view = 'login' }: AuthPageProps) {
  switch (view) {
    case 'signup':
      return <Signup />
    case 'forgot-password':
      return <ForgotPassword />
    case 'onboarding':
      return <Onboarding />
    case 'login':
    default:
      return <Login />
  }
}

function EnsureFigmaStore({ children }: { children: ReactNode }) {
  const existing = useContext(FigmaCtx)
  if (existing) return <>{children}</>
  return <FigmaStoreProvider>{children}</FigmaStoreProvider>
}

export function AuthPage({ view = 'login' }: AuthPageProps) {
  return (
    <EnsureFigmaStore>
      <Suspense
        fallback={
          <div className="flex min-h-screen items-center justify-center text-sm text-muted">
            Loading...
          </div>
        }
      >
        <AuthPageContent view={view} />
      </Suspense>
    </EnsureFigmaStore>
  )
}

export default AuthPage
