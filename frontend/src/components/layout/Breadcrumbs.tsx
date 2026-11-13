"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import { cn } from "../../lib/utils";

export interface Crumb {
  label: string;
  to?: string;
}

export function Breadcrumbs({ crumbs }: { crumbs?: Crumb[] }) {
  const pathname = usePathname();
  const { activeOrg, activeProject } = useLiveApp();

  const orgName = activeOrg?.name || "The Handover";
  const orgInitial = orgName.charAt(0).toUpperCase();

  // Generate automatic breadcrumbs if explicit crumbs are not provided
  const generatedCrumbs: Crumb[] = React.useMemo(() => {
    if (crumbs && crumbs.length > 0) return crumbs;

    const list: Crumb[] = [];

    switch (pathname) {
      case "/overview":
        if (activeProject) {
          list.push({ label: "Projects", to: "/projects" });
          list.push({ label: activeProject.name, to: "/overview" });
        }
        list.push({ label: "Overview" });
        break;
      case "/projects":
        list.push({ label: "My Projects" });
        break;
      case "/team":
        if (activeProject) {
          list.push({ label: "Projects", to: "/projects" });
          list.push({ label: activeProject.name, to: "/overview" });
        }
        list.push({ label: "Team Members" });
        break;
      case "/evidence":
        if (activeProject) {
          list.push({ label: "Projects", to: "/projects" });
          list.push({ label: activeProject.name, to: "/overview" });
        }
        list.push({ label: "Evidence Center" });
        break;
      case "/knowledge":
        if (activeProject) {
          list.push({ label: "Projects", to: "/projects" });
          list.push({ label: activeProject.name, to: "/overview" });
        }
        list.push({ label: "Knowledge Intelligence" });
        break;
      case "/relationships":
        if (activeProject) {
          list.push({ label: "Projects", to: "/projects" });
          list.push({ label: activeProject.name, to: "/overview" });
        }
        list.push({ label: "Relationship Explorer" });
        break;
      case "/verification":
        list.push({ label: "Validation", to: "/verification" });
        list.push({ label: "Verification Center" });
        break;
      case "/conflicts":
        list.push({ label: "Validation", to: "/verification" });
        list.push({ label: "Conflicts" });
        break;
      case "/handover":
        list.push({ label: "Knowledge Transfer", to: "/handover" });
        list.push({ label: "Handover Workspace" });
        break;
      case "/generated-handovers":
        list.push({ label: "Knowledge Transfer", to: "/handover" });
        list.push({ label: "Generated Handovers" });
        break;
      case "/assistant":
        list.push({ label: "AI Assistant", to: "/assistant" });
        list.push({ label: "Project Knowledge Assistant" });
        break;
      case "/sources":
        list.push({ label: "Administration", to: "/settings" });
        list.push({ label: "Connected Sources" });
        break;
      case "/audit":
        list.push({ label: "Administration", to: "/settings" });
        list.push({ label: "Audit Logs" });
        break;
      case "/settings":
        list.push({ label: "Administration", to: "/settings" });
        list.push({ label: "Settings" });
        break;
      default: {
        const seg = pathname.replace(/^\//, "").split("/")[0];
        if (seg) {
          list.push({
            label: seg.charAt(0).toUpperCase() + seg.slice(1).replace(/-/g, " "),
          });
        } else {
          list.push({ label: "Overview" });
        }
        break;
      }
    }

    return list;
  }, [crumbs, pathname, activeProject]);

  return (
    <nav aria-label="Breadcrumb" className="hidden min-w-0 items-center gap-1.5 text-[13px] md:flex">
      {/* Workspace Root Node */}
      <span className="flex shrink-0 items-center gap-1.5 text-muted">
        <span className="flex size-[18px] items-center justify-center rounded-[5px] bg-navy text-[9px] font-bold text-white shadow-2xs">
          {orgInitial}
        </span>
        <span className="hidden lg:inline font-medium text-slate-600 truncate max-w-[140px]">
          {orgName}
        </span>
      </span>

      {/* Path Crumbs */}
      {generatedCrumbs.map((c, i) => {
        const isLast = i === generatedCrumbs.length - 1;
        return (
          <span key={i} className="flex min-w-0 items-center gap-1.5">
            <ChevronRight className="size-3.5 shrink-0 text-slate-300" />
            {c.to && !isLast ? (
              <Link
                href={c.to}
                className="truncate text-muted transition-colors hover:text-navy"
              >
                {c.label}
              </Link>
            ) : (
              <span
                className={cn(
                  "truncate",
                  isLast ? "font-semibold text-navy" : "text-muted"
                )}
              >
                {c.label}
              </span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
