import React, { useState } from 'react';
import { api, ApiError } from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import {
  Gauge,
  Loader2,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  FileText,
  Video,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';
import { RewardAdModal } from '../../components/RewardAdModal';
import { InsufficientCreditsModal } from '../../components/InsufficientCreditsModal';

export const SeoScorePage: React.FC = () => {
  const { credits, refreshUser } = useAuth();
  const [tab, setTab] = useState<'url' | 'draft'>('draft');

  // Input states
  const [videoUrl, setVideoUrl] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  const [isAdModalOpen, setIsAdModalOpen] = useState(false);
  const [isInsufficientModalOpen, setIsInsufficientModalOpen] = useState(false);

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (credits < 1) {
      setIsInsufficientModalOpen(true);
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const payload =
        tab === 'url'
          ? { video_url_or_id: videoUrl }
          : {
              title,
              description,
              tags: tags
                .split(',')
                .map((t) => t.trim())
                .filter(Boolean),
            };

      const res = await api.post<any>('/api/v1/tools/seo-score', payload);
      setResult(res);
      await refreshUser();
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 402) {
          setIsInsufficientModalOpen(true);
        } else {
          setError(typeof err.detail === 'string' ? err.detail : 'Failed to calculate SEO score.');
        }
      } else {
        setError('Network error. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const getScoreRating = (score: number) => {
    if (score >= 42) return { label: 'Excellent', color: 'text-emerald-600 bg-emerald-50 border-emerald-200' };
    if (score >= 32) return { label: 'Good Optimization', color: 'text-indigo-600 bg-indigo-50 border-indigo-200' };
    if (score >= 20) return { label: 'Moderate', color: 'text-amber-600 bg-amber-50 border-amber-200' };
    return { label: 'Needs Improvement', color: 'text-red-600 bg-red-50 border-red-200' };
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border border-slate-200/80 shadow-card flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-[11px] font-bold">
              Cost: 1 Credit
            </span>
            <span className="text-slate-300">•</span>
            <span className="text-xs text-slate-500 font-medium">5-Factor Algorithm</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2.5">
            <Gauge className="w-7 h-7 text-indigo-600" /> Plexudo 50-Point SEO Score
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 max-w-xl">
            Evaluate video titles, descriptions, tag density, and keyword overlap against our 5-factor optimization algorithm.
          </p>
        </div>
      </div>

      {/* Input Mode Tabs & Form */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border border-slate-200/80 shadow-card space-y-6">
        <div className="flex gap-2 p-1.5 rounded-2xl bg-slate-100/80 max-w-md">
          <button
            type="button"
            onClick={() => setTab('draft')}
            className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
              tab === 'draft'
                ? 'bg-white text-indigo-700 shadow-subtle'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileText className="w-3.5 h-3.5" /> Audit Draft Metadata
          </button>
          <button
            type="button"
            onClick={() => setTab('url')}
            className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
              tab === 'url'
                ? 'bg-white text-indigo-700 shadow-subtle'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Video className="w-3.5 h-3.5" /> Audit Live YouTube Video
          </button>
        </div>

        {error && (
          <div className="p-4 rounded-2xl bg-red-50 border border-red-100 text-red-700 text-xs font-semibold flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}

        <form onSubmit={handleCalculate} className="space-y-4">
          {tab === 'draft' ? (
            <>
              <div>
                <label htmlFor="seo-title" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Video Title
                </label>
                <input
                  id="seo-title"
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g., How to Master YouTube SEO in 2026 (Full Guide)"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all"
                />
              </div>

              <div>
                <label htmlFor="seo-description" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Video Description
                </label>
                <textarea
                  id="seo-description"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Paste your video description here with timestamps and relevant keywords..."
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all"
                />
              </div>

              <div>
                <label htmlFor="seo-tags" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Tags (comma-separated)
                </label>
                <input
                  id="seo-tags"
                  type="text"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="youtube seo, video growth, algorithm optimization"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all"
                />
              </div>
            </>
          ) : (
            <div>
              <label htmlFor="seo-video-url" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                YouTube Video URL or Video ID
              </label>
              <input
                id="seo-video-url"
                type="text"
                required
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=... or 11-char ID"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all"
              />
            </div>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 rounded-2xl bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-bold shadow-sm flex items-center justify-center gap-2 transition-all hover:shadow disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <Sparkles className="w-4 h-4" /> Calculate SEO Score (1 Credit)
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Result Presentation */}
      {result && (
        <div className="space-y-6 animate-fade-in">
          {/* Hero Score Card */}
          <div className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-card flex flex-col md:flex-row items-center justify-between gap-8">
            <div className="space-y-2 text-center md:text-left">
              <span className="text-[11px] font-bold uppercase tracking-widest text-indigo-600 bg-indigo-50 border border-indigo-100 px-3 py-1 rounded-full">
                Plexudo SEO Score
              </span>
              <h2 className="text-xl sm:text-2xl font-bold text-slate-900">
                {result.title || result.metadata?.title || 'Audited Video'}
              </h2>
              <div className="flex flex-wrap items-center justify-center md:justify-start gap-2 pt-1">
                {(() => {
                  const rating = getScoreRating(result.seo_score?.total || 0);
                  return (
                    <span className={`px-3 py-1 rounded-xl text-xs font-extrabold border ${rating.color}`}>
                      {rating.label}
                    </span>
                  );
                })()}
                <span className="text-xs text-slate-400">Calculated across 5 algorithm factors</span>
              </div>
            </div>

            {/* Circular / Hero Score Badge */}
            <div className="flex flex-col items-center justify-center p-6 rounded-3xl bg-gradient-to-tr from-indigo-50/80 via-white to-slate-50 border border-indigo-100/80 shadow-subtle shrink-0 min-w-[160px]">
              <div className="text-5xl font-black text-indigo-700 tracking-tight">
                {result.seo_score?.total ?? 0}
                <span className="text-xl font-bold text-slate-400">/50</span>
              </div>
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mt-1">
                Optimization Score
              </span>
            </div>
          </div>

          {/* 5-Category Breakdown Progress Bars */}
          <div className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-card space-y-6">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-indigo-600" /> Algorithmic Factor Breakdown
            </h3>

            <div className="space-y-4">
              {[
                {
                  key: 'title_optimization',
                  name: 'Title Optimization',
                  score: result.seo_score?.breakdown?.title_optimization ?? 0,
                  desc: 'Length (40–70 chars), capital letters, and power hook words.',
                },
                {
                  key: 'description_depth',
                  name: 'Description Depth',
                  score: result.seo_score?.breakdown?.description_depth ?? 0,
                  desc: 'Length (>250 words), timestamp links, and keyword frequency.',
                },
                {
                  key: 'tag_density',
                  name: 'Tag Density',
                  score: result.seo_score?.breakdown?.tag_density ?? 0,
                  desc: 'Target 10–25 high-relevance tags covering niche and long-tail topics.',
                },
                {
                  key: 'keyword_volume',
                  name: 'Keyword Volume',
                  score: result.seo_score?.breakdown?.keyword_volume ?? 0,
                  desc: 'Presence of high-intent search terms across metadata.',
                },
                {
                  key: 'triple_overlap',
                  name: 'Triple Keyword Overlap',
                  score: result.seo_score?.breakdown?.triple_overlap ?? 0,
                  desc: 'Exact match synergy between Title, Description, and Tags.',
                },
              ].map((item) => (
                <div key={item.key} className="space-y-1.5 p-4 rounded-2xl bg-slate-50 border border-slate-200/60">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-800">{item.name}</span>
                    <span className="font-black text-slate-900">
                      {item.score} <span className="text-slate-400 font-normal">/ 10</span>
                    </span>
                  </div>
                  <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-indigo-600 rounded-full transition-all duration-700"
                      style={{ width: `${(item.score / 10) * 100}%` }}
                    />
                  </div>
                  <p className="text-[11px] text-slate-500 pt-0.5">{item.desc}</p>
                </div>
              ))}
            </div>
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
