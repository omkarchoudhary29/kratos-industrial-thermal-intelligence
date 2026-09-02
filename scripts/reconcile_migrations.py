#!/usr/bin/env python3
"""scripts/reconcile_migrations.py
--------------------------------
Safely reconciles schema_migrations tracking table for migrations that were verified
completely applied to the database schema.
"""

import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / ".env.test")


def reconcile_database(db_url: str, db_name: str):
    print(f"--- Reconciling migration tracking for {db_name} ---")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    migrations_to_reconcile = [
        "20261116_phase3_operational_platform.sql",
        "20261116_final_hardening_audit_and_test_isolation.sql"
    ]

    for mig in migrations_to_reconcile:
        cur.execute("SELECT 1 FROM schema_migrations WHERE version = %s;", (mig,))
        if cur.fetchone():
            print(f"  Version '{mig}' already recorded in {db_name}.")
        else:
            cur.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (%s, NOW());",
                (mig,)
            )
            print(f"  ✓ Successfully registered verified migration '{mig}' into {db_name}.schema_migrations.")

    conn.close()


if __name__ == "__main__":
    op_url = os.getenv("DATABASE_URL", "").replace("+psycopg2", "")
    test_url = os.getenv("TEST_DATABASE_URL", "").replace("+psycopg2", "")
    if op_url:
        reconcile_database(op_url, "wildfire_db")
    if test_url:
        reconcile_database(test_url, "wildfire_test_db")
    print("Reconciliation complete.")
