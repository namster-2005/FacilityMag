from tests.conftest import get_admin_token, get_staff_token


def test_guest_report_no_auth(client) -> None:
    resp = client.post(
        "/api/tickets/guest",
        json={"asset_id": "A001", "title": "Leg is wobbly", "reporter_name": "Guest User"},
    )
    assert resp.status_code == 201
    data = resp.get_json()["data"]
    assert data["reporter_id"] is None
    assert data["reporter_name"] == "Guest User"


def test_guest_report_invalid_asset(client) -> None:
    resp = client.post(
        "/api/tickets/guest",
        json={"asset_id": "ZZZZ", "title": "Does not exist"},
    )
    assert resp.status_code == 404


def test_list_tickets_staff(client) -> None:
    token = get_staff_token(client)
    resp = client.get("/api/tickets", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 5


def test_update_ticket_status(client) -> None:
    token = get_staff_token(client)
    # Get first ticket
    resp = client.get("/api/tickets", headers={"Authorization": f"Bearer {token}"})
    ticket_id = resp.get_json()["data"][0]["id"]

    resp = client.put(
        f"/api/tickets/{ticket_id}",
        json={"status": "In Progress"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "In Progress"


def test_add_comment_staff(client) -> None:
    token = get_staff_token(client)
    resp = client.get("/api/tickets", headers={"Authorization": f"Bearer {token}"})
    ticket_id = resp.get_json()["data"][0]["id"]

    resp = client.post(
        f"/api/tickets/{ticket_id}/comment",
        json={"body": "Technician has been notified."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.get_json()["data"]
    assert data["body"] == "Technician has been notified."
