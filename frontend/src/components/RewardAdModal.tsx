import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { X, Play, CheckCircle, Sparkles, Loader2 } from 'lucide-react';

interface RewardAdModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const RewardAdModal: React.FC<RewardAdModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const { claimAdReward } = useAuth();
  const [adState, setAdState] = useState<'intro' | 'playing' | 'completed'>('intro');
  const [countdown, setCountdown] = useState<number>(5);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setAdState('intro');
      setCountdown(5);
      setError(null);
      setIsSubmitting(false);
      return;
    }
  }, [isOpen]);

  useEffect(() => {
    let timer: any;
    if (adState === 'playing' && countdown > 0) {
      timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
    } else if (adState === 'playing' && countdown === 0) {
      (async () => {
        setIsSubmitting(true);
        try {
          await claimAdReward();
          setAdState('completed');
          if (onSuccess) onSuccess();
        } catch (err: any) {
          setError(err.detail || 'Failed to claim reward. Please try again.');
          setAdState('intro');
        } finally {
          setIsSubmitting(false);
        }
      })();
    }
    return () => clearTimeout(timer);
  }, [adState, countdown, claimAdReward, onSuccess]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-md max-h-[90dvh] overflow-y-auto bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-modal space-y-6">
        <button
          onClick={onClose}
          disabled={adState === 'playing' && countdown > 0}
          className="absolute top-5 right-5 text-slate-400 hover:text-slate-700 disabled:opacity-30 transition-colors p-1"
          aria-label="Close reward modal"
        >
          <X className="w-5 h-5" />
        </button>

        {adState === 'intro' && (
          <div className="text-center space-y-5">
            <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center mx-auto shadow-sm">
              <Sparkles className="w-7 h-7" />
            </div>
            <div className="space-y-1.5">
              <h3 className="text-xl font-bold text-slate-900">Earn 1 Free Credit</h3>
              <p className="text-xs sm:text-sm text-slate-500 max-w-xs mx-auto leading-relaxed">
                Watch a quick 5-second sponsor message to instantly receive +1 creator tool credit.
              </p>
            </div>

            {error && <p className="text-xs text-red-600 bg-red-50 p-3 rounded-xl border border-red-100 font-medium">{error}</p>}

            <button
              onClick={() => {
                setCountdown(5);
                setAdState('playing');
              }}
              className="w-full py-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-bold shadow-sm flex items-center justify-center gap-2 transition-all hover:shadow"
            >
              <Play className="w-4 h-4 fill-current" /> Watch Sponsor Video (5s)
            </button>
          </div>
        )}

        {adState === 'playing' && (
          <div className="text-center space-y-6 py-2">
            <div className="relative aspect-video rounded-2xl bg-gradient-to-br from-indigo-50 via-white to-purple-50 border border-indigo-100/80 flex flex-col items-center justify-center p-6 shadow-inner">
              <span className="text-[10px] font-extrabold uppercase tracking-widest text-indigo-600 mb-1.5 px-2.5 py-0.5 rounded-full bg-indigo-100/80">
                Verified Sponsor Partner
              </span>
              <p className="text-sm sm:text-base font-bold text-slate-800 max-w-xs text-center">
                Plexudo AI: Supercharge your YouTube channel retention & growth
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-500 font-medium px-1">
                <span>Reward unlocks in:</span>
                <span className="text-indigo-600 font-bold text-sm">{countdown}s</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full bg-indigo-600 transition-all duration-1000 ease-linear rounded-full"
                  style={{ width: `${((5 - countdown) / 5) * 100}%` }}
                ></div>
              </div>
            </div>

            {isSubmitting && (
              <div className="flex items-center justify-center gap-2 text-xs text-slate-500 font-medium">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-600" /> Verifying reward with server...
              </div>
            )}
          </div>
        )}

        {adState === 'completed' && (
          <div className="text-center space-y-5 py-2">
            <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-sm">
              <CheckCircle className="w-8 h-8" />
            </div>
            <div className="space-y-1.5">
              <h3 className="text-xl font-bold text-slate-900">+1 Credit Added!</h3>
              <p className="text-xs sm:text-sm text-slate-500 max-w-xs mx-auto leading-relaxed">
                Your credit balance has been updated. You can now execute another creator tool.
              </p>
            </div>
            <button
              onClick={onClose}
              className="w-full py-3.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-sm transition-all shadow-sm"
            >
              Continue to Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
