#!/usr/bin/env python3
"""scripts/run_migrations.py
-------------------------
Safe, idempotent migration runner for Industrial Thermal Intelligence.
Executes SQL migrations in backend/db/migrations/ tracking them in schema_migrations.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env.test")
load_dotenv(REPO_ROOT / ".env")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))

from backend.db.connection import get_db_uri
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("migrations")


def run_migrations(target_db: str = None, check_only: bool = False, verbose: bool = False) -> bool:
    migrations_dir = REPO_ROOT / "backend" / "db" / "migrations"
    if not migrations_dir.exists():
        log.error("Migrations directory not found: %s", migrations_dir)
        return False

    sql_files = sorted(migrations_dir.glob("*.sql"))
    if not sql_files:
        log.info("No migration SQL files found in %s", migrations_dir)
        return True

    # Order priority map to ensure dependencies are met
    priority = {
        "20231115_create_osm_facilities_table.sql": 1,
        "20231115_create_source_clusters_view.sql": 2,
        "20231115_create_ingestion_audit_view.sql": 3,
        "20231116_create_reports_and_followups.sql": 4,
        "20261116_phase3_operational_platform.sql": 5,
        "20261116_final_hardening_audit_and_test_isolation.sql": 6,
        "20261117_cryptographic_audit_hash_chain.sql": 7,
    }
    sql_files = sorted(sql_files, key=lambda f: (priority.get(f.name, 100), f.name))

    if target_db == "wildfire_test_db":
        uri = os.getenv("TEST_DATABASE_URL")
        if not uri:
            log.error("TEST_DATABASE_URL not set in environment.")
            return False
    else:
        uri = get_db_uri()

    log.info("Connecting to database: %s", uri.split("@")[-1] if "@" in uri else uri)
    engine = create_engine(uri)

    with engine.begin() as conn:
        # Create schema_migrations tracking table if needed
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))

        # Fetch already applied migrations
        applied = {
            row[0] for row in conn.execute(text("SELECT version FROM schema_migrations;")).fetchall()
        }

        log.info("Found %d total migration files (%d already applied).", len(sql_files), len(applied))

        pending = [f for f in sql_files if f.name not in applied]
        if not pending:
            log.info("Database schema is up to date. No pending migrations.")
            return True

        log.info("Pending migrations: %s", [f.name for f in pending])
        if check_only:
            log.info("Check-only mode requested. Exiting without applying.")
            return True

        for sql_file in pending:
            log.info("Applying migration: %s ...", sql_file.name)
            sql_content = sql_file.read_text(encoding="utf-8")
            try:
                conn.execute(text(sql_content))
                conn.execute(
                    text("INSERT INTO schema_migrations (version) VALUES (:v);"),
                    {"v": sql_file.name}
                )
                log.info("✓ Successfully applied: %s", sql_file.name)
            except Exception as exc:
                log.error("✗ Failed applying %s: %s", sql_file.name, exc)
                raise

    log.info("All pending migrations successfully applied and committed.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run database schema migrations")
    parser.add_argument("--db", choices=["wildfire_db", "wildfire_test_db"], default=None,
                        help="Target database (defaults to operational or DATABASE_URL)")
    parser.add_argument("--check", action="store_true", help="Check pending migrations without applying")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    success = run_migrations(target_db=args.db, check_only=args.check, verbose=args.verbose)
    sys.exit(0 if success else 1)
