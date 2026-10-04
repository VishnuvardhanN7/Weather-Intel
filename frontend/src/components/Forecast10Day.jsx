import React, { useEffect, useState, useRef } from 'react';
import {
  Sun, CloudSun, CloudRain, Zap, CloudFog, Snowflake, Cloud,
  ChevronLeft, ChevronRight, MapPin, RefreshCw
} from 'lucide-react';
import { api } from '../services/api.js';
import { useLocationContext } from '../context/LocationContext.jsx';
import { INDIAN_CITIES } from '../utils/indianCities.js';

function getWeatherIcon(iconType, condition = '') {
  const condLower = (condition || '').toLowerCase();
  if (iconType === 'sun' || condLower.includes('clear')) {
    return <Sun className="w-6 h-6 text-[#D9A441]" />;
  }
  if (iconType === 'thunderstorm' || condLower.includes('thunder')) {
    return <Zap className="w-6 h-6 text-[#111111] dark:text-white" />;
  }
  if (iconType === 'rain' || condLower.includes('rain') || condLower.includes('drizzle')) {
    return <CloudRain className="w-6 h-6 text-[#66635C] dark:text-stone-300" />;
  }
  if (iconType === 'fog' || condLower.includes('fog') || condLower.includes('mist')) {
    return <CloudFog className="w-6 h-6 text-[#96938B]" />;
  }
  if (iconType === 'snow' || condLower.includes('snow')) {
    return <Snowflake className="w-6 h-6 text-[#66635C] dark:text-stone-300" />;
  }
  return <CloudSun className="w-6 h-6 text-[#D9A441]" />;
}

export default function Forecast10Day() {
  const { selectedLocation, selectCityByName } = useLocationContext();
  const [forecastData, setForecastData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const scrollContainerRef = useRef(null);

  const fetchForecast = async (city, lat, lon) => {
    setLoading(true);
    setError(null);
    try {
      let url = `/api/weather/forecast?city=${encodeURIComponent(city)}`;
      if (lat && lon) url += `&latitude=${lat}&longitude=${lon}`;
      const res = await api.get(url);
      if (res.data && res.data.forecast) {
        setForecastData(res.data.forecast);
      } else {
        setForecastData([]);
      }
    } catch (err) {
      console.error('Failed to fetch forecast:', err);
      setError('Unable to load weather forecast');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchForecast(selectedLocation.city, selectedLocation.latitude, selectedLocation.longitude);
  }, [selectedLocation]);

  const handleScroll = (direction) => {
    if (scrollContainerRef.current) {
      const scrollAmount = direction === 'left' ? -280 : 280;
      scrollContainerRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' });
    }
  };

  return (
    <section className="bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-xl p-6 shadow-subtle font-sans">
      {/* Header with City Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-[#111111] dark:text-white tracking-tight">
            10-Day Forecast
          </h2>
          <p className="text-xs text-[#66635C] dark:text-[#9CA3AF] mt-0.5 font-normal">
            Meteorological daily outlook for {selectedLocation.city}{selectedLocation.state ? `, ${selectedLocation.state}` : ''}
          </p>
        </div>

        {/* City Dropdown & Scroll Controls */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center">
            <MapPin className="w-3.5 h-3.5 text-[#D9A441] absolute left-3 pointer-events-none" />
            <select
              value={selectedLocation.city}
              onChange={(e) => selectCityByName(e.target.value)}
              className="pl-8 pr-7 py-1.5 bg-[#F7F7F5] dark:bg-[#0F1117] border border-[#E5E2DA] dark:border-[#262938] text-[#111111] dark:text-white text-xs font-medium rounded-md focus:outline-none cursor-pointer appearance-none"
              aria-label="Select city for 10-day forecast"
            >
              {INDIAN_CITIES.map((c) => (
                <option key={c.city} value={c.city}>{c.city}</option>
              ))}
            </select>
          </div>

          <div className="hidden sm:flex items-center gap-1">
            <button
              onClick={() => handleScroll('left')}
              className="p-1.5 rounded-md bg-[#F7F7F5] hover:bg-[#E5E2DA] dark:bg-[#0F1117] dark:hover:bg-[#262938] text-[#66635C] dark:text-[#9CA3AF] transition-colors"
              aria-label="Scroll forecast left"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleScroll('right')}
              className="p-1.5 rounded-md bg-[#F7F7F5] hover:bg-[#E5E2DA] dark:bg-[#0F1117] dark:hover:bg-[#262938] text-[#66635C] dark:text-[#9CA3AF] transition-colors"
              aria-label="Scroll forecast right"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Horizontal Forecast Cards List */}
      {loading ? (
        <div className="flex items-center justify-center py-10 text-[#66635C]">
          <RefreshCw className="w-5 h-5 animate-spin mr-2 text-[#D9A441]" />
          <span className="text-xs font-medium">Loading 10-day forecast...</span>
        </div>
      ) : error ? (
        <div className="py-6 text-center text-xs text-[#66635C]">
          <p>{error}</p>
          <button
            onClick={() => fetchForecast(selectedLocation.city, selectedLocation.latitude, selectedLocation.longitude)}
            className="mt-2 px-3 py-1 bg-[#111111] text-white font-medium rounded-md text-xs"
          >
            Retry
          </button>
        </div>
      ) : (
        <div
          ref={scrollContainerRef}
          className="flex items-stretch gap-3 overflow-x-auto pb-2 scrollbar-thin snap-x"
        >
          {forecastData.map((item, idx) => {
            const isToday = idx === 0;

            return (
              <div
                key={item.date || idx}
                className={`flex-shrink-0 w-32 sm:w-36 rounded-lg p-3.5 flex flex-col justify-between transition-colors snap-start border ${
                  isToday
                    ? 'bg-[#111111] text-white border-[#111111] shadow-md'
                    : 'bg-[#F7F7F5] dark:bg-[#0F1117] text-[#111111] dark:text-white border-[#E5E2DA] dark:border-[#262938]'
                }`}
              >
                {/* Date & Day Header */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-xs font-bold uppercase tracking-wider ${
                      isToday ? 'text-white' : 'text-[#111111] dark:text-white'
                    }`}>
                      {item.day}
                    </span>
                    {isToday && (
                      <span className="text-[9px] font-extrabold px-1.5 py-0.5 rounded bg-[#D9A441] text-[#111111] uppercase tracking-wider">
                        Today
                      </span>
                    )}
                  </div>
                  <p className={`text-[11px] font-medium ${
                    isToday ? 'text-[#96938B]' : 'text-[#66635C] dark:text-[#9CA3AF]'
                  }`}>
                    {item.day_full?.split(', ')[1] || item.date}
                  </p>
                </div>

                {/* Weather Icon & Condition */}
                <div className="my-3 flex flex-col items-center text-center">
                  <div className="mb-1.5">
                    {getWeatherIcon(item.icon, item.condition)}
                  </div>
                  <p className={`text-xs font-medium line-clamp-1 ${
                    isToday ? 'text-white' : 'text-[#111111] dark:text-white'
                  }`}>
                    {item.condition}
                  </p>
                </div>

                {/* Temp High / Low */}
                <div className={`pt-2 border-t flex items-center justify-between text-xs font-semibold ${
                  isToday ? 'border-stone-800' : 'border-[#E5E2DA] dark:border-[#262938]'
                }`}>
                  <span className={isToday ? 'text-white' : 'text-[#111111] dark:text-white'}>
                    {item.temp_max}°
                  </span>
                  <span className={isToday ? 'text-[#96938B]' : 'text-[#66635C] dark:text-[#9CA3AF]'}>
                    {item.temp_min}°
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}


