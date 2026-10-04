import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft, ExternalLink, MapPin, Clock, ShieldAlert, Sparkles, Play,
  CheckCircle2, AlertTriangle, Info, Camera, Tag
} from 'lucide-react';
import { api } from '../services/api.js';
import WeatherImageFallback from '../components/WeatherImageFallback.jsx';

function formatRelativeTime(dateInput) {
  if (!dateInput) return 'Recently';
  const date = new Date(dateInput);
  if (isNaN(date.getTime())) return 'Recently';

  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function CategoryBadge({ category, isStatic, isDemo, isVideo }) {
  const cat = (category || 'WEATHER NEWS').toUpperCase();

  if (isDemo || isStatic) {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[#111111] text-[#D9A441] text-xs font-extrabold uppercase tracking-wider border border-[#D9A441]/40 shadow-sm">
        <Sparkles className="w-3.5 h-3.5 text-[#D9A441]" />
        DEMO STORY
      </span>
    );
  }

  if (isVideo || cat === 'VIDEOS' || cat === 'VIDEO') {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-red-950/90 text-red-200 text-xs font-extrabold uppercase tracking-wider border border-red-500/30">
        <Play className="w-3.5 h-3.5 fill-current text-red-400" />
        VIDEO STORY
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[#F7EED7] dark:bg-[#2A2518] text-[#A97820] dark:text-[#D9A441] text-xs font-extrabold uppercase tracking-wider border border-[#D9A441]/30">
      <ShieldAlert className="w-3.5 h-3.5 text-[#D9A441]" />
      {cat}
    </span>
  );
}

export default function StoryDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [story, setStory] = useState(null);
  const [relatedStories, setRelatedStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [imgFailed, setImgFailed] = useState(false);

  useEffect(() => {
    async function fetchStoryDetail() {
      setLoading(true);
      setError(null);
      setImgFailed(false);
      try {
        const res = await api.get(`/api/stories/${id}`);
        if (res.data && res.data.story) {
          setStory(res.data.story);
          setRelatedStories(res.data.related_stories || []);
        } else {
          setError('Story not found');
        }
      } catch (err) {
        console.error('Failed to load story detail:', err);
        setError('Weather story not found or unavailable');
      } finally {
        setLoading(false);
      }
    }
    fetchStoryDetail();
    window.scrollTo(0, 0);
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F7F7F5] dark:bg-[#0F1117] flex items-center justify-center p-6">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-4 border-[#D9A441] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-[#66635C] dark:text-[#9CA3AF] font-semibold">Loading story details...</p>
        </div>
      </div>
    );
  }

  if (error || !story) {
    return (
      <div className="min-h-screen bg-[#F7F7F5] dark:bg-[#0F1117] flex items-center justify-center p-6">
        <div className="bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-2xl p-8 max-w-md text-center space-y-4 shadow-md">
          <AlertTriangle className="w-10 h-10 text-[#D9A441] mx-auto" />
          <h2 className="text-lg font-bold text-[#111111] dark:text-white">Story Not Found</h2>
          <p className="text-xs text-[#66635C] dark:text-[#9CA3AF]">{error || 'The requested weather story could not be loaded.'}</p>
          <button
            onClick={() => navigate('/stories')}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#111111] text-white text-xs font-bold hover:bg-black transition-colors"
          >
            <ArrowLeft className="w-4 h-4 text-[#D9A441]" />
            Back to Stories
          </button>
        </div>
      </div>
    );
  }

  const locationText = typeof story.location === 'object' ? story.location?.display || story.location?.city || 'India' : story.location || 'India';
  const hasImage = Boolean(story.image_url) && !imgFailed;

  return (
    <div className="min-h-screen bg-[#F7F7F5] dark:bg-[#0F1117] text-[#111111] dark:text-white font-sans pb-24">
      
      {/* Top Navigation Bar */}
      <div className="bg-white dark:bg-[#161822] border-b border-[#E5E2DA] dark:border-[#262938] py-4 px-4 sm:px-6 lg:px-8 sticky top-[72px] z-30 shadow-sm">
        <div className="max-w-[1200px] mx-auto flex items-center justify-between">
          <button
            onClick={() => navigate('/stories')}
            className="inline-flex items-center gap-2 text-xs sm:text-sm font-bold text-[#111111] dark:text-white hover:text-[#A97820] dark:hover:text-[#D9A441] transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4 text-[#D9A441]" />
            <span>Back to Weather Stories</span>
          </button>
          
          <div className="flex items-center gap-3">
            {(story.is_demo || story.is_static) && (
              <span className="text-[11px] font-extrabold text-[#D9A441] bg-[#111111] px-2.5 py-1 rounded-md border border-[#D9A441]/40 flex items-center gap-1.5">
                <Sparkles className="w-3 h-3 text-[#D9A441]" />
                DEMO STORY
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Main Article Container */}
      <article className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 pt-8 sm:pt-10 space-y-8">
        
        {/* Notice Banner for Demo Content */}
        {(story.is_demo || story.is_static) && (
          <div className="bg-[#111111] text-[#F3F4F6] border border-[#D9A441]/40 rounded-2xl p-4 flex items-center justify-between gap-4 shadow-sm">
            <div className="flex items-center gap-3">
              <Info className="w-5 h-5 text-[#D9A441] shrink-0" />
              <p className="text-xs sm:text-sm font-medium leading-relaxed">
                <strong>Demo Editorial Content</strong> — This story is a educational demonstration record and not a current breaking weather incident.
              </p>
            </div>
            <span className="text-[10px] font-extrabold text-[#D9A441] tracking-wider uppercase border border-[#D9A441]/30 px-2 py-1 rounded shrink-0 hidden sm:inline-block">
              DEMO DATA
            </span>
          </div>
        )}

        {/* Story Header */}
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <CategoryBadge
              category={story.category}
              isStatic={story.is_static}
              isDemo={story.is_demo}
              isVideo={story.is_video}
            />
            
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[#F7F7F5] dark:bg-[#0F1117] text-[#66635C] dark:text-stone-300 text-xs font-semibold border border-[#E5E2DA] dark:border-[#262938]">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
              VERIFIED EDITORIAL
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-[#111111] dark:text-white leading-tight tracking-tight">
            {story.title}
          </h1>

          <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-[#E5E2DA] dark:border-[#262938] text-xs text-[#66635C] dark:text-[#9CA3AF]">
            <div className="flex flex-wrap items-center gap-4">
              <span className="font-bold text-[#111111] dark:text-white">{story.source || 'ATMOS News'}</span>
              <span>•</span>
              <span className="flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-[#D9A441]" />
                {locationText}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-[#D9A441]" />
                {formatRelativeTime(story.published_at || story.reported_at)}
              </span>
            </div>

            {Array.isArray(story.tags) && story.tags.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <Tag className="w-3 h-3 text-[#D9A441]" />
                {story.tags.slice(0, 3).map((t, idx) => (
                  <span key={idx} className="px-2 py-0.5 rounded bg-[#F7F7F5] dark:bg-[#0F1117] border border-[#E5E2DA] dark:border-[#262938] text-[10px] font-semibold text-[#66635C] dark:text-stone-300">
                    #{t}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Primary Story Image or Video Player */}
        <div className="relative w-full rounded-3xl overflow-hidden bg-[#F7F7F5] dark:bg-[#0F1117] border border-[#E5E2DA] dark:border-[#262938] shadow-md max-h-[550px]">
          {story.is_video && story.source_url && story.source_url.includes('youtube') ? (
            <div className="aspect-video w-full max-h-[550px]">
              <iframe
                src={`https://www.youtube-nocookie.com/embed/${story.source_url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/)?.[1] || ''}`}
                title={story.title}
                className="w-full h-full border-0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
          ) : hasImage ? (
            <img
              src={story.image_url}
              alt={story.title}
              onError={() => setImgFailed(true)}
              className="w-full h-full object-cover max-h-[550px]"
            />
          ) : (
            <div className="h-[350px]">
              <WeatherImageFallback category={story.category} />
            </div>
          )}

          {/* Image Attribution */}
          {!story.is_video && story.image_credit && (
            <div className="absolute bottom-3 right-3 bg-[#111111]/80 backdrop-blur-md text-white text-[11px] font-medium px-3 py-1.5 rounded-lg border border-white/10 flex items-center gap-1.5 z-10">
              <Camera className="w-3.5 h-3.5 text-[#D9A441]" />
              {story.image_credit_url ? (
                <a href={story.image_credit_url} target="_blank" rel="noopener noreferrer" className="hover:underline text-stone-200">
                  {story.image_credit}
                </a>
              ) : (
                <span>{story.image_credit}</span>
              )}
            </div>
          )}
        </div>

        {/* Story Body */}
        <div className="bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-3xl p-6 sm:p-10 space-y-6 shadow-sm">
          <div className="prose dark:prose-invert max-w-none text-sm sm:text-base text-[#111111] dark:text-stone-200 leading-relaxed whitespace-pre-line space-y-4">
            {story.description}
          </div>

          {/* Footer Action Links */}
          <div className="pt-6 border-t border-[#E5E2DA] dark:border-[#262938] flex flex-wrap items-center justify-between gap-4">
            {story.source_url ? (
              <a
                href={story.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#111111] text-white text-xs font-bold hover:bg-black transition-colors shadow-sm cursor-pointer"
              >
                <span>{story.is_video ? 'Watch video on YouTube →' : 'Read original source story →'}</span>
                <ExternalLink className="w-4 h-4 text-[#D9A441]" />
              </a>
            ) : (
              <div className="text-xs text-[#96938B] font-semibold flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 text-[#D9A441]" />
                <span>ATMOS Verified Educational & Preparedness Bulletin</span>
              </div>
            )}
          </div>
        </div>

        {/* Related Stories */}
        {relatedStories.length > 0 && (
          <section className="pt-10 border-t border-[#E5E2DA] dark:border-[#262938] space-y-6" aria-label="Related Stories">
            <h3 className="text-xl font-extrabold text-[#111111] dark:text-white tracking-tight">
              Related Weather Stories
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {relatedStories.map((rel) => (
                <motion.div
                  key={rel.id || rel.title}
                  whileHover={{ y: -4 }}
                  onClick={() => navigate(`/stories/${rel.id}`)}
                  className="bg-white dark:bg-[#161822] border border-[#E5E2DA] dark:border-[#262938] rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-all cursor-pointer p-4 space-y-3"
                >
                  {rel.image_url ? (
                    <div className="aspect-video rounded-xl overflow-hidden bg-[#F7F7F5] dark:bg-[#0F1117]">
                      <img src={rel.image_url} alt={rel.title} className="w-full h-full object-cover" />
                    </div>
                  ) : (
                    <div className="aspect-video rounded-xl overflow-hidden">
                      <WeatherImageFallback category={rel.category} />
                    </div>
                  )}
                  <h4 className="text-xs font-bold text-[#111111] dark:text-white line-clamp-2 leading-snug">
                    {rel.title}
                  </h4>
                  <div className="text-[10px] text-[#96938B] font-semibold flex items-center justify-between">
                    <span>{rel.source || 'ATMOS News'}</span>
                    {(rel.is_demo || rel.is_static) && (
                      <span className="text-[9px] font-extrabold text-[#D9A441]">DEMO</span>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </section>
        )}

      </article>
    </div>
  );
}
