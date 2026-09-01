# KRATOS V3.1 — System Architecture & Component Design

KRATOS V3.1 is an enterprise-grade geospatial surveillance platform designed for monitoring, characterizing, and evaluating thermal anomalies across industrial corridors, energy generation infrastructure, and forest landscapes.

```mermaid
flowchart TD
    subgraph DataIngestion ["1. Data Ingestion & Remote Sensing"]
        FIRMS["NASA FIRMS API\n(NOAA-20 / NOAA-21 VIIRS 375m)"]
        OSM["OpenStreetMap (OSM)\n(2,423 Industrial Infrastructure Polygons)"]
        WorldCover["ESA WorldCover\n(10m Landcover Categorization)"]
    end

    subgraph StorageLayer ["2. Storage & Geospatial Layer"]
        Postgres[("PostgreSQL 18 + PostGIS 3.6\n(wildfire_db)")]
        ParquetArchive[("Parquet Historical Archive\n(8,891 Events: 2021-2025\n312 Corroborated Sources)")]
        AuditStore[("HMAC-SHA256 Chained\nSystem Audit Log")]
    end

    subgraph AnalyticalEngine ["3. Multi-Model Intelligence & Analytics"]
        IForest["Isolation Forest Pipeline\n(16-Feature Spatial-Radiometric Outlier)"]
        MAD["Robust Statistical Deviation\n(MAD z-scores & P95/P99 Quantiles)"]
        CUSUM["CUSUM Change Detection\n(Sequential Step-Shift Monitoring)"]
        PriorityEngine["Operational Priority Engine\n(CRITICAL / HIGH / MEDIUM / LOW)"]
    end

    subgraph ApplicationBackend ["4. Flask Backend & WSGI"]
        WSGI["Waitress / Gunicorn WSGI\n(Port 5000, 8 Threads)"]
        AuthRBAC["JWT Auth & RBAC\n(Sliding-Window Rate Limiter)"]
        ReportService["Report Intelligence Engine\n(Evidence Synthesis & Signed PDF)"]
        FollowUpService["Follow-Up Task Management\n(Idempotent Queue Lifecycle)"]
        SSRFGuard["SSRF-Hardened Integrations\n(Connector Directory & Sync Jobs)"]
    end

    subgraph ClientUI ["5. React 19 Frontend (Vite)"]
        ViteDev["Vite Dev / Staging Server\n(Port 5173, Reverse Proxy)"]
        LeafletMap["Interactive GIS Map\n(Leaflet + Heatmaps + Clusters)"]
        InvestigationDrawer["Target Investigation & AI Chat\n(Dossier Drawer & Gemini Agent)"]
        Workspaces["Operational Workspaces\n(Reports, Follow-Ups, Analytics, Integrations)"]
    end

    FIRMS --> Postgres
    OSM --> Postgres
    WorldCover --> Postgres
    ParquetArchive --> AnalyticalEngine

    Postgres <--> ApplicationBackend
    AuditStore <--> ApplicationBackend
    AnalyticalEngine <--> ApplicationBackend

    ApplicationBackend <--> ViteDev
    ViteDev --> LeafletMap
    ViteDev --> InvestigationDrawer
    ViteDev --> Workspaces
```

## Core Architectural Subsystems

### 1. Ingestion & Spatial Preprocessing
- **Satellite Feeds:** Actively queries NASA FIRMS Area API for NOAA-20 and NOAA-21 VIIRS 375m active fire detections across designated regional bounding boxes.
- **Deduplication:** Spatial-temporal clustering within 500 meters and 90 minutes prevents multiple satellite line-of-sight counts from ballooning hotspot statistics.
- **Facility Association:** PostGIS ST_DWithin and ST_Intersects joins locate thermal detections within 1,000 meters of 2,423 mapped industrial assets.

### 2. Analytical Intelligence Layer
- **Multi-Model Consensus:** Blends multivariate unsupervised machine learning with deterministic statistical methods to reduce false alarms from routine flaring or seasonal agriculture.
- **Deterministic Priority Index:** Produces a standardized priority score (0–100) combining Fire Radiative Power (MW), temperature excursion above baseline, persistence, infrastructure proximity, and environmental vulnerability.

### 3. Application Services & Security
- **Production WSGI:** Dual-stack deployment via Waitress (Windows environments) and Gunicorn (Linux environments) with thread-safe connection pooling.
- **Cryptographic Audit Trail:** Every report creation, status escalation, and connector registration appends a cryptographically chained HMAC-SHA256 entry.
