import React, { useState } from 'react';
import { api, ApiError } from '../../lib/api';
import { useAuth } from '../../context/AuthContext';
import {
  Bot,
  Loader2,
  Sparkles,
  Copy,
  Check,
  Zap,
  Target,
  FileText,
  AlertCircle,
} from 'lucide-react';
import { RewardAdModal } from '../../components/RewardAdModal';
import { InsufficientCreditsModal } from '../../components/InsufficientCreditsModal';

const PROMPT_TYPES = [
  { id: 'retention_hooks', name: '15-Sec Retention Hooks', icon: Zap, desc: 'Intro hooks that stop viewers from clicking away' },
  { id: 'titles', name: 'High-CTR Title Generator', icon: Target, desc: 'Viral algorithmic title variants' },
  { id: 'description', name: 'SEO Video Description', icon: FileText, desc: 'Optimized description with timestamps outline' },
  { id: 'channel_ideas', name: 'Video Topic Generator', icon: Sparkles, desc: 'Breakout content angles based on your niche' },
];

export const AiAssistantPage: React.FC = () => {
  const { credits, refreshUser } = useAuth();
  const [promptType, setPromptType] = useState('retention_hooks');
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);
  const [copied, setCopied] = useState(false);

  const [isAdModalOpen, setIsAdModalOpen] = useState(false);
  const [isInsufficientModalOpen, setIsInsufficientModalOpen] = useState(false);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (credits < 1) {
      setIsInsufficientModalOpen(true);
      return;
    }

    setError(null);
    setLoading(true);
    setCopied(false);

    try {
      const res = await api.post<any>('/api/v1/tools/ai-assistant', {
        prompt_type: promptType,
        topic,
      });
      setResult(res);
      await refreshUser();
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 402) {
          setIsInsufficientModalOpen(true);
        } else {
          setError(typeof err.detail === 'string' ? err.detail : 'Failed to generate AI content. Please try again.');
        }
      } else {
        setError('Network connection error. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!result?.generation) return;
    navigator.clipboard.writeText(result.generation);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  return (
    <div className="space-y-5 sm:space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="bg-white p-5 sm:p-6 rounded-2xl sm:rounded-3xl border border-slate-200/80 shadow-card flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-700 text-[11px] font-bold">
              Cost: 1 Credit
            </span>
            <span className="text-slate-300">•</span>
            <span className="text-xs text-slate-500 font-medium">Groq AI Powered</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <Bot className="w-6 h-6 text-emerald-600" /> AI Creator Assistant
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 max-w-xl">
            Generate viral video hooks, high-CTR titles, and retention-focused descriptions using Groq AI.
          </p>
        </div>
      </div>

      {/* Input Form */}
      <div className="bg-white p-5 sm:p-6 rounded-2xl sm:rounded-3xl border border-slate-200/80 shadow-card space-y-4">
        {error && (
          <div className="p-3.5 rounded-xl bg-red-50 border border-red-100 text-red-700 text-xs font-semibold flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}

        <form onSubmit={handleGenerate} className="space-y-4">
          <div>
            <span className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-2">
              Select Generation Mode
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {PROMPT_TYPES.map((t) => {
                const Icon = t.icon;
                const isSelected = promptType === t.id;
                return (
                  <button
                    type="button"
                    key={t.id}
                    onClick={() => setPromptType(t.id)}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      isSelected
                        ? 'bg-emerald-50/80 border-emerald-300 shadow-subtle'
                        : 'bg-slate-50 border-slate-200/80 hover:bg-slate-100/70'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Icon className={`w-4 h-4 ${isSelected ? 'text-emerald-600' : 'text-slate-400'}`} />
                      <span className={`text-xs font-bold ${isSelected ? 'text-emerald-950' : 'text-slate-700'}`}>
                        {t.name}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5 pl-6 leading-tight">{t.desc}</p>
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <label htmlFor="ai-topic-input" className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
              Video Topic, Niche or Draft Idea
            </label>
            <input
              id="ai-topic-input"
              type="text"
              required
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., How I built a profitable AI app in 7 days without coding"
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2 text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-500/20 transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white font-bold text-sm shadow-sm flex items-center justify-center gap-2 transition-all hover:shadow disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Sparkles className="w-4 h-4" /> Generate Creator Strategy (1 Credit)
              </>
            )}
          </button>
        </form>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4 animate-fade-in">
          <div className="p-5 sm:p-6 rounded-2xl sm:rounded-3xl bg-white border border-slate-200/80 shadow-card space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100">
                Groq AI Generation ({result.prompt_type})
              </span>
              <button
                onClick={handleCopy}
                className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-subtle"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" /> Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" /> Copy Text
                  </>
                )}
              </button>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/60 font-sans text-xs sm:text-sm text-slate-800 leading-relaxed whitespace-pre-wrap">
              {result.generation}
            </div>
          </div>
        </div>
      )}

      <InsufficientCreditsModal
        isOpen={isInsufficientModalOpen}
        onClose={() => setIsInsufficientModalOpen(false)}
        onOpenAdModal={() => setIsAdModalOpen(true)}
      />

      <RewardAdModal
        isOpen={isAdModalOpen}
        onClose={() => setIsAdModalOpen(false)}
        onSuccess={refreshUser}
      />
    </div>
  );
};
