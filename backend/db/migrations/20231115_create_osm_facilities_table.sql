-- Migration: 20231115_create_osm_facilities_table.sql
-- Description: Create osm_facilities table with PostGIS geometry support for points, lines, and polygons

CREATE TABLE IF NOT EXISTS osm_facilities (
    id BIGSERIAL PRIMARY KEY,
    osm_id BIGINT NOT NULL,
    osm_type VARCHAR(16) NOT NULL, -- 'node', 'way', 'relation'
    name TEXT,
    facility_category VARCHAR(64) NOT NULL, -- 'industrial', 'power', 'mine', 'refinery', 'substation', etc.
    subcategory VARCHAR(64),
    region_id INTEGER REFERENCES fire_events(id) ON DELETE SET NULL,
    region_name VARCHAR(128),
    tags JSONB,
    geometry GEOMETRY(Geometry, 4326) NOT NULL,
    centroid GEOMETRY(Point, 4326) NOT NULL,
    source VARCHAR(32) DEFAULT 'osm_overpass',
    retrieved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_osm_facilities_type_id UNIQUE (osm_type, osm_id)
);

CREATE INDEX IF NOT EXISTS ix_osm_facilities_geom ON osm_facilities USING GIST (geometry);
CREATE INDEX IF NOT EXISTS ix_osm_facilities_centroid ON osm_facilities USING GIST (centroid);
CREATE INDEX IF NOT EXISTS ix_osm_facilities_region_id ON osm_facilities (region_id);
CREATE INDEX IF NOT EXISTS ix_osm_facilities_category ON osm_facilities (facility_category);
