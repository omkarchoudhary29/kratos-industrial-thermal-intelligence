"""backend/api/submissions.py
--------------------------
API routes for formal statutory authority directory and submission tracking.
"""

from datetime import datetime, timezone
import logging
import os
from typing import Any, Dict

from flask import Blueprint, jsonify, request
from db.connection import db
from db.models import AuthoritySubmission, InvestigationReport, SystemAuditLog
from services.authority_submission import (
    get_authority_directory,
    record_authority_submission,
    STATUTORY_AUTHORITIES,
    VALID_CHANNELS,
    VALID_SUBMISSION_STATUSES,
)
from utils.auth_middleware import _decode_access_token, block_in_demo_mode

submissions_bp = Blueprint("submissions", __name__, url_prefix="/api/v1/submissions")
log = logging.getLogger("submissions_api")


def _get_current_user():
    user, _ = _decode_access_token()
    if user:
        return user.username, user.id, "Compliance Reviewer"
    return "Operational Analyst", None, "Monitoring Analyst"


@submissions_bp.get("/authorities")
def list_authorities():
    """List directory of statutory authorities for environmental submission routing."""
    return jsonify({
        "total": len(STATUTORY_AUTHORITIES),
        "authorities": get_authority_directory(),
        "valid_channels": list(VALID_CHANNELS),
        "valid_statuses": list(VALID_SUBMISSION_STATUSES),
    })


@submissions_bp.post("/record")
@block_in_demo_mode("Recording authority submissions is disabled in public demo mode.")
def record_submission():
    """Record a formal submission of an intelligence report to a statutory authority."""
    body: Dict[str, Any] = request.get_json(silent=True) or {}
    report_id = body.get("report_id")
    authority_id = (body.get("authority_id") or "").lower().strip()
    purpose = body.get("purpose", "regulatory_compliance")
    channel = (body.get("channel") or "PORTAL").upper().strip()
    reference_number = (body.get("reference_number") or "").strip()
    acknowledgement_number = body.get("acknowledgement_number")
    notes = body.get("notes")

    username, user_id, role = _get_current_user()
    submitted_by = body.get("submitted_by") or username

    if not report_id:
        return jsonify({"error": "report_id is required."}), 400
    if not authority_id:
        return jsonify({"error": "authority_id is required."}), 400
    if not reference_number:
        return jsonify({"error": "Official reference_number (docket/filing ID) is required."}), 400

    try:
        sub_record = record_authority_submission(
            report_id=int(report_id),
            authority_id=authority_id,
            purpose=purpose,
            channel=channel,
            reference_number=reference_number,
            submitted_by=submitted_by,
            acknowledgement_number=acknowledgement_number,
            notes=notes,
            receipt_metadata=body.get("receipt_metadata"),
            ip_address=request.remote_addr,
        )
        return jsonify(sub_record), 201
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        log.error("Failed to record submission: %s", e, exc_info=True)
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@submissions_bp.get("")
def list_submissions():
    """List all recorded authority submissions with optional status or authority filter."""
    authority_id = request.args.get("authority_id")
    status = request.args.get("status")
    report_id = request.args.get("report_id")
    include_test = request.args.get("include_test", "false").lower() in ("1", "true", "yes") or os.getenv("TESTING") == "1"
    limit = max(1, min(100, int(request.args.get("limit", 50))))
    offset = max(0, int(request.args.get("offset", 0)))

    q = AuthoritySubmission.query
    if not include_test:
        q = q.filter(AuthoritySubmission.is_test == False)
    if authority_id:
        q = q.filter(AuthoritySubmission.authority_id == authority_id.lower().strip())
    if status:
        q = q.filter(AuthoritySubmission.status == status.upper().strip())
    if report_id:
        q = q.filter(AuthoritySubmission.report_id == int(report_id))

    total = q.count()
    rows = q.order_by(AuthoritySubmission.submitted_at.desc()).offset(offset).limit(limit).all()

    return jsonify({
        "total": total,
        "limit": limit,
        "offset": offset,
        "submissions": [
            {
                "id": s.id,
                "submission_key": s.submission_key,
                "report_id": s.report_id,
                "report_key": s.report_key,
                "authority_id": s.authority_id,
                "authority_name": s.authority_name,
                "purpose": s.purpose,
                "channel": s.channel,
                "reference_number": s.reference_number,
                "acknowledgement_number": s.acknowledgement_number,
                "submitted_by": s.submitted_by,
                "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
                "status": s.status,
                "notes": s.notes,
            }
            for s in rows
        ],
    })


@submissions_bp.get("/<int:id>")
def get_submission(id: int):
    """Retrieve full submission receipt by ID."""
    sub = db.session.get(AuthoritySubmission, id)
    if not sub:
        return jsonify({"error": f"Submission with ID {id} not found."}), 404

    return jsonify({
        "id": sub.id,
        "submission_key": sub.submission_key,
        "report_id": sub.report_id,
        "report_key": sub.report_key,
        "authority_id": sub.authority_id,
        "authority_name": sub.authority_name,
        "purpose": sub.purpose,
        "channel": sub.channel,
        "reference_number": sub.reference_number,
        "acknowledgement_number": sub.acknowledgement_number,
        "submitted_by": sub.submitted_by,
        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        "status": sub.status,
        "notes": sub.notes,
        "receipt_metadata": sub.receipt_metadata or {},
    })


@submissions_bp.post("/<int:id>/status")
@block_in_demo_mode("Updating authority submission status is disabled in public demo mode.")
def update_submission_status(id: int):
    """Update status of a submission (e.g., mark as ACKNOWLEDGED or COMPLETED)."""
    sub = db.session.get(AuthoritySubmission, id)
    if not sub:
        return jsonify({"error": f"Submission with ID {id} not found."}), 404

    body: Dict[str, Any] = request.get_json(silent=True) or {}
    new_status = (body.get("status") or "").upper().strip()
    ack_number = body.get("acknowledgement_number")
    notes = body.get("notes")

    if new_status not in VALID_SUBMISSION_STATUSES:
        return jsonify({
            "error": f"Invalid status '{new_status}'. Allowed: {VALID_SUBMISSION_STATUSES}"
        }), 400

    sub.status = new_status
    if ack_number:
        sub.acknowledgement_number = str(ack_number).strip()
    if notes:
        sub.notes = f"{sub.notes}\n[Update]: {notes}" if sub.notes else notes
    sub.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "id": sub.id,
        "submission_key": sub.submission_key,
        "status": sub.status,
        "acknowledgement_number": sub.acknowledgement_number,
        "updated_at": sub.updated_at.isoformat(),
    })
