import React, { useState, useEffect } from 'react';
import {
  FileText,
  X,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Printer,
  Copy,
  Check,
  RefreshCw,
  Download,
  FileSpreadsheet,
  BookmarkPlus,
  Layers,
  MapPin,
  Crosshair,
} from 'lucide-react';
import { Region, InvestigationReportData, ReportScope } from '../types';
import { useSelectedFeature } from '../context/SelectedFeatureContext';
import { api } from '../services/api';

interface InvestigationReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedRegion: Region | null;
  initialScope?: ReportScope;
  initialFeatureType?: string;
  initialFeatureId?: string;
  onCreateFollowUp?: (report: InvestigationReportData) => void;
}

export const InvestigationReportModal: React.FC<InvestigationReportModalProps> = ({
  isOpen,
  onClose,
  selectedRegion,
  initialScope,
  initialFeatureType,
  initialFeatureId,
  onCreateFollowUp,
}) => {
  const { selectedFeature } = useSelectedFeature();

  const [scope, setScope] = useState<ReportScope>(
    initialScope || (initialFeatureId || selectedFeature ? 'feature' : 'region')
  );
  const [report, setReport] = useState<InvestigationReportData | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Sync scope when props change
  useEffect(() => {
    if (initialScope) {
      setScope(initialScope);
    } else if (initialFeatureId || selectedFeature) {
      setScope('feature');
    }
  }, [initialScope, initialFeatureId, selectedFeature]);

  // Generate or regenerate report
  const handleGenerate = async (targetScope = scope) => {
    setIsGenerating(true);
    setError(null);
    try {
      const featType = initialFeatureType || selectedFeature?.type || 'cluster';
      const featId = initialFeatureId || selectedFeature?.id || 'bastar_source_0';

      const payload: any = {
        scope: targetScope,
        region_id: selectedRegion?.id,
        region_name: selectedRegion?.name || 'Bastar Woodlands',
      };

      if (targetScope === 'feature') {
        payload.feature_type = featType;
        payload.feature_id = featId;
      } else if (targetScope === 'viewport') {
        payload.bounds = {
          west: 80.0,
          south: 18.0,
          east: 84.0,
          north: 22.0,
        };
      }

      const res = await api.generateInvestigationReport(payload);
      setReport(res);
    } catch (err: any) {
      console.error('Failed to generate investigation report:', err);
      setError(err.message || 'Failed to compile report.');
    } finally {
      setIsGenerating(false);
    }
  };

  // Generate on first open if no report is loaded
  useEffect(() => {
    if (isOpen && !report && !isGenerating) {
      handleGenerate(scope);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleCopy = () => {
    const text = document.getElementById('investigation-report-body')?.innerText || '';
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadPdf = () => {
    if (!report?.report_key) return;
    const url = api.getReportPdfDownloadUrl(report.report_key);
    window.open(url, '_blank');
  };

  const handleDownloadCsv = () => {
    if (!report?.report_key) return;
    const url = api.getReportCsvDownloadUrl(report.report_key);
    window.open(url, '_blank');
  };

  const sections = report?.sections;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/85 backdrop-blur-md animate-fade-in">
      <div className="bg-[#0D131F] border border-[#2A374D] w-full max-w-5xl rounded-xl shadow-2xl flex flex-col max-h-[92vh] overflow-hidden text-[#E2E8F0]">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-[#1E293B] flex items-center justify-between bg-[#070A10]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#0F172A] border border-[#F59E0B]/50 flex items-center justify-center text-[#F59E0B]">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-white uppercase font-mono tracking-wider">
                  Area Monitoring & Thermal Activity Report
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#1E293B] text-[#94A3B8] border border-[#334155]">
                  AI-assisted analysis
                </span>
              </div>
              <span className="text-[11px] text-[#94A3B8] font-mono">
                Evidence-Grounded Intelligence · {report?.region_name || selectedRegion?.name || 'National Overview'}
              </span>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center gap-2">
            {report && (
              <>
                <button
                  onClick={handleDownloadPdf}
                  className="px-2.5 py-1.5 rounded bg-[#1E293B] hover:bg-[#2A374D] border border-[#334155] text-xs font-mono text-white flex items-center gap-1.5 transition-colors"
                  title="Download Publication PDF"
                >
                  <Download className="w-3.5 h-3.5 text-[#F59E0B]" />
                  <span>Download PDF</span>
                </button>

                <button
                  onClick={handleDownloadCsv}
                  className="px-2.5 py-1.5 rounded bg-[#1E293B] hover:bg-[#2A374D] border border-[#334155] text-xs font-mono text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
                  title="Export Raw Evidence CSV"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-blue-400" />
                  <span>Export CSV</span>
                </button>

                {onCreateFollowUp && (
                  <button
                    onClick={() => onCreateFollowUp(report)}
                    className="px-2.5 py-1.5 rounded bg-[#1E293B] hover:bg-[#2A374D] border border-[#F59E0B]/50 text-xs font-mono text-[#F59E0B] flex items-center gap-1.5 transition-colors"
                    title="Create Follow-up Task"
                  >
                    <BookmarkPlus className="w-3.5 h-3.5" />
                    <span>Create Follow-up</span>
                  </button>
                )}

                <button
                  onClick={handleCopy}
                  className="p-1.5 rounded hover:bg-[#1E293B] text-[#94A3B8] hover:text-white transition-colors"
                  title="Copy text"
                >
                  {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>

                <button
                  onClick={() => window.print()}
                  className="p-1.5 rounded hover:bg-[#1E293B] text-[#94A3B8] hover:text-white transition-colors"
                  title="Print Report"
                >
                  <Printer className="w-4 h-4" />
                </button>
              </>
            )}

            <button
              onClick={onClose}
              className="p-1.5 rounded hover:bg-[#1E293B] text-[#94A3B8] hover:text-white transition-colors ml-1"
              title="Close modal"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Scope Selector Ribbon */}
        <div className="px-6 py-2.5 bg-[#0F172A] border-b border-[#1E293B] flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-1">
            <span className="text-[11px] font-mono text-[#64748B] uppercase mr-2 font-semibold">Scope:</span>
            
            <button
              onClick={() => {
                setScope('region');
                handleGenerate('region');
              }}
              className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
                scope === 'region'
                  ? 'bg-[#1E293B] text-[#F59E0B] border border-[#F59E0B]/50 font-bold'
                  : 'text-[#94A3B8] hover:text-white'
              }`}
            >
              Full Region Report
            </button>

            <button
              onClick={() => {
                setScope('viewport');
                handleGenerate('viewport');
              }}
              className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
                scope === 'viewport'
                  ? 'bg-[#1E293B] text-[#F59E0B] border border-[#F59E0B]/50 font-bold'
                  : 'text-[#94A3B8] hover:text-white'
              }`}
            >
              Current Map Area
            </button>

            <button
              onClick={() => {
                setScope('feature');
                handleGenerate('feature');
              }}
              className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
                scope === 'feature'
                  ? 'bg-[#1E293B] text-[#F59E0B] border border-[#F59E0B]/50 font-bold'
                  : 'text-[#94A3B8] hover:text-white'
              }`}
            >
              Selected Thermal Feature
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleGenerate(scope)}
              disabled={isGenerating}
              className="px-3 py-1 rounded bg-[#121927] hover:bg-[#182235] border border-[#334155] hover:border-[#F59E0B] text-xs font-mono text-[#E2E8F0] flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-[#F59E0B] ${isGenerating ? 'animate-spin' : ''}`} />
              <span>{isGenerating ? 'Compiling Evidence...' : 'Regenerate'}</span>
            </button>
          </div>
        </div>

        {/* Report Content Body */}
        <div id="investigation-report-body" className="p-6 overflow-y-auto space-y-6 text-xs text-[#CBD5E1] leading-relaxed">
          {isGenerating ? (
            <div className="py-20 text-center space-y-3">
              <RefreshCw className="w-8 h-8 text-[#F59E0B] animate-spin mx-auto" />
              <p className="font-mono text-sm text-white">Compiling deterministic satellite telemetry & evidence...</p>
              <p className="text-xs text-[#64748B] max-w-md mx-auto">
                Querying PostgreSQL PostGIS spatial tables, metric DBSCAN clusters, and OpenStreetMap infrastructure layers.
              </p>
            </div>
          ) : error ? (
            <div className="p-6 bg-red-950/20 border border-red-800/50 rounded-lg text-center space-y-2">
              <AlertTriangle className="w-6 h-6 text-red-400 mx-auto" />
              <p className="text-sm font-semibold text-white">Report Generation Error</p>
              <p className="text-xs text-red-300 font-mono">{error}</p>
            </div>
          ) : report ? (
            <>
              {/* Report Identification & Metadata */}
              <div className="p-4 rounded-lg bg-[#070A10] border border-[#1E293B] space-y-2 font-mono text-[11px]">
                <div className="flex flex-wrap items-center justify-between border-b border-[#1E293B] pb-2 text-[#94A3B8]">
                  <span>Report ID: <strong className="text-white">{report.report_key}</strong></span>
                  <span>Scope: <strong className="text-[#F59E0B] uppercase">{report.scope}</strong></span>
                  <span>Region: <strong className="text-white">{report.region_name}</strong></span>
                  <span>Generated: <strong className="text-white">{report.created_at ? new Date(report.created_at).toUTCString() : 'Active'}</strong></span>
                </div>
                <div className="text-[10px] text-[#64748B] flex flex-wrap gap-4 pt-1">
                  <span>Author: {report.creator_name || 'Operational Intelligence Analyst'}</span>
                  <span>Telemetry: NASA FIRMS VIIRS NOAA-20 / NOAA-21 NRT</span>
                  <span>Status: Deterministically Verified</span>
                </div>
              </div>

              {/* 1. Executive Summary */}
              <div className="p-4 rounded-lg bg-[#121927] border border-[#F59E0B]/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-[#F59E0B] font-bold">
                    1. Executive Summary
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                    Observation Validated
                  </span>
                </div>
                <p className="text-white text-xs leading-normal">
                  {sections?.executive_summary || report.summary}
                </p>
              </div>

              {/* 2. Sensor Provenance & Monitoring Coverage */}
              {sections?.monitoring_coverage && (
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-white uppercase font-mono tracking-wider">
                    2. Monitoring Coverage & Sensor Provenance
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono text-[11px]">
                    <div className="p-3 bg-[#070A10] rounded border border-[#1E293B] space-y-1">
                      <span className="text-[#64748B] text-[10px] uppercase block">Primary Satellite Feeds</span>
                      <span className="text-white font-semibold">{sections.monitoring_coverage.satellites_evaluated}</span>
                      <span className="text-[#94A3B8] block text-[10px]">Nominal Resolution: {sections.monitoring_coverage.spatial_resolution}</span>
                    </div>
                    <div className="p-3 bg-[#070A10] rounded border border-[#1E293B] space-y-1">
                      <span className="text-[#64748B] text-[10px] uppercase block">Spatial Clustering & Upstream Latency</span>
                      <span className="text-white font-semibold">{sections.monitoring_coverage.spatial_clustering_method}</span>
                      <span className="text-emerald-400 block text-[10px]">Latency: {sections.monitoring_coverage.upstream_latency}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* 3. Priority Thermal Signals */}
              {sections?.priority_signals && sections.priority_signals.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-white uppercase font-mono tracking-wider flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-[#F59E0B]" />
                    3. Priority Thermal Signals & Footprint Metrics
                  </h3>
                  <div className="overflow-x-auto rounded border border-[#1E293B]">
                    <table className="w-full text-left font-mono text-[11px]">
                      <thead className="bg-[#070A10] text-[#94A3B8] border-b border-[#1E293B]">
                        <tr>
                          <th className="py-2 px-3">Cluster ID</th>
                          <th className="py-2 px-3">Location</th>
                          <th className="py-2 px-3">Hits</th>
                          <th className="py-2 px-3">Mean FRP</th>
                          <th className="py-2 px-3">Max FRP</th>
                          <th className="py-2 px-3">Classification</th>
                          <th className="py-2 px-3">Nearest Facility</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#1E293B] bg-[#0D131F]">
                        {sections.priority_signals.map((sig, idx) => (
                          <tr key={idx} className="hover:bg-[#121927]">
                            <td className="py-2 px-3 font-semibold text-white">{sig.id}</td>
                            <td className="py-2 px-3 text-[#94A3B8]">{sig.coordinates}</td>
                            <td className="py-2 px-3 text-white">{sig.detection_count || 1}</td>
                            <td className="py-2 px-3 text-[#F59E0B] font-semibold">{sig.mean_frp}</td>
                            <td className="py-2 px-3 text-red-400 font-semibold">{sig.max_frp}</td>
                            <td className="py-2 px-3">
                              <span className="px-1.5 py-0.5 rounded text-[10px] bg-[#1E293B] text-[#E2E8F0] border border-[#334155]">
                                {sig.classification}
                              </span>
                            </td>
                            <td className="py-2 px-3 text-[#CBD5E1] truncate max-w-[160px]">{sig.nearest_facility}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* 4. Infrastructure & Facility Correlation */}
              {sections?.facility_correlation && (
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-white uppercase font-mono tracking-wider">
                    4. Infrastructure & Facility Correlation
                  </h3>
                  <div className="p-3.5 bg-[#070A10] rounded border border-[#1E293B] space-y-2 text-[11px]">
                    <div className="flex items-start gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                      <span>
                        <strong>Correlation Model:</strong> {sections.facility_correlation.assessment_model}
                      </span>
                    </div>
                    <div className="p-2.5 rounded bg-[#0A0E17] border border-[#1E293B] text-[10px] text-[#94A3B8] font-mono">
                      <strong>Causation Safeguard:</strong> {sections.facility_correlation.causation_disclaimer}
                    </div>
                  </div>
                </div>
              )}

              {/* 5. ML & Statistical Anomaly Bounds */}
              {sections?.ml_evaluation && (
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-white uppercase font-mono tracking-wider">
                    5. Machine Learning & Statistical Anomaly Evaluation
                  </h3>
                  <div className="p-3.5 bg-[#070A10] rounded border border-[#1E293B] space-y-2 font-mono text-[11px]">
                    <div className="flex justify-between items-center">
                      <span className="text-[#64748B]">Anomaly Detection Model:</span>
                      <span className="text-white font-semibold">{sections.ml_evaluation.algorithm}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-[#64748B]">Statistical Interpretation:</span>
                      <span className="text-[#E2E8F0]">{sections.ml_evaluation.output_type}</span>
                    </div>
                    <div className="p-2.5 rounded bg-[#121927] border border-[#1E293B] text-[10px] text-[#94A3B8] leading-relaxed">
                      <strong>Scientific Notice:</strong> {sections.ml_evaluation.critical_note}
                    </div>
                  </div>
                </div>
              )}

              {/* 6. Recommended Verification Actions */}
              {sections?.recommendations && (
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-white uppercase font-mono tracking-wider text-[#F59E0B]">
                    6. Recommended Operational Verification Actions
                  </h3>
                  <ul className="space-y-1.5 list-disc list-inside text-[11px] text-[#CBD5E1] bg-[#070A10] p-3.5 rounded border border-[#1E293B]">
                    {sections.recommendations.map((rec, idx) => (
                      <li key={idx} className="leading-relaxed">{rec}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 7. Limitations & Uncertainty */}
              {sections?.limitations && (
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-white uppercase font-mono tracking-wider text-[#64748B]">
                    7. Limitations & Data Quality Constraints
                  </h3>
                  <ul className="space-y-1.5 list-disc list-inside text-[10px] text-[#94A3B8] bg-[#070A10] p-3 rounded border border-[#1E293B]">
                    {sections.limitations.map((lim, idx) => (
                      <li key={idx}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 8. Sources & Methodology */}
              <div className="pt-3 border-t border-[#1E293B] flex flex-wrap justify-between items-center text-[10px] font-mono text-[#64748B]">
                <span>Telemetry: NASA FIRMS NRT VIIRS 375m</span>
                <span>Spatial Stack: PostgreSQL 18 / PostGIS 3.6.2</span>
                <span>Land Cover: ESA WorldCover 10m v200 & OSM</span>
              </div>
            </>
          ) : null}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-[#1E293B] bg-[#070A10] flex justify-between items-center text-xs">
          <span className="text-[11px] text-[#64748B] font-mono">
            KRATOS Industrial Thermal Intelligence V2 · Official Intelligence Dossier
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-[#1E293B] hover:bg-[#2A374D] text-xs text-white font-medium transition-colors"
          >
            Dismiss
          </button>
        </div>

      </div>
    </div>
  );
};
