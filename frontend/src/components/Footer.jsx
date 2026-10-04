import React from 'react';
import { Link } from 'react-router-dom';
import { CloudSun } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-[#0A0B10] border-t border-[#262938] mt-12 py-8 sm:py-10 px-4 sm:px-6 lg:px-8 font-sans text-white relative">
      {/* Subtle top gold accent line */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-[1px] bg-gradient-to-r from-transparent via-[#D9A441]/50 to-transparent" />

      <div className="max-w-[1500px] mx-auto space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 pb-8 border-b border-[#262938]">
          
          {/* LEFT / BRAND (col-span-4) */}
          <div className="md:col-span-4 space-y-3.5">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-[#161822] border border-[#262938] flex items-center justify-center text-[#D9A441] shadow-sm">
                <CloudSun className="w-4 h-4 text-[#D9A441]" />
              </div>
              <span className="text-lg font-extrabold text-white tracking-tight uppercase">
                WEATHER INTEL
              </span>
            </div>
            
            <p className="text-xs font-semibold text-[#E5E2DA]">
              National Weather Big Data Analytics Platform
            </p>
            
            <p className="text-xs text-[#96938B] leading-relaxed max-w-sm">
              Real-time weather intelligence for India.
            </p>

            {/* LIVE WEATHER INTELLIGENCE STATUS INDICATOR */}
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#161822] border border-[#262938] text-[11px] font-extrabold tracking-wider text-white shadow-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-emerald-400">LIVE WEATHER INTELLIGENCE</span>
            </div>
          </div>

          {/* RIGHT / COLUMNS (col-span-8) */}
          <div className="md:col-span-8 grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-8">
            
            {/* PLATFORM */}
            <div className="space-y-3">
              <h4 className="text-[11px] font-extrabold text-[#D9A441] uppercase tracking-wider">
                PLATFORM
              </h4>
              <ul className="space-y-2 text-xs font-medium text-[#96938B]">
                <li>
                  <Link to="/dashboard" className="hover:text-white transition-colors duration-150 inline-block">
                    Dashboard
                  </Link>
                </li>
                <li>
                  <Link to="/weather-map" className="hover:text-white transition-colors duration-150 inline-block">
                    Weather Map
                  </Link>
                </li>
                <li>
                  <Link to="/stories" className="hover:text-white transition-colors duration-150 inline-block">
                    Stories
                  </Link>
                </li>
                <li>
                  <Link to="/analytics" className="hover:text-white transition-colors duration-150 inline-block">
                    Analytics
                  </Link>
                </li>
              </ul>
            </div>

            {/* INTELLIGENCE */}
            <div className="space-y-3">
              <h4 className="text-[11px] font-extrabold text-[#D9A441] uppercase tracking-wider">
                INTELLIGENCE
              </h4>
              <ul className="space-y-2 text-xs font-medium text-[#96938B]">
                <li>
                  <Link to="/events" className="hover:text-white transition-colors duration-150 inline-block">
                    Weather Events
                  </Link>
                </li>
                <li>
                  <Link to="/dashboard" className="hover:text-white transition-colors duration-150 inline-block">
                    Live Monitoring
                  </Link>
                </li>
                <li>
                  <Link to="/ask-intel" className="hover:text-white transition-colors duration-150 inline-block">
                    AI Intelligence
                  </Link>
                </li>
                <li>
                  <Link to="/ask-intel" className="hover:text-white transition-colors duration-150 inline-block">
                    Ask Intel
                  </Link>
                </li>
              </ul>
            </div>

            {/* SYSTEM */}
            <div className="space-y-3">
              <h4 className="text-[11px] font-extrabold text-[#D9A441] uppercase tracking-wider">
                SYSTEM
              </h4>
              <ul className="space-y-2 text-xs font-medium text-[#96938B]">
                <li>
                  <Link to="/admin" className="hover:text-white transition-colors duration-150 inline-block">
                    Admin Panel
                  </Link>
                </li>
                <li>
                  <a 
                    href="/api/health" 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="hover:text-white transition-colors duration-150 inline-block"
                  >
                    API Status
                  </a>
                </li>
                <li>
                  <span className="inline-flex items-center gap-1.5 text-[#96938B] hover:text-white transition-colors duration-150 cursor-pointer">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    <span>System Status</span>
                  </span>
                </li>
              </ul>
            </div>

          </div>

        </div>

        {/* BOTTOM BAR */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[#96938B] font-medium pt-1">
          <p>© 2026 Weather Intel · National Weather Big Data Analytics Platform</p>
          <p className="text-xs font-bold text-stone-300 tracking-wider">LIVE DATA • INDIA</p>
        </div>
      </div>
    </footer>
  );
}


