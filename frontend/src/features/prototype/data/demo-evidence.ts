import type { EvidenceItem } from "../types/evidence";

export const DEMO_EVIDENCE: EvidenceItem[] = [
  {
    id: "evi-001",
    name: "PR #104: Token-expiry checks and rotation handler",
    source: "github",
    recordType: "pull_request",
    author: "Alex Vance",
    timestamp: "2 hours ago",
    ingestedAt: "2026-11-12T13:45:00Z",
    status: "extracted",
    originalSource: {
      provider: "github",
      containerName: "nexora-tech/nexora-auth-service",
      resourceName: "pull/104",
      externalUrl: "https://github.com/nexora-tech/nexora-auth-service/pull/104",
      externalId: "pr:104",
    },
    extractedContent: {
      excerpt:
        "Reduces access token TTL to 15 minutes. Implements strict token-family rotation on refresh cookie exchange to mitigate session hijacking.",
      diffSummary: "+148 lines, -32 lines in auth/tokens.py and security/cookie.py",
      commitSha: "a9c2f81d4e",
      labels: ["security", "auth", "breaking-change"],
      fullTextPreview:
        "## Description\nImplements strict single-use refresh token rotation.\nWhen a refresh token is reused, all tokens belonging to that session family are immediately invalidated.\n\n## Rationale\nAligns platform with OAuth 2.1 BCP recommendations for single-page and SPA clients.",
    },
    sourceReference: "REF-GH-PR-104 [SAMPLE]",
    relatedRecords: [
      {
        id: "evi-004",
        name: "Auth architecture specification",
        source: "pdf",
        recordType: "document",
      },
      {
        id: "evi-005",
        name: "Commit: Refresh-token rotation",
        source: "github",
        recordType: "commit",
      },
    ],
    associatedKnowledge: [
      {
        id: "know-01",
        category: "decision",
        title: "Short-lived JWT Access Tokens (15m)",
        summary: "Enforces 15-minute expiration to reduce window of compromise.",
        confidence: 0.94,
      },
      {
        id: "know-02",
        category: "risk",
        title: "Token Family Revocation Cascade",
        summary: "Legitimate concurrent requests may trigger false-positive family revocation.",
        confidence: 0.81,
      },
    ],
    chunks: [
      {
        chunkIndex: 0,
        sectionHeading: "PR Overview & Rationale",
        contentText:
          "Reduces access token TTL to 15 minutes. Implements strict token-family rotation on refresh cookie exchange to mitigate session hijacking.",
        tokenCount: 42,
      },
      {
        chunkIndex: 1,
        sectionHeading: "Security Validation",
        contentText:
          "Added redis-backed blacklist lookup with 30s TTL buffer. Handled clock-skew across distributed pods.",
        tokenCount: 36,
      },
    ],
    metadata: {
      fileSizeBytes: 4820,
      sha256Hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    },
  },
  {
    id: "evi-002",
    name: "NXA-289: Password reset implementation and token dispatch",
    source: "jira",
    recordType: "task",
    author: "Emily Watson",
    timestamp: "3 hours ago",
    ingestedAt: "2026-11-12T12:30:00Z",
    status: "indexed",
    originalSource: {
      provider: "jira",
      containerName: "Nexora Assist Board",
      resourceName: "NXA-289",
      externalUrl: "https://nexora.atlassian.net/browse/NXA-289",
      externalId: "issue:NXA-289",
    },
    extractedContent: {
      excerpt:
        "Configured secure reset token generation using HMAC-SHA256 with 1-hour expiration. Integrated asynchronous email dispatcher worker.",
      issueKey: "NXA-289",
      labels: ["backend", "identity", "p1"],
      fullTextPreview:
        "Summary: Password reset implementation\nAssignee: Emily Watson\nStatus: In Review\nDescription:\nUsers requesting password reset receive a single-use signed link.\nReset tokens are invalidated upon consumption or password update.",
    },
    sourceReference: "REF-JIRA-NXA-289 [SAMPLE]",
    relatedRecords: [
      {
        id: "evi-006",
        name: "API implementation notes",
        source: "docx",
        recordType: "document",
      },
    ],
    associatedKnowledge: [
      {
        id: "know-03",
        category: "task",
        title: "Async Password Reset Notification Rail",
        summary: "Uses email worker for asynchronous notification dispatch.",
        confidence: 0.89,
      },
    ],
    chunks: [
      {
        chunkIndex: 0,
        sectionHeading: "Issue Description & Acceptance Criteria",
        contentText:
          "Configured secure reset token generation using HMAC-SHA256 with 1-hour expiration. Integrated asynchronous email dispatcher worker.",
        tokenCount: 38,
      },
    ],
  },
  {
    id: "evi-003",
    name: "Meeting notes — Authentication & Successor Transition",
    source: "pdf",
    recordType: "document",
    author: "Michael Chang",
    timestamp: "Yesterday at 14:10",
    ingestedAt: "2026-11-11T14:15:00Z",
    status: "extracted",
    originalSource: {
      provider: "pdf",
      containerName: "docs/pdf",
      resourceName: "Auth_Architecture_Sync_20261111.pdf",
      externalId: "doc:pdf-003",
    },
    extractedContent: {
      excerpt:
        "Discussion with Alex and Daniel regarding cryptographic secret rotation schedule and database migration rollback procedures before Daniel assumes primary ownership.",
      pageNumber: 2,
      sectionTitle: "Handover Readiness & Ownership Transfer",
      fullTextPreview:
        "# Authentication Architecture & Handover Sync\nDate: 2026-11-11\nAttendees: Alex Vance, Daniel Cho, Michael Chang\n\nKey Topics:\n1. Transition of KMS signing keys to Daniel.\n2. Review of Redis cluster failover for revoked sessions.\n3. Documentation of undocumented retry loops in payment callbacks.",
    },
    sourceReference: "REF-DOC-PDF-003 [SAMPLE]",
    relatedRecords: [
      {
        id: "evi-001",
        name: "PR #104: Token-expiry checks and rotation handler",
        source: "github",
        recordType: "pull_request",
      },
      {
        id: "evi-004",
        name: "Auth architecture specification",
        source: "pdf",
        recordType: "document",
      },
    ],
    associatedKnowledge: [
      {
        id: "know-04",
        category: "architecture",
        title: "KMS Secret Ownership Transition",
        summary: "Daniel Cho designated successor for KMS key lifecycle procedures.",
        confidence: 0.96,
      },
    ],
    chunks: [
      {
        chunkIndex: 0,
        pageNumber: 1,
        sectionHeading: "Attendees & Agenda",
        contentText:
          "Handover sync meeting between Alex (departing) and Daniel (successor) covering core auth boundaries.",
        tokenCount: 28,
      },
      {
        chunkIndex: 1,
        pageNumber: 2,
        sectionHeading: "Key Risks Identified",
        contentText:
          "Discussion regarding cryptographic secret rotation schedule and database migration rollback procedures.",
        tokenCount: 35,
      },
    ],
    metadata: {
      fileSizeBytes: 248100,
      mimeType: "application/pdf",
      sha256Hash: "6f52e5a6b0c2e3d4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8",
    },
  },
  {
    id: "evi-004",
    name: "Auth architecture specification (ADR-012)",
    source: "pdf",
    recordType: "document",
    author: "Alex Vance",
    timestamp: "Nov 08, 2026",
    ingestedAt: "2026-11-08T09:20:00Z",
    status: "indexed",
    originalSource: {
      provider: "pdf",
      containerName: "docs/pdf",
      resourceName: "ADR-012_Auth_Service_Boundaries.pdf",
      externalId: "doc:pdf-004",
    },
    extractedContent: {
      excerpt:
        "Architectural Decision Record 012: Separation of Platform Authentication from Delegated External Source OAuth connections.",
      pageNumber: 1,
      sectionTitle: "Context and Problem Statement",
      fullTextPreview:
        "# ADR-012: Separation of Platform Authentication from External Source OAuth\nStatus: Accepted\nDate: 2026-11-08\n\n## Context\nThe Handover platform requires users to connect personal GitHub and Jira accounts without commingling source access permissions with internal project membership.",
    },
    sourceReference: "REF-DOC-ADR-012 [SAMPLE]",
    relatedRecords: [
      {
        id: "evi-001",
        name: "PR #104: Token-expiry checks and rotation handler",
        source: "github",
        recordType: "pull_request",
      },
    ],
    associatedKnowledge: [
      {
        id: "know-05",
        category: "decision",
        title: "Project Membership != Source Access",
        summary:
          "External source permissions must be verified at query time independently of workspace membership.",
        confidence: 0.99,
      },
    ],
    chunks: [
      {
        chunkIndex: 0,
        pageNumber: 1,
        sectionHeading: "Decision",
        contentText:
          "Platform auth uses short-lived JWTs and HttpOnly cookies. Source connections use encrypted delegated OAuth tokens.",
        tokenCount: 32,
      },
    ],
    metadata: {
      fileSizeBytes: 512400,
      mimeType: "application/pdf",
      sha256Hash: "98fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855e3b0c442",
    },
  },
  {
    id: "evi-005",
    name: "Commit: Refresh-token rotation algorithm update",
    source: "github",
    recordType: "commit",
    author: "Alex Vance",
    timestamp: "Nov 07, 2026",
    ingestedAt: "2026-11-07T18:12:00Z",
    status: "extracted",
    originalSource: {
      provider: "github",
      containerName: "nexora-tech/nexora-backend",
      resourceName: "commit/c4b821a",
      externalUrl: "https://github.com/nexora-tech/nexora-backend/commit/c4b821a",
      externalId: "commit:c4b821a",
    },
    extractedContent: {
      excerpt:
        "commit c4b821a78e1b\nAuthor: Alex Vance <alex.vance@nexora.internal>\nDate: Sat Nov 7 18:05:22 2026\nUpdate token family tracking table schema and index on session_id.",
      commitSha: "c4b821a78e",
      diffSummary: "+28 lines, -4 lines in migrations/versions/004_tokens.py",
      fullTextPreview:
        "commit c4b821a78e1b4df8921a\nAuthor: Alex Vance\n\nUpdate token family tracking table schema and index on session_id.\nResolves race condition where parallel tab refreshes caused spurious invalidation.",
    },
    sourceReference: "REF-GH-COMMIT-C4B8 [SAMPLE]",
    relatedRecords: [
      {
        id: "evi-001",
        name: "PR #104: Token-expiry checks and rotation handler",
        source: "github",
        recordType: "pull_request",
      },
    ],
    associatedKnowledge: [
      {
        id: "know-06",
        category: "risk",
        title: "Session Table Concurrency Locks",
        summary: "High concurrency token rotation requires non-blocking row leases.",
        confidence: 0.88,
      },
    ],
    chunks: [
      {
        chunkIndex: 0,
        sectionHeading: "Commit Diff Excerpt",
        contentText:
          "CREATE INDEX ix_user_sessions_family_lookup ON user_sessions (user_id, token_family_id);",
        tokenCount: 22,
      },
    ],
  },
  {
    id: "evi-006",
    name: "API implementation notes & service contracts",
    source: "docx",
    recordType: "document",
    author: "Emily Watson",
    timestamp: "Nov 05, 2026",
    ingestedAt: "2026-11-05T11:00:00Z",
    status: "pending_extraction",
    originalSource: {
      provider: "docx",
      containerName: "docs/docx",
      resourceName: "Identity_API_Contracts_v2.docx",
      externalId: "doc:docx-006",
    },
    extractedContent: {
      excerpt:
        "Technical specification for external integration endpoints, pagination headers, and rate limiting thresholds under heavy load.",
      sectionTitle: "Section 3: Rate Limiting & Backpressure",
      fullTextPreview:
        "# Identity & Retrieval API Contracts v2\nAuthor: Emily Watson\nStatus: Pending Final OCR Pass\n\nDefines client payload contracts, response envelope structures, and circuit breaker parameters for Jira and GitHub sync jobs.",
    },
    sourceReference: "REF-DOC-DOCX-006 [SAMPLE]",
    relatedRecords: [
      {
        id: "evi-002",
        name: "Password reset task",
        source: "jira",
        recordType: "task",
      },
    ],
    associatedKnowledge: [
      {
        id: "know-07",
        category: "dependency",
        title: "GitHub API Secondary Rate Limits",
        summary: "Sync jobs must space out GraphQL and REST calls with exponential jitter.",
        confidence: 0.92,
      },
    ],
    chunks: [
      {
        chunkIndex: 0,
        sectionHeading: "Section 1: Contract Versioning",
        contentText:
          "All public endpoints enforce /api/v1 version prefix with forward-compatible JSON schemas.",
        tokenCount: 25,
      },
    ],
    metadata: {
      fileSizeBytes: 184500,
      mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      sha256Hash: "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
    },
  },
  {
    id: "evi-007",
    name: "NXA-312: Fix database deadlock in concurrent session invalidation",
    source: "jira",
    recordType: "issue",
    author: "David Morales",
    timestamp: "Nov 03, 2026",
    ingestedAt: "2026-11-03T16:22:00Z",
    status: "extracted",
    originalSource: {
      provider: "jira",
      containerName: "Nexora Assist Board",
      resourceName: "NXA-312",
      externalUrl: "https://nexora.atlassian.net/browse/NXA-312",
      externalId: "issue:NXA-312",
    },
    extractedContent: {
      excerpt:
        "Deadlock resolved by ordering session revocation by primary key before acquiring row-level locks.",
      issueKey: "NXA-312",
      labels: ["bug", "database", "resolved"],
      fullTextPreview:
        "Issue: Database deadlock during logout from all devices\nReporter: David Morales\nFix: Ensure sort order on session IDs prior to executing bulk UPDATE statement.",
    },
    sourceReference: "REF-JIRA-NXA-312 [SAMPLE]",
    relatedRecords: [
      {
        id: "evi-005",
        name: "Commit: Refresh-token rotation",
        source: "github",
        recordType: "commit",
      },
    ],
    associatedKnowledge: [
      {
        id: "know-08",
        category: "risk",
        title: "PostgreSQL Deadlock on Bulk Updates",
        summary: "Always sort IDs deterministically before acquiring row locks in SQLAlchemy.",
        confidence: 0.95,
      },
    ],
    chunks: [
      {
        chunkIndex: 0,
        sectionHeading: "Root Cause Analysis",
        contentText:
          "Two concurrent processes revoked sessions in opposite alphabetical UUID order, leading to cycle wait.",
        tokenCount: 30,
      },
    ],
  },
  {
    id: "evi-008",
    name: "Disaster recovery runbook for session and token rails",
    source: "docx",
    recordType: "document",
    author: "Sarah Jenkins",
    timestamp: "Oct 29, 2026",
    ingestedAt: "2026-10-29T10:15:00Z",
    status: "indexed",
    originalSource: {
      provider: "docx",
      containerName: "docs/docx",
      resourceName: "DR_Runbook_Sessions_2026.docx",
      externalId: "doc:docx-008",
    },
    extractedContent: {
      excerpt:
        "Emergency operational manual: failover steps when Redis cache goes down, manual secret rollover, and audit log verification.",
      sectionTitle: "Section 4: Complete Session Purge Emergency Procedure",
      fullTextPreview:
        "# Disaster Recovery Runbook\nDocument Version: 3.2\nOwner: Sarah Jenkins\n\nCovers degraded mode operations when Redis sentinel experiences split-brain condition.",
    },
    sourceReference: "REF-DOC-DOCX-008 [SAMPLE]",
    relatedRecords: [
      {
        id: "evi-003",
        name: "Meeting notes — Authentication",
        source: "pdf",
        recordType: "document",
      },
    ],
    associatedKnowledge: [
      {
        id: "know-09",
        category: "architecture",
        title: "Degraded Auth Mode Fallback",
        summary: "Fallback directly to PostgreSQL when Redis sentinel becomes unreachable.",
        confidence: 0.91,
      },
    ],
    chunks: [
      {
        chunkIndex: 0,
        sectionHeading: "Failover Procedure",
        contentText:
          "Switch database connection string to replica pool and notify on-call engineer via automated pager.",
        tokenCount: 32,
      },
    ],
    metadata: {
      fileSizeBytes: 312000,
      mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      sha256Hash: "b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2",
    },
  },
];
