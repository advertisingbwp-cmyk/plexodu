import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Sparkles, LogOut, User as UserIcon, AlertTriangle, CheckCircle, Menu, X } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { RewardAdModal } from './RewardAdModal';
import { api } from '../lib/api';

interface NavbarProps {
  onMobileMenuToggle?: () => void;
  isMobileMenuOpen?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ onMobileMenuToggle, isMobileMenuOpen }) => {
  const { user, credits, logout } = useAuth();
  const navigate = useNavigate();
  const [isAdModalOpen, setIsAdModalOpen] = useState(false);
  const [resendStatus, setResendStatus] = useState<string | null>(null);

  const handleResendVerification = async () => {
    try {
      await api.post('/api/v1/auth/resend-verification');
      setResendStatus('Verification email sent! Check your inbox.');
      setTimeout(() => setResendStatus(null), 5000);
    } catch {
      setResendStatus('Failed to resend. Please try again later.');
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <>
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200/80 shadow-subtle">
        {/* Email verification alert banner if unverified */}
        {user && !user.email_verified && (
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-xs flex items-center justify-between text-amber-900">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>
                Please verify your email address (<strong>{user.email}</strong>) to unlock all creator tools.
              </span>
            </div>
            <div className="flex items-center gap-3">
              {resendStatus ? (
                <span className="text-emerald-700 font-semibold flex items-center gap-1">
                  <CheckCircle className="w-3.5 h-3.5" /> {resendStatus}
                </span>
              ) : (
                <button
                  onClick={handleResendVerification}
                  className="font-bold underline hover:text-amber-950 transition-colors"
                >
                  Resend Verification
                </button>
              )}
            </div>
          </div>
        )}

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Mobile Menu Button */}
            <button
              onClick={onMobileMenuToggle}
              className="p-2 -ml-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 md:hidden transition-colors"
              aria-label="Toggle navigation menu"
            >
              {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>

            <Link to="/dashboard" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center font-black text-white text-base shadow-sm group-hover:scale-105 transition-transform">
                P
              </div>
              <span className="text-lg font-bold tracking-tight text-slate-900 group-hover:text-indigo-600 transition-colors">
                Plexudo
              </span>
              <span className="hidden sm:inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-600 border border-slate-200">
                Studio
              </span>
            </Link>
          </div>

          <div className="flex items-center gap-3 sm:gap-4">
            {/* Authoritative Server Credit Balance */}
            <div className="flex items-center gap-2 bg-indigo-50/80 border border-indigo-200/60 rounded-xl px-3 py-1.5">
              <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              <span className="text-xs font-medium text-indigo-900 hidden sm:inline">Credits:</span>
              <span className="text-sm font-bold text-indigo-700 tracking-wide">{credits}</span>
            </div>

            {/* Rewarded Ad Trigger Button */}
            <button
              onClick={() => setIsAdModalOpen(true)}
              className="px-3.5 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 rounded-xl shadow-sm flex items-center gap-1.5 transition-all hover:shadow"
            >
              <Sparkles className="w-3.5 h-3.5" /> <span className="hidden xs:inline">Earn</span> Free Credits
            </button>

            {/* Profile Info & Actions */}
            {user && (
              <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
                <Link
                  to="/profile"
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                >
                  <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-xs">
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                  <span className="hidden md:inline">{user.username}</span>
                </Link>
                <button
                  onClick={handleLogout}
                  title="Log out"
                  className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                  aria-label="Log out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <RewardAdModal isOpen={isAdModalOpen} onClose={() => setIsAdModalOpen(false)} />
    </>
  );
};
