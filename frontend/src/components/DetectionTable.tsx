import React, { useState } from 'react';
import { ThermalEvent } from '../types';
import { Search, ExternalLink, CheckCircle2 } from 'lucide-react';

interface DetectionTableProps {
  events: ThermalEvent[];
  onSelectEvent?: (event: ThermalEvent) => void;
}

export const DetectionTable: React.FC<DetectionTableProps> = ({
  events,
  onSelectEvent,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [iforestFilter, setIforestFilter] = useState<string>('all');

  const filteredEvents = events.filter((ev) => {
    const matchesSearch =
      ev.source_event_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ev.region_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (ev.nearest_industry_name || '').toLowerCase().includes(searchTerm.toLowerCase());

    const matchesRisk = riskFilter === 'all' || ev.final_risk_level === riskFilter;
    const matchesIForest =
      iforestFilter === 'all' ||
      (iforestFilter === 'true' && ev.iforest_agreement === true) ||
      (iforestFilter === 'false' && ev.iforest_agreement === false);

    return matchesSearch && matchesRisk && matchesIForest;
  });

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-4 shadow-xs">
      {/* Search & Filters Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by ID, region, or facility..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 focus:border-blue-500 focus:bg-white text-xs text-slate-900 pl-9 pr-3 py-1.5 rounded-lg outline-none transition-colors"
          />
        </div>

        <div className="flex items-center gap-2">
          {/* Risk Level Filter */}
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            aria-label="Filter by Risk Level"
            className="bg-slate-50 border border-slate-200 text-xs text-slate-700 font-medium px-2.5 py-1.5 rounded-lg focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Risk Levels</option>
            <option value="critical">Critical Risk</option>
            <option value="high">High Risk</option>
            <option value="medium">Medium Risk</option>
            <option value="low">Low Risk</option>
          </select>

          {/* Isolation Forest Agreement */}
          <select
            value={iforestFilter}
            onChange={(e) => setIforestFilter(e.target.value)}
            aria-label="Filter by Isolation Forest Confirmation"
            className="bg-slate-50 border border-slate-200 text-xs text-slate-700 font-medium px-2.5 py-1.5 rounded-lg focus:outline-none focus:border-blue-500"
          >
            <option value="all">All ML Predictions</option>
            <option value="true">Confirmed Anomaly (IForest)</option>
            <option value="false">Normal Range (IForest)</option>
          </select>

          <span className="text-xs text-slate-500 font-mono">
            {filteredEvents.length} events
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-200 text-[11px] font-mono text-slate-500 uppercase">
              <th className="py-2.5 px-3">Event ID</th>
              <th className="py-2.5 px-3">Risk Level</th>
              <th className="py-2.5 px-3">Region</th>
              <th className="py-2.5 px-3">Coordinates</th>
              <th className="py-2.5 px-3">Max FRP</th>
              <th className="py-2.5 px-3">IForest Check</th>
              <th className="py-2.5 px-3">Nearest Facility</th>
              <th className="py-2.5 px-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-mono">
            {filteredEvents.slice(0, 15).map((ev) => {
              const risk = ev.final_risk_level;
              return (
                <tr
                  key={ev.source_event_id}
                  onClick={() => onSelectEvent && onSelectEvent(ev)}
                  className="hover:bg-slate-50 cursor-pointer transition-colors group"
                >
                  <td className="py-3 px-3 font-semibold text-slate-900 group-hover:text-blue-600">
                    {ev.source_event_id.slice(0, 16)}...
                  </td>
                  <td className="py-3 px-3">
                    <span
                      className={`badge ${
                        risk === 'critical'
                          ? 'badge-critical'
                          : risk === 'high'
                          ? 'badge-high'
                          : risk === 'medium'
                          ? 'badge-medium'
                          : 'badge-low'
                      }`}
                    >
                      {risk}
                    </span>
                  </td>
                  <td className="py-3 px-3 font-sans text-slate-700">
                    {ev.region_name}
                  </td>
                  <td className="py-3 px-3 text-slate-500">
                    {ev.latitude.toFixed(3)}°, {ev.longitude.toFixed(3)}°
                  </td>
                  <td className="py-3 px-3 text-slate-900 font-bold">
                    {ev.max_frp ? `${ev.max_frp.toFixed(1)} MW` : '—'}
                  </td>
                  <td className="py-3 px-3">
                    {ev.iforest_agreement ? (
                      <span className="flex items-center gap-1 text-emerald-600 font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Confirmed</span>
                      </span>
                    ) : (
                      <span className="text-slate-400">Normal</span>
                    )}
                  </td>
                  <td className="py-3 px-3 font-sans text-slate-600 max-w-[160px] truncate">
                    {ev.nearest_industry_name || 'Forest / Rural'}
                  </td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (onSelectEvent) onSelectEvent(ev);
                      }}
                      className="p-1 hover:text-blue-600 text-slate-400 transition-colors"
                      title="Inspect event details"
                      aria-label="Inspect event details"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredEvents.length === 0 && (
          <div className="py-8 text-center text-slate-400 text-xs">
            No thermal detection events match the selected filters.
          </div>
        )}
      </div>
    </div>
  );
};
