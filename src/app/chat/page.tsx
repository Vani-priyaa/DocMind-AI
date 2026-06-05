"use client";

import React, { useState, useEffect } from 'react';
import { Sidebar } from "@/components/Sidebar";
import { ChatInterface } from "@/components/ChatInterface";
import { getSessions, createSession, updateSession, deleteSession } from "@/lib/api";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

export default function ChatPage() {
  const [user, setUser] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const router = useRouter();

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    if (!storedUser) {
      router.push("/");
      return;
    }
    const userData = JSON.parse(storedUser);
    if (!userData || !userData.id) {
      localStorage.removeItem("user");
      router.push("/");
      return;
    }
    setUser(userData);
    loadSessions(userData.id);
  }, []);

  const loadSessions = async (userId) => {
    try {
      const res = await getSessions(userId);
      const sessionsData = res || [];
      setSessions(sessionsData);
      if (sessionsData.length > 0 && !currentSession) {
        setCurrentSession(sessionsData[0]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleNewChat = async () => {
    try {
      const res = await createSession(user.id, `New Analysis ${sessions.length + 1}`);
      setSessions([res, ...sessions]);
      setCurrentSession(res);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRenameSession = async (sessionId, newTitle) => {
    try {
      const res = await updateSession(sessionId, newTitle);
      setSessions(sessions.map(s => s.id === sessionId ? res : s));
      if (currentSession?.id === sessionId) {
        setCurrentSession(res);
      }
      toast.success("Session renamed");
    } catch (err) {
      console.error(err);
      toast.error("Failed to rename session");
    }
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      await deleteSession(sessionId);
      const updatedSessions = sessions.filter(s => s.id !== sessionId);
      setSessions(updatedSessions);
      if (currentSession?.id === sessionId) {
        setCurrentSession(updatedSessions.length > 0 ? updatedSessions[0] : null);
      }
      toast.success("Session deleted");
    } catch (err) {
      console.error(err);
      toast.error("Failed to delete session");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("user");
    router.push("/");
  };

  if (!user) return null;

  return (
    <div className="flex h-screen bg-white dark:bg-black overflow-hidden">
      <Sidebar
        sessions={sessions}
        currentSession={currentSession}
        onSelectSession={setCurrentSession}
        onLogout={handleLogout}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
      />
      <main className="flex-1 h-full relative">
        {currentSession ? (
          <ChatInterface
            session={currentSession}
            onNewChat={handleNewChat}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full space-y-4">
            <h2 className="text-2xl font-bold">Welcome to Conversational Data Analyst</h2>
            <p className="text-zinc-500">Select a chat or start a new analysis to begin.</p>
            <button
              onClick={handleNewChat}
              className="px-4 py-2 bg-black text-white rounded-md hover:bg-zinc-800 transition-colors"
            >
              Start New Analysis
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
