import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { api, getToken, getUser, setAuth as persistAuth, clearAuth } from '../services/api.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getUser());
  const [loading, setLoading] = useState(() => !getUser());

  const sync = useCallback(() => setUser(getUser()), []);

  const refreshSession = useCallback(async () => {
    // A stored token means the session should continue. Revalidate it so the
    // UI reflects the latest role/name after a page refresh or route change.
    if (!getToken()) {
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get('/api/auth/me');
      const current = getUser() || {};
      persistAuth({ token: getToken(), user: { ...current, ...data } });
      setUser({ ...current, ...data });
    } catch {
      clearAuth();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshSession();
    window.addEventListener('auth:changed', sync);
    return () => window.removeEventListener('auth:changed', sync);
  }, [refreshSession, sync]);

  const login = useCallback((token, nextUser) => {
    persistAuth({ token, user: nextUser });
    setUser(getUser());
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
  }, []);

  const value = {
    user,
    isAuthenticated: Boolean(user),
    loading,
    login,
    logout,
    refresh: refreshSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}

export default AuthContext;