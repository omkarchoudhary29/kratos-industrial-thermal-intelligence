import React, { useState } from 'react';
import { Calendar, History, Clock, RotateCcw, AlertTriangle } from 'lucide-react';

export type TimeRangePreset =
  | 'latest'
  | '1h'
  | '3h'
  | '6h'
  | '12h'
  | '24h'
  | '7d'
  | '30d'
  | '90d'
  | 'all'
  | 'custom';

interface TimelineControlProps {
  currentPreset: TimeRangePreset;
  startDate?: string;
  endDate?: string;
  onRangeChange: (preset: TimeRangePreset, start?: string, end?: string) => void;
  totalFilteredCount?: number;
}

export const TimelineControl: React.FC<TimelineControlProps> = ({
  currentPreset,
  startDate,
  endDate,
  onRangeChange,
  totalFilteredCount,
}) => {
  const [customStart, setCustomStart] = useState<string>(startDate || '2023-01-01');
  const [customEnd, setCustomEnd] = useState<string>(
    endDate || new Date().toISOString().split('T')[0]
  );
  const [showCustomPicker, setShowCustomPicker] = useState(false);

  const isHistorical = currentPreset !== 'latest' && currentPreset !== '24h' && currentPreset !== '1h' && currentPreset !== '3h' && currentPreset !== '6h' && currentPreset !== '12h';

  const presets: Array<{ id: TimeRangePreset; label: string }> = [
    { id: 'latest', label: 'Latest NRT' },
    { id: '1h', label: '1h' },
    { id: '3h', label: '3h' },
    { id: '6h', label: '6h' },
    { id: '12h', label: '12h' },
    { id: '24h', label: '24h' },
    { id: '7d', label: '7d' },
    { id: '30d', label: '30d' },
    { id: '90d', label: '90d' },
    { id: 'all', label: 'All Catalog' },
  ];

  const handlePresetClick = (preset: TimeRangePreset) => {
    if (preset === 'custom') {
      setShowCustomPicker(true);
      onRangeChange('custom', customStart, customEnd);
    } else {
      setShowCustomPicker(false);
      onRangeChange(preset);
    }
  };

  const handleApplyCustom = (e: React.FormEvent) => {
    e.preventDefault();
    onRangeChange('custom', customStart, customEnd);
  };

  return (
    <div className="space-y-2">
      {/* Historical Replay Alert Banner */}
      {isHistorical && (
        <div className="flex items-center justify-between px-3.5 py-2 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs font-mono animate-fadeIn shadow-xs">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 animate-pulse flex-shrink-0" />
            <span>
              <strong>HISTORICAL REPLAY MODE</strong> — Showing acquisitions between{' '}
              <span className="font-bold underline text-amber-900">{startDate || 'catalog start'}</span> and{' '}
              <span className="font-bold underline text-amber-900">{endDate || 'catalog end'}</span>.
              {totalFilteredCount !== undefined && (
                <span className="text-amber-700 ml-2 font-semibold">({totalFilteredCount} detections loaded)</span>
              )}
            </span>
          </div>

          <button
            onClick={() => handlePresetClick('latest')}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-600 text-white font-semibold text-[11px] hover:bg-amber-700 transition-colors shadow-xs"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Return to Live</span>
          </button>
        </div>
      )}

      {/* Main Timeline Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-2 rounded-xl bg-white border border-slate-200 shadow-xs">
        {/* Left: Presets */}
        <div className="flex flex-wrap items-center gap-1">
          <div className="flex items-center gap-1 text-[11px] text-slate-500 font-mono mr-1.5">
            <Clock className="w-3.5 h-3.5 text-blue-600" />
            <span className="font-bold">TIMELINE:</span>
          </div>

          {presets.map((p) => {
            const isActive = currentPreset === p.id;
            return (
              <button
                key={p.id}
                onClick={() => handlePresetClick(p.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-mono transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white font-bold shadow-xs'
                    : 'bg-slate-50 text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200/80'
                }`}
              >
                {p.label}
              </button>
            );
          })}

          <button
            onClick={() => setShowCustomPicker(!showCustomPicker)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-mono transition-all ${
              currentPreset === 'custom' || showCustomPicker
                ? 'bg-blue-50 text-blue-700 border border-blue-300 font-bold'
                : 'bg-slate-50 text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200/80'
            }`}
          >
            <Calendar className="w-3 h-3 text-blue-600" />
            <span>Custom Range</span>
          </button>
        </div>

        {/* Right: Operational Status Note */}
        <div className="hidden lg:flex items-center gap-2 text-[10px] font-mono text-slate-500">
          <History className="w-3.5 h-3.5 text-blue-600" />
          <span>NASA FIRMS VIIRS NRT Telemetry Grid</span>
        </div>
      </div>

      {/* Collapsible Custom Date Form */}
      {showCustomPicker && (
        <form
          onSubmit={handleApplyCustom}
          className="flex flex-wrap items-center gap-3 p-3 rounded-xl bg-white border border-slate-200 text-xs font-mono shadow-md animate-fadeIn"
        >
          <div className="flex items-center gap-2">
            <span className="text-slate-600 font-semibold">From:</span>
            <input
              type="date"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-900 text-xs font-medium focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-600 font-semibold">To:</span>
            <input
              type="date"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-900 text-xs font-medium focus:outline-none focus:border-blue-500"
            />
          </div>

          <button
            type="submit"
            className="px-3 py-1 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 transition-colors shadow-xs"
          >
            Apply Replay Window
          </button>

          <button
            type="button"
            onClick={() => setShowCustomPicker(false)}
            className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200 border border-slate-200"
          >
            Close
          </button>
        </form>
      )}
    </div>
  );
};
