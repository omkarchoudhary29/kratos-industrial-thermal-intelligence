import React from 'react';
import {
  X,
  Database,
  Satellite,
  ShieldCheck,
  Brain,
  Layers,
  Award,
  ExternalLink,
  Info,
} from 'lucide-react';

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AboutModal: React.FC<AboutModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div
        className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="about-modal-title"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-xs">
              <Info className="w-4 h-4" />
            </div>
            <div>
              <h2 id="about-modal-title" className="text-base font-bold text-slate-900 font-mono">
                KRATOS V3.1 — Platform Architecture & Data Provenance
              </h2>
              <p className="text-xs text-slate-500">
                Industrial Thermal Intelligence & Autonomous Geospatial Surveillance
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 rounded-lg transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="px-6 py-5 overflow-y-auto space-y-6 text-sm text-slate-700 leading-relaxed">
          {/* Executive Overview */}
          <section className="bg-blue-50/60 border border-blue-100 rounded-xl p-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-blue-900 font-mono mb-1.5 flex items-center gap-1.5">
              <Award className="w-4 h-4 text-blue-600" />
              Executive Purpose & Mission
            </h3>
            <p className="text-xs text-blue-950">
              KRATOS V3.1 is an enterprise-grade geospatial surveillance platform designed for 
              continuous monitoring, characterization, and risk evaluation of high-temperature thermal 
              anomalies across industrial corridors, energy facilities, and forest frontiers.
            </p>
          </section>

          {/* Data Provenance & Baseline */}
          <section className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 font-mono flex items-center gap-1.5">
              <Database className="w-4 h-4 text-emerald-600" />
              Empirical Baseline & Data Provenance
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-900 mb-1">
                  <Satellite className="w-3.5 h-3.5 text-blue-600" />
                  Satellite Remote Sensing
                </div>
                <p className="text-xs text-slate-600">
                  NASA FIRMS VIIRS (S-NPP, NOAA-20, NOAA-21) active fire products at 375m spatial 
                  resolution with day/night orbital passes.
                </p>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-900 mb-1">
                  <Layers className="w-3.5 h-3.5 text-emerald-600" />
                  Historical Baseline (2021–2025)
                </div>
                <p className="text-xs text-slate-600">
                  <strong>8,891</strong> fused thermal events spanning 5 years across 6 industrial corridors 
                  and 4 forest fire landscapes.
                </p>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-900 mb-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-purple-600" />
                  Industrial Infrastructure
                </div>
                <p className="text-xs text-slate-600">
                  <strong>2,423</strong> OpenStreetMap (OSM) mapped industrial/energy facilities and 
                  <strong> 312</strong> corroborated persistent thermal sources.
                </p>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-900 mb-1">
                  <Brain className="w-3.5 h-3.5 text-amber-600" />
                  Dual-Branch Anomaly Intelligence
                </div>
                <p className="text-xs text-slate-600">
                  Unsupervised Isolation Forest ML model combined with deterministic physical rules 
                  (FRP, temperature, recurrence, landcover).
                </p>
              </div>
            </div>
          </section>

          {/* Operational Priority Scale */}
          <section className="space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 font-mono">
              Operational Priority Classification
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="border border-red-200 bg-red-50/50 rounded-lg p-2 text-center">
                <span className="text-[10px] font-bold text-red-700 uppercase font-mono block">CRITICAL</span>
                <span className="text-[11px] text-slate-600">Score &ge; 75 &bull; Urgent Dispatch</span>
              </div>
              <div className="border border-amber-200 bg-amber-50/50 rounded-lg p-2 text-center">
                <span className="text-[10px] font-bold text-amber-700 uppercase font-mono block">HIGH</span>
                <span className="text-[11px] text-slate-600">Score 50–74 &bull; Active Investigation</span>
              </div>
              <div className="border border-yellow-200 bg-yellow-50/50 rounded-lg p-2 text-center">
                <span className="text-[10px] font-bold text-yellow-700 uppercase font-mono block">MEDIUM</span>
                <span className="text-[11px] text-slate-600">Score 30–49 &bull; Scheduled Review</span>
              </div>
              <div className="border border-slate-200 bg-slate-50 rounded-lg p-2 text-center">
                <span className="text-[10px] font-bold text-slate-700 uppercase font-mono block">LOW</span>
                <span className="text-[11px] text-slate-600">Score &lt; 30 &bull; Baseline Telemetry</span>
              </div>
            </div>
          </section>

          {/* Public Recruiter & Demo Information */}
          <section className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 font-mono">
              Public Demonstration & Reviewer Access
            </h3>
            <p className="text-xs text-slate-600">
              For evaluation by technical reviewers and recruiters, the application provides ready-to-use reviewer credentials:
            </p>
            <div className="bg-white border border-slate-200 rounded-lg p-2.5 font-mono text-xs text-slate-800 space-y-1">
              <div><span className="text-slate-400">Reviewer User:</span> demo_reviewer</div>
              <div><span className="text-slate-400">Reviewer Pass:</span> KratosDemo2026!</div>
              <div><span className="text-slate-400">Role:</span> Standard Operational Reviewer (Read-Only Safety Bounds)</div>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>KRATOS V3.1 Release Candidate &bull; Production Hardened</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
