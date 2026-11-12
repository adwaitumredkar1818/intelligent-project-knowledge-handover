"use client";

import React, {
  createContext,
  useContext,
  useState,
  useMemo,
  useCallback,
  type ReactNode,
} from "react";
import type {
  Project,
  TeamMember,
  SourceConnection,
  EvidenceItem,
  EvidenceFilterState,
  SourceProvider,
  EvidenceRecordType,
  EvidenceProcessingStatus,
} from "../types";
import {
  DEMO_PROJECTS,
  DEMO_MEMBERS,
  DEMO_SOURCES,
  DEMO_EVIDENCE,
} from "../data";

export interface ToastMessage {
  id: string;
  type: "success" | "info" | "warning" | "error";
  title: string;
  message: string;
}

interface PrototypeContextType {
  // Projects
  projects: Project[];
  selectedProject: Project;
  setSelectedProjectById: (id: string) => void;
  createProject: (newProject: Omit<Project, "id" | "createdAt" | "lastActivityAt" | "membersCount" | "sourcesCount" | "evidenceCount">) => void;

  // Team Members
  members: TeamMember[];
  addMember: (member: Omit<TeamMember, "id" | "joinedAt" | "avatarInitials">) => void;
  updateMember: (id: string, updates: Partial<TeamMember>) => void;
  removeMember: (id: string) => void;
  setTransitionRoles: (departingId: string, successorId: string, scope?: string) => boolean;

  // Sources
  sources: SourceConnection[];
  triggerSourceSync: (sourceId: string) => void;
  addMockSource: (provider: SourceProvider, accountIdentifier: string) => void;

  // Evidence
  evidenceList: EvidenceItem[];
  selectedEvidenceId: string | null;
  selectedEvidence: EvidenceItem | null;
  setSelectedEvidenceId: (id: string | null) => void;
  evidenceFilters: EvidenceFilterState;
  setEvidenceFilters: React.Dispatch<React.SetStateAction<EvidenceFilterState>>;
  addLocalDocumentPreview: (file: { name: string; size: number; type: string }) => void;

  // Search & Modals
  isGlobalSearchOpen: boolean;
  setIsGlobalSearchOpen: (open: boolean) => void;
  isCreateProjectModalOpen: boolean;
  setIsCreateProjectModalOpen: (open: boolean) => void;
  isAddSourceModalOpen: boolean;
  setIsAddSourceModalOpen: (open: boolean) => void;
  isUploadModalOpen: boolean;
  setIsUploadModalOpen: (open: boolean) => void;
  selectedSourceForModal: SourceConnection | null;
  setSelectedSourceForModal: (source: SourceConnection | null) => void;

  // Mobile navigation
  isMobileSidebarOpen: boolean;
  setIsMobileSidebarOpen: (open: boolean) => void;

  // Toasts
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, "id">) => void;
  dismissToast: (id: string) => void;
}

const defaultFilterState: EvidenceFilterState = {
  searchQuery: "",
  selectedProvider: "all",
  selectedRecordType: "all",
  selectedStatus: "all",
  sortBy: "newest",
};

const PrototypeContext = createContext<PrototypeContextType | undefined>(undefined);

export function PrototypeProvider({ children }: { children: ReactNode }) {
  // State initialization with demo fixtures
  const [projects, setProjects] = useState<Project[]>(DEMO_PROJECTS);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(DEMO_PROJECTS[0]?.id || "proj-nexora-assist-001");
  const [members, setMembers] = useState<TeamMember[]>(DEMO_MEMBERS);
  const [sources, setSources] = useState<SourceConnection[]>(DEMO_SOURCES);
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>(DEMO_EVIDENCE);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(DEMO_EVIDENCE[0]?.id || null);
  const [evidenceFilters, setEvidenceFilters] = useState<EvidenceFilterState>(defaultFilterState);

  // Modals & UI overlays
  const [isGlobalSearchOpen, setIsGlobalSearchOpen] = useState(false);
  const [isCreateProjectModalOpen, setIsCreateProjectModalOpen] = useState(false);
  const [isAddSourceModalOpen, setIsAddSourceModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedSourceForModal, setSelectedSourceForModal] = useState<SourceConnection | null>(null);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Toasts
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((toast: Omit<ToastMessage, "id">) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const selectedProject = useMemo(() => {
    return projects.find((p) => p.id === selectedProjectId) || projects[0]!;
  }, [projects, selectedProjectId]);

  const selectedEvidence = useMemo(() => {
    if (!selectedEvidenceId) return null;
    return evidenceList.find((e) => e.id === selectedEvidenceId) || null;
  }, [evidenceList, selectedEvidenceId]);

  const setSelectedProjectById = useCallback((id: string) => {
    const proj = projects.find((p) => p.id === id);
    if (proj) {
      setSelectedProjectId(id);
      addToast({
        type: "info",
        title: "Workspace Switched",
        message: `Switched active workspace to "${proj.name}".`,
      });
    }
  }, [projects, addToast]);

  const createProject = useCallback(
    (newProjectData: Omit<Project, "id" | "createdAt" | "lastActivityAt" | "membersCount" | "sourcesCount" | "evidenceCount">) => {
      const newId = `proj-${newProjectData.slug}-${Date.now().toString(36)}`;
      const newProj: Project = {
        ...newProjectData,
        id: newId,
        createdAt: new Date().toISOString(),
        lastActivityAt: "Just now",
        membersCount: 1,
        sourcesCount: 0,
        evidenceCount: 0,
      };

      setProjects((prev) => [newProj, ...prev]);
      setSelectedProjectId(newId);
      addToast({
        type: "success",
        title: "Project Workspace Created",
        message: `"${newProj.name}" has been added to local state (Sample Data Only).`,
      });
    },
    [addToast]
  );

  const addMember = useCallback(
    (newMemberData: Omit<TeamMember, "id" | "joinedAt" | "avatarInitials">) => {
      const initials = newMemberData.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2);

      const newMember: TeamMember = {
        ...newMemberData,
        id: `mem-${Date.now().toString(36)}`,
        joinedAt: new Date().toISOString().split("T")[0] || "2026-11-12",
        avatarInitials: initials || "TM",
      };

      setMembers((prev) => [...prev, newMember]);
      addToast({
        type: "success",
        title: "Team Member Added",
        message: `${newMember.name} added with role "${newMember.role}".`,
      });
    },
    [addToast]
  );

  const updateMember = useCallback(
    (id: string, updates: Partial<TeamMember>) => {
      setMembers((prev) =>
        prev.map((m) => (m.id === id ? { ...m, ...updates } : m))
      );
      addToast({
        type: "info",
        title: "Member Updated",
        message: "Team member responsibilities updated.",
      });
    },
    [addToast]
  );

  const removeMember = useCallback(
    (id: string) => {
      const target = members.find((m) => m.id === id);
      if (target?.transitionDesignation === "departing_owner") {
        addToast({
          type: "error",
          title: "Cannot Remove Member",
          message: "Reassign the departing knowledge owner role before removing this member.",
        });
        return;
      }

      setMembers((prev) => prev.filter((m) => m.id !== id));
      addToast({
        type: "info",
        title: "Member Removed",
        message: `${target?.name || "Member"} removed from sample workspace.`,
      });
    },
    [members, addToast]
  );

  const setTransitionRoles = useCallback(
    (departingId: string, successorId: string, scope?: string) => {
      if (departingId === successorId) {
        addToast({
          type: "error",
          title: "Invalid Transition Configuration",
          message: "The departing member and incoming successor must be different individuals.",
        });
        return false;
      }

      const departing = members.find((m) => m.id === departingId);
      const successor = members.find((m) => m.id === successorId);

      if (!departing || !successor) {
        addToast({
          type: "error",
          title: "Member Not Found",
          message: "Selected transition participants could not be found.",
        });
        return false;
      }

      // Update members designation
      setMembers((prev) =>
        prev.map((m) => {
          if (m.id === departingId) return { ...m, transitionDesignation: "departing_owner" };
          if (m.id === successorId) return { ...m, transitionDesignation: "successor" };
          if (m.transitionDesignation !== "standard") return { ...m, transitionDesignation: "standard" };
          return m;
        })
      );

      // Update selected project transition
      setProjects((prev) =>
        prev.map((p) => {
          if (p.id === selectedProjectId) {
            return {
              ...p,
              transition: {
                ...p.transition,
                departingMember: {
                  id: departing.id,
                  name: departing.name,
                  role: departing.role,
                  email: departing.email,
                },
                successor: {
                  id: successor.id,
                  name: successor.name,
                  role: successor.role,
                  email: successor.email,
                },
                handoverScope: scope || p.transition.handoverScope,
              },
            };
          }
          return p;
        })
      );

      addToast({
        type: "success",
        title: "Transition Updated",
        message: `${departing.name} (Departing) → ${successor.name} (Successor).`,
      });
      return true;
    },
    [members, selectedProjectId, addToast]
  );

  const triggerSourceSync = useCallback(
    (sourceId: string) => {
      const source = sources.find((s) => s.id === sourceId);
      if (!source) return;

      if (source.provider === "slack") {
        addToast({
          type: "warning",
          title: "Source Unavailable",
          message: "Slack integration is not enabled in this prototype.",
        });
        return;
      }

      // Simulate syncing state
      setSources((prev) =>
        prev.map((s) => (s.id === sourceId ? { ...s, status: "syncing" } : s))
      );

      addToast({
        type: "info",
        title: "Synchronisation Initiated",
        message: `Simulating background sync for ${source.provider.toUpperCase()}...`,
      });

      setTimeout(() => {
        setSources((prev) =>
          prev.map((s) =>
            s.id === sourceId
              ? {
                  ...s,
                  status: "connected",
                  lastSyncedAt: "Just now",
                }
              : s
          )
        );
        addToast({
          type: "success",
          title: "Sync Completed",
          message: `Ingested latest changes from ${source.provider.toUpperCase()} (Simulated).`,
        });
      }, 1500);
    },
    [sources, addToast]
  );

  const addMockSource = useCallback(
    (provider: SourceProvider, accountIdentifier: string) => {
      const newSource: SourceConnection = {
        id: `src-${provider}-${Date.now().toString(36)}`,
        provider,
        accountIdentifier,
        connectedByName: "Current User",
        status: "connected",
        scopes: provider === "github" ? ["repo", "read:org"] : ["read:jira-work"],
        isShared: true,
        lastSyncedAt: "Just now",
        mappings: [
          {
            id: `map-${Date.now().toString(36)}`,
            sourceConnectionId: `src-${provider}-${Date.now().toString(36)}`,
            provider,
            externalResourceId: provider === "github" ? "nexora-tech/new-repo" : "NEW-PROJECT",
            externalResourceName: provider === "github" ? "new-repo" : "New Jira Project",
            lastSyncedAt: "Just now",
            status: "active",
            recordsCount: 5,
          },
        ],
        stats: {
          totalRecords: 5,
          lastJobType: "full_sync",
          lastDurationSeconds: 1.2,
        },
      };

      setSources((prev) => [...prev, newSource]);
      addToast({
        type: "success",
        title: "Source Connection Added",
        message: `Connected ${provider.toUpperCase()}: ${accountIdentifier} (Sample Prototype).`,
      });
    },
    [addToast]
  );

  const addLocalDocumentPreview = useCallback(
    (file: { name: string; size: number; type: string }) => {
      const isDocx = file.name.endsWith(".docx");
      const provider: SourceProvider = isDocx ? "docx" : "pdf";
      const recordType: EvidenceRecordType = "document";
      const status: EvidenceProcessingStatus = "extracted";

      const newEvidence: EvidenceItem = {
        id: `evi-local-${Date.now().toString(36)}`,
        name: file.name,
        source: provider,
        recordType,
        author: "Current User",
        timestamp: "Just now",
        ingestedAt: new Date().toISOString(),
        status,
        originalSource: {
          provider,
          containerName: `local/uploads/${provider}`,
          resourceName: file.name,
          externalId: `local:${file.name}`,
        },
        extractedContent: {
          excerpt: `[Sample Local Preview] Extracted content from local file ${file.name} (${(file.size / 1024).toFixed(1)} KB). In a production environment, this file would undergo AES-256 encryption at rest and PyMuPDF/DOCX extraction.`,
          pageNumber: 1,
          sectionTitle: "Executive Summary",
          fullTextPreview: `# ${file.name}\nSize: ${(file.size / 1024).toFixed(1)} KB\nSimulated OCR: Completed\n\nThis is an illustrative sample extraction preview demonstrating the 3-panel Evidence Workspace.`,
        },
        sourceReference: `REF-LOCAL-${file.name.slice(0, 8).toUpperCase()} [SAMPLE]`,
        relatedRecords: [],
        associatedKnowledge: [
          {
            id: `know-local-${Date.now()}`,
            category: "architecture",
            title: `Extracted Specifications: ${file.name}`,
            summary: "Extracted structural sections and technical decisions preview.",
            confidence: 0.95,
          },
        ],
        chunks: [
          {
            chunkIndex: 0,
            pageNumber: 1,
            sectionHeading: "Document Header",
            contentText: `Extracted content from ${file.name}. Validated format and calculated SHA-256 integrity checksum.`,
            tokenCount: 26,
          },
        ],
        metadata: {
          fileSizeBytes: file.size,
          mimeType: file.type || (isDocx ? "application/docx" : "application/pdf"),
          sha256Hash: "simulated_sha256_hash_value_for_prototype_only",
        },
      };

      setEvidenceList((prev) => [newEvidence, ...prev]);
      setSelectedEvidenceId(newEvidence.id);
      addToast({
        type: "success",
        title: "Document Preview Loaded",
        message: `"${file.name}" added to Evidence Library preview.`,
      });
    },
    [addToast]
  );

  return (
    <PrototypeContext.Provider
      value={{
        projects,
        selectedProject,
        setSelectedProjectById,
        createProject,

        members,
        addMember,
        updateMember,
        removeMember,
        setTransitionRoles,

        sources,
        triggerSourceSync,
        addMockSource,

        evidenceList,
        selectedEvidenceId,
        selectedEvidence,
        setSelectedEvidenceId,
        evidenceFilters,
        setEvidenceFilters,
        addLocalDocumentPreview,

        isGlobalSearchOpen,
        setIsGlobalSearchOpen,
        isCreateProjectModalOpen,
        setIsCreateProjectModalOpen,
        isAddSourceModalOpen,
        setIsAddSourceModalOpen,
        isUploadModalOpen,
        setIsUploadModalOpen,
        selectedSourceForModal,
        setSelectedSourceForModal,
        isMobileSidebarOpen,
        setIsMobileSidebarOpen,

        toasts,
        addToast,
        dismissToast,
      }}
    >
      {children}
    </PrototypeContext.Provider>
  );
}

export function usePrototype() {
  const context = useContext(PrototypeContext);
  if (!context) {
    throw new Error("usePrototype must be used within a PrototypeProvider");
  }
  return context;
}
