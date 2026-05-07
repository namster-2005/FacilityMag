import os
import pytest
import tempfile
from typing import Any

# Create a temp DB file — stays open across route handler close() calls
_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_db_file.close()
TEST_DB_PATH = _db_file.name

os.environ["DB_PATH"] = TEST_DB_PATH

import database  # noqa: E402 — must be after env var
from app import app  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db() -> None:
    """Drop + recreate schema and seed before every test."""
    db = database.get_db()
    db.executescript("""
        DROP TABLE IF EXISTS ticket_comments;
        DROP TABLE IF EXISTS tickets;
        DROP TABLE IF EXISTS asset_logs;
        DROP TABLE IF EXISTS maintenance_tasks;
        DROP TABLE IF EXISTS assets;
        DROP TABLE IF EXISTS locations;
        DROP TABLE IF EXISTS users;
    """)
    db.commit()
    db.close()
    with app.app_context():
        database.init_db()


@pytest.fixture
def client() -> Any:
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def get_admin_token(client: Any) -> str:
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@assetbase.com", "password": "admin123"},
    )
    return resp.get_json()["data"]["token"]


def get_staff_token(client: Any) -> str:
    resp = client.post(
        "/api/auth/login",
        json={"email": "minh@assetbase.com", "password": "staff123"},
    )
    return resp.get_json()["data"]["token"]
