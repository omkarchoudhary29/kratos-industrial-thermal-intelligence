# Changelog

All notable changes to the **KRATOS** platform are documented in this file.

## [3.1.0] — 2026-11-18 (Release Candidate)

### Added
- **Multi-Model Anomaly Detection:** Consensus engine combining Multivariate Isolation Forest (16 features), Robust Statistical Deviation (MAD z-score & P95/P99 quantiles), and CUSUM sequential change detection.
- **Evidence-Grounded Dossiers & PDF Generation:** Generation of formal investigation reports with deterministic evidence extraction, executive narratives, and signed PDF document export.
- **Statutory Authority Submission Tracking:** Routing and lifecycle management for state pollution boards and regulatory bodies with receipt metadata and reference tracking.
- **High-Priority Follow-Up Workflows:** Idempotent follow-up task queue with priority triage (CRITICAL, HIGH, MEDIUM, LOW), status transitions, and deduplication.
- **Data Integrations & SSRF Protection:** External connector directory with encrypted credentials and strict RFC-compliant SSRF endpoint validation.
- **Cryptographic Audit Trail:** HMAC-SHA256 predecessor hash chaining on all operational audit logs backed by PostgreSQL immutability triggers.
- **Public Demonstration Mode (`APP_MODE=demo`):** Read-only protection guards on statutory submissions and connector configuration with dedicated `demo_reviewer` provisioning.
- **Thread-Safe Sliding-Window Rate Limiting:** Brute-force protection on authentication (5/min), report generation (10/min), and AI investigator chat (20/min).
- **Data Provenance Modal:** In-app transparency view detailing the 5-year empirical baseline (8,891 events, 2,423 OSM facilities, 312 thermal sources).
- **Production WSGI Server:** Waitress (Windows) and Gunicorn (Linux) WSGI entrypoints with multi-worker scaling.

### Changed
- Refactored frontend to React 19 / TypeScript with Vite dev server and sub-millisecond reverse proxying.
- Upgraded timeline synchronization to support custom date-range queries with point-in-time filtering across 2021–2025.
- Separated test database execution strictly into `wildfire_test_db`, eliminating operational database contamination.

### Fixed
- Fixed pandas `Timestamp` JSON serialization during dynamic report synthesis.
- Corrected actor callsign resolution in report generation routes.
- Resolved race condition in concurrent audit log hash generation using row-level locking.

---

## [3.0.0] — 2026-11-14

### Added
- Initial geospatial thermal monitoring dashboard for 6 industrial corridors and 4 forest fire landscapes in India.
- Ingestion pipeline for NASA FIRMS VIIRS (S-NPP, NOAA-20, NOAA-21) active fire products.
- PostGIS spatial clustering of thermal detections within 300m radius.
- Initial PostgreSQL schema migrations and basic JWT authentication.
