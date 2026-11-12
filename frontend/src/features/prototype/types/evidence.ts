import type { SourceProvider } from "./source";

export type EvidenceRecordType =
  | "pull_request"
  | "issue"
  | "commit"
  | "document"
  | "task"
  | "note";

export type EvidenceProcessingStatus =
  | "extracted"
  | "indexed"
  | "pending_extraction"
  | "processing"
  | "failed";

export interface EvidenceChunk {
  chunkIndex: number;
  pageNumber?: number;
  sectionHeading?: string;
  contentText: string;
  tokenCount: number;
}

export interface RelatedEvidenceLink {
  id: string;
  name: string;
  source: SourceProvider;
  recordType: EvidenceRecordType;
}

export interface AssociatedKnowledgeItem {
  id: string;
  category: "decision" | "architecture" | "risk" | "task" | "dependency";
  title: string;
  summary: string;
  confidence: number;
}

export interface EvidenceItem {
  id: string;
  name: string;
  source: SourceProvider;
  recordType: EvidenceRecordType;
  author: string;
  timestamp: string;
  ingestedAt: string;
  status: EvidenceProcessingStatus;
  originalSource: {
    provider: SourceProvider;
    containerName: string;
    resourceName: string;
    externalUrl?: string;
    externalId: string;
  };
  extractedContent: {
    excerpt: string;
    pageNumber?: number;
    sectionTitle?: string;
    fullTextPreview?: string;
    diffSummary?: string;
    commitSha?: string;
    issueKey?: string;
    labels?: string[];
  };
  sourceReference: string;
  relatedRecords: RelatedEvidenceLink[];
  associatedKnowledge: AssociatedKnowledgeItem[];
  chunks: EvidenceChunk[];
  metadata?: {
    fileSizeBytes?: number;
    mimeType?: string;
    sha256Hash?: string;
  };
}

export interface EvidenceFilterState {
  searchQuery: string;
  selectedProvider: SourceProvider | "all";
  selectedRecordType: EvidenceRecordType | "all";
  selectedStatus: EvidenceProcessingStatus | "all";
  sortBy: "newest" | "oldest" | "title" | "author";
}

export interface EvidenceMetrics {
  totalRecords: number;
  byProvider: Record<SourceProvider, number>;
  byStatus: Record<EvidenceProcessingStatus, number>;
  totalDocuments: number;
  totalBytes: number;
}
