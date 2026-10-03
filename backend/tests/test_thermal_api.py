from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from main import create_app
from pipeline.db import setup_db


class ThermalAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        setup_db(cls.app)
        cls.client = cls.app.test_client()

    def test_health_check(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")

    def test_thermal_stats_endpoint(self):
        res = self.client.get("/api/v1/thermal/stats")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("total_events", data)
        self.assertIn("high_events", data)
        self.assertIn("critical_events", data)

    def test_thermal_events_list(self):
        res = self.client.get("/api/v1/thermal/events?limit=10")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("events", data)
        self.assertLessEqual(len(data["events"]), 10)

    def test_thermal_map_endpoint(self):
        res = self.client.get("/api/v1/thermal/map?limit=10")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("events", data)
        self.assertLessEqual(len(data["events"]), 10)

    def test_thermal_sources_endpoint(self):
        res = self.client.get("/api/v1/thermal/sources?limit=10")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("sources", data)
        self.assertLessEqual(len(data["sources"]), 10)

    def test_ml_evaluation_endpoint(self):
        res = self.client.get("/api/v1/thermal/ml-evaluation")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("model_metadata", data)
        self.assertIn("operational_agreement_metrics", data)
        self.assertIn("regional_performance", data)
        self.assertIn("score_distribution", data)

    def test_regions_catalog(self):
        res = self.client.get("/api/regions/")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreaterEqual(len(data), 10)

    def test_fires_status(self):
        res = self.client.get("/api/fires/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("model_version", data)


if __name__ == "__main__":
    unittest.main()
