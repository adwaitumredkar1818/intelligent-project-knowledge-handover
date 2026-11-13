// Sample prototype content. Production builds replace every collection here with live backend data.

export type ProjectRole = 'manager' | 'outgoing' | 'incoming'
export type MemberRole = ProjectRole | 'contributor' | 'viewer'
export type Verification = 'verified' | 'needs_review' | 'rejected' | 'conflicting' | 'insufficient'
export type SourceType = 'github' | 'jira' | 'slack' | 'docs' | 'confluence' | 'gdrive'
export type HandoverStatus = 'draft' | 'in_progress' | 'pending_review' | 'approved' | 'published' | 'completed'

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

export const personById = (id?: string) => people.find((p) => p.id === id) ?? people[0]
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

export const initialProjects: Project[] = [
  { id: 'atlas', workspaceId: 'northwind', name: 'Atlas Payments Platform', code: 'PAY', description: 'Core payments ledger, settlement and acquirer integrations serving 1,200 merchants across EU and UK.', category: 'Backend platform', status: 'active', health: 82, ownerId: 'maya', role: 'manager', lastActivity: '12 min ago', coverage: 78, startDate: '2024-02-05', endDate: '2025-11-28', color: '#315FBA' },
  { id: 'orion', workspaceId: 'northwind', name: 'Orion Mobile App', code: 'ORN', description: 'Customer-facing React Native app for merchant onboarding, payouts and dispute management.', category: 'Mobile', status: 'at_risk', health: 64, ownerId: 'sofia', role: 'outgoing', lastActivity: '1 h ago', coverage: 61, startDate: '2024-06-10', endDate: '2025-09-30', color: '#B5728E' },
  { id: 'helix', workspaceId: 'northwind', name: 'Helix Data Pipeline', code: 'HLX', description: 'Event ingestion and analytics warehouse powering finance reporting and merchant insights.', category: 'Data & analytics', status: 'active', health: 88, ownerId: 'tom', role: 'incoming', lastActivity: '3 h ago', coverage: 84, startDate: '2023-11-01', endDate: '2025-12-15', color: '#299B80' },
  { id: 'nova', workspaceId: 'northwind', name: 'Nova Design System', code: 'NVA', description: 'Shared component library and tokens for all Northwind web surfaces.', category: 'Design system', status: 'planning', health: 0, ownerId: 'maya', role: 'manager', lastActivity: '2 days ago', coverage: 0, startDate: '2025-06-02', endDate: '2026-01-30', color: '#8B78C9' },
]

export interface ProjectMember {
  projectId: string
  personId: string
  role: MemberRole
  responsibilities: string[]
  tasks: number
}

export const projectMembers: ProjectMember[] = [
  { projectId: 'atlas', personId: 'maya', role: 'manager', responsibilities: ['Delivery & roadmap', 'Handover approvals'], tasks: 2 },
  { projectId: 'atlas', personId: 'james', role: 'outgoing', responsibilities: ['Settlement service', 'Ledger schema migrations', 'Acquirer credential rotation'], tasks: 6 },
  { projectId: 'atlas', personId: 'priya', role: 'incoming', responsibilities: ['Settlement service (from Jul 1)'], tasks: 1 },
  { projectId: 'atlas', personId: 'lucas', role: 'outgoing', responsibilities: ['Kafka cluster operations', 'CI pipelines'], tasks: 3 },
  { projectId: 'atlas', personId: 'omar', role: 'incoming', responsibilities: ['Kafka cluster operations (shadowing)'], tasks: 0 },
  { projectId: 'atlas', personId: 'aisha', role: 'contributor', responsibilities: ['Refunds regression suite'], tasks: 4 },
  { projectId: 'atlas', personId: 'grace', role: 'viewer', responsibilities: ['PCI DSS evidence review'], tasks: 0 },
  { projectId: 'orion', personId: 'sofia', role: 'manager', responsibilities: ['Mobile delivery', 'App store releases'], tasks: 3 },
  { projectId: 'orion', personId: 'maya', role: 'outgoing', responsibilities: ['Offline sync architecture', 'Release train ownership'], tasks: 4 },
  { projectId: 'orion', personId: 'daniel', role: 'incoming', responsibilities: ['Offline sync (from Jul 8)'], tasks: 2 },
  { projectId: 'orion', personId: 'tom', role: 'contributor', responsibilities: ['Product requirements'], tasks: 1 },
  { projectId: 'helix', personId: 'tom', role: 'manager', responsibilities: ['Data platform roadmap'], tasks: 1 },
  { projectId: 'helix', personId: 'elena', role: 'outgoing', responsibilities: ['Dagster orchestration', 'BigQuery cost management'], tasks: 5 },
  { projectId: 'helix', personId: 'maya', role: 'incoming', responsibilities: ['Dagster orchestration (from Jun 23)'], tasks: 2 },
  { projectId: 'helix', personId: 'omar', role: 'contributor', responsibilities: ['dbt models', 'Finance dashboards'], tasks: 3 },
  { projectId: 'nova', personId: 'maya', role: 'manager', responsibilities: ['Project setup'], tasks: 0 },
]

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

export const initialSources: Source[] = [
  { id: 'src-gh-atlas', projectId: 'atlas', type: 'github', name: 'GitHub', account: 'northwind-eng', status: 'connected', lastSync: '12 min ago', records: 4820, scope: ['atlas-ledger', 'atlas-settlement', 'atlas-gateway'], frequency: 'Every 15 minutes', volume: '1.8 GB' },
  { id: 'src-jira-atlas', projectId: 'atlas', type: 'jira', name: 'Jira', account: 'northwind.atlassian.net', status: 'connected', lastSync: '25 min ago', records: 1312, scope: ['PAY', 'PAYOPS'], frequency: 'Hourly', volume: '214 MB' },
  { id: 'src-slack-atlas', projectId: 'atlas', type: 'slack', name: 'Slack', account: 'Northwind HQ', status: 'error', lastSync: '2 days ago', records: 9240, scope: ['#payments-arch', '#payments-oncall', '#incidents'], frequency: 'Hourly', volume: '96 MB' },
  { id: 'src-docs-atlas', projectId: 'atlas', type: 'docs', name: 'Documents', account: 'Manual uploads', status: 'connected', lastSync: 'Jun 16', records: 38, scope: ['ADRs', 'Runbooks', 'Vendor contracts'], frequency: 'On upload', volume: '62 MB' },
  { id: 'src-gh-orion', projectId: 'orion', type: 'github', name: 'GitHub', account: 'northwind-eng', status: 'connected', lastSync: '1 h ago', records: 2210, scope: ['orion-app', 'orion-sync'], frequency: 'Every 15 minutes', volume: '740 MB' },
  { id: 'src-jira-orion', projectId: 'orion', type: 'jira', name: 'Jira', account: 'northwind.atlassian.net', status: 'syncing', lastSync: 'Syncing now', records: 640, scope: ['ORN'], frequency: 'Hourly', volume: '88 MB' },
  { id: 'src-gh-helix', projectId: 'helix', type: 'github', name: 'GitHub', account: 'northwind-data', status: 'connected', lastSync: '3 h ago', records: 3105, scope: ['helix-dagster', 'helix-dbt'], frequency: 'Hourly', volume: '1.1 GB' },
  { id: 'src-slack-helix', projectId: 'helix', type: 'slack', name: 'Slack', account: 'Northwind HQ', status: 'connected', lastSync: '3 h ago', records: 5120, scope: ['#data-platform'], frequency: 'Hourly', volume: '41 MB' },
  { id: 'src-docs-helix', projectId: 'helix', type: 'docs', name: 'Documents', account: 'Manual uploads', status: 'connected', lastSync: 'Jun 02', records: 14, scope: ['Architecture notes'], frequency: 'On upload', volume: '18 MB' },
]

export const SOURCE_META: Record<SourceType, { label: string; description: string }> = {
  github: { label: 'GitHub', description: 'Repositories, commits, pull requests, reviews and code ownership.' },
  jira: { label: 'Jira', description: 'Issues, sprints, epics, assignees and status history.' },
  slack: { label: 'Slack', description: 'Selected public channels and threads relevant to the project.' },
  docs: { label: 'PDF & DOCX uploads', description: 'Architecture records, runbooks, specs and contracts.' },
  confluence: { label: 'Confluence', description: 'Spaces and pages containing project documentation.' },
  gdrive: { label: 'Google Drive', description: 'Authorised shared folders with project documents.' },
}

export type EvidenceType = 'commit' | 'pr' | 'issue' | 'message' | 'pdf' | 'docx'

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

export const evidence: Evidence[] = [
  { id: 'ev-412', projectId: 'atlas', type: 'pr', title: 'Introduce Kafka-based settlement events', sourceId: 'src-gh-atlas', authorId: 'james', date: '2025-03-14 16:22', memberId: 'james', processing: 'processed', verification: 'verified', ref: 'atlas-settlement#412',
    content: 'This PR moves settlement triggering out of the ledger transaction path. The ledger now publishes `ledger.entry.posted` events to Kafka and the settlement worker consumes them asynchronously.\n\nWhy: settlement batches were holding row locks on ledger tables for up to 40s during peak, causing API p99 latency spikes (see PAY-1102).\n\nRollout: behind `settlement_async` flag, enabled for 5% merchants first.',
    extracted: ['Decision: settlement decoupled from ledger via Kafka events', 'Reason: row lock contention causing p99 latency spikes', 'Rollout guarded by settlement_async feature flag'] },
  { id: 'ev-sl-arch', projectId: 'atlas', type: 'message', title: 'Settlement decoupling discussion', sourceId: 'src-slack-atlas', authorId: 'james', date: '2025-03-02 10:41', memberId: 'james', processing: 'processed', verification: 'verified', ref: '#payments-arch · thread',
    content: 'James Okafor: Proposal — publish ledger events to Kafka and let settlement consume. Removes the lock problem entirely.\nLucas Berg: Cluster has headroom today, but we should plan for retention growth.\nMaya Chen: Agreed. Let\'s write it up as an ADR and pilot behind a flag.\nJames Okafor: Will draft ADR-007 this week.',
    extracted: ['Proposal for event-driven settlement', 'Concern: Kafka retention growth', 'Action: ADR-007 to be drafted by James'] },
  { id: 'ev-adr7', projectId: 'atlas', type: 'pdf', title: 'ADR-007 Event-driven settlement.pdf', sourceId: 'src-docs-atlas', authorId: 'james', date: '2025-03-06 09:00', memberId: 'james', processing: 'processed', verification: 'verified', ref: 'ADRs/ADR-007.pdf · 6 pages',
    content: 'Status: Accepted\nContext: Settlement runs inside ledger transactions, causing lock contention.\nDecision: Ledger emits domain events to Kafka (topic ledger.entry.posted, 14-day retention). Settlement worker consumes with at-least-once semantics and idempotent writes.\nConsequences: Eventual consistency between ledger and settlement (target < 60s). Requires idempotency keys on all writes.',
    extracted: ['Kafka topic ledger.entry.posted with 14-day retention', 'At-least-once delivery with idempotent writes', 'Eventual consistency target under 60 seconds'] },
  { id: 'ev-1182', projectId: 'atlas', type: 'issue', title: 'PAY-1182 Refund reconciliation job', sourceId: 'src-jira-atlas', authorId: 'maya', date: '2025-05-20 11:05', memberId: 'james', processing: 'processed', verification: 'needs_review', ref: 'PAY-1182 · In progress',
    content: 'Build a nightly job reconciling refunds between ledger and acquirer reports. Acceptance: mismatches flagged in #payments-oncall; report stored in S3. Assignee: James Okafor. Story points: 8. Sprint 24.',
    extracted: ['Task: nightly refund reconciliation job', 'Owner: James Okafor', 'Status: In progress, Sprint 24'] },
  { id: 'ev-a3f9', projectId: 'atlas', type: 'commit', title: 'Add idempotency middleware to payments API', sourceId: 'src-gh-atlas', authorId: 'priya', date: '2025-04-02 14:10', memberId: 'priya', processing: 'processed', verification: 'verified', ref: 'atlas-gateway@a3f9c21',
    content: 'feat(api): require Idempotency-Key header on POST /payments and /refunds\n\n- Store keys in Redis with 24h TTL\n- Return cached response for duplicate keys\n- Reject requests without key (400) when strict mode is enabled',
    extracted: ['Idempotency-Key required on POST /payments and /refunds', 'Keys stored in Redis, 24h TTL'] },
  { id: 'ev-runbook', projectId: 'atlas', type: 'docx', title: 'Payments Runbook v3.docx', sourceId: 'src-docs-atlas', authorId: 'lucas', date: '2025-01-18 08:30', memberId: 'lucas', processing: 'processed', verification: 'needs_review', ref: 'Runbooks/Payments Runbook v3.docx · 22 pages',
    content: 'Section 4 — Deployments: Deploys go through ArgoCD. Production sync requires approval from the on-call payments engineer. Acquirer credentials are rotated quarterly by the settlement owner.\nSection 7 — Settlement failures: Check consumer lag in Grafana dashboard "Settlement". Restart worker if lag > 10k.',
    extracted: ['Production deploys via ArgoCD with on-call approval', 'Settlement owner rotates acquirer credentials quarterly', 'Restart settlement worker when lag exceeds 10k'] },
  { id: 'ev-1204', projectId: 'atlas', type: 'issue', title: 'PAY-1204 Rotate acquirer API credentials', sourceId: 'src-jira-atlas', authorId: 'james', date: '2025-06-03 09:12', memberId: 'james', processing: 'processed', verification: 'needs_review', ref: 'PAY-1204 · To do',
    content: 'Quarterly rotation of Adyen and Worldpay API credentials. Due Jun 30. Requires Vault write access (Platform team). Blocks PAY-1150 merchant batch 3 cutover.',
    extracted: ['Credential rotation due Jun 30', 'Requires Vault write access', 'Blocks PAY-1150'] },
  { id: 'ev-incident', projectId: 'atlas', type: 'message', title: 'Acquirer timeout incident 28 May', sourceId: 'src-slack-atlas', authorId: 'lucas', date: '2025-05-28 22:47', memberId: 'james', processing: 'processed', verification: 'conflicting', ref: '#incidents · thread',
    content: 'Lucas Berg: Settlement batch for 14 merchants failed — acquirer returned 504s for ~9 minutes.\nJames Okafor: Worker has no retry on timeout, only on 5xx. Manually re-ran batch at 23:20.\nLucas Berg: Should we add retries before the July volume peak?\nJames Okafor: Yes, ticket incoming. Root cause might also be our connection pool, not sure yet.',
    extracted: ['Settlement worker lacks retry on acquirer timeouts', 'Manual batch re-run performed', 'Root cause uncertain: acquirer vs connection pool'] },
  { id: 'ev-398', projectId: 'atlas', type: 'pr', title: 'Postgres logical replication for ledger replicas', sourceId: 'src-gh-atlas', authorId: 'james', date: '2025-02-11 13:30', memberId: 'james', processing: 'processed', verification: 'verified', ref: 'atlas-ledger#398',
    content: 'Adds logical replication slots for ledger read replicas used by reporting. Physical replicas were rejected because reporting needs a subset of tables and its own indexes.',
    extracted: ['Decision: logical over physical replication for ledger replicas', 'Reason: reporting needs table subset and custom indexes'] },
  { id: 'ev-1150', projectId: 'atlas', type: 'issue', title: 'PAY-1150 SOAP gateway migration – batch 3', sourceId: 'src-jira-atlas', authorId: 'maya', date: '2025-04-28 10:00', memberId: 'james', processing: 'processed', verification: 'verified', ref: 'PAY-1150 · Blocked',
    content: 'Migrate final 3 merchants (Lindqvist Retail, Okapi Foods, Brightline Travel) from legacy SOAP gateway to REST. Blocked by PAY-1204 credential rotation.',
    extracted: ['3 merchants remain on SOAP gateway', 'Blocked by PAY-1204'] },
  { id: 'ev-kafka', projectId: 'atlas', type: 'pdf', title: 'Kafka capacity review Q2.pdf', sourceId: 'src-docs-atlas', authorId: 'lucas', date: '2025-06-09 15:00', memberId: 'lucas', processing: 'processed', verification: 'needs_review', ref: 'Reviews/Kafka capacity Q2.pdf · 4 pages',
    content: 'Broker disk utilisation at 78% (threshold 85%). Projected to breach threshold mid-August at current growth. Options: reduce retention on ledger.entry.posted to 7 days, or add two brokers (est. €1.4k/month).',
    extracted: ['Kafka disk at 78%, threshold 85%', 'Projected breach mid-August', 'Options: reduce retention or add brokers'] },
  { id: 'ev-7bd0', projectId: 'atlas', type: 'commit', title: 'Skip flaky ledger integration tests in CI', sourceId: 'src-gh-atlas', authorId: 'lucas', date: '2025-06-12 18:05', memberId: 'lucas', processing: 'processing', verification: 'insufficient', ref: 'atlas-ledger@7bd02e4',
    content: 'ci: mark LedgerReplicationIT and SettlementConsumerIT as @flaky until fixtures are stabilised. TODO: re-enable.',
    extracted: ['Two integration tests skipped in CI'] },
  { id: 'ev-monthend', projectId: 'atlas', type: 'message', title: 'Month-end close steps', sourceId: 'src-slack-atlas', authorId: 'james', date: '2025-05-31 17:20', memberId: 'james', processing: 'processed', verification: 'insufficient', ref: '#payments-oncall · message',
    content: 'James Okafor: Reminder for month-end — after the close job, I manually adjust the FX rounding entries before finance exports. Will document properly at some point.',
    extracted: ['Undocumented manual FX rounding adjustment at month-end'] },
  { id: 'ev-contract', projectId: 'atlas', type: 'docx', title: 'SOAP gateway vendor contract summary.docx', sourceId: 'src-docs-atlas', authorId: 'tom', date: '2025-01-09 12:00', memberId: 'maya', processing: 'failed', verification: 'needs_review', ref: 'Contracts/SOAP vendor summary.docx',
    content: 'Vendor support contract for legacy SOAP gateway ends 30 September 2025. Extension available at 3x cost on a monthly basis.',
    extracted: ['SOAP vendor contract ends 30 Sep 2025'] },
  { id: 'ev-orn-88', projectId: 'orion', type: 'pr', title: 'Offline-first sync engine with WatermelonDB', sourceId: 'src-gh-orion', authorId: 'maya', date: '2025-04-17 11:00', memberId: 'maya', processing: 'processed', verification: 'verified', ref: 'orion-sync#88',
    content: 'Introduces a local SQLite store via WatermelonDB and a pull/push sync protocol. Chosen over Realm due to licensing and better React Native New Architecture support.',
    extracted: ['Decision: WatermelonDB for offline-first sync', 'Realm rejected for licensing and RN support'] },
  { id: 'ev-orn-431', projectId: 'orion', type: 'issue', title: 'ORN-431 Conflict resolution for payouts edits', sourceId: 'src-jira-orion', authorId: 'sofia', date: '2025-06-05 10:00', memberId: 'maya', processing: 'processed', verification: 'needs_review', ref: 'ORN-431 · In progress',
    content: 'Define last-write-wins vs field-level merge for payout bank detail edits made offline. Owner: Maya Chen. Due Jul 4.',
    extracted: ['Open task: conflict resolution strategy', 'Owner: Maya Chen, due Jul 4'] },
  { id: 'ev-orn-rel', projectId: 'orion', type: 'commit', title: 'Release train config for 3.8', sourceId: 'src-gh-orion', authorId: 'maya', date: '2025-06-11 16:40', memberId: 'maya', processing: 'processed', verification: 'needs_review', ref: 'orion-app@e19ac03',
    content: 'chore(release): bump to 3.8.0, enable staged rollout 10% on Play Store; iOS phased release. Fastlane lanes updated.',
    extracted: ['Release 3.8 staged rollout configured', 'Fastlane lanes owned by release owner'] },
  { id: 'ev-hlx-dag', projectId: 'helix', type: 'pdf', title: 'Orchestration migration proposal.pdf', sourceId: 'src-docs-helix', authorId: 'elena', date: '2025-01-22 09:00', memberId: 'elena', processing: 'processed', verification: 'verified', ref: 'Architecture/Orchestration proposal.pdf',
    content: 'We propose replacing Airflow with Dagster. Asset-based modelling matches our dbt lineage, local testing is first-class, and it removes 40% of custom sensor code.',
    extracted: ['Decision: Dagster replaces Airflow', 'Reasons: asset model, testing, less custom code'] },
  { id: 'ev-hlx-part', projectId: 'helix', type: 'message', title: 'BigQuery partitioning thread', sourceId: 'src-slack-helix', authorId: 'elena', date: '2025-03-11 14:20', memberId: 'elena', processing: 'processed', verification: 'verified', ref: '#data-platform · thread',
    content: 'Elena Petrova: Partitioning events by day + clustering on merchant_id cut scan costs by ~62% in the test project.\nOmar Haddad: dbt incremental models will need the partition filter.\nElena Petrova: Yes, I\'ll add a macro.',
    extracted: ['Daily partitioning + merchant_id clustering', '~62% scan cost reduction', 'dbt macro for partition filter'] },
  { id: 'ev-hlx-cost', projectId: 'helix', type: 'commit', title: 'Add slot reservation alerts', sourceId: 'src-gh-helix', authorId: 'elena', date: '2025-06-01 10:30', memberId: 'elena', processing: 'processed', verification: 'needs_review', ref: 'helix-dagster@44ad1b9',
    content: 'Adds alerting when BigQuery slot utilisation exceeds 85% for 30 minutes. Pager routes to #data-oncall.',
    extracted: ['Slot utilisation alert at 85%'] },
]

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

export const decisions: Decision[] = [
  { id: 'd-kafka', projectId: 'atlas', title: 'Decouple settlement from the ledger using Kafka events', summary: 'Ledger publishes ledger.entry.posted events; settlement worker consumes asynchronously with idempotent writes.', ownerId: 'james', date: '2025-03-06', confidence: 94, verification: 'verified', evidenceIds: ['ev-412', 'ev-sl-arch', 'ev-adr7'], reasoning: 'Settlement batches held row locks on ledger tables for up to 40 seconds at peak, causing API p99 latency spikes. Event-driven decoupling removes the lock contention and allows independent scaling.', discussions: ['#payments-arch thread, 2 Mar', 'Architecture review, 5 Mar'] },
  { id: 'd-idem', projectId: 'atlas', title: 'Require idempotency keys on all payment write APIs', summary: 'POST /payments and /refunds reject requests without an Idempotency-Key header in strict mode.', ownerId: 'priya', date: '2025-04-02', confidence: 91, verification: 'verified', evidenceIds: ['ev-a3f9', 'ev-adr7'], reasoning: 'At-least-once delivery introduced by event-driven settlement requires idempotent writes to prevent duplicate charges.', discussions: ['PR review on atlas-gateway'] },
  { id: 'd-repl', projectId: 'atlas', title: 'Use logical replication for ledger read replicas', summary: 'Reporting replicas use logical replication slots rather than physical streaming replicas.', ownerId: 'james', date: '2025-02-11', confidence: 87, verification: 'needs_review', evidenceIds: ['ev-398'], reasoning: 'Reporting needs a subset of ledger tables and its own indexes, which physical replicas cannot provide.', discussions: ['PR #398 review comments'] },
  { id: 'd-soap', projectId: 'atlas', title: 'Retire legacy SOAP gateway before contract end', summary: 'All merchants move to the REST gateway before the vendor contract ends on 30 September 2025.', ownerId: 'maya', date: '2025-01-09', confidence: 78, verification: 'needs_review', evidenceIds: ['ev-contract', 'ev-1150'], reasoning: 'Extending vendor support costs 3x on a monthly basis; the REST gateway already serves 99.7% of volume.', discussions: ['Quarterly planning, Jan'] },
  { id: 'd-retention', projectId: 'atlas', title: 'Reduce ledger event retention to 7 days', summary: 'Proposed response to Kafka capacity pressure; conflicts with ADR-007 which specifies 14 days.', ownerId: 'lucas', date: '2025-06-09', confidence: 52, verification: 'conflicting', evidenceIds: ['ev-kafka', 'ev-adr7'], reasoning: 'Capacity review proposes cutting retention; ADR-007 still states 14-day retention. No record of a final decision.', discussions: ['Capacity review, 9 Jun'] },
  { id: 'd-orn-wm', projectId: 'orion', title: 'Adopt WatermelonDB for offline-first sync', summary: 'Local SQLite via WatermelonDB with pull/push sync protocol.', ownerId: 'maya', date: '2025-04-17', confidence: 92, verification: 'verified', evidenceIds: ['ev-orn-88'], reasoning: 'Better support for React Native New Architecture and no licensing constraints compared with Realm.', discussions: ['Mobile architecture sync, Apr'] },
  { id: 'd-orn-rel', projectId: 'orion', title: 'Staged rollouts for every production release', summary: 'Play Store 10% staged rollout and iOS phased release from 3.8 onwards.', ownerId: 'maya', date: '2025-06-11', confidence: 74, verification: 'needs_review', evidenceIds: ['ev-orn-rel'], reasoning: 'Reduce blast radius after the 3.6 crash regression.', discussions: ['Release retro 3.6'] },
  { id: 'd-hlx-dag', projectId: 'helix', title: 'Replace Airflow with Dagster', summary: 'Asset-based orchestration aligned with dbt lineage.', ownerId: 'elena', date: '2025-01-22', confidence: 95, verification: 'verified', evidenceIds: ['ev-hlx-dag'], reasoning: 'Asset model matches dbt lineage, first-class local testing, removes 40% of custom sensor code.', discussions: ['Data platform review, Jan'] },
  { id: 'd-hlx-part', projectId: 'helix', title: 'Partition events by day and cluster by merchant', summary: 'BigQuery events table partitioned daily, clustered on merchant_id.', ownerId: 'elena', date: '2025-03-11', confidence: 90, verification: 'verified', evidenceIds: ['ev-hlx-part'], reasoning: 'Cut scan costs by ~62% in testing; dbt incremental models updated with partition filter macro.', discussions: ['#data-platform thread'] },
]

export const tasks: Task[] = [
  { id: 't-recon', projectId: 'atlas', title: 'Complete refund reconciliation job', summary: 'Nightly job reconciling ledger refunds with acquirer reports; mismatches posted to #payments-oncall.', ownerId: 'james', date: '2025-05-20', confidence: 89, verification: 'needs_review', evidenceIds: ['ev-1182'], priority: 'High', status: 'In progress', due: 'Jun 27', history: [{ personId: 'maya', date: 'May 20', note: 'Created and assigned to James' }, { personId: 'james', date: 'Jun 02', note: 'Moved to In progress' }] },
  { id: 't-rotate', projectId: 'atlas', title: 'Rotate acquirer API credentials', summary: 'Quarterly rotation of Adyen and Worldpay credentials in Vault.', ownerId: 'james', date: '2025-06-03', confidence: 86, verification: 'needs_review', evidenceIds: ['ev-1204', 'ev-runbook'], priority: 'Critical', status: 'To do', due: 'Jun 30', history: [{ personId: 'james', date: 'Jun 03', note: 'Created' }] },
  { id: 't-soap3', projectId: 'atlas', title: 'Migrate final 3 merchants off SOAP gateway', summary: 'Lindqvist Retail, Okapi Foods and Brightline Travel.', ownerId: 'james', date: '2025-04-28', confidence: 90, verification: 'verified', evidenceIds: ['ev-1150'], priority: 'High', status: 'Blocked', due: 'Aug 15', history: [{ personId: 'maya', date: 'Apr 28', note: 'Created' }, { personId: 'james', date: 'Jun 03', note: 'Blocked by PAY-1204' }] },
  { id: 't-runbook', projectId: 'atlas', title: 'Document month-end FX rounding adjustment', summary: 'Capture the manual step currently performed by James after the close job.', ownerId: 'james', date: '2025-05-31', confidence: 61, verification: 'insufficient', evidenceIds: ['ev-monthend'], priority: 'High', status: 'To do', due: 'Jun 28', history: [{ personId: 'james', date: 'May 31', note: 'Mentioned in Slack' }] },
  { id: 't-retry', projectId: 'atlas', title: 'Add timeout retries to settlement worker', summary: 'Exponential backoff for acquirer timeouts before July volume peak.', ownerId: 'priya', date: '2025-05-29', confidence: 82, verification: 'needs_review', evidenceIds: ['ev-incident'], priority: 'Critical', status: 'To do', due: 'Jul 04', history: [{ personId: 'james', date: 'May 29', note: 'Raised after incident' }, { personId: 'maya', date: 'Jun 14', note: 'Reassigned to Priya' }] },
  { id: 't-flaky', projectId: 'atlas', title: 'Re-enable skipped ledger integration tests', summary: 'Stabilise fixtures for LedgerReplicationIT and SettlementConsumerIT.', ownerId: 'lucas', date: '2025-06-12', confidence: 70, verification: 'needs_review', evidenceIds: ['ev-7bd0'], priority: 'Medium', status: 'To do', due: 'Jul 11', history: [{ personId: 'lucas', date: 'Jun 12', note: 'Tests skipped' }] },
  { id: 't-oncall', projectId: 'atlas', title: 'Transfer payments on-call rotation', summary: 'Move James\'s on-call slots and PagerDuty escalation to Priya.', ownerId: 'maya', date: '2025-06-15', confidence: 80, verification: 'verified', evidenceIds: ['ev-runbook'], priority: 'Medium', status: 'In progress', due: 'Jun 30', history: [{ personId: 'maya', date: 'Jun 15', note: 'Created' }] },
  { id: 't-kafka', projectId: 'atlas', title: 'Upgrade Kafka client to 3.7', summary: 'Required for KIP-848 consumer rebalance improvements.', ownerId: 'lucas', date: '2025-05-02', confidence: 84, verification: 'verified', evidenceIds: ['ev-kafka'], priority: 'Low', status: 'Done', due: 'Jun 06', history: [{ personId: 'lucas', date: 'May 02', note: 'Created' }, { personId: 'lucas', date: 'Jun 06', note: 'Completed' }] },
  { id: 't-orn-conf', projectId: 'orion', title: 'Define offline conflict resolution for payout edits', summary: 'Choose last-write-wins vs field-level merge.', ownerId: 'maya', date: '2025-06-05', confidence: 88, verification: 'needs_review', evidenceIds: ['ev-orn-431'], priority: 'High', status: 'In progress', due: 'Jul 04', history: [{ personId: 'sofia', date: 'Jun 05', note: 'Assigned to Maya' }] },
  { id: 't-orn-rel', projectId: 'orion', title: 'Ship release 3.8 to 100%', summary: 'Monitor crash-free rate before expanding staged rollout.', ownerId: 'maya', date: '2025-06-11', confidence: 79, verification: 'needs_review', evidenceIds: ['ev-orn-rel'], priority: 'Medium', status: 'In progress', due: 'Jun 25', history: [{ personId: 'maya', date: 'Jun 11', note: 'Started rollout' }] },
  { id: 't-hlx-cost', projectId: 'helix', title: 'Tune slot reservations for finance month-end', summary: 'Raise reservation during the first 3 days of each month.', ownerId: 'elena', date: '2025-06-01', confidence: 81, verification: 'needs_review', evidenceIds: ['ev-hlx-cost'], priority: 'High', status: 'In progress', due: 'Jul 01', history: [{ personId: 'elena', date: 'Jun 01', note: 'Created' }, { personId: 'tom', date: 'Jun 17', note: 'Transferring to Maya' }] },
  { id: 't-hlx-dbt', projectId: 'helix', title: 'Add partition filter macro to remaining dbt models', summary: '6 incremental models still scan full table.', ownerId: 'omar', date: '2025-03-12', confidence: 85, verification: 'verified', evidenceIds: ['ev-hlx-part'], priority: 'Medium', status: 'To do', due: 'Jul 15', history: [{ personId: 'elena', date: 'Mar 12', note: 'Created' }] },
]

export const risks: Risk[] = [
  { id: 'r-retry', projectId: 'atlas', title: 'Settlement worker has no retry on acquirer timeouts', summary: 'A 9-minute acquirer outage on 28 May failed batches for 14 merchants; recovery was manual.', ownerId: 'priya', date: '2025-05-28', confidence: 83, verification: 'conflicting', evidenceIds: ['ev-incident'], severity: 'Critical', impact: 'Delayed merchant payouts during July volume peak', component: 'Settlement Worker', mitigation: ['Add exponential backoff for 504/timeout responses', 'Alert on failed batch count > 0', 'Confirm whether connection pool exhaustion contributed'], resolution: 'Open' },
  { id: 'r-bus', projectId: 'atlas', title: 'Ledger schema migrations depend on a single maintainer', summary: '92% of ledger migration commits in 12 months authored by James Okafor.', ownerId: 'james', date: '2025-06-10', confidence: 88, verification: 'needs_review', evidenceIds: ['ev-398', 'ev-412'], severity: 'High', impact: 'Knowledge loss after James leaves the project', component: 'Ledger Service', mitigation: ['Pair Priya on next two migrations', 'Record migration checklist in runbook'], resolution: 'Mitigating' },
  { id: 'r-kafka', projectId: 'atlas', title: 'Kafka broker disk projected to breach threshold in August', summary: 'Disk utilisation at 78% against 85% threshold.', ownerId: 'lucas', date: '2025-06-09', confidence: 90, verification: 'verified', evidenceIds: ['ev-kafka'], severity: 'High', impact: 'Consumer lag and potential event loss', component: 'Kafka Cluster', mitigation: ['Decide retention vs broker expansion', 'Add disk utilisation alert at 80%'], resolution: 'Open' },
  { id: 'r-monthend', projectId: 'atlas', title: 'Undocumented manual step in month-end close', summary: 'FX rounding entries are manually adjusted before finance exports.', ownerId: 'james', date: '2025-05-31', confidence: 58, verification: 'insufficient', evidenceIds: ['ev-monthend'], severity: 'High', impact: 'Incorrect finance exports if step is missed', component: 'Ledger Service', mitigation: ['Ask James to document the exact procedure', 'Automate adjustment in close job'], resolution: 'Open' },
  { id: 'r-soap', projectId: 'atlas', title: 'SOAP vendor contract ends 30 September', summary: '3 merchants remain on legacy gateway and migration is blocked.', ownerId: 'maya', date: '2025-04-28', confidence: 76, verification: 'needs_review', evidenceIds: ['ev-contract', 'ev-1150'], severity: 'Medium', impact: '3x support cost or service interruption for 3 merchants', component: 'SOAP Legacy Gateway', mitigation: ['Unblock credential rotation', 'Schedule merchant cutover windows'], resolution: 'Mitigating' },
  { id: 'r-tests', projectId: 'atlas', title: 'Integration tests skipped in CI', summary: 'Two settlement-related integration tests disabled since 12 June.', ownerId: 'lucas', date: '2025-06-12', confidence: 72, verification: 'needs_review', evidenceIds: ['ev-7bd0'], severity: 'Medium', impact: 'Regressions in settlement consumer may go undetected', component: 'Settlement Worker', mitigation: ['Re-enable after fixture fix', 'Add nightly run'], resolution: 'Open' },
  { id: 'r-orn-conf', projectId: 'orion', title: 'Offline edits to bank details can silently overwrite', summary: 'No conflict strategy defined for offline payout edits.', ownerId: 'maya', date: '2025-06-05', confidence: 80, verification: 'needs_review', evidenceIds: ['ev-orn-431'], severity: 'High', impact: 'Incorrect payout destination', component: 'Sync Engine', mitigation: ['Field-level merge with server validation'], resolution: 'Open' },
  { id: 'r-hlx-cost', projectId: 'helix', title: 'Month-end slot contention delays finance reports', summary: 'Slot utilisation exceeded 85% for 6 hours on 1 June.', ownerId: 'elena', date: '2025-06-01', confidence: 84, verification: 'needs_review', evidenceIds: ['ev-hlx-cost'], severity: 'Medium', impact: 'Finance dashboards late by up to 4 hours', component: 'BigQuery Warehouse', mitigation: ['Scheduled reservation increase', 'Prioritise finance jobs'], resolution: 'Mitigating' },
]

export const dependencies: Dependency[] = [
  { id: 'dep-kafka', projectId: 'atlas', title: 'Settlement Worker depends on Kafka cluster', summary: 'Consumes ledger.entry.posted.', ownerId: 'lucas', date: '2025-03-14', confidence: 95, verification: 'verified', evidenceIds: ['ev-412', 'ev-adr7'], depType: 'Technical', from: 'Settlement Worker', to: 'Kafka Cluster', blocking: false },
  { id: 'dep-adyen', projectId: 'atlas', title: 'Settlement depends on Adyen & Worldpay APIs', summary: 'External acquirer APIs for batch settlement.', ownerId: 'james', date: '2025-05-28', confidence: 92, verification: 'verified', evidenceIds: ['ev-incident', 'ev-1204'], depType: 'External', from: 'Settlement Worker', to: 'Acquirer APIs', blocking: false },
  { id: 'dep-rotate', projectId: 'atlas', title: 'SOAP migration blocked by credential rotation', summary: 'PAY-1150 cannot proceed until PAY-1204 is complete.', ownerId: 'james', date: '2025-06-03', confidence: 90, verification: 'verified', evidenceIds: ['ev-1150', 'ev-1204'], depType: 'Task', from: 'Migrate final 3 merchants', to: 'Rotate acquirer credentials', blocking: true },
  { id: 'dep-vault', projectId: 'atlas', title: 'Credential rotation requires Platform team Vault access', summary: 'Write access to secret/payments/acquirers.', ownerId: 'lucas', date: '2025-06-03', confidence: 81, verification: 'needs_review', evidenceIds: ['ev-1204'], depType: 'External', from: 'Rotate acquirer credentials', to: 'Platform team (Vault)', blocking: true },
  { id: 'dep-replica', projectId: 'atlas', title: 'Reporting depends on ledger logical replicas', summary: 'Finance reporting reads from replication slots.', ownerId: 'james', date: '2025-02-11', confidence: 86, verification: 'needs_review', evidenceIds: ['ev-398'], depType: 'Technical', from: 'Reporting', to: 'Ledger Service', blocking: false },
  { id: 'dep-idem', projectId: 'atlas', title: 'Payments API depends on Redis for idempotency', summary: 'Idempotency keys stored with 24h TTL.', ownerId: 'priya', date: '2025-04-02', confidence: 89, verification: 'verified', evidenceIds: ['ev-a3f9'], depType: 'Technical', from: 'Payments API Gateway', to: 'Redis', blocking: false },
  { id: 'dep-orn', projectId: 'orion', title: 'Sync engine depends on Payouts API v2', summary: 'Pull/push endpoints owned by Atlas team.', ownerId: 'maya', date: '2025-04-17', confidence: 85, verification: 'needs_review', evidenceIds: ['ev-orn-88'], depType: 'External', from: 'Sync Engine', to: 'Payouts API v2', blocking: false },
  { id: 'dep-hlx', projectId: 'helix', title: 'dbt models depend on Dagster asset materialisation', summary: 'dbt runs triggered as Dagster assets.', ownerId: 'elena', date: '2025-01-22', confidence: 90, verification: 'verified', evidenceIds: ['ev-hlx-dag'], depType: 'Technical', from: 'dbt models', to: 'Dagster', blocking: false },
]

export interface Gap { id: string; projectId: string; question: string; context: string; askedOf: string }
export const gaps: Gap[] = [
  { id: 'g1', projectId: 'atlas', question: 'What exactly is the month-end FX rounding adjustment procedure?', context: 'Mentioned once in Slack; no runbook entry.', askedOf: 'james' },
  { id: 'g2', projectId: 'atlas', question: 'Was retention on ledger.entry.posted reduced to 7 days?', context: 'Capacity review and ADR-007 conflict.', askedOf: 'lucas' },
  { id: 'g3', projectId: 'atlas', question: 'Who approves production deploys while James is unavailable?', context: 'Runbook references "on-call payments engineer" only.', askedOf: 'james' },
  { id: 'g4', projectId: 'orion', question: 'Which Fastlane secrets are stored locally vs in CI?', context: 'Release lanes reference local keychain.', askedOf: 'maya' },
  { id: 'g5', projectId: 'orion', question: 'Is field-level merge already prototyped?', context: 'ORN-431 has no linked PR.', askedOf: 'maya' },
  { id: 'g6', projectId: 'helix', question: 'Where are Dagster sensor credentials managed?', context: 'No reference in repository or docs.', askedOf: 'elena' },
]

export interface TimelineEvent { id: string; projectId: string; date: string; type: 'milestone' | 'commit' | 'pr' | 'decision' | 'task' | 'discussion' | 'ownership' | 'event'; title: string; detail: string; personId: string; evidenceId?: string }
export const timeline: TimelineEvent[] = [
  { id: 'tl1', projectId: 'atlas', date: '2025-06-17', type: 'ownership', title: 'Settlement ownership transfer started', detail: 'Handover HO-1042 created: James Okafor → Priya Nair', personId: 'maya' },
  { id: 'tl2', projectId: 'atlas', date: '2025-06-12', type: 'commit', title: 'Integration tests skipped in CI', detail: 'atlas-ledger@7bd02e4', personId: 'lucas', evidenceId: 'ev-7bd0' },
  { id: 'tl3', projectId: 'atlas', date: '2025-06-09', type: 'decision', title: 'Kafka retention reduction proposed', detail: 'Conflicts with ADR-007; unresolved', personId: 'lucas', evidenceId: 'ev-kafka' },
  { id: 'tl4', projectId: 'atlas', date: '2025-06-06', type: 'task', title: 'Kafka client upgraded to 3.7', detail: 'Task completed', personId: 'lucas' },
  { id: 'tl5', projectId: 'atlas', date: '2025-05-28', type: 'event', title: 'Acquirer timeout incident', detail: '14 merchant batches failed, manual recovery', personId: 'lucas', evidenceId: 'ev-incident' },
  { id: 'tl6', projectId: 'atlas', date: '2025-05-20', type: 'task', title: 'Refund reconciliation job scoped', detail: 'PAY-1182 created in Sprint 24', personId: 'maya', evidenceId: 'ev-1182' },
  { id: 'tl7', projectId: 'atlas', date: '2025-04-15', type: 'milestone', title: 'Async settlement at 100% of merchants', detail: 'settlement_async flag fully rolled out', personId: 'james' },
  { id: 'tl8', projectId: 'atlas', date: '2025-04-02', type: 'commit', title: 'Idempotency middleware merged', detail: 'atlas-gateway@a3f9c21', personId: 'priya', evidenceId: 'ev-a3f9' },
  { id: 'tl9', projectId: 'atlas', date: '2025-03-14', type: 'pr', title: 'PR #412 Kafka settlement events merged', detail: 'atlas-settlement#412', personId: 'james', evidenceId: 'ev-412' },
  { id: 'tl10', projectId: 'atlas', date: '2025-03-06', type: 'decision', title: 'ADR-007 accepted', detail: 'Event-driven settlement', personId: 'james', evidenceId: 'ev-adr7' },
  { id: 'tl11', projectId: 'atlas', date: '2025-03-02', type: 'discussion', title: 'Settlement decoupling discussed', detail: '#payments-arch thread', personId: 'james', evidenceId: 'ev-sl-arch' },
  { id: 'tl12', projectId: 'atlas', date: '2025-02-11', type: 'pr', title: 'Logical replication for ledger replicas', detail: 'atlas-ledger#398', personId: 'james', evidenceId: 'ev-398' },
  { id: 'tl13', projectId: 'atlas', date: '2025-01-09', type: 'milestone', title: 'SOAP retirement planned for Q3', detail: 'Quarterly planning', personId: 'maya' },
  { id: 'tl14', projectId: 'orion', date: '2025-06-11', type: 'commit', title: 'Release 3.8 staged rollout', detail: 'orion-app@e19ac03', personId: 'maya', evidenceId: 'ev-orn-rel' },
  { id: 'tl15', projectId: 'orion', date: '2025-04-17', type: 'pr', title: 'Offline sync engine merged', detail: 'orion-sync#88', personId: 'maya', evidenceId: 'ev-orn-88' },
  { id: 'tl16', projectId: 'helix', date: '2025-06-17', type: 'ownership', title: 'Orchestration ownership transfer', detail: 'Elena Petrova → Maya Chen', personId: 'tom' },
  { id: 'tl17', projectId: 'helix', date: '2025-03-11', type: 'decision', title: 'Daily partitioning adopted', detail: '#data-platform', personId: 'elena', evidenceId: 'ev-hlx-part' },
  { id: 'tl18', projectId: 'helix', date: '2025-01-22', type: 'decision', title: 'Dagster replaces Airflow', detail: 'Orchestration proposal accepted', personId: 'elena', evidenceId: 'ev-hlx-dag' },
]

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

export const initialHandovers: Handover[] = [
  { id: 'ho-1042', code: 'HO-1042', projectId: 'atlas', outgoingId: 'james', incomingId: 'priya', created: 'Jun 17, 2025', updated: '12 min ago', status: 'pending_review', progress: 86, due: 'Jun 30', scope: 'Settlement service, ledger migrations, acquirer integrations' },
  { id: 'ho-1038', code: 'HO-1038', projectId: 'orion', outgoingId: 'maya', incomingId: 'daniel', created: 'Jun 12, 2025', updated: '1 h ago', status: 'in_progress', progress: 58, due: 'Jul 08', scope: 'Offline sync engine, release train' },
  { id: 'ho-1035', code: 'HO-1035', projectId: 'helix', outgoingId: 'elena', incomingId: 'maya', created: 'Jun 09, 2025', updated: 'Yesterday', status: 'published', progress: 100, due: 'Jun 23', scope: 'Dagster orchestration, BigQuery cost management', publishedOn: 'Jun 17, 2025', access: 'Active' },
  { id: 'ho-1044', code: 'HO-1044', projectId: 'atlas', outgoingId: 'lucas', incomingId: 'omar', created: 'Jun 18, 2025', updated: '2 h ago', status: 'draft', progress: 12, due: 'Jul 18', scope: 'Kafka cluster operations, CI pipelines' },
  { id: 'ho-1029', code: 'HO-1029', projectId: 'atlas', outgoingId: 'sofia', incomingId: 'aisha', created: 'May 02, 2025', updated: 'May 21', status: 'completed', progress: 100, due: 'May 20', scope: 'Refunds regression suite', publishedOn: 'May 14, 2025', access: 'Active', acknowledgedOn: 'May 21, 2025' },
  { id: 'ho-1033', code: 'HO-1033', projectId: 'orion', outgoingId: 'tom', incomingId: 'sofia', created: 'May 28, 2025', updated: 'Jun 15', status: 'approved', progress: 100, due: 'Jun 20', scope: 'Product requirements & roadmap' },
  { id: 'ho-1017', code: 'HO-1017', projectId: 'helix', outgoingId: 'omar', incomingId: 'maya', created: 'Mar 30, 2025', updated: 'Apr 12', status: 'completed', progress: 100, due: 'Apr 10', scope: 'Finance dashboard models', publishedOn: 'Apr 08, 2025', access: 'Expires Jul 31', acknowledgedOn: 'Apr 12, 2025' },
]

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
export const initialNotifications: Notification[] = [
  { id: 'n1', type: 'invitation', title: 'New handover received', body: 'Elena Petrova published HO-1035 · Helix Data Pipeline to you.', time: '9:41', read: false, link: '/handovers/received', group: 'Today' },
  { id: 'n2', type: 'review', title: 'Approval requested', body: 'James Okafor submitted HO-1042 · Atlas Payments for your review.', time: '9:12', read: false, link: '/handovers/ho-1042/review', group: 'Today' },
  { id: 'n3', type: 'integration', title: 'Slack sync failed', body: 'Token expired for Northwind HQ on Atlas Payments. Reconnect to resume.', time: '8:30', read: false, link: '/projects/atlas/sources/src-slack-atlas', group: 'Today' },
  { id: 'n4', type: 'ingestion', title: 'Ingestion completed', body: '412 new records processed from GitHub for Atlas Payments.', time: '7:55', read: true, link: '/projects/atlas/ingestion', group: 'Today' },
  { id: 'n5', type: 'review', title: '6 findings need your verification', body: 'HO-1038 · Orion Mobile has unverified responsibilities attributed to you.', time: 'Yesterday', read: false, link: '/handovers/ho-1038/review', group: 'Yesterday' },
  { id: 'n6', type: 'approval', title: 'Handover approved', body: 'HO-1033 · Orion Mobile was approved by Sofia Alvarez.', time: 'Yesterday', read: true, link: '/handovers/ho-1033', group: 'Yesterday' },
  { id: 'n7', type: 'project', title: 'Conflicting evidence detected', body: 'Kafka retention decision conflicts with ADR-007 on Atlas Payments.', time: 'Jun 15', read: true, link: '/projects/atlas/intelligence/decisions', group: 'Earlier' },
  { id: 'n8', type: 'project', title: 'Added to Nova Design System', body: 'You were added as Project Manager.', time: 'Jun 14', read: true, link: '/projects/nova', group: 'Earlier' },
]

export interface AuditLog { id: string; userId: string; action: string; resource: string; project: string; time: string; type: 'Access' | 'Handover' | 'Integration' | 'Verification' | 'Membership' | 'Settings' }
export const auditLogs: AuditLog[] = [
  { id: 'a1', userId: 'maya', action: 'Viewed handover report', resource: 'HO-1042', project: 'Atlas Payments', time: 'Jun 18, 2025 09:44', type: 'Access' },
  { id: 'a2', userId: 'james', action: 'Submitted handover for approval', resource: 'HO-1042', project: 'Atlas Payments', time: 'Jun 18, 2025 09:12', type: 'Handover' },
  { id: 'a3', userId: 'james', action: 'Verified finding', resource: 'Decision · Kafka settlement', project: 'Atlas Payments', time: 'Jun 18, 2025 09:05', type: 'Verification' },
  { id: 'a4', userId: 'system', action: 'Sync failed: token expired', resource: 'Slack · Northwind HQ', project: 'Atlas Payments', time: 'Jun 18, 2025 08:30', type: 'Integration' },
  { id: 'a5', userId: 'elena', action: 'Published handover', resource: 'HO-1035', project: 'Helix Data', time: 'Jun 17, 2025 17:02', type: 'Handover' },
  { id: 'a6', userId: 'tom', action: 'Approved handover', resource: 'HO-1035', project: 'Helix Data', time: 'Jun 17, 2025 16:40', type: 'Handover' },
  { id: 'a7', userId: 'maya', action: 'Created handover', resource: 'HO-1044', project: 'Atlas Payments', time: 'Jun 17, 2025 14:18', type: 'Handover' },
  { id: 'a8', userId: 'lucas', action: 'Rejected finding', resource: 'Risk · Redis eviction', project: 'Atlas Payments', time: 'Jun 17, 2025 11:02', type: 'Verification' },
  { id: 'a9', userId: 'maya', action: 'Invited member', resource: 'grace.liu@northwind.io', project: '—', time: 'Jun 16, 2025 15:30', type: 'Membership' },
  { id: 'a10', userId: 'maya', action: 'Changed AI confidence threshold to 70%', resource: 'Workspace settings', project: '—', time: 'Jun 16, 2025 10:12', type: 'Settings' },
  { id: 'a11', userId: 'lucas', action: 'Connected source', resource: 'GitHub · northwind-eng', project: 'Atlas Payments', time: 'Jun 14, 2025 09:20', type: 'Integration' },
  { id: 'a12', userId: 'sofia', action: 'Changed member role', resource: 'Daniel Kim → Incoming', project: 'Orion Mobile', time: 'Jun 12, 2025 13:45', type: 'Membership' },
  { id: 'a13', userId: 'priya', action: 'Downloaded evidence', resource: 'ADR-007.pdf', project: 'Atlas Payments', time: 'Jun 11, 2025 16:05', type: 'Access' },
  { id: 'a14', userId: 'maya', action: 'Updated data retention to 24 months', resource: 'Workspace settings', project: '—', time: 'Jun 10, 2025 11:00', type: 'Settings' },
]

export interface IngestJob { id: string; projectId: string; sourceId: string; started: string; records: number; status: 'succeeded' | 'running' | 'failed' | 'queued'; duration: string; error?: string }
export const initialJobs: IngestJob[] = [
  { id: 'job-8812', projectId: 'atlas', sourceId: 'src-gh-atlas', started: 'Today 09:30', records: 412, status: 'running', duration: '—' },
  { id: 'job-8811', projectId: 'atlas', sourceId: 'src-jira-atlas', started: 'Today 09:05', records: 56, status: 'queued', duration: '—' },
  { id: 'job-8809', projectId: 'atlas', sourceId: 'src-slack-atlas', started: 'Today 08:30', records: 0, status: 'failed', duration: '4s', error: 'invalid_auth: OAuth token expired for workspace Northwind HQ. The connecting user must re-authorise Slack.' },
  { id: 'job-8807', projectId: 'atlas', sourceId: 'src-gh-atlas', started: 'Today 07:45', records: 388, status: 'succeeded', duration: '3m 12s' },
  { id: 'job-8803', projectId: 'atlas', sourceId: 'src-docs-atlas', started: 'Yesterday 16:20', records: 3, status: 'failed', duration: '41s', error: 'Parse error in "SOAP gateway vendor contract summary.docx": document is password-protected.' },
  { id: 'job-8799', projectId: 'atlas', sourceId: 'src-jira-atlas', started: 'Yesterday 15:05', records: 74, status: 'succeeded', duration: '48s' },
  { id: 'job-8795', projectId: 'atlas', sourceId: 'src-gh-atlas', started: 'Yesterday 11:45', records: 296, status: 'succeeded', duration: '2m 40s' },
  { id: 'job-8790', projectId: 'orion', sourceId: 'src-jira-orion', started: 'Today 09:00', records: 120, status: 'running', duration: '—' },
  { id: 'job-8770', projectId: 'orion', sourceId: 'src-gh-orion', started: 'Today 08:00', records: 84, status: 'succeeded', duration: '1m 02s' },
  { id: 'job-8750', projectId: 'helix', sourceId: 'src-gh-helix', started: 'Today 06:00', records: 140, status: 'succeeded', duration: '1m 30s' },
  { id: 'job-8748', projectId: 'helix', sourceId: 'src-slack-helix', started: 'Today 06:00', records: 210, status: 'succeeded', duration: '58s' },
]

export const architecture: Record<string, { layer: string; items: string[] }[]> = {
  atlas: [
    { layer: 'Clients', items: ['Merchant API', 'Dashboard', 'Mobile (Orion)'] },
    { layer: 'Edge', items: ['Payments API Gateway', 'Redis (idempotency)'] },
    { layer: 'Core services', items: ['Ledger Service', 'Settlement Worker', 'Refunds Module'] },
    { layer: 'Infrastructure', items: ['Kafka Cluster', 'PostgreSQL + replicas', 'Vault'] },
    { layer: 'External', items: ['Adyen', 'Worldpay', 'SOAP Legacy Gateway'] },
  ],
  orion: [
    { layer: 'App', items: ['React Native 0.76', 'Navigation', 'Design system'] },
    { layer: 'Data', items: ['WatermelonDB', 'Sync Engine'] },
    { layer: 'Delivery', items: ['Fastlane', 'Play Console', 'App Store Connect'] },
    { layer: 'Backend', items: ['Payouts API v2', 'Auth service'] },
  ],
  helix: [
    { layer: 'Sources', items: ['Atlas events', 'Orion telemetry', 'CRM exports'] },
    { layer: 'Ingestion', items: ['Pub/Sub', 'Dagster sensors'] },
    { layer: 'Orchestration', items: ['Dagster assets', 'dbt models'] },
    { layer: 'Warehouse', items: ['BigQuery (partitioned)', 'Slot reservations'] },
    { layer: 'Consumption', items: ['Looker finance', 'Merchant insights API'] },
  ],
}

export const activityTrend = [
  { label: 'Jun 5', evidence: 180, findings: 22 },
  { label: 'Jun 6', evidence: 240, findings: 31 },
  { label: 'Jun 9', evidence: 210, findings: 26 },
  { label: 'Jun 10', evidence: 320, findings: 44 },
  { label: 'Jun 11', evidence: 290, findings: 38 },
  { label: 'Jun 12', evidence: 410, findings: 52 },
  { label: 'Jun 13', evidence: 360, findings: 47 },
  { label: 'Jun 16', evidence: 300, findings: 35 },
  { label: 'Jun 17', evidence: 470, findings: 61 },
  { label: 'Jun 18', evidence: 388, findings: 49 },
]
