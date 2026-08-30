import React, { useState } from 'react';
import { api, ApiError } from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import {
  Video,
  Loader2,
  Sparkles,
  Eye,
  ThumbsUp,
  MessageSquare,
  Tag,
  AlertCircle,
  TrendingUp,
} from 'lucide-react';
import { RewardAdModal } from '../../components/RewardAdModal';
import { InsufficientCreditsModal } from '../../components/InsufficientCreditsModal';

export const VideoAnalyzerPage: React.FC = () => {
  const { credits, refreshUser } = useAuth();
  const [videoUrl, setVideoUrl] = useState('');
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
      const res = await api.post<any>('/api/v1/tools/video-analyzer', {
        video_url_or_id: videoUrl,
      });
      setResult(res);
      await refreshUser();
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 402) {
          setIsInsufficientModalOpen(true);
        } else {
          setError(typeof err.detail === 'string' ? err.detail : 'Failed to analyze video. Please verify the URL or ID.');
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
            <span className="px-2.5 py-0.5 rounded-full bg-purple-50 border border-purple-100 text-purple-700 text-[11px] font-bold">
              Cost: 1 Credit
            </span>
            <span className="text-slate-300">•</span>
            <span className="text-xs text-slate-500 font-medium">Live YouTube Data</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2.5">
            <Video className="w-7 h-7 text-purple-600" /> YouTube Video Analyzer
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 max-w-xl">
            Inspect live engagement rates, view velocity, tag structure, and AI title improvement suggestions.
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
            <label htmlFor="analyzer-video-url" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              YouTube Video URL or Video ID
            </label>
            <input
              id="analyzer-video-url"
              type="text"
              required
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=... or 11-character ID"
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-purple-600 focus:ring-2 focus:ring-purple-500/20 transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 rounded-2xl bg-purple-600 hover:bg-purple-700 active:bg-purple-800 text-white font-bold shadow-sm flex items-center justify-center gap-2 transition-all hover:shadow disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Sparkles className="w-4 h-4" /> Analyze Video (1 Credit)
              </>
            )}
          </button>
        </form>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-fade-in">
          {/* Main Video Card */}
          <div className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-card space-y-6">
            <div className="flex flex-col sm:flex-row gap-6 items-start">
              {result.thumbnail_url && (
                <img
                  src={result.thumbnail_url}
                  alt={result.title}
                  className="w-full sm:w-56 aspect-video rounded-2xl object-cover border border-slate-200 shadow-sm shrink-0"
                />
              )}
              <div className="space-y-2">
                <span className="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-100">
                  {result.channel_title || 'YouTube Creator'}
                </span>
                <h2 className="text-lg sm:text-xl font-bold text-slate-900 leading-snug">
                  {result.title}
                </h2>
                <p className="text-xs text-slate-500">
                  Published: {new Date(result.published_at).toLocaleDateString()}
                </p>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/60 text-center space-y-1">
                <Eye className="w-4 h-4 text-slate-400 mx-auto" />
                <p className="text-xs font-bold text-slate-400 uppercase">Views</p>
                <p className="text-lg font-black text-slate-900">{result.view_count?.toLocaleString() || 0}</p>
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/60 text-center space-y-1">
                <ThumbsUp className="w-4 h-4 text-slate-400 mx-auto" />
                <p className="text-xs font-bold text-slate-400 uppercase">Likes</p>
                <p className="text-lg font-black text-slate-900">{result.like_count?.toLocaleString() || 0}</p>
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/60 text-center space-y-1">
                <MessageSquare className="w-4 h-4 text-slate-400 mx-auto" />
                <p className="text-xs font-bold text-slate-400 uppercase">Comments</p>
                <p className="text-lg font-black text-slate-900">{result.comment_count?.toLocaleString() || 0}</p>
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/60 text-center space-y-1">
                <TrendingUp className="w-4 h-4 text-slate-400 mx-auto" />
                <p className="text-xs font-bold text-slate-400 uppercase">Engagement</p>
                <p className="text-lg font-black text-purple-700">{result.engagement_rate || '0.0%'}</p>
              </div>
            </div>

            {/* Tags Cloud */}
            {result.tags && result.tags.length > 0 && (
              <div className="space-y-2 pt-2">
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <Tag className="w-3.5 h-3.5 text-slate-400" /> Extracted Tags ({result.tags.length})
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {result.tags.map((tag: string, i: number) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 text-xs font-medium border border-slate-200/60"
                    >
                      #{tag}
                    </span>
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
