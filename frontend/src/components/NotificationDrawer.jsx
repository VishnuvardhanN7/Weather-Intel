import React, { useEffect, useState, useCallback, useRef } from 'react';
import { X, Bell, CheckCheck, MapPin, ShieldAlert, Info, Settings, Loader2 } from 'lucide-react';
import { api } from '../services/api.js';

const TYPE_ICONS = {
  alert: MapPin,
  verification: ShieldAlert,
  system: Info,
};

const TYPE_COLORS = {
  alert: 'text-red-600',
  verification: 'text-[#D9A441]',
  system: 'text-[#D9A441]',
};

export default function NotificationDrawer({ open, onClose }) {
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('all');
  const drawerRef = useRef(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [listRes, countRes] = await Promise.all([
        api.get('/api/notifications?per_page=50'),
        api.get('/api/notifications/unread-count'),
      ]);
      setItems(listRes.data.data || []);
      setUnread(countRes.data.unread_count || 0);
    } catch {
      /* logged out / offline */
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!open) return;
    refresh();
    const timer = setInterval(refresh, 45000);
    return () => clearInterval(timer);
  }, [open, refresh]);

  useEffect(() => {
    if (open && drawerRef.current) {
      drawerRef.current.focus();
    }
  }, [open]);

  const markRead = async (id) => {
    try {
      await api.post(`/api/notifications/${id}/read`);
      setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
      setUnread((u) => Math.max(0, u - 1));
    } catch {
      /* ignore */
    }
  };

  const markAllRead = async () => {
    try {
      await api.post('/api/notifications/read-all');
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnread(0);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape' && open) onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const filtered = filter === 'unread'
    ? items.filter((n) => !n.is_read)
    : filter === 'alerts'
    ? items.filter((n) => n.type === 'alert')
    : items;

  return (
    <div className="fixed inset-0 z-[9999]" role="dialog" aria-modal="true" aria-label="Notifications">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <aside
        ref={drawerRef}
        tabIndex={-1}
        className="absolute right-0 top-0 h-full w-full max-w-md bg-white border-l border-[#E5E2DA] flex flex-col outline-none shadow-2xl"
      >
        <div className="flex items-center justify-between p-5 border-b border-[#E5E2DA]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-[#F7EED7] flex items-center justify-center text-[#D9A441]">
              <Bell className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-bold text-[#111111] tracking-tight">System Alerts & Notifications</h2>
            {unread > 0 && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-500/15 text-red-700 border border-red-500/20">
                {unread} new
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {unread > 0 && (
              <button
                onClick={markAllRead}
                className="text-xs font-semibold text-[#D9A441] hover:text-[#A97820] inline-flex items-center gap-1 transition-colors"
              >
                <CheckCheck className="w-3.5 h-3.5" /> Mark all read
              </button>
            )}
            <button onClick={onClose} className="p-2 rounded-full hover:bg-[#F7F7F5] text-[#66635C] hover:text-[#111111] transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="flex gap-2 px-5 py-3 border-b border-[#E5E2DA]" role="tablist">
          {[
            { id: 'all', label: 'All' },
            { id: 'unread', label: 'Unread' },
            { id: 'alerts', label: 'Alerts' },
          ].map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={filter === tab.id}
              onClick={() => setFilter(tab.id)}
              className={`px-3 py-1.5 text-xs font-bold rounded-full transition-all ${
                filter === tab.id
                  ? 'bg-[#111111] text-white shadow-sm'
                  : 'text-[#66635C] hover:text-[#111111] hover:bg-[#F7F7F5]'
              }`}
            >
              {tab.label}
            </button>
          ))}
          {loading && (
            <Loader2 className="w-3.5 h-3.5 text-[#D9A441] animate-spin ml-auto self-center" />
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {filtered.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-[#96938B] p-8 text-center">
              <Bell className="w-10 h-10 mb-3 opacity-30 text-[#96938B]" />
              <p className="text-xs font-semibold">
                {filter === 'unread' ? 'No unread notifications' : 'No notification history'}
              </p>
            </div>
          )}

          <div className="space-y-1.5">
            {filtered.map((n) => {
              const Icon = TYPE_ICONS[n.type] || Info;
              const iconColor = TYPE_COLORS[n.type] || 'text-[#96938B]';
              return (
                <div
                  key={n.id}
                  onClick={() => !n.is_read && markRead(n.id)}
                  role="button"
                  tabIndex={0}
                  className={`p-4 rounded-xl transition-all cursor-pointer border ${
                    n.is_read
                      ? 'bg-[#F7F7F5] border-[#E5E2DA] opacity-70'
                      : 'bg-white border-[#E5E2DA] hover:border-[#D9A441] shadow-sm'
                  }`}
                >
                  <div className="flex gap-3">
                    <div className="mt-0.5 shrink-0">
                      <Icon className={`w-4 h-4 ${iconColor}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-bold text-[#111111]">{n.title}</p>
                      <p className="text-xs text-[#66635C] mt-1 leading-relaxed">{n.message}</p>
                      <p className="text-[10px] font-medium text-[#96938B] mt-2">
                        {new Date(n.created_at).toLocaleString()}
                      </p>
                    </div>
                    {!n.is_read && (
                      <span className="w-2 h-2 mt-1 rounded-full bg-[#D9A441] flex-shrink-0" />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </aside>
    </div>
  );
}
