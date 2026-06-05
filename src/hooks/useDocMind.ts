"use client";

import { useState, useCallback, useEffect } from "react";
import {
  uploadPDF,
  getSessionDocuments,
  getDocumentVersions,
  getVersionFileUrl,
  askQuestion,
  summarizeDocument,
  editDocument,
  confirmEdit,
  getAutocompleteSuggestions,
  getPdfChatHistory,
  deleteDocument as apiDeleteDocument,
} from "@/lib/api";
import { toast } from "sonner";

interface DocState {
  documents: any[];
  activeDocId: number | null;
  activeDocName: string | null;
  versions: any[];
  currentVersionId: number | null;
  pdfUrl: string | null;
  messages: any[];
  loading: boolean;
  uploading: boolean;
  editLoading: boolean;
  highlightPage: number | null;
}

export function useDocMind(sessionId: number | null) {
  const [state, setState] = useState<DocState>({
    documents: [],
    activeDocId: null,
    activeDocName: null,
    versions: [],
    currentVersionId: null,
    pdfUrl: null,
    messages: [],
    loading: false,
    uploading: false,
    editLoading: false,
    highlightPage: null,
  });

  // Load documents for session
  const loadDocuments = useCallback(async () => {
    if (!sessionId) return;
    try {
      const docs: any = await getSessionDocuments(sessionId);
      setState((s) => ({ ...s, documents: Array.isArray(docs) ? docs : [] }));
    } catch (err) {
      console.error("Failed to load documents:", err);
    }
  }, [sessionId]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Select a document
  const selectDocument = useCallback(async (docId: number) => {
    try {
      const versions: any = await getDocumentVersions(docId);
      const versionsList = Array.isArray(versions) ? versions : [];
      const latestVersion = versionsList[0];
      const doc = state.documents.find((d) => d.id === docId);

      // Load chat history
      const history: any = await getPdfChatHistory(docId);

      setState((s) => ({
        ...s,
        activeDocId: docId,
        activeDocName: doc?.filename || null,
        versions: versionsList,
        currentVersionId: latestVersion?.id || null,
        pdfUrl: latestVersion ? getVersionFileUrl(docId, latestVersion.id) : null,
        messages: Array.isArray(history) ? history : [],
        highlightPage: null,
      }));
    } catch (err) {
      console.error("Failed to select document:", err);
    }
  }, [state.documents]);

  // Select a specific version
  const selectVersion = useCallback((versionId: number) => {
    if (!state.activeDocId) return;
    setState((s) => ({
      ...s,
      currentVersionId: versionId,
      pdfUrl: getVersionFileUrl(s.activeDocId!, versionId),
    }));
  }, [state.activeDocId]);

  // Upload a PDF
  const handleUploadPdf = useCallback(async (file: File) => {
    if (!sessionId) return;
    setState((s) => ({ ...s, uploading: true }));

    try {
      const result: any = await uploadPDF(sessionId, file, (percent) => {
        // Could show progress bar
      });

      toast.success(`"${file.name}" uploaded and indexed!`);

      // Reload documents
      await loadDocuments();

      // Auto-select the uploaded doc
      if (result?.id) {
        setTimeout(() => selectDocument(result.id), 500);
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to upload PDF");
    } finally {
      setState((s) => ({ ...s, uploading: false }));
    }
  }, [sessionId, loadDocuments, selectDocument]);

  // Send a message (chat, edit, or summarize)
  const sendChatMessage = useCallback(async (message: string) => {
    if (!state.activeDocId) {
      toast.error("Please select a document first");
      return;
    }

    setState((s) => ({
      ...s,
      loading: true,
      messages: [...s.messages, { role: "user", content: message, message_type: "chat" }],
    }));

    try {
      let result: any;

      // Check for edit commands
      if (message.startsWith("[EDIT] ")) {
        const command = message.replace("[EDIT] ", "");
        result = await editDocument(state.activeDocId, command);

        // Add edit preview to messages
        setState((s) => ({
          ...s,
          loading: false,
          messages: [
            ...s.messages,
            {
              role: "assistant",
              content: `📝 Edit Preview: ${result.description || result.preview_summary || ""}`,
              message_type: "edit",
              sources: [],
              editPreview: result.preview_id ? result : undefined,
            },
          ],
        }));
        return;
      }

      // Check for summarize commands
      if (message.startsWith("[SUMMARIZE] ")) {
        const text = message.replace("[SUMMARIZE] ", "");
        // Parse mode from text
        let mode = "executive";
        if (text.toLowerCase().includes("bullet")) mode = "bullet";
        else if (text.toLowerCase().includes("technical")) mode = "technical";

        result = await summarizeDocument(state.activeDocId, mode);

        setState((s) => ({
          ...s,
          loading: false,
          messages: [
            ...s.messages,
            {
              role: "assistant",
              content: result.summary || "Summary generated.",
              message_type: "summary",
              sources: result.sources || [],
            },
          ],
        }));
        return;
      }

      // Regular Q&A
      result = await askQuestion(state.activeDocId, message);

      setState((s) => ({
        ...s,
        loading: false,
        messages: [
          ...s.messages,
          {
            role: "assistant",
            content: result.answer || "No answer found.",
            sources: result.sources || [],
            follow_ups: result.follow_ups || [],
            message_type: "chat",
          },
        ],
      }));
    } catch (err: any) {
      console.error("Chat error:", err);
      toast.error("Failed to process message");
      setState((s) => ({
        ...s,
        loading: false,
        messages: [
          ...s.messages,
          {
            role: "assistant",
            content: "Sorry, I encountered an error processing your request. Please try again.",
            message_type: "chat",
          },
        ],
      }));
    }
  }, [state.activeDocId]);

  // Confirm an edit
  const handleConfirmEdit = useCallback(async (previewId: number) => {
    if (!state.activeDocId) return;
    setState((s) => ({ ...s, editLoading: true }));

    try {
      const result: any = await confirmEdit(state.activeDocId, previewId);

      if (result.success) {
        toast.success(`Version ${result.version_number} created!`);

        // Reload versions and update PDF view
        const versions: any = await getDocumentVersions(state.activeDocId);
        const versionsList = Array.isArray(versions) ? versions : [];
        const latestVersion = versionsList[0];

        setState((s) => {
          const updatedMessages = s.messages.map((m) => {
            if (m.editPreview && m.editPreview.preview_id === previewId) {
              return {
                ...m,
                editPreview: {
                  ...m.editPreview,
                  status: "applied",
                },
              };
            }
            return m;
          });

          return {
            ...s,
            editLoading: false,
            versions: versionsList,
            currentVersionId: latestVersion?.id || null,
            pdfUrl: latestVersion ? getVersionFileUrl(s.activeDocId!, latestVersion.id) : null,
            messages: [
              ...updatedMessages,
              {
                role: "assistant",
                content: `✅ Edit applied! Created version ${result.version_number}.`,
                message_type: "edit",
              },
            ],
          };
        });

        // Reload documents to update page count
        loadDocuments();
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to apply edit");
      setState((s) => ({ ...s, editLoading: false }));
    }
  }, [state.activeDocId, loadDocuments]);

  // Reject an edit
  const handleRejectEdit = useCallback((previewId: number) => {
    setState((s) => {
      const updatedMessages = s.messages.map((m) => {
        if (m.editPreview && m.editPreview.preview_id === previewId) {
          return {
            ...m,
            editPreview: {
              ...m.editPreview,
              status: "discarded",
            },
          };
        }
        return m;
      });

      return {
        ...s,
        messages: [
          ...updatedMessages,
          {
            role: "assistant",
            content: "Edit discarded. No changes were made to the document.",
            message_type: "edit",
          },
        ],
      };
    });
  }, []);

  // Fetch autocomplete suggestions
  const fetchSuggestions = useCallback(async (partial: string): Promise<string[]> => {
    if (!state.activeDocId || partial.length < 3) return [];
    try {
      const result: any = await getAutocompleteSuggestions(state.activeDocId, partial);
      return result?.suggestions || [];
    } catch {
      return [];
    }
  }, [state.activeDocId]);

  // Navigate to a cited page
  const handleCitationClick = useCallback((pageNumber: number) => {
    setState((s) => ({ ...s, highlightPage: pageNumber }));
  }, []);

  // Delete a document
  const handleDeleteDocument = useCallback(async (docId: number) => {
    try {
      await apiDeleteDocument(docId);
      toast.success("Document deleted");
      
      setState((s) => ({
        ...s,
        documents: s.documents.filter((d) => d.id !== docId),
        activeDocId: s.activeDocId === docId ? null : s.activeDocId,
        activeDocName: s.activeDocId === docId ? null : s.activeDocName,
        pdfUrl: s.activeDocId === docId ? null : s.pdfUrl,
        messages: s.activeDocId === docId ? [] : s.messages,
        versions: s.activeDocId === docId ? [] : s.versions,
      }));
    } catch (err) {
      toast.error("Failed to delete document");
    }
  }, []);

  // Rollback to a version
  const handleRollbackVersion = useCallback((versionId: number) => {
    selectVersion(versionId);
    toast.info("Viewing selected version");
  }, [selectVersion]);

  // Download current PDF
  const handleDownloadPdf = useCallback(() => {
    if (state.pdfUrl) {
      const link = document.createElement("a");
      link.href = state.pdfUrl;
      link.download = state.activeDocName || "document.pdf";
      link.click();
    }
  }, [state.pdfUrl, state.activeDocName]);

  return {
    ...state,
    loadDocuments,
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
  };
}
