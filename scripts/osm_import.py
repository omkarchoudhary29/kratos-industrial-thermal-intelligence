#!/usr/bin/env python3
"""scripts/osm_import.py
---------------------
Overpass API importer for OSM industrial and energy facilities into PostgreSQL/PostGIS.
Fetches, caches, validates geometry, and safely loads facilities into osm_facilities table.
"""

import argparse
import json
import logging
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))

from backend.db.connection import get_db_uri
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("osm_import")

CACHE_DIR = REPO_ROOT / "data" / "raw" / "osm"

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


MONITORING_REGIONS = [
    {
        "id": 2,
        "key": "vijayanagar_toranagallu",
        "name": "Vijayanagar / Toranagallu Industrial Region Monitoring",
        "bbox": (15.1, 76.58, 15.24, 76.76),  # s, w, n, e
    },
    {
        "id": 3,
        "key": "talcher_angul",
        "name": "Talcher / Angul Industrial Corridor Monitoring",
        "bbox": (20.75, 84.75, 21.25, 85.25),
    },
    {
        "id": 4,
        "key": "dhanbad_bokaro",
        "name": "Dhanbad / Bokaro Industrial Corridor Monitoring",
        "bbox": (23.45, 85.75, 24.05, 86.45),
    },
    {
        "id": 5,
        "key": "singrauli_sonbhadra",
        "name": "Singrauli / Sonbhadra Energy Corridor Monitoring",
        "bbox": (23.75, 82.3, 24.4, 83.15),
    },
    {
        "id": 6,
        "key": "korba",
        "name": "Korba Power and Industrial Region Monitoring",
        "bbox": (22.15, 82.4, 22.75, 83.05),
    },
    {
        "id": 7,
        "key": "jamnagar_vadinar",
        "name": "Jamnagar / Vadinar Refinery Corridor Monitoring",
        "bbox": (22.15, 69.65, 22.75, 70.45),
    },
    {
        "id": 8,
        "key": "gadchiroli",
        "name": "Gadchiroli Forest Landscape Monitoring",
        "bbox": (19.5, 79.0, 20.8, 80.5),
    },
    {
        "id": 9,
        "key": "kanha",
        "name": "Kanha Forest Landscape Monitoring",
        "bbox": (21.3, 79.0, 23.2, 80.8),
    },
    {
        "id": 10,
        "key": "bastar",
        "name": "Bastar Forest Landscape Monitoring",
        "bbox": (17.8, 81.2, 19.8, 82.8),
    },
    {
        "id": 11,
        "key": "mizoram",
        "name": "Mizoram Forest Landscape Monitoring",
        "bbox": (22.0, 92.2, 24.0, 93.5),
    },
]


import ssl

ssl_ctx = ssl.create_default_context()

def build_overpass_query(bbox: Tuple[float, float, float, float]) -> str:
    s, w, n, e = bbox
    return f"""
[out:json][timeout:35];
(
  nwr["landuse"="industrial"]({s},{w},{n},{e});
  nwr["industrial"]({s},{w},{n},{e});
  nwr["power"~"plant|substation|generator"]({s},{w},{n},{e});
  nwr["man_made"~"works|storage_tank|chimney|refinery|flare"]({s},{w},{n},{e});
  nwr["landuse"="quarry"]({s},{w},{n},{e});
  nwr["natural"="quarry"]({s},{w},{n},{e});
  nwr["mine"]({s},{w},{n},{e});
  nwr["craft"]({s},{w},{n},{e});
);
out body geom;
"""


def fetch_from_overpass(query: str, cache_file: Path, force: bool = False) -> Dict[str, Any]:
    if not force and cache_file.exists() and cache_file.stat().st_size > 100:
        log.info("Loading cached OSM data from %s", cache_file)
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("Cache file corrupted, refetching: %s", e)

    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    last_err = None

    for endpoint in OVERPASS_ENDPOINTS:
        log.info("Querying Overpass at %s ...", endpoint)
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"User-Agent": "KratosThermalIntelligence/2.0 (SIH26162 Research)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=40, context=ssl_ctx) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    CACHE_DIR.mkdir(parents=True, exist_ok=True)
                    cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                    log.info("✓ Retrieved and cached %d elements.", len(payload.get("elements", [])))
                    return payload
        except Exception as exc:
            log.warning("Overpass endpoint %s failed: %s", endpoint, exc)
            last_err = exc
            time.sleep(1)

    raise RuntimeError(f"All Overpass endpoints failed. Last error: {last_err}")



def classify_facility(tags: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    power = str(tags.get("power", "")).lower()
    industrial = str(tags.get("industrial", "")).lower()
    man_made = str(tags.get("man_made", "")).lower()
    landuse = str(tags.get("landuse", "")).lower()
    natural = str(tags.get("natural", "")).lower()
    building = str(tags.get("building", "")).lower()

    if power in ("plant", "generator"):
        return "power_plant", tags.get("plant:source") or tags.get("generator:source") or power
    if power == "substation":
        return "substation", tags.get("substation") or "substation"
    if "refinery" in man_made or "refinery" in industrial or "refinery" in tags:
        return "refinery", "oil_refinery"
    if landuse == "quarry" or natural == "quarry" or "mine" in tags or industrial == "mining":
        return "mining_quarry", tags.get("resource") or "quarry"
    if man_made in ("works", "chimney", "flare", "storage_tank"):
        return "industrial", man_made
    if landuse == "industrial" or industrial or building in ("industrial", "manufacture", "warehouse"):
        return "industrial", industrial or building or "industrial_area"

    return "infrastructure", tags.get("craft") or "facility"


def element_to_wkt(el: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Convert OSM element to WKT geometry (preserving points, lines, polygons) and centroid WKT."""
    el_type = el.get("type")

    if el_type == "node":
        lat = el.get("lat")
        lon = el.get("lon")
        if lat is not None and lon is not None:
            pt = f"POINT({lon:.7f} {lat:.7f})"
            return pt, pt
        return None, None

    elif el_type == "way":
        geom = el.get("geometry", [])
        if not geom or len(geom) < 2:
            return None, None
        coords = [(pt["lon"], pt["lat"]) for pt in geom if "lon" in pt and "lat" in pt]
        if len(coords) < 2:
            return None, None

        # Check if closed polygon
        is_closed = coords[0] == coords[-1] and len(coords) >= 4
        if is_closed:
            coord_str = ", ".join(f"{c[0]:.7f} {c[1]:.7f}" for c in coords)
            wkt = f"POLYGON(({coord_str}))"
        else:
            coord_str = ", ".join(f"{c[0]:.7f} {c[1]:.7f}" for c in coords)
            wkt = f"LINESTRING({coord_str})"

        # Center point
        avg_lon = sum(c[0] for c in coords) / len(coords)
        avg_lat = sum(c[1] for c in coords) / len(coords)
        centroid = f"POINT({avg_lon:.7f} {avg_lat:.7f})"
        return wkt, centroid

    elif el_type == "relation":
        # Check if relation contains outer way geometries
        members = el.get("members", [])
        outer_coords = []
        all_coords = []
        for m in members:
            m_geom = m.get("geometry", [])
            for pt in m_geom:
                if "lon" in pt and "lat" in pt:
                    all_coords.append((pt["lon"], pt["lat"]))
                    if m.get("role") == "outer":
                        outer_coords.append((pt["lon"], pt["lat"]))

        coords_to_use = outer_coords if len(outer_coords) >= 4 else all_coords
        if len(coords_to_use) >= 4 and coords_to_use[0] == coords_to_use[-1]:
            coord_str = ", ".join(f"{c[0]:.7f} {c[1]:.7f}" for c in coords_to_use)
            wkt = f"POLYGON(({coord_str}))"
        elif len(all_coords) >= 2:
            coord_str = ", ".join(f"{c[0]:.7f} {c[1]:.7f}" for c in all_coords)
            wkt = f"LINESTRING({coord_str})"
        else:
            return None, None

        avg_lon = sum(c[0] for c in all_coords) / len(all_coords)
        avg_lat = sum(c[1] for c in all_coords) / len(all_coords)
        centroid = f"POINT({avg_lon:.7f} {avg_lat:.7f})"
        return wkt, centroid

    return None, None


def import_osm(region_filter: Optional[str] = None, force_download: bool = False) -> Dict[str, Any]:
    uri = get_db_uri()
    engine = create_engine(uri)

    regions_to_process = (
        [r for r in MONITORING_REGIONS if r["key"] == region_filter or str(r["id"]) == region_filter]
        if region_filter
        else MONITORING_REGIONS
    )

    if not regions_to_process:
        log.error("No regions matched filter: %s", region_filter)
        return {"error": "Invalid region filter"}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    total_imported = 0
    total_skipped = 0
    region_counts = {}

    for reg in regions_to_process:
        reg_id = reg["id"]
        reg_key = reg["key"]
        reg_name = reg["name"]
        bbox = reg["bbox"]

        cache_file = CACHE_DIR / f"{reg_key}.json"
        log.info("Processing region %s (ID %d)...", reg_name, reg_id)

        try:
            query = build_overpass_query(bbox)
            payload = fetch_from_overpass(query, cache_file, force=force_download)
        except Exception as e:
            log.error("Failed fetching OSM data for %s: %s", reg_name, e)
            continue

        elements = payload.get("elements", [])
        log.info("Parsing %d elements for %s...", len(elements), reg_name)

        imported_for_reg = 0
        with engine.begin() as conn:
            for el in elements:
                osm_id = el.get("id")
                osm_type = el.get("type")
                tags = el.get("tags", {})
                name = tags.get("name")
                category, subcategory = classify_facility(tags)

                wkt, centroid_wkt = element_to_wkt(el)
                if not wkt or not centroid_wkt:
                    total_skipped += 1
                    continue

                insert_sql = text("""
                    INSERT INTO osm_facilities (
                        osm_id, osm_type, name, facility_category, subcategory,
                        region_id, region_name, tags, geometry, centroid, source
                    )
                    VALUES (
                        :osm_id, :osm_type, :name, :facility_category, :subcategory,
                        :region_id, :region_name, :tags,
                        ST_SetSRID(ST_GeomFromText(:wkt), 4326),
                        ST_SetSRID(ST_GeomFromText(:centroid), 4326),
                        'osm_overpass'
                    )
                    ON CONFLICT (osm_type, osm_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        facility_category = EXCLUDED.facility_category,
                        subcategory = EXCLUDED.subcategory,
                        region_id = EXCLUDED.region_id,
                        region_name = EXCLUDED.region_name,
                        tags = EXCLUDED.tags,
                        geometry = EXCLUDED.geometry,
                        centroid = EXCLUDED.centroid,
                        retrieved_at = NOW();
                """)
                try:
                    conn.execute(insert_sql, {
                        "osm_id": osm_id,
                        "osm_type": osm_type,
                        "name": name,
                        "facility_category": category,
                        "subcategory": subcategory,
                        "region_id": reg_id,
                        "region_name": reg_name,
                        "tags": json.dumps(tags),
                        "wkt": wkt,
                        "centroid": centroid_wkt,
                    })
                    imported_for_reg += 1
                except Exception as exc:
                    log.warning("Failed inserting osm element %s_%s: %s", osm_type, osm_id, exc)
                    total_skipped += 1

        log.info("✓ Region %s: %d facilities persisted.", reg_key, imported_for_reg)
        region_counts[reg_key] = imported_for_reg
        total_imported += imported_for_reg
        time.sleep(1)


    log.info("=" * 60)
    log.info("OSM IMPORT COMPLETE: %d total facilities persisted, %d skipped.", total_imported, total_skipped)
    log.info("=" * 60)
    return {"total_imported": total_imported, "total_skipped": total_skipped, "regions": region_counts}


def print_database_stats():
    uri = get_db_uri()
    engine = create_engine(uri)
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM osm_facilities;")).scalar()
        print(f"\nTotal OSM Facilities in DB: {total}")

        print("\nBreakdown by Facility Category:")
        cats = conn.execute(text("""
            SELECT facility_category, COUNT(*) 
            FROM osm_facilities 
            GROUP BY facility_category 
            ORDER BY count DESC;
        """)).fetchall()
        for cat, cnt in cats:
            print(f"  {cat}: {cnt}")

        print("\nBreakdown by OSM Element Type:")
        types = conn.execute(text("""
            SELECT osm_type, COUNT(*) 
            FROM osm_facilities 
            GROUP BY osm_type 
            ORDER BY count DESC;
        """)).fetchall()
        for t, cnt in types:
            print(f"  {t}: {cnt}")

        print("\nBreakdown by Geometry Type:")
        geoms = conn.execute(text("""
            SELECT GeometryType(geometry), COUNT(*) 
            FROM osm_facilities 
            GROUP BY GeometryType(geometry) 
            ORDER BY count DESC;
        """)).fetchall()
        for g, cnt in geoms:
            print(f"  {g}: {cnt}")

        print("\nNamed vs Unnamed:")
        named = conn.execute(text("""
            SELECT 
                COUNT(*) FILTER (WHERE name IS NOT NULL AND name != '') AS named_count,
                COUNT(*) FILTER (WHERE name IS NULL OR name = '') AS unnamed_count
            FROM osm_facilities;
        """)).fetchone()
        print(f"  Named: {named[0]}, Unnamed: {named[1]}")

        print("\nBreakdown by Monitoring Region:")
        regs = conn.execute(text("""
            SELECT region_name, COUNT(*) 
            FROM osm_facilities 
            GROUP BY region_name 
            ORDER BY count DESC;
        """)).fetchall()
        for r, cnt in regs:
            print(f"  {r}: {cnt}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import OSM facilities into PostGIS")
    parser.add_argument("--region", type=str, default=None, help="Filter to specific region key")
    parser.add_argument("--force-download", action="store_true", help="Force re-download from Overpass")
    parser.add_argument("--stats", action="store_true", help="Print current database stats and exit")
    args = parser.parse_args()

    if args.stats:
        print_database_stats()
        sys.exit(0)

    res = import_osm(region_filter=args.region, force_download=args.force_download)
    print_database_stats()
