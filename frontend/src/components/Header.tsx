import React, { useEffect, useState } from 'react';
import {
  Flame,
  Satellite,
  Clock,
  Sparkles,
  User as UserIcon,
  LogOut,
  Bell,
  ChevronDown,
  Info,
} from 'lucide-react';
import { Region, User, SearchResult, NotificationItem } from '../types';
import { GlobalSearch } from './GlobalSearch';
import { NotificationCenter } from './NotificationCenter';
import { AboutModal } from './AboutModal';
import { api } from '../services/api';

interface HeaderProps {
  regions: Region[];
  selectedRegion: Region | null;
  onSelectRegion: (region: Region | null) => void;
  user: User | null;
  onOpenAuth: (mode?: 'signin' | 'signup') => void;
  onLogout: () => void;
  onOpenAIReport: () => void;
  onSelectSearchResult: (result: SearchResult) => void;
  onSelectNotification: (alert: NotificationItem) => void;
}

export const Header: React.FC<HeaderProps> = ({
  regions,
  selectedRegion,
  onSelectRegion,
  user,
  onOpenAuth,
  onLogout,
  onOpenAIReport,
  onSelectSearchResult,
  onSelectNotification,
}) => {
  const [utcTime, setUtcTime] = useState<string>('');
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isAboutOpen, setIsAboutOpen] = useState(false);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().replace('GMT', 'UTC'));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch initial unread count
  useEffect(() => {
    api
      .getNotifications({ limit: 1 })
      .then((res) => {
        setUnreadCount(res.unread_count || 0);
      })
      .catch(() => {});
  }, []);

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-4 flex items-center justify-between select-none z-30 sticky top-0 shadow-xs">
      {/* Left: Brand Identity */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center shadow-md shadow-blue-500/20 flex-shrink-0">
          <Flame className="w-5 h-5 text-white" />
        </div>
        <div className="hidden sm:block">
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm tracking-wider text-slate-900 uppercase font-mono">
              KRATOS
            </span>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
              V3.0
            </span>
          </div>
          <p className="text-[11px] text-slate-500 tracking-tight">
            Geospatial Thermal Anomaly & Infrastructure Surveillance
          </p>
        </div>
      </div>

      {/* Middle: Region Selector & Global Search */}
      <div className="flex items-center gap-3 flex-1 max-w-2xl mx-4">
        {/* Dynamic Region Selector Dropdown */}
        <div className="relative flex-shrink-0">
          <select
            value={selectedRegion?.id || ''}
            onChange={(e) => {
              const val = e.target.value;
              if (!val) {
                onSelectRegion(null);
              } else {
                const reg = regions.find((r) => r.id === val);
                if (reg) onSelectRegion(reg);
              }
            }}
            aria-label="Select Monitoring Region"
            className="appearance-none bg-slate-50 border border-slate-200 hover:border-blue-500 text-xs text-slate-900 font-semibold py-1.5 pl-3 pr-8 rounded-lg focus:outline-none focus:border-blue-600 transition-colors cursor-pointer shadow-xs"
          >
            <option value="">National Overview (Pan-India)</option>
            <optgroup label="Industrial Corridors (6)">
              {regions
                .filter((r) => r.category === 'industrial_corridor')
                .map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.state})
                  </option>
                ))}
            </optgroup>
            <optgroup label="Forest Fire Landscapes (4)">
              {regions
                .filter((r) => r.category === 'forest_landscape')
                .map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.state})
                  </option>
                ))}
            </optgroup>
          </select>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>

        {/* Unified Geospatial Global Search */}
        <GlobalSearch onSelectResult={onSelectSearchResult} className="flex-1" />
      </div>

      {/* Right: Telemetry, Notification Bell, AI Briefing & Account */}
      <div className="flex items-center gap-2.5 relative">
        {/* Live Satellites & UTC Clock Pill */}
        <div className="hidden xl:flex items-center gap-2.5 px-3 py-1 bg-slate-50 border border-slate-200 rounded-lg text-[11px] font-mono text-slate-600">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <Satellite className="w-3.5 h-3.5 text-emerald-600" />
            <span className="font-medium text-slate-700">NOAA-20 / 21 VIIRS</span>
          </div>
          <span className="text-slate-300">|</span>
          <div className="flex items-center gap-1 text-slate-500">
            <Clock className="w-3 h-3 text-slate-400" />
            <span>{utcTime || 'SYNCHRONIZING...'}</span>
          </div>
        </div>

        {/* Real Persistent Notification Bell */}
        <div className="relative">
          <button
            onClick={() => setIsNotificationsOpen((prev) => !prev)}
            className="p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors relative"
            aria-label="View notifications"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 bg-red-600 text-white text-[10px] font-mono font-bold rounded-full flex items-center justify-center shadow-xs">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </button>

          {/* Slide-out Notification Center Dropdown */}
          <NotificationCenter
            isOpen={isNotificationsOpen}
            onClose={() => setIsNotificationsOpen(false)}
            onSelectAlert={onSelectNotification}
            onUnreadCountChange={setUnreadCount}
          />
        </div>

        {/* About & Data Provenance Button */}
        <button
          onClick={() => setIsAboutOpen(true)}
          className="flex items-center gap-1.5 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 px-2.5 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all shadow-xs active:scale-95"
          title="Platform Architecture & Data Provenance"
          aria-label="Platform Architecture & Data Provenance"
        >
          <Info className="w-3.5 h-3.5 text-blue-600" />
          <span className="hidden sm:inline">About</span>
        </button>

        {/* AI Situational Briefing Trigger */}
        <button
          onClick={onOpenAIReport}
          className="flex items-center gap-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all shadow-xs active:scale-95"
        >
          <Sparkles className="w-3.5 h-3.5 text-blue-600 animate-spin-slow" />
          <span className="hidden md:inline">AI Situation Briefing</span>
          <span className="md:hidden">AI</span>
        </button>

        {/* User Account / Auth */}
        {user ? (
          <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
            <div className="flex items-center gap-1.5 text-xs">
              <span className="w-7 h-7 rounded-full bg-blue-100 border border-blue-200 flex items-center justify-center text-[11px] font-bold text-blue-700">
                {user.username.slice(0, 2).toUpperCase()}
              </span>
              <span className="text-slate-800 font-medium text-xs hidden lg:inline">
                {user.username}
              </span>
              {user.is_admin && (
                <span className="px-1.5 py-0.2 bg-red-50 text-red-600 border border-red-200 text-[9px] rounded font-bold">
                  ADMIN
                </span>
              )}
            </div>
            <button
              onClick={onLogout}
              title="Sign Out"
              aria-label="Sign Out"
              className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-slate-100 rounded-md transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => onOpenAuth('signin')}
              className="flex items-center gap-1.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors shadow-xs"
            >
              <UserIcon className="w-3.5 h-3.5 text-slate-400" />
              <span>Sign In</span>
            </button>
            <button
              onClick={() => onOpenAuth('signup')}
              className="hidden sm:flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider font-mono transition-colors shadow-xs"
            >
              <span>Sign Up</span>
            </button>
          </div>
        )}
      </div>

      {/* About & Data Provenance Modal */}
      <AboutModal isOpen={isAboutOpen} onClose={() => setIsAboutOpen(false)} />
    </header>
  );
};
