"use client";

import React, { useState } from "react";
import { Lock, Mail, User as UserIcon, ArrowRight, ShieldCheck, AlertCircle } from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

export function AuthModal() {
  const { user, login, register, isLoadingAuth } = useLiveApp();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (isLoadingAuth || user) {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        if (!fullName.trim()) {
          throw new Error("Please enter your full name");
        }
        await register(email, password, fullName);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Authentication failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#1E2C42]/80 backdrop-blur-xs p-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-2xl border border-[#DCE3EB] overflow-hidden">
        {/* Header */}
        <div className="bg-[#253650] text-white p-6 text-center relative">
          <div className="w-12 h-12 rounded-xl bg-[#4774A9] border border-[#249E91]/40 flex items-center justify-center font-bold text-xl mx-auto shadow-md mb-3 text-white">
            H
          </div>
          <h2 className="text-lg font-bold tracking-tight">The Handover</h2>
          <p className="text-xs text-[#249E91] font-medium mt-0.5">
            Intelligent Project Knowledge Reconstruction &amp; Handover Platform
          </p>
          <p className="text-[11px] text-[#A0AEC0] mt-2 max-w-xs mx-auto leading-relaxed">
            Prevent Critical Knowledge From Leaving With People.
          </p>
        </div>

        {/* Form Body */}
        <div className="p-6">
          <div className="flex border-b border-[#DCE3EB] mb-5 text-xs font-semibold">
            <button
              type="button"
              className={`pb-2.5 px-4 transition-colors ${
                mode === "login"
                  ? "border-b-2 border-[#4774A9] text-[#4774A9]"
                  : "text-[#69778D] hover:text-[#25334B]"
              }`}
              onClick={() => {
                setMode("login");
                setErrorMessage(null);
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`pb-2.5 px-4 transition-colors ${
                mode === "register"
                  ? "border-b-2 border-[#4774A9] text-[#4774A9]"
                  : "text-[#69778D] hover:text-[#25334B]"
              }`}
              onClick={() => {
                setMode("register");
                setErrorMessage(null);
              }}
            >
              Create Account
            </button>
          </div>

          {errorMessage && (
            <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <div>
                <label className="block text-xs font-semibold text-[#25334B] mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <UserIcon className="w-4 h-4 text-[#69778D] absolute left-3 top-2.5" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Elena Rostova"
                    className="w-full pl-9 pr-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-[#25334B] mb-1">
                Work Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-[#69778D] absolute left-3 top-2.5" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@organization.com"
                  className="w-full pl-9 pr-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#25334B] mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-[#69778D] absolute left-3 top-2.5" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-3 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 py-2.5 px-4 rounded-lg bg-[#4774A9] hover:bg-[#365F92] text-white text-xs font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50 cursor-pointer shadow-xs"
            >
              <span>{isSubmitting ? "Authenticating..." : mode === "login" ? "Sign In to Workspace" : "Create Account & Workspace"}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="mt-5 pt-4 border-t border-[#DCE3EB] flex items-center justify-between text-[11px] text-[#69778D]">
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-[#249E91]" />
              <span>FastAPI &amp; Supabase Auth JWKS</span>
            </div>
            <span>AES-256-GCM Encrypted</span>
          </div>
        </div>
      </div>
    </div>
  );
}
