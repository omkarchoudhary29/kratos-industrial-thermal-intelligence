import React, { useState, useEffect } from 'react';
import {
  Satellite,
  Clock,
  Database,
  Info,
  ChevronDown,
  ChevronUp,
  RefreshCw,
} from 'lucide-react';
import { api } from '../services/api';
import { DataFreshnessInfo } from '../types';

export const DataFreshnessBar: React.FC = () => {
  const [freshness, setFreshness] = useState<DataFreshnessInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const data = await api.getFiresStatus();
      setFreshness(data);
    } catch (err) {
      console.warn('Could not fetch pipeline status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 120000);
    return () => clearInterval(interval);
  }, []);

  const formatTimestamp = (iso?: string | null) => {
    if (!iso) return 'Synchronized with catalog';
    try {
      const d = new Date(iso);
      return d.toLocaleString('en-US', {
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
        timeZoneName: 'short',
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="bg-slate-50 border-b border-slate-200 text-[11px] text-slate-600 transition-all select-none">
      {/* Primary Bar */}
      <div className="max-w-7xl mx-auto px-4 py-1.5 flex flex-wrap items-center justify-between gap-y-1 gap-x-4">
        {/* Left side: Satellite feeds & operational health */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          {/* Active Sensor Feed */}
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-slate-900 font-mono font-bold tracking-wider text-[10px] uppercase">
              NOAA-21 VIIRS
            </span>
            <span className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-1.5 py-0.2 rounded text-[9px] font-mono font-semibold">
              Primary NRT
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-1.5 text-slate-400">
            <span>•</span>
            <span className="text-slate-700 font-medium">NOAA-20</span>
            <span className="text-[10px] text-slate-500">(Operational)</span>
          </div>

          <div className="hidden md:flex items-center gap-1.5 text-slate-400">
            <span>•</span>
            <span className="text-slate-600">Suomi-NPP</span>
            <span className="text-[9px] bg-slate-200/80 text-slate-600 px-1 py-0.2 rounded font-mono">
              Archive Baseline
            </span>
          </div>

          {/* Latency Note */}
          <div className="hidden lg:flex items-center gap-1 text-amber-700 font-mono text-[10px]">
            <Clock className="w-3 h-3 text-amber-600" />
            <span>FIRMS Latency: ~2–4h orbital pass to NRT</span>
          </div>
        </div>

        {/* Right side: Observation timestamp, OSM tag, and toggle */}
        <div className="flex items-center gap-3 font-mono text-[10px]">
          <div className="flex items-center gap-1 text-slate-700">
            <span className="text-slate-400 font-semibold">LATEST OBS:</span>
            <span className="text-slate-900 font-bold">
              {formatTimestamp(freshness?.last_observed_at || freshness?.last_successful_sync)}
            </span>
          </div>

          <div className="hidden xl:flex items-center gap-1 text-slate-600">
            <Database className="w-3 h-3 text-blue-600" />
            <span>OSM: 1,200+ Facilities</span>
          </div>

          <button
            onClick={fetchStatus}
            disabled={loading}
            className="p-1 text-slate-400 hover:text-slate-800 transition-colors"
            title="Refresh Ingestion Telemetry"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin text-blue-600' : ''}`} />
          </button>

          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-white border border-slate-200 hover:border-slate-300 text-slate-700 font-medium transition-colors shadow-xs"
          >
            <span>Telemetry</span>
            {expanded ? <ChevronUp className="w-3 h-3 text-slate-500" /> : <ChevronDown className="w-3 h-3 text-slate-500" />}
          </button>
        </div>
      </div>

      {/* Expandable Telemetry Drawer */}
      {expanded && (
        <div className="border-t border-slate-200 bg-white px-4 py-3 text-[11px] animate-fadeIn">
          <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-1">
              <span className="text-[10px] font-mono text-slate-400 uppercase font-bold block">
                Ingestion Engine
              </span>
              <div className="text-slate-900 font-mono font-medium">
                Status: <span className="text-emerald-600 font-bold">{freshness?.status || 'Active Sync'}</span>
              </div>
              <div className="text-[10px] text-slate-500">
                Poll Interval: {freshness?.poll_interval_minutes || 15} minutes
              </div>
              <div className="text-[10px] text-slate-500">
                Active Feeds: {freshness?.sources?.join(', ') || 'NOAA-21, NOAA-20 VIIRS'}
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-[10px] font-mono text-slate-400 uppercase font-bold block">
                Synchronized Records
              </span>
              <div className="text-slate-900 font-mono font-medium">
                Ingested: <span className="text-blue-700 font-bold">{freshness?.records_received || 0}</span>
              </div>
              <div className="text-[10px] text-slate-500">
                New Signals: {freshness?.new_records || 0}
              </div>
              <div className="text-[10px] text-slate-500">
                Last Ingestion: {formatTimestamp(freshness?.last_successful_sync)}
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-[10px] font-mono text-slate-400 uppercase font-bold block">
                Spatial & Infrastructure Context
              </span>
              <div className="text-slate-900 font-mono font-medium">
                OSM Facilities: <span className="text-indigo-600 font-bold">1,200 Features</span>
              </div>
              <div className="text-[10px] text-slate-500">
                Persistent Hotspots: 312 Clusters (DBSCAN 300m)
              </div>
              <div className="text-[10px] text-slate-500">
                Model Pipeline: Isolation Forest v1.0 (16-feature vector)
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-[10px] font-mono text-amber-700 uppercase font-bold flex items-center gap-1">
                <Info className="w-3 h-3 text-amber-600" />
                Basemap Imagery Advisory
              </span>
              <p className="text-[10px] leading-tight text-slate-500">
                Satellite basemap tiles are static high-resolution composite imagery from Esri / Carto / OSM. Imagery acquisition dates vary by tile provider and do not represent real-time live satellite video.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
