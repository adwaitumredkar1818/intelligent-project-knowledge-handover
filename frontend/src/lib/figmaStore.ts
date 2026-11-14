// figmaStore.ts — Figma prototype data adapter for the production frontend.
// All Northwind Labs fixture data lives here. Production builds replace each
// collection with live backend data once the respective API module is ready.

'use client'

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import React from 'react'

// ─── Types ───────────────────────────────────────────────────────────────────

export type ProjectRole = 'manager' | 'outgoing' | 'incoming'
export type MemberRole = ProjectRole | 'contributor' | 'viewer'
export type Verification = 'verified' | 'needs_review' | 'rejected' | 'conflicting' | 'insufficient'
export type SourceType = 'github' | 'jira' | 'slack' | 'docs' | 'confluence' | 'gdrive'
export type HandoverStatus = 'draft' | 'in_progress' | 'pending_review' | 'approved' | 'published' | 'completed'
export type EvidenceType = 'commit' | 'pr' | 'issue' | 'message' | 'pdf' | 'docx'

export const ROLE_LABEL: Record<MemberRole, string> = {
  manager: 'Project Manager',
  outgoing: 'Outgoing Member',
  incoming: 'Incoming Member',
  contributor: 'Contributor',
  viewer: 'Viewer',
}

export interface Person {
  id: string
  name: string
  title: string
  email: string
  color: string
  wsRole: 'Owner' | 'Admin' | 'Member'
  status: 'Active' | 'Invited' | 'Suspended'
}

export const ME = 'maya'

export const people: Person[] = [
  { id: 'maya', name: 'Maya Chen', title: 'Engineering Manager', email: 'maya.chen@northwind.io', color: '#315FBA', wsRole: 'Owner', status: 'Active' },
  { id: 'james', name: 'James Okafor', title: 'Staff Backend Engineer', email: 'james.okafor@northwind.io', color: '#299B80', wsRole: 'Member', status: 'Active' },
  { id: 'priya', name: 'Priya Nair', title: 'Senior Backend Engineer', email: 'priya.nair@northwind.io', color: '#8B78C9', wsRole: 'Member', status: 'Active' },
  { id: 'lucas', name: 'Lucas Berg', title: 'Platform Engineer', email: 'lucas.berg@northwind.io', color: '#B45309', wsRole: 'Admin', status: 'Active' },
  { id: 'sofia', name: 'Sofia Alvarez', title: 'Mobile Lead', email: 'sofia.alvarez@northwind.io', color: '#B5728E', wsRole: 'Member', status: 'Active' },
  { id: 'daniel', name: 'Daniel Kim', title: 'Mobile Engineer', email: 'daniel.kim@northwind.io', color: '#0369A1', wsRole: 'Member', status: 'Active' },
  { id: 'aisha', name: 'Aisha Rahman', title: 'QA Engineer', email: 'aisha.rahman@northwind.io', color: '#4D7C0F', wsRole: 'Member', status: 'Active' },
  { id: 'tom', name: 'Tom Whitfield', title: 'Product Manager', email: 'tom.whitfield@northwind.io', color: '#9333EA', wsRole: 'Admin', status: 'Active' },
  { id: 'elena', name: 'Elena Petrova', title: 'Data Engineer', email: 'elena.petrova@northwind.io', color: '#C2410C', wsRole: 'Member', status: 'Active' },
  { id: 'omar', name: 'Omar Haddad', title: 'Analytics Engineer', email: 'omar.haddad@northwind.io', color: '#1E40AF', wsRole: 'Member', status: 'Active' },
  { id: 'grace', name: 'Grace Liu', title: 'Security Engineer', email: 'grace.liu@northwind.io', color: '#475569', wsRole: 'Member', status: 'Invited' },
]

export const personById = (id?: string): Person => people.find((p) => p.id === id) ?? people[0]!
export const initials = (name: string) => name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()

export interface Project {
  id: string
  workspaceId: string
  name: string
  code: string
  description: string
  category: string
  status: 'active' | 'at_risk' | 'planning' | 'completed'
  health: number
  ownerId: string
  role: ProjectRole
  lastActivity: string
  coverage: number
  startDate: string
  endDate: string
  color: string
}

export const initialProjects: Project[] = []

export interface ProjectMember {
  projectId: string
  personId: string
  role: MemberRole
  responsibilities: string[]
  tasks: number
}

export const projectMembers: ProjectMember[] = []

export interface Source {
  id: string
  projectId: string
  type: SourceType
  name: string
  account: string
  status: 'connected' | 'syncing' | 'error' | 'disconnected'
  lastSync: string
  records: number
  scope: string[]
  frequency: string
  volume: string
}

export const initialSources: Source[] = []

export const SOURCE_META: Record<SourceType, { label: string; description: string }> = {
  github: { label: 'GitHub', description: 'Repositories, commits, pull requests, reviews and code ownership.' },
  jira: { label: 'Jira', description: 'Issues, sprints, epics, assignees and status history.' },
  slack: { label: 'Slack', description: 'Selected public channels and threads relevant to the project.' },
  docs: { label: 'PDF & DOCX uploads', description: 'Architecture records, runbooks, specs and contracts.' },
  confluence: { label: 'Confluence', description: 'Spaces and pages containing project documentation.' },
  gdrive: { label: 'Google Drive', description: 'Authorised shared folders with project documents.' },
}

export interface Evidence {
  id: string
  projectId: string
  type: EvidenceType
  title: string
  sourceId: string
  authorId: string
  date: string
  memberId: string
  processing: 'processed' | 'processing' | 'queued' | 'failed'
  verification: Verification
  ref: string
  content: string
  extracted: string[]
}

export const evidence: Evidence[] = []

export interface FindingBase {
  id: string
  projectId: string
  title: string
  summary: string
  ownerId: string
  date: string
  confidence: number
  verification: Verification
  evidenceIds: string[]
}
export interface Decision extends FindingBase { reasoning: string; discussions: string[] }
export interface Task extends FindingBase { priority: 'Critical' | 'High' | 'Medium' | 'Low'; status: 'To do' | 'In progress' | 'Blocked' | 'Done'; due: string; history: { personId: string; date: string; note: string }[] }
export interface Risk extends FindingBase { severity: 'Critical' | 'High' | 'Medium' | 'Low'; impact: string; component: string; mitigation: string[]; resolution: 'Open' | 'Mitigating' | 'Resolved' }
export interface Dependency extends FindingBase { depType: 'Technical' | 'Task' | 'External'; from: string; to: string; blocking: boolean }

export const decisions: Decision[] = []
export const tasks: Task[] = []
export const risks: Risk[] = []
export const dependencies: Dependency[] = []

export interface Gap { id: string; projectId: string; question: string; context: string; askedOf: string }
export const gaps: Gap[] = []

export interface TimelineEvent { id: string; projectId: string; date: string; type: 'milestone' | 'commit' | 'pr' | 'decision' | 'task' | 'discussion' | 'ownership' | 'event'; title: string; detail: string; personId: string; evidenceId?: string }
export const timeline: TimelineEvent[] = []

export interface Handover {
  id: string
  code: string
  projectId: string
  outgoingId: string
  incomingId: string
  created: string
  updated: string
  status: HandoverStatus
  progress: number
  due: string
  scope: string
  publishedOn?: string
  access?: 'Active' | 'Revoked' | 'Expires Jul 31'
  acknowledgedOn?: string
}

export const initialHandovers: Handover[] = []

export const HANDOVER_STATUS_LABEL: Record<HandoverStatus, string> = {
  draft: 'Draft',
  in_progress: 'In progress',
  pending_review: 'Pending review',
  approved: 'Approved',
  published: 'Published',
  completed: 'Completed',
}

export const STAGES: HandoverStatus[] = ['draft', 'in_progress', 'pending_review', 'approved', 'published', 'completed']

export interface Notification { id: string; type: 'invitation' | 'review' | 'approval' | 'ingestion' | 'integration' | 'project'; title: string; body: string; time: string; read: boolean; link: string; group: 'Today' | 'Yesterday' | 'Earlier' }
export const initialNotifications: Notification[] = []

export interface AuditLog { id: string; userId: string; action: string; resource: string; project: string; time: string; type: 'Access' | 'Handover' | 'Integration' | 'Verification' | 'Membership' | 'Settings' }
export const auditLogs: AuditLog[] = []

export interface IngestJob { id: string; projectId: string; sourceId: string; started: string; records: number; status: 'succeeded' | 'running' | 'failed' | 'queued'; duration: string; error?: string }
export const initialJobs: IngestJob[] = []

export const architecture: Record<string, { layer: string; items: string[] }[]> = {}

export const activityTrend: { label: string; evidence: number; findings: number }[] = []

// ─── Store (React Context + useState, Next.js compatible) ─────────────────────

export interface Toast { id: number; title: string; body?: string; tone: 'success' | 'info' | 'error' }
export interface Comment { by: string; text: string; time: string }

export const WORKSPACES = [
  { id: 'sandbox', name: 'Workspace', plan: 'Active workspace' },
]

function useStoreValue() {
  const [authed, setAuthed] = useState(true)
  const [workspaceId, setWorkspaceId] = useState('sandbox')
  const [projects, setProjects] = useState<Project[]>(initialProjects)
  const [currentProjectId, setCurrentProjectId] = useState('')
  const [members, setMembers] = useState<ProjectMember[]>(projectMembers)
  const [sources, setSources] = useState<Source[]>(initialSources)
  const [handovers, setHandovers] = useState<Handover[]>(initialHandovers)
  const [jobs, setJobs] = useState<IngestJob[]>(initialJobs)
  const [notifications, setNotifications] = useState<Notification[]>(initialNotifications)
  const [verif, setVerif] = useState<Record<string, Verification>>(() => ({}))
  const [edits, setEdits] = useState<Record<string, string>>({})
  const [comments, setComments] = useState<Record<string, Comment[]>>({})
  const [gapAnswers, setGapAnswers] = useState<Record<string, string>>({})
  const [toasts, setToasts] = useState<Toast[]>([])
  const [collapsed, setCollapsed] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [perspective, setPerspective] = useState<Record<string, ProjectRole>>({})

  const toast = useCallback((title: string, body?: string, tone: Toast['tone'] = 'success') => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, title, body, tone }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200)
  }, [])

  const wsProjects = useMemo(() => projects.filter((p) => p.workspaceId === workspaceId), [projects, workspaceId])
  const currentProject = wsProjects.find((p) => p.id === currentProjectId) ?? wsProjects[0]
  const wsHandovers = useMemo(() => handovers.filter((h) => wsProjects.some((p) => p.id === h.projectId)), [handovers, wsProjects])

  const switchProject = useCallback(
    (id: string, silent = false) => {
      setCurrentProjectId(id)
      const p = projects.find((x) => x.id === id)
      if (p && !silent && id !== currentProjectId) toast(`Switched to ${p.name}`, `Your role here: ${ROLE_LABEL[p.role]}. Navigation and permissions updated.`, 'info')
    },
    [projects, currentProjectId, toast],
  )

  return {
    authed, setAuthed, workspaceId, setWorkspaceId, projects: wsProjects, allProjects: projects, setProjects, currentProject, switchProject,
    members, setMembers, sources, setSources, handovers: wsHandovers, setHandovers, jobs, setJobs, notifications, setNotifications,
    verif, setVerif, edits, setEdits, comments, setComments, gapAnswers, setGapAnswers, toasts, toast,
    collapsed, setCollapsed, paletteOpen, setPaletteOpen, perspective, setPerspective,
    updateHandover: (id: string, patch: Partial<Handover>) => setHandovers((hs) => hs.map((h) => (h.id === id ? { ...h, ...patch } : h))),
    projectRole: (projectId: string): ProjectRole => projects.find((p) => p.id === projectId)?.role ?? 'incoming',
  }
}

export type Store = ReturnType<typeof useStoreValue>
export const FigmaCtx = createContext<Store | null>(null)

export function FigmaStoreProvider({ children }: { children: ReactNode }) {
  const value = useStoreValue()
  return React.createElement(FigmaCtx.Provider, { value }, children)
}

export function useFigmaStore() {
  const v = useContext(FigmaCtx)
  if (!v) throw new Error('useFigmaStore must be used inside FigmaStoreProvider')
  return v
}

// Alias for backward compat with figma component imports
export { useFigmaStore as useStore }
export { FigmaStoreProvider as StoreProvider }
