# The Handover — Frontend Interactive Prototype

This directory contains the isolated interactive frontend prototype for **The Handover** (**Intelligent Project Knowledge Reconstruction & Handover Platform**).

## Overview
This prototype implements the complete visual layout, information hierarchy, navigation, and user interactions for:
1. **Module 1: Project Workspace** (Overview, Project Directory, Team Members)
2. **Module 2: Evidence Workspace** (3-Panel Evidence Center, Connected Sources Management)

## Architecture & Principles
- **Strictly Frontend-Only**: Does not communicate with backend APIs or touch PostgreSQL/ChromaDB.
- **Isolated In-Memory State**: Managed by `PrototypeContext.tsx` with typed fixtures in `features/prototype/data/`.
- **Persistent Mandatory Banner**: Every screen displays `DEMO WORKSPACE · SAMPLE DATA ONLY`.
- **Three-Panel Layout**: Evidence Center reproduces the 3 columns faithfully:
  - Column 1: Connected Sources (GitHub, Jira, PDF, DOCX, Slack disabled)
  - Column 2: Evidence Library (Search, filters, table, local upload preview)
  - Column 3: Evidence Details (Provenance, original source, extracted content, related records)
- **Palette**: Dark Navy (`#253650`), Primary Blue (`#4774A9`), Teal Accent (`#249E91`), Neutral Background (`#F4F6F9`).

## Routes
- `/prototype` $\to$ Redirects to `/prototype/overview`
- `/prototype/overview` $\to$ Project Workspace Dashboard (Reference 2)
- `/prototype/projects` $\to$ Project Directory & Create Project Modal
- `/prototype/team` $\to$ Team Members & Transition Configuration
- `/prototype/evidence` $\to$ Evidence Center (Reference 3: 3-Panel Layout)
- `/prototype/sources` $\to$ Connected Sources Management
