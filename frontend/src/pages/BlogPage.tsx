import React from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, Clock, ArrowRight, Sparkles } from 'lucide-react';

export const BlogPage: React.FC = () => {
  const posts = [
    {
      title: 'Mastering YouTube SEO in 2026: The Definitive 50-Point Audit Guide',
      excerpt: 'Discover how the modern YouTube search algorithm ranks videos by measuring semantic keyword density, triple keyword overlap, and audience engagement retention.',
      readTime: '6 min read',
      category: 'SEO & Ranking',
      date: 'Aug 2026',
    },
    {
      title: 'High-Retention Video Hooks: How to Hook 70%+ of Viewers in the First 15 Seconds',
      excerpt: 'The first 15 seconds determine whether your video explodes or dies. Learn the 3 proven psychological hook structures used by the top 1% of creators.',
      readTime: '5 min read',
      category: 'Growth Strategy',
      date: 'Aug 2026',
    },
    {
      title: 'Long-Tail YouTube Keywords: Finding High-Intent Search Queries With Zero Competition',
      excerpt: 'Stop competing on saturated 1-word keywords. Use intent-based clustering to rank #1 across regional YouTube searches in US, UK, India, Pakistan, and UAE.',
      readTime: '7 min read',
      category: 'Keyword Research',
      date: 'Aug 2026',
    },
  ];

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
            <Link to="/youtube-seo-tool" className="hover:text-indigo-600 transition-colors">SEO Score</Link>
            <Link to="/youtube-video-analyzer" className="hover:text-indigo-600 transition-colors">Video Analyzer</Link>
            <Link to="/youtube-keyword-tool" className="hover:text-indigo-600 transition-colors">Keywords</Link>
            <Link to="/youtube-trend-analyzer" className="hover:text-indigo-600 transition-colors">Trends</Link>
            <Link to="/youtube-competitor-analysis" className="hover:text-indigo-600 transition-colors">Competitors</Link>
            <Link to="/blog" className="text-indigo-600 font-bold">Blog</Link>
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

      {/* Hero Header */}
      <section className="pt-8 pb-10 bg-white border-b border-slate-200/80">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center space-y-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-[11px] font-bold">
            <BookOpen className="w-3.5 h-3.5" />
            <span>Plexudo Creator Academy</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            YouTube Growth Guides & Algorithm Insights
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 max-w-lg mx-auto">
            Actionable, data-backed tutorials on YouTube SEO, CTR optimization, retention hooks, and keyword strategy.
          </p>
        </div>
      </section>

      {/* Blog Cards */}
      <section className="py-10 max-w-4xl mx-auto px-4 sm:px-6 space-y-6 flex-grow">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {posts.map((post, idx) => (
            <article key={idx} className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-subtle hover:shadow-card hover:border-indigo-200 transition-all flex flex-col justify-between">
              <div className="space-y-2.5">
                <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium">
                  <span className="text-indigo-600 font-bold bg-indigo-50 px-2 py-0.5 rounded-md">{post.category}</span>
                  <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {post.readTime}</span>
                </div>
                <h2 className="text-sm font-bold text-slate-900 hover:text-indigo-600 transition-colors leading-snug">
                  {post.title}
                </h2>
                <p className="text-xs text-slate-500 leading-relaxed">
                  {post.excerpt}
                </p>
              </div>

              <Link
                to="/signup"
                className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-indigo-600 hover:text-indigo-700 group"
              >
                <span>Read Full Guide</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </Link>
            </article>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200/80 bg-white mt-auto py-8">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row justify-between items-center text-xs text-slate-400 gap-4">
          <p>&copy; 2026 Plexudo. Creator Academy. Zero fake data.</p>
          <div className="flex gap-4">
            <Link to="/" className="hover:text-indigo-600">Home</Link>
            <Link to="/login" className="hover:text-indigo-600">Sign In</Link>
            <Link to="/signup" className="hover:text-indigo-600">Claim 3 Credits</Link>
          </div>
        </div>
      </footer>
    </div>
  );
};
