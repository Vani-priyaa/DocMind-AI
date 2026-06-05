"use client";

import React from "react";

interface CitationChipProps {
  pageNumber: number;
  heading?: string;
  snippet?: string;
  onClick?: (pageNumber: number) => void;
}

export function CitationChip({ pageNumber, heading, snippet, onClick }: CitationChipProps) {
  return (
    <button
      onClick={() => onClick?.(pageNumber)}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold
        bg-primary/10 text-primary border border-primary/20
        hover:bg-primary/20 hover:border-primary/30
        transition-all duration-200 cursor-pointer group"
      title={snippet ? `${heading || ''} — ${snippet.slice(0, 100)}...` : `Go to page ${pageNumber}`}
    >
      <svg className="w-3 h-3 opacity-60 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      Page {pageNumber}
    </button>
  );
}
