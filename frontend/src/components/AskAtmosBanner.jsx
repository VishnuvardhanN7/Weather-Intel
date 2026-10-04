import React from 'react';
import { Sparkles, ArrowRight, MessageSquare } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useLocationContext } from '../context/LocationContext.jsx';

export default function AskAtmosBanner() {
  const navigate = useNavigate();
  const { selectedLocation } = useLocationContext();
  const city = selectedLocation.city;

  const sampleQuestions = [
    `Will it rain in ${city} tomorrow?`,
    `Are there severe weather events near ${city}?`,
    `What weather alerts are active for ${selectedLocation.state || city}?`,
    `What should I do during a thunderstorm in ${city}?`,
  ];

  const handleAskQuestion = (question) => {
    navigate(`/ask-atmos?q=${encodeURIComponent(question)}`);
  };

  return (
    <section className="bg-[#111111] border border-[#E5E2DA]/20 rounded-2xl p-6 sm:p-8 text-white shadow-sm relative overflow-hidden">
      <div className="relative z-10 space-y-6">
        {/* Top Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5 max-w-xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#D9A441]/20 text-[#D9A441] text-xs font-bold border border-[#D9A441]/30">
              <Sparkles className="w-3.5 h-3.5" /> ATMOS AI ASSISTANT
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              ASK ATMOS ABOUT {city.toUpperCase()}
            </h2>
            <p className="text-xs sm:text-sm text-stone-300 font-medium">
              Have a question about the weather in {city}? Ask our RAG-powered intelligent weather assistant.
            </p>
          </div>

          <button
            onClick={() => navigate('/ask-atmos')}
            className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-[#D9A441] hover:bg-[#E2B84A] text-[#111111] font-bold text-xs sm:text-sm rounded-full transition-all duration-200 shadow-sm shrink-0 cursor-pointer self-start md:self-auto"
          >
            <span>Ask ATMOS</span>
            <ArrowRight className="w-4 h-4 text-[#111111]" />
          </button>
        </div>

        {/* Sample Question Pills */}
        <div className="pt-4 border-t border-white/10">
          <p className="text-[11px] font-bold text-stone-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <MessageSquare className="w-3.5 h-3.5 text-[#D9A441]" /> Common Questions for {city}:
          </p>
          <div className="flex flex-wrap gap-2">
            {sampleQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleAskQuestion(q)}
                className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-full text-xs font-medium border border-white/10 transition-all text-left flex items-center gap-2 group cursor-pointer"
              >
                <span>"{q}"</span>
                <ArrowRight className="w-3 h-3 text-[#D9A441] opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
