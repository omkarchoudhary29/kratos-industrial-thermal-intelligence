from __future__ import annotations

import sys
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from services.firms_ingestion_service import MODEL_FEATURES, validate_model_schema
from services.ml_evaluation import ml_evaluation_service
from pipeline.thermal.classification import classify_thermal_source


class MLPipelineTests(unittest.TestCase):
    def test_model_artifact_features_match_constants(self):
        validated = validate_model_schema()
        self.assertEqual(tuple(validated), MODEL_FEATURES)
        self.assertEqual(len(MODEL_FEATURES), 16)

    def test_isolation_forest_pipeline_inference(self):
        metrics = ml_evaluation_service.get_evaluation_metrics()
        meta = metrics["model_metadata"]
        self.assertTrue(meta["loaded"])
        self.assertEqual(meta["feature_count"], 16)
        self.assertEqual(meta["contamination"], 0.02)

    def test_score_distribution_bounds(self):
        metrics = ml_evaluation_service.get_evaluation_metrics()
        dist = metrics["score_distribution"]
        if dist["count"] > 0:
            self.assertGreaterEqual(dist["min"], 0.0)
            self.assertLessEqual(dist["max"], 1.0)
            self.assertGreater(dist["mean"], 0.5)

    def test_source_classification_rules(self):
        # Industrial fire scenario
        industrial_row = pd.Series({
            "frp": 150.0,
            "max_frp": 150.0,
            "source_baseline_frp": 30.0,
            "frp_peak_ratio": 5.0,
            "landcover_group": "built_up",
            "landcover_class": "built_up",
            "inside_industrial_polygon": True,
            "near_industrial_facility": True,
            "distance_to_nearest_industry_m": 50.0,
            "unique_active_days": 1,
            "active_duration_days": 1.0,
        })
        cls, conf = classify_thermal_source(industrial_row)
        self.assertIn(cls, ["industrial_fire", "industrial_process_heat", "gas_flare"])

        # Wildfire forest scenario
        wildfire_row = pd.Series({
            "frp": 45.0,
            "source_baseline_frp": 0.0,
            "max_frp": 45.0,
            "landcover_group": "vegetation",
            "landcover_class": "tree_cover",
            "forest_fraction_500m": 0.85,
            "inside_industrial_polygon": False,
            "near_industrial_facility": False,
            "distance_to_nearest_industry_m": 8000.0,
            "unique_active_days": 1,
            "active_duration_days": 1.0,
        })
        cls_wf, conf_wf = classify_thermal_source(wildfire_row)
        self.assertEqual(cls_wf, "wildfire")


if __name__ == "__main__":
    unittest.main()
