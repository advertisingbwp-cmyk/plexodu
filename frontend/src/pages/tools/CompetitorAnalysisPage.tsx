import React, { useState } from 'react';
import { api, ApiError } from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import {
  Users,
  Loader2,
  Sparkles,
  Tv,
  Eye,
  Video,
  AlertCircle,
  TrendingUp,
} from 'lucide-react';
import { RewardAdModal } from '../../components/RewardAdModal';
import { InsufficientCreditsModal } from '../../components/InsufficientCreditsModal';

export const CompetitorAnalysisPage: React.FC = () => {
  const { credits, refreshUser } = useAuth();
  const [channelUrl, setChannelUrl] = useState('');
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
      const res = await api.post<any>('/api/v1/tools/competitor-analysis', {
        channel_url_or_id: channelUrl,
      });
      setResult(res);
      await refreshUser();
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 402) {
          setIsInsufficientModalOpen(true);
        } else {
          setError(typeof err.detail === 'string' ? err.detail : 'Failed to audit competitor channel. Please check the URL or Handle.');
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
            <span className="px-2.5 py-0.5 rounded-full bg-amber-50 border border-amber-100 text-amber-700 text-[11px] font-bold">
              Cost: 1 Credit
            </span>
            <span className="text-slate-300">•</span>
            <span className="text-xs text-slate-500 font-medium">Channel Benchmark</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2.5">
            <Users className="w-7 h-7 text-amber-600" /> Competitor Channel Insights
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 max-w-xl">
            Audit competitor channels, subscriber reach, total video catalogue, and recent upload performance.
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
            <label htmlFor="competitor-channel-input" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Competitor YouTube Channel URL, Handle or ID
            </label>
            <input
              id="competitor-channel-input"
              type="text"
              required
              value={channelUrl}
              onChange={(e) => setChannelUrl(e.target.value)}
              placeholder="e.g., https://youtube.com/@mkbhd or UC..."
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-amber-600 focus:ring-2 focus:ring-amber-500/20 transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 rounded-2xl bg-amber-600 hover:bg-amber-700 active:bg-amber-800 text-white font-bold shadow-sm flex items-center justify-center gap-2 transition-all hover:shadow disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Sparkles className="w-4 h-4" /> Audit Competitor (1 Credit)
              </>
            )}
          </button>
        </form>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-fade-in">
          <div className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-card space-y-6">
            <div className="flex items-center gap-5">
              {result.avatar_url ? (
                <img
                  src={result.avatar_url}
                  alt={result.title}
                  className="w-16 h-16 rounded-2xl border border-slate-200 shadow-sm shrink-0"
                />
              ) : (
                <div className="w-16 h-16 rounded-2xl bg-amber-50 border border-amber-100 text-amber-600 font-bold flex items-center justify-center text-xl shrink-0">
                  <Tv className="w-8 h-8" />
                </div>
              )}
              <div className="space-y-1">
                <span className="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-100">
                  Channel Audit
                </span>
                <h2 className="text-xl font-bold text-slate-900">{result.title}</h2>
                <p className="text-xs text-slate-500 line-clamp-2">{result.description || 'Public YouTube Creator'}</p>
              </div>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-3 gap-3 pt-2">
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/60 text-center space-y-1">
                <Users className="w-4 h-4 text-slate-400 mx-auto" />
                <p className="text-xs font-bold text-slate-400 uppercase">Subscribers</p>
                <p className="text-lg font-black text-slate-900">{result.subscriber_count?.toLocaleString() || 0}</p>
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/60 text-center space-y-1">
                <Video className="w-4 h-4 text-slate-400 mx-auto" />
                <p className="text-xs font-bold text-slate-400 uppercase">Uploads</p>
                <p className="text-lg font-black text-slate-900">{result.video_count?.toLocaleString() || 0}</p>
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/60 text-center space-y-1">
                <Eye className="w-4 h-4 text-slate-400 mx-auto" />
                <p className="text-xs font-bold text-slate-400 uppercase">Lifetime Views</p>
                <p className="text-lg font-black text-amber-700">{result.view_count?.toLocaleString() || 0}</p>
              </div>
            </div>

            {/* Recent Videos Grid */}
            {result.recent_videos && result.recent_videos.length > 0 && (
              <div className="space-y-3 pt-2">
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Recent Channel Uploads ({result.recent_videos.length})
                </h3>
                <div className="divide-y divide-slate-100">
                  {result.recent_videos.map((vid: any, i: number) => (
                    <div key={i} className="py-3 flex items-center justify-between text-xs gap-3">
                      <p className="font-semibold text-slate-800 truncate">{vid.title}</p>
                      <span className="text-slate-400 shrink-0 text-[11px]">
                        {new Date(vid.published_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
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
