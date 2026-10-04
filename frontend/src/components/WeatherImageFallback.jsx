import React from 'react';

export default function WeatherImageFallback({ className = '' }) {
  return (
    <div className={`w-full h-full bg-[#E5E2DA] dark:bg-[#1E2130] flex items-center justify-center ${className}`}>
      <div className="w-8 h-8 rounded-full border-2 border-stone-300 dark:border-stone-700 bg-stone-200 dark:bg-stone-800 flex items-center justify-center opacity-40">
        <span className="text-[10px] font-bold text-stone-500 dark:text-stone-400">ATMOS</span>
      </div>
    </div>
  );
}
