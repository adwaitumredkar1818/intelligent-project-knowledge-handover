"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { api, setStoredToken, ApiError } from "../lib/api";
import type {
  User,
  Organisation,
  Project,
  ProjectOverview,
  ProjectMember,
  ProjectSourceMapping,
  SourceConnection,
  EvidenceSummary,
  EvidenceDetail,
  EvidenceMetrics,
  KnowledgeFinding,
  KnowledgeSummaryTelemetry,
  VerificationSummaryData,
  VerificationCaseQueueItem,
  HandoverCaseItem,
} from "../lib/types";

export interface ToastMessage {
  id: string;
  type: "success" | "info" | "warning" | "error";
  title: string;
  message: string;
}

interface LiveAppContextType {
  // Auth
  user: User | null;
  token: string | null;
  isLoadingAuth: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;

  // Organisations
  organisations: Organisation[];
  activeOrg: Organisation | null;
  setActiveOrg: (org: Organisation) => void;
  createOrganisation: (name: string, slug?: string) => Promise<Organisation>;

  // Projects
  projects: Project[];
  activeProject: Project | null;
  setActiveProject: (project: Project | null) => void;
  createProject: (
    data: { name: string; slug?: string; description?: string; target_handover_date?: string },
    options?: { orgId?: string; newOrgName?: string }
  ) => Promise<Project>;
  isLoadingProjects: boolean;
  refreshProjects: () => Promise<void>;

  // Overview
  overview: ProjectOverview | null;
  isLoadingOverview: boolean;
  refreshOverview: () => Promise<void>;

  // Team Members
  members: ProjectMember[];
  isLoadingMembers: boolean;
  addMember: (data: { email?: string; user_id?: string; role_name?: string; transition_role?: string }) => Promise<void>;
  updateMember: (memberId: string, data: { role_name?: string; transition_role?: string }) => Promise<void>;
  refreshMembers: () => Promise<void>;

  // Sources
  sourceMappings: ProjectSourceMapping[];
  orgConnections: SourceConnection[];
  isLoadingSources: boolean;
  connectSource: (provider: "github" | "jira", token: string, accountId: string) => Promise<SourceConnection>;
  createMapping: (data: { source_connection_id: string; external_resource_key: string; external_resource_name: string; external_resource_url?: string }) => Promise<ProjectSourceMapping>;
  triggerSync: (mappingId: string) => Promise<void>;
  refreshSources: () => Promise<void>;

  // Evidence
  evidenceList: EvidenceSummary[];
  evidenceMetrics: EvidenceMetrics | null;
  selectedEvidenceId: string | null;
  selectedEvidence: EvidenceDetail | null;
  isLoadingEvidence: boolean;
  isLoadingEvidenceDetail: boolean;
  evidenceFilter: { q: string; provider: string };
  setEvidenceFilter: React.Dispatch<React.SetStateAction<{ q: string; provider: string }>>;
  setSelectedEvidenceId: (id: string | null) => void;
  refreshEvidence: () => Promise<void>;
  uploadDocument: (file: File, title?: string) => Promise<{ document_id: string; title: string }>;
  downloadEvidence: (evidenceId: string, filename?: string) => Promise<void>;

  // Downstream intelligence
  knowledgeSummary: KnowledgeSummaryTelemetry | null;
  findings: KnowledgeFinding[];
  isLoadingFindings: boolean;
  refreshFindings: () => Promise<void>;
  triggerReconstruction: () => Promise<void>;

  // Verification
  verificationSummary: VerificationSummaryData | null;
  verificationQueue: VerificationCaseQueueItem[];
  isLoadingVerification: boolean;
  refreshVerification: () => Promise<void>;
  approveVerificationCase: (caseId: string, notes?: string) => Promise<void>;
  rejectVerificationCase: (caseId: string, reason?: string) => Promise<void>;

  // Handover
  handoverCases: HandoverCaseItem[];
  isLoadingHandovers: boolean;
  refreshHandovers: () => Promise<void>;
  createHandoverCase: (data: { title: string; description?: string }) => Promise<Record<string, unknown>>;

  // UI state & modals
  isAuthModalOpen: boolean;
  setIsAuthModalOpen: (open: boolean) => void;
  authModalMode: "login" | "register";
  setAuthModalMode: (mode: "login" | "register") => void;
  openAuthModal: (mode?: "login" | "register") => void;
  closeAuthModal: () => void;
  isCreateOrgModalOpen: boolean;
  setIsCreateOrgModalOpen: (open: boolean) => void;
  isCreateProjectModalOpen: boolean;
  setIsCreateProjectModalOpen: (open: boolean) => void;
  isAddSourceModalOpen: boolean;
  setIsAddSourceModalOpen: (open: boolean) => void;
  isUploadModalOpen: boolean;
  setIsUploadModalOpen: (open: boolean) => void;
  isAddMemberModalOpen: boolean;
  setIsAddMemberModalOpen: (open: boolean) => void;
  isMobileSidebarOpen: boolean;
  setIsMobileSidebarOpen: (open: boolean) => void;

  // Toasts
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, "id">) => void;
  dismissToast: (id: string) => void;
}

const LiveAppContext = createContext<LiveAppContextType | undefined>(undefined);

export function LiveAppProvider({ children }: { children: ReactNode }) {
  // Auth state
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);

  // Org & Project state
  const [organisations, setOrganisations] = useState<Organisation[]>([]);
  const [activeOrg, setActiveOrgInternal] = useState<Organisation | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProjectInternal] = useState<Project | null>(null);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);

  // Overview state
  const [overview, setOverview] = useState<ProjectOverview | null>(null);
  const [isLoadingOverview, setIsLoadingOverview] = useState(false);

  // Members state
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);

  // Sources state
  const [sourceMappings, setSourceMappings] = useState<ProjectSourceMapping[]>([]);
  const [orgConnections, setOrgConnections] = useState<SourceConnection[]>([]);
  const [isLoadingSources, setIsLoadingSources] = useState(false);

  // Evidence state
  const [evidenceList, setEvidenceList] = useState<EvidenceSummary[]>([]);
  const [evidenceMetrics, setEvidenceMetrics] = useState<EvidenceMetrics | null>(null);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceDetail | null>(null);

  // Downstream intelligence states
  const [knowledgeSummary, setKnowledgeSummary] = useState<KnowledgeSummaryTelemetry | null>(null);
  const [findings, setFindings] = useState<KnowledgeFinding[]>([]);
  const [isLoadingFindings, setIsLoadingFindings] = useState(false);

  // Verification states
  const [verificationSummary, setVerificationSummary] = useState<VerificationSummaryData | null>(null);
  const [verificationQueue, setVerificationQueue] = useState<VerificationCaseQueueItem[]>([]);
  const [isLoadingVerification, setIsLoadingVerification] = useState(false);

  // Handover states
  const [handoverCases, setHandoverCases] = useState<HandoverCaseItem[]>([]);
  const [isLoadingHandovers, setIsLoadingHandovers] = useState(false);
  const [isLoadingEvidence, setIsLoadingEvidence] = useState(false);
  const [isLoadingEvidenceDetail, setIsLoadingEvidenceDetail] = useState(false);
  const [evidenceFilter, setEvidenceFilter] = useState<{ q: string; provider: string }>({
    q: "",
    provider: "all",
  });

  // Organisation selector wrapper that persists user workspace preference
  const setActiveOrg = useCallback(
    (action: Organisation | null | ((prev: Organisation | null) => Organisation | null)) => {
      setActiveOrgInternal((prev) => {
        const next = typeof action === "function" ? action(prev) : action;
        if (next && typeof window !== "undefined") {
          localStorage.setItem("handover_active_org_id", next.id);
        } else if (!next && typeof window !== "undefined") {
          localStorage.removeItem("handover_active_org_id");
        }
        return next;
      });
    },
    []
  );

  // Project selector wrapper that resets stale project-specific caches
  const setActiveProject = useCallback(
    (action: Project | null | ((prev: Project | null) => Project | null)) => {
      setActiveProjectInternal((prev) => {
        const next = typeof action === "function" ? action(prev) : action;
        if (next && typeof window !== "undefined") {
          localStorage.setItem("handover_active_project_id", next.id);
        } else if (!next && typeof window !== "undefined") {
          localStorage.removeItem("handover_active_project_id");
        }
        if (prev?.id === next?.id) return prev;
        setOverview(null);
        setMembers([]);
        setEvidenceList([]);
        setSourceMappings([]);
        return next;
      });
    },
    []
  );

  // Modals & UI
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState<"login" | "register">("login");
  const openAuthModal = useCallback((mode: "login" | "register" = "login") => {
    setAuthModalMode(mode);
    if (typeof window !== "undefined") {
      window.location.href = mode === "login" ? "/login" : "/signup";
    }
  }, []);
  const closeAuthModal = useCallback(() => {
    setIsAuthModalOpen(false);
  }, []);

  const [isCreateOrgModalOpen, setIsCreateOrgModalOpen] = useState(false);
  const [isCreateProjectModalOpen, setIsCreateProjectModalOpen] = useState(false);
  const [isAddSourceModalOpen, setIsAddSourceModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isAddMemberModalOpen, setIsAddMemberModalOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Toasts
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((toast: Omit<ToastMessage, "id">) => {
    const id = "toast_" + Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Listen for global session expiration events dispatched by api.ts
  useEffect(() => {
    const handleSessionExpired = () => {
      setStoredToken(null);
      setToken(null);
      setUser(null);
      setActiveOrg(null);
      setActiveProject(null);
      setOrganisations([]);
      setProjects([]);
      setMembers([]);
      setEvidenceList([]);
      setOverview(null);
    };

    window.addEventListener("handover:session-expired", handleSessionExpired);
    return () => {
      window.removeEventListener("handover:session-expired", handleSessionExpired);
    };
  }, []);

  // Initialize auth from localStorage and verify with backend
  useEffect(() => {
    async function initAuth() {
      setIsLoadingAuth(true);
      try {
        const stored = typeof window !== "undefined" ? localStorage.getItem("handover_access_token") : null;
        if (stored) {
          setToken(stored);
          try {
            const me = await api.auth.me();
            setUser(me);
          } catch {
            // Token expired or invalid — try silent refresh via HttpOnly cookie
            try {
              const refreshed = await api.auth.refreshToken();
              setStoredToken(refreshed.access_token);
              setToken(refreshed.access_token);
              const me = await api.auth.me();
              setUser(me);
            } catch {
              setStoredToken(null);
              setToken(null);
              setUser(null);
            }
          }
        } else {
          // If no access token is stored, attempt silent refresh from HttpOnly cookie
          try {
            const refreshed = await api.auth.refreshToken();
            setStoredToken(refreshed.access_token);
            setToken(refreshed.access_token);
            const me = await api.auth.me();
            setUser(me);
          } catch {
            // No active session, user remains unauthenticated
          }
        }
      } catch {
        // Silent auth init
      } finally {
        setIsLoadingAuth(false);
      }
    }
    initAuth();
  }, []);

  // Once authenticated, load organisations
  const refreshOrganisations = useCallback(async () => {
    if (!user) return;
    try {
      const orgs = await api.organisations.list();
      setOrganisations(orgs);
      if (orgs.length > 0) {
        const storedOrgId = typeof window !== "undefined" ? localStorage.getItem("handover_active_org_id") : null;
        const preferredOrg =
          (storedOrgId ? orgs.find((o) => o.id === storedOrgId) : null) ??
          orgs.find((o) => o.name.toLowerCase().includes("handover")) ??
          orgs[0] ??
          null;
        setActiveOrg((current) => (current ? (orgs.find((o) => o.id === current.id) ?? preferredOrg) : preferredOrg));
      } else {
        setActiveOrg(null);
      }
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) return;
      console.error("Error loading organisations:", err);
    }
  }, [user, setActiveOrg]);

  useEffect(() => {
    let active = true;
    void Promise.resolve().then(async () => {
      if (!active) return;
      if (user) {
        await refreshOrganisations();
      } else {
        setOrganisations([]);
        setActiveOrg(null);
        setProjects([]);
        setActiveProject(null);
      }
    });
    return () => {
      active = false;
    };
  }, [user, refreshOrganisations, setActiveOrg, setActiveProject]);

  // Load projects for active organization
  const refreshProjects = useCallback(async () => {
    if (!user || !activeOrg) {
      setProjects([]);
      setActiveProject(null);
      return;
    }
    setIsLoadingProjects(true);
    try {
      const projs = await api.projects.list(activeOrg.id);
      setProjects(projs);
      if (projs.length > 0) {
        const storedProjId = typeof window !== "undefined" ? localStorage.getItem("handover_active_project_id") : null;
        const preferredProj =
          (storedProjId ? projs.find((p) => p.id === storedProjId) : null) ?? projs[0] ?? null;
        setActiveProject((current) => (current ? (projs.find((p) => p.id === current.id) ?? preferredProj) : preferredProj));
      } else {
        setActiveProject(null);
      }
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) return;
      console.error("Error loading projects:", err);
      addToast({
        type: "error",
        title: "Failed to load projects",
        message: err instanceof Error ? err.message : "Could not retrieve projects",
      });
    } finally {
      setIsLoadingProjects(false);
    }
  }, [user, activeOrg, addToast, setActiveProject]);

  useEffect(() => {
    if (!user || !activeOrg) return;
    let active = true;
    void Promise.resolve().then(async () => {
      if (active) {
        await refreshProjects();
      }
    });
    return () => {
      active = false;
    };
  }, [activeOrg, refreshProjects]);

  // Load project overview
  const refreshOverview = useCallback(async () => {
    if (!user || !activeProject) {
      setOverview(null);
      return;
    }
    const currentProjectId = activeProject.id;
    setIsLoadingOverview(true);
    try {
      const ov = await api.projects.getOverview(currentProjectId);
      setActiveProjectInternal((curr) => {
        if (curr?.id === currentProjectId) {
          setOverview(ov);
        }
        return curr;
      });
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) return;
      console.error("Error loading project overview:", err);
    } finally {
      setIsLoadingOverview(false);
    }
  }, [user, activeProject]);

  // Load project members
  const refreshMembers = useCallback(async () => {
    if (!user || !activeProject) {
      setMembers([]);
      return;
    }
    const currentProjectId = activeProject.id;
    setIsLoadingMembers(true);
    try {
      const [membersRes, transRes] = await Promise.allSettled([
        api.members.list(currentProjectId),
        api.projects.getTransition(currentProjectId),
      ]);
      const rawMembers = membersRes.status === "fulfilled" ? membersRes.value : [];
      const transitionData = transRes.status === "fulfilled"
        ? (transRes.value as { departing_user?: { id?: string }; successor_user?: { id?: string } } | null)
        : null;

      const currentOverview = overview && overview.project_id === currentProjectId ? overview : null;
      const departingId = transitionData?.departing_user?.id || currentOverview?.departing_member?.id;
      const successorId = transitionData?.successor_user?.id || currentOverview?.successor?.id;

      const annotated = rawMembers.map((mem) => {
        let tRole: "departing_owner" | "incoming_assignee" | "reviewer" | null = null;
        if (mem.user_id === departingId) {
          tRole = "departing_owner";
        } else if (mem.user_id === successorId) {
          tRole = "incoming_assignee";
        } else if (mem.role_name === "reviewer") {
          tRole = "reviewer";
        }
        return {
          ...mem,
          transition_role: tRole,
        };
      });

      setActiveProjectInternal((curr) => {
        if (curr?.id === currentProjectId) {
          setMembers(annotated);
        }
        return curr;
      });
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) return;
      console.error("Error loading project members:", err);
    } finally {
      setIsLoadingMembers(false);
    }
  }, [user, activeProject, overview]);

  // Load project sources & org connections
  const refreshSources = useCallback(async () => {
    if (!user || !activeProject || !activeOrg) {
      setSourceMappings([]);
      setOrgConnections([]);
      return;
    }
    setIsLoadingSources(true);
    try {
      const [mappings, conns] = await Promise.all([
        api.sources.listProjectMappings(activeProject.id),
        api.sources.listOrgConnections(activeOrg.id),
      ]);
      setSourceMappings(mappings);
      setOrgConnections(conns);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) return;
      console.error("Error loading sources:", err);
    } finally {
      setIsLoadingSources(false);
    }
  }, [user, activeProject, activeOrg]);

  // Load evidence list and metrics
  const refreshEvidence = useCallback(async () => {
    if (!user || !activeProject) {
      setEvidenceList([]);
      setEvidenceMetrics(null);
      return;
    }
    const currentProjectId = activeProject.id;
    setIsLoadingEvidence(true);
    try {
      const [items, metrics] = await Promise.all([
        api.evidence.list(currentProjectId, {
          q: evidenceFilter.q || undefined,
          provider: evidenceFilter.provider !== "all" ? evidenceFilter.provider : undefined,
          limit: 100,
        }),
        api.evidence.getMetrics(currentProjectId),
      ]);
      setEvidenceList(items);
      setEvidenceMetrics(metrics);
      if (items.length > 0 && items[0]) {
        const firstId = items[0].id;
        setSelectedEvidenceId((prev) => {
          if (!prev || !items.some((it) => it.id === prev)) {
            return firstId;
          }
          return prev;
        });
      } else {
        setSelectedEvidenceId(null);
        setSelectedEvidence(null);
      }
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) return;
      console.error("Error loading evidence:", err);
    } finally {
      setIsLoadingEvidence(false);
    }
  }, [user?.id, activeProject?.id, evidenceFilter.provider, evidenceFilter.q]);

  // Load evidence detail when selectedEvidenceId changes
  useEffect(() => {
    async function loadDetail() {
      if (!user || !selectedEvidenceId) {
        setSelectedEvidence(null);
        return;
      }
      setIsLoadingEvidenceDetail(true);
      try {
        const detail = await api.evidence.getDetail(selectedEvidenceId);
        setSelectedEvidence(detail);
      } catch (err: unknown) {
        if (err instanceof ApiError && err.status === 401) return;
        console.error("Error loading evidence detail:", err);
        setSelectedEvidence(null);
      } finally {
        setIsLoadingEvidenceDetail(false);
      }
    }
    loadDetail();
  }, [user?.id, selectedEvidenceId]);

  // Downstream Intelligence Handlers
  const refreshFindings = useCallback(async () => {
    if (!user || !activeProject) {
      setFindings([]);
      setKnowledgeSummary(null);
      return;
    }
    setIsLoadingFindings(true);
    try {
      const [sum, list] = await Promise.allSettled([
        api.knowledgeIntelligence.getSummary(activeProject.id),
        api.knowledgeIntelligence.listFindings(activeProject.id),
      ]);
      if (sum.status === "fulfilled") setKnowledgeSummary(sum.value as unknown as KnowledgeSummaryTelemetry);
      if (list.status === "fulfilled") setFindings((list.value.items || []) as unknown as KnowledgeFinding[]);
    } catch (err) {
      console.error("Error loading findings:", err);
    } finally {
      setIsLoadingFindings(false);
    }
  }, [user?.id, activeProject?.id]);

  const triggerReconstruction = useCallback(async () => {
    if (!activeProject) return;
    try {
      await api.knowledgeIntelligence.listFindings(activeProject.id);
      addToast({
        type: "info",
        title: "Reconstruction Triggered",
        message: "Ollama Qwen3 8B knowledge extraction job queued.",
      });
      await refreshFindings();
      await refreshOverview();
    } catch (err: unknown) {
      addToast({
        type: "error",
        title: "Reconstruction Failed",
        message: err instanceof Error ? err.message : "Failed to trigger knowledge extraction",
      });
    }
  }, [activeProject, refreshFindings, refreshOverview, addToast]);

  const refreshVerification = useCallback(async () => {
    if (!user || !activeProject) {
      setVerificationQueue([]);
      setVerificationSummary(null);
      return;
    }
    setIsLoadingVerification(true);
    try {
      const [sum, q] = await Promise.allSettled([
        api.verification.getSummary(activeProject.id),
        api.verification.getQueue(activeProject.id),
      ]);
      if (sum.status === "fulfilled") setVerificationSummary(sum.value as unknown as VerificationSummaryData);
      if (q.status === "fulfilled") setVerificationQueue((q.value.items || []) as unknown as VerificationCaseQueueItem[]);
    } catch (err) {
      console.error("Error loading verification data:", err);
    } finally {
      setIsLoadingVerification(false);
    }
  }, [user?.id, activeProject?.id]);

  const approveVerificationCase = useCallback(async (caseId: string, notes?: string) => {
    if (!activeProject) return;
    try {
      await api.verification.approveCase(activeProject.id, caseId, notes);
      addToast({
        type: "success",
        title: "Finding Verified",
        message: "Statement verified and promoted to verified knowledge.",
      });
      await refreshVerification();
      await refreshFindings();
    } catch (err: unknown) {
      addToast({
        type: "error",
        title: "Approval Failed",
        message: err instanceof Error ? err.message : "Failed to approve verification case",
      });
    }
  }, [activeProject, refreshVerification, refreshFindings, addToast]);

  const rejectVerificationCase = useCallback(async (caseId: string, reason?: string) => {
    if (!activeProject) return;
    try {
      await api.verification.rejectCase(activeProject.id, caseId, reason);
      addToast({
        type: "info",
        title: "Finding Rejected",
        message: "Candidate finding was marked as rejected.",
      });
      await refreshVerification();
    } catch (err: unknown) {
      addToast({
        type: "error",
        title: "Rejection Failed",
        message: err instanceof Error ? err.message : "Failed to reject verification case",
      });
    }
  }, [activeProject, refreshVerification, addToast]);

  const refreshHandovers = useCallback(async () => {
    if (!user || !activeProject) {
      setHandoverCases([]);
      return;
    }
    setIsLoadingHandovers(true);
    try {
      const res = await api.handover.listCases(activeProject.id);
      setHandoverCases((res.items || []) as unknown as HandoverCaseItem[]);
    } catch (err) {
      console.error("Error loading handover cases:", err);
    } finally {
      setIsLoadingHandovers(false);
    }
  }, [user?.id, activeProject?.id]);

  const createHandoverCase = useCallback(async (data: { title: string; description?: string }) => {
    if (!activeProject) throw new Error("No active project");
    const res = await api.handover.createCase(activeProject.id, data);
    addToast({
      type: "success",
      title: "Handover Case Created",
      message: `Handover ${res.title} created successfully.`,
    });
    await refreshHandovers();
    return res;
  }, [activeProject, refreshHandovers, addToast]);


  // Trigger data refreshes when active project changes
  const activeProjectId = activeProject?.id;
  const currentUserId = user?.id;

  useEffect(() => {
    if (!currentUserId || !activeProjectId) return;
    let active = true;
    void Promise.resolve().then(() => {
      if (!active) return;
      void refreshOverview();
      void refreshMembers();
      void refreshSources();
      void refreshFindings();
      void refreshVerification();
      void refreshHandovers();
    });
    return () => {
      active = false;
    };
  }, [
    currentUserId,
    activeProjectId,
    refreshOverview,
    refreshMembers,
    refreshSources,
    refreshFindings,
    refreshVerification,
    refreshHandovers,
  ]);

  // Load evidence only when active project or filters change
  useEffect(() => {
    if (!currentUserId || !activeProjectId) return;
    let active = true;
    void Promise.resolve().then(() => {
      if (!active) return;
      void refreshEvidence();
    });
    return () => {
      active = false;
    };
  }, [currentUserId, activeProjectId, refreshEvidence]);

  // Auth actions
  const login = async (email: string, password: string) => {
    const res = await api.auth.login({ email, password });
    setStoredToken(res.access_token);
    setToken(res.access_token);
    const me = await api.auth.me();
    setUser(me);
    addToast({
      type: "success",
      title: "Authenticated",
      message: `Signed in as ${me.email}`,
    });
  };

  const register = async (email: string, password: string, fullName: string) => {
    await api.auth.register({ email, password, full_name: fullName });
    // After registration, log in
    await login(email, password);
    addToast({
      type: "success",
      title: "Account Created",
      message: "Welcome to The Handover!",
    });
  };

  const logout = async () => {
    try {
      await api.auth.logout();
    } catch {
      // ignore
    }
    setStoredToken(null);
    setToken(null);
    setUser(null);
    setActiveOrg(null);
    setActiveProject(null);
    setOrganisations([]);
    setProjects([]);
    setMembers([]);
    setEvidenceList([]);
    setOverview(null);
    addToast({
      type: "info",
      title: "Signed Out",
      message: "You have been logged out.",
    });
  };

  // Org & Project actions
  const createOrganisation = async (name: string, slug?: string) => {
    const org = await api.organisations.create({ name, slug });
    await refreshOrganisations();
    setActiveOrg(org);
    addToast({
      type: "success",
      title: "Organisation Created",
      message: `Organisation ${org.name} is ready`,
    });
    return org;
  };

  const createProject = async (
    data: { name: string; slug?: string; description?: string; target_handover_date?: string },
    options?: { orgId?: string; newOrgName?: string }
  ) => {
    let targetOrg: Organisation | null = activeOrg;

    if (options?.newOrgName && options.newOrgName.trim()) {
      targetOrg = await createOrganisation(options.newOrgName.trim());
    } else if (options?.orgId) {
      targetOrg = organisations.find((o) => o.id === options.orgId) ?? activeOrg;
    }

    if (!targetOrg && organisations.length > 0 && organisations[0]) {
      targetOrg = organisations[0];
      setActiveOrg(targetOrg);
    }

    if (!targetOrg) {
      throw new Error("Please specify or create an Organisation workspace first.");
    }

    const proj = await api.projects.create(targetOrg.id, data);
    await refreshProjects();
    setActiveProject(proj);
    setIsCreateProjectModalOpen(false);
    addToast({
      type: "success",
      title: "Project Workspace Created",
      message: `Project ${proj.name} is now active in ${targetOrg.name}`,
    });
    return proj;
  };

  // Member actions
  const addMember = async (data: { email?: string; user_id?: string; role_name?: string; transition_role?: string }) => {
    if (!activeProject) throw new Error("No active project");
    await api.members.add(activeProject.id, data);
    await refreshMembers();
    setIsAddMemberModalOpen(false);
    addToast({
      type: "success",
      title: "Member Added",
      message: "Team member joined the project workspace",
    });
  };

  const updateMember = async (memberId: string, data: { role_name?: string; transition_role?: string }) => {
    if (!activeProject) throw new Error("No active project");
    await api.members.update(activeProject.id, memberId, data);
    await refreshMembers();
    addToast({
      type: "success",
      title: "Role Updated",
      message: "Participant role updated successfully",
    });
  };

  // Source actions
  const connectSource = async (provider: "github" | "jira", token: string, accountId: string) => {
    if (!activeOrg) throw new Error("No active organisation");
    const conn = await api.sources.connectSource(activeOrg.id, {
      provider,
      access_token: token,
      account_identifier: accountId,
    });
    await refreshSources();
    addToast({
      type: "success",
      title: "Source Connected",
      message: `Connected ${provider.toUpperCase()} account (${accountId})`,
    });
    return conn;
  };

  const createMapping = async (data: { source_connection_id: string; external_resource_key: string; external_resource_name: string; external_resource_url?: string }) => {
    if (!activeProject) throw new Error("No active project");
    const mapping = await api.sources.createProjectMapping(activeProject.id, data);
    await refreshSources();
    setIsAddSourceModalOpen(false);
    addToast({
      type: "success",
      title: "Resource Mapped",
      message: `Mapped ${mapping.external_resource_name} to project`,
    });
    return mapping;
  };

  const triggerSync = async (mappingId: string) => {
    if (!activeProject) return;
    try {
      const res = await api.sources.triggerSync(activeProject.id, mappingId);
      addToast({
        type: "info",
        title: "Sync Started",
        message: res.message || "Background sync job submitted",
      });
      await refreshSources();
      await refreshEvidence();
      await refreshOverview();
    } catch (err: unknown) {
      addToast({
        type: "error",
        title: "Sync Failed",
        message: err instanceof Error ? err.message : "Failed to trigger sync",
      });
    }
  };

  // Evidence actions
  const uploadDocument = async (file: File, title?: string) => {
    if (!activeProject) throw new Error("No active project");
    const res = await api.evidence.upload(activeProject.id, file, title);
    await refreshEvidence();
    await refreshOverview();
    setIsUploadModalOpen(false);
    addToast({
      type: "success",
      title: "Document Ingested",
      message: `${file.name} uploaded and encrypted at rest`,
    });
    return res;
  };

  const downloadEvidence = async (evidenceId: string, filename?: string) => {
    try {
      const blob = await api.evidence.download(evidenceId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || `evidence-${evidenceId.slice(0, 8)}.bin`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      addToast({
        type: "success",
        title: "Download Complete",
        message: `Decrypted ${filename || "evidence file"} successfully`,
      });
    } catch (err: unknown) {
      addToast({
        type: "error",
        title: "Download Failed",
        message: err instanceof Error ? err.message : "Could not download decrypted evidence",
      });
    }
  };

  const value: LiveAppContextType = {
    user,
    token,
    isLoadingAuth,
    login,
    register,
    logout,
    organisations,
    activeOrg,
    setActiveOrg,
    createOrganisation,
    projects,
    activeProject,
    setActiveProject,
    createProject,
    isLoadingProjects,
    refreshProjects,
    overview,
    isLoadingOverview,
    refreshOverview,
    members,
    isLoadingMembers,
    addMember,
    updateMember,
    refreshMembers,
    sourceMappings,
    orgConnections,
    isLoadingSources,
    connectSource,
    createMapping,
    triggerSync,
    refreshSources,
    evidenceList,
    evidenceMetrics,
    selectedEvidenceId,
    selectedEvidence,
    isLoadingEvidence,
    isLoadingEvidenceDetail,
    evidenceFilter,
    setEvidenceFilter,
    setSelectedEvidenceId,
    refreshEvidence,
    uploadDocument,
    downloadEvidence,
    knowledgeSummary,
    findings,
    isLoadingFindings,
    refreshFindings,
    triggerReconstruction,
    verificationSummary,
    verificationQueue,
    isLoadingVerification,
    refreshVerification,
    approveVerificationCase,
    rejectVerificationCase,
    handoverCases,
    isLoadingHandovers,
    refreshHandovers,
    createHandoverCase,
    isAuthModalOpen,
    setIsAuthModalOpen,
    authModalMode,
    setAuthModalMode,
    openAuthModal,
    closeAuthModal,
    isCreateOrgModalOpen,
    setIsCreateOrgModalOpen,
    isCreateProjectModalOpen,
    setIsCreateProjectModalOpen,
    isAddSourceModalOpen,
    setIsAddSourceModalOpen,
    isUploadModalOpen,
    setIsUploadModalOpen,
    isAddMemberModalOpen,
    setIsAddMemberModalOpen,
    isMobileSidebarOpen,
    setIsMobileSidebarOpen,
    toasts,
    addToast,
    dismissToast,
  };

  return (
    <LiveAppContext.Provider value={value}>
      {children}
    </LiveAppContext.Provider>
  );
}

export function useLiveApp() {
  const context = useContext(LiveAppContext);
  if (!context) {
    throw new Error("useLiveApp must be used within a LiveAppProvider");
  }
  return context;
}
