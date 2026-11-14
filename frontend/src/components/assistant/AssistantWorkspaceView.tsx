"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Bot,
  Send,
  Sparkles,
  Database,
  ExternalLink,
  ShieldCheck,
  RefreshCw,
  User,
  MessageSquare,
  HelpCircle,
  AlertCircle,
  ChevronRight,
} from "lucide-react";
import { useLiveApp } from "../../context/LiveAppContext";
import { Button } from "../ui";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Array<{
    title: string;
    source_url?: string;
    excerpt?: string;
    confidence?: number;
  }>;
  created_at?: string;
}

export function AssistantWorkspaceView() {
  const { activeProject } = useLiveApp();
  const [conversations, setConversations] = useState<Array<Record<string, unknown>>>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "initial-welcome",
      role: "assistant",
      content:
        "Hello! I am your Project Knowledge Assistant. I answer questions grounded strictly in authorized project evidence, architectural records, decisions, and transition dossiers. What would you like to know about this project?",
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadConversations = async (projectId: string) => {
    try {
      const token = localStorage.getItem("auth_token");
      const res = await fetch(
        `http://127.0.0.1:8000/api/v1/conversations?project_id=${projectId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        setConversations(data || []);
      }
    } catch (err) {
      console.error("Failed to load conversations:", err);
    }
  };

  useEffect(() => {
    if (activeProject) {
      loadConversations(activeProject.id);
    }
  }, [activeProject]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = textToSend || inputValue;
    if (!text.trim() || !activeProject) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputValue("");
    setIsLoading(true);

    try {
      const token = localStorage.getItem("auth_token");
      let convId = activeConversationId;

      // Create conversation if not exists
      if (!convId) {
        const cRes = await fetch("http://127.0.0.1:8000/api/v1/conversations", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            project_id: activeProject.id,
            title: text.slice(0, 40),
          }),
        });
        if (cRes.ok) {
          const cData = await cRes.json();
          convId = cData.id;
          setActiveConversationId(convId);
        }
      }

      // Send message to assistant
      if (convId) {
        const aRes = await fetch(
          `http://127.0.0.1:8000/api/v1/conversations/${convId}/messages`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ message: text }),
          }
        );

        if (aRes.ok) {
          const aData = await aRes.json();
          const assistantMsg: Message = {
            id: `asst-${Date.now()}`,
            role: "assistant",
            content: aData.answer || aData.response || "No response received.",
            citations: aData.citations || aData.supporting_evidence || [],
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantMsg]);
        } else {
          throw new Error("Assistant response failed");
        }
      }
    } catch (err) {
      console.error("Assistant chat error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content:
            "I could not complete retrieval for that request. Supporting project evidence may be unavailable or the local inference engine may be initializing.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-[#DCE3EB]">
        <Bot className="w-12 h-12 text-[#69778D] mb-3 mx-auto" />
        <div className="font-bold text-sm text-[#25334B]">No Active Project Selected</div>
        <p className="text-xs text-[#69778D] mt-1">Select a project workspace to open the AI Assistant.</p>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-6rem)] flex flex-col gap-4">
      {/* Header */}
      <div className="bg-white rounded-xl border border-[#DCE3EB] px-5 py-3.5 shadow-2xs flex items-center justify-between shrink-0">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-[#4774A9] uppercase tracking-wider">
            <span>AI Project Assistant</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#249E91]" />
            <span className="text-[#69778D] font-normal">{activeProject.name}</span>
          </div>
          <h1 className="text-lg font-bold text-[#25334B] tracking-tight">
            Evidence-Backed Knowledge Assistant
          </h1>
        </div>

        <div className="flex items-center gap-2 text-xs text-[#69778D] font-mono">
          <ShieldCheck className="w-4 h-4 text-[#249E91]" />
          <span>Strict Pre-Retrieval ACLs</span>
        </div>
      </div>

      {/* Main Chat Container */}
      <div className="flex-1 bg-white rounded-xl border border-[#DCE3EB] shadow-2xs flex flex-col overflow-hidden">
        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex gap-3 text-xs leading-relaxed ${
                m.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {m.role === "assistant" && (
                <div className="w-7 h-7 rounded-lg bg-[#E8EEF5] text-[#4774A9] flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-2xl p-4 rounded-xl ${
                  m.role === "user"
                    ? "bg-[#4774A9] text-white"
                    : "bg-[#F6F8FC] border border-[#DCE3EB] text-[#25334B]"
                }`}
              >
                <div className="whitespace-pre-wrap">{m.content}</div>

                {/* Evidence Citations */}
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-[#DCE3EB] space-y-2">
                    <div className="text-[10px] font-bold text-[#4774A9] uppercase tracking-wider flex items-center gap-1.5">
                      <Database className="w-3.5 h-3.5" />
                      <span>Supporting Evidence Citations</span>
                    </div>
                    {m.citations.map((c, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded bg-white border border-[#DCE3EB] text-[11px]"
                      >
                        <div className="font-bold text-[#25334B]">{c.title}</div>
                        {c.excerpt && (
                          <div className="text-[#69778D] mt-0.5 font-mono text-[10px]">
                            {c.excerpt}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {m.role === "user" && (
                <div className="w-7 h-7 rounded-lg bg-[#25334B] text-white flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-3 text-xs text-[#69778D] items-center">
              <div className="w-7 h-7 rounded-lg bg-[#E8EEF5] text-[#4774A9] flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 animate-pulse" />
              </div>
              <span className="italic">Searching project evidence and reasoning...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Queries */}
        <div className="p-3 bg-[#F4F6F9] border-t border-[#DCE3EB] flex items-center gap-2 overflow-x-auto text-xs shrink-0">
          <span className="text-[10px] uppercase font-bold text-[#69778D] shrink-0">Suggested:</span>
          {[
            "What are the major architectural decisions in this project?",
            "What critical blockers or risks are currently unmitigated?",
            "Who owns the core platform services?",
          ].map((prompt, i) => (
            <button
              key={i}
              onClick={() => handleSendMessage(prompt)}
              className="px-3 py-1 rounded-full bg-white border border-[#DCE3EB] text-[#25334B] hover:border-[#4774A9] text-xs shrink-0 transition-colors"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-3 bg-white border-t border-[#DCE3EB] flex items-center gap-3 shrink-0">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            placeholder={`Ask a question about ${activeProject.name}...`}
            className="flex-1 text-xs text-[#25334B] placeholder:text-[#69778D] focus:outline-none px-2 py-1"
          />
          <Button
            variant="primary"
            icon={Send}
            onClick={() => handleSendMessage()}
            disabled={isLoading || !inputValue.trim()}
          >
            Ask Assistant
          </Button>
        </div>
      </div>
    </div>
  );
}
