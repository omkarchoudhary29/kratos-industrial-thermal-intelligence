# KRATOS V3.1 — Data Stores & Spatial Baseline Catalog

This directory contains the core historical observations, preprocessed geospatial layers, and empirical baselines powering KRATOS V3.1.

## 1. Directory Structure

```text
data/
├── processed/
│   ├── final_fused_events.parquet           # 8,891 historical fused thermal events (2021–2025)
│   ├── thermal_sources.parquet              # 312 persistent thermal source locations
│   └── facility_association_summary.json    # Pre-computed facility-to-source spatial joins
├── static/                                  # Spatial boundaries, state geometries, GeoJSON layers
├── events/                                  # Cached FIRMS ingest buffers and partition indices
└── raw/                                     # Raw satellite telemetry payloads
```

## 2. Core Datasets & Provenance

### `data/processed/final_fused_events.parquet`
- **Record Count:** 8,891 thermal events.
- **Temporal Span:** January 4, 2021 through December 31, 2025.
- **Sensors:** S-NPP VIIRS, NOAA-20 VIIRS, NOAA-21 VIIRS (375m spatial resolution, I-band 3.75 µm).
- **Key Columns:**
  - `latitude`, `longitude`: WGS84 EPSG:4326 coordinates.
  - `frp`: Fire Radiative Power in Megawatts (MW).
  - `bright_ti4`: 375m I-4 brightness temperature (Kelvin).
  - `bright_ti5`: 375m I-5 thermal infrared brightness temperature (Kelvin).
  - `acq_datetime`: ISO 8601 UTC acquisition timestamp.
  - `satellite`: Sensor platform (`NOAA-20`, `NOAA-21`, `S-NPP`).
  - `daynight`: Solar illumination indicator (`D` / `N`).
  - `region_id`: Associated monitoring corridor or landscape.
  - `confidence`: NASA detection confidence metric.

### `data/processed/thermal_sources.parquet`
- **Record Count:** 312 distinct persistent thermal sources.
- **Corroboration:** Sources identified through spatial density clustering and cross-referenced with 2,423 mapped OpenStreetMap (OSM) industrial infrastructure polygons.
- **Attributes:** Source ID, cluster affiliation, nearest facility name, facility sector, historical event frequency, and mean FRP.

## 3. Data Licensing & Scientific Attribution

1. **NASA FIRMS Active Fire Data:**
   - Provided by NASA's Land, Atmosphere Near-real-time Capability for EOS (LANCE).
   - Citation: *NASA Near Real-Time and MCD14DL VIIRS Active Fire Detections.*
2. **OpenStreetMap (OSM):**
   - Industrial boundary polygons provided under Open Data Commons Open Database License (ODbL).
   - © OpenStreetMap contributors.
3. **ESA WorldCover 2021:**
   - Global land cover at 10m resolution provided by European Space Agency (ESA) WorldCover Consortium.
