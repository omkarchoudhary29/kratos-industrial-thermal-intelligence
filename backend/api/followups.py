"""backend/api/followups.py
-------------------------
Follow-Up Task Management API for KRATOS V2.
Enables operational analysts to track observations, persistent clusters,
and investigation reports through verification and resolution workflows.
"""

from datetime import datetime, timezone
from functools import wraps
import logging
import os
from typing import Any, Dict
import uuid

from flask import Blueprint, jsonify, request
from db.connection import db
from db.models import FollowUpTask, FollowUpNote, User
from utils.auth_middleware import _decode_access_token

followups_bp = Blueprint("followups", __name__, url_prefix="/api/v1/followups")
log = logging.getLogger("followups_api")

VALID_PRIORITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
VALID_STATUSES = {
    "OPEN",
    "ASSIGNED",
    "IN_PROGRESS",
    "AWAITING_FIELD_VERIFICATION",
    "AWAITING_VERIFICATION",
    "UNDER_REVIEW",
    "RESOLVED",
    "CLOSED",
}
ACTIVE_STATUSES = {
    "OPEN",
    "ASSIGNED",
    "IN_PROGRESS",
    "AWAITING_FIELD_VERIFICATION",
    "AWAITING_VERIFICATION",
    "UNDER_REVIEW",
}


def optional_token_required(function):
    @wraps(function)
    def decorated(*args, **kwargs):
        user, _ = _decode_access_token()
        if user:
            request.current_user = {
                "user_id": user.id,
                "username": user.username,
                "is_admin": bool(user.is_admin),
                "is_demo": False,
            }
            request.auth_user = user
        else:
            request.current_user = {
                "user_id": None,
                "username": "operator",
                "is_admin": False,
                "is_demo": True,
            }
            request.auth_user = None
        return function(*args, **kwargs)
    return decorated


@followups_bp.route("", methods=["POST"])
@optional_token_required
def create_followup():
    """Create a new persistent follow-up task linked to a feature or report."""
    body: Dict[str, Any] = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    feature_type = (body.get("feature_type") or "cluster").lower().strip()
    feature_id = (body.get("feature_id") or "").strip()

    if not title:
        return jsonify({"error": "Task title is required."}), 400
    if not feature_id:
        return jsonify({"error": "Linked feature ID is required."}), 400

    # Idempotency / Duplicate Prevention Check
    force = body.get("force", False) or request.args.get("force", "false").lower() == "true"
    if not force:
        existing = FollowUpTask.query.filter(
            FollowUpTask.feature_type == feature_type,
            FollowUpTask.feature_id == feature_id,
            FollowUpTask.status.in_(ACTIVE_STATUSES),
        ).first()
        if existing:
            return jsonify({
                "error": f"An active follow-up task already exists for this {feature_type} ({existing.task_key}).",
                "is_duplicate": True,
                "existing_task": {
                    "id": existing.id,
                    "task_key": existing.task_key,
                    "title": existing.title,
                    "status": existing.status,
                    "priority": existing.priority,
                    "assigned_to": existing.assigned_to,
                    "created_at": existing.created_at.isoformat() if existing.created_at else None,
                },
            }), 409

    priority = (body.get("priority") or "MEDIUM").upper().strip()
    if priority not in VALID_PRIORITIES:
        priority = "MEDIUM"

    status = (body.get("status") or "OPEN").upper().strip()
    if status not in VALID_STATUSES:
        status = "OPEN"

    region_name = body.get("region_name") or "General Corridor"
    report_id = body.get("report_id")
    description = body.get("description")
    assigned_to = body.get("assigned_to")
    due_date = body.get("due_date")

    # Current user
    user_payload = request.current_user or {}
    creator_id = user_payload.get("id")
    creator_name = user_payload.get("username") or "Operational Analyst"

    now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    rand_suffix = uuid.uuid4().hex[:6].upper()
    task_key = f"FLW-{now_str}-{rand_suffix}"

    try:
        task = FollowUpTask(
            task_key=task_key,
            title=title,
            feature_type=feature_type,
            feature_id=feature_id,
            region_name=region_name,
            report_id=report_id,
            priority=priority,
            status=status,
            description=description,
            assigned_to=assigned_to,
            due_date=due_date,
            created_by_id=creator_id if creator_id and creator_id > 0 else None,
            created_by_name=creator_name,
        )
        db.session.add(task)
        db.session.flush()

        # Initial audit note
        init_note = FollowUpNote(
            follow_up_id=task.id,
            author_id=creator_id if creator_id and creator_id > 0 else None,
            author_name=creator_name,
            note_text=f"Task initiated with status '{status}' and priority '{priority}'. Initial observation notes: {description or 'None provided.'}",
            status_change=status,
        )
        db.session.add(init_note)
        db.session.commit()

        return jsonify({
            "id": task.id,
            "task_key": task.task_key,
            "title": task.title,
            "feature_type": task.feature_type,
            "feature_id": task.feature_id,
            "region_name": task.region_name,
            "report_id": task.report_id,
            "priority": task.priority,
            "status": task.status,
            "description": task.description,
            "assigned_to": task.assigned_to,
            "created_by_name": task.created_by_name,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }), 201

    except Exception as e:
        db.session.rollback()
        log.error("Failed to create follow-up task: %s", e, exc_info=True)
        return jsonify({"error": f"Failed to create task: {str(e)}"}), 500


@followups_bp.route("", methods=["GET"])
@optional_token_required
def list_followups():
    """List follow-up tasks with optional status and priority filters."""
    status = request.args.get("status")
    priority = request.args.get("priority")
    feature_id = request.args.get("feature_id")
    region = request.args.get("region")
    include_test = request.args.get("include_test", "false").lower() in ("1", "true", "yes")
    limit = min(int(request.args.get("limit", 50)), 100)
    offset = int(request.args.get("offset", 0))

    q = FollowUpTask.query
    if not include_test:
        q = q.filter(FollowUpTask.is_test == False)
    if status and status.upper() in VALID_STATUSES:
        q = q.filter(FollowUpTask.status == status.upper())
    if priority and priority.upper() in VALID_PRIORITIES:
        q = q.filter(FollowUpTask.priority == priority.upper())
    if feature_id:
        q = q.filter(FollowUpTask.feature_id == feature_id)
    if region:
        q = q.filter(FollowUpTask.region_name.ilike(f"%{region}%"))

    total = q.count()
    tasks = q.order_by(FollowUpTask.created_at.desc()).offset(offset).limit(limit).all()

    return jsonify({
        "tasks": [
            {
                "id": t.id,
                "task_key": t.task_key,
                "title": t.title,
                "feature_type": t.feature_type,
                "feature_id": t.feature_id,
                "region_name": t.region_name,
                "report_id": t.report_id,
                "priority": t.priority,
                "status": t.status,
                "description": t.description,
                "assigned_to": t.assigned_to,
                "created_by_name": t.created_by_name,
                "note_count": len(t.notes),
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in tasks
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }), 200


@followups_bp.route("/<identifier>", methods=["GET"])
@optional_token_required
def get_followup(identifier: str):
    """Retrieve full follow-up details including audit notes and attachments."""
    if identifier.isdigit():
        task = db.session.get(FollowUpTask, int(identifier))
    else:
        task = FollowUpTask.query.filter_by(task_key=identifier).first()

    if not task:
        return jsonify({"error": "Task not found"}), 404

    return jsonify({
        "id": task.id,
        "task_key": task.task_key,
        "title": task.title,
        "feature_type": task.feature_type,
        "feature_id": task.feature_id,
        "region_name": task.region_name,
        "report_id": task.report_id,
        "priority": task.priority,
        "status": task.status,
        "description": task.description,
        "assigned_to": task.assigned_to,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_by_name": task.created_by_name,
        "evidence_attachments": task.evidence_attachments or [],
        "audit_trail": task.audit_trail or [],
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "notes": [
            {
                "id": n.id,
                "author_name": n.author_name,
                "note_text": n.note_text,
                "status_change": n.status_change,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in task.notes
        ],
    }), 200


@followups_bp.route("/<identifier>", methods=["PATCH"])
@optional_token_required
def update_followup(identifier: str):
    """Update follow-up task status, priority, description, or assignment."""
    if identifier.isdigit():
        task = db.session.get(FollowUpTask, int(identifier))
    else:
        task = FollowUpTask.query.filter_by(task_key=identifier).first()

    if not task:
        return jsonify({"error": "Task not found"}), 404

    body: Dict[str, Any] = request.get_json(silent=True) or {}
    user_payload = request.current_user or {}
    author_name = user_payload.get("username") or "Operational Analyst"
    author_id = user_payload.get("id")

    status_changed = False
    old_status = task.status
    if "status" in body:
        new_status = body["status"].upper().strip()
        if new_status in VALID_STATUSES and new_status != old_status:
            task.status = new_status
            status_changed = True

    if "priority" in body:
        new_pri = body["priority"].upper().strip()
        if new_pri in VALID_PRIORITIES:
            task.priority = new_pri

    if "assigned_to" in body:
        task.assigned_to = body["assigned_to"]

    if "description" in body:
        task.description = body["description"]

    if "due_date" in body:
        task.due_date = body["due_date"]

    if "evidence_attachments" in body:
        attachments = list(task.evidence_attachments or [])
        new_att = body["evidence_attachments"]
        if isinstance(new_att, list):
            attachments.extend(new_att)
        elif isinstance(new_att, dict):
            attachments.append(new_att)
        task.evidence_attachments = attachments

    # Append note if requested or if status changed
    audit_note = body.get("note") or body.get("note_text")
    if status_changed or audit_note:
        note_msg = audit_note or f"Status transitioned from {old_status} to {task.status}."
        note = FollowUpNote(
            follow_up_id=task.id,
            author_id=author_id if author_id and author_id > 0 else None,
            author_name=author_name,
            note_text=note_msg,
            status_change=task.status if status_changed else None,
        )
        db.session.add(note)

    # Append to audit trail
    trail = list(task.audit_trail or [])
    trail.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": author_name,
        "status": task.status,
        "priority": task.priority,
        "note": audit_note or "",
    })
    task.audit_trail = trail
    task.updated_at = datetime.now(timezone.utc)

    # Record centralized tamper-evident audit log
    from services.audit_service import record_audit_event
    record_audit_event(
        username=author_name,
        user_role=user_payload.get("role", "Field Officer"),
        action_type="FOLLOWUP_TASK_UPDATE",
        resource_type="follow_up_task",
        resource_id=task.task_key,
        status="SUCCESS",
        details={
            "status": task.status,
            "priority": task.priority,
            "assigned_to": task.assigned_to,
            "note": audit_note or "",
        },
        is_test=getattr(task, "is_test", False) or os.getenv("TESTING") == "1",
        session=db.session,
    )
    db.session.commit()

    return jsonify({
        "id": task.id,
        "task_key": task.task_key,
        "status": task.status,
        "priority": task.priority,
        "assigned_to": task.assigned_to,
        "updated_at": task.updated_at.isoformat(),
    }), 200


@followups_bp.route("/merge", methods=["POST"])
@optional_token_required
def merge_followups():
    """Administratively merge duplicate follow-ups into a primary task."""
    body: Dict[str, Any] = request.get_json(silent=True) or {}
    primary_id = body.get("primary_id")
    secondary_ids = body.get("secondary_ids") or []
    notes = body.get("notes", "Administrative merge of duplicate tasks.")

    if not primary_id or not secondary_ids:
        return jsonify({"error": "primary_id and secondary_ids list are required."}), 400

    primary_task = db.session.get(FollowUpTask, int(primary_id))
    if not primary_task:
        return jsonify({"error": f"Primary task {primary_id} not found."}), 404

    merged_count = 0
    for s_id in secondary_ids:
        sec = db.session.get(FollowUpTask, int(s_id))
        if sec and sec.id != primary_task.id:
            for n in sec.notes:
                primary_task.notes.append(FollowUpNote(
                    task=primary_task,
                    author_name=n.author_name,
                    author_id=n.author_id,
                    note_text=f"[Merged from {sec.task_key}] {n.note_text}",
                    status_change=n.status_change,
                ))
            sec.status = "CLOSED"
            close_note = FollowUpNote(
                task=sec,
                author_name="System / Administrator",
                note_text=f"Closed via administrative merge into primary task {primary_task.task_key}: {notes}",
                status_change="CLOSED",
            )
            db.session.add(close_note)
            merged_count += 1

    merge_primary_note = FollowUpNote(
        task=primary_task,
        author_name="System / Administrator",
        note_text=f"Merged {merged_count} duplicate task(s) into this record. Notes: {notes}",
    )
    db.session.add(merge_primary_note)
    db.session.commit()

    return jsonify({
        "status": "success",
        "primary_task_key": primary_task.task_key,
        "merged_tasks_count": merged_count,
    }), 200


@followups_bp.route("/<identifier>/notes", methods=["POST"])
@optional_token_required
def add_followup_note(identifier: str):
    """Add an analyst note to a follow-up task."""
    if identifier.isdigit():
        task = db.session.get(FollowUpTask, int(identifier))
    else:
        task = FollowUpTask.query.filter_by(task_key=identifier).first()

    if not task:
        return jsonify({"error": "Task not found"}), 404

    body: Dict[str, Any] = request.get_json(silent=True) or {}
    note_text = (body.get("note_text") or "").strip()
    if not note_text:
        return jsonify({"error": "Note text cannot be empty."}), 400

    user_payload = request.current_user or {}
    author_name = user_payload.get("username") or "Operational Analyst"
    author_id = user_payload.get("id")

    status_change = body.get("status_change")
    if status_change and status_change.upper() in VALID_STATUSES:
        task.status = status_change.upper()

    note = FollowUpNote(
        follow_up_id=task.id,
        author_id=author_id if author_id and author_id > 0 else None,
        author_name=author_name,
        note_text=note_text,
        status_change=status_change,
    )
    db.session.add(note)
    task.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "id": note.id,
        "author_name": note.author_name,
        "note_text": note.note_text,
        "status_change": note.status_change,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }), 201
