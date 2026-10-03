"""Phase A validation tests: OSM facilities API, spatial clustering, and pipeline status."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from sqlalchemy import text

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from main import create_app
from db.connection import db


class PhaseAValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_osm_categories_endpoint(self):
        res = self.client.get("/api/v1/osm/categories")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("categories", data)
        categories = {c["category"]: c["count"] for c in data["categories"]}
        self.assertIn("industrial", categories)
        self.assertGreater(categories["industrial"], 0)

    def test_osm_facilities_geojson_endpoint(self):
        res = self.client.get("/api/v1/osm/facilities?limit=10")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("type"), "FeatureCollection")
        self.assertIn("features", data)
        self.assertGreater(data.get("total", 0), 0)
        self.assertLessEqual(len(data["features"]), 10)

        # Inspect GeoJSON schema
        feat = data["features"][0]
        self.assertEqual(feat["type"], "Feature")
        self.assertIn("geometry", feat)
        self.assertIn("type", feat["geometry"])
        self.assertIn("coordinates", feat["geometry"])
        self.assertIn("properties", feat)
        props = feat["properties"]
        self.assertIn("osm_id", props)
        self.assertIn("osm_type", props)
        self.assertIn("facility_category", props)

    def test_osm_facilities_filter_by_region(self):
        res = self.client.get("/api/v1/osm/facilities?region_id=7&limit=5")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("type"), "FeatureCollection")
        self.assertGreater(data.get("total", 0), 0)
        for feat in data["features"]:
            self.assertEqual(feat["properties"]["region_id"], 7)

    def test_osm_facilities_filter_by_category(self):
        res = self.client.get("/api/v1/osm/facilities?category=refinery")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreaterEqual(data.get("total", 0), 2)
        names = [f["properties"]["name"] for f in data["features"]]
        self.assertTrue(any("Reliance" in n for n in names))

    def test_thermal_pipeline_status_endpoint(self):
        res = self.client.get("/api/v1/thermal/pipeline/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("status", data)
        self.assertIn("audit", data)
        audit = data["audit"]
        self.assertIn("total_osm_facilities", audit)
        self.assertGreaterEqual(audit["total_osm_facilities"], 2000)

    def test_source_clusters_view_metric_dbscan(self):
        with self.app.app_context():
            res = db.session.execute(text("""
                SELECT COUNT(*) AS total_points,
                       COUNT(DISTINCT cluster_id) FILTER (WHERE cluster_id IS NOT NULL) AS cluster_count
                FROM source_clusters;
            """)).mappings().first()
            self.assertIsNotNone(res)
            self.assertGreater(res["total_points"], 0)
            self.assertGreater(res["cluster_count"], 0)


if __name__ == "__main__":
    unittest.main()
