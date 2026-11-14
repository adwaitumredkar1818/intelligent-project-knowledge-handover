# Typed Relationship Intelligence & Taxonomy

**Platform:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Module:** **Module C — Typed Relationship Intelligence**  
**Audit Phase:** **Phase 2.7 — Complete Knowledge Intelligence Engine**  
**Date:** 2026-11-14  

---

## 1. Controlled Relationship Taxonomy

The platform enforces a controlled directed relationship vocabulary in `backend/app/models/enums.py` (`RelationshipType`), grouped across five essential domains:

### 1.1 Decision Relationships
- `proposed_by`: Links a decision to its originating person/contributor.
- `approved_by`: Links a decision to the authorized technical lead or reviewer.
- `supersedes`: Connects a newer architectural decision to an obsolete one.
- `implements`: Links tasks, commits, or code to the governing decision.
- `motivated_by`: Connects a decision to the requirement or problem it resolves.
- `contradicts`: Surfaces contradictory decisions across disparate sources.
- `revises`: Connects an amended decision to its predecessor.

### 1.2 Work Relationships
- `assigned_to`: Tracks task ownership and participant allocation.
- `owned_by`: Establishes accountability for a component or epic.
- `implemented_by`: Connects a work item to code PRs or author.
- `reviewed_by`: Records peer code reviews and sign-offs.
- `blocks`: Explicit blocking impediment.
- `blocked_by`: Inverse blocking relationship.
- `depends_on`: Technical or task prerequisite.
- `requires`: Strict architectural or operational dependency.

### 1.3 Technical Relationships
- `uses`: Service-to-service or module-to-library invocation.
- `integrates_with`: External API or cross-system boundary.
- `extends`: Class/module inheritance or plugin architecture.
- `replaces`: Technology deprecation and component migration.
- `deployed_as`: Infrastructure mapping (container, daemon, serverless).
- `configured_by`: Environment variable or config file link.

### 1.4 Evidence Relationships
- `supported_by`: Mandatory verifiable citation link to `evidence_items`.
- `mentioned_in`: Informal reference in meeting notes or chats.
- `derived_from`: Reconstructed finding derived from OCR or raw text.
- `corroborated_by`: Multi-source cross-verification.
- `conflicts_with`: Contradictory evidence citation link.

### 1.5 Project Relationships
- `belongs_to`: Project-to-organisation or task-to-project hierarchy.
- `part_of`: Sub-system to parent system hierarchy.
- `completed_in`: Milestone or sprint delivery link.
