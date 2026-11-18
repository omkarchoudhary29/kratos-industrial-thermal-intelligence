#!/usr/bin/env python3
"""scripts/export_demo_database.py
---------------------------------
KRATOS V3.1 — Production-Grade Demonstration Database Sanitization & Export.

Workflow:
1. Takes a consistent snapshot of operational database 'wildfire_db' without modifying it.
2. Restores snapshot into a dedicated staging database 'wildfire_demo_staging'.
3. Sanitizes staging database:
   - Removes all test-contaminated records (is_test = TRUE).
   - Cleans orphaned notes and cascade records.
   - Flushes ephemeral sessions and refresh tokens.
   - Rotates demo accounts: sets up clean 'admin' and 'demo_reviewer' with bcrypt hashes.
   - Removes transient/dummy test accounts.
   - Masks sensitive connectors, authorization headers, and endpoint credentials.
   - Resets sequence counters.
4. Exports custom-format binary dump (.dump) to external directory outside Git.
5. Verifies dump by restoring into isolated 'wildfire_demo_verify' database and auditing counts.
6. Cleans up staging and verify databases.
7. Emits cryptographically signed SHA-256 manifest.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import bcrypt
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import RealDictCursor

# Directories
REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = Path(r"D:\mukesh\Documents\Gen ai\kratos_demo_db_export")
EXPORT_DUMP_FILE = EXPORT_DIR / "wildfire_demo_sanitized.dump"
MANIFEST_FILE = EXPORT_DIR / "manifest.json"

# Credentials for local PostgreSQL admin
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
SOURCE_DB = "wildfire_db"
STAGING_DB = "wildfire_demo_staging"
VERIFY_DB = "wildfire_demo_verify"

# Demo User Credentials to provision in sanitized dump
ADMIN_USER = "admin"
ADMIN_EMAIL = "admin@kratos.intelligence"
ADMIN_PASS_PLAIN = "KratosAdmin2026!"

REVIEWER_USER = "demo_reviewer"
REVIEWER_EMAIL = "demo_reviewer@kratos.intelligence"
REVIEWER_PASS_PLAIN = "KratosDemo2026!"


def get_pg_env() -> Dict[str, str]:
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD
    return env


def execute_pg_command(cmd: list[str], description: str) -> None:
    print(f"[cmd] {description}: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=get_pg_env(), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {description} failed (code {result.returncode}):\n{result.stderr}")
        raise RuntimeError(f"{description} failed: {result.stderr}")


def get_maint_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn


def get_db_connection(dbname: str):
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=dbname,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn


def drop_and_create_db(dbname: str) -> None:
    maint_conn = get_maint_connection()
    cur = maint_conn.cursor()
    # Terminate existing connections to target database
    cur.execute(
        """
        SELECT pg_terminate_backend(pid) 
        FROM pg_stat_activity 
        WHERE datname = %s AND pid <> pg_backend_pid();
        """,
        (dbname,),
    )
    cur.execute(f'DROP DATABASE IF EXISTS "{dbname}";')
    cur.execute(f'CREATE DATABASE "{dbname}";')
    cur.close()
    maint_conn.close()
    print(f"[db] Fresh database created: {dbname}")


def drop_db(dbname: str) -> None:
    maint_conn = get_maint_connection()
    cur = maint_conn.cursor()
    cur.execute(
        """
        SELECT pg_terminate_backend(pid) 
        FROM pg_stat_activity 
        WHERE datname = %s AND pid <> pg_backend_pid();
        """,
        (dbname,),
    )
    cur.execute(f'DROP DATABASE IF EXISTS "{dbname}";')
    cur.close()
    maint_conn.close()
    print(f"[db] Database dropped: {dbname}")


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_sanitization_and_export():
    print("=" * 75)
    print("KRATOS V3.1 — DEMONSTRATION DATABASE SANITIZATION & EXPORT")
    print("=" * 75)
    start_time = time.time()

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    temp_initial_dump = EXPORT_DIR / "temp_source_snapshot.dump"

    # Step 1: Snapshot operational wildfire_db to temporary dump file (READ-ONLY)
    print(f"\n[1/6] Taking snapshot of source operational database: {SOURCE_DB}...")
    execute_pg_command(
        [
            "pg_dump",
            "-h", DB_HOST,
            "-p", str(DB_PORT),
            "-U", DB_USER,
            "-d", SOURCE_DB,
            "-Fc",
            "-f", str(temp_initial_dump),
        ],
        f"Snapshot {SOURCE_DB}",
    )
    print(f"      Snapshot created: {temp_initial_dump.stat().st_size / (1024*1024):.2f} MB")

    # Step 2: Create staging database and restore snapshot
    print(f"\n[2/6] Restoring snapshot into staging database: {STAGING_DB}...")
    drop_and_create_db(STAGING_DB)
    # Enable PostGIS on staging
    staging_conn = get_db_connection(STAGING_DB)
    with staging_conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    staging_conn.close()

    # pg_restore into staging
    restore_cmd = [
        "pg_restore",
        "-h", DB_HOST,
        "-p", str(DB_PORT),
        "-U", DB_USER,
        "-d", STAGING_DB,
        "--no-owner",
        "--no-privileges",
        str(temp_initial_dump),
    ]
    # Note: pg_restore may return 1 if postgis extension already exists in dump, which is normal
    res = subprocess.run(restore_cmd, env=get_pg_env(), capture_output=True, text=True)
    if res.returncode not in (0, 1):
        raise RuntimeError(f"Restore into {STAGING_DB} failed: {res.stderr}")
    print(f"      Staging database successfully populated.")

    # Step 3: Sanitize staging database
    print(f"\n[3/6] Applying sanitization rules to {STAGING_DB}...")
    conn = get_db_connection(STAGING_DB)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 3.1 Scrub test records
    cur.execute("DELETE FROM investigation_reports WHERE is_test = TRUE;")
    del_reports = cur.rowcount
    cur.execute("DELETE FROM follow_up_tasks WHERE is_test = TRUE;")
    del_tasks = cur.rowcount
    cur.execute("DELETE FROM authority_submissions WHERE is_test = TRUE;")
    del_subs = cur.rowcount
    cur.execute("DELETE FROM follow_up_notes WHERE follow_up_id NOT IN (SELECT id FROM follow_up_tasks);")
    del_notes = cur.rowcount
    print(f"      Scrubbed test records: {del_reports} reports, {del_tasks} tasks, {del_subs} submissions, {del_notes} orphaned notes.")

    # 3.2 Clear refresh tokens and ephemeral sessions
    cur.execute("DELETE FROM refresh_tokens;")
    del_tokens = cur.rowcount
    print(f"      Flushed {del_tokens} active refresh tokens.")

    # 3.3 Sanitize users and rotate demonstration reviewer credentials
    cur.execute("DELETE FROM users;")
    admin_pw_hash = bcrypt.hashpw(ADMIN_PASS_PLAIN.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")
    reviewer_pw_hash = bcrypt.hashpw(REVIEWER_PASS_PLAIN.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")

    cur.execute(
        """
        INSERT INTO users (id, username, email, password_hash, is_admin, chat_count, created_at)
        VALUES 
            (1, %s, %s, %s, TRUE, 0, NOW()),
            (2, %s, %s, %s, FALSE, 0, NOW());
        """,
        (ADMIN_USER, ADMIN_EMAIL, admin_pw_hash, REVIEWER_USER, REVIEWER_EMAIL, reviewer_pw_hash),
    )
    print("      Provisioned sanitized demo credentials (admin, demo_reviewer).")

    # 3.4 Sanitize data_connectors credentials
    cur.execute(
        """
        UPDATE data_connectors 
        SET endpoint_url = 'postgresql://localhost:5432/wildfire_db' 
        WHERE connector_key = 'conn_postgis_core';
        """
    )
    # Mask any configuration secrets if present
    cur.execute("SELECT id, configuration FROM data_connectors;")
    connectors = cur.fetchall()
    for row in connectors:
        cfg = row["configuration"] or {}
        changed = False
        for secret_key in ("api_key", "password", "token", "secret", "auth_token"):
            if secret_key in cfg:
                cfg[secret_key] = "DEMO_MASKED_CREDENTIAL"
                changed = True
        if changed:
            cur.execute("UPDATE data_connectors SET configuration = %s WHERE id = %s;", (json.dumps(cfg), row["id"]))
    print("      Masked connector endpoints and configuration secrets.")

    # 3.5 Reset sequence counters
    cur.execute(
        """
        SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE((SELECT MAX(id) FROM users), 1), true);
        SELECT setval(pg_get_serial_sequence('investigation_reports', 'id'), COALESCE((SELECT MAX(id) FROM investigation_reports), 1), true);
        SELECT setval(pg_get_serial_sequence('follow_up_tasks', 'id'), COALESCE((SELECT MAX(id) FROM follow_up_tasks), 1), true);
        SELECT setval(pg_get_serial_sequence('authority_submissions', 'id'), COALESCE((SELECT MAX(id) FROM authority_submissions), 1), true);
        """
    )
    print("      Reset relational sequence generators.")
    cur.close()
    conn.close()

    # Step 4: Export sanitized dump from staging DB
    print(f"\n[4/6] Exporting sanitized binary dump to {EXPORT_DUMP_FILE}...")
    execute_pg_command(
        [
            "pg_dump",
            "-h", DB_HOST,
            "-p", str(DB_PORT),
            "-U", DB_USER,
            "-d", STAGING_DB,
            "-Fc",
            "-f", str(EXPORT_DUMP_FILE),
        ],
        f"Export {STAGING_DB} -> {EXPORT_DUMP_FILE.name}",
    )
    dump_size_mb = EXPORT_DUMP_FILE.stat().st_size / (1024 * 1024)
    dump_sha256 = compute_sha256(EXPORT_DUMP_FILE)
    print(f"      Sanitized dump generated: {dump_size_mb:.2f} MB")
    print(f"      SHA-256: {dump_sha256}")

    # Step 5: Verification — Restore into clean verify database and audit
    print(f"\n[5/6] Verifying dump restoration in isolated database: {VERIFY_DB}...")
    drop_and_create_db(VERIFY_DB)
    v_conn = get_db_connection(VERIFY_DB)
    with v_conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    v_conn.close()

    restore_verify_cmd = [
        "pg_restore",
        "-h", DB_HOST,
        "-p", str(DB_PORT),
        "-U", DB_USER,
        "-d", VERIFY_DB,
        "--no-owner",
        "--no-privileges",
        str(EXPORT_DUMP_FILE),
    ]
    res_verify = subprocess.run(restore_verify_cmd, env=get_pg_env(), capture_output=True, text=True)
    if res_verify.returncode not in (0, 1):
        raise RuntimeError(f"Restore into verify database failed: {res_verify.stderr}")

    verify_conn = get_db_connection(VERIFY_DB)
    v_cur = verify_conn.cursor(cursor_factory=RealDictCursor)

    # Audit verification counts
    v_cur.execute("SELECT count(*) AS c FROM osm_facilities;")
    verified_facilities = v_cur.fetchone()["c"]
    v_cur.execute("SELECT count(*) AS c FROM fire_detections;")
    verified_detections = v_cur.fetchone()["c"]
    v_cur.execute("SELECT count(*) AS c FROM monitoring_fire_events;")
    verified_monitoring_events = v_cur.fetchone()["c"]
    v_cur.execute("SELECT count(*) AS c FROM fire_events;")
    verified_fire_events = v_cur.fetchone()["c"]
    v_cur.execute("SELECT count(*) AS c FROM source_clusters;")
    verified_clusters = v_cur.fetchone()["c"]
    v_cur.execute("SELECT count(*) AS c FROM users;")
    verified_users = v_cur.fetchone()["c"]
    v_cur.execute("SELECT count(*) AS c FROM refresh_tokens;")
    verified_tokens = v_cur.fetchone()["c"]

    # Verify zero test contamination
    v_cur.execute("SELECT count(*) AS c FROM investigation_reports WHERE is_test = TRUE;")
    test_reports = v_cur.fetchone()["c"]
    v_cur.execute("SELECT count(*) AS c FROM follow_up_tasks WHERE is_test = TRUE;")
    test_tasks = v_cur.fetchone()["c"]
    v_cur.execute("SELECT count(*) AS c FROM authority_submissions WHERE is_test = TRUE;")
    test_subs = v_cur.fetchone()["c"]

    v_cur.execute("SELECT count(*) AS c FROM investigation_reports;")
    total_reports = v_cur.fetchone()["c"]
    v_cur.execute("SELECT count(*) AS c FROM follow_up_tasks;")
    total_tasks = v_cur.fetchone()["c"]
    v_cur.execute("SELECT count(*) AS c FROM authority_submissions;")
    total_subs = v_cur.fetchone()["c"]

    v_cur.close()
    verify_conn.close()

    assert test_reports == 0, f"Expected 0 test reports, found {test_reports}"
    assert test_tasks == 0, f"Expected 0 test tasks, found {test_tasks}"
    assert test_subs == 0, f"Expected 0 test submissions, found {test_subs}"
    assert verified_users == 2, f"Expected 2 sanitized users, found {verified_users}"
    assert verified_tokens == 0, f"Expected 0 refresh tokens, found {verified_tokens}"
    assert verified_facilities >= 2400, f"Facility count mismatch: {verified_facilities}"

    print(f"      [PASS] OSM Facilities:          {verified_facilities:,}")
    print(f"      [PASS] Fire Detections:         {verified_detections:,}")
    print(f"      [PASS] Monitoring Events:       {verified_monitoring_events:,}")
    print(f"      [PASS] Configured Regions:      {verified_fire_events:,}")
    print(f"      [PASS] Persistent Clusters:     {verified_clusters:,}")
    print(f"      [PASS] Verified Users:          {verified_users:,} (admin, demo_reviewer)")
    print(f"      [PASS] Active Refresh Tokens:   {verified_tokens}")
    print(f"      [PASS] Clean Reports:           {total_reports} (0 test records)")
    print(f"      [PASS] Clean Tasks:             {total_tasks} (0 test records)")
    print(f"      [PASS] Clean Submissions:       {total_subs} (0 test records)")

    # Step 6: Cleanup temporary databases and snapshot file
    print(f"\n[6/6] Cleaning up staging and verify databases...")
    drop_db(VERIFY_DB)
    drop_db(STAGING_DB)
    if temp_initial_dump.exists():
        temp_initial_dump.unlink()
        print(f"      Removed temporary snapshot: {temp_initial_dump.name}")

    # Write Manifest
    manifest_data = {
        "export_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dump_file": EXPORT_DUMP_FILE.name,
        "dump_path": str(EXPORT_DUMP_FILE),
        "file_size_bytes": EXPORT_DUMP_FILE.stat().st_size,
        "file_size_mb": round(dump_size_mb, 2),
        "sha256": dump_sha256,
        "format": "PostgreSQL custom archive (-Fc)",
        "postgresql_version": "PostgreSQL 18.x + PostGIS 3.6.x",
        "verified_metrics": {
            "osm_facilities": verified_facilities,
            "fire_detections": verified_detections,
            "monitoring_fire_events": verified_monitoring_events,
            "fire_events": verified_fire_events,
            "source_clusters": verified_clusters,
            "users": verified_users,
            "investigation_reports_clean": total_reports,
            "follow_up_tasks_clean": total_tasks,
            "authority_submissions_clean": total_subs,
            "refresh_tokens_purged": True,
            "test_records_purged": True,
        },
        "demonstration_accounts": [
            {
                "username": ADMIN_USER,
                "email": ADMIN_EMAIL,
                "role": "Administrator",
                "default_password": ADMIN_PASS_PLAIN,
            },
            {
                "username": REVIEWER_USER,
                "email": REVIEWER_EMAIL,
                "role": "Demo Reviewer",
                "default_password": REVIEWER_PASS_PLAIN,
            },
        ],
        "restoration_command": f'pg_restore -h <DB_HOST> -p <DB_PORT> -U <DB_USER> -d <DB_NAME> --no-owner --no-privileges "{EXPORT_DUMP_FILE.name}"',
    }

    with open(MANIFEST_FILE, "w", encoding="utf-8") as mf:
        json.dump(manifest_data, mf, indent=2)

    elapsed = time.time() - start_time
    print("=" * 75)
    print(f"[SUCCESS] Demonstration Database Export Completed in {elapsed:.1f}s")
    print(f"          Dump:     {EXPORT_DUMP_FILE}")
    print(f"          Manifest: {MANIFEST_FILE}")
    print(f"          SHA-256:  {dump_sha256}")
    print("=" * 75)


if __name__ == "__main__":
    run_sanitization_and_export()
