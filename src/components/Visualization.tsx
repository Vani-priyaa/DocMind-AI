"use client";

import React, { useState } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell
} from 'recharts';
import { MessageSquarePlus, Send, Sparkles, Download, Table, ChartBar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

const COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export function Visualization({ data, type, xAxis, yAxis, title, onAskAbout }) {
  const [query, setQuery] = useState("");
  const [view, setView] = useState('chart');

  const normalizedData = React.useMemo(() => {
    if (!data || !Array.isArray(data)) return [];
    
    const firstItem = data[0] || {};
    const keys = Object.keys(firstItem);
    
    return data.map(item => {
      const newItem = { ...item };
      if (xAxis && item[xAxis] !== undefined) newItem.name = item[xAxis];
      if (yAxis && item[yAxis] !== undefined) newItem.value = item[yAxis];
      if (newItem.name === undefined) newItem.name = item.label || item.x || item.category || item[keys[0]];
      if (newItem.value === undefined) newItem.value = item.y || item.amount || item.count || item[keys[1]] || item[keys[0]];
      return newItem;
    });
  }, [data, xAxis, yAxis]);

  if (!data || !type) return null;

  const handleDownloadCSV = () => {
    try {
      if (!data || !Array.isArray(data) || data.length === 0) {
        toast.error("No data available to download");
        return;
      }
      const headers = Object.keys(data[0]);
      const csvRows = [
        headers.join(','),
        ...data.map(row => headers.map(header => {
          const val = row[header] === null || row[header] === undefined ? "" : row[header];
          const escaped = ('' + val).replace(/"/g, '""');
          return `"${escaped}"`;
        }).join(','))
      ];
      const csvContent = csvRows.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${(title || 'chart_data').replace(/[^a-z0-9]/gi, '_').toLowerCase()}.csv`);
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
      toast.success("Data downloaded as CSV");
    } catch (err) {
      console.error("CSV Download Error:", err);
      toast.error("Failed to download CSV");
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    onAskAbout(`About the chart "${title}": ${query}`);
    setQuery("");
  };

  const renderChartContent = () => {
    if (!data || !Array.isArray(data) || data.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-zinc-500 gap-2">
          <ChartBar className="w-8 h-8 opacity-20" />
          <p className="text-sm font-medium">No data points available for this visualization</p>
        </div>
      );
    }

    let chartComponent = null;
    switch (type) {
      case 'bar':
        chartComponent = (
          <BarChart data={normalizedData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#88888820" />
            <XAxis dataKey="name" stroke="#888888" fontSize={11} tickLine={false} axisLine={false} tick={{fill: '#888888'}} />
            <YAxis stroke="#888888" fontSize={11} tickLine={false} axisLine={false} tick={{fill: '#888888'}} />
            <Tooltip cursor={{fill: '#f4f4f5'}} contentStyle={{ backgroundColor: 'white', borderRadius: '12px', border: '1px solid #e4e4e7' }} />
            <Legend verticalAlign="top" height={36}/>
            <Bar dataKey="value" fill="#2563eb" radius={[6, 6, 0, 0]} barSize={40}>
              {normalizedData.map((_, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} opacity={0.8} />)}
            </Bar>
          </BarChart>
        );
        break;
      case 'line':
        chartComponent = (
          <LineChart data={normalizedData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#88888820" />
            <XAxis dataKey="name" stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
            <YAxis stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ backgroundColor: 'white', borderRadius: '12px', border: '1px solid #e4e4e7' }} />
            <Legend verticalAlign="top" height={36}/>
            <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={3} dot={{ r: 4, fill: '#2563eb', strokeWidth: 2, stroke: '#fff' }} />
          </LineChart>
        );
        break;
      case 'pie':
        chartComponent = (
          <PieChart>
            <Pie data={normalizedData} cx="50%" cy="50%" innerRadius={70} outerRadius={100} paddingAngle={5} dataKey="value" nameKey="name">
              {normalizedData.map((_, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
            </Pie>
            <Tooltip contentStyle={{ backgroundColor: 'white', borderRadius: '12px', border: '1px solid #e4e4e7' }} />
            <Legend layout="vertical" align="right" verticalAlign="middle" />
          </PieChart>
        );
        break;
      case 'scatter':
        chartComponent = (
          <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#88888820" />
            <XAxis dataKey="name" type="category" name={xAxis || "X"} stroke="#888888" fontSize={11} />
            <YAxis dataKey="value" type="number" name={yAxis || "Y"} stroke="#888888" fontSize={11} />
            <Tooltip cursor={{ strokeDasharray: '3 3' }} />
            <Legend verticalAlign="top" height={36}/>
            <Scatter name="Data Points" data={normalizedData} fill="#2563eb" />
          </ScatterChart>
        );
        break;
      default:
        chartComponent = <div className="flex items-center justify-center h-full text-zinc-500">Unsupported chart type: {type}</div>;
    }

    return (
      <div className="w-full h-full min-h-[350px] flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%">
          {chartComponent}
        </ResponsiveContainer>
      </div>
    );
  };

  const renderTable = () => (
    <div className="overflow-auto max-h-[350px] w-full rounded-xl border border-zinc-100 dark:border-zinc-800">
      <table className="w-full text-sm text-left border-collapse">
        <thead className="text-xs text-zinc-500 uppercase bg-zinc-50 dark:bg-zinc-900 sticky top-0 z-10">
          <tr>
            {Object.keys(data[0] || {}).map(k => (
              <th key={k} className="px-4 py-3 font-bold border-b border-zinc-100 dark:border-zinc-800">{k}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {data.map((row, i) => (
            <tr key={i} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-900/50 transition-colors">
              {Object.values(row).map((v, j) => (
                <td key={j} className="px-4 py-3 text-zinc-700 dark:text-zinc-300">
                  {v === null || v === undefined ? "-" : String(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="w-full mt-4 bg-white dark:bg-zinc-950 rounded-[2rem] border border-zinc-200 dark:border-zinc-800 shadow-2xl overflow-hidden transition-all group/viz">
      <div className="p-6 border-b border-zinc-100 dark:border-zinc-900 bg-zinc-50/30 dark:bg-zinc-900/30 flex items-center justify-between">
        <div>
          {title && <h4 className="text-lg font-black text-zinc-900 dark:text-zinc-100 flex items-center gap-2 tracking-tight">
            <Sparkles className="w-5 h-5 text-blue-500" /> {title}
          </h4>}
          <div className="flex items-center gap-1.5 mt-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <p className="text-[10px] text-zinc-400 uppercase tracking-widest font-black">AI Insights Engine</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="bg-zinc-100 dark:bg-zinc-800 p-1 rounded-xl flex gap-1">
            <Button variant={view === 'chart' ? 'secondary' : 'ghost'} size="sm" onClick={() => setView('chart')} className="rounded-lg h-8 px-3 text-[10px] font-bold uppercase tracking-wider">
              <ChartBar className="w-3.5 h-3.5 mr-1.5" /> Chart
            </Button>
            <Button variant={view === 'table' ? 'secondary' : 'ghost'} size="sm" onClick={() => setView('table')} className="rounded-lg h-8 px-3 text-[10px] font-bold uppercase tracking-wider">
              <Table className="w-3.5 h-3.5 mr-1.5" /> Data
            </Button>
          </div>
          <Button variant="outline" size="icon" onClick={handleDownloadCSV} className="rounded-xl h-10 w-10 border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 shadow-sm" title="Download CSV">
            <Download className="w-4 h-4 text-zinc-600 dark:text-zinc-400" />
          </Button>
        </div>
      </div>
      <div className="p-8">
        <div className="h-[350px] w-full min-h-[350px] flex items-center justify-center overflow-hidden">
          {view === 'chart' ? renderChartContent() : renderTable()}
        </div>
      </div>
      <div className="p-6 bg-zinc-50/50 dark:bg-zinc-900/20 border-t border-zinc-100 dark:border-zinc-900">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <div className="relative flex-1">
            <MessageSquarePlus className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Deep dive into this visualization..." className="pl-11 h-12 bg-white dark:bg-black border-zinc-200 dark:border-zinc-800 rounded-2xl focus-visible:ring-blue-500 transition-all shadow-sm" />
          </div>
          <Button type="submit" size="icon" className="h-12 w-12 rounded-2xl bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white shadow-lg transition-all hover:scale-105 active:scale-95">
            <Send className="w-4.5 h-4.5" />
          </Button>
        </form>
      </div>
    </div>
  );
}
