import config  # loads .env variables
import logging
import os
import time
from flask import Flask, Response
from flask_cors import CORS
from pathlib import Path
from db.connection import db, get_db_uri

BASE_DIR     = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def create_app():
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    # ── Environment-Governed CORS Hardening ────────────────────────────────────
    raw_origins = os.getenv("CORS_ALLOWED_ORIGINS")
    is_prod = os.getenv("PRODUCTION", "0").lower() in ("1", "true", "yes") or os.getenv("ENV") == "production"

    if raw_origins:
        allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    elif not is_prod:
        # Default permitted development & staging origins
        allowed_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5000",
            "http://127.0.0.1:5000",
        ]
    else:
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: CORS_ALLOWED_ORIGINS must be explicitly configured "
            "in production environment. Wildcard CORS is strictly prohibited in production mode."
        )

    CORS(
        app,
        resources={r"/*": {"origins": allowed_origins}},
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
        expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
        supports_credentials=True,
    )

    # ── Database & Connection Pooling Configuration ───────────────────────────
    db_uri = get_db_uri()
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if "sqlite" not in db_uri:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            "pool_pre_ping": os.getenv("DB_POOL_PRE_PING", "true").lower() in ("1", "true", "yes"),
        }

    db.init_app(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from api.auth      import auth_bp
    from api.events    import events_bp
    from api.timesteps import timesteps_bp
    from api.firms     import firms_bp
    from api.config    import config_bp
    from api.regions   import regions_bp
    from api.crowd     import crowd_bp
    from api.thermal   import thermal_bp
    from api.fires         import fires_bp
    from api.osm           import osm_bp
    from api.reports       import reports_bp
    from api.followups     import followups_bp
    from api.notifications import notifications_bp
    from api.search        import search_bp
    from api.intelligence  import intelligence_bp
    from api.submissions   import submissions_bp
    from api.analytics      import analytics_bp
    from api.integrations   import integrations_bp
    from api.settings       import settings_bp

    app.register_blueprint(auth_bp,          url_prefix='/auth')
    app.register_blueprint(events_bp,        url_prefix='/api/events')
    app.register_blueprint(timesteps_bp,     url_prefix='/api')
    app.register_blueprint(firms_bp,         url_prefix='/api/firms')
    app.register_blueprint(config_bp,        url_prefix='/api/config')
    app.register_blueprint(regions_bp,       url_prefix='/api/regions')
    app.register_blueprint(crowd_bp,         url_prefix='/api/events')
    app.register_blueprint(thermal_bp,       url_prefix='/api/v1/thermal')
    app.register_blueprint(fires_bp,         url_prefix='/api/fires')
    app.register_blueprint(osm_bp,           url_prefix='/api/v1/osm')
    app.register_blueprint(reports_bp,       url_prefix='/api/v1/reports')
    app.register_blueprint(followups_bp,     url_prefix='/api/v1/followups')
    app.register_blueprint(notifications_bp, url_prefix='/api/v1/notifications')
    app.register_blueprint(search_bp,        url_prefix='/api/v1/search')
    app.register_blueprint(intelligence_bp,  url_prefix='/api/v1/intelligence')
    app.register_blueprint(submissions_bp,   url_prefix='/api/v1/submissions')
    app.register_blueprint(analytics_bp,     url_prefix='/api/v1/analytics')
    app.register_blueprint(integrations_bp,  url_prefix='/api/v1/integrations')
    app.register_blueprint(settings_bp,      url_prefix='/api/v1/settings')

    # ── Frontend routes ───────────────────────────────────────────────────────
    from flask import redirect, request, send_from_directory

    @app.route('/openapi.yaml')
    def openapi_spec():
        """Serve the API contract consumed by the local Swagger UI."""
        return send_from_directory(str(BASE_DIR.parent / 'docs'), 'api.yaml')

    @app.route('/docs')
    @app.route('/docs/')
    def swagger_ui():
        """Render interactive API documentation for the local server."""
        return Response(
            '''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Wildfire Decision Support API</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.ui = SwaggerUIBundle({
        url: '/openapi.yaml',
        dom_id: '#swagger-ui',
        deepLinking: true,
        persistAuthorization: true,
      });
    </script>
  </body>
</html>''',
            mimetype='text/html',
        )

    DIST_DIR = FRONTEND_DIR / "dist"
    LEGACY_DIR = FRONTEND_DIR / "legacy" if (FRONTEND_DIR / "legacy").exists() else FRONTEND_DIR

    @app.route('/')
    @app.route('/login')
    @app.route('/signup')
    @app.route('/dashboard')
    @app.route('/dashboard/')
    def index():
        if DIST_DIR.exists() and (DIST_DIR / 'index.html').exists():
            return send_from_directory(str(DIST_DIR), 'index.html')
        return send_from_directory(str(FRONTEND_DIR), 'index.html')

    @app.route('/assets/<path:filename>')
    def vite_assets(filename):
        """Serve Vite-bundled production assets (JS, CSS, fonts)."""
        if DIST_DIR.exists() and (DIST_DIR / 'assets').exists():
            return send_from_directory(str(DIST_DIR / 'assets'), filename)
        return ('Asset not found', 404)

    @app.route('/health')
    def health():
        """Railway readiness check: HTTP is live and database is reachable."""
        from flask import jsonify
        from sqlalchemy import text

        try:
            db.session.execute(text("SELECT 1"))
        except Exception as exc:
            db.session.rollback()
            app.logger.warning("Health check database query failed: %s", exc)
            return jsonify({"status": "unhealthy", "database": "unavailable"}), 503
        return jsonify({"status": "healthy", "database": "available"}), 200

    @app.route('/demo')
    @app.route('/demo/')
    @app.route('/demo/dashboard')
    @app.route('/demo/dashboard/')
    @app.route('/legacy')
    @app.route('/legacy/')
    def legacy_dashboard():
        """Preserve full access to the legacy SIH demonstration interface."""
        if (LEGACY_DIR / 'dashboard.html').exists():
            return send_from_directory(str(LEGACY_DIR), 'dashboard.html')
        return send_from_directory(str(FRONTEND_DIR), 'dashboard.html')

    @app.route('/demo/dashboard.html')
    @app.route('/dashboard.html')
    def legacy_dashboard_url():
        """Keep old links working while redirecting to the legacy dashboard."""
        query = request.query_string.decode('latin-1')
        target = '/demo' + (f'?{query}' if query else '')
        return redirect(target, code=308)

    @app.route('/css/<path:filename>')
    def frontend_css(filename):
        css_dir = LEGACY_DIR / 'css' if (LEGACY_DIR / 'css').exists() else FRONTEND_DIR / 'css'
        return send_from_directory(str(css_dir), filename)

    @app.route('/js/<path:filename>')
    def frontend_js(filename):
        js_dir = LEGACY_DIR / 'js' if (LEGACY_DIR / 'js').exists() else FRONTEND_DIR / 'js'
        return send_from_directory(str(js_dir), filename)

    @app.route('/demo/<path:filename>')
    @app.route('/legacy/<path:filename>')
    def legacy_static(filename):
        return send_from_directory(str(LEGACY_DIR), filename)

    return app


def _setup_database_with_retry(app):
    """Wait for a separately managed database to accept connections."""
    from pipeline.db import setup_db
    from psycopg2 import OperationalError as PsycopgOperationalError
    from sqlalchemy.exc import OperationalError as SqlalchemyOperationalError

    attempts = max(1, int(os.getenv("DB_STARTUP_MAX_ATTEMPTS", "12")))
    retry_seconds = max(0.1, float(os.getenv("DB_STARTUP_RETRY_SECONDS", "5")))

    for attempt in range(1, attempts + 1):
        try:
            setup_db(app)
            return
        except (PsycopgOperationalError, SqlalchemyOperationalError) as exc:
            if attempt == attempts:
                raise
            logging.warning(
                "Database is not ready (attempt %d/%d): %s; retrying in %.1fs",
                attempt,
                attempts,
                exc,
                retry_seconds,
            )
            time.sleep(retry_seconds)


def _sweep_desynced_timesteps(app):
    """Reset timesteps where STATUS.json says done/failed but output files are gone.

    'running' is stored in-memory only (builder_slots._running) and never written
    to disk, so zombie running states vanish automatically on restart — no sweep needed.
    """
    import json
    import pandas as pd
    from db.models import EventTimestep, FireEvent

    _DATA_DIR = BASE_DIR.parent / "data"

    def _read_status(status_dir) -> str:
        path = Path(status_dir) / "STATUS.json"
        if not path.exists():
            return "pending"
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("status", "pending")
        except Exception:
            return "pending"

    def _write_status(status_dir, status: str) -> None:
        d = Path(status_dir)
        d.mkdir(parents=True, exist_ok=True)
        (d / "STATUS.json").write_text(json.dumps({"status": status}, indent=2), encoding="utf-8")

    with app.app_context():
        rows = EventTimestep.query.all()
        reset_count = 0
        for ts in rows:
            event = db.session.get(FireEvent, ts.event_id)
            if not event:
                continue
            ts_str = pd.Timestamp(ts.slot_time).strftime("%Y-%m-%dT%H%M")
            year = event.year or (event.start_date.year if getattr(event, "start_date", None) else 2026)
            ts_base = _DATA_DIR / "events" / f"{year}_{event.id:04d}" / "timesteps" / ts_str
            ml_dir  = ts_base / "prediction" / "ML"
            sp_dir  = ts_base / "spatial_analysis"

            ml_status = _read_status(ml_dir)
            if ml_status in ("done", "failed"):
                sentinel = ml_dir / "fire_context.json"
                if not sentinel.exists():
                    _write_status(ml_dir, "pending")
                    _write_status(sp_dir, "pending")
                    reset_count += 1

        if reset_count:
            print(f"=== [sweep] Reset {reset_count} desynced timestep(s) to pending ===")
        else:
            print("=== [sweep] All timesteps consistent ===")


if __name__ == '__main__':  
    import threading
    from pipeline.env import prepare_all_events
    from pipeline.check import run_checks

    app = create_app()

    # DB must finish before Flask starts (API needs tables to exist)
    print("=== Setting up database ===")
    _setup_database_with_retry(app)
    print("=== Database ready ===")

    # Pipeline runs in background — Flask starts immediately
    def _run_pipeline():
        run_offline_pipeline = os.getenv(
            "RUN_OFFLINE_PIPELINE_ON_STARTUP", "0"
        ).strip().lower() in {"1", "true", "yes"}
        if run_offline_pipeline:
            print("=== [pipeline] Preparing legacy environment ===")
            prepare_all_events(app)

            print("=== [pipeline] Sweeping desynced timesteps ===")
            _sweep_desynced_timesteps(app)

            print("=== [pipeline] Running checks ===")
            run_checks(app)
            print("=== [pipeline] Complete — timestep slots ready ===")
        else:
            print(
                "=== [pipeline] Offline preprocessing disabled; "
                "using prepared thermal intelligence artifacts ==="
            )

        from pipeline.thermal.refresh import (
            bootstrap_cached_firms,
            start_thermal_refresh_scheduler,
        )
        print("=== [thermal-live] Importing recent cached FIRMS detections ===")
        bootstrap_cached_firms(app)
        start_thermal_refresh_scheduler(app)

    threading.Thread(target=_run_pipeline, daemon=True).start()

    print("=== Starting Flask ===")
    app.run(host='0.0.0.0', debug=False, port=int(os.getenv("PORT", "5000")))
