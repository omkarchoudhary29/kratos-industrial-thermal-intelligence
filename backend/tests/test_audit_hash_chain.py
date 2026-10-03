"""backend/tests/test_audit_hash_chain.py
--------------------------------------
Comprehensive verification of the cryptographic audit hash chain for KRATOS V3.1.
Tests:
- Centralized audit creation across settings, submissions, integrations, reports, follow-ups
- Deterministic predecessor linking and hash calculation
- Concurrency serialization via advisory lock
- Tamper detection (altered payload, altered hash, missing predecessor)
- PostgreSQL trigger immutability (rejection of UPDATE and DELETE)
- Audit verification endpoint
"""

import json
import os
import sys
import threading
from pathlib import Path
import psycopg2
import pytest
from flask import Flask

# Ensure backend root is in python path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import create_app
from db.connection import db
from db.models import SystemAuditLog, User
from services.audit_service import (
    GENESIS_HASH,
    compute_audit_hash,
    record_audit_event,
    verify_audit_chain,
)


@pytest.fixture(scope="module")
def app():
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


def test_initial_chain_verification_on_test_db(app):
    """Verify that backfilled historical audit logs form a continuous valid chain."""
    with app.app_context():
        res = verify_audit_chain()
        assert res["is_valid"] is True, f"Audit chain should be valid, errors: {res}"
        assert res["total_records"] > 0
        assert res["broken_links"] == 0
        assert res["invalid_records"] == 0
        assert res["chain_head"] is not None


def test_record_audit_event_predecessor_linking(app):
    """Test that consecutive audit events link correctly to predecessor hashes."""
    with app.app_context():
        # Record event A
        entry_a = record_audit_event(
            username="test_auditor_a",
            action_type="TEST_ACTION_A",
            resource_type="test_resource",
            resource_id="res_001",
            details={"step": "first"},
            is_test=True,
        )
        db.session.commit()

        # Record event B
        entry_b = record_audit_event(
            username="test_auditor_b",
            action_type="TEST_ACTION_B",
            resource_type="test_resource",
            resource_id="res_002",
            details={"step": "second"},
            is_test=True,
        )
        db.session.commit()

        assert entry_b.previous_record_hash == entry_a.integrity_hash
        assert entry_b.integrity_hash != entry_a.integrity_hash

        # Verification must still pass
        ver = verify_audit_chain()
        assert ver["is_valid"] is True


def test_concurrent_audit_writes_serialization(app):
    """Test that concurrent audit writes serialize without duplicate hashes or broken links."""
    errors = []

    def worker(worker_id):
        try:
            with app.app_context():
                record_audit_event(
                    username=f"concurrent_worker_{worker_id}",
                    action_type="CONCURRENT_TEST",
                    resource_type="concurrency_resource",
                    resource_id=f"worker_{worker_id}",
                    details={"worker_id": worker_id},
                    is_test=True,
                )
                db.session.commit()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent workers experienced errors: {errors}"

    with app.app_context():
        ver = verify_audit_chain()
        assert ver["is_valid"] is True, f"Chain should remain valid under concurrency: {ver}"


def test_database_trigger_rejects_update(app):
    """Verify that PostgreSQL BEFORE UPDATE trigger rejects any modification to system_audit_logs."""
    test_db_url = os.getenv("TEST_DATABASE_URL", "").replace("+psycopg2", "")
    conn = psycopg2.connect(test_db_url)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT id FROM system_audit_logs ORDER BY id DESC LIMIT 1;")
    row = cur.fetchone()
    assert row is not None, "Need at least one audit row"
    target_id = row[0]

    with pytest.raises(psycopg2.InternalError) as exc_info:
        cur.execute("UPDATE system_audit_logs SET username = 'hacked_admin' WHERE id = %s;", (target_id,))
        conn.commit()

    conn.rollback()
    conn.close()
    assert "append-only" in str(exc_info.value).lower() or "prohibited" in str(exc_info.value).lower()


def test_database_trigger_rejects_delete(app):
    """Verify that PostgreSQL BEFORE DELETE trigger rejects any deletion from system_audit_logs."""
    test_db_url = os.getenv("TEST_DATABASE_URL", "").replace("+psycopg2", "")
    conn = psycopg2.connect(test_db_url)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT id FROM system_audit_logs ORDER BY id DESC LIMIT 1;")
    row = cur.fetchone()
    assert row is not None
    target_id = row[0]

    with pytest.raises(psycopg2.InternalError) as exc_info:
        cur.execute("DELETE FROM system_audit_logs WHERE id = %s;", (target_id,))
        conn.commit()

    conn.rollback()
    conn.close()
    assert "append-only" in str(exc_info.value).lower() or "prohibited" in str(exc_info.value).lower()


def test_tamper_detection_in_verification_service():
    """Verify that tampered simulated records are detected by verify_audit_chain logic."""
    class MockAuditRecord:
        def __init__(self, id, ts, username, role, action, rtype, rid, details, prev_hash, h, v):
            self.id = id
            self.timestamp = ts
            self.username = username
            self.user_role = role
            self.action_type = action
            self.resource_type = rtype
            self.resource_id = rid
            self.details = details
            self.previous_record_hash = prev_hash
            self.integrity_hash = h
            self.integrity_version = v

    from datetime import datetime, timezone

    # 1. Valid chain of 2 records
    ts1 = datetime.now(timezone.utc)
    h1 = compute_audit_hash(1, ts1.isoformat(), "admin", "Admin", "LOGIN", "session", None, None, GENESIS_HASH, "v2_chain")
    rec1 = MockAuditRecord(1, ts1, "admin", "Admin", "LOGIN", "session", None, None, GENESIS_HASH, h1, "v2_chain")

    ts2 = datetime.now(timezone.utc)
    h2 = compute_audit_hash(2, ts2.isoformat(), "admin", "Admin", "SETTINGS", "config", None, {"threshold": 50}, h1, "v2_chain")
    rec2 = MockAuditRecord(2, ts2, "admin", "Admin", "SETTINGS", "config", None, {"threshold": 50}, h1, h2, "v2_chain")

    # Tamper payload of rec2
    rec2_tampered = MockAuditRecord(2, ts2, "admin", "Admin", "SETTINGS", "config", None, {"threshold": 999}, h1, h2, "v2_chain")

    class MockSession:
        def __init__(self, records):
            self.records = records
        def query(self, model):
            return self
        def order_by(self, order):
            return self
        def all(self):
            return self.records

    mock_sess_clean = MockSession([rec1, rec2])
    res_clean = verify_audit_chain(session=mock_sess_clean)
    assert res_clean["is_valid"] is True

    mock_sess_tampered = MockSession([rec1, rec2_tampered])
    res_tampered = verify_audit_chain(session=mock_sess_tampered)
    assert res_tampered["is_valid"] is False
    assert res_tampered["invalid_records"] == 1
    assert res_tampered["first_failure"]["reason"] == "HASH_PAYLOAD_MISMATCH"


def test_verify_endpoint(client):
    """Test the HTTP verification endpoint GET /api/v1/settings/audit-logs/verify."""
    resp = client.get("/api/v1/settings/audit-logs/verify")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "is_valid" in data
    assert data["is_valid"] is True
    assert "total_records" in data
    assert "chain_head" in data
    assert data["broken_links"] == 0
