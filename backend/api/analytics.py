"""backend/api/analytics.py
------------------------
API routes for Advanced Geospatial Analytics Workspace.
"""

from flask import Blueprint, jsonify, request
from services.advanced_analytics import advanced_analytics_service

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/v1/analytics")


@analytics_bp.get("/overview")
def get_analytics_overview():
    """Summary overview of cross-corridor intelligence, thermal distribution, and KPIs."""
    include_test = request.args.get("include_test", "false").lower() in ("1", "true", "yes")
    corridors = advanced_analytics_service.get_corridor_comparisons()
    distribution = advanced_analytics_service.get_thermal_distribution()
    taxonomy = advanced_analytics_service.get_classification_breakdown()
    workflow = advanced_analytics_service.get_operational_workflow_kpis(include_test=include_test)

    return jsonify({
        "total_corridors_monitored": len(corridors),
        "corridors": corridors,
        "thermal_distribution": distribution,
        "classification_taxonomy": taxonomy,
        "workflow_kpis": workflow,
    })


@analytics_bp.get("/corridors")
def get_corridors_analytics():
    """Detailed 10-corridor comparative metrics."""
    return jsonify({
        "corridors": advanced_analytics_service.get_corridor_comparisons()
    })


@analytics_bp.get("/thermal-distribution")
def get_thermal_distribution():
    """Diurnal day/night ratios and recurrence spectrum."""
    return jsonify(advanced_analytics_service.get_thermal_distribution())


@analytics_bp.get("/classification-breakdown")
def get_classification_breakdown():
    """Multi-source classification distribution."""
    return jsonify(advanced_analytics_service.get_classification_breakdown())


@analytics_bp.get("/models")
def get_model_benchmarks():
    """Model evaluation benchmarks with prominent proxy-label ground truth disclaimer."""
    return jsonify(advanced_analytics_service.get_model_evaluation_metrics())


@analytics_bp.get("/workflow")
def get_workflow_kpis():
    """Operational turnaround times, follow-up resolutions, and submission metrics."""
    include_test = request.args.get("include_test", "false").lower() in ("1", "true", "yes")
    return jsonify(advanced_analytics_service.get_operational_workflow_kpis(include_test=include_test))
