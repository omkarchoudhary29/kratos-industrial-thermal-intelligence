# KRATOS V3.1 — Machine Learning Models & Anomaly Architecture

This directory contains trained model artifacts and schema specifications powering the multi-model anomaly detection engine of KRATOS V3.1.

## 1. Model Artifact Inventory

| Artifact | Type | Training Corpus | Features | Size |
|---|---|---|:---:|:---:|
| `industrial_iforest_train_2021_2024.joblib` | Scikit-Learn `Pipeline` / `IsolationForest` | 2021–2024 VIIRS Active Fire Records | 16 Normalized Spatial & Radiometric Features | 4.42 MB |

## 2. Multi-Model Consensus Architecture

KRATOS evaluates thermal events using three independent mathematical models to prevent false positives from benign industrial operations:

1. **Model 1: Multivariate Isolation Forest**
   - Unsupervised density estimation isolating anomalous spatial-temporal points in 16-dimensional space (FRP, brightness temperature, background deviation, recurrence rate, scan angle, solar zenith).
   - Generates an anomaly score in `[-1.0, 1.0]` where lower values indicate strong outliers.

2. **Model 2: Robust Statistical Deviation (MAD & Quantiles)**
   - Computes Median Absolute Deviation (MAD) modified z-scores against facility-specific historical envelopes.
   - Evaluates upper quantile exceedances ($P_{95}$, $P_{99}$) on both daytime and nighttime passes.

3. **Model 3: CUSUM Sequential Change Detection**
   - Cumulative Sum sequential step-shift detector tracking cumulative deviations from running mean baseline.
   - Triggers on structural shifts in background heat emission indicative of sustained abnormal operations.

## 3. Scientific Validation & Ground Truth Limitations

- **Proxy Labels vs. Ground Truth:** Model evaluation is calibrated using proxy labels (corroborated spatial recurrence and high FRP exceedance) due to the absence of direct plant SCADA telemetric ground truth.
- **Explainability:** Each model outputs human-readable diagnostic reasoning explaining the physical rationale for anomaly attribution.
