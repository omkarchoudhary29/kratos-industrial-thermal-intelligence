"""backend/services/settings_service.py
-----------------------------------
Platform Settings, RBAC Roles, and System Audit Service for KRATOS V3.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from db.connection import db
from db.models import SystemAuditLog, User
from services.ml_evaluation import ml_evaluation_service

log = logging.getLogger("settings_service")

RBAC_ROLES = [
    {
        "role_key": "ADMINISTRATOR",
        "display_name": "System Administrator",
        "description": "Full access to platform configuration, connector lifecycle, user management, and security audit logs. Destructive evidence purge is strictly prohibited by system preservation safeguards.",
        "permissions": ["READ", "WRITE", "APPROVE", "SUBMIT", "MANAGE_USERS", "MANAGE_SYSTEM"],
    },
    {
        "role_key": "MONITORING_ANALYST",
        "display_name": "Senior Monitoring Analyst",
        "description": "Real-time thermal signal surveillance, triage priority queues, and report draft generation.",
        "permissions": ["READ", "WRITE", "CREATE_REPORT", "ASSIGN_FOLLOWUP"],
    },
    {
        "role_key": "COMPLIANCE_REVIEWER",
        "display_name": "Environmental Compliance Reviewer",
        "description": "Review and formal approval of investigation reports, official authority routing, and docket tracking.",
        "permissions": ["READ", "WRITE", "APPROVE_REPORT", "SUBMIT_AUTHORITY"],
    },
    {
        "role_key": "FIELD_INVESTIGATOR",
        "display_name": "Field Verification Officer",
        "description": "Field ground-truth inspection, verification evidence logging, and follow-up closure.",
        "permissions": ["READ", "LOG_FIELD_EVIDENCE", "UPDATE_FOLLOWUP"],
    },
    {
        "role_key": "AUDITOR",
        "display_name": "Read-Only Compliance Auditor",
        "description": "Read-only access to published reports, analytical dashboards, and immutable audit logs.",
        "permissions": ["READ", "EXPORT_EVIDENCE"],
    },
]

DEFAULT_MONITORING_THRESHOLDS = {
    "high_frp_threshold_mw": 15.0,
    "critical_frp_threshold_mw": 35.0,
    "persistence_day_threshold": 3,
    "spatial_cluster_eps_m": 300.0,
    "facility_buffer_radius_m": 2000.0,
    "default_timeline_window_days": 30,
    "default_region": "National Overview",
    "alert_sound_enabled": False,
    "auto_refresh_interval_sec": 30,
}


class SettingsService:
    """Manages platform thresholds, user roles, and audit trail inspection."""

    def __init__(self):
        self._thresholds = dict(DEFAULT_MONITORING_THRESHOLDS)

    def get_monitoring_thresholds(self) -> Dict[str, Any]:
        return dict(self._thresholds)

    def update_monitoring_thresholds(self, updates: Dict[str, Any], username: str = "Administrator") -> Dict[str, Any]:
        for k, v in updates.items():
            if k in self._thresholds:
                self._thresholds[k] = v

        # Centralized audit log entry with tamper-evident cryptographic hash chain
        from services.audit_service import record_audit_event
        record_audit_event(
            username=username,
            user_role="Administrator",
            action_type="SETTINGS_UPDATE",
            resource_type="monitoring_thresholds",
            resource_id="global_thresholds",
            status="SUCCESS",
            details=updates,
            is_test=os.getenv("TESTING") == "1",
            session=db.session,
        )
        db.session.commit()
        return dict(self._thresholds)

    def verify_audit_logs(self) -> Dict[str, Any]:
        """Verify complete cryptographic audit hash chain integrity."""
        from services.audit_service import verify_audit_chain
        return verify_audit_chain(session=db.session)

    def get_rbac_roles(self) -> List[Dict[str, Any]]:
        return RBAC_ROLES

    def get_model_administration_status(self) -> Dict[str, Any]:
        raw_eval = ml_evaluation_service.get_evaluation_metrics()
        meta = raw_eval.get("model_metadata", {})
        return {
            "model_version": meta.get("model_version", "isolation_forest_v2_operational"),
            "algorithm": meta.get("algorithm", "IsolationForest"),
            "training_samples": meta.get("training_samples", 8891),
            "feature_count": meta.get("feature_count", 16),
            "features": meta.get("features", []),
            "baseline_window": meta.get("baseline_window", "30-day rolling"),
            "proxy_label_disclaimer": (
                "Fire Incident Prediction: NOT VALIDATED — INDEPENDENT INCIDENT GROUND TRUTH UNAVAILABLE. "
                "Models perform statistical thermal outlier detection rather than confirmed in-situ fire prediction."
            ),
        }

    def list_audit_logs(
        self,
        action_type: Optional[str] = None,
        username: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        include_test: bool = False,
    ) -> Dict[str, Any]:
        q = SystemAuditLog.query
        if not include_test:
            q = q.filter(SystemAuditLog.is_test == False)
        if action_type:
            q = q.filter(SystemAuditLog.action_type.ilike(f"%{action_type}%"))
        if username:
            q = q.filter(SystemAuditLog.username.ilike(f"%{username}%"))

        total = q.count()
        rows = q.order_by(SystemAuditLog.timestamp.desc()).offset(offset).limit(limit).all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "logs": [
                {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "username": r.username,
                    "user_role": r.user_role,
                    "action_type": r.action_type,
                    "resource_type": r.resource_type,
                    "resource_id": r.resource_id,
                    "status": r.status,
                    "details": r.details or {},
                    "integrity_hash": getattr(r, "integrity_hash", None),
                }
                for r in rows
            ],
        }


settings_service = SettingsService()
