import React, { useState, useEffect, useCallback } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, MapPin, CloudSun, BarChart3, Settings, LogOut,
  Menu, X, Bell, LogIn, SlidersHorizontal, Sun, Moon, Sparkles, Newspaper
} from 'lucide-react';
import clsx from 'clsx';
import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext.jsx';
import { useTheme } from '../context/ThemeContext.jsx';
import { api } from '../services/api.js';
import NotificationDrawer from './NotificationDrawer.jsx';
import AlertPreferences from './AlertPreferences.jsx';
import Footer from './Footer.jsx';

const TOP_NAV_ITEMS = [
  { id: 'dashboard', path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'weather-map', path: '/weather-map', label: 'Weather Map', icon: MapPin },
  { id: 'stories', path: '/stories', label: 'Stories', icon: Newspaper },
  { id: 'analytics', path: '/analytics', label: 'Analytics', icon: BarChart3, adminOnly: true },
  { id: 'admin', path: '/admin', label: 'Admin Panel', icon: Settings, adminOnly: true },
];

export default function Layout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [prefsOpen, setPrefsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const isHomePage = location.pathname === '/' || location.pathname === '/dashboard';
  const isWeatherMapPage = location.pathname === '/weather-map';
  const isAdmin = (user?.role || '').toLowerCase() === 'admin';

  const fetchUnread = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const { data } = await api.get('/api/notifications/unread-count');
      setUnreadCount(data.unread_count || 0);
    } catch {
      /* ignore */
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) {
      setUnreadCount(0);
      return;
    }
    fetchUnread();
    const timer = setInterval(fetchUnread, 60000);
    return () => clearInterval(timer);
  }, [isAuthenticated, fetchUnread]);

  const handleLogout = () => {
    logout();
    setNotifOpen(false);
    setProfileDropdownOpen(false);
    navigate('/');
  };

  const navItems = TOP_NAV_ITEMS.filter((item) => {
    if (isAdmin) {
      return !item.citizenOnly;
    }
    return !item.adminOnly;
  });

  const initials = (user?.full_name || user?.username || 'U').slice(0, 1).toUpperCase();

  const handleNavClick = (item) => {
    setMobileOpen(false);
    if (item.isAlertsTrigger) {
      setPrefsOpen(true);
      return;
    }
    navigate(item.path);
  };

  return (
    <div className="min-h-screen bg-[#F7F7F5] dark:bg-[#0F1117] text-[#111111] dark:text-[#F3F4F6] flex flex-col font-sans selection:bg-[#F7EED7] selection:text-[#111111] transition-colors duration-200">
      <a href="#main-content" className="skip-link">Skip to main content</a>

      {/* Navbar Header: Transparent over Hero on Homepage, Solid on Other Routes */}
      <motion.header
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className={clsx(
          'z-40 px-4 sm:px-6 lg:px-8 transition-colors duration-200 flex items-center',
          isHomePage
            ? 'absolute top-0 left-0 right-0 h-[68px] sm:h-[72px] bg-transparent border-b-0'
            : 'sticky top-0 h-[68px] sm:h-[72px] bg-white/95 dark:bg-[#161822]/95 backdrop-blur-md border-b border-[#E5E2DA] dark:border-[#262938]'
        )}
      >
        <div className="w-full max-w-[1600px] mx-auto flex items-center justify-between gap-3 sm:gap-5">
          
          {/* LEFT: Brand Logo */}
          <div className="flex items-center gap-2 shrink-0">
            <Link to="/" className="flex items-center gap-2 group">
              <div className="w-8 h-8 rounded-lg text-white flex items-center justify-center shadow-md border border-white/20 shrink-0 opacity-100" style={{ backgroundColor: '#111111' }}>
                <CloudSun className="w-4 h-4 text-[#D9A441]" />
              </div>
              <span className={clsx(
                "text-lg font-extrabold tracking-tight font-sans",
                isHomePage ? "text-white drop-shadow-sm" : "text-[#111111] dark:text-white"
              )}>
                ATMOS
              </span>
            </Link>
          </div>

          {/* CENTER: Navigation Links */}
          <nav className="hidden lg:flex items-center justify-center gap-1 sm:gap-1.5 lg:gap-2" aria-label="Main navigation">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || (item.path === '/dashboard' && location.pathname === '/');
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item)}
                  style={isActive ? { backgroundColor: '#111111', opacity: 1 } : {}}
                  className={clsx(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs sm:text-sm font-semibold transition-all duration-150 whitespace-nowrap cursor-pointer shrink-0',
                    isActive
                      ? 'bg-[#111111] text-white font-bold shadow-md border border-white/20'
                      : isHomePage
                      ? 'text-white/90 hover:text-white hover:bg-white/15'
                      : 'text-[#66635C] dark:text-[#9CA3AF] hover:text-[#111111] dark:hover:text-white hover:bg-[#F7F7F5] dark:hover:bg-[#1C1F2E]'
                  )}
                >
                  <Icon className={clsx('w-4 h-4 shrink-0', isActive ? 'text-white' : isHomePage ? 'text-white/80' : 'text-[#66635C] dark:text-[#9CA3AF]')} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* RIGHT: Action Buttons & Controls */}
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            {/* Ask ATMOS Button */}
            <button
              onClick={() => navigate('/ask-atmos')}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs sm:text-sm font-semibold transition-all duration-150 shadow-sm cursor-pointer border border-white/20 shrink-0',
                location.pathname === '/ask-atmos'
                  ? 'bg-black text-white ring-2 ring-[#D9A441]'
                  : 'bg-[#111111] hover:bg-black text-white'
              )}
              title="Ask ATMOS AI Assistant"
              aria-label="Ask ATMOS AI Assistant"
            >
              <Sparkles className="w-4 h-4 text-[#D9A441] shrink-0" />
              <span className="hidden sm:inline">Ask ATMOS</span>
            </button>

            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className={clsx(
                "p-1.5 rounded-full transition-all duration-150 cursor-pointer shrink-0",
                isHomePage
                  ? "text-white/90 hover:text-white hover:bg-white/15"
                  : "text-[#66635C] dark:text-[#9CA3AF] hover:text-[#111111] dark:hover:text-white hover:bg-[#F7F7F5] dark:hover:bg-[#1C1F2E]"
              )}
              title={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
              aria-label={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
            >
              {theme === 'dark' ? (
                <Moon className="w-4 h-4" />
              ) : (
                <Sun className="w-4 h-4" />
              )}
            </button>

            {/* Notifications Button */}
            {isAuthenticated && (
              <button
                onClick={() => setNotifOpen(true)}
                className={clsx(
                  "relative p-1.5 rounded-full transition-all duration-150 cursor-pointer shrink-0",
                  isHomePage
                    ? "text-white/90 hover:text-white hover:bg-white/15"
                    : "text-[#66635C] dark:text-[#9CA3AF] hover:text-[#111111] dark:hover:text-white hover:bg-[#F7F7F5] dark:hover:bg-[#1C1F2E]"
                )}
                aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
              >
                <Bell className="w-4 h-4" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-[#D9A441]" />
                )}
              </button>
            )}

            {/* Alert Preferences */}
            {isAuthenticated && (
              <button
                onClick={() => setPrefsOpen(true)}
                className={clsx(
                  "p-1.5 rounded-full transition-all duration-150 cursor-pointer shrink-0",
                  isHomePage
                    ? "text-white/90 hover:text-white hover:bg-white/15"
                    : "text-[#66635C] dark:text-[#9CA3AF] hover:text-[#111111] dark:hover:text-white hover:bg-[#F7F7F5] dark:hover:bg-[#1C1F2E]"
                )}
                title="Alert Settings"
                aria-label="Alert preferences"
              >
                <SlidersHorizontal className="w-4 h-4" />
              </button>
            )}

            {/* User Profile Avatar / Sign In */}
            {isAuthenticated ? (
              <div className="relative shrink-0">
                <button
                  onClick={() => setProfileDropdownOpen((v) => !v)}
                  className="w-7.5 h-7.5 rounded-full bg-[#111111] text-white text-xs font-bold flex items-center justify-center transition-all duration-150 border border-white/30 focus:outline-none focus:ring-2 focus:ring-[#D9A441]"
                  aria-label="User profile"
                  title={user?.full_name || user?.username}
                >
                  {initials}
                </button>

                {profileDropdownOpen && (
                  <div className="absolute right-0 mt-2 w-52 bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-xl shadow-xl p-2 z-50">
                    <div className="px-3 py-2 border-b border-[#E5E2DA] dark:border-[#262938] mb-1">
                      <p className="text-sm font-bold text-[#111111] dark:text-white truncate">{user?.full_name || user?.username}</p>
                      <p className="text-xs text-[#66635C] dark:text-[#9CA3AF] capitalize">{user?.role || 'User'}</p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-3 py-2 rounded-lg text-xs font-semibold text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 flex items-center gap-2 transition-colors"
                    >
                      <LogOut className="w-4 h-4" /> Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Link to="/login" className="px-3 py-1.5 rounded-full bg-[#111111] text-xs sm:text-sm font-semibold hover:bg-black text-white transition-all duration-150 inline-flex items-center gap-1.5 shadow-sm border border-white/20 shrink-0">
                <LogIn className="w-4 h-4" /> Sign In
              </Link>
            )}

            {/* Mobile Menu Toggle Button */}
            <button
              onClick={() => setMobileOpen((v) => !v)}
              className={clsx(
                "lg:hidden p-1.5 rounded-full transition-all cursor-pointer shrink-0",
                isHomePage ? "text-white hover:bg-white/15" : "text-[#66635C] dark:text-[#9CA3AF] hover:text-[#111111] dark:hover:text-white hover:bg-[#F7F7F5] dark:hover:bg-[#1C1F2E]"
              )}
              aria-label="Toggle navigation"
            >
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </motion.header>

      {/* Mobile Navigation Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-[9999] lg:hidden" role="dialog" aria-modal="true">
          <div className="fixed inset-0 bg-black/60 dark:bg-black/80 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside className="fixed right-0 top-0 h-full w-64 bg-white dark:bg-[#0e1017] border-l border-stone-200 dark:border-stone-800 p-5 flex flex-col justify-between z-50">
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-stone-200 dark:border-stone-800 mb-4">
                <span className="font-bold text-stone-900 dark:text-white text-sm">Navigation</span>
                <button onClick={() => setMobileOpen(false)} className="p-1 text-stone-500 dark:text-stone-400 hover:text-stone-900 dark:hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <nav className="space-y-1">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname === item.path;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleNavClick(item)}
                      className={clsx(
                        'w-full flex items-center gap-3 px-4 py-2.5 rounded-2xl text-xs font-semibold transition-all',
                        isActive
                          ? 'bg-[#14161f] text-white dark:bg-[#faf9f6] dark:text-[#0f1016]'
                          : 'text-stone-700 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 hover:text-stone-900 dark:hover:text-white'
                      )}
                    >
                      <Icon className="w-4 h-4" />
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </nav>
            </div>

            <div className="pt-4 border-t border-stone-200 dark:border-stone-800">
              {isAuthenticated ? (
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center justify-center gap-2 p-2.5 rounded-2xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-red-600 dark:text-red-400 font-semibold text-xs"
                >
                  <LogOut className="w-4 h-4" /> Sign Out
                </button>
              ) : (
                <Link
                  to="/login"
                  onClick={() => setMobileOpen(false)}
                  className="btn-primary w-full flex items-center justify-center gap-2 py-2.5 text-xs"
                >
                  <LogIn className="w-4 h-4" /> Sign In
                </Link>
              )}
            </div>
          </aside>
        </div>
      )}

      {/* Main Content */}
      <main id="main-content" className={clsx("flex-1 w-full mx-auto", (isHomePage || isWeatherMapPage) ? "p-0 max-w-none" : "max-w-[1600px] p-4 sm:p-6 lg:p-8")} tabIndex={-1}>
        {children}
      </main>

      {/* Global Footer (Omitted on Fullscreen Weather Map page) */}
      {!isWeatherMapPage && <Footer />}

      {/* Notifications & Preferences Drawers */}
      <NotificationDrawer open={notifOpen} onClose={() => setNotifOpen(false)} />
      <AlertPreferences open={prefsOpen} onClose={() => setPrefsOpen(false)} />
    </div>
  );
}

