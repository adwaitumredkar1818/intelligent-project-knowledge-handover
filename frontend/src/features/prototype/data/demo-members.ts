import type { TeamMember } from "../types/member";

export const MEMBER_ALEX: TeamMember = {
  id: "mem-alex-001",
  name: "Alex Vance",
  email: "alex.vance@nexora.internal",
  role: "Backend Lead & Security",
  roleCode: "technical_lead",
  responsibilities: "Core authentication pipelines, token lifecycle, and session management.",
  status: "active",
  transitionDesignation: "departing_owner",
  joinedAt: "2024-03-15",
  avatarInitials: "AV",
  contributionStats: {
    evidenceContributed: 38,
    decisionsOwned: 12,
    tasksOwned: 26,
  },
};

export const MEMBER_DANIEL: TeamMember = {
  id: "mem-daniel-002",
  name: "Daniel Cho",
  email: "daniel.cho@nexora.internal",
  role: "Incoming Staff Engineer",
  roleCode: "developer",
  responsibilities: "Successor taking over backend auth service and settlement gateway.",
  status: "active",
  transitionDesignation: "successor",
  joinedAt: "2026-10-01",
  avatarInitials: "DC",
  contributionStats: {
    evidenceContributed: 4,
    decisionsOwned: 1,
    tasksOwned: 5,
  },
};

export const MEMBER_SARAH: TeamMember = {
  id: "mem-sarah-003",
  name: "Sarah Jenkins",
  email: "sarah.jenkins@nexora.internal",
  role: "Frontend Architect",
  roleCode: "project_member",
  responsibilities: "Web workspace, design system token architecture, and client sessions.",
  status: "active",
  transitionDesignation: "standard",
  joinedAt: "2024-06-10",
  avatarInitials: "SJ",
  contributionStats: {
    evidenceContributed: 24,
    decisionsOwned: 7,
    tasksOwned: 19,
  },
};

export const MEMBER_DAVID: TeamMember = {
  id: "mem-david-004",
  name: "David Morales",
  email: "david.morales@nexora.internal",
  role: "Senior ML Engineer",
  roleCode: "ml_engineer",
  responsibilities: "Retrieval embeddings, vector ranking pipelines, and hybrid search indexer.",
  status: "active",
  transitionDesignation: "standard",
  joinedAt: "2024-09-01",
  avatarInitials: "DM",
  contributionStats: {
    evidenceContributed: 19,
    decisionsOwned: 6,
    tasksOwned: 14,
  },
};

export const MEMBER_EMILY: TeamMember = {
  id: "mem-emily-005",
  name: "Emily Watson",
  email: "emily.watson@nexora.internal",
  role: "Database Administrator",
  roleCode: "database_engineer",
  responsibilities: "PostgreSQL schemas, partition strategies, and connection pooling latency.",
  status: "active",
  transitionDesignation: "standard",
  joinedAt: "2024-01-20",
  avatarInitials: "EW",
  contributionStats: {
    evidenceContributed: 22,
    decisionsOwned: 5,
    tasksOwned: 17,
  },
};

export const MEMBER_MICHAEL: TeamMember = {
  id: "mem-michael-006",
  name: "Michael Chang",
  email: "michael.chang@nexora.internal",
  role: "Technical Project Manager",
  roleCode: "project_manager",
  responsibilities: "Sprint governance, cross-functional dependencies, and audit compliance.",
  status: "active",
  transitionDesignation: "standard",
  joinedAt: "2023-11-15",
  avatarInitials: "MC",
  contributionStats: {
    evidenceContributed: 16,
    decisionsOwned: 4,
    tasksOwned: 29,
  },
};

export const DEMO_MEMBERS: TeamMember[] = [
  MEMBER_ALEX,
  MEMBER_DANIEL,
  MEMBER_SARAH,
  MEMBER_DAVID,
  MEMBER_EMILY,
  MEMBER_MICHAEL,
];
