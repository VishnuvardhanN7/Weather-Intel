import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

const TOKEN_KEY = 'token';
const USER_KEY = 'user';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null');
  } catch {
    return null;
  }
}

export function setAuth({ token, user }) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  window.dispatchEvent(new Event('auth:changed'));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  window.dispatchEvent(new Event('auth:changed'));
}

export function isAuthenticated() {
  return Boolean(getToken());
}

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
      delete config.headers['content-type'];
    } else if (config.data instanceof URLSearchParams || (typeof config.data === 'string' && config.data.includes('='))) {
      config.headers['Content-Type'] = 'application/x-www-form-urlencoded';
    }
    return config;
  },
  (error) => Promise.reject(error)
);

/**
 * Preserve the action the user attempted so it can be resumed after login.
 * Only paths that require a real session are redirected; public pages load
 * normally while logged out.
 */
export function rememberReturnTo(path) {
  if (!path || path.startsWith('/login')) return;
  try {
    sessionStorage.setItem('returnTo', path);
  } catch {
    /* private mode - ignore */
  }
}

export function consumeReturnTo() {
  let value = null;
  try {
    value = sessionStorage.getItem('returnTo');
    sessionStorage.removeItem('returnTo');
  } catch {
    /* ignore */
  }
  return value;
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = error?.config?.url || '';
    const path = window.location.pathname + window.location.search;

    if (status === 401) {
      const isMedia = url.includes('/api/media/');
      if (!isMedia) {
        clearAuth();
        if (!path.startsWith('/login')) {
          rememberReturnTo(path);
          window.location.assign('/login?auto=expired');
        }
      }
    }
    return Promise.reject(error);
  }
);

export { api };

export default api;