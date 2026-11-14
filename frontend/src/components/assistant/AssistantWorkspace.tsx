"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Bot,
  Send,
  Plus,
  Trash2,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  RefreshCw,
  AlertCircle,
  MessageSquare,
} from "lucide-react";
import { api } from "../../lib/api";
import { useLiveApp } from "../../context/LiveAppContext";

interface ConversationItem {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface MessageItem {
  id: string;
  role: string;
  content: string;
  citations?: Array<{
    source_id: string;
    source_title: string;
    snippet: string;
    confidence: number;
  }>;
  created_at: string;
}

export function AssistantWorkspace() {
  const { activeProject } = useLiveApp();
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<ConversationItem | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputContent, setInputContent] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [sending, setSending] = useState<boolean>(false);

  const loadConversations = useCallback(async () => {
    if (!activeProject?.id) return;
    setLoading(true);
    try {
      const convs = await api.assistant.listConversations(activeProject.id).catch(() => []);
      setConversations(convs || []);
      if (convs && convs.length > 0 && !selectedConversation && convs[0]) {
        selectConversation(convs[0]);
      }
    } finally {
      setLoading(false);
    }
  }, [activeProject?.id]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const selectConversation = async (conv: ConversationItem) => {
    setSelectedConversation(conv);
    if (!activeProject?.id) return;
    try {
      const msgs = await api.assistant.getMessages(activeProject.id, conv.id).catch(() => []);
      setMessages(msgs || []);
    } catch {
      // Graceful fallback
    }
  };

  const handleCreateConversation = async () => {
    if (!activeProject?.id) return;
    try {
      const newConv = await api.assistant.createConversation(activeProject.id, "Project Handover Q&A");
      await loadConversations();
      if (newConv?.id) {
        selectConversation({
          id: newConv.id,
          title: newConv.title,
          created_at: newConv.created_at,
          updated_at: newConv.created_at,
        });
      }
    } catch {
      // Graceful fallback
    }
  };

  const handleDeleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!activeProject?.id) return;
    try {
      await api.assistant.deleteConversation(activeProject.id, convId);
      if (selectedConversation?.id === convId) {
        setSelectedConversation(null);
        setMessages([]);
      }
      await loadConversations();
    } catch {
      // Graceful fallback
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProject?.id || !selectedConversation || !inputContent.trim()) return;
    const text = inputContent.trim();
    setInputContent("");
    setSending(true);

    // Optimistic user message append
    const tempUserMsg: MessageItem = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const assistantReply = await api.assistant.sendMessage(activeProject.id, selectedConversation.id, text);
      setMessages((prev) => [...prev, assistantReply]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: "Sorry, I encountered an issue retrieving grounded knowledge for this question. Please ensure local Ollama (Qwen3 8B) is running.",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Top Banner */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Bot className="w-7 h-7 text-indigo-400" />
            Project Knowledge Assistant
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Permission-filtered, hybrid-RAG conversational AI with strict source citations and zero hallucination boundaries.
          </p>
        </div>
        <button
          onClick={handleCreateConversation}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          New Investigation
        </button>
      </div>

      {/* Main Split Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-[500px]">
        {/* Left Column: Conversations List */}
        <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-xl flex flex-col overflow-hidden">
          <div className="p-3.5 border-b border-slate-800 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Conversations ({conversations.length})
            </span>
            <button onClick={loadConversations} className="text-slate-500 hover:text-slate-300">
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60">
            {conversations.length === 0 ? (
              <div className="p-6 text-center text-slate-500 text-xs">
                No conversations yet. Start a new investigation above.
              </div>
            ) : (
              conversations.map((c) => {
                const isSelected = selectedConversation?.id === c.id;
                return (
                  <div
                    key={c.id}
                    onClick={() => selectConversation(c)}
                    className={`p-3 cursor-pointer flex items-center justify-between group transition-colors ${
                      isSelected ? "bg-slate-800/80 border-l-4 border-l-indigo-500" : "hover:bg-slate-800/40"
                    }`}
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      <MessageSquare className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                      <span className="text-xs text-slate-200 font-medium truncate">{c.title}</span>
                    </div>
                    <button
                      onClick={(e) => handleDeleteConversation(c.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-rose-400 transition-opacity"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Chat Window */}
        <div className="lg:col-span-9 bg-slate-900 border border-slate-800 rounded-xl flex flex-col overflow-hidden">
          {selectedConversation ? (
            <>
              {/* Messages Container */}
              <div className="flex-1 p-6 overflow-y-auto space-y-4">
                {messages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center text-slate-500">
                    <Sparkles className="w-8 h-8 text-indigo-400 mb-2" />
                    <p className="text-sm font-medium text-slate-300">Ask anything about this project&apos;s reconstructed knowledge.</p>
                    <p className="text-xs text-slate-500 mt-1 max-w-sm">
                      Questions regarding architecture, past decisions, open blockers, or component ownership will be answered with grounded citations.
                    </p>
                  </div>
                ) : (
                  messages.map((m) => {
                    const isAssistant = m.role === "assistant";
                    return (
                      <div
                        key={m.id}
                        className={`flex gap-3 ${isAssistant ? "items-start" : "items-start flex-row-reverse"}`}
                      >
                        <div
                          className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                            isAssistant ? "bg-indigo-600 text-white" : "bg-slate-700 text-slate-200"
                          }`}
                        >
                          {isAssistant ? <Bot className="w-4 h-4" /> : "U"}
                        </div>
                        <div
                          className={`max-w-[80%] rounded-xl p-4 text-xs leading-relaxed ${
                            isAssistant
                              ? "bg-slate-950 border border-slate-800 text-slate-200"
                              : "bg-indigo-600/90 text-white"
                          }`}
                        >
                          <div className="whitespace-pre-wrap">{m.content}</div>

                          {/* Evidence Citations */}
                          {m.citations && m.citations.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-1.5">
                              <span className="text-[10px] font-semibold uppercase tracking-wider text-indigo-400 flex items-center gap-1">
                                <ShieldCheck className="w-3 h-3" /> Grounded Source Citations
                              </span>
                              {m.citations.map((c, idx) => (
                                <div key={idx} className="bg-slate-900 p-2 rounded text-[11px] text-slate-400 border border-slate-800">
                                  <div className="font-semibold text-slate-300 flex items-center justify-between">
                                    <span>{c.source_title}</span>
                                    <span className="text-[10px] text-emerald-400">{(c.confidence * 100).toFixed(0)}% Match</span>
                                  </div>
                                  <p className="font-serif italic mt-0.5 text-slate-400">&quot;{c.snippet}&quot;</p>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
                {sending && (
                  <div className="flex items-center gap-2 text-xs text-indigo-400 italic">
                    <Sparkles className="w-3.5 h-3.5 animate-spin" />
                    Assistant is querying hybrid RAG and synthesizing answer...
                  </div>
                )}
              </div>

              {/* Chat Input Bar */}
              <form onSubmit={handleSendMessage} className="p-3 bg-slate-950 border-t border-slate-800 flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Ask about architecture, technical decisions, blockers, ownership..."
                  value={inputContent}
                  onChange={(e) => setInputContent(e.target.value)}
                  className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
                <button
                  type="submit"
                  disabled={sending || !inputContent.trim()}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
                >
                  <Send className="w-3.5 h-3.5" />
                  Ask
                </button>
              </form>
            </>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-slate-500">
              <Bot className="w-10 h-10 text-slate-700 mb-2" />
              <p className="text-sm font-medium text-slate-400">Select or start a conversation</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
