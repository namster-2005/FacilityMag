"""
AssetBase — Maintenance routes
"""
import uuid
import json
import datetime
from typing import Any

from flask import Blueprint, request, jsonify

from database import get_db
from auth import role_required

maintenance_bp = Blueprint("maintenance", __name__, url_prefix="/api/maintenance")


def _advance_next_due(frequency: str, from_date: str) -> str:
    try:
        base = datetime.date.fromisoformat(from_date)
    except (ValueError, TypeError):
        base = datetime.date.today()

    deltas: dict[str, Any] = {
        "daily":     datetime.timedelta(days=1),
        "weekly":    datetime.timedelta(weeks=1),
        "monthly":   datetime.timedelta(days=30),
        "quarterly": datetime.timedelta(days=91),
        "annual":    datetime.timedelta(days=365),
        "once":      datetime.timedelta(days=0),
    }
    return (base + deltas.get(frequency, datetime.timedelta(days=0))).isoformat()


@maintenance_bp.route("", methods=["GET"])
@role_required("staff")
def list_tasks() -> Any:
    status      = request.args.get("status", "")
    frequency   = request.args.get("frequency", "")
    assigned_to = request.args.get("assigned_to", "")
    overdue     = request.args.get("overdue", "")
    page        = max(1, int(request.args.get("page", 1)))
    limit       = min(200, int(request.args.get("limit", 50)))
    offset      = (page - 1) * limit

    filters: list[str] = []
    params: list[Any]  = []

    if status:
        filters.append("m.status = ?")
        params.append(status)
    if frequency:
        filters.append("m.frequency = ?")
        params.append(frequency)
    if assigned_to:
        filters.append("m.assigned_to = ?")
        params.append(assigned_to)
    if overdue == "true":
        filters.append("m.status = 'Overdue'")

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM maintenance_tasks m {where}", params).fetchone()[0]
    rows = db.execute(
        f"""SELECT m.*,
                   a.name AS asset_name,
                   l.name AS location_name,
                   u.name AS assignee_name
            FROM maintenance_tasks m
            LEFT JOIN assets a    ON a.id = m.asset_id
            LEFT JOIN locations l ON l.id = m.location_id
            LEFT JOIN users u     ON u.id = m.assigned_to
            {where}
            ORDER BY m.next_due ASC
            LIMIT ? OFFSET ?""",
        params + [limit, offset],
    ).fetchall()
    db.close()

    return jsonify({
        "data":  [dict(r) for r in rows],
        "total": total,
        "page":  page,
        "limit": limit,
    }), 200


@maintenance_bp.route("", methods=["POST"])
@role_required("admin")
def create_task() -> Any:
    body = request.get_json(silent=True) or {}
    if not body.get("title"):
        return jsonify({"error": "title is required"}), 400
    if not body.get("frequency"):
        return jsonify({"error": "frequency is required"}), 400

    checklist = body.get("checklist", [])
    task_id = uuid.uuid4().hex
    db = get_db()
    db.execute(
        """INSERT INTO maintenance_tasks
           (id, title, description, asset_id, location_id, assigned_to,
            frequency, checklist_json, status, next_due)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            task_id,
            body["title"],
            body.get("description"),
            body.get("asset_id"),
            body.get("location_id"),
            body.get("assigned_to"),
            body["frequency"],
            json.dumps(checklist),
            body.get("status", "Pending"),
            body.get("next_due", datetime.date.today().isoformat()),
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM maintenance_tasks WHERE id = ?", (task_id,)).fetchone()
    db.close()
    return jsonify({"data": dict(row)}), 201


@maintenance_bp.route("/<task_id>", methods=["GET"])
@role_required("staff")
def get_task(task_id: str) -> Any:
    db = get_db()
    row = db.execute(
        """SELECT m.*,
                   a.name AS asset_name,
                   l.name AS location_name,
                   u.name AS assignee_name
            FROM maintenance_tasks m
            LEFT JOIN assets a    ON a.id = m.asset_id
            LEFT JOIN locations l ON l.id = m.location_id
            LEFT JOIN users u     ON u.id = m.assigned_to
            WHERE m.id = ?""",
        (task_id,),
    ).fetchone()
    db.close()
    if not row:
        return jsonify({"error": "Task not found"}), 404
    return jsonify({"data": dict(row)}), 200


@maintenance_bp.route("/<task_id>", methods=["PUT"])
@role_required("staff")
def update_task(task_id: str) -> Any:
    db = get_db()
    existing = db.execute(
        "SELECT * FROM maintenance_tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "Task not found"}), 404

    body = request.get_json(silent=True) or {}
    updatable = ["title", "description", "asset_id", "location_id",
                 "assigned_to", "frequency", "checklist_json", "status", "next_due"]

    sets: list[str] = ["updated_at = datetime('now')"]
    params: list[Any] = []
    for field in updatable:
        if field in body:
            val = body[field]
            if field == "checklist_json" and isinstance(val, list):
                val = json.dumps(val)
            sets.append(f"{field} = ?")
            params.append(val)
    params.append(task_id)

    db.execute(f"UPDATE maintenance_tasks SET {', '.join(sets)} WHERE id = ?", params)
    db.commit()
    row = db.execute("SELECT * FROM maintenance_tasks WHERE id = ?", (task_id,)).fetchone()
    db.close()
    return jsonify({"data": dict(row)}), 200


@maintenance_bp.route("/<task_id>/complete", methods=["POST"])
@role_required("staff")
def complete_task(task_id: str) -> Any:
    db = get_db()
    task = db.execute(
        "SELECT * FROM maintenance_tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if not task:
        db.close()
        return jsonify({"error": "Task not found"}), 404

    current_due = task["next_due"] or datetime.date.today().isoformat()
    new_due     = _advance_next_due(task["frequency"], current_due)
    now         = datetime.datetime.utcnow().isoformat()

    db.execute(
        """UPDATE maintenance_tasks
           SET status = 'Pending', last_done_at = ?, next_due = ?, updated_at = datetime('now')
           WHERE id = ?""",
        (now, new_due, task_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM maintenance_tasks WHERE id = ?", (task_id,)).fetchone()
    db.close()
    return jsonify({"data": dict(row)}), 200


@maintenance_bp.route("/<task_id>", methods=["DELETE"])
@role_required("admin")
def delete_task(task_id: str) -> Any:
    db = get_db()
    row = db.execute(
        "SELECT id FROM maintenance_tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Task not found"}), 404
    db.execute("DELETE FROM maintenance_tasks WHERE id = ?", (task_id,))
    db.commit()
    db.close()
    return jsonify({"data": {"deleted": True}}), 200
