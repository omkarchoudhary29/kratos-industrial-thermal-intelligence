"""backend/api/integrations.py
---------------------------
API routes for Data & Integrations Workspace.
"""

import logging
import os
from typing import Any, Dict

from flask import Blueprint, jsonify, request
from db.connection import db
from db.models import DataConnector, IntegrationSyncJob
from services.integration_manager import (
    integration_manager,
    validate_url_ssrf_safety,
)
from utils.auth_middleware import _decode_access_token, block_in_demo_mode

integrations_bp = Blueprint("integrations", __name__, url_prefix="/api/v1/integrations")
log = logging.getLogger("integrations_api")


def _get_current_username():
    user, _ = _decode_access_token()
    return user.username if user else "Operational Analyst"


@integrations_bp.get("/connectors")
def list_connectors():
    """List all registered external data connectors with masked credentials."""
    connectors = integration_manager.list_connectors()
    return jsonify({
        "total": len(connectors),
        "connectors": connectors,
    })


@integrations_bp.get("/connectors/<int:id>")
def get_connector(id: int):
    """Retrieve connector details."""
    connector = db.session.get(DataConnector, id)
    if not connector:
        return jsonify({"error": f"Connector {id} not found."}), 404

    return jsonify({
        "id": connector.id,
        "connector_key": connector.connector_key,
        "name": connector.name,
        "provider": connector.provider,
        "connector_type": connector.connector_type,
        "endpoint_url": connector.endpoint_url,
        "auth_type": connector.auth_type,
        "is_active": connector.is_active,
        "health_status": connector.health_status,
        "records_received": connector.records_received,
        "records_accepted": connector.records_accepted,
        "last_sync_at": connector.last_sync_at.isoformat() if connector.last_sync_at else None,
    })


@integrations_bp.post("/test-connection")
def test_connection():
    """Test remote endpoint with strict SSRF enforcement."""
    body: Dict[str, Any] = request.get_json(silent=True) or {}
    url = (body.get("endpoint_url") or "").strip()
    auth_type = body.get("auth_type", "NONE")
    headers = body.get("headers")

    if not url:
        return jsonify({"error": "endpoint_url is required."}), 400

    result = integration_manager.test_remote_endpoint(url, auth_type=auth_type, headers=headers)
    status_code = 200 if result.get("success") else (403 if result.get("security_flag") == "SSRF_BLOCKED" else 400)
    return jsonify(result), status_code


@integrations_bp.post("/connectors")
@block_in_demo_mode("Registering external connectors is disabled in public demo mode.")
def create_connector():
    """Register a new external connector."""
    body: Dict[str, Any] = request.get_json(silent=True) or {}
    username = _get_current_username()

    try:
        new_conn = integration_manager.register_connector(body, username=username)
        return jsonify(new_conn), 201
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        log.error("Failed to register connector: %s", e, exc_info=True)
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@integrations_bp.post("/connectors/<int:id>/sync")
@block_in_demo_mode("Triggering external connector synchronization is disabled in public demo mode.")
def sync_connector(id: int):
    """Trigger a sync job for a connector."""
    username = _get_current_username()
    try:
        res = integration_manager.trigger_sync(id, username=username)
        return jsonify(res), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    except Exception as e:
        log.error("Sync failed: %s", e, exc_info=True)
        return jsonify({"error": f"Sync execution failed: {str(e)}"}), 500


@integrations_bp.get("/sync-jobs")
def list_sync_jobs():
    """List recent synchronization jobs."""
    limit = max(1, min(50, int(request.args.get("limit", 20))))
    jobs = IntegrationSyncJob.query.order_by(IntegrationSyncJob.start_time.desc()).limit(limit).all()
    return jsonify({
        "total": len(jobs),
        "sync_jobs": [
            {
                "id": j.id,
                "job_key": j.job_key,
                "connector_id": j.connector_id,
                "connector_key": j.connector_key,
                "start_time": j.start_time.isoformat() if j.start_time else None,
                "end_time": j.end_time.isoformat() if j.end_time else None,
                "duration_seconds": j.duration_seconds,
                "status": j.status,
                "records_fetched": j.records_fetched,
                "records_accepted": j.records_accepted,
                "duplicates_dropped": j.duplicates_dropped,
                "records_rejected": j.records_rejected,
            }
            for j in jobs
        ],
    })
