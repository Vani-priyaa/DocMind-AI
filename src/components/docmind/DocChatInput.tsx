"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { Send, Upload, Loader2, Sparkles, FileEdit, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";

interface DocChatInputProps {
  onSend: (message: string) => void;
  onUpload: (file: File) => void;
  onFetchSuggestions: (partial: string) => Promise<string[]>;
  loading?: boolean;
  uploading?: boolean;
  disabled?: boolean;
}

export function DocChatInput({
  onSend,
  onUpload,
  onFetchSuggestions,
  loading,
  uploading,
  disabled,
}: DocChatInputProps) {
  const [input, setInput] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestion, setSelectedSuggestion] = useState(-1);
  const [mode, setMode] = useState<"chat" | "edit" | "summarize">("chat");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 160) + "px";
    }
  }, [input]);

  // Fetch suggestions with debounce
  const fetchSuggestions = useCallback(
    async (text: string) => {
      if (text.length < 3) {
        setSuggestions([]);
        setShowSuggestions(false);
        return;
      }

      try {
        const results = await onFetchSuggestions(text);
        if (results.length > 0) {
          setSuggestions(results);
          setShowSuggestions(true);
          setSelectedSuggestion(-1);
        } else {
          setShowSuggestions(false);
        }
      } catch {
        setShowSuggestions(false);
      }
    },
    [onFetchSuggestions]
  );

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInput(value);

    // Debounced suggestion fetch
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(value), 300);
  };

  const handleSend = () => {
    const text = input.trim();
    if (!text || loading) return;

    let finalMessage = text;
    if (mode === "edit") {
      finalMessage = `[EDIT] ${text}`;
    } else if (mode === "summarize") {
      finalMessage = `[SUMMARIZE] ${text}`;
    }

    onSend(finalMessage);
    setInput("");
    setShowSuggestions(false);
    setSuggestions([]);
  };

  const handleSelectSuggestion = (suggestion: string) => {
    setInput(suggestion);
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showSuggestions && suggestions.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedSuggestion((prev) => (prev + 1) % suggestions.length);
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedSuggestion((prev) => (prev - 1 + suggestions.length) % suggestions.length);
        return;
      }
      if (e.key === "Tab" || (e.key === "Enter" && selectedSuggestion >= 0)) {
        e.preventDefault();
        if (selectedSuggestion >= 0) {
          handleSelectSuggestion(suggestions[selectedSuggestion]);
        }
        return;
      }
      if (e.key === "Escape") {
        setShowSuggestions(false);
        return;
      }
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === "application/pdf") {
      onUpload(file);
    }
    e.target.value = "";
  };

  const modeConfig = {
    chat: { icon: Sparkles, label: "Ask", placeholder: "Ask anything about your document..." },
    edit: { icon: FileEdit, label: "Edit", placeholder: "Describe the change you want to make..." },
    summarize: { icon: BookOpen, label: "Summary", placeholder: "e.g., Summarize section 3 in bullet points..." },
  };

  const currentMode = modeConfig[mode];

  return (
    <div className="relative">
      {/* Autocomplete Suggestions Dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <div className="autocomplete-dropdown glass-strong shadow-2xl">
          <div className="p-2">
            <p className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider px-3 py-1">
              Suggested Questions
            </p>
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => handleSelectSuggestion(s)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all duration-150
                  ${i === selectedSuggestion
                    ? "bg-primary/10 text-primary"
                    : "text-foreground/80 hover:bg-muted/60"
                  }`}
              >
                <span className="flex items-center gap-2">
                  <Sparkles className="w-3.5 h-3.5 text-primary/60 shrink-0" />
                  {s}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="glass-strong rounded-2xl shadow-xl">
        {/* Mode Selector */}
        <div className="flex items-center gap-1 px-3 pt-3 pb-1">
          {(Object.keys(modeConfig) as Array<keyof typeof modeConfig>).map((m) => {
            const MIcon = modeConfig[m].icon;
            return (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all
                  ${mode === m
                    ? "bg-primary/10 text-primary border border-primary/20"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  }`}
              >
                <MIcon className="w-3.5 h-3.5" />
                {modeConfig[m].label}
              </button>
            );
          })}
        </div>

        {/* Text Input */}
        <div className="flex items-end gap-2 p-3">
          {/* Upload Button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="shrink-0 p-2.5 rounded-xl hover:bg-muted/50 transition-all text-muted-foreground hover:text-foreground"
          >
            {uploading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Upload className="w-5 h-5" />
            )}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf"
            onChange={handleFileChange}
          />

          {/* Textarea */}
          <textarea
            ref={inputRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onFocus={() => {
              if (input.length >= 3 && suggestions.length > 0) {
                setShowSuggestions(true);
              }
            }}
            onBlur={() => {
              // Delay hiding to allow click on suggestion
              setTimeout(() => setShowSuggestions(false), 200);
            }}
            placeholder={currentMode.placeholder}
            disabled={disabled}
            className="w-full bg-transparent border-none focus:ring-0 focus:outline-none resize-none py-2 text-sm leading-relaxed max-h-40 placeholder:text-muted-foreground/50"
            rows={1}
          />

          {/* Send Button */}
          <Button
            onClick={handleSend}
            disabled={loading || !input.trim() || disabled}
            size="icon"
            className="shrink-0 rounded-xl h-11 w-11 glow-primary"
          >
            {loading ? (
              <Loader2 className="w-4.5 h-4.5 animate-spin" />
            ) : (
              <Send className="w-4.5 h-4.5" />
            )}
          </Button>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-center gap-4 px-3 pb-2">
          <p className="text-[9px] text-muted-foreground/50 uppercase tracking-[0.2em] font-bold">
            DocMind AI
          </p>
          <div className="w-0.5 h-0.5 rounded-full bg-muted-foreground/20" />
          <p className="text-[9px] text-muted-foreground/50 uppercase tracking-[0.2em] font-bold">
            Gemini Powered
          </p>
        </div>
      </div>
    </div>
  );
}
