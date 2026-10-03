# KRATOS V3.1 — Production Deployment & Operations

This document describes production architecture, containerization, WSGI worker scaling, reverse proxy configurations, and disaster recovery procedures.

## 1. Production Architecture Overview

```text
Internet / Client Requests
         │
         ▼
[ Nginx Reverse Proxy (TLS 1.3 Termination, Port 443) ]
         │
         ├───► /assets, /           ──► Static Frontend Build (/frontend/dist)
         └───► /api, /auth, /health  ──► Gunicorn / Waitress WSGI (Port 5000)
                                              │
                                              ▼
                                    [ PostgreSQL 18 + PostGIS 3.6 ]
```

## 2. Production WSGI Entrypoints

KRATOS provides dual production-grade WSGI runners:

1. **Linux / Container Deployments (Gunicorn):**
   - Config file: `backend/gunicorn.conf.py`
   - Entrypoint: `wsgi:app`
   - Execution command:
     ```bash
     gunicorn -c backend/gunicorn.conf.py wsgi:app
     ```
   - Worker architecture: 4–8 pre-fork worker processes with gevent/sync worker classes and graceful restarts.

2. **Windows Deployments (Waitress):**
   - Runner: `backend/wsgi.py`
   - Execution command:
     ```powershell
     python backend/wsgi.py
     ```
   - Threading: 8 persistent worker threads configured via `WAITRESS_THREADS=8`.

## 3. Containerized Deployment (Docker Compose)

KRATOS includes production Docker Compose configurations:

- `Dockerfile`: Multi-stage build with minimal runtime footprint.
- `docker-compose.prod.yml`: Coordinates PostgreSQL/PostGIS, WSGI backend, and Nginx reverse proxy.

```bash
# Build and launch production stack
docker compose -f docker-compose.prod.yml up -d --build
```

## 4. Production Security & Environment Checklist

Before launching in production:
1. `APP_MODE`: Set to `production` (or `demo` for public showcase).
2. `JWT_SECRET_KEY`: Set to a cryptographically secure 64-byte random string.
3. `CORS_ALLOWED_ORIGINS`: Restrict strictly to authorized frontend domains (never `*`).
4. `DATABASE_URL`: Use dedicated application user `wildfire_app_user` with restricted privileges.
5. TLS / SSL: Enforce HTTPS via Let's Encrypt / Cloudflare.
6. Rate Limiting: Verified active on login, reports, and AI chat.

## 5. Automated Backup & Disaster Recovery

Run timestamped database backups:

```bash
python scripts/backup_db.py --db wildfire_db --format custom --tag scheduled
```

- **RPO Target:** < 15 minutes (with continuous WAL archiving) / < 24 hours (standalone dumps).
- **RTO Target:** < 30 minutes (dump restore) / < 2 hours (PITR).
- Backups are stored in non-overwriting timestamped files (`backups/wildfire_db_<TIMESTAMP>_scheduled.dump`) with SHA-256 checksum manifests (`backups/backup_manifest.json`).
- Archive readability is verified automatically using `pg_restore -l`.

### Clean Database Restoration Runbook

1. Verify archive readability:
   ```bash
   pg_restore -l backups/wildfire_db_<TIMESTAMP>_scheduled.dump | head -n 30
   ```
2. Terminate active database sessions:
   ```sql
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE datname = 'wildfire_db' AND pid <> pg_backend_pid();
   ```
3. Execute clean restore:
   ```bash
   pg_restore -h localhost -p 5432 -U postgres -d wildfire_db --clean --if-exists --no-owner --no-privileges backups/wildfire_db_<TIMESTAMP>_scheduled.dump
   ```
4. Run post-restore integrity audit:
   ```bash
   python scripts/inspect_db_state.py
   python -m pytest backend/tests/test_audit_hash_chain.py -v
   ```

## 6. Cloud Platform Deployment (Railway / Render / AWS)

For single-container cloud PaaS platforms like Railway:
- Set build context to repository root (`Dockerfile`).
- Provision PostGIS template service (`postgis/postgis:16-3.4` or `postgis/postgis:18-3.6`).
- Inject `DATABASE_URL` or reference variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).
- Configure persistent volume mounted at `/app/data` to ensure downloaded datasets and model artifacts persist across redeployments.
- Set Healthcheck Path to `/health` with 300s timeout.
- Maintain a single web replica to prevent parallel thermal scheduler conflicts.
