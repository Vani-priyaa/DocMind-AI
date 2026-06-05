"use client";

import React from "react";
import { Clock, RotateCcw, Check, FileText } from "lucide-react";

interface Version {
  id: number;
  version_number: number;
  change_description: string | null;
  created_at: string | null;
}

interface VersionTimelineProps {
  versions: Version[];
  currentVersionId: number | null;
  onSelectVersion: (versionId: number) => void;
  onRollback: (versionId: number) => void;
}

export function VersionTimeline({ versions, currentVersionId, onSelectVersion, onRollback }: VersionTimelineProps) {
  if (!versions.length) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <Clock className="w-8 h-8 mb-2 opacity-30" />
        <p className="text-xs">No versions yet</p>
      </div>
    );
  }

  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="space-y-1">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-3 py-2">
        Version History
      </h3>
      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-6 top-4 bottom-4 w-px bg-border" />

        {versions.map((v, i) => {
          const isActive = v.id === currentVersionId;
          const isLatest = i === 0;

          return (
            <div
              key={v.id}
              className={`relative flex items-start gap-3 px-3 py-2.5 rounded-xl mx-1 cursor-pointer transition-all duration-200
                ${isActive ? "bg-primary/10 border border-primary/20" : "hover:bg-muted/50"}`}
              onClick={() => onSelectVersion(v.id)}
            >
              {/* Timeline dot */}
              <div className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center shrink-0 border-2 transition-colors
                ${isActive
                  ? "bg-primary border-primary text-primary-foreground"
                  : isLatest
                  ? "bg-green-500/20 border-green-500/50 text-green-600 dark:text-green-400"
                  : "bg-muted border-border text-muted-foreground"
                }`}
              >
                {isActive ? (
                  <Check className="w-3 h-3" />
                ) : (
                  <FileText className="w-3 h-3" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-semibold ${isActive ? "text-primary" : ""}`}>
                    v{v.version_number}
                  </span>
                  {isLatest && (
                    <span className="px-1.5 py-0.5 rounded-md bg-green-500/15 text-green-600 dark:text-green-400 text-[10px] font-bold uppercase">
                      Latest
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5 truncate">
                  {v.change_description || "Original upload"}
                </p>
                {v.created_at && (
                  <p className="text-[10px] text-muted-foreground/60 mt-1">
                    {formatTime(v.created_at)}
                  </p>
                )}
              </div>

              {/* Rollback button (only for non-latest versions) */}
              {!isLatest && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onRollback(v.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-all"
                  title="Rollback to this version"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
