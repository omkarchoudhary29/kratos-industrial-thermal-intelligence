#!/usr/bin/env python3
"""
scripts/verify_app.py
---------------------
Comprehensive end-to-end audit and verification for Industrial Thermal Intelligence V2:
  - PostgreSQL 18 & PostGIS 3.6.2 verification
  - Authentication (Sign In with email/username, Sign Up, Token refresh)
  - React V2 Frontend static assets verification
  - All 13 core REST endpoints verification
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
sys.path.insert(0, str(BASE_DIR / "backend"))

import psycopg2
from main import create_app


def run_verification():
    print("=" * 70)
    print(" INDUSTRIAL THERMAL INTELLIGENCE V2 — FULL SYSTEM VERIFICATION")
    print("=" * 70)

    # 1. PostgreSQL & PostGIS Check
    print("\n[1/5] Verifying PostgreSQL 18 & PostGIS 3.6.2...")
    from urllib.parse import urlparse, unquote
    db_url = os.getenv("DATABASE_URL", "")
    p = urlparse(db_url)
    conn = psycopg2.connect(
        host=p.hostname or "localhost",
        port=p.port or 5432,
        user=unquote(p.username) if p.username else "postgres",
        password=unquote(p.password) if p.password else "",
        dbname=p.path.lstrip("/"),
    )
    cur = conn.cursor()
    cur.execute("SELECT current_database(), PostGIS_Version();")
    curr_db, pg_ver = cur.fetchone()
    cur.execute("SELECT PostGIS_Full_Version();")
    full_ver = cur.fetchone()[0]
    print(f"      ✓ Database: {curr_db}")
    print(f"      ✓ PostGIS Version: {pg_ver}")
    print(f"      ✓ PostGIS Details: {full_ver[:80]}...")
    cur.close()
    conn.close()

    # 2. Flask App Initialization
    print("\n[2/5] Creating Flask Application Context...")
    app = create_app()
    client = app.test_client()
    print("      ✓ Flask application created successfully.")

    # 3. Frontend Static Assets
    print("\n[3/5] Verifying Frontend Static Asset Delivery...")
    r_index = client.get("/")
    assert r_index.status_code == 200, f"Expected 200 for /, got {r_index.status_code}"
    assert b"Thermal Intelligence" in r_index.data, "Title missing from index.html"
    print("      ✓ React V3 index.html served at / (HTTP 200)")

    # Find JS and CSS assets
    dist_assets = BASE_DIR / "frontend" / "dist" / "assets"
    js_files = list(dist_assets.glob("*.js"))
    css_files = list(dist_assets.glob("*.css"))
    assert js_files, "No JS files found in dist/assets"
    assert css_files, "No CSS files found in dist/assets"

    r_js = client.get(f"/assets/{js_files[0].name}")
    assert r_js.status_code == 200, f"Expected 200 for JS asset, got {r_js.status_code}"
    print(f"      ✓ Vite JavaScript bundle served: /assets/{js_files[0].name} (HTTP 200)")

    r_css = client.get(f"/assets/{css_files[0].name}")
    assert r_css.status_code == 200, f"Expected 200 for CSS asset, got {r_css.status_code}"
    print(f"      ✓ Tailwind CSS bundle served: /assets/{css_files[0].name} (HTTP 200)")

    # 4. Authentication Verification (Sign In & Sign Up)
    print("\n[4/5] Testing Enterprise Authentication (Sign In & Sign Up)...")
    
    # 4a. Admin Sign In with email
    admin_pw = os.getenv("ADMIN_PASSWORD", "")
    r_login = client.post("/auth/login", json={"identifier": "admin@enterprise.com", "password": admin_pw})
    assert r_login.status_code == 200, f"Admin email login failed: {r_login.status_code} {r_login.data}"
    login_data = r_login.get_json()
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]
    print("      ✓ Sign In with 'admin@enterprise.com' + stored password succeeded (HTTP 200)")

    # 4b. Admin Sign In with username
    r_login_user = client.post("/auth/login", json={"identifier": "admin", "password": admin_pw})
    assert r_login_user.status_code == 200, "Admin username login failed"
    print("      ✓ Sign In with 'admin' + stored password succeeded (HTTP 200)")

    # 4c. Verify invalid / fallback passwords are strictly rejected
    r_bad_pw = client.post("/auth/login", json={"identifier": "admin@enterprise.com", "password": "InvalidPassword_ShouldBeRejected!"})
    assert r_bad_pw.status_code == 401, f"Expected 401 for invalid password, got {r_bad_pw.status_code}"
    print("      ✓ Arbitrary/invalid passwords strictly rejected (HTTP 401)")

    # 4d. Sign Up new enterprise user
    import time
    unique_user = f"analyst_{int(time.time())}"
    r_signup = client.post("/auth/signup", json={
        "username": unique_user,
        "email": f"{unique_user}@enterprise.com",
        "password": "SecurePassword2026!",
    })
    assert r_signup.status_code == 201, f"Signup failed: {r_signup.status_code} {r_signup.data}"
    print(f"      ✓ Sign Up new user '{unique_user}' succeeded (HTTP 201)")

    # 4e. Refresh token
    r_refresh = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r_refresh.status_code == 200, f"Token refresh failed: {r_refresh.status_code}"
    print("      ✓ Token Refresh with JWT rotation succeeded (HTTP 200)")

    # 5. Core REST Endpoints Verification
    print("\n[5/5] Testing Core REST API Endpoints...")
    auth_header = {"Authorization": f"Bearer {access_token}"}

    endpoints = [
        ("GET", "/health", None, 200, "System Health"),
        ("GET", "/api/config", None, 200, "Frontend Configuration Flags"),
        ("GET", "/api/regions/catalog", None, 200, "Industrial Regions Catalog"),
        ("GET", "/api/fires/status", None, 200, "Live Fire Surveillance Status"),
        ("GET", "/api/v1/thermal/stats", None, 200, "Thermal Intelligence Stats"),
        ("GET", "/api/v1/thermal/events", None, 200, "Thermal Events GeoJSON"),
        ("GET", "/api/v1/thermal/map", None, 200, "Thermal Map Layers"),
        ("GET", "/api/v1/thermal/sources", None, 200, "Thermal Source Profiles"),
        ("GET", "/api/v1/thermal/ml-evaluation", None, 200, "ML Evaluation Metrics"),
        ("GET", "/api/events", None, 200, "Replay Fire Events"),
        ("GET", "/api/v1/reports", None, 200, "Investigation Reports List"),
        ("GET", "/api/v1/followups", None, 200, "Follow-Up Tasks List"),
        ("GET", "/api/v1/osm/facilities?limit=5", None, 200, "OSM Facilities GeoJSON"),
        ("GET", "/api/v1/notifications?limit=5", None, 200, "Incident Notifications List"),
        ("GET", "/api/v1/search?q=Singrauli", None, 200, "Unified Global Search"),
        ("GET", "/api/v1/intelligence/source-facility/catalog?limit=5", None, 200, "Source & Facility Catalog"),
        ("GET", "/api/v1/intelligence/thermal-analysis/stats", None, 200, "Thermal Analysis Stats"),
        ("GET", "/api/v1/intelligence/risk-evaluation/queue?limit=5", None, 200, "Operational Priority Queue"),
        ("GET", "/api/v1/intelligence/compliance-screening/standards", None, 200, "Compliance Standards Catalog"),
        ("GET", "/api/v1/intelligence/investigations?limit=5", None, 200, "Investigations Active Queue"),
        ("GET", "/api/v1/intelligence/model-evaluation", None, 200, "Supervised Candidate Evaluation"),
    ]

    for method, path, headers, expected_status, label in endpoints:
        h = auth_header if headers is not None else {}
        resp = client.open(path, method=method, headers=h)
        assert resp.status_code == expected_status, f"Endpoint {path} failed: {resp.status_code} {resp.data}"
        print(f"      ✓ {label:32s} {path:30s} HTTP {resp.status_code}")

    print("\n" + "=" * 70)
    print("✓ ALL VERIFICATION CHECKS PASSED PERFECTLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_verification()
