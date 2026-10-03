"""backend/tests/test_final_hardening.py
--------------------------------------
Comprehensive Scientific Integrity & Acceptance Hardening Tests for KRATOS V3 Phase 2.

Covers:
  - Part 2: Complete Data & KPI Reconciliation across all 9 populations
  - Part 3: Spatial Association Tiers & Mutual Exclusivity (Sum = 312)
  - Part 4: FRP Descriptive Statistics & Diurnal Distribution
  - Part 5: ML Evaluation Audit, Feature Leakage & Proxy-Label Notice
  - Part 6: Operational Priority Formula Bounds & Sensitivity Scenarios
  - Part 8: Regulatory Provenance Register & Stack Concentration Disclaimers
  - Part 9: AI Investigator Evidence Grounding & Integrity Safeguards
"""

import json
import unittest
from pathlib import Path

from main import create_app
from services.compliance_screening import compliance_screening_engine
from services.metric_dictionary import get_metric_definition, get_metric_dictionary
from services.risk_evaluation import risk_evaluation_engine
from services.source_classification import source_classification_engine
from services.thermal_analysis import thermal_analysis_engine


class TestPhase2FinalHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    # ── 1. Part 2: Metric Dictionary & 9 Populations Reconciliation ───────────

    def test_01_metric_dictionary_populations(self):
        """Verify all 9 operational and historical populations in central dictionary."""
        res = get_metric_dictionary()
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["total_populations"], 9)
        metrics = res["metrics"]

        # 1. Archived Detections: 8,891
        self.assertEqual(metrics["archived_detections"]["value"], 8891)
        self.assertIn("final_fused_events.parquet", metrics["archived_detections"]["source"])

        # 2. Persistent Sources: 312
        self.assertEqual(metrics["persistent_sources"]["value"], 312)
        self.assertIn("thermal_sources.parquet", metrics["persistent_sources"]["source"])

        # 3. View Pagination Limit: 100
        self.assertEqual(metrics["view_pagination_limit"]["value"], 100)

        # 4. High / Critical Priority Alerts: 113
        self.assertEqual(metrics["high_critical_alerts"]["value"], 113)

        # 5. Active Investigation Dossiers: 12
        self.assertEqual(metrics["active_investigation_dossiers"]["value"], 12)

        # 6. Isolation Forest Anomaly Outputs: 196
        self.assertEqual(metrics["isolation_forest_anomalies"]["value"], 196)

        # 7. Active Follow-up Tasks: 6
        self.assertEqual(metrics["active_follow_up_tasks"]["value"], 6)

        # 8. Mapped OSM Facilities: 2,423
        self.assertEqual(metrics["mapped_osm_facilities"]["value"], 2423)

        # 9. Database Fire Detections: 853
        self.assertEqual(metrics["database_fire_detections"]["value"], 853)

        # Test single metric lookup
        single = get_metric_definition("persistent_sources")
        self.assertEqual(single["status"], "success")
        self.assertEqual(single["metric"]["value"], 312)

    def test_02_metric_dictionary_api_endpoints(self):
        """Test GET /api/v1/intelligence/metric-dictionary endpoints."""
        res = self.client.get("/api/v1/intelligence/metric-dictionary")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["total_populations"], 9)

        res_single = self.client.get("/api/v1/intelligence/metric-dictionary/archived_detections")
        self.assertEqual(res_single.status_code, 200)
        self.assertEqual(res_single.get_json()["metric"]["value"], 8891)

    # ── 2. Part 3: Spatial Association Tiers (Sum = 312) ──────────────────────

    def test_03_spatial_association_mutually_exclusive_sum_312(self):
        """Verify that mutually exclusive spatial tiers partition the 312 sources exactly to 312."""
        summary = source_classification_engine._load_association_summary()
        exclusive = summary["persistent_sources"]["mutually_exclusive_tiers"]
        distance = summary["persistent_sources"]["distance_based_tiers"]
        overlap = summary["persistent_sources"]["ambiguous_overlap"]

        # Mutually exclusive tiers: 25 + 17 + 123 + 8 + 139 = 312
        self.assertEqual(exclusive["direct_intersection"], 25)
        self.assertEqual(exclusive["strong_association"], 17)
        self.assertEqual(exclusive["nearby_proximity"], 123)
        self.assertEqual(exclusive["ambiguous"], 8)
        self.assertEqual(exclusive["unassociated"], 139)
        self.assertEqual(sum(exclusive.values()), 312)

        # Distance-based tiers: 31 + 19 + 44 + 79 + 139 = 312
        self.assertEqual(distance["direct_intersection"], 31)
        self.assertEqual(distance["strong_association"], 19)
        self.assertEqual(distance["nearby_1000m"], 44)
        self.assertEqual(distance["nearby_2000m"], 79)
        self.assertEqual(distance["unmatched"], 139)
        self.assertEqual(sum(distance.values()), 312)

        # Ambiguous breakdown: 8 total (6 in direct intersection + 2 in strong association)
        self.assertEqual(overlap["total_ambiguous_300m"], 8)
        self.assertEqual(overlap["direct_intersection_overlap"], 6)
        self.assertEqual(overlap["strong_association_overlap"], 2)

    def test_04_source_catalog_reconciliation_api(self):
        """Verify /source-facility/catalog API reports exact 312 sum check."""
        res = self.client.get("/api/v1/intelligence/source-facility/catalog?limit=10")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["total_persistent_sources"], 312)
        self.assertEqual(data["sum_check_mutually_exclusive"], 312)
        self.assertEqual(data["sum_check_distance_based"], 312)
        self.assertEqual(data["facility_association_summary"]["ambiguous"], 8)

    # ── 3. Part 4: FRP Descriptive Statistics Audit ───────────────────────────

    def test_05_frp_descriptive_statistics_and_diurnal(self):
        """Verify descriptive FRP statistics calculation on 8,891 events."""
        stats = thermal_analysis_engine.get_frp_statistics()
        self.assertEqual(stats["count"], 8891)
        self.assertAlmostEqual(stats["mean_mw"], 5.55, places=1)
        self.assertAlmostEqual(stats["median_mw"], 4.95, places=1)
        self.assertAlmostEqual(stats["iqr_mw"], 3.55, places=1)
        self.assertAlmostEqual(stats["max_mw"], 92.89, places=1)
        self.assertAlmostEqual(stats["std_mw"], 3.39, places=1)

        # 6 Bins
        self.assertEqual(len(stats["histogram"]), 6)
        hist_sum = sum(b["count"] for b in stats["histogram"])
        self.assertEqual(hist_sum, 8891)

        # Diurnal distribution
        diurnal = stats["diurnal_breakdown"]
        self.assertEqual(diurnal["daytime_overpasses"] + diurnal["nighttime_overpasses"], 8891)
        self.assertGreater(diurnal["daytime_overpasses"], 5000)

    # ── 4. Part 5: ML Evaluation Audit & Feature Leakage ──────────────────────

    def test_06_candidate_model_evaluation_proxy_label_notice(self):
        """Verify supervised candidate evaluation outputs explicit proxy-label and uncalibrated notices."""
        res = self.client.get("/api/v1/intelligence/model-evaluation")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")

        # Explicit scientific honesty assertions
        self.assertIn("Operational Screening Priority Tier", data["target_class_definition"])
        self.assertEqual(
            data["fire_incident_prediction_validation"],
            "NOT VALIDATED — INDEPENDENT INCIDENT GROUND TRUTH UNAVAILABLE"
        )
        self.assertEqual(data["target_type"], "proxy_operational_screening_rule")
        self.assertIn("feature_leakage_note", data)
        self.assertIn("calibration_disclaimer", data)
        self.assertIn("uncalibrated_probability_notice", data)

    # ── 5. Part 6: Operational Priority Formula Bounds & Sensitivity ──────────

    def test_07_operational_priority_formula_bounds_and_contributions(self):
        """Verify priority formula boundedness [0, 1] and explainable weights."""
        event_sample = {
            "max_frp_ratio": 3.8,
            "max_source_anomaly_score": -0.45,
            "source_detections_prev_30d": 15,
            "detection_count": 8,
            "distance_to_nearest_facility_m": 0.0,
        }
        res = risk_evaluation_engine.evaluate_operational_priority(event_sample)
        op = res["operational_priority"]

        # Mathematical Boundedness
        self.assertGreaterEqual(op["score"], 0.0)
        self.assertLessEqual(op["score"], 1.0)
        self.assertEqual(op["tier"], "CRITICAL")
        self.assertEqual(op["boundedness_guarantee"], "[0.0, 1.0] strictly enforced")

        # Explainable component breakdown
        contrib = op["component_contributions"]
        self.assertEqual(contrib["frp_exceedance_weight"], 0.35)
        self.assertEqual(contrib["persistence_weight"], 0.25)
        self.assertEqual(contrib["anomaly_weight"], 0.25)
        self.assertEqual(contrib["proximity_weight"], 0.15)
        self.assertIn("proximity_role", contrib)

    def test_08_priority_formula_sensitivity_cases(self):
        """Test sensitivity cases: stable high flare, isolated spike, forest hotspot, sparse data."""
        # Case 1: High FRP stable source (FRP ratio = 1.0, high detections)
        stable_flare = {
            "max_frp_ratio": 1.0,
            "max_source_anomaly_score": 0.0,
            "source_detections_prev_30d": 25,
            "detection_count": 25,
            "distance_to_nearest_facility_m": 150.0,
        }
        res_stable = risk_evaluation_engine.evaluate_operational_priority(stable_flare)
        self.assertIn(res_stable["operational_priority"]["tier"], ["LOW", "MEDIUM"])

        # Case 2: Sudden FRP spike on industrial source
        spike = {
            "max_frp_ratio": 4.5,
            "max_source_anomaly_score": -0.60,
            "source_detections_prev_30d": 12,
            "detection_count": 10,
            "distance_to_nearest_facility_m": 0.0,
        }
        res_spike = risk_evaluation_engine.evaluate_operational_priority(spike)
        self.assertEqual(res_spike["operational_priority"]["tier"], "CRITICAL")

        # Case 3: Sparse observation (<2 detections) -> INSUFFICIENT_EVIDENCE
        sparse = {
            "max_frp_ratio": 1.0,
            "max_source_anomaly_score": 0.0,
            "detection_count": 1,
            "distance_to_nearest_facility_m": 500.0,
        }
        res_sparse = risk_evaluation_engine.evaluate_operational_priority(sparse)
        self.assertEqual(res_sparse["operational_priority"]["tier"], "INSUFFICIENT_EVIDENCE")

        # Case 4: Missing facility data -> gracefully handles None
        no_fac = {
            "max_frp_ratio": 2.2,
            "max_source_anomaly_score": -0.20,
            "detection_count": 5,
            "distance_to_nearest_facility_m": None,
        }
        res_no_fac = risk_evaluation_engine.evaluate_operational_priority(no_fac)
        self.assertGreaterEqual(res_no_fac["operational_priority"]["score"], 0.0)

    # ── 6. Part 8: Regulatory Provenance & Stack Disclaimers ───────────────────

    def test_09_regulatory_provenance_register(self):
        """Verify statutory gazette citations, verification status, and stack disclaimers."""
        standards = compliance_screening_engine.get_standards_catalog()
        self.assertEqual(len(standards), 5)

        for std in standards:
            self.assertEqual(std["verification_status"], "VERIFIED_ACTIVE")
            self.assertIn("gazette_notification", std)
            self.assertIn("notification_date", std)
            self.assertIn("stack_concentration_notice", std)
            self.assertIn("regulatory_authority", std)

        # Thermal power standard verification
        tp = compliance_screening_engine.match_sector_standard("Thermal Power Station")
        self.assertIn("S.O. 3305(E)", tp["gazette_notification"])

        # Petroleum refinery flaring standard verification
        ref = compliance_screening_engine.match_sector_standard("Petroleum & Chemical Refinery")
        self.assertIn("G.S.R. 186(E)", ref["gazette_notification"])

        # Steel plant standard verification
        steel = compliance_screening_engine.match_sector_standard("Steel & Metallurgy Plant")
        self.assertIn("G.S.R. 277(E)", steel["gazette_notification"])

        # Coal mining standard verification
        coal = compliance_screening_engine.match_sector_standard("Coal Mine & Handling Yard")
        self.assertIn("Coal Mines Regulations, 2017", coal["statutory_source"])

        # Forest / Eco-Sensitive Zone verification
        forest = compliance_screening_engine.match_sector_standard("Forest Landscape & Canopy")
        self.assertIn("Wildlife (Protection) Act, 1972", forest["statutory_source"])

    def test_10_compliance_screening_stack_concentration_disclaimer(self):
        """Verify compliance screening result contains statutory stack disclaimer."""
        res = compliance_screening_engine.screen_facility_compliance(
            facility_name="Bokaro Steel Plant",
            facility_category="Steel & Metallurgy Plant",
            max_frp_ratio=3.8,
            max_frp_mw=95.0,
            distance_m=0.0,
            detection_count=15,
            is_anomaly_flagged=True,
        )
        self.assertEqual(res["screening_status"], "POTENTIAL_COMPLIANCE_CONCERN")
        self.assertIn("Satellite Fire Radiative Power (FRP) measures radiative energy dissipation", res["legal_disclaimer"])
        self.assertIn("NOT stack particulate", res["legal_disclaimer"])


if __name__ == "__main__":
    unittest.main()
