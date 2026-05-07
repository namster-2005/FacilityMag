import datetime

from tests.conftest import get_admin_token, get_staff_token


def test_create_task_admin(client) -> None:
    token = get_admin_token(client)
    resp = client.post(
        "/api/maintenance",
        json={
            "title":     "Test daily clean",
            "frequency": "daily",
            "next_due":  datetime.date.today().isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["data"]["title"] == "Test daily clean"


def test_complete_task_advances_next_due(client) -> None:
    token = get_staff_token(client)

    # Get all tasks and find the weekly one
    resp = client.get("/api/maintenance", headers={"Authorization": f"Bearer {token}"})
    tasks = resp.get_json()["data"]
    weekly = next(t for t in tasks if t["frequency"] == "weekly")
    old_due = weekly["next_due"]

    resp = client.post(
        f"/api/maintenance/{weekly['id']}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    new_due = resp.get_json()["data"]["next_due"]

    old_date = datetime.date.fromisoformat(old_due)
    new_date = datetime.date.fromisoformat(new_due)
    assert new_date > old_date
    assert (new_date - old_date).days == 7


def test_overdue_filter(client) -> None:
    token = get_staff_token(client)
    resp = client.get(
        "/api/maintenance?overdue=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    tasks = resp.get_json()["data"]
    assert len(tasks) >= 1
    for task in tasks:
        assert task["status"] == "Overdue"
