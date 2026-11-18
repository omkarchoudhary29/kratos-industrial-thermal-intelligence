# KRATOS V3.1 — Industrial Thermal Intelligence & Geospatial Risk Assessment Platform

[![Backend Regression Suite](https://img.shields.io/badge/Tests-140%2F140%20Passed%20(100%25)-success.svg)](backend/tests/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%2018.0%20%2B%20PostGIS%203.6-blue.svg)](https://postgis.net/)
[![Python](https://img.shields.io/badge/Python-3.12%20(64--bit)-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6.svg?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![React](https://img.shields.io/badge/React-19.0-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Flask](https://img.shields.io/badge/Flask-3.1-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.6-F7931E.svg?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Security Audit](https://img.shields.io/badge/Audit-HMAC--SHA256%20Chained-darkgreen.svg)](docs/security.md)
[![Production WSGI](https://img.shields.io/badge/WSGI-Waitress%20%7C%20Gunicorn-orange.svg)](docs/deployment.md)

> **KRATOS V3.1** is an enterprise-grade geospatial surveillance platform designed for continuous monitoring, anomaly characterization, and risk evaluation of high-temperature thermal emissions across heavy industrial corridors, energy generation infrastructure, and forest landscapes.

---

## 1. Project Status Summary

| Subsystem / Dimension | Implementation State | Verification Evidence | Operational Status |
| :--- | :--- | :--- | :---: |
| **Backend API & WSGI** | Flask 3.1, dual Waitress/Gunicorn runners | `backend/wsgi.py`, `backend/gunicorn.conf.py` | **OPERATIONAL (Port 5000)** |
| **Frontend Web Client** | React 19, TypeScript 5.5, Vite 5, Tailwind CSS | 0 TypeScript errors; bundle built in 38.3s | **OPERATIONAL (Port 5173)** |
| **Database Engine** | PostgreSQL 18.0 + PostGIS 3.6 | `wildfire_db` (8,891 events, 312 sources, 2,423 OSM assets) | **OPERATIONAL (Port 5432)** |
| **Test Database Sandbox** | Dedicated `wildfire_test_db` | 140 / 140 regression tests passed in 80.7s | **ISOLATED & VERIFIED** |
| **Machine Learning Engine** | 16-feature Isolation Forest + MAD + CUSUM | `models/industrial_iforest_train_2021_2024.joblib` | **CALIBRATED (Consensus)** |
| **Audit Log Integrity** | HMAC-SHA256 predecessor hash chaining | PostgreSQL trigger `audit_log_immutability_guard` | **CRYPTOGRAPHICALLY SECURED** |
| **Threat Defenses** | Sliding-window rate limiter, SSRF CIDR guard | `backend/utils/rate_limiter.py`, `backend/api/integrations.py` | **HARDENED** |
| **Containerization** | Multi-stage Dockerfile, Docker Compose | `Dockerfile`, `docker-compose.prod.yml` | **DEPLOYMENT READY** |

---

## 2. Executive Overview & Problem Statement

High-temperature industrial processes—including blast furnace steel production, petrochemical cracking, captive power generation, cement clinker kilns, and open-cast coal mining—routinely emit high-energy thermal radiation detectable by spaceborne Earth-observation sensors.

Conventional satellite wildfire alerting platforms (such as standard FIRMS alerts) produce overwhelming false-alarm rates when deployed across industrial corridors, because they treat all high-radiance thermal anomalies as open wildland blazes. Conversely, uncontained industrial runaway events, unauthorized night burning, structural flare failures, and encroaching wildfire frontiers near hazardous petrochemical infrastructure can go undetected without rigorous baseline differentiation.

**KRATOS V3.1 solves this operational challenge through continuous multi-source evidence fusion:**
1. **Remote Sensing Telemetry:** Integrates VIIRS 375m I-band active fire data from NOAA-20, NOAA-21, and Suomi-NPP satellites.
2. **Geospatial Infrastructure Corroboration:** Cross-references satellite observations against 2,423 mapped OpenStreetMap (OSM) heavy industrial polygons and 312 persistent physical thermal source clusters.
3. **Multi-Model Anomaly Consensus:** Synthesizes an unsupervised 16-feature Isolation Forest, facility-specific Median Absolute Deviation (MAD) modified z-scores, and sequential CUSUM drift detection to differentiate routine flaring from true operational excursions.
4. **Evidence-Grounded Dossiers & Follow-Up Workflows:** Generates auditable operational investigation dossiers, cryptographically signed PDF reports, and provides an authoritative Generative AI Investigator powered by Google Gemini.

---

## 3. Core Platform Capabilities

- **Pan-India Geospatial Surveillance:** Continuous coverage across 10 strategic geographic zones (6 industrial energy corridors and 4 forest fire landscapes).
- **5-Year Historical Baseline Archive:** Longitudinal temporal filtering across 8,891 fused thermal events spanning January 4, 2021 through December 31, 2025.
- **Persistent Thermal Source Clustering:** PostGIS DBSCAN spatial clustering identifying 312 corroborated persistent physical emission sources.
- **Topological Infrastructure Association:** PostGIS ST_DWithin joins locating thermal detections within 1,000 meters of 2,423 mapped industrial assets.
- **Multi-Model Anomaly Consensus Engine:** 3-model agreement architecture eliminating false alarms from routine operational flaring.
- **Deterministic Operational Priority Index:** Standardized prioritization scale (CRITICAL, HIGH, MEDIUM, LOW) combining FRP (MW), baseline temperature excursion, infrastructure proximity, recurrence, and environmental vulnerability.
- **Interactive GIS Geospatial UI:** High-performance Leaflet mapping with clustered heatmaps, satellite tile layers, facility boundary polygons, and diurnal cycle breakdown.
- **Evidence-Grounded AI Investigator:** Natural-language geospatial chat powered by Google Gemini with strict prompt guardrails grounded in verified database telemetry.
- **Investigation Report Intelligence:** Automated report generation with dynamic executive summaries, evidence tables, regulatory authority filing tracking, and signed PDF exports.
- **Idempotent Follow-Up Task Management:** Operational triage queue with assignee management, escalation workflows, overdue tracking, and immutable audit notes.
- **SSRF-Hardened Integrations Directory:** Enterprise connector management with strict RFC 1918, loopback, and cloud metadata CIDR protection.
- **Cryptographic Audit Trail:** HMAC-SHA256 predecessor hash chaining on all operational audit logs backed by PostgreSQL trigger immutability.

---

## 4. System Architecture

```mermaid
flowchart TD
    subgraph DataIngestion ["1. Data Ingestion & Remote Sensing"]
        FIRMS["NASA FIRMS API\n(NOAA-20 / NOAA-21 / S-NPP VIIRS 375m)"]
        OSM["OpenStreetMap (OSM)\n(2,423 Industrial Facilities)"]
        WorldCover["ESA WorldCover\n(10m Land Cover Grid)"]
        ERA5["ECMWF ERA5-Land\n(Atmospheric Reanalysis)"]
    end

    subgraph StorageLayer ["2. Storage & Geospatial Database"]
        Postgres[("PostgreSQL 18 + PostGIS 3.6\n(wildfire_db)")]
        ParquetStore[("Historical Parquet Store\n(8,891 Events: 2021–2025\n312 Corroborated Sources)")]
        AuditChain[("HMAC-SHA256 Chained\nAudit Log Ledger")]
    end

    subgraph AnalyticalEngine ["3. Multi-Model Intelligence & Analytics"]
        IForest["Isolation Forest Pipeline\n(16 Normalized Radiometric Features)"]
        MAD["Robust Statistical Deviation\n(MAD z-scores & P95/P99 Quantiles)"]
        CUSUM["CUSUM Change Detection\n(Sequential Structural Shift Monitor)"]
        PriorityEngine["Operational Priority Engine\n(CRITICAL / HIGH / MED / LOW)"]
    end

    subgraph ApplicationBackend ["4. Flask Backend & WSGI Layer"]
        WSGI["Waitress / Gunicorn WSGI\n(Port 5000, 8 Threads)"]
        AuthRBAC["JWT Auth & Sliding-Window Limiter\n(HS256 + Refresh Token Rotation)"]
        ReportEngine["Report Intelligence Engine\n(Evidence Synthesis & Signed PDF)"]
        FollowUpQueue["Follow-Up Lifecycle\n(Idempotent Task Management)"]
        SSRFGuard["SSRF-Hardened Integrations\n(CIDR & Metadata Blocking)"]
    end

    subgraph ClientUI ["5. React 19 Frontend (Vite)"]
        ViteDev["Vite Production / Staging Server\n(Port 5173, Reverse Proxy)"]
        LeafletMap["Interactive GIS Map\n(Leaflet + Clusters + Heatmaps)"]
        TargetDrawer["Target Investigation Drawer\n(Dossier & AI Investigator)"]
        Workspaces["Operational Workspaces\n(Reports, Follow-Ups, Analytics)"]
    end

    FIRMS --> Postgres
    OSM --> Postgres
    WorldCover --> Postgres
    ERA5 --> Postgres
    ParquetStore --> AnalyticalEngine

    Postgres <--> ApplicationBackend
    AuditChain <--> ApplicationBackend
    AnalyticalEngine <--> ApplicationBackend

    ApplicationBackend <--> ViteDev
    ViteDev --> LeafletMap
    ViteDev --> TargetDrawer
    ViteDev --> Workspaces
```

---

## 5. Verified Dataset & Empirical Baseline Metrics

| Metric | Verified Empirical Quantity | Provenance & Validation |
| :--- | :---: | :--- |
| **Fused Historical Thermal Events** | **8,891** | VIIRS S-NPP, NOAA-20, NOAA-21 (375m I-band, 2021–2025) |
| **Corroborated Thermal Sources** | **312** | Recurrence-verified industrial emission clusters ($minPts \ge 2$) |
| **Mapped Industrial Facilities** | **2,423** | OpenStreetMap (OSM) heavy industry, energy, and mining assets |
| **Monitored Strategic Regions** | **10** | 6 heavy industrial corridors + 4 forest conservation landscapes |
| **Historical Baseline Period** | **5 Years** | Continuous observations from January 4, 2021 to December 31, 2025 |
| **Spatial Deduplication Radius** | **500 meters** | Eliminates duplicate counts within 90-minute satellite overpasses |
| **Facility Match Radius** | **1,000 meters** | PostGIS topological join connecting hotspots to nearest infrastructure |

### Strategic Monitoring Corridors & Landscapes

| # | Region Identifier | Region Name | State | Type | Core Monitored Infrastructure / Landscape |
| :-: | :--- | :--- | :--- | :---: | :--- |
| 1 | `vijayanagar` | Vijayanagar / Toranagallu | Karnataka | Industrial | Integrated steel manufacturing, pellet plants, captive thermal energy |
| 2 | `talcher` | Talcher / Angul | Odisha | Industrial | Open-cast coal mining basins, super thermal power, aluminum smelting |
| 3 | `dhanbad` | Dhanbad / Bokaro | Jharkhand | Industrial | Coking coal pits, blast furnace steel complexes, heavy engineering |
| 4 | `singrauli` | Singrauli / Sonbhadra | MP / UP | Industrial | Pithead thermal power super-stations, coal seams, ash ponds |
| 5 | `korba` | Korba Industrial Hub | Chhattisgarh | Industrial | Thermal energy complexes, captive power units, aluminum manufacturing |
| 6 | `jamnagar` | Jamnagar / Vadinar | Gujarat | Industrial | World's largest petroleum refinery complexes, petrochemical crackers |
| 7 | `gadchiroli` | Gadchiroli Forest Frontier | Maharashtra | Forest | Tropical dry and moist deciduous teak forest frontiers |
| 8 | `kanha` | Kanha Conservation Landscape | Madhya Pradesh | Forest | Protected tiger corridor, moist sal forest biomes |
| 9 | `bastar` | Bastar Forest Reserve | Chhattisgarh | Forest | Dense sal and teak forest canopy reserves |
| 10 | `mizoram` | Mizoram Montane Frontier | Mizoram | Forest | Hilly montane bamboo forests and jhum rotational agro-forestry |

---

## 6. AI & Machine Learning Methodology

KRATOS evaluates thermal detections through a multi-model consensus architecture to eliminate false alarms caused by routine flaring or cyclical kiln operations.

```
                  ┌──────────────────────────────────────────────┐
                  │ VIIRS 375m Active Fire Detection Telemetry    │
                  └──────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────┼───────────────────────┐
                 ▼                       ▼                       ▼
      ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
      │      Model 1        │ │      Model 2        │ │      Model 3        │
      │ Multivariate        │ │ Robust Statistical  │ │ CUSUM Sequential    │
      │ Isolation Forest    │ │ Deviation (MAD)     │ │ Change Detection    │
      │ (16 Features)       │ │ (Z-score & Quantiles│ │ (Structural Shift)  │
      └──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘
                 │                       │                       │
                 └───────────────────────┼───────────────────────┘
                                         ▼
                      ┌────────────────────────────────────┐
                      │    Multi-Model Consensus Engine    │
                      │   (Weighted Agreement Decision)    │
                      └──────────────────┬─────────────────┘
                                         ▼
                      ┌────────────────────────────────────┐
                      │    Operational Priority Index      │
                      │  (0-100: CRITICAL/HIGH/MED/LOW)    │
                      └────────────────────────────────────┘
```

### 16-Feature Isolation Forest Vector

The primary machine learning model (`models/industrial_iforest_train_2021_2024.joblib`) uses an unsupervised ensemble of 100 decision trees trained on normalized historical VIIRS telemetry:

| # | Feature Name | Description | Physical Interpretation |
| :-: | :--- | :--- | :--- |
| 1 | `bright_ti4` | VIIRS I-4 brightness temp (Kelvin) | 3.75 µm mid-infrared thermal radiance |
| 2 | `bright_ti5` | VIIRS I-5 brightness temp (Kelvin) | 11.45 µm longwave infrared thermal radiance |
| 3 | `temp_ratio_ti4_ti5` | Ratio $\frac{T_4}{T_5}$ | Spectral gradient separating flames from warm background |
| 4 | `frp` | Fire Radiative Power (MW) | Total instantaneous radiant energy output |
| 5 | `log_frp` | $\log(1 + \text{FRP})$ | Non-linear scaling for high-power thermal excursions |
| 6 | `solar_zenith_angle` | Solar zenith angle (degrees) | Sun position for solar glint correction |
| 7 | `solar_azimuth_angle` | Solar azimuth angle (degrees) | Solar orientation relative to the sensor path |
| 8 | `scan_angle` | Off-nadir scan angle (degrees) | Accounts for pixel enlargement toward scan edge |
| 9 | `track_pixel_size` | Sensor ground track pixel size (km) | Geometric pixel footprint adjustment |
| 10 | `recurrence_rate_30d` | Hotspot count in 30-day window | Differentiates permanent flares from episodic fires |
| 11 | `recurrence_rate_365d`| Hotspot count in 365-day window | Multi-season operational continuity indicator |
| 12 | `facility_distance_m` | Distance to nearest OSM facility | Spatial infrastructure proximity |
| 13 | `landcover_builtup` | ESA WorldCover built-up fraction | Built environment containment probability |
| 14 | `landcover_cropland` | ESA WorldCover cropland fraction | Agricultural residue burning indicator |
| 15 | `landcover_forest` | ESA WorldCover forest fraction | Wildland vegetation fuel hazard indicator |
| 16 | `landcover_shrubland`| ESA WorldCover shrubland fraction | Grassland and dry scrub fire fuel indicator |

### Statistical Deviation & Change Detection

- **Model 2: Robust Statistical Deviation (MAD & Quantiles):**
  Calculates the facility-specific Median Absolute Deviation (MAD) modified z-score against historical diurnal passes:
  $$\text{Modified } Z = \frac{0.6745 \cdot (X - \text{median}(X))}{\text{MAD}}$$
  Observations exceeding Modified $Z > 3.0$ or surpassing the corridor 95th/99th percentiles ($P_{95}, P_{99}$) trigger statistical excursion alerts.
- **Model 3: CUSUM Sequential Change Detection:**
  A two-sided tabular cumulative sum detector tracking structural drift in background heat emissions:
  $$S_t^+ = \max(0, S_{t-1}^+ + X_t - \mu_0 - k)$$
  Detects gradual equipment degradation or persistent unpermitted flaring before single-point thresholds trigger.

### Scientific Limitations & Proxy-Label Ground Truth Policy

1. **Proxy Labels vs. Ground Truth:** Across national-scale satellite archives, independent ground-truth confirmation (e.g., proprietary plant SCADA telemetry or municipal fire logs) is unavailable. Model evaluation is calibrated using mathematically defined proxy labels:
   - *Positive Proxy:* High-power excursions ($> P_{99}$ for the corridor) coupled with low historical recurrence.
   - *Negative Proxy:* Corroborated, low-variance recurrent diurnal signatures matching standard furnace operations.
2. **Sub-Pixel Radiance $\ne$ Open Disasters:** VIIRS detections measure sub-pixel thermal infrared radiance within a 375m ground pixel. A high-radiance signal does not confirm an uncontained disaster without on-ground verification.
3. **FRP $\ne$ Internal Operating Temperature:** Fire Radiative Power (MW) quantifies radiant heat release emitted into the open atmosphere, not internal kiln or boiler temperature.
4. **Cloud & Weather Obscuration:** Monsoonal cloud cover and heavy rainfall attenuate thermal infrared radiance, creating temporary observation gaps during severe storm systems.

---

## 7. Application Showcase

The following high-fidelity captures demonstrate the operational capabilities of KRATOS V3.1:

| Overview Surveillance Dashboard | Interactive GIS Map & Spatial Clusters |
| :---: | :---: |
| ![Overview Dashboard](docs/assets/01_overview_dashboard.png) | ![Interactive GIS Map](docs/assets/02_interactive_gis_map.png) |
| *National surveillance overview, active corridor filters, critical KPIs, and recent event feeds.* | *High-performance Leaflet GIS with clustered heatmaps, satellite tiles, and facility boundaries.* |

| Target Investigation & Evidence Dossier | Thermal Analysis & Diurnal Profiles |
| :---: | :---: |
| ![Target Investigation](docs/assets/03_target_investigation.png) | ![Thermal Analysis](docs/assets/04_thermal_analysis_diurnal.png) |
| *Deep-dive investigation drawer displaying multi-model scores and OSM asset co-location.* | *Diurnal pass distributions, FRP time series, and orbital observation cadence.* |

| AI Geospatial Investigator | Formal Investigation Report Preview |
| :---: | :---: |
| ![AI Investigator](docs/assets/05_ai_investigator.png) | ![Report Preview](docs/assets/06_investigation_report_preview.png) |
| *Authoritative natural-language chat powered by Gemini with grounded spatial evidence.* | *Formal narrative synthesis with regulatory authority tracking and cryptographically signed PDF export.* |

| Operational Analytics & KPIs | High-Priority Follow-Up Task Management |
| :---: | :---: |
| ![Operational Analytics](docs/assets/07_operational_analytics.png) | ![Follow-Up Workflow](docs/assets/08_follow_up_workflow.png) |
| *Cross-corridor comparative analytics, model agreement distributions, and trend analysis.* | *Idempotent task triage queue with assignee management, escalation workflows, and audit notes.* |

---

## 8. Repository Organization

```text
industrial-thermal-intelligence/
├── README.md                           # Master authoritative documentation & pre-deployment guide
├── CONTRIBUTING.md                     # Contributor guidelines, branching, and code style standards
├── SECURITY.md                         # Security architecture, threat model, and vulnerability reporting
├── CHANGELOG.md                        # Version history from V3.0 through V3.1.0 RC
├── .env.example                        # Sanitized configuration template with safe defaults
├── .gitignore                          # Hardened exclusions for secrets, dumps, and build caches
├── .dockerignore                       # Container build context exclusions
├── Dockerfile                          # Multi-stage production container build (Python 3.12 + Node 20)
├── docker-compose.prod.yml             # Production multi-service orchestration (DB + Backend + Nginx)
├── requirements.txt                    # Python backend production dependencies
├── conftest.py                         # Pytest configuration and test database isolation hooks
│
├── frontend/                           # React 19 / TypeScript 5.5 SPA
│   ├── src/                            # Application components, views, hooks, and services
│   │   ├── components/                 # Reusable UI components (Modals, Drawers, Cards)
│   │   ├── views/                      # Main views (Dashboard, Map, Analytics, Reports, FollowUps)
│   │   ├── services/                   # Axios API clients, auth helpers, and state stores
│   │   └── types/                      # TypeScript domain interfaces and API payload types
│   ├── package.json                    # Node dependencies and build scripts
│   ├── tsconfig.json                   # Strict TypeScript compiler options
│   └── vite.config.ts                  # Vite build setup with backend reverse-proxy
│
├── backend/                            # Flask backend & analytical engines
│   ├── api/                            # Modular REST API blueprints
│   │   ├── auth.py                     # Authentication, JWT rotation, and login rate limiting
│   │   ├── events.py                   # Thermal event queries, spatial bounding, and details
│   │   ├── reports.py                  # Report generation, PDF export, and submission tracking
│   │   ├── followups.py                # Idempotent task triage and escalation workflows
│   │   ├── integrations.py             # SSRF-guarded external connector directory
│   │   ├── analytics.py                # Operational metrics, corridor comparisons, model consensus
│   │   └── settings.py                 # System health, configuration, and audit log verification
│   ├── agents/                         # Generative AI investigator (Gemini / Claude)
│   ├── services/                       # Multi-model anomaly detection, report intelligence, DBSCAN
│   ├── db/                             # PostgreSQL connection pool and SQLAlchemy ORM models
│   ├── tests/                          # 20 automated regression test suites (140 tests)
│   ├── utils/                          # Sliding-window rate limiter, SSRF guard, audit hasher
│   ├── gunicorn.conf.py                # Linux production WSGI configuration
│   └── wsgi.py                         # Windows / standalone production WSGI entrypoint (Waitress)
│
├── data/                               # Historical datasets & spatial baseline layers
│   ├── processed/                      # Parquet archives (8,891 fused events, 312 sources)
│   ├── static/                         # GeoJSON boundaries and regional masks
│   └── README.md                       # Spatial baseline data dictionary & licensing
│
├── models/                             # Machine learning artifacts
│   ├── industrial_iforest_train_2021_2024.joblib # 16-feature Isolation Forest model
│   └── README.md                       # Model specifications and validation metrics
│
├── docs/                               # In-depth technical guides
│   ├── architecture.md                 # System architecture & component flows
│   ├── methodology.md                  # Remote sensing & anomaly detection algorithms
│   ├── data-sources.md                 # Data providers & spatial coverage details
│   ├── development-setup.md            # Workstation installation & setup guide
│   ├── deployment.md                   # WSGI, Nginx, Docker, and backup runbooks
│   ├── security.md                     # Security architecture & threat defenses
│   ├── model-validation.md             # Proxy-label policy & ML benchmarking
│   └── assets/                         # Curated application screenshots
│
├── scripts/                            # Operational & deployment utilities
│   ├── backup_db.py                    # Verified database backup utility with SHA-256 manifests
│   ├── prepare_demo_database.py        # Demo database provisioning & sanitization script
│   ├── setup_demo_user.py              # Reviewer account provisioning utility
│   ├── run_migrations.py               # Database schema migration runner
│   └── inspect_db_state.py             # Database integrity verification utility
│
└── .github/
    └── workflows/
        ├── backend-tests.yml           # Automated backend CI with PostGIS service container
        └── frontend-build.yml          # Frontend TypeScript build & lint CI
```

---

## 9. Technology Stack & System Prerequisites

### Prerequisites

| Component | Minimum Version | Recommended Version | Purpose |
| :--- | :---: | :---: | :--- |
| **Operating System** | Windows 10/11 (64-bit) or Ubuntu 22.04 LTS | Ubuntu 24.04 LTS / Windows 11 Pro | Deployment host |
| **Python** | 3.11 (64-bit) | 3.12 (64-bit) | Backend & ML execution |
| **Node.js** | 18.0 LTS | 20.0 LTS (with npm 9+) | Frontend tooling & build |
| **PostgreSQL** | 16.0 | 18.0 | Primary relational store |
| **PostGIS** | 3.4 | 3.6 | Geospatial indexing & analysis |
| **System Memory** | 8 GB RAM | 16 GB RAM | Required for spatial joins |
| **Storage** | 20 GB free disk space | 50 GB SSD | Database and Parquet storage |

---

## 10. Local Installation & Setup Guide

### 1. Database Provisioning

Create the operational database `wildfire_db` and isolated test database `wildfire_test_db` in PostgreSQL:

```sql
-- Connect via psql as postgres superuser
CREATE DATABASE wildfire_db;
CREATE DATABASE wildfire_test_db;

\c wildfire_db;
CREATE EXTENSION IF NOT EXISTS postgis;

\c wildfire_test_db;
CREATE EXTENSION IF NOT EXISTS postgis;
```

### 2. Backend Installation (PowerShell / Linux)

```powershell
# Clone the repository
git clone https://github.com/mukesh/industrial-thermal-intelligence.git
cd industrial-thermal-intelligence

# Create and activate Python virtual environment
python -m venv .venv
.\.venv\Scripts\activate            # Windows PowerShell
# source .venv/bin/activate          # Linux / macOS

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment variables
Copy-Item .env.example .env         # Windows PowerShell
# cp .env.example .env               # Linux / macOS
```

Update your `.env` file with your local PostgreSQL password, secret keys, and optional API keys.

### 3. Database Migrations & Initial Setup

```powershell
# Apply database migrations
python scripts/run_migrations.py

# Seed the demo reviewer account (for testing and showcase)
python scripts/setup_demo_user.py
```

### 4. Frontend Installation & Build Verification

```powershell
cd frontend
npm install
npm run build                       # Verifies TypeScript compilation and creates dist/
```

### 5. Running the Application Locally

**Terminal 1 — Backend Production WSGI (Waitress on Port 5000):**
```powershell
.\.venv\Scripts\python.exe backend/wsgi.py
```

**Terminal 2 — Frontend Dev Server with Reverse Proxy (Vite on Port 5173):**
```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 11. Environment Variables Reference

| Variable Name | Default Value | Required | Purpose & Security Guidance |
| :--- | :---: | :---: | :--- |
| `APP_MODE` | `development` | Yes | `development`, `demo`, or `production`. `demo` blocks destructive actions and external submissions. |
| `DATABASE_URL` | `postgresql://postgres:password@localhost:5432/wildfire_db` | Yes | Connection URI for the primary operational PostgreSQL database. |
| `TEST_DATABASE_URL` | `postgresql://postgres:password@localhost:5432/wildfire_test_db` | Yes | Connection URI for the isolated test database used by automated pytest suites. |
| `JWT_SECRET_KEY` | *(Must be generated)* | Yes | 64-character random string used for HMAC-SHA256 JWT access token signing. |
| `JWT_ACCESS_TOKEN_MINUTES` | `15` | No | Lifespan of short-lived JWT access tokens in minutes. |
| `JWT_REFRESH_TOKEN_DAYS` | `30` | No | Lifespan of rotating refresh tokens in days. |
| `ADMIN_USERNAME` | `admin` | Yes | Initial administrator username. |
| `ADMIN_PASSWORD` | *(Change before deploy)* | Yes | Initial administrator password. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:5000` | Yes | Comma-separated list of permitted CORS origins. Never set to `*` in production. |
| `WAITRESS_THREADS` | `8` | No | Number of worker threads for the Waitress production WSGI server. |
| `LLM_PROVIDER` | `claude` (code default) | No | AI provider for the Investigator agent (`gemini`, `claude`, or `none`). Set `gemini` explicitly when using Google AI Studio. |
| `GEMINI_API_KEY` | *(Required when `LLM_PROVIDER=gemini`)* | No | Google AI Studio key. Current code defaults to `gemini-3.1-flash-lite` with `gemini-3.6-flash` as fallback unless model variables override them. |
| `ANTHROPIC_API_KEY` | *(Optional)* | No | Anthropic API key for Claude 3.5 Sonnet reasoning. |
| `FIRMS_API_KEY` | *(Optional)* | No | NASA LANCE FIRMS MAP_KEY for near-real-time satellite ingestion. |

---

## 12. Authentication, Authorization & Security Architecture

1. **Dual-Token Session Lifecycle:**
   - Stateless 15-minute JWT access tokens signed with HMAC-SHA256 (`HS256`).
   - Cryptographically hashed (SHA-256) rotating refresh tokens stored in PostgreSQL with family ID tracking to detect token reuse or theft.
2. **Password Security:**
   - Salted and hashed using `bcrypt` (12 work factor rounds) with 72-byte truncation guards.
3. **Sliding-Window Rate Limiting:**
   - In-memory thread-safe sliding-window rate limiters defend sensitive endpoints:
     - `/auth/login`: 5 attempts per 60 seconds (IP + username keyed).
     - `/api/v1/reports/generate`: 10 requests per 60 seconds.
     - `/events/<id>/chat`: 20 requests per 60 seconds.
   - Responds with standard HTTP 429 and `Retry-After` header.
4. **Server-Side Request Forgery (SSRF) Defense:**
   - External connector registration validates destination hostnames against loopback, private RFC 1918 subnets, and cloud metadata endpoints (`169.254.169.254`).
5. **Cryptographic Audit Trail:**
   - Every report creation, follow-up status escalation, and connector registration appends an immutable HMAC-SHA256 chained entry to `system_audit_logs`.
   - PostgreSQL trigger `audit_log_immutability_guard` blocks any SQL `UPDATE` or `DELETE` on the audit ledger.
   - Endpoint `GET /api/v1/settings/audit-logs/verify-chain` verifies chain continuity from the genesis record.
6. **Demonstration Mode Guardrails (`APP_MODE=demo`):**
   - General public reviewers can inspect the live map, generate draft reports, and query the AI Investigator.
   - External authority submissions (`POST /api/v1/submissions/record`) and external sync jobs are safely blocked (HTTP 403).

---

## 13. Database Architecture & Migrations

### Core Tables & Spatial Indices

| Table Name | Description | Key Columns & Spatial Indices |
| :--- | :--- | :--- |
| `osm_facilities` | 2,423 mapped industrial assets | `facility_id`, `name`, `sector`, `geometry` (PostGIS `GIST`) |
| `source_clusters` | 312 persistent thermal source locations | `source_id`, `region_id`, `centroid` (PostGIS `GIST`), `recurrence_count` |
| `users` | System user credentials & roles | `id`, `username`, `password_hash`, `role`, `is_active` |
| `refresh_tokens` | Rotating token records | `token_hash`, `user_id`, `family_id`, `revoked`, `expires_at` |
| `investigation_reports` | Formal investigation dossiers | `report_id`, `event_id`, `source_id`, `severity`, `pdf_path` |
| `follow_up_tasks` | Operational triage queue | `task_id`, `event_id`, `priority`, `status`, `assigned_to` |
| `external_connectors` | SSRF-checked API endpoints | `connector_id`, `name`, `target_url`, `status`, `last_sync_at` |
| `system_audit_logs` | Immutable audit ledger | `id`, `timestamp`, `event_type`, `predecessor_hash`, `current_hash` |

### Running Migrations

Database migrations are tracked in `scripts/run_migrations.py`. To apply schema updates:

```powershell
python scripts/run_migrations.py
```

---

## 14. Testing & Quality Assurance Suite

KRATOS includes an exhaustive automated regression suite consisting of **20 test modules containing 140 tests**.

```
============================== 140 passed in 80.73s ==============================
```

### Safety & Isolation

- All test runs automatically redirect to `wildfire_test_db` via `conftest.py`.
- Tests never modify or truncate the operational `wildfire_db` database.
- Database connectors in test suites use isolated test user roles without production credentials.

### Running Backend Tests

```powershell
# Run the complete 140-test regression suite
pytest backend/tests/ -v

# Run targeted test suites
pytest backend/tests/test_audit_hash_chain.py -v   # Cryptographic audit chain tests
pytest backend/tests/test_rate_limiter.py -v        # Sliding-window rate limiter tests
pytest backend/tests/test_ssrf_protection.py -v     # SSRF defense tests
pytest backend/tests/test_model_pipeline.py -v      # Isolation Forest & MAD tests
```

---

## 15. Production Deployment & Operations

### 1. Dual WSGI Production Servers

- **Windows Deployment:**
  ```powershell
  python backend/wsgi.py
  # Serves via Waitress on Port 5000 with 8 persistent threads
  ```
- **Linux / Container Deployment:**
  ```bash
  gunicorn -c backend/gunicorn.conf.py wsgi:app
  # Serves via Gunicorn with 4-8 pre-fork worker processes
  ```

### 2. Multi-Stage Docker Stack

KRATOS includes a production-ready Docker Compose orchestration file (`docker-compose.prod.yml`) that coordinates:
- **PostgreSQL 18 + PostGIS 3.6**
- **Production WSGI Backend**
- **Nginx Reverse Proxy** (handling TLS termination and static frontend distribution)

```bash
# Build and launch the production container stack
docker compose -f docker-compose.prod.yml up -d --build
```

### 3. Cloud PaaS Deployment (Railway / Render / AWS)

For single-container cloud PaaS platforms like Railway:
- Set build context to repository root (`Dockerfile`).
- Provision a PostGIS template service (`postgis/postgis:18-3.6`).
- Inject `DATABASE_URL` and configure application environment variables.
- Attach a persistent volume at `/app/data` to ensure downloaded datasets and models persist across redeployments.
- Set Healthcheck Path to `/health` with a 300-second timeout.
- Maintain a single web replica to prevent multi-instance thermal scheduler conflicts.

### 4. Automated Backup & Disaster Recovery Runbook

```bash
# Execute custom-format compressed backup with SHA-256 verification
python scripts/backup_db.py --db wildfire_db --format custom --tag scheduled
```

- **RPO Target:** < 15 minutes (with continuous WAL archiving) / < 24 hours (standalone dumps).
- **RTO Target:** < 30 minutes (dump restore).
- Backups are stored in `backups/wildfire_db_<TIMESTAMP>_scheduled.dump` with SHA-256 checksums in `backups/backup_manifest.json`.

**Database Restoration Steps:**
```bash
# 1. Verify dump archive readability
pg_restore -l backups/wildfire_db_<TIMESTAMP>_scheduled.dump | head -n 30

# 2. Terminate active database sessions
# Run in psql: SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'wildfire_db' AND pid <> pg_backend_pid();

# 3. Restore database cleanly
pg_restore -h localhost -p 5432 -U postgres -d wildfire_db --clean --if-exists --no-owner --no-privileges backups/wildfire_db_<TIMESTAMP>_scheduled.dump

# 4. Verify post-restore integrity
python scripts/inspect_db_state.py
pytest backend/tests/test_audit_hash_chain.py -v
```

---

## 16. Troubleshooting Guide

| Issue / Symptom | Root Cause | Verified Resolution |
| :--- | :--- | :--- |
| **`could not load library "postgis"`** | PostGIS extension is not installed or enabled in PostgreSQL. | Run Stack Builder in PostgreSQL and install PostGIS, or execute `CREATE EXTENSION postgis;` as superuser. |
| **`Port 5000 already in use`** | Another application or previous backend process is holding port 5000. | Identify and terminate the PID: `Get-NetTCPConnection -LocalPort 5000` followed by `Stop-Process -Id <PID>`. |
| **`Port 5432 connection refused`** | PostgreSQL server is stopped or listening on another port. | Start the PostgreSQL Windows service (`Start-Service postgresql*`) or verify the port in `postgresql.conf`. |
| **`HTTP 429 Too Many Requests`** | Sliding-window rate limiter triggered due to burst requests on login or reports. | Respect the `Retry-After` header (wait 60s) or adjust rate limits in `backend/utils/rate_limiter.py` for testing. |
| **`AI Investigator returns generic summary`** | `GEMINI_API_KEY` is unset or invalid. | Obtain a valid key from Google AI Studio and configure `GEMINI_API_KEY=<key>` in `.env`. |
| **`TypeError: Object of type Timestamp is not JSON serializable`** | Pandas Timestamp or NumPy types present in report payload. | Sanitized recursively via `sanitize_json_payload` in `report_intelligence.py` and `api/reports.py`. |
| **`GDAL / rasterio import error on Windows`** | Binary wheel mismatch with system C libraries. | Install pre-compiled wheels from Christoph Gohlke or use the Dockerized environment (`docker-compose.prod.yml`). |

---

## 17. Public Demonstration Access

When deployed in demonstration mode (`APP_MODE=demo`), pre-configured reviewer credentials are provided for recruiters, interviewers, and technical evaluators:

- **Web Interface URL:** `http://localhost:5173`
- **Username:** `demo_reviewer`
- **Password:** `KratosDemo2026!`
- **Assigned Role:** Standard Operational Reviewer
- **Safety Policy:** Full inspection capabilities across map, dossiers, reports, analytics, and AI chat. Destructive actions and statutory filings are safely disabled.

---

## 18. Pre-Deployment Master Checklist

The following checklist provides a transparent, evidence-grounded assessment of system readiness:

### Section A: System Architecture & Core Stack
- [x] **DONE** Flask 3.1 modular backend with blueprint architecture (`auth`, `events`, `reports`, `followups`, `integrations`, `analytics`, `settings`).
- [x] **DONE** Dual production WSGI runners configured: Waitress on Windows (`backend/wsgi.py`) and Gunicorn on Linux (`backend/gunicorn.conf.py`).
- [x] **DONE** React 19 frontend with TypeScript 5.5, Vite 5, Tailwind CSS, and Leaflet GIS mapping.
- [x] **DONE** Strict separation of configuration between `.env`, `.env.example`, and `.env.test`.

### Section B: Database Engine & Migrations
- [x] **DONE** PostgreSQL 18.0 + PostGIS 3.6 database engine verified on port 5432.
- [x] **DONE** PostGIS spatial indices (`GIST(geometry)`) active on `osm_facilities` and `source_clusters`.
- [x] **DONE** Production database `wildfire_db` loaded with 8,891 events, 312 sources, and 2,423 OSM facilities.
- [x] **DONE** Schema migration runner (`scripts/run_migrations.py`) tracking versions.
- [x] **DONE** Automated test sandbox redirection to `wildfire_test_db` via `conftest.py`.
- [x] **DONE** Database backup script (`scripts/backup_db.py`) with SHA-256 manifests and restore validation.
- [BLOCKED] **BLOCKED** Continuous off-site WAL archiving to cloud bucket (Requires external cloud bucket and IAM credentials).

### Section C: Geospatial & Remote Sensing Ingestion
- [x] **DONE** Multi-satellite VIIRS telemetry processing (NOAA-20, NOAA-21, S-NPP 375m I-band).
- [x] **DONE** Spatial-temporal deduplication (500m radius, 90-minute window) to prevent double-counting.
- [x] **DONE** Facility association joins linking detections within 1,000m of heavy industrial infrastructure.
- [x] **DONE** 10 strategic monitoring corridors configured (6 industrial corridors + 4 forest landscapes).
- [x] **DONE** Background ingestion scheduler (`pipeline/thermal/refresh.py`) for live satellite updates.

### Section D: AI/ML Anomaly Detection & Statistical Pipeline
- [x] **DONE** Scikit-Learn 16-feature Isolation Forest pipeline (`models/industrial_iforest_train_2021_2024.joblib`).
- [x] **DONE** Facility-specific Robust Statistical Deviation model (MAD modified z-scores and $P_{95}/P_{99}$ quantiles).
- [x] **DONE** Sequential CUSUM change detection model for tracking structural heat drift.
- [x] **DONE** Standardized Operational Priority Index (0–100) and severity classification (CRITICAL/HIGH/MED/LOW).
- [x] **DONE** Transparent proxy-label validation policy and scientific disclaimer documentation.

### Section E: Authentication, Authorization & Security Hardening
- [x] **DONE** Dual-token authentication with 15-minute JWT HS256 access tokens and rotating refresh tokens.
- [x] **DONE** Salted bcrypt password hashing with 12 rounds and 72-byte truncation protection.
- [x] **DONE** Thread-safe sliding-window rate limiting on `/auth/login`, `/api/v1/reports/generate`, and chat.
- [x] **DONE** Strict SSRF protection blocking loopback, RFC 1918 subnets, and cloud metadata IPs on external integrations.
- [x] **DONE** Cryptographic audit log predecessor hash chaining (HMAC-SHA256) with chain verification endpoint.
- [x] **DONE** PostgreSQL trigger `audit_log_immutability_guard` preventing update or deletion of audit logs.
- [x] **DONE** Demonstration mode guardrails (`APP_MODE=demo`) blocking statutory submissions and destructive actions.
- [!] **VERIFY** Restricted least-privilege DB user (`wildfire_app_user`) role permissions for staging/production deployment.

### Section F: Operational Workspaces & Workflows
- [x] **DONE** Target investigation drawer displaying multi-model anomaly consensus and OSM facility co-location.
- [x] **DONE** Evidence-grounded AI Investigator powered by Google Gemini with anti-hallucination guardrails.
- [x] **DONE** Report intelligence engine with dynamic executive summaries, evidence tables, and signed PDF exports.
- [x] **DONE** Idempotent follow-up task management queue with status lifecycle, assignees, and audit notes.
- [x] **DONE** External connector directory with connection tester and automated synchronization jobs.
- [x] **DONE** Statutory authority submission tracking for regulatory compliance filings.

### Section G: API & Backend Service Architecture
- [x] **DONE** RESTful API with comprehensive input validation and standardized JSON error payloads.
- [x] **DONE** Thread-safe SQLAlchemy connection pooling with connection recycling and pre-ping checks.
- [x] **DONE** Strict CORS domain whitelisting preventing unauthorized cross-origin requests.
- [x] **DONE** System health endpoint `/health` verifying database connectivity and service readiness.

### Section H: Frontend User Experience & Geospatial Visualization
- [x] **DONE** High-performance Leaflet GIS map with clustered heatmaps and satellite tile layers.
- [x] **DONE** Responsive UI built with Tailwind CSS supporting high-density operational workflows.
- [x] **DONE** Diurnal pass distribution charts and cross-corridor comparative analytics.
- [x] **DONE** Modal dialogs, notifications, and loading skeletons across all workspaces.
- [x] **DONE** Clean TypeScript production compilation with 0 errors.

### Section I: Automated Testing & Quality Assurance
- [x] **DONE** 140 / 140 backend regression tests passing across 20 test modules.
- [x] **DONE** Complete test isolation protecting operational data from test mutations.
- [x] **DONE** Cryptographic audit chain verification tests passing.
- [x] **DONE** Rate limiter and SSRF security tests passing.
- [ ] **TO DO** Automated headless browser end-to-end suite (Cypress / Playwright) in CI pipeline.

### Section J: Production Deployment Readiness
- [x] **DONE** Multi-stage production `Dockerfile` with minimal runtime footprint.
- [x] **DONE** Production Docker Compose stack (`docker-compose.prod.yml`) coordinating DB, WSGI, and Nginx.
- [x] **DONE** Production Nginx reverse-proxy configuration with TLS 1.3 termination.
- [!] **VERIFY** Live public cloud domain deployment (Railway / AWS / GCP) pending owner cloud credentials.
- [BLOCKED] **BLOCKED** Off-site cloud backup automation (Pending production cloud bucket provisioning).

---

## 19. Contributing Guidelines

We welcome technical contributions to the KRATOS platform. Please read our [CONTRIBUTING.md](CONTRIBUTING.md) guide for details on code style, branch naming conventions, pull request workflows, and development environment setup.

---

## 20. Security Policy & Vulnerability Disclosure

Security is fundamental to KRATOS. Please review [SECURITY.md](SECURITY.md) for our security architecture overview, threat modeling principles, and confidential vulnerability disclosure process.

---

## 21. Scientific Data Citations & Acknowledgements

1. **NASA LANCE FIRMS:** VIIRS 375m active fire data provided by NASA's Land, Atmosphere Near-real-time Capability for EOS (LANCE). *Citation: NASA Near Real-Time and MCD14DL VIIRS Active Fire Detections.*
2. **OpenStreetMap:** Industrial facility boundary polygons © OpenStreetMap contributors, licensed under the Open Data Commons Open Database License (ODbL).
3. **ESA WorldCover:** Global land cover 2021 at 10m resolution provided by the European Space Agency WorldCover Consortium, licensed under CC BY 4.0.
4. **ECMWF Copernicus:** ERA5-Land hourly meteorological reanalysis data provided by the Copernicus Climate Change Service.
5. **WorldPop:** High-resolution population distribution grids provided by WorldPop, University of Southampton, licensed under CC BY 4.0.

---

## 22. License

This project is currently maintained as a proprietary demonstration and research platform. All rights are reserved by the project author. For licensing inquiries, commercial deployment, or collaborative research, please open a discussion on GitHub.
