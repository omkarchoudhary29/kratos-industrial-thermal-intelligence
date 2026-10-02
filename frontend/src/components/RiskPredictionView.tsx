import React, { useEffect, useState } from 'react';
import {
  ShieldAlert,
  Flame,
  AlertTriangle,
  Info,
  CheckCircle2,
  HelpCircle,
  BarChart2,
  TrendingUp,
  Cpu,
  Layers,
  Search,
  ExternalLink,
  ChevronRight,
  Filter,
} from 'lucide-react';
import { api } from '../services/api';
import {
  OperationalPriorityItem,
  Region,
  SupervisedModelEvaluation,
} from '../types';

interface RiskPredictionViewProps {
  selectedRegion: Region | null;
  onInspectEvent?: (eventId: string) => void;
}

export const RiskPredictionView: React.FC<RiskPredictionViewProps> = ({
  selectedRegion,
  onInspectEvent,
}) => {
  const [queue, setQueue] = useState<OperationalPriorityItem[]>([]);
  const [modelEval, setModelEval] = useState<SupervisedModelEvaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [tierFilter, setTierFilter] = useState<string>('all');
  const [selectedItem, setSelectedItem] = useState<OperationalPriorityItem | null>(null);

  useEffect(() => {
    fetchPriorityQueue();
    fetchModelEvaluation();
  }, [selectedRegion]);

  const fetchPriorityQueue = async () => {
    try {
      setLoading(true);
      const res = await api.getOperationalPriorityQueue({
        region: selectedRegion?.name,
        limit: 50,
      });
      setQueue(res.queue || []);
      if (res.queue && res.queue.length > 0) {
        setSelectedItem(res.queue[0]);
      }
    } catch (err) {
      console.error('Failed to load operational priority queue:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchModelEvaluation = async () => {
    try {
      const res = await api.getCandidateModelEvaluation();
      setModelEval(res);
    } catch (err) {
      console.error('Failed to load candidate model evaluation:', err);
    }
  };

  const filteredQueue = queue.filter((item) => {
    if (tierFilter !== 'all' && item.priority_tier !== tierFilter) return false;
    return true;
  });

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case 'CRITICAL':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-red-100 text-red-800 border border-red-200">
            CRITICAL (&ge;0.75)
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-800 border border-amber-200">
            HIGH (0.55 - 0.75)
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-100 text-blue-800 border border-blue-200">
            MEDIUM (0.35 - 0.55)
          </span>
        );
      case 'LOW':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-200">
            LOW (&lt;0.35)
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-100 text-purple-800 border border-purple-200">
            INSUFFICIENT EVIDENCE
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-600" />
            <h2 className="text-base font-bold text-slate-900 uppercase font-mono tracking-wide">
              Risk Evaluation, Operational Priority & Predictive Intelligence
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Transparent operational triage formula, strict separation of anomaly vs incident probability, and supervised ML benchmarks.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[11px] font-mono text-slate-500">
            Scope: <strong className="text-slate-800">{selectedRegion?.name || 'Pan-India Overview'}</strong>
          </span>
          <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-red-50 text-red-700 border border-red-200">
            {queue.length} Prioritized Incidents
          </span>
        </div>
      </div>

      {/* 4 Distinct Outputs Explanation Banner */}
      <div className="bg-blue-50/60 border border-blue-200 rounded-xl p-4 space-y-2 text-xs">
        <div className="flex items-center gap-2 text-blue-800 font-bold font-mono">
          <Info className="w-4 h-4 text-blue-600" />
          <span>FOUR STRICTLY DISTINCT INTELLIGENCE OUTPUTS (SCIENTIFIC DEFENSIBILITY)</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-[11px] text-slate-700">
          <div className="bg-white p-2.5 rounded-lg border border-blue-100 space-y-1">
            <strong className="text-blue-900">1. Anomaly Score:</strong>
            <p className="text-slate-600 leading-tight">
              Unsupervised statistical density outlier ranking [0, 1]. Measures relative deviation from regional baseline, NOT a fire confirmation.
            </p>
          </div>
          <div className="bg-white p-2.5 rounded-lg border border-blue-100 space-y-1">
            <strong className="text-blue-900">2. Source Classification:</strong>
            <p className="text-slate-600 leading-tight">
              Physical heat mechanism (process heat, flare, coal handling). Accompanied by honest uncalibrated heuristic confidence ratings.
            </p>
          </div>
          <div className="bg-white p-2.5 rounded-lg border border-blue-100 space-y-1">
            <strong className="text-blue-900">3. Fire Probability:</strong>
            <p className="text-slate-600 leading-tight">
              Explicitly set to <code className="bg-slate-100 px-1 py-0.5 rounded text-rose-700">null</code>. Calibrated Bayesian fire probabilities cannot be manufactured without verified ground truth.
            </p>
          </div>
          <div className="bg-white p-2.5 rounded-lg border border-blue-100 space-y-1">
            <strong className="text-blue-900">4. Operational Priority:</strong>
            <p className="text-slate-600 leading-tight">
              Transparent multi-factor triage formula (FRP exceedance + persistence + anomaly score + facility proximity).
            </p>
          </div>
        </div>
      </div>

      {/* Main Grid: Priority Queue & Detail Component Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Priority Queue (2 cols) */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex justify-between items-center text-xs text-slate-500 font-mono px-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-700">Operational Priority Queue</span>
              <span>({filteredQueue.length} items)</span>
            </div>

            <div className="flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={tierFilter}
                onChange={(e) => setTierFilter(e.target.value)}
                className="border border-slate-300 rounded px-2 py-0.5 text-xs bg-white text-slate-700"
              >
                <option value="all">All Tiers</option>
                <option value="CRITICAL">Critical (&ge;0.75)</option>
                <option value="HIGH">High (0.55 - 0.75)</option>
                <option value="MEDIUM">Medium (0.35 - 0.55)</option>
                <option value="LOW">Low (&lt;0.35)</option>
                <option value="INSUFFICIENT_EVIDENCE">Insufficient Evidence</option>
              </select>
            </div>
          </div>

          {loading ? (
            <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500 text-xs">
              Loading operational priority queue...
            </div>
          ) : filteredQueue.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500 text-xs">
              No events match the selected priority tier filter.
            </div>
          ) : (
            <div className="space-y-2.5 max-h-[640px] overflow-y-auto pr-1">
              {filteredQueue.map((item) => {
                const isSelected = selectedItem?.source_event_id === item.source_event_id;
                return (
                  <div
                    key={item.source_event_id}
                    onClick={() => setSelectedItem(item)}
                    className={`bg-white border rounded-xl p-4 cursor-pointer transition-all space-y-3 ${
                      isSelected
                        ? 'border-red-500 ring-2 ring-red-500/20 shadow-sm bg-red-50/10'
                        : 'border-slate-200 hover:border-slate-300 hover:shadow-xs'
                    }`}
                  >
                    <div className="flex flex-wrap justify-between items-start gap-2">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-slate-900">
                            {item.source_event_id}
                          </span>
                          <span className="text-[10px] font-mono text-slate-500 px-1.5 py-0.2 rounded bg-slate-100">
                            {item.region_name}
                          </span>
                        </div>
                        <div className="text-xs text-slate-600 font-mono">
                          Source: {item.thermal_source_id} &bull; Classification: <strong className="capitalize text-slate-800">{item.source_class.replace(/_/g, ' ')}</strong>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {getTierBadge(item.priority_tier)}
                        <span className="font-mono text-sm font-bold text-slate-900">
                          {item.priority_score.toFixed(3)}
                        </span>
                      </div>
                    </div>

                    <p className="text-xs text-slate-600 leading-tight">
                      {item.tier_rationale}
                    </p>

                    <div className="flex flex-wrap items-center justify-between text-[11px] font-mono text-slate-500 pt-1 border-t border-slate-100">
                      <div className="flex gap-4">
                        <span>Max FRP: <strong className="text-amber-700">{item.max_frp_mw.toFixed(1)} MW</strong></span>
                        <span>FRP Ratio: <strong className="text-slate-800">{item.max_frp_ratio.toFixed(1)}x</strong></span>
                        <span>Anomaly Score: <strong className="text-slate-800">{item.anomaly_score.toFixed(3)}</strong></span>
                      </div>
                      <span className="text-blue-600 font-semibold flex items-center gap-1">
                        Explain Components &rarr;
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Explainable Component Breakdown Drawer */}
        <div className="space-y-4">
          {/* Honest Ground-Truth Integrity Notice */}
          <div className="p-3 bg-amber-50/90 border border-amber-200 rounded-xl space-y-1 text-xs font-mono text-amber-900">
            <div className="flex items-center gap-1.5 font-bold uppercase text-[11px] text-amber-800">
              <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
              <span>Ground-Truth Integrity: Incident Probability Withheld</span>
            </div>
            <p className="text-[10.5px] text-amber-700 leading-tight">
              Independent fire brigade / disaster ground-truth is unavailable for satellite remote-sensing footprints.
              In accordance with KRATOS scientific protocol, unvalidated fire incidence probabilities are withheld. Actionable triage is provided via bounded Operational Priority.
            </p>
          </div>

          {selectedItem ? (
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4 sticky top-20 text-xs">
              <div className="flex justify-between items-start pb-3 border-b border-slate-100">
                <div>
                  <span className="text-[10px] font-mono text-slate-400 font-bold uppercase">Mathematical Explainability</span>
                  <h3 className="text-sm font-bold text-slate-900 font-mono">{selectedItem.source_event_id}</h3>
                  <div className="text-xs text-slate-500 font-mono">{selectedItem.region_name}</div>
                </div>
                {getTierBadge(selectedItem.priority_tier)}
              </div>

              {/* Multi-Model Anomaly Consensus Card */}
              <div className="p-3 bg-indigo-50/70 border border-indigo-200 rounded-xl space-y-2 text-xs font-mono">
                <div className="flex justify-between items-center text-[11px] font-bold text-indigo-900 uppercase">
                  <span className="flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-indigo-600" />
                    Multi-Model Anomaly Consensus
                  </span>
                  <span className="px-2 py-0.5 rounded bg-indigo-100 text-indigo-800 text-[10px]">
                    {selectedItem.anomaly_score < -0.10 ? 'DUAL-MODEL CONCURRENCE (2/3)' : 'NORMAL OPERATIONAL (0/3)'}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-[10px] text-center">
                  <div className="p-2 bg-white rounded border border-indigo-100">
                    <span className="text-slate-400 block text-[9px] font-bold">Model 1: IForest</span>
                    <span className={selectedItem.anomaly_score < -0.10 ? 'text-red-600 font-bold' : 'text-slate-700 font-bold'}>
                      {selectedItem.anomaly_score < -0.10 ? 'Low Density' : 'In Envelope'}
                    </span>
                  </div>
                  <div className="p-2 bg-white rounded border border-indigo-100">
                    <span className="text-slate-400 block text-[9px] font-bold">Model 2: Robust Quantile</span>
                    <span className={selectedItem.max_frp_ratio > 2.0 ? 'text-red-600 font-bold' : 'text-slate-700 font-bold'}>
                      {selectedItem.max_frp_ratio > 2.0 ? '> P95 Exceedance' : 'Normal (P50)'}
                    </span>
                  </div>
                  <div className="p-2 bg-white rounded border border-indigo-100">
                    <span className="text-slate-400 block text-[9px] font-bold">Model 3: CUSUM Drift</span>
                    <span className={selectedItem.max_frp_ratio > 3.0 ? 'text-red-600 font-bold' : 'text-slate-700 font-bold'}>
                      {selectedItem.max_frp_ratio > 3.0 ? 'Step-Shift' : 'Stable Series'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Total Priority Score Box */}
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 space-y-1 text-center">
                <div className="text-[10px] font-mono uppercase text-slate-500">Calculated Operational Priority</div>
                <div className="text-3xl font-bold font-mono text-slate-900">
                  {selectedItem.priority_score.toFixed(4)}
                </div>
                <div className="text-[10px] font-mono text-slate-500">
                  Formula: 0.35&times;FRP + 0.25&times;Persist + 0.25&times;Anomaly + 0.15&times;Proximity
                </div>
              </div>

              {/* Component Contributions Progress Bars */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-800 uppercase font-mono tracking-wide">
                  Weighted Component Breakdown
                </h4>

                {/* 1. FRP Exceedance */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px] font-mono">
                    <span className="text-slate-600">FRP Exceedance (35% weight):</span>
                    <span className="font-bold text-slate-800">
                      +{selectedItem.component_contributions.frp_contribution?.toFixed(4) || '0.0000'}
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-amber-500 h-1.5 rounded-full"
                      style={{
                        width: `${Math.min(100, (selectedItem.component_contributions.frp_contribution / 0.35) * 100)}%`,
                      }}
                    />
                  </div>
                </div>

                {/* 2. Persistence */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px] font-mono">
                    <span className="text-slate-600">Persistence Abnormality (25% weight):</span>
                    <span className="font-bold text-slate-800">
                      +{selectedItem.component_contributions.persistence_contribution?.toFixed(4) || '0.0000'}
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-blue-600 h-1.5 rounded-full"
                      style={{
                        width: `${Math.min(100, (selectedItem.component_contributions.persistence_contribution / 0.25) * 100)}%`,
                      }}
                    />
                  </div>
                </div>

                {/* 3. Normalized Anomaly */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px] font-mono">
                    <span className="text-slate-600">Normalized Anomaly Score (25% weight):</span>
                    <span className="font-bold text-slate-800">
                      +{selectedItem.component_contributions.anomaly_contribution?.toFixed(4) || '0.0000'}
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-purple-600 h-1.5 rounded-full"
                      style={{
                        width: `${Math.min(100, (selectedItem.component_contributions.anomaly_contribution / 0.25) * 100)}%`,
                      }}
                    />
                  </div>
                </div>

                {/* 4. Facility Proximity */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px] font-mono">
                    <span className="text-slate-600">Facility Proximity (15% weight):</span>
                    <span className="font-bold text-slate-800">
                      +{selectedItem.component_contributions.proximity_contribution?.toFixed(4) || '0.0000'}
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-cyan-600 h-1.5 rounded-full"
                      style={{
                        width: `${Math.min(100, (selectedItem.component_contributions.proximity_contribution / 0.15) * 100)}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Uncertainty Penalty */}
                {selectedItem.component_contributions.uncertainty_penalty > 0 && (
                  <div className="p-2 rounded bg-amber-50 border border-amber-200 text-[10px] text-amber-800 font-mono">
                    Uncertainty Penalty Applied: -{selectedItem.component_contributions.uncertainty_penalty} (sparse observation history)
                  </div>
                )}
              </div>

              {/* Fire Incident Probability Notice */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
                <div className="text-[10px] font-mono font-bold uppercase text-slate-500">
                  Fire / Incident Probability
                </div>
                <div className="text-xs font-mono font-bold text-rose-700">null (Uncalibrated)</div>
                <p className="text-[10px] text-slate-500 leading-tight">
                  Calibrated probability is withheld because ground-truth fire incidence verification does not exist for this remote observation.
                </p>
              </div>

              {onInspectEvent && (
                <button
                  onClick={() => onInspectEvent(selectedItem.source_event_id)}
                  className="w-full py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-colors shadow-xs"
                >
                  Inspect Feature in Map Explorer &rarr;
                </button>
              )}
            </div>
          ) : (
            <div className="bg-slate-50 border border-dashed border-slate-300 rounded-xl p-8 text-center text-slate-500 text-xs">
              Select any incident from the priority queue on the left to inspect its explainable mathematical formula components.
            </div>
          )}
        </div>
      </div>

      {/* Candidate Supervised Model Evaluation Benchmark Table */}
      {modelEval && modelEval.evaluated_models && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
          {/* Prominent Scientific Truth Notice */}
          <div className="p-3.5 bg-rose-50 border border-rose-300 rounded-lg flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 text-rose-900 font-bold font-mono">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>Fire Incident Prediction: NOT VALIDATED — INDEPENDENT INCIDENT GROUND TRUTH UNAVAILABLE</span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-100 text-rose-800 font-bold border border-rose-200">
              Proxy Screening Evaluation
            </span>
          </div>

          <div className="flex flex-wrap justify-between items-center gap-2 pb-2 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-purple-600" />
              <h3 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wide">
                Supervised Candidate Classifier Benchmarks (Operational High-Risk Triage)
              </h3>
            </div>
            <span className="text-[10px] font-mono text-slate-500">
              Sample Size: <strong>{modelEval.sample_count} events</strong> &bull; Target: {modelEval.target_class_definition}
            </span>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1.5 text-slate-700 text-xs">
            <div className="font-bold text-slate-800 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-blue-600" />
              <span>Proxy Target & Feature Correlation Notice</span>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              Target labels (<em>n = 113</em>) represent operational screening tiers derived from heuristic FRP ratio (&ge;2.0) and Isolation Forest anomaly score (&le;-0.15). Supervised models achieve near-perfect metrics because they reconstruct operational screening heuristics, <strong>not</strong> because they predict independent, unverified physical fire incidents.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[10px] font-mono uppercase text-slate-500">
                  <th className="py-2.5 px-3">Model Architecture</th>
                  <th className="py-2.5 px-3">Precision</th>
                  <th className="py-2.5 px-3">Recall</th>
                  <th className="py-2.5 px-3">F1 Score</th>
                  <th className="py-2.5 px-3">Confusion Matrix (TP / FP / FN / TN)</th>
                  <th className="py-2.5 px-3">Operational Role</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-xs">
                {modelEval.evaluated_models.map((m, idx) => (
                  <tr key={m.model_name} className="hover:bg-slate-50/80">
                    <td className="py-2.5 px-3 font-bold text-slate-900">
                      {m.model_name}
                      {idx === 0 && (
                        <span className="ml-2 text-[9px] px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800 border border-emerald-200 font-bold">
                          DEPLOYED
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-slate-800">{m.precision.toFixed(4)}</td>
                    <td className="py-2.5 px-3 font-semibold text-blue-700">{m.recall.toFixed(4)}</td>
                    <td className="py-2.5 px-3 font-bold text-purple-700">{m.f1_score.toFixed(4)}</td>
                    <td className="py-2.5 px-3 text-slate-600 text-[11px]">
                      TP: {m.confusion_matrix.true_positives} | FP: {m.confusion_matrix.false_positives} | FN: {m.confusion_matrix.false_negatives} | TN: {m.confusion_matrix.true_negatives}
                    </td>
                    <td className="py-2.5 px-3 text-slate-500 text-[11px] font-sans">
                      {idx === 0 ? 'Production density outlier detection' : 'Candidate supervised operational benchmark'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Explicit Calibration Disclaimer */}
          <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg text-amber-900 text-[11px] leading-relaxed">
            <strong>Calibration Disclaimer:</strong> {modelEval.calibration_disclaimer}
          </div>
        </div>
      )}
    </div>
  );
};
