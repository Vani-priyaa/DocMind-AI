"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable";
import { DocSidebar } from "@/components/docmind/DocSidebar";
import { DocChat } from "@/components/docmind/DocChat";
import { PDFViewer } from "@/components/docmind/PDFViewer";
import { useDocMind } from "@/hooks/useDocMind";
import { getSessions, createSession } from "@/lib/api";

export default function DocMindPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);

  // Initialize user and session
  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    if (!storedUser) {
      router.push("/");
      return;
    }
    const userData = JSON.parse(storedUser);
    if (!userData?.id) {
      localStorage.removeItem("user");
      router.push("/");
      return;
    }
    setUser(userData);

    // Get or create a session for DocMind
    (async () => {
      try {
        const sessions: any = await getSessions(userData.id);
        const sessionsList = Array.isArray(sessions) ? sessions : [];
        
        // Find or create a DocMind session
        let docmindSession = sessionsList.find(
          (s: any) => s.title?.startsWith("DocMind")
        );

        if (!docmindSession) {
          docmindSession = await createSession(userData.id, "DocMind Workspace");
        }

        setSessionId(docmindSession.id);
      } catch (err) {
        console.error("Session error:", err);
        // Create a new session as fallback
        try {
          const newSession: any = await createSession(userData.id, "DocMind Workspace");
          setSessionId(newSession.id);
        } catch {
          console.error("Failed to create session");
        }
      }
    })();
  }, [router]);

  const {
    documents,
    activeDocId,
    activeDocName,
    versions,
    currentVersionId,
    pdfUrl,
    messages,
    loading,
    uploading,
    editLoading,
    highlightPage,
    selectDocument,
    selectVersion,
    handleUploadPdf,
    sendChatMessage,
    handleConfirmEdit,
    handleRejectEdit,
    fetchSuggestions,
    handleCitationClick,
    handleDeleteDocument,
    handleRollbackVersion,
    handleDownloadPdf,
  } = useDocMind(sessionId);

  const handleLogout = () => {
    localStorage.removeItem("user");
    localStorage.removeItem("token");
    router.push("/");
  };

  if (!user || !sessionId) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center animate-pulse-glow">
            <svg className="w-5 h-5 text-primary-foreground animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.49-8.49l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.49 8.49l2.83 2.83" />
            </svg>
          </div>
          <p className="text-sm text-muted-foreground font-medium">Loading DocMind AI...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-background overflow-hidden">
      <ResizablePanelGroup direction="horizontal" className="h-full">
        {/* Left Sidebar — Documents & Versions */}
        <ResizablePanel defaultSize={20} minSize={15} maxSize={30}>
          <DocSidebar
            documents={documents}
            activeDocId={activeDocId}
            versions={versions}
            currentVersionId={currentVersionId}
            onSelectDocument={selectDocument}
            onSelectVersion={selectVersion}
            onRollbackVersion={handleRollbackVersion}
            onUploadPdf={handleUploadPdf}
            onDeleteDocument={handleDeleteDocument}
            onLogout={handleLogout}
            uploading={uploading}
          />
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Center — Chat Interface */}
        <ResizablePanel defaultSize={45} minSize={30}>
          <DocChat
            messages={messages}
            loading={loading}
            uploading={uploading}
            documentName={activeDocName}
            onSend={sendChatMessage}
            onUpload={handleUploadPdf}
            onFetchSuggestions={fetchSuggestions}
            onCitationClick={handleCitationClick}
            onConfirmEdit={handleConfirmEdit}
            onRejectEdit={handleRejectEdit}
            editLoading={editLoading}
          />
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Right Panel — PDF Viewer */}
        <ResizablePanel defaultSize={35} minSize={20}>
          <PDFViewer
            fileUrl={pdfUrl}
            highlightPage={highlightPage}
            documentName={activeDocName || undefined}
            onDownload={handleDownloadPdf}
          />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
