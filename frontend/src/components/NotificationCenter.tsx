import React, { useState, useEffect } from 'react';
import {
  Bell,
  Check,
  CheckCheck,
  Clock,
  MapPin,
  AlertTriangle,
  Flame,
  ShieldAlert,
  X,
  ExternalLink,
  ChevronRight,
  Filter,
} from 'lucide-react';
import { api } from '../services/api';
import { NotificationItem } from '../types';

interface NotificationCenterProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectAlert: (alert: NotificationItem) => void;
  onUnreadCountChange?: (count: number) => void;
}

export const NotificationCenter: React.FC<NotificationCenterProps> = ({
  isOpen,
  onClose,
  onSelectAlert,
  onUnreadCountChange,
}) => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [activeFilter, setActiveFilter] = useState<'all' | 'unread' | 'high'>('all');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const fetchNotifications = async () => {
    setIsLoading(true);
    try {
      const res = await api.getNotifications({ limit: 50 });
      setNotifications(res.notifications || []);
      setUnreadCount(res.unread_count || 0);
      if (onUnreadCountChange) onUnreadCountChange(res.unread_count || 0);
    } catch (err) {
      console.warn('Failed to load notifications:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen]);

  const handleMarkAsRead = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((item) => (item.id === id ? { ...item, is_read: true } : item))
      );
      setUnreadCount(res.unread_count);
      if (onUnreadCountChange) onUnreadCountChange(res.unread_count);
    } catch (err) {
      console.warn('Failed to mark notification read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      const res = await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((item) => ({ ...item, is_read: true })));
      setUnreadCount(0);
      if (onUnreadCountChange) onUnreadCountChange(0);
    } catch (err) {
      console.warn('Failed to mark all notifications read:', err);
    }
  };

  const filteredItems = notifications.filter((item) => {
    if (activeFilter === 'unread') return !item.is_read;
    if (activeFilter === 'high') return item.severity === 'CRITICAL' || item.severity === 'HIGH';
    return true;
  });

  const getSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'HIGH':
        return 'bg-orange-50 text-orange-700 border-orange-200';
      case 'MODERATE':
      case 'MEDIUM':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      default:
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
  };

  const formatTimeAgo = (dateStr?: string | null) => {
    if (!dateStr) return 'Recently';
    const diffMs = Date.now() - new Date(dateStr).getTime();
    const diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
  };

  if (!isOpen) return null;

  return (
    <div className="absolute right-4 top-16 w-96 max-w-[calc(100vw-2rem)] bg-white border border-slate-200 rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col max-h-[85vh] animate-fadeIn">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-blue-50 text-blue-600">
            <Bell className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wide">
              Incident Alerts & Notifications
            </h3>
            <span className="text-[11px] text-slate-500">
              {unreadCount} unread alert{unreadCount !== 1 ? 's' : ''} in database
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="px-2 py-1 rounded text-[11px] text-blue-600 hover:bg-blue-50 font-semibold flex items-center gap-1 transition-colors"
              title="Mark all notifications as read"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              <span>Mark all read</span>
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="px-4 py-2 border-b border-slate-100 flex items-center gap-1.5 bg-white text-xs">
        <button
          onClick={() => setActiveFilter('all')}
          className={`px-2.5 py-1 rounded-md font-medium text-xs transition-colors ${
            activeFilter === 'all'
              ? 'bg-slate-900 text-white'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          All ({notifications.length})
        </button>
        <button
          onClick={() => setActiveFilter('unread')}
          className={`px-2.5 py-1 rounded-md font-medium text-xs transition-colors ${
            activeFilter === 'unread'
              ? 'bg-blue-600 text-white'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Unread ({unreadCount})
        </button>
        <button
          onClick={() => setActiveFilter('high')}
          className={`px-2.5 py-1 rounded-md font-medium text-xs transition-colors ${
            activeFilter === 'high'
              ? 'bg-orange-600 text-white'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          High & Critical
        </button>
      </div>

      {/* Notifications List */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
        {filteredItems.length === 0 ? (
          <div className="py-12 px-4 text-center text-xs text-slate-400">
            No alerts found in this view.
          </div>
        ) : (
          filteredItems.map((item) => (
            <div
              key={item.id}
              onClick={() => {
                onSelectAlert(item);
                if (!item.is_read) {
                  api.markNotificationRead(item.id).catch(() => {});
                  setNotifications((prev) =>
                    prev.map((i) => (i.id === item.id ? { ...i, is_read: true } : i))
                  );
                }
                onClose();
              }}
              className={`p-3.5 hover:bg-slate-50 cursor-pointer transition-colors relative flex items-start gap-3 group ${
                !item.is_read ? 'bg-blue-50/30' : ''
              }`}
            >
              {/* Unread indicator */}
              {!item.is_read && (
                <span className="w-2 h-2 rounded-full bg-blue-600 mt-1.5 flex-shrink-0" />
              )}
              {item.is_read && <span className="w-2 h-2 flex-shrink-0" />}

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-1 mb-1">
                  <span
                    className={`text-[9px] font-mono font-bold uppercase px-1.5 py-0.2 rounded border ${getSeverityBadge(
                      item.severity
                    )}`}
                  >
                    {item.severity}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {formatTimeAgo(item.created_at)}
                  </span>
                </div>

                <p className="text-xs font-medium text-slate-800 line-clamp-2">
                  {item.message}
                </p>

                <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-slate-100 text-[11px] text-slate-500">
                  <div className="flex items-center gap-1 truncate max-w-[200px]">
                    <MapPin className="w-3 h-3 text-slate-400 flex-shrink-0" />
                    <span className="truncate">{item.region_name}</span>
                  </div>

                  {!item.is_read && (
                    <button
                      onClick={(e) => handleMarkAsRead(item.id, e)}
                      className="p-1 rounded text-slate-400 hover:text-blue-600 hover:bg-white transition-colors"
                      title="Mark as read"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-blue-600 flex-shrink-0 mt-3" />
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="p-2.5 bg-slate-50 border-t border-slate-100 text-center">
        <span className="text-[10px] text-slate-400 font-mono">
          Live FIRMS Satellites • Automatic PostGIS Alert Triggering
        </span>
      </div>
    </div>
  );
};
