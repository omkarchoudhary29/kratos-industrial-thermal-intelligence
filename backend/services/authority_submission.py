"""backend/services/authority_submission.py
-----------------------------------------
Official Statutory Authority Directory and Formal Submission Tracking Service.
Enforces the strict rule: PDF download != submission.
All submissions require official routing, docket/reference numbers, and status tracking.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import text
from db.connection import db
from db.models import AuthoritySubmission, InvestigationReport, User, SystemAuditLog

log = logging.getLogger("authority_submission")

STATUTORY_AUTHORITIES = [
    {
        "authority_id": "cpcb",
        "authority_name": "Central Pollution Control Board (CPCB)",
        "jurisdiction": "National / Interstate Air Quality & Industrial Emissions",
        "statutory_act": "Air (Prevention and Control of Pollution) Act, 1981, Section 16",
        "portal_url": "https://cpcb.nic.in/air-quality-portal",
        "official_email": "airquality.cpcb@nic.in",
        "submission_channels": ["PORTAL", "EMAIL", "PHYSICAL_DISPATCH", "API"],
        "default_routing_purpose": "regulatory_compliance",
    },
    {
        "authority_id": "ospcb",
        "authority_name": "Odisha State Pollution Control Board (OSPCB)",
        "jurisdiction": "State of Odisha (Angul-Talcher, Jharsuguda corridors)",
        "statutory_act": "Air (Prevention and Control of Pollution) Act, 1981, Section 17",
        "portal_url": "http://ospcboard.org/online-submission",
        "official_email": "membersecretary@ospcboard.org",
        "submission_channels": ["PORTAL", "EMAIL", "PHYSICAL_DISPATCH"],
        "default_routing_purpose": "regulatory_compliance",
    },
    {
        "authority_id": "jspcb",
        "authority_name": "Jharkhand State Pollution Control Board (JSPCB)",
        "jurisdiction": "State of Jharkhand (Dhanbad-Bokaro industrial belt)",
        "statutory_act": "Air (Prevention and Control of Pollution) Act, 1981, Section 17",
        "portal_url": "https://jspcb.nic.in/industrial-compliance",
        "official_email": "ms@jspcb.org",
        "submission_channels": ["PORTAL", "EMAIL", "PHYSICAL_DISPATCH"],
        "default_routing_purpose": "regulatory_compliance",
    },
    {
        "authority_id": "cecb",
        "authority_name": "Chhattisgarh Environment Conservation Board (CECB)",
        "jurisdiction": "State of Chhattisgarh (Korba, Raigarh corridors)",
        "statutory_act": "Air (Prevention and Control of Pollution) Act, 1981, Section 17",
        "portal_url": "https://enviscecb.org/compliance-portal",
        "official_email": "hocecb@gmail.com",
        "submission_channels": ["PORTAL", "EMAIL", "PHYSICAL_DISPATCH"],
        "default_routing_purpose": "regulatory_compliance",
    },
    {
        "authority_id": "moefcc",
        "authority_name": "Ministry of Environment, Forest and Climate Change (MoEFCC)",
        "jurisdiction": "National Environmental Clearance & Thermal Baseline Policy",
        "statutory_act": "Environment (Protection) Act, 1986, Section 3 & 5",
        "portal_url": "https://parivesh.nic.in",
        "official_email": "ia.division@moef.gov.in",
        "submission_channels": ["PORTAL", "EMAIL", "PHYSICAL_DISPATCH"],
        "default_routing_purpose": "regulatory_compliance",
    },
    {
        "authority_id": "district_admin",
        "authority_name": "District Administration / Sub-Divisional Magistrate",
        "jurisdiction": "District Disaster Management & Industrial Safety",
        "statutory_act": "Disaster Management Act, 2005, Section 30",
        "portal_url": "https://districts.ecourts.gov.in",
        "official_email": "collector.office@nic.in",
        "submission_channels": ["EMAIL", "PHYSICAL_DISPATCH"],
        "default_routing_purpose": "fire_hazard_alert",
    },
    {
        "authority_id": "forest_dept",
        "authority_name": "State Forest Department (Wildlife & Territorial Wings)",
        "jurisdiction": "Protected Forest Buffers, Wildlife Corridors & Reserves",
        "statutory_act": "Indian Forest Act, 1927 & Forest (Conservation) Act, 1980",
        "portal_url": "https://forest.gov.in",
        "official_email": "pccf.wildlife@nic.in",
        "submission_channels": ["PORTAL", "EMAIL", "PHYSICAL_DISPATCH"],
        "default_routing_purpose": "field_verification_request",
    },
    {
        "authority_id": "dgms",
        "authority_name": "Directorate General of Mines Safety (DGMS)",
        "jurisdiction": "Open Cast Mines, Coal Washeries & Overburden Dumps",
        "statutory_act": "Mines Act, 1952, Section 22",
        "portal_url": "https://dgms.gov.in",
        "official_email": "dg@dgms.gov.in",
        "submission_channels": ["PORTAL", "EMAIL", "PHYSICAL_DISPATCH"],
        "default_routing_purpose": "fire_hazard_alert",
    },
]

VALID_PURPOSES = {
    "regulatory_compliance",
    "air_quality_advisory",
    "fire_hazard_alert",
    "field_verification_request",
    "annual_environmental_audit",
}

VALID_CHANNELS = {"PORTAL", "EMAIL", "PHYSICAL_DISPATCH", "API"}
VALID_SUBMISSION_STATUSES = {
    "PREPARED",
    "AWAITING_APPROVAL",
    "APPROVED_FOR_SUBMISSION",
    "SUBMITTED",
    "ACKNOWLEDGED",
    "RETURNED",
    "RESUBMISSION_REQUIRED",
    "COMPLETED",
}


def get_authority_directory() -> List[Dict[str, Any]]:
    """Return the catalog of statutory authorities."""
    return STATUTORY_AUTHORITIES


def record_authority_submission(
    report_id: int,
    authority_id: str,
    purpose: str,
    channel: str,
    reference_number: str,
    submitted_by: str,
    acknowledgement_number: Optional[str] = None,
    notes: Optional[str] = None,
    receipt_metadata: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    is_test: Optional[bool] = None,
) -> Dict[str, Any]:
    """Formally record a submission to a statutory authority.
    
    Enforces strict operational integrity:
    1. Report must exist.
    2. Report must be formally approved prior to dispatch.
    3. Channel, reference number, and authority must be valid.
    """
    report = db.session.get(InvestigationReport, report_id)
    if not report:
        raise ValueError(f"InvestigationReport with ID {report_id} not found.")

    # Enforce Approval Requirement: Report must be in an approved state prior to formal statutory submission
    approved_statuses = {"APPROVED", "APPROVED_FOR_SUBMISSION"}
    current_status = (report.status or "").upper().strip()
    if current_status not in approved_statuses:
        raise ValueError(
            f"Pre-Submission Approval Requirement: InvestigationReport #{report_id} has status '{report.status}'. "
            f"Reports must be formally approved by an authorized reviewer (status in {approved_statuses}) "
            "before recording a formal statutory authority submission."
        )

    auth_entry = next((a for a in STATUTORY_AUTHORITIES if a["authority_id"] == authority_id), None)
    if not auth_entry:
        raise ValueError(f"Unknown statutory authority ID: '{authority_id}'.")

    if channel.upper() not in VALID_CHANNELS:
        raise ValueError(f"Invalid delivery channel '{channel}'. Allowed: {VALID_CHANNELS}")

    # Generate unique submission key
    now_utc = datetime.now(timezone.utc)
    now_str = now_utc.strftime("%Y%m%d")
    rand_suffix = uuid.uuid4().hex[:6].upper()
    submission_key = f"SUB-{now_str}-{rand_suffix}"

    status = "ACKNOWLEDGED" if acknowledgement_number else "SUBMITTED"

    # Determine test provenance
    test_flag = is_test if is_test is not None else (
        "TEST" in reference_number.upper() or os.getenv("TESTING") == "1" or "test" in str(notes).lower()
    )

    submission = AuthoritySubmission(
        submission_key=submission_key,
        report_id=report.id,
        report_key=report.report_key,
        authority_id=authority_id,
        authority_name=auth_entry["authority_name"],
        purpose=purpose or auth_entry["default_routing_purpose"],
        channel=channel.upper(),
        reference_number=reference_number.strip(),
        acknowledgement_number=acknowledgement_number.strip() if acknowledgement_number else None,
        submitted_by=submitted_by,
        submitted_at=now_utc,
        status=status,
        notes=notes,
        receipt_metadata=receipt_metadata or {},
        is_test=test_flag,
    )
    db.session.add(submission)

    # Update report status and submission status
    report.status = "SUBMITTED"
    report.submission_status = "SUBMITTED"

    # Append to approval/audit trail on report
    trail = list(report.approval_trail or [])
    trail.append({
        "timestamp": now_utc.isoformat(),
        "action": "AUTHORITY_SUBMISSION",
        "actor": submitted_by,
        "submission_key": submission_key,
        "authority": auth_entry["authority_name"],
        "channel": channel.upper(),
        "reference_number": reference_number.strip(),
    })
    report.approval_trail = trail

    # Record centralized tamper-evident cryptographic audit log
    from services.audit_service import record_audit_event
    record_audit_event(
        username=submitted_by,
        user_role="Compliance Reviewer",
        action_type="REPORT_SUBMISSION",
        resource_type="investigation_report",
        resource_id=report.report_key,
        ip_address=ip_address,
        status="SUCCESS",
        details={
            "submission_key": submission_key,
            "authority_id": authority_id,
            "authority_name": auth_entry["authority_name"],
            "channel": channel.upper(),
            "reference_number": reference_number.strip(),
            "acknowledgement_number": acknowledgement_number.strip() if acknowledgement_number else None,
        },
        is_test=test_flag,
        session=db.session,
    )
    db.session.commit()

    return {
        "id": submission.id,
        "submission_key": submission.submission_key,
        "report_id": submission.report_id,
        "report_key": submission.report_key,
        "authority_id": submission.authority_id,
        "authority_name": submission.authority_name,
        "purpose": submission.purpose,
        "channel": submission.channel,
        "reference_number": submission.reference_number,
        "acknowledgement_number": submission.acknowledgement_number,
        "submitted_by": submission.submitted_by,
        "submitted_at": submission.submitted_at.isoformat(),
        "status": submission.status,
    }
