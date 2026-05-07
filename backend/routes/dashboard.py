"""
AssetBase — Dashboard route
"""
import datetime
from typing import Any

from flask import Blueprint, jsonify

from database import get_db
from auth import role_required

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("", methods=["GET"])
@role_required("staff")
def get_dashboard() -> Any:
    db = get_db()

    # ── Assets ────────────────────────────────────────────────────────────────
    total_assets = db.execute("SELECT COUNT(*) FROM assets").fetchone()[0]

    by_condition_rows = db.execute(
        "SELECT condition, COUNT(*) AS cnt FROM assets GROUP BY condition"
    ).fetchall()
    by_condition = {r["condition"]: r["cnt"] for r in by_condition_rows}

    by_category_rows = db.execute(
        "SELECT category, COUNT(*) AS cnt FROM assets GROUP BY category"
    ).fetchall()
    by_category = {r["category"]: r["cnt"] for r in by_category_rows}

    need_attention = db.execute(
        "SELECT id, name, condition FROM assets WHERE condition IN ('Bad','Damaged')"
    ).fetchall()

    # ── Tickets ───────────────────────────────────────────────────────────────
    total_tickets = db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    open_tickets  = db.execute(
        "SELECT COUNT(*) FROM tickets WHERE status = 'Open'"
    ).fetchone()[0]
    in_progress   = db.execute(
        "SELECT COUNT(*) FROM tickets WHERE status = 'In Progress'"
    ).fetchone()[0]
    today_str     = datetime.date.today().isoformat()
    overdue_tickets = db.execute(
        "SELECT COUNT(*) FROM tickets WHERE due_date < ? AND status NOT IN ('Resolved','Closed')",
        (today_str,),
    ).fetchone()[0]

    by_priority_rows = db.execute(
        "SELECT priority, COUNT(*) AS cnt FROM tickets GROUP BY priority"
    ).fetchall()
    by_priority = {r["priority"]: r["cnt"] for r in by_priority_rows}

    recent_tickets = db.execute(
        """SELECT id, title, status, priority, created_at
           FROM tickets ORDER BY created_at DESC LIMIT 5"""
    ).fetchall()

    # ── Maintenance ───────────────────────────────────────────────────────────
    total_maint  = db.execute("SELECT COUNT(*) FROM maintenance_tasks").fetchone()[0]
    overdue_maint = db.execute(
        "SELECT COUNT(*) FROM maintenance_tasks WHERE status = 'Overdue'"
    ).fetchone()[0]
    soon_str     = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    due_soon     = db.execute(
        "SELECT COUNT(*) FROM maintenance_tasks WHERE next_due <= ? AND status != 'Done'",
        (soon_str,),
    ).fetchone()[0]

    db.close()

    return jsonify({
        "data": {
            "assets": {
                "total":          total_assets,
                "by_condition":   by_condition,
                "by_category":    by_category,
                "need_attention": [dict(r) for r in need_attention],
            },
            "tickets": {
                "total":       total_tickets,
                "open":        open_tickets,
                "in_progress": in_progress,
                "overdue":     overdue_tickets,
                "by_priority": by_priority,
                "recent":      [dict(r) for r in recent_tickets],
            },
            "maintenance": {
                "total":    total_maint,
                "overdue":  overdue_maint,
                "due_soon": due_soon,
            },
        }
    }), 200
