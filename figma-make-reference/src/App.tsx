import type { ReactNode } from 'react'
import { StoreProvider, useStore } from '@/lib/store'
import { matchRoute, useRoute } from '@/lib/router'
import { Shell, Toaster } from '@/components/Shell'
import { Login, Signup, ForgotPassword, Onboarding } from '@/pages/auth'
import { Dashboard } from '@/pages/dashboard'
import { ProjectsList, CreateProject, ProjectOverview, ProjectTeam, ProjectHandovers, ProjectActivity } from '@/pages/projects'
import { DataSources, SourceDetail, EvidenceLibrary, EvidenceDetail, Ingestion, KnowledgeExplorer } from '@/pages/knowledge'
import { IntelligenceOverview, Decisions, Tasks, Risks, Dependencies, Timeline } from '@/pages/intelligence'
import { AllHandovers, CreateHandover, HandoverWorkspace, PublishedHandovers, ReceivedHandovers } from '@/pages/handovers'
import { Review, Report, RecipientWorkspace, Assistant } from '@/pages/handover-detail'
import { SettingsTeam, Notifications, AuditLogs, Settings, Profile } from '@/pages/admin'
import { BrandSystem, DesignSystem, Flows } from '@/pages/system'
import { Landing } from '@/pages/landing'
import { EmptyState, Button } from '@/components/ui'
import { Compass } from 'lucide-react'
import { navigate } from '@/lib/router'

type P = Record<string, string>
type Crumb = { label: string; to?: string }
interface RouteDef { path: string; render: (p: P) => ReactNode; crumbs: (p: P, ctx: Ctx) => Crumb[]; wide?: boolean }
interface Ctx { projectName: (id: string) => string; handoverCode: (id: string) => string; handoverProject: (id: string) => { id: string; name: string } }

const proj = (p: P, c: Ctx, ...rest: Crumb[]): Crumb[] => [{ label: 'Projects', to: '/projects' }, { label: c.projectName(p.projectId), to: `/projects/${p.projectId}` }, ...rest]
const intel = (p: P, c: Ctx, label?: string): Crumb[] => proj(p, c, { label: 'Intelligence', to: `/projects/${p.projectId}/intelligence` }, ...(label ? [{ label }] : []))
const ho = (p: P, c: Ctx, label?: string): Crumb[] => [{ label: 'Handovers', to: '/handovers' }, { label: c.handoverCode(p.handoverId), to: `/handovers/${p.handoverId}` }, ...(label ? [{ label }] : [])]

const ROUTES: RouteDef[] = [
  { path: '/dashboard', render: () => <Dashboard />, crumbs: () => [{ label: 'Dashboard' }] },
  { path: '/projects', render: () => <ProjectsList />, crumbs: () => [{ label: 'My Projects' }] },
  { path: '/projects/new', render: () => <CreateProject />, crumbs: () => [{ label: 'Projects', to: '/projects' }, { label: 'Create project' }] },
  { path: '/projects/:projectId', render: (p) => <ProjectOverview projectId={p.projectId} />, crumbs: (p, c) => proj(p, c) },
  { path: '/projects/:projectId/team', render: (p) => <ProjectTeam projectId={p.projectId} />, crumbs: (p, c) => proj(p, c, { label: 'Team' }) },
  { path: '/projects/:projectId/handovers', render: (p) => <ProjectHandovers projectId={p.projectId} />, crumbs: (p, c) => proj(p, c, { label: 'Handovers' }) },
  { path: '/projects/:projectId/activity', render: (p) => <ProjectActivity projectId={p.projectId} />, crumbs: (p, c) => proj(p, c, { label: 'Activity' }) },
  { path: '/projects/:projectId/sources', render: (p) => <DataSources projectId={p.projectId} />, crumbs: (p, c) => proj(p, c, { label: 'Data sources' }) },
  { path: '/projects/:projectId/sources/:sourceId', render: (p) => <SourceDetail projectId={p.projectId} sourceId={p.sourceId} />, crumbs: (p, c) => proj(p, c, { label: 'Data sources', to: `/projects/${p.projectId}/sources` }, { label: 'Source details' }) },
  { path: '/projects/:projectId/evidence', render: (p) => <EvidenceLibrary projectId={p.projectId} />, crumbs: (p, c) => proj(p, c, { label: 'Evidence' }), wide: true },
  { path: '/projects/:projectId/evidence/:evidenceId', render: (p) => <EvidenceDetail projectId={p.projectId} evidenceId={p.evidenceId} />, crumbs: (p, c) => proj(p, c, { label: 'Evidence', to: `/projects/${p.projectId}/evidence` }, { label: 'Detail' }) },
  { path: '/projects/:projectId/ingestion', render: (p) => <Ingestion projectId={p.projectId} />, crumbs: (p, c) => proj(p, c, { label: 'Ingestion' }) },
  { path: '/projects/:projectId/knowledge', render: (p) => <KnowledgeExplorer projectId={p.projectId} />, crumbs: (p, c) => proj(p, c, { label: 'Knowledge Explorer' }), wide: true },
  { path: '/projects/:projectId/intelligence', render: (p) => <IntelligenceOverview projectId={p.projectId} />, crumbs: (p, c) => intel(p, c) },
  { path: '/projects/:projectId/intelligence/decisions', render: (p) => <Decisions projectId={p.projectId} />, crumbs: (p, c) => intel(p, c, 'Decisions') },
  { path: '/projects/:projectId/intelligence/tasks', render: (p) => <Tasks projectId={p.projectId} />, crumbs: (p, c) => intel(p, c, 'Tasks'), wide: true },
  { path: '/projects/:projectId/intelligence/risks', render: (p) => <Risks projectId={p.projectId} />, crumbs: (p, c) => intel(p, c, 'Risks') },
  { path: '/projects/:projectId/intelligence/dependencies', render: (p) => <Dependencies projectId={p.projectId} />, crumbs: (p, c) => intel(p, c, 'Dependencies') },
  { path: '/projects/:projectId/intelligence/timeline', render: (p) => <Timeline projectId={p.projectId} />, crumbs: (p, c) => intel(p, c, 'Timeline') },
  { path: '/handovers', render: () => <AllHandovers />, crumbs: () => [{ label: 'All Handovers' }], wide: true },
  { path: '/handovers/new', render: () => <CreateHandover />, crumbs: () => [{ label: 'Handovers', to: '/handovers' }, { label: 'Create handover' }] },
  { path: '/handovers/published', render: () => <PublishedHandovers />, crumbs: () => [{ label: 'Handovers', to: '/handovers' }, { label: 'Published' }] },
  { path: '/handovers/received', render: () => <ReceivedHandovers />, crumbs: () => [{ label: 'Handovers', to: '/handovers' }, { label: 'Received' }] },
  { path: '/handovers/:handoverId', render: (p) => <HandoverWorkspace id={p.handoverId} />, crumbs: (p, c) => ho(p, c) },
  { path: '/handovers/:handoverId/review', render: (p) => <Review id={p.handoverId} />, crumbs: (p, c) => ho(p, c, 'Review & verification'), wide: true },
  { path: '/handovers/:handoverId/report', render: (p) => <Report id={p.handoverId} />, crumbs: (p, c) => ho(p, c, 'Report') },
  { path: '/handovers/:handoverId/recipient', render: (p) => <RecipientWorkspace id={p.handoverId} />, crumbs: (p, c) => [{ label: 'Received', to: '/handovers/received' }, { label: c.handoverCode(p.handoverId) }] },
  { path: '/handovers/:handoverId/assistant', render: (p) => <Assistant id={p.handoverId} />, crumbs: (p, c) => [{ label: 'Handovers', to: '/handovers' }, { label: c.handoverCode(p.handoverId), to: `/handovers/${p.handoverId}` }, { label: 'Assistant' }], wide: true },
  { path: '/notifications', render: () => <Notifications />, crumbs: () => [{ label: 'Notifications' }] },
  { path: '/settings', render: () => <Settings />, crumbs: () => [{ label: 'Settings' }] },
  { path: '/settings/team', render: () => <SettingsTeam />, crumbs: () => [{ label: 'Settings', to: '/settings' }, { label: 'Team management' }] },
  { path: '/settings/audit-logs', render: () => <AuditLogs />, crumbs: () => [{ label: 'Settings', to: '/settings' }, { label: 'Audit logs' }], wide: true },
  { path: '/settings/profile', render: () => <Profile />, crumbs: () => [{ label: 'Settings', to: '/settings' }, { label: 'Profile & account' }] },
  { path: '/design-system', render: () => <DesignSystem />, crumbs: () => [{ label: 'Design system' }] },
  { path: '/brand', render: () => <BrandSystem />, crumbs: () => [{ label: 'Design system', to: '/design-system' }, { label: '3D Brand & Experience System' }] },
  { path: '/flows', render: () => <Flows />, crumbs: () => [{ label: 'Prototype flows' }] },
]

function Router() {
  const { path } = useRoute()
  const s = useStore()
  if (path === '/' || path === '/home') return <Landing />
  if (path === '/login') return <Login />
  if (path === '/signup') return <Signup />
  if (path === '/forgot-password') return <ForgotPassword />
  if (path === '/onboarding') return <Onboarding />
  const ctx: Ctx = {
    projectName: (id) => s.allProjects.find((p) => p.id === id)?.name ?? 'Project',
    handoverCode: (id) => s.handovers.find((h) => h.id === id)?.code ?? 'Handover',
    handoverProject: (id) => { const h = s.handovers.find((x) => x.id === id); const p = s.allProjects.find((x) => x.id === h?.projectId); return { id: p?.id ?? '', name: p?.name ?? '' } },
  }
  for (const r of ROUTES) {
    const params = matchRoute(r.path, path)
    if (params) return <Shell crumbs={r.crumbs(params, ctx)} wide={r.wide}>{r.render(params)}</Shell>
  }
  return <Shell crumbs={[{ label: 'Not found' }]}><EmptyState icon={Compass} title="Page not found" body="The page you're looking for doesn't exist or has moved." action={<Button onClick={() => navigate('/dashboard')}>Go to dashboard</Button>} /></Shell>
}

export default function App() {
  return (
    <StoreProvider>
      <Router />
      <Toaster />
    </StoreProvider>
  )
}
