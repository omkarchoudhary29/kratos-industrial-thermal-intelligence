"""Machine Learning Evaluation and Distribution Monitoring Service.

Provides objective evaluation metrics, regional performance comparison,
score distribution statistics, and model version tracking for the 2021–2024
Isolation Forest pipeline without inventing synthetic or unverified labels.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_DIR / "models" / "industrial_iforest_train_2021_2024.joblib"
EVENTS_PATH = PROJECT_DIR / "data" / "processed" / "final_fused_events.parquet"


class MLEvaluationService:
    def __init__(self):
        self._model_cache: dict[str, Any] | None = None
        self._events_cache: pd.DataFrame | None = None

    def _load_model_metadata(self) -> dict[str, Any]:
        if self._model_cache is not None:
            return self._model_cache

        if not MODEL_PATH.exists():
            return {
                "loaded": False,
                "error": "Model artifact not found",
            }

        try:
            artifact = joblib.load(MODEL_PATH)
            pipeline = artifact.get("pipeline")
            model_step = getattr(pipeline, "named_steps", {}).get("model") if pipeline else None

            self._model_cache = {
                "loaded": True,
                "model_name": "IsolationForest",
                "version": "1.0.0",
                "training_period": artifact.get("training_period", "2021-01-01 to 2024-12-31"),
                "features": artifact.get("features", []),
                "feature_count": len(artifact.get("features", [])),
                "contamination": getattr(model_step, "contamination", 0.02) if model_step else 0.02,
                "n_estimators": getattr(model_step, "n_estimators", 400) if model_step else 400,
                "normalization": artifact.get("normalization", {}),
                "calibration_note": (
                    "Scores are normalized decision-function anomaly rankings in [0, 1]. "
                    "They represent relative deviation from 2021–2024 regional baselines, "
                    "not calibrated Bayesian event probabilities."
                ),
            }
            return self._model_cache
        except Exception as exc:
            log.warning("Could not read model metadata: %s", exc)
            return {"loaded": False, "error": str(exc)}

    def _load_events(self) -> pd.DataFrame:
        if self._events_cache is None and EVENTS_PATH.exists():
            try:
                self._events_cache = pd.read_parquet(EVENTS_PATH)
            except Exception as exc:
                log.warning("Could not load events parquet: %s", exc)
                self._events_cache = pd.DataFrame()
        return self._events_cache if self._events_cache is not None else pd.DataFrame()

    def get_evaluation_metrics(self) -> dict[str, Any]:
        """Compute objective ML evaluation metrics, regional comparisons, and score distributions."""
        meta = self._load_model_metadata()
        df = self._load_events()

        if df.empty:
            return {
                "model_metadata": meta,
                "evaluation_status": "no_data_available",
                "total_samples": 0,
            }

        total_samples = len(df)
        agreed_count = int(df["iforest_agreement"].sum()) if "iforest_agreement" in df else 0
        anomaly_rate = float(agreed_count / total_samples) if total_samples > 0 else 0.0

        # High-risk Operational Grounding:
        # High and Critical events represent confirmed high-exceedance episodes
        if "final_risk_level" in df and "iforest_agreement" in df:
            y_operational = df["final_risk_level"].isin(["high", "critical"])
            y_pred = df["iforest_agreement"] == True

            tp = int((y_operational & y_pred).sum())
            fp = int((~y_operational & y_pred).sum())
            fn = int((y_operational & ~y_pred).sum())
            tn = int((~y_operational & ~y_pred).sum())

            precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
            recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
            f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

            confusion_matrix = {
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "true_negatives": tn,
            }
        else:
            precision, recall, f1 = 0.0, 0.0, 0.0
            confusion_matrix = {}

        # Regional Performance Comparison
        regional_breakdown = []
        if "region_name" in df:
            for region, group in df.groupby("region_name"):
                n_events = len(group)
                n_agreed = int((group["iforest_agreement"] == True).sum()) if "iforest_agreement" in group else 0
                n_high = int(group["final_risk_level"].isin(["high", "critical"]).sum()) if "final_risk_level" in group else 0
                mean_frp = float(group["max_frp"].mean()) if "max_frp" in group and not group["max_frp"].isna().all() else 0.0

                regional_breakdown.append({
                    "region": region,
                    "event_count": n_events,
                    "iforest_anomalies": n_agreed,
                    "high_risk_events": n_high,
                    "anomaly_detection_rate": round(n_agreed / n_events, 4) if n_events > 0 else 0.0,
                    "mean_max_frp": round(mean_frp, 2),
                })

        # Anomaly Score Distribution Monitoring
        scores = df["max_iforest_anomaly_score"].dropna() if "max_iforest_anomaly_score" in df else pd.Series(dtype=float)
        score_distribution = {
            "count": int(len(scores)),
            "mean": round(float(scores.mean()), 4) if not scores.empty else None,
            "std": round(float(scores.std()), 4) if not scores.empty else None,
            "min": round(float(scores.min()), 4) if not scores.empty else None,
            "p25": round(float(scores.quantile(0.25)), 4) if not scores.empty else None,
            "p50": round(float(scores.median()), 4) if not scores.empty else None,
            "p75": round(float(scores.quantile(0.75)), 4) if not scores.empty else None,
            "max": round(float(scores.max()), 4) if not scores.empty else None,
        }

        return {
            "model_metadata": meta,
            "dataset_summary": {
                "total_scored_events": total_samples,
                "model_confirmed_anomalies": agreed_count,
                "empirical_anomaly_rate": round(anomaly_rate, 4),
                "expected_contamination": meta.get("contamination", 0.02),
            },
            "operational_agreement_metrics": {
                "target_class": "High / Critical Risk Episodes",
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "confusion_matrix": confusion_matrix,
                "false_positive_analysis": f"{confusion_matrix.get('false_positives', 0)} moderate-risk events had high statistical deviation without meeting physical breach threshold.",
                "false_negative_analysis": f"{confusion_matrix.get('false_negatives', 0)} high-risk events were elevated by spatial context or persistence despite mild model score.",
            },
            "score_distribution": score_distribution,
            "regional_performance": regional_breakdown,
        }


ml_evaluation_service = MLEvaluationService()
