import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import { Manrope, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { LiveAppProvider } from "../context/LiveAppContext";
import { AppLayout } from "../components/layout/AppLayout";
import { AgentationToolbar } from "../components/AgentationToolbar";

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  title: "The Handover · Intelligent Project Knowledge Reconstruction & Handover Platform",
  description: "Prevent Critical Knowledge From Leaving With People.",
  icons: {
    icon: "/favicon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${manrope.variable} ${jetbrainsMono.variable}`} suppressHydrationWarning>
      <body className="antialiased font-sans" suppressHydrationWarning>
        <LiveAppProvider>
          <Suspense fallback={null}>
            <AppLayout>{children}</AppLayout>
          </Suspense>
          <AgentationToolbar />
        </LiveAppProvider>
      </body>
    </html>
  );
}
