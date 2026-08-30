import React from 'react';
import { Link } from 'react-router-dom';

interface LegalPageProps {
  type: 'privacy' | 'terms';
}

export const LegalPage: React.FC<LegalPageProps> = ({ type }) => {
  const isPrivacy = type === 'privacy';

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

      {/* Content */}
      <main className="flex-1 max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14 space-y-6 w-full">
        <div className="space-y-1">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {isPrivacy ? 'Privacy Policy' : 'Terms of Service'}
          </h1>
          <p className="text-xs text-slate-500">Last updated: August 2026</p>
        </div>

        <div className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-card text-xs text-slate-600 leading-relaxed space-y-6">
          {isPrivacy ? (
            <>
              <section className="space-y-2">
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">1. Closed-App Security Architecture</h2>
                <p>
                  Plexudo operates under a strict Closed-App privacy model. Private user data, YouTube API responses, Groq AI generations, and OAuth credentials are never rendered on public crawlable pages or indexed by search engines.
                </p>
              </section>

              <section className="space-y-2">
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">2. Google OAuth & YouTube Data</h2>
                <p>
                  When you connect your YouTube channel, Plexudo requests read-only permissions to audit your channel metadata and statistics. We encrypt all access tokens and refresh tokens at rest using AES-128 Fernet cryptography. Tokens are never exposed to client-side code, cookies, or public APIs.
                </p>
              </section>

              <section className="space-y-2">
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">3. Information We Collect</h2>
                <p>
                  We collect your email address, username, and Argon2id-hashed passwords for authentication purposes. We never store plain-text passwords.
                </p>
              </section>

              <section className="space-y-2">
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">4. Third-Party Disclosures</h2>
                <p>
                  We do not sell, rent, or trade your personal information or YouTube channel analytics with any third-party advertisers or data brokers.
                </p>
              </section>
            </>
          ) : (
            <>
              <section className="space-y-2">
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">1. Platform Overview</h2>
                <p>
                  Plexudo provides algorithmic YouTube SEO scoring, video analytics, keyword clustering, and AI-assisted content optimization. The platform operates on a credits-based monetization model with zero recurring subscription fees.
                </p>
              </section>

              <section className="space-y-2">
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">2. Credits & Monetization Invariants</h2>
                <p>
                  Every new user receives 3 free welcome credits upon completing email verification. Users can earn additional credits (+1 per verified view) by engaging with sponsor advertisements. Credits are managed authoritatively by server ledger transactions.
                </p>
              </section>

              <section className="space-y-2">
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">3. YouTube API Compliance</h2>
                <p>
                  Plexudo uses the official YouTube Data API v3 and complies with all Google API Services User Data Policies. Plexudo is an independent software tool and is not officially affiliated with Google LLC or YouTube.
                </p>
              </section>
            </>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200/80 bg-white py-6 text-center text-xs text-slate-500">
        <div className="max-w-5xl mx-auto px-4 flex flex-col sm:flex-row justify-between items-center gap-3">
          <p>&copy; 2026 Plexudo. All rights reserved.</p>
          <div className="flex gap-4">
            <Link to="/privacy" className="hover:text-slate-700">Privacy Policy</Link>
            <Link to="/terms" className="hover:text-slate-700">Terms of Service</Link>
          </div>
        </div>
      </footer>
    </div>
  );
};
