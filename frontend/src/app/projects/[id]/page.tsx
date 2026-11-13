"use client";

import React, { Suspense } from "react";
import { useParams } from "next/navigation";
import { ProjectWorkspaceLayout } from "../../../components/project-workspace/ProjectWorkspaceLayout";
import { Loader2 } from "lucide-react";

function ProjectWorkspaceContent() {
  const params = useParams();
  const id = Array.isArray(params?.id) ? params.id[0] : (params?.id as string);

  if (!id) {
    return (
      <div className="flex items-center justify-center p-12 text-xs text-muted">
        <Loader2 className="size-4 animate-spin mr-2" />
        <span>Resolving project workspace...</span>
      </div>
    );
  }

  return <ProjectWorkspaceLayout projectId={id} />;
}

export default function ProjectWorkspacePage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center p-12 text-xs text-muted">
          <Loader2 className="size-4 animate-spin mr-2" />
          <span>Loading project workspace...</span>
        </div>
      }
    >
      <ProjectWorkspaceContent />
    </Suspense>
  );
}
