# KRATOS V3.1 — Remote Sensing & Analytical Methodology

This document details the scientific foundations, satellite radiometric interpretation principles, and algorithmic models powering KRATOS V3.1.

## 1. VIIRS Satellite Thermal Remote Sensing

KRATOS utilizes active fire observations from the Visible Infrared Imaging Radiometer Suite (VIIRS) aboard the Suomi-NPP, NOAA-20, and NOAA-21 polar-orbiting satellites.

### Radiometric Bands & Spatial Resolution
- **I-Band 4 (3.75 µm):** High-gain mid-infrared channel with 375m spatial resolution at nadir. Sensitive to sub-pixel high-temperature combustion and thermal radiation emission.
- **I-Band 5 (11.45 µm):** Longwave infrared channel used for background temperature estimation, cloud masking, and atmospheric correction.
- **Fire Radiative Power (FRP):** Calculated in Megawatts (MW) using the Miria-Wooster empirical formulation. FRP reflects the rate of radiant energy release from sub-pixel thermal sources:
  $$\text{FRP} = \frac{A_{\text{pix}} \cdot \sigma}{\tau} \cdot (T_{4}^4 - T_{4,\text{bg}}^4)$$

## 2. Spatial Clustering & Persistent Source Identification

1. **DBSCAN Spatial Clustering:**
   - Thermal observations are grouped using PostGIS `ST_ClusterDBSCAN` with an epsilon of 300 meters and minimum points requirement ($minPts = 2$).
2. **Persistent Source Corroboration:**
   - Locations exhibiting recurrent thermal activity across multiple quarters (minimum 3 distinct satellite overpasses spanning $> 30$ days) are classified as persistent thermal sources.
   - Identified sources are corroborated against 2,423 OpenStreetMap industrial geometries.

## 3. Multi-Model Anomaly Detection Consensus

To differentiate routine industrial flaring from anomalous, runaway, or unpermitted thermal incidents, KRATOS evaluates detections through three independent models:

### Model 1: Multivariate Isolation Forest
- **Architecture:** Unsupervised ensemble of 100 decision trees trained on normalized 2021–2024 historical features.
- **Input Features (16):**
  - Brightness Temperature ($T_4, T_5$)
  - Brightness Temperature Ratio ($\frac{T_4}{T_5}$)
  - Fire Radiative Power (MW) and $\log(1 + \text{FRP})$
  - Solar Zenith Angle and Solar Azimuth Angle
  - Scan Angle and Sensor Track Size
  - Historical Recurrence Rate (30d and 365d)
  - Distance to Nearest Industrial Facility (meters)
  - WorldCover Land Cover Class (built-up, cropland, forest, shrubland)
- **Scoring:** Outputs an outlier anomaly score in `[-1.0, 1.0]`. Detections with scores $< -0.15$ are flagged.

### Model 2: Robust Statistical Deviation (MAD & Quantiles)
- Computes Median Absolute Deviation (MAD) against the facility's historical diurnal envelope:
  $$\text{MAD} = \text{median}(|X_i - \text{median}(X)|)$$
  $$\text{Modified } Z = \frac{0.6745 \cdot (X - \text{median}(X))}{\text{MAD}}$$
- Observations exceeding Modified $Z > 3.0$ or exceeding the historical 95th/99th percentiles ($P_{95}, P_{99}$) for that facility's operational profile trigger statistical anomaly flags.

### Model 3: CUSUM Sequential Change Detection
- Two-sided tabular Cumulative Sum (CUSUM) detector tracking sustained structural shifts in background heat emission:
  $$S_t^+ = \max(0, S_{t-1}^+ + X_t - \mu_0 - k)$$
  $$S_t^- = \max(0, S_{t-1}^- + \mu_0 - k - X_t)$$
- Detects cumulative operational shifts before single-point threshold limits are exceeded.

## 4. Operational Priority Classification

The Operational Priority Score (0–100) translates multi-source evidence into actionable operational urgency:

$$\text{Priority} = 0.35 \cdot S_{\text{FRP}} + 0.25 \cdot S_{\text{Anomaly}} + 0.20 \cdot S_{\text{Proximity}} + 0.10 \cdot S_{\text{Recurrence}} + 0.10 \cdot S_{\text{Vulnerability}}$$

- **CRITICAL ($\ge 75$):** Severe thermal anomaly with high radiant power near critical industrial or populated assets. Immediate verification required.
- **HIGH ($50 - 74$):** Substantial deviation from historical baseline requiring compliance review and formal dossier synthesis.
- **MEDIUM ($30 - 49$):** Moderate thermal exceedance scheduled for standard monitoring.
- **LOW ($< 30$):** Conforms to historical baseline envelope or routine agricultural background.

## 5. Scientific Limitations

- **Hotspot $\ne$ Incident Confirmation:** Satellite active fire detections identify radiometric heat emission within a 375m ground pixel. They do not prove an uncontained industrial emergency without ground or SCADA verification.
- **FRP $\ne$ Internal Equipment Temperature:** Fire Radiative Power measures radiated energy across the ground surface, not internal boiler, furnace, or kiln operating temperatures.
- **Cloud Obscuration:** Dense cloud cover and heavy monsoonal precipitation attenuate infrared radiation and may delay detection.
