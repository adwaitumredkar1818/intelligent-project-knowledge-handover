import React, { type ReactNode } from "react";
import type { Metadata } from "next";
import { PrototypeProvider } from "../../features/prototype/context/PrototypeContext";
import { AppLayout } from "../../features/prototype/components/app-shell/AppLayout";

export const metadata: Metadata = {
  title: "The Handover · Interactive Prototype",
  description:
    "Interactive frontend prototype for The Handover — Intelligent Project Knowledge Reconstruction & Handover Platform.",
};

export default function PrototypeRootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <PrototypeProvider>
      <AppLayout>{children}</AppLayout>
    </PrototypeProvider>
  );
}
