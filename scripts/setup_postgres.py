#!/usr/bin/env python3
"""
scripts/setup_postgres.py
-------------------------
Production PostgreSQL 18 & PostGIS Setup Utility for Industrial Thermal Intelligence.

Performs:
  1. Verifies connectivity to local PostgreSQL service (localhost:5432).
  2. Verifies whether 'wildfire_db' exists; creates it if missing (never drops existing).
  3. Enables PostGIS extension: 'CREATE EXTENSION IF NOT EXISTS postgis;'
  4. Queries and prints PostGIS_Full_Version() and PostGIS_Version().
  5. Updates .env with the verified database credentials.
  6. Initializes application tables and bootstraps the admin account.
"""

import getpass
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
sys.path.insert(0, str(BASE_DIR / "backend"))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def setup_postgresql(password: str | None = None) -> bool:
    env_file = BASE_DIR / ".env"
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    user = os.getenv("DB_USER", "postgres")
    dbname = os.getenv("DB_NAME", "wildfire_db")

    if not password:
        password = os.getenv("DB_PASSWORD", "")
        if not password or password == "change-me-strong-password":
            print("\n[setup] PostgreSQL administrator password required.")
            password = getpass.getpass("Enter PostgreSQL password for user 'postgres': ")

    print(f"\n[1/6] Connecting to PostgreSQL service at {host}:{port} as '{user}'...")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname="postgres",
            connect_timeout=5,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        print("      ✓ PostgreSQL service connection established.")
    except Exception as exc:
        print(f"      ✗ Connection failed: {exc}")
        return False

    # Check if target application database exists
    print(f"\n[2/6] Checking application database '{dbname}'...")
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
    exists = cur.fetchone() is not None
    if not exists:
        print(f"      Application database '{dbname}' does not exist. Creating...")
        cur.execute(f'CREATE DATABASE "{dbname}";')
        print(f"      ✓ Database '{dbname}' created successfully.")
    else:
        print(f"      ✓ Database '{dbname}' already exists. Preserving existing data.")

    cur.close()
    conn.close()

    # Connect to application database and enable PostGIS
    print(f"\n[3/6] Connecting to '{dbname}' and enabling PostGIS...")
    try:
        app_conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            connect_timeout=5,
        )
        app_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        app_cur = app_conn.cursor()

        app_cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        print("      ✓ Extension 'postgis' verified / enabled.")

        # Verify PostGIS version
        app_cur.execute("SELECT current_database(), PostGIS_Version(), PostGIS_Full_Version();")
        curr_db, pg_ver, full_ver = app_cur.fetchone()
        print(f"\n[4/6] PostGIS Diagnostic Information:")
        print(f"      Current Database: {curr_db}")
        print(f"      PostGIS Version:  {pg_ver}")
        print(f"      Full Details:     {full_ver}")

        app_cur.close()
        app_conn.close()
    except Exception as exc:
        print(f"      ✗ PostGIS configuration failed: {exc}")
        return False

    # Update .env file
    print("\n[5/6] Updating .env database credentials...")
    if env_file.exists():
        content = env_file.read_text(encoding="utf-8")
        content = re.sub(
            r"^DB_PASSWORD=.*$",
            f"DB_PASSWORD={password}",
            content,
            flags=re.MULTILINE,
        )
        quoted_pw = quote_plus(password)
        database_url = f"postgresql+psycopg2://{user}:{quoted_pw}@{host}:{port}/{dbname}"
        content = re.sub(
            r"^DATABASE_URL=.*$",
            f"DATABASE_URL={database_url}",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r"^POSTGRES_PASSWORD=.*$",
            f"POSTGRES_PASSWORD={password}",
            content,
            flags=re.MULTILINE,
        )
        env_file.write_text(content, encoding="utf-8")
        print("      ✓ .env updated with verified credentials.")

    # Initialize tables and seed admin user
    print("\n[6/6] Initializing application tables and bootstrapping admin user...")
    quoted_pw = quote_plus(password)
    os.environ["DB_PASSWORD"] = password
    os.environ["DATABASE_URL"] = f"postgresql+psycopg2://{user}:{quoted_pw}@{host}:{port}/{dbname}"
    os.environ["ALLOW_SQLITE_FALLBACK"] = "0"

    try:
        from main import create_app
        from pipeline.db import setup_db

        app = create_app()
        with app.app_context():
            setup_db(app)
        print("      ✓ All application tables initialized and admin account bootstrapped.")
    except Exception as exc:
        print(f"      ✗ Table initialization error: {exc}")
        return False

    print("\n═════════════════════════════════════════════════════════════════════════")
    print("✓ PRODUCTION POSTGRESQL 18 + POSTGIS SUCCESSFULLY CONFIGURED AND VERIFIED!")
    print("═════════════════════════════════════════════════════════════════════════")
    return True


if __name__ == "__main__":
    pwd = sys.argv[1] if len(sys.argv) > 1 else None
    success = setup_postgresql(pwd)
    sys.exit(0 if success else 1)
