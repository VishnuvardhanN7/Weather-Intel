import React, { useState, useEffect, useRef } from 'react';
import { Search, MapPin, LocateFixed, X, Check, Loader2, AlertCircle } from 'lucide-react';
import { useLocationContext } from '../context/LocationContext.jsx';
import { INDIAN_CITIES } from '../utils/indianCities.js';

export default function CitySearch() {
  const { selectedLocation, setSelectedLocation, selectCityByName, requestUserLocation, loadingLocation, locationDenied } = useLocationContext();
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const searchRef = useRef(null);

  // Debounced search suggestions filter
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
    }, 150);

    return () => clearTimeout(timer);
  }, [query]);

  // Handle clicking outside to close suggestions
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

  return (
    <div className="relative z-30 w-full flex justify-center my-1" ref={searchRef}>
      <div className="w-full sm:w-[85%] lg:w-[70%] max-w-[1020px] mx-auto relative">
        
        {/* Centered Compact Control Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sm:gap-4 bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-xl px-4 py-2.5 min-h-[60px] shadow-subtle">
          
          {/* LEFT: Active City Badge */}
          <div className="flex items-center gap-2.5 shrink-0">
            <div className="w-8 h-8 rounded-lg bg-[#D9A441]/15 text-[#D9A441] flex items-center justify-center shrink-0 border border-[#D9A441]/30">
              <MapPin className="w-4 h-4 text-[#D9A441]" />
            </div>
            <div>
              <span className="text-[10px] font-semibold text-[#96938B] uppercase tracking-wider block">
                Active City
              </span>
              <span className="text-xs font-bold text-[#111111] dark:text-white tracking-tight flex items-center gap-1.5">
                {selectedLocation.city}{selectedLocation.state ? `, ${selectedLocation.state}` : ''}
                {selectedLocation.isUserLocation && (
                  <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-[#2E7D5B]/10 text-[#2E7D5B]">
                    GPS
                  </span>
                )}
              </span>
            </div>
          </div>

          {/* CENTER: Compact Search Input (~420px max-width) */}
          <div className="flex-1 max-w-[420px] mx-auto w-full relative">
            <form onSubmit={handleFormSubmit} className="relative w-full flex items-center">
              <Search className="w-4 h-4 text-[#96938B] absolute left-3 pointer-events-none" />
              <input
                type="text"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setIsOpen(true);
                }}
                onFocus={() => setIsOpen(true)}
                placeholder="Search Indian city (e.g. Vijayawada, Hyderabad, Delhi)..."
                className="w-full pl-9 pr-8 py-2 bg-[#F7F7F5] dark:bg-[#0F1117] border border-[#E5E2DA] dark:border-[#262938] rounded-md text-xs font-medium text-[#111111] dark:text-white placeholder-[#96938B] focus:outline-none focus:border-[#D9A441]"
                aria-label="Search city or location"
              />
              {query && (
                <button
                  type="button"
                  onClick={() => { setQuery(''); setSuggestions([]); }}
                  className="absolute right-2.5 p-1 text-[#96938B] hover:text-[#111111] dark:hover:text-white rounded-md"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </form>

            {/* Suggestions Dropdown (Directly under search input) */}
            {isOpen && suggestions.length > 0 && (
              <div className="absolute left-0 right-0 mt-1.5 bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-lg shadow-lg p-2 z-50 overflow-hidden">
                <div className="px-2.5 py-1 text-[10px] font-semibold text-[#96938B] uppercase tracking-wider border-b border-[#E5E2DA] dark:border-[#262938] mb-1">
                  Indian Cities ({suggestions.length})
                </div>
                <div className="max-h-56 overflow-y-auto space-y-0.5">
                  {suggestions.map((item) => {
                    const isSelected = selectedLocation.city.toLowerCase() === item.city.toLowerCase();
                    return (
                      <button
                        key={`${item.city}-${item.state}`}
                        onClick={() => handleSelectCity(item)}
                        className={`w-full text-left px-3 py-2 rounded-md text-xs flex items-center justify-between transition-colors ${
                          isSelected
                            ? 'bg-[#F7EED7] text-[#A97820] font-semibold'
                            : 'hover:bg-[#F7F7F5] dark:hover:bg-[#0F1117] text-[#111111] dark:text-stone-200 font-normal'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <MapPin className={`w-3.5 h-3.5 ${isSelected ? 'text-[#D9A441]' : 'text-[#96938B]'}`} />
                          <span>{item.city}, <span className="text-[#66635C] font-normal">{item.state}</span></span>
                        </div>
                        {isSelected && <Check className="w-3.5 h-3.5 text-[#D9A441]" />}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* RIGHT: Device Location Trigger Button */}
          <button
            onClick={requestUserLocation}
            disabled={loadingLocation}
            className="px-3 py-2 rounded-md bg-[#F7F7F5] dark:bg-[#0F1117] hover:bg-[#E5E2DA] dark:hover:bg-[#262938] text-[#111111] dark:text-white text-xs font-medium transition-colors flex items-center gap-1.5 shrink-0 border border-[#E5E2DA] dark:border-[#262938] cursor-pointer"
            title="Use current device GPS location"
            aria-label="Use current device GPS location"
          >
            {loadingLocation ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-[#D9A441]" />
            ) : (
              <LocateFixed className="w-3.5 h-3.5 text-[#D9A441]" />
            )}
            <span className="hidden sm:inline">Use GPS</span>
          </button>

        </div>

        {/* Geolocation Denied / Warning Banner */}
        {locationDenied && (
          <div className="mt-2 px-3 py-1.5 rounded-md bg-[#F7F7F5] border border-[#E5E2DA] text-[#66635C] text-xs font-medium flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-[#D9A441] shrink-0" />
            <span>GPS access off. Showing weather for {selectedLocation.city}. Type a city name to search.</span>
          </div>
        )}

      </div>
    </div>
  );
}


