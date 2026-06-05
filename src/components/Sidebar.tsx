"use client";

import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageSquare, LogOut, Settings, Plus, Database, ChevronRight, MoreVertical, Pencil, Trash2, Check, X } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

export function Sidebar({ sessions = [], currentSession, onSelectSession, onLogout, onRenameSession, onDeleteSession }) {
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState("");

  const handleStartEdit = (e, session) => {
    e.stopPropagation();
    setEditingId(session.id);
    setEditTitle(session.title);
  };

  const handleSaveEdit = async (e, id) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      await onRenameSession(id, editTitle);
    }
    setEditingId(null);
  };

  const handleCancelEdit = (e) => {
    e.stopPropagation();
    setEditingId(null);
  };

  return (
    <div className="w-72 border-r border-zinc-100 dark:border-zinc-900 bg-zinc-50/50 dark:bg-black flex flex-col h-full">
      <div className="p-6">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-8 h-8 rounded-lg bg-black dark:bg-white flex items-center justify-center">
            <Database className="w-5 h-5 text-white dark:text-black" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-black dark:text-white">Conversational Data Analyst</h1>
        </div>

        <div className="space-y-1">
          <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest px-2 mb-2">Workspace</p>
          <Button 
            variant="ghost" 
            onClick={() => toast.success("Workspace Overview", { description: `You have ${sessions.length} active analytical sessions loaded.`})}
            className="w-full justify-start text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 rounded-xl px-2"
          >
            <MessageSquare className="w-4 h-4 mr-3" /> All Analyses
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1 px-4">
        <div className="space-y-4">
          <div>
            <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest px-2 mb-3">Recent History</p>
            <div className="space-y-1">
              {sessions.filter(s => s?.id).map((s) => (
                <div key={s.id} className="group relative">
                  {editingId === s.id ? (
                    <div className="flex items-center gap-1 px-2 py-1 bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800">
                      <Input
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="h-8 text-sm focus-visible:ring-0 border-none px-1"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveEdit(e, s.id);
                          if (e.key === 'Escape') handleCancelEdit(e);
                        }}
                      />
                      <button onClick={(e) => handleSaveEdit(e, s.id)} className="p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded">
                        <Check className="w-3.5 h-3.5 text-emerald-500" />
                      </button>
                      <button onClick={handleCancelEdit} className="p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded">
                        <X className="w-3.5 h-3.5 text-zinc-400" />
                      </button>
                    </div>
                  ) : (
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => onSelectSession(s)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          onSelectSession(s);
                        }
                      }}
                      className={`w-full group flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-xl transition-all cursor-pointer ${currentSession?.id === s.id
                        ? "bg-white dark:bg-zinc-900 text-black dark:text-white shadow-sm border border-zinc-200 dark:border-zinc-800"
                        : "text-zinc-500 hover:text-black dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-900"
                        }`}
                    >
                      <div className={`w-1.5 h-1.5 rounded-full ${currentSession?.id === s.id ? "bg-black dark:bg-white" : "bg-transparent group-hover:bg-zinc-300 dark:group-hover:bg-zinc-700"}`} />
                      <span className="truncate flex-1 text-left">{s.title}</span>

                      <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <div
                              role="button"
                              tabIndex={0}
                              className="p-1 hover:bg-zinc-200 dark:hover:bg-zinc-800 rounded-md cursor-pointer"
                              onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                  e.stopPropagation();
                                }
                              }}
                            >
                              <MoreVertical className="w-3.5 h-3.5" />
                            </div>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-32">
                            <DropdownMenuItem onClick={(e) => handleStartEdit(e, s)}>
                              <Pencil className="w-3.5 h-3.5 mr-2" /> Rename
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              className="text-red-500 focus:text-red-500"
                              onClick={(e) => { e.stopPropagation(); onDeleteSession(s.id); }}
                            >
                              <Trash2 className="w-3.5 h-3.5 mr-2" /> Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>

                      {currentSession?.id === s.id && !editingId && <ChevronRight className="w-3.5 h-3.5 opacity-50" />}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </ScrollArea>

      <div className="p-4 mt-auto">
        <div className="bg-zinc-100 dark:bg-zinc-900 rounded-2xl p-4 space-y-1">
          <Button 
            variant="ghost" 
            onClick={() => toast("System Preferences", { description: "Your workspace is currently syncing settings universally."})}
            className="w-full justify-start text-zinc-600 dark:text-zinc-400 hover:bg-white dark:hover:bg-black rounded-xl px-2 h-9"
          >
            <Settings className="w-4 h-4 mr-3" /> Settings
          </Button>
          <Button
            variant="ghost"
            className="w-full justify-start text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 rounded-xl px-2 h-9"
            onClick={onLogout}
          >
            <LogOut className="w-4 h-4 mr-3" /> Logout
          </Button>
        </div>
      </div>
    </div>
  );
}
