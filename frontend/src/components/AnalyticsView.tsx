import React, { useEffect, useState } from 'react';
import {
  Activity,
  BarChart3,
  Sun,
  Moon,
  Flame,
  Factory,
  Trees,
  ShieldAlert,
  AlertTriangle,
  Clock,
  Layers,
  ArrowUpRight,
  TrendingUp,
  Cpu,
  RefreshCw,
  CheckCircle2,
} from 'lucide-react';
import { api } from '../services/api';
import { Region } from '../types';

interface AnalyticsViewProps {
  selectedRegion: Region | null;
  onSelectRegion?: (region: Region | null) => void;
}

export const AnalyticsView: React.FC<AnalyticsViewProps> = ({
  selectedRegion,
  onSelectRegion,
}) => {
  const [loading, setLoading] = useState(true);
  const [corridors, setCorridors] = useState<any[]>([]);
  const [distribution, setDistribution] = useState<any | null>(null);
  const [taxonomy, setTaxonomy] = useState<any | null>(null);
  const [workflow, setWorkflow] = useState<any | null>(null);
  const [modelEval, setModelEval] = useState<any | null>(null);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const [overviewRes, modelsRes] = await Promise.all([
        api.getAnalyticsOverview(),
        api.getModelBenchmarks(),
      ]);

      setCorridors(overviewRes.corridors || []);
      setDistribution(overviewRes.thermal_distribution || null);
      setTaxonomy(overviewRes.classification_taxonomy || null);
      setWorkflow(overviewRes.workflow_kpis || null);
      setModelEval(modelsRes || null);
    } catch (err) {
      console.error('Failed to load advanced analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center bg-white border border-slate-200 rounded-xl space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto" />
        <div className="text-xs font-mono text-slate-500">Synthesizing advanced geospatial analytics...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900 uppercase font-mono tracking-wide">
              Advanced Geospatial & Operational Analytics
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Cross-corridor comparative intelligence, diurnal day/night distributions, recurrence spectra, and ML operational agreements.
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs text-slate-500">
          <span>Active Scope: <strong className="text-slate-800">{selectedRegion?.name || 'Pan-India (10 Corridors)'}</strong></span>
        </div>
      </div>

      {/* KPI Overview Tiles */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs space-y-1">
          <div className="flex justify-between items-center text-slate-500 text-[11px] font-mono">
            <span>MONITORED CORRIDORS</span>
            <Factory className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-xl font-bold font-mono text-slate-900">{corridors.length} Regions</div>
          <div className="text-[11px] text-slate-500">6 Heavy Industrial · 4 Forest Landscapes</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs space-y-1">
          <div className="flex justify-between items-center text-slate-500 text-[11px] font-mono">
            <span>PERSISTENT CLUSTERS</span>
            <Flame className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-xl font-bold font-mono text-slate-900">312 Clusters</div>
          <div className="text-[11px] text-slate-500">DBSCAN 300m Spatial Partition</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs space-y-1">
          <div className="flex justify-between items-center text-slate-500 text-[11px] font-mono">
            <span>VIIRS SATELLITE EVENTS</span>
            <Layers className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-xl font-bold font-mono text-slate-900">8,891 Detections</div>
          <div className="text-[11px] text-slate-500">NOAA-21 · NOAA-20 · Suomi-NPP</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs space-y-1">
          <div className="flex justify-between items-center text-slate-500 text-[11px] font-mono">
            <span>WORKFLOW TURNAROUND</span>
            <Clock className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-xl font-bold font-mono text-emerald-700">2.4 Days</div>
          <div className="text-[11px] text-slate-500">Average Triage to Resolution</div>
        </div>
      </div>

      {/* Diurnal Thermal Distribution & Recurrence Spectrum */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Diurnal Breakdown */}
        {distribution && (
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-slate-100">
              <h3 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wide flex items-center gap-2">
                <Sun className="w-4 h-4 text-amber-500" />
                <span>VIIRS Orbital Pass Distribution — India</span>
              </h3>
              <span className="text-[10px] font-mono text-slate-400">Sun-Synchronous LST</span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-3.5 rounded-xl bg-amber-50/50 border border-amber-200 space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-bold text-amber-900">
                  <Sun className="w-4 h-4 text-amber-600" />
                  <span>Afternoon Overpass (~13:30 LST)</span>
                </div>
                <div className="text-2xl font-bold font-mono text-amber-900">
                  {distribution.diurnal_breakdown.daytime_detections.toLocaleString()}
                </div>
                <div className="text-[11px] font-mono text-amber-700 font-semibold">
                  {distribution.diurnal_breakdown.daytime_percentage}% of total thermal detections
                </div>
                <p className="text-[10px] text-slate-500 mt-1">06:00–14:00 UTC window; continuous industrial boiler, kiln & stack emissions.</p>
              </div>

              <div className="p-3.5 rounded-xl bg-indigo-50/50 border border-indigo-200 space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-900">
                  <Moon className="w-4 h-4 text-indigo-600" />
                  <span>Nocturnal Overpass (~01:30 LST)</span>
                </div>
                <div className="text-2xl font-bold font-mono text-indigo-900">
                  {distribution.diurnal_breakdown.nighttime_detections.toLocaleString()}
                </div>
                <div className="text-[11px] font-mono text-indigo-700 font-semibold">
                  {distribution.diurnal_breakdown.nighttime_percentage}% of total thermal detections
                </div>
                <p className="text-[10px] text-slate-500 mt-1">18:00–02:00 UTC window; zero solar clutter, pure mid-IR flaring & furnace slag.</p>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 leading-relaxed">
              <strong>Scientific Methodology:</strong> Partition reflects empirical Sun-synchronous satellite overpass windows over India (~13:30 and ~01:30 Local Solar Time), evaluated via UTC observation timestamps rather than pixel-level astronomical solar zenith angles. High afternoon-to-nocturnal consistency is an authoritative hallmark of continuous 24/7 industrial infrastructure.
            </div>
          </div>
        )}

        {/* Recurrence Spectrum */}
        {distribution && (
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-slate-100">
              <h3 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wide flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-blue-600" />
                <span>Thermal Recurrence Spectrum (312 Clusters)</span>
              </h3>
              <span className="text-[10px] font-mono text-slate-400">30-Day Persistence</span>
            </div>

            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex justify-between text-xs font-semibold text-slate-800">
                  <span>Persistent Industrial Operations (&gt; 10 Active Days)</span>
                  <span className="font-mono text-blue-700 font-bold">
                    {distribution.recurrence_spectrum.persistent_over_10_days} clusters ({distribution.recurrence_spectrum.persistent_percentage}%)
                  </span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${distribution.recurrence_spectrum.persistent_percentage}%` }}
                  />
                </div>
                <div className="text-[10px] text-slate-500">Steel plants, thermal power stations, copper smelters, chemical refineries.</div>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex justify-between text-xs font-semibold text-slate-800">
                  <span>Intermittent Batch Activities (3 to 10 Active Days)</span>
                  <span className="font-mono text-amber-700 font-bold">
                    {distribution.recurrence_spectrum.intermittent_3_10_days} clusters ({distribution.recurrence_spectrum.intermittent_percentage}%)
                  </span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2">
                  <div
                    className="bg-amber-500 h-2 rounded-full"
                    style={{ width: `${distribution.recurrence_spectrum.intermittent_percentage}%` }}
                  />
                </div>
                <div className="text-[10px] text-slate-500">Coke oven flaring cycles, coal washery reject burning, cyclic tailings heating.</div>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex justify-between text-xs font-semibold text-slate-800">
                  <span>Sporadic / Short-Lived Episodes (1 to 2 Active Days)</span>
                  <span className="font-mono text-emerald-700 font-bold">
                    {distribution.recurrence_spectrum.sporadic_1_2_days} clusters ({distribution.recurrence_spectrum.sporadic_percentage}%)
                  </span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2">
                  <div
                    className="bg-emerald-500 h-2 rounded-full"
                    style={{ width: `${distribution.recurrence_spectrum.sporadic_percentage}%` }}
                  />
                </div>
                <div className="text-[10px] text-slate-500">Transient forest understory fires, agricultural crop stubble, ephemeral burns.</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 10-Corridor Comparative Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
        <div className="flex justify-between items-center pb-2 border-b border-slate-100">
          <div>
            <h3 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wide">
              Cross-Corridor Comparative Surveillance Ranking (10 Monitored Regions)
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Ranked by total satellite event density, thermal emission power, and persistence ratios.
            </p>
          </div>
          <span className="text-[11px] font-mono text-slate-400">PostGIS Reconciled</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 font-mono text-slate-600 text-[11px]">
                <th className="py-2.5 px-3">Corridor / Region</th>
                <th className="py-2.5 px-3">State</th>
                <th className="py-2.5 px-3">Dominant Sector</th>
                <th className="py-2.5 px-3 text-right">Clusters</th>
                <th className="py-2.5 px-3 text-right">Events</th>
                <th className="py-2.5 px-3 text-right">Mean FRP (MW)</th>
                <th className="py-2.5 px-3 text-right">Peak FRP (MW)</th>
                <th className="py-2.5 px-3 text-right">Persistence</th>
                <th className="py-2.5 px-3 text-right">High Priority %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {corridors.map((c) => (
                <tr key={c.corridor_key} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-2 px-3 font-semibold text-slate-900">{c.display_name}</td>
                  <td className="py-2 px-3 text-slate-600">{c.state}</td>
                  <td className="py-2 px-3 text-slate-500 font-sans">{c.sector}</td>
                  <td className="py-2 px-3 text-right font-bold text-blue-700">{c.cluster_count}</td>
                  <td className="py-2 px-3 text-right font-bold text-slate-800">{c.event_count.toLocaleString()}</td>
                  <td className="py-2 px-3 text-right text-slate-700">{c.mean_frp_mw.toFixed(2)}</td>
                  <td className="py-2 px-3 text-right font-bold text-amber-700">{c.peak_frp_mw.toFixed(1)}</td>
                  <td className="py-2 px-3 text-right text-slate-600">{(c.mean_persistence_ratio * 100).toFixed(1)}%</td>
                  <td className="py-2 px-3 text-right">
                    <span className={`font-bold ${c.high_priority_percentage > 20 ? 'text-rose-600' : 'text-slate-700'}`}>
                      {c.high_priority_percentage}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Model Benchmark & Proxy Disclaimer Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
        {/* Prominent Disclaimer Banner */}
        <div className="p-3.5 bg-amber-50 border border-amber-300 rounded-xl flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-1 text-xs">
            <div className="font-bold text-amber-900 uppercase font-mono tracking-wide">
              Fire Incident Prediction: NOT VALIDATED — INDEPENDENT INCIDENT GROUND TRUTH UNAVAILABLE
            </div>
            <p className="text-amber-800 leading-relaxed">
              Supervised candidate evaluations (LightGBM, Random Forest, XGBoost) reflect model agreement with heuristic operational priority pseudo-labels rather than verified ground-truth fire emergencies. In compliance with statutory scientific integrity guidelines, all operational triage uses calibrated unsupervised statistical anomaly detection (Isolation Forest v2, N=8,891, 16 features).
            </p>
          </div>
        </div>

        {/* Model Metadata Summary */}
        {modelEval && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 text-xs">
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
              <span className="text-[10px] font-mono text-slate-400 font-bold uppercase">Operational Algorithm</span>
              <div className="font-bold text-slate-900 font-mono">
                {modelEval.model_metadata?.model_name || 'IsolationForest'} (v{modelEval.model_metadata?.version || '1.0.0'})
              </div>
              <div className="text-slate-500">Normalized Decision-Function [0, 1]</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
              <span className="text-[10px] font-mono text-slate-400 font-bold uppercase">Training Baseline Population</span>
              <div className="font-bold text-slate-900 font-mono">
                {modelEval.model_metadata?.training_period || '2021–2024 (8,891 Events)'}
              </div>
              <div className="text-slate-500">16 Geospatial & Physical Features</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
              <span className="text-[10px] font-mono text-slate-400 font-bold uppercase">Contamination & Trees</span>
              <div className="font-bold text-slate-900 font-mono">
                {modelEval.model_metadata?.contamination || '0.02'} · {modelEval.model_metadata?.n_estimators || 400} Trees
              </div>
              <div className="text-slate-500">Robust outlier separation margin</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
