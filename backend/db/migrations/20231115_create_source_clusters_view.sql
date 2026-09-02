-- Migration: 20231115_create_source_clusters_view.sql
-- Description: Spatial density clustering of fire detections using PostGIS ST_ClusterDBSCAN projected to EPSG:7755 (India metric)

CREATE OR REPLACE VIEW source_clusters AS
WITH clustered_points AS (
    SELECT
        id,
        detection_key,
        monitoring_region_id,
        latitude,
        longitude,
        location,
        acquisition_time,
        frp,
        brightness,
        satellite,
        instrument,
        land_cover,
        ST_ClusterDBSCAN(ST_Transform(location, 7755), eps := 300, minpoints := 2) 
            OVER (PARTITION BY monitoring_region_id ORDER BY acquisition_time) AS cluster_id
    FROM fire_detections
    WHERE location IS NOT NULL
),
cluster_aggregates AS (
    SELECT
        monitoring_region_id,
        cluster_id,
        COUNT(*) AS observation_count,
        MIN(acquisition_time) AS first_seen,
        MAX(acquisition_time) AS last_seen,
        ROUND(EXTRACT(EPOCH FROM (MAX(acquisition_time) - MIN(acquisition_time))) / 86400.0, 2) AS duration_days,
        COUNT(DISTINCT DATE(acquisition_time)) AS active_days,
        AVG(latitude) AS center_lat,
        AVG(longitude) AS center_lon,
        AVG(frp) AS mean_frp,
        MAX(frp) AS max_frp,
        AVG(brightness) AS mean_brightness,
        MAX(brightness) AS max_brightness,
        ST_Centroid(ST_Collect(location)) AS centroid,
        ST_ConvexHull(ST_Collect(location)) AS cluster_geom
    FROM clustered_points
    WHERE cluster_id IS NOT NULL
    GROUP BY monitoring_region_id, cluster_id
)
SELECT
    monitoring_region_id,
    cluster_id,
    'cluster_' || COALESCE(monitoring_region_id::text, '0') || '_' || cluster_id::text AS cluster_key,
    observation_count,
    first_seen,
    last_seen,
    duration_days,
    active_days,
    center_lat,
    center_lon,
    ROUND(mean_frp::numeric, 2) AS mean_frp,
    ROUND(max_frp::numeric, 2) AS max_frp,
    ROUND(mean_brightness::numeric, 2) AS mean_brightness,
    ROUND(max_brightness::numeric, 2) AS max_brightness,
    CASE 
        WHEN active_days >= 7 THEN 'HIGH'
        WHEN active_days >= 3 OR observation_count >= 5 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS persistence_level,
    centroid,
    cluster_geom
FROM cluster_aggregates;
