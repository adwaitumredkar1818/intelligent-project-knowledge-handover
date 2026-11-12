import type {
  AttentionItem,
  KnowledgeCategoryMetric,
  Project,
  ProjectActivityEvent,
  TeamKnowledgeOwnership,
} from "../types/project";
import {
  MEMBER_ALEX,
  MEMBER_DANIEL,
  MEMBER_SARAH,
  MEMBER_DAVID,
  MEMBER_EMILY,
  MEMBER_MICHAEL,
} from "./demo-members";

export const PROJECT_NEXORA_ASSIST: Project = {
  id: "proj-nexora-assist-001",
  name: "Nexora Assist",
  slug: "nexora-assist",
  organisationName: "Nexora Technologies",
  description:
    "Intelligent project knowledge reconstruction co-pilot preserving architectural decisions, auth services, and technical continuity.",
  status: "active",
  visibility: "private",
  owner: {
    id: MEMBER_MICHAEL.id,
    name: MEMBER_MICHAEL.name,
    role: MEMBER_MICHAEL.role,
    email: MEMBER_MICHAEL.email,
  },
  projectManager: {
    id: MEMBER_MICHAEL.id,
    name: MEMBER_MICHAEL.name,
    role: MEMBER_MICHAEL.role,
    email: MEMBER_MICHAEL.email,
  },
  startDate: "2026-01-15",
  targetCompletionDate: "2026-12-31",
  createdAt: "2026-01-15T08:00:00Z",
  lastActivityAt: "12 minutes ago",
  membersCount: 6,
  sourcesCount: 4,
  evidenceCount: 22,
  transition: {
    departingMember: {
      id: MEMBER_ALEX.id,
      name: MEMBER_ALEX.name,
      role: MEMBER_ALEX.role,
      email: MEMBER_ALEX.email,
    },
    successor: {
      id: MEMBER_DANIEL.id,
      name: MEMBER_DANIEL.name,
      role: MEMBER_DANIEL.role,
      email: MEMBER_DANIEL.email,
    },
    targetHandoverDate: "2026-11-28",
    workflowStage: "reconstruct",
    handoverScope:
      "Full core authentication engine, token rotation handlers, KMS encryption keys, and disaster recovery runbooks.",
  },
};

export const PROJECT_LEDGER_MIGRATION: Project = {
  id: "proj-ledger-migration-002",
  name: "Ledger Core Migration",
  slug: "ledger-core-migration",
  organisationName: "Nexora Technologies",
  description:
    "Migration of monolithic transaction ledger to distributed event-driven microservices with dual-write reconciliation.",
  status: "planning",
  visibility: "private",
  owner: {
    id: MEMBER_EMILY.id,
    name: MEMBER_EMILY.name,
    role: MEMBER_EMILY.role,
    email: MEMBER_EMILY.email,
  },
  startDate: "2026-04-01",
  targetCompletionDate: "2027-02-28",
  createdAt: "2026-04-01T10:00:00Z",
  lastActivityAt: "3 days ago",
  membersCount: 4,
  sourcesCount: 2,
  evidenceCount: 14,
  transition: {
    departingMember: {
      id: MEMBER_EMILY.id,
      name: MEMBER_EMILY.name,
      role: MEMBER_EMILY.role,
      email: MEMBER_EMILY.email,
    },
    successor: {
      id: MEMBER_SARAH.id,
      name: MEMBER_SARAH.name,
      role: MEMBER_SARAH.role,
      email: MEMBER_SARAH.email,
    },
    targetHandoverDate: "2026-12-15",
    workflowStage: "connect",
    handoverScope: "Database partitioning, CDC pipelines, and Kafka stream reconciliation.",
  },
};

export const PROJECT_IDENTITY_SSO: Project = {
  id: "proj-identity-sso-003",
  name: "Identity & SSO Service",
  slug: "identity-sso-service",
  organisationName: "Nexora Technologies",
  description:
    "Centralized OAuth2 and SAML 2.0 single sign-on hub for customer and enterprise tenant authentication.",
  status: "completed",
  visibility: "organisation",
  owner: {
    id: MEMBER_SARAH.id,
    name: MEMBER_SARAH.name,
    role: MEMBER_SARAH.role,
    email: MEMBER_SARAH.email,
  },
  startDate: "2025-06-01",
  targetCompletionDate: "2026-03-31",
  createdAt: "2025-06-01T09:00:00Z",
  lastActivityAt: "2 weeks ago",
  membersCount: 5,
  sourcesCount: 3,
  evidenceCount: 32,
  transition: {
    departingMember: {
      id: MEMBER_DAVID.id,
      name: MEMBER_DAVID.name,
      role: MEMBER_DAVID.role,
      email: MEMBER_DAVID.email,
    },
    successor: {
      id: MEMBER_MICHAEL.id,
      name: MEMBER_MICHAEL.name,
      role: MEMBER_MICHAEL.role,
      email: MEMBER_MICHAEL.email,
    },
    targetHandoverDate: "2026-03-31",
    workflowStage: "handover",
    handoverScope: "SAML assertion signing, metadata refresh, and tenant isolation policies.",
  },
};

export const DEMO_PROJECTS: Project[] = [
  PROJECT_NEXORA_ASSIST,
  PROJECT_LEDGER_MIGRATION,
  PROJECT_IDENTITY_SSO,
];

export const DEMO_KNOWLEDGE_CATEGORIES: KnowledgeCategoryMetric[] = [
  {
    id: "cat-decisions",
    category: "Decisions & Rationale",
    count: 18,
    progressPercent: 78,
    description: "Architectural choices, auth token TTLs, and cryptographic standards.",
  },
  {
    id: "cat-tasks",
    category: "Tasks & Completed Work",
    count: 42,
    progressPercent: 64,
    description: "Jira tickets resolved, PRs merged, and pending backlog items.",
  },
  {
    id: "cat-responsibilities",
    category: "Responsibilities & Ownership",
    count: 12,
    progressPercent: 88,
    description: "Assigned code ownership, database schemas, and on-call rotations.",
  },
  {
    id: "cat-risks",
    category: "Risks & Blockers",
    count: 7,
    progressPercent: 45,
    description: "PostgreSQL deadlocks, token revocation cascades, and single points of failure.",
  },
  {
    id: "cat-dependencies",
    category: "Dependencies & Integrations",
    count: 15,
    progressPercent: 70,
    description: "Third-party APIs (GitHub, Jira, Stripe), Redis caching, and KMS.",
  },
];

export const DEMO_ATTENTION_ITEMS: AttentionItem[] = [
  {
    id: "att-001",
    severity: "high",
    type: "Conflict",
    title: "Conflicting password reset status",
    description: "Jira NXA-289 marks reset as completed, but PR #112 tests are currently failing.",
    suggestedAction: "Inspect Evidence Center",
    relatedModule: "evidence",
  },
  {
    id: "att-002",
    severity: "medium",
    type: "Missing Evidence",
    title: "Missing documentation for token expiration edge case",
    description: "No ADR found explaining why 15-minute access token TTL was chosen over 30 minutes.",
    suggestedAction: "Request Review",
    relatedModule: "verification",
  },
  {
    id: "att-003",
    severity: "low",
    type: "Outdated Source",
    title: "Outdated Jira status sync",
    description: "Board Nexora Assist last synced 28 minutes ago; 3 new issues awaiting ingestion.",
    suggestedAction: "Trigger Sync",
    relatedModule: "sources",
  },
  {
    id: "att-004",
    severity: "medium",
    type: "Integration Disabled",
    title: "Slack source connection unavailable",
    description: "Enterprise Slack workspace authorisation is not enabled in this prototype.",
    suggestedAction: "Review Settings",
    relatedModule: "sources",
  },
];

export const DEMO_RECENT_ACTIVITY: ProjectActivityEvent[] = [
  {
    id: "act-001",
    actor: {
      name: "Alex Vance",
      avatarInitials: "AV",
      role: "Backend Lead",
    },
    action: "uploaded architecture notes",
    target: "ADR-012_Auth_Service_Boundaries.pdf",
    timestamp: "12 minutes ago",
    category: "evidence",
  },
  {
    id: "act-002",
    actor: {
      name: "GitHub Sync",
      avatarInitials: "GH",
      role: "System Worker",
    },
    action: "imported merged Pull Request",
    target: "PR #104: Token-expiry checks",
    timestamp: "35 minutes ago",
    category: "source",
  },
  {
    id: "act-003",
    actor: {
      name: "Jira Sync",
      avatarInitials: "JR",
      role: "System Worker",
    },
    action: "synchronised 12 updated issues from board",
    target: "Nexora Assist (NXA)",
    timestamp: "1 hour ago",
    category: "source",
  },
  {
    id: "act-004",
    actor: {
      name: "Emily Watson",
      avatarInitials: "EW",
      role: "Database Engineer",
    },
    action: "uploaded operational procedure",
    target: "Identity_API_Contracts_v2.docx",
    timestamp: "3 hours ago",
    category: "evidence",
  },
  {
    id: "act-005",
    actor: {
      name: "Michael Chang",
      avatarInitials: "MC",
      role: "Project Manager",
    },
    action: "updated transition target date",
    target: "Alex Vance → Daniel Cho (Nov 28, 2026)",
    timestamp: "Yesterday",
    category: "transition",
  },
];

export const DEMO_TEAM_OWNERSHIP: TeamKnowledgeOwnership[] = [
  {
    memberId: MEMBER_ALEX.id,
    name: MEMBER_ALEX.name,
    initials: MEMBER_ALEX.avatarInitials,
    role: MEMBER_ALEX.role,
    domain: "Backend Authentication & Token Rails",
    ownershipPercent: 85,
  },
  {
    memberId: MEMBER_SARAH.id,
    name: MEMBER_SARAH.name,
    initials: MEMBER_SARAH.avatarInitials,
    role: MEMBER_SARAH.role,
    domain: "Frontend Sessions & Web Workspace",
    ownershipPercent: 70,
  },
  {
    memberId: MEMBER_DAVID.id,
    name: MEMBER_DAVID.name,
    initials: MEMBER_DAVID.avatarInitials,
    role: MEMBER_DAVID.role,
    domain: "ML Retrieval & Vector Ranking",
    ownershipPercent: 90,
  },
  {
    memberId: MEMBER_EMILY.id,
    name: MEMBER_EMILY.name,
    initials: MEMBER_EMILY.avatarInitials,
    role: MEMBER_EMILY.role,
    domain: "Database Schema & Partition Policies",
    ownershipPercent: 80,
  },
  {
    memberId: MEMBER_MICHAEL.id,
    name: MEMBER_MICHAEL.name,
    initials: MEMBER_MICHAEL.avatarInitials,
    role: MEMBER_MICHAEL.role,
    domain: "Project Governance & Audit Trail",
    ownershipPercent: 65,
  },
];

export const DEMO_PENDING_REVIEWS = [
  {
    id: "rev-001",
    title: "Refresh-token rotation decision rationale",
    source: "PR #104 & ADR-012",
    owner: "Alex Vance",
    category: "Decision",
    confidence: "94%",
    status: "Awaiting Verification",
  },
  {
    id: "rev-002",
    title: "Password reset token HMAC implementation",
    source: "Jira NXA-289",
    owner: "Emily Watson",
    category: "Task",
    confidence: "89%",
    status: "Awaiting Verification",
  },
  {
    id: "rev-003",
    title: "Authentication service domain ownership transfer",
    source: "Meeting Notes Nov 11",
    owner: "Alex Vance → Daniel Cho",
    category: "Ownership",
    confidence: "96%",
    status: "Awaiting Verification",
  },
];
