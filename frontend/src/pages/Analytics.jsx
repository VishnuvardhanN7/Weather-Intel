import React, { useEffect, useState, useCallback } from 'react';
import { BarChart3, TrendingUp, MapPin, RefreshCw, ShieldCheck, Layers, AlertTriangle, Fingerprint } from 'lucide-react';
import WeatherMap from '../components/WeatherMap.jsx';
import StatsCard from '../components/StatsCard.jsx';
import {
  EventsByTypeBarChart,
  EventsOverTimeChart,
  EventsByStatePieChart,
  SeverityDistributionChart,
  VerificationStatsChart,
  SourceBreakdownChart,
} from '../components/Charts.jsx';
import { api } from '../services/api.js';

export default function Analytics() {
  const [byType, setByType] = useState([]);
  const [overTime, setOverTime] = useState([]);
  const [byState, setByState] = useState([]);
  const [severity, setSeverity] = useState([]);
  const [verification, setVerification] = useState([]);
  const [sourceBreakdown, setSourceBreakdown] = useState([]);
  const [recentEvents, setRecentEvents] = useState([]);
  const [topCities, setTopCities] = useState([]);
  const [intel, setIntel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('30');
  const [granularity, setGranularity] = useState('day');

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      const days = parseInt(timeRange);
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - days);
      const start = startDate.toISOString();

      const results = await Promise.allSettled([
        api.get(`/api/dashboard/events-by-type?start_date=${start}`),
        api.get(`/api/dashboard/events-over-time?start_date=${start}&granularity=${granularity}`),
        api.get('/api/dashboard/events-by-state'),
        api.get('/api/dashboard/severity-distribution'),
        api.get('/api/dashboard/verification-stats'),
        api.get('/api/dashboard/source-breakdown'),
        api.get('/api/dashboard/recent-events?limit=5'),
        api.get('/api/dashboard/top-cities?limit=10'),
        api.get('/api/weather?per_page=100'),
        api.get('/api/dashboard/intelligence-summary'),
      ]);

      const resolve = (r) => r.status === 'fulfilled' ? r.value.data.data : [];
      setByType(resolve(results[0]));
      setOverTime(resolve(results[1]));
      setByState(resolve(results[2]));
      setSeverity(resolve(results[3]));
      setVerification(resolve(results[4]));
      setSourceBreakdown(resolve(results[5]));
      setRecentEvents(resolve(results[6]));
      setTopCities(resolve(results[7]));
      if (results[8].status === 'fulfilled') {
        setRecentEvents(results[8].value.data.data);
      }
      if (results[9].status === 'fulfilled') setIntel(results[9].value.data);
    } catch (err) {
      console.error('Analytics fetch error:', err);
    }
    setLoading(false);
  }, [timeRange, granularity]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  return (
    <div className="space-y-8" role="main" aria-label="Analytics">
      
      {/* Editorial Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-[#E5E2DA] dark:border-[#262938]">
        <div>
          <h1 className="text-2xl sm:text-3xl lg:text-[34px] font-extrabold text-[#111111] dark:text-[#faf9f6] tracking-tight">
            Analytics
          </h1>
          <p className="text-[13px] text-[#66635C] dark:text-stone-400 mt-1.5 font-normal max-w-2xl leading-relaxed">
            Weather patterns across India
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="bg-white dark:bg-[#141620] border border-[#E5E2DA] dark:border-[#262938] text-[#111111] dark:text-stone-200 text-xs font-semibold rounded-full px-3.5 py-2 focus:outline-none focus:border-[#D9A441] shadow-subtle"
          >
            <option value="7">Last 7 Days</option>
            <option value="30">Last 30 Days</option>
            <option value="90">Last 90 Days</option>
            <option value="365">Last 1 Year</option>
          </select>
          <select
            value={granularity}
            onChange={(e) => setGranularity(e.target.value)}
            className="bg-white dark:bg-[#141620] border border-[#E5E2DA] dark:border-[#262938] text-[#111111] dark:text-stone-200 text-xs font-semibold rounded-full px-3.5 py-2 focus:outline-none focus:border-[#D9A441] shadow-subtle"
          >
            <option value="day">Daily</option>
            <option value="week">Weekly</option>
            <option value="month">Monthly</option>
          </select>
          <button onClick={fetchAnalytics} className="btn-secondary inline-flex items-center gap-2 text-xs py-2 px-4" disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* SECTION 1: AI Analytics Overview Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Verification Rate"
          value={`${(intel?.verification_rate || 0).toFixed(1)}%`}
          icon={ShieldCheck}
          variant="success"
        />
        <StatsCard
          title="Corroboration"
          value={`${(intel?.corroboration_rate || 0).toFixed(1)}%`}
          icon={Layers}
          variant="primary"
        />
        <StatsCard
          title="Misinformation"
          value={intel?.detected_misinfo || 0}
          icon={AlertTriangle}
          variant="danger"
        />
        <StatsCard
          title="Priority Load"
          value={(intel?.priority?.critical || 0) + (intel?.priority?.high || 0)}
          icon={Fingerprint}
          variant="warning"
        />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <EventsByTypeBarChart data={byType} />
        <EventsOverTimeChart data={overTime} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-[#161822] overflow-hidden p-0 border border-[#E5E2DA] dark:border-[#262938] rounded-xl shadow-subtle">
            <div className="p-4 border-b border-[#E5E2DA] dark:border-[#262938] bg-[#F7F7F5] dark:bg-[#0E1017]">
              <h3 className="text-sm font-bold text-[#111111] dark:text-white flex items-center gap-2">
                <MapPin className="w-4 h-4 text-[#D9A441]" /> Geographic Incident Concentration
              </h3>
            </div>
            <WeatherMap events={recentEvents} height="360px" />
          </div>
        </div>
        <EventsByStatePieChart data={byState} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <SeverityDistributionChart data={severity} />
        <VerificationStatsChart data={verification} />
        <SourceBreakdownChart data={sourceBreakdown} />
      </div>

      {/* Top Cities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card-editorial">
          <h3 className="text-base font-bold text-[#111111] dark:text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-[#D9A441]" /> Top Cities by Weather Event Volume
          </h3>
          <div className="space-y-3">
            {topCities.map((city, idx) => (
              <div key={idx} className="flex items-center gap-3 p-3 rounded-xl bg-[#F7F7F5] dark:bg-[#0e1017] border border-[#E5E2DA] dark:border-stone-800">
                <span className="text-xs font-bold text-[#96938B] w-5 text-right">{idx + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold text-[#111111] dark:text-white truncate">{city.city}</p>
                  <p className="text-[11px] text-[#66635C] dark:text-stone-400">{city.state}</p>
                </div>
                <div className="w-24 bg-stone-200 dark:bg-stone-800 rounded-full h-2">
                  <div
                    className="bg-[#D9A441] h-2 rounded-full"
                    style={{
                      width: `${topCities.length > 0 ? (city.count / topCities[0].count) * 100 : 0}%`,
                    }}
                  />
                </div>
                <span className="text-xs font-bold text-[#111111] dark:text-white w-8 text-right">{city.count}</span>
              </div>
            ))}
            {topCities.length === 0 && (
              <p className="text-xs text-[#96938B] text-center py-8">No city event data available</p>
            )}
          </div>
        </div>

        <div className="card-editorial">
          <h3 className="text-base font-bold text-[#111111] dark:text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-[#D9A441]" /> Event Category Distribution
          </h3>
          <div className="space-y-3">
            {byType.map((item, idx) => {
              const maxCount = byType.length > 0 ? Math.max(...byType.map(b => b.count)) : 1;
              const pct = (item.count / maxCount) * 100;
              return (
                <div key={idx} className="p-3 bg-[#F7F7F5] dark:bg-[#0e1017] border border-[#E5E2DA] dark:border-stone-800 rounded-xl">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold text-[#111111] dark:text-stone-200 capitalize">{item.event_type?.replace('_', ' ')}</span>
                    <span className="text-xs font-bold text-[#111111] dark:text-white">{item.count}</span>
                  </div>
                  <div className="w-full bg-stone-200 dark:bg-stone-800 rounded-full h-2">
                    <div
                      className="h-2 rounded-full bg-[#D9A441] transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

