"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { X } from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import { ProjectCreationWizard } from "../project-workspace/ProjectCreationWizard";

export function CreateProjectModal() {
  const router = useRouter();
  const { isCreateProjectModalOpen, setIsCreateProjectModalOpen } = useLiveApp();

  if (!isCreateProjectModalOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-2xs p-4 overflow-y-auto">
      <div className="relative w-full max-w-4xl bg-white rounded-2xl shadow-2xl border border-line overflow-hidden my-8 max-h-[92vh] flex flex-col">
        {/* Modal Close Button */}
        <button
          type="button"
          onClick={() => setIsCreateProjectModalOpen(false)}
          className="absolute right-4 top-4 z-10 p-2 rounded-lg text-slate-400 hover:text-navy hover:bg-slate-100 transition-colors cursor-pointer"
          aria-label="Close modal"
        >
          <X className="size-5" />
        </button>

        {/* Modal Body hosting the 3-stage wizard */}
        <div className="p-6 sm:p-8 overflow-y-auto">
          <ProjectCreationWizard
            isModal={true}
            onSuccess={(newProj) => {
              setIsCreateProjectModalOpen(false);
              if (newProj?.id) {
                router.push(`/projects/${newProj.id}/evidence`);
              }
            }}
            onCancel={() => setIsCreateProjectModalOpen(false)}
          />
        </div>
      </div>
    </div>
  );
}
