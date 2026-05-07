"""
AssetBase — JWT authentication helpers and decorators.
"""
import os
import functools
from datetime import datetime, timezone, timedelta
from typing import Any, Callable

import jwt
from flask import request, jsonify, g
from typing import Optional

from database import get_db, verify_password

JWT_SECRET: str = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7


# ── Token helpers ─────────────────────────────────────────────────────────────

def create_token(user: dict[str, Any]) -> str:
    payload = {
        "sub":   user["id"],
        "email": user["email"],
        "role":  user["role"],
        "name":  user["name"],
        "exp":   datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def _get_token_from_request() -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


# ── Decorators ────────────────────────────────────────────────────────────────

def login_required(f: Callable) -> Callable:
    @functools.wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        token = _get_token_from_request()
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        g.current_user = payload
        return f(*args, **kwargs)
    return wrapper


def role_required(min_role: str) -> Callable:
    ROLE_RANK = {"guest": 0, "staff": 1, "admin": 2}

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        @login_required
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user_role = g.current_user.get("role", "guest")
            if ROLE_RANK.get(user_role, -1) < ROLE_RANK.get(min_role, 99):
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ── Auth routes blueprint ─────────────────────────────────────────────────────

from flask import Blueprint

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
def login() -> Any:
    body = request.get_json(silent=True) or {}
    email: str = (body.get("email") or "").strip().lower()
    password: str = body.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    db = get_db()
    row = db.execute(
        "SELECT id, name, email, password, role FROM users WHERE email = ?", (email,)
    ).fetchone()
    db.close()

    if not row or not verify_password(password, row["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    user = dict(row)
    token = create_token(user)
    return jsonify({
        "data": {
            "token": token,
            "user": {
                "id":    user["id"],
                "name":  user["name"],
                "email": user["email"],
                "role":  user["role"],
            },
        }
    }), 200


@auth_bp.route("/me", methods=["GET"])
@login_required
def me() -> Any:
    u = g.current_user
    return jsonify({"data": {
        "id":    u["sub"],
        "name":  u["name"],
        "email": u["email"],
        "role":  u["role"],
    }}), 200
