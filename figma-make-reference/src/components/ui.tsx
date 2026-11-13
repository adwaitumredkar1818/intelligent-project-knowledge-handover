import { lazy, Suspense, useEffect, useRef, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'
import { AlertTriangle, Check, CheckCircle2, ChevronDown, ChevronLeft, ChevronRight, CircleAlert, Eye, EyeOff, HelpCircle, Info, Search, ShieldCheck, ShieldQuestion, ShieldX, Sparkles, X, XCircle, type LucideIcon } from 'lucide-react'
import { initials, personById, type Verification } from '@/lib/data'
import type { EmptyKind, SceneProps } from './OrganicScene'

const LazyOrganicScene = lazy(() => import('./OrganicScene'))

/** Static frosted-glass fallback rendered while the 3D scene loads or when WebGL/canvas is unavailable. */
export function StaticSphereFallback({ className, dark }: { className?: string; dark?: boolean }) {
  return (
    <div className={cn('flex items-center justify-center', className)} aria-hidden>
      <div
        className="relative aspect-square w-[68%] rounded-full"
        style={{
          background: dark
            ? 'radial-gradient(circle at 32% 28%, rgba(255,255,255,0.28), rgba(49,95,186,0.22) 52%, rgba(165,160,217,0.28) 84%, rgba(121,151,190,0.36))'
            : 'radial-gradient(circle at 32% 28%, rgba(255,255,255,0.95), rgba(237,242,250,0.6) 52%, rgba(165,160,217,0.25) 84%, rgba(121,151,190,0.34))',
          boxShadow: '0 32px 52px -34px rgba(32,54,83,0.32), inset 0 0 36px rgba(217,233,229,0.55)',
        }}
      />
    </div>
  )
}

/** Reusable lazy-loaded 3D Organic Knowledge Sphere asset system. */
export function SphereVisual(props: SceneProps) {
  return (
    <Suspense fallback={<StaticSphereFallback className={props.className} dark={props.dark} />}>
      <LazyOrganicScene {...props} />
    </Suspense>
  )
}

const RECON_CAPTIONS = [
  'Collecting authorised evidence nodes…',
  'Tracing relationships across commits, issues and threads…',
  'Reconstructing decisions, responsibilities and risks…',
  'Assembling verified knowledge sphere…',
]

/** Application 2 — Calm, non-blocking 3D knowledge reconstruction loading experience. */
export function ReconstructionLoader({
  progress,
  title = 'Reconstructing project knowledge',
  subtitle,
  compact,
  className,
}: {
  progress?: number
  title?: string
  subtitle?: string
  compact?: boolean
  className?: string
}) {
  const pct = progress !== undefined ? Math.max(0, Math.min(100, progress)) : undefined
  const stageIdx = pct !== undefined ? Math.min(3, Math.floor(pct / 26)) : 1
  return (
    <div className={cn('flex flex-col items-center justify-center text-center', compact ? 'py-4' : 'py-6', className)} role="status" aria-live="polite">
      <SphereVisual
        variant="reconstruct"
        progress={pct !== undefined ? pct / 100 : undefined}
        interactive={false}
        className={compact ? 'size-28' : 'size-44 sm:size-52'}
        label="Animated knowledge reconstruction: scattered nodes forming connected pathways and assembling the Organic Knowledge Sphere"
      />
      <p className="mt-2 text-[14px] font-semibold tracking-[-0.01em] text-navy">{title}</p>
      <p className="mt-0.5 max-w-md text-[12.5px] text-muted">{subtitle ?? RECON_CAPTIONS[stageIdx]}</p>
      {pct !== undefined && (
        <div className="mt-3 flex w-full max-w-xs items-center gap-2.5">
          <Progress value={pct} size="sm" tone={pct >= 100 ? 'green' : 'blue'} />
          <Mono className="text-[11.5px] text-muted">{Math.round(pct)}%</Mono>
        </div>
      )}
    </div>
  )
}

export const cn = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(' ')

/* Buttons */
type BtnVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'subtle' | 'success'
const btnVariants: Record<BtnVariant, string> = {
  primary: 'bg-brand text-white hover:bg-brand-dark shadow-[0_1px_0_rgba(255,255,255,0.12)_inset,0_1px_2px_rgba(32,54,83,0.18)] disabled:bg-brand/45',
  secondary: 'bg-white text-navy border border-line hover:bg-[#f8fafd] hover:border-[#c6d2e6] disabled:text-slate-400',
  ghost: 'text-muted hover:bg-tint hover:text-navy',
  subtle: 'bg-blue-50 text-brand hover:bg-blue-100',
  danger: 'bg-bad text-white hover:bg-red-600 disabled:bg-bad/50',
  success: 'bg-ok text-white hover:bg-teal-600 disabled:bg-ok/50',
}
export function Button({ variant = 'primary', size = 'md', icon: Icon, iconRight: IconR, className, children, ...rest }: { variant?: BtnVariant; size?: 'sm' | 'md' | 'lg'; icon?: LucideIcon; iconRight?: LucideIcon } & ButtonHTMLAttributes<HTMLButtonElement>) {
  const sizes = { sm: 'h-8 px-3 text-[13px] gap-1.5', md: 'h-9 px-3.5 text-sm gap-2', lg: 'h-11 px-5 text-sm gap-2' }
  return (
    <button className={cn(!className?.includes('hidden') && 'inline-flex', 'shrink-0 items-center justify-center rounded-[9px] font-semibold tracking-[-0.01em] transition-all duration-200 active:scale-[0.98] disabled:cursor-not-allowed disabled:active:scale-100', sizes[size], btnVariants[variant], className)} {...rest}>
      {Icon && <Icon className={size === 'sm' ? 'size-3.5' : 'size-4'} />}
      {children}
      {IconR && <IconR className={size === 'sm' ? 'size-3.5' : 'size-4'} />}
    </button>
  )
}
export function IconButton({ icon: Icon, label, className, badge, ...rest }: { icon: LucideIcon; label: string; badge?: number } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button aria-label={label} title={label} className={cn('relative size-9 items-center', !className?.includes('hidden') && 'inline-flex', 'justify-center rounded-[9px] text-muted transition-colors hover:bg-tint hover:text-navy', className)} {...rest}>
      <Icon className="size-[18px]" />
      {!!badge && <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-bad px-1 text-[10px] font-semibold text-white ring-2 ring-white">{badge}</span>}
    </button>
  )
}

/* Badges */
export type Tone = 'blue' | 'green' | 'amber' | 'red' | 'gray' | 'indigo' | 'navy'
const toneCls: Record<Tone, string> = {
  blue: 'bg-blue-50 text-blue-700 ring-blue-600/15',
  green: 'bg-teal-50 text-teal-700 ring-teal-600/15',
  amber: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  red: 'bg-red-50 text-red-700 ring-red-600/15',
  gray: 'bg-slate-100 text-slate-600 ring-slate-500/15',
  indigo: 'bg-indigo-50 text-indigo-700 ring-indigo-600/15',
  navy: 'bg-navy text-white ring-navy',
}
const dotCls: Record<Tone, string> = { blue: 'bg-brand', green: 'bg-ok', amber: 'bg-warn', red: 'bg-bad', gray: 'bg-slate-400', indigo: 'bg-indigo-500', navy: 'bg-white' }
export function Badge({ tone = 'gray', dot, icon: Icon, children, className }: { tone?: Tone; dot?: boolean; icon?: LucideIcon; children: ReactNode; className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset', toneCls[tone], className)}>
      {dot && <span className={cn('size-1.5 rounded-full', dotCls[tone])} />}
      {Icon && <Icon className="size-3" />}
      {children}
    </span>
  )
}

const STATUS: Record<string, [Tone, string]> = {
  draft: ['gray', 'Draft'], in_progress: ['blue', 'In progress'], pending_review: ['amber', 'Pending review'], approved: ['indigo', 'Approved'],
  published: ['blue', 'Published'], completed: ['green', 'Completed'], acknowledged: ['green', 'Acknowledged'],
  processing: ['blue', 'Processing'], processed: ['green', 'Processed'], queued: ['gray', 'Queued'], failed: ['red', 'Failed'], running: ['blue', 'Running'], succeeded: ['green', 'Succeeded'],
  pending: ['amber', 'Pending'], in_review: ['amber', 'In review'], critical: ['red', 'Critical'],
  connected: ['green', 'Connected'], syncing: ['blue', 'Syncing'], error: ['red', 'Needs attention'], disconnected: ['gray', 'Not connected'],
  active: ['green', 'Active'], at_risk: ['amber', 'At risk'], planning: ['gray', 'Planning'],
}
export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const [tone, label] = STATUS[status] ?? ['gray', status]
  return <Badge tone={tone} dot className={className}>{label}</Badge>
}

export const VERIF: Record<Verification, { tone: Tone; label: string; icon: LucideIcon; hint: string }> = {
  verified: { tone: 'green', label: 'Verified', icon: ShieldCheck, hint: 'Confirmed correct by a human reviewer.' },
  needs_review: { tone: 'amber', label: 'Needs review', icon: ShieldQuestion, hint: 'AI-generated and not yet confirmed by a person.' },
  rejected: { tone: 'red', label: 'Rejected', icon: ShieldX, hint: 'A reviewer marked this finding as incorrect.' },
  conflicting: { tone: 'red', label: 'Conflicting evidence', icon: AlertTriangle, hint: 'Sources disagree; a reviewer must resolve it.' },
  insufficient: { tone: 'gray', label: 'Insufficient evidence', icon: CircleAlert, hint: 'Not enough supporting evidence to verify.' },
}
export function VerificationBadge({ status }: { status: Verification }) {
  const v = VERIF[status]
  return (
    <Tooltip content={v.hint}>
      <Badge tone={v.tone} icon={v.icon}>{v.label}</Badge>
    </Tooltip>
  )
}

/** AI confidence is shown in indigo with a sparkle so it is never confused with human verification. */
export function Confidence({ value, compact }: { value: number; compact?: boolean }) {
  const level = value >= 85 ? 'High' : value >= 65 ? 'Medium' : 'Low'
  const bars = value >= 85 ? 3 : value >= 65 ? 2 : 1
  return (
    <Tooltip content={`AI confidence ${value}%: how strongly the model believes this, not whether a person has confirmed it.`}>
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border border-dashed border-indigo-200 bg-indigo-50/60 px-1.5 py-0.5 text-xs font-medium text-indigo-700">
        <Sparkles className="size-3" />
        <span className="flex items-end gap-[2px]">
          {[1, 2, 3].map((b) => <span key={b} className={cn('w-[3px] rounded-sm', b <= bars ? 'bg-indigo-500' : 'bg-indigo-200')} style={{ height: 4 + b * 3 }} />)}
        </span>
        {compact ? `${value}%` : `${level} · ${value}%`}
      </span>
    </Tooltip>
  )
}

/* Layout */
export function Card({ className, interactive, children, ...rest }: { className?: string; interactive?: boolean; children: ReactNode } & React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('rounded-[14px] border border-line/85 bg-white', interactive ? 'tile' : 'shadow-card', className)} {...rest}>{children}</div>
}
export function CardHeader({ title, subtitle, action, icon: Icon, className }: { title: ReactNode; subtitle?: ReactNode; action?: ReactNode; icon?: LucideIcon; className?: string }) {
  return (
    <div className={cn('flex items-start justify-between gap-3 px-5 pt-5 pb-3', className)}>
      <div className="flex min-w-0 items-start gap-2.5">
        {Icon && <Icon className="mt-[3px] size-4 shrink-0 text-sky" />}
        <div className="min-w-0">
          <h3 className="text-[15px] font-semibold tracking-[-0.01em] text-navy">{title}</h3>
          {subtitle && <p className="mt-0.5 text-[13px] text-muted">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  )
}
export function PageHeader({ title, subtitle, actions, eyebrow }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode; eyebrow?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow && <div className="mb-1.5">{eyebrow}</div>}
        <h1 className="text-[26px] font-semibold tracking-[-0.025em] text-navy sm:text-[30px]">{title}</h1>
        {subtitle && <p className="mt-1.5 max-w-2xl text-[14px] leading-relaxed text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}
export function Kpi({ label, value, icon: Icon, hint, tone = 'blue', trend }: { label: string; value: ReactNode; icon: LucideIcon; hint?: ReactNode; tone?: Tone; trend?: { value: string; up: boolean } }) {
  const dot: Record<string, string> = { blue: 'bg-brand', green: 'bg-ok', amber: 'bg-warn', red: 'bg-bad', indigo: 'bg-ai', gray: 'bg-slate-300', navy: 'bg-navy' }
  return (
    <Card className="p-4 sm:p-5">
      <p className="flex items-center gap-2 text-[12.5px] font-medium text-muted"><span className={cn('size-1.5 rounded-full', dot[tone])} />{label}<Icon className="ml-auto size-3.5 text-slate-300" /></p>
      <p className="mt-3 text-[28px] font-semibold leading-none tracking-[-0.03em] text-navy tabular-nums">{value}</p>
      <div className="mt-2 flex items-center gap-2 text-xs text-muted">
        {trend && <span className={cn('font-semibold', trend.up ? 'text-teal-600' : 'text-red-600')}>{trend.up ? '↑' : '↓'} {trend.value}</span>}
        {hint}
      </div>
    </Card>
  )
}

/** A single band of metrics divided by hairlines, used instead of rows of identical KPI cards. */
export function MetricBand({ items, className }: { items: { label: string; value: ReactNode; hint?: ReactNode; tone?: Tone; onClick?: () => void; spark?: number[] }[]; className?: string }) {
  const dot: Record<string, string> = { blue: 'bg-brand', green: 'bg-ok', amber: 'bg-warn', red: 'bg-bad', indigo: 'bg-ai', gray: 'bg-slate-300', navy: 'bg-navy' }
  const sc: Record<string, string> = { blue: '#315FBA', green: '#299B80', amber: '#D39B43', red: '#D36D72', indigo: '#8B78C9', gray: '#A0AEC0', navy: '#203653' }
  return (
    <div className={cn('grid grid-cols-2 gap-3.5', items.length === 5 ? 'lg:grid-cols-5' : items.length >= 4 ? 'lg:grid-cols-4' : 'lg:grid-cols-3', className)}>
      {items.map((m) => (
        <button key={m.label} type="button" onClick={m.onClick} disabled={!m.onClick} className={cn('group relative rounded-[14px] border border-line/85 bg-white px-4 py-4 text-left sm:px-5', m.onClick ? 'tile cursor-pointer' : 'shadow-card')}>
          <p className="flex items-center gap-2 text-[12.5px] font-medium text-muted"><span className={cn('size-1.5 rounded-full', dot[m.tone ?? 'blue'])} />{m.label}</p>
          <div className="mt-2.5 flex items-end justify-between gap-3">
            <p className="text-[28px] font-semibold leading-none tracking-[-0.035em] text-navy tabular-nums sm:text-[30px]">{m.value}</p>
            {m.spark && <Sparkline values={m.spark} color={sc[m.tone ?? 'blue']} />}
          </div>
          {m.hint && <p className="mt-2 text-xs text-muted">{m.hint}</p>}
        </button>
      ))}
    </div>
  )
}

export function Sparkline({ values, color = '#315FBA', w = 72, h = 26 }: { values: number[]; color?: string; w?: number; h?: number }) {
  const max = Math.max(...values), min = Math.min(...values)
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * w},${h - 2 - ((v - min) / (max - min || 1)) * (h - 4)}`).join(' ')
  return <svg width={w} height={h} className="shrink-0" aria-hidden><polyline points={pts} fill="none" stroke={color} strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" opacity="0.85" /></svg>
}

export function Mono({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn('font-mono text-[0.92em] tracking-[-0.01em]', className)}>{children}</span>
}

export function SectionLabel({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn('text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400', className)}>{children}</p>
}

/* Form controls */
const inputCls = 'h-10 w-full rounded-[9px] border border-line bg-white px-3 text-sm text-navy placeholder:text-slate-400 transition focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/10 disabled:bg-slate-50'
export function Field({ label, hint, error, children, className, required }: { label: string; hint?: string; error?: string; children: ReactNode; className?: string; required?: boolean }) {
  return (
    <label className={cn('block', className)}>
      <span className="mb-1.5 block text-[13px] font-medium text-navy">{label}{required && <span className="text-bad"> *</span>}</span>
      {children}
      {error ? <span className="mt-1 block text-xs text-bad">{error}</span> : hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  )
}
export function Input({ className, invalid, ...rest }: InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }) {
  return <input className={cn(inputCls, invalid && 'border-bad focus:border-bad focus:ring-bad/10', className)} {...rest} />
}
export function PasswordInput(props: InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <Input {...props} type={show ? 'text' : 'password'} className="pr-10" />
      <button type="button" onClick={() => setShow(!show)} aria-label={show ? 'Hide password' : 'Show password'} className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 hover:text-navy">
        {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
      </button>
    </div>
  )
}
export function Textarea({ className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(inputCls, 'h-auto min-h-[88px] py-2.5 leading-relaxed', className)} {...rest} />
}
export function Select({ className, children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className={cn('relative', className)}>
      <select className={cn(inputCls, 'appearance-none pr-9')} {...rest}>{children}</select>
      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
    </div>
  )
}
export function SearchInput({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className={cn('relative', className)}>
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
      <input className={cn(inputCls, 'h-9 pl-9')} {...rest} />
    </div>
  )
}
export function Checkbox({ checked, onChange, label, description }: { checked: boolean; onChange: (v: boolean) => void; label?: ReactNode; description?: ReactNode }) {
  return (
    <label className="flex cursor-pointer items-start gap-2.5 text-sm">
      <button type="button" role="checkbox" aria-checked={checked} onClick={() => onChange(!checked)} className={cn('mt-0.5 flex size-[18px] shrink-0 items-center justify-center rounded-[5px] border transition', checked ? 'border-brand bg-brand text-white' : 'border-slate-300 bg-white hover:border-brand')}>
        {checked && <Check className="size-3" strokeWidth={3} />}
      </button>
      {(label || description) && <span><span className="text-navy">{label}</span>{description && <span className="block text-xs text-muted">{description}</span>}</span>}
    </label>
  )
}
export function Radio({ checked, onChange, label, description }: { checked: boolean; onChange: () => void; label: ReactNode; description?: ReactNode }) {
  return (
    <label className="flex cursor-pointer items-start gap-2.5 text-sm" onClick={onChange}>
      <span className={cn('mt-0.5 flex size-[18px] shrink-0 items-center justify-center rounded-full border transition', checked ? 'border-brand' : 'border-slate-300')}>{checked && <span className="size-2.5 rounded-full bg-brand" />}</span>
      <span><span className="text-navy">{label}</span>{description && <span className="block text-xs text-muted">{description}</span>}</span>
    </label>
  )
}
export function Switch({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label?: string }) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} onClick={() => onChange(!checked)} className={cn('relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition', checked ? 'bg-brand' : 'bg-slate-300')}>
      <span className={cn('inline-block size-4 rounded-full bg-white shadow transition', checked ? 'translate-x-[18px]' : 'translate-x-0.5')} />
    </button>
  )
}

/* Tabs */
export function Tabs<T extends string>({ tabs, value, onChange, className }: { tabs: { id: T; label: string; count?: number; icon?: LucideIcon }[]; value: T; onChange: (v: T) => void; className?: string }) {
  return (
    <div className={cn('scrollbar-thin -mb-px flex gap-1 overflow-x-auto border-b border-line', className)} role="tablist">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id} onClick={() => onChange(t.id)} className={cn('flex shrink-0 items-center gap-1.5 border-b-2 px-3 pb-2.5 pt-1 text-sm font-medium transition', value === t.id ? 'border-brand text-brand' : 'border-transparent text-muted hover:text-navy')}>
          {t.icon && <t.icon className="size-4" />}
          {t.label}
          {t.count !== undefined && <span className={cn('rounded-full px-1.5 text-[11px]', value === t.id ? 'bg-tint text-brand' : 'bg-slate-100 text-slate-500')}>{t.count}</span>}
        </button>
      ))}
    </div>
  )
}
export function Segmented<T extends string>({ options, value, onChange }: { options: { id: T; label?: string; icon?: LucideIcon }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="inline-flex rounded-[10px] border border-line bg-slate-50 p-0.5">
      {options.map((o) => (
        <button key={o.id} onClick={() => onChange(o.id)} aria-label={o.label ?? o.id} className={cn('flex h-7 items-center gap-1.5 rounded-lg px-2.5 text-[13px] font-medium transition', value === o.id ? 'bg-white text-navy shadow-sm' : 'text-muted hover:text-navy')}>
          {o.icon && <o.icon className="size-3.5" />}
          {o.label}
        </button>
      ))}
    </div>
  )
}

/* People */
export function Avatar({ id, name, size = 28, className, ring }: { id?: string; name?: string; size?: number; className?: string; ring?: boolean }) {
  const p = id ? personById(id) : undefined
  const n = name ?? p?.name ?? '?'
  const color = p?.color ?? '#718096'
  return (
    <span title={n} className={cn('inline-flex shrink-0 items-center justify-center rounded-full font-semibold', ring && 'ring-2 ring-white', className)} style={{ width: size, height: size, fontSize: size * 0.38, background: `${color}1A`, color }}>
      {initials(n)}
    </span>
  )
}
export function AvatarGroup({ ids, max = 4, size = 26 }: { ids: string[]; max?: number; size?: number }) {
  return (
    <div className="flex -space-x-2">
      {ids.slice(0, max).map((id) => <Avatar key={id} id={id} size={size} ring />)}
      {ids.length > max && <span className="inline-flex items-center justify-center rounded-full bg-slate-100 text-[11px] font-semibold text-slate-600 ring-2 ring-white" style={{ width: size, height: size }}>+{ids.length - max}</span>}
    </div>
  )
}
export function PersonCell({ id, sub }: { id: string; sub?: ReactNode }) {
  const p = personById(id)
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <Avatar id={id} size={28} />
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-navy">{p.name}</p>
        <p className="truncate text-xs text-muted">{sub ?? p.title}</p>
      </div>
    </div>
  )
}

/* Feedback */
export function Progress({ value, tone = 'blue', className, size = 'md' }: { value: number; tone?: 'blue' | 'green' | 'amber' | 'red'; className?: string; size?: 'sm' | 'md' }) {
  const c = { blue: 'bg-brand', green: 'bg-ok', amber: 'bg-warn', red: 'bg-bad' }[tone]
  return (
    <div className={cn('w-full overflow-hidden rounded-full bg-slate-100', size === 'sm' ? 'h-1.5' : 'h-2', className)}>
      <div className={cn('h-full rounded-full transition-all duration-500', c)} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  )
}
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton rounded-lg', className)} />
}

const EMPTY_KIND_TAG: Record<EmptyKind, string> = {
  project: 'Unseeded project space',
  sources: 'Disconnected source clusters',
  knowledge: 'Shell awaiting extracted findings',
  relationships: 'Nodes awaiting linked pathways',
  ingestion: 'Partial ingestion in progress',
}

function inferEmptySphere(title: string): EmptyKind | undefined {
  const t = title.toLowerCase()
  if (t.includes('match') || t.includes('filter') || t.includes('found') || t.includes('caught up') || t.includes('conversation')) return undefined
  if (t.includes('source')) return 'sources'
  if (t.includes('ingestion') || t.includes('job') || t.includes('evidence')) return 'ingestion'
  if (t.includes('relationship') || t.includes('explorer') || t.includes('graph')) return 'relationships'
  if (t.includes('knowledge') || t.includes('reconstructed') || t.includes('finding') || t.includes('gap')) return 'knowledge'
  if (t.includes('project') || t.includes('handover') || t.includes('inbox') || t.includes('published') || t.includes('activity')) return 'project'
  return undefined
}

export function EmptyState({
  icon: Icon,
  title,
  body,
  action,
  sphere,
  className,
}: {
  icon: LucideIcon
  title: string
  body: ReactNode
  action?: ReactNode
  sphere?: EmptyKind | false
  className?: string
}) {
  const kind = sphere === false ? undefined : sphere ?? inferEmptySphere(title)
  return (
    <div className={cn('flex flex-col items-center justify-center px-6 py-12 text-center', className)}>
      {kind ? (
        <div className="mb-3 flex flex-col items-center">
          <SphereVisual
            variant="empty"
            emptyKind={kind}
            interactive={false}
            className="size-32 sm:size-36"
            label={`Empty state 3D sphere (${EMPTY_KIND_TAG[kind]})`}
          />
          <span className="mt-0.5 rounded-full border border-line bg-white/90 px-2.5 py-0.5 font-mono text-[10px] tracking-[0.06em] text-muted">
            {EMPTY_KIND_TAG[kind]}
          </span>
        </div>
      ) : (
        <div className="relative mb-4">
          <div className="absolute inset-0 -m-3 rounded-full bg-tint/70" />
          <span className="relative flex size-12 items-center justify-center rounded-2xl border border-line bg-white text-brand shadow-card"><Icon className="size-5" /></span>
        </div>
      )}
      <h3 className="text-[15px] font-semibold tracking-[-0.01em] text-navy">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-muted">{body}</p>
      {action && <div className="mt-5 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  )
}
export function ErrorState({ title, body, action }: { title: string; body: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50/60 p-4">
      <XCircle className="mt-0.5 size-5 shrink-0 text-bad" />
      <div className="flex-1">
        <p className="text-sm font-semibold text-red-800">{title}</p>
        <p className="mt-0.5 text-[13px] text-red-700/90">{body}</p>
        {action && <div className="mt-3">{action}</div>}
      </div>
    </div>
  )
}
export function Callout({ tone = 'blue', icon: Icon = Info, title, children, action }: { tone?: 'blue' | 'amber' | 'green' | 'red'; icon?: LucideIcon; title?: ReactNode; children?: ReactNode; action?: ReactNode }) {
  const c = { blue: 'border-blue-200 bg-blue-50/60 text-blue-900', amber: 'border-amber-200 bg-amber-50/70 text-amber-900', green: 'border-teal-200 bg-teal-50/60 text-teal-900', red: 'border-red-200 bg-red-50/60 text-red-900' }[tone]
  const ic = { blue: 'text-brand', amber: 'text-warn', green: 'text-ok', red: 'text-bad' }[tone]
  return (
    <div className={cn('flex flex-col gap-3 rounded-xl border p-3.5 sm:flex-row sm:items-center', c)}>
      <div className="flex flex-1 items-start gap-2.5">
        <Icon className={cn('mt-0.5 size-4 shrink-0', ic)} />
        <div className="text-[13px] leading-relaxed">{title && <p className="font-semibold">{title}</p>}{children}</div>
      </div>
      {action}
    </div>
  )
}
export function Tooltip({ content, children, side = 'top' }: { content: ReactNode; children: ReactNode; side?: 'top' | 'bottom' }) {
  return (
    <span className="group/tt relative inline-flex">
      {children}
      <span role="tooltip" className={cn('pointer-events-none absolute left-1/2 z-50 w-max max-w-[240px] -translate-x-1/2 rounded-lg bg-navy px-2.5 py-1.5 text-xs font-normal leading-snug text-white opacity-0 shadow-pop transition-opacity delay-150 group-hover/tt:opacity-100', side === 'top' ? 'bottom-full mb-2' : 'top-full mt-2')}>{content}</span>
    </span>
  )
}
export function HelpTip({ content }: { content: ReactNode }) {
  return <Tooltip content={content}><HelpCircle className="size-3.5 text-slate-400" /></Tooltip>
}

/* Overlays */
export function Modal({ open, onClose, title, subtitle, children, footer, size = 'md' }: { open: boolean; onClose: () => void; title: ReactNode; subtitle?: ReactNode; children: ReactNode; footer?: ReactNode; size?: 'sm' | 'md' | 'lg' }) {
  useEffect(() => {
    if (!open) return
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [open, onClose])
  if (!open) return null
  const w = { sm: 'max-w-md', md: 'max-w-lg', lg: 'max-w-2xl' }[size]
  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-navy/30 p-0 backdrop-blur-[2px] sm:items-center sm:p-4" onMouseDown={onClose}>
      <div role="dialog" aria-modal className={cn('animate-fade flex max-h-[92vh] w-full flex-col rounded-t-2xl bg-white shadow-pop sm:rounded-2xl', w)} onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div>
            <h2 className="text-base font-semibold text-navy">{title}</h2>
            {subtitle && <p className="mt-0.5 text-[13px] text-muted">{subtitle}</p>}
          </div>
          <IconButton icon={X} label="Close" onClick={onClose} className="-mr-2 -mt-1" />
        </div>
        <div className="scrollbar-thin overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex flex-col-reverse gap-2 border-t border-line bg-slate-50/60 px-5 py-3.5 sm:flex-row sm:justify-end">{footer}</div>}
      </div>
    </div>
  )
}
export function ConfirmDialog({ open, onClose, onConfirm, title, body, confirmLabel = 'Confirm', tone = 'primary' }: { open: boolean; onClose: () => void; onConfirm: () => void; title: string; body: ReactNode; confirmLabel?: string; tone?: 'primary' | 'danger' }) {
  return (
    <Modal open={open} onClose={onClose} size="sm" title={
      <span className="flex items-center gap-2.5">
        <span className={cn('flex size-8 items-center justify-center rounded-full', tone === 'danger' ? 'bg-red-50 text-bad' : 'bg-tint text-brand')}>{tone === 'danger' ? <AlertTriangle className="size-4" /> : <CheckCircle2 className="size-4" />}</span>
        {title}
      </span>
    } footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button variant={tone === 'danger' ? 'danger' : 'primary'} onClick={() => { onConfirm(); onClose() }}>{confirmLabel}</Button></>}>
      <div className="text-sm leading-relaxed text-muted">{body}</div>
    </Modal>
  )
}
export function Drawer({ open, onClose, title, children, footer, width = 'max-w-lg' }: { open: boolean; onClose: () => void; title: ReactNode; children: ReactNode; footer?: ReactNode; width?: string }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-[55] flex justify-end bg-navy/20" onMouseDown={onClose}>
      <div className={cn('animate-slide flex h-full w-full flex-col bg-white shadow-pop', width)} onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-4">
          <div className="min-w-0 text-base font-semibold text-navy">{title}</div>
          <IconButton icon={X} label="Close" onClick={onClose} />
        </div>
        <div className="scrollbar-thin flex-1 overflow-y-auto p-5">{children}</div>
        {footer && <div className="flex gap-2 border-t border-line p-4">{footer}</div>}
      </div>
    </div>
  )
}
export function Dropdown({ trigger, children, align = 'right', width = 'w-56' }: { trigger: (open: boolean) => ReactNode; children: (close: () => void) => ReactNode; align?: 'left' | 'right'; width?: string }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const h = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false)
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [open])
  return (
    <div className="relative" ref={ref}>
      <div onClick={() => setOpen(!open)}>{trigger(open)}</div>
      {open && <div className={cn('animate-fade absolute z-50 mt-1.5 rounded-xl border border-line bg-white p-1 shadow-pop', width, align === 'right' ? 'right-0' : 'left-0')}>{children(() => setOpen(false))}</div>}
    </div>
  )
}
export function MenuItem({ icon: Icon, children, onClick, danger, active, hint }: { icon?: LucideIcon; children: ReactNode; onClick?: () => void; danger?: boolean; active?: boolean; hint?: ReactNode }) {
  return (
    <button onClick={onClick} className={cn('flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition', danger ? 'text-red-600 hover:bg-red-50' : 'text-navy hover:bg-tint', active && 'bg-tint')}>
      {Icon && <Icon className={cn('size-4', danger ? 'text-red-500' : 'text-muted')} />}
      <span className="flex-1 truncate">{children}</span>
      {hint}
      {active && <Check className="size-4 text-brand" />}
    </button>
  )
}

/* Tables */
export function Table({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('scrollbar-thin overflow-x-auto', className)}><table className="w-full min-w-[720px] text-left text-sm">{children}</table></div>
}
export function Th({ children, className }: { children?: ReactNode; className?: string }) {
  return <th className={cn('whitespace-nowrap border-b border-line bg-slate-50/70 px-4 py-2.5 text-xs font-medium text-muted first:pl-5 last:pr-5', className)}>{children}</th>
}
export function Td({ children, className }: { children?: ReactNode; className?: string }) {
  return <td className={cn('border-b border-line/70 px-4 py-3 align-middle first:pl-5 last:pr-5', className)}>{children}</td>
}
export function Pagination({ page, pages, onChange, total }: { page: number; pages: number; onChange: (p: number) => void; total: number }) {
  return (
    <div className="flex items-center justify-between px-5 py-3 text-[13px] text-muted">
      <span>{total} records</span>
      <div className="flex items-center gap-1">
        <IconButton icon={ChevronLeft} label="Previous page" disabled={page <= 1} onClick={() => onChange(page - 1)} className="size-8 disabled:opacity-40" />
        {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
          <button key={p} onClick={() => onChange(p)} className={cn('size-8 rounded-lg text-[13px] font-medium', p === page ? 'bg-tint text-brand' : 'hover:bg-slate-100')}>{p}</button>
        ))}
        <IconButton icon={ChevronRight} label="Next page" disabled={page >= pages} onClick={() => onChange(page + 1)} className="size-8 disabled:opacity-40" />
      </div>
    </div>
  )
}

export function useFakeLoading(ms = 550, deps: unknown[] = []) {
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    setLoading(true)
    const t = setTimeout(() => setLoading(false), ms)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return loading
}
