import React, { useState, useEffect } from 'react';
import dayjs from 'dayjs';
import clsx from 'clsx';
import { ChevronUp, ChevronDown, ExternalLink, CheckCircle, XCircle, Clock, AlertTriangle, User, Shield, AtSign, Image, Loader2, Check } from 'lucide-react';

const SEVERITY_STYLES = {
  low: 'badge-low',
  moderate: 'badge-moderate',
  high: 'badge-high',
  critical: 'badge-critical',
};

const STATUS_ICONS = {
  pending: Clock,
  verified: CheckCircle,
  rejected: XCircle,
  needs_review: AlertTriangle,
};

const STATUS_STYLES = {
  pending: 'badge-pending',
  verified: 'badge-verified',
  rejected: 'badge-rejected',
  needs_review: 'badge-moderate',
};

const COLUMNS = [
  { key: 'title', label: 'Event', sortable: true, width: 'w-[30%]' },
  { key: 'event_type', label: 'Type', sortable: true, width: 'w-[12%]' },
  { key: 'severity', label: 'Severity', sortable: true, width: 'w-[10%]' },
  { key: 'city', label: 'City', sortable: true, width: 'w-[12%]' },
  { key: 'state', label: 'State', sortable: true, width: 'w-[12%]' },
  { key: 'source', label: 'Source', sortable: true, width: 'w-[10%]' },
  { key: 'verification_status', label: 'Status', sortable: true, width: 'w-[12%]' },
  { key: 'reported_at', label: 'Reported', sortable: true, width: 'w-[12%]' },
];

function MediaEvidence({ event }) {
  const mediaList = event.media && event.media.length > 0
    ? event.media
    : [
        ...(event.photos || []).map(url => (typeof url === 'string' ? { type: 'image', url } : url)),
        ...(event.videos || []).map(url => (typeof url === 'string' ? { type: 'video', url } : url)),
      ];

  if (!mediaList || mediaList.length === 0) return null;

  return (
    <div className="mt-4">
      <h4 className="text-[11px] font-bold text-stone-500 dark:text-stone-400 uppercase tracking-widest mb-2 flex items-center gap-1.5">
        <Image className="w-3.5 h-3.5 text-[#D9A441]" /> Media Evidence ({mediaList.length})
      </h4>
      <div className="flex flex-wrap gap-3">
        {mediaList.map((m, idx) => {
          const isVideo = m.type === 'video' || m.kind === 'video';
          const srcUrl = m.thumbnail_url || m.url;
          if (!srcUrl) return null;
          return isVideo ? (
            <div key={idx} className="relative group">
              <video src={srcUrl} controls className="h-24 w-36 object-cover rounded-xl border border-[#E5E2DA] dark:border-[#262938] shadow-subtle" />
              <span className="absolute top-1.5 left-1.5 bg-[#111111]/85 text-white text-[9px] px-2 py-0.5 rounded-full font-bold">VIDEO</span>
            </div>
          ) : (
            <a key={idx} href={m.source_url || srcUrl} target="_blank" rel="noopener noreferrer" className="relative group block">
              <img
                src={srcUrl}
                alt={m.caption || "Weather media evidence"}
                className="h-24 w-36 object-cover rounded-xl border border-[#E5E2DA] dark:border-[#262938] transition-transform group-hover:scale-105 shadow-subtle"
                onError={(e) => { e.target.onerror = null; e.target.style.display = 'none'; }}
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
    </div>
  );
}

function SourceBlock({ event }) {
  const details = event.source_details || {};
  const name = details.author_name || details.display;
  const handle = details.handle;
  return (
    <div>
      <h4 className="text-[11px] font-bold text-stone-500 dark:text-stone-400 uppercase tracking-widest mb-2">Source</h4>
      <dl className="text-xs space-y-1.5 text-stone-700 dark:text-stone-300">
        <div className="flex gap-2">
          <dt className="text-stone-500 font-medium">Platform:</dt>
          <dd className="font-semibold text-[#111111] dark:text-white">{details.platform || details.display || event.source}</dd>
        </div>
        {name && (
          <div className="flex gap-2 items-center">
            <AtSign className="w-3.5 h-3.5 text-stone-400 dark:text-stone-500 flex-shrink-0" />
            <dd className="capitalize font-semibold">{name}</dd>
          </div>
        )}
        {handle && (
          <div className="flex gap-2 items-center">
            <User className="w-3.5 h-3.5 text-stone-400 dark:text-stone-500 flex-shrink-0" />
            <dd>@{handle}</dd>
          </div>
        )}
        {details.followers != null && (
          <div className="flex gap-2">
            <dt className="text-stone-500">Followers:</dt>
            <dd>{details.followers.toLocaleString()}</dd>
          </div>
        )}
        {event.reported_by_id && (
          <div className="flex gap-2">
            <dt className="text-stone-500">Reporter:</dt>
            <dd>{event.reported_by_name || `user #${event.reported_by_id}`}</dd>
          </div>
        )}
        {event.verified_by_name && (
          <div className="flex gap-2 items-center">
            <Shield className="w-3.5 h-3.5 text-[#2E7D5B] dark:text-[#2E7D5B] flex-shrink-0" />
            <dt className="text-stone-500">Verified by:</dt>
            <dd className="text-[#2E7D5B] dark:text-[#2E7D5B] font-semibold">{event.verified_by_name}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}

export default function EventTable({ events = [], onVerify, onDelete, onViewIntelligence, onClassify, loading, selectable, selectedIds, onToggleSelect, onSelectAll }) {
  const [sortKey, setSortKey] = useState('reported_at');
  const [sortDir, setSortDir] = useState('desc');
  const [expandedRow, setExpandedRow] = useState(null);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sorted = [...events].sort((a, b) => {
    let aVal = a[sortKey];
    let bVal = b[sortKey];
    if (aVal == null) aVal = '';
    if (bVal == null) bVal = '';
    if (typeof aVal === 'string') aVal = aVal.toLowerCase();
    if (typeof bVal === 'string') bVal = bVal.toLowerCase();
    if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  const renderSortIcon = (key) => {
    if (sortKey !== key) return null;
    return sortDir === 'asc'
      ? <ChevronUp className="w-3.5 h-3.5 inline ml-1 text-[#D9A441]" />
      : <ChevronDown className="w-3.5 h-3.5 inline ml-1 text-[#D9A441]" />;
  };

  if (loading) {
    return (
      <div className="card-editorial">
        <div className="animate-pulse space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-12 bg-stone-200 dark:bg-stone-800/50 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-[#161822] overflow-hidden p-0 border border-[#E5E2DA] dark:border-[#262938] rounded-xl shadow-subtle">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#E5E2DA] dark:border-[#262938] bg-[#F7F7F5] dark:bg-[#0E1017]">
              {selectable && (
                <th className="px-4 py-3.5 w-10">
                  <button
                    onClick={onSelectAll}
                    className={clsx(
                      'w-5 h-5 rounded-md border flex items-center justify-center transition-colors',
                      selectedIds?.size === events.length && events.length > 0
                        ? 'bg-[#111111] border-[#111111] dark:bg-white dark:border-white'
                        : 'border-[#E5E2DA] dark:border-stone-700 hover:border-stone-400'
                    )}
                    aria-label="Select all events"
                  >
                    {selectedIds?.size === events.length && events.length > 0 && (
                      <Check className="w-3 h-3 text-white dark:text-[#111111]" />
                    )}
                  </button>
                </th>
              )}
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => col.sortable && handleSort(col.key)}
                  className={clsx(
                    'px-4 py-3.5 text-left text-[11px] font-bold text-[#66635C] dark:text-stone-400 uppercase tracking-widest',
                    col.sortable && 'cursor-pointer hover:text-[#111111] dark:hover:text-white select-none',
                    col.width
                  )}
                >
                  {col.label}
                  {renderSortIcon(col.key)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E5E2DA] dark:divide-[#262938] bg-white dark:bg-[#161822]">
            {sorted.map((event) => {
              const StatusIcon = STATUS_ICONS[event.verification_status] || Clock;
              return (
                <React.Fragment key={event.id}>
                  <tr
                    className={clsx(
                      'transition-colors',
                      selectedIds?.has(event.id) ? 'bg-[#F7EED7]/60 dark:bg-[#D9A441]/10' : 'hover:bg-[#F7F7F5] dark:hover:bg-stone-800/40',
                      'cursor-pointer'
                    )}
                  >
                    {selectable && (
                      <td className="px-4 py-3.5 w-10" onClick={(e) => { e.stopPropagation(); onToggleSelect?.(event.id); }}>
                        <button
                          className={clsx(
                            'w-5 h-5 rounded-md border flex items-center justify-center transition-colors',
                            selectedIds?.has(event.id)
                              ? 'bg-[#111111] border-[#111111] dark:bg-white dark:border-white'
                              : 'border-[#E5E2DA] dark:border-stone-700 hover:border-stone-400'
                          )}
                          aria-label={`Select event: ${event.title}`}
                        >
                          {selectedIds?.has(event.id) && (
                            <Check className="w-3 h-3 text-white dark:text-[#111111]" />
                          )}
                        </button>
                      </td>
                    )}
                    <td className="px-4 py-3.5 max-w-xs" onClick={() => setExpandedRow(expandedRow === event.id ? null : event.id)}>
                      <p className="font-bold text-[#111111] dark:text-white truncate hover:text-[#D9A441]">{event.title}</p>
                      <p className="text-xs text-[#66635C] dark:text-stone-400 truncate mt-0.5">{event.description?.slice(0, 80)}...</p>
                    </td>
                    <td className="px-4 py-3.5" onClick={() => setExpandedRow(expandedRow === event.id ? null : event.id)}>
                      <span className="capitalize text-[#111111] dark:text-stone-300 font-medium">{event.event_type?.replace('_', ' ')}</span>
                    </td>
                    <td className="px-4 py-3.5" onClick={() => setExpandedRow(expandedRow === event.id ? null : event.id)}>
                      <span className={clsx('badge', SEVERITY_STYLES[event.severity])}>
                        {event.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-[#111111] dark:text-stone-300" onClick={() => setExpandedRow(expandedRow === event.id ? null : event.id)}>{event.city || '-'}</td>
                    <td className="px-4 py-3.5 text-[#111111] dark:text-stone-300" onClick={() => setExpandedRow(expandedRow === event.id ? null : event.id)}>{event.state || '-'}</td>
                    <td className="px-4 py-3.5" onClick={() => setExpandedRow(expandedRow === event.id ? null : event.id)}>
                      <span className="capitalize text-[#66635C] dark:text-stone-400 font-medium">{event.source?.replace('_', ' ')}</span>
                    </td>
                    <td className="px-4 py-3.5" onClick={() => setExpandedRow(expandedRow === event.id ? null : event.id)}>
                      <span className={clsx('badge inline-flex items-center gap-1.5', STATUS_STYLES[event.verification_status])}>
                        <StatusIcon className="w-3 h-3" />
                        {event.verification_status?.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-[#96938B] dark:text-stone-400 text-xs whitespace-nowrap font-medium" onClick={() => setExpandedRow(expandedRow === event.id ? null : event.id)}>
                      {dayjs(event.reported_at).format('DD MMM, HH:mm')}
                    </td>
                  </tr>

                  {expandedRow === event.id && (
                    <tr className="bg-[#F7F7F5] dark:bg-[#0E1017] border-l-4 border-[#D9A441]">
                      <td colSpan={selectable ? 9 : 8} className="px-6 py-5">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                          <div>
                            <h4 className="text-[11px] font-bold text-[#66635C] dark:text-stone-400 uppercase tracking-widest mb-2">Description</h4>
                            <p className="text-xs text-[#111111] dark:text-stone-200 leading-relaxed">{event.description}</p>
                          </div>
                          <div>
                            <h4 className="text-[11px] font-bold text-[#66635C] dark:text-stone-400 uppercase tracking-widest mb-2">Geospatial Details</h4>
                            <dl className="text-xs space-y-1.5 text-stone-700 dark:text-stone-300">
                              <div className="flex gap-2">
                                <dt className="text-stone-500 font-medium">Coordinates:</dt>
                                <dd className="font-semibold text-[#111111] dark:text-white">
                                  {event.latitude != null && event.longitude != null
                                    ? `${event.latitude.toFixed(4)}, ${event.longitude.toFixed(4)}`
                                    : 'Not available'}
                                </dd>
                              </div>
                              <div className="flex gap-2">
                                <dt className="text-stone-500 font-medium">Misinfo Score:</dt>
                                <dd className="font-semibold text-rose-600 dark:text-rose-400">{(event.fake_confidence * 100).toFixed(1)}%</dd>
                              </div>
                              <div className="flex gap-2">
                                <dt className="text-stone-500 font-medium">Classification Conf:</dt>
                                <dd className="font-semibold text-[#D9A441]">{(event.category_confidence * 100).toFixed(1)}%</dd>
                              </div>
                            </dl>
                          </div>
                          <SourceBlock event={event} />
                        </div>

                        <MediaEvidence event={event} />

                        <div className="flex gap-3 flex-wrap mt-5 pt-4 border-t border-[#E5E2DA] dark:border-[#262938]">
                          {event.source_url && (
                            <a
                              href={event.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="btn-secondary text-xs inline-flex items-center gap-1.5"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <ExternalLink className="w-3.5 h-3.5" /> Source Post
                            </a>
                          )}
                          {onVerify && event.verification_status === 'pending' && (
                            <>
                              <button
                                onClick={(e) => { e.stopPropagation(); onVerify(event.id, 'verified'); }}
                                className="btn-primary text-xs inline-flex items-center gap-1.5"
                              >
                                <CheckCircle className="w-3.5 h-3.5 text-[#2E7D5B]" /> Verify
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); onVerify(event.id, 'rejected'); }}
                                className="btn-secondary text-xs inline-flex items-center gap-1.5 text-red-600 hover:bg-red-50"
                              >
                                <XCircle className="w-3.5 h-3.5" /> Reject
                              </button>
                            </>
                          )}
                          {onViewIntelligence && (
                            <button
                              onClick={(e) => { e.stopPropagation(); onViewIntelligence(event.id); }}
                              className="btn-secondary text-xs inline-flex items-center gap-1.5"
                              aria-label={`View AI intelligence for: ${event.title}`}
                            >
                              <Shield className="w-3.5 h-3.5 text-[#D9A441]" /> AI Intelligence Dossier
                            </button>
                          )}
                          {onDelete && (
                            <button
                              onClick={(e) => { e.stopPropagation(); onDelete(event.id); }}
                              className="btn-secondary text-xs inline-flex items-center gap-1.5 text-red-600 hover:bg-red-50"
                              aria-label={`Delete weather event: ${event.title}`}
                            >
                              <XCircle className="w-3.5 h-3.5" /> Delete
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      {sorted.length === 0 && (
        <div className="text-center py-12 text-[#96938B] font-medium">No weather events matched current filters</div>
      )}
    </div>
  );
}

