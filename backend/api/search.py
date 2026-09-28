"""backend/api/search.py
-------------------------
Unified Global Geospatial Search API for KRATOS V3.
Searches across:
- Defined Regions & Corridors (Pan-India, 6 Industrial Corridors, 4 Forest Landscapes)
- OSM Facilities (Power plants, mines, factories, refineries, substations)
- Persistent Thermal Clusters (DBSCAN clusters, persistent heat sources)
- Thermal Observations & Coordinate Queries (e.g., '24.1, 82.6' or detection IDs)
- Generated Intelligence Reports (InvestigationReport)
- Operational Follow-up Tasks (FollowUpTask)
"""

from __future__ import annotations

import re
import logging
from flask import Blueprint, jsonify, request
from sqlalchemy import or_, func

from db.connection import db
from db.models import OSMFacility, InvestigationReport, FollowUpTask
from services.thermal_intelligence import thermal_intelligence

search_bp = Blueprint("search", __name__, url_prefix="/api/v1/search")
log = logging.getLogger("search_api")

# Predefined regions reference with coordinates & extents
SURVEILLANCE_REGIONS = [
    {
        "id": "pan_india",
        "name": "Pan-India National Overview",
        "category": "national",
        "state": "India",
        "latitude": 22.5937,
        "longitude": 78.9629,
        "zoom": 5,
        "description": "Nationwide thermal anomaly surveillance across all states and union territories",
    },
    {
        "id": "singrauli_sonbhadra",
        "name": "Singrauli-Sonbhadra Energy Basin",
        "category": "industrial_corridor",
        "state": "Madhya Pradesh / Uttar Pradesh",
        "latitude": 24.12,
        "longitude": 82.67,
        "zoom": 11,
        "description": "Coal mining, thermal power stations, and heavy industrial facilities",
    },
    {
        "id": "dhanbad_bokaro",
        "name": "Dhanbad-Bokaro Steel & Coal Complex",
        "category": "industrial_corridor",
        "state": "Jharkhand",
        "latitude": 23.79,
        "longitude": 86.43,
        "zoom": 11,
        "description": "Jharia coalfields, coking coal washeries, and steel manufacturing",
    },
    {
        "id": "talcher_angul",
        "name": "Talcher-Angul Coal & Smelting Belt",
        "category": "industrial_corridor",
        "state": "Odisha",
        "latitude": 20.95,
        "longitude": 85.22,
        "zoom": 11,
        "description": "Open-cast coal mines, aluminium smelting, and NTPC thermal generation",
    },
    {
        "id": "korba",
        "name": "Korba Industrial Cluster",
        "category": "industrial_corridor",
        "state": "Chhattisgarh",
        "latitude": 22.35,
        "longitude": 82.68,
        "zoom": 11,
        "description": "Power hub, aluminium plants, and extensive coal pits",
    },
    {
        "id": "vijayanagar",
        "name": "Vijayanagar-Toranagallu Steel Complex",
        "category": "industrial_corridor",
        "state": "Karnataka",
        "latitude": 15.20,
        "longitude": 76.65,
        "zoom": 11,
        "description": "JSW Vijayanagar integrated steelworks and pellet plants",
    },
    {
        "id": "jamnagar_vadinar",
        "name": "Jamnagar-Vadinar Refining Complex",
        "category": "industrial_corridor",
        "state": "Gujarat",
        "latitude": 22.47,
        "longitude": 70.06,
        "zoom": 11,
        "description": "World-scale petroleum refining, petrochemical units, and marine terminals",
    },
    {
        "id": "gadchiroli_tadoba",
        "name": "Gadchiroli-Tadoba Forest Landscape",
        "category": "forest_landscape",
        "state": "Maharashtra",
        "latitude": 20.18,
        "longitude": 79.99,
        "zoom": 10,
        "description": "Dry deciduous forest canopy and tiger reserve wildlife corridors",
    },
    {
        "id": "kanha_pench",
        "name": "Kanha-Pench Ecological Corridor",
        "category": "forest_landscape",
        "state": "Madhya Pradesh",
        "latitude": 22.33,
        "longitude": 80.61,
        "zoom": 10,
        "description": "Sal and mixed deciduous forest ecosystem",
    },
    {
        "id": "bastar",
        "name": "Bastar Woodlands",
        "category": "forest_landscape",
        "state": "Chhattisgarh",
        "latitude": 19.07,
        "longitude": 81.96,
        "zoom": 10,
        "description": "Dense moist deciduous forest tracts and tribal reserve woodlands",
    },
    {
        "id": "mizoram",
        "name": "Mizoram Hill Forests",
        "category": "forest_landscape",
        "state": "Mizoram",
        "latitude": 23.16,
        "longitude": 92.93,
        "zoom": 10,
        "description": "Montane subtropical evergreen forest canopy and shifting cultivation zones",
    },
]


@search_bp.route("", methods=["GET"])
def global_search():
    """Universal search endpoint across regions, OSM facilities, clusters, detections, reports and follow-ups."""
    query_raw = request.args.get("q", "").strip()
    if not query_raw:
        return jsonify({"results": [], "query": "", "total": 0}), 200

    q_lower = query_raw.lower()
    limit_per_category = min(int(request.args.get("limit", 10)), 20)
    results = []

    # 1. Check for Direct Lat, Lon coordinate input (e.g. "24.12, 82.67" or "24.12 82.67")
    coord_match = re.match(r"^([-+]?\d{1,2}(?:\.\d+)?)[,\s]+([-+]?\d{1,3}(?:\.\d+)?)$", query_raw)
    if coord_match:
        try:
            lat = float(coord_match.group(1))
            lon = float(coord_match.group(2))
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                results.append({
                    "category": "coordinates",
                    "id": f"coord_{lat:.4f}_{lon:.4f}",
                    "title": f"Coordinate Target: {lat:.4f}°N, {lon:.4f}°E",
                    "subtitle": "Geographic point coordinate navigation",
                    "latitude": lat,
                    "longitude": lon,
                    "zoom": 14,
                    "feature_type": "observation",
                    "feature_id": f"coord_{lat:.4f}_{lon:.4f}",
                })
        except ValueError:
            pass

    # 2. Search Regions & Corridors
    for reg in SURVEILLANCE_REGIONS:
        if (
            q_lower in reg["name"].lower()
            or q_lower in reg["id"].lower()
            or q_lower in reg["state"].lower()
            or q_lower in reg["description"].lower()
        ):
            results.append({
                "category": "regions",
                "id": reg["id"],
                "title": reg["name"],
                "subtitle": f"{reg['state']} • {reg['category'].replace('_', ' ').title()}",
                "latitude": reg["latitude"],
                "longitude": reg["longitude"],
                "zoom": reg["zoom"],
                "feature_type": "region",
                "feature_id": reg["id"],
                "region_id": reg["id"],
            })

    # 3. Search OSM Facilities in Database
    try:
        search_filter = or_(
            OSMFacility.name.ilike(f"%{query_raw}%"),
            OSMFacility.facility_category.ilike(f"%{query_raw}%"),
            OSMFacility.subcategory.ilike(f"%{query_raw}%"),
            OSMFacility.region_name.ilike(f"%{query_raw}%"),
        )
        osm_facilities = (
            db.session.query(
                OSMFacility.id,
                OSMFacility.osm_id,
                OSMFacility.osm_type,
                OSMFacility.name,
                OSMFacility.facility_category,
                OSMFacility.subcategory,
                OSMFacility.region_name,
                func.ST_Y(OSMFacility.centroid).label("lat"),
                func.ST_X(OSMFacility.centroid).label("lon"),
            )
            .filter(search_filter)
            .limit(limit_per_category)
            .all()
        )
        for fac in osm_facilities:
            display_name = fac.name or f"{fac.subcategory or fac.facility_category} #{fac.osm_id}"
            results.append({
                "category": "facilities",
                "id": f"osm_{fac.id}",
                "title": display_name,
                "subtitle": f"{fac.facility_category.replace('_', ' ').title()} • {fac.region_name or 'Industrial Zone'}",
                "latitude": float(fac.lat) if fac.lat is not None else 0.0,
                "longitude": float(fac.lon) if fac.lon is not None else 0.0,
                "zoom": 15,
                "feature_type": "facility",
                "feature_id": str(fac.id),
                "properties": {
                    "osm_id": fac.osm_id,
                    "osm_type": fac.osm_type,
                    "facility_category": fac.facility_category,
                    "subcategory": fac.subcategory,
                    "region_name": fac.region_name,
                },
            })
    except Exception as exc:
        log.warning("Error searching OSM facilities: %s", exc)

    # 4. Search Persistent Thermal Clusters from Parquet / Service
    try:
        sources_df = thermal_intelligence.sources
        if not sources_df.empty:
            cluster_matches = sources_df[
                sources_df["thermal_source_id"].astype(str).str.lower().str.contains(q_lower)
                | sources_df["region_name"].astype(str).str.lower().str.contains(q_lower)
                | sources_df.get("source_class", "").astype(str).str.lower().str.contains(q_lower)
            ].head(limit_per_category)

            for _, row in cluster_matches.iterrows():
                src_id = str(row["thermal_source_id"])
                cls_name = str(row.get("source_class", "Persistent Cluster")).replace("_", " ").title()
                reg_name = str(row.get("region_name", "Surveillance Region"))
                lat = float(row.get("latitude", row.get("source_latitude", 0.0)))
                lon = float(row.get("longitude", row.get("source_longitude", 0.0)))
                hits = int(row.get("total_detections", row.get("detection_count", 1)))
                results.append({
                    "category": "clusters",
                    "id": src_id,
                    "title": f"Cluster {src_id}",
                    "subtitle": f"{cls_name} • {reg_name} ({hits} detections)",
                    "latitude": lat,
                    "longitude": lon,
                    "zoom": 14,
                    "feature_type": "cluster",
                    "feature_id": src_id,
                    "properties": {
                        "thermal_source_id": src_id,
                        "source_class": row.get("source_class"),
                        "region_name": reg_name,
                        "total_detections": hits,
                    },
                })
    except Exception as exc:
        log.warning("Error searching persistent clusters: %s", exc)

    # 5. Search Generated Intelligence Reports
    try:
        rpt_filter = or_(
            InvestigationReport.report_key.ilike(f"%{query_raw}%"),
            InvestigationReport.title.ilike(f"%{query_raw}%"),
            InvestigationReport.region_name.ilike(f"%{query_raw}%"),
        )
        reports = (
            db.session.query(InvestigationReport)
            .filter(rpt_filter)
            .order_by(InvestigationReport.created_at.desc())
            .limit(limit_per_category)
            .all()
        )
        for rpt in reports:
            results.append({
                "category": "reports",
                "id": rpt.report_key,
                "title": rpt.title,
                "subtitle": f"Report {rpt.report_key} • {rpt.scope.upper()} • {rpt.region_name or 'All Corridors'}",
                "latitude": 22.5937,
                "longitude": 78.9629,
                "zoom": 7,
                "feature_type": "report",
                "feature_id": rpt.report_key,
                "properties": {
                    "report_id": rpt.id,
                    "report_key": rpt.report_key,
                    "scope": rpt.scope,
                    "region_name": rpt.region_name,
                },
            })
    except Exception as exc:
        log.warning("Error searching reports: %s", exc)

    # 6. Search Follow-up Tasks
    try:
        task_filter = or_(
            FollowUpTask.task_key.ilike(f"%{query_raw}%"),
            FollowUpTask.title.ilike(f"%{query_raw}%"),
            FollowUpTask.feature_id.ilike(f"%{query_raw}%"),
            FollowUpTask.region_name.ilike(f"%{query_raw}%"),
        )
        tasks = (
            db.session.query(FollowUpTask)
            .filter(task_filter)
            .order_by(FollowUpTask.created_at.desc())
            .limit(limit_per_category)
            .all()
        )
        for t in tasks:
            results.append({
                "category": "tasks",
                "id": t.task_key,
                "title": t.title,
                "subtitle": f"Task {t.task_key} • {t.priority} • {t.status} ({t.region_name or 'General'})",
                "latitude": 22.5937,
                "longitude": 78.9629,
                "zoom": 8,
                "feature_type": "task",
                "feature_id": t.task_key,
                "properties": {
                    "task_id": t.id,
                    "task_key": t.task_key,
                    "priority": t.priority,
                    "status": t.status,
                    "feature_type": t.feature_type,
                    "target_feature_id": t.feature_id,
                },
            })
    except Exception as exc:
        log.warning("Error searching tasks: %s", exc)

    return jsonify({
        "results": results,
        "query": query_raw,
        "total": len(results),
    }), 200
