import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Loader2, CheckCircle2, AlertCircle, ArrowRight, Tv } from 'lucide-react';
import { api, ApiError } from '../lib/api';
import { useAuth } from '../context/AuthContext';

export const YouTubeCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const errorParam = searchParams.get('error');

  const navigate = useNavigate();
  const { refreshUser } = useAuth();

  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (errorParam) {
      setStatus('error');
      setErrorMessage(`Google authorization error: ${errorParam}`);
      return;
    }

    if (!code || !state) {
      setStatus('error');
      setErrorMessage('Missing OAuth authorization code or state parameter.');
      return;
    }

    (async () => {
      try {
        await api.get(`/api/v1/youtube/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`);
        setStatus('success');
        await refreshUser();
        setTimeout(() => navigate('/dashboard'), 2500);
      } catch (err: any) {
        setStatus('error');
        if (err instanceof ApiError) {
          setErrorMessage(typeof err.detail === 'string' ? err.detail : 'Failed to complete YouTube connection.');
        } else {
          setErrorMessage('Network connection error during OAuth exchange.');
        }
      }
    })();
  }, [code, state, errorParam]);

  return (
    <div className="min-h-dvh flex flex-col items-center justify-center p-4 sm:p-6 lg:p-8 bg-slate-50 selection:bg-indigo-600 selection:text-white">
      <div className="w-full max-w-[420px] my-auto space-y-6">
        <div className="text-center space-y-2">
          <Link to="/" className="inline-flex items-center gap-2.5 group">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center font-black text-white text-xl shadow-sm group-hover:scale-105 transition-transform">
              P
            </div>
            <span className="text-2xl font-bold tracking-tight text-slate-900 group-hover:text-indigo-600 transition-colors">
              Plexudo
            </span>
          </Link>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">YouTube Channel Link</h1>
        </div>

        <div className="bg-white border border-slate-200/80 p-6 sm:p-8 shadow-card rounded-3xl space-y-5 text-center">
          {status === 'processing' && (
            <div className="space-y-4 py-4">
              <Loader2 className="w-10 h-10 text-indigo-600 animate-spin mx-auto" />
              <h2 className="text-lg font-bold text-slate-900">Exchanging Tokens...</h2>
              <p className="text-xs text-slate-500">
                Encrypting OAuth tokens and caching channel metadata.
              </p>
            </div>
          )}

          {status === 'success' && (
            <div className="space-y-4 py-2">
              <div className="w-12 h-12 rounded-2xl bg-emerald-50 border border-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-sm">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h2 className="text-lg font-bold text-slate-900">YouTube Channel Connected!</h2>
              <p className="text-xs text-slate-500">
                Your channel analytics are now integrated. Redirecting to dashboard...
              </p>
              <div className="pt-2">
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-sm transition-all"
                >
                  Go to Dashboard <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="space-y-4 py-2">
              <div className="w-12 h-12 rounded-2xl bg-red-50 border border-red-100 text-red-600 flex items-center justify-center mx-auto shadow-sm">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h2 className="text-lg font-bold text-slate-900">Authorization Failed</h2>
              <p className="text-xs text-slate-500 leading-relaxed">
                {errorMessage || 'Google OAuth failed to authorize your YouTube channel.'}
              </p>
              <div className="pt-2">
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-sm transition-all"
                >
                  Return to Dashboard
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
