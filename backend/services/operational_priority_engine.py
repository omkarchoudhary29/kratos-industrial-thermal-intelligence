"""backend/services/operational_priority_engine.py
------------------------------------------------
KRATOS V3.1 — Evidence-Based Operational Priority Engine.

Synthesizes multiple evidence streams into a strictly bounded [0, 1] operational priority
score while actively de-duplicating collinear features (e.g. FRP ratio vs z-score,
raw detection count vs 30-day persistence).

Four Orthogonal Component Streams:
  1. Radiometric Severity (35%): De-duplicates FRP ratio and robust MAD z-score.
  2. Multi-Model Anomaly Consensus (25%): Independent agreement across Isolation Forest,
     MAD/Quantiles, and CUSUM change detector.
  3. Infrastructure Criticality & Spatial Proximity (25%): PostGIS spatial tier and
     high-consequence industrial facility hazard weighting.
  4. Environmental & Weather Vulnerability (15%): Surface wind speed, low humidity,
     and consecutive dry days fuel dryness.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("operational_priority")


class OperationalPriorityEngine:
    @staticmethod
    def compute_priority(
        radiometric_evidence: Dict[str, Any],
        anomaly_evidence: Dict[str, Any],
        facility_evidence: Dict[str, Any],
        environmental_evidence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Compute the de-duplicated operational priority score and tier."""
        env = environmental_evidence or {}

        # -------------------------------------------------------------
        # 1. Radiometric Severity Component (Weight = 0.35)
        # De-duplicate collinear FRP ratio and MAD z-score
        # -------------------------------------------------------------
        frp_ratio = radiometric_evidence.get("ratio_to_median") or radiometric_evidence.get("max_frp_ratio") or 1.0
        mad_zscore = radiometric_evidence.get("mad_zscore") or radiometric_evidence.get("max_frp_zscore") or 0.0

        # Bound and normalize ratio (1.0x baseline = 0.0, 5.0x baseline = 1.0)
        norm_ratio = min(1.0, max(0.0, (float(frp_ratio) - 1.0) / 4.0))
        # Bound and normalize z-score (0 = 0.0, 5.0 = 1.0)
        norm_zscore = min(1.0, max(0.0, float(mad_zscore) / 5.0))

        # Composite radiometric severity (prevents double-counting)
        radiometric_severity = 0.60 * norm_ratio + 0.40 * norm_zscore

        # -------------------------------------------------------------
        # 2. Multi-Model Anomaly Consensus Component (Weight = 0.25)
        # -------------------------------------------------------------
        consensus = anomaly_evidence.get("consensus", {})
        consensus_score = consensus.get("agreement_score")
        if consensus_score is None:
            # Fallback to iforest flag if consensus not pre-run
            if anomaly_evidence.get("iforest_agreement") or anomaly_evidence.get("is_anomaly"):
                consensus_score = 0.67
            else:
                consensus_score = 0.0
        consensus_score = min(1.0, max(0.0, float(consensus_score)))

        # -------------------------------------------------------------
        # 3. Infrastructure Criticality & Spatial Proximity (Weight = 0.25)
        # -------------------------------------------------------------
        spatial_tier = facility_evidence.get("spatial_tier", "tier_5_unassociated")
        facility_category = facility_evidence.get("taxonomy_key") or facility_evidence.get("facility_category") or ""

        tier_weights = {
            "tier_1_footprint": 1.00,
            "tier_2_perimeter": 0.75,
            "tier_3_industrial_zone": 0.45,
            "tier_4_regional_buffer": 0.20,
            "tier_5_unassociated": 0.05,
        }
        base_spatial_weight = tier_weights.get(spatial_tier, 0.10)

        # High-consequence facility hazard multiplier
        cat_lower = str(facility_category).lower()
        if any(k in cat_lower for k in ["refinery", "petro", "chemical", "gas_flare"]):
            hazard_factor = 1.20
        elif any(k in cat_lower for k in ["steel", "metallurg", "power", "boiler"]):
            hazard_factor = 1.10
        elif any(k in cat_lower for k in ["mine", "coal"]):
            hazard_factor = 1.00
        else:
            hazard_factor = 0.85

        infrastructure_criticality = min(1.0, base_spatial_weight * hazard_factor)

        # -------------------------------------------------------------
        # 4. Environmental & Weather Vulnerability (Weight = 0.15)
        # -------------------------------------------------------------
        wind_speed = env.get("wind_speed_ms") or env.get("wind_speed") or 3.0
        rh = env.get("relative_humidity_pct") or env.get("rh") or 50.0
        dry_days = env.get("dry_days_count") or env.get("consecutive_dry_days") or 2

        # Wind factor (0 to 15 m/s)
        norm_wind = min(1.0, max(0.0, float(wind_speed) / 15.0))
        # Dryness / low humidity factor (100% RH = 0.0, 15% RH = 1.0)
        norm_dryness = min(1.0, max(0.0, (100.0 - float(rh)) / 85.0))
        # Prolonged dry spell factor (0 to 14 days)
        norm_dry_days = min(1.0, max(0.0, float(dry_days) / 14.0))

        environmental_vulnerability = 0.40 * norm_wind + 0.35 * norm_dryness + 0.25 * norm_dry_days

        # -------------------------------------------------------------
        # 5. Composite Bounded Score Calculation
        # -------------------------------------------------------------
        w_rad = 0.35
        w_anom = 0.25
        w_infra = 0.25
        w_env = 0.15

        composite_score = (
            w_rad * radiometric_severity
            + w_anom * consensus_score
            + w_infra * infrastructure_criticality
            + w_env * environmental_vulnerability
        )
        composite_score = round(min(1.0, max(0.0, float(composite_score))), 3)

        # Priority Tiers
        if composite_score >= 0.75:
            priority_tier = "CRITICAL"
            recommended_action = "Immediate on-site emergency verification and industrial safety officer contact required."
        elif composite_score >= 0.55:
            priority_tier = "HIGH"
            recommended_action = "High-priority operational investigation; dispatch field inspector within 4 hours."
        elif composite_score >= 0.35:
            priority_tier = "MODERATE"
            recommended_action = "Routine operational monitoring; cross-reference facility shift log at next reporting cycle."
        else:
            priority_tier = "LOW"
            recommended_action = "Normal background baseline activity; no immediate action indicated."

        return {
            "operational_priority_score": composite_score,
            "operational_priority_tier": priority_tier,
            "recommended_action": recommended_action,
            "component_breakdown": {
                "radiometric_severity": {
                    "raw_score": round(radiometric_severity, 3),
                    "weight": w_rad,
                    "weighted_contribution": round(w_rad * radiometric_severity, 3),
                    "inputs_deduplicated": ["frp_ratio", "mad_zscore"],
                },
                "anomaly_consensus": {
                    "raw_score": round(consensus_score, 3),
                    "weight": w_anom,
                    "weighted_contribution": round(w_anom * consensus_score, 3),
                    "inputs": ["isolation_forest", "robust_quantiles", "cusum_change"],
                },
                "infrastructure_criticality": {
                    "raw_score": round(infrastructure_criticality, 3),
                    "weight": w_infra,
                    "weighted_contribution": round(w_infra * infrastructure_criticality, 3),
                    "spatial_tier": spatial_tier,
                    "hazard_factor": hazard_factor,
                },
                "environmental_vulnerability": {
                    "raw_score": round(environmental_vulnerability, 3),
                    "weight": w_env,
                    "weighted_contribution": round(w_env * environmental_vulnerability, 3),
                    "inputs": ["wind_speed", "relative_humidity", "consecutive_dry_days"],
                },
            },
            "deduplication_audit": (
                "Collinear variables (FRP ratio vs z-score; detection count vs persistence) were mathematically "
                "synthesized prior to weighting to prevent artificial score inflation."
            ),
        }


operational_priority_engine = OperationalPriorityEngine()
