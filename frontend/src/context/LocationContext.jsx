import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { DEFAULT_LOCATION, findNearestCity, findCityByName } from '../utils/indianCities.js';

const LocationContext = createContext(null);
const STORAGE_KEY = 'atmos_selected_location';

export function LocationProvider({ children }) {
  const [selectedLocation, setSelectedLocationState] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed && parsed.city) return parsed;
      }
    } catch {
      /* ignore */
    }
    return DEFAULT_LOCATION;
  });

  const [loadingLocation, setLoadingLocation] = useState(false);
  const [locationDenied, setLocationDenied] = useState(false);

  const setLocation = useCallback((loc) => {
    if (!loc || !loc.city) return;
    const resolved = {
      city: loc.city,
      state: loc.state || '',
      latitude: loc.latitude || 20.5937,
      longitude: loc.longitude || 78.9629,
      isUserLocation: Boolean(loc.isUserLocation),
    };
    setSelectedLocationState(resolved);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(resolved));
    } catch {
      /* ignore */
    }
  }, []);

  const selectCityByName = useCallback((cityName) => {
    const found = findCityByName(cityName);
    if (found) {
      setLocation(found);
      return true;
    } else {
      // Create fallback city entry
      setLocation({
        city: cityName,
        state: '',
        latitude: 20.5937,
        longitude: 78.9629,
      });
      return false;
    }
  }, [setLocation]);

  const requestUserLocation = useCallback(() => {
    if (!('geolocation' in navigator)) {
      setLocationDenied(true);
      return;
    }

    setLoadingLocation(true);
    setLocationDenied(false);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        const nearest = findNearestCity(latitude, longitude);
        setLocation({
          city: nearest.city,
          state: nearest.state,
          latitude: latitude, // Use actual device coordinates for map centering
          longitude: longitude,
          isUserLocation: true,
        });
        setLoadingLocation(false);
      },
      (error) => {
        console.warn('Browser geolocation denied or failed:', error.message);
        setLocationDenied(true);
        setLoadingLocation(false);
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 600000 }
    );
  }, [setLocation]);

  // Request location on first visit if no manual city saved in localStorage
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      requestUserLocation();
    }
  }, [requestUserLocation]);

  const value = {
    selectedLocation,
    setSelectedLocation: setLocation,
    selectCityByName,
    requestUserLocation,
    loadingLocation,
    locationDenied,
  };

  return <LocationContext.Provider value={value}>{children}</LocationContext.Provider>;
}

export function useLocationContext() {
  const ctx = useContext(LocationContext);
  if (!ctx) throw new Error('useLocationContext must be used within LocationProvider');
  return ctx;
}

export default LocationContext;
