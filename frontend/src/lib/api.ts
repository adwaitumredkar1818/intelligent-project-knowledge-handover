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
    let errorData: any = null;
    try {
      errorData = await res.json();
    } catch {
      // ignore
    }
    const message =
      errorData?.detail ||
      errorData?.message ||
      `HTTP error ${res.status}: ${res.statusText}`;
    throw new ApiError(message, res.status, errorData);
  }

  if (res.status === 204) {
    return {} as T;
  }

  return res.json() as Promise<T>;
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
    async login(data: { username: string; password: string }): Promise<{ access_token: string; token_type: string }> {
      const form = new URLSearchParams();
      form.append("username", data.username);
      form.append("password", data.password);
      return request<{ access_token: string; token_type: string }>("/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: form.toString(),
      });
    },
    async me(): Promise<User> {
      return request<User>("/auth/me");
    },
  },

  // Organisations
  organisations: {
    async list(): Promise<Organisation[]> {
      return request<Organisation[]>("/organisations");
    },
    async create(data: { name: string; slug?: string }): Promise<Organisation> {
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
      return request<Project[]>(`/organisations/${orgId}/projects`);
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
      return request<ProjectOverview>(`/projects/${projectId}/overview`);
    },
  },

  // Project Members & Transition Roles
  members: {
    async list(projectId: string): Promise<ProjectMember[]> {
      return request<ProjectMember[]>(`/projects/${projectId}/members`);
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
      return request<SourceConnection[]>(`/organisations/${orgId}/sources`);
    },
    async connectSource(orgId: string, data: { provider: "github" | "jira"; access_token: string; account_identifier: string; granted_scopes?: string[] }): Promise<SourceConnection> {
      return request<SourceConnection>(`/organisations/${orgId}/sources`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async listProjectMappings(projectId: string): Promise<ProjectSourceMapping[]> {
      return request<ProjectSourceMapping[]>(`/projects/${projectId}/sources/mappings`);
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
    async getSyncJobs(projectId: string, mappingId: string): Promise<any[]> {
      return request<any[]>(`/projects/${projectId}/sources/mappings/${mappingId}/jobs`);
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
      return request<EvidenceSummary[]>(`/projects/${projectId}/evidence${qs}`);
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
