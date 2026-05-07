"""
AssetBase — Asset routes
"""
import os
import uuid
import base64
from typing import Any

from flask import Blueprint, request, jsonify, g

from database import get_db
from auth import login_required, role_required

assets_bp = Blueprint("assets", __name__, url_prefix="/api/assets")

BASE_URL: str = os.environ.get("BASE_URL", "http://localhost:5000")
QR_DIR: str   = os.path.join(os.path.dirname(__file__), "..", "qrcodes")
UPLOAD_DIR: str = os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "uploads"))


def _generate_qr(asset_id: str) -> str:
    """Generate a QR PNG for the scan URL, return file path."""
    import qrcode  # type: ignore

    os.makedirs(QR_DIR, exist_ok=True)
    url = f"{BASE_URL.rstrip('/')}/scan/{asset_id}"
    img = qrcode.make(url)
    path = os.path.join(QR_DIR, f"{asset_id}.png")
    img.save(path)
    return path


def _next_asset_id(db: Any) -> str:
    row = db.execute(
        "SELECT id FROM assets ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row:
        return "A001"
    last = row["id"]  # e.g. A012
    n = int(last[1:]) + 1
    return f"A{n:03d}"


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


# ── Public endpoint ───────────────────────────────────────────────────────────

@assets_bp.route("/scan/<asset_id>", methods=["GET"])
def public_scan(asset_id: str) -> Any:
    db = get_db()
    row = db.execute(
        """SELECT a.id, a.name, a.category, a.condition,
                  l.name AS location_name,
                  (SELECT COUNT(*) FROM tickets t
                   WHERE t.asset_id = a.id AND t.status IN ('Open','In Progress')) AS open_tickets
           FROM assets a
           LEFT JOIN locations l ON l.id = a.location_id
           WHERE UPPER(a.id) = UPPER(?)""",
        (asset_id,),
    ).fetchone()
    db.close()
    if not row:
        return jsonify({"error": "Asset not found"}), 404
    return jsonify({"data": dict(row)}), 200


# ── Authenticated endpoints ───────────────────────────────────────────────────

@assets_bp.route("", methods=["GET"])
@role_required("staff")
def list_assets() -> Any:
    q           = request.args.get("q", "").strip()
    category    = request.args.get("category", "")
    condition   = request.args.get("condition", "")
    location_id = request.args.get("location_id", "")
    page        = max(1, int(request.args.get("page", 1)))
    limit       = min(200, int(request.args.get("limit", 50)))
    offset      = (page - 1) * limit

    filters: list[str] = []
    params: list[Any]  = []

    if q:
        filters.append("(UPPER(a.id) LIKE UPPER(?) OR UPPER(a.name) LIKE UPPER(?))")
        params += [f"%{q}%", f"%{q}%"]
    if category:
        filters.append("a.category = ?")
        params.append(category)
    if condition:
        filters.append("a.condition = ?")
        params.append(condition)
    if location_id:
        filters.append("a.location_id = ?")
        params.append(location_id)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    db = get_db()
    total = db.execute(
        f"SELECT COUNT(*) FROM assets a {where}", params
    ).fetchone()[0]

    rows = db.execute(
        f"""SELECT a.*, l.name AS location_name
            FROM assets a
            LEFT JOIN locations l ON l.id = a.location_id
            {where}
            ORDER BY a.id
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


@assets_bp.route("", methods=["POST"])
@role_required("admin")
def create_asset() -> Any:
    body = request.get_json(silent=True) or {}
    required = ["name", "category"]
    for field in required:
        if not body.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    asset_id  = body.get("id")
    db = get_db()
    if not asset_id:
        asset_id = _next_asset_id(db)

    qr_path = _generate_qr(asset_id)

    db.execute(
        """INSERT INTO assets (id, name, category, description, location_id,
                               condition, qr_code_path, serial_number, purchase_date)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            asset_id,
            body["name"],
            body["category"],
            body.get("description"),
            body.get("location_id"),
            body.get("condition", "Good"),
            qr_path,
            body.get("serial_number"),
            body.get("purchase_date"),
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
    db.close()
    return jsonify({"data": dict(row)}), 201


@assets_bp.route("/<asset_id>", methods=["GET"])
@role_required("staff")
def get_asset(asset_id: str) -> Any:
    db = get_db()
    row = db.execute(
        """SELECT a.*, l.name AS location_name
           FROM assets a
           LEFT JOIN locations l ON l.id = a.location_id
           WHERE UPPER(a.id) = UPPER(?)""",
        (asset_id,),
    ).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Asset not found"}), 404

    logs = db.execute(
        "SELECT * FROM asset_logs WHERE asset_id = UPPER(?) ORDER BY created_at DESC",
        (asset_id,),
    ).fetchall()
    open_tickets = db.execute(
        "SELECT * FROM tickets WHERE UPPER(asset_id) = UPPER(?) AND status IN ('Open','In Progress')",
        (asset_id,),
    ).fetchall()
    db.close()

    data = dict(row)
    data["logs"]         = [dict(l) for l in logs]
    data["open_tickets"] = [dict(t) for t in open_tickets]
    return jsonify({"data": data}), 200


@assets_bp.route("/<asset_id>", methods=["PUT"])
@role_required("staff")
def update_asset(asset_id: str) -> Any:
    db = get_db()
    existing = db.execute(
        "SELECT * FROM assets WHERE UPPER(id) = UPPER(?)", (asset_id,)
    ).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "Asset not found"}), 404

    body = request.get_json(silent=True) or {}
    updatable = ["name", "category", "description", "location_id",
                 "condition", "serial_number", "purchase_date"]

    sets: list[str] = ["updated_at = datetime('now')"]
    params: list[Any] = []
    for field in updatable:
        if field in body:
            sets.append(f"{field} = ?")
            params.append(body[field])
    params.append(existing["id"])

    db.execute(f"UPDATE assets SET {', '.join(sets)} WHERE id = ?", params)

    # Auto-log condition changes
    if "condition" in body and body["condition"] != existing["condition"]:
        db.execute(
            """INSERT INTO asset_logs (id, asset_id, user_id, action, from_condition, to_condition)
               VALUES (?,?,?,?,?,?)""",
            (
                uuid.uuid4().hex,
                existing["id"],
                g.current_user["sub"],
                f"Condition: {existing['condition']} → {body['condition']}",
                existing["condition"],
                body["condition"],
            ),
        )

    # Auto-log location changes
    if "location_id" in body and body["location_id"] != existing["location_id"]:
        db.execute(
            """INSERT INTO asset_logs (id, asset_id, user_id, action, from_location, to_location)
               VALUES (?,?,?,?,?,?)""",
            (
                uuid.uuid4().hex,
                existing["id"],
                g.current_user["sub"],
                f"Location changed",
                existing["location_id"],
                body["location_id"],
            ),
        )

    db.commit()
    row = db.execute("SELECT * FROM assets WHERE id = ?", (existing["id"],)).fetchone()
    db.close()
    return jsonify({"data": dict(row)}), 200


@assets_bp.route("/<asset_id>", methods=["DELETE"])
@role_required("admin")
def delete_asset(asset_id: str) -> Any:
    db = get_db()
    row = db.execute(
        "SELECT id FROM assets WHERE UPPER(id) = UPPER(?)", (asset_id,)
    ).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Asset not found"}), 404
    db.execute("DELETE FROM assets WHERE id = ?", (row["id"],))
    db.commit()
    db.close()
    return jsonify({"data": {"deleted": True}}), 200


@assets_bp.route("/<asset_id>/qr", methods=["GET"])
@role_required("staff")
def get_qr(asset_id: str) -> Any:
    db = get_db()
    row = db.execute(
        "SELECT id, qr_code_path FROM assets WHERE UPPER(id) = UPPER(?)", (asset_id,)
    ).fetchone()
    db.close()
    if not row:
        return jsonify({"error": "Asset not found"}), 404

    qr_path = row["qr_code_path"]
    if not qr_path or not os.path.exists(qr_path):
        qr_path = _generate_qr(row["id"])
        db = get_db()
        db.execute("UPDATE assets SET qr_code_path = ? WHERE id = ?", (qr_path, row["id"]))
        db.commit()
        db.close()

    with open(qr_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    return jsonify({"data": {"qr_base64": f"data:image/png;base64,{b64}"}}), 200


@assets_bp.route("/<asset_id>/logs", methods=["GET"])
@role_required("staff")
def get_logs(asset_id: str) -> Any:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM asset_logs WHERE UPPER(asset_id) = UPPER(?) ORDER BY created_at DESC",
        (asset_id,),
    ).fetchall()
    db.close()
    return jsonify({"data": [dict(r) for r in rows]}), 200


@assets_bp.route("/<asset_id>/photo", methods=["POST"])
@role_required("staff")
def upload_photo(asset_id: str) -> Any:
    db = get_db()
    row = db.execute(
        "SELECT id FROM assets WHERE UPPER(id) = UPPER(?)", (asset_id,)
    ).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Asset not found"}), 404

    if "photo" not in request.files:
        db.close()
        return jsonify({"error": "No photo file provided"}), 400

    file = request.files["photo"]
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"{row['id']}_{uuid.uuid4().hex[:8]}.jpg"
    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)

    db.execute("UPDATE assets SET photo_path = ? WHERE id = ?", (path, row["id"]))
    db.commit()
    db.close()
    return jsonify({"data": {"photo_path": path}}), 200
