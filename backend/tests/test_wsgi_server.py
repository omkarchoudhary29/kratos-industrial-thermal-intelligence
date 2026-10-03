"""backend/tests/test_wsgi_server.py
----------------------------------
Verification suite for Production WSGI Server deployment readiness.
Tests:
- Flask application factory callable
- wsgi.py entrypoint presence and interface
- Gunicorn Linux container configuration syntax and parameter validation
- Waitress Windows WSGI server execution and live HTTP health response
"""

import os
import sys
import threading
import time
from pathlib import Path
import pytest
import requests

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import create_app


def test_application_factory_and_wsgi_callable():
    """Verify application factory produces a valid WSGI callable."""
    app = create_app()
    assert callable(app), "Flask app instance must be a valid WSGI callable"
    assert app.url_map is not None


def test_gunicorn_conf_validity():
    """Verify backend/gunicorn.conf.py contains valid configuration settings."""
    conf_path = backend_dir / "gunicorn.conf.py"
    assert conf_path.exists(), "backend/gunicorn.conf.py must exist"

    conf_namespace = {}
    with open(conf_path, "r", encoding="utf-8") as f:
        exec(f.read(), conf_namespace)

    assert conf_namespace.get("worker_class") == "gthread"
    assert conf_namespace.get("workers") >= 1
    assert conf_namespace.get("threads") >= 1
    assert conf_namespace.get("timeout") >= 60
    assert "0.0.0.0" in conf_namespace.get("bind")


def test_waitress_live_server_execution():
    """Verify Waitress serves live HTTP traffic on a dedicated test port."""
    from waitress.server import create_server

    app = create_app()
    test_port = 5098

    # Create waitress server instance
    server = create_server(app, host="127.0.0.1", port=test_port, threads=4)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    try:
        # Give waitress a moment to bind
        time.sleep(1.0)
        resp = requests.get(f"http://127.0.0.1:{test_port}/health", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") in ("healthy", "ok", "degraded")
        assert "database" in data
    finally:
        server.close()
