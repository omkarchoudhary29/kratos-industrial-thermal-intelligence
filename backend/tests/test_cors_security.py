"""backend/tests/test_cors_security.py
------------------------------------
Security regression test suite for CORS origin restrictions and preflight enforcement.
Verifies that:
- Allowed origins receive Access-Control-Allow-Origin header
- Unapproved origins are rejected (no allow header or origin reflected)
- Preflight OPTIONS requests succeed with expected headers
- Production mode without explicit CORS_ALLOWED_ORIGINS fails safely
"""

import os
import sys
from pathlib import Path
import pytest

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import create_app


def test_cors_approved_development_origin():
    """Verify that approved localhost origin receives CORS header."""
    os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:5173,https://staging.kratos.internal"
    os.environ["PRODUCTION"] = "0"
    app = create_app()
    client = app.test_client()

    resp = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert resp.headers.get("Access-Control-Allow-Credentials") == "true"


def test_cors_approved_staging_origin():
    """Verify that configured staging origin receives CORS header."""
    os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:5173,https://staging.kratos.internal"
    os.environ["PRODUCTION"] = "0"
    app = create_app()
    client = app.test_client()

    resp = client.get("/health", headers={"Origin": "https://staging.kratos.internal"})
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == "https://staging.kratos.internal"


def test_cors_unapproved_origin_rejected():
    """Verify that an untrusted external origin does not receive Access-Control-Allow-Origin header."""
    os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:5173"
    os.environ["PRODUCTION"] = "0"
    app = create_app()
    client = app.test_client()

    resp = client.get("/health", headers={"Origin": "https://malicious-attacker.com"})
    assert resp.status_code == 200
    # Unapproved origin must NOT be reflected in Access-Control-Allow-Origin
    assert resp.headers.get("Access-Control-Allow-Origin") != "https://malicious-attacker.com"


def test_cors_preflight_options_request():
    """Verify that preflight OPTIONS request returns approved headers and methods."""
    os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:5173"
    os.environ["PRODUCTION"] = "0"
    app = create_app()
    client = app.test_client()

    resp = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization",
        }
    )
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert "POST" in resp.headers.get("Access-Control-Allow-Methods", "")


def test_cors_production_mode_fails_safe_without_origins():
    """Verify that production startup raises RuntimeError when CORS_ALLOWED_ORIGINS is missing."""
    old_origins = os.environ.pop("CORS_ALLOWED_ORIGINS", None)
    os.environ["PRODUCTION"] = "1"

    try:
        with pytest.raises(RuntimeError) as exc_info:
            create_app()
        assert "CORS_ALLOWED_ORIGINS must be explicitly configured" in str(exc_info.value)
    finally:
        os.environ["PRODUCTION"] = "0"
        if old_origins is not None:
            os.environ["CORS_ALLOWED_ORIGINS"] = old_origins
