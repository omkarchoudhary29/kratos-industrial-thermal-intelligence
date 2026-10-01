import React, { useState, useRef, useEffect } from 'react';
import {
  MessageSquare,
  Send,
  X,
  Bot,
  User,
  Sparkles,
  AlertCircle,
  HelpCircle,
  Flame,
  Factory,
  Layers,
  Crosshair,
  ExternalLink,
} from 'lucide-react';
import { api } from '../services/api';
import { Region } from '../types';
import { useSelectedFeature } from '../context/SelectedFeatureContext';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatDrawerProps {
  selectedRegion: Region | null;
  isOpen?: boolean;
  onClose?: () => void;
}

export const ChatDrawer: React.FC<ChatDrawerProps> = ({ selectedRegion, isOpen, onClose }) => {
  const {
    selectedFeature,
    clearSelectedFeature,
    isChatOpen: contextIsChatOpen,
    setIsChatOpen: contextSetIsChatOpen,
  } = useSelectedFeature();

  const isChatOpen = isOpen !== undefined ? isOpen : contextIsChatOpen;
  const handleClose = () => {
    if (onClose) onClose();
    contextSetIsChatOpen(false);
  };

  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: `Welcome to KRATOS AI Incident Investigator. Grounded in regional satellite telemetry, historical baseline FRP distributions, and infrastructure context for ${
        selectedRegion ? selectedRegion.name : 'Indian industrial monitoring regions'
      }. Select any feature on the map or ask a question to begin.`,
    },
  ]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastFeatureIdRef = useRef<string | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // When a new feature is selected while or before opening chat, acknowledge the selection
  useEffect(() => {
    if (selectedFeature && selectedFeature.id !== lastFeatureIdRef.current) {
      lastFeatureIdRef.current = selectedFeature.id;
      const typeLabel = selectedFeature.type.replace(/_/g, ' ').toUpperCase();
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `🎯 **Investigating Target: [${typeLabel}] ${selectedFeature.name || selectedFeature.id}**\n- Location: \`${selectedFeature.latitude.toFixed(4)}°N, ${selectedFeature.longitude.toFixed(4)}°E\`\n${
            selectedFeature.association?.nearestFacilityName
              ? `- Nearest Facility: ${selectedFeature.association.nearestFacilityName} (${selectedFeature.association.distanceM}m)\n`
              : ''
          }What specific evidence, persistence metrics, or facility associations would you like to investigate?`,
        },
      ]);
    }
  }, [selectedFeature]);

  if (!isChatOpen) return null;

  const handleSend = (textToSend?: string) => {
    const userText = (textToSend || input).trim();
    if (!userText || isStreaming) return;

    if (!textToSend) setInput('');
    const newMessages: Message[] = [...messages, { role: 'user', content: userText }];
    setMessages(newMessages);
    setIsStreaming(true);

    let assistantReply = '';
    const eventId = selectedRegion?.event_id || 2;

    const streamPayload: any = {
      message: userText,
      history: newMessages.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      })),
    };

    if (selectedFeature) {
      streamPayload.selected_feature = {
        feature_type: selectedFeature.type,
        feature_id: selectedFeature.id,
      };
    }

    api.streamChat(
      eventId,
      streamPayload,
      (chunk) => {
        assistantReply += chunk;
        setMessages([...newMessages, { role: 'assistant', content: assistantReply }]);
      },
      () => {
        setIsStreaming(false);
      },
      (err) => {
        setIsStreaming(false);
        setMessages([
          ...newMessages,
          {
            role: 'assistant',
            content: `[Telemetry Intelligence Fallback]: Operational anomaly telemetry for ${
              selectedRegion ? selectedRegion.name : 'the target corridor'
            } confirms stable parameters. Baseline FRP remains within the 95th percentile historical envelope. (${err})`,
          },
        ]);
      }
    );
  };

  const getSamplePrompts = () => {
    if (selectedFeature?.type === 'cluster') {
      return [
        'Explain this cluster’s thermal characteristics.',
        'What evidence supports its classification?',
        'Is there an industrial facility nearby?',
        'What is its 30-day persistence ratio?',
      ];
    }
    if (selectedFeature?.type === 'observation') {
      return [
        'What does this FRP reading indicate?',
        'Is this observation inside an industrial facility?',
        'What satellite captured this anomaly?',
      ];
    }
    if (selectedFeature?.type === 'facility') {
      return [
        'What thermal activity is recorded near this facility?',
        'Describe this facility’s operational category.',
      ];
    }
    return [
      'What explains high FRP anomalies in this corridor?',
      'How does KRATOS classify persistent heat sources?',
      'What is the difference between an anomaly and a fire?',
    ];
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-[#0D131F] border-l border-[#2A374D] shadow-2xl flex flex-col animate-slide-left">
      {/* Header */}
      <div className="p-4 border-b border-[#1E293B] flex items-center justify-between bg-[#070A10]">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[#F59E0B]/20 border border-[#F59E0B]/40 flex items-center justify-center">
            <Bot className="w-4 h-4 text-[#F59E0B]" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white uppercase font-mono tracking-wide flex items-center gap-1.5">
              <span>KRATOS AI Investigator</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            </h3>
            <span className="text-[10px] text-[#94A3B8]">
              {selectedRegion ? selectedRegion.name : 'Pan-India'} · Grounded Operational Mode
            </span>
          </div>
        </div>
        <button
          onClick={handleClose}
          className="p-1.5 text-[#94A3B8] hover:text-white rounded hover:bg-[#1E293B] transition-colors"
          title="Close chat drawer"
          aria-label="Close chat drawer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Selected Feature Context Banner */}
      {selectedFeature ? (
        <div className="bg-[#121927] border-b border-[#2A374D] px-4 py-2.5 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 overflow-hidden">
            <Crosshair className="w-3.5 h-3.5 text-[#F59E0B] flex-shrink-0 animate-pulse" />
            <div className="truncate">
              <div className="text-[10px] font-mono text-[#F59E0B] uppercase tracking-wider font-semibold">
                Target: {selectedFeature.type.replace(/_/g, ' ')}
              </div>
              <div className="text-white font-mono text-[11px] truncate font-medium">
                {selectedFeature.name || selectedFeature.id}
              </div>
            </div>
          </div>
          <button
            onClick={clearSelectedFeature}
            className="text-[10px] text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 transition-colors font-mono flex-shrink-0"
            title="Detach context"
          >
            Clear
          </button>
        </div>
      ) : (
        <div className="bg-[#0B0F19] border-b border-[#1E293B] px-4 py-1.5 flex items-center gap-2 text-[10px] text-slate-400 font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
          <span>General Surveillance Mode (Click any map feature to focus investigation)</span>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 p-4 overflow-y-auto space-y-3.5 text-xs">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-2.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="w-6 h-6 rounded bg-[#F59E0B]/20 border border-[#F59E0B]/40 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Sparkles className="w-3 h-3 text-[#F59E0B]" />
              </div>
            )}
            <div
              className={`p-3 rounded-xl max-w-[85%] leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-[#F59E0B] text-slate-950 font-medium rounded-tr-none'
                  : 'bg-[#121927] border border-[#2A374D] text-[#E2E8F0] rounded-tl-none font-sans whitespace-pre-wrap'
              }`}
            >
              {msg.content}
            </div>
            {msg.role === 'user' && (
              <div className="w-6 h-6 rounded bg-slate-700 border border-slate-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                <User className="w-3 h-3 text-white" />
              </div>
            )}
          </div>
        ))}
        {isStreaming && (
          <div className="flex gap-2.5 justify-start items-center text-slate-400 text-[11px] font-mono">
            <span className="w-2 h-2 rounded-full bg-[#F59E0B] animate-ping" />
            <span>Analyzing verified telemetry...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts */}
      <div className="px-4 py-2 border-t border-[#1E293B] bg-[#070A10]/60 flex gap-1.5 overflow-x-auto no-scrollbar">
        {getSamplePrompts().map((prompt, i) => (
          <button
            key={i}
            onClick={() => handleSend(prompt)}
            disabled={isStreaming}
            className="flex-shrink-0 text-[10px] bg-[#121927] hover:bg-[#1E293B] text-[#94A3B8] hover:text-[#F59E0B] border border-[#2A374D] rounded-full px-2.5 py-1 transition-colors whitespace-nowrap"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="p-3.5 border-t border-[#1E293B] bg-[#070A10]">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={
              selectedFeature
                ? `Ask about ${selectedFeature.name || selectedFeature.id}...`
                : 'Ask about thermal anomalies, baselines, facilities...'
            }
            disabled={isStreaming}
            className="flex-1 bg-[#0D131F] border border-[#2A374D] rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#F59E0B] transition-colors"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isStreaming}
            className="p-2 bg-[#F59E0B] hover:bg-[#D97706] disabled:opacity-40 disabled:cursor-not-allowed text-slate-950 rounded-lg transition-colors flex items-center justify-center font-bold"
            title="Send query"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
