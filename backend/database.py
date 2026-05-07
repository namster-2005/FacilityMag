"""
AssetBase — database schema and seed data
SQLite with WAL mode and foreign key enforcement.
"""
import os
import sqlite3
import uuid
import hashlib
import hmac


DB_PATH: str = os.environ.get("DB_PATH", "assetbase.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Schema ────────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL,
    role        TEXT NOT NULL CHECK(role IN ('admin','staff','guest')),
    avatar      TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS locations (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL CHECK(type IN ('site','storage')),
    address     TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS assets (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL CHECK(category IN ('Furniture','Equipment','Appliance')),
    description     TEXT,
    location_id     TEXT REFERENCES locations(id),
    condition       TEXT NOT NULL DEFAULT 'Good'
                        CHECK(condition IN ('Excellent','Good','Ok','Bad','Damaged')),
    qr_code_path    TEXT,
    photo_path      TEXT,
    serial_number   TEXT,
    purchase_date   TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS asset_logs (
    id              TEXT PRIMARY KEY,
    asset_id        TEXT NOT NULL REFERENCES assets(id),
    user_id         TEXT REFERENCES users(id),
    action          TEXT NOT NULL,
    from_condition  TEXT,
    to_condition    TEXT,
    from_location   TEXT,
    to_location     TEXT,
    note            TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tickets (
    id              TEXT PRIMARY KEY,
    asset_id        TEXT NOT NULL REFERENCES assets(id),
    title           TEXT NOT NULL,
    description     TEXT,
    issue_type      TEXT DEFAULT 'Other',
    status          TEXT NOT NULL DEFAULT 'Open'
                        CHECK(status IN ('Open','In Progress','Resolved','Closed')),
    priority        TEXT NOT NULL DEFAULT 'Standard'
                        CHECK(priority IN ('Emergency','Urgent','Standard','Low')),
    reporter_id     TEXT REFERENCES users(id),
    reporter_name   TEXT,
    assigned_to     TEXT REFERENCES users(id),
    photo_path      TEXT,
    resolution_note TEXT,
    due_date        TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    resolved_at     TEXT
);

CREATE TABLE IF NOT EXISTS ticket_comments (
    id          TEXT PRIMARY KEY,
    ticket_id   TEXT NOT NULL REFERENCES tickets(id),
    user_id     TEXT REFERENCES users(id),
    user_name   TEXT,
    body        TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS maintenance_tasks (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT,
    asset_id        TEXT REFERENCES assets(id),
    location_id     TEXT REFERENCES locations(id),
    assigned_to     TEXT REFERENCES users(id),
    frequency       TEXT NOT NULL
                        CHECK(frequency IN ('daily','weekly','monthly','quarterly','annual','once')),
    checklist_json  TEXT DEFAULT '[]',
    status          TEXT NOT NULL DEFAULT 'Pending'
                        CHECK(status IN ('Pending','In Progress','Done','Overdue')),
    next_due        TEXT,
    last_done_at    TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
"""


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    salt = uuid.uuid4().hex
    digest = hashlib.sha256((salt + plain).encode()).hexdigest()
    return f"{salt}:{digest}"


def verify_password(plain: str, stored: str) -> bool:
    try:
        salt, digest = stored.split(":", 1)
    except ValueError:
        return False
    expected = hashlib.sha256((salt + plain).encode()).hexdigest()
    # constant-time comparison
    return hmac.compare_digest(expected, digest)


# ── Init + seed ───────────────────────────────────────────────────────────────

def init_db() -> None:
    db = get_db()
    with db:
        db.executescript(SCHEMA)
        _seed_if_empty(db)
    db.close()


def _seed_if_empty(db: sqlite3.Connection) -> None:
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        return

    # Users
    admin_id  = "user-admin-001"
    staff1_id = "user-staff-001"
    staff2_id = "user-staff-002"

    users = [
        (admin_id,  "Admin User",  "admin@assetbase.com", hash_password("admin123"), "admin"),
        (staff1_id, "Minh Tran",   "minh@assetbase.com",  hash_password("staff123"), "staff"),
        (staff2_id, "Lan Nguyen",  "lan@assetbase.com",   hash_password("staff123"), "staff"),
    ]
    db.executemany(
        "INSERT INTO users (id, name, email, password, role) VALUES (?,?,?,?,?)",
        users,
    )

    # Locations
    locations = [
        ("loc-001", "HQ — Floor 2", "site",    None),
        ("loc-002", "HQ — Floor 3", "site",    None),
        ("loc-003", "HQ — Pantry",  "site",    None),
        ("loc-004", "East Branch",  "site",    None),
        ("loc-005", "Storage A",    "storage", None),
    ]
    db.executemany(
        "INSERT INTO locations (id, name, type, address) VALUES (?,?,?,?)",
        locations,
    )

    # Assets
    assets = [
        ("A001", "Ergonomic Chair",    "Furniture",  "loc-001", "Good"),
        ("A002", "Standing Desk",      "Furniture",  "loc-002", "Excellent"),
        ("A003", "Air Conditioner",    "Appliance",  "loc-004", "Ok"),
        ("A004", "Projector",          "Equipment",  "loc-005", "Good"),
        ("A005", "Coffee Machine",     "Appliance",  "loc-003", "Bad"),
        ("A006", "Whiteboard",         "Furniture",  "loc-004", "Good"),
        ("A007", "Sofa",               "Furniture",  "loc-005", "Damaged"),
        ("A008", 'Monitor 27"',        "Equipment",  "loc-001", "Excellent"),
        ("A009", "Fire Extinguisher",  "Equipment",  "loc-002", "Good"),
        ("A010", "HVAC Unit",          "Appliance",  "loc-004", "Ok"),
    ]
    db.executemany(
        "INSERT INTO assets (id, name, category, location_id, condition) VALUES (?,?,?,?,?)",
        assets,
    )

    # Tickets
    import datetime as dt
    today = dt.date.today()

    def due(priority: str) -> str:
        deltas = {"Emergency": 0, "Urgent": 2, "Standard": 5, "Low": 10}
        return (today + dt.timedelta(days=deltas[priority])).isoformat()

    tickets = [
        (uuid.uuid4().hex, "A003", "AC not cooling",          "Open",        "Urgent",   staff1_id, None,         staff1_id, due("Urgent")),
        (uuid.uuid4().hex, "A005", "Coffee machine leaking",  "In Progress", "Urgent",   staff2_id, None,         staff2_id, due("Urgent")),
        (uuid.uuid4().hex, "A001", "Chair armrest broken",    "Open",        "Standard", None,      "Guest User", None,      due("Standard")),
        (uuid.uuid4().hex, "A002", "Desk motor stuck",        "Resolved",    "Low",      staff1_id, None,         staff1_id, due("Low")),
        (uuid.uuid4().hex, "A007", "Sofa fabric torn",        "Open",        "Low",      None,      "Guest User", None,      due("Low")),
    ]
    db.executemany(
        """INSERT INTO tickets
           (id, asset_id, title, status, priority, reporter_id, reporter_name, assigned_to, due_date)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        tickets,
    )

    # Maintenance tasks
    tomorrow = (today + dt.timedelta(days=1)).isoformat()
    tasks = [
        (uuid.uuid4().hex, "Daily opening walkthrough",             None,   "loc-001", staff1_id, "daily",     "Pending",  tomorrow),
        (uuid.uuid4().hex, "Monthly HVAC filter check",             "A010", "loc-004", staff2_id, "monthly",   "Pending",  "2026-06-01"),
        (uuid.uuid4().hex, "Quarterly fire extinguisher inspection","A009", "loc-002", staff1_id, "quarterly", "Overdue",  "2026-04-01"),
        (uuid.uuid4().hex, "Weekly AV check",                       "A004", "loc-005", staff2_id, "weekly",    "Pending",  "2026-05-12"),
    ]
    db.executemany(
        """INSERT INTO maintenance_tasks
           (id, title, asset_id, location_id, assigned_to, frequency, status, next_due)
           VALUES (?,?,?,?,?,?,?,?)""",
        tasks,
    )
