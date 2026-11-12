export type ProjectStatus = "active" | "planning" | "completed" | "archived";
export type ProjectVisibility = "private" | "organisation" | "public";

export type WorkflowStage =
  | "connect"
  | "reconstruct"
  | "verify"
  | "review"
  | "handover";

export interface ProjectParticipant {
  id: string;
  name: string;
  role: string;
  email: string;
  avatarUrl?: string;
}

export interface ProjectTransitionInfo {
  departingMember: ProjectParticipant;
  successor: ProjectParticipant;
  targetHandoverDate?: string;
  workflowStage: WorkflowStage;
  handoverScope?: string;
}

export interface Project {
  id: string;
  name: string;
  slug: string;
  organisationName: string;
  description: string;
  status: ProjectStatus;
  visibility: ProjectVisibility;
  owner: ProjectParticipant;
  projectManager?: ProjectParticipant;
  startDate?: string;
  targetCompletionDate?: string;
  createdAt: string;
  lastActivityAt: string;
  membersCount: number;
  sourcesCount: number;
  evidenceCount: number;
  transition: ProjectTransitionInfo;
}

export interface KnowledgeCategoryMetric {
  id: string;
  category: string;
  count: number;
  progressPercent: number;
  description: string;
}

export interface AttentionItem {
  id: string;
  severity: "high" | "medium" | "low";
  type: string;
  title: string;
  description: string;
  suggestedAction?: string;
  relatedModule?: string;
}

export interface ProjectActivityEvent {
  id: string;
  actor: {
    name: string;
    avatarInitials: string;
    role: string;
  };
  action: string;
  target: string;
  timestamp: string;
  category: "evidence" | "source" | "transition" | "review";
}

export interface TeamKnowledgeOwnership {
  memberId: string;
  name: string;
  initials: string;
  role: string;
  domain: string;
  ownershipPercent: number;
}
