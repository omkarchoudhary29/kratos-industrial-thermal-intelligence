#!/usr/bin/env python3
"""scripts/backfill_audit_chain.py
---------------------------------
Controlled historical backfill for system_audit_logs cryptographic chain.
1. Adds schema columns if missing.
2. Backfills historical rows in deterministic ID order with predecessor hashes and canonical digests.
3. Sets integrity_version='v2_backfill' and hash_backfilled_at=NOW().
4. Installs the PostgreSQL BEFORE UPDATE OR DELETE rejection trigger for immutability.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.test")
load_dotenv(REPO_ROOT / ".env")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))

from backend.services.audit_service import GENESIS_HASH, compute_audit_hash


def backfill_database(db_url: str, db_name: str):
    print(f"=== Backfilling audit hash chain for {db_name} ===")
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Add columns if not existing
        cur.execute("""
            ALTER TABLE system_audit_logs 
                ADD COLUMN IF NOT EXISTS previous_record_hash VARCHAR(64),
                ADD COLUMN IF NOT EXISTS integrity_version VARCHAR(16) DEFAULT 'v2_chain',
                ADD COLUMN IF NOT EXISTS hash_backfilled_at TIMESTAMPTZ;
        """)

        # Drop trigger temporarily if re-running backfill
        cur.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_log_modification ON system_audit_logs;")

        # 2. Fetch all historical records in deterministic ascending order
        cur.execute("""
            SELECT id, timestamp, username, user_role, action_type, resource_type, 
                   resource_id, details, is_test
            FROM system_audit_logs
            ORDER BY id ASC;
        """)
        records = cur.fetchall()
        print(f"Found {len(records)} existing audit records in {db_name}.")

        backfill_ts = datetime.now(timezone.utc)
        prev_hash = GENESIS_HASH

        for rec in records:
            h = compute_audit_hash(
                record_id=rec["id"],
                timestamp=rec["timestamp"],
                username=rec["username"],
                user_role=rec["user_role"],
                action_type=rec["action_type"],
                resource_type=rec["resource_type"],
                resource_id=rec["resource_id"],
                details=rec["details"],
                previous_hash=prev_hash,
                integrity_version="v2_backfill"
            )

            cur.execute("""
                UPDATE system_audit_logs
                SET previous_record_hash = %s,
                    integrity_hash = %s,
                    integrity_version = 'v2_backfill',
                    hash_backfilled_at = %s
                WHERE id = %s;
            """, (prev_hash, h, backfill_ts, rec["id"]))

            prev_hash = h

        print(f"✓ Backfilled {len(records)} records. Chain head: {prev_hash[:16]}...")

        # 3. Create database immutability trigger function
        cur.execute("""
            CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'system_audit_logs is an append-only cryptographic ledger. UPDATE and DELETE operations are strictly prohibited.';
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trg_prevent_audit_log_modification ON system_audit_logs;
            CREATE TRIGGER trg_prevent_audit_log_modification
            BEFORE UPDATE OR DELETE ON system_audit_logs
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
        """)
        print("✓ Created PostgreSQL BEFORE UPDATE OR DELETE immutability trigger on system_audit_logs.")

        conn.commit()
        print(f"✓ Successfully committed backfill and trigger on {db_name}.")
    except Exception as e:
        conn.rollback()
        print(f"✗ Failed backfilling {db_name}: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    op_url = os.getenv("DATABASE_URL", "").replace("+psycopg2", "")
    test_url = os.getenv("TEST_DATABASE_URL", "").replace("+psycopg2", "")
    if op_url:
        backfill_database(op_url, "wildfire_db")
    if test_url:
        backfill_database(test_url, "wildfire_test_db")
