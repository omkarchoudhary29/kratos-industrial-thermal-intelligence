"""
scripts/audit_phase2_handoff.py
-------------------------------
Read-only audit script for Phase 2 handoff and Phase 3 baseline data verification.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import create_engine, text

# Add backend to path and load config/.env
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import config
from db.connection import get_db_uri

def run_audit():
    engine = create_engine(get_db_uri())
    print("=== KRATOS V3.1 PHASE 2 HANDOFF & OPERATIONAL DATA AUDIT ===")
    with engine.connect() as conn:
        # Table counts
        tables = [
            "investigation_reports",
            "follow_up_tasks",
            "follow_up_notes",
            "authority_submissions",
            "data_connectors",
            "integration_sync_jobs",
            "fire_alerts",
            "system_audit_logs",
            "osm_facilities",
            "firms_sync_state"
        ]
        print("\n--- TABLE RECORD INVENTORY ---")
        for tbl in tables:
            try:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
                print(f"  {tbl:<25}: {cnt:>6} records")
            except Exception as e:
                print(f"  {tbl:<25}: ERROR ({e})")

        # Reports review
        print("\n--- EXISTING INVESTIGATION REPORTS ---")
        df_rpt = pd.read_sql(text("""
            SELECT id, report_key, scope, region_name, feature_type, feature_id, status, version, submission_status, created_at
            FROM investigation_reports ORDER BY id DESC LIMIT 10
        """), conn)
        if not df_rpt.empty:
            print(df_rpt.to_string())
        else:
            print("  No investigation reports currently stored.")

        # Follow-ups review
        print("\n--- EXISTING FOLLOW-UP TASKS ---")
        df_flw = pd.read_sql(text("""
            SELECT id, task_key, title, feature_type, feature_id, region_name, priority, status, assigned_to, created_at
            FROM follow_up_tasks ORDER BY id DESC LIMIT 15
        """), conn)
        if not df_flw.empty:
            print(df_flw.to_string())
            print("\n  Task status breakdown:")
            status_counts = pd.read_sql(text("SELECT status, COUNT(*) as count FROM follow_up_tasks GROUP BY status"), conn)
            print(status_counts.to_string(index=False))
            print("\n  Task priority breakdown:")
            pri_counts = pd.read_sql(text("SELECT priority, COUNT(*) as count FROM follow_up_tasks GROUP BY priority"), conn)
            print(pri_counts.to_string(index=False))
        else:
            print("  No follow-up tasks currently stored.")

        # Submissions review
        print("\n--- EXISTING AUTHORITY SUBMISSIONS ---")
        df_sub = pd.read_sql(text("""
            SELECT id, submission_key, report_id, authority_id, authority_name, channel, reference_number, status, submitted_at
            FROM authority_submissions ORDER BY id DESC LIMIT 10
        """), conn)
        if not df_sub.empty:
            print(df_sub.to_string())
        else:
            print("  No authority submissions currently stored.")

        # Connectors review
        print("\n--- EXISTING DATA CONNECTORS ---")
        df_conn = pd.read_sql(text("""
            SELECT id, connector_key, name, provider, connector_type, is_active, health_status, records_received, last_sync_at
            FROM data_connectors ORDER BY id
        """), conn)
        if not df_conn.empty:
            print(df_conn.to_string())
        else:
            print("  No data connectors currently stored.")

        # System audit logs review
        print("\n--- RECENT SYSTEM AUDIT LOGS ---")
        df_audit = pd.read_sql(text("""
            SELECT id, timestamp, username, user_role, action_type, resource_type, resource_id, status
            FROM system_audit_logs ORDER BY id DESC LIMIT 10
        """), conn)
        if not df_audit.empty:
            print(df_audit.to_string())
        else:
            print("  No system audit logs recorded.")

if __name__ == "__main__":
    run_audit()
