import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Play, MapPin, Clock, ChevronRight, Video, ArrowRight, ShieldCheck, Sparkles } from 'lucide-react';
import { api } from '../services/api.js';

function formatStoryDate(dateInput) {
  if (!dateInput) return 'Recently';
  const date = new Date(dateInput);
  if (isNaN(date.getTime())) return 'Recently';
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function getYouTubeEmbedUrl(url) {
  if (!url) return null;
  const match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
  if (match && match[1]) {
    return `https://www.youtube-nocookie.com/embed/${match[1]}?autoplay=1`;
  }
  return null;
}

// Filter out lifestyle, cooking, village vlogs, entertainment, and non-weather content from featured selection
function isUnrelatedContent(story) {
  if (!story) return true;
  const text = `${story.title || ''} ${story.description || ''}`.toLowerCase();
  const bannedKeywords = [
    'cooking', 'kitchen', 'recipe', 'food', 'village life', 'lifestyle',
    'entertainment', 'dance', 'gaming', 'movie', 'vlog', 'vlogger', 'craft',
    'fashion', 'mars', 'moon', 'astronomy', 'animal', 'pet', 'cat', 'dog', 'bakery'
  ];
  return bannedKeywords.some(keyword => text.includes(keyword));
}

// Compute deterministic score to pick the highest relevance weather story for Featured position
function getFeaturedPriorityScore(story) {
  if (!story) return -9999;
  if (isUnrelatedContent(story)) return -5000;
  if (story.is_demo) return -1000;

  let score = 0;
  const sev = (story.severity || '').toLowerCase();
  const source = (story.source || '').toLowerCase();
  const cat = (story.category || '').toLowerCase();
  const ver = (story.verification_status || '').toLowerCase();
  const title = (story.title || '').toLowerCase();
  const desc = (story.description || '').toLowerCase();

  // 1. Severe weather priority
  if (sev === 'critical' || sev === 'high') score += 50;

  // 2. Verified AI / JEV intelligence
  if (ver === 'verified' || ver === 'ai_verified' || story.confidence_score >= 0.85) score += 40;

  // 3. Official IMD bulletin
  if (source.includes('imd') || cat.includes('imd')) score += 35;

  // 4. Core weather event types
  const weatherTerms = ['rain', 'flood', 'monsoon', 'storm', 'cyclone', 'heatwave', 'thunderstorm', 'fog', 'cloudburst', 'weather'];
  if (weatherTerms.some(term => title.includes(term) || desc.includes(term))) score += 30;

  // 5. Valid high-res image
  if (story.image_url && String(story.image_url).startsWith('http')) score += 20;

  // 6. Valid weather video
  if (story.is_video) score += 15;

  // Recency factor
  if (story.published_at || story.reported_at) {
    const time = new Date(story.published_at || story.reported_at).getTime();
    if (!isNaN(time)) score += Math.min(20, (time / 1000) / (86400 * 30));
  }

  return score;
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

function ImageContainer({ imageUrl, title, aspectRatio = 'aspect-[16/9]' }) {
  const [failed, setFailed] = useState(false);

  return (
    <div className={`relative w-full ${aspectRatio} overflow-hidden bg-stone-200 dark:bg-stone-900`}>
      {imageUrl && !failed ? (
        <img
          src={imageUrl}
          alt={title || 'Weather Story'}
          loading="lazy"
          onError={() => setFailed(true)}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
      ) : (
        <div className="w-full h-full bg-stone-200 dark:bg-stone-800 flex items-center justify-center">
          <span className="text-xs font-bold text-stone-400 uppercase tracking-widest">WEATHER INTEL</span>
        </div>
      )}
    </div>
  );
}

function MainStoryCard({ story, onClick }) {
  const locationText = typeof story.location === 'object' ? story.location?.display || story.location?.city || 'India' : story.location || 'India';

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
          <ImageContainer imageUrl={story.image_url} title={story.title} aspectRatio="aspect-[16/9]" />
          <div className="absolute top-3 left-3 z-10">
            <CategoryBadge category={story.category} isVideo={story.is_video} />
          </div>
          {story.is_video && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/35 group-hover:bg-black/20 transition-colors">
              <div className="w-12 h-12 rounded-full bg-red-600 text-white flex items-center justify-center border-2 border-white/80 shadow-xl group-hover:scale-110 transition-transform">
                <Play className="w-5 h-5 fill-current ml-0.5 text-white" />
              </div>
            </div>
          )}
        </div>

        <div className="p-5 space-y-2.5">
          <div className="flex items-center gap-2 text-[11px] font-bold text-[#A97820] dark:text-[#D9A441] uppercase tracking-wider">
            <span>{story.category || (story.is_video ? 'VIDEO' : 'RAINFALL')}</span>
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
        <span className="font-bold text-[#111111] dark:text-stone-300">Source: {story.source || 'Weather Intel'}</span>
      </div>
    </motion.div>
  );
}

function CompactSideStory({ story, onClick }) {
  const locationText = typeof story.location === 'object' ? story.location?.display || story.location?.city || 'India' : story.location || 'India';

  return (
    <div
      onClick={() => onClick(story)}
      className="p-3.5 bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-xl hover:shadow-md transition-all cursor-pointer flex gap-4 items-center group"
    >
      <div className="w-28 h-20 shrink-0 rounded-lg overflow-hidden relative">
        <ImageContainer imageUrl={story.image_url} title={story.title} aspectRatio="h-full w-full" />
        {story.is_video && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/35">
            <Play className="w-5 h-5 text-white fill-current" />
          </div>
        )}
      </div>

      <div className="space-y-1.5 flex-1 min-w-0">
        <div className="flex items-center gap-2 text-[10px] font-bold text-[#A97820] dark:text-[#D9A441] uppercase tracking-wider truncate">
          <span>{story.category || (story.is_video ? 'VIDEO' : 'NEWS')}</span>
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

function FeaturedStorySection({ story, onClick }) {
  const [isPlaying, setIsPlaying] = useState(false);
  if (!story) return null;

  const locationText = typeof story.location === 'object' 
    ? story.location?.display || story.location?.city || 'India' 
    : story.location || 'India';

  const youtubeEmbedUrl = story.is_video ? getYouTubeEmbedUrl(story.source_url || story.video_url) : null;

  // Determine dynamic badge label based on story type
  let featureLabel = 'FEATURED WEATHER REPORT';
  const sourceLower = (story.source || '').toLowerCase();
  const catLower = (story.category || '').toLowerCase();
  const verLower = (story.verification_status || '').toLowerCase();

  if (sourceLower.includes('imd') || catLower.includes('imd')) {
    featureLabel = 'FEATURED IMD UPDATE';
  } else if (verLower === 'verified' || verLower === 'ai_verified' || story.confidence_score >= 0.85) {
    featureLabel = 'FEATURED INTELLIGENCE';
  } else if (story.is_video) {
    featureLabel = 'FEATURED VIDEO REPORT';
  }

  const isVerifiedIntel = verLower === 'verified' || verLower === 'ai_verified' || story.confidence_score >= 0.85;

  return (
    <section aria-label="Featured Weather Intelligence" className="mb-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#D9A441] animate-pulse" />
          <h2 className="text-xs font-black text-[#A97820] dark:text-[#D9A441] uppercase tracking-widest flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-[#D9A441]" />
            {featureLabel}
          </h2>
        </div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-3xl overflow-hidden shadow-md hover:shadow-xl transition-all duration-300 grid grid-cols-1 lg:grid-cols-12 group"
      >
        {/* Left: Video / Image (col-span-7) */}
        <div className="lg:col-span-7 relative min-h-[320px] lg:min-h-[440px] bg-stone-900 overflow-hidden">
          {story.is_video && isPlaying && youtubeEmbedUrl ? (
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
                if (story.is_video && youtubeEmbedUrl) {
                  setIsPlaying(true);
                } else {
                  onClick(story);
                }
              }}
              className="relative w-full h-full min-h-[320px] lg:min-h-[440px] cursor-pointer group/media"
            >
              <ImageContainer imageUrl={story.image_url} title={story.title} aspectRatio="w-full h-full min-h-[320px] lg:min-h-[440px]" />
              
              <div className="absolute top-4 left-4 z-10">
                <CategoryBadge category={story.category} isVideo={story.is_video} />
              </div>

              {story.is_video && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/40 group-hover/media:bg-black/30 transition-colors">
                  <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-red-600/90 text-white flex items-center justify-center border-4 border-white/90 shadow-2xl group-hover/media:scale-110 group-hover/media:bg-red-600 transition-all duration-300">
                    <Play className="w-7 h-7 sm:w-9 sm:h-9 fill-current ml-1 text-white" />
                  </div>
                  <span className="mt-3 px-3 py-1 rounded-full bg-black/75 backdrop-blur-md text-white text-xs font-bold tracking-wide border border-white/20 shadow-lg">
                    Click to Play Video Report
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right: Editorial Details (col-span-5) */}
        <div className="lg:col-span-5 p-6 sm:p-8 flex flex-col justify-between space-y-6">
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-xs text-[#A97820] dark:text-[#D9A441] font-extrabold uppercase tracking-wider">
              <span>{story.category || (story.is_video ? 'VIDEO' : 'WEATHER BRIEF')}</span>
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

            {/* Intel Analysis Badge for verified items */}
            {isVerifiedIntel && (
              <div className="p-3 rounded-xl bg-[#F7F7F5] dark:bg-[#0F1117] border border-[#E5E2DA] dark:border-[#262938] flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                <p className="text-[11px] font-semibold text-[#66635C] dark:text-stone-300 leading-snug">
                  <span className="font-bold text-[#111111] dark:text-white">Intel Analysis: </span>
                  Verified weather observation processed by Weather Intel multi-source streaming pipeline.
                </p>
              </div>
            )}

            {story.description && (
              <p className="text-xs sm:text-sm text-[#66635C] dark:text-[#9CA3AF] leading-relaxed line-clamp-4">
                {story.description}
              </p>
            )}
          </div>

          <div className="pt-4 border-t border-[#E5E2DA] dark:border-[#262938] flex items-center justify-between">
            <span className="text-xs font-bold text-[#111111] dark:text-stone-300">
              Source: {story.source || 'Weather Intel'}
            </span>

            <button
              onClick={() => onClick(story)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#111111] text-white text-xs font-bold hover:bg-[#A97820] transition-colors cursor-pointer"
            >
              {story.is_video ? (
                <>
                  <Play className="w-3.5 h-3.5 fill-current text-[#D9A441]" />
                  <span>Watch Report</span>
                </>
              ) : (
                <>
                  <span>Read Story</span>
                  <ArrowRight className="w-4 h-4 text-[#D9A441]" />
                </>
              )}
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
        const res = await api.get('/api/stories?per_page=80');
        const rawData = res.data?.data?.stories || res.data?.data || [];
        
        // Normalize story object to guarantee image_url preservation
        const normalized = rawData.map(s => ({
          ...s,
          image_url: s.image_url || s.imageUrl || s.image || (Array.isArray(s.photos) && s.photos[0]) || null,
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

  // Deterministically select Featured Story using priority score
  const candidateStories = [...stories].sort((a, b) => getFeaturedPriorityScore(b) - getFeaturedPriorityScore(a));
  const featuredStory = candidateStories.length > 0 ? candidateStories[0] : null;

  // Remaining stories pool
  const remainingStories = stories.filter(s => s.id !== featuredStory?.id);

  // Separate remaining real image and real video stories for editorial layout
  const realImageStories = remainingStories.filter(s => !s.is_video && !s.is_demo);
  const realVideoStories = remainingStories.filter(s => s.is_video && !s.is_demo);

  // Interleave remaining image & video stories
  const mixedStories = [];
  const maxLen = Math.max(realImageStories.length, realVideoStories.length);
  for (let i = 0; i < maxLen; i++) {
    if (i < realImageStories.length) mixedStories.push(realImageStories[i]);
    if (i < realVideoStories.length) mixedStories.push(realVideoStories[i]);
  }

  // Fallback if mixed empty
  if (mixedStories.length === 0) {
    mixedStories.push(...remainingStories);
  }

  const topStories = mixedStories.slice(0, 3);
  const latestReportage = mixedStories.slice(3, 11);
  const sideStories = mixedStories.slice(11, 16);
  const archiveStories = mixedStories.slice(16);

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
            {/* FEATURED WEATHER INTELLIGENCE STORY */}
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

            {/* MAIN EDITORIAL FEED */}
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

                {/* Right 4 Cols: Compact editorial list */}
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

            {/* COMPLETE EDITORIAL ARCHIVE & NEWS FEED */}
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
