import React from 'react';
import { Bot, Sparkles, X } from 'lucide-react';
import { useSelectedFeature } from '../context/SelectedFeatureContext';

export const FloatingAIAssistant: React.FC = () => {
  const {
    selectedFeature,
    clearSelectedFeature,
    isChatOpen,
    setIsChatOpen,
  } = useSelectedFeature();

  if (isChatOpen) return null;

  return (
    <div className="fixed bottom-5 right-5 z-40 flex items-center gap-2 select-none animate-fade-in">
      {/* Context indicator pill when a feature is selected */}
      {selectedFeature && (
        <div className="flex items-center gap-2 bg-[#0F172A]/95 border border-[#F59E0B]/50 text-white text-xs px-3 py-2 rounded-full shadow-2xl backdrop-blur-md">
          <span className="w-2 h-2 rounded-full bg-[#F59E0B] animate-ping" />
          <button
            onClick={() => setIsChatOpen(true)}
            className="flex items-center gap-1.5 hover:text-[#F59E0B] font-mono text-[11px] transition-colors"
          >
            <span>Target:</span>
            <span className="font-semibold text-white max-w-[140px] truncate">
              {selectedFeature.name || selectedFeature.id}
            </span>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              clearSelectedFeature();
            }}
            className="p-0.5 rounded-full hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
            title="Clear target context"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Main Floating AI Button */}
      <button
        onClick={() => setIsChatOpen(true)}
        className="group relative flex items-center gap-2.5 px-4 py-2.5 rounded-full bg-gradient-to-r from-[#B45309] to-[#D97706] hover:from-[#D97706] hover:to-[#F59E0B] text-white shadow-xl shadow-[#F59E0B]/20 border border-[#F59E0B]/40 hover:border-[#F59E0B] transition-all transform hover:scale-105 active:scale-95"
        title="Open KRATOS AI Assistant"
      >
        <div className="relative">
          <Bot className="w-4 h-4 text-white" />
          <Sparkles className="w-2.5 h-2.5 text-amber-200 absolute -top-1.5 -right-1.5 animate-pulse" />
        </div>
        <span className="text-xs font-bold font-mono tracking-wide uppercase">
          AI Investigator
        </span>
        {selectedFeature && (
          <span className="w-2 h-2 rounded-full bg-white absolute -top-0.5 -right-0.5" />
        )}
      </button>
    </div>
  );
};
