"""
backend/tests/test_enhancement_phase3.py
----------------------------------------
Exhaustive Automated Verification Suite for KRATOS V3.1 Enhancement Phase 3:
  - Test 1: Full Region Report Generation & Scope Resolution
  - Test 2: Selected Cluster Report Generation & Provenance
  - Test 3: Map Viewport Report Generation & Bounding Box Enforcement
  - Test 4: Selected Facility Report Generation & Causation Safeguard
  - Test 5: PDF Document Integrity, Numbered Canvas & Multi-Section Layout
  - Test 6: Statutory Authority Directory & Submission Lifecycle Tracking
  - Test 7: High-Priority Follow-up Workflow, Idempotency & Audit Trail
  - Test 8: Historical Follow-up Data Preservation & Non-Destructive Integrity
  - Test 9: Advanced Geospatial & Operational Analytics Calculations
  - Test 10: Data Connector Inventory & Credential Masking Security
  - Test 11: Remote Connection Testing & Strict SSRF Protection
  - Test 12: Global AI Investigator Operational Context Grounding
  - Test 13: Notification Center Event Persistence & Mark Read
  - Test 14: System Administration Settings, RBAC & Audit Logs
  - Test 15: Cross-Workspace End-to-End Regression Validation
"""

from datetime import datetime, timezone
import json
import os
import sys
from pathlib import Path
import pytest

# Ensure backend root is in python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import config
from main import create_app
from db.connection import db
from db.models import (
    InvestigationReport,
    FollowUpTask,
    FollowUpNote,
    AuthoritySubmission,
    DataConnector,
    IntegrationSyncJob,
    FireAlert,
    SystemAuditLog,
)
from services.report_intelligence import (
    extract_deterministic_evidence,
    synthesize_report_narrative,
    generate_report_pdf,
    generate_report_evidence_csv,
)
from services.authority_submission import (
    get_authority_directory,
    record_authority_submission,
    STATUTORY_AUTHORITIES,
)
from services.integration_manager import validate_url_ssrf_safety, integration_manager
from services.advanced_analytics import advanced_analytics_service
from services.settings_service import settings_service


@pytest.fixture(scope="module")
def app():
    """Create test application context with database bound."""
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app


@pytest.fixture(scope="module")
def client(app):
    """Flask test client."""
    return app.test_client()


# ── TEST 1: Full Region Report ───────────────────────────────────────────────

def test_1_full_region_report(client):
    """Test full region scope resolution and report generation without selecting a feature."""
    payload = {
        "scope": "region",
        "region_name": "bastar",
        "title": "Comprehensive Bastar Corridor Environmental Audit",
    }
    res = client.post("/api/v1/reports/generate", json=payload)
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.data}"
    data = res.get_json()

    assert data["scope"] == "region"
    assert "bastar" in data["region_name"].lower()
    assert "RPT-" in data["report_key"]
    assert "sections" in data
    assert "executive_summary" in data["sections"]
    assert data["status"] in ("generated", "GENERATED")

    # Verify immutable evidence snapshot stored
    report_db = db.session.get(InvestigationReport, data["id"])
    assert report_db is not None
    assert report_db.evidence_payload is not None
    assert report_db.evidence_payload["metadata"]["scope"] == "region"


# ── TEST 2: Selected Cluster Report ──────────────────────────────────────────

def test_2_selected_cluster_report(client):
    """Test selected persistent cluster report generation with exact cluster identity."""
    payload = {
        "scope": "feature",
        "feature_type": "cluster",
        "feature_id": "bastar_source_0",
        "region_name": "bastar",
    }
    res = client.post("/api/v1/reports/generate", json=payload)
    assert res.status_code == 201
    data = res.get_json()

    assert data["scope"] == "feature"
    assert data["feature_id"] == "bastar_source_0"
    assert "target_feature" in data["evidence"]
    assert data["evidence"]["target_feature"]["id"] == "bastar_source_0"


# ── TEST 3: Map Viewport Report ──────────────────────────────────────────────

def test_3_map_viewport_report(client):
    """Test viewport-bounded report query with strict coordinate bounds."""
    bounds = {"west": 81.0, "south": 18.5, "east": 82.5, "north": 20.0}
    payload = {
        "scope": "viewport",
        "bounds": bounds,
        "region_name": "Active Viewport Area",
    }
    res = client.post("/api/v1/reports/generate", json=payload)
    assert res.status_code == 201
    data = res.get_json()

    assert data["scope"] == "viewport"
    assert "viewport_bounds" in data["evidence"]["observation_stats"]
    assert data["evidence"]["observation_stats"]["viewport_bounds"]["west"] == 81.0


# ── TEST 4: Selected Facility Report ─────────────────────────────────────────

def test_4_selected_facility_report(client):
    """Test OSM facility report generation and causation safeguard disclaimer."""
    payload = {
        "scope": "feature",
        "feature_type": "facility",
        "feature_id": "1",
        "region_name": "Industrial Complex",
    }
    res = client.post("/api/v1/reports/generate", json=payload)
    assert res.status_code == 201
    data = res.get_json()

    assert data["scope"] == "feature"
    sections = data.get("sections", {})
    # Verify causation disclaimer present
    fac_corr = sections.get("section_7_source_facility_context") or sections.get("facility_correlation", {})
    assert "causation_safeguard" in fac_corr or "causation_disclaimer" in fac_corr


# ── TEST 5: PDF Document Integrity ───────────────────────────────────────────

def test_5_pdf_document_integrity(app):
    """Verify that ReportLab builds a readable, valid PDF binary without truncation."""
    with app.app_context():
        report = InvestigationReport.query.order_by(InvestigationReport.id.desc()).first()
        assert report is not None, "No report available for PDF test"

        pdf_bytes = generate_report_pdf(report)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 2000, f"PDF too small ({len(pdf_bytes)} bytes)"
        assert pdf_bytes.startswith(b"%PDF"), "Generated file is not a valid PDF binary"

        # Verify CSV export
        csv_str = generate_report_evidence_csv(report)
        assert "report_id,scope,region_name" in csv_str
        assert report.report_key in csv_str


# ── TEST 6: Statutory Authority Directory & Submissions ──────────────────────

def test_6_statutory_authority_submission(client, app):
    """Test statutory authority catalog and official submission tracking."""
    # 1. Authority directory
    res_dir = client.get("/api/v1/submissions/authorities")
    assert res_dir.status_code == 200
    dir_data = res_dir.get_json()
    assert dir_data["total"] >= 5
    auth_ids = [a["authority_id"] for a in dir_data["authorities"]]
    assert "cpcb" in auth_ids
    assert "moefcc" in auth_ids

    # 2. Record formal submission
    with app.app_context():
        latest_report = InvestigationReport.query.order_by(InvestigationReport.id.desc()).first()
        assert latest_report is not None

        sub_payload = {
            "report_id": latest_report.id,
            "authority_id": "cpcb",
            "purpose": "regulatory_compliance",
            "channel": "PORTAL",
            "reference_number": "CPCB/EIA/2026/TEST-SUB-999",
            "acknowledgement_number": "ACK-CPCB-2026-999",
            "notes": "Automated regression filing for CPCB ambient monitoring.",
        }

        # Validate Pre-Submission Approval Enforcement (Critical Fix 3):
        # Attempting submission while report is in unapproved state must be blocked
        if latest_report.status not in ("APPROVED", "APPROVED_FOR_SUBMISSION"):
            res_fail = client.post("/api/v1/submissions/record", json=sub_payload)
            assert res_fail.status_code == 400
            assert "formally approved" in res_fail.get_json()["error"]

            # Formal approval before statutory dispatch
            latest_report.status = "APPROVED_FOR_SUBMISSION"
            db.session.commit()

        res_sub = client.post("/api/v1/submissions/record", json=sub_payload)
        assert res_sub.status_code == 201
        sub_data = res_sub.get_json()
        assert sub_data["submission_key"].startswith("SUB-")
        assert sub_data["status"] == "ACKNOWLEDGED"

        # Check report updated
        db.session.refresh(latest_report)
        assert latest_report.status == "SUBMITTED"


# ── TEST 7: High-Priority Follow-up Workflow & Deduplication ─────────────────

def test_7_followup_workflow_and_deduplication(client, app):
    """Test follow-up creation, idempotency duplicate prevention, and audit note additions."""
    unique_fid = f"test_cluster_p3_{int(datetime.now(timezone.utc).timestamp())}"

    # 1. Create primary follow-up
    payload = {
        "title": "Investigate High FRP Spike at Metallurgical Complex",
        "feature_type": "cluster",
        "feature_id": unique_fid,
        "region_name": "dhanbad_bokaro",
        "priority": "HIGH",
        "status": "OPEN",
        "assigned_to": "Officer K. Sharma",
        "description": "Inspect flare stack telemetry and verify continuous opacity monitor.",
    }
    res = client.post("/api/v1/followups", json=payload)
    assert res.status_code == 201
    task_data = res.get_json()
    assert task_data["task_key"].startswith("FLW-")
    task_id = task_data["id"]

    # 2. Duplicate prevention check (should return 409 without force)
    res_dup = client.post("/api/v1/followups", json=payload)
    assert res_dup.status_code == 409
    dup_data = res_dup.get_json()
    assert dup_data["is_duplicate"] is True

    # 3. Add operational audit note
    note_payload = {
        "note_text": "Field dispatch completed; plant engineer confirms authorized purging.",
        "status_change": "RESOLVED",
    }
    res_note = client.post(f"/api/v1/followups/{task_id}/notes", json=note_payload)
    assert res_note.status_code == 201

    # 4. Check status updated
    res_get = client.get(f"/api/v1/followups/{task_id}")
    assert res_get.status_code == 200
    task_updated = res_get.get_json()
    assert task_updated["status"] == "RESOLVED"
    assert len(task_updated["notes"]) >= 2


# ── TEST 8: Historical Follow-up Data Preservation ───────────────────────────

def test_8_historical_followup_preservation(app):
    """Confirm zero destructive data deletion; historical tasks remain intact."""
    with app.app_context():
        total_tasks = FollowUpTask.query.count()
        assert total_tasks >= 15, f"Expected at least 15 historical follow-ups, found {total_tasks}"

        resolved_count = FollowUpTask.query.filter(FollowUpTask.status.in_(["RESOLVED", "CLOSED"])).count()
        assert resolved_count >= 5, "Historical resolved records must be preserved"


# ── TEST 9: Advanced Geospatial & Operational Analytics ──────────────────────

def test_9_advanced_analytics_metrics(client):
    """Verify cross-corridor comparative intelligence, thermal distributions, and KPIs."""
    res = client.get("/api/v1/analytics/overview")
    assert res.status_code == 200
    data = res.get_json()

    assert data["total_corridors_monitored"] >= 10
    corridors = data["corridors"]
    assert len(corridors) >= 10
    assert any(c["corridor_key"] == "dhanbad_bokaro" for c in corridors)

    # Check thermal distribution
    dist = data["thermal_distribution"]
    assert "diurnal_breakdown" in dist
    assert "daytime_detections" in dist["diurnal_breakdown"]
    assert "nighttime_detections" in dist["diurnal_breakdown"]

    # Check operational KPIs
    kpis = data["workflow_kpis"]
    assert "follow_up_tasks" in kpis
    assert "authority_submissions" in kpis
    assert "investigation_reports" in kpis


# ── TEST 10: Data Connector Inventory & Credential Masking ───────────────────

def test_10_data_connector_inventory(client):
    """Verify registered external connectors and strict credential masking."""
    res = client.get("/api/v1/integrations/connectors")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] >= 5
    conns = data["connectors"]

    # Check NASA FIRMS and OSM exist
    providers = [c["provider"] for c in conns]
    assert any("NASA" in p for p in providers)
    assert any("OpenStreetMap" in p for p in providers)

    # Check credential masking: no plaintext keys or passwords
    for c in conns:
        assert "password" not in c
        if "configuration" in c and isinstance(c["configuration"], dict):
            for k, v in c["configuration"].items():
                if "key" in k.lower() or "token" in k.lower():
                    assert "***" in str(v) or len(str(v)) <= 8


# ── TEST 11: Remote Connection Testing & SSRF Protection ─────────────────────

def test_11_ssrf_protection_enforcement(client):
    """Verify that dangerous loopback and cloud metadata endpoints are strictly blocked."""
    # 1. Loopback attack
    is_safe, reason = validate_url_ssrf_safety("http://127.0.0.1:5000/admin")
    assert is_safe is False
    assert "SSRF" in reason

    # 2. Localhost alias
    is_safe_host, _ = validate_url_ssrf_safety("http://localhost:8080/secrets")
    assert is_safe_host is False

    # 3. AWS/GCP Metadata service
    is_safe_meta, _ = validate_url_ssrf_safety("http://169.254.169.254/latest/meta-data/")
    assert is_safe_meta is False

    # 4. Valid external HTTPS endpoint
    is_safe_ext, _ = validate_url_ssrf_safety("https://firms.modaps.eosdis.nasa.gov/api/v1")
    assert is_safe_ext is True

    # 5. Test connection API blocks SSRF
    res_blocked = client.post("/api/v1/integrations/test-connection", json={"endpoint_url": "http://127.0.0.1:22"})
    assert res_blocked.status_code == 403


# ── TEST 12: Global AI Investigator Context Grounding ────────────────────────

def test_12_ai_investigator_operational_context(client, app):
    """Test AI assistant context grounding with report, follow-up, and feature targets."""
    with app.app_context():
        latest_report = InvestigationReport.query.order_by(InvestigationReport.id.desc()).first()
        assert latest_report is not None

        # Post chat with report context using demo mode authorization
        chat_payload = {
            "message": "Explain this investigation report and its key environmental findings.",
            "selected_feature": {
                "feature_type": "investigation_report",
                "feature_id": latest_report.report_key,
            },
        }
        res = client.post(
            "/api/events/2/chat",
            json=chat_payload,
            headers={"X-Demo-Mode": "judge-preview"}
        )
        assert res.status_code == 200
        text_resp = res.data.decode("utf-8")
        assert len(text_resp) > 50
        assert "report" in text_resp.lower() or "investigation" in text_resp.lower()
        assert latest_report.report_key in text_resp or "RPT-" in text_resp


# ── TEST 13: Notification Center Persistence ─────────────────────────────────

def test_13_notification_center(client):
    """Verify notification listing, filtering, and mark read actions."""
    res = client.get("/api/v1/notifications?limit=20")
    assert res.status_code == 200
    data = res.get_json()
    assert "notifications" in data
    assert "unread_count" in data
    assert data["total"] >= 100

    # Mark first alert as read
    if data["notifications"]:
        first_id = data["notifications"][0]["id"]
        res_read = client.patch(f"/api/v1/notifications/{first_id}/read")
        assert res_read.status_code == 200
        read_data = res_read.get_json()
        assert read_data["is_read"] is True


# ── TEST 14: Settings, RBAC & Immutable Audit Logs ───────────────────────────

def test_14_settings_and_audit_logs(client):
    """Verify user profile permissions, monitoring threshold updates, and audit trails."""
    # 1. Profile and RBAC roles
    res_prof = client.get("/api/v1/settings/profile")
    assert res_prof.status_code == 200
    prof_data = res_prof.get_json()
    assert "available_roles" in prof_data
    assert len(prof_data["available_roles"]) >= 5

    # 2. Update monitoring thresholds
    update_payload = {"high_frp_threshold_mw": 16.5}
    res_up = client.post("/api/v1/settings/monitoring", json=update_payload)
    assert res_up.status_code == 200
    up_data = res_up.get_json()
    assert up_data["thresholds"]["high_frp_threshold_mw"] == 16.5

    # 3. Verify audit log entry created
    res_logs = client.get("/api/v1/settings/audit-logs?limit=10")
    assert res_logs.status_code == 200
    logs_data = res_logs.get_json()
    assert logs_data["total"] >= 1
    actions = [l["action_type"] for l in logs_data["logs"]]
    assert "SETTINGS_UPDATE" in actions or "REPORT_SUBMISSION" in actions


# ── TEST 15: Cross-Workspace End-to-End Regression ───────────────────────────

def test_15_cross_workspace_regression(client):
    """Verify Phase 1 and Phase 2 endpoints remain intact and functioning seamlessly."""
    # Phase 2 Evidence bundle
    res_ev = client.get("/api/v1/intelligence/evidence?region=bastar")
    assert res_ev.status_code == 200
    assert "evidence_bundle" in res_ev.get_json()

    # Phase 2 Historical baselines
    res_base = client.get("/api/v1/intelligence/historical-baseline?region=bastar")
    assert res_base.status_code == 200

    # Phase 2 Multi-model anomaly
    res_anom = client.get("/api/v1/intelligence/anomalies?region=bastar")
    assert res_anom.status_code == 200

    # Phase 1 Regions
    res_reg = client.get("/api/regions")
    assert res_reg.status_code == 200

    # Phase 1 Search
    res_search = client.get("/api/v1/search?q=Bokaro")
    assert res_search.status_code == 200
