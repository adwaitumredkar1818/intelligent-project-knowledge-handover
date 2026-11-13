# Handover — Figma-to-Production Completeness & Discrepancy Audit

**Document Status:** Complete Engineering Audit  
**Target Application:** The Handover (*Intelligent Project Knowledge Reconstruction & Handover Platform*)  
**Reference Baseline:** Original Figma Make Reference (`figma-make-reference/`)  
**Production Baseline:** Next.js 16 App Router Production Application (`frontend/src/`)  
**Audit Date:** November 2026  
**Deliverable Location:** `docs/engineering-audit/figma-integration-audit.md`  

---

## 1. Executive Summary

### 1.1 The Core Problem
The authenticated dashboard in production (`/overview`) looks and behaves fundamentally differently from the design in the Figma Make project. 

The audit reveals that **the production application did not port the Figma application's authenticated workspace shell, dashboard layout, or design tokens**. Instead, an earlier architectural prototype shell was maintained in `frontend/src/components/layout/` and populated with a single-project container view (`OverviewView.tsx`), while the Figma application’s rich, role-aware cross-project command center (`figma-make-reference/src/pages/dashboard.tsx`) was left unused in the reference directory.

### 1.2 Summary of Root Causes
1. **Divergent Shell Architecture**:
   - **Figma Reference (`Shell.tsx`)**: Utilizes an airy, light-canvas design (`bg-canvas #F6F8FC`), collapsible sidebar (`w-[248px]` to `w-[64px]`), dynamic workspace switcher, project context switcher, quick-access `⌘K` global search, rich breadcrumb navigation (`Projects > [Project] > Intelligence`), role-context chips (`Manager`, `Outgoing`, `Incoming`), notification center with unread counters, and custom user account menus.
   - **Production (`Sidebar.tsx` + `TopNav.tsx`)**: Employs a fixed, dark slate-navy sidebar (`#253650`) with hardcoded static category headers (`WORKSPACE`, `PROJECT INTELLIGENCE`, `VALIDATION`, `KNOWLEDGE TRANSFER`, `AI ASSISTANT`, `ADMINISTRATION`), fixed 14 navigation links, no collapse toggle, no dynamic project nesting, and a heavy top navigation bar rather than breadcrumbs.

2. **Single-Project View vs. Role-Aware Multi-Project Command Center**:
   - **Figma Reference (`dashboard.tsx`)**: Designed as an Executive & Personal Command Center across all user projects. It adapts dynamically based on whether the user is a **Project Manager**, **Outgoing Member** (leaving/handing over), or **Incoming Member** (successor), rendering tailored metric bands, next-best-action rails, interactive trend charts, handover completion stages, verification queues, and missing-information questions.
   - **Production (`OverviewView.tsx`)**: Implemented as a single-project container overview that requires an active project to be selected upfront (showing a blank "No Active Project Selected" state otherwise), focused almost exclusively on raw document upload and connector status cards.

3. **Design System & Visual Token Divergence**:
   - Production uses an older prototype palette (`#4774A9` blue, `#25334B` navy, `#249E91` teal, `#DCE3EB` border).
   - Figma Make specifies Design System 2.0 (`#315FBA` brand blue, `#203653` deep navy, `#299B80` verified teal, `#D39B43` warning amber, `#D36D72` risk red, `#8B78C9` AI lavender, `#D9E1F0` hairline borders, and `14px` border radiuses with `shadow-card` / `shadow-lift`).

4. **Widespread Placeholder Views**:
   - 10 of the 14 authenticated navigation routes in production currently render a generic placeholder (`Phase2ModuleView.tsx`), whereas the Figma Make codebase contains fully realized, interactive implementations for Knowledge Explorer, Intelligence, Handovers, Review Queues, Handover Reports, Recipient Workspaces, AI Assistant, and System Settings.

### 1.3 Scorecard at a Glance
| Category | Total Figma Screens | Fully Integrated | Partially Integrated | Placeholder Only | Missing / Omitted |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Public & Authentication** | 5 | 5 | 0 | 0 | 0 |
| **Workspace & Dashboard** | 3 | 0 | 1 | 0 | 2 |
| **Project Management** | 6 | 0 | 3 | 0 | 3 |
| **Evidence & Knowledge** | 6 | 0 | 2 | 1 | 3 |
| **AI Intelligence** | 6 | 0 | 0 | 5 | 1 |
| **Handovers & Transfer** | 9 | 0 | 0 | 4 | 5 |
| **Admin & Settings** | 5 | 0 | 1 | 2 | 2 |
| **Design System & Studio** | 3 | 0 | 0 | 0 | 3 |
| **Total** | **43** | **5 (11.6%)** | **7 (16.3%)** | **12 (27.9%)** | **19 (44.2%)** |

---

## 2. Complete Page & Screen Mapping Table

The table below maps every route and component defined in `figma-make-reference/src/App.tsx` against the current Next.js 16 production application (`frontend/src/app/` and `frontend/src/components/views/`).

| # | Figma Route | Figma Component | Production Route | Production Component | Integration Status | Visual & Structural Match | Notes & Key Discrepancies |
|---|---|---|---|---|---|---|---|
| 1 | `/` or `/home` | `Landing` | `/` | `LandingPage.tsx` | **FULLY INTEGRATED** | 98% Match | Brand intro animation, organic canvas sphere, comparison table, roles section all integrated. |
| 2 | `/login` | `Login` | `/login` | `login/page.tsx` | **FULLY INTEGRATED** | 100% Match | Split-screen branding, organic sphere, credentials & validation, remember me, direct route. |
| 3 | `/signup` | `Signup` | `/signup` | `signup/page.tsx` | **FULLY INTEGRATED** | 100% Match | Password strength indicator, Terms checkbox, split-screen hero visual. |
| 4 | `/forgot-password` | `ForgotPassword` | `/forgot-password` | `forgot-password/page.tsx` | **FULLY INTEGRATED** | 100% Match | Reset instructions, success state, return to sign in. |
| 5 | `/onboarding` | `Onboarding` | `/onboarding` | `onboarding/page.tsx` | **FULLY INTEGRATED** | 98% Match | 6-step guided wizard (Role, Project, Sources, Scope, Review, Success). |
| 6 | `/dashboard` | `Dashboard` | `/overview` | `OverviewView.tsx` | **REPLACED / DIVERGENT** | 25% Match | **Major discrepancy.** Figma has role-based command center (Manager/Outgoing/Incoming); production has single-project doc/source status cards. |
| 7 | `/projects` | `ProjectsList` | `/projects` | `ProjectsView.tsx` | **PARTIALLY INTEGRATED** | 45% Match | Production has basic card list; missing Grid/List toggle, search/status/role filters, knowledge coverage bars, source icon badges. |
| 8 | `/projects/new` | `CreateProject` | Modal in App | `CreateProjectModal.tsx` | **PARTIALLY INTEGRATED** | 40% Match | Figma has 3-step wizard (Details, Team, Sources) with sticky live preview; production has a single flat modal dialog. |
| 9 | `/projects/:id` | `ProjectOverview` | `/overview` (with active project) | `OverviewView.tsx` | **PARTIALLY INTEGRATED** | 35% Match | Figma has tabbed project header (Overview, Knowledge, Intelligence, Evidence, Sources, Ingestion, Handovers, Activity, Members) and health ring; production lacks tabs. |
| 10 | `/projects/:id/team` | `ProjectTeam` | `/team` | `TeamMembersView.tsx` | **PARTIALLY INTEGRATED** | 50% Match | Production lists project members and roles; missing pending invites card, permissions matrix table, and member role dropdown. |
| 11 | `/projects/:id/handovers` | `ProjectHandovers` | `/handover` | `Phase2ModuleView.tsx` | **PLACEHOLDER ONLY** | 0% Match | Renders "Phase 2 Module Planned" card; Figma has complete project-specific handover table. |
| 12 | `/projects/:id/activity` | `ProjectActivity` | In `/overview` | Embedded Activity Card | **PARTIALLY INTEGRATED** | 30% Match | Embedded as a small card in `/overview`; missing full-page timeline, actor filters, and event type tabs. |
| 13 | `/projects/:id/sources` | `DataSources` | `/sources` | `ConnectedSourcesView.tsx` | **PARTIALLY INTEGRATED** | 55% Match | Production shows source status & connect buttons; missing per-source repository/channel scope selector and historical date range options. |
| 14 | `/projects/:id/sources/:id`| `SourceDetail` | — | None | **NOT INTEGRATED** | 0% Match | Route does not exist in Next.js App Router; no source drilldown view. |
| 15 | `/projects/:id/evidence` | `EvidenceLibrary` | `/evidence` | `EvidenceCenterView.tsx` | **PARTIALLY INTEGRATED** | 50% Match | Production has 3-panel evidence layout; missing Figma’s table pagination, processing badges, slide-over preview drawer, and date filters. |
| 16 | `/projects/:id/evidence/:id`| `EvidenceDetail` | — | None | **NOT INTEGRATED** | 0% Match | Route does not exist; no full-page evidence traceability chain view (Source -> Raw -> Extracted -> Knowledge -> Handover). |
| 17 | `/projects/:id/ingestion` | `Ingestion` | In `/evidence` | Embedded Sync status | **NOT INTEGRATED** | 10% Match | Figma has dedicated batch ingestion job monitor with step-level progress; production only shows background job count badge. |
| 18 | `/projects/:id/knowledge` | `KnowledgeExplorer` | `/knowledge` | `Phase2ModuleView.tsx` | **PLACEHOLDER ONLY** | 0% Match | Renders placeholder; Figma has full 3-panel canvas graph (`KnowledgeCanvas`), category sidebar, and node inspector. |
| 19 | `/projects/:id/intelligence` | `IntelligenceOverview` | `/relationships` | `Phase2ModuleView.tsx` | **PLACEHOLDER ONLY** | 0% Match | Renders placeholder; Figma has Briefing card, Knowledge Health ring, domain breakdown cards, and attention queue. |
| 20 | `.../intelligence/decisions`| `Decisions` | — | None | **NOT INTEGRATED** | 0% Match | Figma has complete decisions register with rationale, confidence, verification badge, and slide-over FindingDrawer. |
| 21 | `.../intelligence/tasks` | `Tasks` | — | None | **NOT INTEGRATED** | 0% Match | Figma has tasks & responsibilities table with owner, assignee, blocking status, and transfer checkbox. |
| 22 | `.../intelligence/risks` | `Risks` | — | None | **NOT INTEGRATED** | 0% Match | Figma has risks register with severity pills (Critical, High, Medium, Low), impact, mitigation, and evidence links. |
| 23 | `.../intelligence/dependencies`| `Dependencies`| — | None | **NOT INTEGRATED** | 0% Match | Figma has technical & cross-team dependency diagram (`DependencyFlow`) and blocker list. |
| 24 | `.../intelligence/timeline` | `Timeline` | — | None | **NOT INTEGRATED** | 0% Match | Figma has chronological milestone and architectural decision timeline with actor avatars. |
| 25 | `/handovers` | `AllHandovers` | `/handover` | `Phase2ModuleView.tsx` | **PLACEHOLDER ONLY** | 0% Match | Renders placeholder; Figma has multi-metric KPI band, status tabs, search, project filter, Table/Card views. |
| 26 | `/handovers/new` | `CreateHandover` | — | None | **NOT INTEGRATED** | 0% Match | Figma has 8-step wizard (`Project`, `Members`, `Sources`, `Scope`, `Review`, `Generate`, `Results`, `Submit`) with simulation. |
| 27 | `/handovers/published` | `PublishedHandovers` | `/generated-handovers` | `Phase2ModuleView.tsx` | **PLACEHOLDER ONLY** | 0% Match | Renders placeholder; Figma has published handover cards, receipt status, and share actions. |
| 28 | `/handovers/received` | `ReceivedHandovers` | — | None | **NOT INTEGRATED** | 0% Match | Figma has dedicated recipient inbox with unacknowledged badges and 30-day onboarding guides. |
| 29 | `/handovers/:id` | `HandoverWorkspace` | — | None | **NOT INTEGRATED** | 0% Match | Figma has handover cockpit with progress ring, verification checklist, participant avatars, and action bar. |
| 30 | `/handovers/:id/review` | `Review` | `/verification` | `Phase2ModuleView.tsx` | **PLACEHOLDER ONLY** | 0% Match | Renders placeholder; Figma has complete split-screen Verification Center with confidence sorting, finding inspector, and comment threads. |
| 31 | `/handovers/:id/report` | `Report` | — | None | **NOT INTEGRATED** | 0% Match | Figma has exportable / printable Handover Dossier with brand header, executive summary, sign-off blocks, and runbooks. |
| 32 | `/handovers/:id/recipient` | `RecipientWorkspace` | — | None | **NOT INTEGRATED** | 0% Match | Figma has successor onboarding portal with 30-60-90 day checklists and acknowledgment signing. |
| 33 | `/handovers/:id/assistant` | `Assistant` | `/assistant` | `Phase2ModuleView.tsx` | **PLACEHOLDER ONLY** | 0% Match | Renders placeholder; Figma has permission-filtered RAG assistant with suggested queries, provenance cards, and chat history. |
| 34 | `/notifications` | `Notifications` | — | None | **NOT INTEGRATED** | 0% Match | Figma has dedicated notification center with unread tabs and direct jump links. |
| 35 | `/settings` | `Settings` | `/settings` | `Phase2ModuleView.tsx` | **PLACEHOLDER ONLY** | 0% Match | Renders placeholder; Figma has organisation settings, data retention policies, AI model toggles, and API keys. |
| 36 | `/settings/team` | `SettingsTeam` | — | None | **NOT INTEGRATED** | 0% Match | Figma has workspace-level team directory with seat limits, email invite modal, and Admin/Member role controls. |
| 37 | `/settings/audit-logs` | `AuditLogs` | `/audit` | `Phase2ModuleView.tsx` | **PLACEHOLDER ONLY** | 0% Match | Renders placeholder; Figma has immutable audit log table with actor avatars, event categories, and CSV export. |
| 38 | `/settings/profile` | `Profile` | — | None | **NOT INTEGRATED** | 0% Match | Figma has profile photo upload, password change, active sessions list, and notification preferences. |
| 39 | `/design-system` | `DesignSystem` | — | None | **NOT INTEGRATED** | 0% Match | Figma has full Design System token showcase (colors, typography, buttons, badges, cards, charts). |
| 40 | `/brand` | `BrandSystem` | — | None | **NOT INTEGRATED** | 0% Match | Figma has interactive 3D Brand Studio demonstrating Organic Knowledge Sphere shaders and presets. |
| 41 | `/flows` | `Flows` | — | None | **NOT INTEGRATED** | 0% Match | Figma has prototype walkthrough guide detailing all persona journeys (Manager, Outgoing, Incoming). |

---

## 3. Deep-Dive: Authenticated Dashboard Discrepancy Analysis

The user asked specifically: *"The current authenticated dashboard does not look like the Figma design. I want to identify exactly why."*

This section conducts an exhaustive, element-by-element comparison between the Figma design (`src/pages/dashboard.tsx` + `src/components/Shell.tsx`) and the current production implementation (`src/components/views/OverviewView.tsx` + `src/components/layout/AppLayout.tsx`).

### 3.1 Architectural Paradigm: Workspace Command Center vs. Single-Project Status Page
| Dimension | Figma Make Reference (`dashboard.tsx`) | Production Implementation (`OverviewView.tsx`) | Impact of Discrepancy |
| :--- | :--- | :--- | :--- |
| **Scope & Framing** | **Cross-Project Executive Command Center**. Summarizes all projects the user is involved in, active handovers requiring attention, incoming handovers, and workspace-level health. | **Single-Project Document & Source Container**. Assumes a single active project is already selected. If no project is selected, it displays a dead-end empty state box. | User cannot see across projects, cannot track handover transitions across teams, and gets blocked if no project is active. |
| **Persona & Role Awareness** | **Three Distinct Dynamic Dashboards**: <br>1. `ManagerDash`: Focuses on approvals, team completion rates, sync health, and blockers.<br>2. `OutgoingDash`: Focuses on personal handover progress, verification queue, and missing info.<br>3. `IncomingDash`: Focuses on received handovers, 30-day onboarding steps, and open tasks to take over. | **Static Monolithic Layout**: Exactly the same 4 KPI cards and 2 lists rendered regardless of whether the user is an executive, a departing engineer, or a newly hired successor. | Fails the core product value proposition: providing tailored transition experiences for departing employees and successors. |
| **Primary Workflow Driver** | **Handover Transition & Knowledge Verification**. Highlights who is leaving, who is taking over, target completion dates, and unresolved risks. | **Document Ingestion & OCR Progress**. Highlights document chunk counts, AES-256 encryption status, and raw source sync counts. | The product looks like a generic file indexing utility rather than a specialized Knowledge Reconstruction & Handover platform. |

### 3.2 Visual & Structural Layout Comparison
```
FIGMA MAKE DASHBOARD STRUCTURE (`dashboard.tsx` + `Shell.tsx`):
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ [Logo] [Workspace Switcher ▼] [Search ⌘K]                 [Breadcrumbs]   [Bell (3)] [Avatar]│
├────────────────────┬─────────────────────────────────────────────────────────────────────────┤
│ Workspace          │ "Good morning, Maya"  ·  Thursday, 13 November               [+ Handover]│
│  • Dashboard (act) │ ┌─────────────────────────────────────────────────────────────────────┐ │
│  • My Projects     │ │ NEXT BEST ACTION: Review HO-1042 before 28 Nov        [Start Review]│ │
│  • Team            │ └─────────────────────────────────────────────────────────────────────┘ │
│ Handovers          │ [Project Switcher Strip: (PAY) Atlas Payments · (SET) Settlement ... ]  │
│  • All Handovers   │ ┌───────────────┬───────────────┬────────────────┬────────────────────┐ │
│  • Create Handover │ │ Total Projects│Active Handover│Pending Approval│Connected Sources   │ │
│  • Received (1)    │ │ 4 (2 managed) │ 3 (sparkline) │ 1 (needs rev)  │ 6 (all healthy)    │ │
│  • Published       │ └───────────────┴───────────────┴────────────────┴────────────────────┘ │
│ Current Project    │ ┌──────────────────────────────────────────────┬──────────────────────┐ │
│  • Overview        │ │ Knowledge Processing Activity (10-Day Trend) │ Handover Completion  │ │
│  • Knowledge       │ │ [Dual Line & Area Chart: Evidence vs Findings│ [Stage Progress Bars:│ │
│  • Intelligence    │ │  1,420 records / 28 findings this week]      │  Draft -> Completed] │ │
│  • Evidence        │ └──────────────────────────────────────────────┴──────────────────────┘ │
│ Settings           │ ┌──────────────────────────────────────────────┬──────────────────────┐ │
│  • Settings        │ │ Attention Required Queue (Actionable Cards)  │ Recent Activity Feed │ │
│  • Notifications   │ │ • HO-1042 waiting for approval      [Review] │ • Maya verified fact │ │
│  • Profile         │ │ • Slack sync paused 2d ago        [Reconnect]│ • Ingested API doc   │ │
│                    │ └──────────────────────────────────────────────┴──────────────────────┘ │
└────────────────────┴─────────────────────────────────────────────────────────────────────────┘
```
```
CURRENT PRODUCTION DASHBOARD STRUCTURE (`OverviewView.tsx` + `Sidebar.tsx`):
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ [The Handover]     │ [Active Org: Northwind Labs ▼] [Active Project: Atlas Payments ▼]        │
├────────────────────┼─────────────────────────────────────────────────────────────────────────┤
│ WORKSPACE          │ Project Workspace Overview · live canonical state                       │
│  • Overview (act)  │ Atlas Payments                                [Ingest Doc] [Connect Src]│
│  • Projects        ├─────────────────────────────────────────────────────────────────────────┤
│  • Team Members    │ ┌───────────────┬───────────────┬────────────────┬────────────────────┐ │
│ PROJECT INTEL      │ │Handover Ready │Conn. Sources  │Evidence Items  │Knowledge Domains   │ │
│  • Evidence Center │ │ 42% (prep)    │ 2 active      │ 18 (240 chunks)│ 0 extracted (Ph2)  │ │
│  • Knowledge (Ph2) │ └───────────────┴───────────────┴────────────────┴────────────────────┘ │
│  • Relations (Ph2) ├──────────────────────────────────────────────┬──────────────────────────┤
│ VALIDATION         │ ┌──────────────────────────────────────────┐ │ ┌──────────────────────┐ │
│  • Verif (Spec)    │ │ Attention Required                       │ │ │ Recent Audit Trail   │ │
│  • Conflicts (Spec)│ │ [Yellow card: All operational]           │ │ │ [Gray list: Audit]   │ │
│ KNOWLEDGE TRANSFER │ └──────────────────────────────────────────┘ │ └──────────────────────┘ │
│  • Handover (Spec) │                                                                         │
│  • Generated (Spec)│                                                                         │
└────────────────────┴─────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Granular Feature Discrepancy Breakdown
1. **Welcome Header & Contextual Greeting**:
   - *Figma*: Displays dynamic greeting (`"Good morning, Maya"`), current localized date (`Thursday, 13 November`), and primary call-to-action buttons (`New Handover`, `New Project`).
   - *Production*: Displays static text `"Project Workspace Overview · live canonical state"` with project description.
2. **Next-Best-Action Rail**:
   - *Figma*: Prominent hero card with an amber/blue accent rail guiding the user to the single most critical pending task (e.g. `"Review HO-1042 before 28 Nov — Maya submitted the handover to Alex"` with a one-click `"Start review"` button).
   - *Production*: Omitted entirely.
3. **Interactive Project Switcher Strip**:
   - *Figma*: Horizontal scrollable pill bar (`ProjectSwitcherStrip`) allowing one-click switching between user projects, displaying project color badge, project code (`PAY`), name, and the user's role in that project (`Manager`, `Outgoing`, `Incoming`).
   - *Production*: Only available through a top dropdown selector in `TopNav`.
4. **Metric Band & Visual Sparklines**:
   - *Figma*: `MetricBand` component rendering high-density tiles with trend sparklines, status hints (`"oldest submitted 12 min ago"`), semantic color tones (`amber`, `green`, `blue`), and clickable drilldown handlers.
   - *Production*: 4 plain cards with basic integer values, no sparklines, and static text.
5. **Interactive Charts**:
   - *Figma*: 
     - Dual-series `LineChart` with area fill showing 10-day knowledge processing activity (Evidence records vs Extracted findings).
     - Handover completion stage breakdown bar chart showing counts across all 6 lifecycle stages (`Draft`, `In Progress`, `Pending Review`, `Approved`, `Published`, `Completed`) with percentage acknowledged.
     - Animated circular `Ring` progress indicators for individual handover health and coverage.
   - *Production*: Uses simple flat HTML `<div style={{ width: '42%' }} />` progress bars. Zero SVG or canvas charts are integrated into the dashboard.
6. **Attention Queue & Actionable Cards**:
   - *Figma*: Attention items are rich actionable cards with icon, severity tone (`amber`, `red`, `ai`), descriptive summary, affected entity, and a direct button (`Review`, `Reconnect`, `Resolve`).
   - *Production*: Simple alert box showing generic text strings from the backend without interactive resolution actions.

---

## 4. Missing Component & Interaction Inventory

The following components from `figma-make-reference/` have not been ported to production or exist only as hollow stubs.

### 4.1 Application Shell & Navigation
- [ ] **Collapsible Sidebar (`Shell.tsx`)**: Smooth CSS transition between `248px` expanded and `64px` collapsed state, displaying icons with floating tooltips when collapsed.
- [ ] **Workspace Switcher (`WorkspaceSwitcher`)**: Dropdown in the sidebar header to switch between enterprise workspaces (e.g. `Northwind Labs`, `Acme Corp`) or launch workspace onboarding.
- [ ] **In-Sidebar Project Switcher (`ProjectSwitcher`)**: Role-aware project selector inside the sidebar navigation tree.
- [ ] **Command Palette (`CommandPalette`)**: Global keyboard shortcut `⌘K` / `Ctrl+K` opening a floating spotlight modal searching across Projects, Handovers, Reconstructed Knowledge entities, and Evidence records.
- [ ] **Breadcrumb Trail (`Breadcrumbs`)**: Top-bar breadcrumbs showing hierarchy with clickable ancestors (`Workspace > Projects > Atlas Payments > Intelligence > Decisions`).
- [ ] **Role Context Chip (`ContextChip`)**: Floating top-bar badge indicating the user's explicit role in the active project (`Manager` [Blue], `Outgoing` [Amber], `Incoming` [Green]).
- [ ] **Notification Center (`NotificationsMenu`)**: Dropdown menu showing unread notification counts, timestamps, actor avatars, and mark-all-as-read actions.
- [ ] **Global Toast System (`Toaster`)**: Bottom-right floating animated notification toasts (`success`, `error`, `info`).

### 4.2 Shared Design System UI Primitives (`components/ui.tsx`)
- [ ] **`MetricBand`**: High-density horizontal KPI band with sparklines, status tones, and drilldown clicks.
- [ ] **`ReconstructionLoader`**: Non-blocking 3D organic knowledge reconstruction progress indicator with 4 phased captions.
- [ ] **`Confidence`**: Specialized AI confidence visualizer showing percentage score, confidence tier (`High`, `Medium`, `Low`), and visual mini-bar.
- [ ] **`VerificationBadge`**: Standardized badges for the 5 epistemic states (`verified`, `needs_review`, `conflicting`, `insufficient`, `rejected`).
- [ ] **`StatusBadge`**: Standardized pill for the 6 handover stages (`draft`, `in_progress`, `pending_review`, `approved`, `published`, `completed`).
- [ ] **`Segmented`**: Apple-style segmented control toggle (used for Grid/List, Graph/List, and Table/Card views).
- [ ] **`Drawer`**: Slide-over right inspection panel for quick preview of evidence items, decisions, and tasks without leaving the list view.
- [ ] **`AvatarGroup`**: Overlapping stacked user avatars with `+N` overflow badge.
- [ ] **`PersonCell`**: Standardized user cell displaying avatar, full name, email, and role badge.

### 4.3 Data Visualizations & Charts (`components/charts.tsx` & `components/graph.tsx`)
- [ ] **`LineChart`**: Smooth SVG line and area chart with tooltips, dual series, and gridlines.
- [ ] **`Ring`**: Circular SVG progress donut with centered percentage or count labels.
- [ ] **`StackedBar`**: Multi-segment horizontal bar displaying proportional breakdowns (e.g. Verified vs Needs Review vs Conflicting).
- [ ] **`Donut`**: Multi-segment SVG donut chart with legend and hover tooltips.
- [ ] **`KnowledgeCanvas`**: Interactive 2D/WebGL force-directed relationship graph visualizing knowledge nodes (Decisions, Tasks, Risks, Architecture) connected to evidence and team members, with category filters and node focus modes.
- [ ] **`DependencyFlow`**: Structured flow diagram visualizing task and architectural dependencies and blocking paths.

### 4.4 Domain & Handover Components (`components/domain.tsx`)
- [ ] **`ProjectHeader`**: Standardized tabbed navigation header across all project sub-pages (`Overview`, `Knowledge`, `Intelligence`, `Evidence`, `Sources`, `Ingestion`, `Handovers`, `Activity`, `Team`).
- [ ] **`HandoverTable`**: Standardized table listing handovers with outgoing $\to$ successor avatar flows, progress bars, and status dots.
- [ ] **`FindingDrawer`**: Slide-over inspector for any reconstructed finding showing original evidence quotes, confidence score, verification history, and human comment thread.
- [ ] **`StageDots`**: 6-stage micro progress dot indicator for handover lifecycles.
- [ ] **`SeverityBadge`**: Standardized indicator for risk severities (`Critical`, `High`, `Medium`, `Low`).
- [ ] **`PermissionNote`**: Warning banner displayed when a user's project role restricts specific operations (e.g. Incoming members viewing verification queues in read-only mode).

---

## 5. Design System & Visual Token Discrepancy Report

The production application's stylesheet (`globals.css`) and Tailwind classes differ substantially from the Figma Make design tokens.

### 5.1 Color Tokens
| Token Name | Figma Reference (Make) | Current Production (Next.js) | Visual Impact |
| :--- | :--- | :--- | :--- |
| **Canvas Background** | `#F6F8FC` (`bg-canvas`) | `#F8FAFC` (Tailwind slate-50) | Figma canvas has a distinct soft cool-blue tint; production is neutral white-gray. |
| **Surface Tint** | `#EDF2FA` (`bg-tint`) | `#F1F5F9` (slate-100) | Sidebar and panel backgrounds in Figma feel branded and airy; production feels generic. |
| **Primary Navy** | `#203653` (`text-navy`) | `#25334B` | Headings and titles in Figma are deep slate-navy; production uses an older muted navy. |
| **Brand Blue** | `#315FBA` (`text-brand`, `bg-brand`) | `#4774A9` | Primary action buttons and links in Figma are rich royal blue; production uses a duller steel blue. |
| **Hairline Borders** | `#D9E1F0` (`border-line`) | `#DCE3EB` / `#304563` | Card borders in Figma are crisp and ultra-clean; production sidebar borders are heavy and dark. |
| **Verified Green** | `#299B80` (`text-ok`, `bg-ok`) | `#249E91` | Verified status indicators in Figma are balanced pine-teal; production is slightly brighter green. |
| **Warning Amber** | `#D39B43` (`text-warn`, `bg-warn`) | `#F59E0B` (amber-500) | Figma uses a sophisticated muted gold-amber; production uses bright browser warning yellow. |
| **Risk / Error Red** | `#D36D72` (`text-bad`, `bg-bad`) | `#E11D48` (rose-600) | Figma uses an editorial soft crimson; production uses stark alert red. |
| **AI Accent** | `#8B78C9` (`text-ai`, `bg-ai`) | `#6366F1` (indigo-500) | Figma uses an elegant lavender-indigo for AI features; production uses default Tailwind indigo. |

### 5.2 Elevation, Radius & Typography
- **Border Radiuses**: Figma Make standardizes on `rounded-[10px]` for controls and buttons, and `rounded-[14px]` for cards. Production alternates inconsistently between `rounded-lg` (`8px`) and `rounded-xl` (`12px`).
- **Shadows**: Figma defines custom elevation tokens:
  - `shadow-card`: `0 1px 3px rgba(32,54,83,0.05), 0 0 0 1px rgba(217,225,240,0.8)`
  - `shadow-lift`: `0 8px 24px -4px rgba(32,54,83,0.12), 0 2px 6px -1px rgba(32,54,83,0.06)`
  - `shadow-pop`: `0 16px 48px -8px rgba(32,54,83,0.22)`
  - Production uses standard Tailwind shadows (`shadow-xs`, `shadow-2xs`), lacking the subtle hairline border ring that gives Figma its crisp, premium feel.
- **Typography Scale**: Figma uses tight letter-spacing (`tracking-[-0.015em]` on body, `tracking-[-0.025em]` on headers) with font weights strictly curated to `font-medium (500)` and `font-semibold (600)` with tabular numeric data (`tabular-nums font-mono`). Production often uses heavy `font-bold (700)`.

---

## 6. Functional Integration & Data Flow Analysis

### 6.1 The State & Data Architecture Gap
The Figma Make reference operates entirely on an in-memory client-side mock store (`src/lib/store.tsx` and `src/lib/data.ts`). It simulates all 41 screens using hardcoded fixtures for personas (Maya, Alex, Elena, Marcus), mock projects (`Atlas Payments`, `Ledger Sync`), and simulated asynchronous delays.

In contrast, **the production application is backed by a real, secure FastAPI backend with PostgreSQL, ChromaDB, and local Ollama inference**.

```
FIGMA MAKE ARCHITECTURE:
[React UI] ──▶ [In-Memory React Context Store (store.tsx)] ──▶ [Static JSON Mock Data (data.ts)]
*(Instant, client-only, zero security, mock fixtures)*

PRODUCTION TARGET ARCHITECTURE:
[Next.js App Router] ──▶ [HTTPX Client / LiveAppContext] ──▶ [FastAPI Backend (:8000)]
                                                                  │
                                   ┌──────────────────────────────┼──────────────────────────────┐
                                   ▼                              ▼                              ▼
                          [PostgreSQL (Canonical)]       [ChromaDB (Vectors)]          [Ollama (Qwen3/GLM)]
                          - Projects & Members           - Project-Isolated            - Structured Extraction
                          - Source Credentials & ACLs      768-dim Collections         - GLM OCR for Scans
                          - Evidence Metadata & Provenance
                          - Reconstructed Knowledge
                          - Verification & Audit Trails
```

### 6.2 Strict Governance & Non-Negotiable Rules
As defined in `AGENTS.md`, the integration of Figma screens into production **must strictly respect** the following constraints:
1. **Zero Fabrication Rule**: We must **NEVER** import fake users, synthetic GitHub repos, or fabricated Jira issues from `data.ts` into the production dashboard or database. Real data from connected sources or explicit user uploads must be the only source of displayed evidence.
2. **Project Membership != Source Access**: When implementing the project views and evidence lists, the backend's strict source-level ACL checks must be preserved. A user viewing a project cannot see private repositories or Jira tickets connected by another user unless explicitly authorized.
3. **No Direct Supabase Auth or Bypass**: Platform authentication remains exclusively managed by FastAPI JWT tokens and `RefreshSession` cookies.

### 6.3 Backend Endpoint Availability Matrix
To determine how readily each Figma screen can be connected to real data, the backend API coverage was audited:

| Canonical Module | Figma Screens | Backend API Readiness | Available Endpoints | Required New Endpoints |
| :--- | :---: | :---: | :--- | :--- |
| **Auth & Onboarding** | 5 | **100% Ready** | `/api/v1/auth/*`, `/api/v1/organisations/*` | None |
| **Workspace & Dashboard** | 3 | **75% Ready** | `/api/v1/projects/{id}/overview`, `/api/v1/audit/recent` | Aggregate multi-project overview endpoint `/api/v1/workspace/dashboard` |
| **Projects & Members** | 6 | **90% Ready** | `/api/v1/projects/*`, `/api/v1/projects/{id}/members/*` | Project health scoring & knowledge coverage aggregation |
| **Evidence & Sources** | 6 | **85% Ready** | `/api/v1/sources/*`, `/api/v1/documents/*`, `/api/v1/evidence/*` | Evidence detail full traceability endpoint `/api/v1/evidence/{id}/trace` |
| **Knowledge Intelligence** | 6 | **40% Ready** | Schema defined in DB; extraction worker operational | Reconstructed entities CRUD endpoints (`/api/v1/projects/{id}/knowledge/*`) |
| **Verification & Conflicts**| 2 | **50% Ready** | Schema defined in DB (`verification_decisions`) | Verification queue & batch review endpoints (`/api/v1/verification/*`) |
| **Handovers & Transfer** | 9 | **35% Ready** | Handover packages schema defined | Handover creation wizard, report compilation, & receipt ack endpoints |
| **Admin & Audit Logs** | 5 | **80% Ready** | `/api/v1/audit/*`, `/api/v1/auth/me` | Organization team seats & invitation management |

---

## 7. Prioritized Issue Register (P0 to P3)

The following register organizes all discovered discrepancies by priority.

### Priority 0 — Critical Architectural Blockers
*Must be resolved before the authenticated application can visually or functionally resemble Figma.*

- [ ] **ISSUE-P0-01: Divergent Application Shell**. Replace static `Sidebar.tsx` + `TopNav.tsx` with a port of `Shell.tsx` adapted for Next.js App Router, featuring collapsible navigation (`248px` to `64px`), dynamic workspace switching, in-sidebar project switching, role badges, and breadcrumb headers.
- [ ] **ISSUE-P0-02: Single-Project Dashboard Divergence**. Refactor `/overview` (or introduce `/dashboard`) from a single-project document container into the cross-project, role-aware command center (`ManagerDash`, `OutgoingDash`, `IncomingDash`), with fallback to `EmptyWorkspace` when no projects exist.
- [ ] **ISSUE-P0-03: Design Token & Visual Theme Desynchronization**. Update `globals.css` and Tailwind configuration with official Design System 2.0 tokens (`#F6F8FC` canvas, `#EDF2FA` tint, `#D9E1F0` line, `#315FBA` brand, `#203653` navy, `rounded-[14px]`, `shadow-card`).

### Priority 1 — High-Impact Experience Gaps
*Core product modules that currently render placeholders or lack essential Figma functionality.*

- [ ] **ISSUE-P1-01: Missing Project Creation Wizard**. Upgrade `CreateProjectModal` to the full 3-step wizard (`Details`, `Team`, `Sources`) with live sticky project summary.
- [ ] **ISSUE-P1-02: Missing Project Sub-Navigation Tabs**. Implement `ProjectHeader` across all project routes with consistent tabs (`Overview`, `Knowledge`, `Intelligence`, `Evidence`, `Sources`, `Ingestion`, `Handovers`, `Activity`, `Team`).
- [ ] **ISSUE-P1-03: Projects List Grid/List View & Filters**. Port Figma's `ProjectsList` with search, status filters, role filters, coverage progress bars, and member avatar stacks.
- [ ] **ISSUE-P1-04: Evidence Center Inspection Drawer & Detail View**. Port `EvidenceLibrary` slide-over preview drawer and full-page `EvidenceDetail` 5-stage traceability view.
- [ ] **ISSUE-P1-05: Missing Verification Center Split-Screen View**. Port `Review` from `handover-detail.tsx` into `/verification`, featuring the prioritized review queue, finding inspector, and provenance links.

### Priority 2 — Medium-Impact Enhancements
*Visual polish, advanced interactive controls, and secondary workflows.*

- [ ] **ISSUE-P2-01: Global Command Palette (`⌘K`)**. Port `CommandPalette` to allow instant keyboard search across projects, handovers, evidence, and knowledge entities.
- [ ] **ISSUE-P2-02: SVG Chart Suite Integration**. Port `LineChart`, `Ring`, `StackedBar`, and `Donut` components into `frontend/src/components/charts/` to power dashboard and intelligence analytics.
- [ ] **ISSUE-P2-03: Knowledge Explorer 3-Panel Canvas Graph**. Port `KnowledgeCanvas` and 3-panel explorer layout into `/knowledge`.
- [ ] **ISSUE-P2-04: Handover Creation 8-Step Wizard**. Port `CreateHandover` wizard into `/handover/new`.
- [ ] **ISSUE-P2-05: Successor Recipient Workspace & Handover Report**. Port `RecipientWorkspace` and printable `Report` views.

### Priority 3 — Polish & Administration
*System administration, settings, and auxiliary developer studio pages.*

- [ ] **ISSUE-P3-01: Workspace Team & Invitation Management**. Port `SettingsTeam` into `/settings/team`.
- [ ] **ISSUE-P3-02: Immutable Audit Log Viewer**. Port `AuditLogs` table into `/audit`.
- [ ] **ISSUE-P3-03: User Profile & Security Settings**. Port `Profile` into `/settings/profile`.
- [ ] **ISSUE-P3-04: Global Toast Notification System**. Integrate `Toaster` component with Next.js state.

---

## 8. Recommended Implementation Roadmap

To systematically bring the production application into 100% parity with the Figma Make reference **without breaking existing backend APIs, database migrations, or security boundaries**, the following phased implementation sequence is recommended:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: Shell & Design System Alignment                                               │
│ • Synchronize design tokens & CSS variables in `globals.css`                          │
│ • Port `Shell.tsx` to Next.js App Router (Collapsible, Breadcrumbs, Role Chips, ⌘K)   │
└───────────────────────────────────────────────────┬────────────────────────────────────┘
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: Cross-Project Role-Aware Dashboard                                            │
│ • Implement `/dashboard` with Manager, Outgoing, and Incoming view modes               │
│ • Integrate SVG charts (`LineChart`, `Ring`, Handover Stages)                         │
│ • Connect to real FastAPI aggregated overview endpoint                                 │
└───────────────────────────────────────────────────┬────────────────────────────────────┘
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: Project Workspace & Creation Wizard                                           │
│ • Upgrade `/projects` with Grid/List view, filters, and coverage metrics              │
│ • Implement 3-step `CreateProject` wizard with live preview card                       │
│ • Establish consistent tabbed `ProjectHeader` across all project sub-pages             │
└───────────────────────────────────────────────────┬────────────────────────────────────┘
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: Evidence Workspace & Traceability                                             │
│ • Port `EvidenceLibrary` with slide-over preview drawer and pagination                 │
│ • Create `/projects/[id]/evidence/[evidenceId]` 5-stage traceability view              │
│ • Port batch ingestion job activity monitor                                            │
└───────────────────────────────────────────────────┬────────────────────────────────────┘
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: Verification Center & Knowledge Intelligence                                  │
│ • Port split-screen `Review` queue into `/verification` (Urgency sorting, provenance) │
│ • Port `KnowledgeExplorer` 3-panel layout and interactive canvas graph                 │
│ • Implement Intelligence sub-tabs (Decisions, Tasks, Risks, Dependencies, Timeline)    │
└───────────────────────────────────────────────────┬────────────────────────────────────┘
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 6: Handover Lifecycle & Recipient Experience                                     │
│ • Implement `/handovers` directory and 8-step `CreateHandover` wizard                  │
│ • Port exportable/printable Handover `Report` dossier                                  │
│ • Implement `RecipientWorkspace` onboarding hub and acknowledgment signing             │
└───────────────────────────────────────────────────┬────────────────────────────────────┘
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 7: Administration & Security Hardening                                           │
│ • Port Workspace Team directory and email invitation modals                            │
│ • Port PostgreSQL Audit Log table viewer with filtering and export                     │
│ • Port User Profile, Session management, and System Settings                           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Safety & Governance Checks Prior to Implementation
- **Preserve Real Backend Connection**: All ported components must bind to `LiveAppContext` and backend API endpoints rather than importing `figma-make-reference/src/lib/data.ts` or `store.tsx`.
- **Preserve Source ACL Boundaries**: The Evidence Library and Knowledge Explorer must strictly enforce the backend's source permissions.
- **Maintain Production Build Hygiene**: Ensure all new App Router segments compile cleanly under Next.js Turbopack with 0 type errors.

---
*Audit compiled and certified for The Handover engineering repository.*
