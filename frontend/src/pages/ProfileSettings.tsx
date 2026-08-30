import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api, ApiError } from '../lib/api';
import {
  User,
  Shield,
  Tv,
  CheckCircle,
  AlertTriangle,
  Loader2,
  Lock,
  ExternalLink,
  LogOut,
  Sparkles,
  Eye,
  EyeOff,
} from 'lucide-react';
import { RewardAdModal } from '../components/RewardAdModal';

export const ProfileSettings: React.FC = () => {
  const { user, credits, logout, refreshUser } = useAuth();

  const [username, setUsername] = useState(user?.username || '');
  const [isUpdatingUsername, setIsUpdatingUsername] = useState(false);
  const [usernameSuccess, setUsernameSuccess] = useState(false);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const [ytStatus, setYtStatus] = useState<{
    connected: boolean;
    channel_title?: string;
    channel_id?: string;
    channel_avatar_url?: string;
    google_email?: string;
  }>({ connected: false });
  const [isDisconnectingYt, setIsDisconnectingYt] = useState(false);
  const [isAdModalOpen, setIsAdModalOpen] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get<any>('/api/v1/youtube/status');
        setYtStatus(res);
      } catch {
        // Ignored
      }
    })();
  }, []);

  const handleUpdateUsername = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdatingUsername(true);
    setUsernameSuccess(false);

    try {
      await api.patch('/api/v1/profile/', { username });
      setUsernameSuccess(true);
      await refreshUser();
      setTimeout(() => setUsernameSuccess(false), 4000);
    } catch (err: any) {
      alert(err.detail || 'Failed to update username');
    } finally {
      setIsUpdatingUsername(false);
    }
  };

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(false);

    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match.');
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters.');
      return;
    }

    setIsUpdatingPassword(true);
    try {
      await api.post('/api/v1/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setPasswordSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setPasswordSuccess(false), 4000);
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setPasswordError('Current password is incorrect.');
        } else {
          setPasswordError(typeof err.detail === 'string' ? err.detail : 'Failed to change password.');
        }
      } else {
        setPasswordError('Network error. Please try again.');
      }
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  const handleConnectYouTube = async () => {
    try {
      const res = await api.get<{ url: string }>('/api/v1/youtube/connect');
      window.location.href = res.url;
    } catch (err: any) {
      alert(err.detail || 'Failed to connect YouTube');
    }
  };

  const handleDisconnectYouTube = async () => {
    if (!confirm('Are you sure you want to disconnect your YouTube channel?')) return;
    setIsDisconnectingYt(true);
    try {
      await api.delete('/api/v1/youtube/disconnect');
      setYtStatus({ connected: false });
    } catch (err: any) {
      alert(err.detail || 'Failed to disconnect YouTube');
    } finally {
      setIsDisconnectingYt(false);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Page Header */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border border-slate-200/80 shadow-card flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Profile & Workspace Settings
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 max-w-xl">
            Manage your creator identity, security credentials, credit balance, and linked YouTube channel.
          </p>
        </div>
      </div>

      {/* Account & Credits Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-subtle space-y-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Email Status</span>
          <p className="text-sm font-bold text-slate-900 truncate">{user?.email}</p>
          <p className="text-xs">
            {user?.email_verified ? (
              <span className="text-emerald-600 font-semibold flex items-center gap-1">
                <CheckCircle className="w-3.5 h-3.5" /> Verified Account
              </span>
            ) : (
              <span className="text-amber-600 font-semibold flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" /> Unverified
              </span>
            )}
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-subtle space-y-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Credit Balance</span>
          <p className="text-2xl font-black text-indigo-700">{credits}</p>
          <button
            onClick={() => setIsAdModalOpen(true)}
            className="text-xs text-indigo-600 hover:text-indigo-700 font-bold flex items-center gap-1"
          >
            <Sparkles className="w-3 h-3" /> Earn free credits &rarr;
          </button>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-subtle space-y-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">YouTube Channel</span>
          <p className="text-sm font-bold text-slate-900 truncate">
            {ytStatus.connected ? ytStatus.channel_title : 'None Connected'}
          </p>
          <p className="text-xs">
            {ytStatus.connected ? (
              <span className="text-emerald-600 font-semibold flex items-center gap-1">
                <CheckCircle className="w-3.5 h-3.5" /> Active Integration
              </span>
            ) : (
              <span className="text-slate-400 font-medium">Disconnected</span>
            )}
          </p>
        </div>
      </div>

      {/* YouTube Connection Manager */}
      <div className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-card space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-red-50 border border-red-100 text-red-600 flex items-center justify-center shadow-sm">
            <Tv className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">YouTube Account Authorization</h2>
            <p className="text-xs text-slate-500">
              Grant Plexudo read-only permissions to audit your channel metrics. Tokens are encrypted at rest.
            </p>
          </div>
        </div>

        {ytStatus.connected ? (
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/60 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              {ytStatus.channel_avatar_url ? (
                <img
                  src={ytStatus.channel_avatar_url}
                  alt={ytStatus.channel_title}
                  className="w-12 h-12 rounded-full border border-slate-200 shadow-sm"
                />
              ) : (
                <div className="w-12 h-12 rounded-full bg-red-100 text-red-700 font-bold flex items-center justify-center text-base">
                  YT
                </div>
              )}
              <div>
                <p className="font-bold text-slate-900 text-sm">{ytStatus.channel_title}</p>
                <p className="text-xs text-slate-500">
                  Google Account: {ytStatus.google_email || 'Linked'} (Channel ID: {ytStatus.channel_id || '—'})
                </p>
              </div>
            </div>
            <button
              onClick={handleDisconnectYouTube}
              disabled={isDisconnectingYt}
              className="px-4 py-2 rounded-xl bg-red-50 hover:bg-red-100 text-red-700 text-xs font-bold transition-colors border border-red-200/60 shrink-0"
            >
              {isDisconnectingYt ? 'Disconnecting...' : 'Disconnect Channel'}
            </button>
          </div>
        ) : (
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/60 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs text-slate-600">
              No YouTube channel currently linked. Connect to analyze your private channel performance.
            </p>
            <button
              onClick={handleConnectYouTube}
              className="px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 active:bg-red-800 text-white font-bold text-xs shadow-sm flex items-center gap-2 transition-all shrink-0"
            >
              <Tv className="w-4 h-4" /> Connect YouTube Channel
            </button>
          </div>
        )}
      </div>

      {/* Username Profile Section */}
      <div className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-card space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center shadow-sm">
            <User className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">Update Creator Handle</h2>
            <p className="text-xs text-slate-500">Change your public display username across Plexudo.</p>
          </div>
        </div>

        {usernameSuccess && (
          <div className="p-3.5 rounded-2xl bg-emerald-50 border border-emerald-100 text-emerald-700 text-xs font-semibold">
            Username updated successfully!
          </div>
        )}

        <form onSubmit={handleUpdateUsername} className="space-y-4">
          <div>
            <label htmlFor="settings-username" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Username
            </label>
            <input
              id="settings-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:bg-white focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all"
            />
          </div>
          <button
            type="submit"
            disabled={isUpdatingUsername || username === user?.username}
            className="px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-sm transition-all disabled:opacity-40"
          >
            {isUpdatingUsername ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : 'Save Username'}
          </button>
        </form>
      </div>

      {/* Security & Password Section */}
      <div className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-card space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center shadow-sm">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">Change Password</h2>
            <p className="text-xs text-slate-500">Update your account password with Argon2id cryptographic protection.</p>
          </div>
        </div>

        {passwordSuccess && (
          <div className="p-3.5 rounded-2xl bg-emerald-50 border border-emerald-100 text-emerald-700 text-xs font-semibold">
            Password updated successfully!
          </div>
        )}

        {passwordError && (
          <div className="p-3.5 rounded-2xl bg-red-50 border border-red-100 text-red-700 text-xs font-semibold">
            {passwordError}
          </div>
        )}

        <form onSubmit={handleUpdatePassword} className="space-y-4">
          <div>
            <label htmlFor="settings-current-password" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Current Password
            </label>
            <div className="relative">
              <input
                id="settings-current-password"
                type={showPassword ? 'text' : 'password'}
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 pr-10 py-2.5 text-sm text-slate-900 focus:bg-white focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                aria-label={showPassword ? 'Hide current password' : 'Show current password'}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="settings-new-password" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                New Password
              </label>
              <input
                id="settings-new-password"
                type={showPassword ? 'text' : 'password'}
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:bg-white focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all"
              />
            </div>
            <div>
              <label htmlFor="settings-confirm-password" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Confirm New Password
              </label>
              <input
                id="settings-confirm-password"
                type={showPassword ? 'text' : 'password'}
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:bg-white focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 transition-all"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isUpdatingPassword}
            className="px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-sm transition-all disabled:opacity-50"
          >
            {isUpdatingPassword ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : 'Update Password'}
          </button>
        </form>
      </div>

      {/* Logout Card */}
      <div className="p-6 rounded-3xl bg-white border border-slate-200/80 shadow-card flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-900">Sign Out</h3>
          <p className="text-xs text-slate-500">Revoke your active session on this device.</p>
        </div>
        <button
          onClick={logout}
          className="px-4 py-2 rounded-xl bg-red-50 hover:bg-red-100 text-red-700 font-bold text-xs transition-colors border border-red-100"
        >
          Sign Out
        </button>
      </div>

      <RewardAdModal isOpen={isAdModalOpen} onClose={() => setIsAdModalOpen(false)} onSuccess={refreshUser} />
    </div>
  );
};
