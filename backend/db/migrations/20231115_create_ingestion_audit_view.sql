-- Migration: 20231115_create_ingestion_audit_view.sql
-- Description: Ingestion audit view tracking pipeline status, detection counts, and enrichment provenance

CREATE OR REPLACE VIEW ingestion_audit AS
SELECT
    s.id AS sync_id,
    s.status AS pipeline_status,
    s.last_attempt_at,
    s.last_successful_sync,
    s.records_received,
    s.new_records,
    s.duplicates,
    s.prediction_failures,
    s.error AS last_error,
    (SELECT COUNT(*) FROM fire_detections) AS total_stored_detections,
    (SELECT COUNT(*) FROM monitoring_fire_events) AS total_monitoring_events,
    (SELECT COUNT(*) FROM fire_alerts) AS total_alerts,
    (SELECT COUNT(*) FROM osm_facilities) AS total_osm_facilities,
    (SELECT MAX(acquisition_time) FROM fire_detections) AS latest_detection_time,
    'VIIRS_NOAA20_NRT,VIIRS_NOAA21_NRT' AS active_satellite_sources,
    'OSM_Overpass_API' AS osm_source,
    NOW() AS audit_generated_at
FROM firms_sync_state s
WHERE s.id = 1;
