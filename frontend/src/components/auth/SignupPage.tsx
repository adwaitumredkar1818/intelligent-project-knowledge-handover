"use client";

import React, { useState, useEffect, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Loader2, ShieldCheck, AlertCircle } from "lucide-react";
import { AuthLayout } from "./AuthLayout";
import { useLiveApp } from "../../context/LiveAppContext";

export function SignupPage() {
  const router = useRouter();
  const { user, register, isLoadingAuth } = useLiveApp();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user && !isLoadingAuth) {
      router.push("/overview");
    }
  }, [user, isLoadingAuth, router]);

  // Enterprise password strength calculation (matches backend Argon2id & validator rules)
  const hasMinLength = password.length >= 12;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSpecial = /[^A-Za-z0-9\s]/.test(password);

  const strengthCount = [hasMinLength, hasUpper && hasLower, hasNumber, hasSpecial].filter(
    Boolean
  ).length;

  const strengthLabels = ["Add password", "Weak", "Fair", "Good", "Strong"];

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (fullName.trim().length < 2) {
      setError("Please enter your full name (at least 2 characters).");
      return;
    }

    const cleanEmail = email.trim();
    if (!cleanEmail || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(cleanEmail)) {
      setError("Please enter a valid work email address.");
      return;
    }

    if (!hasMinLength || !hasUpper || !hasLower || !hasNumber || !hasSpecial) {
      setError(
        "Password must be at least 12 characters and include uppercase, lowercase, numbers, and special characters."
      );
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (!agreeTerms) {
      setError("You must agree to the platform security terms and privacy policy to continue.");
      return;
    }

    setLoading(true);
    try {
      await register(cleanEmail, password, fullName.trim());
      router.push("/overview");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create account.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <h1 className="text-2xl font-semibold tracking-tight text-[#203653]">
        Create your account
      </h1>
      <p className="mt-1.5 text-sm text-[#718096]">
        Start capturing and transferring project knowledge before it is lost.
      </p>

      {error && (
        <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50/80 p-3 text-[13px] text-red-700">
          <AlertCircle className="size-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Figma Make: Google Sign Up Button */}
      <div className="mt-6">
        <button
          type="button"
          onClick={() => {
            setError("Google Workspace SSO registration requires domain verification by your workspace admin.");
          }}
          className="flex h-11 w-full items-center justify-center gap-2.5 rounded-xl border border-[#D9E1F0] bg-white px-4 text-sm font-semibold text-[#203653] shadow-2xs hover:bg-[#F6F8FC] hover:border-[#C3D2EC] active:scale-[0.99] transition cursor-pointer"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden>
            <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.2-2.1 3.5-5.1 3.5-8.8Z" />
            <path fill="#34A853" d="M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24Z" />
            <path fill="#FBBC05" d="M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6h-4a12 12 0 0 0 0 10.8l4-3.1Z" />
            <path fill="#EA4335" d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.9 3.6-4.9 6.7-4.9Z" />
          </svg>
          <span>Sign up with Google</span>
        </button>
      </div>

      {/* Figma Make: Divider */}
      <div className="my-5 flex items-center gap-3 text-xs text-[#718096]">
        <span className="h-px flex-1 bg-[#D9E1F0]" />
        <span>or sign up with email</span>
        <span className="h-px flex-1 bg-[#D9E1F0]" />
      </div>

      <form onSubmit={handleSubmit} className="space-y-3.5" noValidate>
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-[#718096] mb-1.5">
            Full name
          </label>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Maya Chen"
            autoComplete="name"
            required
            className="w-full h-10 rounded-xl border border-[#D9E1F0] bg-white px-3.5 text-sm text-[#203653] placeholder:text-slate-400 focus:border-[#315FBA] focus:outline-none focus:ring-1 focus:ring-[#315FBA] transition"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-[#718096] mb-1.5">
            Work email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="maya.chen@company.com"
            autoComplete="email"
            required
            className="w-full h-10 rounded-xl border border-[#D9E1F0] bg-white px-3.5 text-sm text-[#203653] placeholder:text-slate-400 focus:border-[#315FBA] focus:outline-none focus:ring-1 focus:ring-[#315FBA] transition"
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
              placeholder="Min. 12 characters"
              autoComplete="new-password"
              required
              className="w-full h-10 rounded-xl border border-[#D9E1F0] bg-white px-3.5 pr-10 text-sm text-[#203653] placeholder:text-slate-400 focus:border-[#315FBA] focus:outline-none focus:ring-1 focus:ring-[#315FBA] transition"
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

          {/* Password strength indicators */}
          {password.length > 0 && (
            <div className="mt-2">
              <div className="flex gap-1">
                {[1, 2, 3, 4].map((i) => (
                  <span
                    key={i}
                    className={`h-1 flex-1 rounded-full transition-colors ${
                      i <= strengthCount
                        ? strengthCount <= 1
                          ? "bg-red-500"
                          : strengthCount <= 2
                          ? "bg-amber-500"
                          : strengthCount <= 3
                          ? "bg-blue-500"
                          : "bg-teal-500"
                        : "bg-slate-200"
                    }`}
                  />
                ))}
              </div>
              <div className="mt-1 flex items-center justify-between text-[11px] text-[#718096]">
                <span>Strength: {strengthLabels[strengthCount]}</span>
                <span>Requires 12+ chars, Aa, 0-9, symbol</span>
              </div>
            </div>
          )}
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-[#718096] mb-1.5">
            Confirm password
          </label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Repeat password"
            autoComplete="new-password"
            required
            className="w-full h-10 rounded-xl border border-[#D9E1F0] bg-white px-3.5 text-sm text-[#203653] placeholder:text-slate-400 focus:border-[#315FBA] focus:outline-none focus:ring-1 focus:ring-[#315FBA] transition"
          />
        </div>

        <div className="pt-1">
          <label className="flex items-start gap-2 cursor-pointer text-[12.5px] text-[#718096] leading-snug">
            <input
              type="checkbox"
              checked={agreeTerms}
              onChange={(e) => setAgreeTerms(e.target.checked)}
              className="size-4 mt-0.5 rounded border-[#D9E1F0] text-[#315FBA] focus:ring-[#315FBA]"
            />
            <span>
              I agree to the platform{" "}
              <Link href="/#security" className="text-[#315FBA] underline">
                Security &amp; Governance Terms
              </Link>{" "}
              and privacy standards.
            </span>
          </label>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="mt-3 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#203653] text-sm font-semibold text-white shadow-xs transition hover:bg-[#2b466c] active:scale-[0.99] disabled:opacity-60 cursor-pointer"
        >
          {loading ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              <span>Creating account…</span>
            </>
          ) : (
            <span>Create account</span>
          )}
        </button>
      </form>

      <div className="mt-5 text-center text-sm text-[#718096]">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-[#315FBA] hover:underline">
          Sign in
        </Link>
      </div>

      <div className="mt-5 flex items-center justify-center gap-1.5 text-[11.5px] text-[#718096]/90 border-t border-[#D9E1F0] pt-3.5">
        <ShieldCheck className="size-3.5 text-[#299B80]" />
        <span>Enterprise auth: Argon2id hashing · AES-256-GCM encryption</span>
      </div>
    </AuthLayout>
  );
}
