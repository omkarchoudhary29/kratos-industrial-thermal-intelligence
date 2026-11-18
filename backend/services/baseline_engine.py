"""backend/services/baseline_engine.py
------------------------------------
KRATOS V3.1 — Multi-Level Historical Baseline Engine.

Implements 4 hierarchical baseline levels:
  Level 1: Source-Specific Baseline (by persistent thermal_source_id)
  Level 2: Facility-Specific Baseline (by OSM facility ID / name)
  Level 3: Category-Specific Baseline (by industrial facility category / subcategory)
  Level 4: Regional Context Baseline (by monitored corridor / region)

Features:
  - Point-in-time filtering: excludes future observations relative to event timestamp.
  - Non-parametric quantiles: P25, P50 (median), P75, P90, P95, P99.
  - Robust dispersion metrics: Median Absolute Deviation (MAD), robust MAD z-score, IQR.
  - Baseline Maturity Tiers:
      * N < 5:   "insufficient" (deviations withheld, regional fallback flagged)
      * 5 <= N < 15: "preliminary" (median & IQR computed, sensitive to outliers)
      * 15 <= N < 30: "developing" (robust quantiles enabled)
      * N >= 30: "mature" (full quantile spectrum and parametric drift enabled)
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from services.artifact_resolver import get_events_parquet_path, get_sources_parquet_path

log = logging.getLogger("baseline_engine")

PROJECT_DIR = Path(__file__).resolve().parents[2]
try:
    EVENTS_PATH = get_events_parquet_path()
except Exception:
    EVENTS_PATH = PROJECT_DIR / "data" / "processed" / "final_fused_events.parquet"

try:
    SOURCES_PATH = get_sources_parquet_path()
except Exception:
    SOURCES_PATH = PROJECT_DIR / "data" / "processed" / "thermal_sources.parquet"


def _json_safe(v: Any) -> Any:
    if v is None or pd.isna(v):
        return None
    if isinstance(v, (np.floating, float)):
        if math.isnan(v) or math.isinf(v):
            return None
        return round(float(v), 3)
    if isinstance(v, (np.integer, int)):
        return int(v)
    if isinstance(v, (pd.Timestamp, np.datetime64, datetime)):
        return str(v)
    return v


class MultiLevelBaselineEngine:
    def __init__(self):
        self._events_df: Optional[pd.DataFrame] = None
        self._sources_df: Optional[pd.DataFrame] = None
        self._regional_baselines_cache: Dict[str, Dict[str, Any]] = {}
        self._category_baselines_cache: Dict[str, Dict[str, Any]] = {}

    def _load_data(self) -> None:
        if self._events_df is None and EVENTS_PATH.exists():
            try:
                self._events_df = pd.read_parquet(EVENTS_PATH)
                if "event_date" in self._events_df.columns:
                    self._events_df["event_date"] = pd.to_datetime(self._events_df["event_date"], utc=True)
            except Exception as e:
                log.error("Failed to load fused events parquet: %s", e)
                self._events_df = pd.DataFrame()

        if self._sources_df is None and SOURCES_PATH.exists():
            try:
                self._sources_df = pd.read_parquet(SOURCES_PATH)
            except Exception as e:
                log.error("Failed to load thermal sources parquet: %s", e)
                self._sources_df = pd.DataFrame()

    @staticmethod
    def get_maturity_tier(n: int) -> Tuple[str, str]:
        """Return (tier_name, description)."""
        if n < 5:
            return "insufficient", "Sample size N < 5 is statistically insufficient; baseline deviations withheld to prevent distortion."
        elif n < 15:
            return "preliminary", "Sample size 5 <= N < 15 represents an early empirical baseline; sensitive to individual extremes."
        elif n < 30:
            return "developing", "Sample size 15 <= N < 30 provides robust non-parametric quantiles and standard deviation."
        else:
            return "mature", "Sample size N >= 30 provides high statistical confidence and stable tail quantiles (P95, P99)."

    @staticmethod
    def calculate_robust_stats(values: Union[List[float], np.ndarray, pd.Series]) -> Dict[str, Any]:
        """Compute robust non-parametric metrics on an array of numbers."""
        arr = np.array(values, dtype=float)
        arr = arr[~np.isnan(arr)]
        n = len(arr)

        tier, tier_desc = MultiLevelBaselineEngine.get_maturity_tier(n)

        if n == 0:
            return {
                "sample_size": 0,
                "maturity_tier": tier,
                "maturity_description": tier_desc,
                "mean": None,
                "std": None,
                "median": None,
                "mad": None,
                "iqr": None,
                "p25": None,
                "p50": None,
                "p75": None,
                "p90": None,
                "p95": None,
                "p99": None,
                "min": None,
                "max": None,
            }

        median_val = float(np.median(arr))
        mad_val = float(np.median(np.abs(arr - median_val)))
        mean_val = float(np.mean(arr))
        std_val = float(np.std(arr, ddof=1)) if n > 1 else 0.0

        p25 = float(np.percentile(arr, 25))
        p50 = median_val
        p75 = float(np.percentile(arr, 75))
        p90 = float(np.percentile(arr, 90))
        p95 = float(np.percentile(arr, 95))
        p99 = float(np.percentile(arr, 99))
        iqr = float(p75 - p25)

        return {
            "sample_size": n,
            "maturity_tier": tier,
            "maturity_description": tier_desc,
            "mean": _json_safe(mean_val),
            "std": _json_safe(std_val),
            "median": _json_safe(median_val),
            "mad": _json_safe(mad_val),
            "iqr": _json_safe(iqr),
            "p25": _json_safe(p25),
            "p50": _json_safe(p50),
            "p75": _json_safe(p75),
            "p90": _json_safe(p90),
            "p95": _json_safe(p95),
            "p99": _json_safe(p99),
            "min": _json_safe(float(np.min(arr))),
            "max": _json_safe(float(np.max(arr))),
        }

    @staticmethod
    def compute_deviation(
        observed_value: float,
        baseline_stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compute deviations against baseline with robust MAD z-score and ratio."""
        n = baseline_stats.get("sample_size", 0)
        median = baseline_stats.get("median")
        mad = baseline_stats.get("mad")
        mean = baseline_stats.get("mean")
        std = baseline_stats.get("std")
        p95 = baseline_stats.get("p95")
        p99 = baseline_stats.get("p99")

        if observed_value is None or math.isnan(observed_value):
            return {
                "observed_value": None,
                "ratio_to_median": None,
                "mad_zscore": None,
                "standard_zscore": None,
                "exceeds_p95": False,
                "exceeds_p99": False,
                "reliability_flag": "insufficient_data",
            }

        # Guard against zero or insufficient data
        if n < 5 or median is None:
            return {
                "observed_value": _json_safe(observed_value),
                "ratio_to_median": None,
                "mad_zscore": None,
                "standard_zscore": None,
                "exceeds_p95": False,
                "exceeds_p99": False,
                "reliability_flag": "withheld_insufficient_samples",
            }

        # Ratio to median
        ratio_to_median = (observed_value / median) if median > 0 else (1.0 if observed_value == 0 else 999.0)

        # Robust MAD z-score (using standard 0.6745 normal consistency factor)
        # z_mad = 0.6745 * (x - median) / MAD
        if mad is not None and mad > 0:
            mad_zscore = 0.6745 * (observed_value - median) / mad
        else:
            # Fallback to mean/std if MAD is 0 (constant baseline)
            if std is not None and std > 0:
                mad_zscore = (observed_value - mean) / std
            else:
                mad_zscore = 0.0 if observed_value == median else 5.0

        # Standard parametric z-score
        standard_zscore = ((observed_value - mean) / std) if (std is not None and std > 0) else None

        exceeds_p95 = (observed_value > p95) if p95 is not None else False
        exceeds_p99 = (observed_value > p99) if p99 is not None else False

        return {
            "observed_value": _json_safe(observed_value),
            "ratio_to_median": _json_safe(ratio_to_median),
            "mad_zscore": _json_safe(mad_zscore),
            "standard_zscore": _json_safe(standard_zscore),
            "exceeds_p95": bool(exceeds_p95),
            "exceeds_p99": bool(exceeds_p99),
            "reliability_flag": "statistically_sound" if n >= 15 else "preliminary_caution",
        }

    def get_multi_level_baseline(
        self,
        thermal_source_id: Optional[str] = None,
        facility_id: Optional[str] = None,
        facility_category: Optional[str] = None,
        region_name: Optional[str] = None,
        point_in_time: Optional[Union[str, pd.Timestamp, datetime]] = None,
        observed_frp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Compute the full 4-level baseline hierarchy with point-in-time filtering."""
        self._load_data()

        df = self._events_df
        cutoff_dt: Optional[pd.Timestamp] = None
        if point_in_time is not None and df is not None and not df.empty:
            try:
                cutoff_dt = pd.to_datetime(point_in_time, utc=True)
            except Exception:
                cutoff_dt = None

        def filter_history(sub_df: pd.DataFrame) -> pd.DataFrame:
            if cutoff_dt is not None and "event_date" in sub_df.columns:
                return sub_df[sub_df["event_date"] < cutoff_dt]
            return sub_df

        result: Dict[str, Any] = {
            "query_context": {
                "thermal_source_id": thermal_source_id,
                "facility_id": facility_id,
                "facility_category": facility_category,
                "region_name": region_name,
                "point_in_time": str(cutoff_dt) if cutoff_dt else None,
                "observed_frp": _json_safe(observed_frp),
            },
            "level_1_source": None,
            "level_2_facility": None,
            "level_3_category": None,
            "level_4_regional": None,
            "recommended_baseline_level": "level_4_regional",
            "active_maturity_tier": "insufficient",
        }

        if df is None or df.empty:
            return result

        # -------------------------------------------------------------
        # Level 1: Source-Specific Baseline
        # -------------------------------------------------------------
        if thermal_source_id:
            src_events = df[df["thermal_source_id"] == thermal_source_id]
            src_events = filter_history(src_events)
            if not src_events.empty and "max_frp" in src_events.columns:
                frp_vals = src_events["max_frp"].dropna().values
                stats = self.calculate_robust_stats(frp_vals)
                dev = self.compute_deviation(observed_frp, stats) if observed_frp is not None else {}
                result["level_1_source"] = {
                    "identifier": thermal_source_id,
                    "statistics": stats,
                    "deviation": dev,
                }
                if stats["maturity_tier"] in ("mature", "developing"):
                    result["recommended_baseline_level"] = "level_1_source"
                    result["active_maturity_tier"] = stats["maturity_tier"]
                elif stats["maturity_tier"] == "preliminary":
                    result["recommended_baseline_level"] = "level_1_source"
                    result["active_maturity_tier"] = "preliminary"

        # -------------------------------------------------------------
        # Level 2: Facility-Specific Baseline
        # -------------------------------------------------------------
        if facility_id:
            # Query events associated with this facility
            fac_col = None
            for c in ["nearest_facility_id", "facility_id", "osm_id"]:
                if c in df.columns:
                    fac_col = c
                    break
            if fac_col:
                fac_events = df[df[fac_col].astype(str) == str(facility_id)]
                fac_events = filter_history(fac_events)
                if not fac_events.empty and "max_frp" in fac_events.columns:
                    stats = self.calculate_robust_stats(fac_events["max_frp"].dropna().values)
                    dev = self.compute_deviation(observed_frp, stats) if observed_frp is not None else {}
                    result["level_2_facility"] = {
                        "identifier": str(facility_id),
                        "statistics": stats,
                        "deviation": dev,
                    }
                    if result["active_maturity_tier"] == "insufficient" and stats["maturity_tier"] != "insufficient":
                        result["recommended_baseline_level"] = "level_2_facility"
                        result["active_maturity_tier"] = stats["maturity_tier"]

        # -------------------------------------------------------------
        # Level 3: Category-Specific Baseline
        # -------------------------------------------------------------
        if facility_category:
            cat_norm = str(facility_category).lower().strip()
            # Match against category columns if present
            cat_col = None
            for c in ["nearest_facility_category", "facility_category", "nearest_industry_type"]:
                if c in df.columns:
                    cat_col = c
                    break
            if cat_col:
                cat_events = df[df[cat_col].astype(str).str.lower().str.contains(cat_norm[:5], na=False)]
                cat_events = filter_history(cat_events)
                if not cat_events.empty and "max_frp" in cat_events.columns:
                    stats = self.calculate_robust_stats(cat_events["max_frp"].dropna().values)
                    dev = self.compute_deviation(observed_frp, stats) if observed_frp is not None else {}
                    result["level_3_category"] = {
                        "category_name": facility_category,
                        "statistics": stats,
                        "deviation": dev,
                    }
                    if result["active_maturity_tier"] == "insufficient" and stats["maturity_tier"] != "insufficient":
                        result["recommended_baseline_level"] = "level_3_category"
                        result["active_maturity_tier"] = stats["maturity_tier"]

        # -------------------------------------------------------------
        # Level 4: Regional Context Baseline
        # -------------------------------------------------------------
        if region_name:
            reg_norm = str(region_name).lower().strip()
            reg_events = df[df["region_name"].astype(str).str.lower() == reg_norm]
            if reg_events.empty:
                # Try alias / substring
                reg_events = df[df["region_name"].astype(str).str.lower().str.contains(reg_norm[:4], na=False)]
            reg_events = filter_history(reg_events)
            if not reg_events.empty and "max_frp" in reg_events.columns:
                stats = self.calculate_robust_stats(reg_events["max_frp"].dropna().values)
                dev = self.compute_deviation(observed_frp, stats) if observed_frp is not None else {}
                result["level_4_regional"] = {
                    "region_name": region_name,
                    "statistics": stats,
                    "deviation": dev,
                }
                if result["active_maturity_tier"] == "insufficient":
                    result["recommended_baseline_level"] = "level_4_regional"
                    result["active_maturity_tier"] = stats["maturity_tier"]

        return result


baseline_engine = MultiLevelBaselineEngine()
