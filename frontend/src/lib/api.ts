import type {
  User,
  Organisation,
  Project,
  ProjectOverview,
  ProjectMember,
  SourceConnection,
  ProjectSourceMapping,
  EvidenceSummary,
  EvidenceDetail,
  EvidenceMetrics,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("handover_access_token");
}

export function setStoredToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem("handover_access_token", token);
  } else {
    localStorage.removeItem("handover_access_token");
  }
}

interface ApiErrorPayload {
  error?: {
    message?: string;
    details?: unknown;
  };
  message?: string;
  detail?: unknown;
  details?: unknown;
}

interface ValidationDetailItem {
  msg?: string;
  loc?: unknown[];
}

interface RawOverviewResponse {
  readiness?: ProjectOverview["readiness"];
  sources?: ProjectOverview["sources"];
  project_summary?: {
    project_id?: string;
    name?: string;
    status?: string;
    target_completion_date?: string | null;
  };
  connected_sources?: {
    total_sources?: number;
    active_providers?: string[];
    health_status?: string;
  };
  evidence_overview?: {
    total_records?: number;
    document_count?: number;
    by_provider?: Record<string, number>;
  };
  knowledge_overview?: {
    decisions_count?: number;
    tasks_count?: number;
    risks_count?: number;
    responsibilities_count?: number;
    dependencies_count?: number;
    availability?: string;
  };
  attention_required?: Array<{
    id?: string;
    type?: string;
    message?: string;
    resource_id?: string | null;
  }>;
  attention_items?: Array<{
    id?: string;
    type?: string;
    message?: string;
    resource_id?: string | null;
  }>;
  recent_activity?: Array<{
    id?: string;
    event_type?: string;
    description?: string;
    actor_name?: string | null;
    timestamp?: string;
  }>;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const token = getToken();

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorData: ApiErrorPayload | null = null;
    try {
      errorData = (await res.json()) as ApiErrorPayload;
    } catch {
      // ignore
    }
    let message =
      errorData?.error?.message ||
      errorData?.message ||
      `HTTP error ${res.status}: ${res.statusText}`;

    const details = errorData?.error?.details || errorData?.detail || errorData?.details;
    if (details) {
      if (typeof details === "string") {
        message = details;
      } else if (Array.isArray(details)) {
        const detailMsgs = details.map((d: unknown) => {
          if (typeof d === "string") return d;
          const item = d as ValidationDetailItem | null;
          if (item?.msg) {
            const loc = Array.isArray(item.loc) ? item.loc.slice(-1)[0] : "";
            const cleanMsg = String(item.msg).replace(/^Value error,\s*/i, "");
            return loc && loc !== "body" ? `${String(loc)}: ${cleanMsg}` : cleanMsg;
          }
          return JSON.stringify(d);
        });
        message = detailMsgs.filter(Boolean).join(". ");
      }
    }
    throw new ApiError(message, res.status, errorData);
  }

  if (res.status === 204) {
    return {} as T;
  }

  return res.json() as Promise<T>;
}

function unwrapList<T>(res: unknown): T[] {
  if (!res) return [];
  if (Array.isArray(res)) return res as T[];
  if (typeof res === "object" && "items" in res) {
    const items = (res as { items?: unknown }).items;
    if (Array.isArray(items)) return items as T[];
  }
  return [];
}

export const api = {
  // Authentication
  auth: {
    async register(data: { email: string; password: string; full_name: string }): Promise<User> {
      return request<User>("/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async login(data: { email: string; password: string }): Promise<{ access_token: string; token_type: string }> {
      return request<{ access_token: string; token_type: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async me(): Promise<User> {
      return request<User>("/auth/me");
    },
  },

  // Organisations
  organisations: {
    async list(): Promise<Organisation[]> {
      const res = await request<unknown>("/organisations");
      return unwrapList<Organisation>(res);
    },
    async create(data: { name: string; slug?: string; description?: string }): Promise<Organisation> {
      return request<Organisation>("/organisations", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async get(orgId: string): Promise<Organisation> {
      return request<Organisation>(`/organisations/${orgId}`);
    },
  },

  // Projects
  projects: {
    async list(orgId: string): Promise<Project[]> {
      const res = await request<unknown>(`/organisations/${orgId}/projects`);
      return unwrapList<Project>(res);
    },
    async create(orgId: string, data: { name: string; slug?: string; description?: string; target_handover_date?: string }): Promise<Project> {
      return request<Project>(`/organisations/${orgId}/projects`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async get(projectId: string): Promise<Project> {
      return request<Project>(`/projects/${projectId}`);
    },
    async getOverview(projectId: string): Promise<ProjectOverview> {
      const raw = await request<RawOverviewResponse>(`/projects/${projectId}/overview`);
      if (raw && raw.readiness && raw.sources) {
        return raw as unknown as ProjectOverview;
      }
      const summary = raw?.project_summary || {};
      const connSources = raw?.connected_sources || {};
      const evidOverview = raw?.evidence_overview || {};
      const knowOverview = raw?.knowledge_overview || {};
      const attention = raw?.attention_required || raw?.attention_items || [];
      const activity = raw?.recent_activity || [];

      const totalEvid = evidOverview.total_records || 0;
      const totalSources = connSources.total_sources || 0;
      let readinessPct = 10;
      if (totalSources > 0) readinessPct += 20;
      if (totalEvid > 0) readinessPct += 30;
      if ((knowOverview.decisions_count || 0) > 0 || (knowOverview.tasks_count || 0) > 0) {
        readinessPct += 40;
      }
      readinessPct = Math.min(readinessPct, 100);

      const targetDate = summary.target_completion_date || null;
      let daysRemaining: number | null = null;
      if (targetDate) {
        const diffMs = new Date(targetDate).getTime() - Date.now();
        daysRemaining = Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
      }

      return {
        project_id: summary.project_id || projectId,
        project_name: summary.name || "",
        status: summary.status || "active",
        target_handover_date: targetDate,
        readiness: {
          overall_readiness_pct: readinessPct,
          status: readinessPct >= 80 ? "Ready for Review" : readinessPct >= 40 ? "Reconstruction Active" : "In Preparation",
          target_date: targetDate,
          days_remaining: daysRemaining,
        },
        sources: {
          connected_count: totalSources,
          active_count: (connSources.active_providers || []).length,
          failed_count: connSources.health_status === "error" || connSources.health_status === "failed" ? 1 : 0,
          total_resources: totalSources,
        },
        evidence: {
          total_evidence_items: totalEvid,
          indexed_chunks_count: evidOverview.document_count || totalEvid,
          last_ingested_at: null,
          providers_breakdown: evidOverview.by_provider || {},
        },
        knowledge: {
          decisions_count: knowOverview.decisions_count || 0,
          tasks_count: knowOverview.tasks_count || 0,
          risks_count: knowOverview.risks_count || 0,
          responsibilities_count: knowOverview.responsibilities_count || 0,
          dependencies_count: knowOverview.dependencies_count || 0,
          availability: knowOverview.availability || "available",
        },
        attention_items: attention.map((a) => ({
          id: a.id || String(Math.random()),
          type: a.type || "notice",
          message: a.message || "",
          resource_id: a.resource_id || null,
        })),
        recent_activity: activity.map((ac) => ({
          id: ac.id || String(Math.random()),
          event_type: ac.event_type || "activity",
          description: ac.description || "",
          actor_name: ac.actor_name || null,
          timestamp: ac.timestamp || new Date().toISOString(),
        })),
      };
    },
  },

  // Project Members & Transition Roles
  members: {
    async list(projectId: string): Promise<ProjectMember[]> {
      const res = await request<unknown>(`/projects/${projectId}/members`);
      return unwrapList<ProjectMember>(res);
    },
    async add(projectId: string, data: { user_id?: string; email?: string; role_name?: string; transition_role?: string }): Promise<ProjectMember> {
      return request<ProjectMember>(`/projects/${projectId}/members`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async update(projectId: string, memberId: string, data: { role_name?: string; transition_role?: string }): Promise<ProjectMember> {
      return request<ProjectMember>(`/projects/${projectId}/members/${memberId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    },
  },

  // Sources & Connections
  sources: {
    async listOrgConnections(orgId: string): Promise<SourceConnection[]> {
      const res = await request<unknown>(`/organisations/${orgId}/sources`);
      return unwrapList<SourceConnection>(res);
    },
    async connectSource(orgId: string, data: { provider: "github" | "jira"; access_token: string; account_identifier: string; granted_scopes?: string[] }): Promise<SourceConnection> {
      return request<SourceConnection>(`/organisations/${orgId}/sources`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async listProjectMappings(projectId: string): Promise<ProjectSourceMapping[]> {
      const res = await request<unknown>(`/projects/${projectId}/sources/mappings`);
      return unwrapList<ProjectSourceMapping>(res);
    },
    async createProjectMapping(projectId: string, data: { source_connection_id: string; external_resource_key: string; external_resource_name: string; external_resource_url?: string }): Promise<ProjectSourceMapping> {
      return request<ProjectSourceMapping>(`/projects/${projectId}/sources/mappings`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async triggerSync(projectId: string, mappingId: string): Promise<{ job_id: string; status: string; message: string }> {
      return request<{ job_id: string; status: string; message: string }>(
        `/projects/${projectId}/sources/mappings/${mappingId}/sync`,
        { method: "POST" }
      );
    },
    async getSyncJobs(projectId: string, mappingId: string): Promise<Record<string, unknown>[]> {
      const res = await request<unknown>(`/projects/${projectId}/sources/mappings/${mappingId}/jobs`);
      return unwrapList<Record<string, unknown>>(res);
    },
  },

  // Evidence Workspace
  evidence: {
    async list(projectId: string, params: { q?: string; provider?: string; limit?: number; offset?: number } = {}): Promise<EvidenceSummary[]> {
      const query = new URLSearchParams();
      if (params.q) query.append("q", params.q);
      if (params.provider && params.provider !== "all") query.append("provider", params.provider);
      if (params.limit) query.append("limit", params.limit.toString());
      if (params.offset) query.append("offset", params.offset.toString());
      const qs = query.toString() ? `?${query.toString()}` : "";
      const res = await request<unknown>(`/projects/${projectId}/evidence${qs}`);
      return unwrapList<EvidenceSummary>(res);
    },
    async getMetrics(projectId: string): Promise<EvidenceMetrics> {
      return request<EvidenceMetrics>(`/projects/${projectId}/evidence/metrics`);
    },
    async getDetail(evidenceId: string): Promise<EvidenceDetail> {
      return request<EvidenceDetail>(`/evidence/${evidenceId}`);
    },
    async upload(projectId: string, file: File, title?: string): Promise<{ document_id: string; evidence_item_id?: string; title: string; processing_status: string }> {
      const formData = new FormData();
      formData.append("file", file);
      if (title) formData.append("title", title);
      return request<{ document_id: string; evidence_item_id?: string; title: string; processing_status: string }>(
        `/projects/${projectId}/evidence/upload`,
        {
          method: "POST",
          body: formData,
        }
      );
    },
    async download(evidenceId: string): Promise<Blob> {
      const url = `${API_BASE_URL}/evidence/${evidenceId}/download`;
      const token = getToken();
      const res = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        throw new ApiError(`Download failed with status ${res.status}`, res.status);
      }
      return res.blob();
    },
  },
};
