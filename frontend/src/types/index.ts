export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export type ThermalClass =
  | 'industrial_fire'
  | 'gas_flare'
  | 'agricultural_burning'
  | 'mining_activity'
  | 'wildfire'
  | 'industrial_process_heat'
  | 'unknown';

export interface Region {
  id: string;
  name: string;
  category: 'industrial_corridor' | 'forest_landscape';
  state: string;
  description: string;
  center: [number, number];
  zoom: number;
  bbox: [number, number, number, number]; // [minLon, minLat, maxLon, maxLat]
  event_id?: number;
}

export interface ThermalStats {
  total_events: number;
  high_risk_count: number;
  critical_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  active_regions_count: number;
  last_updated: string | null;
  sensor_counts?: Record<string, number>;
  classification_counts?: Record<string, number>;
  iforest_agreement_count?: number;
  open_followups?: number;
}

export interface ThermalEvent {
  source_event_id: string;
  thermal_source_id: string;
  latitude: number;
  longitude: number;
  region_name: string;
  event_start: string;
  event_end?: string;
  final_risk_level: RiskLevel;
  final_confidence: number;
  final_risk_score: number;
  max_frp: number;
  source_baseline_frp?: number;
  max_frp_ratio?: number;
  iforest_agreement?: boolean;
  iforest_evaluated?: boolean;
  detection_count: number;
  data_mode?: string;
  is_live?: boolean;
  latest_observation_at?: string;
  nearest_industry_name?: string;
  nearest_industry_type?: string;
  distance_to_nearest_industry_m?: number;
  source_event_reason?: string;
}

export interface ThermalSource {
  thermal_source_id: string;
  region_name: string;
  latitude: number;
  longitude: number;
  source_class?: string;
  classification_confidence?: number | null;
  detection_count: number;
  total_detections?: number;
  active_days?: number;
  mean_frp: number;
  max_frp: number;
  persistence_ratio?: number;
  first_seen?: string;
  last_seen?: string;
  nearest_osm_facility?: string;
}

export interface LiveFireDetection {
  id: number;
  detection_key: string;
  fire_event_id?: number;
  monitoring_region_id?: number;
  latitude: number;
  longitude: number;
  acquisition_time: string;
  received_at: string;
  data_latency_seconds: number;
  satellite: string;
  instrument: string;
  source_product?: string;
  brightness?: number;
  bright_ti4?: number;
  bright_ti5?: number;
  frp: number;
  firms_confidence?: string;
  day_night?: string;
  land_cover?: string;
  landcover_group?: string;
  inside_industrial_polygon?: boolean;
  near_industrial_facility?: boolean;
  predicted_class?: string;
  model_confidence?: number;
  model_version?: string;
  alert_status?: string;
}

export interface LiveFireEvent {
  id: number;
  event_key: string;
  monitoring_region_id?: number;
  centroid_latitude: number;
  centroid_longitude: number;
  first_detected_at: string;
  last_detected_at: string;
  status: string;
  detection_count: number;
  max_frp: number;
  average_frp: number;
  predicted_class?: string;
  confidence?: number;
  alert_status: string;
}

export interface SystemStatus {
  scheduler_running: boolean;
  nrt_refresh_enabled: boolean;
  poll_interval_minutes: number;
  model_version: string;
  active_features_count: number;
  last_firms_sync?: string;
  database_status: string;
}

export interface OSMFacilityProperties {
  id: number;
  osm_id: number;
  osm_type: string;
  name: string;
  facility_category: string;
  subcategory?: string;
  region_id?: number;
  region_name?: string;
  tags: Record<string, any>;
  source: string;
  retrieved_at?: string;
}

export interface OSMFacilityFeature {
  type: 'Feature';
  id: number;
  geometry: any;
  properties: OSMFacilityProperties;
}

export interface OSMFacilityCollection {
  type: 'FeatureCollection';
  features: OSMFacilityFeature[];
  total: number;
  count: number;
  limit: number;
  offset: number;
}

export interface User {
  id: number;
  username: string;
  email?: string | null;
  is_admin: boolean;
  created_at?: string;
}

export interface FieldReport {
  id: number;
  post_type: 'fire_report' | 'info' | 'request_help' | 'offer_help';
  lat: number;
  lon: number;
  bearing?: number | null;
  description: string;
  like_count: number;
  flag_count: number;
  created_at: string;
  photo_path?: string | null;
}

export interface AISituationReport {
  region: string;
  generated_at: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  executive_summary: string;
  priority_signals: string[];
  classification_insights: string[];
  infrastructure_threats: string[];
  recommended_actions: string[];
  confidence_metric: number;
  source_provenance: string;
}

export type ReportScope = 'region' | 'viewport' | 'feature';

export interface ReportPrioritySignal {
  id: string;
  coordinates: string;
  detection_count?: number;
  mean_frp?: string;
  max_frp?: string;
  persistence_30d?: string;
  classification?: string;
  nearest_facility?: string;
}

export interface InvestigationReportData {
  id?: number;
  report_id?: number;
  report_key: string;
  scope: ReportScope;
  region_name?: string;
  feature_type?: string;
  feature_id?: string;
  title: string;
  summary?: string;
  sections?: {
    title: string;
    executive_summary: string;
    monitoring_coverage?: Record<string, string>;
    priority_signals?: ReportPrioritySignal[];
    facility_correlation?: {
      assessment_model?: string;
      mapped_facilities_in_region?: Record<string, number>;
      causation_disclaimer?: string;
    };
    ml_evaluation?: {
      algorithm?: string;
      output_type?: string;
      critical_note?: string;
    };
    recommendations?: string[];
    limitations?: string[];
    methodology?: Record<string, string>;
  };
  evidence?: Record<string, any>;
  creator_name?: string;
  created_at?: string;
}

export type FollowUpPriority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type FollowUpStatus =
  | 'OPEN'
  | 'ASSIGNED'
  | 'IN_PROGRESS'
  | 'AWAITING_FIELD_VERIFICATION'
  | 'AWAITING_VERIFICATION'
  | 'UNDER_REVIEW'
  | 'RESOLVED'
  | 'CLOSED';

export interface FollowUpNoteData {
  id: number;
  author_name: string;
  note_text: string;
  status_change?: string | null;
  created_at?: string;
}

export interface FollowUpTaskData {
  id: number;
  task_key: string;
  title: string;
  feature_type: string;
  feature_id: string;
  region_name: string;
  report_id?: number | null;
  priority: FollowUpPriority;
  status: FollowUpStatus;
  description?: string;
  assigned_to?: string;
  due_date?: string | null;
  created_by_name: string;
  note_count?: number;
  notes?: FollowUpNoteData[];
  created_at?: string;
  updated_at?: string;
}

export interface DataFreshnessInfo {
  status: string;
  last_successful_sync: string | null;
  last_attempt_at: string | null;
  last_observed_at: string | null;
  poll_interval_minutes: number;
  model_version: string;
  sources: string[];
  server_time: string;
  records_received: number;
  new_records: number;
}

export interface NotificationItem {
  id: number;
  fire_event_id: number;
  detection_id?: number | null;
  alert_type: string;
  severity: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
  message: string;
  is_read: boolean;
  read_at?: string | null;
  created_at?: string | null;
  region_name: string;
  latitude?: number | null;
  longitude?: number | null;
}

export interface NotificationResponse {
  notifications: NotificationItem[];
  unread_count: number;
  total: number;
  limit: number;
  offset: number;
}

export interface SearchResult {
  category: 'regions' | 'facilities' | 'clusters' | 'observations' | 'reports' | 'tasks' | 'coordinates';
  id: string;
  title: string;
  subtitle: string;
  latitude: number;
  longitude: number;
  zoom: number;
  feature_type: 'region' | 'facility' | 'cluster' | 'observation' | 'report' | 'task';
  feature_id: string;
  region_id?: string;
  properties?: Record<string, any>;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

// ── Phase 2 Intelligence Types ────────────────────────────────────────────────

export interface SourceFacilityItem extends ThermalSource {
  mapped_facility_category: string;
  nearest_facility_name: string;
  spatial_relationship: 'direct_intersection' | 'strong_association' | 'nearby_proximity' | 'ambiguous' | 'unassociated';
  spatial_description: string;
  distance_to_nearest_facility_m?: number | null;
  predicted_source_type: string;
  source_type_confidence?: number | null;
  source_type_rationale: string;
  thermal_activity_behavior: 'isolated_hotspot' | 'recurring_steady' | 'sudden_frp_spike' | 'abnormal_persistence';
  behavior_description: string;
  incident_assessment: 'normal_operational' | 'anomaly_under_review' | 'unusual_heat_exceedance' | 'potential_incident_candidate';
  assessment_notes: string;
}

export interface ThermalAnalysisStats {
  count: number;
  mean_mw: number;
  median_mw: number;
  std_mw: number;
  min_mw: number;
  p25_mw: number;
  p75_mw: number;
  p90_mw: number;
  p99_mw: number;
  max_mw: number;
  iqr_mw: number;
  histogram: Array<{ bin: string; count: number; percentage: number }>;
  diurnal_breakdown: {
    daytime_overpasses: number;
    nighttime_overpasses: number;
    daytime_pct: number;
    nighttime_pct: number;
  };
}

export interface OperationalPriorityItem {
  source_event_id: string;
  thermal_source_id: string;
  region_name: string;
  event_start: string;
  latitude: number;
  longitude: number;
  max_frp_mw: number;
  max_frp_ratio: number;
  priority_score: number;
  priority_tier: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT_EVIDENCE';
  tier_rationale: string;
  anomaly_score: number;
  is_anomaly_flagged: boolean;
  source_class: string;
  component_contributions: {
    frp_exceedance_factor: number;
    frp_contribution: number;
    persistence_factor: number;
    persistence_contribution: number;
    anomaly_factor: number;
    anomaly_contribution: number;
    proximity_factor: number;
    proximity_contribution: number;
    uncertainty_penalty: number;
  };
}

export interface ComplianceStandard {
  id: string;
  sector: string;
  statute: string;
  statutory_source?: string;
  gazette_notification?: string;
  notification_date?: string;
  regulatory_authority?: string;
  regulatory_body: string;
  verification_status?: string;
  stack_concentration_notice?: string;
  key_limits: Record<string, string>;
  thermal_surveillance_relevance: string;
  monitoring_protocol: string;
}

export interface ComplianceScreeningResult {
  facility_name: string;
  facility_category: string;
  screening_status: 'POTENTIAL_COMPLIANCE_CONCERN' | 'FURTHER_EVIDENCE_REQUIRED' | 'NO_CONCERN_IDENTIFIED' | 'INSUFFICIENT_DATA';
  screening_label: string;
  screening_rationale: string;
  recommended_action: string;
  applicable_standard?: ComplianceStandard | null;
  disclaimer: string;
}

export interface InvestigationItem {
  id: number;
  report_key: string;
  title: string;
  region_name: string;
  feature_type: string;
  feature_id?: string | null;
  scope: string;
  human_review_status: 'AI assessment' | 'Analyst reviewed' | 'Field verification pending' | 'Field verified' | 'Authority confirmed';
  created_at: string | null;
  summary_text?: string | null;
  observation_count: number;
  evidence_snapshot?: {
    max_frp_mw?: number | null;
    priority_tier?: string;
    priority_score?: number;
    source_class?: string;
    high_priority_count?: number;
    clusters_count?: number;
  };
}

export interface SupervisedModelEvaluation {
  status: string;
  evaluation_date: string;
  target_class_definition: string;
  sample_count: number;
  fire_incident_prediction_validation?: string;
  target_type?: string;
  proxy_label_explanation?: string;
  feature_leakage_note?: string;
  evaluated_models: Array<{
    model_name: string;
    precision: number;
    recall: number;
    f1_score: number;
    confusion_matrix: {
      true_positives: number;
      false_positives: number;
      false_negatives: number;
      true_negatives: number;
    };
  }>;
  feature_importance_ranking: Array<{ feature: string; importance: number }>;
  calibration_disclaimer: string;
  uncalibrated_probability_notice?: string;
}

// ── Unified 7-Section Feature Intelligence Dossier ──────────────────────────

export interface FeatureDetailSections {
  '1_feature_identity': {
    id: string;
    name: string;
    display_title: string;
    type: 'cluster' | 'observation' | 'facility';
    region_name?: string;
    state?: string;
    district?: string;
    country?: string;
    coordinates: { latitude: number; longitude: number };
    mgrs_grid?: string;
    first_seen?: string;
    last_seen?: string;
    footprint_area_sqm?: number;
    osm_ref?: string;
    category?: string;
    subcategory?: string;
  };
  '2_locality_administrative': {
    country: string;
    state: string;
    district: string;
    taluk_subdivision: string;
    named_locality: string;
    administrative_hierarchy: string;
    monitoring_corridor: string;
    containment_tier: string;
    environmental_jurisdiction: string;
  };
  '3_facility_association': {
    is_infrastructure_asset?: boolean;
    nearest_facility_name?: string;
    facility_name?: string;
    category?: string;
    subcategory?: string;
    facility_category?: string;
    osm_id?: string;
    distance_metres?: number;
    spatial_attribution_tier?: string;
    attribution_code?: string;
    facilities_within_1km?: number;
    facilities_within_3km?: number;
    operational_status?: string;
  };
  '4_thermal_metrics': {
    frp_mw?: number;
    mean_frp_mw?: number;
    max_frp_mw?: number;
    min_frp_mw?: number;
    brightness_kelvin?: number;
    firms_confidence?: string;
    satellite?: string;
    instrument?: string;
    sensor_platform?: string;
    sensor_resolution?: string;
    day_night?: string;
    acquisition_time_utc?: string;
    observation_window?: string;
    persistence_30d_ratio?: number;
    persistence_pct?: string;
    total_observations?: number;
    frp_definition?: string;
    note?: string;
  };
  '5_baseline_quantiles': {
    baseline_period?: string;
    p25_frp_mw?: number;
    p50_frp_mw?: number;
    p75_frp_mw?: number;
    p90_frp_mw?: number;
    p99_frp_mw?: number;
    max_historical_frp_mw?: number;
    current_observation_frp_mw?: number;
    current_percentile_rank?: string;
    anomaly_ratio_vs_median?: number;
  };
  '6_intelligence_and_risk': {
    four_field_classification: {
      mapped_facility_category: string;
      predicted_source_type: string;
      thermal_activity_behavior: string;
      incident_assessment: string;
      source_type_confidence: number;
    };
    operational_priority: {
      score: number;
      tier: string;
      tier_rationale?: string;
      formula?: string;
      components?: Record<string, any>;
    };
    anomaly_evaluation?: {
      raw_decision_score?: number;
      normalized_score?: number;
      isolation_forest_score?: number;
      is_anomaly_flagged: boolean;
      status_label: string;
    };
    scientific_safeguard: {
      fire_incident_probability: string;
      disclaimer: string;
    };
    compliance_screening?: ComplianceScreeningResult;
  };
  '7_verification_and_audit': {
    human_review_status: string;
    workflow_state_machine: string[];
    linked_follow_ups: Array<{
      task_id: number;
      title: string;
      priority: string;
      status: string;
      assigned_to?: string;
      created_at?: string;
    }>;
    linked_investigation_reports: Array<{
      report_id: number;
      title: string;
      status?: string;
      review_state?: string;
      risk_level?: string;
      created_at?: string;
    }>;
    tamper_evident_logged: boolean;
  };
}

export interface FeatureDetailResponse {
  status: 'success' | 'error';
  feature_id: string;
  feature_type: string;
  sections: FeatureDetailSections;
}



