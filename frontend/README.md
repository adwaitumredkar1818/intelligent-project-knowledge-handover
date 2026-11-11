# Frontend Runtime Environment

Next.js + React + TypeScript + Tailwind CSS + shadcn/ui-compatible configuration + Lucide Icons.

> **Note:** Scripts in [`package.json`](package.json) invoke binaries directly via `node ./node_modules/...` so they work reliably on Windows even when the parent workspace directory contains `&`.

## Commands

```powershell
npm run dev           # Start Next.js development server (http://localhost:3000)
npm run build         # Build production bundle
npm run typecheck     # Run Next.js typegen and strict TypeScript check (tsc --noEmit)
npm run lint          # Run ESLint across the frontend workspace
npm run format:check  # Check Prettier formatting
npm run format        # Apply Prettier formatting
```

See [`../documentation/development/environment-setup.md`](../documentation/development/environment-setup.md) for full environment setup and backend/infrastructure coordination.
