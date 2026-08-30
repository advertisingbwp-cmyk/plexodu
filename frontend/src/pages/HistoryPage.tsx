import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import {
  History,
  Filter,
  Calendar,
  Sparkles,
  X,
  Code,
  FileJson,
  ChevronRight,
} from 'lucide-react';
import { EmptyState } from '../components/EmptyState';
import { LoadingSkeleton } from '../components/LoadingSkeleton';

export const HistoryPage: React.FC = () => {
  const [entries, setEntries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterTool, setFilterTool] = useState<string>('ALL');
  const [selectedEntry, setSelectedEntry] = useState<any | null>(null);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const url =
        filterTool === 'ALL'
          ? '/api/v1/history/?limit=50'
          : `/api/v1/history/?tool_type=${filterTool}&limit=50`;
      const res = await api.get<{ entries: any[]; count: number }>(url);
      setEntries(res.entries || []);
    } catch {
      // Handled
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [filterTool]);

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border border-slate-200/80 shadow-card flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2.5">
            <History className="w-7 h-7 text-indigo-600" /> Tool Execution History
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 max-w-xl">
            View past runs, 50-point SEO score reports, keyword queries, and generated AI retention hooks.
          </p>
        </div>

        {/* Filter Dropdown */}
        <div className="flex items-center gap-2 bg-slate-50 p-1.5 rounded-2xl border border-slate-200 shrink-0">
          <Filter className="w-4 h-4 text-slate-400 ml-2" />
          <label htmlFor="history-tool-filter" className="sr-only">Filter by Tool</label>
          <select
            id="history-tool-filter"
            value={filterTool}
            onChange={(e) => setFilterTool(e.target.value)}
            className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none pr-3 py-1 cursor-pointer"
          >
            <option value="ALL">All Tools</option>
            <option value="SEO_SCORE">SEO Score</option>
            <option value="VIDEO_ANALYZER">Video Analyzer</option>
            <option value="KEYWORD_TOOL">Keyword Tool</option>
            <option value="TREND_ANALYZER">Trend Analyzer</option>
            <option value="COMPETITOR_ANALYSIS">Competitor Analysis</option>
            <option value="AI_ASSISTANT">AI Assistant</option>
          </select>
        </div>
      </div>

      {/* History Table / List */}
      {loading ? (
        <LoadingSkeleton rows={4} />
      ) : entries.length === 0 ? (
        <EmptyState
          icon={History}
          title="No Execution History"
          description="You haven't run any creator tools under this filter yet. Run an SEO audit or keyword search to see your history."
        />
      ) : (
        <div className="space-y-4">
          {/* Desktop Table View (>= 640px) */}
          <div className="hidden sm:block bg-white border border-slate-200/80 rounded-3xl overflow-hidden shadow-card divide-y divide-slate-100">
            <div className="grid grid-cols-12 p-4 text-[11px] font-bold uppercase tracking-wider text-slate-400 bg-slate-50/70">
              <div className="col-span-3">Tool</div>
              <div className="col-span-5">Input Parameter</div>
              <div className="col-span-3">Date</div>
              <div className="col-span-1 text-right">Details</div>
            </div>

            {entries.map((item) => (
              <div
                key={item.id}
                className="grid grid-cols-12 p-4 text-xs items-center hover:bg-slate-50/60 transition-colors"
              >
                <div className="col-span-3">
                  <span className="px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 font-bold border border-indigo-100 text-[11px]">
                    {item.tool_type}
                  </span>
                </div>
                <div className="col-span-5 font-semibold text-slate-800 truncate pr-3">
                  {item.input?.title ||
                    item.input?.video_url_or_id ||
                    item.input?.seed_keyword ||
                    item.input?.channel_url_or_id ||
                    item.input?.topic ||
                    item.input?.region_code ||
                    'Tool Execution'}
                </div>
                <div className="col-span-3 text-slate-400 text-[11px]">
                  {new Date(item.created_at).toLocaleString()}
                </div>
                <div className="col-span-1 text-right">
                  <button
                    onClick={() => setSelectedEntry(item)}
                    className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-[11px] transition-colors"
                  >
                    View
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Mobile Card List (< 640px) */}
          <div className="block sm:hidden space-y-3">
            {entries.map((item) => (
              <div
                key={item.id}
                onClick={() => setSelectedEntry(item)}
                className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-subtle flex items-center justify-between gap-3 active:bg-slate-50 cursor-pointer transition-colors"
              >
                <div className="space-y-1.5 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 font-bold border border-indigo-100 text-[10px]">
                      {item.tool_type}
                    </span>
                    <span className="text-slate-400 text-[10px]">
                      {new Date(item.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="font-bold text-xs text-slate-900 truncate">
                    {item.input?.title ||
                      item.input?.video_url_or_id ||
                      item.input?.seed_keyword ||
                      item.input?.channel_url_or_id ||
                      item.input?.topic ||
                      item.input?.region_code ||
                      'Tool Execution'}
                  </p>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* JSON Execution Output Inspector Modal */}
      {selectedEntry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fade-in">
          <div className="relative w-full max-w-2xl bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-modal space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-bold">
                  {selectedEntry.tool_type}
                </span>
                <span className="text-xs text-slate-400">
                  {new Date(selectedEntry.created_at).toLocaleString()}
                </span>
              </div>
              <button
                onClick={() => setSelectedEntry(null)}
                className="text-slate-400 hover:text-slate-700 p-1"
                aria-label="Close details modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="overflow-y-auto space-y-4 pr-1 text-xs">
              <div>
                <p className="font-bold text-slate-700 uppercase tracking-wider text-[10px] mb-1">
                  Input Parameters
                </p>
                <pre className="p-3 rounded-2xl bg-slate-50 border border-slate-200 text-slate-800 font-mono text-[11px] overflow-x-auto">
                  {JSON.stringify(selectedEntry.input, null, 2)}
                </pre>
              </div>

              <div>
                <p className="font-bold text-slate-700 uppercase tracking-wider text-[10px] mb-1">
                  Execution Output
                </p>
                <pre className="p-3 rounded-2xl bg-slate-50 border border-slate-200 text-slate-800 font-mono text-[11px] overflow-x-auto">
                  {JSON.stringify(selectedEntry.result, null, 2)}
                </pre>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setSelectedEntry(null)}
                className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs transition-colors shadow-sm"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
