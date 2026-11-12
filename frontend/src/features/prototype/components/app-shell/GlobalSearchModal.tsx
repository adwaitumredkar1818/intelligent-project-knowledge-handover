"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  X,
  FolderGit2,
  Users,
  Database,
  ArrowRight,
} from "lucide-react";
import { usePrototype } from "../../context/PrototypeContext";

export function GlobalSearchModal() {
  const router = useRouter();
  const {
    isGlobalSearchOpen,
    setIsGlobalSearchOpen,
    projects,
    members,
    evidenceList,
    setSelectedProjectById,
    setSelectedEvidenceId,
  } = usePrototype();

  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input on open
  useEffect(() => {
    if (isGlobalSearchOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isGlobalSearchOpen]);

  // Global keydown shortcut "/" or "Ctrl+K"
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (
        (e.key === "/" || (e.key === "k" && (e.metaKey || e.ctrlKey))) &&
        !["INPUT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName)
      ) {
        e.preventDefault();
        setIsGlobalSearchOpen(true);
      }
      if (e.key === "Escape" && isGlobalSearchOpen) {
        setQuery("");
        setIsGlobalSearchOpen(false);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isGlobalSearchOpen, setIsGlobalSearchOpen]);

  if (!isGlobalSearchOpen) return null;

  const cleanQ = query.trim().toLowerCase();

  const matchingProjects = cleanQ
    ? projects.filter(
        (p) =>
          p.name.toLowerCase().includes(cleanQ) ||
          p.description.toLowerCase().includes(cleanQ)
      )
    : projects.slice(0, 2);

  const matchingMembers = cleanQ
    ? members.filter(
        (m) =>
          m.name.toLowerCase().includes(cleanQ) ||
          m.role.toLowerCase().includes(cleanQ) ||
          m.responsibilities.toLowerCase().includes(cleanQ)
      )
    : members.slice(0, 3);

  const matchingEvidence = cleanQ
    ? evidenceList.filter(
        (e) =>
          e.name.toLowerCase().includes(cleanQ) ||
          e.author.toLowerCase().includes(cleanQ) ||
          e.source.toLowerCase().includes(cleanQ) ||
          e.extractedContent.excerpt.toLowerCase().includes(cleanQ)
      )
    : evidenceList.slice(0, 4);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Global search"
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/50 backdrop-blur-xs select-none"
    >
      <div className="w-full max-w-xl bg-white rounded-lg border border-[#DCE3EB] shadow-2xl overflow-hidden flex flex-col text-xs">
        {/* Search Input Bar */}
        <div className="flex items-center px-3.5 py-3 border-b border-[#DCE3EB] bg-[#F4F6F9]">
          <Search className="w-4 h-4 text-[#69778D] shrink-0 mr-2.5" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search sample projects, members, PRs, documents, and Jira tasks..."
            className="flex-1 bg-transparent text-[#25334B] placeholder-[#69778D] text-sm focus:outline-none"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="p-1 text-[#69778D] hover:text-[#25334B] mr-1"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
          <kbd className="px-1.5 py-0.5 text-[10px] font-mono bg-white border border-[#DCE3EB] rounded text-[#69778D]">
            ESC
          </kbd>
        </div>

        {/* Results Body */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-3">
          {/* Projects Group */}
          {matchingProjects.length > 0 && (
            <div>
              <div className="px-2 py-1 text-[10px] font-bold text-[#69778D] uppercase tracking-wider flex items-center gap-1.5">
                <FolderGit2 className="w-3 h-3 text-[#4774A9]" />
                Projects
              </div>
              <div className="space-y-0.5">
                {matchingProjects.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => {
                      setSelectedProjectById(p.id);
                      setIsGlobalSearchOpen(false);
                      router.push("/prototype/overview");
                    }}
                    className="w-full text-left px-2.5 py-2 rounded hover:bg-[#F4F6F9] flex items-center justify-between transition-colors group"
                  >
                    <div>
                      <div className="font-semibold text-[#25334B] group-hover:text-[#4774A9]">
                        {p.name}
                      </div>
                      <div className="text-[11px] text-[#69778D] truncate max-w-md">
                        {p.description}
                      </div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-[#69778D] opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Members Group */}
          {matchingMembers.length > 0 && (
            <div>
              <div className="px-2 py-1 text-[10px] font-bold text-[#69778D] uppercase tracking-wider flex items-center gap-1.5">
                <Users className="w-3 h-3 text-[#249E91]" />
                Team Members
              </div>
              <div className="space-y-0.5">
                {matchingMembers.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => {
                      setIsGlobalSearchOpen(false);
                      router.push("/prototype/team");
                    }}
                    className="w-full text-left px-2.5 py-2 rounded hover:bg-[#F4F6F9] flex items-center justify-between transition-colors group"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="w-6 h-6 rounded-full bg-[#304563] text-white flex items-center justify-center font-bold text-[10px] shrink-0">
                        {m.avatarInitials}
                      </div>
                      <div className="min-w-0">
                        <div className="font-semibold text-[#25334B] group-hover:text-[#4774A9]">
                          {m.name}
                        </div>
                        <div className="text-[11px] text-[#69778D] truncate max-w-sm">
                          {m.role} · {m.responsibilities}
                        </div>
                      </div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-[#69778D] opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Evidence Group */}
          {matchingEvidence.length > 0 && (
            <div>
              <div className="px-2 py-1 text-[10px] font-bold text-[#69778D] uppercase tracking-wider flex items-center gap-1.5">
                <Database className="w-3 h-3 text-[#4774A9]" />
                Evidence Library Records
              </div>
              <div className="space-y-0.5">
                {matchingEvidence.map((e) => (
                  <button
                    key={e.id}
                    type="button"
                    onClick={() => {
                      setSelectedEvidenceId(e.id);
                      setIsGlobalSearchOpen(false);
                      router.push("/prototype/evidence");
                    }}
                    className="w-full text-left px-2.5 py-2 rounded hover:bg-[#F4F6F9] flex items-center justify-between transition-colors group"
                  >
                    <div className="min-w-0">
                      <div className="font-semibold text-[#25334B] group-hover:text-[#4774A9] truncate">
                        {e.name}
                      </div>
                      <div className="text-[11px] text-[#69778D] flex items-center gap-2 mt-0.5">
                        <span className="uppercase text-[9px] font-mono font-bold bg-[#E8EEF5] text-[#25334B] px-1 py-0.2 rounded">
                          {e.source}
                        </span>
                        <span>{e.author}</span>
                        <span>·</span>
                        <span className="truncate max-w-xs">{e.extractedContent.excerpt}</span>
                      </div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-[#69778D] opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {cleanQ &&
            matchingProjects.length === 0 &&
            matchingMembers.length === 0 &&
            matchingEvidence.length === 0 && (
              <div className="p-8 text-center text-[#69778D]">
                <p className="font-medium">No sample records matching &quot;{query}&quot;</p>
                <p className="text-[11px] mt-1">Try searching for &quot;token&quot;, &quot;Alex&quot;, &quot;auth&quot;, or &quot;Jira&quot;.</p>
              </div>
            )}
        </div>

        {/* Footer info */}
        <div className="p-2.5 bg-[#F4F6F9] border-t border-[#DCE3EB] text-[10px] text-[#69778D] flex items-center justify-between">
          <span>Search operates locally on sample fixtures</span>
          <span>Click any record to navigate directly</span>
        </div>
      </div>
    </div>
  );
}
