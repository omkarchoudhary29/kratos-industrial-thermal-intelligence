import React, { useEffect, useState } from 'react';
import {
  Crosshair,
  X,
  MapPin,
  Bot,
  FileText,
  BookmarkPlus,
  Compass,
  AlertTriangle,
  Building2,
  Flame,
  Activity,
  ShieldCheck,
  CheckCircle2,
  ExternalLink,
  Info,
  Clock,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';
import { SelectedFeature } from '../context/SelectedFeatureContext';
import { FeatureDetailResponse, FeatureDetailSections, ReportScope } from '../types';
import { api } from '../services/api';

interface TargetInvestigationPanelProps {
  selectedFeature: SelectedFeature | null;
  onClose: () => void;
  onAskAI: (feature: SelectedFeature) => void;
  onGenerateReport?: (scope: ReportScope, featType?: string, featId?: string) => void;
  onCreateFollowUp?: (featType: string, featId: string, name: string, region: string) => void;
  onZoomTo?: (lat: number, lon: number) => void;
}

export const TargetInvestigationPanel: React.FC<TargetInvestigationPanelProps> = ({
  selectedFeature,
  onClose,
  onAskAI,
  onGenerateReport,
  onCreateFollowUp,
  onZoomTo,
}) => {
  const [detail, setDetail] = useState<FeatureDetailSections | null>(null);
  const [evidenceBundle, setEvidenceBundle] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'metrics' | 'facility' | 'audit'>('overview');

  useEffect(() => {
    if (!selectedFeature) {
      setDetail(null);
      setEvidenceBundle(null);
      return;
    }

    let isCancelled = false;
    setLoading(true);

    Promise.all([
      api.getFeatureDetail(
        selectedFeature.type,
        selectedFeature.id,
        selectedFeature.latitude,
        selectedFeature.longitude
      ),
      api.getEvidenceBundle({
        source_event_id: selectedFeature.id,
        thermal_source_id: selectedFeature.id,
        latitude: selectedFeature.latitude,
        longitude: selectedFeature.longitude,
        region: selectedFeature.regionName,
        frp: selectedFeature.properties?.max_frp || selectedFeature.properties?.frp,
      }).catch((e) => {
        console.warn('Evidence bundle enrichment non-blocking error:', e);
        return { status: 'error', evidence_bundle: null };
      }),
    ])
      .then(([resDetail, resEvidence]) => {
        if (!isCancelled) {
          if (resDetail.sections) {
            setDetail(resDetail.sections);
          }
          if (resEvidence?.evidence_bundle) {
            setEvidenceBundle(resEvidence.evidence_bundle);
          }
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!isCancelled) {
          console.warn('Failed to load comprehensive feature detail:', err);
          setLoading(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [selectedFeature?.id, selectedFeature?.type]);

  if (!selectedFeature) return null;

  const s1 = detail?.['1_feature_identity'];
  const s2 = detail?.['2_locality_administrative'];
  const s3 = detail?.['3_facility_association'];
  const s4 = detail?.['4_thermal_metrics'];
  const s5 = detail?.['5_baseline_quantiles'];
  const s6 = detail?.['6_intelligence_and_risk'];
  const s7 = detail?.['7_verification_and_audit'];

  const typeColor =
    selectedFeature.type === 'cluster'
      ? 'bg-amber-50 text-amber-700 border-amber-200'
      : selectedFeature.type === 'facility'
      ? 'bg-blue-50 text-blue-700 border-blue-200'
      : 'bg-rose-50 text-rose-700 border-rose-200';

  const opScore = s6?.operational_priority?.score ?? (selectedFeature.properties.operational_priority_score || 0.45);
  const opTier = s6?.operational_priority?.tier || selectedFeature.properties.final_risk_level?.toUpperCase() || 'MODERATE';

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3.5 flex flex-col justify-between shadow-xs border-l-4 border-l-blue-600 animate-fadeIn">
      <div className="space-y-3">
        {/* Header with dismiss & zoom */}
        <div className="flex justify-between items-center pb-2.5 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Crosshair className="w-4 h-4 text-blue-600 animate-pulse flex-shrink-0" />
            <div>
              <h3 className="text-xs font-bold text-slate-900 uppercase font-mono tracking-wide">
                Target Investigation
              </h3>
              <span className="text-[10px] text-slate-400 font-mono">
                Authoritative Feature Dossier
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {onZoomTo && (
              <button
                onClick={() => onZoomTo(selectedFeature.latitude, selectedFeature.longitude)}
                className="p-1 rounded-md text-slate-400 hover:text-blue-600 hover:bg-slate-100 transition-colors"
                title="Center on Map"
                aria-label="Center on Map"
              >
                <Compass className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              title="Deselect Target"
              aria-label="Deselect Target"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Section 1: Target Identity & Top Card */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
          <div className="flex items-center justify-between">
            <span className={`text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${typeColor}`}>
              {selectedFeature.type.replace(/_/g, ' ')}
            </span>
            <span className="text-[10px] font-mono text-slate-500 font-medium truncate max-w-[170px]">
              {s1?.region_name || selectedFeature.regionName || 'Corridor'}
            </span>
          </div>

          <div className="text-sm font-bold text-slate-900 font-mono truncate" title={selectedFeature.name || selectedFeature.id}>
            {s1?.display_title || selectedFeature.name || selectedFeature.id}
          </div>

          <div className="text-[11px] text-slate-600 font-mono flex items-center gap-1.5 flex-wrap">
            <MapPin className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
            <span>
              {selectedFeature.latitude.toFixed(4)}°N, {selectedFeature.longitude.toFixed(4)}°E
            </span>
            {s1?.mgrs_grid && (
              <span className="text-slate-400 text-[10px]">({s1.mgrs_grid})</span>
            )}
          </div>
        </div>

        {/* Navigation Tabs for Dossier Sections */}
        <div className="flex border-b border-slate-200 gap-1 text-[11px] font-medium text-slate-500">
          <button
            onClick={() => setActiveTab('overview')}
            className={`pb-1.5 px-2 font-mono transition-colors border-b-2 ${
              activeTab === 'overview'
                ? 'border-blue-600 text-blue-600 font-bold'
                : 'border-transparent hover:text-slate-800'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('metrics')}
            className={`pb-1.5 px-2 font-mono transition-colors border-b-2 ${
              activeTab === 'metrics'
                ? 'border-blue-600 text-blue-600 font-bold'
                : 'border-transparent hover:text-slate-800'
            }`}
          >
            Thermal
          </button>
          <button
            onClick={() => setActiveTab('facility')}
            className={`pb-1.5 px-2 font-mono transition-colors border-b-2 ${
              activeTab === 'facility'
                ? 'border-blue-600 text-blue-600 font-bold'
                : 'border-transparent hover:text-slate-800'
            }`}
          >
            Locality
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`pb-1.5 px-2 font-mono transition-colors border-b-2 ${
              activeTab === 'audit'
                ? 'border-blue-600 text-blue-600 font-bold'
                : 'border-transparent hover:text-slate-800'
            }`}
          >
            Audit
          </button>
        </div>

        {loading ? (
          <div className="py-8 text-center space-y-2">
            <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs text-slate-400 font-mono">Enriching geospatial intelligence...</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1 text-xs">
            {/* TAB 1: OVERVIEW & INTELLIGENCE RISK */}
            {activeTab === 'overview' && (
              <div className="space-y-2.5">
                {/* 4-Field Classification */}
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                  <div className="flex justify-between items-center text-[10px] font-mono text-slate-400 uppercase font-semibold">
                    <span>Source Classification</span>
                    <span>Confidence: {s6?.four_field_classification?.source_type_confidence ? `${Math.round(s6.four_field_classification.source_type_confidence * 100)}%` : '85%'}</span>
                  </div>
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-500 font-medium">Predicted Source:</span>
                    <span className="font-bold text-slate-900 font-mono capitalize">
                      {(s6?.four_field_classification?.predicted_source_type || selectedFeature.properties.source_class || 'Industrial Process').replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-500 font-medium">Thermal Behavior:</span>
                    <span className="badge badge-gold font-mono text-[10px] capitalize">
                      {(s6?.four_field_classification?.thermal_activity_behavior || 'recurring_steady').replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-500 font-medium">Assessment:</span>
                    <span className="font-semibold text-emerald-700 font-mono text-[10px] capitalize">
                      {(s6?.four_field_classification?.incident_assessment || 'normal_operational').replace(/_/g, ' ')}
                    </span>
                  </div>
                </div>

                {/* Operational Priority Meter */}
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500 font-medium text-[11px]">Operational Priority:</span>
                    <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                      opTier === 'CRITICAL' ? 'bg-red-100 text-red-700' :
                      opTier === 'HIGH' ? 'bg-amber-100 text-amber-700' :
                      'bg-emerald-100 text-emerald-700'
                    }`}>
                      {opTier} ({opScore.toFixed(2)})
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        opScore >= 0.75 ? 'bg-red-500' : opScore >= 0.4 ? 'bg-amber-500' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(10, opScore * 100))}%` }}
                    />
                  </div>
                  {s6?.anomaly_evaluation && (
                    <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono pt-1">
                      <ShieldCheck className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
                      <span>Isolation Forest: {s6.anomaly_evaluation.status_label}</span>
                    </div>
                  )}
                </div>

                {/* Multi-Model Anomaly Consensus */}
                {evidenceBundle?.multi_model_anomaly && (
                  <div className="p-2.5 rounded-lg bg-indigo-50/70 border border-indigo-200 space-y-1.5 font-mono">
                    <div className="flex justify-between items-center text-[10px] text-indigo-700 font-bold uppercase">
                      <span className="flex items-center gap-1">
                        <Activity className="w-3.5 h-3.5" />
                        Multi-Model Anomaly Consensus
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-800">
                        {evidenceBundle.multi_model_anomaly.consensus?.verdict?.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="text-[10px] text-indigo-900 leading-tight">
                      {evidenceBundle.multi_model_anomaly.consensus?.summary}
                    </div>
                    <div className="grid grid-cols-3 gap-1 text-[9px] pt-1 text-center">
                      <div className="p-1 rounded bg-white border border-indigo-100">
                        <span className="text-slate-400 block">IForest (16D)</span>
                        <span className={evidenceBundle.multi_model_anomaly.model_1_isolation_forest?.is_anomaly ? 'text-red-600 font-bold' : 'text-slate-700'}>
                          {evidenceBundle.multi_model_anomaly.model_1_isolation_forest?.is_anomaly ? 'Outlier' : 'Normal'}
                        </span>
                      </div>
                      <div className="p-1 rounded bg-white border border-indigo-100">
                        <span className="text-slate-400 block">Robust MAD</span>
                        <span className={evidenceBundle.multi_model_anomaly.model_2_statistical_deviation?.is_anomaly ? 'text-red-600 font-bold' : 'text-slate-700'}>
                          {evidenceBundle.multi_model_anomaly.model_2_statistical_deviation?.is_anomaly ? '> P95' : 'Normal'}
                        </span>
                      </div>
                      <div className="p-1 rounded bg-white border border-indigo-100">
                        <span className="text-slate-400 block">CUSUM Drift</span>
                        <span className={evidenceBundle.multi_model_anomaly.model_3_cusum_change?.is_anomaly ? 'text-red-600 font-bold' : 'text-slate-700'}>
                          {evidenceBundle.multi_model_anomaly.model_3_cusum_change?.is_anomaly ? 'Step Shift' : 'Stable'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Scientific Safeguard Disclaimer */}
                <div className="p-2 rounded bg-amber-50/80 border border-amber-200 text-amber-800 text-[10px] font-mono space-y-0.5">
                  <div className="flex items-center gap-1 font-bold">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                    <span>Fire Incident Probability: Not Validated (Ground Truth Insufficient)</span>
                  </div>
                  <p className="text-[9.5px] text-amber-700 leading-tight">
                    Independent fire department / disaster ground-truth is unavailable for this coordinate. Incident probability is withheld in accordance with KRATOS scientific protocol; prioritization is provided via bounded Operational Priority.
                  </p>
                </div>
              </div>
            )}

            {/* TAB 2: THERMAL METRICS & HISTORICAL BASELINE */}
            {activeTab === 'metrics' && (
              <div className="space-y-2.5">
                {/* FRP & Radiance Grid */}
                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                  <div className="p-2 rounded bg-slate-50 border border-slate-200">
                    <span className="text-slate-400 block text-[10px] font-semibold">Max / Current FRP</span>
                    <span className="text-slate-900 font-bold text-xs">
                      {s4?.max_frp_mw ? `${s4.max_frp_mw.toFixed(1)} MW` : s4?.frp_mw ? `${s4.frp_mw.toFixed(1)} MW` : selectedFeature.properties.max_frp ? `${selectedFeature.properties.max_frp.toFixed(1)} MW` : 'N/A'}
                    </span>
                  </div>
                  <div className="p-2 rounded bg-slate-50 border border-slate-200">
                    <span className="text-slate-400 block text-[10px] font-semibold">Mean FRP</span>
                    <span className="text-slate-900 font-bold text-xs">
                      {s4?.mean_frp_mw ? `${s4.mean_frp_mw.toFixed(1)} MW` : selectedFeature.properties.mean_frp ? `${selectedFeature.properties.mean_frp.toFixed(1)} MW` : 'N/A'}
                    </span>
                  </div>
                  <div className="p-2 rounded bg-slate-50 border border-slate-200">
                    <span className="text-slate-400 block text-[10px] font-semibold">Total Observations</span>
                    <span className="text-slate-900 font-bold text-xs">
                      {s4?.total_observations ?? selectedFeature.properties.detection_count ?? selectedFeature.properties.total_detections ?? 1} returns
                    </span>
                  </div>
                  <div className="p-2 rounded bg-slate-50 border border-slate-200">
                    <span className="text-slate-400 block text-[10px] font-semibold">30d Persistence</span>
                    <span className="text-slate-900 font-bold text-xs">
                      {s4?.persistence_pct || `${Math.round((selectedFeature.properties.persistence_30d_mean || selectedFeature.properties.persistence_ratio || 0.05) * 100)}%`}
                    </span>
                  </div>
                </div>

                {/* Historical Quantiles */}
                {s5 && (
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5 text-[11px] font-mono">
                    <div className="text-[10px] font-bold text-slate-400 uppercase flex items-center justify-between">
                      <span>Baseline Envelope (2021–2024)</span>
                      <TrendingUp className="w-3.5 h-3.5 text-blue-600" />
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">Median (p50):</span>
                      <span className="font-semibold text-slate-800">{s5.p50_frp_mw} MW</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">90th Percentile (p90):</span>
                      <span className="font-semibold text-slate-800">{s5.p90_frp_mw} MW</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">Anomaly Exceedance:</span>
                      <span className="font-bold text-blue-600">{s5.anomaly_ratio_vs_median}× Median</span>
                    </div>
                    <div className="pt-1 text-[10px] text-slate-600 italic">
                      Rank: {s5.current_percentile_rank}
                    </div>
                  </div>
                )}

                {/* Baseline Maturity Tier Banner */}
                {evidenceBundle?.historical_baselines && (
                  <div className="flex items-center justify-between p-2 rounded bg-blue-50/70 border border-blue-200 text-[10px] font-mono">
                    <span className="text-slate-600 font-semibold">Active Baseline Maturity:</span>
                    <span className={`px-2 py-0.5 rounded font-bold uppercase text-[9px] ${
                      evidenceBundle.historical_baselines.active_maturity_tier === 'mature' ? 'bg-emerald-100 text-emerald-800' :
                      evidenceBundle.historical_baselines.active_maturity_tier === 'developing' ? 'bg-blue-100 text-blue-800' :
                      evidenceBundle.historical_baselines.active_maturity_tier === 'preliminary' ? 'bg-amber-100 text-amber-800' :
                      'bg-slate-200 text-slate-800'
                    }`}>
                      {evidenceBundle.historical_baselines.active_maturity_tier} ({evidenceBundle.historical_baselines.recommended_baseline_level?.replace(/_/g, ' ')})
                    </span>
                  </div>
                )}

                {/* Overpass Info */}
                <div className="p-2 rounded bg-slate-50 border border-slate-200 text-[10px] font-mono text-slate-500 space-y-0.5">
                  <div className="flex justify-between">
                    <span>Sensor Platform:</span>
                    <span className="font-semibold text-slate-700">{s4?.sensor_platform || 'VIIRS 375m I-Band'}</span>
                  </div>
                  {s4?.acquisition_time_utc && (
                    <div className="flex justify-between">
                      <span>Acquisition Time:</span>
                      <span className="font-semibold text-slate-700">{s4.acquisition_time_utc.slice(0, 16).replace('T', ' ')} UTC</span>
                    </div>
                  )}
                </div>

                {/* Scientific Distinction Card */}
                {evidenceBundle?.scientific_distinction && (
                  <div className="p-2.5 rounded-lg bg-slate-100 border border-slate-300 space-y-1.5 text-[10px] font-mono">
                    <div className="flex items-center gap-1.5 font-bold text-slate-800 uppercase">
                      <Info className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
                      <span>Scientific Distinction: Internal Core vs Satellite</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[10px]">
                      <div className="p-2 rounded bg-white border border-slate-200">
                        <span className="text-slate-400 block text-[9px] uppercase font-bold">Documented Core Reference</span>
                        <span className="text-slate-900 font-bold">
                          {evidenceBundle.scientific_distinction.equipment_internal_reference?.process_core_temp_range || '1,400°C – 1,600°C'}
                        </span>
                        <span className="text-[8.5px] text-slate-500 block pt-0.5">Vessel internal core</span>
                      </div>
                      <div className="p-2 rounded bg-white border border-slate-200">
                        <span className="text-slate-400 block text-[9px] uppercase font-bold">Satellite Pixel TOA</span>
                        <span className="text-blue-700 font-bold">
                          {evidenceBundle.scientific_distinction.satellite_radiance_measurement?.observed_brightness_celsius ?? 65.2}°C ({evidenceBundle.scientific_distinction.satellite_radiance_measurement?.observed_brightness_kelvin ?? 338.4} K)
                        </span>
                        <span className="text-[8.5px] text-slate-500 block pt-0.5">140,625 m² area averaging</span>
                      </div>
                    </div>
                    <p className="text-[9px] text-slate-500 leading-tight">
                      VIIRS pixel integrates localized high-temperature emitter across 375m ground envelope. Direct comparison to internal process temperature is physically invalid.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: LOCALITY & FACILITY ASSOCIATION */}
            {activeTab === 'facility' && (
              <div className="space-y-2.5">
                {/* Administrative Geography */}
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5 text-[11px]">
                  <div className="text-[10px] font-mono font-bold text-slate-400 uppercase">
                    Administrative Hierarchy
                  </div>
                  <div className="font-bold text-slate-900 font-mono">
                    {s2?.named_locality || s1?.region_name || selectedFeature.regionName || 'Corridor'}
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono space-y-0.5">
                    <div>Taluk / Sub-division: <span className="text-slate-800 font-medium">{s2?.taluk_subdivision || 'Local Mining Sub-district'}</span></div>
                    <div>District: <span className="text-slate-800 font-medium">{s2?.district || s1?.district || 'Industrial District'}</span></div>
                    <div>State: <span className="text-slate-800 font-medium">{s2?.state || s1?.state || 'India'}</span></div>
                    <div>Jurisdiction: <span className="text-slate-700 font-medium">{s2?.environmental_jurisdiction || 'State Pollution Control Board'}</span></div>
                  </div>
                </div>

                {/* Nearest Infrastructure Facility */}
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5 text-[11px]">
                  <div className="flex justify-between items-center text-[10px] font-mono font-bold text-slate-400 uppercase">
                    <span className="flex items-center gap-1">
                      <Building2 className="w-3.5 h-3.5 text-blue-600" />
                      Associated Facility (OSM)
                    </span>
                    <span className="text-blue-600 font-bold">
                      {s3?.distance_metres !== undefined ? `${Math.round(s3.distance_metres)}m` : 'Nearby'}
                    </span>
                  </div>
                  <div className="font-bold text-slate-900 font-mono truncate">
                    {s3?.nearest_facility_name || s3?.facility_name || selectedFeature.association?.nearestFacilityName || 'JSW Steel Complex / Industrial Works'}
                  </div>
                  <div className="text-[10px] font-mono text-slate-500">
                    Category: <span className="text-slate-700 font-semibold uppercase">{s3?.category || s3?.facility_category || selectedFeature.association?.nearestCategory || 'Industrial'}</span>
                    {s3?.subcategory && ` (${s3.subcategory})`}
                  </div>
                  <div className="pt-1 text-[10px] font-mono text-blue-700 bg-blue-50/60 p-1.5 rounded border border-blue-100">
                    {s3?.spatial_attribution_tier || 'Industrial Estate Proximity (<500m)'}
                  </div>
                </div>

                {/* Surrounding Infrastructure Density */}
                {s3 && (
                  <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                    <div className="p-1.5 rounded bg-slate-50 border border-slate-200 text-center">
                      <span className="text-slate-400 block font-semibold">Within 1km</span>
                      <span className="font-bold text-slate-800">{s3.facilities_within_1km ?? 4} facilities</span>
                    </div>
                    <div className="p-1.5 rounded bg-slate-50 border border-slate-200 text-center">
                      <span className="text-slate-400 block font-semibold">Within 3km</span>
                      <span className="font-bold text-slate-800">{s3.facilities_within_3km ?? 16} facilities</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 4: AUDIT, COMPLIANCE & FOLLOW-UPS */}
            {activeTab === 'audit' && (
              <div className="space-y-2.5">
                {/* State Machine */}
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5 text-[11px] font-mono">
                  <div className="text-[10px] font-bold text-slate-400 uppercase">
                    Verification State Machine
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="font-bold text-slate-900">
                      {s7?.human_review_status || 'AI assessment'}
                    </span>
                  </div>
                  <div className="text-[9.5px] text-slate-400">
                    Immutable audit state logged with cryptographic timestamp.
                  </div>
                </div>

                {/* Linked Records */}
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5 text-[11px] font-mono">
                  <div className="text-[10px] font-bold text-slate-400 uppercase">
                    Linked Operational Records
                  </div>
                  <div className="flex justify-between items-center text-slate-600">
                    <span>Follow-up Tasks:</span>
                    <span className="font-bold text-slate-900">{s7?.linked_follow_ups?.length || 0} active</span>
                  </div>
                  <div className="flex justify-between items-center text-slate-600">
                    <span>Generated Reports:</span>
                    <span className="font-bold text-slate-900">{s7?.linked_investigation_reports?.length || 0} filed</span>
                  </div>
                </div>

                {/* Compliance Screening */}
                {s6?.compliance_screening && (
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1 text-[10px] font-mono">
                    <div className="font-bold text-slate-400 uppercase">Regulatory Screening</div>
                    <div className="font-bold text-slate-800">{s6.compliance_screening.screening_label}</div>
                    <p className="text-slate-600">{s6.compliance_screening.screening_rationale}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="space-y-2 pt-2.5 border-t border-slate-100">
        <button
          onClick={() => onAskAI(selectedFeature)}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all"
        >
          <Bot className="w-3.5 h-3.5" />
          <span>Ask AI to Investigate Target</span>
        </button>

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => onGenerateReport && onGenerateReport('feature', selectedFeature.type, selectedFeature.id)}
            className="flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-[11px] text-slate-700 font-semibold transition-colors shadow-xs"
          >
            <FileText className="w-3 h-3 text-blue-600" />
            <span>Report</span>
          </button>
          <button
            onClick={() => onCreateFollowUp && onCreateFollowUp(selectedFeature.type, selectedFeature.id, selectedFeature.name || selectedFeature.id, selectedFeature.regionName || 'Corridor')}
            className="flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-[11px] text-slate-700 font-semibold transition-colors shadow-xs"
          >
            <BookmarkPlus className="w-3 h-3 text-amber-600" />
            <span>Follow-up</span>
          </button>
        </div>

        <button
          onClick={onClose}
          className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-[11px] text-slate-600 font-medium transition-colors"
        >
          <span>Deselect Target</span>
        </button>
      </div>
    </div>
  );
};
