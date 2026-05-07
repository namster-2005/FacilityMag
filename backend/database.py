"""
AssetBase — database layer
Supports both PostgreSQL (production/Supabase) and SQLite (local dev + tests).
Set DATABASE_URL env var to enable PostgreSQL mode.
"""
import os
import uuid
import hashlib
import hmac

DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
_USE_PG: bool     = bool(DATABASE_URL)
DB_PATH: str      = os.environ.get("DB_PATH", "assetbase.db")


# ── Unified Row type ──────────────────────────────────────────────────────────

class Row(dict):
    """Dict subclass that also supports integer-index access (row[0])."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


# ── PostgreSQL backend ────────────────────────────────────────────────────────

if _USE_PG:
    import psycopg2                    # type: ignore
    import psycopg2.extras             # type: ignore

    def _pg_fix(query: str) -> str:
        """Convert SQLite-style placeholders and functions to PostgreSQL."""
        return (
            query
            .replace("?", "%s")
            .replace("datetime('now')", "NOW()")
        )

    class _PGCursor:
        def __init__(self, cur: "psycopg2.extensions.cursor") -> None:
            self._cur = cur

        def fetchone(self) -> "Row | None":
            r = self._cur.fetchone()
            return Row(r) if r else None

        def fetchall(self) -> "list[Row]":
            return [Row(r) for r in (self._cur.fetchall() or [])]

    class _PGConn:
        def __init__(self) -> None:
            self._conn = psycopg2.connect(
                DATABASE_URL,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )

        def execute(self, query: str, params=None) -> _PGCursor:
            cur = self._conn.cursor()
            cur.execute(_pg_fix(query), params or ())
            return _PGCursor(cur)

        def executemany(self, query: str, params_list) -> None:
            q = _pg_fix(query)
            cur = self._conn.cursor()
            for p in params_list:
                cur.execute(q, p)

        def executescript(self, script: str) -> None:
            cur = self._conn.cursor()
            cur.execute(script)

        def commit(self) -> None:
            self._conn.commit()

        def close(self) -> None:
            try:
                self._conn.close()
            except Exception:
                pass

    def get_db() -> _PGConn:
        return _PGConn()

    def init_db() -> None:
        """No-op for PostgreSQL — schema managed via Supabase migrations."""
        pass


# ── SQLite backend (local dev + tests) ───────────────────────────────────────

else:
    import sqlite3

    class _SQLiteCursor:
        def __init__(self, cur: sqlite3.Cursor) -> None:
            self._cur = cur

        def fetchone(self) -> "Row | None":
            r = self._cur.fetchone()
            return Row(dict(r)) if r else None

        def fetchall(self) -> "list[Row]":
            return [Row(dict(r)) for r in (self._cur.fetchall() or [])]

    class _SQLiteConn:
        def __init__(self) -> None:
            self._conn = sqlite3.connect(DB_PATH)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")

        def execute(self, query: str, params=None) -> _SQLiteCursor:
            cur = self._conn.execute(query, params or ())
            return _SQLiteCursor(cur)

        def executemany(self, query: str, params_list) -> None:
            self._conn.executemany(query, params_list)

        def executescript(self, script: str) -> None:
            self._conn.executescript(script)

        def commit(self) -> None:
            self._conn.commit()

        def close(self) -> None:
            self._conn.close()

    def get_db() -> _SQLiteConn:
        return _SQLiteConn()

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','staff','guest')),
        avatar TEXT, created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS locations (
        id TEXT PRIMARY KEY, name TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('site','storage')),
        address TEXT, created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS assets (
        id TEXT PRIMARY KEY, name TEXT NOT NULL,
        category TEXT NOT NULL CHECK(category IN ('Furniture','Equipment','Appliance')),
        description TEXT, location_id TEXT REFERENCES locations(id),
        condition TEXT NOT NULL DEFAULT 'Good'
            CHECK(condition IN ('Excellent','Good','Ok','Bad','Damaged')),
        qr_code_path TEXT, photo_path TEXT, serial_number TEXT, purchase_date TEXT,
        created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS asset_logs (
        id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(id),
        user_id TEXT REFERENCES users(id), action TEXT NOT NULL,
        from_condition TEXT, to_condition TEXT, from_location TEXT, to_location TEXT,
        note TEXT, created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS tickets (
        id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(id),
        title TEXT NOT NULL, description TEXT, issue_type TEXT DEFAULT 'Other',
        status TEXT NOT NULL DEFAULT 'Open'
            CHECK(status IN ('Open','In Progress','Resolved','Closed')),
        priority TEXT NOT NULL DEFAULT 'Standard'
            CHECK(priority IN ('Emergency','Urgent','Standard','Low')),
        reporter_id TEXT REFERENCES users(id), reporter_name TEXT,
        assigned_to TEXT REFERENCES users(id), photo_path TEXT,
        resolution_note TEXT, due_date TEXT,
        created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now')),
        resolved_at TEXT
    );
    CREATE TABLE IF NOT EXISTS ticket_comments (
        id TEXT PRIMARY KEY, ticket_id TEXT NOT NULL REFERENCES tickets(id),
        user_id TEXT REFERENCES users(id), user_name TEXT, body TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS maintenance_tasks (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
        asset_id TEXT REFERENCES assets(id), location_id TEXT REFERENCES locations(id),
        assigned_to TEXT REFERENCES users(id),
        frequency TEXT NOT NULL
            CHECK(frequency IN ('daily','weekly','monthly','quarterly','annual','once')),
        checklist_json TEXT DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'Pending'
            CHECK(status IN ('Pending','In Progress','Done','Overdue')),
        next_due TEXT, last_done_at TEXT,
        created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
    );
    """

    def init_db() -> None:
        db = get_db()
        db.executescript(_SCHEMA)
        db.commit()
        _seed_if_empty(db)
        db.close()

    def _seed_if_empty(db: _SQLiteConn) -> None:
        import datetime as dt
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return
        today = dt.date.today()

        users = [
            ("user-admin-001", "Admin User", "admin@assetbase.com", hash_password("admin123"), "admin"),
            ("user-staff-001", "Minh Tran",  "minh@assetbase.com",  hash_password("staff123"), "staff"),
            ("user-staff-002", "Lan Nguyen", "lan@assetbase.com",   hash_password("staff123"), "staff"),
        ]
        db.executemany("INSERT INTO users (id,name,email,password,role) VALUES (?,?,?,?,?)", users)

        locations = [
            ("loc-001","HQ — Floor 2","site",None), ("loc-002","HQ — Floor 3","site",None),
            ("loc-003","HQ — Pantry","site",None),  ("loc-004","East Branch","site",None),
            ("loc-005","Storage A","storage",None),
        ]
        db.executemany("INSERT INTO locations (id,name,type,address) VALUES (?,?,?,?)", locations)

        assets = [
            ("A001","Ergonomic Chair","Furniture","loc-001","Good"),
            ("A002","Standing Desk","Furniture","loc-002","Excellent"),
            ("A003","Air Conditioner","Appliance","loc-004","Ok"),
            ("A004","Projector","Equipment","loc-005","Good"),
            ("A005","Coffee Machine","Appliance","loc-003","Bad"),
            ("A006","Whiteboard","Furniture","loc-004","Good"),
            ("A007","Sofa","Furniture","loc-005","Damaged"),
            ("A008",'Monitor 27"',"Equipment","loc-001","Excellent"),
            ("A009","Fire Extinguisher","Equipment","loc-002","Good"),
            ("A010","HVAC Unit","Appliance","loc-004","Ok"),
        ]
        db.executemany("INSERT INTO assets (id,name,category,location_id,condition) VALUES (?,?,?,?,?)", assets)

        def due(p: str) -> str:
            return (today + dt.timedelta(days={"Emergency":0,"Urgent":2,"Standard":5,"Low":10}[p])).isoformat()

        tickets = [
            (uuid.uuid4().hex,"A003","AC not cooling","Open","Urgent","user-staff-001",None,"user-staff-001",due("Urgent")),
            (uuid.uuid4().hex,"A005","Coffee machine leaking","In Progress","Urgent","user-staff-002",None,"user-staff-002",due("Urgent")),
            (uuid.uuid4().hex,"A001","Chair armrest broken","Open","Standard",None,"Guest User",None,due("Standard")),
            (uuid.uuid4().hex,"A002","Desk motor stuck","Resolved","Low","user-staff-001",None,"user-staff-001",due("Low")),
            (uuid.uuid4().hex,"A007","Sofa fabric torn","Open","Low",None,"Guest User",None,due("Low")),
        ]
        db.executemany(
            "INSERT INTO tickets (id,asset_id,title,status,priority,reporter_id,reporter_name,assigned_to,due_date) VALUES (?,?,?,?,?,?,?,?,?)",
            tickets,
        )

        tomorrow = (today + dt.timedelta(days=1)).isoformat()
        tasks = [
            (uuid.uuid4().hex,"Daily opening walkthrough",None,"loc-001","user-staff-001","daily","Pending",tomorrow),
            (uuid.uuid4().hex,"Monthly HVAC filter check","A010","loc-004","user-staff-002","monthly","Pending","2026-06-01"),
            (uuid.uuid4().hex,"Quarterly fire extinguisher inspection","A009","loc-002","user-staff-001","quarterly","Overdue","2026-04-01"),
            (uuid.uuid4().hex,"Weekly AV check","A004","loc-005","user-staff-002","weekly","Pending","2026-05-12"),
        ]
        db.executemany(
            "INSERT INTO maintenance_tasks (id,title,asset_id,location_id,assigned_to,frequency,status,next_due) VALUES (?,?,?,?,?,?,?,?)",
            tasks,
        )
        db.commit()


# ── Password helpers (shared) ─────────────────────────────────────────────────

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
    return hmac.compare_digest(expected, digest)
