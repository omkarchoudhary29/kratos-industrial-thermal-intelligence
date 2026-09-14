# KRATOS V3.1 — Machine Learning Validation & Ground Truth Policy

This document details the training methodology, validation protocols, proxy-label policy, and scientific boundaries of the KRATOS machine learning pipeline.

## 1. Model Artifact Specifications

- **Model File:** `models/industrial_iforest_train_2021_2024.joblib`
- **Algorithm:** Isolation Forest (`sklearn.ensemble.IsolationForest`)
- **Training Population:** Historical VIIRS thermal detections from 2021 through 2024 across monitored industrial corridors.
- **Ensemble Hyperparameters:**
  - `n_estimators`: 100
  - `max_samples`: "auto"
  - `contamination`: 0.05
  - `random_state`: 42

## 2. Proxy Labels vs. Ground Truth

An essential tenet of KRATOS is scientific transparency regarding label provenance:

- **Absence of Ground Truth:** Independent physical confirmation (e.g. fire department dispatch logs, direct plant SCADA instrumentation) is proprietary and unavailable across national-scale satellite archives.
- **Proxy Labels:** Model validation uses mathematically defined proxy labels:
  - Strong positive proxy: Observations exhibiting high Fire Radiative Power exceedance ($> P_{99}$ for the corridor) coupled with low historical recurrence.
  - Negative proxy: Recurrent, low-variance diurnal heating patterns conforming to standard operational furnace or flare cycles.
- **Notice on Inference:** Model confidence scores reflect statistical deviation from historical satellite observation envelopes, not the physical probability of an uncontained fire disaster.

## 3. Evaluation & Benchmarking

The ML evaluation endpoint (`GET /api/v1/ml/evaluation`) reports multi-metric performance against the proxy baseline:
- Area Under ROC Curve (ROC-AUC): Evaluated on historical validation splits.
- Precision @ K: Evaluates top-ranked anomalous detections against verified high-FRP excursions.
- False Positive Mitigation: Consensus between Isolation Forest, MAD z-scores, and CUSUM reduces isolated false alarms by $> 65\%$ compared to single-threshold satellite alerting.
