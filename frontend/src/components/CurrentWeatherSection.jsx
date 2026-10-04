import React, { useEffect, useState } from 'react';
import {
  Sun, CloudSun, CloudRain, Zap, CloudFog, Snowflake, Cloud,
  Wind, Droplets, Eye, Sunrise, Sunset, RefreshCw
} from 'lucide-react';
import { api } from '../services/api.js';
import { useLocationContext } from '../context/LocationContext.jsx';

function getWeatherIcon(code, condition = '') {
  const condLower = (condition || '').toLowerCase();
  if (code === 0 || code === 1 || condLower.includes('clear') || condLower.includes('sunny')) {
    return <Sun className="w-16 h-16 text-[#D9A441]" />;
  }
  if (code === 95 || code === 96 || code === 99 || condLower.includes('thunder')) {
    return <Zap className="w-16 h-16 text-[#111111] dark:text-white" />;
  }
  if ((code >= 51 && code <= 65) || (code >= 80 && code <= 82) || condLower.includes('rain') || condLower.includes('drizzle')) {
    return <CloudRain className="w-16 h-16 text-[#66635C] dark:text-stone-300" />;
  }
  if (code === 45 || code === 48 || condLower.includes('fog') || condLower.includes('mist')) {
    return <CloudFog className="w-16 h-16 text-[#96938B]" />;
  }
  if (condLower.includes('snow')) {
    return <Snowflake className="w-16 h-16 text-[#66635C] dark:text-stone-300" />;
  }
  if (code === 3 || condLower.includes('overcast')) {
    return <Cloud className="w-16 h-16 text-[#66635C]" />;
  }
  return <CloudSun className="w-16 h-16 text-[#D9A441]" />;
}

function getUvDescription(uv) {
  if (uv == null || isNaN(uv)) return '—';
  if (uv <= 2) return 'Low UV';
  if (uv <= 5) return 'Moderate UV';
  if (uv <= 7) return 'High UV';
  if (uv <= 10) return 'Very High UV';
  return 'Extreme UV';
}

function getHumidityDescription(humidity) {
  if (humidity == null || isNaN(humidity)) return '—';
  if (humidity < 30) return 'Dry air';
  if (humidity <= 60) return 'Humidity is good';
  if (humidity <= 80) return 'Humid conditions';
  return 'High moisture';
}

export default function CurrentWeatherSection() {
  const { selectedLocation } = useLocationContext();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchWeather = async (city, lat, lon) => {
    setLoading(true);
    setError(null);
    try {
      let backendUrl = `/api/weather/forecast?city=${encodeURIComponent(city)}`;
      if (lat && lon) backendUrl += `&latitude=${lat}&longitude=${lon}`;
      
      const backendRes = await api.get(backendUrl);
      const backendForecast = backendRes.data?.forecast?.[0] || {};

      const targetLat = lat || backendRes.data?.latitude || 28.6139;
      const targetLon = lon || backendRes.data?.longitude || 77.2090;

      const openMeteoUrl = `https://api.open-meteo.com/v1/forecast?latitude=${targetLat}&longitude=${targetLon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,visibility&daily=sunrise,sunset,uv_index_max&timezone=Asia%2FKolkata&forecast_days=1`;

      let liveMetrics = {};
      try {
        const omResp = await fetch(openMeteoUrl);
        if (omResp.ok) {
          const omData = await omResp.json();
          const current = omData.current || {};
          const daily = omData.daily || {};

          let sunriseFormatted = '—';
          if (daily.sunrise?.[0]) {
            const dt = new Date(daily.sunrise[0]);
            sunriseFormatted = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
          }

          let sunsetFormatted = '—';
          if (daily.sunset?.[0]) {
            const dt = new Date(daily.sunset[0]);
            sunsetFormatted = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
          }

          liveMetrics = {
            currentTemp: current.temperature_2m != null ? Math.round(current.temperature_2m) : null,
            humidity: current.relative_humidity_2m != null ? current.relative_humidity_2m : null,
            windSpeed: current.wind_speed_10m != null ? current.wind_speed_10m : null,
            visibility: current.visibility != null ? Math.round(current.visibility / 1000) : null,
            weatherCode: current.weather_code != null ? current.weather_code : null,
            sunrise: sunriseFormatted,
            sunset: sunsetFormatted,
            uvIndex: daily.uv_index_max?.[0] != null ? Math.round(daily.uv_index_max[0]) : null,
          };
        }
      } catch (err) {
        console.warn('Open-Meteo direct fetch notice:', err);
      }

      const temp = liveMetrics.currentTemp ?? backendForecast.temp_max ?? 22;
      const condition = backendForecast.condition || 'Partly Cloudy';
      const humidity = liveMetrics.humidity ?? backendForecast.humidity ?? 65;
      const windSpeed = liveMetrics.windSpeed ?? backendForecast.wind_speed ?? 12;
      const visibility = liveMetrics.visibility ?? backendForecast.visibility ?? 8;
      const sunrise = liveMetrics.sunrise !== '—' ? liveMetrics.sunrise : '06:00 AM';
      const sunset = liveMetrics.sunset !== '—' ? liveMetrics.sunset : '06:30 PM';
      const uvIndex = liveMetrics.uvIndex ?? 4;
      const weatherCode = liveMetrics.weatherCode ?? backendForecast.weather_code ?? 2;

      setData({
        city: backendRes.data?.city || city,
        state: selectedLocation.state || '',
        temp,
        condition,
        humidity,
        windSpeed,
        visibility,
        sunrise,
        sunset,
        uvIndex,
        weatherCode,
        obsTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });
    } catch (err) {
      console.error('Error loading weather conditions:', err);
      setError('Failed to load current weather conditions.');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchWeather(selectedLocation.city, selectedLocation.latitude, selectedLocation.longitude);
  }, [selectedLocation]);

  return (
    <section className="space-y-4 font-sans" aria-label="Current Weather and Highlights">
      {/* Section Header */}
      <div className="flex items-center justify-between pb-2 border-b border-[#E5E2DA] dark:border-[#262938]">
        <div>
          <h2 className="text-xl font-bold text-[#111111] dark:text-white tracking-tight">
            Weather Conditions
          </h2>
          <p className="text-xs text-[#66635C] dark:text-[#9CA3AF] mt-0.5 font-normal">
            Real-time observations for {selectedLocation.city}{selectedLocation.state ? `, ${selectedLocation.state}` : ''}
          </p>
        </div>
        <button
          onClick={() => fetchWeather(selectedLocation.city, selectedLocation.latitude, selectedLocation.longitude)}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-[#66635C] dark:text-[#9CA3AF] hover:text-[#111111] dark:hover:text-white bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-pulse">
          <div className="lg:col-span-5 h-64 bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-xl p-6" />
          <div className="lg:col-span-7 h-64 bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-xl p-6" />
        </div>
      ) : error || !data ? (
        <div className="p-8 text-center bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-xl text-xs text-[#66635C]">
          {error || 'Weather data unavailable.'}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          
          {/* LEFT PANEL — Large Current Weather Card */}
          <div className="lg:col-span-5 bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-xl p-6 flex flex-col justify-between shadow-subtle">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-[11px] font-semibold text-[#96938B] uppercase tracking-wider">
                  CURRENT WEATHER
                </span>
                <span className="text-xs text-[#66635C] dark:text-[#9CA3AF]">
                  {data.obsTime}
                </span>
              </div>

              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-6xl font-extrabold text-[#111111] dark:text-white leading-none tracking-tight">
                      {data.temp}°
                    </span>
                    <span className="text-2xl font-bold text-[#66635C] dark:text-[#9CA3AF]">
                      C
                    </span>
                  </div>
                  <p className="text-base font-semibold text-[#111111] dark:text-white mt-2">
                    {data.condition}
                  </p>
                </div>

                <div className="shrink-0 p-2">
                  {getWeatherIcon(data.weatherCode, data.condition)}
                </div>
              </div>
            </div>

            {/* Compact Observation Row */}
            <div className="mt-6 pt-4 border-t border-[#E5E2DA] dark:border-[#262938] grid grid-cols-3 gap-2 text-xs">
              <div>
                <span className="text-[11px] text-[#96938B] block">Wind</span>
                <span className="font-semibold text-[#111111] dark:text-white">{data.windSpeed} km/h</span>
              </div>
              <div>
                <span className="text-[11px] text-[#96938B] block">Humidity</span>
                <span className="font-semibold text-[#111111] dark:text-white">{data.humidity}%</span>
              </div>
              <div>
                <span className="text-[11px] text-[#96938B] block">Visibility</span>
                <span className="font-semibold text-[#111111] dark:text-white">{data.visibility} km</span>
              </div>
            </div>
          </div>

          {/* RIGHT PANEL — Today's Highlights Grid */}
          <div className="lg:col-span-7 bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-xl p-6 flex flex-col justify-between shadow-subtle">
            <h3 className="text-base font-bold text-[#111111] dark:text-white mb-4">
              Today's Highlights
            </h3>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              
              {/* 1. Wind Status */}
              <div className="p-3.5 rounded-lg bg-[#F7F7F5] dark:bg-[#0F1117] border border-[#E5E2DA] dark:border-[#262938] flex flex-col justify-between">
                <div className="flex items-center gap-1.5 text-xs text-[#66635C] dark:text-[#9CA3AF] mb-2 font-medium">
                  <Wind className="w-4 h-4 text-[#111111] dark:text-white" />
                  <span>Wind Status</span>
                </div>
                <div>
                  <p className="text-lg font-extrabold text-[#111111] dark:text-white">
                    {data.windSpeed} <span className="text-xs font-normal text-[#66635C]">km/h</span>
                  </p>
                  <p className="text-[11px] text-[#96938B] mt-0.5">
                    {data.obsTime}
                  </p>
                </div>
              </div>

              {/* 2. Humidity */}
              <div className="p-3.5 rounded-lg bg-[#F7F7F5] dark:bg-[#0F1117] border border-[#E5E2DA] dark:border-[#262938] flex flex-col justify-between">
                <div className="flex items-center gap-1.5 text-xs text-[#66635C] dark:text-[#9CA3AF] mb-2 font-medium">
                  <Droplets className="w-4 h-4 text-[#111111] dark:text-white" />
                  <span>Humidity</span>
                </div>
                <div>
                  <p className="text-lg font-extrabold text-[#111111] dark:text-white">
                    {data.humidity}%
                  </p>
                  <p className="text-[11px] text-[#96938B] mt-0.5">
                    {getHumidityDescription(data.humidity)}
                  </p>
                </div>
              </div>

              {/* 3. Sunrise */}
              <div className="p-3.5 rounded-lg bg-[#F7F7F5] dark:bg-[#0F1117] border border-[#E5E2DA] dark:border-[#262938] flex flex-col justify-between">
                <div className="flex items-center gap-1.5 text-xs text-[#66635C] dark:text-[#9CA3AF] mb-2 font-medium">
                  <Sunrise className="w-4 h-4 text-[#D9A441]" />
                  <span>Sunrise</span>
                </div>
                <div>
                  <p className="text-lg font-extrabold text-[#111111] dark:text-white">
                    {data.sunrise}
                  </p>
                  <p className="text-[11px] text-[#96938B] mt-0.5">
                    Dawn observation
                  </p>
                </div>
              </div>

              {/* 4. UV Index */}
              <div className="p-3.5 rounded-lg bg-[#F7F7F5] dark:bg-[#0F1117] border border-[#E5E2DA] dark:border-[#262938] flex flex-col justify-between">
                <div className="flex items-center gap-1.5 text-xs text-[#66635C] dark:text-[#9CA3AF] mb-2 font-medium">
                  <Sun className="w-4 h-4 text-[#D9A441]" />
                  <span>UV Index</span>
                </div>
                <div>
                  <p className="text-lg font-extrabold text-[#111111] dark:text-white">
                    {data.uvIndex} <span className="text-xs font-normal text-[#66635C]">UV</span>
                  </p>
                  <p className="text-[11px] text-[#96938B] mt-0.5">
                    {getUvDescription(data.uvIndex)}
                  </p>
                </div>
              </div>

              {/* 5. Visibility */}
              <div className="p-3.5 rounded-lg bg-[#F7F7F5] dark:bg-[#0F1117] border border-[#E5E2DA] dark:border-[#262938] flex flex-col justify-between">
                <div className="flex items-center gap-1.5 text-xs text-[#66635C] dark:text-[#9CA3AF] mb-2 font-medium">
                  <Eye className="w-4 h-4 text-[#111111] dark:text-white" />
                  <span>Visibility</span>
                </div>
                <div>
                  <p className="text-lg font-extrabold text-[#111111] dark:text-white">
                    {data.visibility} <span className="text-xs font-normal text-[#66635C]">km</span>
                  </p>
                  <p className="text-[11px] text-[#96938B] mt-0.5">
                    Horizontal range
                  </p>
                </div>
              </div>

              {/* 6. Sunset */}
              <div className="p-3.5 rounded-lg bg-[#F7F7F5] dark:bg-[#0F1117] border border-[#E5E2DA] dark:border-[#262938] flex flex-col justify-between">
                <div className="flex items-center gap-1.5 text-xs text-[#66635C] dark:text-[#9CA3AF] mb-2 font-medium">
                  <Sunset className="w-4 h-4 text-[#D9A441]" />
                  <span>Sunset</span>
                </div>
                <div>
                  <p className="text-lg font-extrabold text-[#111111] dark:text-white">
                    {data.sunset}
                  </p>
                  <p className="text-[11px] text-[#96938B] mt-0.5">
                    Dusk observation
                  </p>
                </div>
              </div>

            </div>
          </div>

        </div>
      )}
    </section>
  );
}

