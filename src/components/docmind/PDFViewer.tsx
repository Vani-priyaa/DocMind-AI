"use client";

import React, { useState, useEffect, useRef } from "react";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Maximize2, Download, Loader2, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PDFViewerProps {
  fileUrl: string | null;
  highlightPage?: number | null;
  documentName?: string;
  onDownload?: () => void;
}

export function PDFViewer({ fileUrl, highlightPage, documentName, onDownload }: PDFViewerProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [zoom, setZoom] = useState(100);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Update page when citation is clicked
  useEffect(() => {
    if (highlightPage && highlightPage > 0) {
      setCurrentPage(highlightPage);
      // Use the iframe's PDF viewer page navigation if available
      if (iframeRef.current && fileUrl) {
        const pageUrl = `${fileUrl}#page=${highlightPage}`;
        iframeRef.current.src = pageUrl;
      }
    }
  }, [highlightPage, fileUrl]);

  // Reset when file changes
  useEffect(() => {
    if (fileUrl) {
      setLoading(true);
      setError(false);
      setCurrentPage(1);

      // Fallback timeout to ensure the loading spinner is dismissed
      // even if the browser doesn't trigger the iframe's onLoad event for PDF plug-ins.
      const timer = setTimeout(() => {
        setLoading(false);
      }, 1500);

      return () => clearTimeout(timer);
    }
  }, [fileUrl]);

  const navigatePage = (direction: "prev" | "next") => {
    setCurrentPage((prev) => {
      const newPage = direction === "prev" ? Math.max(1, prev - 1) : prev + 1;
      if (iframeRef.current && fileUrl) {
        iframeRef.current.src = `${fileUrl}#page=${newPage}`;
      }
      return newPage;
    });
  };

  const handleZoom = (direction: "in" | "out" | "fit") => {
    if (direction === "fit") {
      setZoom(100);
    } else {
      setZoom((prev) => Math.max(50, Math.min(200, prev + (direction === "in" ? 25 : -25))));
    }
  };

  if (!fileUrl) {
    return (
      <div className="flex flex-col h-full items-center justify-center text-muted-foreground bg-muted/20">
        <div className="w-16 h-16 rounded-2xl bg-muted/50 flex items-center justify-center mb-4 border border-border/50">
          <FileText className="w-8 h-8 opacity-30" />
        </div>
        <p className="text-sm font-medium">No Document Selected</p>
        <p className="text-xs text-muted-foreground/60 mt-1">Upload or select a PDF to preview it here</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-muted/10">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/50 glass-strong">
        <div className="flex items-center gap-2">
          {/* Page Navigation */}
          <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-0.5">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 rounded-md"
              onClick={() => navigatePage("prev")}
              disabled={currentPage <= 1}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <div className="flex items-center gap-1 px-2">
              <input
                type="number"
                value={currentPage}
                onChange={(e) => {
                  const page = parseInt(e.target.value);
                  if (page > 0) {
                    setCurrentPage(page);
                    if (iframeRef.current) {
                      iframeRef.current.src = `${fileUrl}#page=${page}`;
                    }
                  }
                }}
                className="w-10 h-6 text-center text-xs font-semibold bg-background rounded border border-border/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
                min={1}
              />
              {totalPages > 0 && (
                <span className="text-xs text-muted-foreground">/ {totalPages}</span>
              )}
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 rounded-md"
              onClick={() => navigatePage("next")}
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>

          {/* Separator */}
          <div className="w-px h-5 bg-border/50" />

          {/* Zoom Controls */}
          <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-0.5">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 rounded-md"
              onClick={() => handleZoom("out")}
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </Button>
            <span className="text-xs font-medium w-10 text-center text-muted-foreground">{zoom}%</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 rounded-md"
              onClick={() => handleZoom("in")}
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 rounded-md"
              onClick={() => handleZoom("fit")}
              title="Fit to width"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        {/* Document Name + Download */}
        <div className="flex items-center gap-2">
          {documentName && (
            <span className="text-xs text-muted-foreground font-medium truncate max-w-[150px]">
              {documentName}
            </span>
          )}
          {onDownload && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 rounded-md"
              onClick={onDownload}
              title="Download PDF"
            >
              <Download className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* PDF Content */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto flex items-start justify-center p-4 bg-muted/20"
      >
        <div
          style={{
            transform: `scale(${zoom / 100})`,
            transformOrigin: "top center",
            transition: "transform 0.2s ease",
          }}
          className="w-full max-w-4xl"
        >
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10">
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">Loading PDF...</p>
              </div>
            </div>
          )}

          <iframe
            ref={iframeRef}
            src={`${fileUrl}#page=${currentPage}&toolbar=0`}
            className="w-full rounded-lg shadow-xl border border-border/30"
            style={{
              height: "calc(100vh - 180px)",
              minHeight: "500px",
            }}
            onLoad={() => setLoading(false)}
            onError={() => {
              setLoading(false);
              setError(true);
            }}
          />

          {error && (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <FileText className="w-12 h-12 mb-3 opacity-20" />
              <p className="text-sm font-medium">Failed to load PDF</p>
              <p className="text-xs opacity-60 mt-1">Try downloading the file instead</p>
            </div>
          )}
        </div>
      </div>

      {/* Highlight indicator */}
      {highlightPage && (
        <div className="px-4 py-2 bg-primary/5 border-t border-primary/15 flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          <span className="text-xs text-primary font-medium">
            Showing Page {highlightPage} — referenced in citation
          </span>
        </div>
      )}
    </div>
  );
}
