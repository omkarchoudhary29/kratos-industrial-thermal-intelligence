# KRATOS V3.1 — Local Development & Setup Guide

This guide describes how to configure, run, and develop on KRATOS V3.1 on a Windows or Linux workstation.

## 1. System Requirements

- **Operating System:** Windows 10/11 or Ubuntu 22.04+ LTS
- **Python:** 3.12+ (64-bit)
- **Node.js:** 18.0+ & npm 9.0+
- **PostgreSQL:** 16+ or 18+ with PostGIS 3.4+ or 3.6+
- **Memory:** Minimum 8 GB RAM (16 GB recommended for geospatial queries)

## 2. PostgreSQL & PostGIS Setup

Ensure PostgreSQL is running and has the PostGIS extension enabled:

```sql
-- Connect as postgres superuser
CREATE DATABASE wildfire_db;
CREATE DATABASE wildfire_test_db;

\c wildfire_db;
CREATE EXTENSION IF NOT EXISTS postgis;

\c wildfire_test_db;
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create test user with isolated privileges
CREATE USER wildfire_test_user WITH PASSWORD 'your_test_password';
GRANT ALL PRIVILEGES ON DATABASE wildfire_test_db TO wildfire_test_user;
```

## 3. Python Virtual Environment & Backend Setup

```powershell
# In repository root
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\activate   # Windows PowerShell
# source .venv/bin/activate # Linux / macOS

# Install required dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment file
Copy-Item .env.example .env
# Edit .env with your local PostgreSQL password and API keys
```

## 4. Database Migrations & Baseline Ingestion

Apply database migrations to prepare schema tables:

```powershell
# Run migrations
python scripts/run_migrations.py

# Ingest OSM facility geometries
python scripts/osm_import.py

# Provision demo reviewer account
python scripts/setup_demo_user.py
```

## 5. Frontend Setup

```powershell
cd frontend
npm install
npm run build   # Verify typecheck and production build
```

## 6. Running the Application

### Option A: Production WSGI & Vite Dev Server (Recommended for Development)

**Terminal 1 (Backend WSGI via Waitress):**
```powershell
# In repository root
.\.venv\Scripts\python.exe backend/wsgi.py
# Server starts on http://localhost:5000 (8 worker threads)
```

**Terminal 2 (Frontend with Reverse Proxy):**
```powershell
cd frontend
npm run dev
# Vite server starts on http://localhost:5173
# Automatically proxies /api, /auth, /health to http://127.0.0.1:5000
```

### Option B: Automated Verification Suite

Run all 140 regression tests against the isolated `wildfire_test_db`:

```powershell
pytest backend/tests/ -v
```
