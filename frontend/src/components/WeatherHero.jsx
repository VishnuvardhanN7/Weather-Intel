import React, { useEffect, useState, useRef } from 'react';
import { Search, Navigation, LocateFixed, Wind, Droplets, Eye, Check, X, Loader2, MapPin } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../services/api.js';
import { useLocationContext } from '../context/LocationContext.jsx';
import { INDIAN_CITIES } from '../utils/indianCities.js';

const POPULAR_CITIES = [
  { city: 'Vijayawada', state: 'Andhra Pradesh', latitude: 16.5062, longitude: 80.6480 },
  { city: 'Hyderabad', state: 'Telangana', latitude: 17.3850, longitude: 78.4867 },
  { city: 'Mumbai', state: 'Maharashtra', latitude: 19.0760, longitude: 72.8777 },
  { city: 'Delhi', state: 'Delhi', latitude: 28.6139, longitude: 77.2090 },
  { city: 'Bengaluru', state: 'Karnataka', latitude: 12.9716, longitude: 77.5946 },
  { city: 'Kolkata', state: 'West Bengal', latitude: 22.5726, longitude: 88.3639 },
  { city: 'Chennai', state: 'Tamil Nadu', latitude: 13.0827, longitude: 80.2707 },
];

// Motion Variants for Staggered Animations
const heroContainerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.15,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 18 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: 'easeOut' },
  },
};

export default function WeatherHero() {
  const {
    selectedLocation,
    setSelectedLocation,
    selectCityByName,
    requestUserLocation,
    loadingLocation,
  } = useLocationContext();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Search state
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const searchRef = useRef(null);

  // Filter search suggestions
  useEffect(() => {
    if (!query.trim()) {
      setSuggestions([]);
      return;
    }
    const timer = setTimeout(() => {
      const q = query.trim().toLowerCase();
      const filtered = INDIAN_CITIES.filter(
        (item) => item.city.toLowerCase().includes(q) || item.state.toLowerCase().includes(q)
      ).slice(0, 8);
      setSuggestions(filtered);
    }, 120);

    return () => clearTimeout(timer);
  }, [query]);

  // Click outside to close search suggestions
  useEffect(() => {
    function handleClickOutside(e) {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectCity = (cityObj) => {
    setSelectedLocation(cityObj);
    setQuery('');
    setIsOpen(false);
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (suggestions.length > 0) {
      handleSelectCity(suggestions[0]);
    } else if (query.trim()) {
      selectCityByName(query.trim());
      setQuery('');
      setIsOpen(false);
    }
  };

  // Fetch current weather for Hero
  const fetchHeroWeather = async (city, lat, lon) => {
    setLoading(true);
    try {
      let url = `/api/weather/forecast?city=${encodeURIComponent(city)}`;
      if (lat && lon) url += `&latitude=${lat}&longitude=${lon}`;

      const res = await api.get(url);
      const forecast = res.data?.forecast?.[0] || {};

      const targetLat = lat || res.data?.latitude || 28.6139;
      const targetLon = lon || res.data?.longitude || 77.2090;

      let liveTemp = null;
      let liveHumidity = null;
      let liveWind = null;
      let liveVis = null;

      try {
        const omUrl = `https://api.open-meteo.com/v1/forecast?latitude=${targetLat}&longitude=${targetLon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,visibility&timezone=Asia%2FKolkata`;
        const omRes = await fetch(omUrl);
        if (omRes.ok) {
          const omData = await omRes.json();
          const current = omData.current || {};
          if (current.temperature_2m != null) liveTemp = Math.round(current.temperature_2m);
          if (current.relative_humidity_2m != null) liveHumidity = current.relative_humidity_2m;
          if (current.wind_speed_10m != null) liveWind = current.wind_speed_10m;
          if (current.visibility != null) liveVis = Math.round(current.visibility / 1000);
        }
      } catch (err) {
        console.warn('Hero Open-Meteo notice:', err);
      }

      setData({
        city: res.data?.city || city,
        state: selectedLocation.state || '',
        temp: liveTemp ?? forecast.temp_max ?? 28,
        condition: forecast.condition || 'Partly Cloudy',
        humidity: liveHumidity ?? forecast.humidity ?? 65,
        windSpeed: liveWind ?? forecast.wind_speed ?? 12,
        visibility: liveVis ?? forecast.visibility ?? 10,
        obsTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });
    } catch (err) {
      console.error('Hero weather fetch error:', err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchHeroWeather(selectedLocation.city, selectedLocation.latitude, selectedLocation.longitude);
  }, [selectedLocation]);

  return (
    <section className="relative full-bleed-hero h-[100svh] min-h-[640px] flex flex-col justify-between overflow-hidden">
      {/* Background Image: High-Resolution Photographic Sky */}
      <img
        src="/1.jpg"
        alt="Atmospheric Weather Sky"
        className="absolute inset-0 w-full h-full object-cover object-center pointer-events-none"
      />

      {/* Subtle Restrained Overlay for High Contrast */}
      <div className="absolute inset-0 bg-[#111111]/35 backdrop-blur-[0.5px]" />

      {/* CENTER SECTION: Hero Search Bar & Popular City Pills (Positioned in Middle Region) */}
      <motion.div
        variants={heroContainerVariants}
        initial="hidden"
        animate="visible"
        className="relative z-20 pt-24 sm:pt-28 lg:pt-32 my-auto px-4 max-w-[640px] mx-auto w-full text-center"
      >
        
        {/* Search Bar Surface */}
        <motion.div variants={itemVariants} className="relative w-full" ref={searchRef}>
          <form onSubmit={handleFormSubmit} className="bg-white border border-[#E5E2DA] rounded-2xl p-2 shadow-2xl flex items-center gap-2">
            <Search className="w-5.5 h-5.5 text-[#96938B] ml-2.5 shrink-0" />
            <input
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setIsOpen(true);
              }}
              onFocus={() => setIsOpen(true)}
              placeholder="Search Indian city (e.g. Vijayawada, Delhi, Mumbai)..."
              className="flex-1 bg-transparent py-3 px-1 text-base font-medium text-[#111111] placeholder-[#96938B] focus:outline-none"
              aria-label="Search weather location"
            />
            {query && (
              <button
                type="button"
                onClick={() => { setQuery(''); setSuggestions([]); }}
                className="p-2 text-[#96938B] hover:text-[#111111] rounded-lg transition-colors"
              >
                <X className="w-4.5 h-4.5" />
              </button>
            )}

            {/* Use GPS Location Button */}
            <button
              type="button"
              onClick={requestUserLocation}
              disabled={loadingLocation}
              className="px-4 py-2.5 rounded-xl bg-[#111111] text-white hover:bg-stone-900 text-sm font-semibold flex items-center gap-2 shrink-0 transition-colors cursor-pointer border border-white/10"
              title="Use current GPS location"
            >
              {loadingLocation ? (
                <Loader2 className="w-4 h-4 animate-spin text-[#D9A441]" />
              ) : (
                <LocateFixed className="w-4 h-4 text-[#D9A441]" />
              )}
              <span className="hidden sm:inline">Use GPS</span>
            </button>
          </form>

          {/* Autocomplete Dropdown */}
          <AnimatePresence>
            {isOpen && suggestions.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 6 }}
                className="absolute left-0 right-0 top-full mt-2 bg-white border border-[#E5E2DA] rounded-2xl shadow-2xl p-2 z-50 overflow-hidden text-left"
              >
                <div className="px-3 py-2 text-[11px] font-bold text-[#96938B] uppercase tracking-wider border-b border-[#E5E2DA] mb-1">
                  Indian Cities ({suggestions.length})
                </div>
                <div className="max-h-56 overflow-y-auto space-y-1">
                  {suggestions.map((item) => {
                    const isSelected = selectedLocation.city.toLowerCase() === item.city.toLowerCase();
                    return (
                      <button
                        key={`${item.city}-${item.state}`}
                        onClick={() => handleSelectCity(item)}
                        className={`w-full text-left px-3.5 py-2.5 rounded-xl text-sm flex items-center justify-between transition-colors cursor-pointer ${
                          isSelected
                            ? 'bg-[#F7EED7] text-[#A97820] font-bold'
                            : 'hover:bg-[#F7F7F5] text-[#111111] font-medium'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <MapPin className={`w-4 h-4 ${isSelected ? 'text-[#D9A441]' : 'text-[#96938B]'}`} />
                          <span>{item.city}, <span className="text-[#66635C] font-normal">{item.state}</span></span>
                        </div>
                        {isSelected && <Check className="w-4 h-4 text-[#D9A441]" />}
                      </button>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Popular / Recent Location Pills */}
        <motion.div variants={itemVariants} className="mt-5 flex flex-wrap items-center justify-center gap-2 sm:gap-2.5">
          <span className="text-xs font-bold text-white/80 uppercase tracking-wider mr-1">
            Popular Cities:
          </span>
          {POPULAR_CITIES.map((c) => {
            const isSelected = selectedLocation.city.toLowerCase() === c.city.toLowerCase();
            return (
              <button
                key={c.city}
                onClick={() => setSelectedLocation(c)}
                className={`px-3.5 py-1.5 rounded-full text-xs sm:text-sm font-semibold transition-all backdrop-blur-md cursor-pointer ${
                  isSelected
                    ? 'bg-white text-[#111111] shadow-md scale-105'
                    : 'bg-white/20 hover:bg-white/35 text-white border border-white/20'
                }`}
              >
                {c.city}
              </button>
            );
          })}
        </motion.div>

      </motion.div>

      {/* BOTTOM SECTION: Current Weather Editorial Overlay */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4, ease: 'easeOut' }}
        className="relative z-10 p-6 sm:p-10 lg:p-14 text-white flex flex-col md:flex-row md:items-end justify-between gap-6"
      >
        
        {/* Bottom Left: Active Location & Large Temperature */}
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/20 text-white text-xs sm:text-sm font-semibold backdrop-blur-md border border-white/20">
            <Navigation className="w-4 h-4 text-[#D9A441]" />
            <span>{selectedLocation.city}{selectedLocation.state ? `, ${selectedLocation.state}` : ''}</span>
          </div>

          {loading || !data ? (
            <div className="py-4 animate-pulse">
              <div className="h-16 w-40 bg-white/20 rounded-xl mb-2" />
              <div className="h-7 w-52 bg-white/20 rounded-lg" />
            </div>
          ) : (
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-7xl sm:text-8xl lg:text-9xl font-extrabold tracking-tight leading-none text-white drop-shadow-lg">
                  {data.temp}°
                </span>
                <span className="text-3xl sm:text-4xl lg:text-5xl font-bold text-[#F7EED7] drop-shadow-md">
                  C
                </span>
              </div>
              <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white drop-shadow-md mt-1">
                {data.condition}
              </h2>
              <p className="text-xs sm:text-sm text-white/85 font-medium pt-1">
                Live Meteorological Observation · Updated {data.obsTime}
              </p>
            </div>
          )}
        </div>

        {/* Bottom Right: Key Meteorological Stats Pill Grid */}
        {data && (
          <div className="grid grid-cols-3 gap-3 sm:gap-4 max-w-md w-full bg-black/25 backdrop-blur-md p-4 sm:p-5 rounded-2xl border border-white/20 text-xs sm:text-sm">
            <div className="flex items-center gap-3">
              <Wind className="w-5 h-5 text-[#D9A441] shrink-0" />
              <div>
                <span className="text-[10px] sm:text-xs text-white/70 block uppercase font-semibold">Wind</span>
                <span className="font-extrabold text-white text-sm sm:text-base">{data.windSpeed} <span className="text-[10px] font-normal">km/h</span></span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Droplets className="w-5 h-5 text-[#D9A441] shrink-0" />
              <div>
                <span className="text-[10px] sm:text-xs text-white/70 block uppercase font-semibold">Humidity</span>
                <span className="font-extrabold text-white text-sm sm:text-base">{data.humidity}%</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Eye className="w-5 h-5 text-[#D9A441] shrink-0" />
              <div>
                <span className="text-[10px] sm:text-xs text-white/70 block uppercase font-semibold">Visibility</span>
                <span className="font-extrabold text-white text-sm sm:text-base">{data.visibility} <span className="text-[10px] font-normal">km</span></span>
              </div>
            </div>
          </div>
        )}

      </motion.div>
    </section>
  );
}

