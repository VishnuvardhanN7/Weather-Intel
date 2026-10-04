import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api.js';

export function useWeatherData(params = {}) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 20,
    total: 0,
    total_pages: 0,
  });

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const queryParams = new URLSearchParams();
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined && val !== null && val !== '') {
          queryParams.append(key, val);
        }
      });
      queryParams.append('page', pagination.page);
      queryParams.append('per_page', pagination.per_page);

      const response = await api.get(`/api/weather?${queryParams.toString()}`);
      setEvents(response.data.data);
      setPagination(response.data.pagination);
    } catch (err) {
      setError(err.message || 'Failed to fetch weather data');
    }
    setLoading(false);
  }, [params, pagination.page, pagination.per_page]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const setPage = (page) => setPagination(p => ({ ...p, page }));
  const setPerPage = (per_page) => setPagination(p => ({ ...p, per_page, page: 1 }));
  const refetch = fetchEvents;

  return { events, loading, error, pagination, setPage, setPerPage, refetch };
}

export function useWeatherStats() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/weather/stats/general');
      setStats(response.data);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  return { stats, loading, error, refetch: fetchStats };
}

export function useDashboardAnalytics() {
  const [analytics, setAnalytics] = useState({
    byType: [],
    byState: [],
    overTime: [],
    severity: [],
    verification: [],
    topCities: [],
    recentEvents: [],
  });
  const [loading, setLoading] = useState(true);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      const results = await Promise.allSettled([
        api.get('/api/dashboard/events-by-type'),
        api.get('/api/dashboard/events-by-state'),
        api.get('/api/dashboard/events-over-time?granularity=day'),
        api.get('/api/dashboard/severity-distribution'),
        api.get('/api/dashboard/verification-stats'),
        api.get('/api/dashboard/top-cities?limit=10'),
        api.get('/api/dashboard/recent-events?limit=10'),
      ]);

      const resolve = (r) => r.status === 'fulfilled' ? r.value.data.data : [];

      setAnalytics({
        byType: resolve(results[0]),
        byState: resolve(results[1]),
        overTime: resolve(results[2]),
        severity: resolve(results[3]),
        verification: resolve(results[4]),
        topCities: resolve(results[5]),
        recentEvents: resolve(results[6]),
      });
    } catch (err) {
      console.error('Dashboard analytics error:', err);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  return { analytics, loading, refetch: fetchAnalytics };
}
