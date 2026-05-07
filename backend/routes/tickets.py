"""
AssetBase — Ticket routes
"""
import uuid
import datetime
from typing import Any

from flask import Blueprint, request, jsonify, g

from database import get_db
from auth import login_required, role_required

tickets_bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")


PRIORITY_DAYS = {"Emergency": 0, "Urgent": 2, "Standard": 5, "Low": 10}


def _calc_due(priority: str) -> str:
    days = PRIORITY_DAYS.get(priority, 5)
    return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()


def _enrich_ticket(row: Any, db: Any) -> dict[str, Any]:
    t = dict(row)
    comments = db.execute(
        "SELECT * FROM ticket_comments WHERE ticket_id = ? ORDER BY created_at ASC",
        (t["id"],),
    ).fetchall()
    t["comments"] = [dict(c) for c in comments]
    return t


# ── Public endpoint ───────────────────────────────────────────────────────────

@tickets_bp.route("/guest", methods=["POST"])
def guest_report() -> Any:
    body = request.get_json(silent=True) or {}
    asset_id = (body.get("asset_id") or "").strip().upper()
    title    = (body.get("title") or "").strip()

    if not asset_id:
        return jsonify({"error": "asset_id is required"}), 400
    if not title:
        return jsonify({"error": "title is required"}), 400

    db = get_db()
    asset = db.execute(
        "SELECT id FROM assets WHERE UPPER(id) = ?", (asset_id,)
    ).fetchone()
    if not asset:
        db.close()
        return jsonify({"error": "Asset not found"}), 404

    priority = body.get("priority", "Standard")
    if priority not in PRIORITY_DAYS:
        priority = "Standard"

    ticket_id = uuid.uuid4().hex
    db.execute(
        """INSERT INTO tickets
           (id, asset_id, title, description, priority, reporter_name, due_date)
           VALUES (?,?,?,?,?,?,?)""",
        (
            ticket_id,
            asset["id"],
            title,
            body.get("description"),
            priority,
            body.get("reporter_name") or "Guest User",
            _calc_due(priority),
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    db.close()
    return jsonify({"data": dict(row)}), 201


# ── Authenticated endpoints ───────────────────────────────────────────────────

@tickets_bp.route("", methods=["GET"])
@role_required("staff")
def list_tickets() -> Any:
    status      = request.args.get("status", "")
    priority    = request.args.get("priority", "")
    asset_id    = request.args.get("asset_id", "")
    assigned_to = request.args.get("assigned_to", "")
    page        = max(1, int(request.args.get("page", 1)))
    limit       = min(200, int(request.args.get("limit", 50)))
    offset      = (page - 1) * limit

    filters: list[str] = []
    params: list[Any]  = []

    if status:
        filters.append("t.status = ?")
        params.append(status)
    if priority:
        filters.append("t.priority = ?")
        params.append(priority)
    if asset_id:
        filters.append("UPPER(t.asset_id) = UPPER(?)")
        params.append(asset_id)
    if assigned_to:
        filters.append("t.assigned_to = ?")
        params.append(assigned_to)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM tickets t {where}", params).fetchone()[0]
    rows = db.execute(
        f"""SELECT t.*, a.name AS asset_name,
                   u.name AS assignee_name
            FROM tickets t
            LEFT JOIN assets a ON a.id = t.asset_id
            LEFT JOIN users u ON u.id = t.assigned_to
            {where}
            ORDER BY t.created_at DESC
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


@tickets_bp.route("", methods=["POST"])
@login_required
def create_ticket() -> Any:
    body     = request.get_json(silent=True) or {}
    asset_id = (body.get("asset_id") or "").strip().upper()
    title    = (body.get("title") or "").strip()

    if not asset_id or not title:
        return jsonify({"error": "asset_id and title are required"}), 400

    db = get_db()
    asset = db.execute("SELECT id FROM assets WHERE UPPER(id) = ?", (asset_id,)).fetchone()
    if not asset:
        db.close()
        return jsonify({"error": "Asset not found"}), 404

    priority = body.get("priority", "Standard")
    ticket_id = uuid.uuid4().hex
    db.execute(
        """INSERT INTO tickets
           (id, asset_id, title, description, issue_type, priority, reporter_id, due_date)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            ticket_id,
            asset["id"],
            title,
            body.get("description"),
            body.get("issue_type", "Other"),
            priority,
            g.current_user["sub"],
            _calc_due(priority),
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    db.close()
    return jsonify({"data": dict(row)}), 201


@tickets_bp.route("/<ticket_id>", methods=["GET"])
@role_required("staff")
def get_ticket(ticket_id: str) -> Any:
    db = get_db()
    row = db.execute(
        """SELECT t.*,
                  a.name AS asset_name, a.category AS asset_category,
                  u.name AS assignee_name
           FROM tickets t
           LEFT JOIN assets a ON a.id = t.asset_id
           LEFT JOIN users u  ON u.id = t.assigned_to
           WHERE t.id = ?""",
        (ticket_id,),
    ).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Ticket not found"}), 404
    data = _enrich_ticket(row, db)
    db.close()
    return jsonify({"data": data}), 200


@tickets_bp.route("/<ticket_id>", methods=["PUT"])
@role_required("staff")
def update_ticket(ticket_id: str) -> Any:
    db = get_db()
    existing = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "Ticket not found"}), 404

    body = request.get_json(silent=True) or {}
    updatable = ["status", "priority", "assigned_to", "resolution_note", "issue_type", "title", "description"]

    sets: list[str] = ["updated_at = datetime('now')"]
    params: list[Any] = []

    for field in updatable:
        if field in body:
            sets.append(f"{field} = ?")
            params.append(body[field])

    if "status" in body and body["status"] == "Resolved" and existing["status"] != "Resolved":
        sets.append("resolved_at = datetime('now')")

    params.append(ticket_id)
    db.execute(f"UPDATE tickets SET {', '.join(sets)} WHERE id = ?", params)
    db.commit()
    row = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    db.close()
    return jsonify({"data": dict(row)}), 200


@tickets_bp.route("/<ticket_id>", methods=["DELETE"])
@role_required("admin")
def delete_ticket(ticket_id: str) -> Any:
    db = get_db()
    row = db.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Ticket not found"}), 404
    db.execute("DELETE FROM ticket_comments WHERE ticket_id = ?", (ticket_id,))
    db.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    db.commit()
    db.close()
    return jsonify({"data": {"deleted": True}}), 200


@tickets_bp.route("/<ticket_id>/comment", methods=["POST"])
@role_required("staff")
def add_comment(ticket_id: str) -> Any:
    db = get_db()
    ticket = db.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if not ticket:
        db.close()
        return jsonify({"error": "Ticket not found"}), 404

    body = request.get_json(silent=True) or {}
    text = (body.get("body") or "").strip()
    if not text:
        db.close()
        return jsonify({"error": "Comment body is required"}), 400

    comment_id = uuid.uuid4().hex
    db.execute(
        """INSERT INTO ticket_comments (id, ticket_id, user_id, user_name, body)
           VALUES (?,?,?,?,?)""",
        (
            comment_id,
            ticket_id,
            g.current_user["sub"],
            g.current_user.get("name", ""),
            text,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM ticket_comments WHERE id = ?", (comment_id,)).fetchone()
    db.close()
    return jsonify({"data": dict(row)}), 201
