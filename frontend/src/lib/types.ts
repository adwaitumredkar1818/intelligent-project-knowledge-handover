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
  status: "planning" | "active" | "on_hold" | "completed" | "archived" | string;
  visibility?: "private" | "organisation";
  start_date?: string | null;
  target_completion_date?: string | null;
  target_handover_date?: string | null;
  created_at: string;
  updated_at: string;
  owner_id?: UUID;
  my_project_role?: string | null;
  effective_permissions?: string[];
}

export interface OrganisationMember {
  id: UUID;
  organisation_id: UUID;
  user_id: UUID;
  full_name: string;
  email: string;
  role_name: string;
  status: string;
  joined_at: string;
}

export interface ProjectMember {
  id: UUID;
  project_id: UUID;
  user_id: UUID;
  role_name: string;
  transition_role: "departing_owner" | "incoming_assignee" | "reviewer" | "observer" | null;
  created_at: string;
  user_full_name?: string | null;
  user_email?: string | null;
  full_name?: string | null;
  email?: string | null;
  status?: string;
  responsibility_description?: string | null;
  assigned_by_id?: UUID | null;
}

export interface ProjectTransition {
  id: UUID;
  project_id: UUID;
  departing_user: { id: UUID; full_name: string; email: string };
  successor_user: { id: UUID; full_name: string; email: string };
  workflow_stage: string;
  handover_scope?: string | null;
  source_scope?: string[] | null;
  capture_start_date?: string | null;
  capture_end_date?: string | null;
  context_notes?: string | null;
  created_at: string;
  updated_at: string;
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
  departing_member?: { id: UUID; full_name: string; email: string } | null;
  successor?: { id: UUID; full_name: string; email: string } | null;
  owner?: { id: UUID; full_name: string; email: string } | null;
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
  content_text?: string;
  content_preview?: string;
  char_length?: number;
  character_count?: number;
  word_count?: number;
  chunk_type?: string;
  section_title?: string | null;
  page_number?: number | null;
}

export interface EvidenceSummary {
  id: UUID;
  project_id: UUID;
  source_type: string;
  source_provider?: string;
  provider: string;
  category: string;
  title: string;
  original_filename?: string | null;
  mime_type?: string | null;
  file_size_bytes?: number | null;
  page_count?: number | null;
  source_url: string | null;
  author_name: string | null;
  source_author_identity?: string | null;
  content_hash: string;
  indexing_status: string;
  processing_status?: string;
  error_code?: string | null;
  error_message?: string | null;
  extracted_text_preview?: string | null;
  created_at: string;
  source_created_at: string | null;
}

export interface EvidenceDetail {
  id: UUID;
  project_id: UUID;
  organisation_id?: UUID;
  source_type: string;
  source_provider?: string;
  provider: string;
  category?: string;
  source_external_id?: string;
  title: string;
  original_filename?: string | null;
  mime_type?: string | null;
  file_size_bytes?: number | null;
  source_url: string | null;
  author_name: string | null;
  source_author_identity?: string | null;
  content_hash: string;
  acl_scope?: string;
  indexing_status: string;
  processing_status?: string;
  error_code?: string | null;
  error_message?: string | null;
  extraction_method?: string | null;
  page_count?: number | null;
  ocr_pages_count?: number;
  truncated_pages_count?: number;
  embedding_model?: string | null;
  index_version?: string | null;
  created_at: string;
  updated_at?: string;
  source_created_at: string | null;
  source_updated_at?: string | null;
  extracted_at?: string | null;
  extracted_text_preview?: string | null;
  extracted_content?: {
    char_count?: number;
    word_count?: number;
    extraction_warnings?: string[];
    extracted_text?: string;
  } | null;
  metadata_json?: Record<string, unknown>;
  can_download: boolean;
  download_url?: string | null;
  chunks: EvidenceChunkDetail[];
}

export interface EvidenceMetrics {
  total_items: number;
  by_type: Record<string, number>;
  by_indexing_status: Record<string, number>;
}


// ─── Downstream Platform Types ────────────────────────────────────────────────

export interface KnowledgeFinding {
  id: UUID;
  project_id: UUID;
  knowledge_domain: string;
  category: string;
  title: string;
  summary: string;
  confidence_score: number;
  epistemic_status: "extracted" | "interpreted" | "human_verified";
  review_status: "unreviewed" | "approved" | "rejected" | "disputed";
  evidence_citations_count: number;
  extracted_at: string;
  item_payload?: Record<string, unknown>;
  citations?: Array<{
    chunk_id: string;
    evidence_id: string;
    excerpt_text: string;
    similarity_score?: number;
  }>;
}

export interface KnowledgeDomainMetric {
  domain: string;
  total_findings: number;
  confidence_distribution: Record<string, number>;
  verified_percentage: number;
}

export interface KnowledgeSummaryTelemetry {
  total_findings: number;
  by_category: Record<string, number>;
  by_domain: Record<string, number>;
  verified_count: number;
  candidate_count: number;
  readiness_percentage?: number;
}

export interface TimelineStreamEvent {
  id: UUID;
  project_id: UUID;
  title: string;
  event_type: "decision" | "milestone" | "incident" | "commit" | "task" | string;
  event_timestamp: string;
  confidence: number;
  source_evidence_ids: string[];
  summary?: string;
}

export interface GraphNodeData {
  id: string;
  label: string;
  type: string;
  canonical_name: string;
  confidence: number;
  resolution_status: string;
  domain?: string;
  properties?: Record<string, unknown>;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  type: string;
  verification_status: string;
  confidence: number;
}

export interface KnowledgeGraphData {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
}

export interface VerificationCaseQueueItem {
  id: UUID;
  target_type: string;
  target_id: UUID;
  status: "pending_review" | "approved" | "rejected" | "unresolved";
  priority: "critical" | "high" | "medium" | "low";
  confidence_score: number;
  created_at: string;
  issue_count: number;
  assigned_to_user_id?: string;
  finding?: {
    title: string;
    summary: string;
    domain: string;
    epistemic_status: string;
  };
}

export interface VerificationSummaryData {
  total_cases: number;
  pending_review: number;
  approved: number;
  rejected: number;
  unresolved: number;
  conflicts_count: number;
  stale_count: number;
  handover_eligible_count: number;
}

export interface HandoverCaseItem {
  id: UUID;
  project_id: UUID;
  title: string;
  description?: string;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
  outgoing_owner_user_id?: string;
  incoming_owner_user_id?: string;
  readiness_score?: number;
}

export interface HandoverReadinessData {
  readiness_score: number;
  dimension_scores: Record<string, number>;
  unmet_requirements: string[];
  recommendations: string[];
}

export interface AuditEventItem {
  id: UUID;
  organisation_id: UUID;
  project_id?: UUID | null;
  user_id?: UUID | null;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  outcome: string;
  created_at: string;
  actor_name?: string | null;
  details?: Record<string, unknown> | null;
}
