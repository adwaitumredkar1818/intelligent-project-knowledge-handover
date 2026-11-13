"use client";

import React, { useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowLeft, Mail, MailCheck, Loader2, ShieldCheck } from "lucide-react";
import { AuthLayout } from "./AuthLayout";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanEmail = email.trim();
    if (!cleanEmail || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(cleanEmail)) {
      setError("Please enter a valid work email address.");
      return;
    }

    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setSent(true);
    }, 700);
  };

  return (
    <AuthLayout>
      <Link
        href="/login"
        className="mb-6 inline-flex items-center gap-1.5 text-[13px] font-medium text-[#718096] hover:text-[#203653] transition"
      >
        <ArrowLeft className="size-4" />
        <span>Back to sign in</span>
      </Link>

      {sent ? (
        <div className="animate-fade">
          <span className="flex size-12 items-center justify-center rounded-2xl bg-teal-50 text-[#299B80]">
            <MailCheck className="size-6" />
          </span>
          <h1 className="mt-5 text-2xl font-semibold tracking-tight text-[#203653]">
            Check your inbox
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-[#56657c]">
            If an account exists for{" "}
            <span className="font-semibold text-[#203653]">{email}</span>, we sent a link to
            reset your password. The link expires in 30 minutes.
          </p>
          <div className="mt-6 space-y-2.5">
            <Link
              href="/login"
              className="flex h-11 w-full items-center justify-center rounded-xl bg-[#203653] text-sm font-semibold text-white shadow-xs transition hover:bg-[#2b466c]"
            >
              Return to sign in
            </Link>
            <button
              type="button"
              onClick={() => setSent(false)}
              className="flex h-10 w-full items-center justify-center rounded-xl border border-[#D9E1F0] bg-white text-sm font-medium text-[#718096] hover:bg-slate-50 transition cursor-pointer"
            >
              Didn&apos;t get the email? Resend
            </button>
          </div>
        </div>
      ) : (
        <>
          <span className="flex size-12 items-center justify-center rounded-2xl bg-[#EDF2FA] text-[#315FBA]">
            <Mail className="size-6" />
          </span>
          <h1 className="mt-5 text-2xl font-semibold tracking-tight text-[#203653]">
            Reset your password
          </h1>
          <p className="mt-1.5 text-sm text-[#718096]">
            Enter the work email associated with your account and we will send password reset instructions.
          </p>

          {error && (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50/80 p-3 text-[13px] text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
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

            <button
              type="submit"
              disabled={loading}
              className="mt-2 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#203653] text-sm font-semibold text-white shadow-xs transition hover:bg-[#2b466c] active:scale-[0.99] disabled:opacity-60 cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  <span>Sending…</span>
                </>
              ) : (
                <span>Send reset link</span>
              )}
            </button>
          </form>
        </>
      )}

      <div className="mt-6 flex items-center justify-center gap-1.5 text-[11.5px] text-[#718096]/90 border-t border-[#D9E1F0] pt-4">
        <ShieldCheck className="size-3.5 text-[#299B80]" />
        <span>Enterprise auth: Argon2id hashing · AES-256-GCM encryption</span>
      </div>
    </AuthLayout>
  );
}
