"""Risk-first APIs backed by prepared thermal intelligence artifacts."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.thermal_intelligence import thermal_intelligence


thermal_bp = Blueprint("thermal", __name__)


def _bounded_int(name: str, default: int, *, minimum: int = 0, maximum: int = 2000) -> int:
    try:
        return max(minimum, min(maximum, int(request.args.get(name, default))))
    except (TypeError, ValueError):
        return default


def _optional_year():
    value = request.args.get("year")
    if value in (None, ""):
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _optional_bool(name: str):
    value = request.args.get(name)
    if value is None or value == "":
        return None
    if value.lower() in {"1", "true", "yes"}:
        return True
    if value.lower() in {"0", "false", "no"}:
        return False
    return None


def _risk_levels(default: str | None = None):
    value = request.args.get("risk_level", default)
    return [item.strip() for item in value.split(",") if item.strip()] if value else None


def _filters(default_risk: str | None = None):
    return {
        "risk_levels": _risk_levels(default_risk),
        "confidence": request.args.get("confidence"),
        "region": request.args.get("region"),
        "year": _optional_year(),
        "iforest_agreement": _optional_bool("iforest_agreement"),
        "data_mode": request.args.get("data_mode"),
        "start_time": request.args.get("start_time"),
        "end_time": request.args.get("end_time"),
    }


@thermal_bp.errorhandler(FileNotFoundError)
def _artifact_missing(error):
    return jsonify({"error": str(error), "data_available": False}), 503


@thermal_bp.errorhandler(ValueError)
def _artifact_invalid(error):
    return jsonify({"error": str(error), "data_available": False}), 503


@thermal_bp.get("/stats")
def get_stats():
    return jsonify(thermal_intelligence.stats(
        region=request.args.get("region"),
        year=_optional_year(),
        data_mode=request.args.get("data_mode"),
        start_time=request.args.get("start_time"),
        end_time=request.args.get("end_time"),
    ))


@thermal_bp.get("/events")
def get_events():
    payload = thermal_intelligence.list_events(
        limit=_bounded_int("limit", 100),
        offset=_bounded_int("offset", 0, maximum=1_000_000),
        **_filters(),
    )
    return jsonify(payload)


@thermal_bp.get("/events/<source_event_id>")
def get_event(source_event_id: str):
    event = thermal_intelligence.event_detail(source_event_id)
    if event is None:
        return jsonify({"error": "thermal event not found"}), 404
    return jsonify(event)


@thermal_bp.get("/map")
def get_map_events():
    # Risk-first demo default: do not ship thousands of historical low events.
    payload = thermal_intelligence.map_events(
        limit=_bounded_int("limit", 1000),
        **_filters(default_risk="high,critical"),
    )
    return jsonify(payload)


@thermal_bp.get("/sources")
def get_sources():
    payload = thermal_intelligence.list_sources(
        region=request.args.get("region"),
        limit=_bounded_int("limit", 500),
        offset=_bounded_int("offset", 0, maximum=1_000_000),
    )
    return jsonify(payload)


@thermal_bp.get("/sources/<thermal_source_id>")
def get_source_detail(thermal_source_id: str):
    source = thermal_intelligence.source_detail(thermal_source_id)
    if source is None:
        return jsonify({"error": "thermal source not found"}), 404
    return jsonify(source)


@thermal_bp.get("/ml-evaluation")
def get_ml_evaluation():
    from services.ml_evaluation import ml_evaluation_service
    return jsonify(ml_evaluation_service.get_evaluation_metrics())


@thermal_bp.get("/pipeline/status")
def get_pipeline_status():
    """Report genuine ingestion, enrichment, and provenance status from ingestion_audit."""
    from datetime import datetime, timezone
    from db.connection import db
    from sqlalchemy import text

    try:
        row = db.session.execute(text("SELECT * FROM ingestion_audit;")).mappings().first()
        if not row:
            return jsonify({
                "status": "not_configured",
                "message": "No sync records found in ingestion_audit",
                "details": None,
            })

        data = dict(row)
        last_sync = data.get("last_successful_sync")
        last_error = data.get("last_error")
        raw_status = (data.get("pipeline_status") or "").lower()

        # Determine semantic state
        now = datetime.now(timezone.utc)
        if raw_status in ("running", "syncing"):
            state = "running"
        elif last_error and (data.get("records_received") or 0) == 0:
            state = "failed"
        elif last_error and (data.get("records_received") or 0) > 0:
            state = "partial_success"
        elif last_sync and (now - last_sync).total_seconds() > 3 * 3600:
            state = "stale"
        elif raw_status in ("succeeded", "completed"):
            state = "completed"
        else:
            state = raw_status or "unknown"

        # Format datetimes
        for k in ("last_attempt_at", "last_successful_sync", "latest_detection_time", "audit_generated_at"):
            if data.get(k):
                data[k] = data[k].isoformat()

        return jsonify({
            "status": state,
            "raw_pipeline_status": raw_status,
            "provenance_level": "sync_and_feature_audit",
            "audit": data,
        })
    except Exception as exc:
        return jsonify({
            "status": "failed",
            "error": "Error querying pipeline audit",
            "details": str(exc),
        }), 500

