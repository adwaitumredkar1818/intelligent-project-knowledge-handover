import { Layers } from "lucide-react";

export default function HomePage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background p-8 text-foreground">
      <div className="max-w-md rounded-lg border border-border bg-card p-6 text-card-foreground shadow-xs">
        <div className="mb-3 flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Layers className="h-4 w-4" aria-hidden="true" />
          <span>Runtime Environment Initialised</span>
        </div>
        <h1 className="text-lg font-semibold">
          Intelligent Project Knowledge Reconstruction &amp; Handover Platform
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Phase 1.2 frontend toolchain ready. Product modules will be implemented in subsequent
          phases.
        </p>
      </div>
    </main>
  );
}
