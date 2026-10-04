import React, { useState, useMemo } from 'react';
import {
  CloudSun, MapPin, Clock, CheckCircle2,
  Search, ArrowUpRight, X, ExternalLink, ShieldAlert
} from 'lucide-react';
import { isTestEvent, formatCitizenEvent } from '../utils/eventFormatter.js';
import { useLocationContext } from '../context/LocationContext.jsx';

function getRelativeTime(timestamp) {
  if (!timestamp) return 'Recently reported';
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffSec = Math.floor((now - date) / 1000);

    if (diffSec < 60) return 'Reported just now';
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `Reported ${diffMin} min ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `Reported ${diffHr} hour${diffHr > 1 ? 's' : ''} ago`;
    const diffDay = Math.floor(diffHr / 24);
    if (diffDay < 7) return `Reported ${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  } catch {
    return 'Recently reported';
  }
}

function getSourceLabel(source) {
  switch ((source || '').toLowerCase()) {
    case 'api':
      return 'Official Weather Observation';
    case 'citizen_report':
      return 'Citizen Report';
    case 'web':
      return 'Official News Wire';
    case 'twitter':
      return 'Social Weather Alert';
    default:
      return 'Monitored Update';
  }
}

export default function LiveWeatherEvents({ events = [], loading = false }) {
  const { selectedLocation } = useLocationContext();
  const [filterCategory, setFilterCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEvent, setSelectedEvent] = useState(null);

  // Clean, format, and geographically prioritize events for current location
  const processedEvents = useMemo(() => {
    // 1. Filter out internal test events
    const cleanEvents = events
      .filter((e) => !isTestEvent(e))
      .map((e) => formatCitizenEvent(e));

    // 2. Geographically prioritize events for selectedLocation
    const currentCity = (selectedLocation.city || '').toLowerCase();
    const currentState = (selectedLocation.state || '').toLowerCase();

    return cleanEvents.sort((a, b) => {
      const aCity = (a.city || '').toLowerCase();
      const bCity = (b.city || '').toLowerCase();
      const aState = (a.state || '').toLowerCase();
      const bState = (b.state || '').toLowerCase();
      const aSev = (a.severity || '').toLowerCase();
      const bSev = (b.severity || '').toLowerCase();

      // Priority 1: Exact city match
      const aIsCity = aCity === currentCity;
      const bIsCity = bCity === currentCity;
      if (aIsCity && !bIsCity) return -1;
      if (!aIsCity && bIsCity) return 1;

      // Priority 2: Same state match
      const aIsState = aState === currentState;
      const bIsState = bState === currentState;
      if (aIsState && !bIsState) return -1;
      if (!aIsState && bIsState) return 1;

      // Priority 3: Critical severity alerts
      const aIsCritical = aSev === 'critical' || aSev === 'high';
      const bIsCritical = bSev === 'critical' || bSev === 'high';
      if (aIsCritical && !bIsCritical) return -1;
      if (!aIsCritical && bIsCritical) return 1;

      // Priority 4: Reported timestamp desc
      return new Date(b.reported_at || b.created_at || 0) - new Date(a.reported_at || a.created_at || 0);
    });
  }, [events, selectedLocation]);

  // Filter based on user category pill & text search query
  const filteredEvents = useMemo(() => {
    return processedEvents.filter((e) => {
      const typeLower = (e.event_type || '').toLowerCase();
      const sevLower = (e.severity || '').toLowerCase();
      const cityLower = (e.city || '').toLowerCase();
      const stateLower = (e.state || '').toLowerCase();
      const titleLower = (e.title || '').toLowerCase();

      if (filterCategory === 'severe' && !(sevLower === 'critical' || sevLower === 'high')) return false;
      if (filterCategory === 'rain' && !(typeLower.includes('rain') || typeLower.includes('flood'))) return false;
      if (filterCategory === 'thunder' && !typeLower.includes('thunder')) return false;
      if (filterCategory === 'heat' && !typeLower.includes('heat')) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          cityLower.includes(q) ||
          stateLower.includes(q) ||
          titleLower.includes(q)
        );
      }
      return true;
    });
  }, [processedEvents, filterCategory, searchQuery]);

  return (
    <section className="space-y-6">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block shrink-0 animate-ping-slow" />
            <span className="text-[11px] font-extrabold tracking-widest text-stone-500 dark:text-stone-400 uppercase font-sans">
              REAL-TIME INCIDENTS ({filteredEvents.length})
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-stone-900 dark:text-white tracking-tight font-sans">
            LIVE WEATHER EVENTS — {selectedLocation.city.toUpperCase()}
          </h2>
          <p className="text-xs sm:text-sm text-stone-600 dark:text-stone-400 mt-0.5">
            Prioritized active weather incidents near {selectedLocation.city}{selectedLocation.state ? `, ${selectedLocation.state}` : ''}
          </p>
        </div>

        {/* Filter Pills & Search */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Search Box */}
          <div className="relative flex items-center min-w-[180px] sm:min-w-[220px]">
            <Search className="w-3.5 h-3.5 text-stone-400 absolute left-3 pointer-events-none" />
            <input
              type="text"
              placeholder="Search city or event..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-white dark:bg-[#141620] border border-stone-200 dark:border-stone-800 rounded-full text-xs text-stone-900 dark:text-white placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-500/50 shadow-sm"
            />
          </div>

          {/* Filter Categories */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
            {[
              { id: 'all', label: 'All Events' },
              { id: 'severe', label: 'Critical & Severe' },
              { id: 'rain', label: 'Rain & Flood' },
              { id: 'thunder', label: 'Thunderstorms' },
              { id: 'heat', label: 'Heatwave' },
            ].map((cat) => (
              <button
                key={cat.id}
                onClick={() => setFilterCategory(cat.id)}
                className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all whitespace-nowrap cursor-pointer ${
                  filterCategory === cat.id
                    ? 'bg-[#141620] text-white dark:bg-[#faf9f6] dark:text-[#0f1016] shadow-sm'
                    : 'bg-white dark:bg-[#141620] text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 border border-stone-200 dark:border-stone-800'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Events Grid Container — Controlled height for exactly 3 rows (9 cards visible), with internal vertical scroll */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4.5 max-h-[680px] overflow-hidden">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
            <div key={i} className="h-44 rounded-3xl bg-stone-100 dark:bg-stone-800/50 animate-pulse border border-stone-200 dark:border-stone-800" />
          ))}
        </div>
      ) : filteredEvents.length === 0 ? (
        <div className="bg-white dark:bg-[#141620] border border-stone-200 dark:border-stone-800 rounded-3xl p-10 text-center text-stone-500">
          <CloudSun className="w-10 h-10 mx-auto text-stone-400 mb-3" />
          <h3 className="text-base font-bold text-stone-900 dark:text-white">No active weather events for {selectedLocation.city}</h3>
          <p className="text-xs text-stone-500 mt-1">Showing clean conditions. Search another location or select All Events above.</p>
        </div>
      ) : (
        <div className="relative">
          {/* Scrollable grid container capped at 3 rows (approx 680px height) */}
          <div className="max-h-[680px] overflow-y-auto pr-2.5 scrollbar-thin scrollbar-thumb-stone-300 dark:scrollbar-thumb-stone-700 scrollbar-track-transparent rounded-3xl">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4.5">
              {filteredEvents.map((e) => {
                const severityKey = (e.severity || 'low').toLowerCase();
                const isVerified = e.verification_status === 'VERIFIED';
                const locationStr = [e.city, e.state].filter(Boolean).join(', ') || 'India';
                const isLocal = (e.city || '').toLowerCase() === selectedLocation.city.toLowerCase();

                return (
                  <div
                    key={e.id}
                    onClick={() => setSelectedEvent(e)}
                    className={`bg-white dark:bg-[#141620] border rounded-3xl p-5 shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between cursor-pointer group ${
                      isLocal
                        ? 'border-amber-400/80 dark:border-amber-400/60 ring-1 ring-amber-400/20'
                        : 'border-[#E5E3DC] dark:border-stone-800/90 hover:border-stone-300 dark:hover:border-stone-700'
                    }`}
                  >
                    <div>
                      {/* Top Bar: Event Type & Verification Status */}
                      <div className="flex items-center justify-between gap-2 mb-3">
                        <div className="flex items-center gap-2">
                          <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                            severityKey === 'critical' ? 'bg-red-500 animate-ping' :
                            severityKey === 'high' ? 'bg-orange-500' :
                            severityKey === 'moderate' ? 'bg-amber-500' : 'bg-emerald-500'
                          }`} />
                          <span className="text-xs font-black tracking-wider uppercase text-stone-900 dark:text-white font-sans">
                            {e.event_type?.replace(/_/g, ' ') || 'WEATHER INCIDENT'}
                          </span>
                        </div>

                        {/* Verification Status Pill */}
                        {isVerified ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-extrabold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-500/20 uppercase tracking-wider">
                            <CheckCircle2 className="w-3 h-3 text-emerald-500" /> VERIFIED
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] font-extrabold text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 px-2.5 py-0.5 rounded-full border border-amber-200 dark:border-amber-500/20 uppercase tracking-wider">
                            <Clock className="w-3 h-3 text-amber-500" /> PENDING
                          </span>
                        )}
                      </div>

                      {/* Location Title */}
                      <div className="flex items-center justify-between text-stone-500 dark:text-stone-400 text-xs font-semibold mb-1">
                        <div className="flex items-center gap-1.5">
                          <MapPin className="w-3.5 h-3.5 shrink-0 text-stone-400" />
                          <span>{locationStr}</span>
                        </div>
                        {isLocal && (
                          <span className="text-[9px] font-extrabold px-2 py-0.5 rounded-full bg-amber-500 text-white tracking-widest uppercase">
                            LOCAL
                          </span>
                        )}
                      </div>

                      {/* Headline Title */}
                      <h3 className="text-sm sm:text-[15px] font-bold text-stone-900 dark:text-white group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors line-clamp-2 mb-2 leading-snug">
                        {e.title}
                      </h3>

                      {/* Media Preview on Event Card */}
                      {((e.media && e.media.length > 0) || (e.photos && e.photos.length > 0)) && (
                        <div className="mb-3 relative overflow-hidden rounded-2xl border border-stone-200 dark:border-stone-800/80">
                          <img
                            src={e.media?.[0]?.thumbnail_url || e.media?.[0]?.url || (typeof e.photos[0] === 'string' ? e.photos[0] : e.photos[0]?.url)}
                            alt={e.title}
                            className="w-full h-36 object-cover group-hover:scale-105 transition-transform duration-300"
                            onError={(err) => { err.target.style.display = 'none'; }}
                          />
                          <span className="absolute top-2 right-2 bg-black/75 backdrop-blur-sm text-white text-[9px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 border border-white/20 shadow-sm">
                            MEDIA ({(e.media || e.photos || []).length})
                          </span>
                        </div>
                      )}

                      {/* Short Description */}
                      <p className="text-xs text-stone-600 dark:text-stone-400 line-clamp-2 leading-relaxed mb-4">
                        {e.description}
                      </p>
                    </div>

                    {/* Footer Bar: Relative Time & Source */}
                    <div className="pt-3 border-t border-stone-100 dark:border-stone-800/80 flex items-center justify-between text-[11px] text-stone-500 dark:text-stone-400">
                      <span className="font-medium text-stone-500">
                        {getRelativeTime(e.reported_at || e.created_at)}
                      </span>

                      <span className="inline-flex items-center gap-1 font-semibold text-stone-700 dark:text-stone-300 group-hover:translate-x-0.5 transition-transform">
                        <span>{getSourceLabel(e.source)}</span>
                        <ArrowUpRight className="w-3 h-3 text-stone-400" />
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          {filteredEvents.length > 9 && (
            <p className="text-center text-[11px] font-bold text-stone-400 dark:text-stone-500 mt-2 uppercase tracking-widest">
              ↕ Scroll inside panel to view {filteredEvents.length - 9} more events
            </p>
          )}
        </div>
      )}

      {/* Event Detail Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" role="dialog">
          <div className="bg-white dark:bg-[#141620] border border-stone-200 dark:border-stone-800 rounded-3xl max-w-xl w-full p-6 shadow-2xl relative animate-in fade-in zoom-in duration-200">
            <button
              onClick={() => setSelectedEvent(null)}
              className="absolute top-5 right-5 p-2 text-stone-400 hover:text-stone-900 dark:hover:text-white rounded-full bg-stone-100 dark:bg-stone-800"
              aria-label="Close details modal"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-2 mb-3">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                selectedEvent.severity === 'critical' ? 'bg-red-500/10 text-red-600 border border-red-500/20' :
                selectedEvent.severity === 'high' ? 'bg-orange-500/10 text-orange-600 border border-orange-500/20' :
                'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20'
              }`}>
                {selectedEvent.severity || 'NORMAL'} SEVERITY
              </span>
              <span className="text-xs font-semibold text-stone-500">
                {getSourceLabel(selectedEvent.source)}
              </span>
            </div>

            <h2 className="text-lg font-bold text-stone-900 dark:text-white mb-2 leading-snug">
              {selectedEvent.title}
            </h2>

            <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-400 mb-4">
              <MapPin className="w-3.5 h-3.5" />
              <span>{[selectedEvent.city, selectedEvent.state].filter(Boolean).join(', ') || 'India'}</span>
              <span>•</span>
              <Clock className="w-3.5 h-3.5" />
              <span>{getRelativeTime(selectedEvent.reported_at || selectedEvent.created_at)}</span>
            </div>

            <div className="p-4 rounded-2xl bg-stone-50 dark:bg-[#0e1017] border border-stone-200 dark:border-stone-800 text-xs sm:text-sm text-stone-700 dark:text-stone-300 leading-relaxed mb-6">
              {selectedEvent.description}
            </div>

            {selectedEvent.source_url && (
              <a
                href={selectedEvent.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-600 dark:text-amber-400 hover:underline"
              >
                <span>View original report source</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}

            <div className="mt-6 pt-4 border-t border-stone-100 dark:border-stone-800 flex justify-end">
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-5 py-2 bg-stone-900 text-white dark:bg-white dark:text-stone-900 font-bold rounded-full text-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
