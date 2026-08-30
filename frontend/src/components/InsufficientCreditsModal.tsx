import React from 'react';
import { Sparkles, AlertCircle, X } from 'lucide-react';

interface InsufficientCreditsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenAdModal: () => void;
}

export const InsufficientCreditsModal: React.FC<InsufficientCreditsModalProps> = ({
  isOpen,
  onClose,
  onOpenAdModal,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-md max-h-[90dvh] overflow-y-auto bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-modal space-y-6">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-slate-700 transition-colors p-1"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="text-center space-y-5">
          <div className="w-14 h-14 rounded-2xl bg-amber-50 border border-amber-100 text-amber-600 flex items-center justify-center mx-auto shadow-sm">
            <AlertCircle className="w-7 h-7" />
          </div>

          <div className="space-y-1.5">
            <h3 className="text-xl font-bold text-slate-900">Insufficient Credits</h3>
            <p className="text-xs sm:text-sm text-slate-500 max-w-xs mx-auto leading-relaxed">
              This tool requires <strong>1 credit</strong> to execute. You can earn free credits instantly by watching a 5-second sponsor message.
            </p>
          </div>

          <div className="space-y-3 pt-2">
            <button
              onClick={() => {
                onClose();
                onOpenAdModal();
              }}
              className="w-full py-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-bold text-sm shadow-sm flex items-center justify-center gap-2 transition-all hover:shadow"
            >
              <Sparkles className="w-4 h-4" /> Earn 1 Free Credit (5s)
            </button>
            <button
              onClick={onClose}
              className="w-full py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
