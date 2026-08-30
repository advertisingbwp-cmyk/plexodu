import React from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  ArrowRight,
  TrendingUp,
  Search,
  Video,
  BarChart3,
  Users,
  Bot,
  Gift,
  ShieldCheck,
  Zap,
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col antialiased selection:bg-indigo-600 selection:text-white">
      {/* Top Navigation */}
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200/80 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 sm:h-16 flex items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2 group shrink-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white font-extrabold text-base shadow-sm">
              P
            </div>
            <span className="text-lg sm:text-xl font-bold tracking-tight text-slate-900 group-hover:text-indigo-600 transition-colors">
              Plexudo
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-4 lg:gap-6 text-xs sm:text-sm font-semibold text-slate-600">
            <Link to="/youtube-seo-tool" className="hover:text-indigo-600 transition-colors">SEO Score</Link>
            <Link to="/youtube-video-analyzer" className="hover:text-indigo-600 transition-colors">Video Analyzer</Link>
            <Link to="/youtube-keyword-tool" className="hover:text-indigo-600 transition-colors">Keywords</Link>
            <Link to="/youtube-trend-analyzer" className="hover:text-indigo-600 transition-colors">Trends</Link>
            <Link to="/youtube-competitor-analysis" className="hover:text-indigo-600 transition-colors">Competitors</Link>
            <Link to="/blog" className="hover:text-indigo-600 transition-colors">Blog</Link>
          </nav>

          <div className="flex items-center gap-2 shrink-0">
            <Link
              to="/login"
              className="px-3 py-1.5 text-xs font-bold text-slate-700 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition-all"
            >
              Sign In
            </Link>
            <Link
              to="/signup"
              className="px-3.5 py-1.5 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm transition-all hover:shadow hover:scale-105"
            >
              Get 3 Free Credits
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-8 pb-10 sm:pt-14 sm:pb-14 border-b border-slate-200/80 bg-gradient-to-b from-white to-slate-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center relative z-10 space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-[11px] font-bold shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>The Next-Gen Creator Growth Toolkit</span>
          </div>

          <h1 className="text-2xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900 leading-tight">
            Stop Guessing YouTube SEO.<br />
            <span className="text-indigo-600">Audit & Grow with Real Data.</span>
          </h1>

          <p className="text-xs sm:text-sm text-slate-600 max-w-lg mx-auto leading-relaxed">
            Get instant 50-point algorithmic audits, discover high-volume keywords, track breakout regional trends, and benchmark competitors. Zero fake data.
          </p>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/signup"
              className="w-full sm:w-auto px-6 py-2.5 text-xs sm:text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-md shadow-indigo-600/20 transition-all hover:scale-105 flex items-center justify-center gap-2"
            >
              <span>Claim 3 Free Credits</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/youtube-seo-tool"
              className="w-full sm:w-auto px-6 py-2.5 text-xs sm:text-sm font-bold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200/80 rounded-xl shadow-sm transition-all text-center"
            >
              Explore SEO Score Tool
            </Link>
          </div>
        </div>
      </section>

      {/* Tools Grid Showcase */}
      <section className="py-10 sm:py-12 bg-slate-50 flex-grow">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 space-y-6 sm:space-y-8">
          <div className="text-center space-y-1.5 max-w-xl mx-auto">
            <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
              Everything You Need to Scale Your Channel
            </h2>
            <p className="text-xs text-slate-500">
              Five purpose-built tools powered by the YouTube Data API v3 and Groq AI.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            <Link
              to="/youtube-seo-tool"
              className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-subtle hover:shadow-card hover:border-indigo-200 transition-all group flex flex-col justify-between"
            >
              <div>
                <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center mb-3 shadow-sm">
                  <BarChart3 className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
                  50-Point SEO Score
                </h3>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  Evaluates title optimization, description depth, tag density, search keyword volume, and triple keyword overlap.
                </p>
              </div>
            </Link>

            <Link
              to="/youtube-video-analyzer"
              className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-subtle hover:shadow-card hover:border-purple-200 transition-all group flex flex-col justify-between"
            >
              <div>
                <div className="w-9 h-9 rounded-xl bg-purple-50 border border-purple-100 text-purple-600 flex items-center justify-center mb-3 shadow-sm">
                  <Video className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 group-hover:text-purple-600 transition-colors">
                  Video Analyzer
                </h3>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  Inspect view count, likes, engagement percentage, extracted video tags, and AI title improvement recommendations.
                </p>
              </div>
            </Link>

            <Link
              to="/youtube-keyword-tool"
              className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-subtle hover:shadow-card hover:border-pink-200 transition-all group flex flex-col justify-between"
            >
              <div>
                <div className="w-9 h-9 rounded-xl bg-pink-50 border border-pink-100 text-pink-600 flex items-center justify-center mb-3 shadow-sm">
                  <Search className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 group-hover:text-pink-600 transition-colors">
                  Keyword Explorer
                </h3>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  Uncover estimated high-intent search volumes, long-tail query clusters, and live top-ranking competitor videos.
                </p>
              </div>
            </Link>

            <Link
              to="/youtube-trend-analyzer"
              className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-subtle hover:shadow-card hover:border-cyan-200 transition-all group flex flex-col justify-between"
            >
              <div>
                <div className="w-9 h-9 rounded-xl bg-cyan-50 border border-cyan-100 text-cyan-600 flex items-center justify-center mb-3 shadow-sm">
                  <TrendingUp className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 group-hover:text-cyan-600 transition-colors">
                  Trend Analyzer
                </h3>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  Map breakout tags and viral trends across 5 key creator markets: US, Pakistan, UK, India, and UAE.
                </p>
              </div>
            </Link>

            <Link
              to="/youtube-competitor-analysis"
              className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-subtle hover:shadow-card hover:border-amber-200 transition-all group flex flex-col justify-between"
            >
              <div>
                <div className="w-9 h-9 rounded-xl bg-amber-50 border border-amber-100 text-amber-600 flex items-center justify-center mb-3 shadow-sm">
                  <Users className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 group-hover:text-amber-600 transition-colors">
                  Competitor Benchmark
                </h3>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  Audit public channels, upload frequency, total lifetime views, subscriber metrics, and recent video uploads.
                </p>
              </div>
            </Link>

            <div className="p-5 rounded-2xl bg-gradient-to-br from-indigo-50 via-white to-purple-50 border border-indigo-200/80 shadow-subtle flex flex-col justify-between">
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold text-indigo-700 uppercase tracking-wider bg-indigo-100/80 px-2.5 py-0.5 rounded-full inline-block">
                  Ad-Supported Credits
                </span>
                <h3 className="text-sm font-bold text-slate-900">Zero Subscriptions</h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Claim 3 welcome credits on verification. Earn +1 credit anytime with 5-second verified sponsor ads.
                </p>
              </div>
              <Link
                to="/signup"
                className="mt-3 inline-block w-full text-center py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-sm transition-all"
              >
                Get Started Free &rarr;
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200/80 bg-white mt-auto">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6 mb-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-indigo-600 text-white font-extrabold text-xs flex items-center justify-center">
                  P
                </div>
                <span className="font-bold text-base text-slate-900">Plexudo</span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                The ultimate YouTube growth suite for creators. Real Data API metrics, 50-point algorithmic SEO scoring, and AI assistance with zero fake data.
              </p>
            </div>
            <div>
              <h3 className="text-[11px] font-bold text-slate-900 uppercase tracking-wider mb-2.5">Creator Tools</h3>
              <ul className="space-y-1.5 text-xs font-medium text-slate-500">
                <li><Link to="/youtube-seo-tool" className="hover:text-indigo-600">YouTube SEO Tool</Link></li>
                <li><Link to="/youtube-video-analyzer" className="hover:text-indigo-600">Video Analyzer</Link></li>
                <li><Link to="/youtube-keyword-tool" className="hover:text-indigo-600">Keyword Explorer</Link></li>
                <li><Link to="/youtube-trend-analyzer" className="hover:text-indigo-600">Trend Analyzer</Link></li>
                <li><Link to="/youtube-competitor-analysis" className="hover:text-indigo-600">Competitor Insights</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-[11px] font-bold text-slate-900 uppercase tracking-wider mb-2.5">Resources</h3>
              <ul className="space-y-1.5 text-xs font-medium text-slate-500">
                <li><Link to="/blog" className="hover:text-indigo-600">Creator Blog</Link></li>
                <li><Link to="/dashboard" className="hover:text-indigo-600">Creator Dashboard</Link></li>
                <li><Link to="/login" className="hover:text-indigo-600">Account Login</Link></li>
                <li><Link to="/signup" className="hover:text-indigo-600">Claim 3 Free Credits</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-[11px] font-bold text-slate-900 uppercase tracking-wider mb-2.5">Legal</h3>
              <ul className="space-y-1.5 text-xs font-medium text-slate-500">
                <li><Link to="/privacy" className="hover:text-indigo-600">Privacy Policy</Link></li>
                <li><Link to="/terms" className="hover:text-indigo-600">Terms of Service</Link></li>
              </ul>
              <p className="text-[10px] text-slate-400 mt-3 leading-tight">
                Plexudo is not affiliated with Google or YouTube. YouTube is a registered trademark of Google LLC.
              </p>
            </div>
          </div>
          <div className="border-t border-slate-100 pt-5 flex flex-col sm:flex-row justify-between items-center text-[11px] text-slate-400 gap-3">
            <p>&copy; 2026 Plexudo. All rights reserved. Zero fake data.</p>
            <div className="flex gap-5 font-medium">
              <Link to="/privacy" className="hover:text-slate-600">Privacy</Link>
              <Link to="/terms" className="hover:text-slate-600">Terms</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};
