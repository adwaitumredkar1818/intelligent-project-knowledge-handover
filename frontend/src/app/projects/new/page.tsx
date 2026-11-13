"use client";

import React, { Suspense } from "react";
import { ProjectCreationWizard } from "../../../components/project-workspace/ProjectCreationWizard";
import { Loader2 } from "lucide-react";

export default function NewProjectPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center p-12 text-xs text-muted">
          <Loader2 className="size-4 animate-spin mr-2" />
          <span>Loading project creation wizard...</span>
        </div>
      }
    >
      <ProjectCreationWizard />
    </Suspense>
  );
}
