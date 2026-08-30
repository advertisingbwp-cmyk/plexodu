import React, { useState } from 'react';
import { api, ApiError } from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import {
  Search,
  Loader2,
  Sparkles,
  TrendingUp,
  AlertCircle,
  Hash,
  Video,
} from 'lucide-react';
import { RewardAdModal } from '../../components/RewardAdModal';
import { InsufficientCreditsModal } from '../../components/InsufficientCreditsModal';

export const KeywordToolPage: React.FC = () => {
  const { credits, refreshUser } = useAuth();
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  const [isAdModalOpen, setIsAdModalOpen] = useState(false);
  const [isInsufficientModalOpen, setIsInsufficientModalOpen] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (credits < 1) {
      setIsInsufficientModalOpen(true);
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const res = await api.post<any>('/api/v1/tools/keyword-tool', {
        seed_keyword: keyword,
      });
      setResult(res);
      await refreshUser();
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 402) {
          setIsInsufficientModalOpen(true);
        } else {
          setError(typeof err.detail === 'string' ? err.detail : 'Failed to explore keywords. Please try another search term.');
        }
      } else {
        setError('Network connection error. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border border-slate-200/80 shadow-card flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-pink-50 border border-pink-100 text-pink-700 text-[11px] font-bold">
              Cost: 1 Credit
            </span>
            <span className="text-slate-300">•</span>
            <span className="text-xs text-slate-500 font-medium">Search Intent & Clusters</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2.5">
            <Search className="w-7 h-7 text-pink-600" /> YouTube Keyword Explorer
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 max-w-xl">
            Find estimated search volumes, high-intent long-tail keywords, question phrases, and top ranking videos.
          </p>
        </div>
      </div>

      {/* Input Form */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border border-slate-200/80 shadow-card space-y-6">
        {error && (
          <div className="p-4 rounded-2xl bg-red-50 border border-red-100 text-red-700 text-xs font-semibold flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}

        <form onSubmit={handleSearch} className="space-y-4">
          <div>
            <label htmlFor="keyword-search-term" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Seed Keyword or Topic
            </label>
            <input
              id="keyword-search-term"
              type="text"
              required
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="e.g., Python tutorial, Minecraft building, YouTube automation"
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-pink-600 focus:ring-2 focus:ring-pink-500/20 transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 rounded-2xl bg-pink-600 hover:bg-pink-700 active:bg-pink-800 text-white font-bold shadow-sm flex items-center justify-center gap-2 transition-all hover:shadow disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Sparkles className="w-4 h-4" /> Explore Keywords (1 Credit)
              </>
            )}
          </button>
        </form>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-fade-in">
          {/* Estimated Search Volume Card */}
          <div className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-card flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-pink-50 text-pink-700 border border-pink-100">
                Primary Target Term
              </span>
              <h2 className="text-xl font-bold text-slate-900 capitalize">"{result.seed_keyword}"</h2>
              <p className="text-xs text-slate-500">Estimated Search Volume Range</p>
            </div>
            <div className="text-right">
              <span className="text-2xl sm:text-3xl font-black text-pink-600">
                {result.estimated_search_volume || 'High'}
              </span>
            </div>
          </div>

          {/* Long-Tail Keyword Clusters */}
          {result.long_tail_keywords && result.long_tail_keywords.length > 0 && (
            <div className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-card space-y-4">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Hash className="w-4 h-4 text-pink-600" /> High-Intent Long-Tail Keywords
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {result.long_tail_keywords.map((term: string, i: number) => (
                  <div
                    key={i}
                    className="p-3 rounded-xl bg-slate-50 border border-slate-200/60 text-xs font-medium text-slate-800 flex items-center justify-between"
                  >
                    <span>{term}</span>
                    <span className="text-[10px] font-bold text-pink-600 bg-pink-50 px-2 py-0.5 rounded-md">
                      Low Comp
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Ranking YouTube Videos */}
          {result.top_ranking_videos && result.top_ranking_videos.length > 0 && (
            <div className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-card space-y-4">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Video className="w-4 h-4 text-pink-600" /> Top Ranking Videos for "{result.seed_keyword}"
              </h3>
              <div className="divide-y divide-slate-100">
                {result.top_ranking_videos.map((vid: any, i: number) => (
                  <div key={i} className="py-3 flex items-center justify-between text-xs gap-3">
                    <div className="flex items-center gap-3 truncate">
                      <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-500 font-bold flex items-center justify-center text-[10px] shrink-0">
                        {i + 1}
                      </span>
                      <span className="font-semibold text-slate-800 truncate">{vid.title}</span>
                    </div>
                    <span className="text-slate-400 shrink-0 text-[11px]">{vid.channel_title}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <InsufficientCreditsModal
        isOpen={isInsufficientModalOpen}
        onClose={() => setIsInsufficientModalOpen(false)}
        onOpenAdModal={() => setIsAdModalOpen(true)}
      />

      <RewardAdModal
        isOpen={isAdModalOpen}
        onClose={() => setIsAdModalOpen(false)}
        onSuccess={refreshUser}
      />
    </div>
  );
};
