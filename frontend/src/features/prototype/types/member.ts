export type MemberRole =
  | "project_manager"
  | "project_member"
  | "reviewer"
  | "technical_lead"
  | "developer"
  | "database_engineer"
  | "ml_engineer";

export type TransitionDesignation = "departing_owner" | "successor" | "standard";

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: string;
  roleCode: MemberRole;
  responsibilities: string;
  status: "active" | "invited" | "inactive";
  transitionDesignation: TransitionDesignation;
  joinedAt: string;
  avatarInitials: string;
  contributionStats?: {
    evidenceContributed: number;
    decisionsOwned: number;
    tasksOwned: number;
  };
}
