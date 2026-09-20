"""Thread-safe sliding-window rate limiter for sensitive and expensive endpoints."""

from __future__ import annotations

import math
import os
import threading
import time
from collections import defaultdict
from functools import wraps
from typing import Callable, Dict, List, Tuple

from flask import jsonify, request


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding window rate limiter."""

    def __init__(self, cleanup_interval: float = 300.0) -> None:
        self._lock = threading.Lock()
        self._records: Dict[str, List[float]] = defaultdict(list)
        self._last_cleanup = time.time()
        self._cleanup_interval = cleanup_interval

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
        """Check if request for key is permitted under limit/window.
        
        Returns (allowed: bool, retry_after: int).
        """
        now = time.time()
        cutoff = now - float(window_seconds)

        with self._lock:
            # Periodic cleanup of expired entries
            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup_locked(now)

            timestamps = self._records[key]
            # Discard timestamps outside window
            valid_timestamps = [t for t in timestamps if t > cutoff]
            self._records[key] = valid_timestamps

            if len(valid_timestamps) >= limit:
                oldest = valid_timestamps[0]
                retry_after = max(1, math.ceil(oldest + window_seconds - now))
                return False, retry_after

            # Record this hit
            valid_timestamps.append(now)
            return True, 0

    def _cleanup_locked(self, now: float) -> None:
        """Purge keys that have had no hits in the last hour."""
        threshold = now - 3600.0
        keys_to_remove = [k for k, v in self._records.items() if not v or v[-1] < threshold]
        for k in keys_to_remove:
            del self._records[k]
        self._last_cleanup = now

    def reset(self) -> None:
        """Reset all rate limiter state."""
        with self._lock:
            self._records.clear()
            self._last_cleanup = time.time()


# Global limiter instance
limiter = SlidingWindowRateLimiter()


def _get_client_ip() -> str:
    """Resolve client IP safely, respecting reverse-proxy X-Forwarded-For."""
    xfwd = request.headers.get("X-Forwarded-For", "").strip()
    if xfwd:
        return xfwd.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def _extract_rate_key(key_type: str) -> str:
    """Derive rate limiting key based on request context."""
    client_ip = _get_client_ip()

    if key_type == "ip_or_identifier":
        # Extract login identifier from JSON body if present
        try:
            body = request.get_json(silent=True) or {}
            identifier = str(
                body.get("identifier") or body.get("username") or body.get("email") or ""
            ).strip().lower()
        except Exception:
            identifier = ""
        if identifier:
            return f"{key_type}:{client_ip}:{identifier}"
        return f"{key_type}:{client_ip}"

    elif key_type == "ip_or_user":
        # Check current user from auth middleware
        current_user = getattr(request, "current_user", None) or {}
        user_id = current_user.get("user_id") or current_user.get("username")
        if user_id:
            return f"{key_type}:user_{user_id}"
        return f"{key_type}:ip_{client_ip}"

    # Default to pure IP
    return f"ip:{client_ip}"


def rate_limit(
    limit: int,
    window_seconds: int = 60,
    key_type: str = "ip_or_user",
    bypass_in_test: bool = True,
) -> Callable:
    """Decorator to rate-limit a Flask route handler using sliding window."""

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Bypass in automated test suites
            if bypass_in_test and os.getenv("TESTING") == "1":
                return fn(*args, **kwargs)

            key = _extract_rate_key(key_type)
            allowed, retry_after = limiter.is_allowed(key, limit, window_seconds)

            if not allowed:
                response = jsonify({
                    "message": f"Too many requests. Limit is {limit} per {window_seconds}s.",
                    "retry_after": retry_after,
                })
                response.status_code = 429
                response.headers["Retry-After"] = str(retry_after)
                return response

            return fn(*args, **kwargs)

        return wrapper

    return decorator


# Convenient pre-configured decorators
limit_login = rate_limit(limit=5, window_seconds=60, key_type="ip_or_identifier")
limit_report_generation = rate_limit(limit=10, window_seconds=60, key_type="ip_or_user")
limit_chat = rate_limit(limit=20, window_seconds=60, key_type="ip_or_user")
