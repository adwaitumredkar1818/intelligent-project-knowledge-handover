"use client";

import React, { useState } from "react";
import {
  Lock,
  Mail,
  User as UserIcon,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  Eye,
  EyeOff,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

export function AuthModal() {
  const { user, login, register, isLoadingAuth } = useLiveApp();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (isLoadingAuth || user) {
    return null;
  }

  // Password strength checks (matches backend validate_password_strength)
  const hasMinLength = password.length >= 12;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSpecial = /[^A-Za-z0-9\s]/.test(password);
  const isPasswordStrong = hasMinLength && hasUpper && hasLower && hasNumber && hasSpecial;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (mode === "register") {
      if (fullName.trim().length < 2) {
        setErrorMessage("Please enter your full name (at least 2 characters).");
        return;
      }
      if (!isPasswordStrong) {
        setErrorMessage(
          "Password does not meet enterprise security requirements (must be at least 12 characters with uppercase, lowercase, numbers, and special symbols)."
        );
        return;
      }
    }

    setIsSubmitting(true);
    try {
      if (mode === "login") {
        await login(email.trim(), password);
      } else {
        await register(email.trim(), password, fullName.trim());
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
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-[#25334B]">
                  Password
                </label>
                {mode === "register" && (
                  <span className="text-[10px] text-[#69778D]">
                    Min 12 chars, upper, lower, num &amp; symbol
                  </span>
                )}
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-[#69778D] absolute left-3 top-2.5" />
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={mode === "register" ? "e.g. HandoverPass2026!" : "••••••••"}
                  className="w-full pl-9 pr-10 py-2 rounded-lg border border-[#DCE3EB] text-xs focus:outline-none focus:ring-2 focus:ring-[#4774A9] text-[#25334B]"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-[#69778D] hover:text-[#25334B] transition-colors focus:outline-none"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>

              {/* Password strength criteria indicator in register mode */}
              {mode === "register" && password.length > 0 && (
                <div className="mt-2.5 p-2.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] space-y-1.5 text-[11px]">
                  <div className="font-semibold text-[#475569] mb-1">
                    Password Requirements:
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    <div
                      className={`flex items-center gap-1.5 ${
                        hasMinLength ? "text-emerald-700 font-medium" : "text-[#64748B]"
                      }`}
                    >
                      <CheckCircle2
                        className={`w-3.5 h-3.5 ${
                          hasMinLength ? "text-emerald-600" : "text-[#CBD5E1]"
                        }`}
                      />
                      <span>12+ characters</span>
                    </div>
                    <div
                      className={`flex items-center gap-1.5 ${
                        hasUpper && hasLower ? "text-emerald-700 font-medium" : "text-[#64748B]"
                      }`}
                    >
                      <CheckCircle2
                        className={`w-3.5 h-3.5 ${
                          hasUpper && hasLower ? "text-emerald-600" : "text-[#CBD5E1]"
                        }`}
                      />
                      <span>Upper &amp; lower case</span>
                    </div>
                    <div
                      className={`flex items-center gap-1.5 ${
                        hasNumber ? "text-emerald-700 font-medium" : "text-[#64748B]"
                      }`}
                    >
                      <CheckCircle2
                        className={`w-3.5 h-3.5 ${
                          hasNumber ? "text-emerald-600" : "text-[#CBD5E1]"
                        }`}
                      />
                      <span>At least 1 number</span>
                    </div>
                    <div
                      className={`flex items-center gap-1.5 ${
                        hasSpecial ? "text-emerald-700 font-medium" : "text-[#64748B]"
                      }`}
                    >
                      <CheckCircle2
                        className={`w-3.5 h-3.5 ${
                          hasSpecial ? "text-emerald-600" : "text-[#CBD5E1]"
                        }`}
                      />
                      <span>Special symbol (!@#...)</span>
                    </div>
                  </div>
                </div>
              )}
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
              <span>FastAPI JWT &amp; Argon2id RBAC</span>
            </div>
            <span>AES-256-GCM Encrypted</span>
          </div>
        </div>
      </div>
    </div>
  );
}
