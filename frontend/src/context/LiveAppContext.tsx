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
import { supabase } from "../lib/supabase";
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
  setActiveProject: (project: Project) => void;
  createProject: (data: { name: string; slug?: string; description?: string; target_handover_date?: string }) => Promise<Project>;
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

  // UI state & modals
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
  const [activeOrg, setActiveOrg] = useState<Organisation | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
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
  const [isLoadingEvidence, setIsLoadingEvidence] = useState(false);
  const [isLoadingEvidenceDetail, setIsLoadingEvidenceDetail] = useState(false);
  const [evidenceFilter, setEvidenceFilter] = useState<{ q: string; provider: string }>({
    q: "",
    provider: "all",
  });

  // Modals & UI
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
            // Token expired or invalid
            setStoredToken(null);
            setToken(null);
            setUser(null);
          }
        }
      } catch (err) {
        console.error("Auth init error:", err);
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
        setActiveOrg((current) => (current ? (orgs.find((o) => o.id === current.id) ?? orgs[0] ?? null) : (orgs[0] ?? null)));
      } else {
        setActiveOrg(null);
      }
    } catch (err) {
      console.error("Error loading organisations:", err);
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      refreshOrganisations();
    } else {
      setOrganisations([]);
      setActiveOrg(null);
      setProjects([]);
      setActiveProject(null);
    }
  }, [user, refreshOrganisations]);

  // Load projects for active organization
  const refreshProjects = useCallback(async () => {
    if (!activeOrg) {
      setProjects([]);
      setActiveProject(null);
      return;
    }
    setIsLoadingProjects(true);
    try {
      const projs = await api.projects.list(activeOrg.id);
      setProjects(projs);
      if (projs.length > 0) {
        setActiveProject((current) => (current ? (projs.find((p) => p.id === current.id) ?? projs[0] ?? null) : (projs[0] ?? null)));
      } else {
        setActiveProject(null);
      }
    } catch (err: any) {
      console.error("Error loading projects:", err);
      addToast({
        type: "error",
        title: "Failed to load projects",
        message: err.message || "Could not retrieve projects",
      });
    } finally {
      setIsLoadingProjects(false);
    }
  }, [activeOrg, addToast]);

  useEffect(() => {
    if (activeOrg) {
      refreshProjects();
    }
  }, [activeOrg, refreshProjects]);

  // Load project overview
  const refreshOverview = useCallback(async () => {
    if (!activeProject) {
      setOverview(null);
      return;
    }
    setIsLoadingOverview(true);
    try {
      const ov = await api.projects.getOverview(activeProject.id);
      setOverview(ov);
    } catch (err: any) {
      console.error("Error loading project overview:", err);
    } finally {
      setIsLoadingOverview(false);
    }
  }, [activeProject]);

  // Load project members
  const refreshMembers = useCallback(async () => {
    if (!activeProject) {
      setMembers([]);
      return;
    }
    setIsLoadingMembers(true);
    try {
      const m = await api.members.list(activeProject.id);
      setMembers(m);
    } catch (err: any) {
      console.error("Error loading project members:", err);
    } finally {
      setIsLoadingMembers(false);
    }
  }, [activeProject]);

  // Load project sources & org connections
  const refreshSources = useCallback(async () => {
    if (!activeProject || !activeOrg) {
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
    } catch (err: any) {
      console.error("Error loading sources:", err);
    } finally {
      setIsLoadingSources(false);
    }
  }, [activeProject, activeOrg]);

  // Load evidence list and metrics
  const refreshEvidence = useCallback(async () => {
    if (!activeProject) {
      setEvidenceList([]);
      setEvidenceMetrics(null);
      return;
    }
    setIsLoadingEvidence(true);
    try {
      const [items, metrics] = await Promise.all([
        api.evidence.list(activeProject.id, {
          q: evidenceFilter.q || undefined,
          provider: evidenceFilter.provider !== "all" ? evidenceFilter.provider : undefined,
        }),
        api.evidence.getMetrics(activeProject.id),
      ]);
      setEvidenceList(items);
      setEvidenceMetrics(metrics);
      if (items.length > 0 && !selectedEvidenceId && items[0]) {
        setSelectedEvidenceId(items[0].id);
      }
    } catch (err: any) {
      console.error("Error loading evidence:", err);
    } finally {
      setIsLoadingEvidence(false);
    }
  }, [activeProject, evidenceFilter, selectedEvidenceId]);

  // Load evidence detail when selectedEvidenceId changes
  useEffect(() => {
    async function loadDetail() {
      if (!selectedEvidenceId) {
        setSelectedEvidence(null);
        return;
      }
      setIsLoadingEvidenceDetail(true);
      try {
        const detail = await api.evidence.getDetail(selectedEvidenceId);
        setSelectedEvidence(detail);
      } catch (err: any) {
        console.error("Error loading evidence detail:", err);
        setSelectedEvidence(null);
      } finally {
        setIsLoadingEvidenceDetail(false);
      }
    }
    loadDetail();
  }, [selectedEvidenceId]);

  // Trigger data refreshes when active project changes
  useEffect(() => {
    if (activeProject) {
      refreshOverview();
      refreshMembers();
      refreshSources();
      refreshEvidence();
    }
  }, [activeProject, refreshOverview, refreshMembers, refreshSources, refreshEvidence]);

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
    setStoredToken(null);
    setToken(null);
    setUser(null);
    setActiveOrg(null);
    setActiveProject(null);
    setOrganisations([]);
    setProjects([]);
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

  const createProject = async (data: { name: string; slug?: string; description?: string; target_handover_date?: string }) => {
    if (!activeOrg) throw new Error("No active organisation selected");
    const proj = await api.projects.create(activeOrg.id, data);
    await refreshProjects();
    setActiveProject(proj);
    setIsCreateProjectModalOpen(false);
    addToast({
      type: "success",
      title: "Project Created",
      message: `Project ${proj.name} has been initialised`,
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
    } catch (err: any) {
      addToast({
        type: "error",
        title: "Sync Failed",
        message: err.message || "Failed to trigger sync",
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
    } catch (err: any) {
      addToast({
        type: "error",
        title: "Download Failed",
        message: err.message || "Could not download decrypted evidence",
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
