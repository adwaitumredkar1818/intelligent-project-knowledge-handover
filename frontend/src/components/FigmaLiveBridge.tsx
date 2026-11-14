'use client'

import { useEffect, useRef } from 'react'
import { useLiveApp } from '../context/LiveAppContext'
import { useFigmaStore } from '../lib/figmaStore'
import {
  evidence as storeEvidence,
  decisions as storeDecisions,
  tasks as storeTasks,
  risks as storeRisks,
  dependencies as storeDependencies,
  timeline as storeTimeline,
  people as storePeople,
  type Evidence,
  type Person,
  type Project,
  type Source,
  type Handover,
  type Verification,
  type SourceType,
} from '../lib/figmaStore'

export function FigmaLiveBridge() {
  const {
    user,
    projects,
    activeProject,
    sourceMappings,
    evidenceList,
    findings,
    handoverCases,
    members,
  } = useLiveApp()

  const {
    setProjects,
    switchProject,
    currentProject,
    setSources,
    setHandovers,
  } = useFigmaStore()

  const lastUserEmailRef = useRef<string>('')
  const lastMembersRef = useRef<string>('')
  const lastProjectsSyncRef = useRef<string>('')
  const lastActiveProjectSyncRef = useRef<string>('')
  const lastSourcesSyncRef = useRef<string>('')
  const lastEvidenceRef = useRef<string>('')
  const lastFindingsRef = useRef<string>('')
  const lastHandoversSyncRef = useRef<string>('')

  // 1. Sync User Profile to storePeople
  useEffect(() => {
    if (user && user.email !== lastUserEmailRef.current) {
      lastUserEmailRef.current = user.email
      const existing = storePeople.find((p) => p.id === user.id || p.email === user.email)
      const fullName = user.full_name || user.email.split('@')[0] || 'User'
      if (existing) {
        existing.name = fullName
        existing.email = user.email
      } else {
        const newPerson: Person = {
          id: user.id,
          name: fullName,
          title: 'Team Member',
          email: user.email,
          color: '#315FBA',
          wsRole: 'Owner',
          status: 'Active',
        }
        storePeople.unshift(newPerson)
      }
    }
  }, [user])

  // 2. Sync Members into storePeople
  useEffect(() => {
    if (members && members.length > 0) {
      const key = members.map((m) => m.user_id).join(',')
      if (key !== lastMembersRef.current) {
        lastMembersRef.current = key
        members.forEach((m) => {
          const name = m.user_email?.split('@')[0] || 'Member'
          if (!storePeople.some((p) => p.id === m.user_id)) {
            storePeople.push({
              id: m.user_id,
              name,
              title: m.role_name || 'Contributor',
              email: m.user_email || `${m.user_id}@handover.local`,
              color: '#299B80',
              wsRole: 'Member',
              status: 'Active',
            })
          }
        })
      }
    }
  }, [members])

  // 3. Sync Projects into store.setProjects
  useEffect(() => {
    if (projects && projects.length > 0) {
      const syncKey = projects.map((p) => `${p.id}:${p.name}:${p.status}`).join('|')
      if (syncKey !== lastProjectsSyncRef.current) {
        lastProjectsSyncRef.current = syncKey
        const mapped: Project[] = projects.map((p) => {
          const pRecord = p as unknown as Record<string, unknown>
          const category = typeof pRecord.category === 'string' ? pRecord.category : 'General'
          const role: Project['role'] = (typeof pRecord.user_role === 'string' && (pRecord.user_role === 'manager' || pRecord.user_role === 'outgoing' || pRecord.user_role === 'incoming')) ? pRecord.user_role : 'manager'
          const startDate = typeof pRecord.created_at === 'string' ? pRecord.created_at.split('T')[0]! : '2026-01-01'

          return {
            id: p.id,
            workspaceId: p.organisation_id || 'sandbox',
            name: p.name,
            code: p.name.slice(0, 4).toUpperCase(),
            description: p.description || 'Project managed in The Handover',
            category,
            status: p.status === 'archived' ? 'completed' : 'active',
            health: 92,
            ownerId: user?.id || 'maya',
            role,
            lastActivity: 'Just now',
            coverage: 85,
            startDate,
            endDate: '2026-12-31',
            color: '#315FBA',
          }
        })

        setProjects(mapped)
      }
    }
  }, [projects, user?.id, setProjects])

  // 3b. Switch active project in figma store safely
  useEffect(() => {
    if (activeProject && currentProject?.id !== activeProject.id && lastActiveProjectSyncRef.current !== activeProject.id) {
      lastActiveProjectSyncRef.current = activeProject.id
      switchProject(activeProject.id, true)
    }
  }, [activeProject?.id, currentProject?.id, switchProject])

  // 4. Sync Sources into store.setSources
  useEffect(() => {
    if (activeProject) {
      const syncKey = `${activeProject.id}:${sourceMappings?.length || 0}:${evidenceList?.length || 0}:` +
        (sourceMappings || []).map((sm) => `${sm.id}:${sm.status}:${sm.last_synced_at}`).join('|')
      if (syncKey !== lastSourcesSyncRef.current) {
        lastSourcesSyncRef.current = syncKey
        const mapped: Source[] = (sourceMappings || []).map((sm) => {
          const type = (sm.provider || 'docs') as SourceType
          const recordsCount = (evidenceList || []).filter(
            (e) => (e.provider || '').toLowerCase() === (sm.provider || '').toLowerCase() ||
                   (e.source_type || '').toLowerCase() === (sm.provider || '').toLowerCase() ||
                   (e.source_provider || '').toLowerCase() === (sm.provider || '').toLowerCase()
          ).length

          return {
            id: sm.id,
            projectId: activeProject.id,
            type,
            name: sm.external_resource_name || sm.provider,
            account: sm.external_resource_key || 'authorized',
            status: sm.status === 'failed' ? 'error' : sm.status === 'syncing' ? 'syncing' : 'connected',
            lastSync: sm.last_synced_at ? new Date(sm.last_synced_at).toLocaleTimeString() : 'Recent',
            records: recordsCount,
            scope: [sm.resource_type || 'repository'],
            frequency: 'Real-time / Webhook',
            volume: 'Normal',
          }
        })

        // Check for uploaded documents in evidenceList
        const uploadedDocs = (evidenceList || []).filter((e) => {
          const cat = (e.category || '').toLowerCase()
          const prov = (e.provider || '').toLowerCase()
          const st = (e.source_type || '').toLowerCase()
          const sp = (e.source_provider || '').toLowerCase()
          return (
            cat.includes('pdf') ||
            cat.includes('docx') ||
            prov.includes('upload') ||
            st.includes('upload') ||
            sp.includes('upload')
          )
        })

        if (uploadedDocs.length > 0) {
          mapped.push({
            id: `docs-${activeProject.id}`,
            projectId: activeProject.id,
            type: 'docs',
            name: 'Uploaded Specifications & Runbooks',
            account: `${uploadedDocs.length} documents`,
            status: 'connected',
            lastSync: 'OCR processed',
            records: uploadedDocs.length,
            scope: ['PDF & DOCX Architecture specs', 'Runbooks'],
            frequency: 'On-demand upload',
            volume: `${uploadedDocs.length} files`,
          })
        }

        setSources(mapped)
      }
    }
  }, [sourceMappings, evidenceList, activeProject?.id, setSources])

  // 5. Sync Evidence into global `evidence` array in figmaStore
  useEffect(() => {
    if (evidenceList && activeProject) {
      const syncKey = `${activeProject.id}:` + evidenceList.map((e) => `${e.id}:${e.indexing_status}`).join('|')
      if (syncKey !== lastEvidenceRef.current) {
        lastEvidenceRef.current = syncKey
        const mapped: Evidence[] = evidenceList.map((e) => {
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
            projectId: e.project_id || activeProject.id,
            type,
            title: e.title || 'Evidence Record',
            sourceId: e.provider || 'docs',
            authorId: e.author_name || user?.id || 'system',
            date: e.source_created_at ? e.source_created_at.split('T')[0]! : 'Today',
            memberId: user?.id || 'maya',
            processing: e.indexing_status === 'indexed' ? 'processed' : e.indexing_status === 'failed' ? 'failed' : 'processing',
            verification,
            ref: e.id.slice(0, 8),
            content: 'Decrypted source content available in Evidence Workspace.',
            extracted: [],
          }
        })

        // Update storeEvidence in-place
        storeEvidence.length = 0
        mapped.forEach((m) => storeEvidence.push(m))
      }
    }
  }, [evidenceList, activeProject?.id, user?.id])

  // 6. Sync Findings into decisions, tasks, risks, dependencies in figmaStore
  useEffect(() => {
    if (findings && activeProject) {
      const syncKey = `${activeProject.id}:` + findings.map((f) => `${f.id}:${f.review_status}`).join('|')
      if (syncKey !== lastFindingsRef.current) {
        lastFindingsRef.current = syncKey
        storeDecisions.length = 0
        storeTasks.length = 0
        storeRisks.length = 0
        storeDependencies.length = 0
        storeTimeline.length = 0

        findings.forEach((f) => {
          let verification: Verification = 'needs_review'
          if (f.review_status === 'approved') verification = 'verified'
          else if (f.review_status === 'rejected') verification = 'rejected'
          else if (f.review_status === 'disputed') verification = 'conflicting'

          const citations = f.citations ? f.citations.map((c: { evidence_id: string }) => c.evidence_id) : []

          const base = {
            id: f.id,
            projectId: f.project_id || activeProject.id,
            title: f.title,
            summary: f.summary,
            ownerId: user?.id || 'maya',
            date: f.extracted_at ? f.extracted_at.split('T')[0]! : '2026-03-01',
            confidence: Math.round((f.confidence_score || 0.85) * 100),
            verification,
            evidenceIds: citations,
          }

          const domain = (f.knowledge_domain || '').toUpperCase()

          if (domain.includes('DECISION')) {
            storeDecisions.push({
              ...base,
              reasoning: f.summary,
              discussions: [],
            })
            storeTimeline.push({
              id: `tl-${f.id}`,
              projectId: base.projectId,
              date: base.date,
              type: 'decision',
              title: f.title,
              detail: f.summary,
              personId: base.ownerId,
            })
          } else if (domain.includes('WORK_STATUS') || domain.includes('OWNERSHIP')) {
            storeTasks.push({
              ...base,
              priority: 'High',
              status: 'In progress',
              due: '2026-04-15',
              history: [],
            })
            storeTimeline.push({
              id: `tl-${f.id}`,
              projectId: base.projectId,
              date: base.date,
              type: 'task',
              title: f.title,
              detail: f.summary,
              personId: base.ownerId,
            })
          } else if (domain.includes('RISK') || domain.includes('BLOCKER')) {
            storeRisks.push({
              ...base,
              severity: 'High',
              impact: f.summary,
              component: 'Architecture',
              mitigation: ['Address during handover verification'],
              resolution: 'Open',
            })
          } else if (domain.includes('DEPENDENCY')) {
            storeDependencies.push({
              ...base,
              depType: 'Technical',
              from: f.title.split('->')[0]?.trim() || f.title,
              to: f.title.split('->')[1]?.trim() || 'Core Services',
              blocking: true,
            })
          } else {
            storeDecisions.push({
              ...base,
              reasoning: f.summary,
              discussions: [],
            })
          }
        })
      }
    }
  }, [findings, activeProject?.id, user?.id])

  // 7. Sync Handovers into store.setHandovers
  useEffect(() => {
    if (handoverCases && activeProject) {
      const syncKey = `${activeProject.id}:` + handoverCases.map((hc) => `${hc.id}:${hc.status}:${hc.updated_at}`).join('|')
      if (syncKey !== lastHandoversSyncRef.current) {
        lastHandoversSyncRef.current = syncKey
        const mapped: Handover[] = handoverCases.map((hc) => ({
          id: hc.id,
          code: `HO-${hc.id.slice(0, 4).toUpperCase()}`,
          projectId: hc.project_id || activeProject.id,
          outgoingId: hc.outgoing_owner_user_id || user?.id || 'maya',
          incomingId: hc.incoming_owner_user_id || 'james',
          created: hc.created_at ? hc.created_at.split('T')[0]! : '2026-03-01',
          updated: hc.updated_at ? hc.updated_at.split('T')[0]! : '2026-03-01',
          status: (hc.status === 'draft' || hc.status === 'in_progress' || hc.status === 'pending_review' || hc.status === 'approved' || hc.status === 'published' || hc.status === 'completed') ? hc.status : 'draft',
          progress: hc.status === 'approved' ? 100 : hc.status === 'in_progress' ? 65 : 20,
          due: '2026-04-30',
          scope: hc.title || 'Project Handover Package',
          access: 'Active',
        }))
        setHandovers(mapped)
      }
    }
  }, [handoverCases, activeProject?.id, user?.id, setHandovers])

  return null
}
