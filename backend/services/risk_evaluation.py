"""backend/services/risk_evaluation.py
----------------------------------
KRATOS V3 Phase 2 — Multi-Factor Risk & Operational Priority Evaluation Engine.

Maintains four strictly distinct, non-conflated intelligence outputs:
  1. Anomaly Score: Statistical density outlier score [-1.0, 1.0] and [0, 1] normalized.
  2. Source Classification: Physical type and rule-based confidence rating.
  3. Fire/Incident Probability: null / uncalibrated with honest disclaimer.
  4. Operational Priority Score: Documented, explainable multi-factor formula:
       Priority = 0.35 * FRP_Exceedance + 0.25 * Persistence_Abnormality
                + 0.25 * Normalized_Anomaly + 0.15 * Facility_Proximity
                - Uncertainty_Penalty
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

log = logging.getLogger("risk_evaluation")

PROJECT_DIR = Path(__file__).resolve().parents[2]
EVENTS_PATH = PROJECT_DIR / "data" / "processed" / "final_fused_events.parquet"
SOURCES_PATH = PROJECT_DIR / "data" / "processed" / "thermal_sources.parquet"


class RiskEvaluationEngine:
    def __init__(self):
        self._events_cache: Optional[pd.DataFrame] = None
        self._sources_cache: Optional[pd.DataFrame] = None

    def _get_events(self) -> pd.DataFrame:
        if self._events_cache is None and EVENTS_PATH.exists():
            self._events_cache = pd.read_parquet(EVENTS_PATH)
        return self._events_cache if self._events_cache is not None else pd.DataFrame()

    def _get_sources(self) -> pd.DataFrame:
        if self._sources_cache is None and SOURCES_PATH.exists():
            self._sources_cache = pd.read_parquet(SOURCES_PATH)
        return self._sources_cache if self._sources_cache is not None else pd.DataFrame()

    def evaluate_operational_priority(
        self,
        event_or_source_dict: Dict[str, Any],
        facility_dist_m: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Compute the 4 strictly distinct intelligence outputs with full mathematical explainability."""
        # 1. Anomaly Score
        raw_anomaly = event_or_source_dict.get("max_iforest_anomaly_score")
        if raw_anomaly is None:
            raw_anomaly = event_or_source_dict.get("max_source_anomaly_score", 0.0)
        try:
            raw_anomaly_val = float(raw_anomaly)
        except (TypeError, ValueError):
            raw_anomaly_val = 0.0

        # Normalization [0, 1] - Invert raw decision score so outliers (-1.0) map to 1.0, normal (+1.0) maps to 0.0
        normalized_anomaly = max(0.0, min(1.0, (1.0 - raw_anomaly_val) / 2.0))
        is_anomaly_flagged = bool(
            event_or_source_dict.get("iforest_agreement") is True
            or raw_anomaly_val < -0.15
            or normalized_anomaly > 0.575
        )

        # 2. Source Classification Confidence
        source_class = event_or_source_dict.get("source_class") or event_or_source_dict.get("predicted_source_type", "unclassified")
        class_conf = event_or_source_dict.get("classification_confidence") or event_or_source_dict.get("source_type_confidence")
        if class_conf is not None:
            class_conf = float(class_conf)

        # 3. Fire / Incident Probability (Strictly uncalibrated due to absence of verified ground truth)
        fire_incident_probability = None
        probability_disclaimer = (
            "Probability is deliberately set to null. Calibrated incident probability cannot be "
            "scientifically defended without independent, ground-truth emergency response verifications."
        )

        # 4. Operational Priority Score Calculation
        # Components:
        # a. FRP Exceedance Factor (0.35 weight)
        frp_ratio = event_or_source_dict.get("max_frp_ratio") or event_or_source_dict.get("frp_ratio_24h_vs_30d") or 1.0
        try:
            frp_ratio_val = float(frp_ratio)
        except (TypeError, ValueError):
            frp_ratio_val = 1.0
        frp_factor = max(0.0, min(1.0, (frp_ratio_val - 1.0) / 3.0)) if frp_ratio_val > 1.0 else 0.0

        # b. Persistence Abnormality Factor (0.25 weight)
        prev_30d = event_or_source_dict.get("source_detections_prev_30d") or event_or_source_dict.get("detection_count") or 1
        try:
            prev_30d_val = float(prev_30d)
        except (TypeError, ValueError):
            prev_30d_val = 1.0
        persistence_factor = max(0.0, min(1.0, prev_30d_val / 20.0))

        # c. Normalized Anomaly Factor (0.25 weight)
        anomaly_factor = normalized_anomaly

        # d. Facility Proximity Factor (0.15 weight)
        dist_m = facility_dist_m
        if dist_m is None:
            dist_m = event_or_source_dict.get("distance_to_nearest_facility_m")
            if dist_m is None:
                dist_m = event_or_source_dict.get("distance_to_nearest_industry_m")

        if dist_m is not None:
            try:
                dist_m_val = float(dist_m)
                if dist_m_val == 0.0:
                    proximity_factor = 1.0
                elif dist_m_val <= 300.0:
                    proximity_factor = 0.85
                elif dist_m_val <= 1000.0:
                    proximity_factor = 0.50
                elif dist_m_val <= 2000.0:
                    proximity_factor = 0.25
                else:
                    proximity_factor = 0.0
            except (TypeError, ValueError):
                proximity_factor = 0.0
        else:
            proximity_factor = 0.0

        # e. Uncertainty Penalty
        detections = event_or_source_dict.get("detection_count", 1)
        penalty = 0.15 if detections < 2 else 0.0

        # Priority calculation
        raw_priority = (
            0.35 * frp_factor
            + 0.25 * persistence_factor
            + 0.25 * anomaly_factor
            + 0.15 * proximity_factor
            - penalty
        )
        priority_score = max(0.0, min(1.0, raw_priority))

        # Determine Tier
        if detections < 2 and frp_ratio_val <= 1.0:
            priority_tier = "INSUFFICIENT_EVIDENCE"
            tier_rationale = "Sparse observation record (< 2 detections); insufficient historical baseline for confident triage."
        elif priority_score >= 0.75:
            priority_tier = "CRITICAL"
            tier_rationale = "Exceptional thermal signature combining high FRP exceedance, anomaly score, and proximate industrial exposure."
        elif priority_score >= 0.55:
            priority_tier = "HIGH"
            tier_rationale = "Elevated thermal activity with strong statistical deviation requiring prompt operational review."
        elif priority_score >= 0.35:
            priority_tier = "MEDIUM"
            tier_rationale = "Moderate deviation or recurring steady emission within manageable operational tolerance."
        else:
            priority_tier = "LOW"
            tier_rationale = "Routine background heat signature with minimal departure from historical baseline."

        return {
            "anomaly_score": {
                "raw_decision_score": round(raw_anomaly_val, 4),
                "normalized_score": round(normalized_anomaly, 4),
                "is_anomaly_flagged": is_anomaly_flagged,
                "model_identifier": "IsolationForest_v1.0_2021_2024",
                "interpretation": (
                    "Statistical density anomaly ranking. Negative raw scores indicate outliers "
                    "in the 16-feature multidimensional space."
                ),
            },
            "source_classification": {
                "predicted_type": source_class,
                "confidence_rating": round(class_conf, 2) if class_conf is not None else None,
                "confidence_calibration": "Uncalibrated heuristic rating",
            },
            "fire_incident_probability": fire_incident_probability,
            "fire_probability_disclaimer": probability_disclaimer,
            "operational_priority": {
                "score": round(priority_score, 4),
                "tier": priority_tier,
                "tier_rationale": tier_rationale,
                "formula": "0.35*FRP_Factor + 0.25*Persistence_Factor + 0.25*Anomaly_Factor + 0.15*Proximity_Factor - Penalty",
                "boundedness_guarantee": "[0.0, 1.0] strictly enforced",
                "component_contributions": {
                    "frp_exceedance_factor": round(frp_factor, 4),
                    "frp_exceedance_weight": 0.35,
                    "frp_contribution": round(0.35 * frp_factor, 4),
                    "persistence_factor": round(persistence_factor, 4),
                    "persistence_weight": 0.25,
                    "persistence_contribution": round(0.25 * persistence_factor, 4),
                    "anomaly_factor": round(anomaly_factor, 4),
                    "anomaly_weight": 0.25,
                    "anomaly_contribution": round(0.25 * anomaly_factor, 4),
                    "proximity_factor": round(proximity_factor, 4),
                    "proximity_weight": 0.15,
                    "proximity_contribution": round(0.15 * proximity_factor, 4),
                    "proximity_role": "Operational triage exposure weight representing proximity to high-value infrastructure, NOT causation of combustion.",
                    "uncertainty_penalty": penalty,
                },
            },
        }

    def get_priority_queue(self, limit: int = 50, region: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return the highest operational priority queue items across the nationwide catalog."""
        df = self._get_events()
        if df.empty:
            return []

        subset = df.copy()
        if region:
            reg_norm = str(region).strip().lower().replace("-", "_").replace(" ", "_")
            if reg_norm == "vijayanagar":
                reg_norm = "vijayanagar_toranagallu"
            subset = subset[subset["region_name"].astype(str).str.lower().str.replace("-", "_").str.replace(" ", "_") == reg_norm]

        # Filter high/critical or top FRP events for priority triage
        high_subset = subset.sort_values("max_frp", ascending=False).head(limit * 2)

        queue = []
        for _, row in high_subset.iterrows():
            record = row.to_dict()
            eval_res = self.evaluate_operational_priority(record)
            queue.append({
                "source_event_id": str(record.get("source_event_id")),
                "thermal_source_id": str(record.get("thermal_source_id")),
                "region_name": record.get("region_name"),
                "event_start": str(record.get("event_start")),
                "latitude": float(record.get("latitude", 0.0)),
                "longitude": float(record.get("longitude", 0.0)),
                "max_frp_mw": float(record.get("max_frp", 0.0)),
                "max_frp_ratio": float(record.get("max_frp_ratio", 1.0)),
                "priority_score": eval_res["operational_priority"]["score"],
                "priority_tier": eval_res["operational_priority"]["tier"],
                "tier_rationale": eval_res["operational_priority"]["tier_rationale"],
                "anomaly_score": eval_res["anomaly_score"]["normalized_score"],
                "is_anomaly_flagged": eval_res["anomaly_score"]["is_anomaly_flagged"],
                "source_class": eval_res["source_classification"]["predicted_type"],
                "component_contributions": eval_res["operational_priority"]["component_contributions"],
            })

        queue.sort(key=lambda x: x["priority_score"], reverse=True)
        return queue[:limit]


risk_evaluation_engine = RiskEvaluationEngine()
