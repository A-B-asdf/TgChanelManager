def test_post_message(client):
    response = client.post(
        "/api/post_msg/",
        json={"channel_id": 123, "text": "test", "parse_mode": "HTML"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("sent", "failed")