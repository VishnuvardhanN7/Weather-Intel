import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { Radio, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import WeatherMap from '../components/WeatherMap.jsx';
import { api } from '../services/api.js';
import { useLocationContext } from '../context/LocationContext.jsx';
import { isTestEvent } from '../utils/eventFormatter.js';

export default function WeatherMapPage() {
  const { selectedLocation } = useLocationContext();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeLayer, setActiveLayer] = useState('all');
  const [filterPanelOpen, setFilterPanelOpen] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const eventsRes = await api.get('/api/weather?per_page=100');
      if (eventsRes.data && eventsRes.data.data) {
        const clean = (eventsRes.data.data || []).filter((e) => !isTestEvent(e));
        setEvents(clean);
      }
    } catch (err) {
      console.error('WeatherMapPage fetch error:', err);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const filteredEventsForMap = useMemo(() => {
    if (activeLayer === 'all') return events;
    if (activeLayer === 'rainfall') return events.filter(e => (e.event_type || '').toLowerCase().includes('rain') || (e.event_type || '').toLowerCase().includes('flood'));
    if (activeLayer === 'temperature') return events.filter(e => (e.event_type || '').toLowerCase().includes('heat') || (e.event_type || '').toLowerCase().includes('temp'));
    if (activeLayer === 'wind') return events.filter(e => (e.event_type || '').toLowerCase().includes('wind') || (e.event_type || '').toLowerCase().includes('cyclone'));
    if (activeLayer === 'cloud') return events.filter(e => (e.event_type || '').toLowerCase().includes('fog') || (e.event_type || '').toLowerCase().includes('cloud'));
    if (activeLayer === 'alerts') return events.filter(e => e.severity === 'critical' || e.severity === 'high');
    return events;
  }, [events, activeLayer]);

  const severeEventsCount = events.filter(e => e.severity === 'critical' || e.severity === 'high').length;

  return (
    <div className="relative w-full h-[calc(100vh-68px)] sm:h-[calc(100vh-72px)] overflow-hidden bg-[#0F1117] font-sans" role="main" aria-label="Dedicated Fullscreen Weather Map">
      
      {/* 100% FULLSCREEN MAP */}
      <div className="w-full h-full">
        <WeatherMap
          events={filteredEventsForMap.length > 0 ? filteredEventsForMap : events}
          height="100%"
          targetCenter={[selectedLocation.latitude, selectedLocation.longitude]}
          selectedCityName={selectedLocation.city}
        />
      </div>

      {/* FLOATING MAP FILTERS PANEL (TOP-RIGHT OVERLAY INSIDE THE MAP) */}
      <div className="absolute top-4 right-4 sm:top-6 sm:right-6 z-20 w-[240px] sm:w-[260px] max-h-[calc(100vh-100px)] flex flex-col pointer-events-auto">
        
        {/* Mobile Toggle Button */}
        <div className="sm:hidden mb-2 flex justify-end">
          <button
            onClick={() => setFilterPanelOpen(v => !v)}
            className="px-3 py-2 rounded-xl bg-white/95 dark:bg-[#161822]/95 border border-[#E5E2DA] dark:border-[#262938] text-[#111111] dark:text-white text-xs font-bold flex items-center gap-2 shadow-lg backdrop-blur-md"
          >
            <Radio className="w-4 h-4 text-[#D9A441]" />
            <span>Map Filters</span>
            {filterPanelOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>

        {/* Floating Glass Filter Card */}
        {filterPanelOpen && (
          <div className="bg-white/95 dark:bg-[#161822]/95 backdrop-blur-md border border-[#E5E2DA] dark:border-[#262938] rounded-2xl p-4 shadow-2xl flex flex-col justify-between space-y-3.5 overflow-y-auto max-h-[calc(100vh-130px)]">
            <div className="space-y-3">
              <div className="flex items-center justify-between pb-2.5 border-b border-[#E5E2DA] dark:border-[#262938]">
                <div className="flex items-center gap-2">
                  <Radio className="w-4 h-4 text-[#D9A441]" />
                  <h2 className="text-xs font-extrabold text-[#111111] dark:text-white uppercase tracking-wider font-sans">
                    MAP FILTERS
                  </h2>
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                {[
                  { id: 'all', label: 'All Incidents' },
                  { id: 'rainfall', label: 'Rainfall' },
                  { id: 'temperature', label: 'Temperature' },
                  { id: 'wind', label: 'Wind' },
                  { id: 'cloud', label: 'Cloud Cover' },
                  { id: 'alerts', label: 'Severe Alerts' },
                ].map((layer) => {
                  const isActive = activeLayer === layer.id;
                  return (
                    <button
                      key={layer.id}
                      onClick={() => setActiveLayer(layer.id)}
                      className={`w-full text-left px-3.5 py-2 rounded-xl text-xs font-medium transition-all flex items-center justify-between cursor-pointer ${
                        isActive
                          ? 'bg-[#111111] text-white dark:bg-white dark:text-[#111111] font-extrabold shadow-sm'
                          : 'bg-stone-50 dark:bg-[#0F1117] text-[#66635C] dark:text-[#9CA3AF] hover:text-[#111111] dark:hover:text-white border border-[#E5E2DA] dark:border-[#262938]'
                      }`}
                    >
                      <span className="truncate">{layer.label}</span>
                      {isActive && <span className="w-2 h-2 rounded-full bg-[#D9A441] shrink-0 ml-1.5" />}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="pt-3 border-t border-[#E5E2DA] dark:border-[#262938] space-y-2">
              {severeEventsCount > 0 && (
                <div className="p-2.5 rounded-xl bg-[#F7EED7] dark:bg-[#2A2518] border border-[#D9A441]/40 flex items-center gap-2 text-xs text-[#A97820] dark:text-[#D9A441] font-extrabold">
                  <AlertTriangle className="w-4 h-4 text-[#D9A441] shrink-0" />
                  <span>{severeEventsCount} Active Alert{severeEventsCount > 1 ? 's' : ''}</span>
                </div>
              )}

              <div className="text-[10px] text-[#66635C] dark:text-[#9CA3AF] leading-relaxed font-medium">
                <span className="font-bold text-[#111111] dark:text-white block mb-0.5">Live Telemetry</span>
                IMD Stations & Real-time Radar Feeds
              </div>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}

