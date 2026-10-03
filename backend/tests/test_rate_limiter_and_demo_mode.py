"""Unit tests for thread-safe rate limiter and public demo mode protections."""

import os
import time
from unittest.mock import patch

from flask import Flask, jsonify
import pytest

from utils.rate_limiter import (
    SlidingWindowRateLimiter,
    rate_limit,
    limit_login,
    limit_report_generation,
    limit_chat,
)
from utils.auth_middleware import block_in_demo_mode


class TestSlidingWindowRateLimiter:
    """Core algorithmic unit tests for sliding window rate limiter."""

    def test_basic_limit_enforcement(self):
        limiter = SlidingWindowRateLimiter()
        key = "test_client_1"

        # Allow up to 3
        assert limiter.is_allowed(key, limit=3, window_seconds=10)[0] is True
        assert limiter.is_allowed(key, limit=3, window_seconds=10)[0] is True
        assert limiter.is_allowed(key, limit=3, window_seconds=10)[0] is True

        # 4th should be rejected with positive retry_after
        allowed, retry_after = limiter.is_allowed(key, limit=3, window_seconds=10)
        assert allowed is False
        assert retry_after >= 1

    def test_window_expiration(self):
        limiter = SlidingWindowRateLimiter()
        key = "test_client_exp"

        # 2 allowed
        assert limiter.is_allowed(key, limit=2, window_seconds=1)[0] is True
        assert limiter.is_allowed(key, limit=2, window_seconds=1)[0] is True
        assert limiter.is_allowed(key, limit=2, window_seconds=1)[0] is False

        # Sleep past window
        time.sleep(1.05)
        assert limiter.is_allowed(key, limit=2, window_seconds=1)[0] is True

    def test_limiter_reset(self):
        limiter = SlidingWindowRateLimiter()
        key = "test_reset"

        assert limiter.is_allowed(key, limit=1, window_seconds=60)[0] is True
        assert limiter.is_allowed(key, limit=1, window_seconds=60)[0] is False

        limiter.reset()
        assert limiter.is_allowed(key, limit=1, window_seconds=60)[0] is True


class TestFlaskRateLimiterDecorator:
    """Test Flask decorator integration with status code 429 and Retry-After header."""

    @pytest.fixture
    def app(self):
        app = Flask(__name__)

        @app.route("/test-endpoint", methods=["POST"])
        @rate_limit(limit=2, window_seconds=10, bypass_in_test=False)
        def limited_route():
            return jsonify({"status": "ok"}), 200

        return app

    def test_rate_limit_429_response(self, app):
        client = app.test_client()

        # 2 successful requests
        r1 = client.post("/test-endpoint")
        assert r1.status_code == 200

        r2 = client.post("/test-endpoint")
        assert r2.status_code == 200

        # 3rd request receives 429
        r3 = client.post("/test-endpoint")
        assert r3.status_code == 429
        data = r3.get_json()
        assert "Too many requests" in data["message"]
        assert "Retry-After" in r3.headers


class TestDemoModeGuard:
    """Test demo mode blocking behavior."""

    @pytest.fixture
    def app(self):
        app = Flask(__name__)

        @app.route("/mutating-action", methods=["POST"])
        @block_in_demo_mode("Action blocked in demo mode.")
        def protected_route():
            return jsonify({"success": True}), 200

        return app

    def test_demo_mode_blocks_when_active(self, app):
        client = app.test_client()

        with patch.dict(os.environ, {"APP_MODE": "demo", "TESTING": "0"}):
            resp = client.post("/mutating-action")
            assert resp.status_code == 403
            data = resp.get_json()
            assert data["demo_mode"] is True
            assert "Action blocked in demo mode" in data["message"]

    def test_demo_mode_allows_when_inactive(self, app):
        client = app.test_client()

        with patch.dict(os.environ, {"APP_MODE": "production", "TESTING": "0"}):
            resp = client.post("/mutating-action")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
