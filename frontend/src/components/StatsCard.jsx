import React from 'react';

export default function StatsCard({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = 'default',
  chartType = 'bars', // 'bars' | 'wave' | 'none'
  highlightIndex = -1,
  barHeights = [35, 55, 40, 85, 50, 95, 80],
}) {
  return (
    <div className="bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-xl p-5 sm:p-6 flex flex-col justify-between transition-all duration-200 shadow-subtle relative overflow-hidden group">
      <div>
        {/* Card Header: Uppercase Label & Icon Badge */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <span className="text-[11px] font-bold tracking-wider text-[#66635C] dark:text-stone-300 uppercase font-sans">
            {title}
          </span>
          {Icon && (
            <div className={`w-8.5 h-8.5 rounded-full flex items-center justify-center shrink-0 transition-transform duration-200 group-hover:scale-105 ${
              variant === 'primary' 
                ? 'bg-[#F7EED7] dark:bg-amber-950/40 text-[#111111] dark:text-amber-300 border border-[#D9A441]/30' 
                : 'bg-stone-100/90 dark:bg-stone-800/80 text-[#111111] dark:text-stone-300 border border-[#E5E2DA] dark:border-stone-700/50'
            }`}>
              <Icon className="w-4 h-4 stroke-[2]" />
            </div>
          )}
        </div>

        {/* Large Metric Value */}
        <div className="text-3xl sm:text-4xl font-extrabold text-[#111111] dark:text-[#faf9f6] tracking-tight leading-none font-sans">
          {value}
        </div>
      </div>

      {/* Footer: Subtitle & Micro-chart */}
      <div className="flex items-end justify-between gap-2 mt-5 pt-1">
        {subtitle ? (
          <p className="text-[12px] text-[#66635C] dark:text-stone-300 font-medium leading-tight max-w-[65%]">
            {subtitle}
          </p>
        ) : <div />}

        {/* Micro-chart Visualizations */}
        {chartType === 'bars' && (
          <div className="flex items-end gap-[3px] h-7 shrink-0 pb-0.5">
            {barHeights.map((h, i) => {
              const isHighlight = highlightIndex === i || (highlightIndex === -1 && (i === barHeights.length - 2 || i === barHeights.length - 1));
              return (
                <div
                  key={i}
                  className={`w-1.5 rounded-full transition-all duration-300 ${
                    isHighlight
                      ? 'bg-[#D9A441]'
                      : 'bg-stone-200 dark:bg-stone-800'
                  }`}
                  style={{ height: `${h}%` }}
                />
              );
            })}
          </div>
        )}

        {chartType === 'wave' && (
          <div className="w-20 h-7 shrink-0 flex items-center justify-end">
            <svg className="w-full h-full overflow-visible" viewBox="0 0 80 28" fill="none">
              <path
                d="M 2 20 Q 20 28, 35 15 T 65 18 T 76 8"
                fill="none"
                stroke="#D9A441"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
              <circle cx="76" cy="8" r="3" fill="#D9A441" />
            </svg>
          </div>
        )}
      </div>
    </div>
  );
}



