import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Gauge,
  Video,
  Search,
  TrendingUp,
  Users,
  Bot,
  History,
  Settings,
  Sparkles,
} from 'lucide-react';

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

const toolNav = [
  { name: 'SEO Score', href: '/tools/seo-score', icon: Gauge, badge: '50 Pts' },
  { name: 'Video Analyzer', href: '/tools/video-analyzer', icon: Video },
  { name: 'Keyword Tool', href: '/tools/keyword-tool', icon: Search },
  { name: 'Trend Analyzer', href: '/tools/trend-analyzer', icon: TrendingUp },
  { name: 'Competitors', href: '/tools/competitor-analysis', icon: Users },
  { name: 'AI Assistant', href: '/tools/ai-assistant', icon: Bot, badge: 'Groq AI' },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen = false, onClose }) => {
  const content = (
    <div className="flex flex-col h-full justify-between p-4 space-y-6">
      <div className="space-y-6">
        {/* Main Section */}
        <div>
          <nav className="space-y-1">
            <NavLink
              to="/dashboard"
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700 font-bold shadow-subtle'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`
              }
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Dashboard</span>
            </NavLink>
          </nav>
        </div>

        {/* Creator Tools Section */}
        <div>
          <p className="px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
            Creator Tools
          </p>
          <nav className="space-y-1">
            {toolNav.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3 py-2 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 font-bold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <item.icon className="w-4 h-4 text-slate-500" />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Activity & Account Section */}
        <div>
          <p className="px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
            Workspace
          </p>
          <nav className="space-y-1">
            <NavLink
              to="/history"
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700 font-bold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`
              }
            >
              <History className="w-4 h-4 text-slate-500" />
              <span>History</span>
            </NavLink>
            <NavLink
              to="/profile"
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700 font-bold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`
              }
            >
              <Settings className="w-4 h-4 text-slate-500" />
              <span>Settings</span>
            </NavLink>
          </nav>
        </div>
      </div>

      {/* Credit Info Box in Sidebar */}
      <div className="p-3.5 rounded-2xl bg-gradient-to-br from-indigo-50 to-slate-50 border border-indigo-100/80 space-y-1.5">
        <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-900">
          <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
          <span>Credits Model</span>
        </div>
        <p className="text-[11px] text-slate-500 leading-relaxed">
          1 tool run = 1 credit. Watch verified sponsor ads anytime to claim free credits.
        </p>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200/80 shrink-0 hidden md:block min-h-[calc(100vh-4rem)] shadow-subtle">
        {content}
      </aside>

      {/* Mobile Drawer Overlay */}
      {isOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
            onClick={onClose}
          />
          <aside className="relative w-72 max-w-[80vw] bg-white h-full shadow-2xl z-10 flex flex-col">
            {content}
          </aside>
        </div>
      )}
    </>
  );
};
