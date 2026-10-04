import React, { useState } from 'react';
import { ShieldCheck, CloudRain, Zap, Sun, Waves, Wind, CloudFog, ChevronRight, X, PhoneCall, AlertTriangle } from 'lucide-react';

const SAFETY_TOPICS = [
  {
    id: 'rain',
    title: 'Heavy Rainfall',
    icon: CloudRain,
    color: 'text-[#D9A441] bg-[#F7EED7] border-[#D9A441]/30',
    bullets: [
      'Avoid driving through flooded roads or underpasses',
      'Stay clear of open drains, manholes, and power poles',
      'Keep emergency supplies and battery lights ready',
      'Follow official IMD & district warnings closely',
    ],
    details: [
      'Disconnect ungrounded electrical appliances if water enters home premises.',
      'Boil drinking water during heavy precipitation to prevent waterborne illness.',
      'Move livestock and high-value items to higher elevation before surge.',
      'Report localized street flooding through the Weather Intel Citizen Report tool.',
    ]
  },
  {
    id: 'thunderstorm',
    title: 'Thunderstorm',
    icon: Zap,
    color: 'text-[#D9A441] bg-[#F7EED7] border-[#D9A441]/30',
    bullets: [
      'Seek shelter indoors immediately away from windows',
      'Avoid standing under tall isolated trees or metal structures',
      'Unplug sensitive electronic devices from power outlets',
      'If outdoors, crouch low on balls of feet with hands over ears',
    ],
    details: [
      'Never take shelter under tall objects or exposed metal roofs.',
      'Do not use corded phones during intense lightning activity.',
      'Wait at least 30 minutes after hearing the last thunderclap before venturing outside.',
    ]
  },
  {
    id: 'heatwave',
    title: 'Heatwave',
    icon: Sun,
    color: 'text-[#A97820] bg-[#F7EED7] border-[#D9A441]/30',
    bullets: [
      'Drink plenty of water even if you do not feel thirsty',
      'Avoid direct sunlight between 12:00 PM and 4:00 PM',
      'Wear lightweight, light-colored, loose cotton clothing',
      'Provide shade and clean water for pets and domestic animals',
    ],
    details: [
      'Use ORS, homemade drinks like lassi, torani, lemon water, or buttermilk to stay hydrated.',
      'Recognize heat stroke signs: high body temperature, confusion, or dizziness — seek immediate medical aid (112).',
      'Never leave children or animals inside parked vehicles under direct sunshine.',
    ]
  },
  {
    id: 'flooding',
    title: 'Flooding',
    icon: Waves,
    color: 'text-[#2E7D5B] bg-[#2E7D5B]/10 border-[#2E7D5B]/20',
    bullets: [
      'Move to higher ground or upper floors of sturdy buildings',
      'Do not walk or swim through moving floodwaters',
      'Turn off main electricity switch if water rises around home',
      'Keep important documents in waterproof sealed bags',
    ],
    details: [
      'Just 6 inches of moving water can knock down an adult; 12 inches can sweep away small cars.',
      'Watch out for submerged debris, snakes, and exposed electrical wires.',
      'Keep emergency disaster hotline 1078 stored on mobile phone.',
    ]
  },
  {
    id: 'wind',
    title: 'Strong Winds',
    icon: Wind,
    color: 'text-[#111111] bg-[#F7F7F5] border-[#E5E2DA]',
    bullets: [
      'Secure loose outdoor items, flower pots, and signboards',
      'Stay clear of old structures, tin sheds, and billboards',
      'Park vehicles away from trees and overhead power lines',
      'Remain indoors away from glass windows and balcony doors',
    ],
    details: [
      'High wind gusts can cause sudden structural collapse of temporary sheds.',
      'Be cautious of flying debris on highways and coastal corridors.',
    ]
  },
  {
    id: 'fog',
    title: 'Fog & Low Visibility',
    icon: CloudFog,
    color: 'text-[#66635C] bg-[#F7F7F5] border-[#E5E2DA]',
    bullets: [
      'Drive with low-beam headlights and fog lights turned on',
      'Maintain extra distance behind preceding vehicles',
      'Avoid sudden braking or overtaking on dual carriageways',
      'Use lane markers and road reflectors as driving guides',
    ],
    details: [
      'Never use high-beam headlights in dense fog as light reflects back blinding driver.',
      'If visibility drops to near zero, pull completely off roadway into safe area.',
    ]
  },
];

export default function WeatherSafety() {
  const [selectedTopic, setSelectedTopic] = useState(null);

  return (
    <section className="bg-white border border-[#E5E2DA] rounded-xl p-6 sm:p-8 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-[#E5E2DA]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#2E7D5B] inline-block shrink-0" />
            <span className="text-[11px] font-bold tracking-widest text-[#96938B] uppercase font-sans">
              DISASTER PREPAREDNESS
            </span>
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-[#111111] tracking-tight font-sans">
            WEATHER SAFETY & ADVISORIES
          </h2>
          <p className="text-xs sm:text-sm text-[#66635C] mt-0.5">
            Actionable emergency guidance for severe meteorological conditions
          </p>
        </div>

        <button
          onClick={() => setSelectedTopic(SAFETY_TOPICS[0])}
          className="inline-flex items-center gap-2 px-4 py-2 bg-[#F7F7F5] hover:bg-[#E5E2DA] text-[#111111] text-xs font-bold rounded-full border border-[#E5E2DA] transition-colors self-start sm:self-auto cursor-pointer"
        >
          <ShieldCheck className="w-4 h-4 text-[#2E7D5B]" />
          <span>View Safety Guide</span>
        </button>
      </div>

      {/* Safety Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {SAFETY_TOPICS.map((topic) => {
          const Icon = topic.icon;
          return (
            <div
              key={topic.id}
              onClick={() => setSelectedTopic(topic)}
              className="p-5 rounded-xl bg-[#F7F7F5] border border-[#E5E2DA] hover:border-[#D9A441] transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-3 mb-3">
                  <div className={`p-2.5 rounded-lg border ${topic.color}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-bold text-[#96938B] uppercase tracking-widest">
                    SAFETY ADVISORY
                  </span>
                </div>

                <h3 className="text-sm font-bold text-[#111111] group-hover:text-[#A97820] transition-colors mb-2">
                  {topic.title}
                </h3>

                <ul className="space-y-1.5 mb-4">
                  {topic.bullets.slice(0, 3).map((bullet, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-xs text-[#66635C] leading-snug">
                      <span className="text-[#D9A441] font-bold shrink-0">•</span>
                      <span>{bullet}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="pt-3 border-t border-[#E5E2DA] flex items-center justify-between text-xs font-bold text-[#A97820] group-hover:translate-x-0.5 transition-transform">
                <span>Read Full Guidance</span>
                <ChevronRight className="w-4 h-4" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Full Safety Guide Modal */}
      {selectedTopic && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" role="dialog">
          <div className="bg-white border border-[#E5E2DA] rounded-xl max-w-xl w-full p-6 sm:p-8 shadow-2xl relative">
            <button
              onClick={() => setSelectedTopic(null)}
              className="absolute top-5 right-5 p-2 text-[#96938B] hover:text-[#111111] rounded-full bg-[#F7F7F5]"
              aria-label="Close safety guide modal"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-3 mb-3">
              <div className={`p-2.5 rounded-lg border ${selectedTopic.color}`}>
                <selectedTopic.icon className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-bold text-[#2E7D5B] uppercase tracking-wider">Official Preparedness Guide</span>
                <h2 className="text-xl font-extrabold text-[#111111]">{selectedTopic.title} Safety</h2>
              </div>
            </div>

            <div className="space-y-4 my-5">
              <div className="p-4 rounded-xl bg-[#F7EED7] border border-[#D9A441]/30 text-[#A97820] text-xs font-semibold flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-[#D9A441] shrink-0 mt-0.5" />
                <span>Follow district administration alerts and evacuation notices immediately during severe events.</span>
              </div>

              <h4 className="text-xs font-extrabold text-[#111111] uppercase tracking-wider">Key Safety Actions:</h4>
              <ul className="space-y-2">
                {[...selectedTopic.bullets, ...(selectedTopic.details || [])].map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2.5 text-xs text-[#66635C] leading-relaxed">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#D9A441] shrink-0 mt-1.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="pt-4 border-t border-[#E5E2DA] flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs text-red-600 font-bold">
                <PhoneCall className="w-3.5 h-3.5" /> Emergency: 112 / 1078
              </div>
              <button
                onClick={() => setSelectedTopic(null)}
                className="px-5 py-2 bg-[#111111] text-white font-bold rounded-full text-xs"
              >
                Close Guide
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
