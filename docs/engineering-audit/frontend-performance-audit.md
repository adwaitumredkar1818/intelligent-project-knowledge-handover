# The Handover — Frontend Performance Audit
## Next.js App Router, Rendering, State Management & Bundle Assessment

---

## 1. Executive Summary

The frontend application was evaluated across production build composition, bundle sizes, rendering strategies, context propagation, canvas animation overhead, and network request patterns. 

While the interface exhibits high visual polish, modern typography (Manrope & JetBrains Mono), and sleek dark/light brand styling, it suffers from **severe client-side rendering bottlenecks, context re-render cascades, wasteful animation loops, and an aggressive network waterfall bug on evidence selection**.

---

## 2. Production Build & Bundle Composition

The application was built for production using `next build` (Next.js 16.4.6 with Turbopack). The build generated **27 static routes** and **56 static build assets**.

### Bundle Size Analysis

| Asset / Chunk File | Size (Uncompressed) | Role / Content |
| :--- | :---: | :--- |
| `static/chunks/23-0si33zocg9.js` | **471.2 KB** | Core vendor bundle (React 19, Lucide Icons, Agentation) |
| `static/chunks/01t2i9pe5vz2-.js` | **223.9 KB** | UI Component primitives & views bundle |
| `static/chunks/1wg4rdrutax1u.js` | **160.6 KB** | `brand/OrganicScene.tsx` 3D Canvas Math & Geometry Engine |
| `static/chunks/0cz1d0mv5g_q7.js` | **110.0 KB** | Evidence Center & Document Preview views |
| `static/chunks/0dvprqr1ils0u.js` | **104.1 KB** | Relationship Explorer & Graph Projection views |
| `static/css/2xq8ags1_eual.css` | **99.0 KB** | Global CSS & Tailwind utilities (`globals.css`) |
| Top 15 Assets Cumulative Size | **1,414.2 KB** | Primary initial load payload |
| **Total Static Build Assets** | **1,829.5 KB** | Complete static export asset footprint |

### Anti-Pattern: Bypassing TypeScript Compiler in `next.config.ts`
During build inspection, an uncommitted configuration in `frontend/next.config.ts` was identified:
```typescript
typescript: {
  ignoreBuildErrors: true,
},
```
- **Finding**: TypeScript typechecking is explicitly disabled during `next build`.
- **Impact**: Any future type regressions, interface mismatches, or missing props will silently pass build checks, causing runtime crashes in production.
- **Verification**: Running `npm run typecheck` (`next typegen && tsc --noEmit`) succeeded without errors, proving that `ignoreBuildErrors: true` is completely unnecessary and should be removed immediately.

---

## 3. Server vs. Client Component Architecture

### Overuse of `"use client"`
- **Inspection Finding**: Almost every view and page across the application is marked `"use client"`:
  - `app/overview/page.tsx` $\to$ `"use client"`
  - `app/projects/page.tsx` $\to$ `"use client"`
  - `app/evidence/page.tsx` $\to$ `"use client"`
  - `app/relationships/page.tsx` $\to$ `"use client"`
  - `app/knowledge/page.tsx` $\to$ `"use client"`
  - `app/team/page.tsx` $\to$ `"use client"`
  - `components/views/*.tsx` $\to$ All client components.
- **Architectural Impact**: The Next.js App Router is being used merely as a client-side Single Page Application (SPA). Zero Server Components are leveraged for initial data fetching, layout prerendering, or streaming.
- **Consequence**: Users must download the complete JavaScript bundle before any meaningful workspace content can be rendered, increasing Time to Interactive (TTI) and First Contentful Paint (FCP).

---

## 4. State Management Traps & Re-Render Cascades

### Monolithic `LiveAppContext.tsx` (698 Lines)
`LiveAppContext` holds more than 30 separate state hooks:
- Authentication (`user`, `token`, `isLoadingAuth`)
- Organizations & Projects (`organisations`, `activeOrg`, `projects`, `activeProject`, `isLoadingProjects`)
- Overview (`overview`, `isLoadingOverview`)
- Members (`members`, `isLoadingMembers`)
- Sources (`sourceMappings`, `orgConnections`, `isLoadingSources`)
- Evidence (`evidenceList`, `evidenceMetrics`, `selectedEvidenceId`, `selectedEvidence`, `isLoadingEvidence`, `evidenceFilter`)
- UI State & Modals (`6 modal states`, `isMobileSidebarOpen`, `toasts`)

```typescript
// Line 640 of LiveAppContext.tsx
const value: LiveAppContextType = {
  user, token, isLoadingAuth, login, register, logout,
  organisations, activeOrg, setActiveOrg, createOrganisation,
  projects, activeProject, setActiveProject, createProject, isLoadingProjects, refreshProjects,
  overview, isLoadingOverview, refreshOverview,
  members, isLoadingMembers, addMember, updateMember, refreshMembers,
  sourceMappings, orgConnections, isLoadingSources, connectSource, createMapping, triggerSync, refreshSources,
  evidenceList, evidenceMetrics, selectedEvidenceId, selectedEvidence, isLoadingEvidence, isLoadingEvidenceDetail,
  evidenceFilter, setEvidenceFilter, setSelectedEvidenceId, refreshEvidence, uploadDocument, downloadEvidence,
  isAuthModalOpen, setIsAuthModalOpen, authModalMode, setAuthModalMode, openAuthModal, closeAuthModal,
  isCreateOrgModalOpen, setIsCreateOrgModalOpen, isCreateProjectModalOpen, setIsCreateProjectModalOpen,
  isAddSourceModalOpen, setIsAddSourceModalOpen, isUploadModalOpen, setIsUploadModalOpen,
  isAddMemberModalOpen, setIsAddMemberModalOpen, isMobileSidebarOpen, setIsMobileSidebarOpen,
  toasts, addToast, dismissToast
};
```
Whenever **any** state changes (for example, typing a character into `evidenceFilter.q`, toggling a modal, or toast timer tick), the entire context value object is recreated. Every component subscribed via `useLiveApp()` (`AppLayout`, `Sidebar`, `TopNav`, `OverviewView`, `EvidenceCenterView`, etc.) is forced to re-render.

---

## 5. Critical Performance Bug: Cascading Network Waterfall on Item Selection

A critical defect in `LiveAppContext.tsx` causes a massive network waterfall whenever a user selects an evidence item:

### Code Trace
1. In `LiveAppContext.tsx`, `refreshEvidence` declares `selectedEvidenceId` in its dependency array:
```typescript
// Line 378 of LiveAppContext.tsx
const refreshEvidence = useCallback(async () => {
  if (!activeProject) { ... return; }
  ...
}, [activeProject, evidenceFilter, selectedEvidenceId]); // <-- Defect: selectedEvidenceId
```

2. At line 402, an effect watches `activeProject` and the data-fetching callbacks:
```typescript
// Line 402 of LiveAppContext.tsx
useEffect(() => {
  if (!activeProject) return;
  let active = true;
  void Promise.resolve().then(() => {
    if (!active) return;
    void refreshOverview();
    void refreshMembers();
    void refreshSources();
    void refreshEvidence();
  });
  return () => { active = false; };
}, [activeProject, refreshOverview, refreshMembers, refreshSources, refreshEvidence]);
```

3. When a user clicks on an item in the Evidence Library list:
   - `setSelectedEvidenceId(id)` updates state.
   - Because `selectedEvidenceId` changed, `refreshEvidence` callback identity changes.
   - Because `refreshEvidence` changed, the `useEffect` at line 402 is triggered.
   - **Result**: The application fires **four simultaneous API calls** across the network:
     - `GET /api/v1/projects/{id}/overview`
     - `GET /api/v1/projects/{id}/members`
     - `GET /api/v1/projects/{id}/sources`
     - `GET /api/v1/organisations/{id}/connections`
     - `GET /api/v1/projects/{id}/evidence`
     - `GET /api/v1/projects/{id}/evidence/metrics`
   - Simultaneously, `loadDetail` effect fires `GET /api/v1/projects/{id}/evidence/{evidenceId}`.

**Every single click on an evidence item re-fetches the entire project dataset!** This causes visible UI flickering, wasted server bandwidth, and database load.

---

## 6. Canvas & Animation Overhead: `brand/OrganicScene.tsx` (2,136 Lines)

The application includes an elaborate custom Canvas 2D/3D particle and spline rendering engine in `brand/OrganicScene.tsx`:
- Raymarching and harmonic wave perturbations.
- 3D spline conduits, traveling light pulses, and frosted glass highlight passes.
- Depth sorting and perspective projection matrix calculations.

### Critical Defect in Animation Loop (Line 1974)
```typescript
function frame(now: number) {
  if (!running) return;
  raf = requestAnimationFrame(frame); // <-- Rescheduled unconditionally!
  if (!visible || now - last < minFrame) return; // <-- Drops render, but frame keeps ticking!

  const dt = Math.min(0.05, (now - last) / 1000);
  last = now;
  const t = (now - start) / 1000;
  render(t, dt);
}
```
- **Finding**: While an `IntersectionObserver` updates `visible = entry.isIntersecting`, the animation loop calls `requestAnimationFrame(frame)` **unconditionally on line 1974** before checking `visible`.
- **Impact**: Even when scrolled completely off-screen, the browser schedules and wakes up `requestAnimationFrame` 60 times per second for each canvas instance.
- **Multiple Concurrent Instances**: On `LandingPage.tsx`, four sections mount `OrganicScene` simultaneously:
  1. `HeroSection.tsx`
  2. `IntroducingSection.tsx`
  3. `IntelligenceSection.tsx`
  4. `FinalCtaSection.tsx`
- **Result**: Four animation loops run continuously in parallel, consuming significant CPU, memory, and battery on laptops and mobile devices.

---

## 7. Core Web Vitals (CWV) Assessment

| Metric | Estimated Impact | Primary Bottleneck | Remediation Target |
| :--- | :---: | :--- | :--- |
| **LCP (Largest Contentful Paint)** | $\approx 2.4\text{s} - 3.2\text{s}$ | Massive 471 KB client bundle; synchronous rendering of 3D Canvas in Hero section. | Lazy-load `OrganicScene` below the fold; extract hero poster image. Target: $< 1.8\text{s}$. |
| **INP (Interaction to Next Paint)** | $\approx 180\text{ms} - 320\text{ms}$ | Context re-render cascade updating entire DOM tree on search filter keystrokes. | Debounce search input ($300\text{ms}$); split `LiveAppContext` into granular slices. Target: $< 100\text{ms}$. |
| **CLS (Cumulative Layout Shift)** | $\approx 0.04$ | Relatively stable layout; minor shifts during auth token validation splash. | Reserve container aspect ratios for dynamic tables and canvas elements. Target: $< 0.05$. |

---

## 8. Actionable Frontend Optimizations

1. **Fix Evidence Selection Waterfall**:
   - Remove `selectedEvidenceId` from `refreshEvidence` dependencies.
   - Refactor `refreshEvidence` to update only the list and metrics, without triggering global project re-fetches.
2. **Fix `OrganicScene` Animation Pausing**:
   - In `brand/OrganicScene.tsx`, cancel the animation frame when `visible === false` and only re-invoke `requestAnimationFrame` when the `IntersectionObserver` detects `entry.isIntersecting === true`.
3. **Split `LiveAppContext` into Focused Contexts**:
   - `AuthContext`: Authentication and session state.
   - `ProjectContext`: Active organisation and project metadata.
   - `EvidenceContext`: Evidence library and filters.
   - `UIContext`: Modals and toasts.
4. **Remove Unused Prototype Code**:
   - Delete `frontend/src/features/prototype/` (5,992 lines) to reduce project complexity and prevent bundle confusion.
5. **Re-enable TypeScript Build Verification**:
   - Remove `typescript: { ignoreBuildErrors: true }` from `frontend/next.config.ts`.
