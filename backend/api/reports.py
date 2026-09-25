"""backend/api/reports.py
-----------------------
Endpoints for generating, listing, viewing, downloading, and exporting
Investigation Reports (Full Region, Viewport Area, and Selected Feature).
"""

from datetime import datetime, timezone
import json
import logging
import os
from typing import Any, Dict
import uuid

from functools import wraps
from flask import Blueprint, jsonify, request, Response
from db.connection import db
from db.models import InvestigationReport, User
from utils.auth_middleware import _decode_access_token
from utils.rate_limiter import limit_report_generation
from services.report_intelligence import (
    extract_deterministic_evidence,
    synthesize_report_narrative,
    generate_report_pdf,
    generate_report_evidence_csv,
    sanitize_json_payload,
)

reports_bp = Blueprint("reports", __name__, url_prefix="/api/v1/reports")
log = logging.getLogger("reports_api")


VALID_REPORT_STATUSES = {
    "DRAFT",
    "GENERATED",
    "UNDER_REVIEW",
    "APPROVED",
    "SUBMITTED",
    "ACKNOWLEDGED",
    "RETURNED",
    "CLOSED",
}


def optional_token_required(function):
    @wraps(function)
    def decorated(*args, **kwargs):
        user, _ = _decode_access_token()
        if user:
            request.current_user = {
                "user_id": user.id,
                "username": user.username,
                "is_admin": bool(user.is_admin),
                "is_demo": False,
            }
            request.auth_user = user
        else:
            request.current_user = {
                "user_id": None,
                "username": "operator",
                "is_admin": False,
                "is_demo": True,
            }
            request.auth_user = None
        return function(*args, **kwargs)
    return decorated


@reports_bp.route("/generate", methods=["POST"])
@limit_report_generation
@optional_token_required
def generate_report():
    """Generate and persist an authoritative evidence-grounded investigation report."""
    body: Dict[str, Any] = request.get_json(silent=True) or {}
    scope = body.get("scope", "region").lower().strip()
    if scope not in ("region", "viewport", "feature"):
        scope = "region"

    region_id = body.get("region_id")
    region_name = body.get("region_name")
    bounds = body.get("bounds")
    feature_type = body.get("feature_type")
    feature_id = body.get("feature_id")
    custom_title = body.get("title")

    # Resolve user
    user_payload = request.current_user or {}
    creator_id = user_payload.get("id")
    creator_name = user_payload.get("username") or "Operational Analyst"

    try:
        # Layer 1: Deterministic Evidence Extraction
        evidence = extract_deterministic_evidence(
            scope=scope,
            region_id=region_id,
            region_name=region_name,
            bounds=bounds,
            feature_type=feature_type,
            feature_id=feature_id,
        )

        # Layer 2: Fact-grounded Narrative Synthesis
        sections = synthesize_report_narrative(evidence)
        report_title = custom_title or sections.get("title", f"Investigation Report — {region_name or 'General'}")

        # Unique Report Key
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        rand_suffix = uuid.uuid4().hex[:6].upper()
        report_key = f"RPT-{now_str}-{rand_suffix}"

        evidence = sanitize_json_payload(evidence)
        sections = sanitize_json_payload(sections)

        report = InvestigationReport(
            report_key=report_key,
            scope=scope,
            region_id=region_id,
            region_name=evidence["metadata"].get("region_name", region_name),
            feature_type=feature_type,
            feature_id=feature_id,
            title=report_title,
            bounds=bounds,
            evidence_payload=evidence,
            summary_text=sections.get("executive_summary"),
            sections=sections,
            creator_id=creator_id if creator_id and creator_id > 0 else None,
            creator_name=creator_name,
            status="generated",
            is_test=(os.getenv("TESTING") == "1"),
        )
        db.session.add(report)
        db.session.commit()

        return jsonify({
            "id": report.id,
            "report_id": report.id,
            "report_key": report.report_key,
            "scope": report.scope,
            "region_name": report.region_name,
            "feature_type": report.feature_type,
            "feature_id": report.feature_id,
            "title": report.title,
            "summary": report.summary_text,
            "sections": report.sections,
            "evidence": report.evidence_payload,
            "status": report.status or "generated",
            "version": report.version or "v1.0",
            "creator_name": report.creator_name,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }), 201

    except Exception as e:
        db.session.rollback()
        log.error("Failed to generate report: %s", e, exc_info=True)
        return jsonify({"error": f"Report generation failed: {str(e)}"}), 500


@reports_bp.route("", methods=["GET"])
@optional_token_required
def list_reports():
    """List historical reports with optional filtering."""
    scope = request.args.get("scope")
    region_name = request.args.get("region")
    feature_id = request.args.get("feature_id")
    status = request.args.get("status")
    include_test = request.args.get("include_test", "false").lower() in ("1", "true", "yes") or os.getenv("TESTING") == "1"
    limit = min(int(request.args.get("limit", 20)), 100)
    offset = int(request.args.get("offset", 0))

    q = InvestigationReport.query
    if not include_test:
        q = q.filter(InvestigationReport.is_test == False)
    if scope:
        q = q.filter(InvestigationReport.scope == scope)
    if region_name:
        q = q.filter(InvestigationReport.region_name.ilike(f"%{region_name}%"))
    if feature_id:
        q = q.filter(InvestigationReport.feature_id == feature_id)
    if status:
        q = q.filter(InvestigationReport.status.ilike(status))

    total = q.count()
    reports = q.order_by(InvestigationReport.created_at.desc()).offset(offset).limit(limit).all()

    return jsonify({
        "reports": [
            {
                "id": r.id,
                "report_key": r.report_key,
                "scope": r.scope,
                "region_name": r.region_name,
                "feature_type": r.feature_type,
                "feature_id": r.feature_id,
                "title": r.title,
                "summary": r.summary_text,
                "status": r.status or "generated",
                "version": r.version or "v1.0",
                "submission_status": r.submission_status or "NOT_SUBMITTED",
                "creator_name": r.creator_name,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }), 200


@reports_bp.route("/<identifier>", methods=["GET"])
@optional_token_required
def get_report(identifier: str):
    """Retrieve full report by ID or report_key."""
    if identifier.isdigit():
        report = db.session.get(InvestigationReport, int(identifier))
    else:
        report = InvestigationReport.query.filter_by(report_key=identifier).first()

    if not report:
        return jsonify({"error": "Report not found"}), 404

    # Fetch submissions linked to this report
    submissions = [
        {
            "id": s.id,
            "submission_key": s.submission_key,
            "authority_name": s.authority_name,
            "channel": s.channel,
            "reference_number": s.reference_number,
            "status": s.status,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
        }
        for s in report.submissions
    ]

    return jsonify({
        "id": report.id,
        "report_key": report.report_key,
        "scope": report.scope,
        "region_name": report.region_name,
        "feature_type": report.feature_type,
        "feature_id": report.feature_id,
        "title": report.title,
        "summary": report.summary_text,
        "sections": report.sections,
        "evidence": report.evidence_payload,
        "status": report.status or "generated",
        "version": report.version or "v1.0",
        "submission_status": report.submission_status or "NOT_SUBMITTED",
        "approval_trail": report.approval_trail or [],
        "submissions": submissions,
        "creator_name": report.creator_name,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }), 200


@reports_bp.route("/<identifier>/review-status", methods=["POST"])
@optional_token_required
def update_report_status(identifier: str):
    """Transition report through the 8-stage approval workflow."""
    if identifier.isdigit():
        report = db.session.get(InvestigationReport, int(identifier))
    else:
        report = InvestigationReport.query.filter_by(report_key=identifier).first()

    if not report:
        return jsonify({"error": "Report not found"}), 404

    body: Dict[str, Any] = request.get_json(silent=True) or {}
    new_status = (body.get("status") or "").upper().strip()
    notes = body.get("notes", "")

    if new_status not in VALID_REPORT_STATUSES:
        return jsonify({
            "error": f"Invalid review status '{new_status}'. Allowed: {sorted(list(VALID_REPORT_STATUSES))}"
        }), 400

    user_payload = request.current_user or {}
    actor = user_payload.get("username") or "Operational Reviewer"

    old_status = report.status or "generated"
    report.status = new_status

    trail = list(report.approval_trail or [])
    trail.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": f"STATUS_TRANSITION: {old_status} -> {new_status}",
        "notes": notes,
    })
    report.approval_trail = trail

    # Record centralized tamper-evident audit log
    from services.audit_service import record_audit_event
    record_audit_event(
        username=actor,
        user_role=user_payload.get("role", "Operational Reviewer"),
        action_type="REPORT_STATUS_TRANSITION",
        resource_type="investigation_report",
        resource_id=report.report_key,
        status="SUCCESS",
        details={"old_status": old_status, "new_status": new_status, "notes": notes},
        is_test=getattr(report, "is_test", False) or os.getenv("TESTING") == "1",
        session=db.session,
    )
    db.session.commit()

    return jsonify({
        "id": report.id,
        "report_key": report.report_key,
        "status": report.status,
        "version": report.version or "v1.0",
        "approval_trail": report.approval_trail,
    }), 200


@reports_bp.route("/<identifier>/version", methods=["POST"])
@optional_token_required
def create_report_version(identifier: str):
    """Create an immutable revision snapshot (e.g. v1.1 or v2.0)."""
    if identifier.isdigit():
        report = db.session.get(InvestigationReport, int(identifier))
    else:
        report = InvestigationReport.query.filter_by(report_key=identifier).first()

    if not report:
        return jsonify({"error": "Report not found"}), 404

    body: Dict[str, Any] = request.get_json(silent=True) or {}
    version_tag = body.get("version", "v1.1")
    notes = body.get("notes", "Version revision snapshot")

    user_payload = request.current_user or {}
    actor = user_payload.get("username") or "Operational Reviewer"
    old_version = report.version or "v1.0"

    # Increment version on existing report
    report.version = version_tag
    trail = list(report.approval_trail or [])
    trail.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": f"VERSION_INCREMENT: {version_tag}",
        "notes": notes,
    })
    report.approval_trail = trail

    # Record centralized tamper-evident audit log
    from services.audit_service import record_audit_event
    record_audit_event(
        username=actor,
        user_role=user_payload.get("role", "Operational Reviewer"),
        action_type="REPORT_VERSION_INCREMENT",
        resource_type="investigation_report",
        resource_id=report.report_key,
        status="SUCCESS",
        details={"old_version": old_version, "new_version": version_tag, "notes": notes},
        is_test=getattr(report, "is_test", False) or os.getenv("TESTING") == "1",
        session=db.session,
    )
    db.session.commit()

    return jsonify({
        "id": report.id,
        "report_key": report.report_key,
        "version": report.version,
        "status": report.status,
    }), 200


@reports_bp.route("/<identifier>/pdf", methods=["GET"])
@optional_token_required
def download_report_pdf(identifier: str):
    """Generate and stream publication-grade PDF."""
    if identifier.isdigit():
        report = db.session.get(InvestigationReport, int(identifier))
    else:
        report = InvestigationReport.query.filter_by(report_key=identifier).first()

    if not report:
        return jsonify({"error": "Report not found"}), 404

    try:
        pdf_bytes = generate_report_pdf(report)
        filename = f"{report.report_key}.pdf"
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        log.error("PDF generation failed: %s", e, exc_info=True)
        return jsonify({"error": f"Failed to generate PDF: {str(e)}"}), 500


@reports_bp.route("/<identifier>/csv", methods=["GET"])
@optional_token_required
def download_report_csv(identifier: str):
    """Export raw underlying evidence records as CSV."""
    if identifier.isdigit():
        report = db.session.get(InvestigationReport, int(identifier))
    else:
        report = InvestigationReport.query.filter_by(report_key=identifier).first()

    if not report:
        return jsonify({"error": "Report not found"}), 404

    csv_data = generate_report_evidence_csv(report)
    filename = f"{report.report_key}_evidence.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
