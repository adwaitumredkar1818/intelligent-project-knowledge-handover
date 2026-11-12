"use client";

import React from "react";
import { CheckCircle2, Info, AlertTriangle, AlertCircle, X } from "lucide-react";
import { usePrototype } from "../../context/PrototypeContext";

export function ToastContainer() {
  const { toasts, dismissToast } = usePrototype();

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      aria-atomic="true"
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none select-none"
    >
      {toasts.map((toast) => {
        const icon =
          toast.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 text-[#269878] shrink-0" />
          ) : toast.type === "warning" ? (
            <AlertTriangle className="w-4 h-4 text-[#C48A32] shrink-0" />
          ) : toast.type === "error" ? (
            <AlertCircle className="w-4 h-4 text-[#C65B60] shrink-0" />
          ) : (
            <Info className="w-4 h-4 text-[#4774A9] shrink-0" />
          );

        const borderColor =
          toast.type === "success"
            ? "border-[#269878]/30"
            : toast.type === "warning"
            ? "border-[#C48A32]/30"
            : toast.type === "error"
            ? "border-[#C65B60]/30"
            : "border-[#4774A9]/30";

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto bg-white border ${borderColor} rounded-lg shadow-lg p-3 text-xs flex items-start gap-2.5 transition-all transform duration-200 animate-in fade-in slide-in-from-bottom-2`}
          >
            <div className="mt-0.5">{icon}</div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-[#25334B]">{toast.title}</div>
              <div className="text-[11px] text-[#69778D] mt-0.5 leading-snug">
                {toast.message}
              </div>
            </div>
            <button
              type="button"
              onClick={() => dismissToast(toast.id)}
              className="text-[#69778D] hover:text-[#25334B] p-0.5 rounded shrink-0"
              aria-label="Dismiss toast"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
