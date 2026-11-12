import type { Metadata } from "next";
import "./globals.css";
import { LiveAppProvider } from "../context/LiveAppContext";
import { AppLayout } from "../components/layout/AppLayout";

export const metadata: Metadata = {
  title: "The Handover · Intelligent Project Knowledge Reconstruction & Handover Platform",
  description: "Prevent Critical Knowledge From Leaving With People.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <LiveAppProvider>
          <AppLayout>{children}</AppLayout>
        </LiveAppProvider>
      </body>
    </html>
  );
}
