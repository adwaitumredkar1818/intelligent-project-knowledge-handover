/**
 * Centralized query key factories ensuring clean namespaces and scoped cache invalidation.
 */

export const queryKeys = {
  auth: {
    me: () => ["auth", "me"] as const,
  },
  organisations: {
    all: () => ["organisations"] as const,
    detail: (orgId: string) => ["organisations", orgId] as const,
    members: (orgId: string) => ["organisations", orgId, "members"] as const,
  },
  projects: {
    list: (orgId?: string) => ["projects", "list", { orgId }] as const,
    detail: (projectId: string) => ["projects", projectId, "detail"] as const,
    overview: (projectId: string) => ["projects", projectId, "overview"] as const,
    members: (projectId: string) => ["projects", projectId, "members"] as const,
    transitions: (projectId: string) => ["projects", projectId, "transitions"] as const,
  },
  evidence: {
    list: (projectId: string, filters?: Record<string, unknown>) =>
      ["evidence", projectId, "list", filters || {}] as const,
    detail: (evidenceId: string) => ["evidence", "detail", evidenceId] as const,
    metrics: (projectId: string) => ["evidence", projectId, "metrics"] as const,
  },
  knowledge: {
    overview: (projectId: string) => ["knowledge", projectId, "overview"] as const,
    domains: (projectId: string, domain?: string) =>
      ["knowledge", projectId, "domains", domain || "all"] as const,
    items: (projectId: string, filters?: Record<string, unknown>) =>
      ["knowledge", projectId, "items", filters || {}] as const,
  },
  relationships: {
    graph: (projectId: string) => ["relationships", projectId, "graph"] as const,
    entities: (projectId: string) => ["relationships", projectId, "entities"] as const,
    timeline: (projectId: string) => ["relationships", projectId, "timeline"] as const,
  },
  verification: {
    cases: (projectId: string, filters?: Record<string, unknown>) =>
      ["verification", projectId, "cases", filters || {}] as const,
    conflicts: (projectId: string) => ["verification", projectId, "conflicts"] as const,
    issues: (projectId: string) => ["verification", projectId, "issues"] as const,
  },
  handover: {
    packages: (projectId: string) => ["handover", projectId, "packages"] as const,
    readiness: (projectId: string) => ["handover", projectId, "readiness"] as const,
    checklists: (projectId: string) => ["handover", projectId, "checklists"] as const,
    detail: (packageId: string) => ["handover", "package", packageId] as const,
  },
  assistant: {
    conversations: (projectId: string) => ["assistant", projectId, "conversations"] as const,
    conversation: (conversationId: string) => ["assistant", "conversation", conversationId] as const,
  },
};
