import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import {
  decisions, dependencies, initialHandovers, projectMembers, type ProjectMember, initialJobs, initialNotifications, initialProjects, initialSources, risks, tasks,
  ROLE_LABEL, type Handover, type IngestJob, type Notification, type Project, type ProjectRole, type Source, type Verification,
} from './data'

export interface Toast { id: number; title: string; body?: string; tone: 'success' | 'info' | 'error' }
export interface Comment { by: string; text: string; time: string }

export const WORKSPACES = [
  { id: 'northwind', name: 'Northwind Labs', plan: 'Enterprise · sample data' },
  { id: 'sandbox', name: 'Acme Sandbox', plan: 'Trial · empty workspace' },
]

function useStoreValue() {
  const [authed, setAuthed] = useState(true)
  const [workspaceId, setWorkspaceId] = useState('northwind')
  const [projects, setProjects] = useState<Project[]>(initialProjects)
  const [currentProjectId, setCurrentProjectId] = useState('atlas')
  const [members, setMembers] = useState<ProjectMember[]>(projectMembers)
  const [sources, setSources] = useState<Source[]>(initialSources)
  const [handovers, setHandovers] = useState<Handover[]>(initialHandovers)
  const [jobs, setJobs] = useState<IngestJob[]>(initialJobs)
  const [notifications, setNotifications] = useState<Notification[]>(initialNotifications)
  const [verif, setVerif] = useState<Record<string, Verification>>(() => {
    const m: Record<string, Verification> = {}
    for (const f of [...decisions, ...tasks, ...risks, ...dependencies]) m[f.id] = f.verification
    return m
  })
  const [edits, setEdits] = useState<Record<string, string>>({})
  const [comments, setComments] = useState<Record<string, Comment[]>>({
    'd-retention': [{ by: 'james', text: 'I believe Lucas reverted this after the review. Need confirmation.', time: 'Jun 17' }],
    'r-retry': [{ by: 'priya', text: 'Connection pool metrics look normal for that window, so it was likely the acquirer.', time: 'Jun 16' }],
  })
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

type Store = ReturnType<typeof useStoreValue>
const Ctx = createContext<Store | null>(null)

export function StoreProvider({ children }: { children: ReactNode }) {
  const value = useStoreValue()
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useStore() {
  const v = useContext(Ctx)
  if (!v) throw new Error('useStore outside provider')
  return v
}
