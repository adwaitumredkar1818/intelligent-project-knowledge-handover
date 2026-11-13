"use client";

import React, { type ReactNode } from "react";
import { AppLayout } from "./AppLayout";
import { RoleBadge, ROLE_TONE } from "../ui";

export { RoleBadge, ROLE_TONE };

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
