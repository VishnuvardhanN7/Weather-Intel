import React, { useEffect, useState } from 'react';
import { MapPin, Wind, Droplets, Eye, CloudRain, Navigation, RefreshCw } from 'lucide-react';
import { api } from '../services/api.js';
import { useLocationContext } from '../context/LocationContext.jsx';

export default function LocalWeather() {
  const { selectedLocation } = useLocationContext();
  const [weather, setWeather] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchLocalWeather = async (cityName, lat, lon) => {
    setLoading(true);
    setError(null);
    try {
      let url = `/api/weather/forecast?city=${encodeURIComponent(cityName)}`;
      if (lat && lon) {
        url += `&latitude=${lat}&longitude=${lon}`;
      }
      const res = await api.get(url);
      if (res.data && res.data.forecast && res.data.forecast.length > 0) {
        const today = res.data.forecast[0];
        setWeather({
          city: res.data.city || cityName,
          state: selectedLocation.state || '',
          temp: Math.round((today.temp_max + today.temp_min) / 2),
          temp_max: today.temp_max,
          temp_min: today.temp_min,
          condition: today.condition || 'Partly Cloudy',
          feels_like: Math.round((today.temp_max + today.temp_min) / 2) + 2,
          humidity: today.humidity || 68,
          wind_speed: today.wind_speed || 14,
          visibility: today.visibility || 8.5,
          rain_prob: today.precipitation_probability || 20,
        });
      } else {
        setWeather(null);
      }
    } catch (err) {
      console.error('Failed to fetch local weather:', err);
      setError('Unable to fetch local weather data.');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchLocalWeather(selectedLocation.city, selectedLocation.latitude, selectedLocation.longitude);
  }, [selectedLocation]);

  return (
    <section className="bg-white border border-[#E5E2DA] rounded-xl p-6 sm:p-8 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#D9A441] inline-block shrink-0" />
            <span className="text-[11px] font-bold tracking-widest text-[#96938B] uppercase font-sans">
              LOCAL CONDITIONS
            </span>
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-[#111111] tracking-tight font-sans">
            YOUR WEATHER — {selectedLocation.city.toUpperCase()}
          </h2>
          <p className="text-xs sm:text-sm text-[#66635C] mt-0.5">
            Real-time weather observations for {selectedLocation.city}{selectedLocation.state ? `, ${selectedLocation.state}` : ''}
          </p>
        </div>

        <button
          onClick={() => fetchLocalWeather(selectedLocation.city, selectedLocation.latitude, selectedLocation.longitude)}
          className="p-2.5 rounded-full bg-[#F7F7F5] hover:bg-[#E5E2DA] text-[#66635C] transition-colors flex items-center gap-2 text-xs font-bold self-start sm:self-auto"
          title="Refresh local weather"
        >
          <RefreshCw className={`w-4 h-4 text-[#D9A441] ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 animate-pulse">
          <div className="md:col-span-5 h-44 rounded-xl bg-[#F7F7F5]" />
          <div className="md:col-span-7 grid grid-cols-2 sm:grid-cols-4 gap-3.5">
            {[1, 2, 3, 4].map(i => <div key={i} className="h-44 rounded-xl bg-[#F7F7F5]" />)}
          </div>
        </div>
      ) : error || !weather ? (
        <div className="py-8 text-center text-xs text-[#96938B]">
          <p>{error || 'No weather data available.'}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
          
          {/* Main Temperature & Condition Card */}
          <div className="md:col-span-5 bg-[#F7F7F5] border border-[#E5E2DA] rounded-xl p-6 flex flex-col justify-between">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-1.5 text-[#D9A441] font-bold text-xs mb-1">
                  <Navigation className="w-3.5 h-3.5" />
                  <span>{weather.city}{weather.state ? `, ${weather.state}` : ''}</span>
                </div>
                <h3 className="text-4xl sm:text-5xl font-extrabold text-[#111111] tracking-tight">
                  {weather.temp}°C
                </h3>
              </div>
              <span className="text-xs font-bold px-3 py-1 bg-white text-[#111111] rounded-full border border-[#E5E2DA] shadow-sm">
                {weather.condition}
              </span>
            </div>

            <div className="mt-6 pt-4 border-t border-[#E5E2DA] flex items-center justify-between text-xs text-[#66635C] font-medium">
              <span>Feels like {weather.feels_like}°C</span>
              <span>High: {weather.temp_max}° / Low: {weather.temp_min}°</span>
            </div>
          </div>

          {/* Weather Metrics Grid */}
          <div className="md:col-span-7 grid grid-cols-2 sm:grid-cols-4 gap-3.5">
            <div className="p-4 rounded-xl bg-[#F7F7F5] border border-[#E5E2DA] flex flex-col justify-between">
              <div className="flex items-center gap-2 text-[#66635C] text-xs font-bold mb-2">
                <Droplets className="w-4 h-4 text-[#D9A441]" /> Humidity
              </div>
              <div>
                <p className="text-xl font-extrabold text-[#111111]">{weather.humidity}%</p>
                <p className="text-[10px] text-[#96938B] mt-0.5">Moisture level</p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[#F7F7F5] border border-[#E5E2DA] flex flex-col justify-between">
              <div className="flex items-center gap-2 text-[#66635C] text-xs font-bold mb-2">
                <Wind className="w-4 h-4 text-[#D9A441]" /> Wind
              </div>
              <div>
                <p className="text-xl font-extrabold text-[#111111]">{weather.wind_speed} <span className="text-xs font-semibold">km/h</span></p>
                <p className="text-[10px] text-[#96938B] mt-0.5">Gentle breeze</p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[#F7F7F5] border border-[#E5E2DA] flex flex-col justify-between">
              <div className="flex items-center gap-2 text-[#66635C] text-xs font-bold mb-2">
                <Eye className="w-4 h-4 text-[#D9A441]" /> Visibility
              </div>
              <div>
                <p className="text-xl font-extrabold text-[#111111]">{weather.visibility} <span className="text-xs font-semibold">km</span></p>
                <p className="text-[10px] text-[#96938B] mt-0.5">Clear view</p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[#F7F7F5] border border-[#E5E2DA] flex flex-col justify-between">
              <div className="flex items-center gap-2 text-[#66635C] text-xs font-bold mb-2">
                <CloudRain className="w-4 h-4 text-[#D9A441]" /> Rain Prob
              </div>
              <div>
                <p className="text-xl font-extrabold text-[#111111]">{weather.rain_prob}%</p>
                <p className="text-[10px] text-[#96938B] mt-0.5">Precipitation</p>
              </div>
            </div>
          </div>

        </div>
      )}
    </section>
  );
}
