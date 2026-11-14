"use client";

import React, { type ReactNode } from "react";
import { AppLayout } from "./AppLayout";
import { RoleBadge, ROLE_TONE } from "./Sidebar";
import { Toaster } from "../figma-ui/index";

export { RoleBadge, ROLE_TONE, Toaster };

/**
 * Shell wrapper providing full Figma Make parity.
 * Delegates to the unified production AppLayout.
 */
export function Shell({
  children,
  crumbs,
  wide,
}: {
  children: ReactNode;
  crumbs?: { label: string; to?: string }[];
  wide?: boolean;
}) {
  return <AppLayout>{children}</AppLayout>;
}
