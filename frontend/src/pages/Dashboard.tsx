import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import {
  Sparkles,
  Tv,
  Gauge,
  Video,
  Search,
  TrendingUp,
  Users,
  Bot,
  CheckCircle,
  ExternalLink,
  History as HistoryIcon,
  ArrowUpRight,
  Activity,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { RewardAdModal } from '../components/RewardAdModal';

export const Dashboard: React.FC = () => {
  const { user, credits } = useAuth();
  const [ytStatus, setYtStatus] = useState<{
    connected: boolean;
    channel_title?: string;
    channel_id?: string;
    channel_avatar_url?: string;
    google_email?: string;
  }>({ connected: false });
  const [recentHistory, setRecentHistory] = useState<any[]>([]);
  const [isAdModalOpen, setIsAdModalOpen] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const status = await api.get<any>('/api/v1/youtube/status');
        setYtStatus(status);
      } catch {
        // Ignored
      }

      try {
        const hist = await api.get<{ entries: any[]; count: number }>('/api/v1/history/?limit=5');
        setRecentHistory(hist.entries || []);
      } catch {
        // Ignored
      }
    })();
  }, []);

  const handleConnectYouTube = async () => {
    try {
      const res = await api.get<{ url: string }>('/api/v1/youtube/connect');
      window.location.href = res.url;
    } catch (err: any) {
      alert(err.detail || 'Failed to start YouTube connection');
    }
  };

  const lastSeoEntry = recentHistory.find((e) => e.tool_type === 'SEO_SCORE');
  const lastScore = lastSeoEntry?.result?.seo_score?.total;

  return (
    <div className="space-y-6 sm:space-y-8 max-w-5xl mx-auto">
      {/* Welcome Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 sm:p-8 rounded-3xl border border-slate-200/80 shadow-card">
        <div className="space-y-1.5 min-w-0">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-[11px] font-bold tracking-wide">
              Creator Studio
            </span>
            <span className="text-slate-300">•</span>
            <span className="text-xs text-slate-500 font-medium">Real-time Analytics</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight truncate">
            Welcome back, {user?.username} 👋
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 max-w-xl leading-relaxed">
            Optimize your YouTube videos with 50-point algorithmic audits, competitor tag mapping, and AI retention hooks.
          </p>
        </div>

        <div className="flex items-center gap-3 bg-slate-50 p-2.5 rounded-2xl border border-slate-200/60 shrink-0 w-full sm:w-auto justify-between sm:justify-start">
          <div className="px-2 sm:px-3">
            <p className="text-[10px] sm:text-[11px] font-bold text-slate-400 uppercase tracking-wider">Credits</p>
            <p className="text-xl sm:text-2xl font-black text-slate-900">{credits}</p>
          </div>
          <button
            onClick={() => setIsAdModalOpen(true)}
            className="px-3.5 sm:px-4 py-2 sm:py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-bold text-xs shadow-sm flex items-center gap-1.5 transition-all hover:shadow"
          >
            <Sparkles className="w-3.5 h-3.5" /> +1 Credit
          </button>
        </div>
      </div>

      {/* 4 Summary Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-subtle space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-bold uppercase tracking-wider">Recent SEO Score</span>
            <Gauge className="w-4 h-4 text-indigo-600" />
          </div>
          <p className="text-2xl font-black text-slate-900">
            {lastScore !== undefined ? `${lastScore}/50` : '—'}
          </p>
          <p className="text-[11px] text-slate-500 truncate">
            {lastScore !== undefined ? 'Latest audited video' : 'No audits run yet'}
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-subtle space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-bold uppercase tracking-wider">Tools Executed</span>
            <Activity className="w-4 h-4 text-purple-600" />
          </div>
          <p className="text-2xl font-black text-slate-900">{recentHistory.length}</p>
          <p className="text-[11px] text-slate-500 truncate">Total recorded runs</p>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-subtle space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-bold uppercase tracking-wider">Credit Balance</span>
            <Sparkles className="w-4 h-4 text-indigo-600" />
          </div>
          <p className="text-2xl font-black text-indigo-700">{credits}</p>
          <p className="text-[11px] text-slate-500 truncate">Available tool runs</p>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-subtle space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-bold uppercase tracking-wider">YouTube Channel</span>
            <Tv className="w-4 h-4 text-red-600" />
          </div>
          <p className="text-sm font-bold text-slate-900 truncate mt-1">
            {ytStatus.connected ? ytStatus.channel_title : 'Not Connected'}
          </p>
          <p className="text-[11px] text-slate-500 truncate">
            {ytStatus.connected ? 'Read-only access' : 'Connect via Google'}
          </p>
        </div>
      </div>

      {/* YouTube Connection Card */}
      <div className="p-5 sm:p-6 rounded-3xl bg-white border border-slate-200/80 shadow-card flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-start sm:items-center gap-4 min-w-0">
          <div className="w-12 h-12 rounded-2xl bg-red-50 border border-red-100 text-red-600 flex items-center justify-center shrink-0 shadow-sm">
            <Tv className="w-6 h-6" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-bold text-slate-900 text-sm sm:text-base">YouTube Channel Integration</h3>
              {ytStatus.connected ? (
                <span className="px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-semibold flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" /> Connected
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-xs font-medium border border-slate-200">
                  Disconnected
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
              {ytStatus.connected
                ? `Authorized channel "${ytStatus.channel_title}" (${ytStatus.google_email || 'Google Account'}). Tokens stored securely.`
                : 'Connect your channel via Google OAuth to audit your private uploads and channel retention stats.'}
            </p>
          </div>
        </div>

        <div className="shrink-0 w-full sm:w-auto">
          {ytStatus.connected ? (
            <Link
              to="/profile"
              className="w-full sm:w-auto justify-center px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors flex items-center gap-1.5"
            >
              Manage Connection <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          ) : (
            <button
              onClick={handleConnectYouTube}
              className="w-full sm:w-auto justify-center px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 active:bg-red-800 text-white font-bold text-xs shadow-sm flex items-center gap-2 transition-all hover:shadow"
            >
              <Tv className="w-4 h-4" /> Connect YouTube
            </button>
          )}
        </div>
      </div>

      {/* Creator Tools Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900">Creator Growth Toolkit</h2>
            <p className="text-xs text-slate-500">Every tool run costs exactly 1 credit.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
          <Link
            to="/tools/seo-score"
            className="p-5 sm:p-6 rounded-3xl bg-white border border-slate-200/80 shadow-subtle hover:shadow-card-hover hover:border-indigo-200 transition-all group relative flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-2xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center font-bold group-hover:scale-105 transition-transform shadow-sm">
                  <Gauge className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100">
                  50 Pts
                </span>
              </div>
              <h3 className="font-bold text-slate-900 text-sm sm:text-base group-hover:text-indigo-600 transition-colors flex items-center justify-between">
                SEO Score Tool
                <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 transition-colors" />
              </h3>
              <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                50-point algorithmic audit of video titles, descriptions, tag density, and keyword overlap.
              </p>
            </div>
          </Link>

          <Link
            to="/tools/video-analyzer"
            className="p-5 sm:p-6 rounded-3xl bg-white border border-slate-200/80 shadow-subtle hover:shadow-card-hover hover:border-purple-200 transition-all group relative flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-2xl bg-purple-50 border border-purple-100 text-purple-600 flex items-center justify-center font-bold group-hover:scale-105 transition-transform shadow-sm">
                  <Video className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-100">
                  Live Data
                </span>
              </div>
              <h3 className="font-bold text-slate-900 text-sm sm:text-base group-hover:text-purple-600 transition-colors flex items-center justify-between">
                Video Analyzer
                <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-purple-600 transition-colors" />
              </h3>
              <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                Inspect video stats, engagement rates, tags, duration, and AI title improvement suggestions.
              </p>
            </div>
          </Link>

          <Link
            to="/tools/keyword-tool"
            className="p-5 sm:p-6 rounded-3xl bg-white border border-slate-200/80 shadow-subtle hover:shadow-card-hover hover:border-pink-200 transition-all group relative flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-2xl bg-pink-50 border border-pink-100 text-pink-600 flex items-center justify-center font-bold group-hover:scale-105 transition-transform shadow-sm">
                  <Search className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-pink-50 text-pink-700 border border-pink-100">
                  Search Trends
                </span>
              </div>
              <h3 className="font-bold text-slate-900 text-sm sm:text-base group-hover:text-pink-600 transition-colors flex items-center justify-between">
                Keyword Explorer
                <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-pink-600 transition-colors" />
              </h3>
              <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                Find estimated high-volume search terms, long-tail clusters, and live YouTube ranking videos.
              </p>
            </div>
          </Link>

          <Link
            to="/tools/trend-analyzer"
            className="p-5 sm:p-6 rounded-3xl bg-white border border-slate-200/80 shadow-subtle hover:shadow-card-hover hover:border-cyan-200 transition-all group relative flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-2xl bg-cyan-50 border border-cyan-100 text-cyan-600 flex items-center justify-center font-bold group-hover:scale-105 transition-transform shadow-sm">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-cyan-50 text-cyan-700 border border-cyan-100">
                  5 Regions
                </span>
              </div>
              <h3 className="font-bold text-slate-900 text-sm sm:text-base group-hover:text-cyan-600 transition-colors flex items-center justify-between">
                Trend Analyzer
                <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-cyan-600 transition-colors" />
              </h3>
              <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                Analyze breakout trends across US, PK, UK, IN, and AE with live tag frequency mapping.
              </p>
            </div>
          </Link>

          <Link
            to="/tools/competitor-analysis"
            className="p-5 sm:p-6 rounded-3xl bg-white border border-slate-200/80 shadow-subtle hover:shadow-card-hover hover:border-amber-200 transition-all group relative flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-2xl bg-amber-50 border border-amber-100 text-amber-600 flex items-center justify-center font-bold group-hover:scale-105 transition-transform shadow-sm">
                  <Users className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-100">
                  Benchmark
                </span>
              </div>
              <h3 className="font-bold text-slate-900 text-sm sm:text-base group-hover:text-amber-600 transition-colors flex items-center justify-between">
                Competitor Insights
                <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-amber-600 transition-colors" />
              </h3>
              <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                Audit public channels, upload frequencies, subscriber metrics, and content opportunities.
              </p>
            </div>
          </Link>

          <Link
            to="/tools/ai-assistant"
            className="p-5 sm:p-6 rounded-3xl bg-white border border-slate-200/80 shadow-subtle hover:shadow-card-hover hover:border-emerald-200 transition-all group relative flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-2xl bg-emerald-50 border border-emerald-100 text-emerald-600 flex items-center justify-center font-bold group-hover:scale-105 transition-transform shadow-sm">
                  <Bot className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100">
                  Groq AI
                </span>
              </div>
              <h3 className="font-bold text-slate-900 text-sm sm:text-base group-hover:text-emerald-600 transition-colors flex items-center justify-between">
                AI Creator Assistant
                <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-600 transition-colors" />
              </h3>
              <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                Generate retention hooks, high-CTR titles, timestamps descriptions, and growth advice.
              </p>
            </div>
          </Link>
        </div>
      </div>

      {/* Recent History Table */}
      <div className="space-y-4 pt-2">
        <div className="flex items-center justify-between">
          <h2 className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
            <HistoryIcon className="w-4 h-4 text-indigo-600" /> Recent Tool Activity
          </h2>
          <Link to="/history" className="text-xs font-semibold text-indigo-600 hover:text-indigo-700">
            View full history &rarr;
          </Link>
        </div>

        {recentHistory.length === 0 ? (
          <div className="p-8 rounded-3xl bg-white border border-slate-200/80 shadow-subtle text-center text-xs text-slate-400">
            No creator tools executed yet. Try the SEO Score Tool above to begin!
          </div>
        ) : (
          <div className="bg-white border border-slate-200/80 rounded-3xl overflow-hidden shadow-subtle divide-y divide-slate-100">
            {recentHistory.map((item) => (
              <div key={item.id} className="p-4 flex items-center justify-between text-xs hover:bg-slate-50/60 transition-colors gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 font-bold border border-indigo-100 text-[11px] shrink-0">
                    {item.tool_type}
                  </span>
                  <span className="text-slate-800 font-medium truncate">
                    {item.input?.title || item.input?.video_url_or_id || item.input?.seed_keyword || item.input?.prompt_type || 'Tool Execution'}
                  </span>
                </div>
                <span className="text-slate-400 text-[11px] shrink-0">
                  {new Date(item.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <RewardAdModal isOpen={isAdModalOpen} onClose={() => setIsAdModalOpen(false)} />
    </div>
  );
};
