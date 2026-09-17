"""
api/timesteps.py
----------------
Core blueprint, shared helpers, control endpoints, and chat.

Routes:
    GET  /events/<id>/timesteps
    GET  /events/<id>/timesteps/<ts_id>/status
    POST /events/<id>/timesteps/<ts_id>/run-prediction   body: {force?: bool}
    POST /events/<id>/chat

Prediction/weather/spatial/report routes are registered by importing
the sub-modules at the bottom of this file.
"""

from __future__ import annotations

import json
from pathlib import Path

from datetime import date

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context
from utils.auth_middleware import token_required, admin_required
from utils.rate_limiter import limit_chat

timesteps_bp = Blueprint("timesteps", __name__)

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Chat quota: 5 messages per authenticated user per UTC day. Counts persist in the
# users table so quota survives restarts and is per-user (not per-session).
_CHAT_LIMIT = 5


# ── Shared path helpers ───────────────────────────────────────────────────────

def _ts_base(event_id: int, year: int, slot_time) -> Path:
    import pandas as pd
    yr = year or 2026
    ts_str = pd.Timestamp(slot_time).strftime("%Y-%m-%dT%H%M")
    return _DATA_DIR / "events" / f"{yr}_{event_id:04d}" / "timesteps" / ts_str


def _pred_dir(event_id: int, year: int, slot_time) -> Path:
    """Returns prediction/ML/ — where ML risk-zone outputs live."""
    return _ts_base(event_id, year, slot_time) / "prediction" / "ML"


def _perim_dir(event_id: int, year: int, slot_time) -> Path:
    return _ts_base(event_id, year, slot_time) / "perimeter"


def _hotspot_dir(event_id: int, year: int, slot_time) -> Path:
    return _ts_base(event_id, year, slot_time) / "hotspot"


def _actual_perim_dir(event_id: int, year: int, slot_time) -> Path:
    return _ts_base(event_id, year, slot_time) / "actual_perimeter"


_SENTINEL = {
    # status_dir suffix → file that proves the stage completed without STATUS.json
    "ML":               "fire_context.json",
    "wind_driven":      "STATUS.json",          # no sentinel yet; always needs STATUS.json
    "spatial_analysis": "ML/roads.geojson",
}

def _read_status(status_dir: Path) -> str:
    """Read status, checking in-memory running set first, then STATUS.json, then sentinels."""
    from pipeline.check.builder_slots import _read_status as _slots_read_status, _write_status as _slots_write_status
    # Check in-memory running first
    from pipeline.check.builder_slots import _running, _running_lock
    with _running_lock:
        if str(status_dir) in _running:
            return "running"

    path = status_dir / "STATUS.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("status", "pending")
        except Exception:
            return "pending"

    # STATUS.json missing — check sentinel file to handle pre-STATUS.json runs
    sentinel_name = _SENTINEL.get(status_dir.name)
    if sentinel_name and (status_dir / sentinel_name).exists():
        _write_status(status_dir, "done")
        return "done"

    return "pending"


def _write_status(status_dir: Path, status: str) -> None:
    from pipeline.check.builder_slots import _write_status as _slots_write_status
    _slots_write_status(status_dir, status)


def _get_event_and_ts(event_id: int, ts_id: int):
    from db.models import FireEvent, EventTimestep
    event = FireEvent.query.get(event_id)
    if not event:
        return None, (jsonify({"error": "event not found"}), 404)
    ts = EventTimestep.query.filter_by(id=ts_id, event_id=event_id).first()
    if not ts:
        return None, (jsonify({"error": "timestep not found"}), 404)
    return (event, ts), None


def _read_geojson(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"type": "FeatureCollection", "features": []}


def _read_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


# ── List timesteps ────────────────────────────────────────────────────────────

@timesteps_bp.route("/events/<int:event_id>/timesteps", methods=["GET"])
@token_required
def list_timesteps(event_id: int):
    from db.models import FireEvent, EventTimestep
    event = FireEvent.query.get(event_id)
    if not event:
        return jsonify({"error": "event not found"}), 404
    rows = (
        EventTimestep.query
        .filter_by(event_id=event_id)
        .order_by(EventTimestep.slot_time)
        .all()
    )
    result = []
    for ts in rows:
        base     = _ts_base(event.id, event.year, ts.slot_time)
        ml_st    = _read_status(base / "prediction" / "ML")
        wd_st    = _read_status(base / "prediction" / "wind_driven")
        sp_st    = _read_status(base / "spatial_analysis")
        result.append({
            "id":                      ts.id,
            "slot_time":               ts.slot_time.isoformat(),
            "nearest_t1":              ts.nearest_t1.isoformat(),
            "gap_hours":               ts.gap_hours,
            "data_gap_warn":           ts.data_gap_warn,
            "prediction_status":       ml_st,
            "spatial_analysis_status": sp_st,
            "wind_driven_status":      wd_st,
        })
    return jsonify(result), 200


# ── Status + run-prediction ───────────────────────────────────────────────────

def _reset_ts_if_files_missing(event, ts) -> bool:
    """Reset ML status to 'pending' if STATUS.json says done but perimeter.geojson is gone."""
    base     = _ts_base(event.id, event.year, ts.slot_time)
    ml_dir   = base / "prediction" / "ML"
    ml_st    = _read_status(ml_dir)
    if ml_st not in ("done", "failed"):
        return False
    sentinel = ml_dir / "fire_context.json"
    if sentinel.exists():
        return False
    _write_status(ml_dir, "pending")
    _write_status(base / "spatial_analysis", "pending")
    return True


@timesteps_bp.route("/events/<int:event_id>/timesteps/<int:ts_id>/status", methods=["GET"])
@token_required
def get_ts_status(event_id: int, ts_id: int):
    result, err = _get_event_and_ts(event_id, ts_id)
    if err:
        return err
    event, ts = result
    _reset_ts_if_files_missing(event, ts)
    base = _ts_base(event.id, event.year, ts.slot_time)
    return jsonify({
        "prediction_status":        _read_status(base / "prediction" / "ML"),
        "spatial_analysis_status":  _read_status(base / "spatial_analysis"),
        "wind_driven_status":       _read_status(base / "prediction" / "wind_driven"),
        "crowd_prediction_status":  _read_status(base / "prediction" / "ML_crowd"),
        "spatial_crowd_status":     _read_status(base / "spatial_analysis_crowd"),
    })


@timesteps_bp.route("/events/<int:event_id>/timesteps/<int:ts_id>/run-prediction", methods=["POST"])
@admin_required
def run_prediction(event_id: int, ts_id: int):
    """Trigger prediction pipeline.

    Body (optional JSON):
        { "force": true }          — wipe existing outputs and re-run even if already done.
        { "crowd": true }          — run crowd-augmented prediction (ML_crowd/).
        { "crowd": true, "force": true } — wipe crowd outputs and re-run.
        { "prefetch_next": true }  — after this timestep completes, prefetch only its successor.
    """
    result, err = _get_event_and_ts(event_id, ts_id)
    if err:
        return err
    event, ts = result

    body  = request.get_json(silent=True) or {}
    force = bool(body.get("force"))
    crowd = bool(body.get("crowd"))
    prefetch_next = bool(body.get("prefetch_next"))

    from utils.background import run_in_background
    app = current_app._get_current_object()

    # ── Crowd prediction branch ───────────────────────────────────────────────
    if crowd:
        from pipeline.event_config import uses_wildfire_model
        if not uses_wildfire_model(event):
            return jsonify({
                "error": "crowd wildfire prediction is not configured for this event",
            }), 409

        base     = _ts_base(event.id, event.year, ts.slot_time)
        crow_dir = base / "prediction" / "ML_crowd"
        sp_crowd = base / "spatial_analysis_crowd"
        crow_st  = _read_status(crow_dir)
        sp_crowd_st = _read_status(sp_crowd)

        if force and (crow_st == "running" or sp_crowd_st == "running"):
            return jsonify({"status": "running"})

        if force and crow_st == "done":
            import shutil, os, stat
            def _on_rm_error(func, path, exc_info):
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except Exception:
                    pass
            for d in (crow_dir, sp_crowd):
                if d.exists():
                    try:
                        shutil.rmtree(d, onerror=_on_rm_error)
                    except Exception:
                        pass
            crow_st = "pending"

        if crow_st == "done":
            return jsonify({"status": "done"})

        from pipeline.check.builder_slots import _try_mark_running
        if crow_st == "running" or not _try_mark_running(crow_dir):
            return jsonify({"status": "running"})

        from pipeline.check.builder import build_single_timestep_ondemand_crowd
        run_in_background(build_single_timestep_ondemand_crowd, app, ts_id)
        return jsonify({"status": "running"})

    # ── Standard prediction branch ────────────────────────────────────────────
    base   = _ts_base(event.id, event.year, ts.slot_time)
    ml_dir = base / "prediction" / "ML"
    sp_dir = base / "spatial_analysis"
    ml_st  = _read_status(ml_dir)
    sp_st  = _read_status(sp_dir)

    if force and (ml_st == "running" or sp_st == "running"):
        stage = "prediction" if ml_st == "running" else "spatial_analysis"
        return jsonify({"status": "running", "stage": stage})

    if force and ml_st == "done":
        _wipe_prediction_outputs(event, ts)
        ml_st = "pending"

    # Auto-heal: STATUS says done but files missing
    _reset_ts_if_files_missing(event, ts)

    from pipeline.check.builder import start_timestep_build
    state, stage = start_timestep_build(
        app, event, ts, prefetch_next=prefetch_next,
    )
    if state == "cached":
        return jsonify({"status": "done"})
    return jsonify({"status": "running", "stage": stage})


def _wipe_prediction_outputs(event, ts) -> None:
    """Delete prediction + spatial_analysis dirs and reset STATUS.json to pending.

    Uses an onerror handler to handle Windows-locked files (OneDrive, Explorer).
    Falls back to deleting individual files if rmtree still fails.
    """
    import os
    import shutil
    import stat

    def _on_rm_error(func, path, exc_info):
        """Make read-only files writable then retry (Windows WinError 5 fix)."""
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass  # best-effort; don't crash the endpoint

    base = _ts_base(event.id, event.year, ts.slot_time)

    for sub in ("prediction", "spatial_analysis"):
        d = base / sub
        if d.exists():
            try:
                shutil.rmtree(d, onerror=_on_rm_error)
            except Exception:
                for f in d.rglob("*"):
                    if f.is_file():
                        try:
                            os.chmod(f, stat.S_IWRITE)
                            f.unlink()
                        except Exception:
                            pass

    _write_status(base / "prediction" / "ML", "pending")
    _write_status(base / "prediction" / "wind_driven", "pending")
    _write_status(base / "spatial_analysis", "pending")


# ── Build-all (SSE) ───────────────────────────────────────────────────────────

@timesteps_bp.route("/events/<int:event_id>/build-all", methods=["POST"])
@admin_required
def build_all_predictions(event_id: int):
    """SSE: run full prediction pipeline for all pending timesteps in an event.

    Yields newline-delimited JSON events:
        { total, done, current, status }   status = loading | running | done | error
    """
    import json as _json
    import logging as _logging
    import pandas as _pd
    from db.models import FireEvent, EventTimestep

    _log = _logging.getLogger(__name__)

    event = FireEvent.query.get(event_id)
    if not event:
        return jsonify({"error": "event not found"}), 404

    def _generate():
        from pipeline.check.builder import (
            _get_build_runtime, _build_timestep,
        )

        timesteps = (
            EventTimestep.query
            .filter_by(event_id=event_id)
            .order_by(EventTimestep.slot_time)
            .all()
        )

        pending = [
            ts for ts in timesteps
            if _read_status(_ts_base(event.id, event.year, ts.slot_time) / "prediction" / "ML")
               not in ("done", "running")
        ]

        total = len(pending)
        yield f"data: {_json.dumps({'total': total, 'done': 0, 'status': 'loading'})}\n\n"

        try:
            assets, predictor, threshold = _get_build_runtime(event)
        except Exception as exc:
            _log.error("[build-all] setup failed: %s", exc)
            yield f"data: {_json.dumps({'error': str(exc), 'status': 'error'})}\n\n"
            return

        for i, ts in enumerate(pending):
            ts_label = _pd.Timestamp(ts.slot_time).strftime("%Y-%m-%d %H:%M")
            yield f"data: {_json.dumps({'total': total, 'done': i, 'current': ts_label, 'status': 'running'})}\n\n"
            try:
                _build_timestep(event, ts, assets, predictor, threshold)
            except Exception as exc:
                _log.error("[build-all] ts %d failed: %s", ts.id, exc)

        yield f"data: {_json.dumps({'total': total, 'done': total, 'status': 'done'})}\n\n"

    return Response(
        stream_with_context(_generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Chat ──────────────────────────────────────────────────────────────────────

def _should_apply_chat_quota(payload: dict) -> bool:
    """Return whether this authenticated identity uses the persisted chat quota."""
    return (
        not payload.get("is_admin", False)
        and not payload.get("is_demo", False)
        and payload.get("user_id") is not None
    )


def _report_metadata_is_current(metadata: dict) -> bool:
    """Reject cached report context produced by an older schema or prompt."""
    if not metadata:
        return False

    # Imported lazily because ts_data_routes imports this module to register its
    # endpoints. At request time both modules are fully initialized.
    from api.ts_data_routes import _PROMPT_VERSION, _REPORT_SCHEMA_VERSION

    return (
        metadata.get("schema_version") == _REPORT_SCHEMA_VERSION
        and metadata.get("prompt_version") == _PROMPT_VERSION
    )


def _retrieve_selected_feature_evidence(feat_type: str, feat_id: str) -> dict | None:
    """Retrieve authoritative server-side record for a selected map feature."""
    from db.connection import db
    from sqlalchemy import text
    from services.thermal_intelligence import thermal_intelligence

    t = (feat_type or "").strip().lower()
    fid = (feat_id or "").strip()
    if not t or not fid:
        return None

    # 1. Cluster / Persistent Source
    if t in ("cluster", "thermal_source", "source"):
        source = thermal_intelligence.source_detail(fid)
        if not source:
            sources = thermal_intelligence.sources
            matches = sources[sources["thermal_source_id"].astype(str) == fid]
            if not matches.empty:
                source = thermal_intelligence._records(matches)[0]

        if source:
            lat = source.get("latitude") or source.get("source_latitude")
            lon = source.get("longitude") or source.get("source_longitude")
            nearest_facility = None
            if lat is not None and lon is not None:
                try:
                    q = text("""
                        SELECT name, facility_category, subcategory, osm_id, osm_type,
                               ST_Distance(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, geometry::geography) AS dist_m
                        FROM osm_facilities
                        WHERE geometry && ST_Expand(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 0.03)
                        ORDER BY dist_m ASC
                        LIMIT 1;
                    """)
                    row = db.session.execute(q, {"lon": lon, "lat": lat}).fetchone()
                    if row:
                        dist = round(float(row[5]), 1)
                        tier = "direct_intersection" if dist == 0 else ("strong_association" if dist <= 300 else "nearby")
                        nearest_facility = {
                            "name": row[0] or "Unnamed Facility",
                            "category": row[1],
                            "subcategory": row[2],
                            "osm_id": f"{row[4]} #{row[3]}",
                            "distance_metres": dist,
                            "relationship_tier": tier,
                        }
                except Exception:
                    pass

            from services.source_classification import source_classification_engine
            from services.risk_evaluation import risk_evaluation_engine
            from services.compliance_screening import compliance_screening_engine

            fac_match = None
            if nearest_facility:
                fac_match = {
                    "min_distance_m": nearest_facility.get("distance_metres"),
                    "nearest_facility_name": nearest_facility.get("name"),
                    "nearest_category": nearest_facility.get("category"),
                }
            four_field = source_classification_engine.classify_source_record(source, fac_match)
            op_priority = risk_evaluation_engine.evaluate_operational_priority(source, facility_dist_m=nearest_facility.get("distance_metres") if nearest_facility else None)
            compliance = compliance_screening_engine.screen_facility_compliance(
                facility_name=four_field["nearest_facility_name"],
                facility_category=four_field["mapped_facility_category"],
                max_frp_ratio=float(source.get("max_frp_ratio") or 1.0),
                max_frp_mw=float(source.get("max_frp") or 0.0),
                distance_m=nearest_facility.get("distance_metres") if nearest_facility else None,
                detection_count=int(source.get("total_detections") or source.get("detection_count") or 1),
            )

            return {
                "feature_type": "persistent_thermal_cluster",
                "identifier": fid,
                "region_name": source.get("region_name"),
                "coordinates": {"latitude": lat, "longitude": lon},
                "four_field_intelligence": four_field,
                "operational_priority": op_priority["operational_priority"],
                "anomaly_evaluation": op_priority["anomaly_score"],
                "compliance_screening": compliance,
                "classification": four_field["predicted_source_type"],
                "classification_confidence": four_field["source_type_confidence"],
                "total_detections": source.get("total_detections") or source.get("detection_count"),
                "mean_frp_mw": source.get("mean_frp"),
                "max_frp_mw": source.get("max_frp"),
                "first_seen": str(source.get("first_seen")) if source.get("first_seen") else None,
                "last_seen": str(source.get("last_seen")) if source.get("last_seen") else None,
                "persistence_30d_ratio": source.get("persistence_30d_mean"),
                "nearest_facility": nearest_facility or "No mapped facility within 2km",
                "land_use_context": {
                    "builtup_fraction_1km": source.get("builtup_fraction_1km_mean"),
                    "tree_fraction_1km": source.get("tree_fraction_1km_mean"),
                },
            }

    # 2. Raw Thermal Detection / Observation
    if t in ("observation", "detection", "thermal_event", "event"):
        try:
            q = text("""
                SELECT fd.detection_key, fd.latitude, fd.longitude, fd.acquisition_time,
                       fd.satellite, fd.instrument, fd.brightness, fd.frp, fd.firms_confidence,
                       fd.day_night, fd.land_cover, fd.predicted_class, fd.model_confidence,
                       fe.name AS region_name
                FROM fire_detections fd
                LEFT JOIN fire_events fe ON fd.monitoring_region_id = fe.id
                WHERE fd.detection_key = :fid OR fd.id::text = :fid
                LIMIT 1;
            """)
            r = db.session.execute(q, {"fid": fid}).fetchone()
            if r:
                return {
                    "feature_type": "firms_thermal_observation",
                    "detection_key": r[0],
                    "coordinates": {"latitude": float(r[1]), "longitude": float(r[2])},
                    "acquisition_time_utc": r[3].isoformat() if r[3] else None,
                    "satellite": r[4],
                    "instrument": r[5],
                    "brightness_kelvin": r[6],
                    "frp_mw": r[7],
                    "firms_confidence": r[8],
                    "day_night": r[9],
                    "land_cover": r[10],
                    "predicted_anomaly_class": r[11],
                    "model_confidence": r[12],
                    "region": r[13],
                }
        except Exception:
            pass

        ev = thermal_intelligence.event_detail(fid)
        if ev:
            return {
                "feature_type": "thermal_event",
                "identifier": fid,
                "region_name": ev.get("region_name"),
                "coordinates": {"latitude": ev.get("latitude"), "longitude": ev.get("longitude")},
                "event_start": ev.get("event_start"),
                "final_risk_level": ev.get("final_risk_level"),
                "final_risk_score": ev.get("final_risk_score"),
                "max_frp_mw": ev.get("max_frp"),
                "detection_count": ev.get("detection_count"),
                "iforest_agreement": ev.get("iforest_agreement"),
                "nearest_facility": {
                    "name": ev.get("nearest_industry_name"),
                    "category": ev.get("nearest_industry_type"),
                    "distance_metres": ev.get("distance_to_nearest_industry_m"),
                } if ev.get("nearest_industry_name") else None,
            }

    # 3. OSM Facility
    if t in ("facility", "osm_facility"):
        try:
            q = text("""
                SELECT id, osm_id, osm_type, name, facility_category, subcategory, region_name, tags,
                       ST_Y(centroid) AS lat, ST_X(centroid) AS lon
                FROM osm_facilities
                WHERE osm_id::text = :fid OR id::text = :fid
                LIMIT 1;
            """)
            r = db.session.execute(q, {"fid": fid}).fetchone()
            if r:
                res = {
                    "feature_type": "osm_infrastructure_facility",
                    "facility_id": r[0],
                    "osm_id": f"{r[2]} #{r[1]}",
                    "name": r[3] or "Unnamed Facility",
                    "category": r[4],
                    "subcategory": r[5],
                    "region_name": r[6],
                    "tags": r[7] if isinstance(r[7], dict) else {},
                    "coordinates": {"latitude": float(r[8]), "longitude": float(r[9])} if r[8] and r[9] else None,
                    "source": "OpenStreetMap",
                }
                # Attach regulatory screening
                from services.compliance_screening import compliance_screening_engine
                res["compliance_screening"] = compliance_screening_engine.screen_facility_compliance(
                    facility_name=res["name"],
                    facility_category=res["category"] or "Industrial Complex",
                )
                return res
        except Exception:
            pass

    # 4. Investigation Report Context
    if t in ("report", "investigation_report"):
        try:
            from db.models import InvestigationReport
            rep = None
            if fid.isdigit():
                rep = db.session.get(InvestigationReport, int(fid))
            if not rep:
                rep = InvestigationReport.query.filter_by(report_key=fid).first()
            if rep:
                return {
                    "feature_type": "investigation_report",
                    "identifier": rep.report_key,
                    "report_key": rep.report_key,
                    "title": rep.title,
                    "scope": rep.scope,
                    "region_name": rep.region_name,
                    "version": rep.version or "v1.0",
                    "status": rep.status or "generated",
                    "submission_status": rep.submission_status or "NOT_SUBMITTED",
                    "summary": rep.summary_text,
                    "created_at": rep.created_at.isoformat() if rep.created_at else None,
                }
        except Exception:
            pass

    # 5. Follow-Up Task Context
    if t in ("followup", "follow_up", "task"):
        try:
            from db.models import FollowUpTask
            tsk = None
            if fid.isdigit():
                tsk = db.session.get(FollowUpTask, int(fid))
            if not tsk:
                tsk = FollowUpTask.query.filter_by(task_key=fid).first()
            if tsk:
                return {
                    "feature_type": "follow_up",
                    "identifier": tsk.task_key,
                    "task_key": tsk.task_key,
                    "title": tsk.title,
                    "priority": tsk.priority,
                    "status": tsk.status,
                    "region_name": tsk.region_name,
                    "linked_feature": f"{tsk.feature_type}: {tsk.feature_id}",
                    "assigned_to": tsk.assigned_to,
                    "due_date": tsk.due_date.isoformat() if tsk.due_date else None,
                    "description": tsk.description,
                    "created_at": tsk.created_at.isoformat() if tsk.created_at else None,
                }
        except Exception:
            pass

    # 6. Data Connector Context
    if t in ("connector", "data_connector", "integration"):
        try:
            from db.models import DataConnector
            conn = None
            if fid.isdigit():
                conn = db.session.get(DataConnector, int(fid))
            if not conn:
                conn = DataConnector.query.filter_by(connector_key=fid).first()
            if conn:
                return {
                    "feature_type": "data_connector",
                    "identifier": conn.connector_key,
                    "name": conn.name,
                    "provider": conn.provider,
                    "connector_type": conn.connector_type,
                    "health_status": conn.health_status,
                    "records_received": conn.records_received,
                    "last_sync_at": conn.last_sync_at.isoformat() if conn.last_sync_at else None,
                }
        except Exception:
            pass

    return None


@timesteps_bp.route("/events/<int:event_id>/chat", methods=["POST"])
@token_required
@limit_chat
def chat(event_id: int):
    body    = request.get_json(force=True)
    message = body.get("message", "").strip()
    ts_id   = body.get("timestep_id")
    history = body.get("history", [])
    selected_feature = body.get("selected_feature")

    if not message:
        return jsonify({"error": "message required"}), 400

    payload = request.current_user or {}
    # Demo access uses a synthetic identity (id=0), so it has no User row.
    # Only persisted, non-admin accounts participate in the database-backed
    # daily chat quota.
    if _should_apply_chat_quota(payload):
        from db.connection import db
        # token_required has already resolved and validated this database row.
        # Reuse it so auth and quota enforcement cannot disagree about which
        # user is making the request.
        u = request.auth_user
        today = date.today()
        if u.chat_count_date != today:
            u.chat_count_date = today
            u.chat_count      = 0
        if u.chat_count >= _CHAT_LIMIT:
            return jsonify({"error": f"Daily chat limit reached ({_CHAT_LIMIT} per day). Try again tomorrow."}), 429
        u.chat_count += 1
        db.session.commit()

    summary       = ""
    road_summary  = []
    analysis_mode = None
    retrieved_evidence = {}

    if selected_feature and isinstance(selected_feature, dict):
        feat_type = str(selected_feature.get("feature_type") or "").strip()
        feat_id = str(selected_feature.get("feature_id") or "").strip()
        target_info = _retrieve_selected_feature_evidence(feat_type, feat_id)
        if target_info:
            retrieved_evidence["target_feature"] = target_info

    if ts_id:
        result, _ = _get_event_and_ts(event_id, ts_id)
        if result:
            event_obj, ts_obj = result
            from pipeline.event_config import get_event_config
            event_config = get_event_config(event_obj)
            analysis_mode = event_config.analysis_mode
            import pandas as _pd
            ts_str  = _pd.Timestamp(ts_obj.slot_time).strftime("%Y-%m-%dT%H%M")
            ai_dir  = (_DATA_DIR / "events" / f"{event_obj.year}_{event_obj.id:04d}"
                       / "timesteps" / ts_str / "AI_report")
            # Retrieve authoritative region and observation evidence directly from
            # the same builder used by reports. Chat must not depend on a cached
            # narrative report to know which region/timestep the dashboard shows.
            from api.ts_data_routes import _report_evidence
            evidence, population, retrieved_roads, _, _ = _report_evidence(event_obj, ts_obj)
            if evidence:
                retrieved_evidence = {
                    "scope": "selected_region_and_observation",
                    "event_id": event_obj.id,
                    "timestep_id": ts_obj.id,
                    "evidence": evidence,
                    "population_exposure": population,
                }
                road_summary = retrieved_roads
            else:
                # Region identity remains available while a newly selected
                # timestep's prediction artifact is still being prepared.
                retrieved_evidence = {
                    "scope": "selected_region_and_observation",
                    "event_id": event_obj.id,
                    "timestep_id": ts_obj.id,
                    "observation_time": ts_obj.slot_time.isoformat(),
                    "region": {
                        "event_id": event_obj.id,
                        "region_id": event_config.region_id,
                        "name": event_obj.name,
                        "state": event_config.state,
                        "country_code": event_config.country_code,
                        "monitoring_focus": event_config.monitoring_focus,
                        "bbox": list(event_config.view_bbox or event_config.bbox),
                    },
                    "data_warnings": [
                        "Prepared observation evidence is not yet available for this timestep."
                    ],
                }

            # Add the optional generated report as secondary narrative context.
            metadata = _read_json(ai_dir / "metadata.json") or {}
            report_is_current = _report_metadata_is_current(metadata)
            summary_data = (_read_json(ai_dir / "summary.json") or {}) if report_is_current else {}
            parts = []
            if not report_is_current:
                parts.append(
                    "REPORT STATUS:\nNo current validated report is available for this "
                    "observation. Do not infer observation facts from older reports or "
                    "from regional historical totals."
                )
            if summary_data.get("risk_level"):
                parts.append("RISK LEVEL: " + summary_data["risk_level"])
            if summary_data.get("key_points"):
                parts.append("KEY POINTS:\n" + "\n".join("- " + p for p in summary_data["key_points"]))
            if summary_data.get("situation"):
                parts.append("SITUATION:\n" + summary_data["situation"])
            if summary_data.get("key_risks"):
                parts.append("KEY RISKS:\n" + summary_data["key_risks"])
            if summary_data.get("immediate_actions"):
                parts.append("IMMEDIATE ACTIONS:\n" + summary_data["immediate_actions"])
            if report_is_current:
                parts.append(
                    "REPORT PROVENANCE AND DATA AVAILABILITY:\n"
                    + __import__('json').dumps(metadata, ensure_ascii=False)
                )
            for fname, label in (("risk", "RISK ANALYSIS"), ("impact", "IMPACT ANALYSIS"),
                                  ("evacuation", "EVACUATION ANALYSIS"), ("crowd", "CROWD INTELLIGENCE")):
                d = _read_json(ai_dir / f"{fname}.json") if report_is_current else {}
                if d:
                    parts.append(f"{label}:\n{__import__('json').dumps(d, ensure_ascii=False)}")
            summary = "\n\n".join(parts)

    # Keep the assistant identity correct even before a timestep has been selected.
    if analysis_mode is None:
        from db.models import FireEvent
        from pipeline.event_config import get_event_config

        event_obj = FireEvent.query.get(event_id)
        if event_obj is not None:
            analysis_mode = get_event_config(event_obj).analysis_mode

    from agents.chat_agent import run_chat_agent
    return Response(
        stream_with_context(run_chat_agent(summary=summary, road_summary=road_summary,
                                           message=message, history=history,
                                           analysis_mode=analysis_mode,
                                           retrieved_evidence=retrieved_evidence)),
        mimetype="text/plain",
    )


# ── Register sub-module routes on this blueprint ──────────────────────────────
import api.ts_prediction_routes  # noqa: E402, F401
import api.ts_data_routes        # noqa: E402, F401
