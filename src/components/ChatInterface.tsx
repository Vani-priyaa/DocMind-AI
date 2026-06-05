"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Visualization } from "./Visualization";
import { sendMessage, uploadFile, getHistory, downloadPDF, downloadDataset } from "@/lib/api";
import { Loader2, Send, Upload, FileDown, Plus, Database, User, Bot, Sparkles, Download, LayoutDashboard, List } from "lucide-react";
import { toast } from "sonner";

export function ChatInterface({ session, onNewChat }: { session: any, onNewChat: any }) {
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [downloadingReport, setDownloadingReport] = useState(false);
  const [downloadingDataset, setDownloadingDataset] = useState(false);
  const [viewMode, setViewMode] = useState("chat"); // 'chat' or 'dashboard'
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = (behavior: ScrollBehavior = "auto") => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior, block: "end" });
    }

    if (scrollRef.current) {
      const viewports = scrollRef.current.querySelectorAll('[data-radix-scroll-area-viewport]');
      viewports.forEach((viewport) => {
        viewport.scrollTop = viewport.scrollHeight;
      });
    }
  };

  useEffect(() => {
    const loadHistory = async () => {
      if (session?.id) {
        try {
          const history = await getHistory(session.id);
          // The backend returns an array directly, not an object with a 'messages' key
          setMessages(Array.isArray(history) ? history : (history.messages || []));
        } catch (err) {
          console.error("Failed to load history");
        }
      }
    };
    loadHistory();
  }, [session?.id]);

  useEffect(() => {
    scrollToBottom("smooth");
  }, [messages]);

  const handleSend = async (specificInput?: string) => {
    const query = specificInput || input.trim();
    if (!query || !session) return;

    setInput("");
    setLoading(true);

    setMessages(prev => [...prev, { role: "user", content: query }]);

    try {
      const response = await sendMessage(session.id, query);
      console.log("DEBUG RESPONSE:", response);

      const explanation = response.explanation || (response.data && response.data.explanation) || "No explanation received. Check console.";
      const visualization = response.visualization || (response.data && response.data.visualization);

      setMessages(prev => [...prev, {
        role: "assistant",
        content: explanation,
        data: visualization
      }]);

      if (response.email_to_forward) {
        toast.success(`Analysis report is being sent to ${response.email_to_forward}`);
      }
    } catch (err) {
      console.error(err);
      toast.error("Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const handleAskAboutChart = (query) => {
    handleSend(query);
  };

  const handleUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0 || !session) return;

    setUploading(true);
    const toastId = toast.loading(`Uploading ${files.length} file(s)...`);

    try {
      await Promise.all(files.map(async (file) => {
        const response = await uploadFile(session.id, file);

        const systemMessage = {
          role: "system",
          content: `File "${file.name}" uploaded successfully.`
        };

        // If backend returned a visualization, add it as a separate assistant message or attach to system message
        // Since system messages in this UI don't support 'data' prop natively in the map below (unless we change it),
        // we'll add a second message if viz exists.

        setMessages(prev => {
          const newMessages = [...prev, systemMessage];

          if (response.visualization) {
            newMessages.push({
              role: "assistant",
              content: "I've generated an initial visualization of your data:",
              data: { type: response.visualization.type, data: response.visualization.data, xAxis: response.visualization.xAxis, yAxis: response.visualization.yAxis, title: response.visualization.title }
            });
          }

          return newMessages;
        });
      }));

      toast.success("All files uploaded successfully", { id: toastId });
      // Remove the generic "Data processed" message since we likely showed a chart now
    } catch (err) {
      console.error(err);
      const errorMessage = err.response?.data?.detail || "Failed to upload file.";
      toast.error(`Upload failed: ${errorMessage}`, { id: toastId });
    } finally {
      setUploading(false);
      e.target.value = null;
    }
  };

  const handleDownloadPDF = async () => {
    if (!session) return;
    setDownloadingReport(true);
    const toastId = toast.loading("Generating comprehensive report...");

    try {
      const blob = await downloadPDF(session.id);

      // Create a link element, hide it, direct it towards the blob, and then 'click' it programmatically
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      const filename = `${(session.title || "analyst_report").replace(/[^a-z0-9]/gi, '_').toLowerCase()}.pdf`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();

      // Clean up
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success("Report downloaded successfully", { id: toastId });
    } catch (err) {
      console.error(err);
      toast.error("Failed to generate report. Please try again.", { id: toastId });
    } finally {
      setDownloadingReport(false);
    }
  };

  const handleDownloadDataset = async () => {
    if (!session) return;
    setDownloadingDataset(true);
    const toastId = toast.loading("Preparing your cleaned dataset...");

    try {
      const blob = await downloadDataset(session.id);

      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      // Default filename, though the browser will try to use the header filename if possible
      link.setAttribute('download', `cleaned_dataset_${session.id}.csv`);
      document.body.appendChild(link);
      link.click();

      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success("Dataset downloaded successfully", { id: toastId });
    } catch (err) {
      console.error(err);
      toast.error(err.response?.status === 404 ? "No dataset found. Please upload one first." : "Failed to download dataset. Ensure it is loaded in memory.", { id: toastId });
    } finally {
      setDownloadingDataset(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-black font-sans">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-zinc-100 dark:border-zinc-800 bg-white/80 dark:bg-black/80 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-zinc-800 to-black dark:from-white dark:to-zinc-300 flex items-center justify-center shadow-lg">
            <Database className="w-5 h-5 text-white dark:text-black" />
          </div>
          <div>
            <h2 className="text-base font-bold tracking-tight text-zinc-900 dark:text-zinc-100">{session?.title || "New Chat"}</h2>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <p className="text-[10px] text-zinc-500 font-medium uppercase tracking-wider">AI Analyst Online</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Toggle View Mode */}
          <div className="flex bg-zinc-100 dark:bg-zinc-900 rounded-full p-1 mr-2 border border-zinc-200 dark:border-zinc-800">
            <button
              onClick={() => setViewMode("chat")}
              className={`flex items-center px-4 py-1.5 rounded-full text-xs font-semibold transition-all ${
                viewMode === "chat" 
                ? "bg-white dark:bg-zinc-800 text-black dark:text-white shadow-sm" 
                : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
              }`}
            >
              <List className="w-3.5 h-3.5 mr-1.5" /> Chat
            </button>
            <button
              onClick={() => setViewMode("dashboard")}
              className={`flex items-center px-4 py-1.5 rounded-full text-xs font-semibold transition-all ${
                viewMode === "dashboard" 
                ? "bg-white dark:bg-zinc-800 text-black dark:text-white shadow-sm" 
                : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5 mr-1.5" /> Dashboard
            </button>
          </div>

          <Button variant="ghost" size="sm" onClick={onNewChat} className="rounded-full hover:bg-zinc-100 dark:hover:bg-zinc-900">
            <Plus className="w-4 h-4 mr-2" /> New Chat
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadDataset}
            disabled={downloadingDataset}
            className="rounded-full border-zinc-200 dark:border-zinc-800 shadow-sm hover:bg-zinc-50 dark:hover:bg-zinc-900 group"
          >
            {downloadingDataset ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Download className="w-4 h-4 mr-2 text-zinc-500 group-hover:text-zinc-900 dark:group-hover:text-zinc-100" />
            )}
            <span className="hidden sm:inline">
              {downloadingDataset ? "Exporting..." : "Export Cleaned Data"}
            </span>
            <span className="sm:hidden">Data</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadPDF}
            disabled={downloadingReport}
            className="rounded-full border-zinc-200 dark:border-zinc-800 shadow-sm hover:bg-zinc-50 dark:hover:bg-zinc-900 group"
          >
            {downloadingReport ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <FileDown className="w-4 h-4 mr-2 text-zinc-500 group-hover:text-zinc-900 dark:group-hover:text-zinc-100" />
            )}
            <span className="hidden sm:inline">
              {downloadingReport ? "Generating..." : "Download Full Report"}
            </span>
            <span className="sm:hidden">Report</span>
          </Button>
        </div>
      </header>

      {/* View Router */}
      {viewMode === "dashboard" ? (
        <ScrollArea className="flex-1 bg-zinc-50/50 dark:bg-zinc-900/10">
          <div className="max-w-7xl mx-auto px-6 py-12">
            <div className="flex items-center gap-4 mb-8 pb-6 border-b border-zinc-200 dark:border-zinc-800">
              <div className="w-12 h-12 rounded-2xl bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center">
                <LayoutDashboard className="w-6 h-6 text-zinc-600 dark:text-zinc-400" />
              </div>
              <div>
                <h2 className="text-2xl font-bold tracking-tight text-black dark:text-white">Executive Dashboard</h2>
                <p className="text-sm text-zinc-500 font-medium">Auto-generated interactive visualizations from your analysis</p>
              </div>
            </div>
            
            {messages.filter(m => m.data).length === 0 ? (
              <div className="flex flex-col items-center justify-center py-32 text-zinc-500 bg-white dark:bg-zinc-950 rounded-[2rem] border border-zinc-100 dark:border-zinc-900 shadow-sm">
                <LayoutDashboard className="w-16 h-16 mb-6 opacity-20" />
                <h3 className="text-xl font-bold text-zinc-800 dark:text-zinc-200">No Visualizations Yet</h3>
                <p className="mt-2 opacity-70">Ask the AI to generate a chart to see it pinned to your dashboard.</p>
                <button onClick={() => setViewMode("chat")} className="mt-6 px-6 py-2 bg-black dark:bg-white text-white dark:text-black rounded-full font-medium text-sm transition-all hover:scale-105 shadow-xl">Return to Chat Flow</button>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {messages.filter(m => m.data).map((m, i) => (
                  <div key={i} className="bg-white dark:bg-zinc-950 p-6 rounded-[2rem] border border-zinc-100 dark:border-zinc-900 shadow-xl overflow-hidden hover:border-emerald-500/30 transition-colors">
                    <h3 className="text-lg font-bold mb-6 flex items-center tracking-tight text-zinc-900 dark:text-zinc-100">
                       <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-3 shadow-lg shadow-emerald-500/50"></span>
                       {m.data.title || `Data Insight ${i + 1}`}
                    </h3>
                    <div className="-mx-2 h-[400px]">
                       <Visualization
                         data={m.data.data}
                         type={m.data.type}
                         xAxis={m.data.xAxis}
                         yAxis={m.data.yAxis}
                         title="" 
                         onAskAbout={(q) => {
                           setViewMode("chat");
                           handleAskAboutChart(q);
                         }}
                       />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </ScrollArea>
      ) : (
        <>
          {/* Messages */}
          <ScrollArea className="flex-1" ref={scrollRef}>
            <div className="max-w-4xl mx-auto px-6 py-12 space-y-10">
              {messages.length === 0 && (
                <div className="text-center py-20 space-y-6">
                  <div className="w-20 h-20 rounded-3xl bg-zinc-50 dark:bg-zinc-900 flex items-center justify-center mx-auto shadow-inner border border-zinc-100 dark:border-zinc-800">
                    <Sparkles className="w-10 h-10 text-zinc-400" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Welcome to Conversational Data Analyst</h3>
                    <p className="text-zinc-500 max-w-sm mx-auto text-sm leading-relaxed">
                      I am AnalystBot, how can I help you today? Upload your datasets and let's uncover hidden insights together.
                    </p>
                  </div>
                  <div className="flex flex-wrap justify-center gap-4 pt-4">
                    <label className="flex items-center gap-2 px-6 py-3 rounded-xl bg-black dark:bg-white text-white dark:text-black font-semibold hover:bg-zinc-800 dark:hover:bg-zinc-100 transition-all shadow-lg cursor-pointer">
                      <Upload className="w-5 h-5" />
                      <span>Upload Dataset</span>
                      <input type="file" multiple className="hidden" onChange={handleUpload} disabled={uploading} accept=".csv,.xlsx,.xls" />
                    </label>
                  </div>
                </div>
              )}

              {messages.map((m, i) => (
                <div key={i} className={`flex gap-5 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${m.role === 'user'
                    ? 'bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700'
                    : 'bg-zinc-900 dark:bg-white border border-zinc-800 dark:border-zinc-200'
                    }`}>
                    {m.role === 'user' ? <User className="w-4.5 h-4.5 text-zinc-600 dark:text-zinc-400" /> : <Bot className="w-5 h-5 text-white dark:text-black" />}
                  </div>
                  <div className={`flex flex-col gap-3 max-w-[85%] ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                    {m.role === 'system' ? (
                      <div className="bg-zinc-50/50 dark:bg-zinc-900/30 px-4 py-2 rounded-xl border border-dashed border-zinc-200 dark:border-zinc-800 text-[11px] text-zinc-500 font-semibold tracking-wide flex items-center gap-2">
                        <div className="w-1 h-1 rounded-full bg-zinc-400" />
                        {m.content}
                      </div>
                    ) : (
                      <>
                        <div className={`px-5 py-4 rounded-2xl text-[14px] leading-relaxed shadow-sm ${m.role === 'user'
                          ? 'bg-zinc-900 dark:bg-white text-white dark:text-black font-medium'
                          : 'bg-zinc-50 dark:bg-zinc-900/50 text-zinc-800 dark:text-zinc-200 border border-zinc-100 dark:border-zinc-800'
                          }`}>
                          <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                            {m.content}
                          </div>
                        </div>
                        {m.data && (
                          <Visualization
                            data={m.data.data}
                            type={m.data.type}
                            xAxis={m.data.xAxis}
                            yAxis={m.data.yAxis}
                            title={m.data.title}
                            onAskAbout={handleAskAboutChart}
                          />
                        )}
                      </>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex gap-5">
                  <div className="w-9 h-9 rounded-xl bg-zinc-900 dark:bg-white flex items-center justify-center shrink-0 shadow-sm">
                    <Bot className="w-5 h-5 text-white dark:text-black" />
                  </div>
                  <div className="bg-zinc-50 dark:bg-zinc-900/50 px-5 py-4 rounded-2xl border border-zinc-100 dark:border-zinc-800 flex items-center gap-3 shadow-sm">
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-xs text-zinc-500 font-medium italic">Analyzing datasets...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} className="h-4" />
            </div>
          </ScrollArea>

          {/* Input Section */}
          <div className="p-8 border-t border-zinc-100 dark:border-zinc-900 bg-white/50 dark:bg-black/50 backdrop-blur-md">
            <div className="max-w-4xl mx-auto">
              <div className="relative flex items-end gap-3 bg-white dark:bg-zinc-950 p-3 rounded-2xl border border-zinc-200 dark:border-zinc-800 shadow-xl">
                <label className="shrink-0 p-3 hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-xl cursor-pointer transition-all">
                  <input type="file" multiple className="hidden" onChange={handleUpload} disabled={uploading} accept=".csv,.xlsx,.xls" />
                  {uploading ? (
                    <Loader2 className="w-5 h-5 animate-spin text-zinc-400" />
                  ) : (
                    <Upload className="w-5 h-5 text-zinc-400" />
                  )}
                </label>
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="Ask your AI analyst about trends, correlations, or summaries..."
                  className="w-full bg-transparent border-none focus:ring-0 resize-none py-3 text-[15px] max-h-48"
                  rows={1}
                />
                <Button
                  onClick={() => handleSend()}
                  disabled={loading || !input.trim()}
                  size="icon"
                  className="shrink-0 rounded-xl h-12 w-12 bg-black hover:bg-zinc-800 dark:bg-white dark:hover:bg-zinc-100 dark:text-black shadow-lg"
                >
                  <Send className="w-5 h-5" />
                </Button>
              </div>
              <div className="flex items-center justify-center gap-6 mt-4">
                <p className="text-[10px] text-zinc-400 uppercase tracking-[0.2em] font-bold">
                  Interactive Data Engine
                </p>
                <div className="w-1 h-1 rounded-full bg-zinc-200 dark:bg-zinc-800" />
                <p className="text-[10px] text-zinc-400 uppercase tracking-[0.2em] font-bold">
                  GPT-4o Enhanced
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
