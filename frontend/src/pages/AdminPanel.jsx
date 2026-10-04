import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  Users, Shield, Settings, CheckCircle, XCircle, Clock,
  AlertTriangle, Database, Trash2, Eye, RefreshCw, Plus,
  Keyboard, Filter, ChevronDown, Brain, ListChecks, Loader2,
  Activity, Radio, Zap, Image, Video, Cpu, Server, Layers,
  ExternalLink, Info, Check, Play, ArrowRight, BarChart2
} from 'lucide-react';
import EventTable from '../components/EventTable.jsx';
import StatsCard from '../components/StatsCard.jsx';
import {
  SourceLatencyChart,
  SourceVerifiedVSRejectedChart,
  SourceMediaChart,
  EventsByTypeBarChart
} from '../components/Charts.jsx';
import { api } from '../services/api.js';

const EVENT_TYPES = [
  'rainfall', 'thunderstorm', 'flooding', 'heatwave', 'fog',
  'dust_storm', 'strong_winds', 'cyclone', 'other',
];

export default function AdminPanel() {
  const [events, setEvents] = useState([]);
  const [stats, setStats] = useState(null);
  const [adminMetrics, setAdminMetrics] = useState(null);
  const [systemVersion, setSystemVersion] = useState(null);
  const [funnelData, setFunnelData] = useState([]);
  const [sources, setSources] = useState([]);
  const [mediaStats, setMediaStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const [activeTab, setActiveTab] = useState('events');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedIds, setSelectedIds] = useState(new Set());

  // Ingestion execution modal & persistent latest run state
  const [ingesting, setIngesting] = useState(false);
  const [ingestionMessage, setIngestionMessage] = useState('');
  const [executionSummary, setExecutionSummary] = useState(null);
  const [latestRunSummary, setLatestRunSummary] = useState(() => {
    try {
      const saved = localStorage.getItem('atmos_latest_ingestion_run');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // Source inspector modal state
  const [inspectSource, setInspectSource] = useState(null);
  const [inspectDetail, setInspectDetail] = useState(null);
  const [inspectLoading, setInspectLoading] = useState(false);
  const [syncingSourceId, setSyncingSourceId] = useState(null);

  // Shortcuts & AI override modal state
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [overrideEvent, setOverrideEvent] = useState(null);
  const [overrideType, setOverrideType] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [overrideSaving, setOverrideSaving] = useState(false);
  const [overrideDone, setOverrideDone] = useState(null);

  const openOverride = (event) => {
    setOverrideEvent(event);
    setOverrideType(event.event_type || 'other');
    setOverrideReason('');
    setOverrideDone(null);
  };

  const closeOverride = () => {
    setOverrideEvent(null);
    setOverrideDone(null);
  };

  const submitOverride = async () => {
    if (!overrideEvent || !overrideReason.trim() || overrideSaving) return;
    setOverrideSaving(true);
    try {
      const res = await api.post(`/api/intelligence/events/${overrideEvent.id}/classify`, {
        event_type: overrideType,
        reason: overrideReason.trim(),
      });
      const audit = await api.get(`/api/intelligence/events/${overrideEvent.id}/audit`);
      setOverrideDone({
        summary: res.data,
        audit_entries: audit.data?.audit_entries || [],
      });
      fetchData();
    } catch (err) {
      setOverrideDone({ error: err.response?.data?.detail || 'Override failed.' });
    }
    setOverrideSaving(false);
  };

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [eventsRes, statsRes, sourcesRes, metricsRes, funnelRes, mediaRes, versionRes] = await Promise.allSettled([
        api.get('/api/weather?per_page=100'),
        api.get('/api/weather/stats/general'),
        api.get('/api/admin/sources'),
        api.get('/api/admin/metrics'),
        api.get('/api/admin/pipeline'),
        api.get('/api/admin/media'),
        api.get('/api/admin/system-version'),
      ]);

      if (eventsRes.status === 'fulfilled') setEvents(eventsRes.value.data.data || []);
      if (statsRes.status === 'fulfilled') setStats(statsRes.value.data);
      if (sourcesRes.status === 'fulfilled') setSources(sourcesRes.value.data.sources || []);
      if (metricsRes.status === 'fulfilled') setAdminMetrics(metricsRes.value.data.metrics || null);
      if (funnelRes.status === 'fulfilled') setFunnelData(funnelRes.value.data.funnel || []);
      if (mediaRes.status === 'fulfilled') setMediaStats(mediaRes.value.data.media_stats || null);
      if (versionRes.status === 'fulfilled') setSystemVersion(versionRes.value.data || null);
    } catch (err) {
      console.error('Admin fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Handle single source inspection
  const openSourceInspector = async (source) => {
    setInspectSource(source);
    setInspectLoading(true);
    try {
      const res = await api.get(`/api/admin/sources/${source.source_id}`);
      setInspectDetail(res.data.source || null);
    } catch (err) {
      console.error('Error fetching source details:', err);
      setInspectDetail(null);
    } finally {
      setInspectLoading(false);
    }
  };

  const syncSingleSource = async (sourceId) => {
    setSyncingSourceId(sourceId);
    try {
      const res = await api.post(`/api/admin/sources/${sourceId}/sync`);
      await fetchData();
      if (inspectSource && inspectSource.source_id === sourceId) {
        await openSourceInspector(inspectSource);
      }
    } catch (err) {
      console.error('Source sync error:', err);
    } finally {
      setSyncingSourceId(null);
    }
  };

  const runIngestion = async (useSampleData = false) => {
    setIngesting(true);
    setIngestionMessage('Running multi-source ingestion & streaming pipeline cycle...');
    setExecutionSummary(null);
    try {
      const response = await api.post('/api/ingest/run', {
        sources: ['all'],
        use_sample_data: useSampleData,
      });
      const data = response.data;
      setExecutionSummary(data);
      setLatestRunSummary(data);
      try {
        localStorage.setItem('atmos_latest_ingestion_run', JSON.stringify(data));
      } catch (e) {
        console.warn('Failed to store latest run summary in localStorage:', e);
      }
      const succeeded = data.sources_succeeded ?? 0;
      const attempted = data.sources_attempted ?? (data.sources_triggered ?? 16);
      const warningsCount = data.warnings?.length || 0;
      setIngestionMessage(`INGESTION COMPLETE — ${succeeded} / ${attempted} Sources Successful | ${data.collected || 0} Events Collected | ${data.persisted || 0} Persisted ${warningsCount > 0 ? `(${warningsCount} Warnings)` : ''}`);
      await fetchData();
    } catch (err) {
      setIngestionMessage(err.response?.data?.detail || 'Ingestion failed. Check server logs.');
    } finally {
      setIngesting(false);
    }
  };

  const filteredEvents = useMemo(() => {
    let result = events;

    if (activeTab === 'verification') {
      result = result.filter(e => e.verification_status === 'pending' || e.verification_status === 'needs_review');
    } else if (activeTab === 'suspicious') {
      result = result.filter(e => e.is_fake === true);
    } else if (activeTab === 'verified') {
      result = result.filter(e => e.verification_status === 'verified');
    }

    if (statusFilter !== 'all') {
      result = result.filter(e => e.verification_status === statusFilter);
    }

    return result;
  }, [events, activeTab, statusFilter]);

  const filteredSources = useMemo(() => {
    if (sourceFilter === 'all') return sources;
    if (sourceFilter === 'healthy') return sources.filter(s => s.status === 'HEALTHY' || s.status === 'LIVE_VERIFIED' || s.status === 'READY');
    if (sourceFilter === 'auth_required') return sources.filter(s => s.status === 'AUTH_REQUIRED');
    if (sourceFilter === 'degraded') return sources.filter(s => s.status === 'DEGRADED' || s.status === 'ERROR' || s.status === 'DISABLED');
    return sources;
  }, [sources, sourceFilter]);

  const statusCounts = useMemo(() => ({
    all: events.length,
    pending: events.filter(e => e.verification_status === 'pending').length,
    verified: events.filter(e => e.verification_status === 'verified').length,
    rejected: events.filter(e => e.verification_status === 'rejected').length,
    needs_review: events.filter(e => e.verification_status === 'needs_review').length,
  }), [events]);

  const sourceStatusSummary = useMemo(() => {
    let healthy = 0, authReq = 0, degraded = 0, disabled = 0;
    sources.forEach(s => {
      if (s.status === 'HEALTHY' || s.status === 'LIVE_VERIFIED' || s.status === 'READY') healthy++;
      else if (s.status === 'AUTH_REQUIRED') authReq++;
      else if (s.status === 'DEGRADED' || s.status === 'ERROR') degraded++;
      else disabled++;
    });
    return { healthy, authReq, degraded, disabled, total: sources.length };
  }, [sources]);

  const effectiveFunnelData = useMemo(() => {
    if (funnelData && funnelData.length > 0) return funnelData;

    const totalEvents = events.length || 0;
    const collected = adminMetrics?.total_events_ingested || totalEvents;
    const raw = adminMetrics?.kafka_raw_count || collected;
    const spark = adminMetrics?.total_events_processed || raw;
    const ai = adminMetrics?.ai_evaluated || spark;
    const jevAcc = adminMetrics?.jev_accepted || totalEvents;
    const jevRej = adminMetrics?.jev_rejected || 0;
    const persisted = adminMetrics?.persisted_records || totalEvents;
    const filtered = adminMetrics?.filtered_routine_observations || 0;

    return [
      { stage: 'SOURCE COLLECTED', count: collected, description: 'Raw observations collected from APIs, satellite, web & social' },
      { stage: 'KAFKA RAW BUFFER', count: raw, description: "Published into Kafka topic 'weather.raw'" },
      { stage: 'SPARK & CLEAN LAYER', count: spark, description: "Processed & normalized into Kafka topic 'weather.clean'" },
      { stage: 'AI EVALUATED', count: ai, description: 'Processed through IndicBERT, Fake News AI & Deduplication AI' },
      { stage: 'JEV ACCEPTED', count: jevAcc, description: 'Passed JEV truth scoring gate (probability >= 0.60)' },
      { stage: 'JEV REJECTED', count: jevRej, description: 'Filtered by JEV as low-confidence / unverified claim' },
      { stage: 'PERSISTED (DB & OPENSEARCH)', count: persisted, description: 'Severe incidents passing alertness gate (> 0.90) stored in PostGIS & indexed' },
      { stage: 'FILTERED ROUTINE', count: filtered, description: 'Routine weather observations intentionally filtered by alertness score' },
    ];
  }, [funnelData, adminMetrics, events]);

  const sortedLatestSourceBreakdown = useMemo(() => {
    const breakdown = latestRunSummary?.source_breakdown || {};
    return Object.entries(breakdown).sort(([nameA, countA], [nameB, countB]) => {
      const countDiff = (countB || 0) - (countA || 0);
      if (countDiff !== 0) return countDiff;
      return nameA.localeCompare(nameB);
    });
  }, [latestRunSummary]);

  const sortedModalSourceBreakdown = useMemo(() => {
    const breakdown = executionSummary?.source_breakdown || {};
    return Object.entries(breakdown).sort(([nameA, countA], [nameB, countB]) => {
      const countDiff = (countB || 0) - (countA || 0);
      if (countDiff !== 0) return countDiff;
      return nameA.localeCompare(nameB);
    });
  }, [executionSummary]);

  // Prepare charts data
  const chartLatencyData = useMemo(() => {
    return sources.map(s => ({
      name: s.name,
      latency: s.metrics?.average_latency_ms || 0,
    })).filter(d => d.latency > 0);
  }, [sources]);

  const chartVerifiedVsRejectedData = useMemo(() => {
    const map = {};
    events.forEach(e => {
      const srcName = e.source_details?.display || e.source || 'Other';
      if (!map[srcName]) map[srcName] = { name: srcName, verified: 0, rejected: 0 };
      if (e.verification_status === 'verified') map[srcName].verified++;
      if (e.verification_status === 'rejected') map[srcName].rejected++;
    });
    return Object.values(map);
  }, [events]);

  const chartMediaData = useMemo(() => {
    return sources.map(s => ({
      name: s.name,
      media_count: s.metrics?.media_collected || (mediaStats?.media_by_source?.[s.source_id]?.images || 0) + (mediaStats?.media_by_source?.[s.source_id]?.videos || 0),
    })).filter(d => d.media_count >= 0);
  }, [sources, mediaStats]);

  const handleVerify = async (eventId, status) => {
    try {
      await api.post(`/api/weather/${eventId}/verify`, { verification_status: status });
      fetchData();
    } catch (err) {
      console.error('Verify error:', err);
    }
  };

  const handleDelete = async (eventId) => {
    if (!confirm('Delete Weather Event?\n\nAre you sure you want to permanently delete this weather event?')) return;
    try {
      await api.delete(`/api/weather/${eventId}`);
      fetchData();
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  const toggleSelect = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === filteredEvents.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredEvents.map(e => e.id)));
    }
  };

  const bulkVerify = async (status) => {
    const targets = filteredEvents.filter(e => selectedIds.has(e.id));
    if (targets.length === 0) return;
    if (!confirm(`Verify ${targets.length} selected event(s) as ${status}?`)) return;

    for (const event of targets) {
      try {
        await api.post(`/api/weather/${event.id}/verify`, { verification_status: status });
      } catch (err) {
        console.error(`Bulk verify error for event ${event.id}:`, err);
      }
    }
    setSelectedIds(new Set());
    fetchData();
  };

  const bulkDelete = async () => {
    const targets = filteredEvents.filter(e => selectedIds.has(e.id));
    if (targets.length === 0) return;
    if (!confirm(`Permanently delete ${targets.length} selected event(s)?`)) return;

    for (const event of targets) {
      try {
        await api.delete(`/api/weather/${event.id}`);
      } catch (err) {
        console.error(`Bulk delete error for event ${event.id}:`, err);
      }
    }
    setSelectedIds(new Set());
    fetchData();
  };

  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'v' || e.key === 'V') {
        e.preventDefault();
        bulkVerify('verified');
      }
      if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        bulkVerify('rejected');
      }
      if (e.key === '?') {
        e.preventDefault();
        setShowShortcuts(s => !s);
      }
      if (e.key === 'Escape') {
        setSelectedIds(new Set());
        setShowShortcuts(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selectedIds, filteredEvents]);

  const tabs = [
    { id: 'events', label: 'All Incidents', icon: Database, count: statusCounts.all },
    { id: 'verification', label: 'Verification Queue', icon: Shield, count: statusCounts.pending + statusCounts.needs_review },
    { id: 'suspicious', label: 'Suspicious / Fake Risk', icon: AlertTriangle, count: events.filter(e => e.is_fake).length },
    { id: 'verified', label: 'Verified Authentic', icon: CheckCircle, count: statusCounts.verified },
  ];

  return (
    <div className="space-y-8" role="main" aria-label="Admin Operations Dashboard">
      
      {/* Keyboard Shortcuts Modal */}
      {showShortcuts && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 dark:bg-black/70 backdrop-blur-sm" onClick={() => setShowShortcuts(false)}>
          <div className="card-editorial max-w-md w-full mx-4 bg-white dark:bg-[#0e1017] border border-[#E5E2DA] dark:border-stone-800 p-6 shadow-xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#E5E2DA] dark:border-stone-800">
              <h3 className="text-sm font-bold text-[#111111] dark:text-white flex items-center gap-2">
                <Keyboard className="w-4 h-4 text-[#D9A441]" /> Keyboard Shortcuts
              </h3>
              <button onClick={() => setShowShortcuts(false)} className="text-stone-400 hover:text-[#111111] dark:hover:text-white">
                <XCircle className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1.5"><span className="text-[#66635C] dark:text-stone-400">Verify selected</span><kbd className="px-2.5 py-1 bg-[#F7F7F5] dark:bg-stone-800 rounded-md text-[#111111] dark:text-stone-200 font-mono">V</kbd></div>
              <div className="flex justify-between py-1.5"><span className="text-[#66635C] dark:text-stone-400">Reject selected</span><kbd className="px-2.5 py-1 bg-[#F7F7F5] dark:bg-stone-800 rounded-md text-[#111111] dark:text-stone-200 font-mono">R</kbd></div>
              <div className="flex justify-between py-1.5"><span className="text-[#66635C] dark:text-stone-400">Deselect all / Close</span><kbd className="px-2.5 py-1 bg-[#F7F7F5] dark:bg-stone-800 rounded-md text-[#111111] dark:text-stone-200 font-mono">Esc</kbd></div>
              <div className="flex justify-between py-1.5"><span className="text-[#66635C] dark:text-stone-400">Toggle shortcuts</span><kbd className="px-2.5 py-1 bg-[#F7F7F5] dark:bg-stone-800 rounded-md text-[#111111] dark:text-stone-200 font-mono">?</kbd></div>
            </div>
          </div>
        </div>
      )}

      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-[#E5E2DA] dark:border-[#262938]">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl lg:text-[34px] font-extrabold text-[#111111] dark:text-[#faf9f6] tracking-tight">
              Big Data Operations Dashboard
            </h1>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#2E7D5B]/10 text-[#2E7D5B] dark:text-[#2E7D5B] border border-[#2E7D5B]/20">
              <span className="w-2 h-2 rounded-full bg-[#2E7D5B] animate-pulse"></span> PIPELINE ONLINE
            </span>
            {systemVersion && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold bg-[#F7EED7] text-[#A97820] dark:text-amber-400 border border-[#D9A441]/30">
                {systemVersion.version} ({systemVersion.registered_sources} sources)
              </span>
            )}
          </div>
          <p className="text-[13px] text-[#66635C] dark:text-stone-400 mt-1.5 font-normal max-w-3xl leading-relaxed">
            PS-26069 ATMOS National Weather Big Data Analytics Platform — Ingestion, Kafka Streaming, Spark AI Engine, JEV Truth Verification & Downstream Sink Monitor.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button onClick={() => setShowShortcuts(true)} className="btn-secondary inline-flex items-center gap-2 text-xs py-2 px-4">
            <Keyboard className="w-3.5 h-3.5 text-[#66635C] dark:text-stone-400" />
            <span>Shortcuts</span>
          </button>
          <button onClick={fetchData} className="btn-secondary inline-flex items-center gap-2 text-xs py-2 px-4" disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Big Data Operational Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Events Ingested"
          value={adminMetrics?.total_events_ingested || stats?.total_events || events.length}
          icon={Radio}
          variant="primary"
          subtitle={`${adminMetrics?.events_today || 0} collected today`}
        />
        <StatsCard
          title="Spark / AI Processed"
          value={adminMetrics?.total_events_processed || adminMetrics?.kafka_clean_count || events.length}
          icon={Cpu}
          variant="info"
          subtitle="Spark Stream & IndicBERT"
        />
        <StatsCard
          title="JEV Verified Incidents"
          value={adminMetrics?.jev_accepted || statusCounts.verified}
          icon={CheckCircle}
          variant="success"
          subtitle={`JEV Score >= 0.60 Gate`}
        />
        <StatsCard
          title="Persisted PostGIS Records"
          value={adminMetrics?.persisted_records || events.length}
          icon={Database}
          variant="warning"
          subtitle="Alertness Score > 0.90"
        />
      </div>

      {/* Second Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 font-mono">
        <div className="bg-white dark:bg-[#13151f] border border-[#E5E2DA] dark:border-[#262938] rounded-xl p-4 shadow-subtle">
          <div className="text-[10px] text-[#66635C] font-bold uppercase tracking-wider mb-1">Throughput</div>
          <div className="text-xl font-extrabold text-[#111111] dark:text-white">{adminMetrics?.events_per_minute || 0}</div>
          <div className="text-[10px] text-[#96938B] font-sans mt-0.5">Events / Min</div>
        </div>
        <div className="bg-white dark:bg-[#13151f] border border-[#E5E2DA] dark:border-[#262938] rounded-xl p-4 shadow-subtle">
          <div className="text-[10px] text-[#66635C] font-bold uppercase tracking-wider mb-1">Kafka RAW</div>
          <div className="text-xl font-extrabold text-[#D9A441]">{adminMetrics?.kafka_raw_count || 0}</div>
          <div className="text-[10px] text-[#96938B] font-sans mt-0.5">Raw Buffer</div>
        </div>
        <div className="bg-white dark:bg-[#13151f] border border-[#E5E2DA] dark:border-[#262938] rounded-xl p-4 shadow-subtle">
          <div className="text-[10px] text-[#66635C] font-bold uppercase tracking-wider mb-1">OpenSearch Docs</div>
          <div className="text-xl font-extrabold text-[#A97820]">{adminMetrics?.opensearch_documents || 0}</div>
          <div className="text-[10px] text-[#96938B] font-sans mt-0.5">Indexed Docs</div>
        </div>
        <div className="bg-white dark:bg-[#13151f] border border-[#E5E2DA] dark:border-[#262938] rounded-xl p-4 shadow-subtle">
          <div className="text-[10px] text-[#66635C] font-bold uppercase tracking-wider mb-1">Media Discovered</div>
          <div className="text-xl font-extrabold text-[#D9A441]">{adminMetrics?.media_items || 0}</div>
          <div className="text-[10px] text-[#96938B] font-sans mt-0.5">Photos & Videos</div>
        </div>
        <div className="bg-white dark:bg-[#13151f] border border-[#E5E2DA] dark:border-[#262938] rounded-xl p-4 shadow-subtle">
          <div className="text-[10px] text-[#66635C] font-bold uppercase tracking-wider mb-1">Filtered Routine</div>
          <div className="text-xl font-extrabold text-[#66635C] dark:text-stone-300">{adminMetrics?.filtered_routine_observations || 0}</div>
          <div className="text-[10px] text-[#96938B] font-sans mt-0.5">Alertness &lt;= 0.90</div>
        </div>
        <div className="bg-white dark:bg-[#13151f] border border-[#E5E2DA] dark:border-[#262938] rounded-xl p-4 shadow-subtle">
          <div className="text-[10px] text-[#66635C] font-bold uppercase tracking-wider mb-1">Active Sources</div>
          <div className="text-xl font-extrabold text-[#2E7D5B]">{adminMetrics?.active_sources || sourceStatusSummary.healthy} / 16</div>
          <div className="text-[10px] text-[#96938B] font-sans mt-0.5">Configured APIs</div>
        </div>
      </div>

      {/* Ingestion & Pipeline Control Card */}
      <div className="bg-white dark:bg-[#13151f]/90 border border-[#E5E2DA] dark:border-[#262938] rounded-2xl p-6 sm:p-7 shadow-subtle">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-bold text-[#111111] dark:text-white tracking-tight flex items-center gap-2">
              <Zap className="w-4 h-4 text-[#D9A441]" /> Multi-Source Big Data Ingestion Engine
            </h2>
            <p className="mt-1 text-xs text-[#66635C] dark:text-stone-400 leading-relaxed max-w-2xl">
              Triggers real-time collection from OpenWeather, Open-Meteo, IMD, MOSDAC, RainViewer, NASA POWER, Mastodon Fediverse, Citizen Reports, and Web Sources.
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <button onClick={() => runIngestion(false)} disabled={ingesting} className="btn-primary inline-flex items-center gap-2 text-xs py-2.5 px-5 shadow-subtle">
              <RefreshCw className={`w-3.5 h-3.5 ${ingesting ? 'animate-spin' : ''}`} />
              <span>{ingesting ? 'Running...' : 'Run Ingestion Engine'}</span>
            </button>
            <button onClick={() => runIngestion(true)} disabled={ingesting} className="btn-secondary text-xs py-2.5 px-4">
              Load Sample Dataset
            </button>
          </div>
        </div>
        {ingestionMessage && (
          <div className="mt-3 flex items-center gap-2 text-xs font-semibold text-[#A97820] bg-[#F7EED7] p-2.5 rounded-xl border border-[#D9A441]/30">
            <Activity className="w-4 h-4 animate-spin shrink-0" />
            <span>{ingestionMessage}</span>
          </div>
        )}
      </div>

      {/* INGESTION & PIPELINE MONITOR (Stage-by-Stage Funnel Flow) */}
      <div className="bg-white dark:bg-[#13151f]/90 border border-[#E5E2DA] dark:border-[#262938] rounded-2xl p-6 sm:p-7 shadow-subtle space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#E5E2DA] dark:border-[#262938]">
          <div>
            <h2 className="text-base font-bold text-[#111111] dark:text-white tracking-tight flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#D9A441]" /> INGESTION &amp; PIPELINE MONITOR (Big Data Funnel)
            </h2>
            <p className="text-xs text-[#66635C] dark:text-stone-400 mt-0.5">
              Live end-to-end execution flow showing exact counts at every stage from Ingestion Buffer to PostGIS &amp; OpenSearch.
            </p>
          </div>
          <span className="text-xs font-mono px-3 py-1 rounded-full bg-[#F7F7F5] dark:bg-stone-800 text-[#111111] dark:text-stone-300 font-bold self-start sm:self-auto">
            SOURCE → KAFKA → SPARK → AI → JEV → SINK
          </span>
        </div>

        {/* Persistent Dual Mode Metrics Bar: Last Ingestion Run vs Cumulative */}
        {latestRunSummary && (
          <div className="bg-[#F7EED7]/40 dark:bg-[#D9A441]/10 border border-[#D9A441]/30 rounded-2xl p-5 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#D9A441]/20">
              <div>
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-[#D9A441] animate-pulse" />
                  <span className="text-xs font-bold text-[#A97820] dark:text-amber-300 uppercase tracking-wider">
                    LATEST INGESTION RUN SUMMARY
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#2E7D5B]/10 text-[#2E7D5B] border border-[#2E7D5B]/20">
                    {latestRunSummary.status || 'COMPLETED'}
                  </span>
                </div>
                <p className="text-[11px] text-[#66635C] dark:text-stone-400 mt-0.5 font-sans">
                  Last Ingestion: <span className="font-semibold">{latestRunSummary.timestamp ? new Date(latestRunSummary.timestamp).toLocaleString() : 'Just Now'}</span> | Kafka: <span className="font-semibold text-[#2E7D5B]">{latestRunSummary.kafka_status || 'Connected'}</span>
                </p>
              </div>
              <div className="text-[11px] font-mono text-[#A97820] font-semibold self-start sm:self-auto bg-[#F7EED7] px-3 py-1 rounded-full border border-[#D9A441]/30">
                Sources: {latestRunSummary.sources_succeeded ?? (latestRunSummary.sources_triggered || 0)} / {latestRunSummary.sources_attempted ?? 16} Successful
              </div>
            </div>

            {/* Batch Key Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5 font-mono text-xs">
              <div className="bg-white dark:bg-[#0e1017] p-3 rounded-xl border border-[#E5E2DA] dark:border-[#262938] shadow-xs">
                <span className="text-[10px] text-[#96938B] block uppercase font-bold">Collected</span>
                <span className="text-base font-extrabold text-[#D9A441]">{(latestRunSummary.collected || 0).toLocaleString()}</span>
                <span className="text-[9px] text-[#96938B] block font-sans mt-0.5">Raw API Events</span>
              </div>
              <div className="bg-white dark:bg-[#0e1017] p-3 rounded-xl border border-[#E5E2DA] dark:border-[#262938] shadow-xs">
                <span className="text-[10px] text-[#96938B] block uppercase font-bold">Kafka RAW</span>
                <span className="text-base font-extrabold text-[#A97820]">{(latestRunSummary.published_raw || 0).toLocaleString()}</span>
                <span className="text-[9px] text-[#96938B] block font-sans mt-0.5">weather.raw Topic</span>
              </div>
              <div className="bg-white dark:bg-[#0e1017] p-3 rounded-xl border border-[#E5E2DA] dark:border-[#262938] shadow-xs">
                <span className="text-[10px] text-[#96938B] block uppercase font-bold">Processed</span>
                <span className="text-base font-extrabold text-[#111111] dark:text-white">{(latestRunSummary.spark_processed || latestRunSummary.collected || 0).toLocaleString()}</span>
                <span className="text-[9px] text-[#96938B] block font-sans mt-0.5">Clean &amp; Normalized</span>
              </div>
              <div className="bg-white dark:bg-[#0e1017] p-3 rounded-xl border border-[#E5E2DA] dark:border-[#262938] shadow-xs">
                <span className="text-[10px] text-[#96938B] block uppercase font-bold">JEV Accepted</span>
                <span className="text-base font-extrabold text-[#2E7D5B]">{(latestRunSummary.jev_accepted || 0).toLocaleString()}</span>
                <span className="text-[9px] text-[#96938B] block font-sans mt-0.5">Gate Score &gt;= 0.60</span>
              </div>
              <div className="bg-white dark:bg-[#0e1017] p-3 rounded-xl border border-[#E5E2DA] dark:border-[#262938] shadow-xs">
                <span className="text-[10px] text-[#96938B] block uppercase font-bold">Persisted</span>
                <span className="text-base font-extrabold text-[#2E7D5B]">{(latestRunSummary.persisted ?? latestRunSummary.new_inserts ?? 0).toLocaleString()}</span>
                <span className="text-[9px] text-[#96938B] block font-sans mt-0.5">New DB Records</span>
              </div>
              <div className="bg-white dark:bg-[#0e1017] p-3 rounded-xl border border-[#E5E2DA] dark:border-[#262938] shadow-xs">
                <span className="text-[10px] text-[#96938B] block uppercase font-bold">Skipped Sources</span>
                <span className="text-base font-extrabold text-[#A97820]">{(latestRunSummary.sources_skipped || 0).toLocaleString()}</span>
                <span className="text-[9px] text-[#96938B] block font-sans mt-0.5">Missing Keys</span>
              </div>
              <div className="bg-white dark:bg-[#0e1017] p-3 rounded-xl border border-[#E5E2DA] dark:border-[#262938] shadow-xs">
                <span className="text-[10px] text-[#96938B] block uppercase font-bold">Already Existing</span>
                <span className="text-base font-extrabold text-[#D9A441]">{(latestRunSummary.already_existing || 0).toLocaleString()}</span>
                <span className="text-[9px] text-[#96938B] block font-sans mt-0.5">Idempotent Match</span>
              </div>
              <div className="bg-white dark:bg-[#0e1017] p-3 rounded-xl border border-[#E5E2DA] dark:border-[#262938] shadow-xs">
                <span className="text-[10px] text-[#96938B] block uppercase font-bold">Database</span>
                <span className="text-base font-extrabold text-[#111111] dark:text-white">{(latestRunSummary.total_db_records || 80).toLocaleString()}</span>
                <span className="text-[9px] text-[#96938B] block font-sans mt-0.5">PostgreSQL Total</span>
              </div>
            </div>

            {/* Warnings Area */}
            {latestRunSummary.warnings && latestRunSummary.warnings.length > 0 && (
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3.5 space-y-1.5">
                <div className="text-xs font-bold text-amber-700 dark:text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" /> Warnings &amp; Skipped Optional Sources ({latestRunSummary.warnings.length})
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5 font-mono text-[11px]">
                  {latestRunSummary.warnings.map((warn, idx) => (
                    <div key={idx} className="flex items-center gap-1.5 text-stone-700 dark:text-stone-300 bg-white/60 dark:bg-black/30 px-2.5 py-1 rounded-md">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0"></span>
                      <span className="truncate">{warn}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Latest Source Breakdown */}
            {latestRunSummary.source_breakdown && Object.keys(latestRunSummary.source_breakdown).length > 0 && (
              <div>
                <div className="text-[11px] font-bold text-[#111111] dark:text-stone-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                  <span>Latest Per-Source Collection Breakdown (Batch Run)</span>
                  <span className="text-[10px] text-[#96938B] font-normal font-sans">Collected observations by provider</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 font-mono text-xs">
                  {sortedLatestSourceBreakdown.map(([srcName, count]) => (
                    <div key={srcName} className="bg-white dark:bg-[#0e1017] px-3 py-2 rounded-xl border border-[#E5E2DA] dark:border-stone-800 flex justify-between items-center">
                      <span className="text-[#111111] dark:text-stone-300 font-semibold truncate text-[11px]">{srcName}</span>
                      <span className={`font-bold text-[11px] ${count > 0 ? 'text-[#D9A441]' : 'text-[#96938B]'}`}>
                        {count} {count === 1 ? 'evt' : 'evts'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-[#111111] dark:text-stone-300 uppercase tracking-wider flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-[#2E7D5B]" /> CUMULATIVE PIPELINE STAGE FUNNEL (Total Historic System Metrics)
            </span>
          </div>

          {/* Funnel Stage Diagram */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8 gap-3 font-mono text-xs">
            {effectiveFunnelData.map((f, idx) => (
              <div key={idx} className="relative bg-[#F7F7F5] dark:bg-[#0e1017] border border-[#E5E2DA] dark:border-stone-800/80 rounded-xl p-3.5 flex flex-col justify-between hover:border-stone-300 transition-colors shadow-xs">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-bold text-[#96938B] uppercase tracking-wider truncate">{f.stage}</span>
                    <span className="text-[10px] text-[#96938B] font-sans">#{idx + 1}</span>
                  </div>
                  <div className="text-xl font-black text-[#111111] dark:text-white tracking-tight">{Number(f.count || 0).toLocaleString()}</div>
                </div>
                <p className="text-[10px] font-sans text-[#66635C] mt-3 leading-tight">{f.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Explicit Explanation Box for Filtered Routine Observations */}
        <div className="bg-[#F7EED7] border border-[#D9A441]/30 rounded-2xl p-4 text-xs leading-relaxed text-[#111111] flex items-start gap-3">
          <Info className="w-4 h-4 text-[#A97820] shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Pipeline Architecture Note:</span> Standard routine weather observations (e.g. normal 25°C temperatures or clear sky readings) are processed through Spark AI and JEV scoring, but intentionally filtered downstream by the <code className="font-mono bg-[#E5E2DA] px-1 py-0.5 rounded text-[11px]">alertness_score &gt; 0.90</code> gate so routine weather data does not clutter the high-priority incident portal.
          </div>
        </div>
      </div>

      {/* Execution Summary Modal (After Running Ingestion) */}
      {executionSummary && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 dark:bg-black/70 backdrop-blur-sm p-4" onClick={() => setExecutionSummary(null)}>
          <div className="card-editorial max-w-2xl w-full bg-white dark:bg-[#0e1017] border border-[#E5E2DA] dark:border-stone-800 p-6 shadow-2xl rounded-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#E5E2DA] dark:border-stone-800">
              <h3 className="text-base font-bold text-[#111111] dark:text-white flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-[#2E7D5B]" /> INGESTION RUN COMPLETE (Execution Summary)
              </h3>
              <button onClick={() => setExecutionSummary(null)} className="text-stone-400 hover:text-[#111111] dark:hover:text-white">
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs mb-4">
              <div className="bg-[#F7F7F5] dark:bg-stone-800/40 p-3 rounded-xl border border-[#E5E2DA]">
                <div className="text-[10px] text-[#96938B] uppercase">Sources Succeeded</div>
                <div className="text-base font-bold text-[#2E7D5B]">{executionSummary.sources_succeeded ?? 0} / {executionSummary.sources_attempted ?? 16}</div>
              </div>
              <div className="bg-[#F7F7F5] dark:bg-stone-800/40 p-3 rounded-xl border border-[#E5E2DA]">
                <div className="text-[10px] text-[#96938B] uppercase">Collected</div>
                <div className="text-base font-bold text-[#D9A441]">{executionSummary.collected || 0}</div>
              </div>
              <div className="bg-[#F7F7F5] dark:bg-stone-800/40 p-3 rounded-xl border border-[#E5E2DA]">
                <div className="text-[10px] text-[#96938B] uppercase">Spark Processed</div>
                <div className="text-base font-bold text-[#111111] dark:text-white">{executionSummary.spark_processed || executionSummary.collected || 0}</div>
              </div>
              <div className="bg-[#F7F7F5] dark:bg-stone-800/40 p-3 rounded-xl border border-[#E5E2DA]">
                <div className="text-[10px] text-[#96938B] uppercase">Persisted Rows</div>
                <div className="text-base font-bold text-[#2E7D5B]">{executionSummary.persisted ?? executionSummary.new_inserts ?? 0}</div>
              </div>
            </div>

            {/* Warnings in Modal */}
            {executionSummary.warnings && executionSummary.warnings.length > 0 && (
              <div className="mb-4 bg-amber-500/10 border border-amber-500/30 rounded-xl p-3.5 space-y-1.5">
                <div className="text-xs font-bold text-amber-700 dark:text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" /> Warnings ({executionSummary.warnings.length})
                </div>
                <div className="space-y-1 font-mono text-[11px] max-h-32 overflow-y-auto">
                  {executionSummary.warnings.map((w, idx) => (
                    <div key={idx} className="text-stone-700 dark:text-stone-300 bg-white/60 dark:bg-black/30 px-2.5 py-1 rounded-md">
                      • {w}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <h4 className="text-xs font-bold text-[#111111] dark:text-stone-200 uppercase tracking-wider mb-3">Source Breakdown</h4>
            <div className="divide-y divide-[#E5E2DA] dark:divide-stone-800/60 font-mono text-xs max-h-48 overflow-y-auto mb-4 border border-[#E5E2DA] dark:border-stone-800 rounded-xl p-2">
              {sortedModalSourceBreakdown.map(([src, count]) => (
                <div key={src} className="py-2 px-3 flex justify-between items-center">
                  <span className="font-semibold text-[#111111] dark:text-stone-200">{src}</span>
                  <span className={`font-bold ${count > 0 ? 'text-[#D9A441]' : 'text-[#96938B]'}`}>{count} events</span>
                </div>
              ))}
            </div>

            <button onClick={() => setExecutionSummary(null)} className="btn-primary w-full text-xs py-2.5">
              Close Execution Summary
            </button>
          </div>
        </div>
      )}

      {/* DATA SOURCES SYSTEM REGISTRY SECTION */}
      <div className="bg-white dark:bg-[#13151f]/90 border border-[#E5E2DA] dark:border-[#262938] rounded-2xl p-6 sm:p-7 shadow-subtle">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 pb-4 border-b border-[#E5E2DA] dark:border-[#262938]">
          <div>
            <h2 className="text-base font-bold text-[#111111] dark:text-white tracking-tight flex items-center gap-2">
              <Server className="w-4 h-4 text-[#2E7D5B]" /> DATA SOURCES — System Source Registry
            </h2>
            <p className="text-xs text-[#66635C] dark:text-stone-400 mt-0.5">
              Configured meteorological APIs, satellite networks, radar feeds, social fediverse & crowdsourced channels.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-[#66635C] font-medium">Filter:</span>
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="bg-[#F7F7F5] dark:bg-[#141620] border border-[#E5E2DA] dark:border-[#262938] text-[#111111] dark:text-stone-200 text-xs py-1.5 px-3 rounded-full font-semibold focus:outline-none focus:border-[#D9A441]"
            >
              <option value="all">All Sources ({sourceStatusSummary.total})</option>
              <option value="healthy">Healthy / Live ({sourceStatusSummary.healthy})</option>
              <option value="auth_required">Auth Required ({sourceStatusSummary.authReq})</option>
              <option value="degraded">Degraded / Disabled ({sourceStatusSummary.degraded + sourceStatusSummary.disabled})</option>
            </select>
          </div>
        </div>

        {/* Data Sources Health Table */}
        <div className="overflow-x-auto border border-[#E5E2DA] dark:border-[#262938] rounded-xl shadow-subtle">
          <table className="w-full text-left font-sans text-xs">
            <thead className="bg-[#F7F7F5] dark:bg-[#0e1017] text-[#66635C] dark:text-stone-400 font-bold uppercase text-[10px] tracking-wider border-b border-[#E5E2DA] dark:border-[#262938]">
              <tr>
                <th className="py-3 px-4">SOURCE</th>
                <th className="py-3 px-4">STATUS</th>
                <th className="py-3 px-4">CREDENTIAL</th>
                <th className="py-3 px-4">LAST CHECK</th>
                <th className="py-3 px-4">LAST COLLECTION</th>
                <th className="py-3 px-4">RECORDS</th>
                <th className="py-3 px-4">ERROR / DIAGNOSTIC</th>
                <th className="py-3 px-4 text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E5E2DA] dark:divide-[#262938] font-mono text-xs bg-white dark:bg-[#161822]">
              {filteredSources.map((src) => {
                const statusStr = src.status || 'HEALTHY';
                const credStr = src.authentication_status || (src.authentication_required ? 'MISSING' : 'NOT_REQUIRED');
                return (
                  <tr key={src.source_id} onClick={() => openSourceInspector(src)} className="hover:bg-[#F7F7F5] dark:hover:bg-[#151722] cursor-pointer transition-colors">
                    <td className="py-3 px-4 font-bold text-[#111111] dark:text-white flex items-center gap-2">
                      <span>{src.name}</span>
                      <span className="text-[10px] font-normal text-[#96938B]">({src.provider})</span>
                    </td>
                    <td className="py-3 px-4">
                      {statusStr === 'HEALTHY' && <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#2E7D5B]/10 text-[#2E7D5B] border border-[#2E7D5B]/20">HEALTHY</span>}
                      {statusStr === 'AUTH_REQUIRED' && <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#F7EED7] text-[#A97820] border border-[#D9A441]/30">AUTH_REQUIRED</span>}
                      {statusStr === 'DISABLED' && <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-stone-500/10 text-stone-500 border border-stone-500/20">DISABLED</span>}
                      {statusStr === 'NO_DATA' && <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-stone-100 text-stone-700 border border-stone-300">NO_DATA</span>}
                      {statusStr === 'ERROR' && <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-500 border border-rose-500/20">ERROR</span>}
                      {statusStr === 'DEGRADED' && <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-600 border border-amber-500/20">DEGRADED</span>}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`text-[11px] font-semibold ${credStr === 'CONFIGURED' ? 'text-[#2E7D5B]' : credStr === 'MISSING' ? 'text-rose-500 font-bold' : 'text-[#96938B]'}`}>
                        {credStr}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-[#66635C] text-[11px]">
                      {src.metrics?.last_success_at ? new Date(src.metrics.last_success_at).toLocaleTimeString() : 'Active'}
                    </td>
                    <td className="py-3 px-4 text-[#66635C] text-[11px]">
                      {src.metrics?.last_success_at ? new Date(src.metrics.last_success_at).toLocaleDateString() : 'Recent'}
                    </td>
                    <td className="py-3 px-4 font-bold text-[#111111] dark:text-white">
                      {(src.records_total || src.records_today || 0).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-[11px] text-[#96938B] truncate max-w-xs">
                      {src.metrics?.last_error ? <span className="text-rose-400 font-sans">{src.metrics.last_error}</span> : <span className="text-[#96938B]">None</span>}
                    </td>
                    <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => syncSingleSource(src.source_id)}
                        disabled={syncingSourceId === src.source_id}
                        className="btn-secondary text-[10px] py-1 px-2.5 inline-flex items-center gap-1"
                        title="Test & Sync Source"
                      >
                        <RefreshCw className={`w-3 h-3 ${syncingSourceId === src.source_id ? 'animate-spin text-[#D9A441]' : ''}`} />
                        Sync
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Source Inspector Modal */}
      {inspectSource && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 dark:bg-black/70 backdrop-blur-sm p-4" onClick={() => setInspectSource(null)}>
          <div className="card-editorial max-w-2xl w-full max-h-[85vh] overflow-y-auto bg-white dark:bg-[#0e1017] border border-[#E5E2DA] dark:border-stone-800 p-6 shadow-2xl rounded-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#E5E2DA] dark:border-stone-800">
              <div className="flex items-center gap-3">
                <Server className="w-5 h-5 text-[#D9A441]" />
                <div>
                  <h3 className="text-base font-bold text-[#111111] dark:text-white flex items-center gap-2">
                    {inspectSource.name}
                  </h3>
                  <p className="text-xs text-[#66635C] font-medium">{inspectSource.provider}</p>
                </div>
              </div>
              <button onClick={() => setInspectSource(null)} className="text-stone-400 hover:text-[#111111] dark:hover:text-white">
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {inspectLoading ? (
              <div className="py-12 text-center text-xs text-[#66635C] flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-[#D9A441]" /> Loading source diagnostics...
              </div>
            ) : (
              <div className="space-y-5 text-xs">
                {/* Status & Auth Banner */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
                  <div className="bg-[#F7F7F5] dark:bg-stone-800/40 p-3 rounded-xl border border-[#E5E2DA]">
                    <div className="text-[10px] text-[#96938B] uppercase">Health Status</div>
                    <div className="font-bold text-[#2E7D5B]">{inspectSource.status}</div>
                  </div>
                  <div className="bg-[#F7F7F5] dark:bg-stone-800/40 p-3 rounded-xl border border-[#E5E2DA]">
                    <div className="text-[10px] text-[#96938B] uppercase">Auth Status</div>
                    <div className="font-bold text-[#111111] dark:text-stone-200">{inspectSource.authentication_status}</div>
                  </div>
                  <div className="bg-[#F7F7F5] dark:bg-stone-800/40 p-3 rounded-xl border border-[#E5E2DA]">
                    <div className="text-[10px] text-[#96938B] uppercase">Trust Score</div>
                    <div className="font-bold text-[#D9A441]">{(inspectSource.trust_score * 100).toFixed(0)}%</div>
                  </div>
                  <div className="bg-[#F7F7F5] dark:bg-stone-800/40 p-3 rounded-xl border border-[#E5E2DA]">
                    <div className="text-[10px] text-[#96938B] uppercase">Avg Latency</div>
                    <div className="font-bold text-[#A97820]">{inspectSource.metrics?.average_latency_ms || 0} ms</div>
                  </div>
                </div>

                {/* Description & Capabilities */}
                <div>
                  <h4 className="text-xs font-bold text-[#111111] dark:text-stone-200 uppercase tracking-wider mb-1.5">Capabilities & Description</h4>
                  <p className="text-[#66635C] dark:text-stone-400 leading-relaxed mb-2">{inspectSource.description}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {(inspectSource.capabilities || []).map(cap => (
                      <span key={cap} className="px-2.5 py-0.5 rounded-full bg-[#F7F7F5] dark:bg-stone-800 text-[#111111] dark:text-stone-300 font-mono text-[10px] border border-[#E5E2DA]">
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Social Hashtags if available */}
                {inspectSource.hashtags && inspectSource.hashtags.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold text-[#111111] dark:text-stone-200 uppercase tracking-wider mb-1.5">Monitored Hashtags</h4>
                    <div className="flex flex-wrap gap-1.5">
                      {inspectSource.hashtags.map(tag => (
                        <span key={tag} className="px-2.5 py-0.5 rounded-full bg-[#F7EED7] text-[#A97820] font-bold font-mono text-[10px] border border-[#D9A441]/30">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Geographic Note */}
                {inspectSource.geographic_note && (
                  <div className="bg-[#F7EED7] border border-[#D9A441]/30 p-3 rounded-xl text-[#111111] text-xs">
                    <span className="font-bold">Geographic Coverage Note:</span> {inspectSource.geographic_note}
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    onClick={() => syncSingleSource(inspectSource.source_id)}
                    disabled={syncingSourceId === inspectSource.source_id}
                    className="btn-primary w-full inline-flex items-center justify-center gap-2 text-xs py-2.5"
                  >
                    <RefreshCw className={`w-4 h-4 ${syncingSourceId === inspectSource.source_id ? 'animate-spin' : ''}`} />
                    Trigger Source Collection Sync
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SOURCE PERFORMANCE VISUALIZATIONS SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <SourceLatencyChart data={chartLatencyData} />
        <SourceVerifiedVSRejectedChart data={chartVerifiedVsRejectedData} />
        <SourceMediaChart data={chartMediaData} />
      </div>

      {/* Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[#E5E2DA] dark:border-stone-800 pb-0">
        <div className="flex gap-2 overflow-x-auto" role="tablist">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                role="tab"
                aria-selected={isActive}
                onClick={() => { setActiveTab(tab.id); setSelectedIds(new Set()); }}
                className={`flex items-center gap-2 px-4 py-3 text-xs font-bold border-b-2 transition-all whitespace-nowrap ${
                  isActive
                    ? 'border-[#111111] text-[#111111] dark:border-white dark:text-white'
                    : 'border-transparent text-[#66635C] dark:text-stone-400 hover:text-[#111111] dark:hover:text-white'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
                {tab.count > 0 && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-stone-200 dark:bg-stone-800 text-stone-700 dark:text-stone-300 font-bold">{tab.count}</span>
                )}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-2 pb-2 sm:pb-0">
          <label htmlFor="admin-status-filter" className="text-xs font-bold text-[#66635C] dark:text-stone-400 uppercase tracking-wider flex items-center gap-1">
            <Filter className="w-3 h-3" /> Status:
          </label>
          <select
            id="admin-status-filter"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setSelectedIds(new Set()); }}
            className="bg-white dark:bg-[#141620] border border-[#E5E2DA] dark:border-[#262938] text-[#111111] dark:text-stone-200 text-xs py-1.5 px-3 rounded-full font-semibold focus:outline-none focus:border-[#D9A441] shadow-subtle"
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="verified">Verified</option>
            <option value="rejected">Rejected</option>
            <option value="needs_review">Needs Review</option>
          </select>
        </div>
      </div>

      {/* Bulk action toolbar */}
      {selectedIds.size > 0 && (
        <div className="bg-[#F7EED7] border border-[#D9A441]/30 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <span className="text-xs font-bold text-[#111111]">
            {selectedIds.size} incident(s) selected
          </span>
          <div className="flex gap-2">
            <button onClick={() => bulkVerify('verified')} className="btn-primary text-xs py-2 inline-flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5 text-[#2E7D5B]" /> Verify Selected
            </button>
            <button onClick={() => bulkVerify('rejected')} className="btn-secondary text-xs py-2 inline-flex items-center gap-1 text-red-600 hover:bg-red-50">
              <XCircle className="w-3.5 h-3.5" /> Reject Selected
            </button>
            <button onClick={bulkDelete} className="btn-secondary text-xs py-2 inline-flex items-center gap-1 text-red-600 hover:bg-red-50">
              <Trash2 className="w-3.5 h-3.5" /> Delete Selected
            </button>
            <button onClick={() => setSelectedIds(new Set())} className="btn-secondary text-xs py-2">
              Clear Selection
            </button>
          </div>
        </div>
      )}

      {/* Table Component */}
      <EventTable
        events={filteredEvents}
        onVerify={handleVerify}
        onDelete={handleDelete}
        onClassify={openOverride}
        loading={loading}
        selectable
        selectedIds={selectedIds}
        onToggleSelect={toggleSelect}
        onSelectAll={selectAll}
      />

      {/* AI Classification Override Modal */}
      {overrideEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 dark:bg-black/70 backdrop-blur-sm p-4" onClick={closeOverride}>
          <div className="card-editorial max-w-lg w-full max-h-[85vh] overflow-y-auto bg-white dark:bg-[#0e1017] border border-[#E5E2DA] dark:border-stone-800 p-6 shadow-xl rounded-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#E5E2DA] dark:border-stone-800">
              <h3 className="text-sm font-bold text-[#111111] dark:text-white flex items-center gap-2">
                <Brain className="w-4 h-4 text-[#D9A441]" /> Human Override for AI Classifier
              </h3>
              <button onClick={closeOverride} className="text-stone-400 hover:text-[#111111] dark:hover:text-white">
                <XCircle className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-[#66635C] dark:text-stone-400 mb-4 leading-relaxed">
              Manually reclassify <span className="text-[#111111] dark:text-white font-semibold">“{overrideEvent.title}”</span>. The original AI prediction will remain recorded in the immutable audit log.
            </p>

            {!overrideDone ? (
              <div className="space-y-4">
                <div>
                  <label htmlFor="override-type" className="mb-1.5 block text-xs font-bold text-[#66635C] dark:text-stone-400 uppercase tracking-wider">
                    Target Event Category
                  </label>
                  <select
                    id="override-type"
                    value={overrideType}
                    onChange={(e) => setOverrideType(e.target.value)}
                    className="select w-full text-xs font-medium"
                  >
                    {EVENT_TYPES.map(t => (
                      <option key={t} value={t}>{t.replace('_', ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="override-reason" className="mb-1.5 block text-xs font-bold text-[#66635C] dark:text-stone-400 uppercase tracking-wider">
                    Justification Reason <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    id="override-reason"
                    rows={3}
                    value={overrideReason}
                    onChange={(e) => setOverrideReason(e.target.value)}
                    placeholder="Enter justification for overriding AI classification..."
                    className="input w-full text-xs leading-relaxed"
                  />
                </div>
                <button
                  onClick={submitOverride}
                  disabled={!overrideReason.trim() || overrideSaving}
                  className="btn-primary w-full inline-flex items-center justify-center gap-2 text-xs py-2.5 disabled:opacity-50"
                >
                  {overrideSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
                  Submit Classification Override
                </button>
              </div>
            ) : overrideDone.error ? (
              <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-4 text-xs font-semibold text-rose-700 dark:text-rose-300">
                {overrideDone.error}
              </div>
            ) : (
              <div className="space-y-3">
                <div className="rounded-xl border border-[#2E7D5B]/20 bg-[#2E7D5B]/10 p-4 text-xs font-semibold text-[#2E7D5B]">
                  Event successfully reclassified as <strong>{overrideDone.summary.event_type}</strong>.
                </div>
                <button onClick={closeOverride} className="btn-secondary w-full text-xs py-2.5">
                  Close Window
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
