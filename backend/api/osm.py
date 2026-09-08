"""OSM Facilities API endpoints providing verified infrastructure GeoJSON."""

from __future__ import annotations

import json
import logging
from typing import Any
from flask import Blueprint, jsonify, request
from sqlalchemy import text
from db.connection import db

log = logging.getLogger(__name__)

osm_bp = Blueprint("osm", __name__)


@osm_bp.route("/facilities", methods=["GET"])
def get_facilities():
    """Retrieve OSM facilities as a GeoJSON FeatureCollection.

    Query parameters:
      - region_id: int (matches FireEvent ID)
      - region: str (matches region name substring)
      - category: str (industrial, power_plant, substation, mining_quarry, refinery, etc.)
      - bbox: str (min_lon,min_lat,max_lon,max_lat)
      - limit: int (default 200, max 1000)
      - offset: int (default 0)
    """
    try:
        region_id = request.args.get("region_id", type=int)
        region_name = request.args.get("region")
        category = request.args.get("category")
        bbox_str = request.args.get("bbox")
        limit = min(request.args.get("limit", default=200, type=int), 1000)
        offset = max(request.args.get("offset", default=0, type=int), 0)

        conditions = ["1=1"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if region_id:
            conditions.append("f.region_id = :region_id")
            params["region_id"] = region_id
        elif region_name:
            conditions.append("LOWER(f.region_name) LIKE :region_name")
            params["region_name"] = f"%{region_name.lower().strip()}%"

        if category and category.lower() != "all":
            conditions.append("LOWER(f.facility_category) = :category")
            params["category"] = category.lower().strip()

        if bbox_str:
            try:
                parts = [float(x.strip()) for x in bbox_str.split(",")]
                if len(parts) == 4:
                    min_lon, min_lat, max_lon, max_lat = parts
                    conditions.append(
                        "f.geometry && ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)"
                    )
                    params.update({
                        "min_lon": min_lon,
                        "min_lat": min_lat,
                        "max_lon": max_lon,
                        "max_lat": max_lat,
                    })
            except ValueError:
                return jsonify({"error": "Invalid bbox format. Expected min_lon,min_lat,max_lon,max_lat"}), 400

        where_clause = " AND ".join(conditions)

        count_sql = text(f"""
            SELECT COUNT(*)
            FROM osm_facilities f
            WHERE {where_clause}
        """)
        total_count = db.session.execute(count_sql, params).scalar() or 0

        data_sql = text(f"""
            SELECT 
                f.id,
                f.osm_id,
                f.osm_type,
                f.name,
                f.facility_category,
                f.subcategory,
                f.region_id,
                f.region_name,
                f.tags,
                f.source,
                f.retrieved_at,
                ST_AsGeoJSON(f.geometry) AS geojson_geom
            FROM osm_facilities f
            WHERE {where_clause}
            ORDER BY f.id ASC
            LIMIT :limit OFFSET :offset
        """)

        rows = db.session.execute(data_sql, params).fetchall()

        features = []
        for r in rows:
            geom = json.loads(r.geojson_geom) if r.geojson_geom else None
            features.append({
                "type": "Feature",
                "id": r.id,
                "geometry": geom,
                "properties": {
                    "id": r.id,
                    "osm_id": r.osm_id,
                    "osm_type": r.osm_type,
                    "name": r.name or "Unnamed Facility",
                    "facility_category": r.facility_category,
                    "subcategory": r.subcategory,
                    "region_id": r.region_id,
                    "region_name": r.region_name,
                    "tags": r.tags if isinstance(r.tags, dict) else {},
                    "source": r.source or "OpenStreetMap",
                    "retrieved_at": r.retrieved_at.isoformat() if r.retrieved_at else None,
                }
            })

        return jsonify({
            "type": "FeatureCollection",
            "features": features,
            "total": total_count,
            "count": len(features),
            "limit": limit,
            "offset": offset,
        })

    except Exception as exc:
        log.exception("Error serving OSM facilities")
        return jsonify({"error": "Failed retrieving OSM facilities", "details": str(exc)}), 500


@osm_bp.route("/categories", methods=["GET"])
def get_categories():
    """List distinct facility categories and counts."""
    try:
        region_id = request.args.get("region_id", type=int)
        where = "WHERE region_id = :region_id" if region_id else ""
        params = {"region_id": region_id} if region_id else {}

        sql = text(f"""
            SELECT facility_category, COUNT(*) AS count
            FROM osm_facilities
            {where}
            GROUP BY facility_category
            ORDER BY count DESC
        """)
        rows = db.session.execute(sql, params).fetchall()
        return jsonify({
            "categories": [{"category": r[0], "count": r[1]} for r in rows]
        })
    except Exception as exc:
        log.exception("Error serving OSM categories")
        return jsonify({"error": "Failed retrieving OSM categories", "details": str(exc)}), 500
