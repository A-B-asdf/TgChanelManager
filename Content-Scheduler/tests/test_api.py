from content_scheduler.core.database import init_db

def test_add_schedule(client):
    response = client.post(
        "/api/add_account_schedule/123",
        json={"cron": "0 12 * * *", "timezone": "Europe/Moscow", "active": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "created"
    assert data["account_id"] == 123