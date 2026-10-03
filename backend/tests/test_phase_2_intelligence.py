"""backend/tests/test_phase_2_intelligence.py
-------------------------------------------
Unit tests for KRATOS V3 Phase 2 Intelligence Services and APIs:
  - Source Classification & 4-Field Intelligence
  - Thermal Analysis Engine (FRP stats, recurrence, baseline leakage protection)
  - Multi-Factor Operational Risk Evaluation & Component Explainability
  - Regulatory & Environmental Compliance Screening
  - REST Intelligence Endpoints
"""

import json
import unittest
from pathlib import Path

from main import create_app
from services.compliance_screening import compliance_screening_engine
from services.risk_evaluation import risk_evaluation_engine
from services.source_classification import source_classification_engine
from services.thermal_analysis import thermal_analysis_engine


class TestPhase2Intelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    # ── 1. Source Classification Engine ───────────────────────────────────────

    def test_source_classification_four_fields(self):
        sample = {
            "thermal_source_id": "test_src_1",
            "region_name": "Singrauli-Sonbhadra",
            "detection_count": 15,
            "max_frp": 85.0,
            "max_frp_ratio": 2.8,
            "persistence_30d_mean": 0.45,
            "distance_to_nearest_facility_m": 0.0,
            "nearest_facility_name": "NTPC Vindhyachal Super Thermal Power",
            "nearest_facility_category": "thermal_power",
        }
        res = source_classification_engine.classify_source_record(sample)
        self.assertIn("mapped_facility_category", res)
        self.assertIn("predicted_source_type", res)
        self.assertIn("thermal_activity_behavior", res)
        self.assertIn("incident_assessment", res)
        self.assertIn("spatial_relationship", res)

        self.assertEqual(res["spatial_relationship"], "direct_intersection")
        self.assertEqual(res["mapped_facility_category"], "Thermal Power Station")
        self.assertEqual(res["predicted_source_type"], "industrial_process_heat")
        self.assertEqual(res["incident_assessment"], "unusual_heat_exceedance")
        self.assertIn("Confidence is a heuristic rule-based rating", res["confidence_calibration_notice"])

    def test_supervised_candidate_evaluation(self):
        eval_res = source_classification_engine.evaluate_supervised_candidates()
        self.assertEqual(eval_res.get("status"), "success")
        self.assertIn("evaluated_models", eval_res)
        self.assertGreaterEqual(len(eval_res["evaluated_models"]), 2)
        self.assertIn("calibration_disclaimer", eval_res)
        self.assertIn("feature_importance_ranking", eval_res)

        # Verify precision, recall, F1 structure
        for m in eval_res["evaluated_models"]:
            self.assertIn("precision", m)
            self.assertIn("recall", m)
            self.assertIn("f1_score", m)
            self.assertIn("confusion_matrix", m)

    # ── 2. Thermal Analysis Engine ────────────────────────────────────────────

    def test_thermal_frp_statistics(self):
        stats = thermal_analysis_engine.get_frp_statistics()
        self.assertGreater(stats.get("count", 0), 100)
        self.assertIn("mean_mw", stats)
        self.assertIn("median_mw", stats)
        self.assertIn("max_mw", stats)
        self.assertIn("p25_mw", stats)
        self.assertIn("p75_mw", stats)
        self.assertIn("iqr_mw", stats)
        self.assertIn("histogram", stats)
        self.assertIn("diurnal_breakdown", stats)
        self.assertGreaterEqual(len(stats["histogram"]), 4)

    def test_recurrence_and_persistence(self):
        stats = thermal_analysis_engine.get_recurrence_and_persistence("dhanbad_bokaro_source_10")
        self.assertEqual(stats.get("status"), "active")
        self.assertGreaterEqual(stats.get("total_detections", 0), 1)
        self.assertIn("active_days_count", stats)
        self.assertIn("detections_per_active_month", stats)

    def test_source_baseline_without_leakage(self):
        # Target timestamp at 2023-06-01
        res = thermal_analysis_engine.compute_source_baseline_without_leakage(
            source_id="dhanbad_bokaro_source_10",
            target_timestamp="2023-06-01T00:00:00Z",
            window_days=60,
        )
        self.assertIn("leakage_protection", res)
        if res.get("baseline_available"):
            self.assertIn("baseline_mean_frp_mw", res)
            self.assertIn("baseline_median_frp_mw", res)

    def test_temporal_trends(self):
        trends = thermal_analysis_engine.get_temporal_trends()
        self.assertIn("monthly_trends", trends)
        self.assertGreater(len(trends["monthly_trends"]), 0)

    # ── 3. Risk Evaluation Engine ─────────────────────────────────────────────

    def test_operational_priority_evaluation(self):
        sample = {
            "source_event_id": "test_ev_999",
            "max_frp": 120.0,
            "max_frp_ratio": 3.8,
            "source_detections_prev_30d": 12,
            "max_iforest_anomaly_score": 0.45,
            "iforest_agreement": True,
            "detection_count": 5,
            "distance_to_nearest_facility_m": 120.0,
            "source_class": "industrial_process_heat",
        }
        eval_out = risk_evaluation_engine.evaluate_operational_priority(sample)

        # 4 distinct outputs
        self.assertIn("anomaly_score", eval_out)
        self.assertIn("source_classification", eval_out)
        self.assertIsNone(eval_out["fire_incident_probability"])
        self.assertIn("fire_probability_disclaimer", eval_out)
        self.assertIn("operational_priority", eval_out)

        op = eval_out["operational_priority"]
        self.assertIn(op["tier"], ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INSUFFICIENT_EVIDENCE"])
        self.assertIn("component_contributions", op)
        self.assertIn("frp_contribution", op["component_contributions"])
        self.assertIn("anomaly_contribution", op["component_contributions"])

    def test_priority_queue(self):
        queue = risk_evaluation_engine.get_priority_queue(limit=10)
        self.assertLessEqual(len(queue), 10)
        if queue:
            self.assertIn("priority_score", queue[0])
            self.assertIn("priority_tier", queue[0])
            self.assertIn("component_contributions", queue[0])
            # Queue must be sorted descending by priority score
            scores = [item["priority_score"] for item in queue]
            self.assertEqual(scores, sorted(scores, reverse=True))

    # ── 4. Compliance Screening Engine ────────────────────────────────────────

    def test_compliance_screening(self):
        res = compliance_screening_engine.screen_facility_compliance(
            facility_name="Bokaro Steel Plant",
            facility_category="Steel & Metallurgy Plant",
            max_frp_ratio=4.2,
            max_frp_mw=95.0,
            distance_m=0.0,
            detection_count=10,
            is_anomaly_flagged=True,
        )
        self.assertEqual(res["screening_status"], "POTENTIAL_COMPLIANCE_CONCERN")
        self.assertIn("STATUTORY NOTICE", res["disclaimer"])
        self.assertIsNotNone(res["applicable_standard"])

        # Clean facility test
        res_clean = compliance_screening_engine.screen_facility_compliance(
            facility_name="Toranagallu Manufacturing",
            facility_category="Industrial Manufacturing Complex",
            max_frp_ratio=1.0,
            max_frp_mw=15.0,
            distance_m=200.0,
            detection_count=5,
        )
        self.assertEqual(res_clean["screening_status"], "NO_CONCERN_IDENTIFIED")

    # ── 5. REST Intelligence Endpoints ────────────────────────────────────────

    def test_source_facility_catalog_endpoint(self):
        resp = self.client.get("/api/v1/intelligence/source-facility/catalog?limit=5")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["count"], 5)
        self.assertIn("mapped_facility_category", data["sources"][0])
        self.assertIn("spatial_relationship", data["sources"][0])

    def test_thermal_analysis_endpoints(self):
        r1 = self.client.get("/api/v1/intelligence/thermal-analysis/stats")
        self.assertEqual(r1.status_code, 200)

        r2 = self.client.get("/api/v1/intelligence/thermal-analysis/trends")
        self.assertEqual(r2.status_code, 200)

    def test_risk_evaluation_endpoints(self):
        r1 = self.client.get("/api/v1/intelligence/risk-evaluation/queue?limit=5")
        self.assertEqual(r1.status_code, 200)

        r2 = self.client.post("/api/v1/intelligence/risk-evaluation/evaluate", json={"max_frp": 50.0, "max_frp_ratio": 2.0})
        self.assertEqual(r2.status_code, 200)
        self.assertIsNone(r2.get_json()["fire_incident_probability"])

    def test_compliance_screening_endpoints(self):
        r1 = self.client.get("/api/v1/intelligence/compliance-screening/standards")
        self.assertEqual(r1.status_code, 200)

        r2 = self.client.post("/api/v1/intelligence/compliance-screening/screen", json={
            "facility_name": "Test Plant",
            "facility_category": "Thermal Power Station",
            "max_frp_ratio": 2.5,
        })
        self.assertEqual(r2.status_code, 200)
        self.assertIn("screening_status", r2.get_json())

    def test_investigations_and_workflow_status_transition(self):
        r1 = self.client.get("/api/v1/intelligence/investigations?limit=5")
        self.assertEqual(r1.status_code, 200)
        invs = r1.get_json()["investigations"]
        self.assertGreaterEqual(len(invs), 1)

        target_id = invs[0]["id"]
        # Transition state
        r2 = self.client.post(f"/api/v1/intelligence/investigations/{target_id}/status", json={
            "status": "Analyst reviewed",
            "notes": "Verified thermal baseline deviation; dispatched for secondary review."
        })
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.get_json()["updated_status"], "Analyst reviewed")

    def test_candidate_model_evaluation_endpoint(self):
        resp = self.client.get("/api/v1/intelligence/model-evaluation")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("calibration_disclaimer", data)


if __name__ == "__main__":
    unittest.main()
