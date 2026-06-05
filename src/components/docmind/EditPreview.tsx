"use client";

import React from "react";
import { Check, X, FileEdit, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface DiffLine {
  type: "added" | "removed" | "unchanged" | "header";
  content: string;
}

interface EditPreviewProps {
  description: string;
  previewSummary: string;
  targetPages: number[];
  newContentPreview: string;
  diff: DiffLine[];
  onConfirm: () => void;
  onReject: () => void;
  loading?: boolean;
  status?: string;
}

export function EditPreview({
  description,
  previewSummary,
  targetPages,
  newContentPreview,
  diff,
  onConfirm,
  onReject,
  loading,
  status = "pending_confirmation",
}: EditPreviewProps) {
  return (
    <div className="rounded-2xl border border-primary/20 bg-primary/5 overflow-hidden animate-slide-up">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-3 bg-primary/10 border-b border-primary/15">
        <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
          <FileEdit className="w-4 h-4 text-primary" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold">Edit Preview</p>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
        {targetPages.length > 0 && (
          <div className="flex gap-1">
            {targetPages.map((p) => (
              <span key={p} className="px-2 py-0.5 rounded-md bg-primary/15 text-primary text-xs font-medium">
                Page {p}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Summary */}
      {previewSummary && (
        <div className="px-5 py-3 border-b border-border/50">
          <p className="text-sm text-muted-foreground flex items-start gap-2">
            <ArrowRight className="w-4 h-4 mt-0.5 text-primary shrink-0" />
            {previewSummary}
          </p>
        </div>
      )}

      {/* Diff View */}
      {diff.length > 0 && (
        <div className="px-5 py-3 border-b border-border/50">
          <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">Changes</p>
          <div className="rounded-lg bg-background/50 border border-border/50 overflow-hidden font-mono text-xs">
            {diff.slice(0, 20).map((line, i) => (
              <div
                key={i}
                className={`px-3 py-1 ${
                  line.type === "added"
                    ? "bg-green-500/10 text-green-700 dark:text-green-400"
                    : line.type === "removed"
                    ? "bg-red-500/10 text-red-700 dark:text-red-400 line-through"
                    : line.type === "header"
                    ? "bg-muted/50 text-muted-foreground font-semibold"
                    : "text-muted-foreground"
                }`}
              >
                <span className="opacity-50 mr-2">
                  {line.type === "added" ? "+" : line.type === "removed" ? "−" : " "}
                </span>
                {line.content}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* New Content Preview */}
      {!diff.length && newContentPreview && (
        <div className="px-5 py-3 border-b border-border/50">
          <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">Generated Content</p>
          <div className="rounded-lg bg-green-500/5 border border-green-500/15 p-3">
            <p className="text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap">
              {newContentPreview}
            </p>
          </div>
        </div>
      )}

      {/* Actions */}
      {status === "pending_confirmation" || !status ? (
        <div className="flex items-center gap-3 px-5 py-3">
          <Button
            onClick={onConfirm}
            disabled={loading}
            size="sm"
            className="rounded-xl gap-2 glow-primary"
          >
            <Check className="w-4 h-4" />
            {loading ? "Applying..." : "Apply Changes"}
          </Button>
          <Button
            onClick={onReject}
            disabled={loading}
            variant="ghost"
            size="sm"
            className="rounded-xl gap-2 text-muted-foreground hover:text-destructive"
          >
            <X className="w-4 h-4" />
            Discard
          </Button>
        </div>
      ) : (
        <div className="flex items-center gap-3 px-5 py-3 border-t border-border/10 bg-muted/5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          {status === "applied" ? (
            <span className="text-green-500 dark:text-green-400 flex items-center gap-1.5 font-sans normal-case">
              <Check className="w-4 h-4" /> Applied
            </span>
          ) : (
            <span className="text-muted-foreground flex items-center gap-1.5 font-sans normal-case">
              <X className="w-4 h-4" /> Discarded
            </span>
          )}
        </div>
      )}
    </div>
  );
}
