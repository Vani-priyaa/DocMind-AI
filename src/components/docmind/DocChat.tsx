"use client";

import React, { useRef, useEffect } from "react";
import { Bot, User, Sparkles, FileText, BookOpen, FileEdit } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { CitationChip } from "./CitationChip";
import { EditPreview } from "./EditPreview";
import { DocChatInput } from "./DocChatInput";

interface Source {
  page_number: number;
  heading?: string;
  snippet?: string;
}

interface ChatMessage {
  id?: number;
  role: string;
  content: string;
  sources?: Source[];
  follow_ups?: string[];
  message_type?: string;
  editPreview?: any;
}

interface DocChatProps {
  messages: ChatMessage[];
  loading: boolean;
  uploading: boolean;
  documentName: string | null;
  onSend: (message: string) => void;
  onUpload: (file: File) => void;
  onFetchSuggestions: (partial: string) => Promise<string[]>;
  onCitationClick: (pageNumber: number) => void;
  onConfirmEdit: (previewId: number) => void;
  onRejectEdit: (previewId: number) => void;
  editLoading?: boolean;
}

export function DocChat({
  messages,
  loading,
  uploading,
  documentName,
  onSend,
  onUpload,
  onFetchSuggestions,
  onCitationClick,
  onConfirmEdit,
  onRejectEdit,
  editLoading,
}: DocChatProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Parse citations from text: [Page X]
  const renderContent = (text: string) => {
    if (!text) return null;
    
    const parts = text.split(/(\[Page\s+\d+\])/g);
    return parts.map((part, i) => {
      const match = part.match(/\[Page\s+(\d+)\]/);
      if (match) {
        return (
          <CitationChip
            key={i}
            pageNumber={parseInt(match[1])}
            onClick={onCitationClick}
          />
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  const getMessageIcon = (msg: ChatMessage) => {
    if (msg.role === "user") return User;
    if (msg.message_type === "summary") return BookOpen;
    if (msg.message_type === "edit") return FileEdit;
    return Bot;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center gap-3 px-6 py-4 border-b border-border/50 glass-strong sticky top-0 z-10">
        <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center glow-primary">
          <FileText className="w-5 h-5 text-primary-foreground" />
        </div>
        <div className="flex-1">
          <h2 className="text-sm font-bold tracking-tight">
            {documentName || "DocMind AI"}
          </h2>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
              AI Assistant Ready
            </p>
          </div>
        </div>
      </header>

      {/* Messages */}
      <ScrollArea className="flex-1" ref={scrollRef}>
        <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
          {/* Welcome State */}
          {messages.length === 0 && (
            <div className="text-center py-16 space-y-5 animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto border border-primary/20 animate-pulse-glow">
                <Sparkles className="w-8 h-8 text-primary" />
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-bold">Welcome to DocMind AI</h3>
                <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                  {documentName
                    ? `Ready to analyze "${documentName}". Ask questions, request summaries, or edit the document.`
                    : "Upload a PDF document to get started. I'll extract its content and help you understand it."}
                </p>
              </div>
              {!documentName && (
                <label className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-primary text-primary-foreground font-semibold hover:opacity-90 transition-all shadow-lg cursor-pointer glow-primary">
                  <FileText className="w-5 h-5" />
                  <span>Upload PDF</span>
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) onUpload(file);
                      e.target.value = "";
                    }}
                  />
                </label>
              )}
            </div>
          )}

          {/* Chat Messages */}
          {messages.map((msg, i) => {
            const MsgIcon = getMessageIcon(msg);
            const isUser = msg.role === "user";

            return (
              <div
                key={msg.id || i}
                className={`flex gap-4 ${isUser ? "flex-row-reverse" : "flex-row"} animate-slide-up`}
                style={{ animationDelay: "50ms" }}
              >
                {/* Avatar */}
                <div
                  className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                    isUser
                      ? "bg-muted border border-border"
                      : "bg-primary/10 border border-primary/20"
                  }`}
                >
                  <MsgIcon className={`w-4 h-4 ${isUser ? "text-muted-foreground" : "text-primary"}`} />
                </div>

                {/* Content */}
                <div className={`flex flex-col gap-2 max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
                  {/* Message Bubble */}
                  <div
                    className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                      isUser
                        ? "bg-primary text-primary-foreground"
                        : "glass-card"
                    }`}
                  >
                    <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                      {renderContent(msg.content)}
                    </div>
                  </div>

                  {/* Sources (Citations) */}
                  {!isUser && msg.sources && msg.sources.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 px-1">
                      <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider mr-1">
                        Sources:
                      </span>
                      {msg.sources.map((source, si) => (
                        <CitationChip
                          key={si}
                          pageNumber={source.page_number}
                          heading={source.heading}
                          snippet={source.snippet}
                          onClick={onCitationClick}
                        />
                      ))}
                    </div>
                  )}

                  {/* Follow-up Suggestions */}
                  {!isUser && msg.follow_ups && msg.follow_ups.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-1">
                      {msg.follow_ups.map((q, qi) => (
                        <button
                          key={qi}
                          onClick={() => onSend(q)}
                          className="px-3 py-1.5 rounded-xl text-xs font-medium bg-muted/50 hover:bg-muted border border-border/50 hover:border-primary/30 text-muted-foreground hover:text-foreground transition-all"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Edit Preview */}
                  {!isUser && msg.editPreview && (
                    <EditPreview
                      description={msg.editPreview.description}
                      previewSummary={msg.editPreview.preview_summary}
                      targetPages={msg.editPreview.target_pages || []}
                      newContentPreview={msg.editPreview.new_content_preview || ""}
                      diff={msg.editPreview.diff || []}
                      onConfirm={() => onConfirmEdit(msg.editPreview.preview_id)}
                      onReject={() => onRejectEdit(msg.editPreview.preview_id)}
                      loading={editLoading}
                      status={msg.editPreview.status}
                    />
                  )}
                </div>
              </div>
            );
          })}

          {/* Loading Indicator */}
          {loading && (
            <div className="flex gap-4 animate-slide-up">
              <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center border border-primary/20">
                <Bot className="w-4 h-4 text-primary" />
              </div>
              <div className="glass-card px-4 py-3 rounded-2xl flex items-center gap-3">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
                <span className="text-xs text-muted-foreground font-medium italic">Analyzing document...</span>
              </div>
            </div>
          )}

          <div ref={bottomRef} className="h-4" />
        </div>
      </ScrollArea>

      {/* Input Section */}
      <div className="p-4 border-t border-border/30">
        <div className="max-w-3xl mx-auto">
          <DocChatInput
            onSend={onSend}
            onUpload={onUpload}
            onFetchSuggestions={onFetchSuggestions}
            loading={loading}
            uploading={uploading}
            disabled={false}
          />
        </div>
      </div>
    </div>
  );
}
