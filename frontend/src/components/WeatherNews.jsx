import React, { useEffect, useState } from 'react';
import { ArrowRight, ExternalLink, ShieldAlert, Play, Clock, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '../services/api.js';
import WeatherImageFallback from './WeatherImageFallback.jsx';

function formatRelativeTime(dateInput) {
  if (!dateInput) return 'Recently';
  const date = new Date(dateInput);
  if (isNaN(date.getTime())) return 'Recently';

  const now = new Date();
  const diffSec = Math.floor((now - date) / 1000);

  if (diffSec < 60) return 'Just now';
  if (diffSec < 3600) {
    const min = Math.floor(diffSec / 60);
    return `${min} ${min === 1 ? 'min' : 'mins'} ago`;
  }
  if (diffSec < 86400) {
    const hours = Math.floor(diffSec / 3600);
    return `${hours} ${hours === 1 ? 'hr' : 'hrs'} ago`;
  }
  if (diffSec < 604800) {
    const days = Math.floor(diffSec / 86400);
    return `${days} ${days === 1 ? 'day' : 'days'} ago`;
  }
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function CategoryBadge({ category, isStatic, isDemo, isVideo }) {
  const cat = (category || 'WEATHER NEWS').toUpperCase();

  if (isDemo || isStatic) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#111111] text-[#D9A441] text-[10px] font-extrabold uppercase tracking-wider border border-[#D9A441]/40 shadow-sm">
        <Sparkles className="w-3 h-3 text-[#D9A441]" />
        DEMO STORY
      </span>
    );
  }

  if (isVideo || cat === 'VIDEO' || cat === 'VIDEOS') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-red-950/90 text-red-200 text-[10px] font-extrabold uppercase tracking-wider border border-red-500/30">
        <Play className="w-3 h-3 fill-current text-red-400" />
        VIDEO
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#F7EED7] dark:bg-[#2A2518] text-[#A97820] dark:text-[#D9A441] text-[10px] font-extrabold uppercase tracking-wider border border-[#D9A441]/20">
      <ShieldAlert className="w-3 h-3 text-[#D9A441]" />
      {cat}
    </span>
  );
}

function NewsCard({ article, onClick }) {
  const [imgFailed, setImgFailed] = useState(false);
  const imageUrl = article.image_url;
  const hasImage = Boolean(imageUrl) && !imgFailed;

  const sourceName = article.source || article.source_name || 'Weather Intel News';
  const relTime = formatRelativeTime(article.published_at || article.reported_at || article.created_at);

  return (
    <motion.div
      whileHover={{ y: -4 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      onClick={() => onClick(article)}
      className="bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col justify-between h-full group"
    >
      <div>
        {/* Card Media Header */}
        <div className="relative w-full aspect-[16/9] overflow-hidden bg-[#F7F7F5] dark:bg-[#0F1117]">
          {hasImage ? (
            <img
              src={imageUrl}
              alt={article.title || 'Weather story image'}
              loading="lazy"
              onError={() => setImgFailed(true)}
              className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-300"
            />
          ) : (
            <WeatherImageFallback category={article.category} />
          )}
          
          <div className="absolute top-3 left-3 flex items-center gap-2 z-10">
            <CategoryBadge
              category={article.category}
              isStatic={article.is_static}
              isDemo={article.is_demo}
              isVideo={article.is_video}
            />
          </div>

          {article.is_video && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/10 transition-colors">
              <div className="w-10 h-10 rounded-full bg-[#111111]/80 backdrop-blur-md text-[#D9A441] flex items-center justify-center border border-white/20 shadow-lg group-hover:scale-110 transition-transform">
                <Play className="w-4 h-4 fill-current ml-0.5" />
              </div>
            </div>
          )}
        </div>

        {/* Card Content */}
        <div className="p-5 space-y-2">
          <h3 className="text-base font-bold text-[#111111] dark:text-white leading-snug line-clamp-2 group-hover:text-[#A97820] dark:group-hover:text-[#D9A441] transition-colors">
            {article.title}
          </h3>
          {article.description && (
            <p className="text-xs text-[#66635C] dark:text-[#9CA3AF] line-clamp-2 leading-relaxed font-normal">
              {article.description}
            </p>
          )}
        </div>
      </div>

      {/* Card Footer Metadata */}
      <div className="px-5 pb-4 pt-3 border-t border-[#E5E2DA]/60 dark:border-[#262938] flex items-center justify-between text-xs text-[#66635C] dark:text-[#9CA3AF]">
        <span className="font-semibold text-[#111111] dark:text-stone-300 truncate max-w-[150px]">
          {sourceName}
        </span>
        <div className="flex items-center gap-1.5 text-[11px] text-[#96938B]">
          <Clock className="w-3 h-3 text-[#D9A441]" />
          <span>{relTime}</span>
        </div>
      </div>
    </motion.div>
  );
}

export default function WeatherNews({ fallbackEvents = [] }) {
  const navigate = useNavigate();
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchHomepageNews() {
      setLoading(true);
      try {
        const res = await api.get('/api/stories?per_page=4');
        const items = res.data?.data || [];
        setStories(items);
      } catch (err) {
        console.error('Failed to fetch stories from /api/stories, using fallback:', err);
        if (Array.isArray(fallbackEvents) && fallbackEvents.length > 0) {
          const mapped = fallbackEvents.slice(0, 4).map((e, idx) => ({
            id: e.id || `fb-${idx}`,
            title: e.title,
            description: e.description,
            source: e.source_name || e.source || 'Weather Intel News',
            source_url: e.source_url,
            image_url: e.image_url || (Array.isArray(e.photos) ? e.photos[0] : null),
            category: e.event_type || 'WEATHER NEWS',
            published_at: e.reported_at || e.created_at,
            is_static: Boolean(e.is_static),
            is_demo: Boolean(e.is_demo),
          }));
          setStories(mapped);
        }
      } finally {
        setLoading(false);
      }
    }
    fetchHomepageNews();
  }, [fallbackEvents]);

  const handleCardClick = (article) => {
    if (article.id) {
      navigate(`/stories/${article.id}`);
    } else if (article.source_url) {
      window.open(article.source_url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <section className="font-sans" aria-label="Latest Weather News & Stories">
      {/* Section Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[#E5E2DA] dark:border-[#262938] mb-6 sm:mb-8">
        <div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[#111111] dark:text-white tracking-tight">
            Weather News & Stories
          </h2>
          <p className="text-xs sm:text-sm text-[#66635C] dark:text-[#9CA3AF] mt-1 font-normal">
            Latest verified meteorological bulletins, media reports, and 100 weather stories across India
          </p>
        </div>
        <button
          onClick={() => navigate('/stories')}
          className="inline-flex items-center gap-1.5 text-sm font-bold text-[#111111] dark:text-white hover:text-[#A97820] dark:hover:text-[#D9A441] transition-colors group cursor-pointer"
        >
          <span>See more</span>
          <ArrowRight className="w-4 h-4 text-[#D9A441] group-hover:translate-x-1 transition-transform" />
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 sm:gap-6 animate-pulse">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-72 bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-2xl p-4" />
          ))}
        </div>
      ) : stories.length === 0 ? (
        <div className="py-12 text-center text-xs text-[#66635C] dark:text-[#9CA3AF] bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-2xl">
          No recent weather stories available.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 sm:gap-6 items-stretch">
          {stories.map((article) => (
            <NewsCard key={article.id || article.title} article={article} onClick={handleCardClick} />
          ))}
        </div>
      )}
    </section>
  );
}
