"use client";

import React, { useState, useEffect, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Eye, EyeOff, Loader2, CheckCircle2, ShieldCheck, AlertCircle } from "lucide-react";
import { AuthLayout } from "./AuthLayout";
import { useLiveApp } from "../../context/LiveAppContext";

export function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const registered = searchParams.get("registered") === "1";

  const { user, login, isLoadingAuth } = useLiveApp();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user && !isLoadingAuth) {
      router.push("/overview");
    }
  }, [user, isLoadingAuth, router]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanEmail = email.trim();
    if (!cleanEmail || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(cleanEmail)) {
      setError("Please enter a valid work email address.");
      return;
    }

    if (!password) {
      setError("Please enter your password.");
      return;
    }

    setLoading(true);
    try {
      await login(cleanEmail, password);
      router.push("/overview");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to sign in. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <h1 className="text-2xl font-semibold tracking-tight text-[#203653]">
        Welcome back
      </h1>
      <p className="mt-1.5 text-sm text-[#718096]">
        Sign in to continue to your Handover workspace.
      </p>

      {registered && (
        <div className="mt-4 flex items-center gap-2 rounded-xl border border-teal-200 bg-teal-50/80 p-3 text-[13px] text-teal-800">
          <CheckCircle2 className="size-4 shrink-0 text-[#299B80]" />
          <span>Account created successfully. Please sign in to continue.</span>
        </div>
      )}

      {error && (
        <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50/80 p-3 text-[13px] text-red-700">
          <AlertCircle className="size-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Figma Make: Google Sign In Button */}
      <div className="mt-6">
        <button
          type="button"
          onClick={() => {
            // Enterprise SSO / Google OAuth placeholder trigger
            setError("Google Workspace SSO requires organisation domain configuration in Settings.");
          }}
          className="flex h-11 w-full items-center justify-center gap-2.5 rounded-xl border border-[#D9E1F0] bg-white px-4 text-sm font-semibold text-[#203653] shadow-2xs hover:bg-[#F6F8FC] hover:border-[#C3D2EC] active:scale-[0.99] transition cursor-pointer"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden>
            <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.2-2.1 3.5-5.1 3.5-8.8Z" />
            <path fill="#34A853" d="M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24Z" />
            <path fill="#FBBC05" d="M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6h-4a12 12 0 0 0 0 10.8l4-3.1Z" />
            <path fill="#EA4335" d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.9 3.6-4.9 6.7-4.9Z" />
          </svg>
          <span>Continue with Google</span>
        </button>
      </div>

      {/* Figma Make: Divider */}
      <div className="my-5 flex items-center gap-3 text-xs text-[#718096]">
        <span className="h-px flex-1 bg-[#D9E1F0]" />
        <span>or sign in with email</span>
        <span className="h-px flex-1 bg-[#D9E1F0]" />
      </div>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-[#718096] mb-1.5">
            Work email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            autoComplete="email"
            required
            className="w-full h-11 rounded-xl border border-[#D9E1F0] bg-white px-3.5 text-sm text-[#203653] placeholder:text-slate-400 focus:border-[#315FBA] focus:outline-none focus:ring-1 focus:ring-[#315FBA] transition"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-[#718096] mb-1.5">
            Password
          </label>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              autoComplete="current-password"
              required
              className="w-full h-11 rounded-xl border border-[#D9E1F0] bg-white px-3.5 pr-10 text-sm text-[#203653] placeholder:text-slate-400 focus:border-[#315FBA] focus:outline-none focus:ring-1 focus:ring-[#315FBA] transition"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-[#203653] transition"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between text-[13px]">
          <label className="flex items-center gap-2 cursor-pointer text-[#718096]">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="size-4 rounded border-[#D9E1F0] text-[#315FBA] focus:ring-[#315FBA]"
            />
            <span>Remember me</span>
          </label>
          <Link
            href="/forgot-password"
            className="font-medium text-[#315FBA] hover:underline"
          >
            Forgot password?
          </Link>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="mt-2 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#203653] text-sm font-semibold text-white shadow-xs transition hover:bg-[#2b466c] active:scale-[0.99] disabled:opacity-60 cursor-pointer"
        >
          {loading ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              <span>Signing in…</span>
            </>
          ) : (
            <span>Sign in</span>
          )}
        </button>
      </form>

      <div className="mt-6 text-center text-sm text-[#718096]">
        New to Handover?{" "}
        <Link href="/signup" className="font-semibold text-[#315FBA] hover:underline">
          Create an account
        </Link>
      </div>

      <div className="mt-6 flex items-center justify-center gap-1.5 text-[11.5px] text-[#718096]/90 border-t border-[#D9E1F0] pt-4">
        <ShieldCheck className="size-3.5 text-[#299B80]" />
        <span>Enterprise auth: Argon2id hashing · AES-256-GCM encryption</span>
      </div>
    </AuthLayout>
  );
}
