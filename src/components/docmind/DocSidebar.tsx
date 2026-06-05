"use client";

import React, { useCallback } from "react";
import { FileText, Plus, Upload, Loader2, Trash2, ChevronDown, LogOut } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { VersionTimeline } from "./VersionTimeline";
import { ThemeToggle } from "./ThemeToggle";

interface Document {
  id: number;
  filename: string;
  page_count: number;
  created_at: string | null;
  latest_version_number: number;
  has_summary: boolean;
}

interface Version {
  id: number;
  version_number: number;
  change_description: string | null;
  created_at: string | null;
}

interface DocSidebarProps {
  documents: Document[];
  activeDocId: number | null;
  versions: Version[];
  currentVersionId: number | null;
  onSelectDocument: (docId: number) => void;
  onSelectVersion: (versionId: number) => void;
  onRollbackVersion: (versionId: number) => void;
  onUploadPdf: (file: File) => void;
  onDeleteDocument: (docId: number) => void;
  onLogout: () => void;
  uploading: boolean;
}

export function DocSidebar({
  documents,
  activeDocId,
  versions,
  currentVersionId,
  onSelectDocument,
  onSelectVersion,
  onRollbackVersion,
  onUploadPdf,
  onDeleteDocument,
  onLogout,
  uploading,
}: DocSidebarProps) {
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file && file.type === "application/pdf") {
        onUploadPdf(file);
      }
    },
    [onUploadPdf]
  );

  return (
    <div className="flex flex-col h-full bg-sidebar border-r border-sidebar-border">
      {/* Logo Header */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-sidebar-border">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center glow-primary">
            <FileText className="w-4.5 h-4.5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight">DocMind <span className="gradient-text">AI</span></h1>
            <p className="text-[9px] text-muted-foreground font-medium uppercase tracking-wider">PDF Assistant</p>
          </div>
        </div>
        <ThemeToggle />
      </div>

      {/* Upload Zone */}
      <div
        className="mx-3 mt-3"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <label className="flex items-center justify-center gap-2 w-full px-4 py-3 rounded-xl border-2 border-dashed border-primary/30 bg-primary/5 hover:bg-primary/10 hover:border-primary/50 cursor-pointer transition-all duration-200 group">
          {uploading ? (
            <Loader2 className="w-4 h-4 animate-spin text-primary" />
          ) : (
            <Upload className="w-4 h-4 text-primary/60 group-hover:text-primary transition-colors" />
          )}
          <span className="text-xs font-semibold text-primary/70 group-hover:text-primary transition-colors">
            {uploading ? "Uploading..." : "Upload PDF"}
          </span>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onUploadPdf(file);
              e.target.value = "";
            }}
          />
        </label>
      </div>

      {/* Documents List */}
      <div className="px-3 pt-4 pb-1">
        <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider px-1">
          Documents ({documents.length})
        </h3>
      </div>

      <ScrollArea className="flex-1 px-2">
        <div className="space-y-1 py-1">
          {documents.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-20" />
              <p className="text-xs">No documents yet</p>
              <p className="text-[10px] opacity-60">Upload a PDF to begin</p>
            </div>
          )}

          {documents.map((doc) => {
            const isActive = doc.id === activeDocId;
            return (
              <div
                key={doc.id}
                className={`group flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-200 ${
                  isActive
                    ? "bg-primary/10 border border-primary/20"
                    : "hover:bg-muted/50"
                }`}
                onClick={() => onSelectDocument(doc.id)}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                  isActive ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
                }`}>
                  <FileText className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-xs font-semibold truncate ${isActive ? "text-primary" : ""}`}>
                    {doc.filename}
                  </p>
                  <p className="text-[10px] text-muted-foreground">
                    {doc.page_count} pages · v{doc.latest_version_number}
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteDocument(doc.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-all"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })}
        </div>

        {/* Version Timeline */}
        {activeDocId && versions.length > 0 && (
          <div className="mt-4 mb-2 border-t border-border/50 pt-3">
            <VersionTimeline
              versions={versions}
              currentVersionId={currentVersionId}
              onSelectVersion={onSelectVersion}
              onRollback={onRollbackVersion}
            />
          </div>
        )}
      </ScrollArea>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-sidebar-border">
        <button
          onClick={onLogout}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-xl text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>
    </div>
  );
}
