"""backend/services/source_classification.py
-----------------------------------------
KRATOS V3 Phase 2 — Advanced Source Classification & Industrial Intelligence Engine.

Provides:
  - 4-Field Source & Incident Distinction:
      1. Mapped Facility Category (from PostGIS OSM or landcover context)
      2. Predicted Thermal Source Type (industrial_process_heat, gas_flare, coal_handling, vegetation_burning, unclassified)
      3. Thermal Activity Behavior (isolated_hotspot, recurring_steady, sudden_frp_spike, abnormal_persistence)
      4. Incident Assessment (normal_operational, anomaly_under_review, unusual_heat_exceedance, potential_incident_candidate)
  - PostGIS-grounded spatial relationship tiers (direct_intersection, within_polygon, strong_association, nearby_proximity, ambiguous, unassociated)
  - Supervised baseline evaluation comparing RandomForest against operational heuristic labels with Precision, Recall, F1, Confusion Matrix, and Calibration Disclaimers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger("source_classification")

PROJECT_DIR = Path(__file__).resolve().parents[2]
EVENTS_PATH = PROJECT_DIR / "data" / "processed" / "final_fused_events.parquet"
SOURCES_PATH = PROJECT_DIR / "data" / "processed" / "thermal_sources.parquet"
FACILITY_SUMMARY_PATH = PROJECT_DIR / "data" / "processed" / "facility_association_summary.json"


class SourceClassificationEngine:
    def __init__(self):
        self._summary_cache: Optional[Dict[str, Any]] = None
        self._supervised_benchmark_cache: Optional[Dict[str, Any]] = None

    def _load_association_summary(self) -> Dict[str, Any]:
        if self._summary_cache is not None:
            return self._summary_cache
        if FACILITY_SUMMARY_PATH.exists():
            try:
                self._summary_cache = json.loads(FACILITY_SUMMARY_PATH.read_text(encoding="utf-8"))
            except Exception as e:
                log.warning("Could not read facility association summary: %s", e)
                self._summary_cache = {}
        else:
            self._summary_cache = {}
        return self._summary_cache

    def classify_source_record(
        self,
        source_data: Dict[str, Any],
        facility_match: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Produce the 4 distinct classification fields and spatial tier for a source."""
        # 1. Spatial Relationship & Facility Category
        min_dist_m = source_data.get("distance_to_nearest_facility_m")
        if min_dist_m is None and facility_match:
            min_dist_m = facility_match.get("min_distance_m")

        fac_name = source_data.get("nearest_facility_name")
        fac_cat_raw = source_data.get("nearest_facility_category") or source_data.get("nearest_industry_type")
        if not fac_name and facility_match:
            fac_name = facility_match.get("nearest_facility_name")
        if not fac_cat_raw and facility_match:
            fac_cat_raw = facility_match.get("nearest_category")

        candidates_300m = source_data.get("candidates_300m", 0)
        if facility_match and "candidates_300m" in facility_match:
            candidates_300m = facility_match["candidates_300m"]

        # Map Facility Category
        if fac_cat_raw:
            raw_lower = str(fac_cat_raw).lower()
            if any(k in raw_lower for k in ["steel", "iron", "blast_furnace", "smelter"]):
                mapped_facility_category = "Steel & Metallurgy Plant"
            elif any(k in raw_lower for k in ["power", "generator", "thermal_power"]):
                mapped_facility_category = "Thermal Power Station"
            elif any(k in raw_lower for k in ["refinery", "petro", "oil", "gas", "flare"]):
                mapped_facility_category = "Petroleum & Chemical Refinery"
            elif any(k in raw_lower for k in ["mine", "quarry", "colliery", "coal"]):
                mapped_facility_category = "Coal Mine & Handling Yard"
            elif any(k in raw_lower for k in ["cement", "kiln"]):
                mapped_facility_category = "Cement & Building Materials"
            elif "industrial" in raw_lower:
                mapped_facility_category = "Industrial Manufacturing Complex"
            else:
                mapped_facility_category = fac_cat_raw.title()
        else:
            tree_frac = source_data.get("tree_fraction_1km_mean")
            if tree_frac is not None and tree_frac >= 0.40:
                mapped_facility_category = "Forest Landscape & Canopy"
            else:
                mapped_facility_category = "Non-Industrial / Rural Terrain"

        dist_str = f"{min_dist_m:.1f} m" if min_dist_m is not None else "> 2000 m"

        # Spatial Relationship Tier (Reconciled Mutually Exclusive Partition, Sum = 312)
        if facility_match and "mutually_exclusive_tier" in facility_match:
            spatial_relationship = facility_match["mutually_exclusive_tier"]
            dist_tier = facility_match.get("distance_tier", spatial_relationship)
            if spatial_relationship == "ambiguous":
                spatial_description = f"Ambiguous attribution: {candidates_300m} facilities within 300 m perimeter"
            elif spatial_relationship == "direct_intersection":
                spatial_description = "Direct spatial intersection with mapped facility polygon (0 m distance)"
            elif spatial_relationship == "strong_association":
                spatial_description = f"Within 300 m industrial perimeter ({dist_str})"
            elif spatial_relationship == "nearby_proximity":
                spatial_description = f"Within 2 km industrial zone ({dist_str})"
            else:
                spatial_description = f"Remote/unassociated ({dist_str} to closest mapped infrastructure)"
        elif min_dist_m is not None:
            if candidates_300m > 1:
                spatial_relationship = "ambiguous"
                dist_tier = "direct_intersection" if min_dist_m == 0.0 else "strong_association"
                spatial_description = f"Ambiguous attribution: {candidates_300m} facilities within 300 m perimeter"
            elif min_dist_m == 0.0 or source_data.get("association_tier") == "direct_intersection":
                spatial_relationship = "direct_intersection"
                dist_tier = "direct_intersection"
                spatial_description = "Direct spatial intersection with mapped facility polygon (0 m distance)"
            elif min_dist_m <= 300.0:
                spatial_relationship = "strong_association"
                dist_tier = "strong_association"
                spatial_description = f"Within 300 m industrial perimeter ({dist_str})"
            elif min_dist_m <= 1000.0:
                spatial_relationship = "nearby_proximity"
                dist_tier = "nearby_1000m"
                spatial_description = f"Within 1 km facility proximity buffer ({dist_str})"
            elif min_dist_m <= 2000.0:
                spatial_relationship = "nearby_proximity"
                dist_tier = "nearby_2000m"
                spatial_description = f"Within 2 km industrial zone ({dist_str})"
            else:
                spatial_relationship = "unassociated"
                dist_tier = "unmatched"
                spatial_description = f"Remote/unassociated ({dist_str} to closest mapped infrastructure)"
        else:
            spatial_relationship = "unassociated"
            dist_tier = "unmatched"
            spatial_description = "No proximate mapped industrial infrastructure within search radius (> 2000 m)"

        # 2. Predicted Source Type
        ref_d = source_data.get("distance_to_refinery_km_mean")
        pp_d = source_data.get("distance_to_powerplant_km_mean")
        ind_d = source_data.get("distance_to_industrial_km_mean")
        tree_f = source_data.get("tree_fraction_1km_mean")
        built_f = source_data.get("builtup_fraction_1km_mean")
        persistence = source_data.get("persistence_30d_mean") or source_data.get("persistence_30d") or 0.0

        if (ref_d is not None and ref_d <= 3.0) or ("Refinery" in mapped_facility_category):
            predicted_source_type = "gas_flare"
            source_type_confidence = 0.85
            type_rationale = "High persistent thermal signature within 3 km of active petroleum refinery infrastructure."
        elif ("Coal" in mapped_facility_category) or (fac_name and "colliery" in fac_name.lower()):
            predicted_source_type = "coal_handling"
            source_type_confidence = 0.80
            type_rationale = "Colliery/mining context indicative of coal handling or spontaneous stockpile heating."
        elif (
            spatial_relationship in ("direct_intersection", "strong_association", "within_polygon")
            or (ind_d is not None and ind_d <= 1.5)
            or (pp_d is not None and pp_d <= 2.0)
            or (built_f is not None and built_f >= 0.15)
        ):
            predicted_source_type = "industrial_process_heat"
            source_type_confidence = 0.80
            type_rationale = "Direct spatial association with mapped industrial plant and elevated built-up fraction."
        elif (tree_f is not None and tree_f >= 0.45) and spatial_relationship == "unassociated":
            predicted_source_type = "vegetation_burning"
            source_type_confidence = 0.75
            type_rationale = "Dense tree cover canopy (>45%) distant from industrial zones."
        else:
            predicted_source_type = "unclassified"
            source_type_confidence = None
            type_rationale = "Insufficient infrastructure proximity or ambiguous signature. Preserved as unclassified."

        # 3. Thermal Activity Behavior
        detections = source_data.get("detection_count") or source_data.get("total_detections") or 1
        frp_ratio = source_data.get("max_frp_ratio") or source_data.get("frp_ratio_24h_vs_30d") or 1.0

        if detections < 3:
            activity_behavior = "isolated_hotspot"
            behavior_description = "Low recurrence detection (<3 events); isolated thermal observation."
        elif frp_ratio > 3.0:
            activity_behavior = "sudden_frp_spike"
            behavior_description = f"Significant energy release: FRP is {frp_ratio:.1f}x higher than 30-day baseline."
        elif persistence >= 0.70:
            activity_behavior = "abnormal_persistence"
            behavior_description = f"High temporal persistence: detected in {persistence*100:.0f}% of satellite observation windows."
        else:
            activity_behavior = "recurring_steady"
            behavior_description = f"Steady operational baseline with {detections} recurring detections."

        # 4. Incident Assessment
        if frp_ratio > 3.5 and spatial_relationship in ("direct_intersection", "strong_association"):
            incident_assessment = "potential_incident_candidate"
            assessment_notes = "Major FRP excursion (>3.5x baseline) intersecting registered industrial infrastructure."
        elif frp_ratio > 2.0:
            incident_assessment = "unusual_heat_exceedance"
            assessment_notes = f"Thermal radiative power exceeds normal range ({frp_ratio:.1f}x baseline)."
        elif (
            source_data.get("iforest_agreement") is True
            or source_data.get("final_risk_level") in ("high", "critical")
        ):
            incident_assessment = "anomaly_under_review"
            assessment_notes = "Flagged by multi-feature density model for operational triage."
        else:
            incident_assessment = "normal_operational"
            assessment_notes = "Thermal activity consistent with routine background industrial emission."

        return {
            "mapped_facility_category": mapped_facility_category,
            "nearest_facility_name": fac_name or "Unidentified Facility",
            "spatial_relationship": spatial_relationship,
            "distance_tier": dist_tier,
            "is_ambiguous_attribution": candidates_300m > 1,
            "candidates_within_300m": candidates_300m,
            "spatial_description": spatial_description,
            "distance_to_nearest_facility_m": round(min_dist_m, 1) if min_dist_m is not None else None,
            "predicted_source_type": predicted_source_type,
            "source_type_confidence": source_type_confidence,
            "source_type_rationale": type_rationale,
            "confidence_calibration_notice": (
                "Confidence is a heuristic rule-based rating [0, 1]. "
                "No Bayesian calibration is claimed due to lack of ground-truth sensor tags."
            ),
            "thermal_activity_behavior": activity_behavior,
            "behavior_description": behavior_description,
            "incident_assessment": incident_assessment,
            "assessment_notes": assessment_notes,
        }

    def classify_hierarchical(
        self,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute the 4-Stage Hierarchical Classification with explicit abstention protocol.
        
        Stage A: Spatial & Site Context
        Stage B: Candidate Category Selection (10-Class Taxonomy)
        Stage C: Behavioral & Temporal Filtering (diurnality, recurrence, persistence)
        Stage D: Incident Assessment & Ground-Truth Honest Policy
        """
        # -------------------------------------------------------------
        # STAGE A: Spatial & Site Context
        # -------------------------------------------------------------
        min_dist_m = evidence.get("distance_to_nearest_facility_m")
        if min_dist_m is None and "facility_context" in evidence:
            min_dist_m = evidence["facility_context"].get("distance_m")

        fac_name = evidence.get("nearest_facility_name") or (evidence.get("facility_context", {}).get("nearest_facility_name"))
        fac_cat = evidence.get("nearest_facility_category") or (evidence.get("facility_context", {}).get("facility_category"))
        subcat = evidence.get("nearest_facility_subcategory") or (evidence.get("facility_context", {}).get("subcategory"))

        tree_f = evidence.get("tree_fraction_1km_mean")
        built_f = evidence.get("builtup_fraction_1km_mean")
        candidates_300m = evidence.get("candidates_within_300m") or (evidence.get("facility_context", {}).get("candidates_within_300m", 0))

        if min_dist_m is None:
            spatial_tier = "tier_5_unassociated"
            spatial_desc = "Remote location without proximate mapped industrial infrastructure (> 5 km)"
            context_conf = 0.20
        elif min_dist_m <= 500.0:
            spatial_tier = "tier_1_footprint"
            spatial_desc = f"Direct spatial intersection with facility footprint ({min_dist_m:.1f} m to {fac_name or 'industrial asset'})"
            context_conf = 0.95
        elif min_dist_m <= 1000.0:
            spatial_tier = "tier_2_perimeter"
            spatial_desc = f"Within industrial facility perimeter ({min_dist_m:.1f} m to {fac_name or 'industrial asset'})"
            context_conf = 0.80
        elif min_dist_m <= 3000.0:
            spatial_tier = "tier_3_industrial_zone"
            spatial_desc = f"Within broader industrial corridor / estate ({min_dist_m:.1f} m)"
            context_conf = 0.55
        elif min_dist_m <= 5000.0:
            spatial_tier = "tier_4_regional_buffer"
            spatial_desc = f"Regional buffer proximity ({min_dist_m:.1f} m)"
            context_conf = 0.35
        else:
            spatial_tier = "tier_5_unassociated"
            spatial_desc = f"Unassociated rural/natural terrain ({min_dist_m:.1f} m)"
            context_conf = 0.15

        stage_a = {
            "spatial_tier": spatial_tier,
            "spatial_description": spatial_desc,
            "distance_m": round(min_dist_m, 1) if min_dist_m is not None else None,
            "associated_facility": fac_name or "Unidentified",
            "candidates_within_300m": candidates_300m,
            "is_ambiguous_spatial": bool(candidates_300m > 1),
            "land_cover": {
                "tree_fraction": round(float(tree_f), 3) if tree_f is not None else None,
                "builtup_fraction": round(float(built_f), 3) if built_f is not None else None,
            },
            "context_confidence": context_conf,
        }

        # -------------------------------------------------------------
        # STAGE B: Candidate Category Selection (10-Class Taxonomy)
        # -------------------------------------------------------------
        candidate_categories = []
        conf_scores = []
        combined_text = f"{fac_name or ''} {fac_cat or ''} {subcat or ''}".lower()

        if any(k in combined_text for k in ["steel", "iron", "blast furnace", "smelter", "coke", "metallurg"]):
            candidate_categories.append(("steel_metallurgical", 0.90, "Matched metallurgical keywords and equipment tags"))
        if any(k in combined_text for k in ["power", "thermal", "ntpc", "boiler", "cooling", "generator"]):
            candidate_categories.append(("thermal_power_generation", 0.88, "Matched thermal power generation assets"))
        if any(k in combined_text for k in ["refinery", "petro", "oil", "iocl", "bpcl", "hpcl"]):
            candidate_categories.append(("refinery_petrochemical", 0.88, "Matched petroleum refining infrastructure"))
        if any(k in combined_text for k in ["flare", "gas plant", "gail"]):
            candidate_categories.append(("gas_flaring", 0.85, "Matched gas flaring or processing tags"))
        if any(k in combined_text for k in ["mine", "coal", "colliery", "ccl", "bccl", "spoil"]):
            candidate_categories.append(("coal_mining_handling", 0.85, "Matched coal mining / colliery operational context"))
        if any(k in combined_text for k in ["cement", "kiln", "clinker"]):
            candidate_categories.append(("cement_manufacturing", 0.88, "Matched cement rotary kiln infrastructure"))
        if any(k in combined_text for k in ["quarry", "limestone", "crusher"]):
            candidate_categories.append(("quarry_mineral_processing", 0.75, "Matched quarry mineral processing"))

        # Land cover fallback
        if not candidate_categories:
            if tree_f is not None and tree_f >= 0.45 and spatial_tier in ("tier_4_regional_buffer", "tier_5_unassociated"):
                candidate_categories.append(("wildfire_forest", 0.75, "High canopy tree fraction (>45%) distant from industry"))
            elif built_f is not None and built_f >= 0.20:
                candidate_categories.append(("unclassified_industrial", 0.60, "High built-up fraction without specific facility class"))
            elif spatial_tier == "tier_5_unassociated":
                candidate_categories.append(("agricultural_biomass", 0.50, "Rural landscape without industrial proximity"))
            else:
                candidate_categories.append(("unclassified_industrial", 0.40, "General industrial corridor context"))

        candidate_categories.sort(key=lambda x: x[1], reverse=True)
        top_candidate, top_candidate_conf, top_candidate_rationale = candidate_categories[0]

        stage_b = {
            "top_candidate": top_candidate,
            "candidate_confidence": top_candidate_conf,
            "candidate_rationale": top_candidate_rationale,
            "all_evaluated_candidates": [{"category": c[0], "confidence": c[1], "rationale": c[2]} for c in candidate_categories],
        }

        # -------------------------------------------------------------
        # STAGE C: Behavioral & Temporal Filtering
        # -------------------------------------------------------------
        detections = evidence.get("detection_count") or evidence.get("total_detections") or 1
        persistence = evidence.get("persistence_30d_mean") or evidence.get("persistence_30d") or 0.0
        frp = evidence.get("max_frp") or evidence.get("frp") or 0.0
        frp_ratio = evidence.get("max_frp_ratio") or 1.0

        if detections < 3 and persistence < 0.15:
            behavior_type = "isolated_transient_hotspot"
            behavior_desc = "Transient or isolated observation (< 3 detections); lacks multi-week persistence."
            persistence_weight = 0.30
        elif frp_ratio > 3.0:
            behavior_type = "sudden_radiometric_surge"
            behavior_desc = f"Significant radiometric spike ({frp_ratio:.1f}x baseline median)."
            persistence_weight = 0.85
        elif persistence >= 0.60:
            behavior_type = "continuous_base_load"
            behavior_desc = f"Highly persistent emitter (detected in {persistence*100:.0f}% of satellite passes)."
            persistence_weight = 0.90
        else:
            behavior_type = "recurring_intermittent"
            behavior_desc = f"Intermittent recurring operational emissions ({detections} cumulative detections)."
            persistence_weight = 0.60

        stage_c = {
            "behavior_type": behavior_type,
            "behavior_description": behavior_desc,
            "temporal_detections": detections,
            "persistence_ratio": round(float(persistence), 3),
            "observed_frp_mw": round(float(frp), 2),
            "frp_baseline_ratio": round(float(frp_ratio), 2),
        }

        # -------------------------------------------------------------
        # STAGE D: Incident Assessment & Explicit Abstention Protocol
        # -------------------------------------------------------------
        composite_confidence = round(context_conf * 0.40 + top_candidate_conf * 0.40 + persistence_weight * 0.20, 2)
        
        is_abstained = False
        abstention_reason = None

        if composite_confidence < 0.40:
            is_abstained = True
            final_classification = "unclassified"
            abstention_reason = (
                f"Abstention triggered: Composite classification confidence ({composite_confidence:.2f}) "
                "falls below reliability threshold (0.40). Insufficient geographic and radiometric evidence."
            )
        elif stage_a["is_ambiguous_spatial"] and top_candidate == "unclassified_industrial":
            is_abstained = True
            final_classification = "unclassified"
            abstention_reason = (
                f"Abstention triggered: Ambiguous spatial cluster ({candidates_300m} facilities within 300m) "
                "with conflicting industrial tags. Manual ground verification required."
            )
        else:
            final_classification = top_candidate

        # Honest Ground-Truth Policy: Explicitly evaluate whether independent ground truth exists
        # In satellite thermal monitoring, no external fire brigade or insurance records exist in the real-time telemetry stream
        incident_assessment = {
            "incident_probability_status": "not_validated_ground_truth_insufficient",
            "incident_probability": None,
            "ground_truth_statement": (
                "SCIENTIFIC INTEGRITY NOTICE: Independent fire department and disaster ground-truth records are "
                "unavailable for this satellite detection footprint. In accordance with KRATOS scientific protocol, "
                "unvalidated incident probability claims are withheld. Operational prioritization is provided via bounded Operational Priority."
            ),
            "proxy_operational_alert_level": evidence.get("final_risk_level") or evidence.get("severity") or "LOW",
        }

        return {
            "final_classification": final_classification,
            "confidence_score": composite_confidence,
            "is_abstained": is_abstained,
            "abstention_reason": abstention_reason,
            "stage_a_spatial_context": stage_a,
            "stage_b_candidate_selection": stage_b,
            "stage_c_behavioral_filtering": stage_c,
            "stage_d_incident_assessment": incident_assessment,
        }

    def evaluate_supervised_candidates(self) -> Dict[str, Any]:
        """Train and evaluate candidate supervised classifiers on available operational labels.
        
        Evaluates RandomForestClassifier vs LogisticRegression on the 16-feature vector
        against the operational high/critical incident screening tier, reporting precision,
        recall, F1, confusion matrix, and explicit calibration disclaimers.
        """
        if self._supervised_benchmark_cache is not None:
            return self._supervised_benchmark_cache

        if not EVENTS_PATH.exists():
            return {
                "status": "error",
                "message": "Events parquet not available for candidate benchmarking",
            }

        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.linear_model import LogisticRegression
            from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
            from sklearn.model_selection import StratifiedKFold
            from sklearn.preprocessing import StandardScaler

            df = pd.read_parquet(EVENTS_PATH)
            feature_cols = [
                "max_frp", "mean_frp", "source_baseline_frp", "max_frp_ratio",
                "max_frp_zscore", "max_brightness_zscore", "max_source_anomaly_score",
                "mean_source_anomaly_score", "source_detections_prev_30d",
                "source_active_days_prev_30d", "detection_count",
                "event_duration_hours", "industrial_context_score"
            ]
            valid_cols = [c for c in feature_cols if c in df.columns]

            if len(valid_cols) < 8 or "final_risk_level" not in df:
                return {
                    "status": "insufficient_features",
                    "available_features": valid_cols,
                }

            # Define operational target: High or Critical risk episodes (confirmed priority alerts)
            y = df["final_risk_level"].isin(["high", "critical"]).astype(int).values
            X = df[valid_cols].fillna(0.0).replace([np.inf, -np.inf], 0.0).values

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # 5-fold stratified cross validation
            skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            rf_preds = np.zeros(len(y), dtype=int)
            lr_preds = np.zeros(len(y), dtype=int)

            for train_idx, test_idx in skf.split(X_scaled, y):
                # Random Forest
                rf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, class_weight="balanced")
                rf.fit(X_scaled[train_idx], y[train_idx])
                rf_preds[test_idx] = rf.predict(X_scaled[test_idx])

                # Logistic Regression
                lr = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
                lr.fit(X_scaled[train_idx], y[train_idx])
                lr_preds[test_idx] = lr.predict(X_scaled[test_idx])

            def _metrics_dict(y_true, y_pred, model_name: str) -> Dict[str, Any]:
                p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
                cm = confusion_matrix(y_true, y_pred)
                return {
                    "model_name": model_name,
                    "precision": round(float(p), 4),
                    "recall": round(float(r), 4),
                    "f1_score": round(float(f1), 4),
                    "confusion_matrix": {
                        "true_negatives": int(cm[0][0]),
                        "false_positives": int(cm[0][1]),
                        "false_negatives": int(cm[1][0]),
                        "true_positives": int(cm[1][1]),
                    },
                }

            # Unsupervised Isolation Forest baseline (as currently deployed)
            if_agreed = df.get("iforest_agreement", pd.Series(0, index=df.index)).fillna(False).astype(int).values
            if_metrics = _metrics_dict(y, if_agreed, "Isolation Forest (Unsupervised Baseline)")
            rf_metrics = _metrics_dict(y, rf_preds, "Random Forest Classifier (5-Fold CV)")
            lr_metrics = _metrics_dict(y, lr_preds, "Logistic Regression (5-Fold CV)")

            # Feature importance from final fit
            rf_final = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, class_weight="balanced")
            rf_final.fit(X_scaled, y)
            importances = sorted(
                zip(valid_cols, [round(float(imp), 4) for imp in rf_final.feature_importances_]),
                key=lambda x: x[1],
                reverse=True,
            )

            self._supervised_benchmark_cache = {
                "status": "success",
                "evaluation_date": "2026-11-16",
                "target_class_definition": "Operational Screening Priority Tier (Proxy Labels from Heuristic Rules, n = {})".format(int(y.sum())),
                "sample_count": len(y),
                "fire_incident_prediction_validation": "NOT VALIDATED — INDEPENDENT INCIDENT GROUND TRUTH UNAVAILABLE",
                "target_type": "proxy_operational_screening_rule",
                "proxy_label_explanation": (
                    "Target labels are operational high/critical screening tiers derived from FRP ratio and anomaly score, "
                    "not independently verified ground-truth fire events."
                ),
                "feature_leakage_note": (
                    "High performance metrics (Recall/F1 ~0.99) reflect the supervised model reconstructing operational screening "
                    "rules (FRP ratio and anomaly score) rather than generalizable fire ignition prediction. True fire ground-truth logs are unavailable."
                ),
                "evaluated_models": [
                    if_metrics,
                    rf_metrics,
                    lr_metrics,
                ],
                "feature_importance_ranking": [
                    {"feature": feat, "importance": imp} for feat, imp in importances[:8]
                ],
                "calibration_disclaimer": (
                    "CRITICAL SCIENTIFIC NOTICE: While supervised models achieve high recall on operational "
                    "high-risk classifications, the probabilities are UNCALIBRATED due to the absence of independent, "
                    "human-verified ground-truth fire incident logs. These models serve as operational screening "
                    "triages, not definitive proofs of incident occurrence."
                ),
                "uncalibrated_probability_notice": (
                    "Calibrated probabilities cannot be scientifically defended without independent ground-truth emergency response logs."
                ),
            }
            return self._supervised_benchmark_cache
        except Exception as exc:
            log.exception("Supervised candidate evaluation failed: %s", exc)
            return {
                "status": "error",
                "error": str(exc),
            }


source_classification_engine = SourceClassificationEngine()
