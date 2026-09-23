"""backend/api/notifications.py
------------------------------
Real persistent Notification Center API for KRATOS V3.
Fetches, filters, and manages read/unread alert notifications from fire_alerts and monitoring_fire_events.
"""

from datetime import datetime, timezone
import logging
from flask import Blueprint, jsonify, request
from db.connection import db
from db.models import FireAlert, MonitoringFireEvent, FireEvent, FireDetection

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/v1/notifications")
log = logging.getLogger("notifications_api")


@notifications_bp.route("", methods=["GET"])
def list_notifications():
    """List persistent alerts/notifications with unread count."""
    status = request.args.get("status", "all").lower().strip()
    severity = request.args.get("severity")
    limit = min(int(request.args.get("limit", 50)), 100)
    offset = int(request.args.get("offset", 0))

    query = db.session.query(
        FireAlert,
        FireEvent.name.label("region_name"),
        MonitoringFireEvent.centroid_latitude,
        MonitoringFireEvent.centroid_longitude,
    ).outerjoin(
        MonitoringFireEvent, FireAlert.fire_event_id == MonitoringFireEvent.id
    ).outerjoin(
        FireEvent, MonitoringFireEvent.monitoring_region_id == FireEvent.id
    )

    if status == "unread":
        query = query.filter(FireAlert.is_read == False)
    if severity:
        query = query.filter(FireAlert.severity == severity.upper().strip())

    total = query.count()
    unread_count = db.session.query(FireAlert).filter(FireAlert.is_read == False).count()

    results = query.order_by(FireAlert.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for alert, region_name, lat, lon in results:
        items.append({
            "id": alert.id,
            "fire_event_id": alert.fire_event_id,
            "detection_id": alert.detection_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "is_read": bool(alert.is_read),
            "read_at": alert.read_at.isoformat() if alert.read_at else None,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "region_name": region_name or "General Corridor",
            "latitude": float(lat) if lat is not None else None,
            "longitude": float(lon) if lon is not None else None,
        })

    return jsonify({
        "notifications": items,
        "unread_count": unread_count,
        "total": total,
        "limit": limit,
        "offset": offset,
    }), 200


@notifications_bp.route("/<int:alert_id>/read", methods=["PATCH"])
def mark_read(alert_id: int):
    """Mark a specific alert notification as read."""
    alert = db.session.get(FireAlert, alert_id)
    if not alert:
        return jsonify({"error": "Notification not found"}), 404

    alert.is_read = True
    alert.read_at = datetime.now(timezone.utc)
    db.session.commit()

    unread_count = db.session.query(FireAlert).filter(FireAlert.is_read == False).count()
    return jsonify({
        "id": alert.id,
        "is_read": True,
        "read_at": alert.read_at.isoformat(),
        "unread_count": unread_count,
    }), 200


@notifications_bp.route("/mark-all-read", methods=["POST"])
def mark_all_read():
    """Mark all unread notifications as read."""
    now = datetime.now(timezone.utc)
    updated_count = db.session.query(FireAlert).filter(
        FireAlert.is_read == False
    ).update(
        {"is_read": True, "read_at": now}, synchronize_session="fetch"
    )
    db.session.commit()

    return jsonify({
        "success": True,
        "updated_count": updated_count,
        "unread_count": 0,
    }), 200
