"""backend/tests/test_enhancement_phase2.py
-----------------------------------------
Automated Verification Suite for KRATOS V3.1 Enhancement Phase 2:
  - Test A: Feature Evidence Bundle Schema & Key Verification
  - Test B: Multi-Level Historical Baseline Calculation (Levels 1-4)
  - Test C: Baseline Maturity & Data Sufficiency Tiers
  - Test D: Point-in-Time Baseline Filtering (Leakage Prevention)
  - Test E: Multi-Model Anomaly Detection & Agreement Consensus
  - Test F: 10-Class Industrial Taxonomy & Engineering References
  - Test G: Source Classification Abstention Protocol
  - Test H: Honest Ground-Truth Policy & Probability Withholding
  - Test I: De-duplicated Operational Priority Engine & Bound Verification
  - Test J: REST API Intelligence Endpoints Verification
"""

import math
import pytest
from datetime import datetime, timezone
import pandas as pd

from services.baseline_engine import baseline_engine
from services.facility_intelligence import facility_intelligence
from services.multi_model_anomaly import multi_model_anomaly
from services.operational_priority_engine import operational_priority_engine
from services.source_classification import source_classification_engine
from services.evidence_enrichment import evidence_enrichment_engine


# ── TEST A: Feature Evidence Bundle Schema ────────────────────────────────────
def test_a_evidence_bundle_schema():
    bundle = evidence_enrichment_engine.build_evidence_bundle(
        region_name="dhanbad_bokaro",
        latitude=23.79,
        longitude=86.43,
        observed_frp=35.0,
    )
    expected_top_keys = [
        "feature_identity",
        "satellite_observations",
        "facility_context",
        "historical_baselines",
        "environmental_context",
        "incident_ground_truth",
        "multi_model_anomaly",
        "source_classification",
        "operational_priority",
        "scientific_distinction",
        "explainable_summary",
        "data_gaps",
    ]
    for key in expected_top_keys:
        assert key in bundle, f"Missing key '{key}' in evidence bundle"

    assert bundle["feature_identity"]["region_name"] == "dhanbad_bokaro"
    assert bundle["satellite_observations"]["observed_frp_mw"] == 35.0
    assert "active_maturity_tier" in bundle["historical_baselines"]
    assert "consensus" in bundle["multi_model_anomaly"]
    assert "operational_priority_score" in bundle["operational_priority"]


# ── TEST B: Multi-Level Historical Baseline Calculation ───────────────────────
def test_b_multilevel_historical_baselines():
    # Test regional baseline level 4
    res = baseline_engine.get_multi_level_baseline(
        region_name="dhanbad_bokaro",
        observed_frp=40.0,
    )
    assert res["level_4_regional"] is not None
    stats = res["level_4_regional"]["statistics"]
    assert stats["sample_size"] > 100
    assert stats["median"] is not None
    assert stats["mad"] is not None
    assert stats["p25"] <= stats["median"] <= stats["p75"] <= stats["p95"] <= stats["p99"]

    dev = res["level_4_regional"]["deviation"]
    assert dev["ratio_to_median"] is not None
    assert dev["mad_zscore"] is not None
    assert dev["reliability_flag"] in ("statistically_sound", "preliminary_caution")


# ── TEST C: Baseline Maturity & Data Sufficiency Tiers ────────────────────────
def test_c_baseline_maturity_tiers():
    assert baseline_engine.get_maturity_tier(0)[0] == "insufficient"
    assert baseline_engine.get_maturity_tier(4)[0] == "insufficient"
    assert baseline_engine.get_maturity_tier(5)[0] == "preliminary"
    assert baseline_engine.get_maturity_tier(14)[0] == "preliminary"
    assert baseline_engine.get_maturity_tier(15)[0] == "developing"
    assert baseline_engine.get_maturity_tier(29)[0] == "developing"
    assert baseline_engine.get_maturity_tier(30)[0] == "mature"
    assert baseline_engine.get_maturity_tier(500)[0] == "mature"

    # Robust stats with insufficient sample size
    insuf_stats = baseline_engine.calculate_robust_stats([10.0, 12.0, 15.0])
    assert insuf_stats["maturity_tier"] == "insufficient"
    dev_insuf = baseline_engine.compute_deviation(25.0, insuf_stats)
    assert dev_insuf["reliability_flag"] == "withheld_insufficient_samples"
    assert dev_insuf["ratio_to_median"] is None


# ── TEST D: Point-in-Time Baseline Filtering ─────────────────────────────────
def test_d_point_in_time_filtering():
    # Cutoff at early 2022
    early_cutoff = datetime(2022, 1, 1, tzinfo=timezone.utc)
    res_early = baseline_engine.get_multi_level_baseline(
        region_name="dhanbad_bokaro",
        point_in_time=early_cutoff,
        observed_frp=20.0,
    )
    # Cutoff at late 2024
    late_cutoff = datetime(2024, 12, 31, tzinfo=timezone.utc)
    res_late = baseline_engine.get_multi_level_baseline(
        region_name="dhanbad_bokaro",
        point_in_time=late_cutoff,
        observed_frp=20.0,
    )
    n_early = res_early["level_4_regional"]["statistics"]["sample_size"]
    n_late = res_late["level_4_regional"]["statistics"]["sample_size"]
    assert n_early < n_late, f"Point-in-time failed: n_early ({n_early}) >= n_late ({n_late})"


# ── TEST E: Multi-Model Thermal Anomaly Detection ─────────────────────────────
def test_e_multi_model_anomaly_detection():
    # Test high excursion trigger
    feats = {
        "max_frp": 85.0,
        "frp": 85.0,
        "max_iforest_anomaly_score": -0.22,
        "frp_mean_24h": 65.0,
        "frp_max_24h": 85.0,
        "brightness_mean_24h": 365.0,
        "brightness_max_24h": 375.0,
    }
    stats = {
        "sample_size": 40,
        "median": 8.0,
        "mad": 2.5,
        "p95": 20.0,
        "p99": 35.0,
    }
    recent_frps = [10.0, 14.0, 30.0, 55.0, 85.0]
    res = multi_model_anomaly.evaluate_all(feats, stats, recent_series=recent_frps)

    consensus = res["consensus"]
    assert consensus["total_models"] == 3
    assert 0.0 <= consensus["agreement_score"] <= 1.0
    assert consensus["verdict"] in ("STRONG_ANOMALY", "MODERATE_ANOMALY", "WEAK_ANOMALY", "NORMAL_BASELINE")
    assert res["model_2_statistical_deviation"]["is_anomaly"] is True
    assert res["model_3_cusum_change"]["is_anomaly"] is True


# ── TEST F: 10-Class Industrial Taxonomy Mapping ──────────────────────────────
def test_f_industrial_taxonomy_mapping():
    # Steel check
    t_steel = facility_intelligence.map_taxonomy_category("industrial", "blast_furnace", "Bokaro Steel Works")
    assert t_steel["taxonomy_key"] == "steel_metallurgical"
    assert "Blast Furnace" in t_steel["typical_equipment"]

    # Power plant check
    t_power = facility_intelligence.map_taxonomy_category("power_plant", "coal", "NTPC Thermal Power Station")
    assert t_power["taxonomy_key"] == "thermal_power_generation"

    # Cement check
    t_cement = facility_intelligence.map_taxonomy_category("industrial", "kiln", "UltraTech Cement Works")
    assert t_cement["taxonomy_key"] == "cement_manufacturing"

    # Refinery check
    t_refinery = facility_intelligence.map_taxonomy_category("refinery", "storage_tank", "IOCL Refinery Complex")
    assert t_refinery["taxonomy_key"] == "refinery_petrochemical"

    # Scientific distinction card test
    card = facility_intelligence.get_scientific_distinction_card("steel_metallurgical", observed_brightness_k=345.2, observed_frp_mw=65.0)
    assert "1,500°C" in card["equipment_internal_reference"]["process_core_temp_range"]
    assert card["satellite_radiance_measurement"]["observed_brightness_celsius"] == pytest.approx(72.05, abs=0.1)
    assert card["satellite_radiance_measurement"]["pixel_footprint_m2"] == 140625


# ── TEST G: Source Classification Abstention Protocol ─────────────────────────
def test_g_source_classification_abstention():
    # Case 1: Confident Industrial Classification
    ev_confident = {
        "nearest_facility_name": "Tata Steel Kalinganagar",
        "nearest_facility_category": "industrial",
        "nearest_facility_subcategory": "steelworks",
        "distance_to_nearest_facility_m": 150.0,
        "detection_count": 60,
        "persistence_30d": 0.80,
        "max_frp": 50.0,
        "max_frp_ratio": 2.0,
    }
    c_conf = source_classification_engine.classify_hierarchical(ev_confident)
    assert c_conf["is_abstained"] is False
    assert c_conf["final_classification"] == "steel_metallurgical"
    assert c_conf["confidence_score"] >= 0.80

    # Case 2: Ambiguous Remote Hotspot with insufficient evidence -> Must Abstain
    ev_ambiguous = {
        "nearest_facility_name": None,
        "nearest_facility_category": None,
        "distance_to_nearest_facility_m": 7500.0,
        "detection_count": 1,
        "persistence_30d": 0.01,
        "max_frp": 1.5,
        "max_frp_ratio": 1.0,
        "tree_fraction_1km_mean": 0.05,
    }
    c_abstain = source_classification_engine.classify_hierarchical(ev_ambiguous)
    assert c_abstain["is_abstained"] is True
    assert c_abstain["final_classification"] == "unclassified"
    assert "Abstention triggered" in c_abstain["abstention_reason"]


# ── TEST H: Honest Ground-Truth Policy ─────────────────────────────────────────
def test_h_honest_ground_truth_policy():
    bundle = evidence_enrichment_engine.build_evidence_bundle(
        region_name="talcher_angul",
        latitude=20.95,
        longitude=85.15,
        observed_frp=28.0,
    )
    gt = bundle["incident_ground_truth"]
    assert gt["incident_probability_status"] == "not_validated_ground_truth_insufficient"
    assert gt["incident_probability"] is None
    assert "Independent fire department" in gt["ground_truth_statement"]


# ── TEST I: Operational Priority Engine Bounds & De-duplication ───────────────
def test_i_operational_priority_engine():
    rad = {"ratio_to_median": 4.5, "mad_zscore": 4.0}
    anom = {"consensus": {"agreement_score": 0.67}}
    fac = {"spatial_tier": "tier_1_footprint", "taxonomy_key": "steel_metallurgical"}
    env = {"wind_speed_ms": 7.0, "relative_humidity_pct": 30.0, "dry_days_count": 6}

    priority = operational_priority_engine.compute_priority(rad, anom, fac, env)
    score = priority["operational_priority_score"]
    assert 0.0 <= score <= 1.0
    assert priority["operational_priority_tier"] in ("CRITICAL", "HIGH", "MODERATE", "LOW")
    assert "radiometric_severity" in priority["component_breakdown"]
    assert "anomaly_consensus" in priority["component_breakdown"]
    assert "infrastructure_criticality" in priority["component_breakdown"]
    assert "environmental_vulnerability" in priority["component_breakdown"]
    assert "Collinear variables" in priority["deduplication_audit"]


# ── TEST J: REST API Intelligence Endpoints ───────────────────────────────────
def test_j_api_endpoints():
    from main import create_app
    app = create_app()
    client = app.test_client()

    # /evidence
    r1 = client.get("/api/v1/intelligence/evidence?region=dhanbad_bokaro&frp=35")
    assert r1.status_code == 200
    b1 = r1.get_json()["evidence_bundle"]
    assert b1["feature_identity"]["region_name"] == "dhanbad_bokaro"

    # /facility-profile
    r2 = client.get("/api/v1/intelligence/facility-profile?facility_id=1")
    # A clean CI database may not contain facility id=1. The endpoint is
    # correctly allowed to return 404 for a missing resource; distinguish that
    # from a missing route (404 with Flask's generic HTML body).
    assert r2.status_code in (200, 404)
    if r2.status_code == 200:
        assert r2.get_json().get("status") == "success"
        assert "facility_profile" in r2.get_json()
    else:
        assert r2.get_json().get("status") == "not_found"

    # /historical-baseline
    r3 = client.get("/api/v1/intelligence/historical-baseline?region=dhanbad_bokaro&frp=25")
    assert r3.status_code == 200

    # /anomalies
    r4 = client.get("/api/v1/intelligence/anomalies?region=dhanbad_bokaro")
    assert r4.status_code == 200

    # /classification
    r5 = client.get("/api/v1/intelligence/classification?region=dhanbad_bokaro")
    assert r5.status_code == 200

    # /incident-risk
    r6 = client.get("/api/v1/intelligence/incident-risk?region=dhanbad_bokaro")
    assert r6.status_code == 200

    # /explanations
    r7 = client.get("/api/v1/intelligence/explanations?region=dhanbad_bokaro")
    assert r7.status_code == 200
