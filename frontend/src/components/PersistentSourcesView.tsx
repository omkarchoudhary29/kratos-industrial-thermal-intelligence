import React, { useState } from 'react';
import { ThermalSource } from '../types';
import { Activity, Flame, ShieldAlert, CheckCircle, Factory } from 'lucide-react';

interface PersistentSourcesViewProps {
  sources: ThermalSource[];
}

export const PersistentSourcesView: React.FC<PersistentSourcesViewProps> = ({ sources }) => {
  const [selectedSource, setSelectedSource] = useState<ThermalSource | null>(
    sources[0] || null
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 h-full">
      {/* Sources List Column */}
      <div className="lg:col-span-1 industrial-card p-4 flex flex-col space-y-3 h-[calc(100vh-8rem)]">
        <div className="flex items-center justify-between pb-2 border-b border-[#1E293B]">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-[#F59E0B]" />
            <h2 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
              Persistent Hotspot Clusters
            </h2>
          </div>
          <span className="text-[11px] font-mono text-[#F59E0B] font-semibold">
            {sources.length} active
          </span>
        </div>

        <p className="text-[11px] text-[#64748B]">
          Multi-sensor recurring thermal footprints tracking industrial stacks, flares, and continuous process furnaces.
        </p>

        <div className="overflow-y-auto space-y-2 flex-1 pr-1">
          {sources.map((src) => {
            const isSelected = selectedSource?.thermal_source_id === src.thermal_source_id;
            const srcId = src.thermal_source_id || 'source';
            const isClassified = Boolean(src.source_class && src.source_class !== 'unknown' && src.source_class !== 'unclassified');
            const srcClass = isClassified && src.source_class ? src.source_class.replace(/_/g, ' ') : 'Unclassified';
            const count = src.detection_count ?? (src as any).total_detections ?? 0;

            return (
              <div
                key={srcId}
                onClick={() => setSelectedSource(src)}
                className={`p-3 rounded border cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-[#182235] border-[#F59E0B] shadow-md shadow-[#F59E0B]/10'
                    : 'bg-[#0D131F] border-[#1E293B] hover:border-[#2A374D]'
                }`}
              >
                <div className="flex justify-between items-start mb-1">
                  <span className="font-mono text-xs font-bold text-white">
                    {srcId.slice(0, 14)}
                  </span>
                  <span className={`badge ${isClassified ? 'badge-gold' : 'bg-[#1E293B] text-[#94A3B8] border border-[#2A374D]'}`}>
                    {srcClass}
                  </span>
                </div>
                <div className="flex justify-between text-[11px] text-[#94A3B8]">
                  <span>{src.region_name || 'General Region'}</span>
                  <span className="font-mono">
                    {count} detections
                  </span>
                </div>
                <div className="flex justify-between text-[10px] text-[#64748B] font-mono mt-1 pt-1 border-t border-[#1E293B]/60">
                  <span>Mean FRP: {src.mean_frp ? src.mean_frp.toFixed(1) : '—'} MW</span>
                  <span>Confidence: {src.classification_confidence != null ? `${(src.classification_confidence * 100).toFixed(0)}%` : '—'}</span>
                </div>
              </div>
            );
          })}

          {sources.length === 0 && (
            <div className="text-center py-10 text-[#64748B] text-xs">
              No persistent thermal clusters loaded.
            </div>
          )}
        </div>
      </div>

      {/* Detail Column */}
      <div className="lg:col-span-2 industrial-card p-6 flex flex-col justify-between h-[calc(100vh-8rem)] overflow-y-auto">
        {selectedSource ? (
          <div className="space-y-6">
            {/* Header info */}
            <div className="border-b border-[#1E293B] pb-4 flex justify-between items-start">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/40 uppercase">
                    Cluster ID: {selectedSource.thermal_source_id}
                  </span>
                  <span className="text-xs text-[#94A3B8]">
                    Region: <strong className="text-white">{selectedSource.region_name}</strong>
                  </span>
                </div>
                <h2 className="text-xl font-bold text-white capitalize">
                  {selectedSource.source_class && selectedSource.source_class !== 'unknown' && selectedSource.source_class !== 'unclassified'
                    ? selectedSource.source_class.replace(/_/g, ' ')
                    : 'Unclassified'}
                </h2>
                <p className="text-xs text-[#94A3B8] font-mono mt-1">
                  Latitude: {(selectedSource.latitude ?? (selectedSource as any).source_latitude ?? 0).toFixed(4)}°N | Longitude: {(selectedSource.longitude ?? (selectedSource as any).source_longitude ?? 0).toFixed(4)}°E
                </p>
              </div>

              <div className="text-right">
                <span className="text-xs text-[#64748B] uppercase font-mono block">
                  Rule Heuristic Rating
                </span>
                <span className="text-2xl font-bold font-mono text-[#F59E0B]">
                  {selectedSource.classification_confidence != null
                    ? `${(selectedSource.classification_confidence * 100).toFixed(1)}%`
                    : '—'}
                </span>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-3 bg-[#0D131F] rounded border border-[#1E293B]">
                <span className="text-[10px] font-mono text-[#64748B] uppercase block">
                  Total Observations
                </span>
                <span className="text-lg font-bold font-mono text-white">
                  {selectedSource.detection_count}
                </span>
              </div>
              <div className="p-3 bg-[#0D131F] rounded border border-[#1E293B]">
                <span className="text-[10px] font-mono text-[#64748B] uppercase block">
                  Mean Radiative Power
                </span>
                <span className="text-lg font-bold font-mono text-[#F59E0B]">
                  {selectedSource.mean_frp ? selectedSource.mean_frp.toFixed(1) : '—'} MW
                </span>
              </div>
              <div className="p-3 bg-[#0D131F] rounded border border-[#1E293B]">
                <span className="text-[10px] font-mono text-[#64748B] uppercase block">
                  Peak Historical FRP
                </span>
                <span className="text-lg font-bold font-mono text-orange-400">
                  {selectedSource.max_frp ? selectedSource.max_frp.toFixed(1) : '—'} MW
                </span>
              </div>
              <div className="p-3 bg-[#0D131F] rounded border border-[#1E293B]">
                <span className="text-[10px] font-mono text-[#64748B] uppercase block">
                  Temporal Behavior
                </span>
                <span className="text-lg font-bold font-mono text-emerald-400">
                  Continuous
                </span>
              </div>
            </div>

            {/* Context & Attribution */}
            <div className="p-4 bg-[#0D131F] rounded border border-[#1E293B] space-y-3">
              <h3 className="text-xs font-bold text-white uppercase font-mono flex items-center gap-2">
                <Factory className="w-4 h-4 text-[#F59E0B]" />
                Geospatial & Infrastructure Context
              </h3>
              <p className="text-xs text-[#CBD5E1] leading-relaxed">
                This thermal signature shows high temporal recurrence across satellite revisit tracks. In contrast to transient biomass fires, recurring high-temperature pixels over multiple calendar weeks within an industrial perimeter indicate stationary furnace or process heat emissions.
              </p>
              <div className="pt-2 border-t border-[#1E293B] flex items-center justify-between text-xs text-[#94A3B8]">
                <span>Corridor: {selectedSource.region_name}</span>
                <span className="text-[#F59E0B] font-mono">DBSCAN Epsilon: 300m</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-[#64748B] text-xs">
            Select a persistent cluster from the list to inspect spatial characteristics.
          </div>
        )}
      </div>
    </div>
  );
};
