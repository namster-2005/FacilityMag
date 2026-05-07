"""
AssetBase Backend
-----------------
Flask REST API for co-working facility & asset management.

Start:
    python app.py

Or with gunicorn:
    gunicorn -w 4 -b 0.0.0.0:5000 app:app
"""
import os

from flask import Flask, jsonify, send_from_directory

from database import init_db
from auth import auth_bp
from routes.assets import assets_bp
from routes.tickets import tickets_bp
from routes.maintenance import maintenance_bp
from routes.locations import locations_bp
from routes.dashboard import dashboard_bp

# ── App factory ───────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit

# ── CORS ──────────────────────────────────────────────────────────────────────
@app.after_request
def add_cors(response):  # type: ignore[no-untyped-def]
    origin = os.environ.get("ALLOWED_ORIGIN", "*")
    response.headers["Access-Control-Allow-Origin"]  = origin
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

@app.route("/api/<path:path>", methods=["OPTIONS"])
def handle_options(path: str):  # type: ignore[return-value]
    return "", 204

# ── Blueprints ────────────────────────────────────────────────────────────────
app.register_blueprint(auth_bp)
app.register_blueprint(assets_bp)
app.register_blueprint(tickets_bp)
app.register_blueprint(maintenance_bp)
app.register_blueprint(locations_bp)
app.register_blueprint(dashboard_bp)

# ── Static file serving ───────────────────────────────────────────────────────
QR_DIR     = os.path.join(os.path.dirname(__file__), "qrcodes")
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "uploads"))

@app.route("/qrcodes/<path:filename>")
def serve_qr(filename: str):  # type: ignore[return-value]
    return send_from_directory(QR_DIR, filename)

@app.route("/uploads/<path:filename>")
def serve_uploads(filename: str):  # type: ignore[return-value]
    return send_from_directory(UPLOAD_DIR, filename)

# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/api/health")
def health():  # type: ignore[return-value]
    return jsonify({"status": "ok", "service": "AssetBase API"})

# ── Bootstrap ─────────────────────────────────────────────────────────────────
with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    print(f"AssetBase API running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
