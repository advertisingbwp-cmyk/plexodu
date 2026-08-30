import React from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart3,
  Video,
  Search,
  TrendingUp,
  Users,
  Sparkles,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';

interface PublicToolPageProps {
  tool: 'seo' | 'video' | 'keyword' | 'trend' | 'competitor';
}

export const PublicToolPage: React.FC<PublicToolPageProps> = ({ tool }) => {
  const toolDetails = {
    seo: {
      title: 'YouTube 50-Point SEO Score Tool',
      badge: 'Algorithmic Optimization',
      icon: <BarChart3 className="w-8 h-8 text-indigo-600" />,
      tagline: 'Audit your YouTube video SEO against 50 ranking factors before you hit publish.',
      features: [
        'Title optimization: keyword density, length, and power words',
        'Description depth: search query placement and link structure',
        'Tag density: triple keyword overlap and search relevance',
        'Algorithmic score from 0 to 50 with actionable recommendations',
      ],
      ctaText: 'Audit Video SEO Free (3 Welcome Credits)',
    },
    video: {
      title: 'YouTube Video Performance Analyzer',
      badge: 'Video Metrics & Tags',
      icon: <Video className="w-8 h-8 text-purple-600" />,
      tagline: 'Extract hidden tags, evaluate engagement rates, and get AI title optimizations.',
      features: [
        'Live YouTube Data API v3 views, likes, and comment metrics',
        'Calculated engagement rate benchmarking',
        'Hidden video tags extractor with one-click copy',
        'Groq AI title rewrite suggestions with predicted CTR',
      ],
      ctaText: 'Analyze Video Free (3 Welcome Credits)',
    },
    keyword: {
      title: 'YouTube Keyword Discovery & Rank Explorer',
      badge: 'Search Volume & Intent',
      icon: <Search className="w-8 h-8 text-pink-600" />,
      tagline: 'Uncover high-intent creator keywords with zero fluff and estimated search volume.',
      features: [
        'Estimated monthly search query intent scores',
        'Long-tail variation clustering for niche ranking',
        'Top ranking competitor video benchmarks',
        'Real-time keyword suggestions from YouTube autocomplete',
      ],
      ctaText: 'Explore Keywords Free (3 Welcome Credits)',
    },
    trend: {
      title: 'YouTube Regional Trend Analyzer',
      badge: 'Market Intelligence',
      icon: <TrendingUp className="w-8 h-8 text-cyan-600" />,
      tagline: 'Track breakout videos, trending tags, and viral formats across 5 creator markets.',
      features: [
        'Market tracking for US, Pakistan, UK, India, and UAE',
        'Breakout tag frequency and momentum score',
        'Top 10 trending videos in each creator region',
        'Category breakdown across Gaming, Education, Tech, and Entertainment',
      ],
      ctaText: 'Track Trends Free (3 Welcome Credits)',
    },
    competitor: {
      title: 'YouTube Competitor Benchmark Tool',
      badge: 'Channel Auditing',
      icon: <Users className="w-8 h-8 text-amber-600" />,
      tagline: 'Benchmark your channel against rival creators with deep public channel audits.',
      features: [
        'Lifetime views, subscriber milestones, and video counts',
        'Estimated upload cadence and average views per video',
        'Audit recent top-performing uploads and tags',
        'Direct side-by-side performance comparison',
      ],
      ctaText: 'Benchmark Competitors (3 Welcome Credits)',
    },
  }[tool];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col antialiased selection:bg-indigo-600 selection:text-white">
      {/* Top Header */}
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
            <Link to="/youtube-seo-tool" className={`hover:text-indigo-600 transition-colors ${tool === 'seo' ? 'text-indigo-600 font-bold' : ''}`}>SEO Score</Link>
            <Link to="/youtube-video-analyzer" className={`hover:text-indigo-600 transition-colors ${tool === 'video' ? 'text-indigo-600 font-bold' : ''}`}>Video Analyzer</Link>
            <Link to="/youtube-keyword-tool" className={`hover:text-indigo-600 transition-colors ${tool === 'keyword' ? 'text-indigo-600 font-bold' : ''}`}>Keywords</Link>
            <Link to="/youtube-trend-analyzer" className={`hover:text-indigo-600 transition-colors ${tool === 'trend' ? 'text-indigo-600 font-bold' : ''}`}>Trends</Link>
            <Link to="/youtube-competitor-analysis" className={`hover:text-indigo-600 transition-colors ${tool === 'competitor' ? 'text-indigo-600 font-bold' : ''}`}>Competitors</Link>
            <Link to="/blog" className="hover:text-indigo-600 transition-colors">Blog</Link>
          </nav>

          <div className="flex items-center gap-2 shrink-0">
            <Link to="/login" className="px-3 py-1.5 text-xs font-bold text-slate-700 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition-all">
              Sign In
            </Link>
            <Link to="/signup" className="px-3.5 py-1.5 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm transition-all hover:shadow">
              Get 3 Free Credits
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-12 sm:py-16 bg-white border-b border-slate-200/80">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-bold shadow-sm">
            <Sparkles className="w-3.5 h-3.5" />
            <span>{toolDetails.badge}</span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
            {toolDetails.title}
          </h1>

          <p className="text-xs sm:text-sm text-slate-600 max-w-xl mx-auto leading-relaxed">
            {toolDetails.tagline}
          </p>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/signup"
              className="w-full sm:w-auto px-6 py-3 text-xs sm:text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-md shadow-indigo-600/20 transition-all hover:scale-105 flex items-center justify-center gap-2"
            >
              <span>{toolDetails.ctaText}</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/login"
              className="w-full sm:w-auto px-6 py-3 text-xs sm:text-sm font-bold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200/80 rounded-xl shadow-sm transition-all"
            >
              Sign In to Existing Account
            </Link>
          </div>
        </div>
      </section>

      {/* Features List */}
      <section className="py-10 max-w-3xl mx-auto px-4 sm:px-6 space-y-6 flex-grow">
        <h2 className="text-lg font-bold text-slate-900 text-center">
          What This Tool Analyzes
        </h2>
        <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-subtle space-y-3.5">
          {toolDetails.features.map((feature, idx) => (
            <div key={idx} className="flex items-start gap-3 text-xs sm:text-sm text-slate-700">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span>{feature}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200/80 bg-white mt-auto py-8">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row justify-between items-center text-xs text-slate-400 gap-4">
          <p>&copy; 2026 Plexudo. Powered by YouTube Data API v3 & Groq AI.</p>
          <div className="flex gap-4">
            <Link to="/" className="hover:text-indigo-600">Home</Link>
            <Link to="/blog" className="hover:text-indigo-600">Blog</Link>
            <Link to="/login" className="hover:text-indigo-600">Sign In</Link>
          </div>
        </div>
      </footer>
    </div>
  );
};
