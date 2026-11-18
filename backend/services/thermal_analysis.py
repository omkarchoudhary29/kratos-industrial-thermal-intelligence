"""backend/services/thermal_analysis.py
-------------------------------------
KRATOS V3 Phase 2 — Advanced Thermal Analysis Engine.

Provides:
  - Observation exploration and filtering
  - Statistical FRP distribution metrics (mean, median, max, std, quartiles, IQR)
  - FRP histogram distribution binning
  - Recurrence and persistence metrics (detections, active days, persistence index)
  - Diurnal (day vs night VIIRS overpass) analysis
  - Temporal trend aggregation (monthly and seasonal)
  - Source-specific baseline calculation strictly without future data leakage
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from services.artifact_resolver import get_events_parquet_path, get_sources_parquet_path

log = logging.getLogger("thermal_analysis")

PROJECT_DIR = Path(__file__).resolve().parents[2]
try:
    EVENTS_PATH = get_events_parquet_path()
except Exception:
    EVENTS_PATH = PROJECT_DIR / "data" / "processed" / "final_fused_events.parquet"

try:
    SOURCES_PATH = get_sources_parquet_path()
except Exception:
    SOURCES_PATH = PROJECT_DIR / "data" / "processed" / "thermal_sources.parquet"


def _clean_val(v: Any) -> Any:
    if v is None or pd.isna(v):
        return None
    if isinstance(v, (np.floating, float)):
        if math.isnan(v) or math.isinf(v):
            return None
        return round(float(v), 3)
    if isinstance(v, (np.integer, int)):
        return int(v)
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.isoformat()
    return v


class ThermalAnalysisEngine:
    def __init__(self):
        self._events_cache: Optional[pd.DataFrame] = None
        self._sources_cache: Optional[pd.DataFrame] = None

    def _get_events(self) -> pd.DataFrame:
        if self._events_cache is None and EVENTS_PATH.exists():
            df = pd.read_parquet(EVENTS_PATH)
            df["dt"] = pd.to_datetime(df["event_start"], utc=True, errors="coerce")
            self._events_cache = df
        return self._events_cache if self._events_cache is not None else pd.DataFrame()

    def _get_sources(self) -> pd.DataFrame:
        if self._sources_cache is None and SOURCES_PATH.exists():
            self._sources_cache = pd.read_parquet(SOURCES_PATH)
        return self._sources_cache if self._sources_cache is not None else pd.DataFrame()

    def get_frp_statistics(
        self,
        region: Optional[str] = None,
        source_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compute robust descriptive statistics and histogram distribution for FRP."""
        df = self._get_events()
        if df.empty:
            return {"count": 0, "status": "no_data"}

        subset = df.copy()
        if region:
            reg_norm = str(region).strip().lower().replace("-", "_").replace(" ", "_")
            if reg_norm == "vijayanagar":
                reg_norm = "vijayanagar_toranagallu"
            subset = subset[subset["region_name"].astype(str).str.lower().str.replace("-", "_").str.replace(" ", "_") == reg_norm]
        if source_id:
            subset = subset[subset["thermal_source_id"].astype(str) == str(source_id)]
        if start_time:
            try:
                st = pd.to_datetime(start_time, utc=True)
                subset = subset[subset["dt"] >= st]
            except Exception:
                pass
        if end_time:
            try:
                et = pd.to_datetime(end_time, utc=True)
                subset = subset[subset["dt"] <= et]
            except Exception:
                pass

        if subset.empty:
            return {"count": 0, "status": "empty_subset"}

        frp = subset["max_frp"].dropna()
        if frp.empty:
            return {"count": 0, "status": "no_frp_values"}

        count = len(frp)
        mean_v = float(frp.mean())
        std_v = float(frp.std()) if count > 1 else 0.0
        min_v = float(frp.min())
        p25_v = float(frp.quantile(0.25))
        median_v = float(frp.median())
        p75_v = float(frp.quantile(0.75))
        p90_v = float(frp.quantile(0.90))
        p99_v = float(frp.quantile(0.99))
        max_v = float(frp.max())
        iqr_v = p75_v - p25_v

        # Histogram Bins: [0-10, 10-25, 25-50, 50-100, 100-250, 250+] MW
        bins = [0, 10, 25, 50, 100, 250, float("inf")]
        bin_labels = ["0-10 MW", "10-25 MW", "25-50 MW", "50-100 MW", "100-250 MW", "250+ MW"]
        counts, _ = np.histogram(frp, bins=bins)
        histogram = [
            {"bin": label, "count": int(c), "percentage": round(float(c / count * 100), 2)}
            for label, c in zip(bin_labels, counts)
        ]

        # Diurnal Day vs Night Overpass distribution
        # VIIRS daytime pass is approx 06:00 to 18:00 UTC (11:30 to 23:30 IST),
        # but specifically over India daytime overpass is around 07:30-08:30 UTC (~13:00-14:00 IST).
        # Nighttime pass is around 19:30-20:30 UTC (~01:00-02:00 IST).
        utc_hours = subset["dt"].dt.hour
        is_daytime = (utc_hours >= 6) & (utc_hours <= 14)
        day_count = int(is_daytime.sum())
        night_count = int((~is_daytime).sum())

        return {
            "count": count,
            "mean_mw": round(mean_v, 2),
            "median_mw": round(median_v, 2),
            "std_mw": round(std_v, 2),
            "min_mw": round(min_v, 2),
            "p25_mw": round(p25_v, 2),
            "p75_mw": round(p75_v, 2),
            "p90_mw": round(p90_v, 2),
            "p99_mw": round(p99_v, 2),
            "max_mw": round(max_v, 2),
            "iqr_mw": round(iqr_v, 2),
            "histogram": histogram,
            "diurnal_breakdown": {
                "daytime_overpasses": day_count,
                "nighttime_overpasses": night_count,
                "daytime_pct": round(day_count / count * 100, 1) if count > 0 else 0.0,
                "nighttime_pct": round(night_count / count * 100, 1) if count > 0 else 0.0,
            },
        }

    def get_recurrence_and_persistence(self, source_id: str) -> Dict[str, Any]:
        """Compute recurrence, persistence, and active observation windows for a specific source."""
        df = self._get_events()
        sources_df = self._get_sources()

        src_events = df[df["thermal_source_id"].astype(str) == str(source_id)].sort_values("dt")
        if src_events.empty:
            return {"source_id": source_id, "status": "not_found", "total_detections": 0}

        total_detections = len(src_events)
        active_days = src_events["dt"].dt.floor("D").nunique()
        first_seen = src_events["dt"].min().isoformat()
        last_seen = src_events["dt"].max().isoformat()
        span_days = max(1, (src_events["dt"].max() - src_events["dt"].min()).days)

        active_weeks = src_events["dt"].dt.to_period("W").nunique()
        active_months = src_events["dt"].dt.to_period("M").nunique()

        # Recurrence frequency
        detections_per_active_month = round(total_detections / max(1, active_months), 2)
        detections_per_active_week = round(total_detections / max(1, active_weeks), 2)

        # Baseline FRP
        mean_frp = float(src_events["max_frp"].mean())
        max_frp = float(src_events["max_frp"].max())

        # Source metadata from sources catalog if present
        source_meta = {}
        if not sources_df.empty:
            match = sources_df[sources_df["thermal_source_id"].astype(str) == str(source_id)]
            if not match.empty:
                r = match.iloc[0]
                source_meta = {
                    "source_latitude": _clean_val(r.get("source_latitude", r.get("latitude"))),
                    "source_longitude": _clean_val(r.get("source_longitude", r.get("longitude"))),
                    "cluster_persistence_30d": _clean_val(r.get("persistence_30d_mean", r.get("persistence_30d"))),
                    "cluster_radius_m": _clean_val(r.get("cluster_radius_m", 300.0)),
                    "builtup_fraction": _clean_val(r.get("builtup_fraction_1km_mean")),
                    "tree_fraction": _clean_val(r.get("tree_fraction_1km_mean")),
                }

        return {
            "source_id": source_id,
            "status": "active",
            "total_detections": total_detections,
            "active_days_count": active_days,
            "span_days": span_days,
            "active_weeks_count": active_weeks,
            "active_months_count": active_months,
            "detections_per_active_month": detections_per_active_month,
            "detections_per_active_week": detections_per_active_week,
            "mean_frp_mw": round(mean_frp, 2),
            "max_frp_mw": round(max_frp, 2),
            "first_detection": first_seen,
            "latest_detection": last_seen,
            "source_metadata": source_meta,
        }

    def compute_source_baseline_without_leakage(
        self,
        source_id: str,
        target_timestamp: str,
        window_days: int = 30,
    ) -> Dict[str, Any]:
        """Compute the historical FRP baseline strictly from events prior to target_timestamp."""
        df = self._get_events()
        if df.empty:
            return {"baseline_available": False, "reason": "No events dataset"}

        target_dt = pd.to_datetime(target_timestamp, utc=True)
        window_start = target_dt - pd.Timedelta(days=window_days)

        # Strictly prior to target_dt (no lookahead / future leakage)
        prior_mask = (
            (df["thermal_source_id"].astype(str) == str(source_id))
            & (df["dt"] < target_dt)
            & (df["dt"] >= window_start)
        )
        prior_events = df.loc[prior_mask]

        if prior_events.empty:
            # Fall back to any prior observations before target_dt
            prior_all = df[(df["thermal_source_id"].astype(str) == str(source_id)) & (df["dt"] < target_dt)]
            if prior_all.empty:
                return {
                    "source_id": source_id,
                    "target_timestamp": target_dt.isoformat(),
                    "baseline_available": False,
                    "prior_observations_count": 0,
                    "reason": "First known observation for this thermal source; no historical prior exists.",
                }
            prior_events = prior_all

        prior_frp = prior_events["max_frp"].dropna()
        baseline_mean = float(prior_frp.mean())
        baseline_median = float(prior_frp.median())
        baseline_max = float(prior_frp.max())
        baseline_std = float(prior_frp.std()) if len(prior_frp) > 1 else 0.0

        return {
            "source_id": source_id,
            "target_timestamp": target_dt.isoformat(),
            "baseline_available": True,
            "window_days": window_days,
            "prior_observations_count": len(prior_frp),
            "baseline_mean_frp_mw": round(baseline_mean, 2),
            "baseline_median_frp_mw": round(baseline_median, 2),
            "baseline_max_frp_mw": round(baseline_max, 2),
            "baseline_std_frp_mw": round(baseline_std, 2),
            "leakage_protection": "Strict: no observations at or after target_timestamp were included.",
        }

    def get_temporal_trends(self, region: Optional[str] = None) -> Dict[str, Any]:
        """Compute monthly and quarterly trends of thermal observations and cumulative FRP."""
        df = self._get_events()
        if df.empty:
            return {"trends": []}

        subset = df.copy()
        if region:
            reg_norm = str(region).strip().lower().replace("-", "_").replace(" ", "_")
            if reg_norm == "vijayanagar":
                reg_norm = "vijayanagar_toranagallu"
            subset = subset[subset["region_name"].astype(str).str.lower().str.replace("-", "_").str.replace(" ", "_") == reg_norm]

        subset["month_period"] = subset["dt"].dt.to_period("M").astype(str)
        grouped = subset.groupby("month_period").agg(
            event_count=("max_frp", "count"),
            mean_frp=("max_frp", "mean"),
            max_frp=("max_frp", "max"),
            total_frp=("max_frp", "sum"),
        ).reset_index()

        trends = []
        for _, row in grouped.iterrows():
            trends.append({
                "period": row["month_period"],
                "event_count": int(row["event_count"]),
                "mean_frp_mw": round(float(row["mean_frp"]), 2),
                "max_frp_mw": round(float(row["max_frp"]), 2),
                "total_frp_mw": round(float(row["total_frp"]), 2),
            })

        return {
            "region": region or "All Regions (National)",
            "total_events": len(subset),
            "monthly_trends": trends,
        }


thermal_analysis_engine = ThermalAnalysisEngine()
