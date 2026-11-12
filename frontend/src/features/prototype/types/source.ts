export type SourceProvider = "github" | "jira" | "slack" | "pdf" | "docx";

export type ConnectionStatus = "connected" | "syncing" | "error" | "disabled" | "needs_reauth";

export interface ProjectSourceMapping {
  id: string;
  sourceConnectionId: string;
  provider: SourceProvider;
  externalResourceId: string;
  externalResourceName: string;
  lastSyncedAt?: string;
  status: "active" | "syncing" | "failed";
  recordsCount: number;
}

export interface SourceConnection {
  id: string;
  provider: SourceProvider;
  accountIdentifier: string;
  connectedByName: string;
  status: ConnectionStatus;
  scopes: string[];
  isShared: boolean;
  lastSyncedAt?: string;
  errorMessage?: string;
  requiresReauth?: boolean;
  mappings: ProjectSourceMapping[];
  stats?: {
    totalRecords: number;
    lastJobType?: string;
    lastDurationSeconds?: number;
  };
}
