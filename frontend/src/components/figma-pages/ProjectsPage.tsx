'use client'

import { useContext, useMemo, useState, type ReactNode } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock,
  Database,
  FolderPlus,
  LayoutGrid,
  List,
  Mail,
  MoreHorizontal,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  UserPlus,
  Users,
  Workflow,
  AlertTriangle,
  ListTodo,
  Lightbulb,
  Activity,
  Sparkles,
  X,
  Lock,
  Search,
} from 'lucide-react'
import {
  useFigmaStore,
  FigmaStoreProvider,
  FigmaCtx,
  ME,
  people,
  personById,
  ROLE_LABEL,
  SOURCE_META,
  timeline,
  auditLogs,
  type MemberRole,
  type SourceType,
} from '../../lib/figmaStore'
import {
  Avatar,
  AvatarGroup,
  Badge,
  Button,
  Card,
  CardHeader,
  Checkbox,
  ConfirmDialog,
  Dropdown,
  EmptyState,
  Field,
  Input,
  MenuItem,
  Modal,
  PageHeader,
  PersonCell,
  Progress,
  SearchInput,
  Segmented,
  Select,
  StatusBadge,
  Table,
  Td,
  Textarea,
  Th,
  cn,
} from '../figma-ui/index'
import { Ring, StackedBar } from '../figma-ui/charts'
import { SourceIcon } from '../figma-ui/brand'
import {
  RoleBadge,
  HandoverTable,
  PermissionNote,
  ProjectHeader,
  ProjectNotFound,
  SeverityBadge,
  TaskStatus,
  projectFindings,
  useProject,
  allFindings,
} from '../figma-ui/domain'

export function ProjectsList() {
  const router = useRouter()
  const s = useFigmaStore()
  const [view, setView] = useState<'grid' | 'list'>('grid')
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('all')
  const [role, setRole] = useState('all')

  const list = s.projects.filter(
    (p) =>
      p.name.toLowerCase().includes(q.toLowerCase()) &&
      (status === 'all' || p.status === status) &&
      (role === 'all' || p.role === role)
  )
  const membersOf = (pid: string) => s.members.filter((m) => m.projectId === pid).map((m) => m.personId)
  const srcOf = (pid: string) => s.sources.filter((x) => x.projectId === pid)

  return (
    <>
      <PageHeader
        title="My Projects"
        subtitle="Projects you belong to. Your role is set per project and determines what you can see and do."
        actions={<Button icon={Plus} onClick={() => router.push('/projects/new')}>Create project</Button>}
      />
      <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center">
        <SearchInput placeholder="Search projects" value={q} onChange={(e) => setQ(e.target.value)} className="md:w-72" />
        <div className="flex gap-2">
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-40">
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="at_risk">At risk</option>
            <option value="planning">Planning</option>
          </Select>
          <Select value={role} onChange={(e) => setRole(e.target.value)} className="w-44">
            <option value="all">All my roles</option>
            <option value="manager">Project Manager</option>
            <option value="outgoing">Outgoing Member</option>
            <option value="incoming">Incoming Member</option>
          </Select>
        </div>
        <div className="md:ml-auto">
          <Segmented
            value={view}
            onChange={setView}
            options={[
              { id: 'grid', icon: LayoutGrid, label: 'Grid' },
              { id: 'list', icon: List, label: 'List' },
            ]}
          />
        </div>
      </div>
      {!s.projects.length ? (
        <Card>
          <EmptyState
            icon={FolderPlus}
            title="No projects yet"
            body="Create a project to connect sources, add members and start capturing knowledge."
            action={<Button icon={Plus} onClick={() => router.push('/projects/new')}>Create project</Button>}
          />
        </Card>
      ) : !list.length ? (
        <Card>
          <EmptyState
            icon={Search}
            title="No matching projects"
            body="Try a different search term or clear filters."
            action={
              <Button
                variant="secondary"
                onClick={() => {
                  setQ('')
                  setStatus('all')
                  setRole('all')
                }}
              >
                Clear filters
              </Button>
            }
          />
        </Card>
      ) : view === 'grid' ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {list.map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`} className="group">
              <Card className="tile-target flex h-full flex-col p-5 transition duration-200">
                <div className="flex items-start justify-between">
                  <span className="flex size-10 items-center justify-center rounded-xl text-xs font-bold text-white" style={{ background: p.color }}>
                    {p.code}
                  </span>
                  <StatusBadge status={p.status} />
                </div>
                <h3 className="mt-4 text-[15px] font-semibold text-navy group-hover:text-brand">{p.name}</h3>
                <p className="mt-1 line-clamp-2 flex-1 text-[13px] text-muted">{p.description}</p>
                <div className="mt-4">
                  <RoleBadge role={p.role} />
                </div>
                <div className="mt-4">
                  <div className="mb-1.5 flex justify-between text-xs">
                    <span className="text-muted">Knowledge coverage</span>
                    <span className="font-medium text-navy">{p.coverage}%</span>
                  </div>
                  <Progress value={p.coverage} size="sm" />
                </div>
                <div className="mt-4 flex items-center justify-between border-t border-line pt-4">
                  <AvatarGroup ids={membersOf(p.id)} size={24} />
                  <div className="flex items-center gap-1">
                    {srcOf(p.id).map((x) => (
                      <SourceIcon key={x.id} type={x.type} size={22} />
                    ))}
                    {!srcOf(p.id).length && <span className="text-xs text-slate-400">No sources</span>}
                  </div>
                </div>
                <p className="mt-3 flex items-center gap-1.5 text-xs text-muted">
                  <Clock className="size-3" />
                  {p.lastActivity} · Owner {personById(p.ownerId).name}
                </p>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <Card className="overflow-hidden">
          <Table>
            <thead>
              <tr>
                <Th>Project</Th>
                <Th>Your role</Th>
                <Th>Owner</Th>
                <Th>Members</Th>
                <Th>Sources</Th>
                <Th>Last activity</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {list.map((p) => (
                <tr key={p.id} onClick={() => router.push(`/projects/${p.id}`)} className="cursor-pointer hover:bg-slate-50/70">
                  <Td>
                    <span className="flex items-center gap-3">
                      <span className="flex size-8 items-center justify-center rounded-lg text-[10px] font-bold text-white" style={{ background: p.color }}>
                        {p.code}
                      </span>
                      <span>
                        <span className="block font-medium text-navy">{p.name}</span>
                        <span className="text-xs text-muted">{p.category}</span>
                      </span>
                    </span>
                  </Td>
                  <Td>
                    <RoleBadge role={p.role} />
                  </Td>
                  <Td>
                    <span className="flex items-center gap-2">
                      <Avatar id={p.ownerId} size={22} />
                      <span className="text-[13px]">{personById(p.ownerId).name}</span>
                    </span>
                  </Td>
                  <Td>
                    <AvatarGroup ids={membersOf(p.id)} size={22} />
                  </Td>
                  <Td>
                    <span className="flex gap-1">
                      {srcOf(p.id).map((x) => (
                        <SourceIcon key={x.id} type={x.type} size={22} />
                      ))}
                    </span>
                  </Td>
                  <Td className="text-[13px] text-muted">{p.lastActivity}</Td>
                  <Td>
                    <StatusBadge status={p.status} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      )}
    </>
  )
}

const CP_STEPS = ['Details', 'Team', 'Sources']

export function CreateProject() {
  const router = useRouter()
  const s = useFigmaStore()
  const [step, setStep] = useState(0)
  const [f, setF] = useState({
    name: '',
    description: '',
    category: '',
    owner: ME,
    start: '2025-06-23',
    end: '2025-12-19',
  })
  const [team, setTeam] = useState<{ id: string; role: MemberRole }[]>([{ id: ME, role: 'manager' }])
  const [srcs, setSrcs] = useState<SourceType[]>(['github', 'jira'])
  const [touched, setTouched] = useState(false)

  const nameErr = !f.name.trim() ? 'Project name is required' : ''
  const dateErr = f.end < f.start ? 'Completion must be after start date' : ''

  const next = () => {
    setTouched(true)
    if (step === 0 && (nameErr || dateErr)) return
    setStep(step + 1)
  }

  const create = () => {
    const id = f.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 24) || `proj-${Date.now()}`
    s.setProjects((ps) => [
      ...ps,
      {
        id,
        workspaceId: s.workspaceId,
        name: f.name,
        code: f.name.replace(/[^A-Za-z]/g, '').slice(0, 3).toUpperCase() || 'NEW',
        description: f.description || 'No description yet.',
        category: f.category,
        status: 'planning',
        health: 0,
        ownerId: f.owner,
        role: 'manager',
        lastActivity: 'Just now',
        coverage: 0,
        startDate: f.start,
        endDate: f.end,
        color: '#5B8BC9',
      },
    ])
    s.setMembers((ms) => [...ms, ...team.map((t) => ({ projectId: id, personId: t.id, role: t.role, responsibilities: [], tasks: 0 }))])
    s.setSources((ss) => [
      ...ss,
      ...srcs.map((t) => ({
        id: `src-${t}-${id}`,
        projectId: id,
        type: t,
        name: SOURCE_META[t].label,
        account: 'Awaiting authorisation',
        status: 'disconnected' as const,
        lastSync: 'Never',
        records: 0,
        scope: [],
        frequency: 'Hourly',
        volume: '0 MB',
      })),
    ])
    s.switchProject(id, true)
    s.toast('Project created', `${f.name} is ready. Authorise your selected sources to begin ingestion.`)
    router.push(`/projects/${id}`)
  }

  return (
    <>
      <Link href="/projects" className="mb-4 inline-flex items-center gap-1.5 text-[13px] font-medium text-muted hover:text-navy">
        <ArrowLeft className="size-4" />
        Projects
      </Link>
      <PageHeader title="Create project" subtitle="Set up a project workspace. You'll be its Project Manager." />
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <Card className="p-5 sm:p-7">
          <ol className="mb-7 flex items-center gap-3">
            {CP_STEPS.map((l, i) => (
              <li key={l} className="flex flex-1 items-center gap-2.5">
                <span
                  className={cn(
                    'flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold',
                    i < step ? 'bg-ok text-white' : i === step ? 'bg-brand text-white' : 'bg-slate-100 text-slate-400'
                  )}
                >
                  {i < step ? <Check className="size-3.5" /> : i + 1}
                </span>
                <span className={cn('text-sm font-medium', i === step ? 'text-navy' : 'text-muted')}>{l}</span>
                {i < CP_STEPS.length - 1 && <span className="h-px flex-1 bg-line" />}
              </li>
            ))}
          </ol>
          {step === 0 && (
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Project name" required className="sm:col-span-2" error={touched ? nameErr : undefined}>
                <Input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="e.g. Billing Revamp" invalid={touched && !!nameErr} autoFocus />
              </Field>
              <Field label="Description" className="sm:col-span-2" hint="Helps the AI scope knowledge reconstruction.">
                <Textarea value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} placeholder="What does this project do and who depends on it?" />
              </Field>
              <Field label="Category">
                <Input
                  value={f.category}
                  onChange={(e) => setF({ ...f, category: e.target.value })}
                  placeholder="e.g. Backend platform, Mobile, Infrastructure"
                />
              </Field>
              <Field label="Project owner">
                <Select value={f.owner} onChange={(e) => setF({ ...f, owner: e.target.value })}>
                  {people
                    .filter((p) => p.status === 'Active')
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                </Select>
              </Field>
              <Field label="Start date">
                <Input type="date" value={f.start} onChange={(e) => setF({ ...f, start: e.target.value })} />
              </Field>
              <Field label="Expected completion" error={touched ? dateErr : undefined}>
                <Input type="date" value={f.end} onChange={(e) => setF({ ...f, end: e.target.value })} invalid={touched && !!dateErr} />
              </Field>
            </div>
          )}
          {step === 1 && (
            <div>
              <p className="mb-4 text-sm text-muted">Select members and their project role. You can change this later.</p>
              <ul className="divide-y divide-line rounded-xl border border-line">
                {people
                  .filter((p) => p.status === 'Active')
                  .map((p) => {
                    const sel = team.find((t) => t.id === p.id)
                    return (
                      <li key={p.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                        <Checkbox
                          checked={!!sel}
                          onChange={(v) => (v ? setTeam([...team, { id: p.id, role: 'contributor' }]) : setTeam(team.filter((t) => t.id !== p.id)))}
                        />
                        <div className="min-w-[180px] flex-1">
                          <PersonCell id={p.id} />
                        </div>
                        {sel && (
                          <Select
                            value={sel.role}
                            onChange={(e) => setTeam(team.map((t) => (t.id === p.id ? { ...t, role: e.target.value as MemberRole } : t)))}
                            className="w-44"
                          >
                            {(['manager', 'outgoing', 'incoming', 'contributor', 'viewer'] as MemberRole[]).map((r) => (
                              <option key={r} value={r}>
                                {ROLE_LABEL[r]}
                              </option>
                            ))}
                          </Select>
                        )}
                      </li>
                    )
                  })}
              </ul>
            </div>
          )}
          {step === 2 && (
            <div>
              <p className="mb-4 text-sm text-muted">Choose sources to connect. You'll authorise each one from the project's Data Sources page. Only the scopes you approve are ingested.</p>
              <div className="grid gap-3 sm:grid-cols-2">
                {(['github', 'jira', 'slack', 'docs', 'confluence', 'gdrive'] as SourceType[]).map((t) => {
                  const on = srcs.includes(t)
                  return (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setSrcs(on ? srcs.filter((x) => x !== t) : [...srcs, t])}
                      className={cn(
                        'flex items-start gap-3 rounded-xl border p-4 text-left transition',
                        on ? 'border-brand bg-tint/40 ring-4 ring-brand/10' : 'border-line hover:border-slate-300'
                      )}
                    >
                      <SourceIcon type={t} />
                      <span className="flex-1">
                        <span className="block text-sm font-semibold text-navy">{SOURCE_META[t].label}</span>
                        <span className="block text-xs text-muted">{SOURCE_META[t].description}</span>
                      </span>
                      <span className={cn('flex size-5 items-center justify-center rounded-full border', on ? 'border-brand bg-brand text-white' : 'border-slate-300')}>
                        {on && <Check className="size-3" />}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          )}
          <div className="mt-8 flex justify-between border-t border-line pt-5">
            <Button variant="ghost" icon={ArrowLeft} onClick={() => (step ? setStep(step - 1) : router.push('/projects'))}>
              {step ? 'Back' : 'Cancel'}
            </Button>
            {step < 2 ? <Button iconRight={ArrowRight} onClick={next}>Continue</Button> : <Button icon={CheckCircle2} onClick={create}>Create project</Button>}
          </div>
        </Card>
        <Card className="h-fit p-5 lg:sticky lg:top-0">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Summary</p>
          <p className="mt-3 text-base font-semibold text-navy">{f.name || 'Untitled project'}</p>
          <p className="text-[13px] text-muted">{f.category}</p>
          <dl className="mt-4 space-y-2.5 text-[13px]">
            <div className="flex justify-between">
              <dt className="text-muted">Owner</dt>
              <dd className="font-medium text-navy">{personById(f.owner).name}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Timeline</dt>
              <dd className="font-medium text-navy">{f.start} → {f.end}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Members</dt>
              <dd>
                <AvatarGroup ids={team.map((t) => t.id)} size={22} />
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Sources</dt>
              <dd className="flex gap-1">
                {srcs.map((t) => (
                  <SourceIcon key={t} type={t} size={22} />
                ))}
              </dd>
            </div>
          </dl>
        </Card>
      </div>
    </>
  )
}

export function ProjectOverview({ projectId }: { projectId: string }) {
  const router = useRouter()
  const s = useFigmaStore()
  const p = useProject(projectId)
  if (!p) return <ProjectNotFound />

  const f = projectFindings(p.id)
  const members = s.members.filter((m) => m.projectId === p.id)
  const srcs = s.sources.filter((x) => x.projectId === p.id)
  const hos = s.handovers.filter((h) => h.projectId === p.id && h.status !== 'completed')
  const all = allFindings(p.id)
  const verifiedN = all.filter((x) => s.verif[x.id] === 'verified').length
  const isNew = !srcs.some((x) => x.status !== 'disconnected')

  return (
    <>
      <ProjectHeader
        project={p}
        tab="overview"
        actions={
          p.role === 'manager' ? (
            <>
              <Button variant="secondary" icon={Database} onClick={() => router.push(`/projects/${p.id}/sources`)}>
                Sources
              </Button>
              <Button icon={Workflow} onClick={() => router.push(`/handovers/new?project=${p.id}`)}>
                Create handover
              </Button>
            </>
          ) : p.role === 'incoming' ? (
            <Button icon={Sparkles} onClick={() => router.push(`/projects/${p.id}/knowledge`)}>
              Explore knowledge
            </Button>
          ) : (
            <Button icon={ShieldCheck} onClick={() => router.push(`/handovers/${hos.find((h) => h.outgoingId === ME)?.id ?? ''}/review`)}>
              Verify my handover
            </Button>
          )
        }
      />
      {isNew && (
        <Card className="mb-5">
          <EmptyState
            icon={Database}
            title="Connect sources to start reconstructing knowledge"
            body="This project has no connected sources yet, so there are no decisions, tasks or risks to show."
            action={p.role === 'manager' ? <Button icon={Plus} onClick={() => router.push(`/projects/${p.id}/sources`)}>Connect a source</Button> : undefined}
          />
        </Card>
      )}
      <div className="grid gap-5 lg:grid-cols-3">
        <Card interactive className="p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Project summary</p>
          <div className="mt-4 flex items-center gap-4">
            <Ring
              value={p.health}
              size={72}
              color={p.health >= 80 ? '#299B80' : p.health >= 60 ? '#D39B43' : '#C9D3E3'}
              label={p.health ? `${p.health}` : '—'}
            />
            <div>
              <p className="text-sm font-semibold text-navy">Project health</p>
              <p className="text-xs text-muted">{p.health >= 80 ? 'Healthy · few open risks' : p.health >= 60 ? 'Watch · critical risks open' : 'Not enough data yet'}</p>
              <div className="mt-1.5">
                <StatusBadge status={p.status} />
              </div>
            </div>
          </div>
          <dl className="mt-5 space-y-2.5 border-t border-line pt-4 text-[13px]">
            <div className="flex justify-between">
              <dt className="text-muted">Owner</dt>
              <dd className="flex items-center gap-1.5 font-medium text-navy">
                <Avatar id={p.ownerId} size={20} />
                {personById(p.ownerId).name}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Category</dt>
              <dd className="font-medium text-navy">{p.category}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Timeline</dt>
              <dd className="font-medium text-navy">
                {new Date(p.startDate).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })} – {new Date(p.endDate).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Last activity</dt>
              <dd className="font-medium text-navy">{p.lastActivity}</dd>
            </div>
          </dl>
        </Card>
        <Card>
          <CardHeader
            title="Knowledge coverage"
            subtitle="Share of project areas with verified evidence"
            icon={Sparkles}
            action={<Link href={`/projects/${p.id}/intelligence`} className="text-[13px] font-medium text-brand">Intelligence</Link>}
          />
          <div className="px-5 pb-5">
            <div className="flex items-end gap-2">
              <span className="text-3xl font-semibold text-navy">{p.coverage}%</span>
              <span className="mb-1 text-xs text-muted">{verifiedN} of {all.length} findings verified</span>
            </div>
            <StackedBar
              className="mt-3"
              segments={[
                { label: 'Verified', value: verifiedN, color: '#299B80' },
                { label: 'Needs review', value: all.filter((x) => s.verif[x.id] === 'needs_review').length, color: '#D39B43' },
                { label: 'Conflicting / insufficient', value: all.filter((x) => s.verif[x.id] === 'conflicting' || s.verif[x.id] === 'insufficient').length, color: '#D36D72' },
              ]}
            />
            <div className="mt-4 grid grid-cols-2 gap-2 text-[13px]">
              {[
                ['Decisions', f.decisions.length, Lightbulb],
                ['Tasks', f.tasks.length, ListTodo],
                ['Risks', f.risks.length, AlertTriangle],
                ['Evidence', f.evidence.length, Database],
              ].map(([l, v, I]) => {
                const Ic = I as typeof Lightbulb
                return (
                  <div key={l as string} className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2">
                    <Ic className="size-3.5 text-muted" />
                    <span className="flex-1 text-muted">{l as string}</span>
                    <span className="font-semibold text-navy">{v as number}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </Card>
        <Card>
          <CardHeader
            title="Team members"
            subtitle={`${members.length} members`}
            icon={Users}
            action={<Link href={`/projects/${p.id}/team`} className="text-[13px] font-medium text-brand">Manage</Link>}
          />
          <ul className="space-y-2.5 px-5 pb-5">
            {members.slice(0, 5).map((m) => (
              <li key={m.personId} className="flex items-center justify-between gap-2">
                <PersonCell id={m.personId} sub={m.responsibilities[0] ?? undefined} />
                <Badge tone={m.role === 'outgoing' ? 'amber' : m.role === 'incoming' ? 'green' : m.role === 'manager' ? 'blue' : 'gray'}>
                  {ROLE_LABEL[m.role]}
                </Badge>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <CardHeader
            title="Connected data sources"
            icon={Database}
            action={<Link href={`/projects/${p.id}/sources`} className="text-[13px] font-medium text-brand">View</Link>}
          />
          <ul className="space-y-3 px-5 pb-5">
            {srcs.map((x) => (
              <li key={x.id}>
                <Link href={`/projects/${p.id}/sources/${x.id}`} className="flex items-center gap-3">
                  <SourceIcon type={x.type} size={32} />
                  <span className="flex-1">
                    <span className="block text-[13px] font-medium text-navy">{x.name}</span>
                    <span className="text-xs text-muted">{x.records.toLocaleString()} records · {x.lastSync}</span>
                  </span>
                  <StatusBadge status={x.status} />
                </Link>
              </li>
            ))}
            {!srcs.length && <p className="text-[13px] text-muted">No sources selected.</p>}
          </ul>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader
            title="Active handovers"
            icon={Workflow}
            action={
              p.role === 'manager' && (
                <Button size="sm" variant="secondary" icon={Plus} onClick={() => router.push(`/handovers/new?project=${p.id}`)}>
                  New
                </Button>
              )
            }
          />
          <HandoverTable
            items={hos}
            empty={<EmptyState className="py-8" icon={Workflow} title="No active handovers" body="Create a handover when someone is leaving or changing roles." />}
          />
        </Card>
        <Card>
          <CardHeader
            title="Recent decisions"
            icon={Lightbulb}
            action={<Link href={`/projects/${p.id}/intelligence/decisions`} className="text-[13px] font-medium text-brand">All</Link>}
          />
          <ul className="space-y-3 px-5 pb-5">
            {f.decisions.slice(0, 3).map((d) => (
              <li key={d.id}>
                <Link href={`/projects/${p.id}/intelligence/decisions?id=${d.id}`} className="block rounded-lg hover:bg-slate-50">
                  <p className="text-[13px] font-medium text-navy">{d.title}</p>
                  <p className="mt-0.5 flex items-center gap-2 text-xs text-muted">{personById(d.ownerId).name} · {d.date}</p>
                </Link>
              </li>
            ))}
            {!f.decisions.length && <p className="text-[13px] text-muted">No decisions reconstructed yet.</p>}
          </ul>
        </Card>
        <Card>
          <CardHeader
            title="Outstanding risks"
            icon={AlertTriangle}
            action={<Link href={`/projects/${p.id}/intelligence/risks`} className="text-[13px] font-medium text-brand">All</Link>}
          />
          <ul className="space-y-3 px-5 pb-5">
            {f.risks
              .filter((r) => r.resolution !== 'Resolved')
              .slice(0, 3)
              .map((r) => (
                <li key={r.id} className="flex items-start gap-2.5">
                  <SeverityBadge level={r.severity} />
                  <span className="text-[13px] text-navy">{r.title}</span>
                </li>
              ))}
            {!f.risks.length && <p className="text-[13px] text-muted">No risks identified.</p>}
          </ul>
        </Card>
        <Card>
          <CardHeader
            title="Pending tasks"
            icon={ListTodo}
            action={<Link href={`/projects/${p.id}/intelligence/tasks`} className="text-[13px] font-medium text-brand">All</Link>}
          />
          <ul className="space-y-3 px-5 pb-5">
            {f.tasks
              .filter((t) => t.status !== 'Done')
              .slice(0, 4)
              .map((t) => (
                <li key={t.id} className="flex items-center gap-2.5">
                  <Avatar id={t.ownerId} size={22} />
                  <span className="flex-1 truncate text-[13px] text-navy">{t.title}</span>
                  <TaskStatus status={t.status} />
                </li>
              ))}
            {!f.tasks.length && <p className="text-[13px] text-muted">No tasks yet.</p>}
          </ul>
        </Card>
        <Card>
          <CardHeader
            title="Recent activity"
            icon={Activity}
            action={<Link href={`/projects/${p.id}/activity`} className="text-[13px] font-medium text-brand">All</Link>}
          />
          <ul className="space-y-3 px-5 pb-5">
            {timeline
              .filter((t) => t.projectId === p.id)
              .slice(0, 4)
              .map((t) => (
                <li key={t.id} className="flex gap-2.5">
                  <Avatar id={t.personId} size={22} />
                  <span className="text-[13px] text-navy">
                    {t.title}
                    <span className="block text-xs text-muted">{t.date}</span>
                  </span>
                </li>
              ))}
            {!timeline.some((t) => t.projectId === p.id) && <p className="text-[13px] text-muted">No activity yet.</p>}
          </ul>
        </Card>
      </div>
    </>
  )
}

const PERMS: [string, boolean, boolean, boolean, boolean][] = [
  ['View verified knowledge', true, true, true, true],
  ['View evidence & sources', true, true, true, false],
  ['Verify / reject findings', true, true, false, false],
  ['Add missing information', true, true, false, false],
  ['Connect & manage sources', true, false, false, false],
  ['Create & approve handovers', true, false, false, false],
  ['Publish handover reports', true, false, false, false],
  ['Acknowledge received handovers', false, false, true, false],
]

export function ProjectTeam({ projectId }: { projectId: string }) {
  const router = useRouter()
  const s = useFigmaStore()
  const p = useProject(projectId)
  const [addOpen, setAddOpen] = useState(false)
  const [remove, setRemove] = useState<string | null>(null)
  const [newM, setNewM] = useState({ email: '', role: 'contributor' as MemberRole })
  const [invites, setInvites] = useState([{ email: 'grace.liu@northwind.io', role: 'viewer' as MemberRole, sent: 'Jun 16' }])

  if (!p) return <ProjectNotFound />

  const canManage = p.role === 'manager'
  const members = s.members.filter((m) => m.projectId === p.id)
  const f = projectFindings(p.id)

  const setRole = (pid: string, role: MemberRole) => {
    s.setMembers((ms) => ms.map((m) => (m.projectId === p.id && m.personId === pid ? { ...m, role } : m)))
    s.toast('Role updated', `${personById(pid).name} is now ${ROLE_LABEL[role]}.`)
  }

  return (
    <>
      <ProjectHeader project={p} tab="team" actions={canManage && <Button icon={UserPlus} onClick={() => setAddOpen(true)}>Add member</Button>} />
      {!canManage && (
        <div className="mb-5">
          <PermissionNote role={p.role} action="add, remove or change member roles" />
        </div>
      )}
      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <Card className="overflow-hidden">
          <CardHeader title="Members" subtitle={`${members.length} people on this project`} />
          <Table>
            <thead>
              <tr>
                <Th>Member</Th>
                <Th>Project role</Th>
                <Th>Responsibilities</Th>
                <Th>Assigned tasks</Th>
                <Th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.personId} className="hover:bg-slate-50/50">
                  <Td>
                    <PersonCell id={m.personId} sub={personById(m.personId).email} />
                  </Td>
                  <Td>
                    {canManage && m.personId !== ME ? (
                      <Select value={m.role} onChange={(e) => setRole(m.personId, e.target.value as MemberRole)} className="w-44">
                        {(['manager', 'outgoing', 'incoming', 'contributor', 'viewer'] as MemberRole[]).map((r) => (
                          <option key={r} value={r}>
                            {ROLE_LABEL[r]}
                          </option>
                        ))}
                      </Select>
                    ) : (
                      <Badge tone={m.role === 'outgoing' ? 'amber' : m.role === 'incoming' ? 'green' : m.role === 'manager' ? 'blue' : 'gray'}>
                        {ROLE_LABEL[m.role]}
                      </Badge>
                    )}
                  </Td>
                  <Td>
                    <div className="flex max-w-[260px] flex-wrap gap-1">
                      {m.responsibilities.map((r) => (
                        <span key={r} className="rounded-md bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                          {r}
                        </span>
                      ))}
                      {!m.responsibilities.length && <span className="text-xs text-slate-400">None yet</span>}
                    </div>
                  </Td>
                  <Td>
                    <span className="text-[13px] font-medium text-navy">
                      {f.tasks.filter((t) => t.ownerId === m.personId && t.status !== 'Done').length || m.tasks}
                    </span>
                  </Td>
                  <Td>
                    {canManage && m.personId !== ME && (
                      <Dropdown trigger={() => <button className="rounded-lg p-1.5 text-muted hover:bg-slate-100" aria-label="Member actions"><MoreHorizontal className="size-4" /></button>}>
                        {(close) => (
                          <>
                            <MenuItem icon={Workflow} onClick={() => { close(); router.push(`/handovers/new?project=${p.id}`) }}>
                              Start handover
                            </MenuItem>
                            <MenuItem icon={Mail} onClick={() => { close(); s.toast('Message sent') }}>
                              Message
                            </MenuItem>
                            <MenuItem icon={Trash2} danger onClick={() => { close(); setRemove(m.personId) }}>
                              Remove from project
                            </MenuItem>
                          </>
                        )}
                      </Dropdown>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
        <div className="space-y-5">
          <Card>
            <CardHeader title="Pending invitations" subtitle={`${invites.length} awaiting response`} icon={Mail} />
            <ul className="space-y-2 px-5 pb-5">
              {invites.map((i) => (
                <li key={i.email} className="flex items-center gap-3 rounded-xl border border-line p-3">
                  <Avatar name={i.email} size={28} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[13px] font-medium text-navy">{i.email}</p>
                    <p className="text-xs text-muted">{ROLE_LABEL[i.role]} · sent {i.sent}</p>
                  </div>
                  {canManage && (
                    <>
                      <button className="rounded p-1 text-muted hover:text-brand" title="Resend" onClick={() => s.toast('Invitation resent', i.email)}>
                        <RefreshCw className="size-3.5" />
                      </button>
                      <button
                        className="rounded p-1 text-muted hover:text-bad"
                        title="Revoke"
                        onClick={() => {
                          setInvites(invites.filter((x) => x.email !== i.email))
                          s.toast('Invitation revoked', i.email, 'info')
                        }}
                      >
                        <X className="size-3.5" />
                      </button>
                    </>
                  )}
                </li>
              ))}
              {!invites.length && <p className="text-[13px] text-muted">No pending invitations.</p>}
            </ul>
          </Card>
          <Card>
            <CardHeader title="Permission management" subtitle="What each project role can do" icon={ShieldCheck} />
            <div className="overflow-x-auto px-5 pb-5">
              <table className="w-full text-[12.5px]">
                <thead>
                  <tr className="text-muted">
                    <th className="py-2 text-left font-medium">Capability</th>
                    {['PM', 'Out', 'In', 'View'].map((h) => (
                      <th key={h} className="px-1 py-2 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {PERMS.map(([l, ...v]) => (
                    <tr key={l as string} className="border-t border-line">
                      <td className="py-2 pr-2 text-navy">{l as string}</td>
                      {v.map((x, i) => (
                        <td key={i} className="px-1 text-center">
                          {x ? <Check className="mx-auto size-3.5 text-ok" /> : <span className="text-slate-300">—</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 flex items-start gap-1.5 text-xs text-muted">
                <Lock className="mt-0.5 size-3 shrink-0" />
                Enforced server-side on every request. Hidden controls are a convenience, not a security boundary.
              </p>
            </div>
          </Card>
        </div>
      </div>
      <Modal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        title="Add member"
        subtitle={`Invite someone to ${p.name}`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setAddOpen(false)}>Cancel</Button>
            <Button
              disabled={!/^\S+@\S+\.\S+$/.test(newM.email)}
              onClick={() => {
                const person = people.find((x) => x.email === newM.email)
                if (person && !members.some((m) => m.personId === person.id)) {
                  s.setMembers((ms) => [...ms, { projectId: p.id, personId: person.id, role: newM.role, responsibilities: [], tasks: 0 }])
                  s.toast('Member added', `${person.name} joined as ${ROLE_LABEL[newM.role]}.`)
                } else {
                  setInvites([...invites, { email: newM.email, role: newM.role, sent: 'Just now' }])
                  s.toast('Invitation sent', newM.email)
                }
                setAddOpen(false)
                setNewM({ email: '', role: 'contributor' })
              }}
            >
              Add member
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Email or workspace member" hint="Workspace members are added immediately; others receive an invitation.">
            <Input list="ws-people" value={newM.email} onChange={(e) => setNewM({ ...newM, email: e.target.value })} placeholder="name@northwind.io" />
            <datalist id="ws-people">
              {people.filter((x) => !members.some((m) => m.personId === x.id)).map((x) => (
                <option key={x.id} value={x.email}>
                  {x.name}
                </option>
              ))}
            </datalist>
          </Field>
          <Field label="Project role">
            <Select value={newM.role} onChange={(e) => setNewM({ ...newM, role: e.target.value as MemberRole })}>
              {(['manager', 'outgoing', 'incoming', 'contributor', 'viewer'] as MemberRole[]).map((r) => (
                <option key={r} value={r}>
                  {ROLE_LABEL[r]}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </Modal>
      <ConfirmDialog
        open={!!remove}
        onClose={() => setRemove(null)}
        tone="danger"
        title="Remove member?"
        confirmLabel="Remove"
        body={
          remove && (
            <>
              {personById(remove).name} will lose access to {p.name}. Their verified findings and evidence remain in the project history.
            </>
          )
        }
        onConfirm={() => {
          s.setMembers((ms) => ms.filter((m) => !(m.projectId === p.id && m.personId === remove)))
          s.toast('Member removed', personById(remove!).name, 'info')
        }}
      />
    </>
  )
}

export function ProjectHandovers({ projectId }: { projectId: string }) {
  const router = useRouter()
  const s = useFigmaStore()
  const p = useProject(projectId)
  if (!p) return <ProjectNotFound />

  return (
    <>
      <ProjectHeader
        project={p}
        tab="handovers"
        actions={p.role === 'manager' && <Button icon={Plus} onClick={() => router.push(`/handovers/new?project=${p.id}`)}>Create handover</Button>}
      />
      <Card className="overflow-hidden">
        <HandoverTable
          items={s.handovers.filter((h) => h.projectId === p.id)}
          empty={<EmptyState icon={Workflow} title="No handovers on this project" body="Handovers created for this project will appear here." />}
        />
      </Card>
    </>
  )
}

export function ProjectActivity({ projectId }: { projectId: string }) {
  const p = useProject(projectId)
  const [type, setType] = useState('all')

  const items = useMemo(() => {
    if (!p) return []
    const short = p.name.split(' ')[0] ?? ''
    return [
      ...timeline.filter((t) => t.projectId === p.id).map((t) => ({ id: t.id, who: t.personId, what: t.title, detail: t.detail, when: t.date, kind: 'Knowledge' })),
      ...auditLogs.filter((a) => a.project.startsWith(short)).map((a) => ({ id: a.id, who: a.userId, what: a.action, detail: a.resource, when: a.time, kind: a.type })),
    ]
  }, [p])

  if (!p) return <ProjectNotFound />

  const kinds = ['all', ...Array.from(new Set(items.map((i) => i.kind)))]
  const list = items.filter((i) => type === 'all' || i.kind === type)

  return (
    <>
      <ProjectHeader project={p} tab="activity" />
      <div className="mb-4 flex flex-wrap gap-2">
        {kinds.map((k) => (
          <button
            key={k}
            onClick={() => setType(k)}
            className={cn(
              'rounded-full border px-3 py-1 text-[13px] font-medium transition',
              type === k ? 'border-brand bg-tint text-brand' : 'border-line bg-white text-muted hover:text-navy'
            )}
          >
            {k === 'all' ? 'All activity' : k}
          </button>
        ))}
      </div>
      <Card className="p-5">
        {!list.length ? (
          <EmptyState icon={Activity} title="No activity yet" body="Activity appears as members work and sources sync." />
        ) : (
          <ol className="space-y-0">
            {list.map((i, idx) => (
              <li key={i.id} className="relative flex gap-3 pb-5">
                {idx < list.length - 1 && <span className="absolute left-[13px] top-8 h-[calc(100%-24px)] w-px bg-line" />}
                {i.who === 'system' ? (
                  <span className="flex size-7 items-center justify-center rounded-full bg-slate-100 text-[10px] font-semibold text-slate-500">SYS</span>
                ) : (
                  <Avatar id={i.who} size={28} />
                )}
                <div className="flex-1">
                  <p className="text-[13px] text-navy">
                    <span className="font-medium">{i.who === 'system' ? 'System' : personById(i.who).name}</span> · {i.what}
                  </p>
                  <p className="text-xs text-muted">{i.detail}</p>
                </div>
                <div className="text-right">
                  <Badge tone="gray">{i.kind}</Badge>
                  <p className="mt-1 text-[11px] text-slate-400">{i.when}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </Card>
    </>
  )
}

function EnsureFigmaStore({ children }: { children: ReactNode }) {
  const ctx = useContext(FigmaCtx)
  if (!ctx) {
    return <FigmaStoreProvider>{children}</FigmaStoreProvider>
  }
  return <>{children}</>
}

export interface ProjectsPageProps {
  view?: 'list' | 'new' | 'detail' | 'team' | 'handovers' | 'activity'
  id?: string
}

function ProjectsPageInner({ view = 'list', id }: ProjectsPageProps) {
  const params = useParams()
  const s = useFigmaStore()
  const rawId = id || (Array.isArray(params?.id) ? params.id[0] : (params?.id as string | undefined))
  const pid = (rawId || s.currentProject?.id || 'atlas') as string

  return (
    <>
      {view === 'list' && <ProjectsList />}
      {view === 'new' && <CreateProject />}
      {view === 'detail' && <ProjectOverview projectId={pid} />}
      {view === 'team' && <ProjectTeam projectId={pid} />}
      {view === 'handovers' && <ProjectHandovers projectId={pid} />}
      {view === 'activity' && <ProjectActivity projectId={pid} />}
    </>
  )
}

export function ProjectsPage(props: ProjectsPageProps) {
  return (
    <EnsureFigmaStore>
      <ProjectsPageInner {...props} />
    </EnsureFigmaStore>
  )
}

export default ProjectsPage
