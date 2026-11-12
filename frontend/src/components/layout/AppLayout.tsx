"use client";

import React, { type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";
import { ToastContainer } from "../common/ToastContainer";
import { AuthModal } from "../auth/AuthModal";
import { CreateOrganisationModal } from "../modals/CreateOrganisationModal";
import { CreateProjectModal } from "../modals/CreateProjectModal";
import { UploadDocumentModal } from "../modals/UploadDocumentModal";
import { ConnectSourceModal } from "../modals/ConnectSourceModal";
import { AddMemberModal } from "../modals/AddMemberModal";
import { useLiveApp } from "../../context/LiveAppContext";

export function AppLayout({ children }: { children: ReactNode }) {
  const { user, isLoadingAuth } = useLiveApp();

  return (
    <div className="flex h-screen w-full bg-[#F4F6F9] text-[#25334B] overflow-hidden">
      {/* Persistent Sidebar */}
      <Sidebar />

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <TopNav />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 bg-[#F4F6F9]">
          {children}
        </main>
      </div>

      {/* Global Modals & Notifications */}
      <ToastContainer />
      <AuthModal />
      <CreateOrganisationModal />
      <CreateProjectModal />
      <UploadDocumentModal />
      <ConnectSourceModal />
      <AddMemberModal />
    </div>
  );
}
