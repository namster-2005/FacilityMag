"""
AssetBase — Location routes
"""
import uuid
from typing import Any

from flask import Blueprint, request, jsonify

from database import get_db
from auth import role_required

locations_bp = Blueprint("locations", __name__, url_prefix="/api/locations")


@locations_bp.route("", methods=["GET"])
@role_required("staff")
def list_locations() -> Any:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM locations ORDER BY name ASC"
    ).fetchall()
    db.close()
    return jsonify({"data": [dict(r) for r in rows]}), 200


@locations_bp.route("", methods=["POST"])
@role_required("admin")
def create_location() -> Any:
    body = request.get_json(silent=True) or {}
    if not body.get("name"):
        return jsonify({"error": "name is required"}), 400
    if body.get("type") not in ("site", "storage"):
        return jsonify({"error": "type must be 'site' or 'storage'"}), 400

    loc_id = uuid.uuid4().hex
    db = get_db()
    db.execute(
        "INSERT INTO locations (id, name, type, address) VALUES (?,?,?,?)",
        (loc_id, body["name"], body["type"], body.get("address")),
    )
    db.commit()
    row = db.execute("SELECT * FROM locations WHERE id = ?", (loc_id,)).fetchone()
    db.close()
    return jsonify({"data": dict(row)}), 201


@locations_bp.route("/<loc_id>", methods=["PUT"])
@role_required("admin")
def update_location(loc_id: str) -> Any:
    db = get_db()
    existing = db.execute("SELECT id FROM locations WHERE id = ?", (loc_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "Location not found"}), 404

    body = request.get_json(silent=True) or {}
    sets: list[str] = []
    params: list[Any] = []
    for field in ["name", "type", "address"]:
        if field in body:
            sets.append(f"{field} = ?")
            params.append(body[field])
    if not sets:
        db.close()
        return jsonify({"error": "No fields to update"}), 400

    params.append(loc_id)
    db.execute(f"UPDATE locations SET {', '.join(sets)} WHERE id = ?", params)
    db.commit()
    row = db.execute("SELECT * FROM locations WHERE id = ?", (loc_id,)).fetchone()
    db.close()
    return jsonify({"data": dict(row)}), 200


@locations_bp.route("/<loc_id>", methods=["DELETE"])
@role_required("admin")
def delete_location(loc_id: str) -> Any:
    db = get_db()
    row = db.execute("SELECT id FROM locations WHERE id = ?", (loc_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Location not found"}), 404
    db.execute("DELETE FROM locations WHERE id = ?", (loc_id,))
    db.commit()
    db.close()
    return jsonify({"data": {"deleted": True}}), 200
