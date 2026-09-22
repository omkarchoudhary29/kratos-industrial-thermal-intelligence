"""backend/api/settings.py
------------------------
API routes for Platform Settings, RBAC Roles, and System Audit Logs.
"""

from typing import Any, Dict

from flask import Blueprint, jsonify, request
from services.settings_service import settings_service
from utils.auth_middleware import _decode_access_token

settings_bp = Blueprint("settings", __name__, url_prefix="/api/v1/settings")


def _get_current_user():
    user, _ = _decode_access_token()
    if user:
        return user.username, user.id, "Administrator" if user.is_admin else "Monitoring Analyst"
    return "Operational Analyst", None, "Monitoring Analyst"


@settings_bp.get("/profile")
def get_user_profile():
    """Get active user profile and assigned permissions."""
    username, user_id, role = _get_current_user()
    return jsonify({
        "user_id": user_id,
        "username": username,
        "role": role,
        "available_roles": settings_service.get_rbac_roles(),
    })


@settings_bp.get("/monitoring")
def get_monitoring_settings():
    """Retrieve operational monitoring thresholds."""
    return jsonify(settings_service.get_monitoring_thresholds())


@settings_bp.post("/monitoring")
def update_monitoring_settings():
    """Update operational monitoring thresholds."""
    body: Dict[str, Any] = request.get_json(silent=True) or {}
    username, _, _ = _get_current_user()
    updated = settings_service.update_monitoring_thresholds(body, username=username)
    return jsonify({
        "status": "success",
        "thresholds": updated,
    })


@settings_bp.get("/models")
def get_model_settings():
    """Retrieve machine learning model metadata and training status."""
    return jsonify(settings_service.get_model_administration_status())


@settings_bp.get("/audit-logs")
def get_audit_logs():
    """Query immutable system audit logs."""
    action_type = request.args.get("action_type")
    username = request.args.get("username")
    include_test = request.args.get("include_test", "false").lower() in ("1", "true", "yes")
    limit = max(1, min(100, int(request.args.get("limit", 50))))
    offset = max(0, int(request.args.get("offset", 0)))

    logs_data = settings_service.list_audit_logs(
        action_type=action_type,
        username=username,
        limit=limit,
        offset=offset,
        include_test=include_test,
    )
    return jsonify(logs_data)


@settings_bp.get("/audit-logs/verify")
def verify_audit_logs():
    """Cryptographic audit chain verification endpoint."""
    verification_result = settings_service.verify_audit_logs()
    status_code = 200 if verification_result.get("is_valid") else 409
    return jsonify(verification_result), status_code


@settings_bp.route("/purge", methods=["POST", "DELETE"])
def reject_destructive_purge():
    """Safety guard: Unconditionally rejects destructive evidence purges to uphold preservation rules."""
    username, _, _ = _get_current_user()
    return jsonify({
        "error": "Destructive system purge prohibited.",
        "message": "KRATOS system preservation rules strictly prohibit bulk deletion of historical observations, clusters, reports, and audit logs.",
        "status": "FORBIDDEN",
    }), 403
