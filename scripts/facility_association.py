#!/usr/bin/env python3
"""Compute spatial association between thermal observations/sources and OSM facilities.

Evaluates metric distance using PostGIS geography:
- Direct intersection / inside polygon (distance = 0m, ST_Intersects)
- Strong association (0m < distance <= 300m)
- Nearby mapped facility:
  - 300m < distance <= 1000m (nearby <= 1km)
  - 1000m < distance <= 2000m (nearby <= 2km)
- Multiple candidates (>= 2 facilities within 300m / 1000m)
- Unmatched (distance > 2000m or no facility found)

Evaluates both:
1. 312 Persistent Thermal Sources (from thermal_sources.parquet)
2. 692 Raw Fire Detections (from PostgreSQL fire_detections table)
"""

import json
import os
import sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in environment or .env")

engine = create_engine(DATABASE_URL)


def analyze_persistent_sources():
    parquet_path = REPO_ROOT / "data" / "processed" / "thermal_sources.parquet"
    if not parquet_path.exists():
        parquet_path = REPO_ROOT / "runtime_artifacts" / "thermal_sources.parquet"
    df = pd.read_parquet(parquet_path)
    total_sources = len(df)
    print(f"\n=======================================================", flush=True)
    print(f"1. PERSISTENT THERMAL SOURCES ANALYSIS (Total: {total_sources})", flush=True)
    print(f"=======================================================", flush=True)

    results = []
    with engine.connect() as conn:
        for idx, row in df.iterrows():
            s_id = str(row.get("thermal_source_id"))
            lat = float(row.get("source_latitude") or row.get("latitude"))
            lon = float(row.get("source_longitude") or row.get("longitude"))
            reg = str(row.get("region_name") or "")

            q = text("""
                SELECT 
                    id, osm_id, osm_type, name, facility_category, subcategory,
                    ST_Distance(
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        geometry::geography
                    ) AS dist_m,
                    ST_Intersects(
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                        geometry
                    ) AS is_intersect
                FROM osm_facilities
                WHERE geometry && ST_Expand(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 0.02)
                  AND ST_DWithin(
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                    geometry::geography,
                    2000.0
                )
                ORDER BY dist_m ASC;
            """)
            matches = conn.execute(q, {"lon": lon, "lat": lat}).fetchall()

            if not matches:
                results.append({
                    "source_id": s_id,
                    "region": reg,
                    "latitude": lat,
                    "longitude": lon,
                    "association_tier": "unmatched",
                    "nearest_facility_id": None,
                    "nearest_osm_id": None,
                    "nearest_osm_type": None,
                    "nearest_facility_name": None,
                    "nearest_category": None,
                    "min_distance_m": None,
                    "candidates_300m": 0,
                    "candidates_1000m": 0,
                    "candidates_2000m": 0,
                })
            else:
                nearest = matches[0]
                is_intersect = any(m[7] for m in matches)
                min_dist = float(nearest[6])
                candidates_300 = sum(1 for m in matches if m[6] <= 300.0)
                candidates_1000 = sum(1 for m in matches if m[6] <= 1000.0)
                candidates_2000 = len(matches)

                if is_intersect or min_dist == 0.0:
                    tier = "direct_intersection"
                elif min_dist <= 300.0:
                    tier = "strong_association"
                elif min_dist <= 1000.0:
                    tier = "nearby_1000m"
                else:
                    tier = "nearby_2000m"

                results.append({
                    "source_id": s_id,
                    "region": reg,
                    "latitude": lat,
                    "longitude": lon,
                    "association_tier": tier,
                    "nearest_facility_id": nearest[0],
                    "nearest_osm_id": nearest[1],
                    "nearest_osm_type": nearest[2],
                    "nearest_facility_name": nearest[3],
                    "nearest_category": nearest[4],
                    "min_distance_m": round(min_dist, 2),
                    "candidates_300m": candidates_300,
                    "candidates_1000m": candidates_1000,
                    "candidates_2000m": candidates_2000,
                })

    res_df = pd.DataFrame(results)
    tier_counts = res_df["association_tier"].value_counts().to_dict()
    multiple_300 = int((res_df["candidates_300m"] > 1).sum())
    multiple_1000 = int((res_df["candidates_1000m"] > 1).sum())

    print("Tier breakdown:", flush=True)
    for tier in ["direct_intersection", "strong_association", "nearby_1000m", "nearby_2000m", "unmatched"]:
        count = tier_counts.get(tier, 0)
        pct = (count / total_sources) * 100
        print(f"  - {tier}: {count} ({pct:.1f}%)", flush=True)
    print(f"  - Multiple candidates within 300m: {multiple_300}", flush=True)
    print(f"  - Multiple candidates within 1000m: {multiple_1000}", flush=True)

    return {
        "total_sources": total_sources,
        "tier_counts": tier_counts,
        "multiple_300m": multiple_300,
        "multiple_1000m": multiple_1000,
        "sample_matched": [r for r in results if r["association_tier"] != "unmatched"][:10],
    }


def analyze_fire_detections():
    with engine.connect() as conn:
        total_detections = conn.execute(text("SELECT COUNT(*) FROM fire_detections;")).scalar()
        print(f"\n=======================================================", flush=True)
        print(f"2. FIRE DETECTIONS ANALYSIS (Total in DB: {total_detections})", flush=True)
        print(f"=======================================================", flush=True)

        sql = text("""
            WITH detection_distances AS (
                SELECT 
                    fd.id,
                    fd.detection_key,
                    fd.monitoring_region_id,
                    MIN(ST_Distance(fd.location::geography, f.geometry::geography)) AS min_dist_m,
                    BOOL_OR(ST_Intersects(fd.location, f.geometry)) AS is_intersect,
                    COUNT(f.id) FILTER (WHERE ST_DWithin(fd.location::geography, f.geometry::geography, 300.0)) AS candidates_300m,
                    COUNT(f.id) FILTER (WHERE ST_DWithin(fd.location::geography, f.geometry::geography, 1000.0)) AS candidates_1000m,
                    COUNT(f.id) AS candidates_2000m
                FROM fire_detections fd
                LEFT JOIN osm_facilities f
                    ON f.geometry && ST_Expand(fd.location, 0.02)
                   AND ST_DWithin(fd.location::geography, f.geometry::geography, 2000.0)
                GROUP BY fd.id, fd.detection_key, fd.monitoring_region_id
            )
            SELECT 
                CASE 
                    WHEN is_intersect OR min_dist_m = 0.0 THEN 'direct_intersection'
                    WHEN min_dist_m <= 300.0 THEN 'strong_association'
                    WHEN min_dist_m <= 1000.0 THEN 'nearby_1000m'
                    WHEN min_dist_m <= 2000.0 THEN 'nearby_2000m'
                    ELSE 'unmatched'
                END AS association_tier,
                COUNT(*) AS count,
                COUNT(*) FILTER (WHERE candidates_300m > 1) AS multi_300,
                COUNT(*) FILTER (WHERE candidates_1000m > 1) AS multi_1000
            FROM detection_distances
            GROUP BY 1
            ORDER BY count DESC;
        """)
        rows = conn.execute(sql).fetchall()

        tier_counts = {}
        total_multi_300 = 0
        total_multi_1000 = 0
        print("Tier breakdown:", flush=True)
        for tier, count, m300, m1000 in rows:
            tier_counts[tier] = count
            total_multi_300 += (m300 or 0)
            total_multi_1000 += (m1000 or 0)
            pct = (count / total_detections) * 100 if total_detections else 0
            print(f"  - {tier}: {count} ({pct:.1f}%)", flush=True)
        print(f"  - Multiple candidates within 300m: {total_multi_300}", flush=True)
        print(f"  - Multiple candidates within 1000m: {total_multi_1000}", flush=True)

        return {
            "total_detections": total_detections,
            "tier_counts": tier_counts,
            "multiple_300m": total_multi_300,
            "multiple_1000m": total_multi_1000,
        }


def main():
    sources_summary = analyze_persistent_sources()
    detections_summary = analyze_fire_detections()

    output = {
        "persistent_sources": {
            "total": sources_summary["total_sources"],
            "tiers": sources_summary["tier_counts"],
            "multiple_within_300m": sources_summary["multiple_300m"],
            "multiple_within_1000m": sources_summary["multiple_1000m"],
            "sample_matched": sources_summary["sample_matched"],
        },
        "fire_detections": {
            "total": detections_summary["total_detections"],
            "tiers": detections_summary["tier_counts"],
            "multiple_within_300m": detections_summary["multiple_300m"],
            "multiple_within_1000m": detections_summary["multiple_1000m"],
        }
    }

    out_path = REPO_ROOT / "data" / "processed" / "facility_association_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved association summary to: {out_path}", flush=True)


if __name__ == "__main__":
    main()
