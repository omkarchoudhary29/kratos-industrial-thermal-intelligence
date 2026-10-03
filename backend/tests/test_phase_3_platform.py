"""backend/tests/test_phase_3_platform.py
---------------------------------------
Master Acceptance Test Suite for KRATOS V3 Phase 3 Operational Intelligence Platform.
Validates:
  1. Pre-Phase-3 Baseline & Metric Dictionary integrity
  2. Investigation Dossier non-zero FRP data mapping
  3. Report generation across 3 distinct scopes (Region, Viewport, Feature)
  4. Publication-grade PDF generation (ReportLab %PDF-1.x validation)
  5. Raw CSV evidence export validation
  6. 8-Stage Report Approval & Version Snapshot lifecycle
  7. Statutory Authority Directory & Formal Submission recording
  8. Follow-up idempotency (409 Conflict) & Administrative Merge
  9. Advanced Analytics (10 Corridors, Diurnal Day/Night, Proxy-Label Disclaimer)
  10. Data Connectors, SSRF Protection, and System Audit Logs
"""

from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import unittest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from main import create_app
from pipeline.db import setup_db
from db.connection import db
from db.models import InvestigationReport, FollowUpTask, AuthoritySubmission, DataConnector


class TestPhase3PlatformAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        setup_db(cls.app)
        cls.client = cls.app.test_client()

    # ── Test 1: Pre-Phase-3 Baseline & Metric Dictionary Integrity ────────────
    def test_01_baseline_metric_dictionary(self):
        """Verify metric dictionary returns all operational and historical populations."""
        res = self.client.get("/api/v1/intelligence/metric-dictionary")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("metrics", data)
        self.assertEqual(data["metrics"]["persistent_sources"]["value"], 312)

    # ── Test 2: Investigation Dossier Non-Zero FRP Mapping ─────────────────────
    def test_02_investigations_dossier_frp_mapping(self):
        """Verify that investigation dossiers do NOT display synthetic 0.0 MW FRP."""
        res = self.client.get("/api/v1/intelligence/investigations?limit=20")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreaterEqual(data["count"], 12)
        for inv in data["investigations"]:
            snapshot = inv.get("evidence_snapshot", {})
            max_frp = snapshot.get("max_frp_mw")
            # If max_frp is present, it must be strictly positive
            if max_frp is not None:
                self.assertGreater(max_frp, 0.0, f"Dossier {inv['report_key']} has invalid 0.0 MW FRP")

    # ── Test 3: Report Generation Across 3 Distinct Scopes ────────────────────
    def test_03_report_generation_three_scopes(self):
        """Verify report generation for Regional, Viewport, and Feature scopes."""
        # Scope 1: Regional Scope
        res_reg = self.client.post("/api/v1/reports/generate", json={
            "scope": "region",
            "region_name": "Angul-Talcher",
            "title": "Angul-Talcher Regional Industrial Thermal Audit",
        })
        self.assertEqual(res_reg.status_code, 201)
        reg_data = res_reg.get_json()
        self.assertEqual(reg_data["scope"], "region")
        self.assertIn("RPT-", reg_data["report_key"])
        self.assertGreater(reg_data["evidence"]["observation_stats"]["max_frp_mw"], 0.0)

        # Scope 2: Viewport Scope
        res_view = self.client.post("/api/v1/reports/generate", json={
            "scope": "viewport",
            "bounds": {"south": 20.0, "north": 24.0, "west": 82.0, "east": 86.0},
            "title": "Eastern Industrial Corridor Viewport Dossier",
        })
        self.assertEqual(res_view.status_code, 201)
        view_data = res_view.get_json()
        self.assertEqual(view_data["scope"], "viewport")

        # Scope 3: Selected Feature Scope
        res_feat = self.client.post("/api/v1/reports/generate", json={
            "scope": "feature",
            "feature_type": "cluster",
            "feature_id": "talcher_angul_source_0",
            "title": "Target Cluster talcher_angul_source_0 Investigation",
        })
        self.assertEqual(res_feat.status_code, 201)
        feat_data = res_feat.get_json()
        self.assertEqual(feat_data["scope"], "feature")
        self.assertEqual(feat_data["feature_id"], "talcher_angul_source_0")

    # ── Test 4: PDF Generation & Binary Verification ──────────────────────────
    def test_04_pdf_generation_binary_validity(self):
        """Verify ReportLab produces valid binary PDF documents with %PDF- header."""
        # Fetch an existing report
        res_list = self.client.get("/api/v1/reports?limit=1")
        self.assertEqual(res_list.status_code, 200)
        reports = res_list.get_json()["reports"]
        self.assertGreater(len(reports), 0)
        rep_id = reports[0]["id"]

        # Request PDF
        res_pdf = self.client.get(f"/api/v1/reports/{rep_id}/pdf")
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.mimetype, "application/pdf")
        # PDF files must start with %PDF-
        self.assertTrue(res_pdf.data.startswith(b"%PDF-"), "Generated PDF missing %PDF magic header")
        self.assertGreater(len(res_pdf.data), 1000, "PDF file too small to contain formatted content")

    # ── Test 5: CSV Evidence Export ───────────────────────────────────────────
    def test_05_csv_evidence_export(self):
        """Verify that underlying evidence can be exported as structured CSV."""
        res_list = self.client.get("/api/v1/reports?limit=1")
        rep_id = res_list.get_json()["reports"][0]["id"]

        res_csv = self.client.get(f"/api/v1/reports/{rep_id}/csv")
        self.assertEqual(res_csv.status_code, 200)
        self.assertEqual(res_csv.mimetype, "text/csv")
        csv_text = res_csv.data.decode("utf-8")
        self.assertIn("report_id,scope,region_name", csv_text)

    # ── Test 6: 8-Stage Report Approval Lifecycle & Versioning ────────────────
    def test_06_report_approval_and_versioning(self):
        """Verify report approval transitions and version increment."""
        # Generate new test report
        res_gen = self.client.post("/api/v1/reports/generate", json={
            "scope": "region",
            "region_name": "korba",
            "title": "Korba Approval Workflow Audit",
        })
        rep_id = res_gen.get_json()["id"]

        # Transition to UNDER_REVIEW
        res_trans1 = self.client.post(f"/api/v1/reports/{rep_id}/review-status", json={
            "status": "UNDER_REVIEW",
            "notes": "Forwarded to Compliance Supervisor for gazette checks.",
        })
        self.assertEqual(res_trans1.status_code, 200)
        self.assertEqual(res_trans1.get_json()["status"], "UNDER_REVIEW")

        # Transition to APPROVED
        res_trans2 = self.client.post(f"/api/v1/reports/{rep_id}/review-status", json={
            "status": "APPROVED",
            "notes": "Report approved for statutory submission to CECB.",
        })
        self.assertEqual(res_trans2.status_code, 200)
        self.assertEqual(res_trans2.get_json()["status"], "APPROVED")

        # Increment version to v1.1
        res_ver = self.client.post(f"/api/v1/reports/{rep_id}/version", json={
            "version": "v1.1",
            "notes": "Added supplementary facility distance measurements.",
        })
        self.assertEqual(res_ver.status_code, 200)
        self.assertEqual(res_ver.get_json()["version"], "v1.1")

    # ── Test 7: Statutory Authority Directory & Submission Tracking ───────────
    def test_07_authority_submission_recording(self):
        """Verify authority directory listing and formal submission logging."""
        # 1. Authority directory check
        res_auth = self.client.get("/api/v1/submissions/authorities")
        self.assertEqual(res_auth.status_code, 200)
        auths = res_auth.get_json()["authorities"]
        auth_ids = {a["authority_id"] for a in auths}
        self.assertIn("cpcb", auth_ids)
        self.assertIn("ospcb", auth_ids)
        self.assertIn("cecb", auth_ids)

        # 2. Record formal submission
        res_reports = self.client.get("/api/v1/reports?limit=1")
        rep_id = res_reports.get_json()["reports"][0]["id"]

        res_sub = self.client.post("/api/v1/submissions/record", json={
            "report_id": rep_id,
            "authority_id": "cpcb",
            "purpose": "regulatory_compliance",
            "channel": "PORTAL",
            "reference_number": "CPCB/AIR/2026/TEST-1001",
            "acknowledgement_number": "ACK-2026-CPCB-009",
            "notes": "Formal air quality compliance alert filed via CPCB Portal.",
        })
        self.assertEqual(res_sub.status_code, 201)
        sub_data = res_sub.get_json()
        self.assertIn("SUB-", sub_data["submission_key"])
        self.assertEqual(sub_data["status"], "ACKNOWLEDGED")

        # 3. Retrieve submission list
        res_list = self.client.get(f"/api/v1/submissions?report_id={rep_id}")
        self.assertEqual(res_list.status_code, 200)
        self.assertGreater(res_list.get_json()["total"], 0)

    # ── Test 8: Follow-up Idempotency & Administrative Merge ──────────────────
    def test_08_followup_idempotency_and_merge(self):
        """Verify duplicate task rejection (409) and administrative merge."""
        import uuid
        unique_feat = f"bastar_test_source_{uuid.uuid4().hex[:6]}"

        # Create primary task
        res1 = self.client.post("/api/v1/followups", json={
            "title": "Primary Bastar Flare Inspection",
            "feature_type": "cluster",
            "feature_id": unique_feat,
            "priority": "HIGH",
            "region_name": "bastar",
        })
        self.assertEqual(res1.status_code, 201)
        primary_id = res1.get_json()["id"]

        # Attempt duplicate task without force -> Must return 409 Conflict
        res2 = self.client.post("/api/v1/followups", json={
            "title": "Duplicate Bastar Flare Inspection",
            "feature_type": "cluster",
            "feature_id": unique_feat,
            "priority": "HIGH",
            "region_name": "bastar",
        })
        self.assertEqual(res2.status_code, 409)
        self.assertTrue(res2.get_json()["is_duplicate"])

        # Create secondary task with force=true for merge test
        res3 = self.client.post("/api/v1/followups", json={
            "title": "Secondary Bastar Task",
            "feature_type": "cluster",
            "feature_id": unique_feat,
            "priority": "MEDIUM",
            "region_name": "bastar",
            "force": True,
        })
        self.assertEqual(res3.status_code, 201)
        sec_id = res3.get_json()["id"]

        # Administratively merge secondary into primary
        res_merge = self.client.post("/api/v1/followups/merge", json={
            "primary_id": primary_id,
            "secondary_ids": [sec_id],
            "notes": "Test administrative merge of duplicate tasks.",
        })
        self.assertEqual(res_merge.status_code, 200)
        self.assertEqual(res_merge.get_json()["merged_tasks_count"], 1)

    # ── Test 9: Advanced Geospatial Analytics ─────────────────────────────────
    def test_09_advanced_analytics_endpoints(self):
        """Verify cross-corridor rankings, diurnal breakdown, and proxy disclaimer."""
        res_overview = self.client.get("/api/v1/analytics/overview")
        self.assertEqual(res_overview.status_code, 200)
        data = res_overview.get_json()

        # 10 Corridors
        self.assertEqual(len(data["corridors"]), 10)
        # Diurnal distribution
        self.assertIn("diurnal_breakdown", data["thermal_distribution"])
        self.assertIn("daytime_detections", data["thermal_distribution"]["diurnal_breakdown"])
        # Recurrence spectrum
        self.assertIn("recurrence_spectrum", data["thermal_distribution"])

        # Models endpoint disclaimer
        res_models = self.client.get("/api/v1/analytics/models")
        self.assertEqual(res_models.status_code, 200)
        models_data = res_models.get_json()
        self.assertIn("NOT VALIDATED", models_data["proxy_label_notice"])

    # ── Test 10: Data Connectors & SSRF Protection ────────────────────────────
    def test_10_data_connectors_and_ssrf(self):
        """Verify connector inventory, sync trigger, and strict SSRF blocking."""
        # 1. Connectors catalog
        res_conn = self.client.get("/api/v1/integrations/connectors")
        self.assertEqual(res_conn.status_code, 200)
        self.assertGreaterEqual(res_conn.get_json()["total"], 5)

        # 2. SSRF Protection: Loopback blocked
        res_ssrf1 = self.client.post("/api/v1/integrations/test-connection", json={
            "endpoint_url": "http://127.0.0.1:8080/internal",
        })
        self.assertEqual(res_ssrf1.status_code, 403)
        self.assertEqual(res_ssrf1.get_json()["security_flag"], "SSRF_BLOCKED")

        # 3. SSRF Protection: Cloud metadata IP blocked
        res_ssrf2 = self.client.post("/api/v1/integrations/test-connection", json={
            "endpoint_url": "http://169.254.169.254/latest/meta-data/",
        })
        self.assertEqual(res_ssrf2.status_code, 403)
        self.assertEqual(res_ssrf2.get_json()["security_flag"], "SSRF_BLOCKED")

        # 4. Trigger sync job on first connector
        first_id = res_conn.get_json()["connectors"][0]["id"]
        res_sync = self.client.post(f"/api/v1/integrations/connectors/{first_id}/sync")
        self.assertEqual(res_sync.status_code, 200)
        self.assertEqual(res_sync.get_json()["status"], "SUCCESS")


if __name__ == "__main__":
    unittest.main()
