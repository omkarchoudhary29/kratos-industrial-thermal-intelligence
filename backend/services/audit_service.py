"""backend/services/audit_service.py
---------------------------------
Centralized Cryptographic Audit Logging Service for KRATOS V3.1.
Implements a tamper-evident hash-chained append-only audit trail.
Each log entry's integrity hash incorporates the canonical serialization of the event
and the cryptographic hash of the immediate predecessor record.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import text
from db.connection import db
from db.models import SystemAuditLog

log = logging.getLogger("audit_service")

# Standard deterministic 64-zero genesis anchor for the chain root
GENESIS_HASH = "0" * 64


def normalize_timestamp_utc(ts: Any) -> str:
    """Normalize any datetime or ISO string to a deterministic UTC ISO-8601 string."""
    if ts is None:
        return ""
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return ts
    if hasattr(ts, "astimezone"):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc).isoformat()
    return str(ts)


def compute_canonical_payload(
    record_id: int,
    timestamp: Any,
    username: str,
    user_role: str,
    action_type: str,
    resource_type: str,
    resource_id: Optional[str],
    details: Optional[Dict[str, Any]],
    previous_hash: str,
    integrity_version: str = "v2_chain",
) -> str:
    """
    Produce a deterministic, canonical UTF-8 serialized representation of an audit event.
    Keys are strictly sorted, separators normalized without whitespace, and nulls canonicalized.
    """
    ts_iso = normalize_timestamp_utc(timestamp)
    canonical_details = (
        json.dumps(details, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
        if details is not None
        else "null"
    )
    return (
        f"{record_id}|{ts_iso}|{username}|{user_role}|{action_type}|"
        f"{resource_type}|{resource_id or ''}|{canonical_details}|{previous_hash}|{integrity_version}"
    )


def compute_audit_hash(
    record_id: int,
    timestamp: Any,
    username: str,
    user_role: str,
    action_type: str,
    resource_type: str,
    resource_id: Optional[str],
    details: Optional[Dict[str, Any]],
    previous_hash: str,
    integrity_version: str = "v2_chain",
) -> str:
    """Compute the SHA-256 hexadecimal digest of the canonicalized audit payload."""
    canonical_payload = compute_canonical_payload(
        record_id=record_id,
        timestamp=timestamp,
        username=username,
        user_role=user_role,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        previous_hash=previous_hash,
        integrity_version=integrity_version,
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def record_audit_event(
    username: str,
    action_type: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[int] = None,
    user_role: str = "Monitoring Analyst",
    ip_address: Optional[str] = None,
    status: str = "SUCCESS",
    details: Optional[Dict[str, Any]] = None,
    is_test: bool = False,
    session: Optional[Any] = None,
) -> SystemAuditLog:
    """
    Append an immutable, cryptographically chained audit log entry within an active transaction.
    Serializes concurrent writers using a PostgreSQL transaction-scoped advisory lock.
    """
    sess = session or db.session

    # 1. Concurrency safety: acquire transactional advisory lock
    sess.execute(text("SELECT pg_advisory_xact_lock(hashtext('kratos_system_audit_logs_chain'));"))

    # 2. Retrieve predecessor record hash in deterministic ID order
    last_record = (
        sess.query(SystemAuditLog.id, SystemAuditLog.integrity_hash)
        .order_by(SystemAuditLog.id.desc())
        .first()
    )
    previous_hash = (
        last_record.integrity_hash
        if (last_record and last_record.integrity_hash)
        else GENESIS_HASH
    )

    # 3. Reserve ID from sequence to bind into canonical hash payload
    next_id = sess.execute(text("SELECT nextval('system_audit_logs_id_seq');")).scalar()

    # 4. Canonical timestamp in UTC
    now_utc = datetime.now(timezone.utc)

    # 5. Compute cryptographic hash chained to previous_hash
    integrity_hash = compute_audit_hash(
        record_id=next_id,
        timestamp=now_utc,
        username=username,
        user_role=user_role,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        previous_hash=previous_hash,
        integrity_version="v2_chain",
    )

    # 6. Instantiate model with full provenance
    audit_entry = SystemAuditLog(
        id=next_id,
        timestamp=now_utc,
        user_id=user_id,
        username=username,
        user_role=user_role,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        status=status,
        details=details,
        is_test=is_test,
        previous_record_hash=previous_hash,
        integrity_hash=integrity_hash,
        integrity_version="v2_chain",
        hash_backfilled_at=None,
    )

    sess.add(audit_entry)
    sess.flush()
    log.info(
        "Recorded chained audit entry %d: %s on %s by %s [hash: %s...]",
        next_id, action_type, resource_type, username, integrity_hash[:12]
    )
    return audit_entry


def verify_audit_chain(session: Optional[Any] = None) -> Dict[str, Any]:
    """
    Verify the integrity of the entire audit chain from genesis to head.
    Detects altered payloads, corrupted hashes, broken predecessor links, and deleted entries.
    """
    sess = session or db.session

    records = (
        sess.query(SystemAuditLog)
        .order_by(SystemAuditLog.id.asc())
        .all()
    )

    if not records:
        return {
            "is_valid": True,
            "total_records": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "broken_links": 0,
            "first_failure": None,
            "chain_head": GENESIS_HASH,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    valid_count = 0
    invalid_count = 0
    broken_links = 0
    first_failure = None
    expected_previous = GENESIS_HASH

    for rec in records:
        # Check 1: Predecessor link integrity
        if rec.previous_record_hash != expected_previous:
            broken_links += 1
            if not first_failure:
                first_failure = {
                    "record_id": rec.id,
                    "reason": "PREDECESSOR_LINK_MISMATCH",
                    "expected_previous_hash": expected_previous,
                    "actual_previous_hash": rec.previous_record_hash,
                }

        # Check 2: Payload hash recomputation with UTC normalized timestamp
        expected_hash = compute_audit_hash(
            record_id=rec.id,
            timestamp=rec.timestamp,
            username=rec.username,
            user_role=rec.user_role,
            action_type=rec.action_type,
            resource_type=rec.resource_type,
            resource_id=rec.resource_id,
            details=rec.details,
            previous_hash=rec.previous_record_hash or expected_previous,
            integrity_version=rec.integrity_version or "v2_chain",
        )

        if rec.integrity_hash != expected_hash:
            invalid_count += 1
            if not first_failure:
                first_failure = {
                    "record_id": rec.id,
                    "reason": "HASH_PAYLOAD_MISMATCH",
                    "expected_hash": expected_hash,
                    "actual_hash": rec.integrity_hash,
                }
        else:
            valid_count += 1

        expected_previous = rec.integrity_hash

    return {
        "is_valid": (invalid_count == 0 and broken_links == 0),
        "total_records": len(records),
        "valid_records": valid_count,
        "invalid_records": invalid_count,
        "broken_links": broken_links,
        "first_failure": first_failure,
        "chain_head": records[-1].integrity_hash if records else GENESIS_HASH,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
