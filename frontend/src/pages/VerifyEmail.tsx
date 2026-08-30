import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Mail, CheckCircle2, AlertCircle, Loader2, ArrowRight, Sparkles } from 'lucide-react';
import { api, ApiError } from '../lib/api';
import { useAuth } from '../context/AuthContext';

export const VerifyEmail: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const emailParam = searchParams.get('email');
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();

  const [status, setStatus] = useState<'verifying' | 'success' | 'error' | 'pending'>(
    token ? 'verifying' : 'pending'
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [resendStatus, setResendStatus] = useState<string | null>(null);
  const [resending, setResending] = useState(false);

  useEffect(() => {
    if (!token) return;

    (async () => {
      try {
        await api.post('/api/v1/auth/verify-email', { token });
        setStatus('success');
        await refreshUser();
        setTimeout(() => navigate('/dashboard'), 3500);
      } catch (err: any) {
        setStatus('error');
        if (err instanceof ApiError) {
          setErrorMessage(typeof err.detail === 'string' ? err.detail : 'Verification failed.');
        } else {
          setErrorMessage('Network connection error.');
        }
      }
    })();
  }, [token]);

  const handleResend = async () => {
    setResending(true);
    setResendStatus(null);
    try {
      await api.post('/api/v1/auth/resend-verification', {});
      setResendStatus('Verification link resent successfully! Check your inbox.');
    } catch (err: any) {
      setResendStatus('Failed to resend verification email.');
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-dvh flex flex-col items-center justify-center p-4 sm:p-6 lg:p-8 bg-slate-50 selection:bg-indigo-600 selection:text-white">
      <div className="w-full max-w-[440px] my-auto space-y-6">
        <div className="text-center space-y-2">
          <Link to="/" className="inline-flex items-center gap-2.5 group">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center font-black text-white text-xl shadow-sm group-hover:scale-105 transition-transform">
              P
            </div>
            <span className="text-2xl font-bold tracking-tight text-slate-900 group-hover:text-indigo-600 transition-colors">
              Plexudo
            </span>
          </Link>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Email Verification</h1>
        </div>

        <div className="bg-white border border-slate-200/80 p-6 sm:p-8 shadow-card rounded-3xl space-y-5 text-center">
          {status === 'verifying' && (
            <div className="space-y-4 py-4">
              <Loader2 className="w-10 h-10 text-indigo-600 animate-spin mx-auto" />
              <h2 className="text-lg font-bold text-slate-900">Verifying your email...</h2>
              <p className="text-xs text-slate-500">
                Granting your 3 welcome credits and activating creator features.
              </p>
            </div>
          )}

          {status === 'success' && (
            <div className="space-y-4 py-2">
              <div className="w-12 h-12 rounded-2xl bg-emerald-50 border border-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-sm">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h2 className="text-lg font-bold text-slate-900">Email Verified!</h2>
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-bold mt-1">
                  <Sparkles className="w-3.5 h-3.5" /> +3 Welcome Credits Granted
                </div>
              </div>
              <p className="text-xs text-slate-500">
                Redirecting you to the Creator Studio dashboard in 3 seconds...
              </p>
              <div className="pt-2">
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-sm transition-all"
                >
                  Go to Dashboard Now <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          )}

          {status === 'pending' && (
            <div className="space-y-4 py-2">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center mx-auto shadow-sm">
                <Mail className="w-6 h-6" />
              </div>
              <h2 className="text-lg font-bold text-slate-900">Verify your Email Address</h2>
              <p className="text-xs text-slate-500 leading-relaxed">
                We sent a verification link to{' '}
                <strong className="text-slate-800">{emailParam || user?.email || 'your email'}</strong>. Please click the link to claim your <strong>3 free welcome credits</strong>.
              </p>

              {resendStatus && (
                <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-700 font-medium">
                  {resendStatus}
                </div>
              )}

              <div className="pt-2 flex flex-col gap-2">
                <button
                  onClick={handleResend}
                  disabled={resending}
                  className="w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-sm transition-colors disabled:opacity-50"
                >
                  {resending ? 'Sending...' : 'Resend Verification Email'}
                </button>
                <Link
                  to="/login"
                  className="text-xs text-slate-500 hover:text-slate-800 font-semibold py-1"
                >
                  Return to Sign In
                </Link>
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="space-y-4 py-2">
              <div className="w-12 h-12 rounded-2xl bg-red-50 border border-red-100 text-red-600 flex items-center justify-center mx-auto shadow-sm">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h2 className="text-lg font-bold text-slate-900">Verification Link Expired</h2>
              <p className="text-xs text-slate-500 leading-relaxed">
                {errorMessage || 'This token has already been used or has expired.'}
              </p>
              <div className="pt-2">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-sm transition-all"
                >
                  Return to Sign In
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
