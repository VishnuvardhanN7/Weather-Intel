import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Play, MapPin, Clock, ChevronRight, Video, ArrowRight, ShieldCheck, Sparkles, Newspaper } from 'lucide-react';
import { api } from '../services/api.js';

function formatStoryDate(dateInput) {
  if (!dateInput) return 'Recently';
  const date = new Date(dateInput);
  if (isNaN(date.getTime())) return 'Recently';
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function getYouTubeEmbedUrl(url) {
  if (!url) return null;
  const match = String(url).match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
  if (match && match[1]) {
    return `https://www.youtube-nocookie.com/embed/${match[1]}?autoplay=1`;
  }
  return null;
}

// Banned keywords to reject unrelated content (cooking, village vlogs, lifestyle, entertainment, etc.)
const BANNED_VIDEO_KEYWORDS = [
  'cooking', 'kitchen', 'recipe', 'food', 'village life', 'lifestyle',
  'entertainment', 'dance', 'gaming', 'movie', 'vlog', 'vlogger', 'craft',
  'fashion', 'mars', 'moon', 'astronomy', 'animal', 'pet', 'cat', 'dog', 'bakery',
  "mom's bagiya", 'gardening', 'home decor', 'travel vlog'
];

const WEATHER_RELEVANCE_KEYWORDS = [
  'rain', 'rainfall', 'monsoon', 'storm', 'cyclone', 'flood', 'flooding',
  'heatwave', 'thunderstorm', 'fog', 'cloudburst', 'weather', 'imd', 'mausam',
  'alert', 'forecast', 'downpour', 'heavy rain', 'wind', 'landslide', 'baarish'
];

function isUnrelatedVideoContent(story) {
  if (!story) return true;
  const text = `${story.title || ''} ${story.description || ''}`.toLowerCase();
  return BANNED_VIDEO_KEYWORDS.some(kw => text.includes(kw));
}

function isValidYouTubeWeatherVideo(story) {
  if (!story) return false;
  const url = String(story.source_url || story.video_url || '');
  const hasYouTubeUrl = url.includes('youtube.com') || url.includes('youtu.be');
  const isVideoSource = story.is_video || story.source === 'YouTube' || (story.category || '').toLowerCase() === 'videos';

  if (!hasYouTubeUrl && !isVideoSource) return false;
  if (isUnrelatedVideoContent(story)) return false;

  const text = `${story.title || ''} ${story.description || ''}`.toLowerCase();
  const hasWeatherTerm = WEATHER_RELEVANCE_KEYWORDS.some(kw => text.includes(kw));
  if (!hasWeatherTerm) return false;

  return true;
}

function scoreFeaturedVideo(story) {
  if (!isValidYouTubeWeatherVideo(story)) return -9999;

  let score = 1000;
  const text = `${story.title || ''} ${story.description || ''}`.toLowerCase();

  // Prefer verified/live over demo
  if (!story.is_demo) score += 500;

  // Weather keyword frequency bonus
  WEATHER_RELEVANCE_KEYWORDS.forEach(kw => {
    if (text.includes(kw)) score += 40;
  });

  // Severe weather / IMD alert bonus
  const sev = (story.severity || '').toLowerCase();
  if (sev === 'critical' || sev === 'high') score += 200;
  if (text.includes('heavy rain') || text.includes('flood') || text.includes('monsoon') || text.includes('alert')) score += 150;
  if (text.includes('imd') || text.includes('mausam')) score += 100;
  if (text.includes('india') || text.includes('bihar') || text.includes('delhi') || text.includes('mumbai') || text.includes('rajasthan')) score += 100;

  // Recency bonus
  const pub = story.published_at || story.reported_at;
  if (pub) {
    const time = new Date(pub).getTime();
    if (!isNaN(time)) {
      score += Math.min(200, (time / 1000) / 86400);
    }
  }

  return score;
}

// Robust helper to extract image URL from various API field formats
function getStoryImageUrl(story) {
  if (!story) return null;

  // 1. Direct image fields returned by /api/stories
  const directUrl = story.image_url || story.imageUrl || story.image || story.primary_image_url;
  if (directUrl && typeof directUrl === 'string' && directUrl.trim() !== '') {
    return directUrl.trim();
  }

  // 2. Media array
  if (Array.isArray(story.media) && story.media.length > 0) {
    for (const m of story.media) {
      if (m) {
        if (typeof m === 'string' && m.trim() !== '') return m.trim();
        if (typeof m === 'object') {
          const mUrl = m.url || m.image_url || m.media_url || m.thumbnail_url || m.thumbnail;
          if (mUrl && typeof mUrl === 'string' && mUrl.trim() !== '') return mUrl.trim();
        }
      }
    }
  }

  // 3. Photos array
  if (Array.isArray(story.photos) && story.photos.length > 0) {
    for (const p of story.photos) {
      if (p) {
        if (typeof p === 'string' && p.trim() !== '') return p.trim();
        if (typeof p === 'object') {
          const pUrl = p.url || p.image_url || p.src;
          if (pUrl && typeof pUrl === 'string' && pUrl.trim() !== '') return pUrl.trim();
        }
      }
    }
  }

  // 4. Thumbnail fields
  const thumbUrl = story.thumbnail_url || story.thumbnail;
  if (thumbUrl && typeof thumbUrl === 'string' && thumbUrl.trim() !== '') {
    return thumbUrl.trim();
  }

  // 5. YouTube thumbnail construction
  const videoUrl = story.source_url || story.video_url;
  if (story.is_video || (videoUrl && (videoUrl.includes('youtube') || videoUrl.includes('youtu.be')))) {
    const match = String(videoUrl || '').match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
    if (match && match[1]) {
      return `https://i.ytimg.com/vi/${match[1]}/hqdefault.jpg`;
    }
  }

  return null;
}

function CategoryBadge({ category, isVideo }) {
  const cat = (category || 'WEATHER REPORT').toUpperCase();

  if (isVideo || cat === 'VIDEOS' || cat === 'VIDEO') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-red-600 text-white text-[10px] font-black uppercase tracking-wider shadow-sm">
        <Play className="w-3 h-3 fill-current text-white" />
        VIDEO
      </span>
    );
  }

  return (
    <span className="inline-flex items-center px-2.5 py-1 rounded-sm bg-[#111111] text-[#D9A441] text-[10px] font-extrabold uppercase tracking-wider shadow-sm">
      {cat}
    </span>
  );
}

// Multi-candidate image component with fallback cascade
function ImageContainer({ story, imageUrl, title, aspectRatio = 'aspect-[16/9]' }) {
  const candidateUrls = useMemo(() => {
    const urls = [];
    const primary = imageUrl || getStoryImageUrl(story);
    if (primary) urls.push(primary);

    if (story) {
      // Collect direct fields
      [story.image_url, story.imageUrl, story.image, story.primary_image_url].forEach(u => {
        if (u && typeof u === 'string' && u.trim() !== '' && !urls.includes(u.trim())) {
          urls.push(u.trim());
        }
      });
      // Collect from media array
      if (Array.isArray(story.media)) {
        story.media.forEach(m => {
          if (typeof m === 'string' && m.trim() !== '' && !urls.includes(m.trim())) {
            urls.push(m.trim());
          } else if (m && typeof m === 'object') {
            [m.url, m.thumbnail_url, m.media_url, m.image_url].forEach(u => {
              if (u && typeof u === 'string' && u.trim() !== '' && !urls.includes(u.trim())) {
                urls.push(u.trim());
              }
            });
          }
        });
      }
      // Collect from photos array
      if (Array.isArray(story.photos)) {
        story.photos.forEach(p => {
          if (typeof p === 'string' && p.trim() !== '' && !urls.includes(p.trim())) {
            urls.push(p.trim());
          } else if (p && typeof p === 'object') {
            [p.url, p.image_url, p.src].forEach(u => {
              if (u && typeof u === 'string' && u.trim() !== '' && !urls.includes(u.trim())) {
                urls.push(u.trim());
              }
            });
          }
        });
      }
      // Collect thumbnail fields
      [story.thumbnail_url, story.thumbnail].forEach(u => {
        if (u && typeof u === 'string' && u.trim() !== '' && !urls.includes(u.trim())) {
          urls.push(u.trim());
        }
      });
      // YouTube thumbnail
      const videoUrl = story.source_url || story.video_url;
      if (story.is_video || (videoUrl && (videoUrl.includes('youtube') || videoUrl.includes('youtu.be')))) {
        const match = String(videoUrl || '').match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
        if (match && match[1]) {
          const ytThumb = `https://i.ytimg.com/vi/${match[1]}/hqdefault.jpg`;
          if (!urls.includes(ytThumb)) urls.push(ytThumb);
        }
      }
    }
    return urls;
  }, [story, imageUrl]);

  const [currentIndex, setCurrentIndex] = useState(0);

  const currentSrc = candidateUrls[currentIndex] || null;

  const handleImageError = () => {
    if (currentIndex < candidateUrls.length - 1) {
      setCurrentIndex(prev => prev + 1);
    } else {
      setCurrentIndex(candidateUrls.length); // Exceeds candidates -> show fallback
    }
  };

  return (
    <div className={`relative w-full ${aspectRatio} overflow-hidden bg-stone-200 dark:bg-stone-900`}>
      {currentSrc ? (
        <img
          src={currentSrc}
          alt={title || story?.title || 'Weather Intel Story'}
          loading="lazy"
          onError={handleImageError}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
      ) : (
        <div className="w-full h-full bg-stone-200 dark:bg-stone-800 flex flex-col items-center justify-center p-4 text-center">
          <div className="w-8 h-8 rounded-full border-2 border-stone-300 dark:border-stone-700 bg-stone-300 dark:bg-stone-700 flex items-center justify-center mb-1.5 opacity-50">
            <Newspaper className="w-4 h-4 text-stone-600 dark:text-stone-300" />
          </div>
          <span className="text-[10px] font-extrabold text-stone-500 dark:text-stone-400 uppercase tracking-widest">
            WEATHER INTEL
          </span>
        </div>
      )}
    </div>
  );
}

function MainStoryCard({ story, onClick }) {
  if (!story) return null;
  const locationText = typeof story.location === 'object' ? story.location?.display || story.location?.city || 'India' : story.location || 'India';
  const isVideo = Boolean(story.is_video);
  const storyImgUrl = getStoryImageUrl(story);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -3 }}
      transition={{ duration: 0.2 }}
      onClick={() => onClick(story)}
      className="bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-2xl overflow-hidden shadow-sm hover:shadow-lg transition-all duration-200 cursor-pointer flex flex-col justify-between h-full group"
    >
      <div>
        <div className="relative">
          <ImageContainer story={story} imageUrl={storyImgUrl} title={story.title} aspectRatio="aspect-[16/9]" />
          <div className="absolute top-3 left-3 z-10">
            <CategoryBadge category={story.category} isVideo={isVideo} />
          </div>
          {isVideo && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/35 group-hover:bg-black/20 transition-colors">
              <div className="w-12 h-12 rounded-full bg-red-600 text-white flex items-center justify-center border-2 border-white/80 shadow-xl group-hover:scale-110 transition-transform">
                <Play className="w-5 h-5 fill-current ml-0.5 text-white" />
              </div>
            </div>
          )}
        </div>

        <div className="p-5 space-y-2.5">
          <div className="flex items-center gap-2 text-[11px] font-bold text-[#A97820] dark:text-[#D9A441] uppercase tracking-wider">
            <span>{story.category || (isVideo ? 'VIDEO' : 'RAINFALL')}</span>
            <span>•</span>
            <span className="text-[#66635C] dark:text-[#9CA3AF] truncate max-w-[160px]">{locationText}</span>
          </div>

          <h3 className="text-base sm:text-lg font-extrabold text-[#111111] dark:text-white leading-snug line-clamp-2 group-hover:text-[#A97820] dark:group-hover:text-[#D9A441] transition-colors">
            {story.title}
          </h3>

          {story.description && (
            <p className="text-xs text-[#66635C] dark:text-[#9CA3AF] line-clamp-2 leading-relaxed font-normal">
              {story.description}
            </p>
          )}
        </div>
      </div>

      <div className="px-5 pb-4 pt-3 border-t border-[#E5E2DA]/60 dark:border-[#262938] flex items-center justify-between text-xs text-[#66635C] dark:text-[#9CA3AF]">
        <span className="font-semibold">{formatStoryDate(story.published_at || story.reported_at)}</span>
        <span className="font-bold text-[#111111] dark:text-stone-300 flex items-center gap-1 group-hover:text-[#A97820] dark:group-hover:text-[#D9A441] transition-colors">
          {isVideo ? (
            <>
              <span>Watch Report</span>
              <Play className="w-3 h-3 fill-current text-red-600" />
            </>
          ) : (
            <>
              <span>Read Story</span>
              <ArrowRight className="w-3.5 h-3.5 text-[#D9A441]" />
            </>
          )}
        </span>
      </div>
    </motion.div>
  );
}

function CompactSideStory({ story, onClick }) {
  if (!story) return null;
  const locationText = typeof story.location === 'object' ? story.location?.display || story.location?.city || 'India' : story.location || 'India';
  const isVideo = Boolean(story.is_video);
  const storyImgUrl = getStoryImageUrl(story);

  return (
    <div
      onClick={() => onClick(story)}
      className="p-3.5 bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-xl hover:shadow-md transition-all cursor-pointer flex gap-4 items-center group"
    >
      <div className="w-28 h-20 shrink-0 rounded-lg overflow-hidden relative">
        <ImageContainer story={story} imageUrl={storyImgUrl} title={story.title} aspectRatio="h-full w-full" />
        {isVideo && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/35">
            <Play className="w-5 h-5 text-white fill-current" />
          </div>
        )}
      </div>

      <div className="space-y-1.5 flex-1 min-w-0">
        <div className="flex items-center gap-2 text-[10px] font-bold text-[#A97820] dark:text-[#D9A441] uppercase tracking-wider truncate">
          <span>{story.category || (isVideo ? 'VIDEO' : 'NEWS')}</span>
          <span>•</span>
          <span className="text-[#66635C] dark:text-[#9CA3AF] truncate">{locationText}</span>
        </div>

        <h4 className="text-xs font-bold text-[#111111] dark:text-white leading-snug line-clamp-2 group-hover:text-[#A97820] dark:group-hover:text-[#D9A441] transition-colors">
          {story.title}
        </h4>

        <div className="text-[10px] text-[#66635C] dark:text-[#9CA3AF] flex items-center justify-between font-medium">
          <span>{formatStoryDate(story.published_at || story.reported_at)}</span>
          <span className="font-bold">{story.source || 'IMD'}</span>
        </div>
      </div>
    </div>
  );
}

// FEATURED STORY = VIDEO ONLY section component
function FeaturedStorySection({ story, onClick }) {
  const [isPlaying, setIsPlaying] = useState(false);
  if (!story) return null;

  const locationText = typeof story.location === 'object' 
    ? story.location?.display || story.location?.city || 'India' 
    : story.location || 'India';

  const youtubeEmbedUrl = getYouTubeEmbedUrl(story.source_url || story.video_url);

  return (
    <section aria-label="Featured Weather Video Report" className="mb-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-pulse" />
          <h2 className="text-xs font-black text-red-600 dark:text-red-400 uppercase tracking-widest flex items-center gap-1.5">
            <Video className="w-3.5 h-3.5 text-red-600 dark:text-red-400" />
            FEATURED VIDEO REPORT
          </h2>
        </div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-3xl overflow-hidden shadow-md hover:shadow-xl transition-all duration-300 grid grid-cols-1 lg:grid-cols-12 group"
      >
        {/* Left: Video Player / Thumbnail (col-span-7) */}
        <div className="lg:col-span-7 relative min-h-[320px] lg:min-h-[440px] bg-stone-900 overflow-hidden">
          {isPlaying && youtubeEmbedUrl ? (
            <iframe
              src={youtubeEmbedUrl}
              title={story.title}
              className="w-full h-full min-h-[340px] lg:min-h-[440px] border-0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          ) : (
            <div
              onClick={() => {
                if (youtubeEmbedUrl) {
                  setIsPlaying(true);
                } else {
                  onClick(story);
                }
              }}
              className="relative w-full h-full min-h-[320px] lg:min-h-[440px] cursor-pointer group/media"
            >
              <ImageContainer story={story} imageUrl={getStoryImageUrl(story)} title={story.title} aspectRatio="w-full h-full min-h-[320px] lg:min-h-[440px]" />
              
              <div className="absolute top-4 left-4 z-10">
                <CategoryBadge category={story.category} isVideo={true} />
              </div>

              <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/40 group-hover/media:bg-black/30 transition-colors">
                <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-red-600/90 text-white flex items-center justify-center border-4 border-white/90 shadow-2xl group-hover/media:scale-110 group-hover/media:bg-red-600 transition-all duration-300">
                  <Play className="w-7 h-7 sm:w-9 sm:h-9 fill-current ml-1 text-white" />
                </div>
                <span className="mt-3 px-3 py-1 rounded-full bg-black/75 backdrop-blur-md text-white text-xs font-bold tracking-wide border border-white/20 shadow-lg">
                  Click to Play Video Report
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Right: Editorial Details (col-span-5) */}
        <div className="lg:col-span-5 p-6 sm:p-8 flex flex-col justify-between space-y-6">
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-xs text-[#A97820] dark:text-[#D9A441] font-extrabold uppercase tracking-wider">
              <span className="text-red-600 dark:text-red-400 font-black">YOUTUBE VIDEO</span>
              <span>•</span>
              <span className="text-[#66635C] dark:text-[#9CA3AF] truncate max-w-[140px]">
                {locationText}
              </span>
              <span>•</span>
              <span className="text-[#66635C] dark:text-[#9CA3AF]">
                {formatStoryDate(story.published_at || story.reported_at)}
              </span>
            </div>

            <h2
              onClick={() => onClick(story)}
              className="text-2xl sm:text-3xl font-black text-[#111111] dark:text-white leading-tight hover:text-[#A97820] dark:hover:text-[#D9A441] transition-colors cursor-pointer"
            >
              {story.title}
            </h2>

            {story.description && (
              <p className="text-xs sm:text-sm text-[#66635C] dark:text-[#9CA3AF] leading-relaxed line-clamp-4">
                {story.description}
              </p>
            )}
          </div>

          <div className="pt-4 border-t border-[#E5E2DA] dark:border-[#262938] flex items-center justify-between">
            <span className="text-xs font-bold text-[#111111] dark:text-stone-300">
              Source: {story.source || 'YouTube'}
            </span>

            <button
              onClick={() => {
                if (youtubeEmbedUrl) {
                  setIsPlaying(true);
                } else {
                  onClick(story);
                }
              }}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-bold transition-colors cursor-pointer shadow-md"
            >
              <Play className="w-3.5 h-3.5 fill-current text-white" />
              <span>Watch Report</span>
            </button>
          </div>
        </div>
      </motion.div>
    </section>
  );
}

export default function Stories() {
  const navigate = useNavigate();
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStories() {
      setLoading(true);
      try {
        const res = await api.get('/api/stories?per_page=100');
        const rawData = res.data?.data?.stories || res.data?.data || [];
        
        // Normalize stories ensuring image_url is populated from all candidate sources
        const normalized = rawData.map(s => ({
          ...s,
          image_url: getStoryImageUrl(s),
        }));

        setStories(normalized);
      } catch (err) {
        console.error('Failed to load stories:', err);
      } finally {
        setLoading(false);
      }
    }
    loadStories();
  }, []);

  const handleStoryClick = (story) => {
    if (story.id) {
      navigate(`/stories/${story.id}`);
    } else if (story.source_url) {
      window.open(story.source_url, '_blank', 'noopener,noreferrer');
    }
  };

  // 1. FEATURED STORY = VIDEO ONLY SELECTION
  // Filter for valid weather YouTube videos, excluding cooking/village/lifestyle content
  const videoCandidates = useMemo(() => {
    return stories
      .filter(isValidYouTubeWeatherVideo)
      .sort((a, b) => scoreFeaturedVideo(b) - scoreFeaturedVideo(a));
  }, [stories]);

  // Featured story is strictly a video report
  const featuredStory = videoCandidates.length > 0 ? videoCandidates[0] : null;

  // 2. REMAINING STORIES POOL
  const remainingStories = useMemo(() => {
    return stories.filter(s => s.id !== featuredStory?.id);
  }, [stories, featuredStory]);

  // 3. SEPARATE REAL IMAGE & REAL VIDEO STORIES FOR CARDS BELOW FEATURED
  // Real image stories (stories that are not videos and have legitimate image URLs)
  const realImageStories = useMemo(() => {
    return remainingStories.filter(s => !s.is_video && getStoryImageUrl(s) !== null);
  }, [remainingStories]);

  // Real video stories
  const realVideoStories = useMemo(() => {
    return remainingStories.filter(s => s.is_video || isValidYouTubeWeatherVideo(s));
  }, [remainingStories]);

  // Fallback stories (any remaining stories)
  const otherStories = useMemo(() => {
    return remainingStories.filter(s => !realImageStories.includes(s) && !realVideoStories.includes(s));
  }, [remainingStories, realImageStories, realVideoStories]);

  // 4. INTERLEAVE IMAGE AND VIDEO STORIES FOR EDITORIAL FEED
  const mixedStories = useMemo(() => {
    const list = [];
    const maxLen = Math.max(realImageStories.length, realVideoStories.length);
    for (let i = 0; i < maxLen; i++) {
      if (i < realImageStories.length) list.push(realImageStories[i]);
      if (i < realVideoStories.length) list.push(realVideoStories[i]);
    }
    // Append any remaining text observations or other stories at the end
    list.push(...otherStories);
    return list;
  }, [realImageStories, realVideoStories, otherStories]);

  const topStories = mixedStories.slice(0, 3);
  const latestReportage = mixedStories.slice(3, 11);
  const sideStories = mixedStories.slice(11, 17);
  const archiveStories = mixedStories.slice(17);

  return (
    <div className="min-h-screen bg-[#F7F7F5] dark:bg-[#0F1117] text-[#111111] dark:text-white font-sans pb-24">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 sm:pt-8 space-y-10">

        {loading ? (
          <div className="py-24 text-center space-y-3">
            <div className="w-10 h-10 mx-auto border-3 border-[#D9A441] border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-[#66635C] dark:text-[#9CA3AF] font-medium">Loading Weather Intel stories & bulletins...</p>
          </div>
        ) : (
          <>
            {/* FEATURED STORY: VIDEO ONLY */}
            {featuredStory && (
              <FeaturedStorySection story={featuredStory} onClick={handleStoryClick} />
            )}

            {/* TOP WEATHER STORIES & VIDEO REPORTS */}
            {topStories.length > 0 && (
              <section aria-label="Top Weather Stories">
                <div className="mb-6 border-b border-[#E5E2DA] dark:border-[#262938] pb-2">
                  <h2 className="text-sm font-black text-[#111111] dark:text-white uppercase tracking-wider">
                    TOP WEATHER STORIES & VIDEO REPORTS
                  </h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
                  {topStories.map((story) => (
                    <MainStoryCard key={story.id || story.title} story={story} onClick={handleStoryClick} />
                  ))}
                </div>
              </section>
            )}

            {/* LATEST WEATHER STORIES */}
            <section aria-label="Latest Weather Stories">
              <div className="mb-6 border-b border-[#E5E2DA] dark:border-[#262938] pb-2 flex items-center justify-between">
                <h2 className="text-sm font-black text-[#111111] dark:text-white uppercase tracking-wider">
                  LATEST WEATHER REPORTAGE
                </h2>
                <span className="text-xs text-[#66635C] dark:text-[#9CA3AF] font-medium hidden sm:inline-block">
                  Verified Meteorological Bulletins, Broadcasts & Observations
                </span>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                
                {/* Left 8 Cols: Interleaved 2-column image & video story grid */}
                <div className="lg:col-span-8 grid grid-cols-1 sm:grid-cols-2 gap-6 sm:gap-8">
                  {latestReportage.map((story) => (
                    <MainStoryCard key={story.id || story.title} story={story} onClick={handleStoryClick} />
                  ))}
                </div>

                {/* Right 4 Cols: Compact side stories */}
                {sideStories.length > 0 && (
                  <div className="lg:col-span-4 space-y-4">
                    <div className="p-4 bg-stone-100 dark:bg-[#161822] rounded-2xl border border-[#E5E2DA] dark:border-[#262938]">
                      <h3 className="text-xs font-black uppercase text-[#A97820] dark:text-[#D9A441] tracking-wider mb-3">
                        REGIONAL DEVELOPMENTS & BULLETINS
                      </h3>
                      <div className="space-y-3">
                        {sideStories.map((story) => (
                          <CompactSideStory key={story.id || story.title} story={story} onClick={handleStoryClick} />
                        ))}
                      </div>
                    </div>
                  </div>
                )}

              </div>
            </section>

            {/* MORE WEATHER STORIES & ARCHIVE */}
            {archiveStories.length > 0 && (
              <section aria-label="More Weather Stories" className="pt-4 border-t border-[#E5E2DA] dark:border-[#262938]">
                <div className="mb-6 border-b border-[#E5E2DA] dark:border-[#262938] pb-2">
                  <h2 className="text-sm font-black text-[#111111] dark:text-white uppercase tracking-wider">
                    WEATHER NEWS FEED & BROADCAST ARCHIVE
                  </h2>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
                  {archiveStories.map((story) => (
                    <MainStoryCard key={story.id || story.title} story={story} onClick={handleStoryClick} />
                  ))}
                </div>
              </section>
            )}
          </>
        )}

      </div>
    </div>
  );
}
