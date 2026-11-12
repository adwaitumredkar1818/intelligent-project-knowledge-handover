"use client";

import React from "react";
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";

export function ToastContainer() {
  const { toasts, dismissToast } = useLiveApp();

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"
      aria-live="polite"
    >
      {toasts.map((toast) => {
        const bgColors = {
          success: "bg-emerald-50 border-emerald-200 text-emerald-900",
          error: "bg-rose-50 border-rose-200 text-rose-900",
          warning: "bg-amber-50 border-amber-200 text-amber-900",
          info: "bg-sky-50 border-sky-200 text-sky-900",
        };

        const icons = {
          success: <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />,
          error: <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />,
          warning: <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />,
          info: <Info className="w-4 h-4 text-sky-600 shrink-0" />,
        };

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto p-3.5 rounded-lg border shadow-md flex items-start gap-2.5 transition-all text-xs ${bgColors[toast.type]}`}
          >
            {icons[toast.type]}
            <div className="flex-1 min-w-0">
              <div className="font-semibold">{toast.title}</div>
              <div className="text-[11px] opacity-90 mt-0.5 leading-snug break-words">
                {toast.message}
              </div>
            </div>
            <button
              type="button"
              onClick={() => dismissToast(toast.id)}
              className="text-gray-400 hover:text-gray-600 p-0.5 rounded"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
