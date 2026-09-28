"""backend/services/metric_dictionary.py
--------------------------------------
KRATOS V3 Phase 2 Final Hardening — Central Metric Dictionary System.

Maintains canonical, audited definitions for all 9 core operational and historical populations:
  1. Archived Thermal Detections (8,891 events in final_fused_events.parquet)
  2. Persistent Thermal Sources / Clusters (312 clusters in thermal_sources.parquet)
  3. View Pagination Limit (100 sources per page in operational API)
  4. Operational High / Critical Priority Alerts (113 episodes flagged by triage rules)
  5. Active Investigation Dossiers (12 active priority incident dossiers)
  6. Isolation Forest Anomaly Outputs (196 events flagged by 16-feature density estimator)
  7. Active Follow-up Tasks (6 operational tasks in PostgreSQL follow_up_tasks)
  8. Mapped OSM Industrial Facilities (2,423 infrastructure features in osm_facilities)
  9. Database VIIRS Detections (853 / 692 raw operational detections in fire_detections)

Each metric provides:
  - Canonical Population Key & Display Name
  - Entity Type & Source File / Table
  - Exact Calculation Formula & Methodology
  - Geographic Scope (10 Industrial Corridors vs Pan-India)
  - Temporal Scope (2021-2024 Archive vs Current VIIRS Feed)
  - Scientific Units & Interpretation Limitations
"""

from __future__ import annotations

from typing import Any, Dict, List

METRIC_DICTIONARY: Dict[str, Dict[str, Any]] = {
    "archived_detections": {
        "key": "archived_detections",
        "display_name": "Archived Thermal Detections",
        "value": 8891,
        "entity_type": "Fused Thermal Event Record",
        "source": "data/processed/final_fused_events.parquet",
        "calculation_method": (
            "Temporal fusion of VIIRS active fire hotspots across 10 industrial monitoring corridors. "
            "Individual sensor pixels clustered within 500 m and 12-hour windows into discrete thermal events."
        ),
        "unit": "Fused Thermal Events",
        "geographic_scope": "10 Major Industrial Corridors in India",
        "temporal_scope": "2021-01-01 to 2024-12-31 (4-Year Archival Baseline)",
        "satellite_sensors": ["Suomi-NPP VIIRS (375 m I-Band)"],
        "interpretation_limitations": (
            "Represents historical fused event episodes, not raw instantaneous sensor pixels. "
            "Excludes detections outside the 10 monitored industrial corridors."
        ),
    },
    "persistent_sources": {
        "key": "persistent_sources",
        "display_name": "Persistent Thermal Sources",
        "value": 312,
        "entity_type": "Spatial Cluster Centroid",
        "source": "data/processed/thermal_sources.parquet",
        "calculation_method": (
            "Spatial metric DBSCAN clustering (eps = 500 m, min_samples = 3) on historical thermal observations. "
            "Identifies stationary high-temperature process locations (flares, kilns, furnaces, colliery fires)."
        ),
        "unit": "Persistent Spatial Clusters",
        "geographic_scope": "10 Major Industrial Corridors in India",
        "temporal_scope": "Multi-year recurring presence across 2021-2024 baseline",
        "satellite_sensors": ["Suomi-NPP VIIRS", "NOAA-20 VIIRS"],
        "interpretation_limitations": (
            "Cluster centroid coordinates represent the mean spatial locus of recurring thermal signatures. "
            "A single large plant (e.g. steel complex) may encompass multiple distinct persistent thermal sources."
        ),
    },
    "view_pagination_limit": {
        "key": "view_pagination_limit",
        "display_name": "Source Catalog View Pagination Limit",
        "value": 100,
        "entity_type": "API Parameter / View Default",
        "source": "backend/api/thermal.py & backend/api/intelligence.py",
        "calculation_method": (
            "Default and maximum standard page limit for tabular source list endpoints to ensure sub-50 ms "
            "response times and responsive browser rendering."
        ),
        "unit": "Records per Page",
        "geographic_scope": "Client viewport / API request scope",
        "temporal_scope": "Runtime operational setting",
        "satellite_sensors": ["N/A"],
        "interpretation_limitations": (
            "The 100 count reflects a presentation pagination window, NOT the total population of sources (which is 312)."
        ),
    },
    "high_critical_alerts": {
        "key": "high_critical_alerts",
        "display_name": "Operational High / Critical Priority Episodes",
        "value": 113,
        "entity_type": "Prioritized Event Notification",
        "source": "data/processed/final_fused_events.parquet (final_risk_level in ['high', 'critical'])",
        "calculation_method": (
            "Rule-based operational triage screening flagging events where max_frp_ratio >= 2.0 and "
            "max_source_anomaly_score <= -0.15 (or extreme FRP exceedance above 3.5x baseline)."
        ),
        "unit": "Triage Priority Episodes",
        "geographic_scope": "10 Major Industrial Corridors in India",
        "temporal_scope": "Historical and operational monitoring window",
        "satellite_sensors": ["Suomi-NPP VIIRS", "NOAA-20 VIIRS"],
        "interpretation_limitations": (
            "Represents operational triage alerts for human review. Does NOT constitute confirmed emergency "
            "incidents or disaster occurrences without physical site verification."
        ),
    },
    "active_investigation_dossiers": {
        "key": "active_investigation_dossiers",
        "display_name": "Active Priority Investigation Dossiers",
        "value": 12,
        "entity_type": "Investigation Dossier / Case",
        "source": "backend/api/intelligence.py & PostgreSQL investigation_reports",
        "calculation_method": (
            "Top-tier priority incidents queued for human-in-the-loop analyst review, field verification, "
            "and statutory authority confirmation across active monitoring zones."
        ),
        "unit": "Active Investigation Cases",
        "geographic_scope": "Nationwide active priority queue",
        "temporal_scope": "Current operational monitoring cycle (2026)",
        "satellite_sensors": ["NOAA-20 VIIRS", "NOAA-21 VIIRS", "Suomi-NPP VIIRS"],
        "interpretation_limitations": (
            "Bounded priority queue maintained for operational focus. New cases transition through a 5-stage "
            "verification lifecycle before authority escalation."
        ),
    },
    "isolation_forest_anomalies": {
        "key": "isolation_forest_anomalies",
        "display_name": "Isolation Forest Anomaly Outputs",
        "value": 196,
        "entity_type": "Model Density Outlier Detection",
        "source": "data/processed/final_fused_events.parquet (iforest_agreement == True)",
        "calculation_method": (
            "Unsupervised 16-feature Isolation Forest (contamination = 0.05, 100 estimators) trained on 2021-2024 "
            "industrial baseline data. Detects statistical density outliers in multi-dimensional feature space."
        ),
        "unit": "Statistical Density Outliers",
        "geographic_scope": "10 Major Industrial Corridors in India",
        "temporal_scope": "2021-2024 Multi-Year Training Baseline",
        "satellite_sensors": ["Suomi-NPP VIIRS (I-Band 375 m)"],
        "interpretation_limitations": (
            "Statistical anomaly indicates departure from historical background distribution. "
            "It does NOT equal combustion fire probability or judicial violation."
        ),
    },
    "active_follow_up_tasks": {
        "key": "active_follow_up_tasks",
        "display_name": "Active Operational Follow-up Tasks",
        "value": 6,
        "entity_type": "Operational Task Tracking Item",
        "source": "PostgreSQL follow_up_tasks table",
        "calculation_method": (
            "Actionable field investigation, sensor telemetry check, and compliance audit tasks created by "
            "analysts to track remediation or verification of priority thermal anomalies."
        ),
        "unit": "Operational Workflow Tasks",
        "geographic_scope": "Assigned industrial regions",
        "temporal_scope": "Active operational lifecycle (status != 'COMPLETED')",
        "satellite_sensors": ["N/A"],
        "interpretation_limitations": (
            "Dynamic operational queue reflecting human analyst workload and field inspection tracking."
        ),
    },
    "mapped_osm_facilities": {
        "key": "mapped_osm_facilities",
        "display_name": "Mapped OSM Industrial Facilities",
        "value": 2423,
        "entity_type": "PostGIS Infrastructure Vector Polygon/Multipolygon",
        "source": "PostgreSQL osm_facilities table",
        "calculation_method": (
            "Curated OpenStreetMap infrastructure polygons across power generation, petroleum refining, "
            "metallurgy, chemical processing, and mining sectors within India."
        ),
        "unit": "Registered Facility Polygons",
        "geographic_scope": "Pan-India Monitored Industrial Sectors",
        "temporal_scope": "OpenStreetMap 2026 Ingestion Snapshot",
        "satellite_sensors": ["N/A (Geospatial Ground Reference)"],
        "interpretation_limitations": (
            "OpenStreetMap community data provides physical boundary context. Unmapped informal industries "
            "or newly constructed facilities may be absent from OSM cartography."
        ),
    },
    "database_fire_detections": {
        "key": "database_fire_detections",
        "display_name": "Operational Database VIIRS Detections",
        "value": 853,
        "entity_type": "Raw Satellite VIIRS Hotspot Record",
        "source": "PostgreSQL fire_detections table",
        "calculation_method": (
            "Direct API ingestion from NASA FIRMS active fire feed for NOAA-21 (primary) and NOAA-20 (secondary) "
            "VIIRS 375 m I-band sensors."
        ),
        "unit": "Satellite Pixel Hotspot Detections",
        "geographic_scope": "10 Monitored Industrial Regions",
        "temporal_scope": "Current Operational VIIRS Monitoring Stream",
        "satellite_sensors": ["NOAA-21 VIIRS (430)", "NOAA-20 VIIRS (423)"],
        "interpretation_limitations": (
            "Direct pixel-level satellite observations subject to cloud occlusion, sun glint filters, "
            "and off-nadir spatial smearing at scan edges."
        ),
    },
}


def get_metric_dictionary() -> Dict[str, Any]:
    """Retrieve the complete dictionary of audited operational metrics."""
    return {
        "status": "success",
        "version": "KRATOS_V3_PHASE2_AUDITED",
        "total_populations": len(METRIC_DICTIONARY),
        "metrics": METRIC_DICTIONARY,
    }


def get_metric_definition(metric_key: str) -> Dict[str, Any]:
    """Lookup specific metric metadata by key."""
    if metric_key in METRIC_DICTIONARY:
        return {"status": "success", "metric": METRIC_DICTIONARY[metric_key]}
    return {"status": "error", "message": f"Metric key '{metric_key}' not found in dictionary"}
