"use client";

import React, { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Sidebar, RoleBadge } from "./Sidebar";
import { TopNav } from "./TopNav";
import { CommandPalette } from "./CommandPalette";
import { ToastContainer } from "../common/ToastContainer";
import { Logo } from "../brand";
import { CreateOrganisationModal } from "../modals/CreateOrganisationModal";
import { CreateProjectModal } from "../modals/CreateProjectModal";
import { UploadDocumentModal } from "../modals/UploadDocumentModal";
import { ConnectSourceModal } from "../modals/ConnectSourceModal";
import { AddMemberModal } from "../modals/AddMemberModal";
import { useLiveApp } from "../../context/LiveAppContext";

export { RoleBadge };

export function AppLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoadingAuth } = useLiveApp();

  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window !== "undefined") {
      return (
        localStorage.getItem("handover_sidebar_collapsed") === "true" ||
        window.location.search.includes("collapsed=true")
      );
    }
    return false;
  });
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(() => {
    if (typeof window !== "undefined") {
      return window.location.search.includes("openPalette=true");
    }
    return false;
  });

  // Restore collapsed sidebar preference from localStorage or URL query
  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("handover_sidebar_collapsed");
      const urlHasCollapsed = window.location.search.includes("collapsed=true");
      if (saved === "true" || urlHasCollapsed) {
        setCollapsed(true);
      }
      if (window.location.search.includes("openPalette=true")) {
        setIsCommandPaletteOpen(true);
      }
    }
  }, []);

  const handleToggleCollapse = () => {
    setCollapsed((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        localStorage.setItem("handover_sidebar_collapsed", String(next));
      }
      return next;
    });
  };

  const isAuthPage =
    pathname === "/login" ||
    pathname === "/signup" ||
    pathname === "/forgot-password" ||
    pathname === "/onboarding";

  const isPublicRoute = pathname === "/" || pathname === "/landing" || isAuthPage;

  // Protect all non-public routes by cleanly redirecting unauthenticated users to /login
  useEffect(() => {
    if (!isPublicRoute && !isLoadingAuth && !user) {
      router.push("/login");
    }
  }, [isPublicRoute, isLoadingAuth, user, router]);

  // Public and authentication pages bypass the authenticated shell
  if (isPublicRoute) {
    return (
      <div className="min-h-screen w-full bg-[#F6F8FC] text-navy font-sans antialiased">
        {children}
        <ToastContainer />
      </div>
    );
  }

  // Wide container for data-dense routes
  const isWide =
    pathname === "/evidence" ||
    pathname === "/audit" ||
    pathname === "/knowledge" ||
    pathname === "/relationships" ||
    pathname === "/verification" ||
    pathname === "/handover";

  return (
    <div className="flex h-dvh overflow-hidden bg-canvas font-sans antialiased text-navy">
      {/* Desktop Persistent Sidebar & Mobile Drawer */}
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={handleToggleCollapse}
        onOpenSearch={() => setIsCommandPaletteOpen(true)}
      />

      {/* Main Content Column */}
      <div className="flex min-w-0 flex-1 flex-col h-full overflow-hidden">
        <TopNav
          collapsed={collapsed}
          onToggleCollapse={handleToggleCollapse}
          onOpenSearch={() => setIsCommandPaletteOpen(true)}
        />

        <main id="main-scroll" className="ambient-canvas scrollbar-thin flex-1 overflow-y-auto relative">
          {(!user || isLoadingAuth) && (
            <div className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-canvas/80 backdrop-blur-xs">
              <div className="flex flex-col items-center gap-3">
                <Logo size={32} />
                <p className="text-xs text-muted">Verifying workspace session…</p>
              </div>
            </div>
          )}

          <div
            className={`animate-fade mx-auto w-full px-4 py-6 sm:px-6 lg:px-8 lg:py-8 ${
              isWide ? "max-w-[1600px]" : "max-w-[1360px]"
            }`}
          >
            {children}
          </div>
        </main>
      </div>

      {/* Global Modals & Keyboard Spotlight */}
      <CommandPalette
        open={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />
      <ToastContainer />
      <CreateOrganisationModal />
      <CreateProjectModal />
      <UploadDocumentModal />
      <ConnectSourceModal />
      <AddMemberModal />
    </div>
  );
}
