import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, Send, Bot, User, ArrowLeft, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api.js';

const SAMPLE_QUESTIONS = [
  "What weather events are active in India?",
  "Which regions have heavy rainfall?",
  "Explain the latest weather observations.",
  "Are there any severe weather risks?",
];

function FormattedMessage({ text }) {
  if (!text) return null;
  const lines = text.split('\n');

  return (
    <div className="space-y-1.5 leading-relaxed text-xs sm:text-sm">
      {lines.map((line, lineIdx) => {
        if (!line.trim()) return <div key={lineIdx} className="h-1" />;

        const trimmed = line.trim();
        const isBullet = trimmed.startsWith('•') || trimmed.startsWith('-');
        const lineContent = isBullet ? trimmed.replace(/^[•-]\s*/, '') : line;

        const parts = lineContent.split(/(\*\*.*?\*\*)/g);
        const renderedParts = parts.map((part, partIdx) => {
          if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
            return (
              <strong key={partIdx} className="font-extrabold text-stone-900 dark:text-white">
                {part.slice(2, -2)}
              </strong>
            );
          }
          return part;
        });

        if (isBullet) {
          return (
            <div key={lineIdx} className="flex items-start gap-2 pl-1 my-0.5">
              <span className="text-amber-500 font-bold shrink-0 font-mono">•</span>
              <span className="flex-1">{renderedParts}</span>
            </div>
          );
        }

        return <p key={lineIdx}>{renderedParts}</p>;
      })}
    </div>
  );
}

export default function AskAtmos() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (queryToSend) => {
    const text = (queryToSend || inputQuery).trim();
    if (!text || loading) return;

    const userMessage = {
      id: Date.now(),
      sender: 'user',
      text: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    if (!queryToSend) setInputQuery('');
    setLoading(true);

    try {
      const { data } = await api.post('/api/intelligence/ask', { query: text });
      const assistantMessage = {
        id: Date.now() + 1,
        sender: 'assistant',
        text: data.answer || "I parsed the current weather data, but no explicit details were returned.",
        eventsAnalyzed: data.events_analyzed,
        highPriorityCount: data.high_priority_count,
        avgVerScore: data.avg_verification_score,
        relatedEvents: data.related_events || [],
        verifiedSources: data.verified_sources || [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Ask Intel error:', err);
      const errorMessage = {
        id: Date.now() + 1,
        sender: 'assistant',
        isError: true,
        text: "Unable to reach the Weather Intel service right now. Please check your network connection and try again.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="max-w-4xl mx-auto flex flex-col min-h-[calc(100vh-140px)] relative">
      
      {/* Editorial Page Header with Back Experience */}
      <div className="flex items-center justify-between pb-6 mb-6 border-b border-[#E5E2DA]">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2.5 rounded-full bg-white border border-[#E5E2DA] text-[#66635C] hover:text-[#111111] hover:bg-[#F7F7F5] transition-all shadow-sm"
            title="Go back"
            aria-label="Go back"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#111111] tracking-tight flex items-center gap-2">
              Ask Intel
              <Sparkles className="w-5 h-5 text-[#D9A441]" />
            </h1>
            <p className="text-xs sm:text-sm text-[#66635C] mt-0.5 font-normal">
              Your AI assistant for Indian weather intelligence.
            </p>
          </div>
        </div>

        {messages.length > 0 && (
          <button
            onClick={() => setMessages([])}
            className="text-xs font-semibold text-[#66635C] hover:text-[#111111] flex items-center gap-1.5 px-3.5 py-1.5 rounded-full border border-[#E5E2DA] bg-white transition-colors shadow-sm"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Clear Chat</span>
          </button>
        )}
      </div>

      {/* Main Chat Conversation Area */}
      <div className="flex-1 space-y-6 pb-28">
        
        {/* Empty State */}
        {messages.length === 0 && (
          <div className="py-8 sm:py-12 flex flex-col items-center text-center space-y-6">
            <div className="w-16 h-16 rounded-2xl bg-[#111111] text-[#D9A441] flex items-center justify-center shadow-sm">
              <Sparkles className="w-8 h-8" />
            </div>

            <div className="max-w-md space-y-2">
              <h2 className="text-lg font-bold text-[#111111]">
                How can I assist your weather intelligence today?
              </h2>
              <p className="text-xs sm:text-sm text-[#66635C] leading-relaxed">
                Ask conversational questions regarding real-time severe weather incidents, state risk analyses, verified observations, or ingestion feeds across India.
              </p>
            </div>

            {/* Example Prompt Pills */}
            <div className="w-full max-w-2xl pt-4">
              <p className="text-[11px] font-bold text-[#96938B] uppercase tracking-wider mb-3 text-left">
                Suggested Questions
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
                {SAMPLE_QUESTIONS.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(q)}
                    className="p-4 rounded-xl bg-white border border-[#E5E2DA] hover:border-[#D9A441] text-[#111111] text-xs font-medium transition-all shadow-sm flex items-center justify-between group"
                  >
                    <span>{q}</span>
                    <Sparkles className="w-3.5 h-3.5 text-[#96938B] group-hover:text-[#D9A441] transition-colors shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Message Bubble Feed */}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start gap-3 ${
              msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'
            }`}
          >
            {/* Avatar */}
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${
                msg.sender === 'user'
                  ? 'bg-[#E5E2DA] text-[#111111]'
                  : 'bg-[#111111] text-[#D9A441]'
              }`}
            >
              {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            {/* Message Bubble Content */}
            <div
              className={`max-w-[85%] sm:max-w-[78%] rounded-2xl p-5 shadow-sm space-y-3 ${
                msg.sender === 'user'
                  ? 'bg-[#111111] text-white rounded-tr-xs'
                  : 'bg-white border border-[#E5E2DA] text-[#111111] rounded-tl-xs'
              }`}
            >
              <div className="flex items-center justify-between gap-4 pb-1 border-b border-[#E5E2DA]/40 text-[10px] font-semibold text-[#96938B]">
                <span>{msg.sender === 'user' ? 'You' : 'Intel'}</span>
                <span>{msg.timestamp}</span>
              </div>

              {/* Message Body */}
              <FormattedMessage text={msg.text} />

              {/* Grounded RAG Verified Sources display (Deduplicated) */}
              {msg.verifiedSources && msg.verifiedSources.length > 0 && (() => {
                const uniqueSources = [];
                const seenKeys = new Set();
                for (const s of msg.verifiedSources) {
                  const key = `${(s.city || 'india').toLowerCase()}_${(s.event_type || 'obs').toLowerCase()}_${(s.source || 'verified').toLowerCase()}`;
                  if (!seenKeys.has(key)) {
                    seenKeys.add(key);
                    uniqueSources.push(s);
                  }
                }

                return (
                  <div className="pt-3 border-t border-[#E5E2DA] space-y-1.5 text-left">
                    <p className="text-[10px] font-bold text-[#96938B] uppercase tracking-widest">
                      Verified Sources ({uniqueSources.length})
                    </p>
                    <div className="flex flex-wrap gap-2 pt-0.5">
                      {uniqueSources.map((s, sIdx) => (
                        <div
                          key={sIdx}
                          onClick={() => s.id && navigate(`/events/${s.id}/intelligence`)}
                          className="text-[11px] px-3 py-1.5 rounded-lg bg-[#F7F7F5] border border-[#E5E2DA] text-[#111111] flex items-center gap-2 cursor-pointer hover:border-[#D9A441] transition-colors"
                        >
                          <span className="font-bold text-[#111111]">{s.city || 'India'}{s.state ? `, ${s.state}` : ''}</span>
                          <span className="text-[#96938B]">•</span>
                          <span className="text-[10px] text-[#66635C] capitalize">{s.event_type || 'observation'} ({s.source || 'verified'})</span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}

            </div>
          </div>
        ))}

        {/* Loading Indicator */}
        {loading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-[#111111] text-[#D9A441] flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4 animate-pulse" />
            </div>
            <div className="bg-white border border-[#E5E2DA] text-[#66635C] rounded-2xl rounded-tl-xs p-4 shadow-sm flex items-center gap-3 text-xs font-medium">
              <RefreshCw className="w-4 h-4 animate-spin text-[#D9A441]" />
              <span>Analyzing Indian weather observations and database telemetry...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Sticky Bottom Composer */}
      <div className="sticky bottom-4 max-w-4xl mx-auto w-full z-30">
        <div className="bg-white/95 backdrop-blur-md border border-[#E5E2DA] rounded-xl p-2 shadow-lg flex items-center gap-2 transition-all">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about weather, events, risks, or observations..."
            className="flex-1 bg-transparent px-4 py-2.5 text-xs sm:text-sm text-[#111111] placeholder-[#96938B] focus:outline-none"
            disabled={loading}
          />
          <button
            onClick={() => handleSend()}
            disabled={!inputQuery.trim() || loading}
            className="w-10 h-10 rounded-lg bg-[#111111] text-white hover:bg-black disabled:opacity-40 flex items-center justify-center transition-all shrink-0 shadow-sm cursor-pointer"
            aria-label="Send message"
          >
            <Send className="w-4 h-4 text-[#D9A441]" />
          </button>
        </div>
      </div>
    </div>
  );
}
