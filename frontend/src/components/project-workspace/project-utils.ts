import {
  LayoutDashboard,
  Users,
  Settings,
  Activity,
  type LucideIcon,
} from "lucide-react";

export interface ProjectTabItem {
  id: "overview" | "team" | "settings" | "activity";
  label: string;
  icon: LucideIcon;
}

export const PROJECT_TABS: ProjectTabItem[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "team", label: "Team", icon: Users },
  { id: "settings", label: "Settings", icon: Settings },
  { id: "activity", label: "Activity", icon: Activity },
];

const PALETTE = [
  "#315FBA",
  "#299B80",
  "#D39B43",
  "#5B8BC9",
  "#6366F1",
  "#8B5CF6",
  "#059669",
  "#D97706",
  "#0284C7",
];

export function getProjectCode(name?: string, slug?: string): string {
  if (!name && !slug) return "PRJ";
  const source = (name || slug || "").trim();
  const words = source.split(/[\s-_]+/).filter(Boolean);
  if (words.length >= 2 && words[0] && words[1] && words[0][0] && words[1][0]) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  const clean = source.replace(/[^A-Za-z0-9]/g, "");
  return clean.slice(0, 3).toUpperCase() || "PRJ";
}

export function getProjectColor(key?: string): string {
  if (!key) return PALETTE[0] || "#315FBA";
  let hash = 0;
  for (let i = 0; i < key.length; i++) {
    hash = (hash << 5) - hash + key.charCodeAt(i);
    hash |= 0;
  }
  const index = Math.abs(hash) % PALETTE.length;
  return PALETTE[index] || "#315FBA";
}

export function normalizeProjectRole(role?: string | null): string {
  if (!role) return "Member";
  const r = role.toLowerCase().trim();
  if (r.includes("manager") || r === "pm") return "Project Manager";
  if (r.includes("outgoing") || r.includes("departing")) return "Outgoing Member";
  if (r.includes("incoming") || r.includes("successor")) return "Incoming Member";
  if (r.includes("reviewer")) return "Reviewer";
  if (r.includes("observer") || r.includes("viewer")) return "Viewer";
  return "Contributor";
}
