import React, { useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import dayjs from 'dayjs';
import { Navigation, ExternalLink, MapPin } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { isTestEvent, formatCitizenEvent } from '../utils/eventFormatter.js';

const EVENT_COLORS = {
  rainfall: '#38bdf8',       // cyan/blue
  thunderstorm: '#0284c7',   // dark blue
  flooding: '#06b6d4',       // teal
  heatwave: '#f97316',       // orange
  fog: '#94a3b8',            // slate
  dust_storm: '#d97706',     // amber
  strong_winds: '#38bdf8',   // sky blue
  cyclone: '#ef4444',        // red
  other: '#a1a1aa',          // neutral
};

const SEVERITY_STROKE_COLORS = {
  critical: '#ef4444',
  high: '#f97316',
  moderate: '#38bdf8',
  low: '#10b981',
};

const SEVERITY_SIZES = {
  low: 8,
  moderate: 11,
  high: 14,
  critical: 18,
};

const INDIA_CENTER = [20.5937, 78.9629];

function MapFlyTo({ targetCenter, zoom = 7 }) {
  const map = useMap();
  useEffect(() => {
    if (targetCenter && targetCenter[0] != null && targetCenter[1] != null) {
      map.flyTo(targetCenter, zoom, { duration: 1.2 });
    }
  }, [targetCenter, zoom, map]);
  return null;
}

export default function WeatherMap({
  events = [],
  height = '560px',
  showLegend = true,
  onSelectEvent,
  targetCenter = null,
  selectedCityName = ''
}) {
  const navigate = useNavigate();

  // Filter out internal test events for citizen view & format
  const displayEvents = events
    .filter((e) => !isTestEvent(e))
    .map((e) => formatCitizenEvent(e));

  const centerPos = targetCenter && targetCenter[0] != null ? targetCenter : INDIA_CENTER;
  const zoomLevel = targetCenter && targetCenter[0] != null ? 7 : 5;

  return (
    <div className="relative z-0 isolate w-full h-full overflow-hidden rounded-xl bg-white dark:bg-[#161822]">
      <MapContainer
        center={centerPos}
        zoom={zoomLevel}
        style={{ height, width: '100%' }}
        zoomControl={true}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {targetCenter && targetCenter[0] != null && (
          <MapFlyTo targetCenter={targetCenter} zoom={7} />
        )}

        {displayEvents.map((event) => {
          if (!event.latitude || !event.longitude) return null;

          const severityKey = (event.severity || 'low').toLowerCase();
          const typeKey = (event.event_type || 'other').toLowerCase();

          const strokeColor = SEVERITY_STROKE_COLORS[severityKey] || '#D9A441';
          const fillColor = EVENT_COLORS[typeKey] || '#D9A441';
          const radius = SEVERITY_SIZES[severityKey] || 10;
          const isCritical = severityKey === 'critical';

          const intel = event.metadata_?.intelligence || event.intelligence || {};

          return (
            <CircleMarker
              key={event.id}
              center={[event.latitude, event.longitude]}
              radius={radius}
              pathOptions={{
                color: strokeColor,
                fillColor: fillColor,
                fillOpacity: isCritical ? 0.9 : 0.75,
                weight: isCritical ? 3 : 2,
                opacity: 1,
              }}
              eventHandlers={{
                click: () => onSelectEvent?.(event),
              }}
            >
              <Popup className="editorial-popup">
                <div className="min-w-[260px] p-2.5 font-sans text-[#111827] dark:text-stone-100">
                  <div className="flex items-center gap-2 mb-2 pb-1.5 border-b border-[#E7E7E3] dark:border-[#262938]">
                    <span
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: fillColor }}
                    />
                    <h3 className="font-bold text-xs text-[#111827] dark:text-white truncate leading-snug">
                      {event.title}
                    </h3>
                  </div>

                  <p className="text-[11px] text-[#667085] dark:text-stone-300 mb-2.5 leading-relaxed line-clamp-3">
                    {event.description}
                  </p>

                  <div className="grid grid-cols-2 gap-1 text-[11px] text-[#111827] dark:text-stone-300 bg-[#F7F7F5] dark:bg-[#0F1117] p-2 rounded-md border border-[#E7E7E3] dark:border-[#262938] mb-2">
                    <div>
                      <span className="font-semibold text-[#667085]">Type:</span>{' '}
                      <span className="capitalize font-medium">{event.event_type}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-[#667085]">Severity:</span>{' '}
                      <span className="capitalize font-semibold">{event.severity}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-[#667085]">City:</span>{' '}
                      <span className="font-medium">{event.city || 'N/A'}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-[#667085]">Source:</span>{' '}
                      <span className="capitalize font-medium">{event.source || 'API'}</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1 border-t border-[#E7E7E3] dark:border-[#262938]">
                    <span className="text-[10px] text-[#98A2B3] font-medium">
                      {dayjs(event.reported_at).format('DD MMM YYYY, HH:mm')}
                    </span>
                    <button
                      type="button"
                      onClick={() => navigate(`/events/${event.id}/intelligence`)}
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#D9A441] hover:underline"
                    >
                      AI Dossier <ExternalLink className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>

      {/* Top Floating Indicator Badge */}
      <div className="absolute top-3 left-3 z-10 bg-white/95 dark:bg-[#161822]/95 border border-[#E5E2DA] dark:border-[#262938] rounded-md px-3 py-1.5 flex items-center gap-2 shadow-subtle">
        <Navigation className="w-3.5 h-3.5 text-[#D9A441]" />
        <span className="text-xs font-semibold text-[#111111] dark:text-white">
          {selectedCityName ? `${selectedCityName} Radar` : 'India Weather Radar'}
        </span>
        <span className="text-[11px] text-[#66635C] dark:text-[#9CA3AF] border-l border-[#E5E2DA] dark:border-[#262938] pl-2 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#2E7D5B]" />
          {displayEvents.length} Active Observations
        </span>
      </div>

      {/* Bottom Floating Legend */}
      {showLegend && (
        <div className="absolute bottom-3 right-3 z-10 bg-white/95 dark:bg-[#161822]/95 border border-[#E5E2DA] dark:border-[#262938] rounded-lg p-2.5 shadow-subtle max-w-xs">
          <div className="text-[10px] font-semibold text-[#66635C] dark:text-[#9CA3AF] uppercase tracking-wider mb-1.5 flex items-center justify-between gap-2">
            <span>Severity Key</span>
            <span className="text-[#2E7D5B] font-medium">Live Map</span>
          </div>
          
          <div className="grid grid-cols-2 gap-x-3 gap-y-1">
            {Object.entries(SEVERITY_STROKE_COLORS).map(([sev, color]) => (
              <div key={sev} className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                <span className="text-[10px] text-[#111111] dark:text-stone-300 capitalize font-medium">{sev}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
