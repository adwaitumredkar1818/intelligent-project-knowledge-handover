'use client'

import React, { useEffect, useMemo, useState, useCallback, useContext, type ReactNode } from 'react'
import { useRouter, useParams, useSearchParams } from 'next/navigation'
import NextLink from 'next/link'
import {
  AlertTriangle, ArrowRight, Boxes, CheckCircle2, ChevronDown, ChevronRight, Clock,
  Cpu, Database, ExternalLink, FileSearch, FileUp, Filter, GitMerge, HardDrive,
  Layers, Link2, List, Loader2, Lock, Network, Plug, Plus, RefreshCw, RotateCcw,
  Search, ShieldCheck, Sparkles, Unplug, Upload, User, XCircle, Activity, ScanText,
  Workflow, BrainCircuit, History, Maximize2, Minimize2, Columns3, Check, FileText
} from 'lucide-react'

import { useFigmaStore as useStore, FigmaStoreProvider, FigmaCtx } from '../../lib/figmaStore'
import { useLiveApp } from '../../context/LiveAppContext'
import {
  evidence, personById, SOURCE_META,
  type Evidence, type Source, type SourceType, type Verification
} from '../../lib/figmaStore'

import {
  MetricBand, Avatar, Badge, Button, Callout, Card, CardHeader, Checkbox,
  ConfirmDialog, Drawer, EmptyState, ErrorState, Field, Modal, PageHeader,
  Pagination, Progress, ReconstructionLoader, SearchInput, Segmented, Select,
  SphereVisual, StatusBadge, Table, Td, Th, VerifyBadge as VerificationBadge,
  cn, ConfidenceBadge as Confidence, Switch, Skeleton, useFakeLoading
} from '../figma-ui/index'

import { SourceIcon, EvidenceTypeIcon, EVIDENCE_TYPE_LABEL } from '../figma-ui/brand'
import { BarChart } from '../figma-ui/charts'
import {
  allFindings, FindingDrawer, FindingRowMeta, PermissionNote, ProjectHeader,
  ProjectNotFound, useProject, type AnyFinding, ConfidenceLegend, EvidenceCard, EvidenceChip
} from '../figma-ui/domain'
import { NODE_COLOR, KnowledgeCanvas, buildGraph, type NodeKind } from '../figma-ui/graph'

/* ---------- Navigation & Router Helpers ---------- */
function Link({ to, href, className, children, onClick }: { to?: string; href?: string; className?: string; children: ReactNode; onClick?: () => void }) {
  const target = href || to || '#'
  return <NextLink href={target} className={className} onClick={onClick}>{children}</NextLink>
}

/* ---------- 10. Data Sources Constants & Connect Modal ---------- */
const REPOS: Record<SourceType, string[]> = {
  github: ['atlas-ledger', 'atlas-settlement', 'atlas-gateway', 'atlas-infra', 'payments-sdk-js', 'northwind-docs'],
  jira: ['PAY · Payments', 'PAYOPS · Payments Ops', 'SEC · Security', 'PLAT · Platform'],
  slack: ['#payments-arch', '#payments-oncall', '#incidents', '#eng-general', '#releases'],
  docs: [],
  confluence: ['ENG · Engineering', 'PAY · Payments space', 'OPS · Runbooks'],
  gdrive: ['Payments / Architecture', 'Payments / Vendor contracts'],
}

const SCOPES: Record<SourceType, string[]> = {
  github: ['Read repository contents', 'Read commits, pull requests and reviews', 'Read repository metadata and CODEOWNERS'],
  jira: ['Read issues, comments and history', 'Read sprints and boards'],
  slack: ['Read messages in selected public channels', 'Read user profiles (name, title)'],
  docs: ['Store uploaded files encrypted at rest'],
  confluence: ['Read pages in selected spaces'],
  gdrive: ['Read files in selected folders'],
}

function ConnectFlow({ type, projectId, onClose }: { type: SourceType; projectId: string; onClose: () => void }) {
  const s = useStore()
  const router = useRouter()
  const isUpload = type === 'docs'
  const [step, setStep] = useState<'auth' | 'waiting' | 'select' | 'connecting' | 'done' | 'error'>(isUpload ? 'select' : 'auth')
  const [sel, setSel] = useState<string[]>(REPOS[type]?.slice(0, 3) ?? [])
  const [freq, setFreq] = useState('Every 15 minutes')
  const [range, setRange] = useState('12')
  const [files, setFiles] = useState<string[]>([])
  const meta = SOURCE_META[type] || { label: type, description: '' }

  const authorise = () => {
    setStep('waiting')
    setTimeout(() => setStep('select'), 1100)
  }

  const connect = () => {
    setStep('connecting')
    setTimeout(() => {
      const id = `src-${type}-${projectId}`
      const src: Source = {
        id,
        projectId,
        type,
        name: meta.label,
        account: isUpload ? 'Manual uploads' : type === 'slack' ? 'Northwind HQ' : 'northwind-eng',
        status: 'syncing',
        lastSync: 'Syncing now',
        records: 0,
        scope: isUpload ? files : sel,
        frequency: isUpload ? 'On upload' : freq,
        volume: '—',
      }
      s.setSources((ss) => (ss.some((x) => x.id === id) ? ss.map((x) => (x.id === id ? src : x)) : [...ss, src]))
      s.setJobs((js) => [
        {
          id: `job-${Math.floor(Math.random() * 1000) + 9000}`,
          projectId,
          sourceId: id,
          started: 'Just now',
          records: 0,
          status: 'running',
          duration: '—',
        },
        ...js,
      ])
      setStep('done')
    }, 1400)
  }

  return (
    <Modal
      open
      onClose={onClose}
      size="md"
      title={
        <span className="flex items-center gap-2.5">
          <SourceIcon type={type} size={28} />
          Connect {meta.label}
        </span>
      }
      footer={
        step === 'auth' ? (
          <>
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
            <Button icon={ShieldCheck} onClick={authorise}>Authorise with {meta.label}</Button>
          </>
        ) : step === 'select' ? (
          <>
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
            <Button disabled={isUpload ? !files.length : !sel.length} onClick={connect}>
              {isUpload ? `Upload ${files.length} files` : `Connect ${sel.length} ${type === 'github' ? 'repositories' : type === 'slack' ? 'channels' : 'projects'}`}
            </Button>
          </>
        ) : step === 'done' ? (
          <>
            <Button variant="secondary" onClick={onClose}>Done</Button>
            <Button iconRight={ArrowRight} onClick={() => { onClose(); router.push(`/projects/${projectId}/ingestion`) }}>
              View ingestion activity
            </Button>
          </>
        ) : undefined
      }
    >
      <div className="mb-5 flex items-center gap-1.5 text-[11px] font-medium text-slate-400">
        {(isUpload ? ['Upload', 'Process'] : ['Authorise', 'Select scope', 'Connect']).map((l, i, arr) => {
          const idx = isUpload ? (step === 'done' || step === 'connecting' ? 1 : 0) : step === 'auth' || step === 'waiting' ? 0 : step === 'select' ? 1 : 2
          return (
            <span key={l} className="flex items-center gap-1.5">
              <span className={cn('rounded-full px-2 py-0.5', i <= idx ? 'bg-tint text-brand' : 'bg-slate-100')}>
                {i + 1}. {l}
              </span>
              {i < arr.length - 1 && <ChevronRight className="size-3" />}
            </span>
          )
        })}
      </div>

      {step === 'auth' && (
        <div>
          <div className="rounded-xl border border-line bg-slate-50/60 p-4">
            <div className="flex items-center gap-3">
              <SourceIcon type={type} size={40} />
              <ArrowRight className="size-4 text-slate-400" />
              <span className="flex size-10 items-center justify-center rounded-[10px] border border-line bg-white">
                <svg width="22" height="22" viewBox="0 0 32 32">
                  <path d="M7 19v-5a7 7 0 0 1 7-7h7" fill="none" stroke="#203653" strokeWidth="3.4" strokeLinecap="round" />
                  <path d="M25 13v5a7 7 0 0 1-7 7h-7" fill="none" stroke="#315FBA" strokeWidth="3.4" strokeLinecap="round" />
                </svg>
              </span>
            </div>
            <p className="mt-3 text-sm font-semibold text-navy">Handover is requesting read-only access</p>
            <ul className="mt-2 space-y-1.5">
              {(SCOPES[type] ?? []).map((x) => (
                <li key={x} className="flex items-center gap-2 text-[13px] text-slate-700">
                  <CheckCircle2 className="size-3.5 text-ok" />{x}
                </li>
              ))}
            </ul>
          </div>
          <p className="mt-3 flex items-start gap-1.5 text-xs text-muted">
            <Lock className="mt-0.5 size-3 shrink-0" />
            Handover never writes to your tools. You choose exactly which {type === 'github' ? 'repositories' : 'channels or projects'} are ingested in the next step.
          </p>
        </div>
      )}

      {step === 'waiting' && (
        <div className="flex flex-col items-center py-10 text-center">
          <Loader2 className="size-8 animate-spin text-brand" />
          <p className="mt-4 text-sm font-medium text-navy">Waiting for {meta.label} authorisation…</p>
          <p className="mt-1 text-xs text-muted">Complete sign-in in the popup window.</p>
        </div>
      )}

      {step === 'select' && !isUpload && (
        <div className="space-y-5">
          <div>
            <div className="mb-2 flex items-center justify-between">
              <p className="text-[13px] font-medium text-navy">
                Select {type === 'github' ? 'repositories' : type === 'slack' ? 'channels' : 'projects'}
              </p>
              <button
                className="text-xs font-medium text-brand"
                onClick={() => setSel(sel.length === (REPOS[type]?.length ?? 0) ? [] : REPOS[type] ?? [])}
              >
                {sel.length === (REPOS[type]?.length ?? 0) ? 'Clear' : 'Select all'}
              </button>
            </div>
            <div className="divide-y divide-line rounded-xl border border-line">
              {(REPOS[type] ?? []).map((r) => (
                <div key={r} className="px-3.5 py-2.5">
                  <Checkbox
                    checked={sel.includes(r)}
                    onChange={(v) => setSel(v ? [...sel, r] : sel.filter((x) => x !== r))}
                    label={<span className="font-mono text-[13px]">{r}</span>}
                  />
                </div>
              ))}
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Sync frequency">
              <Select value={freq} onChange={(e) => setFreq(e.target.value)}>
                {['Every 15 minutes', 'Hourly', 'Daily', 'Manual'].map((x) => <option key={x}>{x}</option>)}
              </Select>
            </Field>
            <Field label="Historical import">
              <Select value={range} onChange={(e) => setRange(e.target.value)}>
                <option value="6">Last 6 months</option>
                <option value="12">Last 12 months</option>
                <option value="24">Last 24 months</option>
              </Select>
            </Field>
          </div>
        </div>
      )}

      {step === 'select' && isUpload && (
        <div>
          <button
            onClick={() => setFiles([...files, (['Architecture overview.pdf', 'Deployment runbook.docx', 'Q2 incident review.pdf', 'API contract v4.docx'][files.length % 4] ?? 'Document.pdf')])}
            className="flex w-full flex-col items-center rounded-xl border-2 border-dashed border-[#D9E1F0] bg-tint/30 px-6 py-10 text-center transition hover:border-brand hover:bg-tint/60"
          >
            <Upload className="size-6 text-brand" />
            <p className="mt-3 text-sm font-medium text-navy">Drop PDF or DOCX files, or click to browse</p>
            <p className="mt-1 text-xs text-muted">Up to 50 MB per file · password-protected files cannot be parsed</p>
          </button>
          {!!files.length && (
            <ul className="mt-3 space-y-1.5">
              {files.map((f, i) => (
                <li key={i} className="flex items-center gap-2.5 rounded-lg border border-line px-3 py-2 text-[13px]">
                  <EvidenceTypeIcon type={f.endsWith('pdf') ? 'pdf' : 'docx'} className="size-6" />
                  <span className="flex-1 truncate text-navy">{f}</span>
                  <span className="text-xs text-muted">Ready</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {step === 'connecting' && (
        <ReconstructionLoader
          progress={72}
          compact
          title="Connecting and scheduling first sync…"
          subtitle="Linking authorised repositories into the project knowledge sphere."
        />
      )}

      {step === 'done' && (
        <div className="flex flex-col items-center py-6 text-center">
          <span className="flex size-14 items-center justify-center rounded-full bg-teal-50 text-ok">
            <CheckCircle2 className="size-7" />
          </span>
          <p className="mt-4 text-base font-semibold text-navy">{meta.label} connected successfully</p>
          <p className="mt-1 max-w-sm text-[13px] text-muted">
            The first import has started. Evidence will appear in the library as it is processed, and findings will be reconstructed automatically.
          </p>
        </div>
      )}
    </Modal>
  )
}

/* ---------- 10. Data Sources View ---------- */
export function DataSources({ projectId }: { projectId: string }) {
  const s = useStore()
  const p = useProject(projectId)
  const router = useRouter()
  const [connecting, setConnecting] = useState<SourceType | null>(null)
  const { openConnectSourceModal, setIsUploadModalOpen, sourceMappings, triggerSync } = useLiveApp()

  if (!p) return <ProjectNotFound />
  const canManage = p.role === 'manager'
  const types: SourceType[] = ['github', 'jira', 'slack', 'docs', 'confluence', 'gdrive']
  const srcs = s.sources.filter((x) => x.projectId === p.id)

  return (
    <>
      <ProjectHeader project={p} tab="sources" />
      {!canManage && (
        <div className="mb-5">
          <PermissionNote role={p.role} action="connect or manage data sources" />
        </div>
      )}
      {srcs.some((x) => x.status === 'error') && (
        <div className="mb-5">
          <ErrorState
            title="A source needs attention"
            body="Slack authorisation expired 2 days ago. New discussions are not being ingested."
            action={
              canManage && (
                <Button
                  size="sm"
                  variant="danger"
                  icon={RefreshCw}
                  onClick={() => router.push(`/projects/${p.id}/sources/${srcs.find((x) => x.status === 'error')!.id}`)}
                >
                  Fix connection
                </Button>
              )
            }
          />
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {types.map((t) => {
          const src = srcs.find((x) => x.type === t)
          const connected = src && src.status !== 'disconnected'
          const meta = SOURCE_META[t] || { label: t, description: '' }
          return (
            <Card key={t} interactive className="flex flex-col p-5">
              <div className="flex items-start justify-between">
                <SourceIcon type={t} size={44} />
                <StatusBadge status={src?.status ?? 'disconnected'} />
              </div>
              <h3 className="mt-4 text-[15px] font-semibold text-navy">{meta.label}</h3>
              <p className="mt-1 flex-1 text-[13px] text-muted">{meta.description}</p>
              {connected ? (
                <dl className="mt-4 grid grid-cols-2 gap-2 rounded-xl bg-slate-50 p-3 text-xs">
                  <div>
                    <dt className="text-muted">Last sync</dt>
                    <dd className="mt-0.5 font-medium text-navy">{src.lastSync}</dd>
                  </div>
                  <div>
                    <dt className="text-muted">Records</dt>
                    <dd className="mt-0.5 font-medium text-navy">{src.records.toLocaleString()}</dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-muted">Scope</dt>
                    <dd className="mt-0.5 truncate font-medium text-navy">{src.scope.join(', ') || '—'}</dd>
                  </div>
                </dl>
              ) : (
                <p className="mt-4 rounded-xl border border-dashed border-line p-3 text-xs text-muted">
                  {src ? 'Selected during setup · awaiting authorisation' : 'Not connected to this project'}
                </p>
              )}
              <div className="mt-4 flex gap-2">
                {connected ? (
                  <Button
                    variant="secondary"
                    className="flex-1"
                    onClick={() => {
                      if (t === 'docs') {
                        router.push(`/projects/${p.id}/evidence?provider=upload`)
                      } else {
                        const map = sourceMappings.find((m) => m.provider === t || m.id === src?.id)
                        if (map) {
                          void triggerSync(map.id)
                        } else {
                          router.push(`/projects/${p.id}/evidence?provider=${t}`)
                        }
                      }
                    }}
                  >
                    {t === 'docs' ? 'View Evidence' : 'Sync Now'}
                  </Button>
                ) : (
                  <Button
                    className="flex-1"
                    icon={t === 'docs' ? Upload : Plug}
                    disabled={!canManage}
                    onClick={() => {
                      if (t === 'docs') {
                        setIsUploadModalOpen(true)
                      } else if (t === 'github') {
                        openConnectSourceModal('github')
                      } else if (t === 'jira') {
                        openConnectSourceModal('jira')
                      } else if (t === 'slack') {
                        openConnectSourceModal('slack')
                      } else if (t === 'confluence') {
                        openConnectSourceModal('jira')
                      } else if (t === 'gdrive') {
                        setIsUploadModalOpen(true)
                      }
                    }}
                  >
                    {t === 'docs' ? 'Upload files' : 'Connect'}
                  </Button>
                )}
                {connected && t === 'docs' && canManage && (
                  <Button variant="subtle" icon={Upload} onClick={() => setIsUploadModalOpen(true)}>
                    Upload
                  </Button>
                )}
              </div>
            </Card>
          )
        })}
        <Card className="flex flex-col items-center justify-center border-dashed p-5 text-center">
          <span className="flex size-11 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
            <Plus className="size-5" />
          </span>
          <p className="mt-3 text-sm font-semibold text-navy">Other authorised sources</p>
          <p className="mt-1 text-xs text-muted">Request Linear, GitLab, Notion or a custom API connector.</p>
          <Button
            variant="ghost"
            size="sm"
            className="mt-3"
            onClick={() => s.toast('Request sent', 'Workspace admins will review your connector request.', 'info')}
          >
            Request connector
          </Button>
        </Card>
      </div>
      {connecting && <ConnectFlow type={connecting} projectId={p.id} onClose={() => setConnecting(null)} />}
    </>
  )
}

/* ---------- 11. Source Details View ---------- */
export function SourceDetail({ projectId, sourceId }: { projectId: string; sourceId: string }) {
  const s = useStore()
  const p = useProject(projectId)
  const router = useRouter()
  const src = s.sources.find((x) => x.id === sourceId) || s.sources.find((x) => x.projectId === projectId)
  const [confirm, setConfirm] = useState(false)
  const [syncing, setSyncing] = useState(false)

  if (!p || !src) return <ProjectNotFound />
  const canManage = p.role === 'manager'
  const jobs = s.jobs.filter((j) => j.sourceId === src.id)
  const history = [
    ...jobs,
    { id: 'h1', started: 'Jun 16 14:00', records: 120, status: 'succeeded', duration: '1m 04s' },
    { id: 'h2', started: 'Jun 16 13:00', records: 96, status: 'succeeded', duration: '58s' },
    { id: 'h3', started: 'Jun 15 22:00', records: 0, status: 'failed', duration: '2s' },
  ] as { id: string; started: string; records: number; status: string; duration: string; error?: string }[]

  const update = (patch: Partial<Source>) => s.setSources((ss) => ss.map((x) => (x.id === src.id ? { ...x, ...patch } : x)))
  const reconnect = () => {
    setSyncing(true)
    setTimeout(() => {
      update({ status: 'connected', lastSync: 'Just now' })
      setSyncing(false)
      s.toast(`${src.name} reconnected`, 'Sync resumed. Missed messages will be backfilled.')
    }, 1200)
  }

  return (
    <>
      <Link to={`/projects/${p.id}/sources`} className="mb-4 inline-flex items-center gap-1.5 text-[13px] font-medium text-muted hover:text-navy">
        <ChevronRight className="size-4 rotate-180" />Data sources
      </Link>
      <PageHeader
        title={
          <span className="flex items-center gap-3">
            <SourceIcon type={src.type} size={40} />
            {src.name}
            <StatusBadge status={src.status} />
          </span>
        }
        subtitle={`${src.account} · connected to ${p.name}`}
        actions={
          canManage && (
            <>
              <Button
                variant="secondary"
                icon={syncing ? Loader2 : RefreshCw}
                disabled={syncing || src.status === 'disconnected'}
                onClick={() => {
                  setSyncing(true)
                  setTimeout(() => {
                    setSyncing(false)
                    update({ lastSync: 'Just now' })
                    s.toast('Sync complete', `${src.name} is up to date.`)
                  }, 1200)
                }}
              >
                {syncing ? 'Syncing…' : 'Sync now'}
              </Button>
              <Button variant="secondary" icon={Plug} onClick={reconnect}>Reconnect</Button>
              <Button variant="danger" icon={Unplug} onClick={() => setConfirm(true)} disabled={src.status === 'disconnected'}>
                Disconnect
              </Button>
            </>
          )
        }
      />
      {src.status === 'error' && (
        <div className="mb-5">
          <ErrorState
            title="Authorisation expired"
            body="The Slack token for Northwind HQ was revoked on Jun 16. 0 of 3 channels are syncing."
            action={canManage && <Button size="sm" variant="danger" onClick={reconnect}>{syncing ? 'Reconnecting…' : 'Reconnect Slack'}</Button>}
          />
        </div>
      )}
      {src.status === 'disconnected' && (
        <div className="mb-5">
          <Callout tone="amber" icon={Unplug} title="Disconnected">
            Existing evidence is retained according to your data retention policy. Reconnect to resume syncing.
          </Callout>
        </div>
      )}
      <MetricBand
        className=""
        items={[
          { label: 'Connection health', value: src.status === 'error' ? 'Failing' : src.status === 'disconnected' ? 'Off' : '99.4%', tone: src.status === 'error' ? 'red' : 'green', hint: '30-day sync success' },
          { label: 'Last successful sync', value: <span className="text-xl">{src.lastSync}</span> },
          { label: 'Data volume', value: src.volume, tone: 'indigo', hint: `${src.records.toLocaleString()} records` },
          { label: 'Sync frequency', value: <span className="text-xl">{src.frequency}</span>, tone: 'gray' },
        ]}
      />
      <div className="mt-5 grid gap-5 lg:grid-cols-3">
        <Card className="p-5">
          <p className="text-[15px] font-semibold text-navy">Account information</p>
          <dl className="mt-4 space-y-3 text-[13px]">
            {[
              ['Account', src.account],
              ['Connected by', 'Lucas Berg'],
              ['Connected on', 'Jun 14, 2025'],
              ['Auth method', 'OAuth 2.0 app'],
              ['Source ID', src.id],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3">
                <dt className="text-muted">{k}</dt>
                <dd className="truncate font-medium text-navy">{v}</dd>
              </div>
            ))}
          </dl>
          {canManage && (
            <div className="mt-5 border-t border-line pt-4">
              <Field label="Sync frequency">
                <Select
                  value={src.frequency}
                  onChange={(e) => {
                    update({ frequency: e.target.value })
                    s.toast('Sync frequency updated', e.target.value)
                  }}
                >
                  {['Every 15 minutes', 'Hourly', 'Daily', 'Manual', 'On upload'].map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </Select>
              </Field>
            </div>
          )}
        </Card>
        <Card className="p-5">
          <p className="text-[15px] font-semibold text-navy">
            Selected {src.type === 'github' ? 'repositories' : src.type === 'slack' ? 'channels' : src.type === 'jira' ? 'projects' : 'collections'}
          </p>
          <ul className="mt-4 space-y-2">
            {((REPOS[src.type]?.length ? REPOS[src.type] : src.scope) ?? []).map((r) => (
              <li key={r} className="flex items-center justify-between rounded-lg border border-line px-3 py-2">
                <span className="font-mono text-[12.5px] text-navy">{r}</span>
                <Switch
                  checked={src.scope.includes(r)}
                  onChange={(v) => canManage && update({ scope: v ? [...src.scope, r] : src.scope.filter((x) => x !== r) })}
                  label={r}
                />
              </li>
            ))}
          </ul>
        </Card>
        <Card className="p-5">
          <p className="text-[15px] font-semibold text-navy">Permissions granted</p>
          <ul className="mt-4 space-y-2.5">
            {(SCOPES[src.type] ?? []).map((x) => (
              <li key={x} className="flex items-start gap-2 text-[13px] text-slate-700">
                <ShieldCheck className="mt-0.5 size-4 shrink-0 text-ok" />{x}
              </li>
            ))}
          </ul>
          <div className="mt-4">
            <Callout tone="blue" icon={Lock}>
              Read-only. Handover cannot post, edit or delete anything in {src.name}.
            </Callout>
          </div>
        </Card>
      </div>
      <Card className="mt-5 overflow-hidden">
        <CardHeader title="Sync history" subtitle="Most recent first" />
        <Table>
          <thead>
            <tr>
              <Th>Started</Th>
              <Th>Status</Th>
              <Th>Records</Th>
              <Th>Duration</Th>
              <Th>Details</Th>
            </tr>
          </thead>
          <tbody>
            {history.map((h) => (
              <tr key={h.id}>
                <Td className="text-[13px]">{h.started}</Td>
                <Td><StatusBadge status={h.status} /></Td>
                <Td className="text-[13px]">{h.records}</Td>
                <Td className="text-[13px] text-muted">{h.duration}</Td>
                <Td className="max-w-xs truncate text-xs text-muted">{h.error ?? (h.status === 'failed' ? 'invalid_auth' : '—')}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
      <ConfirmDialog
        open={confirm}
        onClose={() => setConfirm(false)}
        tone="danger"
        title={`Disconnect ${src.name}?`}
        confirmLabel="Disconnect"
        body={
          <>
            Syncing will stop immediately. {src.records.toLocaleString()} existing evidence records remain available until your retention period ends, and verified findings are unaffected.
          </>
        }
        onConfirm={() => {
          update({ status: 'disconnected' })
          s.toast(`${src.name} disconnected`, undefined, 'info')
        }}
      />
    </>
  )
}

/* ---------- 12. Evidence Library (Canonical Three-Panel Workspace) ---------- */
export function EvidenceLibrary({ projectId }: { projectId: string }) {
  const s = useStore()
  const p = useProject(projectId)
  const router = useRouter()
  const { evidenceList, setIsUploadModalOpen } = useLiveApp()
  const loading = useFakeLoading(450, [projectId])
  const [layoutMode, setLayoutMode] = useState<'threepanel' | 'table'>('threepanel')
  const [q, setQ] = useState('')
  const [src, setSrc] = useState('all')
  const [type, setType] = useState('all')
  const [author, setAuthor] = useState('all')
  const [proc, setProc] = useState('all')
  const [range, setRange] = useState('all')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState<Evidence | null>(null)
  const [upload, setUpload] = useState(false)
  const [activeDetailTab, setActiveDetailTab] = useState<'content' | 'facts' | 'findings'>('content')

  const liveItems: Evidence[] = useMemo(() => {
    return (evidenceList || []).map((e) => {
      let type: Evidence['type'] = 'pdf'
      if (e.provider === 'github') type = 'commit'
      else if (e.provider === 'jira') type = 'issue'
      else if (e.provider === 'slack') type = 'message'
      else if (e.source_type?.toLowerCase().includes('doc')) type = 'docx'

      let verification: Verification = 'needs_review'
      if (e.indexing_status === 'indexed') verification = 'verified'
      else if (e.indexing_status === 'failed') verification = 'rejected'

      return {
        id: e.id,
        projectId: e.project_id || p?.id || '',
        type,
        title: e.title || 'Evidence Record',
        sourceId: e.provider || 'docs',
        authorId: e.author_name || 'system',
        date: e.source_created_at ? e.source_created_at.split('T')[0]! : 'Today',
        memberId: 'user',
        processing: e.indexing_status === 'indexed' ? 'processed' : e.indexing_status === 'failed' ? 'failed' : 'processing',
        verification,
        ref: e.id.slice(0, 8),
        content: e.original_filename ? `File: ${e.original_filename}` : 'Decrypted source content available in Evidence Workspace.',
        extracted: [],
      }
    })
  }, [evidenceList, p?.id])

  if (!p) return <ProjectNotFound />

  const storeItems = evidence.filter((e) => e.projectId === p.id)
  const all = storeItems.length > 0 ? storeItems : liveItems
  const cutoff = range === '30' ? '2025-05-19' : range === '90' ? '2025-03-20' : '0'
  const list = all.filter(
    (e) =>
      (e.title + e.ref).toLowerCase().includes(q.toLowerCase()) &&
      (src === 'all' || e.sourceId === src) &&
      (type === 'all' || e.type === type) &&
      (author === 'all' || e.authorId === author) &&
      (proc === 'all' || e.processing === proc) &&
      e.date >= cutoff
  )

  const per = 8
  const pages = Math.max(1, Math.ceil(list.length / per))
  const shown = list.slice((page - 1) * per, page * per)
  const sources = s.sources.filter((x) => x.projectId === p.id)
  const authors = Array.from(new Set(all.map((e) => e.authorId)))

  // Default selected evidence for 3-panel mode
  const selectedEvidence = open || list[0] || null
  const relatedFindings = selectedEvidence ? allFindings(p.id).filter((f) => f.evidenceIds.includes(selectedEvidence.id)) : []
  const selectedSource = selectedEvidence ? s.sources.find((x) => x.id === selectedEvidence.sourceId) : null

  const reset = () => {
    setQ('')
    setSrc('all')
    setType('all')
    setAuthor('all')
    setProc('all')
    setRange('all')
  }

  return (
    <>
      <PageHeader
        eyebrow={<Badge tone="blue">{p.name}</Badge>}
        title="Evidence Center"
        subtitle="Every original record Handover has ingested. Each finding links back here."
        actions={
          <div className="flex items-center gap-2">
            <Segmented
              value={layoutMode}
              onChange={setLayoutMode}
              options={[
                { id: 'threepanel', icon: Columns3, label: '3-Panel Hub' },
                { id: 'table', icon: List, label: 'Table' },
              ]}
            />
            {p.role !== 'incoming' && (
              <Button icon={FileUp} onClick={() => setIsUploadModalOpen(true)}>
                Upload evidence
              </Button>
            )}
          </div>
        }
      />

      {/* Filter Toolbar */}
      <Card className="mb-4 p-3">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
          <SearchInput
            placeholder="Search title or reference"
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1) }}
            className="lg:w-72"
          />
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:flex">
            <Select value={src} onChange={(e) => setSrc(e.target.value)} className="lg:w-36">
              <option value="all">All sources</option>
              {sources.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
            </Select>
            <Select value={type} onChange={(e) => setType(e.target.value)} className="lg:w-36">
              <option value="all">All types</option>
              {Object.entries(EVIDENCE_TYPE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </Select>
            <Select value={author} onChange={(e) => setAuthor(e.target.value)} className="lg:w-40">
              <option value="all">All authors</option>
              {authors.map((a) => <option key={a} value={a}>{personById(a)?.name ?? a}</option>)}
            </Select>
            <Select value={proc} onChange={(e) => setProc(e.target.value)} className="lg:w-36">
              <option value="all">Any processing</option>
              {['processed', 'processing', 'queued', 'failed'].map((x) => <option key={x} value={x}>{(x[0] ?? '').toUpperCase() + x.slice(1)}</option>)}
            </Select>
            <Select value={range} onChange={(e) => setRange(e.target.value)} className="lg:w-36">
              <option value="all">All time</option>
              <option value="30">Last 30 days</option>
              <option value="90">Last 90 days</option>
            </Select>
          </div>
        </div>
      </Card>

      {/* 3-Panel Evidence Hub Layout */}
      {layoutMode === 'threepanel' ? (
        <div className="grid gap-3.5 lg:grid-cols-12 min-h-[580px]">
          {/* PANEL A: Connected Sources */}
          <Card className="flex flex-col p-4 lg:col-span-3">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="flex size-5 items-center justify-center rounded-full bg-brand text-[11px] font-bold text-white">A</span>
                <h3 className="text-sm font-semibold text-navy">Connected Sources</h3>
              </div>
              <Badge tone="gray">{sources.length}</Badge>
            </div>
            <p className="mb-3 text-xs text-muted">Authorised organisational sources feeding this project.</p>
            <div className="space-y-2 flex-1 overflow-y-auto">
              {sources.map((sx) => (
                <div
                  key={sx.id}
                  onClick={() => setSrc(src === sx.id ? 'all' : sx.id)}
                  className={cn(
                    'tile flex cursor-pointer items-start gap-2.5 rounded-xl border p-2.5 transition',
                    src === sx.id ? 'border-brand bg-tint/60 ring-2 ring-brand/20' : 'hover:border-line hover:bg-slate-50'
                  )}
                >
                  <SourceIcon type={sx.type} size={28} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between">
                      <p className="truncate text-[13px] font-medium text-navy">{sx.name}</p>
                      <StatusBadge status={sx.status} />
                    </div>
                    <p className="mt-0.5 truncate text-[11px] text-muted">{sx.records.toLocaleString()} records · {sx.lastSync}</p>
                  </div>
                </div>
              ))}
            </div>
            <Button
              variant="secondary"
              size="sm"
              icon={Plus}
              className="mt-3 w-full"
              onClick={() => router.push(`/projects/${p.id}/sources`)}
            >
              Connect new source
            </Button>
          </Card>

          {/* PANEL B: Evidence Library */}
          <Card className="flex flex-col p-4 lg:col-span-5 overflow-hidden">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="flex size-5 items-center justify-center rounded-full bg-ok text-[11px] font-bold text-white">B</span>
                <h3 className="text-sm font-semibold text-navy">Evidence Library</h3>
              </div>
              <Badge tone="gray">{list.length} items</Badge>
            </div>
            <div className="space-y-2 flex-1 overflow-y-auto pr-1">
              {loading ? (
                <div className="space-y-2">
                  {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-16 w-full" />)}
                </div>
              ) : !list.length ? (
                <EmptyState icon={Filter} title="No records match" body="Try adjusting filters or clearing your query." action={<Button variant="secondary" size="sm" onClick={reset}>Reset</Button>} />
              ) : (
                list.map((e) => {
                  const isSelected = selectedEvidence?.id === e.id
                  return (
                    <div
                      key={e.id}
                      onClick={() => setOpen(e)}
                      className={cn(
                        'tile flex cursor-pointer flex-col gap-1.5 rounded-xl border p-3 transition',
                        isSelected ? 'border-brand bg-tint/40 shadow-sm' : 'hover:border-slate-300 hover:bg-slate-50/60'
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <EvidenceTypeIcon type={e.type} className="size-6 shrink-0" />
                          <p className="truncate text-[13px] font-semibold text-navy">{e.title}</p>
                        </div>
                        <VerificationBadge status={e.verification} />
                      </div>
                      <p className="line-clamp-2 text-xs text-slate-600 leading-relaxed">{e.content}</p>
                      <div className="mt-1 flex items-center justify-between text-[11px] text-muted">
                        <span className="font-mono">{e.ref}</span>
                        <span>{personById(e.authorId)?.name ?? ''} · {(e.date.split(' ')[0] ?? e.date)}</span>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </Card>

          {/* PANEL C: Evidence Details */}
          <Card className="flex flex-col p-4 lg:col-span-4 overflow-hidden">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="flex size-5 items-center justify-center rounded-full bg-ai text-[11px] font-bold text-white">C</span>
                <h3 className="text-sm font-semibold text-navy">Evidence Details</h3>
              </div>
              {selectedEvidence && (
                <Button
                  size="sm"
                  variant="secondary"
                  icon={ExternalLink}
                  onClick={() => router.push(`/projects/${p.id}/evidence/${selectedEvidence.id}`)}
                >
                  Full View
                </Button>
              )}
            </div>
            {selectedEvidence ? (
              <div className="flex-1 overflow-y-auto space-y-4 pr-1">
                <div className="rounded-xl border border-line bg-slate-50/70 p-3.5">
                  <div className="flex items-center gap-2 mb-2">
                    <EvidenceTypeIcon type={selectedEvidence.type} className="size-6" />
                    <h4 className="text-sm font-bold text-navy truncate">{selectedEvidence.title}</h4>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-muted">
                    <div><span>Ref:</span> <strong className="font-mono text-navy">{selectedEvidence.ref}</strong></div>
                    <div><span>Author:</span> <strong className="text-navy">{personById(selectedEvidence.authorId)?.name ?? ''}</strong></div>
                    <div><span>Date:</span> <strong className="text-navy">{selectedEvidence.date}</strong></div>
                    <div><span>Source:</span> <strong className="text-navy">{selectedSource?.name ?? 'Organisational'}</strong></div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Segmented
                    value={activeDetailTab}
                    onChange={setActiveDetailTab}
                    options={[
                      { id: 'content', label: 'Source Record' },
                      { id: 'facts', label: `Facts (${selectedEvidence.extracted.length})` },
                      { id: 'findings', label: `Findings (${relatedFindings.length})` },
                    ]}
                  />
                </div>

                {activeDetailTab === 'content' && (
                  <div>
                    <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">Original Content</p>
                    <div className="rounded-xl border-l-2 border-sky bg-slate-50 p-3 text-xs leading-relaxed text-slate-700 whitespace-pre-wrap font-sans max-h-64 overflow-y-auto">
                      {selectedEvidence.content}
                    </div>
                  </div>
                )}

                {activeDetailTab === 'facts' && (
                  <div>
                    <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">Extracted Facts</p>
                    <ul className="space-y-1.5 max-h-64 overflow-y-auto">
                      {selectedEvidence.extracted.map((f, i) => (
                        <li key={i} className="flex items-start gap-2 rounded-lg border border-dashed border-indigo-200 bg-indigo-50/30 p-2.5 text-xs text-navy">
                          <Sparkles className="size-3.5 shrink-0 text-indigo-500 mt-0.5" />
                          <span>{f}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {activeDetailTab === 'findings' && (
                  <div>
                    <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">Reconstructed Findings</p>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {relatedFindings.map((f) => (
                        <div key={f.id} className="rounded-xl border border-line p-2.5 bg-white">
                          <div className="flex items-center justify-between mb-1">
                            <Badge tone="indigo">{f.kind}</Badge>
                            <VerificationBadge status={s.verif[f.id] ?? f.verification} />
                          </div>
                          <p className="text-xs font-semibold text-navy">{f.title}</p>
                          <p className="text-[11px] text-muted line-clamp-1 mt-0.5">{f.summary}</p>
                        </div>
                      ))}
                      {!relatedFindings.length && (
                        <p className="text-xs text-muted">No findings link to this evidence record yet.</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <EmptyState icon={FileSearch} title="Select a record" body="Click any item in the library to inspect its details and provenance." />
            )}
          </Card>
        </div>
      ) : (
        /* Classic Table Layout with Drawer */
        <Card className="overflow-hidden">
          {loading ? (
            <div className="space-y-3 p-5">
              {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : !all.length ? (
            <EmptyState
              icon={FileSearch}
              title="No evidence yet"
              body="Connect a source or upload documents. Evidence appears here as it's ingested."
              action={<Button onClick={() => router.push(`/projects/${p.id}/sources`)}>Connect sources</Button>}
            />
          ) : !list.length ? (
            <EmptyState
              icon={Filter}
              title="No evidence matches these filters"
              body="Try widening the date range or clearing filters."
              action={<Button variant="secondary" onClick={reset}>Clear filters</Button>}
            />
          ) : (
            <>
              <Table>
                <thead>
                  <tr>
                    <Th>Evidence</Th>
                    <Th>Source</Th>
                    <Th>Author</Th>
                    <Th>Date</Th>
                    <Th>Member</Th>
                    <Th>Processing</Th>
                    <Th>Verification</Th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((e) => {
                    const sx = s.sources.find((x) => x.id === e.sourceId)
                    return (
                      <tr
                        key={e.id}
                        onClick={() => setOpen(e)}
                        className={cn('cursor-pointer hover:bg-slate-50/70', open?.id === e.id && 'bg-tint/40')}
                      >
                        <Td>
                          <span className="flex items-center gap-3">
                            <EvidenceTypeIcon type={e.type} />
                            <span className="min-w-0">
                              <span className="block max-w-[280px] truncate font-medium text-navy">{e.title}</span>
                              <span className="text-xs text-muted">{EVIDENCE_TYPE_LABEL[e.type]} · {e.ref}</span>
                            </span>
                          </span>
                        </Td>
                        <Td>
                          {sx && (
                            <span className="flex items-center gap-2">
                              <SourceIcon type={sx.type} size={22} />
                              <span className="text-[13px]">{sx.name}</span>
                            </span>
                          )}
                        </Td>
                        <Td>
                          <span className="flex items-center gap-2 whitespace-nowrap">
                            <Avatar id={e.authorId} size={22} />
                            <span className="text-[13px]">{personById(e.authorId)?.name ?? ''}</span>
                          </span>
                        </Td>
                        <Td className="whitespace-nowrap text-[13px] text-muted">{(e.date.split(' ')[0] ?? e.date)}</Td>
                        <Td><Avatar id={e.memberId} size={22} /></Td>
                        <Td><StatusBadge status={e.processing} /></Td>
                        <Td><VerificationBadge status={e.verification} /></Td>
                      </tr>
                    )
                  })}
                </tbody>
              </Table>
              <Pagination page={page} pages={pages} onChange={setPage} total={list.length} />
            </>
          )}
        </Card>
      )}

      {/* Slide-out Drawer */}
      <Drawer
        open={!!open}
        onClose={() => setOpen(null)}
        title={open && <span className="flex items-center gap-2.5"><EvidenceTypeIcon type={open.type} />{open.title}</span>}
        footer={
          open && (
            <>
              <Button className="flex-1" iconRight={ArrowRight} onClick={() => router.push(`/projects/${p.id}/evidence/${open.id}`)}>
                Open full evidence
              </Button>
              <Button variant="secondary" icon={ExternalLink} onClick={() => s.toast('Opening original source', open.ref, 'info')}>
                Original
              </Button>
            </>
          )
        }
      >
        {open && (
          <div className="space-y-5">
            <div className="flex flex-wrap gap-2">
              <StatusBadge status={open.processing} />
              <VerificationBadge status={open.verification} />
            </div>
            <dl className="grid grid-cols-2 gap-3 text-[13px]">
              {[
                ['Reference', open.ref],
                ['Author', personById(open.authorId)?.name ?? ''],
                ['Timestamp', open.date],
                ['Type', EVIDENCE_TYPE_LABEL[open.type]],
              ].map(([k, v]) => (
                <div key={k}>
                  <dt className="text-xs text-muted">{k}</dt>
                  <dd className="font-medium text-navy">{v}</dd>
                </div>
              ))}
            </dl>
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Original content</p>
              <p className="whitespace-pre-line rounded-xl border-l-2 border-sky bg-slate-50 p-3.5 text-[13px] leading-relaxed text-slate-700">
                {open.content}
              </p>
            </div>
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Extracted information</p>
              <ul className="space-y-1.5">
                {open.extracted.map((x) => (
                  <li key={x} className="flex items-start gap-2 text-[13px] text-navy">
                    <Sparkles className="mt-0.5 size-3.5 shrink-0 text-indigo-500" />
                    {x}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </Drawer>

      {/* Upload Modal */}
      <Modal
        open={upload}
        onClose={() => setUpload(false)}
        title="Upload evidence"
        subtitle="PDF or DOCX · files are scanned and processed automatically"
        footer={
          <>
            <Button variant="secondary" onClick={() => setUpload(false)}>Cancel</Button>
            <Button
              onClick={() => {
                setUpload(false)
                s.setJobs((js) => [
                  {
                    id: `job-${Date.now() % 10000}`,
                    projectId: p.id,
                    sourceId: `src-docs-${p.id}`,
                    started: 'Just now',
                    records: 2,
                    status: 'queued',
                    duration: '—',
                  },
                  ...js,
                ])
                s.toast('2 files queued for processing', 'Track progress in Ingestion Activity.')
              }}
            >
              Upload
            </Button>
          </>
        }
      >
        <div className="flex flex-col items-center rounded-xl border-2 border-dashed border-[#D9E1F0] bg-tint/30 px-6 py-10 text-center">
          <Upload className="size-6 text-brand" />
          <p className="mt-3 text-sm font-medium text-navy">Drag files here or browse</p>
          <p className="mt-1 text-xs text-muted">2 files selected: Deployment runbook.docx, Incident review.pdf</p>
        </div>
        <Field label="Associate with member" className="mt-4">
          <Select>
            {s.members.filter((m) => m.projectId === p.id).map((m) => (
              <option key={m.personId}>{personById(m.personId)?.name ?? m.personId}</option>
            ))}
          </Select>
        </Field>
      </Modal>
    </>
  )
}

/* ---------- 13. Evidence Detail View ---------- */
function OriginalContent({ e }: { e: Evidence }) {
  if (e.type === 'message') {
    return (
      <div className="space-y-3">
        {e.content.split('\n').map((line, i) => {
          const [name, ...rest] = line.split(': ')
          const person = [...new Set(evidence.map((x) => x.authorId))].map(personById).find((pp) => pp?.name === name)
          return (
            <div key={i} className="flex gap-3">
              <Avatar id={person?.id} name={name} size={32} />
              <div>
                <p className="text-[13px] font-semibold text-navy">
                  {name} <span className="font-normal text-slate-400">{(e.date.split(' ')[1] ?? '')}</span>
                </p>
                <p className="text-[13.5px] leading-relaxed text-slate-700">{rest.join(': ')}</p>
              </div>
            </div>
          )
        })}
      </div>
    )
  }
  if (e.type === 'commit') {
    return (
      <pre className="overflow-x-auto whitespace-pre-wrap rounded-xl bg-[#0f1b33] p-4 font-mono text-[12.5px] leading-relaxed text-slate-200">
        {e.content}
      </pre>
    )
  }
  return <div className="whitespace-pre-line text-[14px] leading-7 text-slate-700">{e.content}</div>
}

export function EvidenceDetail({ projectId, evidenceId }: { projectId: string; evidenceId: string }) {
  const s = useStore()
  const p = useProject(projectId)
  const e = evidence.find((x) => x.id === evidenceId) || evidence.find((x) => x.projectId === projectId)
  const [drawer, setDrawer] = useState<AnyFinding>()

  if (!p || !e) return <ProjectNotFound />
  const src = s.sources.find((x) => x.id === e.sourceId)
  const related = allFindings(p.id).filter((f) => f.evidenceIds.includes(e.id))
  const handovers = s.handovers.filter((h) => h.projectId === p.id && h.status !== 'draft')
  const groups = (['Decision', 'Task', 'Risk', 'Dependency'] as const).map((k) => ({
    k,
    items: related.filter((r) => r.kind === k),
  }))

  return (
    <>
      <Link to={`/projects/${p.id}/evidence`} className="mb-4 inline-flex items-center gap-1.5 text-[13px] font-medium text-muted hover:text-navy">
        <ChevronRight className="size-4 rotate-180" />Evidence library
      </Link>
      <PageHeader
        title={
          <span className="flex items-center gap-3">
            <EvidenceTypeIcon type={e.type} className="size-10" />
            {e.title}
          </span>
        }
        subtitle={`${EVIDENCE_TYPE_LABEL[e.type]} · ${e.ref}`}
        actions={
          <Button variant="secondary" icon={ExternalLink} onClick={() => s.toast('Opening original source', e.ref, 'info')}>
            Open in {src?.name ?? 'source'}
          </Button>
        }
      />
      <Card className="mb-5 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Evidence traceability</p>
        <div className="scrollbar-thin flex items-stretch gap-2 overflow-x-auto pb-1">
          {[
            { icon: Database, label: 'Source', value: src ? `${src.name} · ${src.account}` : '—' },
            { icon: FileSearch, label: 'Original record', value: e.ref },
            { icon: ScanText, label: 'Extracted facts', value: `${e.extracted.length} statements` },
            { icon: BrainCircuit, label: 'Findings', value: `${related.length} linked` },
            { icon: Workflow, label: 'Handovers', value: handovers.length ? handovers.map((h) => h.code).join(', ') : 'None' },
          ].map((st, i, arr) => (
            <div key={st.label} className="flex shrink-0 items-center gap-2">
              <div className={cn('min-w-[150px] rounded-xl border px-3 py-2.5', i === 1 ? 'border-brand bg-tint/50' : 'border-line bg-white')}>
                <p className="flex items-center gap-1.5 text-[11px] font-medium text-muted">
                  <st.icon className="size-3.5" />{st.label}
                </p>
                <p className="mt-0.5 text-[13px] font-semibold text-navy">{st.value}</p>
              </div>
              {i < arr.length - 1 && <ArrowRight className="size-4 shrink-0 text-slate-300" />}
            </div>
          ))}
        </div>
      </Card>
      <div className="grid gap-5 lg:grid-cols-[1fr_380px]">
        <div className="space-y-5">
          <Card className="p-5 sm:p-6">
            <div className="mb-4 flex items-center justify-between">
              <p className="text-[15px] font-semibold text-navy">Original evidence</p>
              <Badge tone="gray">Unmodified source content</Badge>
            </div>
            <OriginalContent e={e} />
          </Card>
          <Card>
            <CardHeader title="Extracted information" subtitle="Statements the AI derived from this record" icon={Sparkles} />
            <ul className="space-y-2 px-5 pb-5">
              {e.extracted.map((x) => (
                <li key={x} className="flex items-start gap-3 rounded-xl border border-dashed border-indigo-200 bg-indigo-50/30 px-3.5 py-2.5 text-[13px] text-navy">
                  <Sparkles className="mt-0.5 size-3.5 shrink-0 text-indigo-500" />
                  {x}
                </li>
              ))}
            </ul>
          </Card>
          <Card>
            <CardHeader title="Related findings" subtitle="Decisions, tasks and risks supported by this evidence" icon={Link2} />
            <div className="space-y-4 px-5 pb-5">
              {groups.filter((g) => g.items.length).map((g) => (
                <div key={g.k}>
                  <p className="mb-2 text-xs font-medium text-muted">{g.k === 'Dependency' ? 'Dependencies' : `${g.k}s`}</p>
                  <ul className="space-y-2">
                    {g.items.map((f) => (
                      <li key={f.id}>
                        <button
                          onClick={() => setDrawer(f)}
                          className="flex w-full flex-col gap-2 rounded-xl border border-line px-3.5 py-3 text-left hover:border-brand/40 sm:flex-row sm:items-center"
                        >
                          <span className="flex-1 text-[13px] font-medium text-navy">{f.title}</span>
                          <FindingRowMeta f={f} />
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              {!related.length && <p className="text-[13px] text-muted">No findings reference this evidence yet.</p>}
            </div>
          </Card>
        </div>
        <div className="space-y-5">
          <Card className="p-5">
            <p className="text-[15px] font-semibold text-navy">Source metadata</p>
            <dl className="mt-4 space-y-3 text-[13px]">
              <div className="flex items-center justify-between">
                <dt className="text-muted">Author</dt>
                <dd className="flex items-center gap-1.5 font-medium text-navy">
                  <Avatar id={e.authorId} size={20} />{personById(e.authorId)?.name ?? ''}
                </dd>
              </div>
              <div className="flex justify-between"><dt className="text-muted">Timestamp</dt><dd className="font-medium text-navy">{e.date}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Source</dt><dd className="font-medium text-navy">{src?.name} · {src?.account}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Reference</dt><dd className="font-mono text-xs text-navy">{e.ref}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Associated member</dt><dd className="font-medium text-navy">{personById(e.memberId)?.name ?? ''}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Processing</dt><dd><StatusBadge status={e.processing} /></dd></div>
              <div className="flex justify-between"><dt className="text-muted">Ingested</dt><dd className="font-medium text-navy">Job #8807 · 3m 12s</dd></div>
            </dl>
          </Card>
          <Card className="p-5">
            <p className="text-[15px] font-semibold text-navy">Verification</p>
            <div className="mt-3"><VerificationBadge status={e.verification} /></div>
            <p className="mt-3 text-[13px] text-muted">
              {e.verification === 'verified'
                ? 'Confirmed as accurate and relevant by James Okafor on Jun 18.'
                : e.verification === 'conflicting'
                ? 'Contradicts another record. A reviewer must decide which is current.'
                : e.verification === 'insufficient'
                ? 'Too little context to confirm. Ask the author for more detail.'
                : 'Not yet reviewed by a person.'}
            </p>
            {e.processing === 'failed' && (
              <div className="mt-4">
                <ErrorState
                  title="Processing failed"
                  body="Document is password-protected. Upload an unlocked copy to extract information."
                  action={
                    <Button size="sm" variant="secondary" icon={RotateCcw} onClick={() => s.toast('Retry queued', e.title, 'info')}>
                      Retry
                    </Button>
                  }
                />
              </div>
            )}
          </Card>
        </div>
      </div>
      <FindingDrawer finding={drawer} onClose={() => setDrawer(undefined)} />
    </>
  )
}

/* ---------- 14. Ingestion Activity View ---------- */
const STAGES = [
  { id: 'fetch', label: 'Fetch', icon: Database },
  { id: 'parse', label: 'Parse', icon: ScanText },
  { id: 'extract', label: 'Extract', icon: Sparkles },
  { id: 'link', label: 'Link', icon: GitMerge },
  { id: 'index', label: 'Index', icon: Layers },
]

export function Ingestion({ projectId }: { projectId: string }) {
  const s = useStore()
  const p = useProject(projectId)
  const router = useRouter()
  const [expanded, setExpanded] = useState<string | null>('job-8809')
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setTick((x) => x + 1), 900)
    return () => clearInterval(t)
  }, [])

  const jobs = s.jobs.filter((j) => j.projectId === projectId)
  const running = jobs.filter((j) => j.status === 'running')

  useEffect(() => {
    if (!running.length) return
    if (tick > 0 && tick % 7 === 0) {
      s.setJobs((js) =>
        js.map((j) =>
          j.projectId === projectId && j.status === 'running'
            ? { ...j, status: 'succeeded', duration: '2m 18s', records: j.records || 164 }
            : j.projectId === projectId && j.status === 'queued'
            ? { ...j, status: 'running' }
            : j
        )
      )
      s.setSources((ss) =>
        ss.map((x) =>
          x.projectId === projectId && x.status === 'syncing'
            ? { ...x, status: 'connected', lastSync: 'Just now', records: x.records + 164, volume: x.volume === '—' ? '38 MB' : x.volume }
            : x
        )
      )
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick])

  if (!p) return <ProjectNotFound />
  const total = s.sources.filter((x) => x.projectId === p.id).reduce((a, b) => a + b.records, 0)
  const queued = jobs.filter((j) => j.status === 'queued').reduce((a, b) => a + (b.records || 40), 0)
  const proc = running.reduce((a, b) => a + (b.records || 160), 0)
  const failed = jobs.filter((j) => j.status === 'failed').length
  const activeStage = running.length ? tick % STAGES.length : -1

  const retry = (id: string) => {
    s.setJobs((js) => js.map((j) => (j.id === id ? { ...j, status: 'running', error: undefined } : j)))
    s.toast('Retry started', id, 'info')
    setTimeout(() => {
      s.setJobs((js) => js.map((j) => (j.id === id ? { ...j, status: 'succeeded', records: 48, duration: '22s' } : j)))
    }, 3500)
  }

  const history = [320, 410, 280, 520, 460, 390, 610, 480, 350, 540, 600, 470, 388, 412].map((v, i) => ({
    label: `${5 + i}`,
    value: v,
    color: i === 13 ? '#315FBA' : '#C3D2EC',
  }))

  return (
    <>
      <PageHeader
        eyebrow={<Badge tone="blue">{p.name}</Badge>}
        title="Ingestion Activity"
        subtitle="Monitor how source records move through the processing pipeline."
        actions={
          <>
            <Button
              variant="secondary"
              icon={RefreshCw}
              onClick={() => s.toast('Sync triggered for all sources', undefined, 'info')}
              disabled={p.role !== 'manager'}
            >
              Sync all
            </Button>
            <Button icon={BrainCircuit} onClick={() => router.push(`/projects/${p.id}/intelligence`)}>
              View intelligence
            </Button>
          </>
        }
      />
      <MetricBand
        className=""
        items={[
          { label: 'Total records', value: total.toLocaleString() },
          { label: 'Queued', value: queued, tone: 'gray' },
          {
            label: 'Processing',
            value: proc,
            tone: 'indigo',
            hint: running.length ? (
              <span className="flex items-center gap-1 text-brand">
                <Loader2 className="size-3 animate-spin" />live
              </span>
            ) : (
              'idle'
            ),
          },
          {
            label: 'Successful',
            value: jobs.filter((j) => j.status === 'succeeded').reduce((a, b) => a + b.records, 0),
            tone: 'green',
            hint: 'last 48 h',
          },
          { label: 'Failed jobs', value: failed, tone: 'red', hint: failed ? 'retry available' : 'none' },
        ]}
      />
      <Card className="mt-5 p-5">
        <div className="mb-5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <SphereVisual
              variant={running.length ? 'reconstruct' : 'empty'}
              emptyKind="ingestion"
              progress={running.length ? ((tick % 7) + 1) / 7 : undefined}
              interactive={false}
              className="size-16 shrink-0"
            />
            <div>
              <p className="text-[15px] font-semibold text-navy">Processing pipeline</p>
              <p className="text-[13px] text-muted">
                {running.length
                  ? `${running.length} job${running.length > 1 ? 's' : ''} in progress · assembling project knowledge sphere`
                  : 'All caught up. New records are picked up on the next sync.'}
              </p>
            </div>
          </div>
          {!running.length && <Badge tone="green" icon={CheckCircle2}>Idle</Badge>}
        </div>
        <div className="grid grid-cols-5 gap-2 sm:gap-3">
          {STAGES.map((st, i) => {
            const done = running.length ? i < activeStage : true
            const active = i === activeStage
            return (
              <div key={st.id} className="relative">
                <div
                  className={cn(
                    'flex flex-col items-center rounded-xl border p-2 text-center transition sm:p-4',
                    active ? 'border-brand bg-tint/60 ring-4 ring-brand/10' : done ? 'border-teal-100 bg-teal-50/40' : 'border-line'
                  )}
                >
                  <span
                    className={cn(
                      'flex size-9 items-center justify-center rounded-full',
                      active ? 'bg-brand text-white' : done ? 'bg-ok text-white' : 'bg-slate-100 text-slate-400'
                    )}
                  >
                    {active ? <Loader2 className="size-4 animate-spin" /> : <st.icon className="size-4" />}
                  </span>
                  <p className="mt-2 text-xs font-semibold text-navy sm:text-[13px]">{st.label}</p>
                  <p className="hidden text-[11px] text-muted sm:block">{active ? `${proc} records` : done ? 'Complete' : 'Waiting'}</p>
                </div>
                {i < STAGES.length - 1 && (
                  <ChevronRight className="absolute -right-2.5 top-1/2 z-10 hidden size-4 -translate-y-1/2 text-slate-300 sm:block" />
                )}
              </div>
            )
          })}
        </div>
        {running.map((j) => {
          const sx = s.sources.find((x) => x.id === j.sourceId)
          return (
            <div key={j.id} className="mt-4 flex items-center gap-3 rounded-xl bg-slate-50 px-3.5 py-2.5">
              {sx && <SourceIcon type={sx.type} size={26} />}
              <span className="text-[13px] font-medium text-navy">{sx?.name} · {j.id}</span>
              <Progress value={((tick % 7) + 1) * 14} className="flex-1" />
              <span className="text-xs text-muted">{((tick % 7) + 1) * 14}%</span>
            </div>
          )
        })}
      </Card>
      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_380px]">
        <Card className="overflow-hidden">
          <CardHeader title="Recent jobs" subtitle="Expand failed jobs for error details" />
          {!jobs.length ? (
            <EmptyState icon={Boxes} title="No ingestion jobs yet" body="Jobs appear after you connect a source." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th className="w-8" />
                  <Th>Job</Th>
                  <Th>Source</Th>
                  <Th>Started</Th>
                  <Th>Records</Th>
                  <Th>Duration</Th>
                  <Th>Status</Th>
                  <Th />
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => {
                  const sx = s.sources.find((x) => x.id === j.sourceId)
                  return [
                    <tr
                      key={j.id}
                      className={cn(j.error && 'cursor-pointer hover:bg-slate-50')}
                      onClick={() => j.error && setExpanded(expanded === j.id ? null : j.id)}
                    >
                      <Td>
                        {j.error && (
                          <ChevronDown className={cn('size-4 text-slate-400 transition', expanded === j.id ? '' : '-rotate-90')} />
                        )}
                      </Td>
                      <Td className="font-mono text-xs text-navy">{j.id}</Td>
                      <Td>
                        {sx && (
                          <span className="flex items-center gap-2">
                            <SourceIcon type={sx.type} size={22} />
                            <span className="text-[13px]">{sx.name}</span>
                          </span>
                        )}
                      </Td>
                      <Td className="whitespace-nowrap text-[13px] text-muted">{j.started}</Td>
                      <Td className="text-[13px]">{j.records}</Td>
                      <Td className="text-[13px] text-muted">{j.duration}</Td>
                      <Td><StatusBadge status={j.status} /></Td>
                      <Td>
                        {j.status === 'failed' && p.role === 'manager' && (
                          <Button size="sm" variant="secondary" icon={RotateCcw} onClick={(ev) => { ev.stopPropagation(); retry(j.id) }}>
                            Retry
                          </Button>
                        )}
                      </Td>
                    </tr>,
                    expanded === j.id && j.error ? (
                      <tr key={`${j.id}-e`}>
                        <td colSpan={8} className="border-b border-line bg-red-50/40 px-5 py-3">
                          <p className="flex items-start gap-2 font-mono text-xs text-red-700">
                            <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />{j.error}
                          </p>
                        </td>
                      </tr>
                    ) : null,
                  ]
                })}
              </tbody>
            </Table>
          )}
        </Card>
        <Card>
          <CardHeader title="Processing history" subtitle="Records processed per day · June" icon={Activity} />
          <div className="px-5 pb-5">
            <BarChart data={history} height={190} />
          </div>
        </Card>
      </div>
    </>
  )
}

/* ---------- 15. Knowledge Explorer View ---------- */
const CATS: { id: 'all' | NodeKind; label: string }[] = [
  { id: 'all', label: 'All knowledge' },
  { id: 'Decision', label: 'Decisions' },
  { id: 'Task', label: 'Tasks' },
  { id: 'Risk', label: 'Risks' },
  { id: 'Dependency', label: 'Dependencies' },
  { id: 'Person', label: 'People' },
  { id: 'Component', label: 'Technical components' },
  { id: 'Evidence', label: 'Evidence' },
]

const VFILTERS = [
  { id: 'all', label: 'Any status' },
  { id: 'verified', label: 'Verified' },
  { id: 'needs_review', label: 'Needs review' },
  { id: 'conflicting', label: 'Conflicting' },
  { id: 'insufficient', label: 'Insufficient' },
]

function Inspector({
  pid,
  nodeId,
  onOpen,
  onNavigate,
  onClose,
  compact,
}: {
  pid: string
  nodeId: string
  onOpen: (f: AnyFinding) => void
  onNavigate: (id: string) => void
  onClose?: () => void
  compact?: boolean
}) {
  const s = useStore()
  const { nodes, adj } = useMemo(() => buildGraph(pid), [pid])
  const node = nodes.get(nodeId)
  if (!node) return null

  const f = allFindings(pid).find((x) => x.id === nodeId)
  const neighbors = [...(adj.get(nodeId) ?? [])].map((id) => nodes.get(id)!).filter(Boolean)
  const groups = (['Decision', 'Task', 'Risk', 'Dependency', 'Person', 'Component'] as NodeKind[])
    .map((k) => ({ k, items: neighbors.filter((n) => n.kind === k) }))
    .filter((g) => g.items.length)
  const ev = neighbors.filter((n) => n.kind === 'Evidence').map((n) => evidence.find((e) => e.id === n.id)!).filter(Boolean)
  const v = f ? (s.verif[f.id] ?? f.verification) : undefined

  return (
    <div key={nodeId} className="animate-fade">
      <div className="flex items-start justify-between gap-2">
        <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em]" style={{ color: NODE_COLOR[node.kind] }}>
          <span className="size-2 rounded-full" style={{ background: NODE_COLOR[node.kind] }} />
          {node.kind}
        </span>
        {onClose && (
          <button onClick={onClose} className="-mr-1 -mt-1 rounded-md p-1 text-muted hover:bg-canvas" aria-label="Close inspector">
            <XCircle className="size-4" />
          </button>
        )}
      </div>
      <h3 className="mt-2 text-[18px] font-semibold leading-snug tracking-[-0.02em] text-navy">{node.label}</h3>
      {f && <p className="mt-2 text-[13.5px] leading-relaxed text-[#4a5d7c]">{s.edits[f.id] ?? f.summary}</p>}
      {node.kind === 'Person' && (
        <p className="mt-2 text-[13px] text-muted">{personById(node.id.slice(2))?.title ?? 'Team member'} · {neighbors.length} linked findings</p>
      )}
      {node.kind === 'Component' && (
        <p className="mt-2 text-[13px] text-muted">Technical component referenced by {neighbors.length} findings.</p>
      )}
      {node.kind === 'Evidence' && (() => {
        const e = evidence.find((x) => x.id === node.id)
        return e ? <p className="mt-2 line-clamp-4 text-[13px] leading-relaxed text-muted">{e.content}</p> : null
      })()}
      {f && v && (
        <div className="mt-4 grid grid-cols-2 gap-2">
          <div className="rounded-xl border border-dashed border-indigo-200 bg-indigo-50/50 p-3">
            <p className="flex items-center gap-1 text-[10.5px] font-semibold uppercase tracking-[0.1em] text-indigo-500">
              <Sparkles className="size-3" />AI confidence
            </p>
            <p className="mt-1 text-[22px] font-semibold leading-none tracking-[-0.02em] text-indigo-700">{f.confidence}%</p>
            <p className="mt-1.5 text-[10.5px] leading-snug text-indigo-900/60">Model certainty</p>
          </div>
          <div
            className={cn(
              'rounded-xl border p-3',
              v === 'verified'
                ? 'border-teal-200 bg-teal-50/50'
                : v === 'conflicting' || v === 'rejected'
                ? 'border-red-200 bg-red-50/40'
                : 'border-line bg-white'
            )}
          >
            <p className="flex items-center gap-1 text-[10.5px] font-semibold uppercase tracking-[0.1em] text-slate-500">
              <ShieldCheck className="size-3" />Verification
            </p>
            <div className="mt-1.5"><VerificationBadge status={v} /></div>
            <p className="mt-1.5 text-[10.5px] leading-snug text-muted">Human confirmation</p>
          </div>
        </div>
      )}
      {f && (
        <Button className="mt-4 w-full" variant={v === 'verified' ? 'secondary' : 'primary'} icon={ShieldCheck} onClick={() => onOpen(f)}>
          Open details & verify
        </Button>
      )}
      {!compact && groups.length > 0 && (
        <p className="mb-2 mt-6 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">Related entities · {neighbors.length - ev.length}</p>
      )}
      <div className="space-y-3">
        {groups.map((g) => (
          <div key={g.k}>
            <p className="mb-1 text-[11.5px] font-medium text-muted">{g.k === 'Person' ? 'People' : g.k === 'Dependency' ? 'Dependencies' : `${g.k}s`}</p>
            <ul>
              {g.items.map((n) => (
                <li key={n.id}>
                  <button
                    onClick={() => onNavigate(n.id)}
                    className="group flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[13px] transition-colors hover:bg-canvas"
                  >
                    <span className="size-1.5 shrink-0 rounded-full" style={{ background: NODE_COLOR[n.kind] }} />
                    <span className="flex-1 truncate text-navy">{n.label}</span>
                    <ChevronRight className="size-3.5 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-brand" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      {ev.length > 0 && (
        <>
          <p className="mb-2 mt-6 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">Supporting evidence · {ev.length}</p>
          <ul className="space-y-1.5">
            {ev.map((e) => (
              <li key={e.id}>
                <Link to={`/projects/${pid}/evidence/${e.id}`} className="tile group flex items-center gap-2.5 rounded-lg border px-2.5 py-2">
                  <EvidenceTypeIcon type={e.type} className="size-6 rounded-md [&_svg]:size-3" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[12.5px] font-medium text-navy">{e.title}</span>
                    <span className="block truncate font-mono text-[10.5px] text-muted">{e.ref}</span>
                  </span>
                  <ExternalLink className="size-3 shrink-0 text-slate-400 group-hover:text-brand" />
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

export function KnowledgeExplorer({ projectId }: { projectId: string }) {
  const p = useProject(projectId)
  const s = useStore()
  const router = useRouter()
  const { nodes, adj } = useMemo(() => buildGraph(projectId), [projectId])
  const [cat, setCat] = useState<'all' | NodeKind>('all')
  const [vf, setVf] = useState('all')
  const [showEv, setShowEv] = useState(true)
  const [showPeople, setShowPeople] = useState(true)
  const [q, setQ] = useState('')
  const [view, setView] = useState<'graph' | 'list'>(() => (typeof window !== 'undefined' && window.innerWidth < 1024 ? 'list' : 'graph'))
  const [focus, setFocus] = useState(false)
  const first = [...nodes.values()].find((n) => n.kind === 'Decision')?.id ?? [...nodes.keys()][0]
  const [sel, setSel] = useState<string>(first || '')
  const [trail, setTrail] = useState<string[]>(first ? [first] : [])
  const [sheet, setSheet] = useState(false)
  const [drawer, setDrawer] = useState<AnyFinding>()
  const findings = useMemo(() => allFindings(projectId), [projectId])

  const vOf = (id: string) => {
    const f = findings.find((x) => x.id === id)
    return f ? s.verif[f.id] ?? f.verification : undefined
  }

  const graphFilter = useMemo(
    () => (n: { kind: NodeKind; id: string }) => {
      if (!showEv && n.kind === 'Evidence') return false
      if (!showPeople && n.kind === 'Person') return false
      if (cat !== 'all' && n.kind !== cat && n.kind !== 'Evidence' && n.kind !== 'Person') return false
      if (vf !== 'all') {
        const v = vOf(n.id)
        if (v && v !== vf) return false
      }
      return true
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [showEv, showPeople, cat, vf, s.verif]
  )

  if (!p) return <ProjectNotFound />
  const all = [...nodes.values()]
  const list = all.filter(
    (n) =>
      (cat === 'all' ? n.kind !== 'Evidence' : n.kind === cat) &&
      n.label.toLowerCase().includes(q.toLowerCase()) &&
      (vf === 'all' || !vOf(n.id) || vOf(n.id) === vf)
  )

  const select = (id: string) => {
    const n = nodes.get(id)
    if (!n) return
    setSel(id)
    setTrail((t) => [...t.filter((x) => x !== id), id].slice(-5))
    setSheet(true)
  }

  if (!nodes.size) {
    return (
      <>
        <ProjectHeader project={p} tab="knowledge" />
        <Card>
          <EmptyState
            icon={Network}
            title="No knowledge yet"
            body="Once sources are ingested, decisions, tasks, risks and their relationships appear here."
            action={p.role === 'manager' && <Button onClick={() => router.push(`/projects/${p.id}/sources`)}>Connect sources</Button>}
          />
        </Card>
      </>
    )
  }

  const nav = (
    <div className="flex h-full flex-col">
      <div className="p-3"><SearchInput placeholder="Search knowledge" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      <nav className="scrollbar-thin flex-1 overflow-y-auto px-2 pb-3">
        <p className="px-2 pb-1 pt-1 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-slate-400">Categories</p>
        {CATS.map((c) => {
          const n = c.id === 'all' ? all.filter((x) => x.kind !== 'Evidence').length : all.filter((x) => x.kind === c.id).length
          return (
            <button
              key={c.id}
              onClick={() => { setCat(c.id); setView(view) }}
              className={cn(
                'flex w-full items-center gap-2.5 rounded-lg px-2.5 py-[7px] text-left text-[13px] transition-colors duration-150',
                cat === c.id ? 'bg-white font-semibold text-navy shadow-[0_0_0_1px_rgba(217,225,240,0.9)]' : 'font-medium text-[#4a5d7c] hover:bg-white/60'
              )}
            >
              {c.id !== 'all' ? <span className="size-2 rounded-full" style={{ background: NODE_COLOR[c.id] }} /> : <Sparkles className="size-3 text-brand" />}
              <span className="flex-1">{c.label}</span>
              <span className="font-mono text-[11px] text-slate-400">{n}</span>
            </button>
          )
        })}
        <p className="px-2 pb-1 pt-5 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-slate-400">Filters</p>
        <div className="space-y-3 px-2.5 pt-1">
          <Select value={vf} onChange={(e) => setVf(e.target.value)}>
            {VFILTERS.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
          </Select>
          <label className="flex items-center justify-between text-[13px] text-[#4a5d7c]">
            Show evidence
            <Switch checked={showEv} onChange={setShowEv} />
          </label>
          <label className="flex items-center justify-between text-[13px] text-[#4a5d7c]">
            Show people
            <Switch checked={showPeople} onChange={setShowPeople} />
          </label>
        </div>
      </nav>
      <div className="border-t border-line p-3 text-[11.5px] leading-relaxed text-muted">
        <span className="font-semibold text-indigo-600">AI confidence</span> is model certainty.{' '}
        <span className="font-semibold text-teal-700">Verified</span> means a person confirmed it.
      </div>
    </div>
  )

  const listView = (
    <ul className="scrollbar-thin h-full divide-y divide-line overflow-y-auto">
      {list.map((n) => {
        const f = findings.find((x) => x.id === n.id)
        return (
          <li key={n.id}>
            <button
              onClick={() => select(n.id)}
              className={cn('flex w-full flex-col gap-2 px-5 py-3.5 text-left transition-colors hover:bg-[#f9fbfe] sm:flex-row sm:items-center', sel === n.id && 'bg-blue-50/60')}
            >
              <span className="flex flex-1 items-center gap-3">
                <span className="size-2 shrink-0 rounded-full" style={{ background: NODE_COLOR[n.kind] }} />
                <span>
                  <span className="block text-[13.5px] font-medium text-navy">{n.label}</span>
                  <span className="text-[11.5px] text-muted">{n.kind} · {adj.get(n.id)?.size ?? 0} relationships</span>
                </span>
              </span>
              {f && <FindingRowMeta f={f} />}
            </button>
          </li>
        )
      })}
      {!list.length && <EmptyState icon={Search} title="Nothing found" body="Try another search, category or filter." />}
    </ul>
  )

  const toolbar = (
    <div className="flex items-center gap-2">
      <Segmented value={view} onChange={setView} options={[{ id: 'graph', icon: Network, label: 'Graph' }, { id: 'list', icon: List, label: 'List' }]} />
      <Button variant="secondary" size="sm" className="hidden lg:inline-flex" icon={focus ? Minimize2 : Maximize2} onClick={() => setFocus(!focus)}>
        {focus ? 'Exit focus' : 'Focus'}
      </Button>
    </div>
  )

  return (
    <>
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-[12.5px] text-muted">
            <span className="size-2 rounded-full" style={{ background: p.color }} />{p.name}
          </p>
          <h1 className="mt-1 text-[26px] font-semibold tracking-[-0.025em] text-navy">Knowledge Explorer</h1>
        </div>
        {toolbar}
      </div>

      {/* Desktop three-panel workspace */}
      <div
        className={cn(
          'hidden overflow-hidden rounded-[14px] border border-line bg-white shadow-card lg:grid',
          focus ? 'lg:grid-cols-[1fr]' : 'lg:grid-cols-[232px_1fr_340px]'
        )}
        style={{ height: 'calc(100dvh - 210px)', minHeight: 560 }}
      >
        {!focus && <aside className="min-h-0 border-r border-line bg-[#f8fafd]">{nav}</aside>}
        <section className="relative min-h-0 min-w-0 bg-white">
          {view === 'graph' ? (
            <>
              <div className="pointer-events-none absolute inset-0 dot-grid opacity-60" />
              <KnowledgeCanvas pid={p.id} center={sel} onSelect={select} filter={graphFilter} />
              {trail.length > 1 && (
                <div className="absolute left-3 top-3 flex max-w-[70%] items-center gap-1 overflow-hidden rounded-[10px] border border-line bg-white/95 px-2 py-1 shadow-card backdrop-blur">
                  <History className="size-3.5 shrink-0 text-slate-400" />
                  {trail.map((id, i) => (
                    <span key={id} className="flex min-w-0 items-center gap-1">
                      {i > 0 && <ChevronRight className="size-3 shrink-0 text-slate-300" />}
                      <button onClick={() => select(id)} className={cn('truncate rounded px-1 text-[12px]', id === sel ? 'font-semibold text-navy' : 'text-muted hover:text-navy')}>
                        {nodes.get(id)?.label.slice(0, 22)}
                      </button>
                    </span>
                  ))}
                </div>
              )}
              <div className="absolute bottom-3 left-3 flex flex-wrap gap-x-3 gap-y-1 rounded-[10px] border border-line bg-white/95 px-3 py-1.5 backdrop-blur">
                {(['Decision', 'Task', 'Risk', 'Dependency', 'Person', 'Component', 'Evidence'] as NodeKind[]).map((k) => (
                  <span key={k} className="flex items-center gap-1.5 text-[11px] text-muted">
                    <span className="size-2 rounded-full" style={{ background: NODE_COLOR[k] }} />{k}
                  </span>
                ))}
              </div>
              {focus && (
                <div className="absolute right-3 top-3 w-[300px] rounded-[14px] border border-line bg-white/97 p-4 shadow-pop backdrop-blur">
                  <Inspector pid={p.id} nodeId={sel} onOpen={setDrawer} onNavigate={select} compact />
                </div>
              )}
            </>
          ) : (
            listView
          )}
        </section>
        {!focus && (
          <aside className="scrollbar-thin min-h-0 overflow-y-auto border-l border-line bg-white p-5">
            <Inspector pid={p.id} nodeId={sel} onOpen={setDrawer} onNavigate={select} />
          </aside>
        )}
      </div>

      {/* Mobile & tablet: list-first exploration with a bottom-sheet inspector */}
      <div className="lg:hidden">
        <div className="scrollbar-thin -mx-4 mb-3 flex gap-1.5 overflow-x-auto px-4">
          {CATS.map((c) => (
            <button
              key={c.id}
              onClick={() => setCat(c.id)}
              className={cn(
                'flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12.5px] font-medium',
                cat === c.id ? 'border-navy bg-navy text-white' : 'border-line bg-white text-[#4a5d7c]'
              )}
            >
              {c.id !== 'all' && <span className="size-1.5 rounded-full" style={{ background: NODE_COLOR[c.id] }} />}
              {c.label}
            </button>
          ))}
        </div>
        <div className="mb-3"><SearchInput placeholder="Search knowledge" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        <Card className="overflow-hidden">
          {view === 'graph' ? (
            <div className="relative h-[440px]">
              <div className="pointer-events-none absolute inset-0 dot-grid opacity-60" />
              <KnowledgeCanvas pid={p.id} center={sel} onSelect={select} filter={graphFilter} focusLabel={false} />
            </div>
          ) : (
            <div className="max-h-[70dvh]">{listView}</div>
          )}
        </Card>
        {sheet && (
          <div className="animate-fade-only fixed inset-0 z-[55] bg-navy/25" onClick={() => setSheet(false)}>
            <div className="animate-slide-up absolute inset-x-0 bottom-0 max-h-[78dvh] overflow-y-auto rounded-t-[20px] bg-white p-5 pb-8 shadow-pop" onClick={(e) => e.stopPropagation()}>
              <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-slate-200" />
              <Inspector pid={p.id} nodeId={sel} onOpen={(f) => { setSheet(false); setDrawer(f) }} onNavigate={select} onClose={() => setSheet(false)} />
              {view === 'list' && (
                <Button variant="secondary" className="mt-4 w-full" icon={Network} onClick={() => { setView('graph'); setSheet(false) }}>
                  Show in graph
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
      <FindingDrawer finding={drawer} onClose={() => setDrawer(undefined)} />
    </>
  )
}

/* ---------- Master KnowledgePage Component ---------- */
export interface KnowledgePageProps {
  view?: 'sources' | 'source-detail' | 'evidence' | 'evidence-detail' | 'ingestion' | 'knowledge'
  projectId?: string
  sourceId?: string
  evidenceId?: string
}

function KnowledgePageInner({
  view = 'sources',
  projectId,
  sourceId,
  evidenceId,
}: KnowledgePageProps) {
  const params = useParams() as { id?: string; sourceId?: string; evidenceId?: string } | null
  const { activeProject, projects } = useLiveApp()
  const s = useStore()

  const pid =
    projectId ||
    params?.id ||
    activeProject?.id ||
    s.currentProject?.id ||
    (projects.length > 0 ? projects[0]?.id : undefined) ||
    (s.projects.length > 0 ? s.projects[0]?.id : undefined) ||
    ''
  const sid = sourceId || params?.sourceId || 'src-github-atlas'
  const eid = evidenceId || params?.evidenceId || 'e-settle-adr'

  switch (view) {
    case 'sources':
      return <DataSources projectId={pid} />
    case 'source-detail':
      return <SourceDetail projectId={pid} sourceId={sid} />
    case 'evidence':
      return <EvidenceLibrary projectId={pid} />
    case 'evidence-detail':
      return <EvidenceDetail projectId={pid} evidenceId={eid} />
    case 'ingestion':
      return <Ingestion projectId={pid} />
    case 'knowledge':
      return <KnowledgeExplorer projectId={pid} />
    default:
      return <DataSources projectId={pid} />
  }
}

export function KnowledgePage(props: KnowledgePageProps) {
  const existingCtx = useContext(FigmaCtx)
  if (existingCtx) {
    return <KnowledgePageInner {...props} />
  }
  return (
    <FigmaStoreProvider>
      <KnowledgePageInner {...props} />
    </FigmaStoreProvider>
  )
}

export default KnowledgePage
