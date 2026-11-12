"use client";

import React, { useState, useRef } from "react";
import {
  X,
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Trash2,
} from "lucide-react";
import { usePrototype } from "../../context/PrototypeContext";

type UploadStep = "idle" | "selected" | "processing" | "complete";

export function UploadDocumentModal() {
  const { isUploadModalOpen, setIsUploadModalOpen, addLocalDocumentPreview } =
    usePrototype();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [step, setStep] = useState<UploadStep>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isUploadModalOpen) return null;

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setErrorMessage(null);
    const file = e.target.files?.[0];
    if (!file) return;

    const isPdf = file.type === "application/pdf" || file.name.endsWith(".pdf");
    const isDocx =
      file.name.endsWith(".docx") ||
      file.type.includes("wordprocessingml");

    if (!isPdf && !isDocx) {
      setErrorMessage("Only PDF and DOCX files are supported in this prototype.");
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setErrorMessage("File exceeds 25MB limit.");
      return;
    }

    setSelectedFile(file);
    setStep("selected");
  }

  function handleStartSimulation() {
    if (!selectedFile) return;
    setStep("processing");

    setTimeout(() => {
      setStep("complete");
    }, 1400);
  }

  function handleAddToLibrary() {
    if (!selectedFile) return;
    addLocalDocumentPreview({
      name: selectedFile.name,
      size: selectedFile.size,
      type: selectedFile.type,
    });
    handleClose();
  }

  function handleClose() {
    setSelectedFile(null);
    setStep("idle");
    setErrorMessage(null);
    setIsUploadModalOpen(false);
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-doc-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs select-none"
    >
      <div className="w-full max-w-md bg-white rounded-lg border border-[#DCE3EB] shadow-2xl overflow-hidden flex flex-col text-xs">
        {/* Header */}
        <div className="px-4 py-3 bg-[#F4F6F9] border-b border-[#DCE3EB] flex items-center justify-between">
          <div className="flex items-center gap-2 text-[#25334B] font-bold text-sm">
            <UploadCloud className="w-4 h-4 text-[#4774A9]" />
            <span id="upload-doc-modal-title">Upload Project Documentation</span>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="p-1 text-[#69778D] hover:text-[#25334B] rounded"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Prototype Warning Banner */}
        <div className="px-4 py-2 bg-[#C48A32]/10 border-b border-[#C48A32]/20 text-[11px] text-[#C48A32] flex items-start gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold">Local prototype preview only.</div>
            <div>
              Files remain inside your browser and are never uploaded to the backend or server.
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-4 space-y-3.5">
          {errorMessage && (
            <div className="p-2.5 rounded bg-[#C65B60]/10 border border-[#C65B60]/30 text-[#C65B60]">
              {errorMessage}
            </div>
          )}

          {/* Drag & Drop Area */}
          {step === "idle" && (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-[#DCE3EB] hover:border-[#4774A9] bg-[#F4F6F9]/60 hover:bg-[#E8EEF5]/40 rounded-lg p-6 text-center cursor-pointer transition-colors"
            >
              <FileText className="w-8 h-8 text-[#4774A9] mx-auto mb-2" />
              <div className="font-semibold text-[#25334B]">
                Click to browse local files
              </div>
              <div className="text-[11px] text-[#69778D] mt-1">
                Supports PDF (PyMuPDF / GLM OCR) and DOCX (python-docx)
              </div>
              <div className="text-[10px] text-[#69778D] mt-2 font-mono">
                Maximum size: 25MB
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>
          )}

          {/* Selected File Card */}
          {selectedFile && (
            <div className="border border-[#DCE3EB] rounded-lg p-3 bg-[#F4F6F9] space-y-2.5">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-8 h-8 rounded bg-[#4774A9]/10 text-[#4774A9] flex items-center justify-center shrink-0">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="font-bold text-[#25334B] truncate">
                      {selectedFile.name}
                    </div>
                    <div className="text-[10px] text-[#69778D] mt-0.5">
                      {(selectedFile.size / 1024).toFixed(1)} KB ·{" "}
                      {selectedFile.name.endsWith(".docx") ? "DOCX Document" : "PDF Document"}
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedFile(null);
                    setStep("idle");
                  }}
                  className="p-1 text-[#69778D] hover:text-[#C65B60] rounded transition-colors"
                  title="Discard selected file"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Status Stepper */}
              <div className="pt-2 border-t border-[#DCE3EB]/60">
                {step === "selected" && (
                  <div className="flex items-center justify-between text-[11px] text-[#4774A9] font-medium">
                    <span>Preview ready for simulated extraction</span>
                    <button
                      type="button"
                      onClick={handleStartSimulation}
                      className="px-2.5 py-1 rounded bg-[#4774A9] text-white text-xs font-semibold hover:bg-[#365F92] transition-colors"
                    >
                      Process Preview
                    </button>
                  </div>
                )}

                {step === "processing" && (
                  <div className="flex items-center gap-2 text-[11px] text-[#4774A9] font-medium">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Simulating PyMuPDF structural chunking...</span>
                  </div>
                )}

                {step === "complete" && (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-[11px] text-[#269878] font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Demo extraction complete (3 chunks previewed)</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-[#F4F6F9] border-t border-[#DCE3EB] flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={handleClose}
            className="px-3 py-1.5 rounded border border-[#DCE3EB] text-[#25334B] hover:bg-white font-medium transition-colors"
          >
            Cancel
          </button>
          {step === "complete" && (
            <button
              type="button"
              onClick={handleAddToLibrary}
              className="px-4 py-1.5 rounded bg-[#249E91] hover:bg-[#1f877c] text-white font-semibold transition-colors shadow-xs"
            >
              Add to Evidence Library
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
