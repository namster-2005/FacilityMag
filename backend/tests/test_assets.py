from tests.conftest import get_admin_token, get_staff_token


def test_list_assets_requires_auth(client) -> None:
    resp = client.get("/api/assets")
    assert resp.status_code == 401


def test_list_assets_staff(client) -> None:
    token = get_staff_token(client)
    resp = client.get("/api/assets", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 10


def test_create_asset_admin_only(client) -> None:
    admin_token = get_admin_token(client)
    staff_token = get_staff_token(client)

    payload = {"name": "Test Chair", "category": "Furniture", "location_id": "loc-001"}

    # Admin should succeed
    resp = client.post(
        "/api/assets",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201

    # Staff should be forbidden
    resp = client.post(
        "/api/assets",
        json=payload,
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp.status_code == 403


def test_public_scan(client) -> None:
    resp = client.get("/api/assets/scan/A001")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["id"] == "A001"
    # Sensitive fields should not be present
    assert "password" not in data


def test_update_condition_logs(client) -> None:
    token = get_staff_token(client)
    # Update condition
    resp = client.put(
        "/api/assets/A001",
        json={"condition": "Bad"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Verify log entry created
    resp = client.get(
        "/api/assets/A001/logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    logs = resp.get_json()["data"]
    assert len(logs) >= 1
    assert any("Bad" in log["action"] for log in logs)
