import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { Loader2 } from 'lucide-react';

// Public Marketing & SEO Pages
import { LandingPage } from './pages/LandingPage';
import { BlogPage } from './pages/BlogPage';
import { PublicToolPage } from './pages/PublicToolPage';

// Auth Pages
import { Login } from './pages/Login';
import { Signup } from './pages/Signup';
import { VerifyEmail } from './pages/VerifyEmail';
import { ForgotPassword } from './pages/ForgotPassword';
import { ResetPassword } from './pages/ResetPassword';
import { YouTubeCallback } from './pages/YouTubeCallback';

// Private Dashboard & Tools Pages
import { Dashboard } from './pages/Dashboard';
import { ProfileSettings } from './pages/ProfileSettings';
import { HistoryPage } from './pages/HistoryPage';
import { SeoScorePage } from './pages/tools/SeoScorePage';
import { VideoAnalyzerPage } from './pages/tools/VideoAnalyzerPage';
import { KeywordToolPage } from './pages/tools/KeywordToolPage';
import { TrendAnalyzerPage } from './pages/tools/TrendAnalyzerPage';
import { CompetitorAnalysisPage } from './pages/tools/CompetitorAnalysisPage';
import { AiAssistantPage } from './pages/tools/AiAssistantPage';

const ProtectedLayout: React.FC = () => {
  const { user, loading } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  if (loading) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-slate-50 text-indigo-600">
        <Loader2 className="w-10 h-10 animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-dvh bg-slate-50 flex flex-col selection:bg-indigo-600 selection:text-white">
      <Navbar
        onMobileMenuToggle={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        isMobileMenuOpen={isMobileMenuOpen}
      />
      <div className="flex-1 flex w-full max-w-7xl mx-auto">
        <Sidebar
          isOpen={isMobileMenuOpen}
          onClose={() => setIsMobileMenuOpen(false)}
        />
        <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 max-w-5xl w-full mx-auto">
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/profile" element={<ProfileSettings />} />
            <Route path="/settings" element={<ProfileSettings />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/tools/seo-score" element={<SeoScorePage />} />
            <Route path="/tools/video-analyzer" element={<VideoAnalyzerPage />} />
            <Route path="/tools/keyword-tool" element={<KeywordToolPage />} />
            <Route path="/tools/trend-analyzer" element={<TrendAnalyzerPage />} />
            <Route path="/tools/competitor-analysis" element={<CompetitorAnalysisPage />} />
            <Route path="/tools/ai-assistant" element={<AiAssistantPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Landing & Marketing Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/blog" element={<BlogPage />} />
          <Route path="/youtube-seo-tool" element={<PublicToolPage tool="seo" />} />
          <Route path="/youtube-video-analyzer" element={<PublicToolPage tool="video" />} />
          <Route path="/youtube-keyword-tool" element={<PublicToolPage tool="keyword" />} />
          <Route path="/youtube-trend-analyzer" element={<PublicToolPage tool="trend" />} />
          <Route path="/youtube-competitor-analysis" element={<PublicToolPage tool="competitor" />} />

          {/* Public Auth Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/youtube/callback" element={<YouTubeCallback />} />

          {/* Protected Application Routes */}
          <Route path="/*" element={<ProtectedLayout />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
