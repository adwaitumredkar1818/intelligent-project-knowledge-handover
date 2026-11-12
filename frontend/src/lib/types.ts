export type UUID = string;

export interface User {
  id: UUID;
  email: string;
  full_name: string;
  is_active: boolean;
}

export interface Organisation {
  id: UUID;
  name: string;
  slug: string;
  created_at: string;
}

export interface Project {
  id: UUID;
  organisation_id: UUID;
  name: string;
  slug: string;
  description: string | null;
  status: "active" | "archived" | "completed";
  target_handover_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectMember {
  id: UUID;
  project_id: UUID;
  user_id: UUID;
  role_name: string;
  transition_role: "departing_owner" | "incoming_assignee" | "reviewer" | "observer" | null;
  created_at: string;
  user_full_name: string | null;
  user_email: string | null;
}

export interface ReadinessScoreCard {
  overall_readiness_pct: number;
  status: string;
  target_date: string | null;
  days_remaining: number | null;
}

export interface SourceOverviewCard {
  connected_count: number;
  active_count: number;
  failed_count: number;
  total_resources: number;
}

export interface EvidenceOverviewCard {
  total_evidence_items: number;
  indexed_chunks_count: number;
  last_ingested_at: string | null;
  providers_breakdown: Record<string, number>;
}

export interface KnowledgeOverviewCard {
  decisions_count: number;
  tasks_count: number;
  risks_count: number;
  responsibilities_count: number;
  dependencies_count: number;
  availability: string;
}

export interface AttentionItemCard {
  id: string;
  type: string;
  message: string;
  resource_id?: string | null;
}

export interface ProjectActivityCard {
  id: string;
  event_type: string;
  description: string;
  actor_name?: string | null;
  timestamp: string;
}

export interface ProjectOverview {
  project_id: UUID;
  project_name: string;
  status: string;
  target_handover_date: string | null;
  readiness: ReadinessScoreCard;
  sources: SourceOverviewCard;
  evidence: EvidenceOverviewCard;
  knowledge: KnowledgeOverviewCard;
  attention_items: AttentionItemCard[];
  recent_activity: ProjectActivityCard[];
}

export interface SourceConnection {
  id: UUID;
  organisation_id: UUID;
  provider: "github" | "jira" | "slack";
  display_name: string;
  status: string;
  last_synced_at: string | null;
}

export interface ProjectSourceMapping {
  id: UUID;
  organisation_id: UUID;
  project_id: UUID;
  source_connection_id: UUID;
  provider: "github" | "jira" | "slack";
  resource_type: string;
  external_resource_key: string;
  external_resource_name: string;
  external_resource_url: string | null;
  status: string;
  last_synced_at: string | null;
  last_sync_status: string | null;
  last_error_summary: string | null;
}

export interface EvidenceChunkDetail {
  id: UUID;
  chunk_index: number;
  content_preview: string;
  character_count: number;
}

export interface EvidenceSummary {
  id: UUID;
  project_id: UUID;
  source_type: string;
  provider: string;
  title: string;
  source_url: string | null;
  author_name: string | null;
  content_hash: string;
  indexing_status: string;
  created_at: string;
  source_created_at: string | null;
}

export interface EvidenceDetail {
  id: UUID;
  project_id: UUID;
  source_type: string;
  provider: string;
  title: string;
  source_url: string | null;
  author_name: string | null;
  content_hash: string;
  indexing_status: string;
  created_at: string;
  source_created_at: string | null;
  extracted_text_preview?: string | null;
  can_download: boolean;
  download_url?: string | null;
  chunks: EvidenceChunkDetail[];
}

export interface EvidenceMetrics {
  total_items: number;
  by_type: Record<string, number>;
  by_indexing_status: Record<string, number>;
}
