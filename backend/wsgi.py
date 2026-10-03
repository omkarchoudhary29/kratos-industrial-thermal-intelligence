"""backend/wsgi.py
Production WSGI application entrypoint for Gunicorn (Linux) and Waitress (Windows).
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from main import create_app, _setup_database_with_retry

app = create_app()

# Initialize database schema/tables safely on startup
with app.app_context():
    _setup_database_with_retry(app)

# Background scheduler guard: only start background scheduler if explicitly enabled
# and avoid duplicate schedulers across multiple workers
if os.getenv("ENABLE_BACKGROUND_SCHEDULER", "1").lower() in ("1", "true", "yes"):
    from pipeline.thermal.refresh import (
        bootstrap_cached_firms,
        start_thermal_refresh_scheduler,
    )
    import threading

    def _run_bg():
        bootstrap_cached_firms(app)
        start_thermal_refresh_scheduler(app)

    threading.Thread(target=_run_bg, daemon=True).start()

if __name__ == "__main__":
    from waitress import serve
    port = int(os.getenv("PORT", "5000"))
    threads = int(os.getenv("WAITRESS_THREADS", "8"))
    print(f"=== Starting Waitress Production WSGI Server on 0.0.0.0:{port} ({threads} threads) ===")
    serve(app, host="0.0.0.0", port=port, threads=threads)
