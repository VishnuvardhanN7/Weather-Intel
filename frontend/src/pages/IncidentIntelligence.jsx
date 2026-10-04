import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../services/api.js';
import {
  ArrowLeft,
  ShieldCheck,
  AlertTriangle,
  Fingerprint,
  Activity,
  BarChart3,
  Clock,
  Layers,
  CheckCircle2,
  XCircle,
  Loader2,
  ExternalLink,
} from 'lucide-react';

const STATUS_META = {
  VERIFIED: { color: 'text-[#2E7D5B] bg-[#2E7D5B]/10 border-[#2E7D5B]/20', icon: CheckCircle2 },
  PROBABLE: { color: 'text-[#A97820] bg-[#F7EED7] border-[#D9A441]/30', icon: CheckCircle2 },
  NEEDS_REVIEW: { color: 'text-amber-700 dark:text-amber-400 bg-amber-500/10 border-amber-500/20', icon: AlertTriangle },
  UNVERIFIED: { color: 'text-[#66635C] dark:text-stone-400 bg-stone-100 dark:bg-stone-800 border-[#E5E2DA] dark:border-stone-700', icon: AlertTriangle },
  REJECTED: { color: 'text-rose-700 dark:text-rose-400 bg-rose-500/10 border-rose-500/20', icon: XCircle },
};

const TYPE_LABELS = {
  rainfall: 'Rainfall',
  thunderstorm: 'Thunderstorm',
  flooding: 'Flooding',
  heatwave: 'Heatwave',
  fog: 'Fog',
  dust_storm: 'Dust Storm',
  strong_winds: 'Strong Winds',
  cyclone: 'Cyclone',
  other: 'Other',
};

const SEVERITY_LABELS = {
  LOW: 'Low',
  MODERATE: 'Moderate',
  HIGH: 'High',
  CRITICAL: 'Critical',
};

function Badge({ status, label }) {
  const meta = STATUS_META[status] || STATUS_META.UNVERIFIED;
  const Icon = meta.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold ${meta.color}`}>
      <Icon className="h-3.5 w-3.5" />
      {label || status}
    </span>
  );
}

function ScoreRing({ score }) {
  const clamped = Math.max(0, Math.min(100, score || 0));
  const color = clamped >= 75 ? '#2E7D5B' : clamped >= 50 ? '#D9A441' : clamped >= 25 ? '#E2B84A' : '#EF4444';
  const circumference = 2 * Math.PI * 42;
  const offset = circumference - (clamped / 100) * circumference;
  return (
    <div className="relative h-28 w-28">
      <svg viewBox="0 0 100 100" className="h-28 w-28 -rotate-90">
        <circle cx="50" cy="50" r="42" fill="none" className="stroke-[#E5E2DA] dark:stroke-[#262838]" strokeWidth="9" />
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke={color}
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 600ms ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-black text-[#111111] dark:text-white">{Math.round(clamped)}</span>
        <span className="text-[10px] uppercase font-bold tracking-widest text-[#96938B]">/ 100</span>
      </div>
    </div>
  );
}

function Card({ title, icon: Icon, children, className = '' }) {
  return (
    <section className={`rounded-2xl border border-[#E5E2DA] dark:border-stone-800 bg-white dark:bg-[#13151f]/90 p-6 shadow-subtle ${className}`}>
      <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-[#111111] dark:text-[#faf9f6] tracking-tight">
        {Icon && <Icon className="h-4 w-4 text-[#D9A441]" />}
        {title}
      </h2>
      {children}
    </section>
  );
}

function BreakdownBar({ label, value, max = 25 }) {
  const v = Math.max(0, Math.min(max, value || 0));
  const pct = (v / max) * 100;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-[#66635C] dark:text-stone-400 font-medium">{label}</span>
        <span className="font-bold text-[#111111] dark:text-white">{v.toFixed(1)}</span>
      </div>
      <div className="h-2 rounded-full bg-stone-100 dark:bg-stone-800">
        <div
          className="h-2 rounded-full bg-[#D9A441]"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function fmtTime(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export default function IncidentIntelligence() {
  const { eventId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const res = await api.get(`/api/intelligence/events/${eventId}`);
        if (!cancelled) {
          setData(res.data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError('Unable to load intelligence data for this event.');
      }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
  }, [eventId]);

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 p-6">
        <div className="flex items-center justify-center py-24 text-[#66635C] font-medium">
          <Loader2 className="mr-3 h-5 w-5 animate-spin text-[#D9A441]" />
          Loading intelligence dossier...
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 p-6">
        <Link to="/events" className="inline-flex items-center gap-2 text-xs font-bold text-[#66635C] hover:text-[#111111]">
          <ArrowLeft className="h-4 w-4" /> Back to incidents
        </Link>
        <div className="rounded-2xl border border-[#E5E2DA] dark:border-stone-800 bg-white dark:bg-[#13151f] p-6 text-center text-xs font-semibold text-rose-600 shadow-subtle">
          {error || 'No intelligence dossier available.'}
        </div>
      </div>
    );
  }

  const event = data.event;
  const intel = data.intelligence || {};
  const classification = intel.classification || {};
  const verification = intel.verification || {};
  const severityData = intel.severity || {};
  const sourceTrust = intel.source_trust || {};
  const corroboration = intel.corroboration || {};
  const explanation = intel.explanation || {};
  const timeline = intel.timeline || [];
  const breakdown = verification.breakdown || {};

  const verificationStatus = event.verification_status || 'unverified';
  const verifyStatusUpper = String(verificationStatus).toUpperCase().replace('_', ' ');

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      
      {/* Navigation & Header Badges */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link to="/events" className="inline-flex items-center gap-2 text-xs font-bold text-[#66635C] hover:text-[#111111] transition-colors">
          <ArrowLeft className="h-4 w-4 text-[#D9A441]" /> Back to Incidents
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <Badge status={verificationStatus} label={verifyStatusUpper} />
          <span className="rounded-full border border-[#E5E2DA] dark:border-stone-800 bg-stone-100 dark:bg-[#141620] px-3 py-1 text-xs font-bold text-[#111111] dark:text-stone-300">
            {TYPE_LABELS[event.event_type] || event.event_type}
          </span>
        </div>
      </div>

      <header className="rounded-2xl border border-[#E5E2DA] dark:border-stone-800 bg-white dark:bg-[#13151f] p-6 sm:p-8 shadow-subtle">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-[#111111] dark:text-[#faf9f6] tracking-tight">{event.title}</h1>
        <p className="mt-2 text-xs text-[#66635C] dark:text-stone-300 leading-relaxed max-w-3xl">{event.description}</p>
        <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-xs font-medium text-[#96938B] pt-4 border-t border-[#E5E2DA] dark:border-stone-800">
          <span>📍 {event.city || 'Unknown city'}{event.state ? `, ${event.state}` : ''}</span>
          <span>🕒 Reported {fmtTime(event.reported_at)}</span>
          {event.latitude != null && (
            <span>🧭 {event.latitude.toFixed(4)}, {event.longitude.toFixed(4)}</span>
          )}
        </div>
      </header>

      {/* AI Decision / WHY TRUST THIS EVENT */}
      <Card title="AI Decision — Intelligence Justification" icon={ShieldCheck} className="border-[#D9A441]/30">
        <div className="grid gap-6 md:grid-cols-[auto_1fr]">
          <div className="flex flex-col items-center gap-2">
            <ScoreRing score={verification.score} />
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#96938B]">
              Verification Index
            </span>
            <span className="text-[10px] text-[#96938B]">Model v{verification.version || '1.0'}</span>
          </div>
          <div className="space-y-3">
            {verification.reasoning && (
              <p className="rounded-xl border border-[#E5E2DA] dark:border-stone-800 bg-[#F7F7F5] dark:bg-[#0e1017] p-4 text-xs font-medium text-[#111111] dark:text-stone-200 leading-relaxed">
                {verification.reasoning}
              </p>
            )}
            {explanation.verification_reason && (
              <p className="text-xs text-[#66635C] dark:text-stone-300 font-medium">{explanation.verification_reason}</p>
            )}
            {verification.evidence?.length > 0 && (
              <ul className="space-y-1.5 pt-2">
                {verification.evidence.map((e, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-[#111111] dark:text-stone-300">
                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#2E7D5B]" />
                    {e}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Verification Component Scores" icon={BarChart3}>
          {Object.keys(breakdown).length > 0 ? (
            <div className="space-y-3">
              <BreakdownBar label="Source Reliability" value={breakdown.source_reliability} />
              <BreakdownBar label="Cross-Source Corroboration" value={breakdown.cross_source_corroboration} />
              <BreakdownBar label="Geographic Consistency" value={breakdown.geographic_consistency} max={20} />
              <BreakdownBar label="Temporal Consistency" value={breakdown.temporal_consistency} max={10} />
              <BreakdownBar label="Official Agency Confirmation" value={breakdown.official_evidence} max={10} />
              <BreakdownBar label="Visual Media Evidence" value={breakdown.media_evidence} max={5} />
            </div>
          ) : (
            <p className="text-xs text-[#96938B]">Insufficient component data</p>
          )}
        </Card>

        <Card title="NLP Classification Signals" icon={Fingerprint}>
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-2xl font-extrabold text-[#111111] dark:text-white">
              {TYPE_LABELS[classification.category] || classification.category || '—'}
            </span>
            <span className="rounded-full border border-[#D9A441]/30 bg-[#F7EED7] px-3 py-1 text-xs font-bold text-[#A97820]">
              {((classification.confidence || 0) * 100).toFixed(0)}% confidence
            </span>
          </div>
          {explanation.classification_reason && (
            <p className="mt-3 text-xs text-[#66635C] dark:text-stone-300">{explanation.classification_reason}</p>
          )}
          {classification.matched_patterns?.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-[10px] uppercase font-bold tracking-widest text-[#96938B]">Matched Signals</p>
              <div className="flex flex-wrap gap-2">
                {(classification.matched_patterns || []).slice(0, 8).map((p, i) => (
                  <span key={i} className="rounded-xl bg-[#F7F7F5] dark:bg-[#0e1017] border border-[#E5E2DA] dark:border-stone-800 px-3 py-1 text-xs text-[#111111] dark:text-stone-300 font-medium">{p}</span>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card title="Severity Assessment" icon={Activity}>
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl border border-amber-500/20 bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center text-lg font-black">
              {SEVERITY_LABELS[severityData.severity]?.[0] || '—'}
            </div>
            <div>
              <p className="text-xl font-bold text-[#111111] dark:text-white">
                {SEVERITY_LABELS[severityData.severity] || severityData.severity || '—'}
              </p>
              <p className="text-xs text-[#96938B]">
                Confidence: {((severityData.confidence || 0) * 100).toFixed(0)}%
              </p>
            </div>
          </div>
          {explanation.severity_reason && (
            <p className="mt-3 text-xs text-[#66635C] dark:text-stone-300">{explanation.severity_reason}</p>
          )}
        </Card>

        <Card title="Source Credibility" icon={ShieldCheck}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-base font-bold text-[#111111] dark:text-white">{sourceTrust.source_name || '—'}</p>
              <p className="text-xs text-[#96938B] capitalize">{sourceTrust.source_type || '—'} source</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-black text-[#D9A441]">
                {sourceTrust.trust_score != null ? Math.round(sourceTrust.trust_score) : '—'}
              </p>
              <p className="text-[10px] uppercase font-bold tracking-widest text-[#96938B]">Trust / 100</p>
            </div>
          </div>
          {event.source_url && (
            <a
              href={event.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-flex items-center gap-1.5 text-xs font-bold text-[#D9A441] hover:text-[#A97820]"
            >
              View original post <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </Card>

        <Card title="Corroboration Cluster" icon={Layers}>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-[#F7F7F5] dark:bg-[#0e1017] border border-[#E5E2DA] dark:border-stone-800 p-3 text-center">
              <p className="text-2xl font-extrabold text-[#111111] dark:text-white">{corroboration.related_report_count ?? 0}</p>
              <p className="text-xs text-[#96938B]">Related reports</p>
            </div>
            <div className="rounded-xl bg-[#F7F7F5] dark:bg-[#0e1017] border border-[#E5E2DA] dark:border-stone-800 p-3 text-center">
              <p className="text-2xl font-extrabold text-[#D9A441]">
                {corroboration.source_count ?? 0}
              </p>
              <p className="text-xs text-[#96938B] font-bold">RELATED SOURCES</p>
            </div>
          </div>
        </Card>

        {((event.media && event.media.length > 0) || (event.photos && event.photos.length > 0)) && (
          <Card title="Media & Visual Evidence" icon={ShieldCheck} className="lg:col-span-2">
            <div className="flex flex-wrap gap-4">
              {(event.media && event.media.length > 0 ? event.media : [
                ...(event.photos || []).map(url => (typeof url === 'string' ? { type: 'image', url } : url)),
                ...(event.videos || []).map(url => (typeof url === 'string' ? { type: 'video', url } : url)),
              ]).map((m, idx) => {
                const isVideo = m.type === 'video' || m.kind === 'video';
                const srcUrl = m.thumbnail_url || m.url;
                if (!srcUrl) return null;
                return isVideo ? (
                  <div key={idx} className="relative group">
                    <video src={srcUrl} controls className="h-32 w-48 object-cover rounded-xl border border-[#E5E2DA] dark:border-stone-800" />
                    <span className="absolute top-2 left-2 bg-[#111111]/80 text-white text-[9px] font-bold px-2 py-0.5 rounded-full">VIDEO</span>
                  </div>
                ) : (
                  <a key={idx} href={m.source_url || srcUrl} target="_blank" rel="noopener noreferrer" className="relative group block">
                    <img
                      src={srcUrl}
                      alt={m.caption || "Weather media evidence"}
                      className="h-32 w-48 object-cover rounded-xl border border-[#E5E2DA] dark:border-stone-800 transition-transform group-hover:scale-105"
                      onError={(err) => { err.target.style.display = 'none'; }}
                    />
                    {m.caption && (
                      <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity rounded-xl p-2 flex items-end">
                        <span className="text-[10px] text-white line-clamp-2">{m.caption}</span>
                      </div>
                    )}
                  </a>
                );
              })}
            </div>
          </Card>
        )}
      </div>

      {timeline.length > 0 && (
        <Card title="Ingestion & AI Pipeline Timeline" icon={Clock}>
          <ol className="relative ml-4 space-y-4 border-l-2 border-[#E5E2DA] dark:border-stone-800 pl-6">
            {timeline.map((step, i) => (
              <li key={i} className="relative">
                <span className="absolute -left-[31px] top-1 h-3 w-3 rounded-full border-2 border-[#E5E2DA] dark:border-stone-800 bg-[#D9A441]" />
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="text-xs font-bold text-[#111111] dark:text-white">{step.label}</p>
                  <span className="text-[11px] text-[#96938B] font-medium">{fmtTime(step.time)}</span>
                </div>
                {step.detail && <p className="text-xs text-[#66635C] dark:text-stone-400 mt-0.5">{step.detail}</p>}
              </li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  );
}