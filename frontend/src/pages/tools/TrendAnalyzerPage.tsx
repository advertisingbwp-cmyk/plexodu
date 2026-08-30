import React, { useState } from 'react';
import { api, ApiError } from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import {
  TrendingUp,
  Loader2,
  Sparkles,
  Globe,
  Tag,
  Video,
  AlertCircle,
  Flame,
} from 'lucide-react';
import { RewardAdModal } from '../../components/RewardAdModal';
import { InsufficientCreditsModal } from '../../components/InsufficientCreditsModal';

const REGIONS = [
  { code: 'US', name: 'United States 🇺🇸' },
  { code: 'PK', name: 'Pakistan 🇵🇰' },
  { code: 'UK', name: 'United Kingdom 🇬🇧' },
  { code: 'IN', name: 'India 🇮🇳' },
  { code: 'AE', name: 'United Arab Emirates 🇦🇪' },
];

export const TrendAnalyzerPage: React.FC = () => {
  const { credits, refreshUser } = useAuth();
  const [region, setRegion] = useState('US');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  const [isAdModalOpen, setIsAdModalOpen] = useState(false);
  const [isInsufficientModalOpen, setIsInsufficientModalOpen] = useState(false);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (credits < 1) {
      setIsInsufficientModalOpen(true);
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const res = await api.post<any>('/api/v1/tools/trend-analyzer', {
        region_code: region,
      });
      setResult(res);
      await refreshUser();
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 402) {
          setIsInsufficientModalOpen(true);
        } else {
          setError(typeof err.detail === 'string' ? err.detail : 'Failed to analyze trends.');
        }
      } else {
        setError('Network error. Please try again.');
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
            <span className="px-2.5 py-0.5 rounded-full bg-cyan-50 border border-cyan-100 text-cyan-700 text-[11px] font-bold">
              Cost: 1 Credit
            </span>
            <span className="text-slate-300">•</span>
            <span className="text-xs text-slate-500 font-medium">5 Regional Markets</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2.5">
            <TrendingUp className="w-7 h-7 text-cyan-600" /> YouTube Trend Analyzer
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 max-w-xl">
            Analyze viral trending videos and extracted tag patterns across US, PK, UK, IN, and AE regions.
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

        <form onSubmit={handleAnalyze} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Select Geographic Market
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              {REGIONS.map((r) => (
                <button
                  type="button"
                  key={r.code}
                  onClick={() => setRegion(r.code)}
                  className={`p-3 rounded-2xl border text-xs font-bold flex items-center justify-between transition-all ${
                    region === r.code
                      ? 'bg-cyan-50 border-cyan-300 text-cyan-900 shadow-subtle'
                      : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  <span>{r.name}</span>
                  <span className="text-[10px] text-slate-400 font-normal">{r.code}</span>
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 rounded-2xl bg-cyan-600 hover:bg-cyan-700 active:bg-cyan-800 text-white font-bold shadow-sm flex items-center justify-center gap-2 transition-all hover:shadow disabled:opacity-50 mt-4"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Sparkles className="w-4 h-4" /> Fetch Breakout Trends (1 Credit)
              </>
            )}
          </button>
        </form>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-fade-in">
          {/* Tag Frequency Matrix */}
          {result.trending_tags && result.trending_tags.length > 0 && (
            <div className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-card space-y-4">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Flame className="w-4 h-4 text-cyan-600" /> High-Frequency Breakout Tags ({result.region_code})
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.trending_tags.map((tag: any, i: number) => (
                  <span
                    key={i}
                    className="px-3 py-1.5 rounded-xl bg-cyan-50 border border-cyan-200/60 text-cyan-800 text-xs font-semibold flex items-center gap-1.5"
                  >
                    <span>#{tag.tag || tag}</span>
                    {tag.count && (
                      <span className="text-[10px] font-bold text-cyan-600 bg-cyan-100/80 px-1.5 py-0.5 rounded">
                        {tag.count}x
                      </span>
                    )}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Trending Videos Feed */}
          {result.videos && result.videos.length > 0 && (
            <div className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-card space-y-4">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Video className="w-4 h-4 text-cyan-600" /> Live Trending Feed ({result.region_code})
              </h3>
              <div className="divide-y divide-slate-100">
                {result.videos.map((vid: any, i: number) => (
                  <div key={i} className="py-3.5 flex items-center justify-between text-xs gap-3">
                    <div className="flex items-center gap-3 truncate">
                      <span className="w-6 h-6 rounded-full bg-cyan-50 text-cyan-700 font-black flex items-center justify-center text-xs shrink-0 border border-cyan-100">
                        {i + 1}
                      </span>
                      <div className="truncate">
                        <p className="font-bold text-slate-900 truncate">{vid.title}</p>
                        <p className="text-[11px] text-slate-400">{vid.channel_title}</p>
                      </div>
                    </div>
                    <span className="text-slate-500 font-semibold shrink-0 text-xs">
                      {vid.view_count ? `${Number(vid.view_count).toLocaleString()} views` : 'Trending'}
                    </span>
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
