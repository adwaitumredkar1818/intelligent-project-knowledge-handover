"use client";

import React, { type ReactNode } from "react";
import { DemoBanner } from "./DemoBanner";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";
import { GlobalSearchModal } from "./GlobalSearchModal";
import { ToastContainer } from "./ToastContainer";
import { CreateProjectModal } from "../project/CreateProjectModal";
import { AddSourceModal } from "../sources/AddSourceModal";
import { UploadDocumentModal } from "../evidence/UploadDocumentModal";

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="min-h-screen bg-[#F4F6F9] text-[#25334B] flex flex-col font-sans antialiased">
      {/* 1. Mandatory Persistent Demo Banner */}
      <DemoBanner />

      {/* 2. Main Shell Layout (Sidebar + Content) */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Persistent Dark Navy Sidebar */}
        <Sidebar />

        {/* Central Region (TopNav + Workspace View) */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0 overflow-hidden bg-[#F4F6F9]">
          <TopNav />

          {/* Central Workspace Region C */}
          <main className="flex-1 overflow-y-auto min-h-0 focus:outline-none">
            {children}
          </main>
        </div>
      </div>

      {/* 3. Global Interactive Modals & Floating Toasts */}
      <GlobalSearchModal />
      <CreateProjectModal />
      <AddSourceModal />
      <UploadDocumentModal />
      <ToastContainer />
    </div>
  );
}
