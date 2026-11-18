"""backend/gunicorn.conf.py
Gunicorn configuration for KRATOS V3.1 Linux container production deployment.
"""
import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# Concurrency & Worker configuration
workers = int(os.getenv("WEB_CONCURRENCY", "1"))

# Use gthread worker model for native multithreading and SSE streaming compatibility
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", "4"))

# Request timeouts & keepalive
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# Worker recycling to prevent memory leaks from geospatial libraries
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "50"))

# Access and error logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()

# Process naming
proc_name = "kratos_v3_api"


def on_starting(server):
    """Log startup metadata."""
    server.log.info("Starting KRATOS V3.1 Production WSGI Server (Gunicorn gthread)")


def worker_exit(server, worker):
    """Graceful worker exit."""
    server.log.info(f"Worker {worker.pid} exited cleanly.")
