import React, { useEffect, useState, useCallback } from 'react';
import WeatherHero from '../components/WeatherHero.jsx';
import CurrentWeatherSection from '../components/CurrentWeatherSection.jsx';
import Forecast10Day from '../components/Forecast10Day.jsx';
import WeatherNews from '../components/WeatherNews.jsx';
import { api } from '../services/api.js';
import { isTestEvent } from '../utils/eventFormatter.js';

export default function Dashboard() {
  const [events, setEvents] = useState([]);

  const fetchData = useCallback(async () => {
    try {
      const eventsRes = await api.get('/api/weather?per_page=100');
      if (eventsRes.data && eventsRes.data.data) {
        const clean = (eventsRes.data.data || []).filter(e => !isTestEvent(e));
        setEvents(clean);
      }
    } catch (err) {
      console.error('Dashboard fetch error:', err);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <div className="font-sans" role="main" aria-label="Weather Intel Home Page">
      
      {/* 1. FULL-WIDTH HERO SECTION (WITH PHOTOGRAPHIC BACKGROUND /1.jpg & INTEGRATED NAVBAR OVERLAY) */}
      <WeatherHero />

      {/* LOWER HOMEPAGE CONTENT CONTAINER (Appears ONLY when user scrolls down, with ~56px-64px breathing space) */}
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 space-y-12 mt-14 sm:mt-16 pb-16">
        {/* 2. WEATHER CONDITIONS (DETAILED METEOROLOGICAL BREAKDOWN & TODAY'S HIGHLIGHTS) */}
        <CurrentWeatherSection />

        {/* 3. 10-DAY FORECAST */}
        <Forecast10Day />

        {/* 4. LATEST WEATHER NEWS */}
        <WeatherNews fallbackEvents={events} />
      </div>

    </div>
  );
}
