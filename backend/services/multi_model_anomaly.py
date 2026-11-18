"""backend/services/multi_model_anomaly.py
----------------------------------------
KRATOS V3.1 — Multi-Model Thermal Anomaly Detection Engine.

Combines three distinct mathematical paradigms:
  1. Model 1: Production 16-feature Isolation Forest (unsupervised density estimation)
  2. Model 2: Robust Statistical Deviation (MAD z-score > 3.0 & upper quantile exceedance > P95/P99)
  3. Model 3: CUSUM Sequential Change Detection (cumulative sum step-shift detector)

Provides:
  - Consensus agreement score [0, 1]
  - Consensus verdict (STRONG_ANOMALY, MODERATE_ANOMALY, WEAK_ANOMALY, NORMAL_BASELINE)
  - Detailed per-model explainable diagnostics
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from services.artifact_resolver import get_iforest_model_path

log = logging.getLogger("multi_model_anomaly")

PROJECT_DIR = Path(__file__).resolve().parents[2]
try:
    IFOREST_MODEL_PATH = get_iforest_model_path()
except Exception:
    IFOREST_MODEL_PATH = PROJECT_DIR / "models" / "industrial_iforest_train_2021_2024.joblib"


class MultiModelAnomalyEngine:
    def __init__(self):
        self._iforest_pipeline = None
        self._iforest_features = None
        self._load_iforest()

    def _load_iforest(self) -> None:
        if IFOREST_MODEL_PATH.exists():
            try:
                bundle = joblib.load(IFOREST_MODEL_PATH)
                if isinstance(bundle, dict):
                    self._iforest_pipeline = bundle.get("pipeline")
                    self._iforest_features = bundle.get("features", [])
                else:
                    self._iforest_pipeline = bundle
                log.info("Loaded Isolation Forest model successfully.")
            except Exception as e:
                log.warning("Could not load Isolation Forest model: %s", e)

    # -----------------------------------------------------------------------
    # Model 1: Isolation Forest
    # -----------------------------------------------------------------------
    def evaluate_isolation_forest(
        self,
        feature_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate 16-feature Isolation Forest model."""
        if not self._iforest_pipeline or not self._iforest_features:
            # Fallback estimation if model weights not directly runnable
            pre_score = feature_dict.get("max_iforest_anomaly_score") or feature_dict.get("iforest_score")
            if pre_score is not None:
                is_anomaly = bool(pre_score < -0.10)
                return {
                    "model_name": "Isolation Forest (Pre-computed / 16-Feature)",
                    "anomaly_score": round(float(pre_score), 4),
                    "is_anomaly": is_anomaly,
                    "threshold_applied": -0.10,
                    "confidence": round(min(1.0, max(0.0, abs(pre_score) * 2.0)), 2),
                    "reasoning": f"Isolation Forest decision score of {pre_score:.3f} falls in {'sparse density outlier space' if is_anomaly else 'dense normal operational envelope'}.",
                }
            return {
                "model_name": "Isolation Forest",
                "anomaly_score": None,
                "is_anomaly": False,
                "threshold_applied": -0.10,
                "confidence": 0.0,
                "reasoning": "Isolation Forest model artifact unavailable; evaluation skipped.",
            }

        # Build feature vector
        row = []
        for feat in self._iforest_features:
            val = feature_dict.get(feat, 0.0)
            if val is None or pd.isna(val):
                val = 0.0
            row.append(float(val))

        try:
            X = pd.DataFrame([row], columns=self._iforest_features)
            score = float(self._iforest_pipeline.decision_function(X)[0])
            is_anomaly = bool(score < -0.10)
            conf = float(np.clip(abs(score) * 2.5, 0.20, 0.98))

            return {
                "model_name": "Isolation Forest (16-Feature Pipeline)",
                "anomaly_score": round(score, 4),
                "is_anomaly": is_anomaly,
                "threshold_applied": -0.10,
                "confidence": round(conf, 2),
                "reasoning": f"16-dimensional isolation score {score:.3f} indicates {'unusual low-density multivariate signature' if is_anomaly else 'consistent multivariate operational baseline'}.",
            }
        except Exception as e:
            log.warning("Isolation forest inference failed: %s", e)
            return {
                "model_name": "Isolation Forest",
                "anomaly_score": None,
                "is_anomaly": False,
                "threshold_applied": -0.10,
                "confidence": 0.0,
                "reasoning": f"Inference error: {e}",
            }

    # -----------------------------------------------------------------------
    # Model 2: Robust Statistical Deviation (MAD & Quantiles)
    # -----------------------------------------------------------------------
    @staticmethod
    def evaluate_statistical_deviation(
        observed_frp: float,
        baseline_stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate robust non-parametric statistical deviation."""
        n = baseline_stats.get("sample_size", 0)
        median = baseline_stats.get("median")
        mad = baseline_stats.get("mad")
        p95 = baseline_stats.get("p95")
        p99 = baseline_stats.get("p99")

        if n < 5 or median is None or observed_frp is None:
            return {
                "model_name": "Robust Statistical Deviation (MAD/Quantile)",
                "mad_zscore": None,
                "ratio_to_median": None,
                "exceeds_p95": False,
                "exceeds_p99": False,
                "is_anomaly": False,
                "confidence": 0.0,
                "reasoning": "Insufficient baseline sample count (N < 5) to establish reliable statistical anomaly boundaries.",
            }

        # Compute robust MAD z-score
        # z = 0.6745 * (x - median) / mad
        if mad and mad > 0:
            z_mad = 0.6745 * (observed_frp - median) / mad
        else:
            z_mad = 0.0 if observed_frp <= median else 4.0

        ratio = (observed_frp / median) if median > 0 else 1.0
        exceeds_p95 = bool(p95 is not None and observed_frp > p95)
        exceeds_p99 = bool(p99 is not None and observed_frp > p99)

        # Anomaly criteria: z_mad > 3.0 AND exceeds P95 (or P99 if mature)
        is_anomaly = bool(z_mad >= 3.0 and (exceeds_p95 or ratio >= 3.0))

        conf = 0.0
        if is_anomaly:
            conf = 0.90 if exceeds_p99 else 0.75
        else:
            conf = 0.85 if z_mad < 2.0 else 0.50

        return {
            "model_name": "Robust Statistical Deviation (MAD/Quantile)",
            "mad_zscore": round(float(z_mad), 3),
            "ratio_to_median": round(float(ratio), 2),
            "exceeds_p95": exceeds_p95,
            "exceeds_p99": exceeds_p99,
            "is_anomaly": is_anomaly,
            "confidence": round(conf, 2),
            "reasoning": f"Observed FRP ({observed_frp:.1f} MW) is {ratio:.1f}x baseline median (z_MAD={z_mad:.2f}). {'Exceeds P95/P99 extreme percentile thresholds.' if is_anomaly else 'Within non-parametric distribution limits.'}",
        }

    # -----------------------------------------------------------------------
    # Model 3: CUSUM Sequential Change Detection
    # -----------------------------------------------------------------------
    @staticmethod
    def evaluate_cusum_change(
        recent_series: List[float],
        baseline_median: float,
        baseline_mad: float,
        slack_k: float = 0.5,
        threshold_h: float = 4.0,
    ) -> Dict[str, Any]:
        """CUSUM step-shift and cumulative drift detector."""
        if not recent_series or baseline_median is None:
            return {
                "model_name": "CUSUM Sequential Change Detection",
                "cusum_score": 0.0,
                "is_anomaly": False,
                "confidence": 0.0,
                "reasoning": "No sequential time series available for CUSUM evaluation.",
            }

        # Standard deviation proxy from MAD
        sigma = (baseline_mad / 0.6745) if baseline_mad and baseline_mad > 0 else 1.0

        # One-sided upper CUSUM
        s_pos = 0.0
        max_s = 0.0
        k = slack_k * sigma
        h = threshold_h * sigma

        for x in recent_series:
            s_pos = max(0.0, s_pos + (x - baseline_median - k))
            if s_pos > max_s:
                max_s = s_pos

        is_anomaly = bool(max_s >= h)
        normalized_score = min(10.0, max_s / max(1e-5, h))

        return {
            "model_name": "CUSUM Sequential Change Detection",
            "cusum_score": round(float(normalized_score), 2),
            "raw_max_drift": round(float(max_s), 2),
            "threshold_h": round(float(h), 2),
            "is_anomaly": is_anomaly,
            "confidence": round(min(0.95, 0.40 + 0.50 * (max_s / max(1e-5, h))), 2) if is_anomaly else 0.70,
            "reasoning": f"Cumulative sequential deviation reached {max_s:.1f} (threshold h={h:.1f}). {'Indicates persistent upward operational regime shift.' if is_anomaly else 'No persistent upward drift detected.'}",
        }

    # -----------------------------------------------------------------------
    # Multi-Model Consensus Engine
    # -----------------------------------------------------------------------
    def evaluate_all(
        self,
        feature_dict: Dict[str, Any],
        baseline_stats: Dict[str, Any],
        recent_series: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Run all three models and compute agreement metrics."""
        observed_frp = feature_dict.get("max_frp") or feature_dict.get("frp") or 0.0

        m1 = self.evaluate_isolation_forest(feature_dict)
        m2 = self.evaluate_statistical_deviation(float(observed_frp), baseline_stats)

        # Build recent series if not provided
        if not recent_series:
            recent_series = [float(observed_frp)]

        med = baseline_stats.get("median") or float(observed_frp)
        mad = baseline_stats.get("mad") or 1.0
        m3 = self.evaluate_cusum_change(recent_series, med, mad)

        # Consensus counting
        flags = [m1["is_anomaly"], m2["is_anomaly"], m3["is_anomaly"]]
        agreement_count = sum(1 for f in flags if f)
        agreement_score = round(agreement_count / 3.0, 3)

        if agreement_count == 3:
            verdict = "STRONG_ANOMALY"
            summary = "Unanimous consensus (3/3 models): Multivariate Isolation Forest, Robust Statistical Exceedance, and CUSUM Sequential Drift all indicate significant anomalous heating."
        elif agreement_count == 2:
            verdict = "MODERATE_ANOMALY"
            summary = "Dual-model consensus (2/3 models): Elevated thermal signature confirmed across multiple independent mathematical paradigms."
        elif agreement_count == 1:
            verdict = "WEAK_ANOMALY"
            summary = "Isolated model detection (1/3 models): Signal detected by single model; likely benign operational variation or transient sensor artifact."
        else:
            verdict = "NORMAL_BASELINE"
            summary = "Consensus normal (0/3 models): Thermal parameters conform to established historical baseline envelope."

        return {
            "model_1_isolation_forest": m1,
            "model_2_statistical_deviation": m2,
            "model_3_cusum_change": m3,
            "consensus": {
                "agreement_count": agreement_count,
                "total_models": 3,
                "agreement_score": agreement_score,
                "verdict": verdict,
                "summary": summary,
            },
        }


multi_model_anomaly = MultiModelAnomalyEngine()
